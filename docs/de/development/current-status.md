# Aktueller Status

Stand: 5. August 2026. Der Quellstand gehört zur Entwicklungslinie 0.97.0.
Die genaue Entwicklungsbuildnummer und die Git-Metadaten werden beim Build aus
`buildVars.py` erzeugt und deshalb in dieser Momentaufnahme nicht wiederholt.

Der aktuell veröffentlichte Beta-Pre-Release bleibt 0.96.0; sein
GitHub-Veröffentlichungslink und die versionsbezogenen deutschen und
englischen Changelog-Links bleiben prominent in `README.md`. Die vom Projekt
festgelegte Reife ist Beta. Diese Dokumentation leitet aus Testumfang,
Versionsnummer oder Funktionsmenge keine darüber hinausgehende
Stabilitätseinstufung ab.

Der Prüfansatz ist risikoorientiert und nach bestem Wissen, nicht vollständig.
Automatisierte Suiten und praktische Referenzabläufe können nicht jede
Kombination aus NVDA, Windows Terminal, Neovim, SSH, Plugins und Benutzerdaten
vorwegnehmen. Fehlerberichte werden nach Möglichkeit zeitnah reproduziert,
priorisiert und korrigiert; dieses Kapitel verspricht weder Fehlerfreiheit noch
feste Reaktionszeiten.

Dieses Kapitel ist eine Momentaufnahme. Die Entstehung einzelner Funktionen
steht im `changelog.md`; geplante Arbeit steht in `plan.md`. Alte
Featurebranch-Berichte und zwischenzeitliche Testbuilds sind keine Beschreibung
des aktuellen Produkts und werden hier deshalb nicht chronologisch wiederholt.

Repositoryprüfungen in GitHub Actions trennen die listenerfreie Standardsuite,
echte gepinnte Completion-Plugin-Verträge, reale Diagnose-Provider- und
Linterprozesse, den geführten Human-Test-Runner unter Windows PowerShell,
simulierte SSH-/Askpass-Pfade und echte wegwerfbare TCP-/Unix-Socket-Fälle in
unabhängige Jobs. Der Windows-Job prüft Runner, beide Sprachen,
Testdefinitionen und Ergebnisvertrag, erklärt aber keine Wahrnehmungsaufgabe
als menschlich bestanden. Die
Completion-Matrix prüft Neovim 0.10.1/0.12.3, `nvim-cmp`, `blink.cmp` v1 und
den vorläufigen v2-Stand. Die Diagnosematrix prüft auf beiden
Neovim-Versionen `nvim-lint` und ALE mit sieben echten Lintern für C, Python,
Bash, Go, Rust, Ruby und Markdown sowie die LSP-Brücke `none-ls.nvim`. Die
listenerfreie Standardsuite startet außerdem einen kleinen deterministischen
LSP-Server über stdio und prüft damit Signaturhilfe, Parameterdokumentation und
Hover-Rückfall durch Neovims echten LSP-Client. Die Jobs verwenden weder
produktive SSH-Ziele noch private Infrastruktur und ersetzen keine praktische
Windows-/NVDA-Prüfung.

## Referenzumgebung

Der hauptsächliche praktische Pfad wurde mit dieser Umgebung geprüft:

- Windows 11 25H2, 64 Bit;
- NVDA 2026.1.1;
- Windows Terminal 1.24.x;
- `OpenSSH_for_Windows_9.5p2` mit LibreSSL 3.8.2 und Schlüsselanmeldung;
- Rocky Linux 10.2;
- Neovim 0.10.1 und Python 3.12.13 auf Linux.

Lokales `nvim.exe` unter Windows ist automatisiert mit Neovim 0.10.1 geprüft.
Die F12-Zuordnung, parallele lokale und SSH-Sitzungen sowie Oil wurden praktisch
auch mit Neovim 0.12.3 geprüft. Das macht 0.12.3 nicht zur alleinigen
Referenzversion; optionale neuere APIs bleiben durch Featuretests abgesichert.

Die vollständigen Plattformgrenzen stehen in `compatibility.md`.

## Implementierter Gesamtpfad

### Installation und Verbindungen

- Das `.nvda-addon` enthält das NVDA-Add-on, das lokale Neovim-Plugin und ein
  rootloses Linux-Benutzerpaket mit Plugin, Bridge, Protokoll und Installer.
- Der Komponenten-Dialog kann lokale und gespeicherte SSH-Ziele installieren,
  aktualisieren und entfernen. Zur Zielmaschine ist kein Laufzeitdownload
  erforderlich.
- Lokale Windows-Sitzungen verwenden einen dynamischen, ausschließlich an
  `127.0.0.1` gebundenen Neovim-RPC-Port.
- Entfernte Linux-Sitzungen verwenden Protokoll v2 über SSH-stdin/stdout und
  einen privaten Unix-RPC-Socket auf dem Ziel.
- Die dateibasierte Session-Registry entdeckt laufende Neovim-Instanzen. Sie
  ist nicht die Windows-Registry.
- Ein physischer F12-Druck ordnet die fokussierte Neovim-Sitzung dem konkreten
  Windows-Terminal-Control zu. Tabs, Panes und Fenster können getrennte lokale
  oder entfernte Verbindungen halten.
