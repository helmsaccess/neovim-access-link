# Funktions- und Accessibility-Matrix

Diese Referenz ordnet die implementierten zugänglichen Abläufe ihren
semantischen Quellen und dem vorhandenen Prüfnachweis zu. „Automatisiert“
bedeutet nicht, dass jede reale Kombination aus NVDA, Neovim, Plugins und
Braillehardware praktisch geprüft wurde. Die konkrete Referenzumgebung und
bekannten Grenzen stehen in [Kompatibilität](compatibility.md).

## Editor und Navigation

| Bereich | Semantische Quelle und Ausgabe | Nachweis |
|---|---|---|
| Modi und Fokus | `ModeChanged`, `nvim_get_mode()` und korrelierter Fokuskontext liefern Sprache oder Klänge für Normal, Insert, Replace, Visual, Select, Operator-Pending, Befehlszeile und Terminal. | Automatisiert; Kernabläufe praktisch unter Windows/NVDA. |
| Zeichen, Wörter und Zeilen | Cursorereignisse, UTF-8-sichere Positionen und Zustandsdifferenzen liefern Zeichen-, Wort- und Zeilenansagen sowie konfigurierbare Details am Cursor. | Automatisiert; Navigation und Detailkombinationen praktisch geprüft. |
| Sprachexploration | Kontextbezogene `NVDA+h/j/k/l`-Gesten lesen Zeichen, Wörter oder Zeilen an einer virtuellen Position, ohne den echten Cursor zu bewegen. Beim Loslassen gelten eigene Detailoptionen. | Protokoll-, Lua-, Controller-, AppModule- und Pakettests; Grundpfade praktisch geprüft. |
| Bearbeitung und Auswahl | Text-, Cursor- und Auswahlereignisse beschreiben Eingabe, Löschen, Ersetzen sowie Visual-Zeichen-, -Zeilen- und -Blockauswahl. | Unit-, Protokoll- und echte Neovim-Tests; Kernpfade praktisch geprüft. |
| Suche und Struktur | Öffentliche Neovim-Zustände beschreiben Suche, Matching Pairs, Folds, Marks, Register und Makros. | Echte TUI- und Präsentationstests. |
| Buffer, Fenster und Tabs | `BufEnter`, `WinEnter` und `TabEnter` liefern getrennte Kontext- und Statuswechsel. | Echte TUI- und Präsentationstests; praktische Mehrfenster- und Tabwechsel. |

Zeilen- und Wortnavigation besitzen eigene Einstellungen dafür, ob zusätzlich
das aktuelle Wort beziehungsweise Cursorzeichen ausgegeben wird. Die
Sprachexploration verwendet getrennte Einstellungen für ihre Abschlussansage.

## Meldungen, Menüs und Entwicklungswerkzeuge

| Bereich | Semantische Quelle und Ausgabe | Nachweis |
|---|---|---|
| Befehlszeile und Meldungen | Neovims externe UI-Ereignisse liefern Befehlszeile, Cursorposition, Meldungen und bestätigte Rückkehr in den vorherigen Modus. Sprache, Braille und Klänge bleiben getrennt planbar. | Paket-, Präsentations-, RPC- und echte TUI-Tests; seltene Pager-Varianten bleiben begrenzt. |
| Completion | Neovims Completion, `nvim-cmp` und `blink.cmp` liefern Auswahl, Typ, Quelle und verfügbare Dokumentation. | Listenerfreie Tests auf Neovim 0.10.1 und 0.12.3 sowie reale Modulverträge; erneute praktische Abnahme einzelner externer Plugins bleibt offen. |
| LSP-Kontext | Hover, Signaturhilfe, aktiver Parameter und gehaltene Funktionsansicht verwenden öffentliche LSP-Antworten mit Anfrage- und Editoridentität. | Parser-, Race-, Mehrclient-, echte LSP- und Pakettests; gehaltene Ansicht praktisch noch nicht vollständig abgenommen. |
| Diagnosen | `vim.diagnostic` ist die providerneutrale Grenze für Meldung, Bereich, Schwere und Navigation. Gezieltes Betreten von Fehlern oder Warnungen kann Klänge auslösen. | Automatisierte Verträge mit LSP, `nvim-lint`, ALE und `none-ls.nvim`; praktische Windows/NVDA-Breite bleibt begrenzt. |
| Rechtschreibung | Neovims `spell` und die native `z=`-Liste liefern Fehlerstatus und nummerierte Vorschläge. Das Add-on entfernt Nummern aus der Ausgabe, navigiert kontextbezogen und übernimmt nur einen bestätigten Index. | Parser-, Protokoll-, RPC-, AppModule- und Brailletests; `z=` praktisch mit einer physischen Braillezeile geprüft. |
| `vim.ui`-Auswahl | `vim.ui.select()` und `vim.ui.input()` liefern Prompt, Auswahl und Abschluss semantisch. | Echte TUI-Tests. |

