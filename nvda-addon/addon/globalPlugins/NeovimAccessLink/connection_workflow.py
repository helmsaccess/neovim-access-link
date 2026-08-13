"""Connection discovery, selection, binding, and recovery workflows."""

from __future__ import annotations

import os
import time
from typing import Any

import addonHandler
import api
import ui
from logHandler import log

from .core.connection_profiles import parse_profile, parse_profiles
from .core.connection_targets import LOCAL_WINDOWS_TCP, local_windows_target, remote_ssh_target
from .session_claim import (
	ClaimTransitionKind,
	DiscoverySelectionKind,
	RememberedBindingActivationKind,
	RememberedStateRequestKind,
	TemporaryBindingOfferKind,
)

addonHandler.initTranslation()

_TEMPORARY_BINDING_RECOVERY_DELAYS_MS = (50, 150, 350, 750)
_REMEMBERED_STATE_RETRY_DELAYS_MS = (150, 350, 750)


class ConnectionWorkflow:
	"""Orchestrate connections without owning transport or canonical session state."""

	def __init__(
		self,
		*,
		coordinator: Any,
		editor_session: Any,
		session_claim: Any,
		terminal_focus: Any,
		terminal_actions: Any,
		event_delivery: Any,
		settings: Any,
		presentation: Any,
		control_dispatcher: Any,
		control_results: Any,
		client_stopper: Any,
		scheduler: Any,
		diagnostics: Any,
		dialogs: Any,
		claim_key_name: str,
		package_dir: str,
	) -> None:
		self._connectionCoordinator = coordinator
		self._editorSessionController = editor_session
		self._sessionClaimService = session_claim
		self._terminalFocusService = terminal_focus
		self._terminalActions = terminal_actions
		self._eventDelivery = event_delivery
		self._settingsService = settings
		self._presentation = presentation
		self._controlDispatcher = control_dispatcher
		self._controlResults = control_results
		self._clientStopper = client_stopper
		self._scheduler = scheduler
		self._diagnostics = diagnostics
		self._dialogs = dialogs
		self._claimKeyName = claim_key_name
		self._packageDir = package_dir
		self._sessionPasswords = {}
		self._terminalIntegrationService = None

	@property
	def _gate(self):
		return self._connectionCoordinator.gate

	@property
	def _instanceManager(self):
		return self._connectionCoordinator.instances

	def bind_terminal_integration(self, integration) -> None:
		if integration is None or self._terminalIntegrationService is not None:
			raise RuntimeError("terminal integration may be bound exactly once")
		self._terminalIntegrationService = integration

	def _identityFields(self, identity):
		return self._terminalFocusService.identity_fields(identity)

	def _scheduleMainThreadCall(self, delay_ms, callback, *args):
		return self._scheduler.later(delay_ms, callback, *args)

	def _askpassPath(self):
		return os.path.join(self._packageDir, "resources", "ssh-askpass.cmd")

	def _dispatchControl(self, client, kind, payload, *, on_result=None):
		"""Queue one outbound control and report bounded-queue rejection immediately."""
		queued = self._controlDispatcher.submit(
			client,
			kind,
			payload,
			on_result=on_result,
		)
		if not queued:
			self._controlResults.rejected(kind, payload, on_result)
		return queued

	def _ensureTerminalLifecycleSweep(self):
		self._terminalFocusService.ensure_lifecycle_sweep()

	def toggle_accessibility(self, gesture=None):
		try:
			self._toggleNeovimMode()
		except Exception as error:
			self._gate.disable()
			self._stopClient()
			self._diagnostics.record("toggleError", errorType=type(error).__name__, error=str(error))
			log.exception("NeovimAccessLink activation failed")
			ui.message(_("Neovim accessibility failed; normal terminal output restored"))

	def toggle_braille_exploration(self, gesture=None):
		"""Toggle the persistent virtual Braille cursor for the selected editor."""
		try:
			plan = self._terminalIntegrationService.toggle_braille_exploration()
			if not plan.changed:
				# Translators: Spoken when Braille exploration cannot be used in this context.
				ui.message(_("Braille exploration mode unavailable"))
				return
			if plan.enabled:
				# Translators: Spoken when Braille display navigation stops moving the editor cursor.
				ui.message(_("Braille exploration mode"))
			else:
				# Translators: Spoken when Braille display navigation follows the editor cursor again.
				ui.message(_("Braille cursor mode"))
			self._eventDelivery.queue_braille_refresh(rebuild=True)
		except Exception as error:
			self._diagnostics.record(
				"brailleExplorationToggleError",
				errorType=type(error).__name__,
				error=str(error),
			)
			log.exception("Braille exploration toggle failed")
			# Translators: Spoken when switching the Braille navigation mode failed.
			ui.message(_("Braille exploration mode unavailable"))
			self._eventDelivery.queue_braille_refresh(rebuild=True)

	def _toggleNeovimMode(self):
		identity = self._gate.focused
		if self._gate.manual_enabled:
			self._sessionClaimService.cancel_pending_authorization()
			self._gate.disable()
			self._eventDelivery.reset_editor_planning()
			self.clear_passwords()
			self._stopClient()
			ui.message(_("Neovim accessibility off"))
			self._eventDelivery.queue_braille_refresh(rebuild=True)
			self._diagnostics.record("manualMode", enabled=False)
			log.info("NeovimAccessLink manual mode disabled")
			return
		if identity is None:
			ui.message(_("Neovim accessibility unavailable in this window"))
			return
		self._gate.manual_enabled = True
		self._eventDelivery.reset_editor_planning()
		self._diagnostics.record("manualMode", enabled=True, terminal=self._identityFields(identity))
		log.info("NeovimAccessLink manual mode requested")
		self._gate.focused = identity
		self._beginClaimInventory()
		if self._connectionCoordinator.connected:
			self._gate.authenticated = True
			self._gate.nvim_active = True
			self._gate.bound_terminal = identity
			ui.message(_("Neovim accessibility on"))
			self._eventDelivery.queue_braille_refresh(rebuild=True)
		else:
			ui.message(_("Checking local and saved Neovim connections"))

	def _promptForSessionClaim(self, profile, identity):
		self._diagnostics.record(
			"sessionClaimRequested",
			profileId=profile.identifier,
			terminal=self._identityFields(identity),
			key=self._claimKeyName,
		)
		ui.message(
			_(
				"Neovim accessibility ready for {name}. Focus the desired Neovim session and press {key}"
			).format(name=profile.name, key=self._claimKeyName)
		)

	def _automaticClaimProfiles(self):
		"""Return profiles that can be inspected without opening a password dialog."""
		try:
			profiles = parse_profiles(self._settingsService.snapshot().get("connections", []))
		except ValueError as error:
			self._diagnostics.record("claimInventoryConfigError", error=str(error))
			return []
		result = []
		seen = set()
		for profile in profiles:
			if profile.authentication == "password" and profile.identifier not in self._sessionPasswords:
				continue
			key = (
				profile.ssh_target,
				profile.port,
				profile.identity_file,
				profile.authentication,
			)
			if key in seen:
				continue
			seen.add(key)
			result.append(profile)
		return result

	def _beginClaimInventory(self):
		profiles = self._automaticClaimProfiles()
		passwords = {
			profile.identifier: self._sessionPasswords.get(profile.identifier, "") for profile in profiles
		}
		self._sessionClaimService.start_inventory(
			profiles,
			passwords,
			self._finishClaimInventory,
		)

	def _beginAutomaticClaimResolution(self, identity, local_claim_not_before_ns=0):
		profiles = [
			profile
			for profile in self._automaticClaimProfiles()
			if self._sessionClaimService.is_target_eligible("remoteSsh", profile.identifier)
		]
		passwords = {
			profile.identifier: self._sessionPasswords.get(profile.identifier, "") for profile in profiles
		}
		baseline = self._sessionClaimService.baseline_snapshot()
		self._sessionClaimService.start_resolution(
			profiles,
			passwords,
			identity,
			baseline,
			local_claim_not_before_ns,
			self._finishAutomaticClaimResolution,
		)

	def _finishClaimInventory(self, generation, results, _identity=None):
		summary = self._sessionClaimService.finish_inventory(generation, results)
		if summary is None:
			return
		configured = len(self._settingsService.snapshot().get("connections", []))
		self._diagnostics.record(
			"claimInventoryReady",
			eligibleTargets=summary.eligible_targets,
			errors=summary.errors,
			eligibleSessions=summary.eligible_sessions,
			localSessions=summary.local_sessions,
			remoteSessions=summary.remote_sessions,
			automaticSshProfiles=summary.automatic_ssh_profiles,
			scannedSshProfiles=summary.scanned_ssh_profiles,
			configuredSshProfiles=configured,
		)
		if summary.errors and configured > summary.scanned_ssh_profiles:
			ui.message(
				_(
					"Neovim connections ready. Some saved connections could not be checked, "
					"and password connections require manual selection. Focus Neovim and press {key}"
				).format(key=self._claimKeyName)
			)
		elif summary.errors:
			ui.message(
				_(
					"Neovim connections ready. Some saved connections could not be checked. "
					"Focus Neovim and press {key}, or choose a connection manually"
				).format(key=self._claimKeyName)
			)
		elif configured > summary.scanned_ssh_profiles:
			ui.message(
				_(
					"Neovim connections ready. Password connections require manual selection. "
					"Focus Neovim and press {key}"
				).format(key=self._claimKeyName)
			)
		else:
			ui.message(
				_("Neovim connections ready. Focus Neovim and press {key}").format(key=self._claimKeyName)
			)

	def _finishAutomaticClaimResolution(
		self,
		generation,
		results,
		identity,
		local_claim_not_before_ns=0,
	):
		resolution = self._sessionClaimService.finish_resolution(
			generation,
			results,
			identity,
			local_claim_not_before_ns,
		)
		if resolution is None:
			return
		for target_error in resolution.errors:
			self._diagnostics.record(
				"automaticClaimTargetError",
				targetKind=target_error.target_kind,
				targetId=target_error.target_id,
				errorType=target_error.error_type,
				error=target_error.error,
			)
		candidates = resolution.candidates
		self._diagnostics.record(
			"automaticClaimResolutionCompleted",
			candidates=len(candidates),
			targets=resolution.targets,
		)
		if not candidates:
			return
		if len(candidates) == 1:
			self._connectAutomaticClaim(identity, candidates[0])
			return
		self._showAutomaticClaimChoice(generation, identity, candidates)

	def _connectAutomaticClaim(self, identity, candidate):
		kind, profile, session = candidate
		if kind == "localWindowsTcp":
			if not self._reuseLocalSession(identity, session, offer_remember=True):
				self._startLocalSession(identity, session, replace_existing=True, offer_remember=True)
			return
		if self._reuseClaimedSession(profile, identity, session, offer_remember=True):
			return
		self._startDiscoveredSession(profile, identity, session, True, True)

	def _showAutomaticClaimChoice(self, generation, identity, candidates):
		labels = []
		for kind, profile, session in candidates:
			target = _("This computer") if kind == "localWindowsTcp" else profile.name
			labels.append(
				_("{target}: {session}").format(
					target=target,
					session=self._remoteSessionLabel(session),
				)
			)
		ui.message(_("Multiple Neovim sessions confirmed F12; opening session selection"))

		def finish(selection):
			if selection is None or not self._sessionClaimService.is_current(generation, identity):
				return
			if 0 <= selection < len(candidates):
				self._connectAutomaticClaim(identity, candidates[selection])

		self._dialogs.choose(
			title=_("Select Neovim session"),
			message=_("More than one Neovim session confirmed F12. Select the intended session."),
			choices=labels,
			on_result=finish,
		)

	def start_connection(self, gesture=None):
		identity = self._gate.focused
		if identity is None:
			return
		if not self._gate.manual_enabled:
			ui.message(_("Activate Neovim accessibility before connecting a terminal"))
			return
		profiles = self._settingsService.snapshot().get("connections", [])
		choices = [_("This computer - local Neovim")]
		choices.extend(profile.get("name", "") for profile in profiles)
		self._diagnostics.record(
			"connectionProfileDialogScheduled",
			terminal=self._identityFields(identity),
			profileCount=len(profiles),
			localTarget=True,
		)
		ui.message(_("Opening the Neovim server selection"))

		def finish(selection):
			if selection is None:
				self._diagnostics.record("connectionProfileDialogClosed", accepted=False)
				return
			if not 0 <= selection < len(choices):
				ui.message(_("The selected connection profile is unavailable"))
				return
			if selection == 0:
				self._sessionClaimService.set_pending_target(identity, LOCAL_WINDOWS_TCP, "")
				self._diagnostics.record(
					"connectionTargetDialogClosed",
					accepted=True,
					targetKind=LOCAL_WINDOWS_TCP,
					terminal=self._identityFields(identity),
				)
				ui.message(
					_("Local Neovim selected. Focus the desired Neovim session and press {key}").format(
						key=self._claimKeyName,
					)
				)
				return
			try:
				profile = parse_profile(profiles[selection - 1])
			except ValueError:
				ui.message(_("The selected connection profile is unavailable"))
				return
			self._diagnostics.record(
				"connectionProfileDialogClosed",
				accepted=True,
				profileId=profile.identifier,
			)
			if profile.authentication == "password" and self.password_for_profile(profile) is None:
				return
			self._sessionClaimService.set_pending_target(identity, "remoteSsh", profile.identifier)
			self._promptForSessionClaim(profile, identity)

		self._dialogs.choose(
			title=_("Connect terminal to Neovim"),
			message=_("Select where the Neovim session is running."),
			choices=choices,
			on_result=finish,
		)

	def claim_focused_session(
		self,
		gesture,
		forward_gesture=True,
		expected_identity=None,
		claim_generation=None,
	):
		"""Observe F12 reaching Neovim, then select only that fresh claim."""
		identity = self._gate.focused
		if expected_identity is None:
			expected_identity = identity
		if claim_generation is None:
			claim_generation = self._sessionClaimService.authorize(expected_identity)
		if claim_generation is None or not self._sessionClaimService.accept(
			expected_identity,
			claim_generation,
		):
			self._diagnostics.record("sessionClaimIgnored", reason="notAuthorizedOrFocusChanged")
			if forward_gesture and gesture is not None:
				gesture.send()
			return
		transition = self._sessionClaimService.consume_transition(expected_identity)
		identity = transition.identity
		if transition.kind == ClaimTransitionKind.PASS_THROUGH:
			if forward_gesture and gesture is not None:
				gesture.send()
			return
		if transition.kind == ClaimTransitionKind.INVENTORY_PENDING:
			ui.message(
				_(
					"Neovim connections are still being checked. Press {key} again after the ready message"
				).format(key=self._claimKeyName)
			)
			return
		local_claim_not_before_ns = time.monotonic_ns()
		if forward_gesture and gesture is not None:
			gesture.send()
		if not self._gate.manual_enabled:
			self._gate.manual_enabled = True
			self._eventDelivery.reset_editor_planning()
			self._gate.focused = identity
			self._diagnostics.record(
				"manualMode",
				enabled=True,
				terminal=self._identityFields(identity),
			)
		if transition.kind == ClaimTransitionKind.LOCAL:
			ui.message(_("Connecting the focused local Neovim session"))
			self._scheduleMainThreadCall(
				250,
				self._beginLocalSessionSelection,
				identity,
				True,
				True,
				True,
				None,
				local_claim_not_before_ns,
			)
			return
		if transition.kind == ClaimTransitionKind.AUTOMATIC:
			ui.message(_("Connecting the focused Neovim session"))
			self._scheduleMainThreadCall(
				250,
				self._beginAutomaticClaimResolution,
				identity,
				local_claim_not_before_ns,
			)
			return
		profile = self._connectionProfileById(transition.target_id)
		if profile is None:
			if transition.explicit_target:
				ui.message(_("The selected connection profile is unavailable"))
			else:
				ui.message(
					_("Configure a Neovim connection before using {key} pairing").format(
						key=self._claimKeyName,
					)
				)
			return
		ui.message(_("Connecting the focused Neovim session"))
		self._scheduleMainThreadCall(
			250,
			self._beginSessionSelection,
			profile,
			identity,
			True,
			True,
			True,
		)

	def _beginLocalSessionSelection(
		self,
		identity,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		fallback_profile=None,
		claim_not_before_ns=0,
	):
		if not require_recent_claim:
			ui.message(_("Looking for local Neovim sessions"))
		self._sessionClaimService.start_local_discovery(
			identity,
			replace_existing,
			offer_remember,
			require_recent_claim,
			fallback_profile,
			claim_not_before_ns,
			self._finishLocalSessionDiscovery,
		)

	def _finishLocalSessionDiscovery(
		self,
		generation,
		identity,
		sessions,
		error,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		fallback_profile=None,
		claim_not_before_ns=0,
	):
		selection = self._sessionClaimService.resolve_local_discovery(
			generation,
			identity,
			sessions,
			error,
			require_recent_claim=require_recent_claim,
			has_fallback=fallback_profile is not None,
			claim_not_before_ns=claim_not_before_ns,
		)
		if selection.kind == DiscoverySelectionKind.STALE:
			self._diagnostics.record("localSessionDiscoveryIgnored")
			return
		if selection.kind == DiscoverySelectionKind.ERROR:
			self._diagnostics.record(
				"localSessionDiscoveryError",
				errorType=selection.error_type,
				error=selection.error,
			)
			ui.message(_("Could not list local Neovim sessions"))
			return
		if selection.kind == DiscoverySelectionKind.FALLBACK:
			self._beginSessionSelection(
				fallback_profile,
				identity,
				replace_existing,
				offer_remember,
				require_recent_claim,
			)
			return
		if selection.kind == DiscoverySelectionKind.EMPTY:
			ui.message(
				_(
					"No local Neovim accessibility session was found. Install the local components "
					"and restart Neovim"
				)
			)
			return
		if selection.kind == DiscoverySelectionKind.CLAIM_MISSING:
			ui.message(_("The focused local Neovim did not confirm F12 pairing; try again"))
			return
		if selection.kind == DiscoverySelectionKind.CHOOSE:
			self._showLocalSessionChoice(
				generation,
				identity,
				selection.sessions,
				replace_existing,
				offer_remember,
			)
			return
		session = selection.session
		if require_recent_claim:
			if self._reuseLocalSession(identity, session, offer_remember):
				return
		self._startLocalSession(
			identity,
			session,
			replace_existing=replace_existing,
			offer_remember=offer_remember,
		)

	def _reuseLocalSession(self, identity, session, offer_remember=False):
		plan = self._sessionClaimService.plan_local_connection(
			identity,
			session,
			allow_reuse=True,
			replace_existing=False,
		)
		instance = self._applyConnectionReuse(identity, plan, offer_remember)
		if instance is None:
			return False
		self.activate_remembered_binding(identity, instance.identifier)
		ui.message(_("Neovim connection selected: {name}").format(name=instance.label))
		return True

	def _applyConnectionReuse(self, identity, plan, offer_remember=False):
		result = self._sessionClaimService.apply_connection_reuse(identity, plan)
		if result is None:
			return None
		for terminal in result.displaced_identities:
			self._terminalFocusService.forget_identity(terminal)
		self._ensureTerminalLifecycleSweep()
		if offer_remember and not self._sessionClaimService.is_temporary_binding_remembered(identity):
			self._sessionClaimService.request_temporary_binding_offer(result.instance.identifier)
		return result.instance

	def _startLocalSession(
		self,
		identity,
		session,
		replace_existing=False,
		offer_remember=False,
	):
		plan = self._sessionClaimService.plan_local_connection(
			identity,
			session,
			allow_reuse=False,
			replace_existing=replace_existing,
		)
		self._startLocalManagedInstance(
			session,
			identity,
			self._remoteSessionLabel(session),
			plan.replace_instance_id,
			offer_remember,
		)

	def _showLocalSessionChoice(
		self,
		generation,
		identity,
		sessions,
		replace_existing,
		offer_remember,
	):
		labels = [self._remoteSessionLabel(session) for session in sessions]
		ui.message(_("Multiple local Neovim sessions found; opening session selection"))

		def finish(selection):
			if not self._sessionClaimService.is_discovery_current(generation, identity):
				return
			if selection is None:
				return
			if not 0 <= selection < len(sessions):
				ui.message(_("The selected local Neovim session is no longer available"))
				return
			self._startLocalSession(
				identity,
				sessions[selection],
				replace_existing,
				offer_remember,
			)

		self._dialogs.choose(
			title=_("Local Neovim session"),
			message=_("Select the local Neovim session for the focused terminal."),
			choices=labels,
			on_result=finish,
		)

	def _startLocalManagedInstance(
		self,
		session,
		identity,
		session_label="",
		replace_instance_id="",
		offer_remember=False,
	):
		if identity is None:
			ui.message(_("Starting a connection instance requires a focused terminal"))
			return
		target = local_windows_target(_("This computer - local Neovim"))
		label = _("Local Neovim, {session}").format(
			session=session_label or _("Neovim session"),
		)
		result = self._sessionClaimService.start_local_connection(
			identity,
			session,
			target,
			label,
			context_label=_("local"),
			replace_instance_id=replace_instance_id,
		)
		self._completeManagedConnectionStart(
			result,
			offer_remember=offer_remember,
			diagnostic_fields={"targetKind": LOCAL_WINDOWS_TCP},
			failure_message=_("Could not start the local Neovim connection"),
		)

	def _completeManagedConnectionStart(
		self,
		result,
		*,
		offer_remember=False,
		diagnostic_fields=None,
		failure_message="",
	):
		if result.instance is None:
			self._reportConnectionStartError(
				RuntimeError(result.error),
				diagnostic_fields,
				failure_message,
				error_type=result.error_type,
			)
			return None
		self._ensureTerminalLifecycleSweep()
		if offer_remember:
			self._sessionClaimService.request_temporary_binding_offer(result.instance.identifier)
		if result.replacement_error_type:
			self._diagnostics.record(
				"replacedConnectionStopError",
				instanceId=result.replaced_instance_id,
				errorType=result.replacement_error_type,
				error=result.replacement_error,
			)
		ui.message(_("Neovim connection started: {name}").format(name=result.instance.label))
		return result.instance

	def _reportConnectionStartError(
		self,
		error,
		diagnostic_fields,
		failure_message,
		*,
		error_type="",
	):
		self._diagnostics.record(
			"connectionInstanceStartError",
			**(diagnostic_fields or {}),
			errorType=error_type or type(error).__name__,
			error=str(error),
		)
		ui.message(failure_message)

	def disconnect_connection(self, gesture=None):
		identity = self._gate.focused
		if identity is None:
			return
		result = self._sessionClaimService.disconnect_connection(identity)
		if result.instance is None:
			if result.error_type:
				self._diagnostics.record(
					"connectionInstanceDisconnectError",
					errorType=result.error_type,
					error=result.error,
				)
			ui.message(_("No Neovim connection instance is selected for this terminal"))
			return
		self._terminalFocusService.forget_identity(identity)
		if result.error_type:
			self._diagnostics.record(
				"connectionInstanceDisconnectError",
				instanceId=result.instance.identifier,
				errorType=result.error_type,
				error=result.error,
			)
		ui.message(_("Neovim connection disconnected: {name}").format(name=result.instance.label))

	def forget_temporary_binding(self, gesture=None):
		identity = self._gate.focused
		if identity is None:
			return
		if not self._sessionClaimService.forget_temporary_binding(identity):
			ui.message(_("No temporary Neovim connection is remembered for this terminal"))
			return
		self._diagnostics.record("temporaryTerminalBindingForgotten", terminal=self._identityFields(identity))
		ui.message(_("Temporary Neovim connection forgotten"))

	def _remoteSessionLabel(self, session):
		if session.name and session.cwd and session.cwd != session.name:
			return _("{name}, working directory {cwd}").format(name=session.name, cwd=session.cwd)
		return session.name or session.cwd or _("Neovim session")

	def _remoteSessionLabels(self, profile, sessions, include_connection_status=True):
		bases = [self._remoteSessionLabel(session) for session in sessions]
		totals = {base: bases.count(base) for base in set(bases)}
		positions = {}
		connected = {
			instance.session_id
			for instance in self._instanceManager.list()
			if instance.target_id == profile.identifier
		}
		labels = []
		for session, base in zip(sessions, bases):
			label = base
			if totals[base] > 1:
				positions[base] = positions.get(base, 0) + 1
				if session.started_unix:
					started = time.strftime("%H:%M", time.localtime(session.started_unix))
					label = _("{label}, started {started}").format(label=label, started=started)
				label = _("{label}, session {position} of {total}").format(
					label=label,
					position=positions[base],
					total=totals[base],
				)
			if include_connection_status and session.identifier in connected:
				label = _("{label}, already connected").format(label=label)
			labels.append(label)
		return labels

	def _beginSessionSelection(
		self,
		profile,
		identity,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		preserve_dialog_identity=False,
	):
		if not preserve_dialog_identity and self._gate.focused != identity:
			return
		password = self.password_for_profile(profile)
		if profile.authentication == "password" and password is None:
			return
		self._diagnostics.record(
			"remoteSessionDiscoveryStarted",
			profileId=profile.identifier,
			terminal=self._identityFields(identity),
			preserveDialogIdentity=preserve_dialog_identity,
		)
		if not require_recent_claim:
			ui.message(_("Looking for Neovim sessions on {name}").format(name=profile.name))
		self._sessionClaimService.start_remote_discovery(
			profile,
			identity,
			password or "",
			replace_existing,
			offer_remember,
			require_recent_claim,
			preserve_dialog_identity,
			self._finishSessionDiscovery,
		)

	def _finishSessionDiscovery(
		self,
		generation,
		profile,
		identity,
		sessions,
		error,
		replace_existing=False,
		offer_remember=False,
		require_recent_claim=False,
		preserve_dialog_identity=False,
	):
		selection = self._sessionClaimService.resolve_remote_discovery(
			generation,
			identity,
			sessions,
			error,
			require_recent_claim=require_recent_claim,
			preserve_dialog_identity=preserve_dialog_identity,
		)
		if selection.kind == DiscoverySelectionKind.STALE:
			self._diagnostics.record("sessionDiscoveryIgnored", profileId=profile.identifier)
			return
		if selection.kind == DiscoverySelectionKind.ERROR:
			self._diagnostics.record(
				"sessionDiscoveryError",
				profileId=profile.identifier,
				errorType=selection.error_type,
				error=selection.error,
			)
			ui.message(_("Could not list Neovim sessions on {name}").format(name=profile.name))
			return
		if selection.kind == DiscoverySelectionKind.EMPTY:
			ui.message(_("No active Neovim session was found on {name}").format(name=profile.name))
			return
		if selection.kind == DiscoverySelectionKind.CLAIM_MISSING:
			self._diagnostics.record(
				"freshSessionClaimMissing",
				profileId=profile.identifier,
				sessionCount=len(sessions),
			)
			ui.message(_("The focused Neovim did not confirm F12 pairing; try again"))
			return
		if selection.kind == DiscoverySelectionKind.CHOOSE:
			self._showRemoteSessionChoice(
				generation,
				profile,
				identity,
				selection.sessions,
				replace_existing,
				offer_remember,
				preserve_dialog_identity,
			)
			return
		session = selection.session
		if require_recent_claim:
			self._diagnostics.record(
				"freshSessionClaimSelected",
				profileId=profile.identifier,
				sessionId=session.identifier,
				claimAgeMs=session.claim_age_ms,
			)
			if self._reuseClaimedSession(
				profile,
				identity,
				session,
				offer_remember=offer_remember,
			):
				return
			self._startDiscoveredSession(
				profile,
				identity,
				session,
				replace_existing,
				offer_remember,
			)
			return
		self._startDiscoveredSession(
			profile,
			identity,
			session,
			replace_existing,
			offer_remember,
		)

	def _reuseClaimedSession(self, profile, identity, session, offer_remember=False):
		"""Move or refresh an existing transport instead of duplicating it."""
		plan = self._sessionClaimService.plan_remote_connection(
			identity,
			profile.identifier,
			session,
			allow_reuse=True,
			replace_existing=False,
		)
		instance = self._applyConnectionReuse(identity, plan, offer_remember)
		if instance is None:
			return False
		client = self._instanceManager.client_for(instance.identifier)
		already_active = (
			self._gate.bound_terminal == identity
			and self._connectionCoordinator.active_client is client
			and self._gate.authenticated
			and self._gate.nvim_active
			and self._connectionCoordinator.active_instance_id == instance.identifier
		)
		self.activate_remembered_binding(identity, instance.identifier)
		if already_active and self._sessionClaimService.has_temporary_binding_offer(instance.identifier):
			self._dispatchControl(client, "requestFullState", {})
		self._diagnostics.record(
			"claimedSessionTransportReused",
			instanceId=instance.identifier,
			profileId=profile.identifier,
			sessionId=session.identifier,
			terminal=self._identityFields(identity),
		)
		ui.message(_("Neovim connection selected: {name}").format(name=instance.label))
		return True

	def _startDiscoveredSession(
		self,
		profile,
		identity,
		session,
		replace_existing=False,
		offer_remember=False,
		session_label="",
	):
		plan = self._sessionClaimService.plan_remote_connection(
			identity,
			profile.identifier,
			session,
			allow_reuse=False,
			replace_existing=replace_existing,
		)
		self._startManagedInstance(
			profile.identifier,
			session.identifier,
			identity=identity,
			session_label=session_label or self._remoteSessionLabel(session),
			replace_instance_id=plan.replace_instance_id,
			offer_remember=offer_remember,
		)

	def _showRemoteSessionChoice(
		self,
		generation,
		profile,
		identity,
		sessions,
		replace_existing,
		offer_remember,
		preserve_dialog_identity=False,
	):
		choices = self._remoteSessionLabels(profile, sessions)
		self._diagnostics.record(
			"remoteSessionDialogScheduled",
			profileId=profile.identifier,
			sessionCount=len(sessions),
			terminal=self._identityFields(identity),
		)
		ui.message(
			_("Multiple Neovim sessions found on {name}; opening session selection").format(
				name=profile.name,
			)
		)

		def finish(selection):
			if not self._sessionClaimService.is_discovery_current(
				generation,
				identity,
				preserve_dialog_identity=preserve_dialog_identity,
			):
				self._diagnostics.record(
					"remoteSessionDialogIgnored",
					profileId=profile.identifier,
					reason="stale",
				)
				return
			if selection is None:
				self._diagnostics.record(
					"remoteSessionDialogClosed",
					profileId=profile.identifier,
					accepted=False,
				)
				return
			if not 0 <= selection < len(sessions):
				ui.message(_("The selected Neovim session is no longer available"))
				return
			session = sessions[selection]
			self._diagnostics.record(
				"remoteSessionDialogClosed",
				profileId=profile.identifier,
				accepted=True,
			)
			labels = self._remoteSessionLabels(profile, sessions, include_connection_status=False)
			self._startDiscoveredSession(
				profile,
				identity,
				session,
				replace_existing,
				offer_remember,
				labels[selection],
			)

		self._dialogs.choose(
			title=_("Neovim session"),
			message=_("Select the Neovim session for the focused terminal."),
			choices=choices,
			on_result=finish,
		)

	def _startManagedInstance(
		self,
		profile_id,
		session_id,
		identity=None,
		session_label="",
		replace_instance_id="",
		offer_remember=False,
	):
		try:
			profile = next(
				item
				for item in parse_profiles(self._settingsService.snapshot().get("connections", []))
				if item.identifier == profile_id
			)
		except (StopIteration, ValueError) as error:
			self._diagnostics.record("connectionInstanceStartError", error=str(error), profileId=profile_id)
			ui.message(_("The selected connection profile is unavailable"))
			return
		identity = identity or self._gate.focused
		if identity is None:
			ui.message(_("Starting a connection instance requires a focused terminal"))
			return
		password = self.password_for_profile(profile)
		if profile.authentication == "password" and password is None:
			return
		result = self._sessionClaimService.start_remote_connection(
			identity,
			profile,
			session_id,
			remote_ssh_target(profile.identifier, profile.name),
			f"{profile.name}, {session_label}" if session_label else profile.name,
			password=password or "",
			askpass_path=self._askpassPath(),
			context_label=profile.name,
			replace_instance_id=replace_instance_id,
		)
		self._completeManagedConnectionStart(
			result,
			offer_remember=offer_remember,
			diagnostic_fields={"profileId": profile.identifier},
			failure_message=_("Could not start the Neovim connection"),
		)

	def offer_temporary_binding(self, identity, instance_id):
		offer = self._sessionClaimService.arm_temporary_binding_reactivation(identity, instance_id)
		if offer.kind == TemporaryBindingOfferKind.FOCUS_CHANGED:
			self._diagnostics.record(
				"temporaryTerminalBindingOfferIgnored",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if offer.kind == TemporaryBindingOfferKind.UNAVAILABLE:
			self._diagnostics.record(
				"temporaryTerminalBindingUnavailable",
				terminal=self._identityFields(identity),
			)
			return
		if offer.kind != TemporaryBindingOfferKind.OFFER or offer.instance is None:
			return
		app_module = self._terminalFocusService.focused_app_module
		adapter_token = self._terminalFocusService.focused_adapter_token

		def finish(accepted):
			if not accepted:
				self._diagnostics.record(
					"temporaryTerminalBindingDeclined",
					instanceId=instance_id,
					terminal=self._identityFields(identity),
				)
			else:
				remembered = self._sessionClaimService.remember_temporary_binding(identity, instance_id)
				if remembered.kind != TemporaryBindingOfferKind.OFFER or remembered.instance is None:
					self._diagnostics.record(
						"temporaryTerminalBindingOfferIgnored",
						instanceId=instance_id,
						reason=remembered.kind.value,
					)
				else:
					self._diagnostics.record(
						"temporaryTerminalBindingRemembered",
						instanceId=instance_id,
						transportKind=remembered.instance.transport_kind,
						terminal=self._identityFields(identity),
					)
					ui.message(_("Connection remembered for this terminal tab until NVDA exits"))
			self._scheduleTemporaryBindingRecovery(
				identity,
				instance_id,
				app_module,
				adapter_token,
			)

		self._dialogs.confirm(
			title=_("Remember temporary terminal connection"),
			message=_(
				"Remember this connection for this Windows Terminal tab until NVDA or "
				"Windows Terminal closes?\n\n{connection}"
			).format(connection=offer.instance.label),
			on_result=finish,
		)

	def _scheduleTemporaryBindingRecovery(
		self,
		identity,
		instance_id,
		app_module,
		adapter_token,
	):
		if app_module is None or adapter_token is None:
			self._sessionClaimService.consume_temporary_binding_reactivation(None, None)
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryStopped",
				instanceId=instance_id,
				reason="adapterUnavailable",
			)
			return
		self._diagnostics.record(
			"temporaryTerminalBindingFocusRecoveryScheduled",
			attempts=len(_TEMPORARY_BINDING_RECOVERY_DELAYS_MS),
			instanceId=instance_id,
		)
		self._scheduleMainThreadCall(
			_TEMPORARY_BINDING_RECOVERY_DELAYS_MS[0],
			self._recoverTemporaryBindingFocus,
			identity,
			instance_id,
			app_module,
			adapter_token,
			0,
		)

	def _recoverTemporaryBindingFocus(
		self,
		identity,
		instance_id,
		app_module,
		adapter_token,
		attempt,
	):
		try:
			focus_obj = api.getFocusObject()
		except Exception as error:
			focus_obj = None
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryFocusError",
				errorType=type(error).__name__,
				instanceId=instance_id,
			)
		focus_identity = self._terminalFocusService.identity(focus_obj) if focus_obj is not None else None
		focus_source = "cached"
		try:
			system_focus_obj = api.getDesktopObject().objectWithFocus()
		except Exception as error:
			system_focus_obj = None
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoverySystemFocusError",
				errorType=type(error).__name__,
				instanceId=instance_id,
			)
		if system_focus_obj is not None:
			focus_obj = system_focus_obj
			focus_identity = self._terminalFocusService.identity(system_focus_obj)
			focus_source = "system"
		if focus_identity is not None and focus_identity != identity:
			selected = self._instanceManager.selected_for(focus_identity)
			self._sessionClaimService.consume_temporary_binding_reactivation(
				focus_identity,
				selected.identifier if selected is not None else None,
			)
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryStopped",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if focus_identity == identity and getattr(focus_obj, "appModule", None) is app_module:
			selected = self._instanceManager.selected_for(identity)
			if selected is None or selected.identifier != instance_id:
				self._sessionClaimService.consume_temporary_binding_reactivation(None, None)
				self._diagnostics.record(
					"temporaryTerminalBindingFocusRecoveryStopped",
					instanceId=instance_id,
					reason="selectionChanged",
				)
				return
			focus_already_current = (
				self._gate.focused == identity
				and self._terminalFocusService.focused_app_module is app_module
				and self._terminalFocusService.focused_adapter_token is adapter_token
			)
			foreground_confirmed = (
				self._gate.bound_terminal == identity
				and self._gate.authenticated
				and self._gate.nvim_active
				and self._connectionCoordinator.active_instance_id == instance_id
			)
			if focus_already_current and foreground_confirmed:
				self._sessionClaimService.consume_temporary_binding_reactivation(
					identity,
					instance_id,
				)
				self._diagnostics.record(
					"temporaryTerminalBindingFocusRecoveryStopped",
					instanceId=instance_id,
					reason="alreadyCurrent",
				)
				return
			# A cached object may lag behind operating-system focus after a modal
			# dialog. Only an exact live object may trigger a new handshake.
			if focus_source == "system":
				allowed = self._sessionClaimService.is_temporary_binding_remembered(
					identity
				) or self._sessionClaimService.has_temporary_binding_reactivation(
					identity,
					instance_id,
				)
				if focus_already_current and allowed:
					# gainFocus can restore the adapter fields before its delayed
					# foreground handshake has run. Retry that exact, idempotent
					# request now instead of mistaking adapter focus for a confirmed
					# Neovim binding. A later scheduled copy observes PENDING.
					self.request_remembered_binding_state(identity, instance_id)
					self._sessionClaimService.consume_temporary_binding_reactivation(
						identity,
						instance_id,
					)
					self._diagnostics.record(
						"temporaryTerminalBindingFocusHandshakeRetried",
						instanceId=instance_id,
						terminal=self._identityFields(identity),
					)
					return
				try:
					recovered = allowed and self._terminalFocusService.recover_after_modal(
						focus_obj,
						identity,
						instance_id,
						app_module,
						adapter_token,
					)
				except Exception as error:
					self._gate.disconnect()
					self._sessionClaimService.consume_temporary_binding_reactivation(None, None)
					self._diagnostics.record(
						"temporaryTerminalBindingFocusRecoveryStopped",
						errorType=type(error).__name__,
						instanceId=instance_id,
						reason="error",
					)
					return
				if not recovered:
					self._diagnostics.record(
						"temporaryTerminalBindingFocusRecoveryStopped",
						instanceId=instance_id,
						reason="authorizationChanged",
					)
					return
				self._diagnostics.record(
					"temporaryTerminalBindingFocusRecovered",
					attempt=attempt + 1,
					focusSource=focus_source,
					instanceId=instance_id,
					terminal=self._identityFields(identity),
				)
				return
		if attempt + 1 < len(_TEMPORARY_BINDING_RECOVERY_DELAYS_MS):
			next_attempt = attempt + 1
			self._scheduleMainThreadCall(
				_TEMPORARY_BINDING_RECOVERY_DELAYS_MS[next_attempt],
				self._recoverTemporaryBindingFocus,
				identity,
				instance_id,
				app_module,
				adapter_token,
				next_attempt,
			)
			return
		self._sessionClaimService.consume_temporary_binding_reactivation(
			identity if focus_identity == identity else None,
			instance_id if focus_identity == identity else None,
		)
		if focus_identity != identity:
			self._diagnostics.record(
				"temporaryTerminalBindingFocusRecoveryStopped",
				instanceId=instance_id,
				reason="timeout",
			)

	def activate_remembered_binding(self, identity, instance_id, focus_regained=False):
		activation = self._sessionClaimService.activate_remembered_binding(
			identity,
			instance_id,
			focus_regained=focus_regained,
		)
		if activation.kind != RememberedBindingActivationKind.ACTIVATE:
			return
		# Focus events for Windows Terminal tabs can be followed by transient
		# child-focus events. Let focus settle before accepting a new fullState.
		self._scheduleMainThreadCall(
			100,
			self.request_remembered_binding_state,
			identity,
			instance_id,
		)
		self._diagnostics.record(
			"temporaryTerminalBindingActivated",
			instanceId=instance_id,
			terminal=self._identityFields(identity),
			suppressionImmediate=False,
		)

	def request_remembered_binding_state(self, identity, instance_id, attempt=0):
		# A recovery callback and the normal delayed focus callback can overlap
		# around a modal dialog. The first correlated reply may confirm the exact
		# binding before the second callback runs. Do not turn that stale callback
		# into another focusContext request and a duplicate mode cue.
		if self._connectionCoordinator.is_foreground_instance_confirmed(instance_id, identity):
			self._diagnostics.record(
				"temporaryTerminalBindingStateSkipped",
				instanceId=instance_id,
				reason="alreadyConfirmed",
			)
			return
		request = self._sessionClaimService.plan_remembered_state_request(identity, instance_id)
		if request.kind == RememberedStateRequestKind.SKIP:
			self._diagnostics.record(
				"temporaryTerminalBindingStateSkipped",
				instanceId=instance_id,
				reason="focusChanged",
			)
			return
		if request.kind == RememberedStateRequestKind.PENDING:
			self._diagnostics.record(
				"temporaryTerminalBindingStatePending",
				instanceId=instance_id,
			)
			return
		if request.kind == RememberedStateRequestKind.STALE or request.client is None:
			return
		if request.kind == RememberedStateRequestKind.FOCUS_CONTEXT:
			self._dispatchControl(
				request.client,
				"requestFocusContext",
				{"requestId": request.request_id},
				on_result=lambda accepted, error_type: self._finishRememberedStateDispatch(
					identity,
					instance_id,
					attempt,
					request.kind,
					request.request_id,
					accepted,
					error_type,
				),
			)
			return
		self._dispatchControl(
			request.client,
			"requestFullState",
			{},
			on_result=lambda accepted, error_type: self._finishRememberedStateDispatch(
				identity,
				instance_id,
				attempt,
				request.kind,
				None,
				accepted,
				error_type,
			),
		)

	def _finishRememberedStateDispatch(
		self,
		identity,
		instance_id,
		attempt,
		request_kind,
		request_id,
		accepted,
		error_type,
	):
		focus_context = request_kind == RememberedStateRequestKind.FOCUS_CONTEXT
		if (
			focus_context
			and not accepted
			and isinstance(request_id, int)
			and self._connectionCoordinator.matches_focus_context(instance_id, request_id, identity)
		):
			self._connectionCoordinator.discard_focus_context(instance_id)
		self._diagnostics.record(
			(
				"temporaryTerminalFocusContextRequested"
				if focus_context
				else "temporaryTerminalBindingStateRequested"
			),
			instanceId=instance_id,
			requestId=request_id,
			sent=accepted,
			errorType=error_type,
		)
		if not accepted:
			self._retryRememberedBindingState(identity, instance_id, attempt)

	def _retryRememberedBindingState(self, identity, instance_id, attempt):
		if attempt >= len(_REMEMBERED_STATE_RETRY_DELAYS_MS):
			self._diagnostics.record(
				"temporaryTerminalBindingStateRetryStopped",
				attempts=attempt,
				instanceId=instance_id,
			)
			return
		self._scheduleMainThreadCall(
			_REMEMBERED_STATE_RETRY_DELAYS_MS[attempt],
			self.request_remembered_binding_state,
			identity,
			instance_id,
			attempt + 1,
		)

	def settings_connections_changed(self):
		"""Refresh claim discovery only while manual support is active."""
		if not self._gate.manual_enabled:
			return False
		self._beginClaimInventory()
		return True

	def _connectionProfileById(self, identifier):
		return self._settingsService.connection_profile_by_id(identifier)

	def password_for_profile(self, profile):
		if profile is None or profile.authentication != "password":
			return ""
		if profile.identifier in self._sessionPasswords:
			return self._sessionPasswords[profile.identifier]
		password = self._promptPassword(profile.name)
		if password is None:
			self._diagnostics.record("sshPasswordCancelled", profileId=profile.identifier)
			return None
		self._sessionPasswords[profile.identifier] = password
		return password

	def _promptPassword(self, profile_name):
		return self._dialogs.password(profile_name)

	def clear_passwords(self):
		self._sessionPasswords.clear()

	def _stopClient(self):
		self._sessionClaimService.invalidate_connection_state()
		self._connectionCoordinator.discard_focus_context()
		self._terminalActions.discard_requests()
		if self._instanceManager.list():
			queued = 0
			for instance in tuple(self._instanceManager.list()):
				_detached, client = self._instanceManager.detach(instance.identifier)
				self._controlDispatcher.discard_client(client)
				if self._clientStopper.submit(instance.identifier, client):
					queued += 1
				else:
					self._diagnostics.record(
						"managedClientStopRejected",
						instanceId=instance.identifier,
					)
			self._connectionCoordinator.clear_runtime_tracking()
			self._diagnostics.record("clientInstancesStopped", queued=queued)
			return
		self._connectionCoordinator.clear_runtime_tracking()
