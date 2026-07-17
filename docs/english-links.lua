local targets = {
  ["settings.md"] = "#docs__en__manual__settingsmd__manual-add-on-settings",
  ["communication.md"] = "#docs__en__manual__communicationmd__manual-communication-connections-and-session-binding",
  ["ssh-and-tmux.md"] = "#docs__en__manual__ssh-and-tmuxmd__using-ssh-tmux-and-neovim",
  ["menus-and-completion.md"] = "#docs__en__manual__menus-and-completionmd__menus-and-completion",
  ["terminals-and-file-managers.md"] = "#docs__en__manual__terminals-and-file-managersmd__embedded-terminal-and-file-managers",
  ["sounds.md"] = "#docs__en__manual__soundsmd__sounds-and-earcons",
  ["braille.md"] = "#docs__en__manual__braillemd__braille-support",
  ["troubleshooting.md"] = "#docs__en__manual__troubleshootingmd__troubleshooting-and-diagnostic-report",

  ["getting-started.md"] = "#docs__en__development__getting-startedmd__development-and-test-onboarding",
  ["current-status.md"] = "#docs__en__development__current-statusmd__current-status",
  ["compatibility.md"] = "#docs__en__development__compatibilitymd__compatibility",
  ["repository-layout.md"] = "#docs__en__development__repository-layoutmd__repository-layout",
  ["architecture.md"] = "#docs__en__development__architecturemd__architecture",
  ["adr/0001-neovim-integration-point.md"] = "#docs__en__development__adr__0001-neovim-integration-pointmd__adr-0001-hybrid-neovim-integration-point",
  ["adr/0002-nvda-api-boundaries.md"] = "#docs__en__development__adr__0002-nvda-api-boundariesmd__adr-0002-nvda-api-boundaries-for-the-first-beta",
  ["adr/0003-oil-confirmation-fallback.md"] = "#docs__en__development__adr__0003-oil-confirmation-fallbackmd__adr-0003-narrow-fallback-for-oil-confirmations",
  ["security.md"] = "#docs__en__development__securitymd__security-and-privacy",
  ["latency.md"] = "#docs__en__development__latencymd__latency",
  ["protocol.md"] = "#docs__en__development__protocolmd__protocol-v2",
  ["settings-reference.md"] = "#docs__en__development__settings-referencemd__add-on-settings-reference",
  ["component-installation.md"] = "#docs__en__development__component-installationmd__rootless-component-installation-and-ssh-stdio",
  ["testing.md"] = "#docs__en__development__testingmd__test-strategy",
  ["accessibility.md"] = "#docs__en__development__accessibilitymd__feature-and-accessibility-matrix",
  ["release-and-build.md"] = "#docs__en__development__release-and-buildmd__release-version-and-build-process",
  ["nvda-2026.1-api-notes.md"] = "#docs__en__development__nvda-20261-api-notesmd__nvda-202611-api-review",
  ["licensing-and-contributions.md"] = "#docs__en__development__licensing-and-contributionsmd__licensing-and-contributions",
  ["dependencies.md"] = "#docs__en__development__dependenciesmd__bundled-dependencies",
  ["plan.md"] = "#docs__en__development__planmd__active-plan",
  ["changelog.md"] = "#docs__en__development__changelogmd__changelog",
}

function Link(link)
  local path = link.target:match("^([^#]+)") or link.target
  local replacement = targets[path]
  if replacement then
    link.target = replacement
    return link
  end
end
