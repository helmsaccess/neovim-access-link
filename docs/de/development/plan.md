# Aktiver Plan

Stand: 19. Juli 2026.

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

## 1. Dokumentation verständlich und überprüfbar machen

Laufend:

- Entwicklerdokumentation mit Architektur und Begriffen beginnen lassen,
  bevor Protokolldetails und Spezialfälle folgen;
- dauerhafte Referenz, aktuellen Status, aktiven Plan und historische
  Entwicklung klar trennen;
- deutsche und englische Kernkapitel strukturell parallel halten;
- Aussagen zu Prozessen, Session-Registry, Zuordnung, Gate, Rückkanälen,
  Polling und Fallbacks gegen den aktuellen Code prüfen;
- HTML-Build, interne Links und veröffentlichte Quellen automatisiert prüfen.

## 2. NVDA-Verantwortungsgrenzen verschlanken

[ADR-0004](adr/0004-nvda-lifetime-and-event-ownership.md) wird in einzeln
prüfbaren Schritten umgesetzt:

- UI-Registrierung und Komponentenverwaltung vom Terminalpfad trennen;
- gemeinsame Verbindungen und Zustände aus der GlobalPlugin-Klasse in normale
  Dienste verschieben;
- Windows-Terminal-Ereignisse, Overlays und `nextHandler` vollständig im
  AppModule besitzen;
- F12-Fokusprüfung weiter eingrenzen, ohne Tab-, Pane- oder Fensterwechsel zu
  beeinträchtigen.

Phase 1 ist automatisiert umgesetzt: Fensteridentität und Prozesslebensdauer
verwenden `winUser`, `winBindings` und `winKernel`; der neutrale Session-Lister
erhält die Prozessprüfung injiziert. Adapter-, Registry-, Claim-, Lifecycle-
und vollständige Built-Add-on-Tests bestehen. Die praktische Prüfung von
Prozessende, geschlossenen Tabs/Panes und Plugin-Neuladen unter Windows/NVDA
steht noch aus; bis dahin gilt die Phase nicht als praktisch abgenommen.

Phase 2 ist automatisiert umgesetzt: `NvdaUiManager` besitzt die symmetrische
Registrierung von Einstellungen und Werkzeugmenü, die Verbindungsformulare
sowie Installation und Entfernung der Neovim-Komponenten. Die
`GlobalPlugin`-Klasse erzeugt und beendet diesen Manager, enthält aber nicht
mehr dessen Implementierung. Struktur-, Lokalisierungs-, Dialog-, Installer-
und Built-Add-on-Tests bestehen; Einstellungen, Werkzeugdialoge und deutsche
UI-Texte wurden anschließend praktisch bestätigt.

Phase 3 ist automatisiert umgesetzt. Ein NVDA-unabhängiger
`ConnectionCoordinator` besitzt Instanzmanager, aktiven Client, Gate, aktiven
Sprachplaner, Authentifizierung, Terminalzuordnungen, begrenzte korrelierte
Anfragen, getrennte Laufzeitzustände sowie Auswahl, Fokusbestätigung und
vollständige Zustandsbereinigung einer Instanz. `NvdaPresentation` besitzt die
NVDA-spezifische Ausgabe geplanter Sprache, Braillemeldungen und Klänge;
`NvdaUiManager` bleibt für Einstellungen, Werkzeuge und Komponentenformulare
zuständig. Ein identitätsgeprüfter `ServiceRegistrar` veröffentlicht erst die
vollständig initialisierte Dienstinstanz und schützt Add-on-Neuladen vor dem
verspäteten Beenden einer älteren Instanz. Schmale
Kompatibilitätseigenschaften halten den bisherigen Ereignispfad während des
Umbaus stabil. Die F12-Zuordnung wurde nicht verändert; ihre Härtung gehört
ausdrücklich zu Phase 5.
Der Phase-3-Abschlussstand wurde anschließend mit lokalen und entfernten
Verbindungen über mehrere Windows-Terminal-Fenster, Tabs und Panes praktisch
bestätigt.

Phase 4 ist automatisiert umgesetzt und praktisch bestätigt.
Das Windows-Terminal-AppModule besitzt nun alle Terminalereignisse, die
Overlayauswahl und jeden Aufruf von `nextHandler`. Ein undurchsichtiges Token
verhindert, dass ein verspätetes `loseFocus` eines alten WT-Prozesses den neuen
Fokus löscht. `gainFocus` verwendet einen zweiphasigen Vertrag: Der gemeinsame
Dienst bereitet nur die Fokusentscheidung vor, das AppModule ruft NVDAs
nativen Handler genau einmal auf, damit Terminal-LiveText initialisiert wird,
und schließt danach die strukturierte Fokusbehandlung ab. Generation und Token
verwerfen verspätete Abschlüsse; wartende `fullState`-Ereignisse gehen dabei
nicht verloren. Frühe und späte Fehler fallen ohne zweiten nativen Aufruf
offen aus. Lokale und entfernte Verbindungen, mehrere WT-Fenster, Tabs und
Panes, Fokuswechsel, native Shellausgabe, Sprache und Klänge zeigten im
anschließenden Praxistest keine Probleme. Braille konnte mangels verfügbarer
Hardware nicht praktisch geprüft werden. F12 und frei belegbare Befehle
bleiben in dieser Phase unverändert.

Phase 5 ist automatisiert umgesetzt und praktisch bestätigt.
Der F12-Decider fragt erst nach einem Treffer der einen Claim-Taste NVDAs
aktuelles Fokusobjekt ab. Er autorisiert nur die konkrete, noch registrierte
Windows-Terminal-AppModule-Instanz, wenn die daraus gebildete vollständige
`TermControl`-Identität mit dem Gate übereinstimmt. Der frühere
Einzeladapter-Fallback ist entfernt; ein Fokuswechsel vor der eingereihten
Hauptthreadauswertung verwirft weiterhin die Einmalgeneration. Im Insert-Modus
bleibt die physische Taste als Claim nachweisbar, wird danach aber nicht mehr
als `<F12>` eingefügt: ab Neovim 0.11 durch den Rückgabevertrag von
`vim.on_key`, unter Neovim 0.10 durch eine nur bei unbelegtem F12 eingerichtete
Insert-Mode-`<Ignore>`-Zuordnung. Andere Modi und vorhandene Benutzerbelegungen
bleiben unverändert. Automatisierte Negativfälle umfassen fremde Anwendungen,
veraltete Controls, mehrere WT-AppModules und schnelle Fokuswechsel. Der
anschließende Praxistest des Normal- und Insert-Claims sowie der Fokus- und
Control-Abschottung zeigte keine Fehler.

Die Platzierung frei belegbarer Befehle ist für eine spätere, getrennte Stufe
geklärt: NVDA 2026.1.1 bezieht den Tastenbefehldialog aus dem vorherigen Fokus
und dessen AppModule. Bei zuvor fokussiertem Windows Terminal sind die Befehle
des Windows-Terminal-AppModules deshalb sichtbar und können dort enger
begrenzt werden. Bis diese Verlagerung eigens umgesetzt und geprüft ist,
bleiben die vorhandenen Metadaten unverändert. Nach jeder Stufe müssen gebautes Add-on,
Fail-open-Verhalten sowie lokale und SSH-Sitzungen in mehreren Tabs, Panes und
Fenstern geprüft werden; Architekturumbau und Verhaltensänderung werden nicht
im selben Schritt vermischt.

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
