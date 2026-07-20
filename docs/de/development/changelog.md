# Changelog

Begriffshinweis: „Registry“ bezeichnet in allen historischen Einträgen die
dateibasierte Neovim-Sitzungsregistrierung aus kurzlebigen JSON-Dateien, niemals
die Windows-Registry. Das Produkt verwendet keine Schlüssel unter `HKCU` oder
`HKLM`.

## 0.95.0-dev.21+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Lokale und entfernte Discovery-Ergebnisse werden nun im neutralen
  `SessionClaimService` ausgewertet. Unveränderliche Ergebnisse unterscheiden
  veraltete Fortsetzungen, Fehler, leere Listen, SSH-Fallback, fehlende frische
  Claims, Einzelauswahl und erforderliche Auswahldialoge.
- NVDA-Meldungen und modale Dialoge bleiben auf dem Hauptthread im Global
  Plugin; Wiederverwendung und konkrete Verbindungsstarts folgen in den
  nächsten V2-4-Schnitten.
- Dieser interne Schnitt wurde noch nicht separat praktisch geprüft.

## 0.95.0-dev.20+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Die letzten nur delegierenden lokalen und entfernten Discovery-Methoden
  wurden aus dem Global Plugin entfernt. Tests sprechen den neutralen
  Claimdienst nun direkt an; Auswahl-UI und Verbindungsstarts bleiben bewusst
  an ihren bisherigen NVDA-Hauptthreadgrenzen.
- Dieser interne Schnitt wurde automatisiert, aber noch nicht separat praktisch
  geprüft.

## 0.95.0-dev.19+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Der nächste V2-4-Schnitt verschiebt die fachliche Entscheidung nach einem
  autorisierten F12-Claim in den neutralen `SessionClaimService`. Ein
  unveränderliches Ergebnis unterscheidet lokale, entfernte und automatische
  Auflösung sowie noch nicht bereites Inventar.
- Das Global Plugin behält NVDA-Meldungen, Dialoge, Hauptthread-Zeitsteuerung
  und konkrete Verbindungsstarts. Discovery-Generation sowie lokale und SSH-
  Sitzungslisten-Worker liegen nun ebenfalls im Claimdienst. Ausstehende
  Zielwahlen werden weiterhin genau einmal verbraucht; nicht authentifizierte
  alte Bindungen werden nicht wiederverwendet.
- Dieser interne Schnitt wurde automatisiert, aber noch nicht separat praktisch
  geprüft.

## 0.95.0-dev.18+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Der erste V2-4-Schnitt führt `SessionClaimService` als alleinigen Eigentümer
  von einmaliger F12-Autorisierung, Claim-Generationen und Claim-Inventarzustand
  ein. Die öffentliche Terminalfassade autorisiert und verwirft Claims nun
  direkt über diesen neutralen Dienst.
- Lokale/SSH-Inventarworker und die rein fachliche Auswertung von Inventar und
  frischen Kandidaten laufen nun hinter dem Dienst; NVDA-Queue und Adapter sind
  injiziert. Auswahl und Verbindungsübergänge behalten ihr Verhalten, bis
  spätere V2-4-Schnitte ihre Orchestrierung verschieben.
- Dieser interne Schnitt wurde noch nicht separat praktisch abgenommen.

## 0.95.0-dev.17+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Der neue `TerminalFocusService` besitzt Terminalidentität, Fokusgeneration,
  AppModule-/Adapterkorrelation, Fokusabschluss und Lifecycle-Sweep. Die
  öffentliche Terminalfassade delegiert Fokusoperationen direkt an ihn.
- Geschlossene Controls benötigen weiterhin zwei eindeutige Negativprüfungen;
  fokussierte Controls und unsichere UIA-Ergebnisse bleiben erhalten. Client-
  Stoppen läuft nach der Bereinigung weiter außerhalb des Hauptthreads.
- Diese interne Phase wurde noch nicht separat praktisch abgenommen.

## 0.95.0-dev.16+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Der erste V2-3-Schnitt verschob Fokusobjekt, Identitätscache,
  AppModule-/Adapterkorrelation und Fokusgeneration in den
  `TerminalFocusService`; der Lifecycle-Sweep folgte in `dev.17`.

## 0.95.0-dev.15+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Ein eigener `SettingsService` besitzt nun Laden, Normalisierung, Speichern
  und NVDA-Profilwechsel. Einstellungsdialog und Präsentation arbeiten mit
  getrennten Snapshots beziehungsweise fachlichen Updates statt mit einem
  frei veränderlichen Plugin-Dictionary.
- Der `NvdaUiManager` erhält keine Global-Plugin-Instanz mehr. Seine schmalen
  Abhängigkeiten, idempotente Registrierung, Teilfehler, Abbruchpfade und
  Hintergrundoperationen sind automatisiert geprüft; Einstellungen und
  Werkzeuge bleiben prozessweit verfügbar.
- Diese interne Phase wurde noch nicht separat praktisch abgenommen.

## 0.95.0-dev.14+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Ein neuer öffentlicher `TerminalIntegrationService` verbirgt das konkrete
  Global Plugin vor Windows-Terminal-AppModule und Braille-Overlay. Ein fester
  Befehlstyp ersetzt dynamische Methodennamen; Fokusentscheidungen und
  F12-Autorisierungen sind unveränderlich.
- Ausfall, unvollständige Initialisierung, Add-on-Neuladen, späte Fokusfehler,
  ein defekter Braillevertrag und veraltete F12-Autorisierungen sind fail-open
  automatisiert geprüft. Diese interne Phase wurde noch nicht separat
  praktisch abgenommen.

## 0.95.0 (Beta)

- Die Produktversion wurde auf ausdrückliche Vorgabe auf `0.95.0` angehoben.
  Der konfigurierte Releasekanal bleibt unverändert `beta`.
- Windows-Terminal-Ereignisse, Overlayauswahl, `nextHandler` und frei belegbare
  Terminalbefehle gehören nun dem AppModule. Das Global Plugin konzentriert
  sich stärker auf gemeinsame Lebensdauer, Einstellungen, Werkzeuge und
  Dienstkoordination.
- F12 prüft die konkrete AppModule-Instanz und vollständige
  `TermControl`-Identität, bestätigt den Fokus erneut auf NVDAs Hauptthread und
  fügt bei einer unbelegten Zuordnung im Insert-Modus kein `<F12>` mehr ein.
- Eigene Windows-DLL-Bindings wurden durch NVDAs Wrapper ersetzt. Reload,
  mehrere Windows-Terminal-Fenster, Tabs und Panes sowie Fail-open-Pfade sind
  breiter automatisiert geprüft.
- Die strukturierte Braille-Overlayauswahl besitzt ihre `controlTypes`-
  Abhängigkeit direkt im AppModule und wird über den echten NVDA-Hook getestet.
  Eine praktische Prüfung mit Braillehardware steht weiterhin aus.
- NVDA-seitiger Python-Code folgt NVDAs Stilkonventionen. Ein datiertes
  Qualitätsreview dokumentiert Vergleichsbasis, behobene Regressionen,
  verbleibende Grenzen und empfohlene Folgeschritte.

## 0.94.2-dev.13+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Die Overlayauswahl importiert NVDAs `controlTypes` nun direkt im Windows-
  Terminal-AppModule. Dadurch wird die strukturierte Braille-Overlayklasse
  wieder eingesetzt, ohne von einem zufälligen Reexport des Global Plugins
  abzuhängen.
- Regressionstests rufen den tatsächlichen NVDA-Overlay-Hook für passende und
  unpassende Controls sowie den fail-open-Fehlerpfad auf.
- F12 ist jetzt präzise als öffentlicher, prozessweit aufgerufener Decider mit
  AppModule-eigener Lebensdauer und strikter Kontextprüfung dokumentiert.
  Begründete `E402`-Ausnahmen gelten nur noch an den erforderlichen Imports.
- Ein datiertes Qualitätsreview erklärt Anlass, Vergleichsbasis, behobene und
  verbleibende Befunde, Prüfnachweise und die empfohlene weitere Reihenfolge.

## 0.94.2-dev.12+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Phase 7 formatiert ausschließlich die direkt von NVDA geladenen Python-
  Module nach NVDAs Konventionen: Tabs, LF und 110 Zeichen Zeilenlänge. Core,
  Bridge, Protokoll und Tests behalten ihren vorhandenen konsistenten Stil.
- Eine auf `nvda-addon/addon/` begrenzte Ruff-0.14.5-Konfiguration sowie eine
  entsprechend gefilterte GitHub-Actions-Prüfung verhindern erneute
  Stilvermischung. Der dynamisch erforderliche Importpfad des Global Plugins
  ist dokumentiert ausgenommen; zwei als unbenutzt eingeordnete Imports sind
  entfernt. Dev-Build 13 korrigiert die dabei übersehene indirekte
  `controlTypes`-Abhängigkeit.
- Die Änderung beabsichtigt kein Laufzeitverhalten zu ändern. Vollständige
  Suiten und gebautes Add-on prüfen den mechanisch umformatierten Stand.

## 0.94.2-dev.11+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Phase 6 verlagert alle zehn frei belegbaren Terminalbefehle vom Global
  Plugin in das Windows-Terminal-AppModule. NVDA zeigt sie an, wenn Windows
  Terminal vor dem Öffnen des Tastenbefehldialogs fokussiert war, und löst ihre
  Belegungen nicht mehr in fremden Anwendungen auf.
- Die Ausführung prüft die exakt fokussierte AppModule-Instanz und vollständige
  `TermControl`-Identität erneut. Ein Fokusrennen oder nicht verfügbarer
  gemeinsamer Dienst gibt die Originalgeste durch, ohne Gate, Bindungen oder
  Unterdrückung zu verändern; getrennte AppModule-Instanzen können keine
  Befehle füreinander ausführen.
- Skriptnamen, übersetzte Bezeichnungen, Kategorien und Standardbelegungen
  bleiben unverändert. Weil NVDA die besitzende Klasse in einer
  Benutzergestenzuordnung speichert, müssen in einem früheren Featurebuild
  zugewiesene Gesten einmal neu belegt werden. Automatisierte Add-on- und
  Paketabdeckung ist vollständig. Der Praxistest fand in lokalen und SSH-Tabs
  sowie Panes keine Fehler. Er bestätigte auch NVDAs erwartete
  Darstellungsnuance: Nach dem Laden der AppModule-Klasse kann die globale
  Benutzergestenkarte eine gespeicherte Zuordnung aus einer anderen Anwendung
  heraus auflisten, während die Laufzeitauflösung auf Windows Terminal
  begrenzt bleibt.