Diagnosen werden bei Hintergrundaktualisierungen nicht automatisch vollständig
gesprochen. Ausdrückliche Befehle lesen aktuelle, vorherige, nächste, erste
oder letzte Diagnose. Rechtschreibausgabe folgt NVDAs Einstellungen unter
Dokumentformatierung für Sprache, Klang und Braille.

## Braille

| Bereich | Verhalten | Nachweis |
|---|---|---|
| Aktuelle Zeile | Eine öffentliche NVDA-`TextInfoRegion` bildet Text, Cursor, Tabs, Auswahl und Änderungen ab. | Automatisiert für Unicode, Tabs, leere Zeilen und Fokusaufbau; praktisch auf BRAILLEX EL 80c. |
| Routing | Routingtasten setzen den Cursor in Normal-, Insert- und Befehlszeilenmodus; veraltete oder nicht eindeutig zugeordnete Ziele werden abgelehnt. | Protokoll-, Controller-, Transport-, Lua- und Pakettests; praktisch auf BRAILLEX EL 80c. |
| Standardnavigation | NVDAs öffentliche Zeilen- und Scrollbefehle verschieben den Ausschnitt oder wechseln mit einer definierten Zielspalte zur Nachbarzeile. | Automatisiert lokal und über SSH; grundlegender Hardwarepfad bestätigt. |
| Wiederholtes Routing | Optionale Doppel- oder Dreifachbetätigung führt konfigurierte Wort- oder Zeilenaktionen aus. Voreinstellung ist ausschließlich Routing. | Zustands-, Einstellungs-, Protokoll-, Transport- und RPC-Tests; Referenzablauf praktisch geprüft. |
| Braille-Exploration | Ein pro Neovim-Sitzung gespeicherter virtueller Zeilenstand hält Position und horizontalen Ausschnitt, ohne den echten Cursor zu bewegen. Änderungen der angezeigten Zeile werden vollständig aktualisiert; Routing übernimmt nur einen aktuellen validierten Stand. | Instanz-, Interleaving-, Editier-, Routing-, Transport- und echte RPC-Tests; Kernpfad auf BRAILLEX EL 80c. |
| Flüchtige Ansichten | Rechtschreibvorschläge und gehaltene LSP- oder Diagnoseinformationen verwenden eine vorübergehende öffentliche Brailleregion und stellen danach die Editorregion wieder her. | Controller-, AppModule-, Regions- und Pakettests; Rechtschreibansicht praktisch geprüft. |

Die praktische Brailleprüfung belegt eine Anzeige- und Treiberkombination. Sie
ist kein Nachweis für jede Anzeige, Übersetzungstabelle oder Eingabebelegung.

## Terminal, Dateien und Zwischenablage

| Bereich | Verhalten | Nachweis |
|---|---|---|
| Eingebettetes Terminal | Direkte Terminaleingabe verwendet natives Passthrough; Terminal-Normalmodus, Prozessende, Befehlszeilenrückkehr und Bufferwechsel bleiben strukturiert. | Protokoll-, Gate-, TUI- und Pakettests; Kernpfade praktisch geprüft. |
| Dateimanager | Adapter für Oil, netrw, mini.files, nvim-tree und Neo-tree liefern Namen, Typ und Zustand ohne visuelle Dekoration. Bestätigte Aktionen werden zusammengefasst. | Breite Adapter- und Unicode-Tests; nur Oil praktisch unter Windows/NVDA geprüft. |
| Zwischenablage | Vier frei belegbare NVDA-Befehle übertragen Visual-Auswahl, Register 0 oder Windows-Zwischenablage ausdrücklich und korreliert. | Protokoll-, Lua-, Bridge- und Pakettests; alle vier Wege lokal und über SSH praktisch geprüft. |

Es gibt keine automatische Zwischenablagesynchronisation. Dateimanager werden
nur über ihren dokumentierten öffentlichen Zustand unterstützt; ein neuer
Pluginname allein begründet keinen Adapter.

## Sitzungsisolation und Ausfallverhalten

Ein konkretes UI-Automation-`TermControl` wird genau einer bestätigten
Neovim-Sitzung zugeordnet. Dadurch bleiben lokale und entfernte Sitzungen,
normale Shell-Panes, Tabs, Split-Panes, Fenster und mehrere
Windows-Terminal-Prozesse voneinander getrennt. Fokus-, Instanz-, Sequenz- und
Editoridentität werden vor Ausgabe, Unterdrückung oder Steuerung erneut
geprüft.

Fehlt eine Fähigkeit, ist eine Zuordnung unklar oder bricht die Verbindung ab,
verbraucht das Add-on keine fachliche Aktion und gibt NVDAs natives
Terminalverhalten frei. Mehrinstanz-, Fokusrennen-, Disconnect-, Reload- und
Negativpfade besitzen automatisierte Abdeckung; gemischte lokale und entfernte
Fenster, Tabs und Panes wurden praktisch geprüft.

Weitere Details stehen in [Architektur](architecture.md),
[Protokoll](protocol.md), [Teststrategie](testing.md) und den
[geführten Praxistests](human-testing.md).
