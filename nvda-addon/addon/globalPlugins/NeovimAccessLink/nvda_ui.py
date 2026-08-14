"""NVDA settings, menu, and component-management integration."""

import os
import pathlib
import threading

import addonHandler
import ui

from .core.connection_profiles import (
	parse_profile,
	parse_profiles,
	remove_profile,
	save_profile,
	unique_profile_id,
)
from .core.connection_targets import ConnectionTarget, LOCAL_WINDOWS_TCP, local_windows_target
from .core.config_transfer import (
	CONFIGURATION_COPY_LOCAL,
	CONFIGURATION_STARTER,
	CONFIGURATION_UNCHANGED,
	LocalConfigArchiveBuilder,
)
from .core.local_install import LocalPluginInstaller
from .core.ssh_install import InstallResult, SshUserInstaller
from .core.starter_config import StarterConfigInstaller, default_local_config_directory
from .settings_service import (
	AUTOMATIC_PARAMETER_HINTS_DEFAULT,
	BRAILLE_DEVELOPER_START_DEFAULT,
	BRAILLE_DEVELOPER_START_MAXIMUM,
	BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT,
	BRAILLE_ROUTING_DEFAULTS,
	BRAILLE_SUGGESTION_START_DEFAULT,
	BRAILLE_SUGGESTION_START_MAXIMUM,
	TEMPORARY_BINDING_PROMPT_DEFAULT,
)

addonHandler.initTranslation()