- Nonce, Sitzungskennung, Sequenznummern, Heartbeats, Resync und der erste
  gültige `fullState` begrenzen und authentifizieren den dauerhaften Pfad.
- Fokusverlust, Deaktivierung, Protokollfehler und Transportende geben native
  Terminalausgabe fail-open wieder frei.
- Das Windows-Terminal-AppModule und das strukturierte Braille-Overlay greifen
  über einen schmalen `TerminalIntegrationService` auf den gemeinsamen Dienst
  zu. Feste Befehlswerte und unveränderliche Fokus- und Claim-Ergebnisse
  verhindern private oder dynamische Aufrufe über die AppModule-Grenze.
- Ein eigener `SettingsService` besitzt Laden, Normalisierung, Speichern und
  NVDA-Profilwechsel. Präsentation und Werkzeugdialoge erhalten nur Snapshots
  oder schmale Operationen; der `NvdaUiManager` kennt keine Global-Plugin-
  Instanz.
- Ein `TerminalFocusService` besitzt Terminalidentität, Fokusgeneration,
  AppModule-/Adapterkorrelation und den periodischen Lifecycle-Sweep. Unsichere
  UIA-Ergebnisse fallen offen aus; geschlossene, nicht fokussierte Controls
  werden erst nach zwei eindeutigen Negativprüfungen bereinigt.
- Die abgeschlossene V2-4-Extraktion übergibt `SessionClaimService` die
  alleinige Zuständigkeit für einmalige F12-Autorisierung, Claim-Generationen und Claim-
  Inventarzustand. Lokale und SSH-Inventar- und Sitzungslisten-Worker,
  Discovery-Generation sowie Kandidatenauswertung laufen hinter diesem Dienst.
  Er entscheidet außerdem unveränderlich zwischen lokaler, entfernter und
  automatischer Auflösung sowie den Ergebnissen einer Sitzungssuche. Aus dem
  gemeinsamen Instanzzustand plant er jetzt auch Wiederverwendung oder Start
  lokaler und entfernter Sitzungen einschließlich einer gegebenenfalls zu
  ersetzenden Instanz. Einen aktuellen Wiederverwendungsplan wendet er auf die
  Instanzbindungen an und liefert verdrängte Terminalidentitäten zur
  NVDA-seitigen Fokusbereinigung zurück. Start, Bindung und Runtime-Auswahl
  neuer Instanzen bilden dort ebenfalls einen Übergang; Rückrollen und das
  Stilllegen einer ersetzten Instanz beenden Clients asynchron. NVDA-Meldungen,
  Dialoge und fokusbezogene Nebenwirkungen behalten ihre
  bisherigen Hauptthreadgrenzen. Auch die explizite Instanzauswahl und
  Trennung sind neutrale Dienstübergänge: Auswahlfehler stellen die vorherige
  Bindung wieder her, Trennung entfernt Runtimezustand und Bindung vor dem
  asynchronen Clientstopp. Die Wiederherstellung gemerkter Bindungen wird dort
  fail-open vorbereitet und erzeugt je nach Authentifizierung eine korrelierte
  Fokuskontext- oder Vollzustandsanforderung. Verzögerung und Transportaufruf
  bleiben am NVDA-Rand. Der Dienst besitzt außerdem den ausstehenden
  Merkvorgang für temporäre Terminalbindungen und prüft Fokus, Control,
  Instanz und Auswahl nach NVDAs verwalteter modaler Rückfrage erneut. Dialog,
  Meldung und Diagnostik bleiben NVDA-seitig. Eine einmalige, korrelierte
  Reaktivierung überbrückt ausschließlich den Fokusverlust dieser Rückfrage.
  Bleibt das erwartete Windows-Terminal-Fokusereignis aus oder zeigt NVDAs
  Cache noch den geschlossenen Dialog, prüft ein kurzer begrenzter Wiederanlauf
  zusätzlich das tatsächlich fokussierte NVDA-Objekt. Nur die vollständig
  gleiche Terminalidentität verwendet die korrelierte Fokuskontext-Anfrage;
  jede Unsicherheit bleibt fail-open. Dabei zählt ein wieder fokussiertes
  Terminalobjekt erst nach bestätigtem Fokuskontext als aktive Bindung. Ein
  noch nicht ausgeführter Handshake wird idempotent vorgezogen; lehnt der
  Transport das Senden vorübergehend ab, folgen höchstens drei begrenzte
  Wiederholungen. Eine bereits gemerkte Tab-Identität
  behält ihre Merkentscheidung auch bei einer neuen, erneut mit F12
  autorisierten Neovim-Instanz und erzeugt keinen redundanten Dialog. Eine
  Ablehnung erzeugt keine dauerhafte Bindung. Eine injizierte `ManagedClientFactory`
  konstruiert lokale TCP- und entfernte SSH-Clients mit instanzkorrelierten
  Callbacks. Der Claimdienst verbindet diese Konstruktion mit seinem
  transaktionalen Startübergang; Profil, Passwort und übersetzte Ausgabe
  verbleiben am NVDA-Rand. Das Global Plugin verwendet Claimziele,
  Berechtigungen und Baselines nur noch über schmale Dienstoperationen;
  schreibbare Zustandskopien werden nicht geteilt.
