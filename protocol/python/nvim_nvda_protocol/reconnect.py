"""Deterministic SSH reconnect backoff."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExponentialBackoff:
    initial_seconds: float = 0.25
    maximum_seconds: float = 10.0
    factor: float = 2.0
    _next_seconds: float | None = None

    def next_delay(self) -> float:
        delay = self.initial_seconds if self._next_seconds is None else self._next_seconds
        self._next_seconds = min(self.maximum_seconds, delay * self.factor)
        return delay

    def reset(self) -> None:
        self._next_seconds = None
