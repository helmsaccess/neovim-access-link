# Aktiver Plan

Stand: 23. Juli 2026.

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
- deutsche und englische Kernkapitel strukturell parallel halten;
- Aussagen zu Prozessen, Session-Registry, Zuordnung, Gate, Rückkanälen,
  Polling und Fallbacks gegen den aktuellen Code prüfen;
- HTML-Build, interne Links und veröffentlichte Quellen automatisiert prüfen.

## 2. Architekturgrenzen nur bei belegtem Nutzen weiter verändern

Die in [ADR-0004](adr/0004-nvda-lifetime-and-event-ownership.md) beschlossene
Verschlankung ist umgesetzt und praktisch über mehrere Fenster, Tabs und Panes
mit lokalen und entfernten Sitzungen geprüft. Der aktuelle Aufbau steht in
`current-status.md`; die Entwicklung und ihre Messwerte stehen im Changelog
sowie in den Anhängen A und B.

Eine weitere Aufteilung ist nicht allein wegen Dateigröße oder LOC geplant.
Sie wird nur wieder aufgenommen, wenn sie einen eindeutigen Zustandsbesitzer,
einen kleineren öffentlichen Vertrag, einen ohne NVDA prüfbaren Fehlerpfad
oder einen belegbaren Robustheitsgewinn schafft. AppModule-Ereignisbesitz,
Fail-open, F12-Isolation, asynchroner Transport sowie Fenster-, Tab- und
Pane-Trennung bleiben dabei verbindliche Invarianten.

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

## 5. Braille an echter Hardware prüfen

- Sobald Hardware verfügbar ist, mehr als eine repräsentative Braillezeile
  beziehungsweise Treiberkombination praktisch prüfen.
- Cursor, Auswahl, Unicode, Tabs, Dateimanagersegmente und Routing prüfen.
- Mehrdeutige oder synthetische Zellen müssen ohne erfundenes Routingziel
  bleiben.
- Gefundene Hardwareunterschiede erst nach reproduzierbarem Nachweis in den
  Planer übernehmen.

## 6. Robustheit und Kompatibilitätsbreite erhöhen

- Langzeitbetrieb, wiederholte SSH-Abbrüche und Reconnects testen.
- Große Ereignislast, große Dateien und viele parallele Sitzungen messen.
- Weitere repräsentative Windows-, NVDA-, Neovim-, Sprach- und
  SSH-Konfigurationen risikobasiert in die praktische Matrix aufnehmen.
- Die ungeklärte ältere Rocky-Linux-/Neovim-Kombination nur untersuchen, wenn
  dafür ein konkretes Unterstützungsziel festgelegt wird.
- Portable Layouts, `NVIM_APPNAME`, andere Terminalfrontends und Neovim-GUIs
  erst mit eigener Identitäts-, Fokus-, Sicherheits- und Fail-open-Architektur
  planen.

## Reihenfolge für neue Funktionen

Vor neuer Funktionsbreite haben Isolationsfehler, Datenverlust, unklare
Rückkanäle, Hauptthread-Blockaden und falsche Ausgabe aus einer anderen Sitzung
Vorrang. Neue Integrationen verwenden bevorzugt öffentliche semantische
Ereignisse. Polling ist nur eine dokumentierte, begrenzte Notlösung, wenn keine
zuverlässige Ereignislösung existiert.
