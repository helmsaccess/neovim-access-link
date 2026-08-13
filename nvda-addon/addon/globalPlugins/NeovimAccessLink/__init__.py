"""Minimal NVDA entry point for the structured Neovim integration."""

import addonHandler
import globalPluginHandler
from logHandler import log

addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Own exactly one process-wide runtime generation."""

	def __init__(self):
		super().__init__()
		from .composition import create_runtime
		from .runtime_config import ADDON_ID, ADDON_VERSION

		self._addonIdentity = (ADDON_ID, ADDON_VERSION)
		try:
			self._runtime = create_runtime()
		except Exception:
			super().terminate()
			raise
		log.info("%s %s initialized", ADDON_ID, ADDON_VERSION)

	def terminate(self):
		addon_id, addon_version = self._addonIdentity
		runtime = getattr(self, "_runtime", None)
		try:
			if runtime is not None:
				runtime.close()
		finally:
			log.info("%s %s terminated", addon_id, addon_version)
			super().terminate()
