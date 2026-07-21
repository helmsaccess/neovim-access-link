# Entwicklungsdokumentation

Diese Dokumentation erklärt, wie Neovim Access Link aufgebaut ist, wie eine
Änderung sicher entwickelt wird und welche Aussagen tatsächlich durch Code
oder Tests belegt sind. Die Bedienung des fertigen Add-ons steht im
[Anwenderhandbuch](../manual/README.md).

## Empfohlener Einstieg

Wer das Projekt noch nicht kennt, liest diese Seiten in der folgenden
Reihenfolge:

1. [Überblick für neue Entwickler](overview.md) – Grundidee, Datenfluss und
   Aufgabenteilung ohne Implementierungsdetails.
2. [Architektur](architecture.md) – Prozesse, Begriffe, Zuständigkeiten und der
   vollständige Lebenszyklus einer Verbindung.
3. [Repository-Struktur](repository-layout.md) – wo die zugehörigen Quellen und
   Tests liegen.
4. [Einstieg für Entwicklung und Tests](getting-started.md) – Voraussetzungen,
   erste Befehle und passende Prüfungen für typische Änderungen.
5. [Aktueller Status](current-status.md) – bestätigte Plattformen, Reifegrad
   und bekannte Grenzen des gegenwärtigen Stands.

Die ersten drei Dokumente erklären dauerhaft gültige Zusammenhänge. Der
aktuelle Status ist dagegen eine Momentaufnahme und darf nicht als
Architekturbeschreibung verwendet werden.

## Nach Aufgabe weiterlesen

### Verhalten oder Barrierefreiheit ändern

- [Funktions- und Accessibility-Matrix](accessibility.md)
- [Teststrategie](testing.md)
- [Kompatibilität](compatibility.md)
- [NVDA-2026.1-API-Prüfung](nvda-2026.1-api-notes.md)

### Verbindung, Installation oder Sicherheit ändern

- [Protokoll v2](protocol.md)
- [Komponenteninstallation und SSH-stdio](component-installation.md)
- [Sicherheit und Datenschutz](security.md)
- [Latenz](latency.md)

### Einstellungen, Übersetzungen oder Veröffentlichung ändern

- [Interne Einstellungsreferenz](settings-reference.md)
- [Lokalisierung mit gettext](localization.md)
- [Release-, Versions- und Buildprozess](release-and-build.md)
- [Gebündelte Abhängigkeiten](../../../nvda-addon/DEPENDENCIES.md)
- [Lizenzierung und Beiträge](licensing-and-contributions.md)

## Entscheidungen, Planung und Verlauf

Architekturentscheidungen erklären, warum eine dauerhafte Grenze gewählt
wurde. Sie sind keine Bedienungsanleitung und kein Ersatz für den aktuellen
Code.

- [ADR-0001: hybrider Neovim-Andockpunkt](adr/0001-neovim-integration-point.md)
- [ADR-0002: NVDA-API-Grenzen](adr/0002-nvda-api-boundaries.md)
- [ADR-0003: enger Oil-Bestätigungsfallback](adr/0003-oil-confirmation-fallback.md)
- [ADR-0004: NVDA-Lebensdauer und Besitz von Anwendungsevents](adr/0004-nvda-lifetime-and-event-ownership.md)
- [Aktiver Plan](plan.md)
- [Changelog](changelog.md)

## Welche Seite ist wofür maßgeblich?

- `overview.md` vermittelt das vereinfachte Grundmodell; für konkrete interne
  Grenzen ist die Architektur maßgeblich.
- `architecture.md` beschreibt aktuelle Komponenten, Verantwortlichkeiten und
  Abhängigkeitsgrenzen.
- `protocol.md` ist die Referenz für Nachrichten, Validierung und Steuerbefehle.
- `security.md` beschreibt Vertrauensgrenzen und Fail-open-Anforderungen.
- `testing.md` enthält reproduzierbare Nachweise und manuelle Prüfschritte.
- `current-status.md` nennt bestätigte Plattformen und noch offene Breite.
- `plan.md` enthält beabsichtigte Arbeit; eine Planung ist keine bereits
  implementierte Funktion.
- `changelog.md` bewahrt den zeitlichen Verlauf; ältere Einträge beschreiben
  nicht automatisch das heutige Verhalten.
- Datierte Qualitätsreviews dokumentieren Vergleichsbasis und Nachweise eines
  bestimmten Entwicklungsstands. Für später geändertes Verhalten sind
  Architektur, Status und Code maßgeblich.

Alle Aussagen sollen ihren Geltungsbereich benennen. „Windows Terminal“ darf
beispielsweise nicht pauschal mit „Tab“ gleichgesetzt werden: Der Code bindet
ein konkretes UI-Automation-`TermControl`, das je nach Layout einen Tabinhalt
oder ein Pane repräsentieren kann.

## Anhänge: datierte Qualitätsberichte

Die Berichte bewahren Vergleichsbasis, Messwerte und damalige Empfehlungen.
Sie stehen am Ende der gebauten Entwicklerdokumentation und ersetzen weder die
aktuelle Architektur noch Status, Plan oder Code.

- [Anhang A: Qualitätsreview der Global-Plugin-Verschlankung vom 19. Juli 2026, 20:04:03 CEST](quality-review-global-plugin-slimming-2026-07-19.md) –
  Zwischenreview des Featurebranches gegen `main`, einschließlich behobener
  Regressionen und damaliger Restrisiken.
- [Anhang B: Codeanalyse des abgeschlossenen Featurestands gegenüber `v0.94.2` vom 21. Juli 2026, 01:11:58 CEST](code-analysis-global-plugin-slimming-v0.94.2-2026-07-21.md) –
  quantitative und qualitative Abschlussbewertung von Testbarkeit,
  Wartbarkeit, Robustheit und zusätzlicher Strukturkomplexität.
