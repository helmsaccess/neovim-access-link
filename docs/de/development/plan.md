# Aktiver Plan

Stand: 20. Juli 2026.

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

Phase 6 ist automatisiert und praktisch bestätigt. Die zehn frei belegbaren
Terminalbefehle liegen nicht mehr im Global Plugin, sondern im Windows-
Terminal-AppModule.
NVDA 2026.1.1 zeigt unbelegte Befehle zunächst an, wenn Windows Terminal vor
dem Öffnen des Tastenbefehldialogs fokussiert war, und löst ihre Belegungen
nicht mehr in fremden Anwendungen auf. Nach dem Laden der AppModule-Klasse
kann eine gespeicherte Zuordnung andernorts aufgelistet bleiben; dies ist
NVDAs Darstellung der Benutzergestenkarte, keine globale Ausführung. Die
Ausführung prüft konkrete AppModule-Instanz und Control erneut; Fokusrennen und
ein nicht verfügbarer gemeinsamer Dienst geben
die Originalgeste durch. Für frühere GlobalPlugin-Skripte gespeicherte
Belegungen müssen neu zugewiesen werden. Sichtbarkeit, Neuzuweisung, lokale und
SSH-Befehle sowie mehrere Fenster, Tabs und Panes sind praktisch bestätigt;
es wurde kein Fehler gefunden. Nach jeder Stufe müssen gebautes Add-on,
Fail-open-Verhalten sowie lokale und SSH-Sitzungen in mehreren Tabs, Panes und
Fenstern geprüft werden.

Phase 7 ist mechanisch umgesetzt. Die direkt von NVDA geladenen Python-Module
unter `nvda-addon/addon/` folgen nun NVDAs Ruff-Format mit Tabs, LF und 110
Zeichen Zeilenlänge. Core, Bridge, Protokoll und Tests behalten ihren jeweils
bereits konsistenten Stil. Ruff 0.14.5 prüft nur diese klar begrenzte NVDA-
Stilzone lokal und in GitHub Actions; der dynamisch erforderliche Importpfad
des Global Plugins besitzt nur an den erforderlichen Importen begründete
`E402`-Ausnahmen. Der nachträglich erkannte Verlust der Braille-Overlayauswahl
ist durch einen direkten `controlTypes`-Import im AppModule und Tests des
tatsächlichen Overlay-Hooks korrigiert.