## 0.94.2-dev.10+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Phase 5 autorisiert einen physischen F12-Druck nur noch, wenn NVDAs
  aktuelles Fokusobjekt genau zu einer lebenden Windows-Terminal-AppModule-
  Instanz gehört und dessen vollständige `TermControl`-Identität mit dem Gate
  übereinstimmt. Der Einzeladapter-Fallback ist entfernt; Einmalgeneration und
  erneute Prüfung auf dem Hauptthread bleiben als zweite Schranke erhalten.
- Eine Zuordnung im Insert-Modus fügt bei unbelegtem F12 kein `<F12>` mehr in
  den Buffer ein. Neovim ab 0.11 konsumiert nur diesen beobachteten
  Insert-Claim in `vim.on_key`; Neovim 0.10 verwendet dafür ausschließlich
  eine schmale Insert-Mode-`<Ignore>`-Zuordnung. Vorhandene Benutzerbelegungen
  werden nicht überschrieben, andere Modi bleiben unverändert.
- Negativtests decken fremde Anwendungen, veraltete Control-Identitäten,
  mehrere AppModule-Instanzen und schnelle Fokuswechsel ab. Lua- und
  Registrytests bestehen unter Neovim 0.10.1 und 0.12.3. Der anschließende
  Praxistest von Normal- und Insert-Claims sowie Fokus- und Control-Abschottung
  zeigte keine Fehler.

## 0.94.2-dev.9+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Phase 4 verlagert alle Windows-Terminal-Ereignisse, die Overlayauswahl und
  jeden Aufruf von `nextHandler` vollständig in das AppModule. Der gemeinsame
  Dienst liefert nur noch fachliche Fokus- und Suppressionsentscheidungen.
- `gainFocus` initialisiert NVDAs native Terminal-LiveText-Behandlung genau
  einmal, bevor strukturierte Sprachunterdrückung oder ein wartender
  `fullState` abgeschlossen werden. Adaptertoken und Fokusgenerationen
  verwerfen verspätete Fokus- und `loseFocus`-Abschlüsse, ohne den Zustand
  einer neueren WT-Instanz zu löschen.
- Struktur-, Reentranz-, Fail-open-, Mehrfenster-, Tab- und Pane-Regressionen
  bestehen automatisiert. F12 und frei belegbare Befehle bleiben unverändert;
  lokale und entfernte Verbindungen, mehrere WT-Fenster, Tabs und Panes,
  Fokuswechsel, native Shellausgabe, Sprache und Klänge wurden anschließend
  ohne festgestellte Probleme praktisch geprüft. Braille blieb mangels
  verfügbarer Hardware ungeprüft.

## 0.94.2-dev.8+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Phase 3 der Verantwortungsverschlankung trennt nun gemeinsame
  Verbindungs-, Anfrage- und Instanzzustände sowie die konkrete NVDA-Ausgabe
  von Sprache, Braillemeldungen und Klängen aus der `GlobalPlugin`-Klasse.
- Auswahl, fokusbestätigte Aktivierung und vollständige Bereinigung einer
  Verbindungsinstanz verwenden gemeinsame Coordinator-Verträge. Ersetzen,
  Trennen und das Entfernen geschlossener Tabs verwerfen dadurch dieselben
  ausstehenden Zustände.
- Ereignisbesitz, `nextHandler` und F12-Zuordnung bleiben unverändert und sind
  bewusst den späteren Phasen 4 und 5 vorbehalten. Add-on-, Protokoll-,
  Bridge-, Neovim-, gettext-, Dokumentations- und Paketprüfungen bestehen; die
  praktische Abnahme mit lokalen und entfernten Verbindungen in mehreren
  Fenstern, Tabs und Panes wurde anschließend bestätigt. Das bereits zuvor
  vorhandene Einfügen von `<F12>` bei einer Zuordnung im Insert-Modus bleibt
  als getrennter Phase-5-Fall offen.

## 0.94.2-dev.6+feature.global-plugin-slimming (Featurebranch-Testbuild)

- Ein NVDA-unabhängiger `ConnectionCoordinator` besitzt gemeinsamen
  Verbindungs- und Instanzzustand; ein identitätsgeprüfter Registrar schützt
  Add-on-Neuladen vor dem verspäteten Beenden einer älteren Dienstinstanz.
- Begrenzung, Korrelation und instanzbezogenes Verwerfen ausstehender
  Zwischenablage- und Terminalsteuerungsanfragen liegen nun ebenfalls im
  Coordinator. Ereignisbesitz, F12-Zuordnung und Fail-open-Verhalten bleiben
  unverändert.
- Der Stand besteht die vollständigen Add-on-, Bridge-, gettext- und
  Neovim-Plugin-Prüfungen und wurde anschließend praktisch bestätigt.

## 0.94.2

- Anwender- und Entwicklerdokumentation führen nun von den Grundbegriffen zur
  Architektur und trennen aktuellen Status, offenen Plan und historischen
  Verlauf klar voneinander.
- Bedienbezeichnungen wurden mit Gettext-Katalog und NVDA-Quellcode
  abgeglichen. Sitzungs-Registry, Windows-Terminal-`TermControl`, F12,
  SSH-Lebenszyklus, Rückkanäle und Completion-Befehle sind präziser erklärt.
- Prüfung und Support werden als risikobasierter Best-Effort-Prozess ohne
  Zusage erschöpfender Abdeckung oder fester Reaktionszeiten beschrieben.

## 0.94.1

- Der automatisiert und praktisch geprüfte Gettext-Stand aus dem Featurebranch
  wird als Version `0.94.1` übernommen. Produktkanal und Reifegradeinordnung
  bleiben unverändert.
- Der deutsche Katalog deckt alle 310 extrahierten Texte ab; MO-, Paket- und
  Vollständigkeitstests verhindern leere oder unbemerkte englische Anzeigen.

## 0.94.0-dev.3+feature.gettext-translation (Featurebranch-Testbuild)

- Native NVDA-gettext-Kataloge verwenden die öffentliche Domain `nvda`; ein
  deutsches Manifest und der kompilierte deutsche Laufzeitkatalog werden im
  Add-on ausgeliefert.
- Ein Standardbibliothek-Werkzeug extrahiert POT/PO reproduzierbar, erhält
  Übersetzungen, prüft Katalogabdeckung und benannte Formatplatzhalter und
  kompiliert deterministische MO-Dateien ohne externe gettext-Abhängigkeit.
- Die Speech-Planung bleibt NVDA-unabhängig und erhält die aktive Übersetzung
  als Callback. Modus-, Fokus-, Navigations-, Auswahl-, Fold-, Register- und
  Dateimanagertexte werden über feste Templates lokalisiert. Der deutsche
  Katalog deckt alle 310 aktuell extrahierten Texte ab.
- Katalog-, Speech- und Archivregressionen bestehen. Eine praktische Abnahme
  unter deutschem NVDA steht noch aus.
- Unübersetzte PO-Einträge werden wie bei `msgfmt` nicht in die MO-Datei
  geschrieben. Dadurch liefert gettext den englischen Quelltext statt einer
  leeren Zeichenkette; beide Werkzeuge-Menüeinträge und ihre Formulare bleiben
  unterscheidbar und bedienbar.

## 0.94.0 (Vorabversion)

- Die Produktversion wurde auf ausdrückliche Vorgabe auf `0.94.0` angehoben.
  Der Vorabkanal und die Einordnung zwischen Alpha und Beta bleiben
  unverändert.

## 0.93.0-dev.1+feature.cleanup-0.94.0-prerelease (Featurebranch-Testbuild)

- Die interne NVDA-Add-on-ID, das GlobalPlugin-Paket, der native
  Konfigurationsabschnitt und der Artefaktpräfix heißen einheitlich
  `NeovimAccessLink`. Der frühere Stand muss vor dem Test deinstalliert werden;
  alte Einstellungen und Gestenzuweisungen werden bewusst nicht übernommen.
- JSON-Einstellungsmigration, native `schemaVersion`, alte AppModule-Skript-IDs
  und die unbenutzte Beispielkonfiguration sind entfernt. Ein alter
  `nvimNvdaAccess`-Abschnitt oder eine gleichnamige JSON-Datei bleibt
  unverändert und wird nicht gelesen.
- Bridge und Verbindungsverwaltung verwenden nur noch typisierte Neovim-RPC-
  Endpunkte und Verbindungsziele. Die alten Python-Reexports, Socket- und
  Remoteprofil-Kurzformen sind entfernt; Protokoll-, Registry- und
  Fail-open-Sicherheitsprüfungen bleiben bestehen.
- 277 Add-on-/Core-/Pakettests, 42 Protokolltests, 31 Bridge-Tests und die
  Lua-Suiten mit Neovim 0.10.1 und 0.12.3 bestehen. Das Add-on enthält nur den
  neuen GlobalPlugin-Pfad; Archivprüfung und alle sechs HTML-Builds sind grün.

## 0.93.0-dev.7 (Featurebranch-Testbuild)

- Oils öffentliche `parsed_name`-Angabe ist während einer noch nicht mit
  `:w` angewendeten Bearbeitung nun der semantische Name für Sprache und
  Braille. Der Pfad bleibt bis zum belegten Abschluss an `entry.name` gebunden;
  ein Entwurfsname wird daher nicht als bereits ausgeführte Umbenennung
  ausgegeben.
- Dateimanager-Navigation bewahrt neben dem dekorationsfreien semantischen
  Eintrag die feste Bewegungsart. Damit spielen insbesondere `0`, `$`, `gg`
  und `G` wieder ihre Zeilen- und Dateigrenzklänge; Zeilenwechsel können ihre
  Randklänge ebenfalls ausgeben.
- Regressionstests prüfen Entwurfsname gegenüber bestätigtem Pfad, die
  Plugin-Ereignisverkabelung auf Neovim 0.10/0.12 sowie Sprachplanung ohne
  Rückfall auf Icons oder Zusatzspalten. Ein isolierter realer Oil-Lauf belegt
  den Entwurfsnamen ohne Dateisystemänderung.
- Die praktische Windows-/NVDA-Abnahme mit Neovim 0.12 bestätigt Oil samt
  Entwurfsnamen und Klängen. Oil ist bislang der einzige unter Windows
  praktisch geprüfte Dateimanager und bildet eine solide Grundlage; netrw,
  mini.files, nvim-tree und Neo-tree folgen schrittweise.

## 0.93.0-dev.6 (Featurebranch-Testbuild)

- Meldung erzeugende Ex-Befehle koppeln ihren unmittelbaren strukturierten
  Rückgabestatus an den vorherigen Modus. Der passende Modusklang folgt genau
  einmal; die Meldung bleibt immer erhalten und wird je nach „Session focus“
  ohne Zusatz, mit aktueller Zeile oder mit Kontext, Modus und Verbindung
  ausgegeben. Spätere asynchrone Meldungen werden nicht gekoppelt; ein Befehl
  ohne Meldung kann keinen späteren Moduswechsel unterdrücken.
