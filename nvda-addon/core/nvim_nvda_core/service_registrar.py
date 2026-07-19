"""Identity-safe publication for one process-wide service."""

from __future__ import annotations

from typing import Any


class ServiceRegistrar:
    """Publish a fully initialized service and reject stale removal attempts."""

    def __init__(self) -> None:
        self._current: Any | None = None
        self._token: object | None = None

    @property
    def current(self) -> Any | None:
        return self._current

    def publish(self, service: Any) -> object:
        if service is None:
            raise ValueError("service is required")
        token = object()
        self._current = service
        self._token = token
        return token

    def unpublish(self, service: Any, token: object | None) -> bool:
        if service is not self._current or token is not self._token:
            return False
        self._current = None
        self._token = None
        return True
