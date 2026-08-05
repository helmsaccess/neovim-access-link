# Aktiver Plan

Stand: 5. August 2026.

Dieses Kapitel enthält nur offene oder laufende Arbeit. Implementierte
Funktionen stehen in `current-status.md`; abgeschlossene Einzelschritte und
frühere Featurebranches stehen im `changelog.md`. Ein Punkt in diesem Plan ist
keine Zusage, dass die Funktion bereits verfügbar oder praktisch bestätigt
ist.

Die Reihenfolge und Prüftiefe richten sich nach Risiko, verfügbaren
Testumgebungen und tatsächlich gemeldeten Fehlern. Der Plan verspricht weder
die Prüfung jeder denkbaren Kombination noch feste Reaktions- oder
Behebungszeiten. Reproduzierbare Fehler werden nach Möglichkeit zeitnah
untersucht; Sicherheits-, Isolations- und Datenverlustrisiken haben Vorrang.

## 1. Dokumentation verständlich und überprüfbar halten

Laufend:

- Entwicklerdokumentation mit Architektur und Begriffen beginnen lassen,
  bevor Protokolldetails und Spezialfälle folgen;
- dauerhafte Referenz, aktuellen Status, aktiven Plan, Changelog und datierte
  Berichte klar trennen;
- deutsche und englische Kapitel durch den Dokumentationsbuild strukturell
  parallel halten und inhaltliche Änderungen gemeinsam prüfen;
- Aussagen zu Prozessen, Session-Registry, Zuordnung, Gate, Rückkanälen,
  Polling und Fallbacks gegen den aktuellen Code prüfen;
- HTML-Build, interne Links und veröffentlichte Quellen automatisiert prüfen;
- aktuelle Erklärungen frei von Entwicklungschronologie halten und Geschichte
  auf Changelog, datierte Berichte und ADRs begrenzen.

## 2. Architekturgrenzen nur bei belegtem Nutzen weiter verändern

Der in [ADR-0004](adr/0004-nvda-lifetime-and-event-ownership.md) beschlossene
Anwendungsschnitt ist umgesetzt und praktisch über mehrere Fenster, Tabs und
Panes mit lokalen und entfernten Sitzungen geprüft. Der erneute Audit in
[Anhang C](global-plugin-appmodule-audit-2026-08-04.md) bestätigt diesen
Scope, zeigt aber auch die weiterhin umfangreiche prozessweite
NVDA-Randkoordination in der konkreten Global-Plugin-Klasse und den breiten
öffentlichen Terminaldienst. Der aktuelle Aufbau steht in
`current-status.md`; Entwicklung und Messwerte stehen im Changelog sowie in
den Anhängen A bis C.

Eine weitere Aufteilung ist nicht allein wegen Dateigröße oder LOC geplant.
Sie wird in kleinen fachlichen Schnitten nur aufgenommen, wenn sie einen
eindeutigen Zustandsbesitzer, einen kleineren öffentlichen Vertrag, einen ohne
NVDA prüfbaren Fehlerpfad oder einen belegbaren Robustheitsgewinn schafft.
AppModule-Ereignisbesitz,
Fail-open, F12-Isolation, asynchroner Transport sowie Fenster-, Tab- und
Pane-Trennung bleiben dabei verbindliche Invarianten.

Als Kandidaten werden zuerst Verbindungs-/Claimabläufe, NVDA-Ereignisausgabe,
Kontextpräsentation und verbraucherspezifische Dienstverträge bewertet. Eine
Auslagerung erfolgt nur mit klaren Invarianten und Regressionstests; gemeinsam
genutzte prozessweite Abläufe werden nicht in das AppModule kopiert.

## 3. Praktische Abschottung verbreitern

- Die wichtigsten negativen Windows-Terminal-Fälle für ungebundene Shell-Tabs
  und -Panes, getrennte Fenster, schnelle Fokuswechsel, geschlossene Controls
  und weiterlebende RPC-Verbindungen schrittweise praktisch protokollieren.
  Reale Fehlerfälle werden in die Matrix aufgenommen.
