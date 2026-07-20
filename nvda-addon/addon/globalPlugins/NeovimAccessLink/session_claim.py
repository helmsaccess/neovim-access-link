"""State owner for one-shot Neovim session claims."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum

from .core.connection_coordinator import ConnectionCoordinator
from .core.connection_instances import ConnectionInstance
from .core.connection_targets import ConnectionTarget
from .core.gate import TerminalIdentity


@dataclass(frozen=True)
class ClaimInventoryResult:
	"""Accepted inventory counts after state has been updated."""

	eligible_targets: int
	errors: int
	eligible_sessions: int
	local_sessions: int
	remote_sessions: int
	automatic_ssh_profiles: int
	scanned_ssh_profiles: int


@dataclass(frozen=True)
class ClaimTargetError:
	"""Safe diagnostic description of one failed target scan."""

	target_kind: str
	target_id: str
	error_type: str
	error: str


@dataclass(frozen=True)
class ClaimResolutionResult:
	"""Fresh candidates and target errors from one accepted scan generation."""

	candidates: tuple[tuple[str, object | None, object], ...]
	errors: tuple[ClaimTargetError, ...]
	targets: int


class ClaimTransitionKind(Enum):
	"""Next action after one authorized claim gesture."""

	PASS_THROUGH = "passThrough"
	INVENTORY_PENDING = "inventoryPending"
	LOCAL = "local"
	REMOTE = "remote"
	AUTOMATIC = "automatic"


class DiscoverySelectionKind(Enum):
	"""Domain outcome of one accepted local or remote session listing."""

	STALE = "stale"
	ERROR = "error"
	EMPTY = "empty"
	FALLBACK = "fallback"
	CLAIM_MISSING = "claimMissing"
	SELECT = "select"
	CHOOSE = "choose"


class ConnectionPlanKind(Enum):
	"""Whether a discovered session reuses an instance or starts a new one."""

	REUSE = "reuse"
	START = "start"


@dataclass(frozen=True)
class ClaimTransition:
	"""Immutable routing decision without NVDA UI or client side effects."""

	kind: ClaimTransitionKind
	identity: TerminalIdentity | None
	target_id: str = ""
	explicit_target: bool = False


@dataclass(frozen=True)
class DiscoverySelection:
	"""Immutable selection result consumed by the NVDA main-thread adapter."""

	kind: DiscoverySelectionKind
	session: object | None = None
	sessions: tuple[object, ...] = ()
	error_type: str = ""
	error: str = ""


@dataclass(frozen=True)
class ConnectionPlan:
	"""Immutable connection action selected from coordinator-owned instances."""

	kind: ConnectionPlanKind
	instance: ConnectionInstance | None = None
	replace_instance_id: str = ""


@dataclass(frozen=True)
class ConnectionReuseResult:
	"""Applied instance binding plus terminal identities displaced by reuse."""

	instance: ConnectionInstance
	displaced_identities: tuple[TerminalIdentity, ...] = ()


@dataclass(frozen=True)
class ConnectionStartResult:
	"""Result of starting and selecting one managed connection instance."""

	instance: ConnectionInstance | None = None
	error_type: str = ""
	error: str = ""
	replacement_error_type: str = ""
	replacement_error: str = ""


class SessionClaimService:
	"""Own claim authorization and inventory state without NVDA dependencies."""

	def __init__(
		self,
		coordinator: ConnectionCoordinator,
		*,
		record_diagnostic: Callable[..., None],
		identity_fields: Callable[[TerminalIdentity | None], dict | None],
		list_local_sessions: Callable[[], list],
		list_remote_sessions: Callable[[object, str], list],
		queue_main_thread: Callable[..., None],
		start_worker: Callable[[str, Callable, tuple], None],
		monotonic: Callable[[], float],
		sleep: Callable[[float], None],
		local_claim_wait_seconds: float,
		local_claim_poll_seconds: float,
		new_instance_runtime: Callable[[], dict],
		stop_client_async: Callable[[str, object], None],
	):
		self._coordinator = coordinator
		self._recordDiagnostic = record_diagnostic
		self._identityFields = identity_fields
		self._listLocalSessions = list_local_sessions
		self._listRemoteSessions = list_remote_sessions
		self._queueMainThread = queue_main_thread
		self._startWorker = start_worker
		self._monotonic = monotonic
		self._sleep = sleep
		self._localClaimWaitSeconds = local_claim_wait_seconds
		self._localClaimPollSeconds = local_claim_poll_seconds
		self._newInstanceRuntime = new_instance_runtime
		self._stopClientAsync = stop_client_async
		self._gestureGeneration = 0
		self._pendingObserved: tuple[TerminalIdentity, int] | None = None
		self._discoveryGeneration = 0
		self._inventoryGeneration = 0
		self._inventoryReady = False
		self._baselines: dict[tuple[str, str, str], int] = {}
		self._eligibleTargets: set[tuple[str, str]] = set()
		self._inventoryErrors: dict[tuple[str, str], str] = {}
		self._pendingTargets: dict[TerminalIdentity, tuple[str, str]] = {}

	def authorize(self, identity: TerminalIdentity | None) -> int | None:
		"""Authorize one physical claim for the exact focused terminal."""
		gate = self._coordinator.gate
		if (
			not gate.manual_enabled
			or identity is None
			or gate.focused != identity
			or identity.frontend_kind != "windowsTerminal"
			or (
				not self._inventoryReady
				and identity not in self._pendingTargets
				and self._coordinator.instances.selected_for(identity) is None
			)
		):
			return None
		self._gestureGeneration += 1
		generation = self._gestureGeneration
		self._pendingObserved = (identity, generation)
		self._recordDiagnostic(
			"sessionClaimAuthorized",
			generation=generation,
			terminal=self._identityFields(identity),
		)
		return generation

	def accept(self, identity: TerminalIdentity, generation: int) -> bool:
		if self._pendingObserved != (identity, generation):
			return False
		self._pendingObserved = None
		gate = self._coordinator.gate
		return gate.manual_enabled and gate.focused == identity

	def cancel(self, identity: TerminalIdentity, generation: int) -> bool:
		"""Discard only a matching queued claim after its frontend scope changed."""
		if self._pendingObserved != (identity, generation):
			return False
		self._pendingObserved = None
		self._recordDiagnostic("sessionClaimIgnored", reason="frontendScopeChanged")
		return True

	def cancel_pending_authorization(self) -> None:
		self._pendingObserved = None

	def consume_transition(self, identity: TerminalIdentity | None) -> ClaimTransition:
		"""Consume a pending target and decide the next claim action."""
		selected = self._coordinator.instances.selected_for(identity) if identity is not None else None
		selected_authenticated = (
			selected is not None and selected.identifier in self._coordinator.authenticated_instances
		)
		pairing_selected = selected if selected_authenticated else None
		self._recordDiagnostic(
			"sessionClaimGestureReceived",
			terminal=self._identityFields(identity),
			inventoryReady=self._inventoryReady,
			selected=selected is not None,
			selectedAuthenticated=selected_authenticated,
		)
		pending_target = self._pendingTargets.pop(identity, None) if identity is not None else None
		if (
			pending_target is None
			and pairing_selected is not None
			and pairing_selected.transport_kind == "localWindowsTcp"
		):
			pending_target = ("localWindowsTcp", "")
		if identity is None or identity.frontend_kind != "windowsTerminal":
			return ClaimTransition(ClaimTransitionKind.PASS_THROUGH, identity)
		if pairing_selected is None and pending_target is None and not self._inventoryReady:
			return ClaimTransition(ClaimTransitionKind.INVENTORY_PENDING, identity)
		if pending_target is not None:
			kind, target_id = pending_target
			if kind == "localWindowsTcp":
				return ClaimTransition(
					ClaimTransitionKind.LOCAL,
					identity,
					explicit_target=True,
				)
			return ClaimTransition(
				ClaimTransitionKind.REMOTE,
				identity,
				target_id=target_id,
				explicit_target=True,
			)
		if pairing_selected is None:
			return ClaimTransition(ClaimTransitionKind.AUTOMATIC, identity)
		return ClaimTransition(
			ClaimTransitionKind.REMOTE,
			identity,
			target_id=pairing_selected.target_id,
		)

	def invalidate_connection_state(self) -> None:
		"""Invalidate callbacks and clear discovery state during disconnect or teardown."""
		self._pendingTargets.clear()
		self._pendingObserved = None
		self._discoveryGeneration += 1
		self._inventoryGeneration += 1
		self._inventoryReady = False
		self._baselines.clear()
		self._eligibleTargets.clear()
		self._inventoryErrors.clear()

	def begin_discovery(self) -> int:
		"""Invalidate older session-list callbacks and return the new generation."""
		self._discoveryGeneration += 1
		return self._discoveryGeneration

	def is_discovery_current(
		self,
		generation: int,
		identity: TerminalIdentity,
		*,
		preserve_dialog_identity: bool = False,
	) -> bool:
		"""Validate a worker or dialog continuation against current claim scope."""
		gate = self._coordinator.gate
		return (
			generation == self._discoveryGeneration
			and gate.manual_enabled
			and (preserve_dialog_identity or gate.focused == identity)
		)

	def start_local_discovery(
		self,
		identity: TerminalIdentity,
		replace_existing: bool,
		offer_remember: bool,
		require_recent_claim: bool,
		fallback_profile: object | None,
		claim_not_before_ns: int,
		finished: Callable[..., None],
	) -> int:
		generation = self.begin_discovery()
		self._startWorker(
			"nvim-nvda-local-session-list",
			self.discover_local_sessions,
			(
				generation,
				identity,
				replace_existing,
				offer_remember,
				require_recent_claim,
				fallback_profile,
				claim_not_before_ns,
				finished,
			),
		)
		return generation

	def discover_local_sessions(
		self,
		generation: int,
		identity: TerminalIdentity,
		replace_existing: bool,
		offer_remember: bool,
		require_recent_claim: bool,
		fallback_profile: object | None,
		claim_not_before_ns: int,
		finished: Callable[..., None],
	) -> None:
		if require_recent_claim:

			def fresh(sessions: list) -> bool:
				return any(
					0 <= session.claim_age_ms <= 15_000
					and (not claim_not_before_ns or session.claimed_monotonic_ns >= claim_not_before_ns)
					for session in sessions
				)

			sessions, error, attempts = self.poll_local_sessions(fresh)
			self._recordDiagnostic(
				"localClaimWaitCompleted",
				attempts=attempts,
				sessions=len(sessions),
				matched=error is None and fresh(sessions),
				errorType=type(error).__name__ if error is not None else "",
			)
		else:
			try:
				sessions, error = self._listLocalSessions(), None
			except Exception as caught:
				sessions, error = [], caught
		self._queueMainThread(
			finished,
			generation,
			identity,
			sessions,
			error,
			replace_existing,
			offer_remember,
			require_recent_claim,
			fallback_profile,
			claim_not_before_ns,
		)

	def start_remote_discovery(
		self,
		profile: object,
		identity: TerminalIdentity,
		password: str,
		replace_existing: bool,
		offer_remember: bool,
		require_recent_claim: bool,
		preserve_dialog_identity: bool,
		finished: Callable[..., None],
	) -> int:
		generation = self.begin_discovery()
		self._startWorker(
			"nvim-nvda-session-list",
			self.discover_remote_sessions,
			(
				generation,
				profile,
				identity,
				password,
				replace_existing,
				offer_remember,
				require_recent_claim,
				preserve_dialog_identity,
				finished,
			),
		)
		return generation

	def discover_remote_sessions(
		self,
		generation: int,
		profile: object,
		identity: TerminalIdentity,
		password: str,
		replace_existing: bool,
		offer_remember: bool,
		require_recent_claim: bool,
		preserve_dialog_identity: bool,
		finished: Callable[..., None],
	) -> None:
		try:
			sessions, error = self._listRemoteSessions(profile, password), None
		except Exception as caught:
			sessions, error = [], caught
		self._queueMainThread(
			finished,
			generation,
			profile,
			identity,
			sessions,
			error,
			replace_existing,
			offer_remember,
			require_recent_claim,
			preserve_dialog_identity,
		)

	def resolve_local_discovery(
		self,
		generation: int,
		identity: TerminalIdentity,
		sessions: list,
		error: Exception | None,
		*,
		require_recent_claim: bool,
		has_fallback: bool,
		claim_not_before_ns: int,
	) -> DiscoverySelection:
		"""Choose the next local-discovery action without invoking NVDA UI."""
		if not self.is_discovery_current(generation, identity):
			return DiscoverySelection(DiscoverySelectionKind.STALE)
		if error is not None:
			if has_fallback:
				return DiscoverySelection(DiscoverySelectionKind.FALLBACK)
			return DiscoverySelection(
				DiscoverySelectionKind.ERROR,
				error_type=type(error).__name__,
				error=str(error),
			)
		if not sessions:
			return DiscoverySelection(
				DiscoverySelectionKind.FALLBACK if has_fallback else DiscoverySelectionKind.EMPTY
			)
		if require_recent_claim:
			claimed = tuple(
				session
				for session in sessions
				if 0 <= session.claim_age_ms <= 15_000
				and (not claim_not_before_ns or session.claimed_monotonic_ns >= claim_not_before_ns)
			)
			if not claimed:
				return DiscoverySelection(
					DiscoverySelectionKind.FALLBACK if has_fallback else DiscoverySelectionKind.CLAIM_MISSING
				)
			return DiscoverySelection(
				DiscoverySelectionKind.SELECT,
				session=min(claimed, key=lambda item: item.claim_age_ms),
			)
		if len(sessions) > 1:
			return DiscoverySelection(DiscoverySelectionKind.CHOOSE, sessions=tuple(sessions))
		return DiscoverySelection(DiscoverySelectionKind.SELECT, session=sessions[0])

	def resolve_remote_discovery(
		self,
		generation: int,
		identity: TerminalIdentity,
		sessions: list,
		error: Exception | None,
		*,
		require_recent_claim: bool,
		preserve_dialog_identity: bool,
	) -> DiscoverySelection:
		"""Choose the next remote-discovery action without invoking NVDA UI."""
		if not self.is_discovery_current(
			generation,
			identity,
			preserve_dialog_identity=preserve_dialog_identity,
		):
			return DiscoverySelection(DiscoverySelectionKind.STALE)
		if error is not None:
			return DiscoverySelection(
				DiscoverySelectionKind.ERROR,
				error_type=type(error).__name__,
				error=str(error),
			)
		if not sessions:
			return DiscoverySelection(DiscoverySelectionKind.EMPTY)
		if require_recent_claim:
			claimed = tuple(session for session in sessions if 0 <= session.claim_age_ms <= 15_000)
			if not claimed:
				return DiscoverySelection(DiscoverySelectionKind.CLAIM_MISSING)
			return DiscoverySelection(
				DiscoverySelectionKind.SELECT,
				session=min(claimed, key=lambda item: item.claim_age_ms),
			)
		if len(sessions) > 1:
			return DiscoverySelection(DiscoverySelectionKind.CHOOSE, sessions=tuple(sessions))
		return DiscoverySelection(DiscoverySelectionKind.SELECT, session=sessions[0])

	def plan_local_connection(
		self,
		identity: TerminalIdentity,
		session: object,
		*,
		allow_reuse: bool,
		replace_existing: bool,
	) -> ConnectionPlan:
		"""Plan local reuse or replacement without starting or stopping a client."""
		manager = self._coordinator.instances
		if allow_reuse:
			instance = next(
				(
					item
					for item in manager.list()
					if item.transport_kind == "localWindowsTcp" and item.session_id == session.identifier
				),
				None,
			)
			if instance is not None:
				return ConnectionPlan(ConnectionPlanKind.REUSE, instance=instance)
		selected = manager.selected_for(identity) if replace_existing else None
		return ConnectionPlan(
			ConnectionPlanKind.START,
			replace_instance_id=selected.identifier if selected is not None else "",
		)

	def plan_remote_connection(
		self,
		identity: TerminalIdentity,
		target_id: str,
		session: object,
		*,
		allow_reuse: bool,
		replace_existing: bool,
	) -> ConnectionPlan:
		"""Plan remote reuse or replacement without starting or stopping a client."""
		manager = self._coordinator.instances
		if allow_reuse:
			matches = tuple(
				item
				for item in manager.list()
				if item.target_id == target_id and item.session_id == session.identifier
			)
			if matches:
				selected = manager.selected_for(identity)
				instance = next(
					(
						item
						for item in matches
						if selected is not None and item.identifier == selected.identifier
					),
					matches[0],
				)
				return ConnectionPlan(ConnectionPlanKind.REUSE, instance=instance)
		selected = manager.selected_for(identity) if replace_existing else None
		return ConnectionPlan(
			ConnectionPlanKind.START,
			replace_instance_id=selected.identifier if selected is not None else "",
		)

	def apply_connection_reuse(
		self,
		identity: TerminalIdentity,
		plan: ConnectionPlan,
	) -> ConnectionReuseResult | None:
		"""Apply a current reuse plan without invoking focus, UI, or client operations."""
		instance = plan.instance
		if plan.kind != ConnectionPlanKind.REUSE or instance is None:
			return None
		manager = self._coordinator.instances
		if not any(item.identifier == instance.identifier for item in manager.list()):
			return None
		try:
			displaced = tuple(
				terminal
				for terminal in manager.bound_terminals_for(instance.identifier)
				if terminal != identity
			)
			for terminal in displaced:
				manager.unbind(terminal)
			manager.bind(identity, instance.identifier)
		except ValueError:
			return None
		return ConnectionReuseResult(instance, displaced)

	def start_connection(
		self,
		identity: TerminalIdentity,
		target: ConnectionTarget,
		session_id: str,
		label: str,
		client: object,
		*,
		context_label: str = "",
		replace_instance_id: str = "",
	) -> ConnectionStartResult:
		"""Start and select a client before asynchronously retiring its replacement."""
		if not isinstance(identity, TerminalIdentity):
			return ConnectionStartResult(error_type="ValueError", error="terminal identity is required")
		manager = self._coordinator.instances
		try:
			instance = manager.add_target(
				target,
				session_id,
				label,
				client,
				context_label=context_label,
			)
		except Exception as error:
			return ConnectionStartResult(error_type=type(error).__name__, error=str(error))
		try:
			manager.bind(identity, instance.identifier)
			self._coordinator.select_instance(
				instance.identifier,
				identity,
				self._newInstanceRuntime,
			)
		except Exception as error:
			self._discard_started_instance(instance.identifier)
			return ConnectionStartResult(error_type=type(error).__name__, error=str(error))
		replacement_error_type = ""
		replacement_error = ""
		if replace_instance_id and replace_instance_id != instance.identifier:
			try:
				_detached, replaced_client = manager.detach(replace_instance_id)
				self._coordinator.discard_instance_tracking(
					replace_instance_id,
					self._newInstanceRuntime,
				)
				self._stopClientAsync(replace_instance_id, replaced_client)
			except Exception as error:
				replacement_error_type = type(error).__name__
				replacement_error = str(error)
		return ConnectionStartResult(
			instance=instance,
			replacement_error_type=replacement_error_type,
			replacement_error=replacement_error,
		)

	def _discard_started_instance(self, instance_id: str) -> None:
		"""Roll back a client that started but could not be selected."""
		try:
			_detached, client = self._coordinator.instances.detach(instance_id)
		except ValueError:
			return
		self._coordinator.discard_instance_tracking(instance_id, self._newInstanceRuntime)
		self._stopClientAsync(instance_id, client)

	def begin_inventory(self) -> int:
		self._inventoryGeneration += 1
		self._inventoryReady = False
		return self._inventoryGeneration

	def start_inventory(
		self,
		profiles: list,
		passwords: dict[str, str],
		finished: Callable[..., None],
	) -> int:
		generation = self.begin_inventory()
		self._startWorker(
			"nvim-nvda-claim-inventory",
			self.scan_targets,
			(generation, profiles, passwords, None, finished),
		)
		return generation

	def begin_resolution(self) -> int:
		self._inventoryGeneration += 1
		return self._inventoryGeneration

	def start_resolution(
		self,
		profiles: list,
		passwords: dict[str, str],
		identity: TerminalIdentity,
		baseline: dict[tuple[str, str, str], int],
		local_claim_not_before_ns: int,
		finished: Callable[..., None],
	) -> int:
		generation = self.begin_resolution()
		self._startWorker(
			"nvim-nvda-claim-resolution",
			self.scan_automatic_targets,
			(
				generation,
				profiles,
				passwords,
				identity,
				baseline,
				local_claim_not_before_ns,
				finished,
			),
		)
		return generation

	def is_current(self, generation: int, identity: TerminalIdentity | None = None) -> bool:
		gate = self._coordinator.gate
		return (
			generation == self._inventoryGeneration
			and gate.manual_enabled
			and (identity is None or gate.focused == identity)
		)

	@staticmethod
	def claim_sequence(session: object) -> int:
		value = getattr(session, "claim_sequence", 0)
		return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

	def finish_inventory(self, generation: int, results: list[tuple]) -> ClaimInventoryResult | None:
		if not self.is_current(generation):
			self._recordDiagnostic("claimInventoryIgnored")
			return None
		baselines = {}
		eligible = set()
		errors = {}
		for kind, target_id, _profile, sessions, error in results:
			target = (kind, target_id)
			if error is not None:
				errors[target] = str(error)
				continue
			eligible.add(target)
			for session in sessions:
				baselines[(kind, target_id, session.identifier)] = self.claim_sequence(session)
		self._baselines = baselines
		self._eligibleTargets = eligible
		self._inventoryErrors = errors
		self._inventoryReady = True
		return ClaimInventoryResult(
			eligible_targets=len(eligible),
			errors=len(errors),
			eligible_sessions=len(baselines),
			local_sessions=sum(
				len(sessions)
				for kind, _target_id, _profile, sessions, error in results
				if kind == "localWindowsTcp" and error is None
			),
			remote_sessions=sum(
				len(sessions)
				for kind, _target_id, _profile, sessions, error in results
				if kind == "remoteSsh" and error is None
			),
			automatic_ssh_profiles=len([target for target in eligible if target[0] == "remoteSsh"]),
			scanned_ssh_profiles=len([item for item in results if item[0] == "remoteSsh"]),
		)

	def finish_resolution(
		self,
		generation: int,
		results: list[tuple],
		identity: TerminalIdentity,
		local_claim_not_before_ns: int = 0,
	) -> ClaimResolutionResult | None:
		if not self.is_current(generation, identity):
			self._recordDiagnostic("automaticClaimResolutionIgnored")
			return None
		candidates = []
		errors = []
		new_baselines = dict(self._baselines)
		for kind, target_id, profile, sessions, error in results:
			if error is not None:
				errors.append(
					ClaimTargetError(
						target_kind=kind,
						target_id=target_id,
						error_type=type(error).__name__,
						error=str(error),
					),
				)
				continue
			current_keys = set()
			for session in sessions:
				key = (kind, target_id, session.identifier)
				current_keys.add(key)
				sequence = self.claim_sequence(session)
				previous = self._baselines.get(key, 0)
				fresh_local_claim = (
					kind == "localWindowsTcp"
					and local_claim_not_before_ns > 0
					and 0 <= session.claim_age_ms <= 15_000
					and session.claimed_monotonic_ns >= local_claim_not_before_ns
				)
				if sequence > previous or fresh_local_claim:
					candidates.append((kind, profile, session))
				new_baselines[key] = sequence
			for key in list(new_baselines):
				if key[:2] == (kind, target_id) and key not in current_keys:
					del new_baselines[key]
		self._baselines = new_baselines
		return ClaimResolutionResult(
			candidates=tuple(candidates),
			errors=tuple(errors),
			targets=len(results),
		)

	def scan_automatic_targets(
		self,
		generation: int,
		profiles: list,
		passwords: dict[str, str],
		identity: TerminalIdentity,
		baseline: dict[tuple[str, str, str], int],
		local_claim_not_before_ns: int,
		finished: Callable[..., None],
	) -> None:
		"""Resolve a local claim before probing unrelated SSH targets."""

		def changed(sessions: list) -> bool:
			return any(
				self.claim_sequence(session)
				> baseline.get(
					("localWindowsTcp", "local-windows", session.identifier),
					0,
				)
				or (
					local_claim_not_before_ns > 0
					and 0 <= session.claim_age_ms <= 15_000
					and session.claimed_monotonic_ns >= local_claim_not_before_ns
				)
				for session in sessions
			)

		local_sessions, local_error, local_attempts = self.poll_local_sessions(changed)
		local_changed = local_error is None and changed(local_sessions)
		self._recordDiagnostic(
			"automaticLocalClaimChecked",
			attempts=local_attempts,
			sessions=len(local_sessions),
			changed=local_changed,
			errorType=type(local_error).__name__ if local_error is not None else "",
		)
		local_result = (
			"localWindowsTcp",
			"local-windows",
			None,
			local_sessions,
			local_error,
		)
		if local_changed:
			self._queueMainThread(
				finished,
				generation,
				[local_result],
				identity,
				local_claim_not_before_ns,
			)
			return

		results = [local_result]
		jobs = [("remoteSsh", profile.identifier, profile) for profile in profiles]
		if jobs:
			workers = max(1, min(4, len(jobs)))
			with ThreadPoolExecutor(
				max_workers=workers,
				thread_name_prefix="nvim-nvda-claim-remote",
			) as pool:
				futures = {
					pool.submit(
						self._listRemoteSessions,
						profile,
						passwords.get(profile.identifier, ""),
					): (kind, target_id, profile)
					for kind, target_id, profile in jobs
				}
				for future in as_completed(futures):
					kind, target_id, profile = futures[future]
					try:
						results.append((kind, target_id, profile, future.result(), None))
					except Exception as error:
						results.append((kind, target_id, profile, [], error))
		self._queueMainThread(finished, generation, results, identity)

	def poll_local_sessions(self, predicate: Callable[[list], bool]) -> tuple[list, Exception | None, int]:
		"""Wait briefly for Neovim's atomic registry update on a worker thread."""
		deadline = self._monotonic() + self._localClaimWaitSeconds
		attempts = 0
		sessions = []
		while True:
			attempts += 1
			try:
				sessions = self._listLocalSessions()
			except Exception as error:
				return [], error, attempts
			if predicate(sessions) or self._monotonic() >= deadline:
				return sessions, None, attempts
			self._sleep(self._localClaimPollSeconds)

	def scan_targets(
		self,
		generation: int,
		profiles: list,
		passwords: dict[str, str],
		identity: TerminalIdentity | None,
		finished: Callable[..., None],
	) -> None:
		jobs = [("localWindowsTcp", "local-windows", None)]
		jobs.extend(("remoteSsh", profile.identifier, profile) for profile in profiles)

		def scan(kind: str, profile: object | None):
			if kind == "localWindowsTcp":
				return self._listLocalSessions()
			return self._listRemoteSessions(profile, passwords.get(profile.identifier, ""))

		results = []
		workers = max(1, min(4, len(jobs)))
		with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="nvim-nvda-scan") as pool:
			futures = {
				pool.submit(scan, kind, profile): (kind, target_id, profile)
				for kind, target_id, profile in jobs
			}
			for future in as_completed(futures):
				kind, target_id, profile = futures[future]
				try:
					results.append((kind, target_id, profile, future.result(), None))
				except Exception as error:
					results.append((kind, target_id, profile, [], error))
		self._queueMainThread(finished, generation, results, identity)

	@property
	def pending_targets(self) -> dict[TerminalIdentity, tuple[str, str]]:
		return self._pendingTargets

	@pending_targets.setter
	def pending_targets(self, value: dict[TerminalIdentity, tuple[str, str]]) -> None:
		self._pendingTargets = value

	@property
	def pending_observed(self) -> tuple[TerminalIdentity, int] | None:
		return self._pendingObserved

	@pending_observed.setter
	def pending_observed(self, value: tuple[TerminalIdentity, int] | None) -> None:
		self._pendingObserved = value

	@property
	def inventory_generation(self) -> int:
		return self._inventoryGeneration

	@inventory_generation.setter
	def inventory_generation(self, value: int) -> None:
		self._inventoryGeneration = value

	@property
	def discovery_generation(self) -> int:
		return self._discoveryGeneration

	@discovery_generation.setter
	def discovery_generation(self, value: int) -> None:
		self._discoveryGeneration = value

	@property
	def inventory_ready(self) -> bool:
		return self._inventoryReady

	@inventory_ready.setter
	def inventory_ready(self, value: bool) -> None:
		self._inventoryReady = value

	@property
	def baselines(self) -> dict[tuple[str, str, str], int]:
		return self._baselines

	@baselines.setter
	def baselines(self, value: dict[tuple[str, str, str], int]) -> None:
		self._baselines = value

	@property
	def eligible_targets(self) -> set[tuple[str, str]]:
		return self._eligibleTargets

	@eligible_targets.setter
	def eligible_targets(self, value: set[tuple[str, str]]) -> None:
		self._eligibleTargets = value

	@property
	def inventory_errors(self) -> dict[tuple[str, str], str]:
		return self._inventoryErrors

	@inventory_errors.setter
	def inventory_errors(self, value: dict[tuple[str, str], str]) -> None:
		self._inventoryErrors = value
