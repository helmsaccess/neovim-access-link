"""Construct protocol control messages with one monotonic sequence."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MessageFactory:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence: int = 0

    def create(self, kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        message = {
            "protocolVersion": 2,
            "sessionId": self.session_id,
            "sequence": self.sequence,
            "timestampMonotonic": time.monotonic_ns(),
            "type": kind,
            "payload": payload or {},
        }
        self.sequence += 1
        return message