- Eine neue Dateimanager-Workflow-Spezifikation mit 118 Assertions deckt
  Erstellen, Umbenennen, Kopieren/Duplizieren, Verschieben, Löschen,
  Wiederherstellen, Batchaktionen, Zustandswechsel, Fehler/Abbruch,
  Pfadminimierung sowie Schreibprojektnamen mit Leerzeichen und Unicode ab.
- Der echte TUI-Promptpfad belegt eine ausgewählte Nein-Antwort; Speech-Tests
  prüfen Ja, Nein und Abbruch. Kanonische
  Dateitypen wie `directory` bleiben auch in nvim-tree-Aktionsresultaten
  erhalten. Öffnen aus einem Manager folgt in allen drei Varianten der
  konfigurierten Fokusausgabe.
- Die automatisierte Abdeckung ist erweitert; eine praktische Abnahme dieses
  Testbuilds steht ausdrücklich noch aus.

## 0.93.0-dev.5 (Featurebranch-Testbuild)

- Der enge Oil-Promptparser erkennt die echten eingerückten `MOVE`-, `COPY`-,
  `TRASH`- und `PURGE`-Zeilen sowie `RESTORE`. Er beschreibt Umbenennen und
  Duplizieren eindeutig, kennzeichnet Lösch- und Papierkorbaktionen als
  destruktiv und überträgt weiterhin keine Namen oder Pfade.
- Direkt getipptes Y/N wird beobachtet, aber weder abgefangen noch ersetzt.
  Das ereignisgesteuerte Schließen wartet einen Neovim-Schedulerzyklus, damit
  `promptClosed` Annahme beziehungsweise Abbruch zuverlässig trägt; Oil bleibt
  allein für Tastenauswertung und Dateioperation verantwortlich. Es gibt weder
  Timer noch Polling.
- Reale isolierte Oil-Prüfungen decken abgebrochenes Umbenennen, Duplizieren
  und Löschen sowie bestätigtes Löschen ab. Der TUI-Regressionstest verlangt
  ausdrücklich `accepted=false`; 105 Dateimanagerassertionen bestehen.
- Das Handbuch empfiehlt `skip_confirm_for_simple_edits = false`, dokumentiert
  die zentralen Promptoptionen von nvim-tree und Neo-tree sowie mini.files'
  gemeinsame Ja-/Nein-/Abbruchabfrage.

## 0.93.0-dev.4 (Featurebranch-Testbuild)

- Der netrw-Fallback wertet Header und die Listenstile schmal, lang, breit und
  Baum getrennt aus. Leerzeichen, wiederholte Leerzeichen, Tabs, Unicode und
  Symlinkdekoration bleiben erhalten beziehungsweise werden gezielt getrennt;
  der Baumroot wird nicht mehr an sich selbst angehängt. Reale isolierte
  netrw-Ansichten ergänzen die synthetischen Grenztests.
- Eingebaute Dateimanageradapter werden direkt nach `filetype` ausgewählt.
  Optionale Adapter besitzen ein festes Laufzeitbudget: Drei wiederholte Fehler
  oder Aufrufe über 5 ms lösen pro Buffer eine fünfsekündige Abkühlung aus.
  Bufferende räumt den Zustand auf; normale Navigation bleibt fail-open.
- `:checkhealth nvim_nvda` zeigt ausschließlich feste Fehler-, Langsamkeits-
  und Abkühlzähler, niemals Fehlertext, Pfade oder Eintragsnamen. Externe
  Adapter müssen synchron, begrenzt und frei von I/O und Polling sein. 99
  Dateimanagerassertionen prüfen den erweiterten Pfad.
- `root` bezeichnet nun die öffentliche Manager-/Branchwurzel und
  `currentDirectory` die fokussierte Ebene. nvim-tree läuft über öffentliche
  Elternknoten zum Root; mini.files trennt Branchanfang und Fokus. Ohne Eintrag
  spricht Fokuskontext nur den letzten Verzeichnisnamen statt eines
  vollständigen lokalen, entfernten oder virtuellen Pfads.
- Neovim 0.10 kann von einem Ex-Befehl wie `:normal` intern ausgeführte Tasten
  erst nach `CmdlineLeave` an `vim.on_key` liefern. Access Link unterscheidet
  sie nun am leeren `typed`-Wert von direkter Eingabe; Befehlstext kann dadurch
  auch auf der Referenzversion keine semantische Cursorbewegung vortäuschen.
  Die vollständigen Lua-Suiten bestehen mit Neovim 0.10.1 und 0.12.3.
- Dateimanagerbuffer behalten nun eine dauerhaft semantische Braillezeile mit
  Name, Typ und Zustand. Routing wird ausschließlich auf einen genau einmal in
  der echten Bufferzeile gefundenen Namen abgebildet; Statussegmente und
  mehrdeutige Namen werden sicher abgewiesen.
- Echte TUI-Tests decken Annahme und Abbruch von `vim.ui.input`, Auswahl über
  `vim.ui.select` sowie Lua-`vim.fn.confirm` mit gewählter Option auf Neovim
  0.10.1 und 0.12.3 ab. Blockierende Prompts werden beim Modusende auch ohne
  `msg_clear` geschlossen; externe UI- und Wrapperereignisse auf 0.12 werden
  auch bei verspäteter Zustellung dedupliziert. Prompt und sichtbare
  Auswahlbezeichnungen sind UTF-8-sicher begrenzt.
- Oils eigener Bestätigungs-Float besitzt kein öffentliches Prompt-Ereignis.
  Ein enger Fallback akzeptiert ausschließlich `oil_preview` in einem echten
  Float und feste Aktionsverben. Er meldet Aktion/Anzahl sowie Y/N, entfernt
  Rohzeile, Name und vollständigen Pfad aus dem semantischen Promptzustand und
  unterdrückt konkurrierende generische Float-Ereignisse. Ein isolierter Test
  mit dem realen Oil-Hauptzweig belegt Abbruch ohne Dateisystemänderung.

## 0.93.0-dev.3 (Featurebranch-Testbuild)

- Das neue Ereignis `fileManagerActionResult` überträgt ausschließlich
  fest typisierte Aktion, Ergebnis, Anzahl, optionalen Basename und optionalen
  Eintragstyp. Vollständige lokale, SSH- oder virtuelle Pfade verlassen die
  Plugin-Ereignisschicht nicht. Erfolgreiche Aktionen stammen aus öffentlichen
  mini.files-, nvim-tree- und Neo-tree-Ereignissen; Oil liefert über
  `OilActionsPost` zusätzlich Fehler und dort erkennbare Abbrüche.
- Mehrere synchrone Aktionen im selben aktiven Buffer/Fenster werden innerhalb
  eines Schedulerzyklus zusammengefasst. Wechselt Buffer, Fenster, Tab oder
  Dateimanager vor der Ausgabe, wird das Ergebnis verworfen. Fehlende
  Fehler-/Abbruchereignisse anderer Plugins werden nicht aus Rendern oder Text
  geraten.
- Sprache und Braille melden kompakt erstellt, hinzugefügt, umbenannt,
  kopiert, verschoben, gelöscht, geändert oder wiederhergestellt. Fehler
  unterbrechen mit hoher Priorität; Abbrüche bleiben Statusmeldungen. 62
  Lua-Assertions und eigene Speech-Regressionen decken Erfolg, Fehler,
  Bündelung, Pfadminimierung und Fokuswechsel ab.

## 0.93.0-dev.2 (Featurebranch-Testbuild)

- Eine getrennte Dateimanager-Ereignisschicht abonniert öffentliche
  Zustandsereignisse von Oil, nvim-tree, Neo-tree und mini.files. Sie liest
  danach ausschließlich den aktiven Buffer beziehungsweise das aktive Fenster
  über die bestehende semantische Adapter-API neu ein, fasst schnelle
  Renderfolgen innerhalb eines Neovim-Schedulerzyklus zusammen und sendet nur
  echte Zustandsänderungen. Es gibt weder Timerabfrage noch Dateisystempolling.
- Markierung und Dateimanager-Clipboard sind getrennte, fest begrenzte
  Zustände. Änderungen am selben Eintrag melden nun markiert, Markierung
  aufgehoben, kopiert, ausgeschnitten, Clipboard geleert sowie geöffnet oder
  geschlossen; Neo-tree-Copy/Cut wird nicht mehr als allgemeines „markiert“
  gesprochen.
- 40 Lua-Assertions prüfen öffentliche Ereignisattrappen, Deduplizierung,
  Zusammenfassung und die Abweisung inaktiver Buffer/Fenster. Speech-Tests
  prüfen vollständige Einträge und die Zustandsdifferenzen.

## 0.93.0-dev.1 (Featurebranch-Testbuild)

- Eingebaute und externe Dateimanageradapter begrenzen Namen auf 512 Byte sowie
  Pfade und Wurzeln auf 2048 Byte jetzt zentral und ausschließlich an gültigen
  UTF-8-Codepointgrenzen. Lange Unicode-Namen können dadurch keine ungültige
  Transportnachricht mehr erzeugen; ungültiger UTF-8-Adapteroutput wird als
  einzelner Wert verworfen.
- Lua-Regressionstests decken exakte und geteilte Zwei-, Drei- und
  Vierbytegrenzen, lange Pfade und ungültige Bytefolgen ab. Die Begrenzung
  bleibt bytebasiert und führt weder Polling noch Dateisystemabfragen ein.

## 0.93.0 (Vorabversion)

- Die Produktversion wurde auf ausdrückliche Vorgabe auf `0.93.0` angehoben.
  Der Releasekanal bleibt unverändert `beta`; der Gesamtstand bleibt zwischen
  Alpha und Beta und wird nicht als stabil eingestuft.
- Enthält die praktisch bestätigten Terminal- und Bufferwechsel-Härtungen,
  strukturierte Kommandozeilen- und Prozessmeldungen, semantische
  Fenster-/Tab-Kontextausgabe sowie die korrigierte erneute F12-Zuordnung von
  einer beendeten lokalen zu einer SSH-Neovim-Sitzung.

## 0.92.0-dev.11 (Featurebranch-Testbuild)

- Eine getrennte, aber noch gemerkte lokale Verbindung zwingt eine neue
  F12-Zuordnung nicht mehr in die lokale Sitzungssuche. Nur eine weiterhin
  authentifizierte Bindung darf ihren lokalen oder SSH-Zieltyp vorgeben. Nach
  dem Ende von lokalem Neovim kann dasselbe WT-Control daher per frischem F12
  wieder gegen alle inventarisierten lokalen und SSH-Sitzungen aufgelöst
  werden; die neue Verbindung ersetzt die veraltete Instanz kontrolliert.
