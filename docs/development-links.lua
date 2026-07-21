-- Rewrite links between the ordered German developer sources to their scoped
-- H1 targets. Links into the separately built handbook stay external.
local targets = {
  ["overview.md"] = "#docs__de__development__overviewmd__überblick-für-neue-entwickler",
  ["getting-started.md"] = "#docs__de__development__getting-startedmd__einstieg-für-entwicklung-und-tests",
  ["current-status.md"] = "#docs__de__development__current-statusmd__aktueller-status",
  ["compatibility.md"] = "#docs__de__development__compatibilitymd__kompatibilität",
  ["repository-layout.md"] = "#docs__de__development__repository-layoutmd__repository-struktur",
  ["architecture.md"] = "#docs__de__development__architecturemd__architektur",
  ["localization.md"] = "#docs__de__development__localizationmd__lokalisierung-mit-gettext",
  ["adr/0001-neovim-integration-point.md"] = "#docs__de__development__adr__0001-neovim-integration-pointmd__adr-0001-hybrider-neovim-andockpunkt",
  ["adr/0002-nvda-api-boundaries.md"] = "#docs__de__development__adr__0002-nvda-api-boundariesmd__adr-0002-nvda-api-grenzen-für-den-ersten-beta-stand",
  ["adr/0003-oil-confirmation-fallback.md"] = "#docs__de__development__adr__0003-oil-confirmation-fallbackmd__adr-0003-eng-begrenzter-fallback-für-oil-bestätigungen",
  ["adr/0004-nvda-lifetime-and-event-ownership.md"] = "#docs__de__development__adr__0004-nvda-lifetime-and-event-ownershipmd__adr-0004-nvda-lebensdauer-und-besitz-von-anwendungsevents",
  ["security.md"] = "#docs__de__development__securitymd__sicherheit-und-datenschutz",
  ["latency.md"] = "#docs__de__development__latencymd__latenz",
  ["protocol.md"] = "#docs__de__development__protocolmd__protokoll-v2",
  ["settings-reference.md"] = "#docs__de__development__settings-referencemd__add-on-einstellungen",
  ["component-installation.md"] = "#docs__de__development__component-installationmd__rootlose-installation-und-ssh-stdio-transport",
  ["testing.md"] = "#docs__de__development__testingmd__teststrategie",
  ["accessibility.md"] = "#docs__de__development__accessibilitymd__funktionsmatrix",
  ["release-and-build.md"] = "#docs__de__development__release-and-buildmd__release--versions--und-buildprozess",
  ["nvda-2026.1-api-notes.md"] = "#docs__de__development__nvda-20261-api-notesmd__nvda-202611-api-untersuchung",
  ["quality-review-global-plugin-slimming-2026-07-19.md"] = "#docs__de__development__quality-review-global-plugin-slimming-2026-07-19md__anhang-a-qualitätsreview-der-global-plugin-verschlankung",
  ["code-analysis-global-plugin-slimming-v0.94.2-2026-07-21.md"] = "#docs__de__development__code-analysis-global-plugin-slimming-v0942-2026-07-21md__anhang-b-codeanalyse-von-featureglobal-plugin-slimming-gegenüber-v0942",
  ["licensing-and-contributions.md"] = "#docs__de__development__licensing-and-contributionsmd__lizenzierung-und-beiträge",
  ["../../../nvda-addon/DEPENDENCIES.md"] = "#nvda-addon__dependenciesmd__gebündelte-abhängigkeiten",
  ["plan.md"] = "#docs__de__development__planmd__aktiver-plan",
  ["changelog.md"] = "#docs__de__development__changelogmd__changelog",

  ["../manual/README.md"] = "neovim-access-link-handbook-de.html",
  ["../manual/communication.md"] = "neovim-access-link-handbook-de.html#docs__de__manual__communicationmd__handbuch-kommunikation-verbindung-und-sitzungszuordnung",
}

function Link(link)
  local path = link.target:match("^([^#]+)") or link.target
  local replacement = targets[path]
  if replacement then
    link.target = replacement
    return link
  end
end
