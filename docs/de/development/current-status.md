# Aktueller Status

Stand: 5. August 2026. Der Quellstand gehört zur Entwicklungslinie 0.97.0;
die genaue Entwicklungsbuildnummer und Git-Metadaten erzeugt `buildVars.py`.
Der aktuell veröffentlichte Beta-Pre-Release ist 0.96.0. Das Projekt leitet aus
Testumfang oder Funktionsmenge keine höhere Stabilitätseinstufung ab.

Diese Seite ist die kompakte Momentaufnahme des implementierten und geprüften
Stands. [Architektur](architecture.md) und
[Funktionsmatrix](accessibility.md) erklären Details; das
[Changelog](changelog.md) beschreibt abgeschlossene Änderungen und der
[Plan](plan.md) künftige Arbeit.

## Referenzumgebung

Der hauptsächliche praktische Pfad wurde mit Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x, OpenSSH für Windows 9.5p2, Rocky Linux 10.2 und
Neovim 0.10.1 beziehungsweise 0.12.3 geprüft. Lokales Windows-Neovim,
Linux-Neovim über SSH und tmux innerhalb einer SSH-Sitzung sind abgedeckt.
Die vollständigen Plattform- und Versionsgrenzen stehen in
[Kompatibilität](compatibility.md).

## Implementierter Gesamtpfad

### Installation, Verbindung und Besitzgrenzen

- Das `.nvda-addon` enthält NVDA-Integration, Neovim-Plugin und ein rootloses
  Linux-Benutzerpaket mit Bridge, Protokoll und Installer. Der Werkzeugdialog
  installiert, aktualisiert oder entfernt lokale und gespeicherte SSH-Ziele.
- Lokale Sitzungen verwenden dynamisches, nur an `127.0.0.1` gebundenes TCP;
  entfernte Sitzungen verwenden SSH-stdin/stdout und einen privaten
  Unix-RPC-Socket. Sitzungen werden aus kurzlebigen JSON-Dateien erkannt, nicht
  aus der Windows-Registry.
- Ein physischer F12-Druck ordnet die laufende Neovim-Instanz dem exakt
  fokussierten Windows-Terminal-Control zu. Mehrere Fenster, Tabs und Panes
  halten unabhängige lokale, entfernte oder normale Shell-Sitzungen.
- Authentifizierung, Sequenzen, Heartbeats, Resync und Fokuskorrelation
  begrenzen den dauerhaften Pfad. Trennung, ungültiger Zustand oder unsichere
  Fokusidentität geben NVDAs natives Terminalverhalten fail-open frei.
- Windows-Terminal-Ereignisse und `nextHandler` gehören dem AppModule.
  Getrennte Dienste besitzen Fokus, Sitzungszuordnung, Verbindungen,
  Editorzustand, Einstellungen, Präsentation und Laufzeit. Das Global Plugin
  bleibt der prozessweite NVDA-Rand und die Kompositionswurzel; der aktuelle
  Schnitt ist in [Architektur](architecture.md) und
  [Anhang C](global-plugin-appmodule-audit-2026-08-04.md) dokumentiert.

### Editor und Ausgabe

Der semantische Pfad verarbeitet Normal-, Insert-, Replace-, Visual-, Select-,
Operator-Pending-, Befehlszeilen- und Terminalmodi. Er deckt Navigation,
Eingabe, Löschen, Ersetzen, Auswahl, Suche, Folds, Buffer-, Fenster- und
Tabwechsel sowie strukturierte Neovim-Meldungen ab.

- Sprache und Sounds melden Modus, Zeichen, Wörter, Zeilen, Einrückung,
  Grenzen und konfigurierbaren Fokuskontext.
- Der Sprachexplorationsmodus liest Zeichen, Wörter und Zeilen, ohne den
  echten Cursor zu bewegen. Strukturierte Braillezeilen unterstützen Routing,
  Standardnavigation, wiederholte Routingaktionen und einen pro Sitzung
  gespeicherten Braille-Explorationsmodus.
- Neovims eingebaute Completion, `nvim-cmp` und `blink.cmp` liefern Auswahl,
  Typ, Quelle und verfügbare Dokumentation. LSP-Hover, Signaturhilfe,
  automatische aktive Parameter und gehaltene Parameteransichten sind
  korreliert und bewegen den Editorcursor nicht.
- Diagnosen aus `vim.diagnostic` lassen sich nach aktueller, vorheriger,
  nächster, erster und letzter Position lesen. Gehaltene Diagnoseansichten,
  Fehler-, Warn- und Leerbestätigungsklänge verwenden denselben validierten
  Datenpfad.
- Neovims native `z=`-Vorschläge sind mit Sprache, Braille und kontextbezogenen
  NVDA-Befehlen zugänglich. Rechtschreibfeedback folgt NVDAs getrennten
  Dokumentformatierungsoptionen.

