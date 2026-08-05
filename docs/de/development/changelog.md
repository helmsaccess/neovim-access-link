# Changelog

Dieses Changelog fasst abgeschlossene Änderungen nach Produktversion zusammen.
Die [detaillierte Historie](changelog-history.md) bewahrt frühere Entwicklungs-
und Testbuild-Einträge bis zum 5. August 2026.

## Unveröffentlicht

- Beginnt die Entwicklungslinie 0.97.0 nach dem Beta-Pre-Release 0.96.0.
- Ergänzt LSP-Parameteransagen im Insert-Modus sowie gehaltene, rein lesende
  Ansichten für Signaturen, Parameter und Diagnosen mit korrelierter Sprache
  und Braille.
- Härtet native Completion, `nvim-cmp` und `blink.cmp`, einschließlich
  Dokumentationsauflösung, Menüklängen und dem Zustand ohne ausgewählten
  Kandidaten.
- Vereinheitlicht Diagnosen aus LSP, `nvim-lint`, ALE und `none-ls.nvim`,
  erweitert Navigationsbefehle und ergänzt getrennte Fehler-, Warn- und
  Leerbestätigungsklänge.
- Behebt Linux-Sitzungserkennung mit abweichenden Laufzeitumgebungen und ohne
  `XDG_RUNTIME_DIR` sowie Fokus- und Merkpfade nach der optionalen
  F12-Rückfrage.
- Trennt sichere, SSH- und Socket-Prüfungen in unabhängige Testphasen und
  erweitert die reproduzierbaren Completion-, LSP-, Linter- und geführten
  Praxistests.
- Ordnet Quick Guide und Handbuch nach Leseraufgaben neu. Eine echte, getestete
  Lua-Beispielkonfiguration erzeugt identische Codeblöcke für GitHub und die
  deutschen und englischen HTML-Handbücher.
- Präzisiert nach erneutem Architekturaudit die verbleibende prozessweite
  Rolle des Global Plugins, ohne den AppModule-eigenen Ereignispfad zu
  verbreitern.
- Ordnet die Entwicklerdokumentation nach Einstieg, aktuellen Erklärungen,
  Aufgaben, Referenzen und Entscheidungen neu, entfernt veraltete
  Transportaussagen und ergänzt einen eigenen CI-Build mit automatischer
  Strukturprüfung der deutschen und englischen Fassungen.

## 0.96.0

- Ergänzt strukturierte Braillezeilen, Cursor-Routing, Standardnavigation und
  einen pro Sitzung gespeicherten Braille-Explorationsmodus.
- Macht Neovims eingebaute `z=`-Rechtschreibvorschläge über Sprache,
  Braille und kontextbezogene NVDA-Befehle zugänglich.
- Gleicht Rechtschreibfeedback an NVDAs Dokumentformatierung an und stabilisiert
  Brailleausschnitte bei Fokus-, Sitzungs- und Textwechseln.

## 0.95.2

- Führt den Sprachexplorationsmodus für Zeichen, Wörter und Zeilen ein, ohne
  den echten Neovim-Cursor zu bewegen.
- Ergänzt Ursprungsklänge und getrennte Detailoptionen für normale Navigation
  und Explorationsabschluss.

## 0.95.1

- Verschlankt das Global Plugin zu einer Kompositionswurzel mit ausgelagerten
  Diensten für Fokus, Zuordnung, Editorzustand, Verbindungen, Einstellungen,
  Braille und Laufzeit.
- Erhält lokale und SSH-Sitzungen über mehrere Windows-Terminal-Fenster, Tabs
  und Panes einschließlich Zwischenablage und Komponentenverwaltung.

## 0.95.0 (Beta)

- Verlegt Windows-Terminal-Ereignisse, Overlayauswahl, `nextHandler` und frei
  belegbare Terminalbefehle in das AppModule.
- Begrenzt F12 auf die konkrete AppModule- und `TermControl`-Identität und
  verhindert ein eingefügtes `<F12>` bei einer Zuordnung im Insert-Modus.
- Verwendet NVDAs Windows-Bindings und Stilkonventionen im NVDA-seitigen Code.

## 0.94.2

- Strukturiert Anwender- und Entwicklerdokumentation von Grundbegriffen bis zu
  Architektur, aktuellem Status, Plan und Verlauf.
- Gleicht UI-Bezeichnungen mit Gettext-Katalog und NVDA-Quellcode ab und
  beschreibt Prüfung und Support als risikobasierten Best-Effort-Prozess.

## 0.94.1

- Liefert den vollständigen deutschen Gettext-Katalog samt reproduzierbaren
  Katalog-, MO- und Paketprüfungen aus.

## 0.94.0 (Vorabversion)

- Vereinheitlicht Produkt-ID, Paketnamen, Konfigurationsabschnitt und
  Artefaktpräfix unter `NeovimAccessLink`.

## 0.93.0 (Vorabversion)

- Härtet Terminal- und Bufferwechsel, strukturierte Kommandozeilen- und
  Prozessmeldungen sowie Fenster- und Tab-Kontextausgabe.
- Korrigiert die erneute F12-Zuordnung von einer beendeten lokalen zu einer
  SSH-Neovim-Sitzung.

## 0.92.0 (Beta-Vorabveröffentlichung)

- Ergänzt einstellbare Fokusausgabe, control-spezifische
  Windows-Terminal-Abschottung und ausdrückliche Zwischenablagebefehle für
  lokale und SSH-Verbindungen.

## 0.91.0 (Beta-Veröffentlichung)

- Führt control-spezifische Windows-Terminal-Zuordnung mit fail-open
  Fokuswechseln und einmaliger F12-Autorisierung ein.
- Bestätigt lokale und entfernte Verbindungen in mehreren Tabs und geteilten
  Panes praktisch.

## 0.90.0 (Beta-Veröffentlichung)

- Ergänzt die praktisch bestätigte Fokus-Kontextansage mit Datei, Modus und
  konfiguriertem Verbindungsnamen.

## 0.89.35 (Beta-Veröffentlichung)

- Härtet Sitzungsregistrierung und Windows-Terminal-Bindungen für lokale und
  entfernte Neovim-Sitzungen.
- Übernimmt Neovims externe UI erst nach authentifizierter Registrierung und
  gibt sie bei Fehlern fail-open an die native TUI zurück.
