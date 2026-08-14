# Aktueller Status

Stand: 14. August 2026. Der Quellstand entwickelt die Linie 0.99.0;
`buildVars.py` erzeugt Artefakte als 0.99.0-dev.3 mit Branch- und
Commitmetadaten und setzt den Update-Kanal im Manifest auf Beta. Der aktuelle
veröffentlichte Pre-Release ist 0.98.0.
Das Projekt leitet aus Testumfang oder Funktionsmenge keine höhere
Stabilitätseinstufung ab.

Diese Seite ist die kompakte Momentaufnahme des implementierten und geprüften
Stands. [Architektur](architecture.md) und
[Funktionsmatrix](accessibility.md) erklären Details; das
[Changelog](changelog.md) beschreibt abgeschlossene Änderungen und der
[Plan](plan.md) künftige Arbeit.

## Referenzumgebung

Der hauptsächliche praktische Pfad wurde mit Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x, lokalem Neovim 0.12.3 sowie Neovim 0.10.1 und 0.12.3
auf Rocky Linux 10.2 über OpenSSH für Windows 9.5p2 geprüft. Lokales
Windows-Neovim, Linux-Neovim über SSH und tmux innerhalb einer SSH-Sitzung
sind abgedeckt. Der abschließende Feldtest des Entwicklungsbuilds 3 unter
NVDA 2026.2beta10 umfasste automatische F12-Bindungen, häufige Wechsel zwischen
lokalem und entferntem Pane sowie einem weiteren Windows-Terminal-Fenster, das
Beenden und erneute Starten des entfernten Neovim und natives Tippecho außerhalb
der aktiven Sitzung. Die Bindungen blieben getrennt und aktiv; getrennte
SSH-Zustandsabbilder lösten keine falschen Wiederverbindungen aus. Das Manifest
nennt deshalb 2026.2 als zuletzt getestete NVDA-Version.
Die vollständigen Plattform- und Versionsgrenzen stehen in
[Kompatibilität](compatibility.md).

## Implementierter Gesamtpfad

### Installation, Verbindung und Besitzgrenzen

- Das `.nvda-addon` enthält NVDA-Integration, Neovim-Plugin und ein rootloses
  Linux-Benutzerpaket mit Bridge, Protokoll und Installer. Das oberste
  `Neovim Access Link`-Menü öffnet Einstellungen, Komponentenverwaltung und
  vier lokalisierte installierte HTML-Dokumente.
- Die Komponenteninstallation kann über eine standardmäßig unveränderte
  Konfigurationsauswahl eine kleine Grundkonfiguration mit Lazy und Oil
  installieren. Vorhandene reguläre `init.lua` und `init.vim` werden zuerst in
  eindeutige Sicherungspfade verschoben; der Ergebnisdialog nennt Installation
  und Sicherungen. Die Grundkonfiguration verwendet echte Tabulatorzeichen in
  einem Zwei-Spalten-Raster auch nach dateitypspezifischen Vorgaben, keine
  Zeilennummern und Leader-Befehle für Oil und Lazy. Ein isolierter
  Headless-Start mit echten lokalen Access-Link-, Lazy- und Oil-Verzeichnissen
  ist unter Neovim 0.10.1 geprüft. Alternativ kopiert sie die vollständige
  lokale Windows-Konfiguration auf ausgewählte Linux-Verbindungen, nachdem
  Links, Dateitypen, Pfade und Größen begrenzt und geprüft wurden. Eine
  vorhandene Linux-Konfiguration wird als vollständiges Verzeichnis atomar
  gesichert.
  Windows-spezifischen Inhalt verändert das Add-on nicht; Lazy muss die
  installierte Access-Link-Kopie ausdrücklich als lokales Plugin laden.
  Automatisierte Tests decken Archivierung, lokale und rootlose
  Linux-Paketpfade, SSH-Übertragung und Rollback ab. Die Grundkonfiguration ist
  lokal unter Windows praktisch abgenommen; die Konfigurationsübernahme auf
  Linux über SSH steht praktisch noch aus.
- Die Komponentenentfernung verlangt nach der Zielauswahl eine ausdrückliche,
  standardmäßig abgelehnte Bestätigung. Sie entfernt lokal nur das installierte
  Plugin und auf Linux zusätzlich Bridge und zugehörige Komponentenpfade.
  Neovim-Konfigurationen und Sicherungen bleiben unverändert; ausdrückliche
  Plugin-Ladeeinträge bleiben der Benutzerkonfiguration überlassen.