- Die Diagnose unterscheidet nun `selected` von `selectedAuthenticated`, damit
  eine vorhandene Zuordnung nicht mehr mit einer lebenden Neovim-Verbindung
  verwechselt wird. Temporäre Transportabbrüche bleiben fail-open und werden
  nicht allein durch einen Netzwerkstatus automatisch umgebunden.
- Die praktische Abnahme bestätigte die erneute Zuordnung vom beendeten lokalen
  Neovim zur SSH-Sitzung im selben WT-Control ohne weitere Auffälligkeiten.

## 0.92.0-dev.10 (Featurebranch-Testbuild)

- Die Kontextwahl fasst beim Wechsel zwischen Neovim-Fenstern und -Tabs
  Zielposition, Datei- oder Spezialkontext, Änderungs-/Schreibschutzstatus,
  Modus und Verbindungsname in genau einer Ansage zusammen. Ein
  vorausgehendes Modusereignis bleibt dabei sprachlich still; der unabhängige
  Modusklang bleibt erhalten. `No announcement` und `Current line` ändern
  ihr Verhalten nicht.
- Kurze Dateinamen werden mit `file` eindeutig bezeichnet, beispielsweise
  `file T, modified, normal mode`. Terminalpuffer nennen nur den semantischen
  Modus, also `terminal mode` oder `terminal-normal mode`, statt der doppelten
  Form `terminal, terminal mode`. Bereits vorhandene Terminalfenster werden
  nicht mehr mit einem neu durch `:terminal` erzeugten Puffer verwechselt.

## 0.92.0-dev.9 (Featurebranch-Testbuild)

- Die Kontextwahl beim Einstieg über `:terminal` bleibt jetzt auch dann exakt
  einmalig, wenn `contextChanged` vor dem abschließenden
  `terminalNormal`-Modusereignis eintrifft. Initialer Terminaltext und das
  automatische Cursorereignis können danach kein einzelnes „T“, „M“ oder
  anderes Zeilenzeichen ergänzen.
- Der Neovim-Tastenbeobachter behandelt Text in Kommandozeile und direkter
  Terminaleingabe nicht mehr als mögliche Normalmodusbewegung. Damit kann
  etwa das abschließende `l` aus `:terminal` kein späteres Cursorereignis als
  ausdrücklich ausgelöste Zeichenbewegung fehlklassifizieren.

## 0.92.0-dev.8 (Featurebranch-Testbuild)

- Der mit `:terminal` erzeugte Terminalbuffer verwendet beim Einstieg dieselbe
  profilfähige Auswahl wie andere Bufferwechsel. „Keine Ansage“ bleibt still,
  „Aktuelle Zeile“ wartet ereignisgetrieben auf die erste tatsächliche
  Terminalzeile und die Kontextwahl meldet Terminal-Normalmodus und
  Verbindung. Ein automatisches Folge-Cursorereignis kann die Zeile nicht mehr
  durch ihr erstes Zeichen ersetzen.
- Beim anschließenden Eintritt in die direkte Terminaleingabe mit `i` wird die
  vollständige Zeile am Terminalcursor einmal ausgegeben. Sie ersetzt dort
  eine konkurrierende gesprochene Modusansage; der Insert-/Fokusklang und der
  fail-open Passthrough bleiben erhalten.

## 0.92.0-dev.7 (Featurebranch-Testbuild)

- Bei `:bp`, `:bn` und den entsprechenden vollständigen Bufferbefehlen werden
  kurzlebige gesprochene Rückkehrmodi nicht mehr vor die konfigurierte
  Zielausgabe gestellt. „Keine Ansage“ bleibt nach dem Kommando still,
  „Aktuelle Zeile“ spricht nur die vollständige Zielzeile und die Kontextwahl
  spricht Ziel, Modus und Verbindung genau einmal. Der unabhängige Modusklang
  und die Ansage beim Eintritt in die Kommandozeile bleiben erhalten.
- `commandLineType` unterscheidet Ex-Befehle von gleich geschriebenen Suchmustern;
  `/bn` löst daher keine Bufferwechsel-Unterdrückung aus. Ein wirkungsloser
  Bufferbefehl im einzigen Terminalbuffer spricht weiterhin seinen
  strukturierten Hinweis, aber keinen abgebrochenen „terminal-normal mode“.

## 0.92.0-dev.6 (Featurebranch-Testbuild)

- Ein nach `BufEnter`/`BufWinEnter` automatisch folgendes `cursorMoved` kann
  die konfigurierte Zielzeile nicht mehr durch das einzelne Zeichen an der
  Zielspalte ersetzen. Die Ansage ist damit unabhängig von der Cursorposition
  im Ausgangsbuffer.
- `textChanged` vergleicht keine Zeilen verschiedener Buffer mehr. Ein beim
  Sichtbarwerden des Zielbuffers eintreffendes Änderungsereignis wird nicht
  als Eingabe oder Ersetzung des Ausgangstextes ausgegeben.

## 0.92.0-dev.5 (Featurebranch-Testbuild)

- Erfolgreiche Bufferwechsel im selben Tab und Fenster, etwa mit `:bp` oder
  `:bn`, verwenden nun ebenfalls die profilfähige Fokusauswahl: keine Ansage,
  aktuelle Zielzeile oder Zielkontext mit Modus und gespeichertem
  Verbindungsnamen. Die Quelle bleibt `BufEnter`/`contextChanged`; Polling wird
  nicht eingeführt.
- Tab- und Fensterwechsel behalten ihre eigenen Kontextansagen. Modusklänge
  bleiben unabhängig von der gewählten Fokus-/Bufferwechselausgabe.

## 0.92.0-dev.4 (Featurebranch-Testbuild)

- UI-Protokollmeldungen werden unter Neovim 0.12 erst nach Verlassen des
  `vim.ui_attach`-Fast-Event-Callbacks ausgewertet. Dadurch erzeugen
  Zustandsabfragen weder `E5560` noch einen versteckten Enter-Hinweis; Befehle,
  Suche und nachfolgende Meldungen bleiben bedienbar.
- Der lange reale TUI-Test leert den PTY-Ausgabepuffer vor weiteren physischen
  Tasten. Neovim 0.12 kann dadurch nicht mehr an Testausgabe blockieren; das
  ist eine Härtung des Testtreibers, keine Produktverzögerung.

## 0.92.0-dev.3 (Featurebranch-Testbuild)

- Der Eintritt in die Neovim-Kommandozeile besitzt einen eigenen kurzen
  600-Hz-Ton. Der Rückweg aus der Kommandozeile im Terminalkontext verwendet
  den Normalmodusklang; der Zwischenzustand beim Erzeugen eines neuen
  Terminalbuffers erzeugt weiterhin keinen doppelten Klang.
- Ein exaktes `:bd` auf einem noch laufenden Terminaljob meldet vor Neovims
  blockierendem Enter-Hinweis strukturiert `E89`, dass der Buffer nicht
  geschlossen wurde. `:bd!` bleibt eine ausdrücklich destruktive
  Nutzerentscheidung und wird nie automatisch ausgeführt.
- Buffer-Navigationsbefehle wie `:bp` oder `:bn` melden im Terminalkontext
  verständlich, wenn kein anderer gelisteter Buffer vorhanden ist. Bei einem
  tatsächlichen Wechsel bleibt `BufEnter` die ereignisgetriebene Quelle der
  Zielansage; Polling und Terminal-Screen-Scraping werden nicht eingeführt.

## 0.92.0-dev.2 (Featurebranch-Testbuild)

- `modeRaw=nt` wird nicht länger mit dem Normalmodus eines Dateibuffers
  zusammengefasst, sondern als eigener kanonischer `terminalNormal`-Zustand
  gesprochen und mit genau einem Normalmodusklang bestätigt.
- Das Zeichen-Echo der Neovim-Kommandozeile verwendet nun deren eigene
  UTF-8-Byteposition statt der unveränderten Editor-Cursorspalte. Dadurch
  werden Folgetext und Unicode gemäß NVDAs Zeichen-/Wortecho ausgegeben.
- Ein frei belegbarer NVDA-Befehl ohne Standardgeste verlässt direkte
  Terminaleingabe über die feste Neovim-Operation `stopinsert`. Lokaler und
  SSH-Pfad prüfen Anfrage-ID, Instanz, fokussierte Control-Bindung, Buffer,
  Fenster, Tab und exakten Terminalmodus; beliebiger Lua-/Ex-Code ist nicht
  übertragbar. `changedtick` wird bewusst nicht verlangt, weil asynchrone
  Terminalausgabe den Buffer laufend ändert und die Operation keinen Text
  liest oder verändert.
- `TermClose` meldet das Ende des Terminalprozesses mit Exit-Status
  ereignisgetrieben als strukturierte Meldung. Terminal-Screen-Scraping oder
  Polling wird nicht eingeführt.
- Der reale TUI-Test verwendet isolierte XDG- und Runtime-Pfade, damit ein
  lokal installiertes älteres Plugin den getesteten Branch nicht überlagert.

## 0.92.0-dev.1 (Featurebranch-Testbuild)

- Direkte Eingabe in einem eingebetteten Terminal verwendet nun den
  Insert-/Fokusklang; der Übergang in den Terminal-Normalmodus verwendet den
  Normalmodusklang. Der Passthrough-Gate wird jeweils vor der optionalen
  Rückmeldung fail-open umgestellt.
- Der Command-line-Modus bleibt unabhängig von deaktivierter Insert-/Normal-
  Sprachrückmeldung hörbar. Nach Befehlen erscheinende nichtleere
  `msg_show`-Meldungen werden auch bei leerer oder neuer UI-Klassifikation als
  gewöhnliche Meldung in Sprache und Braille ausgegeben; Suchzähler behalten
  ihren eigenen strukturierten Pfad.

## 0.92.0 (Beta-Vorabveröffentlichung)

- Die Produktversion wurde auf ausdrückliche Vorgabe auf `0.92.0` angehoben.
  Der GitHub-Eintrag wird als Pre-Release veröffentlicht.
- Der Releasekanal bleibt `beta`; der Gesamtstand bleibt zwischen Alpha und
  Beta und wird nicht als stabil eingestuft.
- Enthält die einstellbare Fokusausgabe für gebundene Neovim-Sitzungen, die
  control-spezifische Windows-Terminal-Abschottung sowie die ausdrücklich
  ausgelösten Zwischenablagebefehle für lokale und SSH-Verbindungen.

## 0.91.0-dev.4 (unveröffentlichter Featurebranch-Testbuild)

