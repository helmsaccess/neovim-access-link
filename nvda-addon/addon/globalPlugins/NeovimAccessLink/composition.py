"""Transactional composition root for the process-wide NVDA runtime."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from typing import Any

import buildVersion
import config
import core as nvdaCore
import globalVars
import queueHandler
import speech
from logHandler import log

from . import runtime_config as runtimeConfig
from .addon_runtime import AddonRuntime
from .client_stopper import ClientStopper
from .connection_dialogs import NvdaConnectionDialogs
from .connection_workflow import ConnectionWorkflow
from .control_dispatcher import ControlDispatcher
from .control_results import ControlResultDelivery
from .core.connection_coordinator import ConnectionCoordinator
from .core.diagnostics import DiagnosticBuffer
from .core.gate import SessionGate
from .core.local_client import LocalTcpClient
from .core.speech import SpeechPlanner
from .core.ssh_sessions import SshSessionLister
from .core.stdio_client import SshStdioClient
from .editor_session import EditorSessionController
from .event_delivery import EventDelivery
from .managed_clients import ManagedClientFactory
from .nvda_presentation import NvdaPresentation
from .nvda_ui import NvdaUiManager
from .runtime_scheduler import RuntimeScheduler
from .service_registry import serviceRegistrar
from .session_claim import SessionClaimService
from .settings_service import SettingsService
from .terminal_actions import TerminalActions
from .terminal_focus import TerminalFocusService
from .terminal_integration import TerminalCommand, TerminalIntegrationService
from .temporary_binding import TemporaryBindingWorkflow


class PluginRuntime:
	"""Own the typed runtime graph and its idempotent lifetime."""

	def __init__(
		self,
		lifecycle: AddonRuntime,
		*,
		coordinator,
		editor_session,
		settings,
		presentation,
		control_dispatcher,
		client_stopper,
		session_claim,
		terminal_focus,
		ui_manager,
		terminal_actions,
		event_delivery,
		connection_workflow,
		temporary_bindings,
		integration,
		scheduler,
		diagnostics,
	) -> None:
		self._lifecycle = lifecycle
		self.coordinator = coordinator
		self.editor_session = editor_session
		self.settings = settings
		self.presentation = presentation
		self.control_dispatcher = control_dispatcher
		self.client_stopper = client_stopper
		self.session_claim = session_claim
		self.terminal_focus = terminal_focus
		self.ui_manager = ui_manager
		self.terminal_actions = terminal_actions
		self.event_delivery = event_delivery
		self.connection_workflow = connection_workflow
		self.temporary_bindings = temporary_bindings
		self.integration = integration
		self.scheduler = scheduler
		self.diagnostics = diagnostics

	@property
	def closed(self) -> bool:
		return self._lifecycle.closed

	def close(self) -> bool:
		return self._lifecycle.close()


def create_runtime() -> PluginRuntime:
	"""Build, activate, or completely roll back one add-on runtime."""
	cleanup: list[tuple[str, Callable[[], Any]]] = []

	def own(name: str, close: Callable[[], Any]) -> None:
		cleanup.append((name, close))

	def rollback() -> None:
		for name, close in reversed(cleanup):
			try:
				close()
			except Exception:
				log.exception("NeovimAccessLink construction rollback failed: %s", name)

	workflow: ConnectionWorkflow | None = None
	temporary_bindings: TemporaryBindingWorkflow | None = None
	event_delivery: EventDelivery | None = None
	try:
		diagnostics = DiagnosticBuffer()
		scheduler = RuntimeScheduler(
			queue_function=lambda *args, **kwargs: queueHandler.queueFunction(*args, **kwargs),
			event_queue=queueHandler.eventQueue,
			call_later=lambda *args, **kwargs: nvdaCore.callLater(*args, **kwargs),
			record_diagnostic=diagnostics.record,
		)
		own("scheduler", scheduler.close)
		runtimeConfig.register_nvda_config_spec()
		settings = SettingsService(
			config.conf,
			section_name=runtimeConfig.NVDA_CONFIG_SECTION,
			feedback_defaults=runtimeConfig.FEEDBACK_DEFAULTS,
			navigation_details_defaults=runtimeConfig.NAVIGATION_DETAILS_DEFAULTS,
			focus_announcement_values=runtimeConfig.FOCUS_ANNOUNCEMENT_VALUES,
			focus_announcement_default=runtimeConfig.FOCUS_ANNOUNCEMENT_DEFAULT,
			record_diagnostic=diagnostics.record,
			on_connections_changed=lambda: (
				workflow.settings_connections_changed() if workflow is not None else False
			),
		)
		presentation = NvdaPresentation(
			os.path.join(globalVars.appDir, "waves"),
			os.path.join(runtimeConfig.PACKAGE_DIR, "resources", "sounds"),
			settings.snapshot,
			runtimeConfig.FEEDBACK_DEFAULTS,
			runtimeConfig.FEEDBACK_FOR_SOUND,
			diagnostics.record,
			numbered_choice_start=settings.braille_suggestion_start,
			developer_context_start=settings.braille_developer_start,
		)
		own("presentation", presentation.close)
		coordinator = ConnectionCoordinator(
			gate=SessionGate(runtimeConfig.FRONTEND_POLICY.enabled_kinds),
			planner=SpeechPlanner(translate=_),
		)
		editor_session = EditorSessionController(
			coordinator,
			new_planner=lambda: SpeechPlanner(translate=_),
			max_pending_clipboard_requests=runtimeConfig.MAX_PENDING_CLIPBOARD_REQUESTS,
			max_pending_terminal_control_requests=(runtimeConfig.MAX_PENDING_TERMINAL_CONTROL_REQUESTS),
			translate=_,
		)
		control_results = ControlResultDelivery(
			scheduler=scheduler,
			editor_session=editor_session,
			diagnostics=diagnostics,
		)
		control_dispatcher = ControlDispatcher(
			on_result=control_results,
			max_pending=runtimeConfig.MAX_PENDING_OUTBOUND_CONTROLS,
		)
		own("controlDispatcher", control_dispatcher.close)

		def dispatch_control(client, kind, payload, *, on_result=None):
			queued = control_dispatcher.submit(client, kind, payload, on_result=on_result)
			if not queued:
				control_results.rejected(kind, payload, on_result)
			return queued

		def record_stop_error(instance_id: str, error: Exception) -> None:
			diagnostics.record(
				"managedClientStopError",
				instanceId=instance_id,
				errorType=type(error).__name__,
				error=str(error),
			)

		client_stopper = ClientStopper(on_error=record_stop_error)
		own("clientStopper", client_stopper.close)

		def stop_client(instance_id: str, client: Any) -> None:
			control_dispatcher.discard_client(client)
			if not client_stopper.submit(instance_id, client):
				diagnostics.record("managedClientStopRejected", instanceId=instance_id)

		managed_client_factory = ManagedClientFactory(
			local_client_constructor=lambda *args, **kwargs: LocalTcpClient(*args, **kwargs),
			ssh_client_constructor=lambda *args, **kwargs: SshStdioClient(*args, **kwargs),
			on_event=lambda instance_id, event: (
				event_delivery.on_managed_event(instance_id, event) if event_delivery is not None else None
			),
			on_state=lambda instance_id, state: (
				event_delivery.on_managed_state(instance_id, state) if event_delivery is not None else None
			),
			record_network_diagnostic=lambda category, fields: (
				event_delivery.record_network_diagnostic(category, fields)
				if event_delivery is not None
				else diagnostics.record(category, **fields)
			),
		)

		def list_remote_sessions(profile, password):
			return SshSessionLister().list(
				profile.ssh_target,
				profile.port,
				profile.identity_file,
				password=password,
				askpass_path=os.path.join(runtimeConfig.PACKAGE_DIR, "resources", "ssh-askpass.cmd"),
			)

		def start_worker(name, target, args):
			threading.Thread(target=target, args=args, name=name, daemon=True).start()

		session_claim = SessionClaimService(
			coordinator,
			record_diagnostic=diagnostics.record,
			identity_fields=runtimeConfig.terminal_identity_fields,
			list_local_sessions=lambda: runtimeConfig.local_session_lister().list(),
			list_remote_sessions=list_remote_sessions,
			queue_main_thread=lambda callback, *args: scheduler.queue(callback, *args),
			start_worker=start_worker,
			monotonic=time.monotonic,
			sleep=time.sleep,
			local_claim_wait_seconds=runtimeConfig.LOCAL_CLAIM_WAIT_SECONDS,
			local_claim_poll_seconds=runtimeConfig.LOCAL_CLAIM_POLL_SECONDS,
			new_instance_runtime=editor_session.new_runtime,
			stop_client_async=stop_client,
			client_factory=managed_client_factory,
		)
		terminal_focus = TerminalFocusService(
			coordinator,
			identity_for_object=runtimeConfig.identity_for_object,
			identity_element=runtimeConfig.identity_element_for_object,
			identity_fields=runtimeConfig.terminal_identity_fields,
			record_diagnostic=diagnostics.record,
			discard_transient_context=lambda: (
				event_delivery.discard_transient_focus_context() if event_delivery is not None else None
			),
			activate_remembered_binding=lambda identity, instance_id, focus_regained=False: (
				temporary_bindings.activate_remembered_binding(identity, instance_id, focus_regained)
				if temporary_bindings is not None
				else None
			),
			consume_temporary_binding_reactivation=(session_claim.consume_temporary_binding_reactivation),
			handle_pending_full_state=lambda instance_id, event: (
				event_delivery.handle_managed_event(instance_id, event)
				if event_delivery is not None
				else None
			),
			reset_typed_echo=lambda: (
				event_delivery.reset_typed_echo() if event_delivery is not None else None
			),
			cancel_speech=speech.cancelSpeech,
			schedule_main_thread_call=scheduler.later,
			identity_exists=runtimeConfig.terminal_identity_exists,
			monotonic=time.monotonic,
			lifecycle_interval_ms=runtimeConfig.TERMINAL_LIFECYCLE_INTERVAL_MS,
			new_instance_runtime=editor_session.new_runtime,
			stop_client_async=stop_client,
			log_lifecycle_failure=lambda: log.exception("terminal lifecycle sweep failed open"),
		)
		dialogs = NvdaConnectionDialogs(
			deliver_result=scheduler.queue,
			runtime_active=lambda: not scheduler.closed,
		)
		temporary_bindings = TemporaryBindingWorkflow(
			coordinator=coordinator,
			session_claim=session_claim,
			terminal_focus=terminal_focus,
			dispatch_control=dispatch_control,
			scheduler=scheduler,
			diagnostics=diagnostics,
			dialogs=dialogs,
		)
		ui_manager = NvdaUiManager(
			settings,
			record_diagnostic=diagnostics.record,
			queue_main_thread=scheduler.queue,
			password_for_profile=lambda profile: (
				workflow.password_for_profile(profile) if workflow is not None else None
			),
			askpass_path=lambda: os.path.join(
				runtimeConfig.PACKAGE_DIR,
				"resources",
				"ssh-askpass.cmd",
			),
			product_name=runtimeConfig.PRODUCT_NAME,
			package_dir=runtimeConfig.PACKAGE_DIR,
			code_addon=runtimeConfig.CODE_ADDON,
			feedback_defaults=runtimeConfig.FEEDBACK_DEFAULTS,
			navigation_details_defaults=runtimeConfig.NAVIGATION_DETAILS_DEFAULTS,
			focus_announcement_default=runtimeConfig.FOCUS_ANNOUNCEMENT_DEFAULT,
		)
		terminal_actions = TerminalActions(
			coordinator=coordinator,
			editor_session=editor_session,
			control_dispatcher=control_dispatcher,
			presentation=presentation,
			diagnostics=diagnostics,
			addon_version=runtimeConfig.ADDON_VERSION,
			product_name=runtimeConfig.PRODUCT_NAME,
			nvda_version=lambda: getattr(buildVersion, "version", "unknown"),
		)
		event_delivery = EventDelivery(
			coordinator=coordinator,
			editor_session=editor_session,
			terminal_actions=terminal_actions,
			session_claim=session_claim,
			terminal_focus=terminal_focus,
			settings=settings,
			presentation=presentation,
			scheduler=scheduler,
			diagnostics=diagnostics,
			offer_temporary_binding=lambda identity, instance_id: (
				temporary_bindings.offer_temporary_binding(identity, instance_id)
				if temporary_bindings is not None
				else None
			),
		)
		workflow = ConnectionWorkflow(
			coordinator=coordinator,
			editor_session=editor_session,
			session_claim=session_claim,
			terminal_focus=terminal_focus,
			terminal_actions=terminal_actions,
			event_delivery=event_delivery,
			settings=settings,
			presentation=presentation,
			control_dispatcher=control_dispatcher,
			dispatch_control=dispatch_control,
			client_stopper=client_stopper,
			temporary_bindings=temporary_bindings,
			scheduler=scheduler,
			diagnostics=diagnostics,
			dialogs=dialogs,
			claim_key_name=runtimeConfig.SESSION_CLAIM_KEY_NAME,
			package_dir=runtimeConfig.PACKAGE_DIR,
		)
		integration = TerminalIntegrationService(
			terminal_focus,
			session_claim,
			editor_session,
			command_actions={
				TerminalCommand.TOGGLE_ACCESSIBILITY: workflow.toggle_accessibility,
				TerminalCommand.TOGGLE_BRAILLE_EXPLORATION: workflow.toggle_braille_exploration,
				TerminalCommand.READ_COMPLETION_DOCUMENTATION: (
					terminal_actions.read_completion_documentation
				),
				TerminalCommand.COPY_VISUAL_SELECTION: terminal_actions.copy_selection,
				TerminalCommand.COPY_LAST_YANK: terminal_actions.copy_last_yank,
				TerminalCommand.PASTE_WINDOWS_CLIPBOARD: terminal_actions.paste_windows_clipboard,
				TerminalCommand.SET_REGISTER_FROM_WINDOWS_CLIPBOARD: (
					terminal_actions.set_register_from_windows_clipboard
				),
				TerminalCommand.LEAVE_DIRECT_TERMINAL_INPUT: (terminal_actions.leave_direct_terminal_input),
				TerminalCommand.START_CONNECTION: workflow.start_connection,
				TerminalCommand.DISCONNECT_CONNECTION: workflow.disconnect_connection,
				TerminalCommand.FORGET_TEMPORARY_BINDING: workflow.forget_temporary_binding,
			},
			copy_diagnostic_report=terminal_actions.copy_diagnostic_report,
			claim_focused_session=workflow.claim_focused_session,
			present_braille_route_character=presentation.speak_braille_routed_character,
			control_dispatcher=control_dispatcher,
			present_exploration=event_delivery.present_exploration,
			exploration_details=lambda: settings.navigation_details(exploration=True),
			present_numbered_choice=presentation.present_numbered_choice,
			dismiss_numbered_choice=presentation.dismiss_numbered_choice,
			present_developer_context=presentation.present_developer_context,
			dismiss_developer_context=presentation.dismiss_developer_context,
			refresh_braille=lambda: event_delivery.queue_braille_refresh(True),
			numbered_choice_braille_start=settings.braille_suggestion_start,
			braille_routing_actions=settings.braille_routing_actions,
			braille_follows_speech_exploration=settings.braille_follows_speech_exploration,
			routing_repeat_timeout_ms=lambda: int(config.conf["keyboard"]["multiPressTimeout"]),
			schedule_later=scheduler.later,
			no_item_selected_message=_("No item selected"),
			record_diagnostic=diagnostics.record,
			fail_open_event=event_delivery.fail_open_terminal_event,
		)
		own("terminalIntegration", integration.close)
		event_delivery.bind_terminal_integration(integration)
		workflow.bind_terminal_integration(integration)
		lifecycle = AddonRuntime(
			registrar=serviceRegistrar,
			integration_service=integration,
			control_dispatcher=control_dispatcher,
			scheduler=scheduler,
			client_stopper=client_stopper,
			gate=coordinator.gate,
			profile_switch_action=config.post_configProfileSwitch,
			profile_switch_handler=settings.handle_profile_switch,
			clear_session_passwords=workflow.clear_passwords,
			stop_connections=workflow.stop_connections,
			focus_service=terminal_focus,
			claim_service=session_claim,
			ui_manager=ui_manager,
			presentation=presentation,
			diagnostics=diagnostics,
		)
		settings_snapshot = settings.snapshot()
		diagnostics.record(
			"addonStart",
			nvdaVersion=getattr(buildVersion, "version", "unknown"),
			configured=bool(settings_snapshot.get("connections")),
		)
		plugin_runtime = PluginRuntime(
			lifecycle,
			coordinator=coordinator,
			editor_session=editor_session,
			settings=settings,
			presentation=presentation,
			control_dispatcher=control_dispatcher,
			client_stopper=client_stopper,
			session_claim=session_claim,
			terminal_focus=terminal_focus,
			ui_manager=ui_manager,
			terminal_actions=terminal_actions,
			event_delivery=event_delivery,
			connection_workflow=workflow,
			temporary_bindings=temporary_bindings,
			integration=integration,
			scheduler=scheduler,
			diagnostics=diagnostics,
		)
		# AddonRuntime now owns every previously registered resource. Replace
		# individual rollback entries before activation so a start failure closes
		# each owner exactly once.
		cleanup.clear()
		own("runtime", lifecycle.close)
		lifecycle.start()
		cleanup.clear()
		return plugin_runtime
	except Exception:
		rollback()
		raise