- Der anschließende Praxis-Meilenstein ist mit mehreren Fenstern, Tabs und
  Panes, gemischten lokalen und entfernten Sitzungen sowie den
  Zwischenablagepfaden abgeschlossen. V2-5 hat daraufhin begonnen: Ein
  `EditorSessionController` mutiert den aktiven instanzgetrennten
  Editorzustand, wechselt dessen Runtime, verarbeitet Modus-, Menü-,
  Transport- und Verbindungszustand und erzeugt geordnete neutrale Aktionen
  für strukturiertes Tippecho. Er besitzt außerdem die begrenzten
  Zwischenablage-, Register- und Terminalsteuerungsanfragen, korreliert ihre
  Antworten mit Instanz und Terminalidentität und entfernt einmaligen
  Zwischenablagetext vor der weiteren Zustandsverarbeitung. Transportaufruf,
  Fokus-/Gate-Prüfung, Windows-Zwischenablage und konkrete Ausgabe bleiben am
  NVDA-Rand. Der Controller bündelt Zustandsübergang, Terminal-Passthrough,
  Modusklangentscheidung und neutrale Sprachaktionen in einem
  unveränderlichen Ereignisplan. Er speichert außerdem den entstehenden
  Passthroughzustand für die aktive Instanz und ergänzt den gespeicherten
  Verbindungsnamen in einer getrennten Kopie eines bereits validierten Fokus-
  oder Kontextereignisses. Das Global Plugin wendet die Gate-Entscheidung an
  und liefert den Plan über `NvdaPresentation` aus. Der Braillepfad erhält vom
  Controller einen isolierten Zeilenplan; semantisches Cursor-Routing wird
  dort gegen Capability, aktiven Client und vollständigen Editorzustand
  validiert. Terminalbestätigung, Instanzauthentifizierung, NVDA-Overlay und
  konkreter Transport bleiben außerhalb. Zwischenablage-, Register- und
  eingebettete Terminalaktionen erhalten ebenfalls erst nach Capability-,
  Modus-, Buffer- und kanonischer Zustandsprüfung einen unveränderlichen
  ausgehenden Allowlist-Plan. Eine Ablehnung erzeugt keinen ausstehenden
  Request; exakte Terminalprüfung, Windows-Zwischenablage, Rückmeldung und
  Senden verbleiben am NVDA-Rand. Der abschließende Audit führt auch das
  Zurücksetzen des semantischen Planers und den Zugriff auf instanzbezogene
  Completion-Dokumentation durch den Controller. V2-5 ist automatisiert
  abgeschlossen. Seine sieben vorübergehenden
  Global-Plugin-Kompatibilitätseigenschaften wurden inzwischen in V2-6
  entfernt.
- V2-6 ist abgeschlossen und begann mit einem normalen `AddonRuntime`. Er
  veröffentlicht den
  vollständigen Terminaldienst erst nach der prozessweiten Registrierung und
  besitzt eine feste, wiederholbare Abbaureihenfolge. Entfernen des Dienstes
  und fail-open Gate-Öffnung geschehen vor Verbindungs- und
  Zustandsbereinigung; UI und Präsentation schließen zuletzt. Einzelne
  Bereinigungsfehler werden diagnostiziert, ohne spätere Schritte zu stoppen;
  ein später Initialisierungsfehler rollt Registrierungen zurück.
- Der zweite V2-6-Schnitt entfernt die früheren Global-Plugin-Sichten auf
  Editorplaner, Zustand, Modus, Tippecho, Completion-Dokumentation und
  Transport-Capabilities. Tests verwenden nun die tatsächliche Besitzgrenze
  von Coordinator und Controller.
- Der dritte V2-6-Schnitt entfernt entsprechend die früheren
  Global-Plugin-Sichten auf ausstehende Claims, Inventargeneration und
  -bereitschaft, Baselines, zulässige Ziele, Inventarfehler und
  Discovery-Generation. Tests verwenden nun den besitzenden
  `SessionClaimService`; verbliebene Kompatibilitätssichten betreffen spätere
  Verbindungs- oder Fokusmigration und werden vor einer Entfernung separat
  geprüft.
- Der vierte V2-6-Schnitt entfernt elf weitere passive Sichten ohne
  Produktivaufrufer. Sound-Cache-Tests verwenden `NvdaPresentation`;
  Bindungs-, Runtime- und Requesttests den `ConnectionCoordinator`;
  AppModule- und Adapterfokusdaten verbleiben im `TerminalFocusService`.
  Aktive Verbindungs-, Gate-, Fokusobjekt- und Lifecyclesichten benötigen
  weiterhin einen getrennten Produktivaudit.
- Der fünfte V2-6-Schnitt schließt die Bereinigung der
  Fokus-/Lifecycle-Kompatibilität ab. Die Brailleaktualisierung liest das
  fokussierte Terminalobjekt aus `TerminalFocusService`; Lifecycletests ändern
  den Zeitwert direkt an diesem Dienst. Aktive Verbindungs- und Gatesichten
  verbleiben für ihren eigenen Audit.
