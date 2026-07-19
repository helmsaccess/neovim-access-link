"""Narrow Windows API adapters backed by NVDA 2026.1 interfaces."""

from __future__ import annotations


_ERROR_INVALID_PARAMETER = 87
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259


def windowIdentityExists(identity, *, _winUser=None):
	"""Return True or False for a conclusive HWND check, or None if uncertain."""
	try:
		if _winUser is None:
			import winUser as _winUser
		if not _winUser.isWindow(identity.window_handle):
			return False
		processID, threadID = _winUser.getWindowThreadProcessID(identity.window_handle)
		if not threadID:
			return False
		return processID == identity.process_id
	except Exception:
		return None


def processAlive(pid, *, _kernel32=None, _winKernel=None):
	"""Return True or False for a conclusive process check, or None if uncertain."""
	try:
		if _kernel32 is None:
			from winBindings import kernel32 as _kernel32
		if _winKernel is None:
			import winKernel as _winKernel
		handle = _kernel32.OpenProcess(
			_PROCESS_QUERY_LIMITED_INFORMATION,
			False,
			pid,
		)
		if not handle:
			return False if _kernel32.GetLastError() == _ERROR_INVALID_PARAMETER else None
		try:
			return _winKernel.GetExitCodeProcess(handle) == _STILL_ACTIVE
		finally:
			try:
				_winKernel.closeHandle(handle)
			except Exception:
				pass
	except Exception:
		return None
