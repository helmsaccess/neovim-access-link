"""Session and sequence validation without speech or transport coupling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Disposition = Literal["accept", "duplicate", "staleSession", "resyncRequired"]


@dataclass
class SessionTracker:
    session_id: str | None = None
    last_sequence: int = -1
    needs_resync: bool = True

    def reset(self) -> None:
        self.session_id = None
        self.last_sequence = -1
        self.needs_resync = True

    def observe(self, message: dict[str, Any]) -> Disposition:
        session_id = message["sessionId"]
        sequence = message["sequence"]
        if self.session_id is None:
            self.session_id = session_id
            if message["type"] != "fullState":
                return "resyncRequired"
            self.last_sequence = sequence
            self.needs_resync = False
            return "accept"
        if session_id != self.session_id:
            if message["type"] != "fullState":
                return "staleSession"
            self.session_id = session_id
            self.last_sequence = sequence
            self.needs_resync = False
            return "accept"
        if self.needs_resync:
            if message["type"] != "fullState":
                return "resyncRequired"
            self.last_sequence = sequence
            self.needs_resync = False
            return "accept"
        if sequence <= self.last_sequence:
            return "duplicate"
        if sequence != self.last_sequence + 1:
            self.needs_resync = True
            return "resyncRequired"
        self.last_sequence = sequence
        return "accept"