- Der sechste V2-6-Schnitt entfernt sieben Sichten auf aktiven Client- und
  Verbindungszustand. Produktion und Tests verwenden den
  `ConnectionCoordinator` nun direkt für aktiven Client und aktive Instanz,
  Verbindungsstatus, authentifizierte Instanzen, Terminal-Passthrough und
  zurückgestellte Full-States.
- Der siebte V2-6-Schnitt schließt den öffentlichen Terminaldienst unmittelbar
  nach dem Unpublish und sichert eingereihte Runtimecallbacks nochmals beim
  Aufruf ab. Veraltete Dienstreferenzen und verspätete Claim-, Netzwerk-,
  Braille- oder Scheduleraufrufe bleiben dadurch wirkungslos und fail-open.
  Gate und Instanzmanager bleiben nach getrenntem Audit als häufig verwendete
  Kompositionsabhängigkeiten bestehen; eine weitere Indirektion würde keine
  klarere Besitzgrenze schaffen.
- Der achte V2-6-Schnitt bündelt auch die Aktivierung in `AddonRuntime`.
  Profilcallback, UI und Veröffentlichung erfolgen genau einmal in dieser
  Reihenfolge; Fehler an jeder Grenze lösen denselben vollständigen Teardown
  aus. Das Global Plugin markiert Registrierung und Publish nicht mehr über
  getrennte Übergangsaufrufe.
- Der neunte V2-6-Schnitt beseitigt die doppelte Verbindungsbereinigung im
  Teardown. `AddonRuntime` invalidiert Claim und Fokus, stoppt Clients einmal
  über den Coordinator-Eigentümer und löscht dessen Laufzeitstand danach
  einmal. `_stopClient()` bleibt ausschließlich für aktive Nutzer- und
  Profilwechselpfade erhalten.
- Der zehnte V2-6-Schnitt entfernt die breite Global-Plugin-Rückreferenz aus
  dem öffentlichen `TerminalIntegrationService`. Eine vollständige feste
  Befehlszuordnung und schmale Callbacks ersetzen den freien Zugriff auf die
  Kompositionswurzel; Fokus-, F12- und Brailledienste bleiben getrennt.
- Der elfte V2-6-Schnitt verschiebt Brailleregion und Terminaloverlay in
  `nvda_braille.py`. Die neutrale `service_registry.py` besitzt die
  prozessweite Dienstveröffentlichung; weder dieser Registry-Baustein noch das
  Braillemodul importiert das Global Plugin.
- Der abschließende V2-6-Strukturaudit entfernt die letzte nur von Tests
  verwendete Runtimefabrik und ergänzt Abhängigkeitsprüfungen am Paket. Die
  Kompositionswurzel behält genau zwei häufig verwendete
  Kompositionssichten auf Gate und Instanzmanager. Dort verbleibt kein
  AppModule-Ereigniseinstieg, und keiner
  der ausgelagerten Runtime- oder NVDA-Randdienste hängt von der
  `GlobalPlugin`-Klasse ab. Weitere Auslagerungen werden bewusst gestoppt,
  solange kein zusätzlicher Gewinn bei Besitz, Zuverlässigkeit oder
  Testbarkeit belegt ist. V2-6 und Praxis-Meilenstein 2 sind ohne neu
  gemeldeten Fehler abgeschlossen. Die spätere praktische Prüfung des
  `z=`-Vorschlagspfads mit einer physischen Braillezeile war erfolgreich; eine
  breitere Braillematrix bleibt offen.
- Ein erneuter Strukturaudit vom 4. August 2026 bestätigt den erreichten
  Anwendungsschnitt: Ereigniseinstiege, Overlayauswahl, `nextHandler`,
  konfigurierbare Skriptmetadaten und Eingabebeobachter liegen weiterhin im
  Windows-Terminal-AppModule; ausgelagerte Dienste hängen nicht von der
  `GlobalPlugin`-Klasse ab. Er präzisiert zugleich, dass die konkrete Klasse
  heute noch ein umfangreicher prozessweiter NVDA-Randcontroller und keine
  rein minimale Kompositionswurzel ist. Der öffentliche Terminaldienst ist
  hinsichtlich Vertrauen und Besitz begrenzt, besitzt aber eine breite
  Methodenoberfläche. Weitere Zerlegung bleibt deshalb eine schrittweise
  Option mit konkretem Besitz- oder Testnutzen, keine Verschiebung gemeinsamer
  Abläufe in das AppModule und kein LOC-Selbstzweck. Siehe [Anhang C](global-plugin-appmodule-audit-2026-08-04.md).

### Editorausgabe

Der semantische Pfad deckt unter anderem ab:

- Normal-, Insert-, Replace-, Visual-, Kommandozeilen- und Terminalmodi;
- zeichen-, wort- und zeilenweise Navigation sowie Datei- und Zeilengrenzen;
- Eingabe, Löschen, Ersetzen, Auswahl und Suchtreffer;
- eingebaute Completion, `nvim-cmp`, `blink.cmp`, versionsübergreifende
  Signaturhilfe und LSP-Hover, Diagnosen, Folds und Meldungen;
- typisierte Kommandozeile und korrelierte Rückkehrmeldung eines Ex-Befehls;
- konfigurierbare Fokusausgabe: keine Ansage, aktuelle Zeile oder Kontext mit
  Modus und gespeichertem Verbindungsnamen;