- Ergänzt vier frei belegbare NVDA-Befehle ohne Standardgesten: aktuelle
  Visual-Auswahl nach Windows kopieren, Neovims Register 0 kopieren und
  Windows-Zwischenablagentext über `nvim_paste` einfügen oder in Neovims
  Register 0 speichern und Neovims unbenanntes Register für normales `p`
  darauf zeigen lassen.
- Lokaler und SSH-Pfad verwenden dieselben festen, korrelierten Steuerungen.
  Fokus, Control-Bindung, Instanz, Anfrage-ID, Buffer, Fenster, Tab,
  `changedtick` und Modus werden geprüft; Text ist NUL-frei und auf 256 KiB
  UTF-8 begrenzt. Es gibt kein Polling, Auto-Sync oder Auto-Retry.
- Paste ist auf normale veränderbare Editorbuffer beschränkt. Einmalig
  übertragener Copy-Text wird aus Cache und redigierter Diagnose entfernt.
  Die Erfolgsrückmeldung ist profilfähig als Aus/Sprache/Töne/Beides; Fehler
  bleiben hörbar. Offene Anfragen sind begrenzt.
- Alle vier Befehle wurden im bereitgestellten `dev.4`-Build praktisch ohne
  Probleme bestätigt.
- Frei belegbare Befehle sind im Tastenbefehldialog nun unabhängig von der
  zuvor fokussierten Anwendung sichtbar. Außerhalb eines exakt erkannten
  Windows-Terminal-Controls wird eine zugewiesene Geste unverändert
  weitergegeben; Ereignisse, F12, Overlays und Standardgesten bleiben im
  WT-AppModule. Bereits in früheren Featurebuilds gespeicherte Gestenzuweisungen
  bleiben über undokumentierte Kompatibilitätsaliase wirksam.
- Der `dev.4`-Praxistest bestätigte die Produktkategorie beim Öffnen des
  Tastenbefehldialogs aus einer Fremdanwendung, unveränderte Gestenweitergabe
  außerhalb WT und korrekte Ausführung im gebundenen Neovim-Control.
- 38 Protokoll-, 28 Bridge-, 244 Add-on/Core-/Pakettests und alle
  Lua-Spezifikationen einschließlich 28 Zwischenablageassertionen bestehen;
  Add-on und sechs HTML-Dokumente bauen erfolgreich.

## 0.91.0-dev.1 (unveröffentlichter Featurebranch-Testbuild)

- Ergänzt eine profilfähige Fokusauswahl: keine Ansage, aktuelle strukturierte
  Zeile oder der bisherige Datei-/Spezialkontext mit Modus und Verbindungsname.
  Das bisherige Verhalten bleibt Standard.
- Bestätigter Sitzungsfokus gibt für Insert und Normal unabhängig von der
  Fokusauswahl den durch die vorhandenen Modusklang-Einstellungen erlaubten
  Klang aus.
- Fokuskorrelation, Gate, strukturierte Braillezeile und fail-open Verhalten
  bleiben immer aktiv. Automatisierte Tests decken alle Auswahlwerte,
  Unicode-/Leerzeilen, Braille, Klangtrennung, NVDA-Profile und eine sichere
  Schema-5-Migration ohne erneuten Altdateiimport ab.
- Der praktische NVDA-/WT-Test bestätigte die drei Auswahlwerte und die
  Modusklänge mit lokaler sowie entfernter SSH-Sitzung ohne Probleme.

## 0.91.0 (Beta-Veröffentlichung)

- Übernimmt die control-spezifische Windows-Terminal-Abschottung mit
  fail-open Fokuswechseln und ohne aktivitätsbasierte Umbindung.
- Der Aktivierungsbefehl bleibt überall globaler Ein-/Ausschalter; F12
  autorisiert jeweils genau einen Zuordnungsversuch für das fokussierte
  Terminal-Control.
- Lokale und entfernte Verbindungen in mehreren Tabs sowie horizontale und
  vertikale Split-Panes wurden praktisch ohne Fehler bestätigt.
- Der Gesamtstand bleibt zwischen Alpha und Beta und wird nicht als stabil
  eingestuft.

## 0.90.0-dev.3 (unveröffentlichter Featurebranch-Testbuild)

- Der Praxistest von `dev.1` zeigte zwei gekoppelte Regressionen: F12 blieb im
  zweiten WT-Tab wirkungslos, und der Aktivierungsbefehl konnte dort den Dienst
  nicht mehr ausschalten. Das Vorab-Arming wurde deshalb entfernt.
- Der Aktivierungsbefehl ist wieder in jedem Control der globale
  Ein-/Ausschalter. Bei eingeschaltetem Dienst autorisiert jeder physische
  F12-Druck genau einen Zuordnungsversuch für das exakt fokussierte Control.
- Ohne frischen Neovim-Claim bleibt dieser ausdrückliche Versuch still und
  erzeugt weder Auswahl, Bindung noch Unterdrückung. Regressionstests decken
  den zweiten Tab, die globale Deaktivierung und den stillen Shell-Fall ab.
- Der praktische `dev.3`-Test bestätigte die lokale Zuordnung im ersten Tab,
  eine entfernte F12-Zuordnung im zweiten Tab ohne erneute Aktivierung und die
  globale Deaktivierung aus diesem zweiten Tab vollständig.
- Horizontale und vertikale WT-Split-Panes funktionierten im anschließenden
  Praxistest bei parallelen lokalen und SSH-Verbindungen in anderen Tabs
  fehlerfrei und ohne Querzuordnung.

## 0.90.0-dev.1 (bereitgestellter Featurebranch-Testbuild)

- F12 bleibt der physische Neovim-/Registry-Handshake, wird aber nur noch für
  genau ein zuvor ausdrücklich vorbereitetes WT-`TermControl`, einmalig und
  höchstens 60 Sekunden ausgewertet. Andere Shell-Panes bleiben auch bei
  laufender Unterstützung ohne Suche, Dialog oder Bindung.
- Ein erneuter Aktivierungsbefehl in einem ungebundenen Control armiert dieses
  Control, ohne bestehende lokale oder entfernte Verbindungen in anderen Tabs,
  Split-Panes oder Fenstern zu beenden. Im gebundenen Control bleibt der Befehl
  die globale Deaktivierung.
- WT-AppModule-Instanzen teilen eine einzige Gestenbeobachterregistrierung.
  Netzwerkaktivität einer anderen Instanz kann keine ungebundene Pane mehr
  umbinden oder dort einen Bestätigungsdialog öffnen.
- Fokusverlust suspendiert Unterdrückung fail-open. Gemerkte Verbindungen werden
  beim Wechsel erst nach einer zu Control, Instanz und Request-ID passenden
  frischen Kontextantwort reaktiviert. Mehrere Tabs und Fenster behalten dabei
  getrennte Verbindungen und Editor-Laufzeitzustände.
- Automatisierte Negativ-, Mehrcontrol- und Mehrfenstertests sind ergänzt; der
  praktische NVDA-/WT-Test steht aus. Ein zusätzlicher unabhängiger Nachweis des
  Vordergrundprogramms innerhalb desselben Controls bleibt Folgearbeit.

## 0.90.0 (Beta-Veröffentlichung)

- Übernimmt die praktisch bestätigte Fokus-Kontextansage einschließlich
  Dateiname, Modus und konfiguriertem Verbindungsnamen.
- Der Gesamtstand bleibt zwischen Alpha und Beta und wird nicht als stabil
  eingestuft.

## 0.89.0-dev.3 (unveröffentlichter Featurebranch-Testbuild)

- Fokusansagen nennen zusätzlich den in den Einstellungen vergebenen
  Verbindungsnamen, beispielsweise „on Example“. Lokale Windows-Sitzungen werden
  als „on local“ bezeichnet; technische Hostnamen werden nicht zusätzlich
  offengelegt.

## 0.89.0-dev.2 (unveröffentlichter Featurebranch-Testbuild)

- Beim Rückwechsel aus einer anderen Anwendung in dasselbe registrierte
  WT-Control wird die Fokus-Kontextabfrage nun tatsächlich ausgelöst. Der
  vorherige Frühabbruch hielt die erhaltene authentifizierte Bindung
  fälschlich für ein Fokusereignis innerhalb desselben Controls.

## 0.89.0-dev.1 (unveröffentlichter Featurebranch-Testbuild)

- Ein erneut fokussiertes, authentifiziertes und registriertes WT-Control kann
  Datei beziehungsweise Spezialbuffer, Status und Modus kompakt ausgeben.
- Die Abfrage ist ereignisgetrieben und korreliert. Ungebundene Controls sowie
  verspätete oder nicht mehr passende Antworten bleiben wirkungslos; Polling
  und Terminal-Screen-Scraping werden nicht verwendet.
- Der praktische NVDA-/WT-Test steht aus. Dieser Stand ist nicht stabil und
  bleibt zwischen Alpha und Beta.

Dieses Changelog beschreibt auslieferbare Beta-Stände. Die zahlreichen
experimentellen Vor-Beta-Builds werden nicht einzeln fortgeführt; Git enthält
deren vollständigen Verlauf.

## 0.89.35 (Beta-Veröffentlichung)

- Die Härtung des Registry-Lebenszyklus und die Pflege der
  Windows-Terminal-Bindungen werden nach praktischer Prüfung mit lokalem
  Windows-Neovim und einem SSH-Testziel als Vorabversion veröffentlicht. Der
  Gesamtstand bleibt zwischen Alpha und Beta.
- Vollständige Wirkungslosigkeit in ungebundenen Windows-Terminal-Panes bleibt
  dokumentierte Folgearbeit; unsicherer Unterdrückungszustand bleibt fail-open.

- Die Diagnose von 0.89.34 identifiziert den vermeintlichen F12-Fehler als
  bereits aktive Swap-Datei-Bestätigung (`r?`, confirm, swap), nicht als
  Eingabe- oder RPC-Fehler.
- `ext_messages` und `ext_popupmenu` werden nicht mehr beim Neovim-Start
  angehängt. Die UI-Verantwortung wechselt erst nach Registrierung eines
  authentifizierten Kanals und geht bei Abmeldung, Snapshot- oder RPC-Fehler
  wieder an die native TUI zurück. Swap-Wiederherstellung und andere Abfragen
  vor der Verbindung bleiben dadurch sichtbar und der Terminalpfad bleibt
  fail-open.
- In Hit-Enter-, Pager- oder Bestätigungsmodi beobachtetes F12 schreibt keinen
  Session-Claim. Zuerst muss die native Abfrage beantwortet und danach F12 in
  einem Editormodus gedrückt werden; das Add-on wählt nie selbst eine
  möglicherweise destruktive Swap-Aktion.