- Das Manifest folgt dem NVDA-Template mit Projektadresse,
  Standardhilfedatei, Update-Kanal und lokalisiertem Änderungsprotokoll.
  Entwicklungsbuilds der Linie 0.99.0 verwenden den Abschnitt
  `Unveröffentlicht`; die Store-Vergleichsversion bleibt bis zu einer
  tatsächlichen Store-Veröffentlichung 0.96.0. Der Paketbuild verwirft fehlende,
  leere, unbekannte oder fehlerhaft formatierte Templatefelder und prüft die
  englische Standardhilfe sowie das deutsche Lokalisierungsmanifest.
- Der Dokumentationsjob verwendet wie der lokale Referenzbuild den offiziellen
  Pandoc-3.1.11.1-Binärbuild aus einem prüfsummengesicherten Archiv. Das
  Buildskript lehnt abweichend paketierte Builds derselben Version ab. Dadurch
  bleibt die eingecheckte installierte HTML-Hilfe reproduzierbar.
- `NVDA+Alt+N` ist die voreingestellte, im Tastenbefehlsdialog änderbare
  Aktivierungsgeste. Sie gehört weiterhin dem Windows-Terminal-AppModule;
  außerhalb eines passenden fokussierten Controls bleibt der native
  Tastaturpfad erhalten.
- Lokale Sitzungen verwenden dynamisches, nur an `127.0.0.1` gebundenes TCP;
  entfernte Sitzungen verwenden SSH-stdin/stdout und einen privaten
  Unix-RPC-Socket. Sitzungen werden aus kurzlebigen JSON-Dateien erkannt, nicht
  aus der Windows-Registry.
- Ein physischer F12-Druck ordnet die laufende Neovim-Instanz dem exakt
  fokussierten Windows-Terminal-Control zu. Mehrere Fenster, Tabs und Panes
  halten unabhängige lokale, entfernte oder normale Shell-Sitzungen.
- Eine erfolgreiche F12-Zuordnung wird ohne Rückfrage automatisch für das
  konkrete Control bis zum Ende von NVDA oder Windows Terminal gemerkt. Sie
  bleibt reine Laufzeitinformation; es gibt weder eine Profilentscheidung noch
  eine zugehörige Einstellung. Beim Fokuswechsel wird die laufende Sitzung erst
  nach erneut korreliert bestätigtem Vordergrundkontext aktiviert. Die native
  Terminalausgabe einschließlich Tippecho bleibt bis dahin fail-open.
- Authentifizierung, Sequenzen, Heartbeats, Resync und Fokuskorrelation
  begrenzen den dauerhaften Pfad. Trennung, ungültiger Zustand oder unsichere
  Fokusidentität geben NVDAs natives Terminalverhalten fail-open frei.
  Eine neue Transport-Sitzung wird nur durch `fullState` mit Sequenz 0
  übernommen; boolesche oder negative Hüllensequenzen und Zeitstempel werden
  verworfen. Nach einer Sequenzlücke beendet nur ein neueres Zustandsabbild
  derselben Sitzung den Resync-Zustand.
  Beim Ende einer entfernten Neovim-Instanz übersetzt der SSH-Client den
  Bridge-Lebenszyklusstatus unmittelbar in denselben Fail-open-Pfad wie eine
  lokale RPC-Trennung, auch wenn SSH-Prozess und Bridge weiterlaufen. Während
  dieser Trennung angeforderte Zustandsabbilder authentifizieren die Instanz
  nicht erneut; erst `fullState` mit einem verbundenen Neovim-Zustand darf
  wieder einen Verbindungsübergang auslösen. Ein automatisierter Grenztest
  bildet dafür ein gemischtes lokales/SSH-Pane-Szenario mit beendeter
  Remote-Instanz und wiederholtem Fokuswechsel nach.