- getrennte Sprach-, Klang- und dauerhafte Brailleplanung.

Completion verarbeitet nur den ausgewählten Kandidaten und meldet dessen
Position, lokalisierten LSP-Typ, Parameter und Quelle. Nachgeladene
Dokumentation von Neovims eingebauter LSP-Completion und `nvim-cmp`
aktualisiert den instanzbezogenen Abrufbefehl still. Neovims interne
Vorschauaktualisierung erscheint nicht nachträglich in `complete_info()`.
Fehlt die Dokumentation am ursprünglichen Kandidaten, löst der native Pfad
deshalb nur die aktuelle Auswahl zusätzlich über den öffentlichen
`completionItem/resolve`-Vertrag auf und verwirft veraltete Antworten.
Der von Neovims eingebauter Completion bewusst verwendete Zustand ohne
ausgewählten Kandidaten zwischen letztem und erstem Vorschlag wird als eigener
semantischer Zustand in Sprache und Braille gemeldet und leert die zuvor
ausgewählte Dokumentation.
Echte Modulanbindung ist automatisiert gegen den aktuellen `nvim-cmp`-Stand,
`blink.cmp` v1.10.2 und den vorläufigen v2-Zweig geprüft; eine vollständige
TUI-/Windows-/NVDA-Konfigurationsmatrix bleibt offen. `blink.cmp` kann
ausschließlich intern aufgelöste Dokumentation noch nicht öffentlich liefern;
Ghost Text ohne Menü ist kein zugängliches Auswahlmenü.

LSP-Hover gibt automatisch nur die erste aussagekräftige Zeile aus. Die
vollständige, instanzgetrennte Dokumentation ist über denselben frei belegbaren
Befehl wie Completion-Dokumentation lesbar und wird bei Cursor-, Modus- oder
Bufferkontextwechsel still verworfen.
`:NvimNvdaLspStatus` gibt den begrenzten Clientstatus des aktuellen Buffers auf
Anforderung aus. Fortschritt wird zur Vermeidung einer Sprachflut nicht
automatisch angesagt.

Im Einfügemodus verfolgt Access Link den aktiven Parameter eines
Funktionsaufrufs automatisch. Ein begrenzter, Tree-sitter-unterstützter
Resolver wählt bei Verschachtelung den innersten Aufruf und ignoriert
Klammern in Zeichenketten und Kommentaren. Nach 120 ms Ruhe wird öffentliche
LSP-Signaturhilfe mit Trigger-/Retriggerkontext angefragt. Ausschließlich
`activeSignature` und `activeParameter` des Servers bestimmen die Ansage;
Kommas werden nicht lokal gezählt. Exakte Generation, Buffer-, Fenster-,
Textstand-, Modus-, Cursor- und Aufrufprüfung verwirft veraltete Antworten.
Bewegung im selben Argument bleibt still, Rückkehr in ein bereits ausgefülltes
früheres Argument spricht erneut. Das Ereignis ist validierte reine Sprache
und ersetzt niemals die Quelltext-Braillezeile. Die Funktion ist
profilabhängig abschaltbar.

`NVDA+Leertaste` startet eine korrelierte, rein lesende Abfrage von
LSP-Signaturhilfe mit Hover-Rückfall. Sie funktioniert auf dem Funktionsnamen
sowie der unmittelbar zugehörigen öffnenden und schließenden Aufrufklammer,
ohne den echten Cursor zu verschieben. Solange die NVDA-Taste gehalten wird,
schalten `NVDA+h/l` lokal ausschließlich durch die Parameter der gewählten
Signatur und `NVDA+k/j` ausschließlich durch Signaturen. Jede Signatur besitzt
einen unabhängigen, bei 1 beginnenden Parameterstand. Erstansicht und
Signaturwechsel zeigen Signatur samt Dokumentation, Parameterwechsel nur den
Parameter; der erste Parameterbefehl nach einer solchen Signaturansicht blendet
den ausgewählten Parameter ein, ohne ihn bereits zu überspringen. Sprache und
Braille mischen beide Achsen nicht. Längere Inhalte
blättern ohne Rückfall in die Quelltextnavigation.
Ein eigener instanzgetrennter Controller bindet die Anzeige an die exakte
Fokus-, Buffer-, Fenster-, Tab-, `changedtick`- und Cursoridentität; jede
Abweichung verwirft Antwort und Braillemeldung.
Das Windows-Terminal-AppModule übernimmt `NVDA+Leertaste` und
`NVDA+Umschalt+Leertaste` nur bei exakt fokussierter, authentifizierter
Instanz mit der jeweils benötigten Fähigkeit. Ohne diese Autorisierung bleibt
NVDAs normale Skriptauflösung erhalten; Access Link sendet in diesem
Rückfallpfad insbesondere keine Leertaste an das Terminal.

