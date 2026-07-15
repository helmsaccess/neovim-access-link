# ADR-0002: NVDA-API-Grenzen für den ersten Beta-Stand

## Status

Angenommen für Beta-Build 0.89.1. Vor jeder Anpassung der unterstützten
NVDA-Hauptversion erneut zu prüfen.

## Grundsatz

Das Add-on verwendet die üblichen öffentlichen Add-on-Einstiegspunkte:
`globalPluginHandler.GlobalPlugin`, ein anwendungsspezifisches AppModule,
`scriptHandler.script`, `addonHandler.getCodeAddon()`, NVDA-Ereignishandler,
`queueHandler`, `ui.message`, Speech/Braille-Objekte und den nativen
Konfigurationsprofil-Stack. Es verändert keine NVDA-Quelldatei und ersetzt
keine globale NVDA-Funktion.

Für drei eng begrenzte Aufgaben bietet NVDA 2026.1.1 jedoch keine gleichwertige,
ausdrücklich stabile Add-on-API. Diese Ausnahmen dürfen nicht stillschweigend
ausgeweitet werden.

## Ausnahme 1: `Terminal._reportNewLines`

Die Braille-/LiveText-Overlayklasse überschreibt die geschützte Methode
`_reportNewLines`, um native Terminalfragmente ausschließlich für die
authentifizierte und fokussierte Neovim-Sitzung zu unterdrücken. Ein öffentlicher
Hook zwischen Terminal-Diff und nativer LiveText-Ausgabe existiert nicht.

- Risiko: Signatur oder Aufrufreihenfolge kann sich mit NVDA ändern.
- Begrenzung: Bei fehlender Sitzung, Fehler, Fokusverlust oder Deaktivierung
  wird sofort `super()._reportNewLines` verwendet; das Verhalten ist fail-open.
- Ablöseplan: Für jede neue NVDA-Hauptversion Quellprüfung und Regressionstest;
  auf eine öffentliche Terminal-Ausgabesperre wechseln, sobald NVDA sie anbietet.

## Ausnahme 2: UIA-Runtime-ID über `NVDAObject.UIAElement`

Windows Terminal stellt keine vom Add-on kontrollierte dauerhafte Tab-ID bereit.
Für die ausschließlich laufzeitbezogene, niemals gespeicherte Tabzuordnung liest
das Add-on `cachedClassName` und `getRuntimeId()` vom zugrunde liegenden
`UIAElement`. Zum Erkennen geschlossener Tabs wird dasselbe Element zunächst
direkt geprüft und anschließend nach NVDAs eigenem UIA-Muster über eine
`RuntimeId`-Property-Condition im Teilbaum des weiterhin validierten
Fensterhandles gesucht. Die Werte werden nur nach Prüfung des Windows-Terminal-
AppModules, des Prozesses und der freigegebenen UIA-Klasse verwendet.

- Risiko: Form und Lebensdauer des UIA-Wrappers können sich ändern.
- Begrenzung: Fehlende oder ungültige Werte deaktivieren Zuordnung und
  Unterdrückung; COM-/UIA-Fehler gelten als unklar und lösen keine Bereinigung
  aus. Fenstertitel oder Terminaltext dienen nie als Ersatzheuristik.
- Ablöseplan: Einen späteren öffentlichen, stabilen Terminal-/Tab-Identifier
  bevorzugen und die Runtime-ID-Abhängigkeit entfernen.

## Ausnahme 3: Einbindung in NVDA-Einstellungs- und Werkzeugdialoge

Die Registrierung über `NVDASettingsDialog.categoryClasses`, der Zugriff auf
das Werkzeugmenü und `gui.runScriptModalDialog` entsprechen verbreiteter
NVDA-Add-on-Praxis, sind aber nicht als eigenständige, langfristig stabile
Erweiterungsschnittstellen zugesagt.

- Risiko: Menü- oder Dialogstruktur kann sich zwischen NVDA-Hauptversionen
  ändern; die Funktion könnte dann nicht angeboten werden.
- Begrenzung: Registrierung und Entfernung sind symmetrisch und
  ausnahmegesichert. Netzwerk- und Installationsarbeit läuft nie im Dialog-
  oder NVDA-Hauptthread. Ein GUI-Fehler darf die Terminalausgabe nicht sperren.
- Ablöseplan: Offizielle registrierbare Settings-/Tools-Erweiterungspunkte
  übernehmen, sobald NVDA sie bereitstellt; bis dahin pro Zielversion mit dem
  echten NVDA-Paket und dem extrahierten gebauten Add-on testen.

## Nicht als Ausnahme zugelassen

Globale Eingabe-Hooks, Monkeypatches, Terminal-Screen-Scraping, dauerhafte
UIA-IDs, private Netzwerkschnittstellen und blockierende Arbeit im NVDA-
Hauptthread bleiben ausgeschlossen. F12 wird vom nur für Windows Terminal
geladenen AppModule beobachtet, aber weder als NVDA-Skript gebunden noch
synthetisch weitergereicht.