### Entwicklungswerkzeuge, Terminal und Dateien

- LSP-Daten und Diagnosen bleiben providerneutral. Automatisierte Verträge
  bestehen für native LSP-Completion, `nvim-cmp`, `blink.cmp`, `nvim-lint`,
  ALE und `none-ls.nvim`; Benutzer installieren die jeweiligen externen
  Sprachserver und Linter selbst.
- Direkte Eingabe in einem Neovim-Terminalbuffer verwendet natives
  Terminal-Passthrough. Terminal-Normalmodus, Kommandozeilenrückkehr,
  Prozessende und Bufferwechsel bleiben strukturiert.
- Oil, netrw, mini.files, nvim-tree und Neo-tree besitzen normalisierte
  Adapter und automatisierte Grundabläufe. Oil ist der einzige unter
  Windows/NVDA praktisch geprüfte Dateimanager.
- Vier frei belegbare Befehle übertragen Visual-Auswahl, Register 0 oder
  Windows-Zwischenablage ausdrücklich und korreliert. Es gibt keine
  automatische Zwischenablagesynchronisation.

### Lokalisierung und Dokumentation

Englisch ist die UI-Quellsprache; der vollständige deutsche Gettext-Katalog
wird geprüft und mitgebaut. Quick Guide, Handbuch, Entwicklerdokumentation und
geführter Praxistest-Leitfaden entstehen in Deutsch und Englisch als acht
geprüfte HTML-Dateien. Die kopierbare Neovim-Beispielkonfiguration stammt aus
einer echten getesteten Lua-Datei und wird identisch in beide Handbücher
synchronisiert.

## Prüfnachweis

Automatisierte Suiten prüfen Protokoll und Begrenzungen, Bridge, lokale und
SSH-Clients, mehrere Instanzen, Fokus und Fail-open-Verhalten, Editor- und
Präsentationsplanung, Lua mit echten headless-Neovim-Prozessen, Paketinhalt,
Lokalisierung sowie Dokumentationslinks. Gepinnte Matrizen decken Neovim
0.10.1 und 0.12.3 sowie reale Completion-, LSP-, Diagnose- und Linterpfade ab.
Listenerfreie, SSH- und echte Sockettests laufen getrennt. Einzelheiten und
Befehle stehen in [Teststrategie](testing.md).

Praktisch bestätigt wurden insbesondere:

- Installation und Aktualisierung lokaler und entfernter Komponenten;
- parallele lokale und SSH-Sitzungen in mehreren Fenstern, Tabs und Panes;
- Fokuswechsel zwischen verbundenem Neovim und normalen Shell-Controls;
- Navigation, Sprachexploration, Modus-, Buffer- und Terminalwechsel;
- Braille-Routing, beide Braillemodi und Rechtschreibvorschläge mit einer
  Papenmeier BRAILLEX EL 80c;
- alle vier Zwischenablagepfade lokal und über SSH sowie Oil-Navigation,
  Umbenennung und Bestätigungen.

Die Prüfung ist risikoorientiert und nach bestem Wissen, nicht vollständig.
Automatisierte und praktische Referenzabläufe ersetzen keine Abnahme jeder
Kombination aus NVDA, Braillehardware, Neovim, Plugins und Benutzerdaten.

## Bekannte Grenzen

- Windows Terminal ist das einzige unterstützte Frontend. Andere Terminals
  und grafische Neovim-Oberflächen besitzen keinen freigegebenen Adapter.
- Unter Windows wird das normale `%LOCALAPPDATA%\nvim-data`-Layout erwartet;
  portable Installationen und getrennte Datenpfade über `NVIM_APPNAME` sind
  nicht freigegeben.
- Nur Oil ist als Dateimanager praktisch unter Windows/NVDA bestätigt. Die
  anderen Adapter sind automatisiert, nicht praktisch freigegeben.
- Der Braille-Praxistest belegt eine Hardware- und Treiberkombination, nicht
  jede Anzeige, Übersetzungstabelle oder Eingabebelegung.
- Für externe Completion-Plugins, Sprachserver und Linter gilt der jeweils
  dokumentierte öffentliche Vertrag; eine vollständige Plugin- und
  Versionsmatrix ist nicht zugesagt.

## Weiterführende Referenzen

- [Kompatibilität](compatibility.md) für Plattformen, Versionen und Prüftiefe;
- [Funktionsmatrix](accessibility.md) für einzelne zugängliche Abläufe;
- [Teststrategie](testing.md) und
  [geführte Praxistests](human-testing.md) für Nachweise;
- [Changelog](changelog.md) für abgeschlossene und
  [Plan](plan.md) für beabsichtigte Arbeit.