Allgemeine Diagnostics werden unabhängig von ihrer Herkunft über
`vim.diagnostic` validiert, begrenzt und deterministisch ausgewählt. Fünf
frei belegbare Neovim-Befehle lesen beziehungsweise erreichen vorherige,
nächste, erste, letzte und aktuelle Diagnose, ohne bestehende Mappings zu
ändern. Reale gepinnte Linux-Tests bestätigen `nvim-lint` und ALE mit
Clang-Tidy für C, Ruff für Python, ShellCheck für Bash, Staticcheck für Go,
Clippy für Rust, RuboCop für Ruby und `markdownlint-cli2` für Markdown sowie
den `none-ls.nvim`-LSP-Brückenpfad auf Neovim 0.10.1/0.12.3. Diese
automatisierte Providerabdeckung ist keine praktische Windows-/NVDA-Abnahme.
Native LSP-Wege wie `gopls` und `rust-analyzer` verwenden denselben Vertrag,
bleiben aber Teil der später gebündelten Praxisrunde.
Direkt getippte native `[d`-/`]d`-Sprünge bleiben auch dann semantisch
beobachtbar, wenn ein aufrufspezifischer Callback Neovims globalen
Diagnosesprung-Hook ersetzt.
`NVDA+Umschalt+Leertaste` hält eine begrenzte Liste der Diagnosen am Cursor und auf
der aktuellen Zeile; `NVDA+k/j` schaltet ohne echte Cursorbewegung. Eine
textfreie Diagnosezusammenfassung ermöglicht getrennt konfigurierbare Fehler-
und Warnklänge beim Betreten einer Diagnosezeile und an jeder durch
ausdrückliche Navigation erreichten Position in einem exakten Bereich.
Eine ausdrückliche Positions- oder Zeilenabfrage ohne Treffer meldet das leere
Ergebnis und verwendet abhängig von derselben Einstellung einen dritten
kurzen Bestätigungsklang; passive Bewegung über fehlerfreie Zeilen sowie
Informationen und Hinweise bleiben klanglos. Die drei Signale stammen aus dem
MIT-lizenzierten Code-OSS-Quellstand von Visual Studio Code; Commit,
Prüfsummen, Konvertierung und Lizenz sind im Add-on dokumentiert.

Die dauerhafte Brailleausgabe folgt derselben semantischen Editorquelle wie
Sprache und Klang, besitzt aber eine getrennte Planung. Eine öffentliche
`braille.TextInfoRegion` übersetzt den vollständigen Zeilentext. Im
Braille-Cursormodus meldet `braille.handler.handleCaretMove` semantische
Cursorbewegungen an NVDA, sodass der sichtbare Ausschnitt bei langen Zeilen
dem Cursor nach NVDAs Standardverhalten folgt. Leere Zeilen sowie die
Einfügeposition hinter dem letzten Zeichen bleiben als routbare
cursortragende Zelle darstellbar.

Routing funktioniert in Normal-, Insert- und Befehlszeilenmodus. Es verwendet
NVDAs öffentliche `brailleToRawPos`-Abbildung und setzt den Neovim-Cursor erst
nach Fokus-, Capability-, Zustands-, Modus-, `changedtick`- und
UTF-8-Prüfung. Ein optionales Quellzeichen wird über
`speech.speakSpelling` benannt. Doppelte und dreifache Routingbetätigung kann
konfiguriert feste Wort- oder Zeilenaktionen auslösen; es wird niemals
übertragener Befehlstext ausgeführt.

NVDAs horizontale Braillenavigation verschiebt den sichtbaren Ausschnitt.
Vorherige/nächste Zeile verwendet einen festen semantischen
`moveBrailleLine`-Auftrag und behält Neovims bevorzugte sichtbare Spalte.
Der unabhängige Braille-Explorationsmodus liest Zeilen dagegen ohne Bewegung
des echten Cursors. Er besitzt eigene Korrelations- und Lua-Zustände, hält
virtuelle Zeile, Lesespalte und manuell gewählten Ausschnitt bei echten
Cursorbewegungen fest und aktualisiert nur betroffene explorierte Inhalte.
Beim bestätigten Sessionfokus bleibt die konfigurierte Fokusansage hörbar,
übernimmt im Braille-Explorationsmodus aber nicht den vorübergehenden
Braille-Nachrichtenpuffer; der wiederhergestellte Ausschnitt wird daher sofort
sichtbar.
Die Moduswahl und nummerierte native Auswahllisten liegen in der Runtime der
jeweiligen Neovim-Instanz. Mehrere lokale oder entfernte Sessions können ihren
Braille-Cursor- oder Explorationsmodus daher unabhängig wählen. Ein
Control- oder Anwendungswechsel erhält virtuelle Position, Lesespalte und
horizontalen NVDA-Ausschnitt in der zugehörigen Session-Runtime, verwirft aber
fokusgebundene Eingabefolgen. Bei der Rückkehr gilt wieder genau die Ansicht
dieser Session. Ein Disconnect setzt nur die betroffene Runtime zurück.
Ein Braillecursor erscheint dort ausschließlich, wenn er dem einen echten
Neovim-Cursor entspricht. Routing übernimmt die virtuelle Position bewusst in
den echten Cursor. Der Sprachexplorationsmodus bleibt eine getrennte
Sprachfunktion; optional kann seine vollständige virtuelle Zeile auf Braille
erscheinen.

