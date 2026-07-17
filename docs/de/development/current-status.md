# Aktueller Status

Stand: 2026-07-17, Beta-Version 0.93.0; der Gesamtstand bleibt zwischen
Alpha und Beta.

Im Testbuild `0.93.0-dev.1` ist der erste nach dem Terminal-Abgleich offene
Dateimanagerpunkt umgesetzt. Namen, Pfade, Wurzeln, Typen und externe
Adapterbezeichnungen werden weiterhin nach Protokollbudget in Bytes begrenzt,
aber nur noch an validierten UTF-8-Codepointgrenzen. Ungültiger Adapteroutput
wird feldweise verworfen. Zwei-/Dreibytezeichen, Emoji, lange Pfade und
ungültige Bytefolgen sind in nun 27 Dateimanagerassertionen abgedeckt; alle
Lua-Spezifikationen bestehen. Öffentliche Pluginereignisse für Änderungen am
selben Eintrag, getrennte Markierungs-/Copy-/Cut-Semantik, Aktionsresultate und
reale Plugin-/Brailletests bleiben die nächsten Dateimanagerphasen.

Im Testbuild `0.92.0-dev.11` auf `feature/terminal-file-manager-hardening` sind
elf Terminal-Hardening-Schritte umgesetzt. Erfolgreiche `:bp`-/`:bn`-
Bufferwechsel im selben Tab und Fenster verwenden jetzt dieselbe profilfähige
Auswahl wie der Sitzungsfokus: keine Ansage, aktuelle Zielzeile oder
Zielkontext mit Modus und gespeichertem Verbindungsnamen. Die Auswertung folgt
`BufEnter`-basierten `contextChanged`-Ereignissen; ein vorausgehendes
Modusereignis kann die Ansage nicht verschlucken. Tab-/Fenster-Zielpositionen
bleiben erhalten; Modusklänge bleiben unabhängig. Kurzlebige gesprochene Rückkehrmodi werden bei
diesen Bufferbefehlen mit der Zielausgabe zusammengefasst; dadurch bleibt
„Keine Ansage“ still und weder ein abgebrochenes „T“ noch eine doppelte
Modusansage überlagert die Zielzeile. Der Ex-Typ wird strukturiert von Suche
unterschieden. Automatische Cursor- und Änderungsereignisse
des Zielbuffers überschreiben die Zielzeile nicht und vergleichen keinen Text
mit dem Ausgangsbuffer. Dasselbe gilt beim Erzeugen eines Terminalbuffers mit
`:terminal`: Die Fokuswahl steuert den Einstieg, die Zeilenwahl wartet auf die
erste echte Terminalzeile und das automatische Cursorereignis bleibt stumm.
Auch eine umgekehrte Reihenfolge von Terminalkontext und abschließendem
Modusereignis bleibt zusammengefasst; Kommandozeilentext kann nicht als
Normalmodusbewegung in den neuen Buffer hineinreichen.
Der Eintritt in direkte Terminaleingabe gibt die vollständige Cursorzeile aus
und behält den Insertklang. `modeRaw=nt` ist ein eigener
kanonischer `terminalNormal`-Zustand, Command-line-Echo verwendet die
UTF-8-Byteposition der Befehlszeile, und ein frei belegbarer, lokal wie über
SSH fest validierter `stopinsert`-Befehl ersetzt bei Bedarf die
layoutabhängige Folge `Ctrl+\`, `Ctrl+N`. `TermClose` meldet das Prozessende mit
Exit-Status. Passthrough wird vor optionaler Rückmeldung fail-open umgestellt;
Duplikate der Terminal-Kontextereignisse erzeugen keinen zweiten Modusklang.
Die Kommandozeile besitzt nun einen eigenen Ton; Rückkehr, wirkungslose
Buffer-Navigation und Neovims `E89` bei `:bd` auf einem laufenden Terminaljob
werden eindeutig ausgegeben, ohne `:bd!` selbst auszuführen. UI-Meldungen
werden unter Neovim 0.12 außerhalb des `vim.ui_attach`-Fast-Event-Kontexts
ausgewertet und erzeugen daher keinen `E5560`-Enter-Zustand.
Bei Fenster- und Tabwechseln fasst die Kontextwahl nun Zielposition,
eindeutigen Datei- oder Spezialkontext, Status, Modus und Verbindung in einer
Ansage zusammen. Dadurch werden `T` als `file T` und Terminalmodi ohne
doppelte Terminalbezeichnung ausgegeben; Modusklänge bleiben getrennt.
Eine nach Sitzungsende getrennte, aber noch gemerkte lokale Instanz blockiert
keine neue SSH-Zuordnung mehr: Nur authentifizierte Bindungen schränken F12
auf ihren bisherigen Zieltyp ein; sonst wird die ausdrückliche Geste erneut
gegen das vollständige inventarisierte Zielset aufgelöst.
Alle 265 Add-on/Core-/Pakettests, 41 Protokolltests, 31 Bridge-/TUI-Tests und
sämtliche Lua-Spezifikationen bestehen; Add-on und sechs HTML-Dokumente bauen
erfolgreich. Die umgesetzten Terminal-, Buffer-, Fenster-/Tab- und erneuten
SSH-Zuordnungspfade wurden praktisch ohne weitere Probleme bestätigt.
Pager-Sonderfälle und die vollständige negative Windows-Terminal-Matrix bleiben
weiter zu prüfen.

Auf `feature/copy-paste` sind vier frei belegbare, ausdrücklich ausgelöste
NVDA-Befehle implementiert: Visual-Auswahl kopieren, Register 0 kopieren,
Windows-Zwischenablagentext über Neovims Paste-API einfügen oder in Neovims
Register 0 speichern und das unbenannte Register für normales `p` darauf
zeigen lassen. Lokal und über SSH gilt derselbe korrelierte Protokollpfad. Er prüft Fokus, Control-Bindung,
Instanz, Anfrage-ID, Buffer, Fenster, Tab, `changedtick` und Modus, begrenzt
Text auf 256 KiB UTF-8 und hält Copy-Text aus Zustands-Cache und Diagnosen fern.
Paste bleibt auf normale veränderbare Editorbuffer beschränkt. 38 Protokoll-,
28 Bridge-, 244 Add-on/Core-/Pakettests und alle Lua-Spezifikationen inklusive
28 Zwischenablageassertionen bestehen; Add-on und sechs HTML-Dokumente bauen
erfolgreich. Alle vier Befehle wurden im bereitgestellten `dev.4`-Build
praktisch ohne Probleme bestätigt.

Der erste Build registrierte die frei belegbaren Befehle nur im Windows-
Terminal-AppModule. Nach NVDAs anwendungsbezogener Filterung fehlte deshalb die
gesamte Produktkategorie, wenn der Tastenbefehldialog etwa aus dem Explorer
geöffnet wurde. Die Korrektur registriert unbelegte globale Metadaten, prüft
beim Aufruf erneut die exakte WT-`TermControl`-Identität und gibt die Geste in
anderen Anwendungen unverändert weiter. Der `dev.4`-Praxistest bestätigte die
Kategorie aus einer Fremdanwendung, die unveränderte Weitergabe dort und die
korrekte Ausführung im gebundenen Neovim-Control vollständig.

Der erste Praxistest mit `0.89.0-dev.1` zeigte beim Wechsel Explorer → dasselbe
WT-Control keine Dateinamenansage. Die Diagnose enthielt Fokusverlust,
erneuten Fokus und Unterdrückung, aber keine Fokus-Kontextanfrage. Ursache war
ein Frühabbruch anhand der absichtlich erhaltenen authentifizierten Bindung.
`0.89.0-dev.2` unterscheidet nun echte Fokuswiederkehr von internen
Fokusereignissen; die Korrektur wurde praktisch bestätigt.

## Gesamtbewertung

Das Add-on wurde unter Windows 11 25H2 mit NVDA 2026.1.1,
`OpenSSH_for_Windows_9.5p2` mit `LibreSSL 3.8.2` und Windows Terminal 1.24.x
praktisch getestet;
die Gegenstelle lief auf Rocky Linux 10.2 mit Neovim 0.10.1. Installation aus
dem NVDA-Menü, die vom Add-on verwaltete SSH-stdio-Verbindung und die Nutzung
in einer bestehenden SSH-/tmux-Sitzung funktionieren grundsätzlich. Der Stand
eignet sich für vorsichtige Erprobung, ist aber insgesamt noch im Alpha- bis
Beta-Zustand, nicht erschöpfend getestet und nicht stabil veröffentlicht.

Die deutsche Anwenderdokumentation liegt als kurzer Einstieg und vollständiges
Handbuch in getrennten Markdown-Quellen vor. Der reproduzierbare Build erzeugt
`neovim-access-link-quick-guide-de.html` und
`neovim-access-link-handbook-de.html`. Die Entwicklerdokumentation wird als
`neovim-access-link-developer-documentation-de.html` gebaut. Quick Guide,
Handbuch und Entwicklerdokumentation werden zusätzlich auf Englisch erzeugt.

## Aktueller technischer Stand

- Die im Projekt historisch „Registry“ genannte Sitzungsregistrierung besteht
  ausschließlich aus kurzlebigen JSON-Dateien und ist nicht die Windows-
  Registry; `HKCU` und `HKLM` werden nicht verwendet.
- Schema 3 dieser dateibasierten Sitzungsregistrierung schützt lokale und entfernte Discovery mit zufälliger
  Endpoint-Nonce sowie unter Linux mit Prozessstartkennung. Eindeutig tote
  Einträge und exakt nonce-eindeutige eigene Pluginsockets werden bereinigt;
  übernommene oder benutzerdefinierte Pfade bleiben unangetastet. Unklare Fehler bleiben
  nicht-destruktiv. Geschlossene einzelne WT-Tabs oder ganze Fenster entfernen
  nach zwei negativen Prüfungen im Abstand von fünf Minuten ihre jeweilige NVDA-Bindung und
  stoppen den Client außerhalb des Hauptthreads, ohne Neovim oder tmux zu
  beenden. Isolierte SIGKILL-Tests lokal und auf `user@example.invalid` hinterließen keine
  sichtbare Sitzung und keine eigenen nonce-eindeutigen Sitzungsdatei-/Socketreste.
  Fokussierte Tabs werden nie durch die UIA-Wartungsprüfung entfernt; diese
  Prüfung läuft nicht in Editor-, Status- oder Aktionspfaden.
  Discovery liest Sitzungsdateien, Prozessidentität und Endpunkt nur passiv. Die
  Nonce wird erst auf dem anschließend dauerhaft verwendeten RPC-Kanal und vor
  jeder Pluginregistrierung geprüft; Inventur und Polling öffnen keine
  Wegwerfkanäle.

- Protokoll v2 ist die einzige unterstützte Neovim-NVDA-Schnittstelle.
- Entfernte Linux-Sitzungen verwenden ausschließlich längenbegrenztes
  MessagePack-Protokoll v2 über SSH-stdin/stdout. Lokale Windows-Sitzungen
  verwenden Neovims MessagePack-RPC über einen dynamischen, exakt an
  `127.0.0.1` gebundenen Port. Allgemeine Netzwerklistener, Tunnelports,
  Anwendungstokens und v1-Aushandlung bleiben ausgeschlossen.
- Bridge und Plugin werden rootlos pro Linux-Benutzer aus dem NVDA-Menü
  installiert. Das vollständige, beim Add-on-Build erzeugte Linux-Paket ist im
  Add-on eingebettet; zur Zielmaschine wird kein externer Download benötigt.
  Mehrere gespeicherte Verbindungen können ausdrücklich per Checkbox in einem
  Durchlauf gewählt werden; die Sammelcheckbox folgt auch manuellen
  Einzelmarkierungen. Jedes abgeschlossene Ziel erhält eine kurze
  Fortschrittsmeldung; eine abschließende Sprachausgabe und eine nicht
  blockierende kompakte Ergebnisübersicht trennen erfolgreiche und
  fehlgeschlagene Aktualisierungen. SSH-Upload und entfernte Installation sind
  jeweils auf 60 Sekunden begrenzt. Der Aktualisierungsbefehl
  liegt unter NVDAs „Tools“-Menü; die Add-on-Einstellungen werden ausschließlich
  als reguläre NVDA-Einstellungskategorie angeboten.
  Ein zweiter Werkzeugmenüeintrag entfernt die Komponenten im Hintergrund von
  ausdrücklich ausgewählten lokalen oder entfernten Zielen. Er bewahrt
  Verbindungsprofile, Benutzerkonfiguration, SSH-Dateien und fremde Plugins und
  meldet jedes Ziel in einer nicht blockierenden Ergebnisübersicht.
  Die validierte Paketkonfiguration hält die Kennung von Neovims
  Markierungstaste und die Kennung der von NVDA beobachteten Geste konsistent;
  sie bindet selbst weder ein Neovim-Mapping noch ein NVDA-Skript. Ein normales
  `nvim datei` genügt
  anschließend.
- Mehrere Verbindungsprofile, Hosts, Benutzer und parallele Neovim-Sitzungen
  werden getrennt verwaltet. F12 markiert die tatsächlich fokussierte
  Neovim-Instanz kurzzeitig und bindet genau sie an den fokussierten
  Windows-Terminal-Tab; interne IDs müssen nicht eingegeben werden. Für einen
  bereits gebundenen Tab gilt dessen Ziel. Beim Aktivieren erfasst ein
  begrenzter Hintergrundscan die lokalen Sitzungsdateien und alle ohne Passwortdialog
  erreichbaren gespeicherten SSH-Verbindungen. In einem ungebundenen Tab sucht
  F12 die veränderte Claim-Sequenz über diesen gesamten Bestand; ein
  Standardziel gibt es nicht. Passwortprofile ohne Laufzeitpasswort und
  Sonderfälle bleiben ausdrücklich über den Verbindungsdialog erreichbar.
- Die native Windows-CLI `nvim.exe` in Windows Terminal ist als eigener
  Verbindungstyp implementiert. Das eingebettete Plugin kann über denselben
  Komponenten-Dialog lokal installiert werden, registriert lokale Sitzungen
  unter `%LOCALAPPDATA%\nvim-nvda` und wird per F12 eindeutig zugeordnet.
  Lokale und SSH-Sitzungen können parallel an unterschiedliche Tabs gebunden
  sein. Der Grundpfad sowie lokale und SSH-Tabs parallel wurden unter Windows
  praktisch bestätigt. Zwei gleichzeitige lokale Tabs, mehrere Windows-
  Terminal-Fenster, tmux, die zielübergreifende Discovery und der Wechsel
  zwischen lokalen und entfernten Sitzungen funktionieren praktisch. Auch die
  dev.42-Korrektur für ein bereits vor der Aktivierung fokussiertes Terminal,
  der normale F12-AppModule-Pfad, das globale Aktivierungs-Toggle, verzögerte
  Claim-Callbacks und das Lesen aggregierter NVDA-Konfiguration wurden praktisch
  bestätigt.
- In 0.89.3 wird ein frischer lokaler F12-Claim vor SSH geprüft und unmittelbar
  verbunden. Eine bis zu 1,5 Sekunden begrenzte Nachsuche fängt verzögert
  sichtbare atomare Sitzungsdatei-Updates ab. Die automatisierten Regressionstests
  sind bestanden; die lokale automatische und manuelle Zuordnung wurde mit
  dem installierten Beta-Build praktisch als zuverlässig bestätigt.
- Ein unveränderter interaktiver Mapping-Test mit sicher aktualisierten
  Komponenten zeigte, dass F12 bei aktiver NVDA-Unterstützung Neovim nicht
  erreichte. `decide_handleRawKey=True` erlaubt zwar NVDAs weitere Verarbeitung,
  garantiert aber keine OS-Weitergabe. 0.89.11 entfernt diesen Beobachter,
  bindet F12 lokal im Windows-Terminal-App-Modul und gibt die Originalgeste mit
  `gesture.send()` vor der Claim-Auswertung ausdrücklich an Neovim weiter.
- Der interaktive 0.89.11-Test bestätigte anschließend `onKey`, den originalen
  Mapping-Callback und einen erfolgreichen Claim. 0.89.12 übernimmt den direkt
  vor `gesture.send()` erfassten monotonen Zeitanker in die automatische lokale
  Auswertung. Dadurch bleibt die Aktivierungsbaseline erhalten, während der
  konkrete frische Tastendruck zusätzlich eindeutig erkannt wird.
- 0.89.12 bestätigte lokale Zuordnung und eine entfernte Tessa-Verbindung,
  zeigte beim Wiederholen aber unveränderte Claim-Sequenzen in beiden
  tatsächlich laufenden Tessa-Sitzungen. 0.89.13 gibt F12 deshalb mit zehn
  Millisekunden GUI-Schleifenabstand erst nach Rückkehr aus NVDAs Input-Hook
  weiter; die Auswertung beginnt unverändert nach 250 Millisekunden. Der
  praktische 0.89.13-Test widerlegte auch diese synthetische Weitergabe.
- Nach manueller Auswahl funktionierte dieselbe Tessa-Sitzung; ein physischer
  F12-Kontrolltest und weitere Versuche erhöhten ihr Register anschließend auf
  `claimSequence=3`. 0.89.14 beobachtet F12 daher mit
  `decide_executeGesture`, bindet kein NVDA-Skript und lässt den ursprünglichen
  Tastendruck über NVDAs `NoInputGestureAction`-Pfad direkt durch. Nur die
  Claim-Auswertung wird auf die NVDA-Ereigniswarteschlange übergeben.
- Der 0.89.14-Bericht bestätigte anschließend nur die lokale automatische
  Zuordnung; die Tessa-Verbindung entstand manuell. Ein isolierter Neovim-
  0.10.1-Lauf empfing F12 zuverlässig als `typed=<F12>`, stellte den internen
  Schlüssel jedoch als Terminalcode dar und löste das `<F12>`-Mapping nicht
  aus. 0.89.15 wertet deshalb `typed` im vorhandenen `vim.on_key`-Beobachter
  aus. Bei deaktivierter Unterstützung ignoriert der NVDA-Beobachter F12 nun
  vollständig.
- Der 0.89.15-Praxistest bestätigte Tessa und die inaktive F12-Beobachtung bei
  deaktivierter Unterstützung. Lokales Neovim 0.12.3 wurde automatisch
  verbunden, geriet aber unmittelbar in den `r?`-/Hit-Enter-Zustand und verlor
  anschließend seinen RPC-Server. 0.89.16 plant den Sitzungsdatei-Schreibzugriff
  deshalb mit `vim.schedule()` außerhalb von `vim.on_key` ein.
- Der abschließende 0.89.16-Praxistest bestätigte die automatische Zuordnung
  sowohl für lokales Neovim 0.12.3 als auch für Tessa mit Neovim 0.10.1.
  Wiederholte F12-Markierungen funktionierten, und bei deaktivierter
  Unterstützung blieb die Beobachtung vollständig inaktiv: Es erschien kein
  Zuordnungsdialog. Damit sind Markierung, Sitzungsdatei-Claim, Add-on-Zuordnung und
  Transportverbindung als getrennte Schritte praktisch bestätigt.
- Der 0.89.35-Praxistest bestätigte die Korrektur der späteren
  `r?`-Regression. Während einer nativen Swap-Datei-Rückfrage erzeugte der
  erste F12-Druck keinen Claim (`changed=false`, kein Kandidat). Nach dem
  Beantworten der Rückfrage in Neovim verband der nächste F12-Druck mit
  `keyModeAfterClaim=n`; das erste `i` wechselte in den Insert-Modus, und Text
  sowie Zeilenwechsel erzeugten anschließend strukturierte `textChanged`-
  Ereignisse. Frische lokale Windows-Neovim- und Tessa-SSH-Sitzungen zeigten
  denselben Normal-zu-Insert-Wechsel. Beim Wechsel zwischen gemerkten lokalen
  und entfernten Terminal-Tabs wurde jeweils ein aktueller `fullState`
  geliefert. Der verborgene `r?`-Zustand trat in diesem Test nicht erneut auf.
  Das spätere Beenden des ersten lokalen Editors trennte dessen Client;
  begrenzte Wiederverbindungsversuche stellten die Unterdrückung nicht wieder
  her, und das Deaktivieren der Unterstützung stoppte den Client. Spätere
  lokale und SSH-Sitzungen erhielten eigene Verbindungsinstanzen; die erste
  Verbindung wurde nicht unbemerkt wiederverwendet.
- Der Aktivierungsbefehl erfasst mögliche Ziele, öffnet aber noch keine
  dauerhaften Bridgeverbindungen. Nach der Bereitschaftsmeldung verbindet F12
  den eindeutigen Treffer; der explizite Dialogweg bleibt für Passwort- und
  Sonderfallauswahl.
- Add-on-Rückmeldungen und Verbindungswerte liegen in einem validierten nativen
  NVDA-Konfigurationsabschnitt. NVDAs reguläre Profile, Vererbung und Auslöser
  gelten dadurch ohne eine eigene Profilwahl des Add-ons. Profilwechsel laden
  wirksame Werte neu, unterbrechen aber keine laufende Editorverbindung.
- Optionales, ausdrücklich bestätigtes Merken von Windows-Terminal-Tabs über
  stabile UIA-Runtime-IDs; nur im RAM, ohne Titel-/Textauswertung und mit
  sicherem Fallback auf den Verbindungsdialog.
- Aktivierung, Verbindung, strukturierte Ausgabe, Braille-Overlay und native
  Terminalunterdrückung liegen im ausschließlich für Windows Terminal geladenen
  NVDA-AppModule. Darin müssen freigegebene UIA-Klasse und stabile Runtime-ID
  gemeinsam passen. PuTTY ist in der Frontendrichtlinie nur als geplant
  vermerkt und kann ohne implementierten Adapter nicht freigeschaltet werden.
  Ereignisse, Overlays, F12-Zuordnung und der standardbelegte Diagnosebefehl
  liegen im ausschließlich für `windowsterminal.exe` geladenen NVDA-AppModule.
  Unbelegte globale Skriptadapter dienen nur der dauerhaften Sichtbarkeit im
  Tastenbefehldialog und delegieren ausschließlich nach strikter WT-Prüfung.
- Strukturierte Sprache und Braille decken Modi, Navigation, Bearbeitung,
  Visual Character/Line/Block, Einrückung, Completion und Menüs, Suche,
  Diagnostics und Rechtschreibung, Folds, Marks, Register, Makros, Terminal-
  Normalmodus sowie verbreitete Dateimanager ab.
- Bei Deaktivierung, falscher Sitzung oder Verbindungsverlust fällt das Add-on
  auf die normale NVDA-Terminalausgabe zurück.
- Das Repository enthält genau zwei typisierte Produktpfade: SSH-stdio für
  Linux und IPv4-Loopback-RPC für lokales Windows-Neovim. Historische
  allgemeine TCP-/Tokenimplementierungen und Benchmarkprototypen bleiben
  entfernt.

Die detaillierte Funktionsmatrix steht in [accessibility.md](accessibility.md),
die Architektur in [architecture.md](architecture.md) und die Bedienung im
[Anwenderhandbuch](../manual/README.md).

## Verifikation dieses Branches

- 243 Python-Tests: 203 Add-on/Core einschließlich Repositoryrichtlinien,
  26 Protokoll und 14 Bridge
- 151 Lua-Assertions mit echtem Neovim
- alle Bridge-/TUI-/Sockettests bestanden; vier in der eingeschränkten
  Socket-Sandbox erwartbar gescheiterte Fälle wurden isoliert außerhalb dieser
  Sandbox vollständig und erfolgreich wiederholt
- Add-on-Archiv 0.89.35, getrennte deutsche und englische HTML-Dokumente, zentrale Metadatenableitung,
  Manifestversion und interne Links wurden automatisiert geprüft
- Die vollständige Komponentenentfernung wurde mit dem installierten
  Testbuild praktisch bestätigt.

Reproduzierbare Befehle stehen in [testing.md](testing.md).

## Bekannte Grenzen und nächste Arbeit

1. Die Brailleunterstützung wurde noch mit keiner echten Braillezeile geprüft
   und enthält sehr wahrscheinlich Fehler. Hardwaretests verschiedener
   Hersteller einschließlich Punkte 7/8 und Routingtasten sowie anschließende
   Korrekturen sind ein wichtiges priorisiertes TODO.
2. Lange Arbeitsläufe, wiederholte SSH-Abbrüche, große Dateien und schnelle
   Ereignisfolgen brauchen weitere Belastungstests.
3. Weitere Windows-Terminals, SSH-Konfigurationen, NVDA-Profile, Sprachen und
   Neovim-Versionen gehören in eine breitere Kompatibilitätsmatrix.
4. Frei gezeichnete Plugin-Oberflächen benötigen eine Standard-API oder einen
   Adapter; nicht jede beliebige TUI-Darstellung ist automatisch zugänglich.
5. Lokales Neovim unter Windows ist für die CLI-Version in Windows Terminal
   [implementiert, dokumentiert und praktisch bestätigt](../manual/communication.md).
   `NVIM_APPNAME`, portable
   Installationen und die GUI-Version sind noch nicht unterstützt.
6. Eine ältere Neovim-Version auf Rocky Linux 9 funktionierte mit dem aktuellen
   Stand nicht. Die genaue Versionsgrenze und Ursache sind nicht untersucht;
   Neovim 0.10.1 auf Rocky Linux 10.2 bleibt die bestätigte Basis. Diese
   Rückwärtskompatibilität hat derzeit keine Priorität.
7. Auch außerhalb von Braille wurden noch nicht alle Add-on-Funktionen
   ausführlich praktisch geprüft. Lokalisierung, Releaseprüfung und ein
   erschöpfender stabiler Abnahmelauf stehen noch aus.
8. Der Branch `feature/addon-isolation` begrenzt jeden durch den physischen
   F12-Druck einmalig autorisierten Claim auf ein einzelnes WT-`TermControl`, entfernt
   aktivitätsbasierte Wiederbindungen und suspendiert gemerkte Verbindungen
   beim Fokuswechsel bis zur passenden frischen Kontextantwort. Automatisierte
   Tests belegen getrennte Controls und Fenster sowie stille, bindungs- und
   unterdrückungsfreie F12-Versuche ohne frischen Claim. Der erste Praxistest
   deckte einen fehlerhaften Vorab-Arming-Entwurf auf: F12 funktionierte im
   zweiten Tab nicht und der globale Ausschalter war dort blockiert. Beides ist
   für `dev.3` mit Regressionstests korrigiert. Der anschließende Praxistest
   bestätigte lokale und entfernte Zuordnung in zwei Tabs ohne erneute
   Aktivierung, den Tabwechsel und die globale Deaktivierung aus dem zweiten
   Tab. Horizontale und vertikale Split-Panes funktionierten anschließend bei
   parallelen lokalen und SSH-Verbindungen in anderen Tabs fehlerfrei.
   Getrennte WT-Fenster, tmux und die vollständige Negativmatrix ungebundener
   Shell-Panes stehen noch aus.
   `focusContext` ist außerdem noch kein unabhängiger
   Beweis des Vordergrundprogramms innerhalb desselben Controls; Overlay und
   weitergehende Fokuskorrelation bleiben Folgearbeit.