- Der Praxistest bestätigte den vollständigen Pfad lokal und über ein SSH-Testziel:
  F12 während der Swap-Rückfrage lieferte keinen Kandidaten, der nächste
  F12-Druck nach ihrer Auflösung verband im Normalmodus, das erste `i` öffnete
  den Insert-Modus und die strukturierte Texteingabe lief normal weiter. Nach
  dem Schließen des ersten Editors trennte sich dessen Client;
  Wiederverbindungsversuche blieben fail-open, und das Deaktivieren der
  Unterstützung stoppte diesen Client, bevor spätere Sitzungen eigene Instanzen
  erhielten.

## 0.89.34 (Diagnose-Testbuild, durch 0.89.35 ersetzt)

- Der Praxistest von 0.89.33 bewies, dass die sichtbare F12-Zuordnung auf
  Windows-Neovims interne Funktionstastenform nicht angewendet wird. Die
  Zuordnung ist wieder entfernt.
- Neovim dokumentiert den Rohmodus `r?` ausdrücklich als `:confirm`-Abfrage.
  Der UI-Meldungsbeobachter behält dafür nur begrenzte Metadaten vor der
  Verbindung: Aktivstatus, Meldungsart, Bytelänge und eine feste Kategorie wie
  Swap, Überschreiben, ungespeicherte Änderungen, Beenden, Löschen oder
  Sonstiges. Prompttext und Pfade werden weder behalten noch gemeldet.

## 0.89.33 (nicht bestandener Korrektur-Testbuild)

- Die Diagnose von 0.89.32 grenzt den Windows-Fehler eindeutig ein: Beide
  Tastenwerte sind genau `<F12>`, Beobachter und Claim sind fehlerfrei, dennoch
  endet Neovims normale Verarbeitung dieser reservierten Taste im
  nichtblockierenden Modus `r?`.
- Die konfigurierte Claim-Taste erhält nun in jedem Neovim-Eingabemodus eine
  stille, sofortige No-op-Zuordnung. `vim.on_key` beobachtet und persistiert den
  Claim weiterhin zuerst; die Zuordnung konsumiert ausschließlich die folgende
  Standardverarbeitung. Vorhandene Benutzerzuordnungen werden nie überschrieben.
- Es wird weder Escape noch andere synthetische Eingabe eingespeist. Ein realer
  PTY-Regressionstest mit Neovim 0.12.3 sendet F12, erkennt den Claim und
  verlangt anschließend Normalmodus.

## 0.89.32 (nicht bestandener Diagnose-Testbuild)

- Der Praxistest von 0.89.31 geriet weiterhin in den blockierenden
  `r?`-/Hit-Enter-Modus. Die Beobachtermetadaten waren im Protokoll vorhanden,
  wurden aber vom expliziten Diagnosefeldfilter des Add-ons ausgelassen.
- Ereignisdiagnosen zeigen nun ausschließlich die zur Eingrenzung nötigen
  begrenzten Felder: Blockierungsstatus, feste aktuelle Fehlernummer/-klasse,
  übersetzte F12-Formen und Bytelängen, Beobachter-/Claim-Fehlerklassen sowie
  den Modus nach dem geplanten Claim. Fehlermeldung und Editorinhalt werden
  nicht zusätzlich protokolliert.
- Zustandsschnappschüsse unterscheiden Neovims Blockierungsflag vom Rohmodus.

## 0.89.31 (Diagnose- und Korrektur-Testbuild)

- Der komplette `vim.on_key`-Beobachter ist jetzt durch `pcall` gekapselt;
  auch der geplante Registry-Claim kann keine Lua-Ausnahme mehr bis in Neovims
  Eingabeschleife tragen. Fehler deaktivieren oder konsumieren keine Taste.
- Das erste `fullState` enthält ausschließlich für einen erkannten F12-Claim
  begrenzte, nicht-sensitive Metadaten: Funktionstastenübersetzung,
  Byte-Längen, feste Fehlerkategorien und den Modus nach dem geplanten Claim.
  Es werden keine normalen Tasten, Meldungstexte oder Editorinhalte erfasst.
- Ein Regressionstest erzwingt einen `keytrans`-Fehler und verlangt, dass er
  Neovims Eingabe nicht verlässt. Ein realer PTY-Test sendet die vollständige
  F12-CSI-Sequenz an Neovim 0.12.3 und prüft Claim sowie Normalmodus.

## 0.89.30 (nicht bestandener Beta-Testbuild)

- Die Registry-Inventur ist wieder rein passiv und öffnet beim Polling keine
  kurzlebigen Neovim-RPC-Kanäle mehr. Zuvor konnten innerhalb von 1,5 Sekunden
  etwa 30 Identitätsabfragen pro Kandidat Neovims Kanal-/UI-Zustand
  beeinflussen. Das ist der belastbarste konkrete Unterschied gegenüber dem
  praktisch bestätigten Stand 0.89.16 und damit die wahrscheinlichste Ursache
  der `r?`-Regression.
- Die `sessionNonce` wird mit dem ausgewählten Registryeintrag bis zum echten,
  dauerhaften RPC-Kanal getragen und dort vor `setup()` und
  `register_channel()` geprüft. Ein Unterschied trennt fail-open und wird nicht
  erneut verbunden. Endpoint-Authentisierung und TOCTOU-Schutz bleiben damit
  ohne zweiten Kanal erhalten.
- Der experimentelle verzögerte Escape aus 0.89.29 ist entfernt; der
  F12-/Eingabepfad entspricht wieder dem praktisch bestätigten Verhalten.
- Die automatisierte Matrix lief mit dem offiziellen Linux-Build von Neovim
  0.12.3. Der Testtreiber lädt dessen optionales `netrw` ausdrücklich;
  versionsabhängige Standarddialogdetails sind kein eigener Protokollvertrag.

## 0.89.29 (Beta-Testbuild)

- 0.89.28 bewies mit leerem `preConnectErrorCode` und
  `preConnectErrorKind`, dass `r?` nicht durch Lua, Snapshot, Registry oder
  Textlock entsteht, sondern als Modus von der vollständig weiterverarbeiteten
  physischen F12-Terminalsequenz zurückbleibt.
- Der bewährte Claim-Pfad bleibt unverändert. Erst 100 ms nach dem
  persistierten Claim, wenn die restlichen Bytes der Terminalsequenz
  verarbeitet sind, speist das Plugin einmal Escape ein. Das liegt deutlich
  vor NVDAs Claim-Auswertung nach 250 ms. Anders als 0.89.26 läuft Escape damit
  nicht vor den noch wartenden F12-Bytes.
- Ein Regressionstest verlangt verzögerten Claim und anschließenden
  Normalmodus; F12 bleibt weiterhin ungebunden.

## 0.89.28 (Diagnose-Testbuild, durch 0.89.29 ersetzt)

- Ergänzt am ersten `fullState` ausschließlich datensparsame Diagnosefelder
  für einen bereits vor der Verbindung gesetzten Neovim-Fehler: nur
  `preConnectErrorCode` und eine feste Fehlerkategorie, niemals Meldungstext,
  Pfade oder Editorinhalt. Damit lässt sich der weiterhin vor der ersten
  normalen Taste vorhandene `r?`-Zustand einer Phase zuordnen, ohne den
  bewährten Eingabepfad erneut zu verändern.

## 0.89.27 (nicht bestandener Beta-Testbuild)

- Stellte den Eingabepfad von `main` wieder her, der erste `fullState` war im
  Praxistest aber weiterhin bereits `r?`. Damit liegt die Ursache vor der
  normalen Eingabe, wahrscheinlich in Claim, Registry-Identitätsprüfung oder
  Verbindungsaufbau; 0.89.28 instrumentiert diese Grenze.

- Die nach 0.89.22 experimentell eingeführten Änderungen am
  `vim.on_key`-Pfad wurden gezielt entfernt: kein F12-No-op-Mapping, kein
  Rohtermcode-Sonderpfad, kein allgemeiner Callback-Wrapper und kein
  künstlich eingespeistes Escape. Der Eingabe- und Claimpfad entspricht damit
  wieder dem auf `main` praktisch bestätigten Stand 0.89.16.
- Erhalten bleiben die von der Eingabe unabhängigen Änderungen: Registry-
  Schema 3, Prozess-/Nonce-Prüfung, robuste WT-Lebenszyklusbehandlung sowie die
  notwendige Neovim-0.12-Signaturkorrektur für `vim.str_utfindex` und das
  fail-open Abbrechen eines tatsächlich fehlerhaften Snapshots.
- Der Vergleichstest verlangt wieder ausdrücklich, dass F12 ungebunden bleibt
  und der bewährte `typed`-Beobachter genau einen verzögerten Claim schreibt.

## 0.89.26 (nicht bestandener Beta-Testbuild)

- Stellte nach F12 zunächst Normalmodus her, erzeugte aber bei der ersten
  normalen Eingabe erneut `r?`. Das künstlich eingespeiste Escape und die
  übrigen experimentellen Eingabeänderungen wurden daher vollständig aus dem
  Registry-Branch entfernt.

- Nach einem erkannten F12-Claim führt das Plugin im geplanten normalen
  Ereigniszyklus Escape aus und stellt damit einen ungefährlichen Normalmodus
  her. Das ist nötig, weil `vim.on_key` nur beobachtet und die interne
  Windows-Terminal-Funktionstastensequenz nicht konsumieren kann; im
  Praxistest von 0.89.25 wurde deren Rest als `v` verarbeitet und Neovim stand
  unmittelbar nach der Verbindung im visuellen Zeichenmodus.
- Ein Regressionstest beginnt absichtlich im visuellen Modus und verlangt,
  dass der verzögerte Claim genau einmal persistiert wird und anschließend
  Normalmodus erreicht ist.

## 0.89.25 (nicht bestandener Beta-Testbuild)

- Erkannte und persistierte F12 wieder, ließ die beobachtete interne
  Tastensequenz aber normal weiterlaufen. Der erste `fullState` zeigte daher
  `modeRaw=v`; die anschließende Bedienung wirkte blockiert.

- Die F12-Erkennung vergleicht im `vim.on_key`-Callback nur noch rohe Strings
  mit einem bereits beim Pluginstart berechneten Termcode. Sie ruft dort vor
  dem Claim weder `keytrans()` noch eine andere Vim-Funktion auf. Damit bleibt
  der Claim unter Neovim 0.12 funktionsfähig, obwohl dessen Textlock solche
  Funktionsaufrufe ablehnt.
- Der Regressionstest lässt `keytrans()` während F12 absichtlich fehlschlagen
  und verlangt trotzdem genau eine verzögert persistierte Claim-Sequenz.

## 0.89.24 (nicht bestandener Beta-Testbuild)