AppModule, Overlay, Core-Controller, Capability-gehandeltes Protokoll,
Neovim-Adapter und lokaler wie SSH-Transport bleiben getrennt. Sämtliche
optionalen Rückkanäle laufen über den begrenzten `ControlDispatcher`, sodass
kein Braillepfad Netzwerk-I/O auf NVDAs Hauptthread ausführt. Eine volle oder
geschlossene Queue verwirft die Aktion fail-open. Dauerhafte Region, Routing,
Navigation und Exploration verwenden für den wiederhergestellten Ausschnitt
nur NVDAs öffentliche `BrailleBuffer.windowStartPos`-Eigenschaft und lesen
keine privaten Treiber- oder Scrollzustände. Die einzige Braille-spezifische
private Ausnahme betrifft die
gezielt besessene Lebensdauer der vorübergehenden
Rechtschreibvorschlagsmeldung und ist in ADR-0002 begründet.

Protokollvalidatoren, Core, Paketinhalt, NVDA-Adapter, Lua, lokaler und
SSH-Transport sowie echte Neovim-RPC-Abläufe sind automatisiert abgedeckt.
Routing, lange Zeilen, Zeilengrenzen, Navigation, beide Braillemodi,
Routingaktionen und Rechtschreibvorschläge wurden praktisch mit einer
Papenmeier BRAILLEX EL 80c bestätigt. Das belegt den Referenzpfad, nicht jede
Braillezeile, Tabelle, Sprache oder Treiberkombination.

Der kontextbezogene Sprachexplorationsmodus verwendet `NVDA+h/j/k/l` und
`Umschalt+NVDA+h/l`. Diese Befehle lesen Zeichen, Zeilen
oder Wörter an einer flüchtigen Position, ohne den echten Cursor zu bewegen.
AppModule-, Protokoll-, Controller-, Dispatcher- und Lua-Tests sind vorhanden;
Zeichen-, Wort- und Zeilenexploration, Abschlussansage, Ursprungsklang und
rückwärtige Wortbewegung wurden unter NVDA praktisch bestätigt. Auch die
profilfähige, getrennte Detailauswahl für normale Wort-/Zeilennavigation und
den Explorationsabschluss wurde praktisch ohne festgestellte Fehler geprüft.
Dieser Nachweis bestätigt den getesteten Grundpfad, nicht jede denkbare
Tastaturbelegung, Sprache oder Plugin-Kombination.

Version 0.96.0 ergänzt eine zugängliche Bedienung von Neovims eingebauter
`z=`-Rechtschreibliste. Ein strikter Lua-Adapter erkennt
nur die belegte native Abfrage; ein neutraler Controller hält deren Auswahl
flüchtig.
`NVDA+j/k` wählt zyklisch, Sprache und Braille zeigen den Vorschlag ohne
Nummer, und `NVDA+Eingabe` bestätigt nur den validierten Index. Loslassen der
NVDA-Taste verwirft die lokale Auswahl und lässt Neovims Prompt offen.
Eine profilfähige, einsbasierte Einstellung verschiebt die vorübergehende
Braillemeldung auf ein späteres Modul; ungültige oder zu weit rechts liegende
Werte werden sicher angepasst. Protokoll, lokaler und SSH-Transport, echter
Neovim-RPC, Controller, AppModule, Brailleplanung und gebautes Add-on sind
automatisiert geprüft. Eine praktische Windows-/NVDA-Abnahme einschließlich
einer physischen Braillezeile war erfolgreich; breitere Braillehardware bleibt
ungeprüft.

Die Funktionstabelle und bekannte Unterschiede stehen in
`accessibility.md`.

### Terminal- und Dateimanagerpfade

- Terminal-Insert und `terminalNormal` sind eigene Zustände. Direkte
  Terminaleingabe aktiviert Passthrough; ein frei belegbarer NVDA-Befehl kann
  über den festen `stopinsert`-Pfad in Terminal-Normal zurückkehren.
- Kommandozeilentext, Rückkehrmodus, Meldungen, Bufferwechsel sowie
  Fenster-/Tabwechsel werden strukturiert korreliert, nicht aus sichtbarem
  Terminaltext geraten.
- Oil, netrw, mini.files, nvim-tree und Neo-tree besitzen normalisierte
  Dateimanagereinträge und automatisierte Workflowabdeckung. Navigation,
  bearbeitete Namen, Grenzklänge und Bestätigungsabläufe wurden praktisch
  bislang nur für Oil unter Windows/NVDA geprüft.
- Oil bildet eine brauchbare praktische Grundlage. Für die anderen Manager ist
  die vorhandene automatisierte oder isolierte Abdeckung keine praktische
  Freigabeempfehlung.

### Zwischenablage

Vier frei belegbare Befehle des Windows-Terminal-AppModules können:

- die aktive Visual-Auswahl nach Windows kopieren;
- Neovims Register 0 nach Windows kopieren;
- Windows-Zwischenablagentext über `nvim_paste` einfügen;
- oder Register 0 ersetzen und das unbenannte Register darauf zeigen lassen.

Lokal und über SSH gilt derselbe korrelierte, größenbegrenzte Pfad. Es gibt
keine automatische Synchronisation und keine automatische Wiederholung. Diese
und die übrigen frei belegbaren Terminalbefehle erscheinen im
Tastenbefehldialog zunächst, wenn Windows Terminal vor dessen Öffnen fokussiert
war; in fremden Anwendungen werden sie nicht aufgelöst. Sobald die AppModule-
Klasse geladen ist, kann NVDA eine gespeicherte Zuordnung während dieses Laufs
andernorts weiter auflisten, ohne ihre Ausführung global zu machen.