Die anschließende Verschlankung V2 wird wieder in kleine, automatisiert
abgesicherte Phasen geteilt. V2-1 bis V2-3 sind automatisiert umgesetzt: Der
Registrar veröffentlicht nur einen schmalen `TerminalIntegrationService` für
AppModule und Braille-Overlay. Ein eigener `SettingsService` besitzt Laden,
Normalisierung, Speichern und Profilwechsel. Präsentation und
`NvdaUiManager` verwenden dessen Snapshots und fachliche Operationen; der
UI-Manager kennt weder das Global Plugin noch dessen Zustand. Ein eigener
`TerminalFocusService` besitzt Identität, Fokuskorrelation und Lifecycle-Sweep.
Doppelte Registrierung, Teilfehler, ungültige Konfiguration und Verbindungsänderungen
sind direkt geprüft. Die prozessweite Verfügbarkeit von Einstellungen und
Werkzeugen bleibt unverändert. Eine praktische Zwischenprüfung ist für diese
internen Phasen nicht vorgesehen; sie wird mit späteren nutzerwirksamen
V2-Schritten gebündelt. V2-4 ist automatisiert abgeschlossen:
`SessionClaimService` besitzt F12-
Autorisierung, Inventarzustand, Scans, Kandidatenauswertung und die
unveränderliche Übergangsentscheidung. Discovery-Lebensdauer und
Sitzungslisten-Worker sowie die fachliche Ergebnisauswahl liegen ebenfalls
dort. Der Dienst plant Wiederverwendung oder Start einer lokalen
beziehungsweise entfernten Instanz und setzt einen aktuellen Plan auf den
neutralen
Instanzbindungen um und gibt verdrängte Terminalidentitäten an den NVDA-Rand
zurück. Start, Bindung und Runtime-Auswahl neuer Instanzen liegen ebenfalls in
diesem Dienst; Rückrollen und ersetzte Clients werden ohne blockierenden Stopp
auf dem NVDA-Hauptthread abgewickelt. Explizite Auswahl und Trennung laufen als
transaktionale Dienstübergänge; Clientstopps werden erst nach dem fail-open Zustandsabbau
asynchron ausgeführt. Die fail-open Aktivierung einer gemerkten Instanz und die
korrelierte Entscheidung zwischen Fokuskontext und Vollzustand liegen
inzwischen ebenfalls im Dienst. Er besitzt auch den ausstehenden Merkvorgang
temporärer Terminalbindungen und validiert Fokus, Control und Instanz nach dem
modalen Dialog erneut; Dialog, Diagnostik und Transportaufruf bleiben am
NVDA-Rand. Eine injizierte Fabrik kapselt die lokale und entfernte
Clientkonstruktion sowie deren instanzkorrelierte Callbacks; der
Claimdienst verbindet sie mit seinem Startübergang. Der Abschluss-Audit
entfernte unnötige Weiterleitungen und direkte produktive Zugriffe auf
veränderliche Claim-Container. Die Kompositionswurzel behält nur NVDAs
Hauptthread-, Dialog-, Meldungs- und Transportgrenzen. Nach dem gebündelten
Praxis-Meilenstein beginnt V2-5. Dieser Meilenstein ist inzwischen mit
mehreren Fenstern, Tabs und Panes, lokalen und entfernten Sitzungen sowie
Zwischenablageoperationen abgeschlossen. Der erste V2-5-Schnitt führt einen
`EditorSessionController` ein. Er übernimmt die Mutation und Umschaltung des
instanzgetrennten Editorzustands einschließlich Modus, Menüdokumentation,
Transportfähigkeiten, Verbindungszustand und strukturiertem Tippecho. Konkrete
NVDA-Ausgabe und Fokus-/Gate-Entscheidungen bleiben außerhalb. Der zweite
Schnitt verschiebt die begrenzte Anfrageverwaltung und Antwortkorrelation für
Zwischenablage, Register und eingebettete Terminalsteuerung in denselben
Controller. Netzwerkaufruf, Windows-Zwischenablage, Diagnostik und
übersetzte Rückmeldung bleiben in der NVDA-Kompositionswurzel. Der dritte
Schnitt führt Zustandsübergang, Terminal-Passthrough, Modusklang und neutrale
Sprachaktionen in einem unveränderlichen Ereignisplan zusammen. Damit plant
das Global Plugin Editorereignisse nicht mehr selbst, sondern liefert nur
über NVDA aus und wendet Gate-Übergänge an. Der vierte Schnitt ergänzt
isolierte Braillepläne und validierte semantische Routingpläne. Das Overlay
bleibt NVDA-spezifisch, und nur der NVDA-Rand führt den festen
`routeCursor`-Transportaufruf aus. Der fünfte Schnitt verschiebt die
Normalisierung des Verbindungsnamens und die Passthroughverfolgung der aktiven
Instanz in den Controller. Der sechste Schnitt ergänzt unveränderliche
ausgehende Allowlist-Pläne nach Capability-, Modus-, Buffer- und kanonischer
Zustandsprüfung für Zwischenablage, Register und eingebettete
Terminalsteuerung. Fokuskorrelation, Authentifizierung,
Windows-Zwischenablage und Transport bleiben bewusst außerhalb. Der
abschließende Audit verschiebt das Zurücksetzen des semantischen Planers und
den Zugriff auf Completion-Dokumentation hinter denselben Controller. V2-5
ist damit automatisiert abgeschlossen; nur vorübergehende
Kompatibilitätseigenschaften werden in V2-6 entfernt. Die geplante praktische
Abnahme folgt nach dieser Bereinigung.
V2-6 hat mit `AddonRuntime` begonnen: Späte Veröffentlichung und die bestehende
Abbaureihenfolge besitzen nun einen wiederholbaren Eigentümer. Für
Dienstentfernung, Abbruch verzögerter Aufrufe, fail-open Gate-Öffnung,
Verbindungs-/Zustandsbereinigung und abschließendes Schließen von UI und
Präsentation bestehen direkte Reihenfolge- und Fehlerfortsetzungstests. Die
weitere V2-6-Arbeit verschiebt Zusammensetzungsbesitz tiefer in diese Runtime,
entfernt Migrationseigenschaften und schmale Übergangscallbacks und schließt
vor der Praxisabnahme die Abdeckung für Teilinitialisierung und verspätete
Callbacks ab.
Die erste Migrationsbereinigung ist abgeschlossen: Alle sieben
Kompatibilitätseigenschaften für die Editorruntime wurden aus dem Global
Plugin entfernt; Tests verwenden den Controller-/Coordinatorvertrag direkt.
Auch die Claim-Migrationsbereinigung ist abgeschlossen: Acht Claim-,
Inventar- und Discovery-Sichten wurden entfernt; Tests verwenden den
`SessionClaimService` direkt. Verbindungs- und Fokus-Kompatibilitätssichten
werden erst nach demselben Produktivnutzungs-Audit entfernt.

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