- Verhinderte den sichtbaren Fehler aus dem Eingabebeobachter, kapselte aber
  auch die noch vor dem F12-Vergleich aufgerufene `keytrans()`-Funktion. Unter
  Neovim 0.12 blieb der Fehler dadurch unsichtbar und der Claim aus.

- Die UIA-Lebenszyklusprüfung läuft ausschließlich im periodischen
  Wartungslauf. Sie wurde aus Editorereignissen, Verbindungsstatus und
  Terminalaktionen entfernt, nachdem 0.89.23 einen aktiven fokussierten Tab
  fälschlich als geschlossen entfernt hatte.
- Ein fokussierter Tab gilt immer als lebend. Bei inaktiven Tabs führen erst
  zwei aufeinanderfolgende negative Prüfungen im Abstand von fünf Minuten zur
  Trennung; eine einzelne vorübergehende UIA-Lücke ist nicht-destruktiv.
- Der gesamte `vim.on_key`-Beobachter ist nun eine ausfallsichere
  Nebenbeobachtung: API-Unterschiede oder Textlock-Fehler dürfen keine Taste
  ablehnen und keinen `r?`-/Hit-Enter-Prompt erzeugen. Auch geplante Claim- und
  Rechtschreibprüfungen geben Fehler nicht mehr in Neovims Eingabeschleife
  weiter. Ein Regressionstest simuliert die API-Ablehnung.

## 0.89.23 (nicht bestandener Beta-Testbuild)

- Die Claim-Taste wird weiterhin versionsübergreifend über `vim.on_key` und
  dessen unveränderten `typed`-Wert erkannt. Wenn Neovim `<F12>` regulär als
  Mapping auflöst, konsumiert nun zusätzlich eine stille No-op-Zuordnung die
  Taste nach der Beobachtung. Der Praxistest zeigte dennoch `r?`-/Hit-Enter-
  Prompts, weil Fehler aus dem übrigen Eingabebeobachter noch bis in Neovims
  Eingabeschleife gelangen konnten.

- Snapshots verwenden unter Neovim 0.11 und neuer die neue
  `vim.str_utfindex(text, encoding, index, strict)`-Signatur, unter Neovim 0.10
  weiterhin die alte Signatur. Damit erzeugt lokales Neovim 0.12 beim ersten
  Moduswechsel keinen Lua-/Hit-Enter-Fehler mehr.
- Unerwartete Snapshot-Fehler schließen den Plugin-RPC-Kanal ohne sichtbaren
  Neovim-Fehlerprompt; NVDA trennt dadurch fail-open zur nativen WT-Ausgabe.

- Die periodische Bereinigung geschlossener WT-Bindungen läuft nur noch alle
  fünf Minuten statt alle zwei Sekunden. Unmittelbares Fail-open bei
  Verbindungsabbruch und Registryprüfung bei Discovery bleiben unverändert.

- Die für lokale Registry-Prüfungen benötigte Datei `registry_probe.py` ist
  jetzt im NVDA-Add-on enthalten. Ein Pakettest prüft Datei und relativen
  Import ausdrücklich am extrahierten Installationsarchiv.

- Windows-Terminal-Ereignisse fallen bei jeder unerwarteten Add-on-Ausnahme
  genau einmal auf NVDA's native Verarbeitung zurück und beenden sofort die
  sitzungsbezogene Unterdrückung.
- Die Registry-Lebenszyklusprüfung läuft nicht mehr synchron vor
  `Terminal.event_gainFocus`; NVDA kann daher seine native LiveText-Überwachung
  auch bei einem Fehler in der Add-on-Verwaltung sicher starten.
- Scheitert der periodische Lebenszyklustest unerwartet, beendet er die
  Unterdrückung fail-open und plant sich nicht erneut ein.

- Registry-Schema 3 kombiniert Prozessidentität und eine per RPC bestätigte
  zufällige Sitzungs-Nonce gegen PID-, Port- und Socket-Wiederverwendung.
- Ältere Registry-Schemata ohne vollständigen Identitätsnachweis bleiben
  verborgen; nach dem Komponentenupdate ist dafür ein Neovim-Neustart nötig.
- Registrydateien und Nonce-RPC-Antworten sind absolut zeit- und
  größenbegrenzt. Berechtigungsfehler gelten niemals als Todesnachweis.
- Nur eindeutig tote private Einträge und exakt nonce-eindeutige eigene
  Pluginsockets werden bereinigt. Übernommene oder benutzerdefinierte Pfade
  bleiben unangetastet; Timeouts und Zugriffsfehler sind nicht-destruktiv.
- Geschlossene WT-Tabs und ganze Fenster verlieren ihre Bindung fail-open. Der NVDA-Client
  stoppt nach spätestens der fünfminütigen Sicherheitsprüfung außerhalb des Hauptthreads;
  Neovim- und tmux-Prozesse werden nie
  beendet.
- Mehrtab-/Mehrfenster-Regressionen sowie isolierte SIGKILL-Tests decken lokale
  und entfernte Pfade ab. Inaktive, aber offene Tabs bleiben über ihr direkt geprüftes
  UIA-Element gültig; unklare UIA-Fehler sind nicht-destruktiv.

## 0.89.22 (Beta-Testbuild, durch 0.89.23 ersetzt)

- Korrigierte die Snapshot-Signatur für Neovim 0.12, beseitigte aber nicht die
  anschließende Standardverarbeitung der beobachteten, ungebundenen F12-Taste.

## 0.89.21 (Beta-Testbuild, durch 0.89.22 ersetzt)

- Setzte die WT-Bindungsbereinigung auf fünf Minuten, enthielt aber noch den
  unter Neovim 0.12 inkompatiblen alten `vim.str_utfindex`-Aufruf.

## 0.89.20 (Beta-Testbuild, durch 0.89.21 ersetzt)

- Enthielt bereits die Paketierungs- und Fail-open-Korrekturen, verwendete für
  die reine WT-Bindungsbereinigung aber noch das unnötig kurze
  Zwei-Sekunden-Intervall.

## 0.89.18 (nicht bestandener Beta-Testbuild)

- Das Add-on konnte wegen der fehlenden gepackten Datei `registry_probe.py`
  nicht importiert werden. Einstellungen, Werkzeugmenü, Unterdrückung und der
  periodische Lebenszyklustest wurden deshalb in diesem Build nie gestartet.

## 0.89.17 (nicht bestandener Beta-Testbuild)

- Dieser Build wurde nach materiellen Registry-Änderungen irrtümlich unter
  derselben Versionsnummer erneut erzeugt. Er ist nicht mehr zur Installation
  vorgesehen.
- Im Praxistest konnte bereits das Laden des Add-ons die native Ausgabe von
  Windows Terminal verhindern. 0.89.23 ersetzt diesen Stand mit einer
  ausdrücklichen Fail-open-Barriere.

## 0.89.16 (Beta-Testbuild)

- Der über `typed` erkannte Claim wird mit `vim.schedule()` in Neovims normalen
  Ereigniszyklus verlagert. Der `vim.on_key`-Callback führt damit keine
  Registry-, Dateisystem- oder regulären Vim-Funktionszugriffe mehr aus.
- Der Regressionstest prüft ausdrücklich, dass die Claim-Sequenz während des
  Tastencallbacks unverändert bleibt und erst durch den geplanten Callback
  erhöht wird.
- Der abschließende Praxistest bestätigte wiederholte automatische
  F12-Zuordnungen sowohl mit lokalem Neovim 0.12.3 als auch mit Neovim 0.10.1
  auf einem SSH-Testziel. Bei deaktivierter Unterstützung blieb die Beobachtung inaktiv und
  öffnete keinen Zuordnungsdialog.

## 0.89.15 (nicht bestandener Beta-Testbuild)

- Das Neovim-Plugin erkennt die konfigurierte Claim-Taste nun am unveränderten
  `typed`-Wert seines bestehenden `vim.on_key`-Beobachters. Es verlässt sich
  nicht mehr darauf, dass Neovim 0.10.1 den internen Terminalcode als
  `<F12>`-Mapping auflöst.
- Ein isolierter Test auf diesem SSH-Ziel bewies den Unterschied: Neovim meldete zweimal
  `typed=<F12>`, intern aber `key=<t_…>`; die `<F12>`-Zuordnung lief keinmal
  und der Test endete im Timeout.
- Der NVDA-Beobachter ist bei deaktivierter Unterstützung vollständig inaktiv.
  F12 bleibt dann ein normaler Tastendruck und öffnet keinen Add-on-Dialog.
- Der praktische Test bestätigte die automatische Verbindung zum SSH-Testziel und den
  inaktiven Beobachter bei deaktivierter Unterstützung. Lokales Neovim 0.12.3
  wurde ebenfalls automatisch gefunden und kurz verbunden, wechselte aber
  unmittelbar in den `r?`-/Hit-Enter-Zustand und verlor danach seinen RPC-
  Server. 0.89.16 verschiebt den Registry-Schreibzugriff aus `vim.on_key`.

## 0.89.14 (nicht bestandener Beta-Testbuild)

- F12 ist nicht mehr als NVDA-Skript gebunden und wird nicht mehr synthetisch
  wiedereingespeist. Das nur für Windows Terminal geladene App-Modul beobachtet
  die Geste am öffentlichen `decide_executeGesture`-Erweiterungspunkt, reicht
  sie unverändert an NVDAs normale Auflösung weiter und startet die Claim-Suche
  getrennt über NVDAs Ereigniswarteschlange.
- Ohne gebundenes Skript endet NVDAs Auflösung für F12 mit
  `NoInputGestureAction`; der Keyboard-Hook lässt deshalb den ursprünglichen
  physischen Tastendruck direkt zum Betriebssystem durch. Ein Kontrolltest
  bestätigte drei echte Claims in derselben entfernten Sitzung.
- Der praktische Test bestätigte die automatische lokale Zuordnung; das SSH-Testziel
  blieb jedoch ohne Claim. Die erfolgreiche Verbindung im Bericht stammte von
  der manuellen Profil- und Sitzungsauswahl. Der isolierte Folgetest
  lokalisierte den verbleibenden Fehler in Neovims Terminalcode-zu-Mapping-
  Auflösung.

## 0.89.13 (nicht bestandener Beta-Testbuild)

- F12 wird in Windows Terminal nun erst nach Rückkehr aus NVDAs Eingabe-Hook
  mit einer kurzen GUI-Schleifenverzögerung weitergegeben. Dadurch verarbeitet
  das Terminal die Funktionstaste außerhalb des noch laufenden NVDA-Skripts;
  die begrenzte Claim-Suche beginnt weiterhin erst danach.