- Für geprüfte und neu entdeckte unsichere Zustände sicherstellen, dass die
  native Terminalausgabe erhalten bleibt und weder eine Bindung noch eine
  Fokusansage entsteht.
- Den offenen Fall untersuchen, in dem innerhalb eines bereits gebundenen
  `TermControl` eine Shell oder tmux Neovim sichtbar ersetzt, während dessen
  RPC-Kanal noch lebt. Screen-Scraping ist keine zulässige Abkürzung.

## 4. Dateimanager praktisch abnehmen

Oil ist unter Windows/NVDA praktisch bestätigt. Als Nächstes werden netrw,
mini.files, nvim-tree und Neo-tree schrittweise lokal und über SSH geprüft:

- Navigation und Öffnen;
- Erstellen, Umbenennen, Kopieren, Verschieben und Löschen;
- Ja/Nein/Abbruch, Konflikte und schreibgeschützte Ziele;
- Mehrfachauswahl und Manager-Clipboard;
- Unicode, Leerzeichen und lange Namen;
- Fokuswechsel zu Datei, Terminal, Tab, Pane und Fenster;
- Sprache, Klänge und Braille ohne veralteten Managerzustand.

Fehlende öffentliche Pluginereignisse werden nicht durch unbeschränktes
Polling oder allgemeines Popup-Scraping ersetzt.

## 5. Braille-Hardwarematrix verbreitern

- Über die bereits bestätigte Braillezeile hinaus mehr als eine repräsentative
  Braillezeile beziehungsweise Treiberkombination praktisch prüfen.
- Cursor, Auswahl, Unicode, Tabs, Dateimanagersegmente und Routing prüfen.
- Standardbefehle für horizontales Verschieben sowie Auf/Ab mit
  Spaltenerhalt auf mehreren Treibern und Zeilenbreiten prüfen.
- Die optionalen Doppel-/Dreifachaktionen mit allen vier Befehlen, drei
  Zeilenstarts, Zeitablauf, Positionswechsel und sicherer Nullvoreinstellung
  praktisch prüfen.
- Mehrdeutige oder synthetische Zellen müssen ohne erfundenes Routingziel
  bleiben.
- Gefundene Hardwareunterschiede erst nach reproduzierbarem Nachweis in den
  Planer übernehmen.

## 6. Braille-Navigationsmodi praktisch abnehmen

- Den implementierten, frei belegbaren Umschalter zwischen `Cursor` und
  `Exploration` mit mehreren Braillezeilen und Treibern praktisch prüfen.
- Bestätigen, dass Auf/Ab im Braille-Explorationsmodus nur die flüchtige Leseposition
  verändert und Routing anschließend den echten Cursor auf die gewählte Zeile
  setzt.
- Unabhängigkeit vom Sprachexplorationsmodus, getrennte Moduswahl für mehrere
  parallele lokale und entfernte Sitzungen, gezielten Reset nur der getrennten
  Sitzung sowie die Ablehnung in Befehlszeile und direktem Terminalmodus
  praktisch prüfen.
- Nach Bearbeitungen auf der explorierten Zeile praktisch bestätigen, dass
  virtuelle Zeile und horizontaler Ausschnitt stehen bleiben, der Inhalt
  vollständig aktualisiert wird und ein erneutes Routing den aktuellen Modus
  und Bufferstand verwendet. Nach zwischenzeitlichen Änderungen bei einer
  anderen Echtcursorzeile muss Routing aus einem nicht mehr belegten
  Zeilenstand abgelehnt werden und nach erneutem Abruf der Zeile wieder
  funktionieren.
- Die Moduswahl wird bereits für die Lebensdauer jeder verbundenen Sitzung
  getrennt gehalten; neue und getrennte Sitzungen beginnen sicher im
  Cursormodus. Erst nach der Hardwareabnahme über eine zusätzliche
  profilfähige Speicherung über Verbindungen oder NVDA-Neustarts hinweg
  entscheiden.