- Windows-Terminal-Ereignisse und `nextHandler` gehören dem AppModule.
  Getrennte Dienste besitzen Fokus, Sitzungszuordnung, Verbindungen,
  Editorzustand, Einstellungen, Präsentation und Laufzeit. Das Global Plugin
  erzeugt und schließt nur noch die transaktional zusammengesetzte Runtime.
  Verbindungsworkflow, Laufzeitpflege temporärer Bindungen,
  Terminalaktionen und Ereignislieferung haben eigene Besitzer; AppModule und
  Brailleadapter sehen nur ihre statischen Ports. Ausgehende Controls verwenden
  eine begrenzte Queue und bleiben je Client geordnet, während ein fester
  Workerpool unabhängige Clients voneinander isoliert. Ein zweiter fester Pool
  übernimmt jeden bereits abgetrennten Client bis zu dessen Stopp. Ausschalten
  und Teardown warten deshalb nicht auf Transport-I/O. Den aktuellen Schnitt
  beschreibt die
  [Architektur](architecture.md); der datierte Anhang C bewahrt nur die
  damalige Prüfgrundlage.

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
- Native inkrementelle Suche meldet Vorschautreffer, begrenzte Trefferzahlen,
  Umbrüche am Bufferende und sichtbare Suchhervorhebung. Direkte
  `inccommand`-Ersetzungen im aktuellen Buffer melden für `nosplit` und
  `split` die Vorschauzeile und die begrenzte Anzahl betroffener Zeilen.
- Quickfix- und Positionslisten melden Anzahl, Position und die vollständige
  ausgewählte Trefferzeile. Native Ersetzungsabfragen nennen Zeile und
  Position, bevor Neovim die Antwort verarbeitet.
- Bufferlokale Ersetzungen verwenden Neovims Ergebnismeldung oder ersatzweise
  die beobachtete Zahl geänderter Zeilen. Mehrbuffer-Ersetzungen erhalten eine
  einzige Zusammenfassung beobachteter geänderter und ungespeicherter Buffer;
  Neovims interne Bufferwechsel erscheinen nicht als Fokuswechsel.
  Automatisierte Tests decken Quickfix-Dateien, gelistete Buffer und
  Argumentdateien einschließlich eines zunächst ungeladenen Argumentbuffers
  ab. Die geführten L4- und L6-Abläufe sind noch nicht vollständig praktisch
  unter Windows/NVDA abgenommen.
- Diagnosen aus `vim.diagnostic` lassen sich nach aktueller, vorheriger,
  nächster, erster und letzter Position lesen. Gehaltene Diagnoseansichten,
  Fehler-, Warn- und Leerbestätigungsklänge verwenden denselben validierten
  Datenpfad.
- Neovims native `z=`-Vorschläge sind mit Sprache, Braille und kontextbezogenen
  NVDA-Befehlen zugänglich. Rechtschreibfeedback folgt NVDAs getrennten
  Dokumentformatierungsoptionen.
- Neovims eingebauter `:Tutor` bleibt vollständig Neovim-eigen. Access Link
  liest ab Neovim 0.12 ausschließlich dessen native, eindeutige Extmarks in
  Tutor-Puffern, spricht Zustandswechsel nur im unveränderten Buffer-, Fenster-
  und Zeilenkontext sowie die Bewertung beim erneuten Lesen der Zeile und zeigt
  `✓` beziehungsweise `✗` dauerhaft, aber nicht routbar,
  hinter dem Braille-Zeilentext. Ein bufferlokaler Textbeobachter entsteht erst
  im Tutor-Puffer; es gibt kein Polling und keine zusätzlichen
  Steuerungsnachrichten. Zustandswerte anderer Typen oder außerhalb dieses
  Kontexts werden vor der kanonischen Zustandsübernahme verworfen. Unter
  Neovim 0.10 bleibt Tutor unverändert bei
  Neovim, und Access Link registriert dafür keine Beobachter. Beide Grenzen
  sowie der 0.12-Pfad sind headless, der 0.12-Pfad zusätzlich über eine
  isolierte echte TUI automatisiert geprüft. Ein eigener GitHub-Actions-Job
  führt den nativen Lua-Vertrag und genau diesen aktuellen Socket-/TUI-Test
  unter dem festgelegten Neovim 0.12.3 aus.

### Entwicklungswerkzeuge, Terminal und Dateien

- LSP-Daten und Diagnosen bleiben providerneutral. Automatisierte Verträge
  bestehen für native LSP-Completion, `nvim-cmp`, `blink.cmp`, `nvim-lint`,
  ALE und `none-ls.nvim`; Benutzer installieren die jeweiligen externen
  Sprachserver und Linter selbst.
- Lazys öffentlicher `nofile`-/`lazy`-Puffer erhält einen eindeutigen
  Fokuskontext. Beim Öffnen werden die aktuelle Bedienzeile und bei der
  Zeilennavigation der Inhalt ohne rein visuelle Leerzeichen am Zeilenende
  gesprochen. Dokumentierte Lebenszyklusereignisse melden Beginn und Ende
  von Installation, Aktualisierung, Bereinigung, Prüfung, Protokollansicht und
  Synchronisierung neutral über Sprache und Braille. Pluginzeilen, virtueller
  Fortschritt und Erfolg werden nicht abgeleitet. Die geführten P1- bis
  P4-Abläufe wurden im Windows-/NVDA-Referenzpfad praktisch bestätigt.
