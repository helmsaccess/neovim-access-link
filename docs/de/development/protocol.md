# Protokoll v2

Protokoll v2 ist die einzige unterstützte semantische Schnittstelle zum
NVDA-Add-on. Es existiert keine Aushandlung oder Kompatibilität mit v1.

## Maßgebliche Quellverträge

| Bereich | Validator oder Produzent | Vertragstests |
|---|---|---|
| Framing und Envelope | [`codec.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/protocol/python/nvim_nvda_protocol/codec.py), [`messages.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/protocol/python/nvim_nvda_protocol/messages.py) | [`test_protocol.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/protocol/python/tests/test_protocol.py) |
| Lokale Controls und Capabilities | [`local_client.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/protocol/python/nvim_nvda_protocol/local_client.py) | [`test_local_client.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/protocol/python/tests/test_local_client.py) |
| SSH-stdio-Weiterleitung | [`stdio.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/bridge/python/nvim_nvda_bridge/stdio.py) | [`test_stdio.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/bridge/python/tests/test_stdio.py) |
| Neovim-Zustand und feste Operationen | [`state.lua`](https://github.com/helmsaccess/neovim-access-link/blob/main/neovim-plugin/lua/nvim_nvda/state.lua), [`init.lua`](https://github.com/helmsaccess/neovim-access-link/blob/main/neovim-plugin/lua/nvim_nvda/init.lua) | [Lua-Vertragstests](https://github.com/helmsaccess/neovim-access-link/tree/main/neovim-plugin/tests) |

Diese Seite erklärt den gültigen Vertrag; die verlinkten Validatoren sind für
akzeptierte Werte maßgeblich. Eine Protokolländerung aktualisiert Produzent,
beide Transportvalidatoren, Tests und beide Sprachfassungen gemeinsam.

## Transport

### SSH-stdio

Bei Linux startet das NVDA-Add-on pro Verbindung einen Windows-OpenSSH-Prozess. Dessen
Remote-Befehl startet `~/.local/bin/nvim-nvda-bridge`; das Anwendungsprotokoll
läuft ausschließlich über SSH-stdin und SSH-stdout. TCP-Listener,
Portweiterleitungen, Anwendungstokens und ein `hello`-Handshake gehören nicht
zu v2.

Vor dem ersten Frame schreibt die Bridge exakt:

```text
NVIM-NVDA-STDIO/2
```

Der Client verwirft höchstens 64 KiB Shell-Startausgabe vor dieser Markierung.
Danach ist stdout ausschließlich dem gerahmten Protokoll vorbehalten;
Diagnosen gehen nach stderr.

### Lokales Windows-RPC

Bei lokalem Windows-Neovim verbindet sich `LocalTcpClient` direkt mit Neovims
dynamischem MessagePack-RPC-Port auf exakt `127.0.0.1`. Der SSH-Startmarker und
das Längenframing entfallen auf diesem lokalen Teilstück; Ereignisse werden
jedoch vor der Übergabe an NVDA mit demselben v2-Envelope, denselben Typen und
demselben 1-MiB-Limit validiert. Freie Host- oder Portkonfiguration ist nicht
vorgesehen.

## Framing und Envelope

Jede Nachricht besteht aus einem vier Byte großen vorzeichenlosen
Big-Endian-Längenpräfix und einem MessagePack-Objekt. Die maximale Framegröße
beträgt 1 MiB.

Pflichtfelder:

```text
protocolVersion      muss 2 sein
sessionId            nicht leere Transport-Sitzungskennung
sequence             monoton steigende Ganzzahl ab 0
timestampMonotonic   nicht negativer monotoner Zeitstempel
type                  nicht leerer Ereignis- oder Steuerungstyp
payload               Map
```

Eine andere Protokollversion, fehlende Pflichtfelder, ungültige Typen,
beschädigtes MessagePack und übergroße Frames beenden die betreffende
Transportinstanz. Unbekannte optionale Payloadfelder dürfen ignoriert werden.

Dateimanagerzustand enthält nur begrenzte semantische Werte. Eintragsnamen sind
auf 512 UTF-8-Byte, Pfade und Wurzeln auf 2048 Byte sowie Typ- und
Adapterbezeichnungen auf 64 Byte begrenzt. Das Plugin validiert vollständige
UTF-8-Sequenzen und schneidet ausschließlich vor einem Codepoint; ein
ungültiger Adapterwert wird verworfen, statt eine beschädigte Nachricht zu
senden.

Ein Dateimanagereintrag kann `selectionState` mit ausschließlich `marked` oder
`unmarked` sowie `clipboardState` mit ausschließlich `copied`, `cut` oder
`none` enthalten. `expanded` bleibt ein Boolean. Das alte Feld `marked` wird
nur kompatibel mitgeführt und darf Copy gegenüber Cut nicht semantisch
ersetzen. `fileManagerEntryChanged` entsteht sowohl bei strukturierter
Navigation als auch nach einem öffentlichen Pluginereignis, wenn sich der
erneut gelesene Zustand tatsächlich geändert hat. Inaktive Buffer/Fenster und
identische Zustände erzeugen kein Ereignis; Renderfolgen werden innerhalb
eines Neovim-Schedulerzyklus zusammengefasst, nicht gepollt.
Bei strukturierter Navigation kann `fileManagerMotion` ausschließlich eine
feste interne Bewegungsart wie `lineStart`, `lineEnd`, `fileStart`, `fileEnd`
oder `lineChanged` enthalten. Sie bewahrt Klänge und Bewegungsabsicht, ohne die
dekorierte Managerzeile zur Sprachquelle zu machen. Bei Oil bezeichnet
`entry.name` den öffentlichen `parsed_name`, sobald dieser nichtleer ist;
`entry.path` bleibt bis zum Abschluss aus dem bestätigten `name` gebildet.
`fileManager.root` bezeichnet die öffentliche Manager- oder Branchwurzel;
`fileManager.currentDirectory` bezeichnet die fokussierte Ebene. Beide sind
optional, UTF-8-validiert und auf 2048 Byte begrenzt. Fehlende Werte werden
nicht aus `entry.path` geraten.

`promptOpened` überträgt eine auf 2048 Byte begrenzte bewusste
Bedienausgabe sowie einen festen Prompttyp. `promptClosed` unterscheidet bei
`vim.ui.input/select` Annahme und Abbruch. Für `vim.fn.confirm` enthält es
`answered=true`, den numerischen Auswahlindex und höchstens eine auf 512 Byte
begrenzte sichtbare Auswahlbezeichnung; aus der Bezeichnung wird keine
Dateiaktion abgeleitet. Die Promptantwort selbst wird nicht übertragen oder
gespeichert. Ein blockierender Modusübergang kann das Schließen belegen, wenn
Neovims externe UI kein `msg_clear` liefert.
Oils `oil_preview`-Bestätigungs-Fallback verwendet denselben Promptvertrag,
aber ausschließlich feste Aktionsverben, Anzahl und Y/N. Die gerenderte Zeile,
Namen und Pfade werden im `promptOpened`-Zustand geleert; unbekannte Verben oder
ein gleichnamiger Nicht-Float erzeugen kein semantisches Prompt-Ereignis.
Wird direkt `y` oder `n` getippt, trägt das zugehörige `promptClosed`
`accepted=true` beziehungsweise `accepted=false`. Andere Schließwege lassen
`accepted` aus, statt eine Auswahl zu erraten.

`fileManagerActionResult.payload.fileManagerAction` enthält ausschließlich:

```text
manager     UTF-8-validierte Bezeichnung, höchstens 64 Byte
action      add | change | copy | create | delete | move | multiple | rename | restore
result      success | cancelled | failed
count       Ganzzahl 1 bis 10000
name        optionaler UTF-8-validierter Basename, höchstens 512 Byte
entryType   optionaler bekannter semantischer Typ
```

Der Adapter verwirft den vollständigen Quell-/Zielpfad vor dem Senden. Mehrere
synchrone Ergebnisse im selben aktiven Buffer/Fenster/Tab werden innerhalb
eines Schedulerzyklus zusammengefasst. Ein Identitäts- oder Managerwechsel vor
der Ausgabe verwirft sie. Das Ereignis bestätigt nur, was die öffentliche
Plugin-API als Abschluss meldet; fehlende Fehler- oder Abbruchereignisse werden
nicht aus Meldungstext oder Renderzustand rekonstruiert.

## Sitzungsbeginn, Sequenzierung und Resync

Die erste akzeptierte Nachricht jeder Transport-Sitzung ist `fullState` mit
Sequenz 0. Vorherige oder fremde Sitzungskennungen werden nicht übernommen.

- Doppelte oder rückwärts laufende Sequenzen werden verworfen.
- Eine Sequenzlücke setzt den Client auf „Resync erforderlich“.
- Der Client sendet `requestFullState`.
- Erst ein neues `fullState` hebt diesen Zustand auf.
- Nach SSH-Reconnect erzeugt die Bridge eine neue `sessionId` und beginnt
  wieder bei Sequenz 0.

Die Bridge sendet standardmäßig jede Sekunde `heartbeat`. Der SSH-Prozess nutzt
zusätzlich `ServerAliveInterval=5` und `ServerAliveCountMax=2`; dadurch erkennt
OpenSSH einen abgebrochenen Transport und der Add-on-Client verbindet sich mit
begrenztem exponentiellem Backoff neu.

Der lokale Client besitzt keinen separaten Heartbeat: Ein geschlossener
Neovim-RPC-Socket erzeugt `disconnected`; Reconnect verwendet ebenfalls
begrenzten Backoff. Ein gültiger `fullState` ist auch lokal die erste
Authentifizierung der Accessibility-Sitzung.

## Fähigkeiten

Es gibt keinen Aushandlungs-Handshake. `fullState.payload._transport` beschreibt
den tatsächlich gestarteten v2-Transport:

```json
{
  "kind": "ssh-stdio",
  "capabilities": [
    "heartbeat",
    "resync",
    "semanticEvents",
    "cursorRouting",
    "accessibleMenus",
    "focusContext",
    "clipboardTransfer",
    "terminalControl"
  ]
}
```

Lokal lautet `kind` `windows-loopback-tcp`; die Fähigkeiten entsprechen der
Liste ohne `heartbeat`. `exploration` wird nur ergänzt, wenn das verbundene
Neovim-Plugin diese feste Fähigkeit in `pluginCapabilities` bestätigt. So
fängt ein aktualisiertes Add-on keine Explorationstasten ab, solange noch ein
älteres Plugin installiert ist oder läuft.
`numberedChoices` wird entsprechend nur ergänzt, wenn das Plugin die
strukturierte Erkennung und Annahme nummerierter nativer Auswahllisten
bestätigt.
`brailleLineNavigation` wird nur ergänzt, wenn das Plugin den festen
benachbarten Zeilenwechsel und den bevorzugten Virtuellspaltenzustand
unterstützt.
`brailleExploration` wird unabhängig davon nur ergänzt, wenn das Plugin den
getrennten flüchtigen Braille-Zeilenkanal bestätigt.
`brailleRoutingActions` wird nur ergänzt, wenn das Plugin die festen
Mehrfachbetätigungsaktionen und ihre vollständige Zustandsprüfung bestätigt.
`callableContextQuery` und `diagnosticContextQuery` werden nur ergänzt, wenn
das Plugin die korrelierten, lesenden Kontextabfragen bestätigt.
`activeParameterHints` wird nur ergänzt, wenn das Plugin automatische,
strukturierte Übergänge des aktiven LSP-Parameters erzeugt. Bridge und lokaler
Client verwerfen diesen Ereignistyp ohne die Fähigkeit.
`diagnosticCursorSummary` kennzeichnet zusätzlich die kleine, textfreie
Diagnosezusammenfassung im normalen Snapshot.

## Dateibasierte Sitzungsregistrierung und ausdrückliche Zuordnung

Die folgenden „Registry“-Einträge sind kurzlebige JSON-Dateien des Neovim-
Plugins. Sie haben nichts mit der Windows-Registry zu tun; weder `HKCU` noch
`HKLM` werden gelesen oder beschrieben. Windows verwendet normalerweise
`%LOCALAPPDATA%\nvim-nvda\sessions`, Linux das private Laufzeitverzeichnis
`$XDG_RUNTIME_DIR/nvim-nvda/sessions` oder einen benutzerbezogenen `/tmp`-
Fallback.

Schema 3 bindet einen Eintrag mit einer zufälligen `sessionNonce` an den
tatsächlichen Neovim-RPC-Endpunkt. Unter Linux muss zusätzlich
`processStartTicks` mit `/proc/<pid>/stat` übereinstimmen; `ownsSocket` erlaubt
die Bereinigung nur für den exakt zu PID und Nonce gehörenden Plugin-Socket.
Übernommene oder benutzerdefinierte Sockets werden nie gelöscht. PID oder
Dateiexistenz allein gelten nicht als Identitätsnachweis.
Der private Dateiname enthält PID und Nonce; nur genau diese eindeutige Datei
darf Discovery bei zweifelsfrei veralteter Identität entfernen.
Ein Scan verarbeitet höchstens 256 JSON-Sitzungsdateien; jede Datei ist auf 65.536
Byte begrenzt. Discovery und Claim-Polling bleiben passiv und öffnen keinen
RPC-Kanal. Nach der eindeutigen Auswahl wird die Nonce der Sitzungsdatei auf demselben
dauerhaften RPC-Kanal abgefragt, der anschließend Ereignisse liefert, und zwar
vor Plugin-Setup und Kanalregistrierung. Ein Unterschied beendet diesen Kanal
fail-open ohne Wiederverbindung.

Lokale und entfernte Sitzungsdateien enthalten neben Sitzungsmetadaten eine
monoton steigende Ganzzahl `claimSequence`. Der Wert beginnt beim Pluginstart
bei 0 und wird bei jeder über den unveränderten `typed`-Wert erkannten
Sitzungsmarkierung erhöht; `claimedMonotonic` hält den zugehörigen monotonen
Zeitpunkt. Der Schreibzugriff läuft über `vim.schedule()` außerhalb von
`vim.on_key`. Beide Werte sind nur ein flüchtiger Claim: weder
Transport-Sequenzzähler noch Authentisierung, Terminalbindung oder dauerhafte
Auswahl. Sie werden nicht über Pluginneustarts hinweg erhalten. Neovims
Editor-Marks sind davon vollständig unabhängig.

Beim Aktivieren liest das Add-on die lokalen Sitzungsdateien und die Sitzungslisten der
automatisch erreichbaren SSH-Ziele im Hintergrund und merkt die jeweiligen
Claim-Sequenzen als Baseline. Nach F12 wird derselbe Bestand erneut gelesen.
Nur eine gegenüber ihrer Baseline erhöhte Sequenz gilt als ausdrücklicher
Treffer. Damit benötigt die Zuordnung weder Standardverbindung noch interne ID,
Fenstertitel oder Terminaltext. Der eigentliche dauerhafte TCP- beziehungsweise
SSH-Transport startet erst nach einem eindeutigen Treffer oder einer
ausdrücklichen Dialogauswahl.

## Ereignisrichtung

Neovim erzeugt semantische Ereignisse als Push-Nachrichten. Die Bridge hält nur
den zuletzt bestätigten kanonischen Zustand; sie speichert ohne aktive
stdio-Sitzung keine Ereignisse für spätere Wiedergabe.

Wichtige Typen sind `fullState`, `modeChanged`, `characterMoved`, `wordMoved`,
`lineChanged`, `selectionChanged`, `textChanged`, `textDeleted`,
`textReplaced`, `searchMatchChanged`, `menuOpened`, `menuSelectionChanged`,
`menuSelectionCleared`, `menuItemUpdated`, `menuClosed`, `signatureChanged`,
`activeParameterChanged`,
`signatureClosed`,
`hoverChanged`, `hoverClosed`, `lspStatus`, `diagnosticChanged`,
`diagnosticMoved`, `foldChanged`,
`commandLineChanged`, `messageReceived`, `errorReceived`,
`fileManagerEntryChanged`, `fileManagerActionResult`,
`leaveTerminalInputResult`, `exploreTextResult`,
`brailleExploreLineResult` und
`numberedChoiceOpened`, `numberedChoiceClosed`,
`callableContextResult`, `diagnosticContextResult` und
`connectionStateChanged`. Der kanonische Modus `terminalNormal` bildet Neovims
rohen Modus `nt` ab und bleibt vom normalen Dateibuffer-Modus getrennt.
`menuSelectionCleared` bezeichnet bei weiterhin geöffnetem Menü den von
Neovim gemeldeten Zustand ohne ausgewählten Kandidaten. Er löscht den
Dokumentationscache und wird als eigener zugänglicher Zustand ausgegeben.
`commandLineChanged.payload.commandLineType` enthält Neovims strukturierten
Kommandozeilentyp, insbesondere `:`, `/` oder `?`; `commandLine` enthält den
Inhalt ohne dieses Präfix. Dadurch werden Ex-Befehle nicht aus Textmustern
erraten und gleich geschriebene Suchmuster bleiben unabhängig.
`menuItemUpdated` behält Auswahl, Index und Anzahl bei und aktualisiert nur
Metadaten wie eine nachträglich aufgelöste Dokumentation. NVDA aktualisiert
damit den instanzbezogenen Dokumentationscache ohne eine zweite Auswahlansage.
`signatureClosed` beendet den flüchtigen Signaturzustand beim Verlassen seines
Editor-Kontexts und erzeugt keine eigene Sprachmeldung.
`activeParameterChanged` ist ein flüchtiger, nicht kanonisch gespeicherter
Sprachhinweis aus dem Einfügemodus. Die Payload bindet den Aufruf mit
`callName`, einsbasierter `callStartLine` und nullbasierter
`callStartByteColumn`; sie enthält die begrenzte `signature`,
`signatureIndex`/`signatureCount`, `activeParameter`/`parameterCount`, das
begrenzte `parameter`-Label und genau einen Grund `callEntered`,
`signatureChanged` oder `parameterChanged`. Alle Indizes sind einsbasiert,
Anzahlen auf 100 begrenzt und müssen zueinander passen. Zusätzlich müssen
Insert-Modus, Buffer, Fenster, `changedtick` und Cursor vollständig vorhanden
und gültig sein. Protokoll, Bridge und lokaler Client lehnen fehlende,
ungültige, übergroße oder widersprüchliche Pflichtfelder ab; die üblichen
validierten Snapshot-Felder dürfen daneben erhalten bleiben. Das Ereignis erzeugt keine
Braillemeldung und wird nicht für spätere Wiedergabe zwischengespeichert.
`hoverChanged` enthält eine kurze Zusammenfassung und die begrenzte
vollständige Dokumentation; Sprache und Braille verwenden automatisch nur die
Zusammenfassung. `hoverClosed` verwirft die instanzbezogene
Hover-Dokumentation ohne eigene Meldung.
`lspStatus` enthält ausschließlich die begrenzten Namen der am aktuellen
Buffer hängenden LSP-Clients und wird nur durch `:NvimNvdaLspStatus` erzeugt.
`diagnosticChanged` aktualisiert den kanonischen Zustand nach
`DiagnosticChanged`, bleibt aber ohne automatische Präsentation.
`diagnosticMoved` wird nach einer ausdrücklich beobachteten oder über einen
Access-Link-Befehl ausgelösten Diagnosenavigation erzeugt. Sein Snapshot trägt
höchstens eine aktuell einschließende Diagnose sowie `diagnosticCount`.
Bei Access-Link-Befehlen ist dies der ausdrücklich ausgewählte Eintrag der
geordneten Diagnosemenge; dadurch können mehrere Diagnosen an derselben
Position unterschiedliche Indizes und Klänge behalten.
Die Diagnose enthält eine auf 2048 gültige UTF-8-Bytes begrenzte Meldung,
Schwere, eine auf 256 Bytes begrenzte Quelle, optional einen auf 256 Bytes
begrenzten String- oder ganzzahligen Code, einsbasierte Zeilen,
nullbasierte UTF-8-Bytespalten sowie Index und Anzahl. Fehlende Quellen dürfen
auf den begrenzten Neovim-Namespace-Namen zurückfallen. Ungültige
Produzentendatensätze werden verworfen; sie werden weder ausgeführt noch als
Neovim- oder Linterbefehl interpretiert.
`diagnosticSummary` enthält für passive Klänge nur Anzahl und höchste Schwere
auf der Zeile beziehungsweise an der Cursorposition sowie eine opake,
textfreie Bereichsidentität. Diagnosemeldung, Quellcode und Quick-Fix-Daten
gehören nicht in diese Zusammenfassung.

`messageReceived.payload.commandLineReturn=true` kennzeichnet ausschließlich
die unmittelbare strukturierte Ausgabe eines gerade beendeten, nichtleeren
Ex-Befehls. Das Feld wird nach genau dieser Ausgabe verworfen; spätere
asynchrone Meldungen erhalten es nicht. Der Empfänger koppelt damit den
Rückkehrklang und die konfigurierte Fokuspräsentation, ohne Meldungstext oder
Modus aus Zeitabständen zu erraten.
`focusContext` ist eine korrelierte Momentaufnahme aus demselben kanonischen
Zustands-Cache. `_focusRequestId` ordnet sie genau der auslösenden Fokusanfrage
zu; sie ist kein frei laufender Editorstream.

Die maßgebliche Payloadstruktur wird vom Neovim-Zustandsmodell erzeugt und in
der Funktionsmatrix `accessibility.md` beschrieben. Buffertext wird nicht
blind vollständig übertragen.

## Steuerungsrichtung

Vom Add-on zur Bridge sind nur diese Typen vorgesehen:

- `requestFullState` ohne inhaltliche Payload;
- `requestFocusContext` mit einer ganzzahligen `requestId` zwischen 0 und
  2147483647;
- `routeCursor` mit festem Ziel `editor` oder `commandLine`, `bufferId`,
  `windowId`, `byteColumn`, `changedtick` und exaktem `modeRaw`. Das Editorziel
  trägt zusätzlich `line`; das Befehlszeilenziel trägt den exakt erwarteten,
  auf 16 KiB begrenzten `commandLine`-Inhalt und `commandLineType`;
- `brailleRouteAction` mit `bufferId`, `windowId`, `line`, `byteColumn`,
  `changedtick`, exaktem `modeRaw` und genau einer Aktion `changeWord`,
  `deleteWord`, `changeLine` oder `deleteLine`. Nur eine Zeilenaktion trägt
  zusätzlich genau einen Start `routing`, `indentation` oder `beginning`;
- `moveBrailleLine` mit `bufferId`, `windowId`, aktueller `line`,
  `changedtick`, exaktem `modeRaw`, einer festen `direction` aus `previous`
  oder `next`, einer festen Zielregel `targetColumn` aus `preferred`, `start`
  oder `end` und `preferredVirtualColumn` zwischen 0 und 2147483647;
- `copyTextRequest` mit korrelierter `requestId`, erwarteter Buffer-, Fenster-,
  Tab-, `changedtick`- und Modusidentität sowie genau einer Quelle
  `visualSelection` oder `yankRegister`;
- `pasteTextRequest` mit derselben erwarteten Identität und höchstens 256 KiB
  gültigem, NUL-freiem UTF-8-Text;
- `setRegisterRequest` mit derselben erwarteten Identität und Textgrenze; das
  Ziel ist fest Register 0 als Speicher des unbenannten Registers; ein
  Registername wird nicht übertragen.
- `leaveTerminalInputRequest` mit korrelierter `requestId`, Buffer-, Fenster-
  und Tabidentität sowie exakt `modeRaw=t`. Die feste Zieloperation ist
  ausschließlich `stopinsert`; Lua- oder Ex-Text wird nicht übertragen.
- `exploreTextRequest` mit positiven Anfrage-, Explorations- und
  Aktionsnummern, einer der sechs festen Bewegungen, Wiederholungszahl 1 bis
  64 sowie exakter Buffer-/Fenster-/Tab-/`changedtick`-/Modus- und
  Echtcursoridentität;
- `endExplorationRequest` mit Anfrage- und Explorations-ID zum Verwerfen des
  flüchtigen Lua-Zustands.
- `brailleExploreLineRequest` mit derselben vollständigen Ursprungsidentität,
  positiver Anfrage-, Explorations- und Aktionsnummer, genau `lineUp` oder
  `lineDown`, Wiederholungszahl 1 und `desiredVirtualColumn` zwischen 0 und
  2147483647 sowie derselben festen `targetColumn`-Auswahl;
- `endBrailleExplorationRequest` mit Anfrage- und Explorations-ID zum
  Verwerfen ausschließlich des getrennten Braille-Lua-Zustands.
- `acceptNumberedChoiceRequest` mit korrelierter Anfrage-ID, Auswahlart,
  Auswahl-ID, nullbasiertem Eintragsindex sowie exakter
  Buffer-/Fenster-/Tab-/`changedtick`-Identität.
- `callableContextRequest` und `diagnosticContextRequest` mit korrelierter
  Anfrage-ID sowie exakter Buffer-, Fenster-, Tab-, `changedtick`-, Zeilen-
  und UTF-8-Bytespaltenidentität.

Beide Kontextantworten wiederholen diese vollständige Identität. Die
Diagnoseantwort enthält höchstens 100 Einträge der aktuellen Zeile; die
Signaturantwort höchstens 100 Signaturen mit jeweils höchstens 100 Parametern.
Einzeltexte sind auf 16 KiB, die Summe aller Texte einer Antwort auf 256 KiB
begrenzt. Add-on und Plugin verwerfen verspätete Antworten nach Fokus-,
Instanz-, Buffer-, Text- oder Cursorwechsel. Die Abfragen verändern weder den
Editorcursor noch Neovims Diagnoseauswahl.

`requestFocusContext` wird nur für eine bereits authentifizierte, exakt an das
aktuell fokussierte Terminal-Control gebundene Instanz gesendet. Die Antwort
wird bei abweichender Request-ID, Instanz, Bindung oder Fokusidentität
verworfen. Der Ablauf ist fokusereignisgetrieben und verwendet kein Polling.

`routeCursor` prüft aktuelle Buffer-/Fensterkennung, `changedtick`, exakten
Rohmodus sowie Zeilen- und UTF-8-Bytespalten-Grenzen. Das Editorziel setzt den
Cursor über `nvim_win_set_cursor()`, zeichnet neu und veröffentlicht den
Zustand auch im Insert-Modus unmittelbar. Das Befehlszeilenziel vergleicht
zusätzlich Typ und vollständigen Inhalt und ruft anschließend Neovims
öffentliche Funktion `setcmdline()` mit demselben Text und der neuen
Bytespalte auf. Inhalt und Position werden danach erneut geprüft. Empfangener
Text wird nie als Lua-, Ausdrucks- oder Ex-Code ausgeführt.

`brailleRouteAction` ist nur mit ausgehandelter Capability im Normal- oder
Insert-Modus zulässig. Bridge und Plugin akzeptieren exakt die für die
jeweilige Aktion genannten Felder; zusätzliche Felder werden verworfen. Das
Plugin prüft aktuellen Buffer, Fenster, `changedtick`, Rohmodus, Cursorzeile,
UTF-8-Bytespalte, Zeichenrand sowie `modifiable` und `readonly`. Wortaktionen
auf Leerraum oder am Zeilenende werden verworfen. Erst danach bildet es die
festen Kennungen intern auf `cw`, `dw`, `c$` oder `d$` ab. Die Zeilenstarts
entsprechen keiner Bewegung, `^` oder `0`. Insert-Löschaktionen kehren in den
Insert-Modus zurück; Änderungsaktionen verbleiben entsprechend Neovims
Operatorsemantik im Insert-Modus. Frei wählbare Tastensequenzen oder
Befehlstexte sind kein Protokollfeld.

`moveBrailleLine` prüft erneut aktuelle Buffer-/Fensterkennung,
`changedtick`, Rohmodus und Ausgangszeile. Befehlszeilen- und
Terminal-Eingabemodus werden verworfen. Das Ziel ist ausschließlich die
unmittelbar benachbarte Zeile. `preferred` bildet die bevorzugte virtuelle
Spalte mit `virtcol2col()` auf eine gültige UTF-8-Bytespalte ab und speichert
dieselbe Spalte wieder als `curswant`. `start` wählt Bytespalte und
Wunschspalte null. `end` wählt UTF-8-sicher das letzte Zeichen im Normalmodus
beziehungsweise die Position direkt hinter dem Text im Insert-Modus; eine
Leerzeile ergibt in beiden Fällen null. Danach wird genau ein
`cursorMoved`-Ereignis mit Grund `brailleLineNavigation` veröffentlicht.

`copyTextResult`, `pasteTextResult` und `setRegisterResult` tragen dieselbe
Anfrage-ID und einen festen Ergebniscode. Nur `copyTextResult` darf einmalig das Feld
`clipboardText` enthalten. Add-on, lokaler Client und Bridge verwerfen eine
nicht mehr zu Fokus, Control, Instanz und Anfrage passende Antwort. Der Text
wird nach der einmaligen Übergabe an NVDAs Zwischenablage-API aus dem
kanonischen Zustands-Cache entfernt und erscheint weder in späterem
`fullState` noch in `focusContext`. Einfügen ruft ausschließlich
`nvim_paste(..., true, -1)` auf; fehlgeschlagene oder zeitlich veraltete
Aktionen werden nicht automatisch wiederholt.
`setRegisterRequest` normalisiert CRLF, wählt anhand eines abschließenden
Zeilenumbruchs Zeichen- oder Zeilentyp und ruft ausschließlich das feste
`setreg('0', ..., type .. '"')` auf. Das ersetzt Register 0 und lässt das
unbenannte Register darauf zeigen, ohne ein benanntes Benutzerregister zu
verwenden.

`leaveTerminalInputResult` trägt dieselbe Anfrage-ID, `ok` und einen festen
Ergebniscode. Add-on und Plugin prüfen zusätzlich die authentifizierte,
fokussierte Control-/Instanzbindung und den aktuellen Terminalbuffer. Ein
`changedtick` gehört bewusst nicht zu diesem Befehl: Terminaljobs ändern ihn
asynchron, während `stopinsert` weder Buffertext liest noch verändert. Der
tatsächliche Moduswechsel folgt weiterhin ereignisgetrieben über
`ModeChanged`/`TermLeave`; es gibt kein Polling.

`exploreTextResult` korreliert Anfrage, Exploration, Aktionsnummer und feste
Aktion. Erfolgreiche Ergebnisse enthalten genau die Einheit Zeichen, Wort
oder Zeile, eine begrenzte virtuelle Position, den booleschen Wert `atOrigin`
und höchstens 16 KiB Text. Optional enthält `explorationLineText` die ebenfalls
auf 16 KiB begrenzte vollständige virtuelle Zeile. Sie dient ausschließlich
einer konfigurierbaren, abgeleiteten Brailleansicht und wird ebenso wie alle
anderen Ergebnisfelder nie in den kanonischen Zustand übernommen. Nur ein
Wortergebnis darf zusätzlich den festen
semantischen Wert `formatError=spelling|grammar` tragen; Meldung, Quelle und
sonstige Diagnosedaten werden nicht übertragen. Die Ursprungsmarkierung
richtet sich nach der
angeforderten Einheit: genaues Zeichen, enthaltendes Wort oder Zeile. Damit
bleiben Neovims Wortregeln auf der Neovim-Seite. Die Lua-Engine liest höchstens
256 Zeilen beziehungsweise 64 KiB pro Wortsuche und liefert nur feste
Erfolgs-, Grenz- oder Fehlercodes. Sie ruft keine Cursor-, Feedkeys-, Normal-,
Such- oder Bufferänderungsoperation auf. Der Empfänger verwirft Antworten nach
Fokus-, Bindungs-, Kontext- oder ID-Wechsel.

`brailleExploreLineResult` verwendet dieselbe strikte Korrelation, erlaubt
aber ausschließlich die Einheit `line` und die Aktionen `lineUp` oder
`lineDown`. Das höchstens 16 KiB große Ergebnis trägt die virtuelle Zeile und
ihre UTF-8-, Zeichen- und virtuelle Spalte. Add-on, Bridge und lokaler Client
nehmen dieses Ergebnis nur einmalig entgegen und speichern es nicht als
kanonischen Zustand. Sprach- und Braille-Exploration besitzen getrennte
Aktionsfolgen; ein Abschlussauftrag verwirft nur seinen eigenen Kanal.

`numberedChoiceOpened` ist ein flüchtiges Ereignis und wird nie Teil des
kanonischen Zustands. Für `choiceKind=spellSuggestions` enthält es eine
Auswahl-ID und höchstens 128 gültige UTF-8-Einträge mit je höchstens 4 KiB.
Das Plugin emittiert es nur nach einem belegten direkten `z=` und einer
lückenlos ab 1 nummerierten nativen Liste. `numberedChoiceClosed` verwirft die
Auswahl bei geschlossenem UI- oder geändertem Editorkontext.
`acceptNumberedChoiceRequest` muss exakt zu diesem aktiven Prompt passen. Der
Transport sendet nur den validierten einsbasierten Zahlenwert und `Enter` über
Neovims öffentliche Eingabe-API; Vorschlagstext wird nicht zurückgesendet.

## Sicherheitsgrenze

Bei Linux übernimmt SSH Host- und Benutzer-Authentifizierung, Vertraulichkeit und
Integrität. Das eingeschränkte v2-Protokoll exponiert Neovims mächtige
MessagePack-RPC-Schnittstelle nicht bis Windows. Damit bleibt die Bridge eine
explizite Sicherheitsgrenze statt eines allgemeinen Remote-Control-Kanals.
Lokal bleibt Neovims mächtiger RPC-Port auf IPv4-Loopback beschränkt. Der
Zugriff liegt damit innerhalb des angemeldeten Windows-Benutzerkontexts; er ist
kein Ferntransport und wird nicht als frei konfigurierbarer RPC-Zugang
angeboten.
