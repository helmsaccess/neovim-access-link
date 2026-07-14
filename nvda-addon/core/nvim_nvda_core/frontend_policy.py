"""Validated allow-list for terminal frontend adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


AVAILABLE_ADAPTERS = {"windowsTerminal": "windowsterminal"}


@dataclass(frozen=True)
class FrontendDescriptor:
    kind: str
    status: str
    app_module: str
    uia_class_names: frozenset[str]
    requires_runtime_id: bool

    @property
    def enabled(self) -> bool:
        return self.status == "enabled"


class FrontendPolicy:
    def __init__(self, descriptors: tuple[FrontendDescriptor, ...]) -> None:
        self._descriptors = {descriptor.kind: descriptor for descriptor in descriptors}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FrontendPolicy":
        if not isinstance(value, Mapping) or value.get("format") != 1:
            raise ValueError("frontend policy format must be 1")
        raw_frontends = value.get("frontends")
        if not isinstance(raw_frontends, list) or not raw_frontends:
            raise ValueError("frontend policy requires a non-empty frontend list")
        descriptors = []
        seen = set()
        for raw in raw_frontends:
            if not isinstance(raw, Mapping):
                raise ValueError("frontend entries must be objects")
            kind = raw.get("kind")
            status = raw.get("status")
            app_module = raw.get("appModule")
            classes = raw.get("uiaClassNames")
            requires_runtime = raw.get("requiresRuntimeId")
            if not isinstance(kind, str) or not kind or kind in seen:
                raise ValueError("frontend kinds must be unique non-empty strings")
            if status not in {"enabled", "planned", "disabled"}:
                raise ValueError("frontend status is invalid")
            if not isinstance(app_module, str):
                raise ValueError("appModule must be a string")
            if status == "enabled" and kind not in AVAILABLE_ADAPTERS:
                raise ValueError(f"no implemented adapter for enabled frontend {kind}")
            if status == "enabled" and app_module != AVAILABLE_ADAPTERS[kind]:
                raise ValueError(f"enabled frontend {kind} requires its implemented AppModule")
            if not isinstance(classes, list) or not all(
                isinstance(item, str) and item for item in classes
            ):
                raise ValueError("uiaClassNames must contain non-empty strings")
            if not isinstance(requires_runtime, bool):
                raise ValueError("requiresRuntimeId must be boolean")
            if status == "enabled" and not classes:
                raise ValueError("enabled frontends require explicit UIA classes")
            seen.add(kind)
            descriptors.append(FrontendDescriptor(
                kind=kind,
                status=status,
                app_module=app_module,
                uia_class_names=frozenset(classes),
                requires_runtime_id=requires_runtime,
            ))
        return cls(tuple(descriptors))

    def descriptor(self, kind: str) -> FrontendDescriptor | None:
        return self._descriptors.get(kind)

    def allows(self, kind: str) -> bool:
        descriptor = self.descriptor(kind)
        return descriptor is not None and descriptor.enabled

    @property
    def enabled_kinds(self) -> frozenset[str]:
        return frozenset(
            descriptor.kind for descriptor in self._descriptors.values() if descriptor.enabled
        )