- Native LSP-Umbenennung bleibt vollständig bei Neovim und dem Sprachserver.
  Access Link beobachtet `LspRequest` und tatsächliche Bufferänderungen und
  fasst interne Text-, Cursor- und Kontextänderungen zu einem belegbaren
  Abschluss zusammen. Der geführte L5-Test gibt beide tatsächlich umbenannten
  Referenzzeilen ohne zusätzlichen Puffer- oder Fokuswechsel aus. Dieser Ablauf
  ist automatisiert, noch nicht praktisch unter Windows/NVDA abgenommen.
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
synchronisiert. Der Dokumentationsbuild prüft außerdem die vollständigen
deutschen und englischen Dateisätze, parallele Überschriftenstrukturen,
Markdownlinks, generierte HTML-Ziele sowie Sprach-, Titel- und
Beschreibungsmetadaten. GitHub Actions führt diesen Build als eigenen Job aus.
Windows-Nutzer können zusätzlich mit `build.cmd` parameterlos einen aktuellen
Entwicklungsstand bauen. Der Wrapper verwendet nur ein temporäres
Python-Environment und lässt den regulären Build- und CI-Weg unverändert.

## Prüfnachweis

Automatisierte Suiten prüfen Protokoll und Begrenzungen, Bridge, lokale und
SSH-Clients, mehrere Instanzen, Fokus und Fail-open-Verhalten, Editor- und
Präsentationsplanung, Lua mit echten headless-Neovim-Prozessen, Paketinhalt,
Lokalisierung sowie Dokumentationslinks. Gepinnte Läufe verwenden je nach
Testzweck Neovim 0.10.1 oder 0.12.3 und reale Completion-, LSP-, Diagnose- und
Linterpfade. Das Clang-Tidy-Profil verwendet direkt das gepinnte Programm,
legt C11 sowie die mitgelieferte Testkonfiguration explizit fest und führt
Standard- und Fehlerausgabe zusammen. Das
Markdownlint-Profil prüft die absolute Testdatei statt eines stdin-Kaltstarts;
beide Parser erhalten Windows-Laufwerks- und UNC-Pfade vollständig.
Die öffentliche Neovim-Plugin-Fassade komponiert getrennte Besitzer für
Kanal, Eingabe, Completion, Befehlszeile, UI-Prompts, Oil-Bestätigungen und
Kontextwechsel. Der Kanal behandelt Zustandserfassung, Payload-Erweiterung und
RPC-Versand als eine Fail-open-Grenze. Eingabepräfixe sind ein einzelner
markierter Zustand. Bei einem internen Publikationsfehler schließt der Kanal
auch den realen RPC-Transport. Ein Verbindungswechsel verwirft alte geplante
Controllerereignisse und setzt transiente Menü-, Prompt- und Laufzeitzustände
vor dem nächsten `fullState` still zurück. Semantische Lua-Tests prüfen reale
RPC-Serialisierungsfehler, schnelle Reconnects, Menülebenszyklen, gekoppelte
Präfixbefehle, wiederholtes Setup sowie Completion- und
Befehlszeilenübergänge; der Add-on-Test prüft die identische Aufnahme der
getesteten Module statt ihrer internen Quelltextform.
Reale TUI-Tests leeren über eine gemeinsame Sendehilfe eine zeitlich und nach
Datenmenge begrenzte ausstehende PTY-Ausgabe vor jedem physischen Tastenschritt.
Jeder isolierte Runner-Job besitzt zusätzlich ein festes Zeitlimit; dessen
Abbruch beendet die gesamte eigene Prozessgruppe einschließlich gestarteter
Neovim- und Hilfsprozesse.
Die abgeschlossene Unit-Test-Nachprüfung prüft die extrahierten NVDA-Runtime-
Eigentümer direkt, während vollständige Kompositionsverträge in der verkleinerten
Paketfixture verbleiben. Mockisolierte Bridge-Verträge und echte TUI-/Socket-
Szenarien sind getrennte, dateibasiert klassifizierte Suiten. Vier gezielte
Protokollmutationen müssen an Bool-/Integer-Grenze, exakter Feldmenge,
Größenobergrenze und Sitzungssequenz scheitern. Der Runner weist außerdem
Skip-Gründe und Python-Warnungen auch bei erfolgreichen Jobs aus.
Für reale Provider gilt in Vorprüfung und Testhilfe eine einheitliche,
begrenzte Wartezeit von 60 Sekunden. Damit bleiben kalte Starts auf Windows
und Netzlaufwerken zulässig, ohne einen hängenden Provider unbegrenzt abzuwarten.
Listenerfreie, SSH- und echte Sockettests laufen getrennt. Einzelheiten und
Befehle stehen in [Teststrategie](testing.md).
Geführte Praxistests isolieren die verbleibende Wahrnehmungsprüfung von
Sprache, Braille, Klängen, Fokus und Reaktionszeit. Ihre technische Vorprüfung
bestätigt reale Providerdaten und die für die jeweilige Aufgabe isolierte
Tastensteuerung. Die Kompatibilitätssuite enthält zusätzlich vier lazy.nvim-
Aufgaben mit vollständig lokalen Git-Fixtures für Fenster, Installation,
Aktualisierung und Synchronisierung; die Einzelauswahl gruppiert sie unter
Plugin-Verwaltung. Die Headless-Vorprüfung verlangt keine dort absichtlich
unterdrückte Lazy-Oberfläche; sie prüft den öffentlichen Befehl und die
isolierte Fixture-Konfiguration. Die Fixture-Repositories deaktivieren
Zeilenendenkonvertierung und unnötige Git-Ausgaben. Aufbau und sichere
Tastenbelegung stehen in
[Geführte Praxistests](human-testing.md).
Optionale leere Pfadlisten bleiben im PowerShell-Runner echte JSON-Arrays; die
Lua-Verifikation normalisiert zusätzlich älteres oder fremdes JSON-`null`,
bevor F5 die tatsächlichen Git-Zustände prüft. Die Bestätigung nennt nur die
belegten Ziele mit erwarteter Revision sowie gegebenenfalls das nachweislich
entfernte Ziel.
Im echten Lazy-Puffer überträgt das Plugin außerdem den auf 2048 UTF-8-Byte
begrenzten ersten zusammenhängenden Textblock. Er erscheint beim Rendern erst
nach dem anfänglichen Kontextwechsel; Access Link spricht ihn dann genau einmal
als vollständige Bedienleiste, trotz Layout-Leerzeile und
fensterbreitenabhängigem Umbruch. Zeilenweise Navigation unterdrückt rein
visuelle Rand- und Auffüll-Leerzeichen. In einem exakt als `nofile`/`lazy`
erkannten Puffer entfernt die Sprachplanung private Unicode-Zeichen aus allen
Sprachanteilen; Sprachexploration ist darin eingeschlossen. Der unveränderte
Quelltext bleibt Grundlage für Braille, Cursor und Routing. Die aktuelle
Pluginzeile wird nur aus Lazys dokumentierten Icon-Hervorhebungen erkannt. Eine
unmittelbar folgende `dir`-Eigenschaft mit dokumentierter `LazyProp`-Extmark
kennzeichnet sie als ausgeklappt. Sprache verwendet NVDAs lokalisierte Zustände
`eingeklappt` und `ausgeklappt`; Braille hängt wie NVDAs Baumansichten `+` oder
`-` an die Zeile.
Ein Zustandswechsel erzeugt keine vorübergehende Braillemeldung und verdeckt
damit den aktualisierten Marker nicht. Die Bedienleiste lässt sich nach der
Öffnung mit der vorhandenen NVDA-Zeilenexploration erneut lesen. Bei unbekannter
oder mehrdeutiger Darstellung bleibt Access Link still.

Praktisch bestätigt wurden insbesondere:

- Installation und Aktualisierung lokaler und entfernter Komponenten;
- parallele lokale und SSH-Sitzungen in mehreren Fenstern, Tabs und Panes;
- Fokuswechsel zwischen verbundenem Neovim und normalen Shell-Controls;
- Navigation, Sprachexploration, Modus-, Buffer- und Terminalwechsel;
- Braille-Routing, beide Braillemodi und Rechtschreibvorschläge mit einer
  Papenmeier BRAILLEX EL 80c;
- lazy.nvim-Fenster, Sprachexploration, Braillemarker sowie Installation,
  Aktualisierung und Synchronisierung mit isolierten lokalen Test-Plugins;
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
