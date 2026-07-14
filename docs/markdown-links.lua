-- Pandoc --file-scope prefixes headings with the source path. Rewrite links
-- between the ordered German Markdown sources to their scoped H1 targets in
-- the combined HTML documentation.
local targets = {
  ["manual/README.md"] = "#docs__de__manual__readmemd__neovim-access-link-handbuch",
  ["development/README.md"] = "#docs__de__development__readmemd__entwicklungsdokumentation",
  ["../development/README.md"] = "#docs__de__development__readmemd__entwicklungsdokumentation",
  ["../README.md"] = "#docs__de__readmemd__deutsche-dokumentation",

  ["settings.md"] = "#docs__de__manual__settingsmd__handbuch-einstellungen-des-nvda-add-ons",
  ["communication.md"] = "#docs__de__manual__communicationmd__handbuch-kommunikation-verbindung-und-sitzungszuordnung",
  ["../manual/communication.md"] = "#docs__de__manual__communicationmd__handbuch-kommunikation-verbindung-und-sitzungszuordnung",
  ["ssh-and-tmux.md"] = "#docs__de__manual__ssh-and-tmuxmd__betrieb-mit-ssh-tmux-und-neovim",
  ["menus-and-completion.md"] = "#docs__de__manual__menus-and-completionmd__menüs-und-autovervollständigung",
  ["terminals-and-file-managers.md"] = "#docs__de__manual__terminals-and-file-managersmd__terminal-und-dateimanager",
  ["sounds.md"] = "#docs__de__manual__soundsmd__sounds-und-earcons",
  ["braille.md"] = "#docs__de__manual__braillemd__braille-unterstützung",
  ["troubleshooting.md"] = "#docs__de__manual__troubleshootingmd__fehlerdiagnose-und-diagnosebericht",

  ["current-status.md"] = "#docs__de__development__current-statusmd__aktueller-status",
  ["compatibility.md"] = "#docs__de__development__compatibilitymd__kompatibilität",
  ["accessibility.md"] = "#docs__de__development__accessibilitymd__funktionsmatrix",
  ["plan.md"] = "#docs__de__development__planmd__plan",
  ["architecture.md"] = "#docs__de__development__architecturemd__architektur",
  ["adr/0001-neovim-integration-point.md"] = "#docs__de__development__adr__0001-neovim-integration-pointmd__adr-0001-hybrider-neovim-andockpunkt",
  ["adr/0002-nvda-api-boundaries.md"] = "#docs__de__development__adr__0002-nvda-api-boundariesmd__adr-0002-nvda-api-grenzen-für-den-ersten-beta-stand",
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
  ["../../../AGENTS.md"] = "#agentsmd__repository-instructions-for-coding-agents",
}

function Link(link)
  local path = link.target:match("^([^#]+)") or link.target
  local replacement = targets[path]
  if replacement then
    link.target = replacement
    return link
  end
end
