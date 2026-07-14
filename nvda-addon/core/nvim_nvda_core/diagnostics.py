"""Thread-safe, bounded and privacy-preserving diagnostic report."""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from typing import Any

_SENSITIVE = frozenset({
    "password", "lineText", "selectedText", "text", "beforeText", "registerText",
})


class DiagnosticBuffer:
    def __init__(self, max_entries: int = 500) -> None:
        self._entries: deque[dict[str, Any]] = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self.started_ns = time.monotonic_ns()

    def record(self, category: str, **fields: Any) -> None:
        safe = {key: self._sanitize(key, value) for key, value in fields.items()}
        entry = {
            "elapsedMs": round((time.monotonic_ns() - self.started_ns) / 1_000_000, 3),
            "thread": threading.current_thread().name,
            "category": category,
            **safe,
        }
        with self._lock:
            self._entries.append(entry)

    def report(
        self,
        header: dict[str, Any] | None = None,
        *,
        product_name: str | None = None,
    ) -> str:
        with self._lock:
            entries = list(self._entries)
        title = f"{product_name} diagnostic report" if product_name else "Diagnostic report"
        lines = [title, "privacy: text and tokens redacted"]
        if header:
            lines.append("header=" + json.dumps(header, ensure_ascii=False, sort_keys=True, default=str))
        lines.extend(json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str) for entry in entries)
        return "\n".join(lines)

    def _sanitize(self, key: str, value: Any) -> Any:
        if key in _SENSITIVE:
            return f"<redacted length={len(value) if isinstance(value, (str, bytes, list)) else 'unknown'}>"
        if isinstance(value, dict):
            return {nested_key: self._sanitize(nested_key, nested) for nested_key, nested in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._sanitize(key, item) for item in value[:50]]
        if isinstance(value, str) and len(value) > 500:
            return value[:500] + "<truncated>"
        return value