- Ein praktischer 0.89.12-Lauf bestätigte lokale Claims und einmalig auch eine
  SSH-Verbindung zum Testziel. Beim folgenden Fehlversuch blieben jedoch beide
  Register der tatsächlich laufenden entfernten Neovim-Prozesse unverändert auf
  `claimSequence=0`; Aktivierung und Deaktivierung hatten ihre Clients dagegen
  ordnungsgemäß beendet und neu erfasst.
- Die verzögerte synthetische Weitergabe blieb im praktischen Test erfolglos.
  Die manuelle Auswahl verband dieselbe Sitzung, und ein anschließend bei
  deaktivierter Unterstützung direkt durchgelassener physischer Tastendruck
  sowie weitere Versuche erhöhten deren Register dagegen bis
  `claimSequence=3`. 0.89.14 entfernt daher die synthetische Weitergabe.

## 0.89.12 (Beta-Testbuild)

- Die lokale automatische Zuordnung übernimmt nun wie der manuelle Pfad einen
  unmittelbar vor der F12-Weitergabe erfassten monotonen Zeitanker. Ein Claim
  gilt als frisch, wenn seine Sequenz gegenüber der Aktivierungsbaseline
  gestiegen ist oder er nach genau diesem Tastendruck geschrieben wurde.
- Ein interaktiver Test von 0.89.11 bestätigte die vollständige Tastenkette bis
  zum erfolgreichen Registry-Claim und begrenzte den verbleibenden Fehler auf
  die Add-on-Auswertung.

## 0.89.11 (nicht bestandener Beta-Testbuild)

- Ein unveränderter interaktiver Test der originalen Produktzuordnung bewies,
  dass F12 bei aktiver NVDA-Unterstützung Neovim überhaupt nicht erreichte.
  Der Rohtasten-Decider wurde deshalb entfernt.
- F12 ist wieder ausschließlich im Windows-Terminal-App-Modul gebunden. Das
  Skript gibt die Originalgeste mit NVDAs öffentlichem `gesture.send()` zuerst
  an Neovim weiter und startet danach die begrenzte Claim-Auswertung.
- Die in 0.89.9 und 0.89.10 erprobten, als Ursache widerlegten Änderungen an
  Neovims Zuordnung wurden zurückgenommen.
- Die Weitergabe und der Neovim-Claim funktionierten praktisch, die alleinige
  Sequenzbaseline der automatischen lokalen Auswertung erkannte den Claim aber
  weiterhin nicht zuverlässig. 0.89.12 ergänzt den tastendruckgebundenen
  Zeitanker.

## 0.89.10 (nicht bestandener Beta-Testbuild)

- Die F12-Zuordnung wird nun wie im erfolgreichen interaktiven Prüflauf für
  jeden Neovim-Modus einzeln registriert. Unter dem getesteten Windows-
  Terminalpfad war die bisherige gemeinsame Mehrmodus-Zuordnung zwar über
  `maparg()` sichtbar, reagierte aber nicht auf die intern als Terminalcode
  dargestellte Funktionstaste.
- Regressionstests prüfen Beschreibung, `nowait` und ausführbaren Callback
  getrennt für Normal-, Insert-, Visual-, Select-, Operator-, Befehlszeilen-
  und Terminalmodus.
- Der praktische Test mit sicher aktualisierten Komponenten schlug weiterhin
  fehl. Ein unveränderter Mapping-Prüflauf zeigte anschließend, dass F12 nicht
  bis zu Neovim gelangte; die Mapping-Änderung war daher nicht ursächlich.

## 0.89.9 (nicht bestandener Beta-Testbuild)

- Die Neovim-Zuordnung für die Sitzungsauswahl wird nun ausdrücklich ohne
  Wartezeit ausgewertet. Ein interaktiver Test zeigte, dass Windows Terminal
  F12 korrekt an Neovim lieferte und der Claim selbst funktionierte, während
  die bisherige dauerhafte Zuordnung in Neovims Mapping-Auflösung hängen
  bleiben konnte.
- Der Regressionstest prüft neben dem wiederholten Claim nun auch die für
  Terminal-Funktionstasten erforderliche `nowait`-Eigenschaft.
- Der praktische Test zeigte, dass `nowait` allein nicht genügte. 0.89.10
  übernimmt zusätzlich die einzelne Registrierung je Modus aus dem
  erfolgreichen interaktiven Prüflauf.

## 0.89.8 (nicht bestandener Beta-Testbuild)

- Die F12-Skriptbindung und künstliche Tastenwiedereinspeisung wurden entfernt.
  Das Windows-Terminal-App-Modul beobachtet die unveränderte physische Taste
  über den öffentlichen NVDA-Erweiterungspunkt `decide_handleRawKey` und lässt
  sie immer normal zu Neovim weiterlaufen.
- Das Add-on wertet den anschließend von Neovim atomar geschriebenen Claim nur
  bei aktivierter Unterstützung und fokussiertem Windows Terminal aus. Andere
  Anwendungen und andere Tasten lösen keine Add-on-Aktion aus.
- Ein interaktiver Prüflauf bewies anschließend, dass die unveränderte Taste
  Neovim erreichte, aber die dauerhafte Neovim-Zuordnung nicht ausgelöst wurde.
  0.89.9 korrigiert diese letzte Zuordnungsstufe.

## 0.89.7 (nicht bestandener Beta-Testbuild)

- Leitete F12 vor der Fokusaktualisierung künstlich wieder ein. Praktische
  Tests zeigten weiterhin zustandsabhängig unveränderte Claim-Zähler; 0.89.8
  entfernt die Wiedereinspeisung vollständig.
- Die in 0.89.6 erprobte aggressive Erneuerung der Neovim-Belegung wurde
  verworfen: Der praktische Test zeigte unveränderte Claim-Zähler und damit
  einen Fehler vor der Neovim-Belegung. Benutzerdefinierte Belegungen werden
  nicht wiederholt überschrieben.

## 0.89.6 (nicht bestandener Beta-Testbuild)

- Erprobte eine wiederholte Erneuerung der F12-Belegung. Der praktische Test
  widerlegte die zugrunde liegende Ursache; dieser Ansatz ist in 0.89.7 wieder
  entfernt.

## 0.89.5 (Beta-Testbuild)

- Unter `NVDA-Menü → Werkzeuge → Neovim Access Link: Remove components...`
  können die eingebetteten Komponenten auf dem lokalen Windows-Rechner und
  auf ausdrücklich ausgewählten gespeicherten Linux-Verbindungen vollständig
  entfernt werden.
- Der zugängliche Mehrfachauswahldialog, die Hintergrundverarbeitung und die
  kompakte Ergebnisübersicht entsprechen dem Installationsablauf. Gespeicherte
  Verbindungen, Neovim- und SSH-Konfiguration sowie fremde Plugins bleiben
  erhalten.

## 0.89.4 (Beta-Testbuild)

- Quick Guide, Handbuch und Entwicklerdokumentation liegen vollständig auf
  Deutsch und Englisch als Markdown-Quellen und getrennte HTML-Ausgaben vor.
- Das Projekt wird unter `GPL-2.0-only` veröffentlicht. Der unveränderte
  Lizenztext wird in beide installierbaren Pakete aufgenommen; Beitragsregeln
  und die zusätzliche Relizenzierungserlaubnis sind getrennt dokumentiert.
- Standarddateien für eine GitHub-Veröffentlichung wurden ergänzt und private
  Produktanforderungen aus dem öffentlichen Quellbaum entfernt.

## 0.89.3 (Beta-Testbuild)

- Quick Guide, Anwenderhandbuch und Entwicklerdokumentation werden als drei
  eigenständige HTML-Dateien mit eigenem Inhaltsverzeichnis und geprüften
  internen Links gebaut.
- Die lokale F12-Nachsuche wartet begrenzt auf verzögert sichtbare atomare
  Registry-Aktualisierungen. Automatische und manuelle lokale Zuordnung wurden
  mit dem installierten Beta-Build praktisch bestätigt.
- Diagnoseberichte unterscheiden lokale und entfernte Sitzungszahlen,
  Nachsuche und Auflösungsabschluss, ohne Editorinhalt offenzulegen.

## 0.89.2 (Beta-Testbuild)

- Ein durch F12 eindeutig bestätigtes lokales Windows-Neovim wird unmittelbar
  ausgewertet und wartet nicht mehr auf langsamere SSH-Sitzungsprüfungen.

## 0.89.1 (erste Beta-Vorbereitung)

- Der sichtbare Produktname lautet „Neovim Access Link“, der Autor ist Emanuel
  Helms. Produktidentität, Version, Buildnummer und NVDA-Kompatibilitätsdaten
  werden ausschließlich in `buildVars.py` gepflegt.
- Manifest, Laufzeitdiagnose und Paketnamen werden aus dieser zentralen Quelle
  abgeleitet. Der interne NVDA-Identifier `nvimNvdaAccess` bleibt zugunsten
  kompatibler Installationen und NVDA-Profile stabil.
- Die Dokumentation wurde nach Sprache und Zielgruppe gegliedert. Bekannte
  Ausnahmen von öffentlichen NVDA-APIs sind in ADR-0002 begründet.

## Zusammenfassung der Vor-Beta-Entwicklung

- Das Produkt wechselte auf Protokoll v2 mit SSH-stdio für Linux und einem
  strikt an `127.0.0.1` gebundenen lokalen Neovim-RPC-Transport für Windows.
  Alte allgemeine TCP-, Tunnel-, Token- und v1-Pfade wurden entfernt.
- Das Add-on installiert Bridge, Protokollcode, MessagePack, Plugin und
  Zuordnungskonfiguration rootlos aus dem eingebetteten Paket. Mehrere Ziele
  werden im Hintergrund aktualisiert und zugänglich zusammengefasst.
- Verbindungsprofile und Laufzeitinstanzen wurden getrennt. Mehrere lokale und
  entfernte Sitzungen, Konten, Tabs, Fenster und tmux-Kontexte können parallel
  über eine ausdrückliche F12-Markierung gebunden werden; ein Standardziel ist
  nicht erforderlich.
- Windows-Terminal-spezifische Ereignisse, Gesten und Unterdrückung wurden in
  das NVDA-AppModule verschoben. Fremde Anwendungen bleiben unberührt;
  Deaktivierung, Fehler und Verbindungsverlust öffnen die normale
  Terminalausgabe wieder.
- Strukturierte Sprache und Braille wurden um Modi, Navigation, Bearbeitung,
  Auswahl, Completion, Menüs, Suche, Diagnostics, Folds, Marks, Register,
  Makros und verbreitete Dateimanager erweitert.
- Einstellungen verwenden NVDAs reguläre Konfigurationsprofile. Komponenten-
  und Verbindungsdialoge laufen zugänglich und blockieren NVDAs Hauptthread
  nicht.