## 7. Robustheit und Kompatibilitätsbreite erhöhen

- Langzeitbetrieb, wiederholte SSH-Abbrüche und Reconnects testen.
- Große Ereignislast, große Dateien und viele parallele Sitzungen messen.
- Weitere repräsentative Windows-, NVDA-, Neovim-, Sprach- und
  SSH-Konfigurationen risikobasiert in die praktische Matrix aufnehmen.
- Die implementierten gehaltenen Parameter- und Diagnoseansichten mit
  Pyright sowie weiteren repräsentativen LSP-Servern praktisch auf
  20-/40-/80-Modul-Braillezeilen prüfen. Dabei Mehrfachsignaturen,
  Hover-Rückfall, überlappende Diagnosen, jede NVDA-Tasten-Release-Reihenfolge
  und Klangunterdrückung beim Tippen bestätigen.
- Die ungeklärte ältere Rocky-Linux-/Neovim-Kombination nur untersuchen, wenn
  dafür ein konkretes Unterstützungsziel festgelegt wird.
- Portable Layouts, `NVIM_APPNAME`, andere Terminalfrontends und Neovim-GUIs
  erst mit eigener Identitäts-, Fokus-, Sicherheits- und Fail-open-Architektur
  planen.

## 8. Diagnose-Provider und Sprachen risikobasiert verbreitern

Die gemeinsame `vim.diagnostic`-Schicht, reale nvim-lint-/ALE-Verträge für C,
Python, Bash, Go, Rust, Ruby und Markdown sowie der echte
`none-ls.nvim`-LSP-Brückenvertrag sind implementiert. Weitere Kombinationen
werden nach Verbreitung und nach reproduzierbaren Problemen ergänzt, ohne
Sprachen im Add-on fest zu verdrahten:

- Go zusätzlich zu dem belegten Staticcheck-Pfad mit `gopls` in der
  gebündelten LSP-Praxisrunde prüfen; golangci-lint nur bei zusätzlichem
  realem Bedarf pinnen;
- Rust zusätzlich zu dem belegten Cargo-/Clippy-Pfad mit `rust-analyzer` und
  dessen Clippy-Diagnostics praktisch prüfen;
- `ruby-lsp`, alternative Ruby-Analysatoren oder weitere Markdown-Prüfer nur
  bei belegter Nutzung ergänzen; RuboCop und `markdownlint-cli2` bilden die
  automatisierte Ausgangsbasis;
- ausgelagerte none-ls-Zusatzquellen erst zusammen mit einem konkreten
  verbreiteten Werkzeug und allen tatsächlich benötigten Commits pinnen;
- Navigation aus Trouble, Telescope, ALE-eigenen Listen oder anderen
  Diagnoseansichten nur über öffentliche semantische APIs anbinden;
- einen eigenen Adapter ausschließlich dann erwägen, wenn ein verbreiteter
  Provider seine Diagnosen nachweislich nicht nach `vim.diagnostic` spiegeln
  kann.

Für jede neue Kombination bleiben echte Werkzeugausführung, gepinnter
Provider, korrekte UTF-8-Bytebereiche, Quelle/Code/Meldung, beide unterstützten
Neovim-Versionen und die klare Trennung von automatisierter und praktischer
Abnahme erforderlich.

## Reihenfolge für neue Funktionen

Vor neuer Funktionsbreite haben Isolationsfehler, Datenverlust, unklare
Rückkanäle, Hauptthread-Blockaden und falsche Ausgabe aus einer anderen Sitzung
Vorrang. Neue Integrationen verwenden bevorzugt öffentliche semantische
Ereignisse. Polling ist nur eine dokumentierte, begrenzte Notlösung, wenn keine
zuverlässige Ereignislösung existiert.
