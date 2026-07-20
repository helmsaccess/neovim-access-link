"""Construct managed transport clients without owning NVDA or connection state."""

from collections.abc import Callable


class ManagedClientFactory:
	"""Wire transport callbacks to one instance-aware event boundary."""

	def __init__(
		self,
		*,
		local_client_constructor: Callable[..., object],
		ssh_client_constructor: Callable[..., object],
		on_event: Callable[[str | None, dict], None],
		on_state: Callable[[str | None, str], None],
		record_network_diagnostic: Callable[[str, dict], None],
	):
		self._localClientConstructor = local_client_constructor
		self._sshClientConstructor = ssh_client_constructor
		self._onEvent = on_event
		self._onState = on_state
		self._recordNetworkDiagnostic = record_network_diagnostic

	@staticmethod
	def _instance_id(client: object | None) -> str | None:
		return getattr(client, "nvim_nvda_instance_id", None)

	def create_local(self, session: object) -> object:
		client: object | None = None

		def on_event(event: dict) -> None:
			self._onEvent(self._instance_id(client), event)

		def on_state(state: str) -> None:
			self._onState(self._instance_id(client), state)

		def on_diagnostic(category: str, fields: dict) -> None:
			self._recordNetworkDiagnostic(
				category,
				{**fields, "instanceId": self._instance_id(client)},
			)

		client = self._localClientConstructor(
			session.host,
			session.port,
			on_event,
			on_state,
			on_diagnostic=on_diagnostic,
			session_nonce=session.session_nonce,
		)
		return client

	def create_remote(
		self,
		profile: object,
		session_id: str,
		*,
		password: str,
		askpass_path: str,
	) -> object:
		client: object | None = None

		def on_event(event: dict) -> None:
			self._onEvent(self._instance_id(client), event)

		def on_state(state: str) -> None:
			self._onState(self._instance_id(client), state)

		def on_diagnostic(category: str, fields: dict) -> None:
			self._recordNetworkDiagnostic(
				category,
				{**fields, "instanceId": self._instance_id(client)},
			)

		client = self._sshClientConstructor(
			profile.ssh_target,
			on_event,
			on_state,
			on_diagnostic=on_diagnostic,
			ssh_port=profile.port,
			identity_file=profile.identity_file,
			session_id=session_id,
			password=password,
			askpass_path=askpass_path,
		)
		return client