### Lokalisierung und Dokumentation

- Englisch ist die Quellsprache der Projektoberfläche; ein vollständiger
  deutscher NVDA-gettext-Katalog wird mitgebaut.
- Manifest, Einstellungen, Werkzeugdialoge, Meldungen und Speech-Plannertexte
  durchlaufen die Übersetzungsprüfung.
- Quick Guide, Handbuch, Entwicklerdokumentation und geführter
  Praxistest-Leitfaden werden jeweils als deutsches und englisches HTML
  erzeugt.
- Die neu bearbeiteten Braille-, Sprachexplorations- und Statustexte sind in
  beiden Sprachen inhaltlich abgeglichen. Ältere englische Handbuch- und
  Entwicklerkapitel sind teilweise Kurzfassungen und noch nicht vollständig
  inhaltsgleich; ihre Angleichung steht im aktiven Plan.

## Aktueller Prüfnachweis

Die gepflegten automatisierten Prüfungen umfassen:

- Lua-Spezifikationen und echte headless-Neovim-Läufe;
- Protokoll-, lokaler Client-, SSH-stdio- und Bridge-Tests;
- NVDA-unabhängige Zustands-, Sprach-, Braille- und Gate-Tests;
- Add-on-Integrations- und gebaute-Pakettests;
- Lokalisierungs-, Manifest-, Archiv- und Dokumentationsprüfungen.

Die Tests validieren unter anderem Begrenzungen, ungültiges UTF-8,
Sequenzlücken, Resync, späte Antworten, Fokuswechsel, parallele Instanzen,
Zwischenablagekorrelation, Terminalrückkehr, flüchtige nummerierte
Auswahllisten, sitzungsgetrennte Braillemodi und Dateimanagerworkflows.

Automatisierte Tests ersetzen keine Prüfung in NVDA, Windows Terminal, über
echtes SSH oder an Braillehardware. Die genaue Befehlsfolge und die praktische
Abnahmematrix stehen in `testing.md`.

## Praktisch bestätigte Nutzung

Ohne Anspruch auf eine vollständige Plattformmatrix wurden bestätigt:

- Installation und Aktualisierung lokaler und entfernter Komponenten;
- lokale und SSH-basierte F12-Zuordnung;
- parallele lokale und entfernte Sitzungen in mehreren Tabs, Panes und
  Windows-Terminal-Fenstern;
- Wechsel zwischen gemerkten Verbindungen ohne Übernahme durch fremde
  Shell-Controls;
- vorhandene SSH- und tmux-Sitzungen ohne deren Beendigung oder Umbau;
- Fokusansagen und Verbindungsnamen lokal und entfernt;
- alle vier Zwischenablagebefehle lokal und über SSH;
- Terminalmodus, Kommandozeilenrückkehr und Bufferwechsel;
- Oil-Navigation, Umbenennungsvorschau, Klänge und Bestätigungsabläufe.

## Bekannte Grenzen

- Windows Terminal ist das einzige freigegebene Terminalfrontend. Andere
  Terminals und Neovim-GUIs besitzen keine geprüften Fokus-, Identitäts- und
  Fail-open-Adapter.
- Unterstützt wird das normale `%LOCALAPPDATA%\nvim-data`-Layout. Portable
  Installationen und `NVIM_APPNAME` sind nicht freigegeben.
- Eine ältere Neovim-Version auf Rocky Linux 9 verband sich mit einem aktuellen
  Stand nicht. Ursache und genaue Versionsgrenze sind nicht untersucht; daraus
  folgt keine Kompatibilitätszusage.
- Routing, Navigation, beide Braillemodi, Routingaktionen und der
  `z=`-Vorschlagspfad wurden in den beschriebenen Referenzabläufen mit einer
  physischen Braillezeile praktisch geprüft. Weitere Displays, Treiber,
  Übersetzungstabellen und die jüngsten Editier-/Routing-Randfälle des
  Braille-Explorationsmodus bleiben praktisch zu prüfen.
- Nur Oil ist als Dateimanager praktisch unter Windows/NVDA geprüft. netrw,
  mini.files, nvim-tree und Neo-tree benötigen schrittweise reale Abnahme.
- Repräsentative negative Isolationsfälle für Shells, Tabs, Panes, Fenster,
  Fokusverlust und geschlossene Controls benötigen weitere praktische Breite.
- Lange Laufzeiten, wiederholte Reconnects, sehr große Ereignislast und viele
  parallele Sitzungen benötigen weitere Stresstests.
- Sprachprofile, Windows-/NVDA-Versionen und reale SSH-Konfigurationen sind
  noch nicht breit genug für eine allgemeine Kompatibilitätszusage geprüft.

## Nächste Orientierung

- Architektur verstehen: `architecture.md`
- konkrete Grenzen prüfen: `compatibility.md`
- offene Arbeit priorisieren: `plan.md`
- Tests ausführen oder erweitern: `testing.md`
- Änderungen historisch nachvollziehen: `changelog.md`