class NvdaUiManager:
	"""Own add-on UI registration and user-triggered component maintenance."""

	def __init__(
		self,
		settings_service,
		*,
		record_diagnostic,
		queue_main_thread,
		password_for_profile,
		askpass_path,
		product_name,
		package_dir,
		code_addon,
		feedback_defaults,
		navigation_details_defaults,
		focus_announcement_default,
	):
		self._settingsService = settings_service
		self._recordDiagnostic = record_diagnostic
		self._queueMainThread = queue_main_thread
		self._passwordForProfile = password_for_profile
		self._askpassPath = askpass_path
		self._productName = product_name
		self._packageDir = package_dir
		self._codeAddon = code_addon
		self._feedbackDefaults = feedback_defaults
		self._navigationDetailsDefaults = navigation_details_defaults
		self._focusAnnouncementDefault = focus_announcement_default
		self._menuItems = []
		self._topLevelMenuItem = None
		self._topLevelMenu = None
		self._menuTray = None
		self._settingsPanelClass = None
		self._registered = False

	def register(self):
		"""Register independent NVDA UI entry points."""
		if self._registered:
			return
		self._registered = True
		self._installMenus()
		self._registerSettingsPanel()

	def unregister(self):
		"""Remove every NVDA UI entry point registered by this manager."""
		if not self._registered:
			return
		self._registered = False
		self._removeMenus()
		self._unregisterSettingsPanel()

	def _promptConnectionProfile(self, existing, profiles):
		values = dict(existing or {})
		while True:
			result = self._showConnectionProfileDialog(values)
			if result is None:
				return None
			values.update(result)
			try:
				port = int(result["port"])
			except ValueError:
				ui.message(_("SSH port must be a number between 1 and 65535"))
				continue
			identifier = values.get("id", "") or unique_profile_id(
				result["name"],
				{profile.get("id", "") for profile in profiles},
			)
			candidate = {
				"id": identifier,
				"name": result["name"].strip(),
				"host": result["host"].strip(),
				"user": result["user"].strip(),
				"port": port,
				"identityFile": result["identityFile"],
				"authentication": result["authentication"],
			}
			if candidate["authentication"] == "password":
				candidate["identityFile"] = ""
			try:
				return parse_profile(candidate).as_dict()
			except ValueError as error:
				self._recordDiagnostic("connectionProfileValidationError", error=str(error))
				ui.message(_("The connection settings are invalid: {error}").format(error=str(error)))

	@staticmethod
	def _authenticationChoices():
		return (
			_("Use OpenSSH setup (recommended: keys, ssh-agent or SSH config)"),
			_("Ask for the SSH password when connecting (password is not saved)"),
		)

	@staticmethod
	def _authenticationDescription(authentication):
		if authentication == "password":
			return _(
				"NVDA asks for the Linux account password when it connects. "
				"The password stays in memory only and the Linux SSH server must allow password login."
			)
		return _(
			"OpenSSH uses the normal Windows SSH configuration, a selected private key, "
			"or ssh-agent. Choose this when ssh from Windows already works without a password prompt."
		)

	def _showConnectionProfileDialog(self, values):
		import gui
		import wx

		dialog = wx.Dialog(
			gui.mainFrame,
			title=_("Add Linux connection") if not values.get("id") else _("Edit Linux connection"),
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
		)
		try:
			outer = wx.BoxSizer(wx.VERTICAL)
			introduction = wx.StaticText(
				dialog,
				label=_(
					"Save the Linux account used for Neovim. The same connection is used to "
					"install the Linux components and to exchange accessibility data."
				),
			)
			introduction.Wrap(560)
			outer.Add(introduction, 0, wx.EXPAND | wx.ALL, 10)
			grid = wx.FlexGridSizer(rows=0, cols=2, vgap=8, hgap=10)
			grid.AddGrowableCol(1, 1)

			def add_text(label, value, name):
				grid.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
				control = wx.TextCtrl(dialog, value=value, name=name)
				grid.Add(control, 1, wx.EXPAND)
				return control

			name = add_text(_("Connection name:"), values.get("name", ""), "connectionName")
			host = add_text(
				_("Server name, address or SSH alias:"),
				values.get("host", ""),
				"connectionHost",
			)
			user = add_text(
				_("Linux username (optional when defined by SSH config):"),
				values.get("user", ""),
				"connectionUser",
			)
			port = add_text(_("SSH port:"), str(values.get("port", 22)), "connectionPort")
			identity = add_text(
				_("Private key file (optional):"),
				values.get("identityFile", ""),
				"connectionIdentity",
			)
			grid.Add(wx.StaticText(dialog, label=_("Sign-in method:")), 0, wx.ALIGN_CENTER_VERTICAL)
			authentication = wx.Choice(dialog, choices=list(self._authenticationChoices()))
			authentication.SetSelection(1 if values.get("authentication") == "password" else 0)
			grid.Add(authentication, 1, wx.EXPAND)
			outer.Add(grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
			authentication_help = wx.StaticText(dialog)
			authentication_help.Wrap(560)
			outer.Add(authentication_help, 0, wx.EXPAND | wx.ALL, 10)

			def update_authentication(_event=None):
				method = "password" if authentication.GetSelection() == 1 else "openSsh"
				authentication_help.SetLabel(self._authenticationDescription(method))
				authentication_help.Wrap(560)
				identity.Enable(method == "openSsh")
				dialog.Layout()

			authentication.Bind(wx.EVT_CHOICE, update_authentication)
			update_authentication()
			buttons = dialog.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
			if buttons is not None:
				outer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
			dialog.SetSizerAndFit(outer)
			dialog.SetMinSize((640, -1))
			dialog.CentreOnParent()
			name.SetFocus()
			if dialog.ShowModal() != wx.ID_OK:
				return None
			return {
				"name": name.GetValue(),
				"host": host.GetValue(),
				"user": user.GetValue(),
				"port": port.GetValue(),
				"identityFile": identity.GetValue(),
				"authentication": ("password" if authentication.GetSelection() == 1 else "openSsh"),
			}
		finally:
			dialog.Destroy()

	@staticmethod
	def _profileChoiceLabel(value):
		try:
			profile = parse_profile(value)
			port = f":{profile.port}" if profile.port != 22 else ""
			return f"{profile.name} — {profile.ssh_target}{port}"
		except ValueError:
			if isinstance(value, dict):
				return str(value.get("name", _("Invalid connection")))
			return _("Invalid connection")

	def _registerSettingsPanel(self):
		try:
			import wx
			from gui import guiHelper
			from gui.settingsDialogs import NVDASettingsDialog, SettingsPanel

			ui_manager = self
			settings_service = self._settingsService
			product_name = self._productName
			feedback_defaults = self._feedbackDefaults
			navigation_details_defaults = self._navigationDetailsDefaults
			focus_announcement_default = self._focusAnnouncementDefault
			labels = (
				("global", _("&Global action feedback:")),
				("mode", _("Insert and normal &mode changes:")),
				("delete", _("&Deleting text:")),
				("replace", _("&Replacing text:")),
				("lineBoundary", _("Line &boundaries:")),
				("fileBoundary", _("&File boundaries:")),
				("lineCrossed", _("Crossing into another &line:")),
				("matchingError", _("Missing matching &bracket:")),
				("diagnosticLine", _("Diagnostics when entering a &line:")),
				("diagnosticPosition", _("Diagnostics at the cursor &position:")),
				("clipboard", _("Copy and &paste:")),
			)

			class NeovimAccessLinkSettingsPanel(SettingsPanel):
				title = product_name

				def makeSettings(self, sizer):
					settings = settings_service.snapshot()
					helper = guiHelper.BoxSizerHelper(self, sizer=sizer)
					self.settingsNotebook = wx.Notebook(self)
					helper.addItem(self.settingsNotebook)
					general_page = wx.Panel(self.settingsNotebook)
					feedback_page = wx.Panel(self.settingsNotebook)
					navigation_page = wx.Panel(self.settingsNotebook)
					braille_page = wx.Panel(self.settingsNotebook)
					connections_page = wx.Panel(self.settingsNotebook)
					general_sizer = wx.BoxSizer(wx.VERTICAL)
					feedback_sizer = wx.BoxSizer(wx.VERTICAL)
					navigation_sizer = wx.BoxSizer(wx.VERTICAL)
					braille_sizer = wx.BoxSizer(wx.VERTICAL)
					connections_sizer = wx.BoxSizer(wx.VERTICAL)
					general_page.SetSizer(general_sizer)
					feedback_page.SetSizer(feedback_sizer)
					navigation_page.SetSizer(navigation_sizer)
					braille_page.SetSizer(braille_sizer)
					connections_page.SetSizer(connections_sizer)
					# Translators: Name of the general settings tab.
					self.settingsNotebook.AddPage(general_page, _("General"))
					# Translators: Name of the sound and speech feedback settings tab.
					self.settingsNotebook.AddPage(feedback_page, _("Feedback"))
					# Translators: Name of the navigation-detail settings tab.
					self.settingsNotebook.AddPage(navigation_page, _("Navigation"))
					# Translators: Name of the Braille settings tab.
					self.settingsNotebook.AddPage(braille_page, _("Braille"))
					# Translators: Name of the connection settings tab.
					self.settingsNotebook.AddPage(connections_page, _("Connections"))
					self.settingsTabLabels = (
						_("General"),
						_("Feedback"),
						_("Navigation"),
						_("Braille"),
						_("Connections"),
					)
					general_helper = guiHelper.BoxSizerHelper(general_page, sizer=general_sizer)
					feedback_helper = guiHelper.BoxSizerHelper(feedback_page, sizer=feedback_sizer)
					navigation_helper = guiHelper.BoxSizerHelper(
						navigation_page,
						sizer=navigation_sizer,
					)
					braille_helper = guiHelper.BoxSizerHelper(
						braille_page,
						sizer=braille_sizer,
					)
					connections_helper = guiHelper.BoxSizerHelper(
						connections_page,
						sizer=connections_sizer,
					)

					global_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						general_page,
						label=_("Global action feedback"),
					)
					general_helper.addItem(global_sizer)
					global_group = guiHelper.BoxSizerHelper(general_page, sizer=global_sizer)
					choices = [_("Off"), _("Speech"), _("Tones"), _("Both Speech and Tones")]
					self.feedbackControls = {}
					self.feedbackValueMaps = {}
					feedback = settings.get("feedback", feedback_defaults)
					key, label = labels[0]
					control = global_group.addLabeledControl(label, wx.Choice, choices=choices)
					control.SetSelection(int(feedback.get(key, feedback_defaults[key])))
					self.feedbackControls[key] = control
					self.feedbackValueMaps[key] = (0, 1, 2, 3)

					focus_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						general_page,
						label=_("Session focus"),
					)
					general_helper.addItem(focus_sizer)
					focus_group = guiHelper.BoxSizerHelper(general_page, sizer=focus_sizer)
					self.focusAnnouncement = focus_group.addLabeledControl(
						_("When focusing or changing buffers in a Neovim session:"),
						wx.Choice,
						choices=[
							_("No announcement"),
							_("Current line"),
							_("Current context, mode and connection name"),
						],
					)
					self.focusAnnouncement.SetSelection(
						int(
							settings.get(
								"focusAnnouncement",
								focus_announcement_default,
							)
						)
					)
					# Translators: Checkbox controlling brief parameter speech while typing calls.
					self.automaticParameterHints = wx.CheckBox(
						general_page,
						label=_("Automatically speak the active function &parameter while typing"),
					)
					self.automaticParameterHints.SetValue(
						bool(
							settings.get(
								"automaticParameterHints",
								AUTOMATIC_PARAMETER_HINTS_DEFAULT,
							)
						)
					)
					focus_group.addItem(self.automaticParameterHints)

					# Translators: Group for Braille behavior during speech exploration.
					braille_exploration_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						braille_page,
						label=_("Speech exploration mode"),
					)
					braille_helper.addItem(braille_exploration_sizer)
					braille_exploration_group = guiHelper.BoxSizerHelper(
						braille_page,
						sizer=braille_exploration_sizer,
					)
					# Translators: Checkbox making the Braille display follow speech exploration.
					self.brailleFollowSpeechExploration = wx.CheckBox(
						braille_page,
						label=_("Braille display follows the &speech exploration mode position"),
					)
					self.brailleFollowSpeechExploration.SetValue(
						bool(
							settings.get(
								"brailleFollowSpeechExploration",
								BRAILLE_FOLLOW_SPEECH_EXPLORATION_DEFAULT,
							)
						)
					)
					braille_exploration_group.addItem(self.brailleFollowSpeechExploration)

					# Translators: Group for actions assigned to Braille routing keys.
					braille_routing_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						braille_page,
						label=_("Routing keys"),
					)
					braille_helper.addItem(braille_routing_sizer)
					braille_routing_group = guiHelper.BoxSizerHelper(
						braille_page,
						sizer=braille_routing_sizer,
					)
					braille_routing = settings.get("brailleRouting", BRAILLE_ROUTING_DEFAULTS)
					# Translators: Action performed by pressing one Braille routing key twice.
					self.brailleRoutingWordAction = braille_routing_group.addLabeledControl(
						_("Double routing press on a &word:"),
						wx.Choice,
						choices=[
							_("Route only"),
							_("Change word (cw)"),
							_("Delete word (dw)"),
						],
					)
					self.brailleRoutingWordAction.SetSelection(
						int(braille_routing.get("wordAction", BRAILLE_ROUTING_DEFAULTS["wordAction"]))
					)
					# Translators: Action performed by pressing one Braille routing key three times.
					self.brailleRoutingLineAction = braille_routing_group.addLabeledControl(
						_("Triple routing press on a &line:"),
						wx.Choice,
						choices=[
							_("Route only"),
							_("Change to end of line (c$)"),
							_("Delete to end of line (d$)"),
						],
					)
					self.brailleRoutingLineAction.SetSelection(
						int(braille_routing.get("lineAction", BRAILLE_ROUTING_DEFAULTS["lineAction"]))
					)
					# Translators: Starting position used for a triple-press Braille line action.
					self.brailleRoutingLineStart = braille_routing_group.addLabeledControl(
						_("&Start triple-press line action at:"),
						wx.Choice,
						choices=[
							_("Routed position"),
							_("First non-blank character"),
							_("Beginning of line"),
						],
					)
					self.brailleRoutingLineStart.SetSelection(
						int(braille_routing.get("lineStart", BRAILLE_ROUTING_DEFAULTS["lineStart"]))
					)
					# Translators: Explains which NVDA setting controls repeated Braille routing timing.
					braille_routing_group.addItem(
						wx.StaticText(
							braille_page,
							label=_(
								"Timing uses NVDA's multiple key press timeout from the Keyboard settings."
							),
						)
					)

					# Translators: Group for Braille presentation of spelling suggestions.
					braille_spelling_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						braille_page,
						label=_("Spelling suggestions"),
					)
					braille_helper.addItem(braille_spelling_sizer)
					braille_spelling_group = guiHelper.BoxSizerHelper(
						braille_page,
						sizer=braille_spelling_sizer,
					)
					# Translators: One-based Braille cell where a spelling suggestion begins.
					self.brailleSuggestionStart = braille_spelling_group.addLabeledControl(
						_("Start spelling &suggestions at Braille cell:"),
						wx.SpinCtrl,
						min=BRAILLE_SUGGESTION_START_DEFAULT,
						max=BRAILLE_SUGGESTION_START_MAXIMUM,
					)
					self.brailleSuggestionStart.SetValue(
						int(
							settings.get(
								"brailleSuggestionStart",
								BRAILLE_SUGGESTION_START_DEFAULT,
							)
						)
					)
					# Translators: Group for Braille presentation of temporary developer information.
					braille_developer_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						braille_page,
						label=_("Developer information"),
					)
					braille_helper.addItem(braille_developer_sizer)
					braille_developer_group = guiHelper.BoxSizerHelper(
						braille_page,
						sizer=braille_developer_sizer,
					)
					# Translators: One-based Braille cell where held parameters or diagnostics begin.
					self.brailleDeveloperStart = braille_developer_group.addLabeledControl(
						_("Start temporary &developer information at Braille cell:"),
						wx.SpinCtrl,
						min=BRAILLE_DEVELOPER_START_DEFAULT,
						max=BRAILLE_DEVELOPER_START_MAXIMUM,
					)
					self.brailleDeveloperStart.SetValue(
						int(
							settings.get(
								"brailleDeveloperStart",
								settings.get(
									"brailleSuggestionStart",
									BRAILLE_DEVELOPER_START_DEFAULT,
								),
							)
						)
					)

					actions_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						feedback_page,
						label=_("Individual actions"),
					)
					feedback_helper.addItem(actions_sizer)
					actions_group = guiHelper.BoxSizerHelper(feedback_page, sizer=actions_sizer)
					for key, label in labels[1:]:
						value_map = (
							(0, 2) if key in {"diagnosticLine", "diagnosticPosition"} else (0, 1, 2, 3)
						)
						control_choices = [_("Off"), _("Tones")] if len(value_map) == 2 else choices
						control = actions_group.addLabeledControl(
							label,
							wx.Choice,
							choices=control_choices,
						)
						value = int(feedback.get(key, feedback_defaults[key]))
						control.SetSelection(value_map.index(value) if value in value_map else 0)
						self.feedbackControls[key] = control
						self.feedbackValueMaps[key] = value_map
					note = wx.StaticText(
						feedback_page,
						label=_(
							"Typing echo, indentation, suggestions, spelling and grammar continue to use NVDA settings."
						),
					)
					actions_group.addItem(note)

					navigation_details = settings.get(
						"navigationDetails",
						navigation_details_defaults,
					)
					# Translators: Group for feedback after ordinary Neovim cursor movement.
					normal_navigation_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						navigation_page,
						label=_("Normal navigation"),
					)
					navigation_helper.addItem(normal_navigation_sizer)
					normal_navigation_group = guiHelper.BoxSizerHelper(
						navigation_page,
						sizer=normal_navigation_sizer,
					)
					# Translators: Choices for details spoken after word navigation.
					word_detail_choices = [
						_("Word only"),
						_("Word and cursor character"),
					]
					# Translators: Choices for details spoken after line navigation.
					line_detail_choices = [
						_("Line only"),
						_("Line and current word"),
						_("Line and cursor character"),
						_("Line, current word and cursor character"),
					]
					self.navigationDetailControls = {}
					# Translators: Label for details spoken after normal word navigation.
					control = normal_navigation_group.addLabeledControl(
						_("&Word navigation:"),
						wx.Choice,
						choices=word_detail_choices,
					)
					control.SetSelection(
						int(
							navigation_details.get(
								"navigationWord",
								navigation_details_defaults["navigationWord"],
							)
						)
					)
					self.navigationDetailControls["navigationWord"] = control
					# Translators: Label for details spoken after normal line navigation.
					control = normal_navigation_group.addLabeledControl(
						_("&Line navigation:"),
						wx.Choice,
						choices=line_detail_choices,
					)
					control.SetSelection(
						int(
							navigation_details.get(
								"navigationLine",
								navigation_details_defaults["navigationLine"],
							)
						)
					)
					self.navigationDetailControls["navigationLine"] = control

					# Translators: Group for feedback when the NVDA key ends speech exploration.
					exploration_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						navigation_page,
						label=_("Speech exploration mode release"),
					)
					navigation_helper.addItem(exploration_sizer)
					exploration_group = guiHelper.BoxSizerHelper(
						navigation_page,
						sizer=exploration_sizer,
					)
					# Translators: Label for details spoken after word speech exploration.
					control = exploration_group.addLabeledControl(
						_("After &word exploration in speech exploration mode:"),
						wx.Choice,
						choices=word_detail_choices,
					)
					control.SetSelection(
						int(
							navigation_details.get(
								"explorationWord",
								navigation_details_defaults["explorationWord"],
							)
						)
					)
					self.navigationDetailControls["explorationWord"] = control
					# Translators: Label for details spoken after line speech exploration.
					control = exploration_group.addLabeledControl(
						_("After &line exploration in speech exploration mode:"),
						wx.Choice,
						choices=line_detail_choices,
					)
					control.SetSelection(
						int(
							navigation_details.get(
								"explorationLine",
								navigation_details_defaults["explorationLine"],
							)
						)
					)
					self.navigationDetailControls["explorationLine"] = control

					connection_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						connections_page,
						label=_("Saved SSH connections"),
					)
					connections_helper.addItem(connection_sizer)
					connection_group = guiHelper.BoxSizerHelper(
						connections_page,
						sizer=connection_sizer,
					)
					self.connectionProfiles = list(settings.get("connections", []))
					self.connectionChoice = connection_group.addLabeledControl(
						_("Saved &connections:"),
						wx.Choice,
						choices=[
							ui_manager._profileChoiceLabel(profile) for profile in self.connectionProfiles
						],
					)
					self.connectionChoice.SetSelection(0 if self.connectionProfiles else -1)
					self.connectionChoice.Bind(wx.EVT_CHOICE, self._onConnectionSelection)
					connection_buttons = guiHelper.ButtonHelper(wx.HORIZONTAL)
					self.addConnectionButton = connection_buttons.addButton(
						connections_page,
						label=_("&Add connection..."),
					)
					self.editConnectionButton = connection_buttons.addButton(
						connections_page,
						label=_("&Edit connection..."),
					)
					self.removeConnectionButton = connection_buttons.addButton(
						connections_page,
						label=_("&Remove connection"),
					)
					self.addConnectionButton.Bind(wx.EVT_BUTTON, self._onAddConnection)
					self.editConnectionButton.Bind(wx.EVT_BUTTON, self._onEditConnection)
					self.removeConnectionButton.Bind(wx.EVT_BUTTON, self._onRemoveConnection)
					connection_group.addItem(connection_buttons)
					connection_group.addItem(
						wx.StaticText(
							connections_page,
							label=_(
								"To install or update components, use the add-on command "
								"in NVDA's {name} menu and select this computer "
								"or saved Linux connections."
							).format(name=product_name),
						)
					)
					# Translators: Group controlling the question shown after a new F12 association.
					temporary_binding_sizer = wx.StaticBoxSizer(
						wx.VERTICAL,
						connections_page,
						label=_("Temporary terminal connections"),
					)
					connections_helper.addItem(temporary_binding_sizer)
					temporary_binding_group = guiHelper.BoxSizerHelper(
						connections_page,
						sizer=temporary_binding_sizer,
					)
					# Translators: Choice controlling whether the temporary connection question is shown.
					self.temporaryBindingPrompt = temporary_binding_group.addLabeledControl(
						_("After a new &F12 association:"),
						wx.Choice,
						choices=[
							_("Ask whether to remember the connection"),
							_("Remember the connection"),
							_("Do not remember the connection"),
						],
					)
					self.temporaryBindingPrompt.SetSelection(
						int(
							settings.get(
								"temporaryBindingPrompt",
								TEMPORARY_BINDING_PROMPT_DEFAULT,
							)
						)
					)
					self._updateConnectionButtons()

				def _onConnectionSelection(self, _event):
					self._updateConnectionButtons()

				def _updateConnectionButtons(self):
					selected = 0 <= self.connectionChoice.GetSelection() < len(self.connectionProfiles)
					self.editConnectionButton.Enable(selected)
					self.removeConnectionButton.Enable(selected)

				def _refreshConnections(self, selected_id=""):
					self.connectionChoice.SetItems(
						[ui_manager._profileChoiceLabel(profile) for profile in self.connectionProfiles]
					)
					index = next(
						(
							position
							for position, profile in enumerate(self.connectionProfiles)
							if profile.get("id") == selected_id
						),
						0 if self.connectionProfiles else -1,
					)
					self.connectionChoice.SetSelection(index)
					self._updateConnectionButtons()

				def _onAddConnection(self, _event):
					profile = ui_manager._promptConnectionProfile(None, self.connectionProfiles)
					if profile is None:
						return
					profiles = save_profile(self.connectionProfiles, profile)
					self.connectionProfiles = [item.as_dict() for item in profiles]
					self._refreshConnections(profile["id"])

				def _onEditConnection(self, _event):
					index = self.connectionChoice.GetSelection()
					if not 0 <= index < len(self.connectionProfiles):
						return
					original = self.connectionProfiles[index]
					profile = ui_manager._promptConnectionProfile(original, self.connectionProfiles)
					if profile is None:
						return
					profiles = save_profile(self.connectionProfiles, profile, original["id"])
					self.connectionProfiles = [item.as_dict() for item in profiles]
					self._refreshConnections(profile["id"])

				def _onRemoveConnection(self, _event):
					index = self.connectionChoice.GetSelection()
					if not 0 <= index < len(self.connectionProfiles):
						return
					identifier = self.connectionProfiles[index].get("id", "")
					profiles = remove_profile(self.connectionProfiles, identifier)
					self.connectionProfiles = [item.as_dict() for item in profiles]
					self._refreshConnections()

				def onSave(self):
					change = settings_service.update(
						{
							"focusAnnouncement": self.focusAnnouncement.GetSelection(),
							"automaticParameterHints": self.automaticParameterHints.GetValue(),
							"temporaryBindingPrompt": self.temporaryBindingPrompt.GetSelection(),
							"brailleSuggestionStart": self.brailleSuggestionStart.GetValue(),
							"brailleDeveloperStart": self.brailleDeveloperStart.GetValue(),
							"brailleFollowSpeechExploration": (
								self.brailleFollowSpeechExploration.GetValue()
							),
							"brailleRouting": {
								"wordAction": self.brailleRoutingWordAction.GetSelection(),
								"lineAction": self.brailleRoutingLineAction.GetSelection(),
								"lineStart": self.brailleRoutingLineStart.GetSelection(),
							},
							"feedback": {
								key: self.feedbackValueMaps[key][control.GetSelection()]
								for key, control in self.feedbackControls.items()
							},
							"navigationDetails": {
								key: control.GetSelection()
								for key, control in self.navigationDetailControls.items()
							},
							"connections": list(self.connectionProfiles),
						}
					)
					if change.claim_inventory_started:
						ui.message(_("Saved connections changed; checking Neovim connections again"))

			NVDASettingsDialog.categoryClasses.append(NeovimAccessLinkSettingsPanel)
			self._settingsPanelClass = NeovimAccessLinkSettingsPanel
		except Exception as error:
			self._recordDiagnostic(
				"settingsPanelUnavailable",
				errorType=type(error).__name__,
				error=str(error),
			)

	def _unregisterSettingsPanel(self):
		panel = self._settingsPanelClass
		self._settingsPanelClass = None
		if panel is None:
			return
		try:
			from gui.settingsDialogs import NVDASettingsDialog

			if panel in NVDASettingsDialog.categoryClasses:
				NVDASettingsDialog.categoryClasses.remove(panel)
		except Exception as error:
			self._recordDiagnostic(
				"settingsPanelRemoveError",
				errorType=type(error).__name__,
				error=str(error),
			)

	def _installMenus(self):
		try:
			import gui
			import wx

			tray = gui.mainFrame.sysTrayIcon
			menu = wx.Menu()
			self._menuTray = tray
			self._topLevelMenu = menu

			def append(label, handler):
				item = menu.Append(wx.ID_ANY, label)
				tray.Bind(wx.EVT_MENU, handler, item)
				self._menuItems.append((item, handler, wx))

			# Translators: Opens the add-on settings category.
			append(_("&Settings..."), self._onOpenSettings)
			# Translators: Opens component installation and update choices.
			append(_("&Install or update components..."), self._onInstallServer)
			# Translators: Opens component removal choices.
			append(_("&Remove components..."), self._onRemoveComponents)
			menu.AppendSeparator()
			# Translators: Opens the installed quick guide in a web browser.
			append(_("&Quick Guide"), self._documentationHandler("quick-guide.html"))
			# Translators: Opens the installed user manual in a web browser.
			append(_("User &Manual"), self._documentationHandler("readme.html"))
			# Translators: Opens the installed developer documentation in a web browser.
			append(
				_("&Developer Documentation"),
				self._documentationHandler("developer-documentation.html"),
			)
			# Translators: Opens the installed guided practical tests in a web browser.
			append(
				_("Guided &Practical Tests"),
				self._documentationHandler("human-testing.html"),
			)
			main_menu = tray.menu
			position = min(2, main_menu.GetMenuItemCount())
			self._topLevelMenuItem = main_menu.Insert(
				position,
				wx.ID_ANY,
				self._productName,
				menu,
			)
		except Exception as error:
			self._removeMenus()
			self._recordDiagnostic(
				"menuUnavailable",
				errorType=type(error).__name__,
				error=str(error),
			)

	def _removeMenus(self):
		tray = self._menuTray
		for item, handler, wx in self._menuItems:
			try:
				tray.Unbind(wx.EVT_MENU, handler=handler, source=item)
			except Exception:
				pass
		if self._topLevelMenuItem is not None and tray is not None:
			try:
				tray.menu.Remove(self._topLevelMenuItem.GetId())
			except Exception:
				pass
		self._menuItems = []
		self._topLevelMenuItem = None
		self._topLevelMenu = None
		self._menuTray = None

	def _onOpenSettings(self, _event):
		if self._settingsPanelClass is None:
			ui.message(_("{name} settings are unavailable").format(name=self._productName))
			return
		try:
			import gui
			from gui.settingsDialogs import NVDASettingsDialog

			gui.mainFrame.popupSettingsDialog(NVDASettingsDialog, self._settingsPanelClass)
		except Exception as error:
			self._recordDiagnostic(
				"settingsOpenError",
				errorType=type(error).__name__,
				error=str(error),
			)
			ui.message(_("Could not open {name} settings").format(name=self._productName))

	def _documentationHandler(self, file_name):
		def open_documentation(_event):
			self._openDocumentation(file_name)

		return open_documentation

	def _openDocumentation(self, file_name):
		try:
			path = self._codeAddon.getDocFilePath(file_name)
			if not path:
				raise FileNotFoundError(file_name)
			os.startfile(path)
		except Exception as error:
			self._recordDiagnostic(
				"documentationOpenError",
				fileName=file_name,
				errorType=type(error).__name__,
				error=str(error),
			)
			ui.message(_("Could not open the installed documentation"))

	@staticmethod
	def _installProfileLabel(profile):
		method = (
			_("OpenSSH keys or configuration")
			if profile.authentication == "openSsh"
			else _("password prompt")
		)
		return _("{name}: {target}, port {port}, {method}").format(
			name=profile.name,
			target=profile.ssh_target,
			port=profile.port,
			method=method,
		)

	@staticmethod
	def _installTargetLabel(target):
		if isinstance(target, ConnectionTarget) and target.kind == LOCAL_WINDOWS_TCP:
			return _("This computer: local Windows Neovim plugin")
		return NvdaUiManager._installProfileLabel(target)

	@staticmethod
	def _installTargetSummary(target):
		if isinstance(target, ConnectionTarget) and target.kind == LOCAL_WINDOWS_TCP:
			return target.name, _("this computer")
		return target.name, target.ssh_target

	def _chooseComponentTargets(self, remove=False):
		import gui
		import wx
		from gui.nvdaControls import CustomCheckListBox

		try:
			profiles = parse_profiles(self._settingsService.snapshot().get("connections", []))
		except ValueError as error:
			self._recordDiagnostic("installProfileListError", error=str(error))
			ui.message(_("The saved Linux connections are invalid; correct them in settings first"))
			return None
		targets = [local_windows_target(_("This computer - local Neovim")), *profiles]
		dialog = wx.Dialog(
			gui.mainFrame,
			title=_("Remove Neovim components") if remove else _("Install or update Neovim components"),
		)
		outer_sizer = wx.BoxSizer(wx.VERTICAL)
		instructions = wx.StaticText(
			dialog,
			label=_(
				"Close Neovim on the selected targets, then choose where to remove the components. "
				"Other Neovim plugins and configuration are preserved."
			)
			if remove
			else _("Select one or more targets. Administrator rights are not required."),
		)
		instructions.Wrap(620)
		outer_sizer.Add(instructions, 0, wx.ALL | wx.EXPAND, 12)
		select_all = wx.CheckBox(dialog, label=_("Select all connections"))
		outer_sizer.Add(select_all, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
		list_label = wx.StaticText(
			dialog,
			label=_("Connections to remove components from:") if remove else _("Connections to update:"),
		)
		outer_sizer.Add(list_label, 0, wx.LEFT | wx.RIGHT, 12)
		connection_list = CustomCheckListBox(
			dialog,
			choices=[self._installTargetLabel(target) for target in targets],
		)
		connection_list.SetName(
			_("Connections to remove components from") if remove else _("Connections to update")
		)
		outer_sizer.Add(connection_list, 1, wx.ALL | wx.EXPAND, 12)
		configuration_choice = None
		if not remove:
			# Translators: Label for choosing whether the installer changes Neovim configuration.
			configuration_label = wx.StaticText(dialog, label=_("Neovim configuration:"))
			outer_sizer.Add(configuration_label, 0, wx.LEFT | wx.RIGHT, 12)
			configuration_modes = (
				CONFIGURATION_UNCHANGED,
				CONFIGURATION_STARTER,
				CONFIGURATION_COPY_LOCAL,
			)
			configuration_choice = wx.Choice(
				dialog,
				choices=(
					# Translators: Component installer option that leaves all Neovim configuration unchanged.
					_("Do not change Neovim configuration"),
					# Translators: Component installer option that creates a basic Neovim configuration.
					_("Install the basic Neovim configuration with lazy.nvim and Oil"),
					# Translators: Copies this computer's complete Neovim configuration to Linux targets.
					_("Copy this computer's Neovim configuration to selected Linux connections"),
				),
			)
			configuration_choice.SetSelection(0)
			configuration_choice.SetName(_("Neovim configuration"))
			outer_sizer.Add(configuration_choice, 0, wx.ALL | wx.EXPAND, 12)
			# Translators: Explains the two optional configuration installation modes and their limits.
			configuration_note = wx.StaticText(
				dialog,
				label=_(
					"The basic configuration applies to every selected target. Copying transfers the complete "
					"local Windows configuration only to selected Linux connections. Existing target "
					"configuration is backed up first. Windows-specific paths and directly executed scripts "
					"may need adjustment on Linux. With lazy.nvim, the installed Access Link copy must be "
					"listed explicitly as a local plugin. Review the local configuration for secrets before "
					"copying it."
				),
			)
			configuration_note.Wrap(620)
			outer_sizer.Add(configuration_note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

		def on_select_all(_event):
			checked = select_all.IsChecked()
			for index in range(len(targets)):
				connection_list.Check(index, checked)

		def on_connection_checked(event):
			event.Skip()
			select_all.SetValue(all(connection_list.IsChecked(index) for index in range(len(targets))))

		select_all.Bind(wx.EVT_CHECKBOX, on_select_all)
		connection_list.Bind(wx.EVT_CHECKLISTBOX, on_connection_checked)
		outer_sizer.Add(
			dialog.CreateButtonSizer(wx.OK | wx.CANCEL),
			0,
			wx.ALL | wx.ALIGN_RIGHT,
			12,
		)
		dialog.SetSizerAndFit(outer_sizer)
		dialog.SetMinSize((720, 500 if not remove else 360))
		select_all.SetFocus()
		try:
			while dialog.ShowModal() == wx.ID_OK:
				selected = [targets[index] for index in connection_list.GetCheckedItems()]
				if selected:
					if remove:
						return selected
					configuration_mode = configuration_modes[configuration_choice.GetSelection()]
					if configuration_mode == CONFIGURATION_COPY_LOCAL and not any(
						not isinstance(target, ConnectionTarget) or target.kind != LOCAL_WINDOWS_TCP
						for target in selected
					):
						wx.MessageBox(
							_("Select at least one saved Linux connection to copy the local configuration."),
							_("No Linux connection selected"),
							wx.OK | wx.ICON_WARNING,
							dialog,
						)
						select_all.SetFocus()
						continue
					return selected, configuration_mode
				wx.MessageBox(
					_("Select at least one target to remove components from.")
					if remove
					else _("Select at least one target to update."),
					_("No target selected"),
					wx.OK | wx.ICON_WARNING,
					dialog,
				)
				select_all.SetFocus()
			return None
		finally:
			dialog.Destroy()

	def _chooseInstallProfiles(self):
		return self._chooseComponentTargets(remove=False)

	def _chooseUninstallProfiles(self):
		return self._chooseComponentTargets(remove=True)

	def _onInstallServer(self, _event):
		selection = self._chooseInstallProfiles()
		if selection is None:
			return
		targets, configuration_mode = selection
		jobs = []
		immediate_results = []
		for profile in targets:
			if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
				jobs.append((profile, ""))
				continue
			password = self._passwordForProfile(profile)
			if profile.authentication == "password" and password is None:
				immediate_results.append(
					(
						profile,
						InstallResult(False, _("SSH password entry cancelled")),
					)
				)
				continue
			jobs.append((profile, password or ""))
		if not jobs:
			self._finishServerInstalls(immediate_results)
			return
		ui.message(_("Updating Neovim components on {count} targets").format(count=len(jobs)))
		package = os.path.join(self._packageDir, "resources", "server-user.tar.gz")
		local_plugin = os.path.join(self._packageDir, "resources", "neovim-plugin")
		starter_config = os.path.join(self._packageDir, "resources", "starter-init.lua")
		threading.Thread(
			target=self._runServerInstalls,
			args=(
				jobs,
				package,
				immediate_results,
				local_plugin,
				configuration_mode,
				starter_config,
			),
			daemon=True,
		).start()

	def _runServerInstalls(
		self,
		jobs,
		package,
		initial_results=None,
		local_plugin="",
		configuration_mode=CONFIGURATION_UNCHANGED,
		starter_config="",
	):
		results = list(initial_results or [])
		installer = SshUserInstaller()
		local_installer = LocalPluginInstaller()
		package_path = pathlib.Path(package)
		total = len(jobs) + len(results)
		completed = len(results)
		imported_config = b""
		if configuration_mode == CONFIGURATION_COPY_LOCAL:
			try:
				archive = LocalConfigArchiveBuilder().build(default_local_config_directory())
				diagnostics = archive.diagnostics
			except (OSError, ValueError) as error:
				archive = None
				diagnostics = str(error)
			if archive is None or not archive.success:
				failure = InstallResult(
					False,
					_("The local Windows Neovim configuration could not be prepared"),
					diagnostics,
				)
				for profile, _password in jobs:
					results.append((profile, failure))
					self._recordDiagnostic(
						"componentInstall",
						targetId=profile.identifier,
						targetKind=(profile.kind if isinstance(profile, ConnectionTarget) else "remoteSsh"),
						success=False,
						message=failure.message,
						diagnostics=failure.diagnostics,
						configurationInstalled=False,
						configurationMode=configuration_mode,
						configurationBackups=0,
					)
					completed += 1
					self._queueMainThread(
						self._reportServerInstallProgress,
						profile,
						failure,
						completed,
						total,
					)
				self._queueMainThread(self._finishServerInstalls, results)
				return
			imported_config = archive.payload
		for profile, password in jobs:
			try:
				if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
					result = local_installer.install(pathlib.Path(local_plugin))
					if result.success and configuration_mode == CONFIGURATION_STARTER:
						configuration = StarterConfigInstaller().install(pathlib.Path(starter_config))
						if configuration.success:
							result = InstallResult(
								True,
								"Local Neovim plugin and starter configuration installed",
								"\n".join(filter(None, (result.diagnostics, configuration.diagnostics))),
								configuration.configuration_path,
								configuration.backup_paths,
								CONFIGURATION_STARTER,
							)
						else:
							# Translators: A requested basic init.lua could not be installed safely.
							message = _("The basic Neovim configuration could not be installed")
							result = InstallResult(
								False,
								message,
								"\n".join(filter(None, (result.diagnostics, configuration.diagnostics))),
							)
				else:
					result = installer.install(
						profile.ssh_target,
						package_path,
						profile.port,
						profile.identity_file,
						password,
						self._askpassPath(),
						configuration_mode,
						imported_config,
					)
			except Exception as error:
				result = InstallResult(
					False,
					_("Unexpected installation error"),
					"{kind}: {message}".format(kind=type(error).__name__, message=error),
				)
			results.append((profile, result))
			self._recordDiagnostic(
				"componentInstall",
				targetId=profile.identifier,
				targetKind=(profile.kind if isinstance(profile, ConnectionTarget) else "remoteSsh"),
				success=result.success,
				message=result.message,
				diagnostics=result.diagnostics,
				configurationInstalled=bool(result.configuration_path),
				configurationMode=result.configuration_kind,
				configurationBackups=len(result.configuration_backups),
			)
			completed += 1
			self._queueMainThread(
				self._reportServerInstallProgress,
				profile,
				result,
				completed,
				total,
			)
		self._queueMainThread(self._finishServerInstalls, results)

	def _reportServerInstallProgress(self, profile, result, completed, total):
		name = self._installTargetSummary(profile)[0]
		if result.success:
			ui.message(
				_("{name} updated, {completed} of {total}").format(
					name=name,
					completed=completed,
					total=total,
				)
			)
		else:
			ui.message(
				_("{name} failed, {completed} of {total}").format(
					name=name,
					completed=completed,
					total=total,
				)
			)

	@staticmethod
	def _installResultSummary(results):
		successful = [(profile, result) for profile, result in results if result.success]
		failed = [(profile, result) for profile, result in results if not result.success]
		lines = [_("Neovim component update completed.")]
		lines.extend(("", _("Successful: {count}").format(count=len(successful))))
		lines.extend(
			_("- {name} ({target})").format(
				name=NvdaUiManager._installTargetSummary(profile)[0],
				target=NvdaUiManager._installTargetSummary(profile)[1],
			)
			for profile, _result in successful
		)
		for profile, result in successful:
			if not result.configuration_path:
				continue
			name = NvdaUiManager._installTargetSummary(profile)[0]
			if result.configuration_kind == CONFIGURATION_COPY_LOCAL:
				# Translators: Reports where the local Windows Neovim configuration was copied.
				lines.append(
					_("  {name} imported configuration: {path}").format(
						name=name,
						path=result.configuration_path,
					)
				)
			else:
				# Translators: Reports where the optional basic Neovim configuration was installed.
				lines.append(
					_("  {name} basic configuration: {path}").format(
						name=name,
						path=result.configuration_path,
					)
				)
			for backup in result.configuration_backups:
				# Translators: Reports a backup created before replacing an existing Neovim configuration.
				lines.append(_("  Existing configuration backup: {path}").format(path=backup))
		lines.extend(("", _("Failed: {count}").format(count=len(failed))))
		lines.extend(
			_("- {name} ({target}): {reason}").format(
				name=NvdaUiManager._installTargetSummary(profile)[0],
				target=NvdaUiManager._installTargetSummary(profile)[1],
				reason=result.message,
			)
			for profile, result in failed
		)
		if successful:
			lines.extend(("", _("Restart Neovim once on successfully updated targets.")))
		return "\n".join(lines)

	def _finishServerInstalls(self, results):
		import gui

		successful = len([result for _profile, result in results if result.success])
		failed = len(results) - successful
		if successful:
			self._settingsService.save()
		ui.message(
			_("Neovim component update completed: {successful} successful, {failed} failed").format(
				successful=successful, failed=failed
			)
		)
		dialog = gui.MessageDialog(
			gui.mainFrame,
			self._installResultSummary(results),
			_("Neovim component update results"),
		)
		dialog.Show()

	def _onRemoveComponents(self, _event):
		targets = self._chooseUninstallProfiles()
		if targets is None:
			return
		if not self._confirmComponentRemoval(targets):
			return
		jobs = []
		immediate_results = []
		for profile in targets:
			if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
				jobs.append((profile, ""))
				continue
			password = self._passwordForProfile(profile)
			if profile.authentication == "password" and password is None:
				immediate_results.append(
					(
						profile,
						InstallResult(False, _("SSH password entry cancelled")),
					)
				)
				continue
			jobs.append((profile, password or ""))
		if not jobs:
			self._finishComponentRemovals(immediate_results)
			return
		ui.message(_("Removing Neovim components from {count} targets").format(count=len(jobs)))
		threading.Thread(
			target=self._runComponentRemovals,
			args=(jobs, immediate_results),
			daemon=True,
		).start()

	@staticmethod
	def _confirmComponentRemoval(targets):
		import gui
		import wx

		# Translators: Confirmation shown after selecting targets for component removal.
		message = _(
			"Access Link will remove its installed Neovim plugin and, on Linux targets, its bridge.\n\n"
			"Neovim configuration and configuration backups will not be changed. If a configuration "
			"explicitly loads Access Link, for example through lazy.nvim, remove or disable that entry "
			"manually.\n\nSelected targets: {count}. Continue?"
		).format(count=len(targets))
		return (
			wx.MessageBox(
				message,
				# Translators: Title of the destructive component-removal confirmation.
				_("Confirm Neovim component removal"),
				wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
				gui.mainFrame,
			)
			== wx.YES
		)

	def _runComponentRemovals(self, jobs, initial_results=None):
		results = list(initial_results or [])
		installer = SshUserInstaller()
		local_installer = LocalPluginInstaller()
		total = len(jobs) + len(results)
		completed = len(results)
		for profile, password in jobs:
			try:
				if isinstance(profile, ConnectionTarget) and profile.kind == LOCAL_WINDOWS_TCP:
					result = local_installer.uninstall()
				else:
					result = installer.uninstall(
						profile.ssh_target,
						profile.port,
						profile.identity_file,
						password,
						self._askpassPath(),
					)
			except Exception as error:
				result = InstallResult(
					False,
					_("Unexpected removal error"),
					"{kind}: {message}".format(kind=type(error).__name__, message=error),
				)
			results.append((profile, result))
			self._recordDiagnostic(
				"componentRemoval",
				targetId=profile.identifier,
				targetKind=(profile.kind if isinstance(profile, ConnectionTarget) else "remoteSsh"),
				success=result.success,
				message=result.message,
				diagnostics=result.diagnostics,
			)
			completed += 1
			self._queueMainThread(
				self._reportComponentRemovalProgress,
				profile,
				result,
				completed,
				total,
			)
		self._queueMainThread(self._finishComponentRemovals, results)

	def _reportComponentRemovalProgress(self, profile, result, completed, total):
		name = self._installTargetSummary(profile)[0]
		if result.success:
			ui.message(
				_("{name} removed, {completed} of {total}").format(
					name=name,
					completed=completed,
					total=total,
				)
			)
		else:
			ui.message(
				_("{name} failed, {completed} of {total}").format(
					name=name,
					completed=completed,
					total=total,
				)
			)

	@staticmethod
	def _componentRemovalResultSummary(results):
		successful = [(profile, result) for profile, result in results if result.success]
		failed = [(profile, result) for profile, result in results if not result.success]
		lines = [_("Neovim component removal completed.")]
		lines.extend(("", _("Successful: {count}").format(count=len(successful))))
		lines.extend(
			_("- {name} ({target})").format(
				name=NvdaUiManager._installTargetSummary(profile)[0],
				target=NvdaUiManager._installTargetSummary(profile)[1],
			)
			for profile, _result in successful
		)
		lines.extend(("", _("Failed: {count}").format(count=len(failed))))
		lines.extend(
			_("- {name} ({target}): {reason}").format(
				name=NvdaUiManager._installTargetSummary(profile)[0],
				target=NvdaUiManager._installTargetSummary(profile)[1],
				reason=result.message,
			)
			for profile, result in failed
		)
		lines.extend(
			(
				"",
				_("Saved connection settings were preserved."),
				# Translators: Explains what removal deliberately leaves for the user to maintain.
				_(
					"Neovim configuration and configuration backups were not changed. Remove or disable "
					"any explicit Access Link plugin entry there if it is no longer needed."
				),
			)
		)
		return "\n".join(lines)

	def _finishComponentRemovals(self, results):
		import gui

		successful = len([result for _profile, result in results if result.success])
		failed = len(results) - successful
		ui.message(
			_("Neovim component removal completed: {successful} successful, {failed} failed").format(
				successful=successful, failed=failed
			)
		)
		dialog = gui.MessageDialog(
			gui.mainFrame,
			self._componentRemovalResultSummary(results),
			_("Neovim component removal results"),
		)
		dialog.Show()
