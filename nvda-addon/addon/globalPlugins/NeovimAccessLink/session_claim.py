"""State owner for one-shot Neovim session claims."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from .core.connection_coordinator import ConnectionCoordinator
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
		self._gestureGeneration = 0
		self._pendingObserved: tuple[TerminalIdentity, int] | None = None
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

	def invalidate_connection_state(self) -> None:
		"""Invalidate callbacks and clear discovery state during disconnect or teardown."""
		self._pendingTargets.clear()
		self._pendingObserved = None
		self._inventoryGeneration += 1
		self._inventoryReady = False
		self._baselines.clear()
		self._eligibleTargets.clear()
		self._inventoryErrors.clear()

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
