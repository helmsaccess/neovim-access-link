-- Pandoc --file-scope prefixes headings with the source path. Rewrite links
-- between the ordered German Markdown sources to their scoped H1 targets in
-- the combined HTML documentation.
local targets = {
  ["manual/README.md"] = "#docs__de__manual__readmemd__neovim-access-link-handbuch",
  ["README.md"] = "neovim-access-link-handbook-de.html",
  ["quick-guide.md"] = "neovim-access-link-quick-guide-de.html",
  ["development/README.md"] = "#docs__de__development__readmemd__entwicklungsdokumentation",
  ["../development/README.md"] = "#docs__de__development__readmemd__entwicklungsdokumentation",
  ["../README.md"] = "#docs__de__readmemd__deutsche-dokumentation",

  ["basics.md"] = "#docs__de__manual__basicsmd__neovim--und-windows-terminal-grundlagen",
  ["commands.md"] = "#docs__de__manual__commandsmd__befehlsreferenz",
  ["settings.md"] = "#docs__de__manual__settingsmd__einstellungsreferenz",
  ["speech-exploration.md"] = "#docs__de__manual__speech-explorationmd__sprachexplorationsmodus",
  ["communication.md"] = "#docs__de__manual__communicationmd__verbindung-täglicher-einstieg-und-sitzungswechsel",
  ["../manual/communication.md"] = "#docs__de__manual__communicationmd__verbindung-täglicher-einstieg-und-sitzungswechsel",
  ["ssh-and-tmux.md"] = "#docs__de__manual__ssh-and-tmuxmd__ssh-und-tmux-verwenden",
  ["language-tools.md"] = "#docs__de__manual__language-toolsmd__lsp-autovervollständigung-und-linter-einrichten",
  ["example-configuration.md"] = "#docs__de__manual__example-configurationmd__kleine-python-konfiguration-mit-lazy-und-oil",
  ["menus-and-completion.md"] = "#docs__de__manual__menus-and-completionmd__menüs-completion-und-diagnosen",
  ["terminals-and-file-managers.md"] = "#docs__de__manual__terminals-and-file-managersmd__eingebettetes-terminal-und-dateimanager",
  ["sounds.md"] = "#docs__de__manual__soundsmd__sounds-und-earcons",
  ["braille.md"] = "#docs__de__manual__braillemd__braille-unterstützung",
  ["troubleshooting.md"] = "#docs__de__manual__troubleshootingmd__fehler-beheben-und-diagnosebericht-erstellen",
  ["../development/compatibility.md"] = "neovim-access-link-developer-documentation-de.html#docs__de__development__compatibilitymd__kompatibilität",

  ["current-status.md"] = "#docs__de__development__current-statusmd__aktueller-status",
  ["compatibility.md"] = "#docs__de__development__compatibilitymd__kompatibilität",
  ["accessibility.md"] = "#docs__de__development__accessibilitymd__funktionsmatrix",
  ["plan.md"] = "#docs__de__development__planmd__plan",
  ["architecture.md"] = "#docs__de__development__architecturemd__architektur",
  ["adr/0001-neovim-integration-point.md"] = "#docs__de__development__adr__0001-neovim-integration-pointmd__adr-0001-hybrider-neovim-andockpunkt",
  ["adr/0002-nvda-api-boundaries.md"] = "#docs__de__development__adr__0002-nvda-api-boundariesmd__adr-0002-nvda-api-grenzen-für-den-ersten-beta-stand",
  ["adr/0003-oil-confirmation-fallback.md"] = "#docs__de__development__adr__0003-oil-confirmation-fallbackmd__adr-0003-eng-begrenzter-fallback-für-oil-bestätigungen",
  ["adr/0004-nvda-lifetime-and-event-ownership.md"] = "#docs__de__development__adr__0004-nvda-lifetime-and-event-ownershipmd__adr-0004-nvda-lebensdauer-und-besitz-von-anwendungsevents",
  ["protocol.md"] = "#docs__de__development__protocolmd__protokoll-v2",
  ["security.md"] = "#docs__de__development__securitymd__sicherheit-und-datenschutz",
  ["latency.md"] = "#docs__de__development__latencymd__latenz",
  ["testing.md"] = "#docs__de__development__testingmd__teststrategie",
  ["release-and-build.md"] = "#docs__de__development__release-and-buildmd__release--versions--und-buildprozess",
  ["settings-reference.md"] = "#docs__de__development__settings-referencemd__add-on-einstellungen",
  ["component-installation.md"] = "#docs__de__development__component-installationmd__rootlose-installation-und-ssh-stdio-transport",
  ["nvda-2026.1-api-notes.md"] = "#docs__de__development__nvda-20261-api-notesmd__nvda-202611-api-untersuchung",
  ["changelog.md"] = "#docs__de__development__changelogmd__changelog",

  ["../../../nvda-addon/DEPENDENCIES.md"] = "#nvda-addon__dependenciesmd__gebündelte-abhängigkeiten",
}

function Link(link)
  local path = link.target:match("^([^#]+)") or link.target
  local replacement = targets[path]
  if replacement then
    link.target = replacement
    return link
  end
end
