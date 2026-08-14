"""Process-wide publication for the narrow terminal integration service."""

from __future__ import annotations

from .core.service_registrar import ServiceRegistrar


serviceRegistrar = ServiceRegistrar()


def get_terminal_integration_service():
	"""Return the service published for application and Braille adapters."""
	return serviceRegistrar.current
