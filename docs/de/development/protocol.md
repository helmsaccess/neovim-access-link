# Protokoll v2

Protokoll v2 ist die einzige unterstützte semantische Schnittstelle zum
NVDA-Add-on. Es existiert keine Aushandlung oder Kompatibilität mit v1.

## Transport

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
    "accessibleMenus"
  ]
}
```

Lokal lautet `kind` `windows-loopback-tcp`; die Fähigkeiten entsprechen der
Liste ohne `heartbeat`.

## Registry und ausdrückliche Zuordnung

Schema 3 bindet einen Eintrag mit einer zufälligen `sessionNonce` an den
tatsächlichen Neovim-RPC-Endpunkt. Unter Linux muss zusätzlich
`processStartTicks` mit `/proc/<pid>/stat` übereinstimmen; `ownsSocket` erlaubt
die Bereinigung nur für den exakt zu PID und Nonce gehörenden Plugin-Socket.
Übernommene oder benutzerdefinierte Sockets werden nie gelöscht. PID oder
Dateiexistenz allein gelten nicht als Identitätsnachweis.
Der private Dateiname enthält PID und Nonce; nur genau diese eindeutige Datei
darf Discovery bei zweifelsfrei veralteter Identität entfernen.
Ein Scan verarbeitet höchstens 256 Registrydateien; jede Datei ist auf 65.536
Byte begrenzt. Discovery und Claim-Polling bleiben passiv und öffnen keinen
RPC-Kanal. Nach der eindeutigen Auswahl wird die Registry-Nonce auf demselben
dauerhaften RPC-Kanal abgefragt, der anschließend Ereignisse liefert, und zwar
vor Plugin-Setup und Kanalregistrierung. Ein Unterschied beendet diesen Kanal
fail-open ohne Wiederverbindung.

Lokale und entfernte Registryeinträge enthalten neben Sitzungsmetadaten eine
monoton steigende Ganzzahl `claimSequence`. Der Wert beginnt beim Pluginstart
bei 0 und wird bei jeder über den unveränderten `typed`-Wert erkannten
Sitzungsmarkierung erhöht; `claimedMonotonic` hält den zugehörigen monotonen
Zeitpunkt. Der Schreibzugriff läuft über `vim.schedule()` außerhalb von
`vim.on_key`. Beide Werte sind nur ein flüchtiger Claim: weder
Transport-Sequenzzähler noch Authentisierung, Terminalbindung oder dauerhafte
Auswahl. Sie werden nicht über Pluginneustarts hinweg erhalten. Neovims
Editor-Marks sind davon vollständig unabhängig.

Beim Aktivieren liest das Add-on die lokale Registry und die Sitzungslisten der
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
`menuClosed`, `signatureChanged`, `diagnosticChanged`, `foldChanged`,
`messageReceived`, `errorReceived` und `connectionStateChanged`.
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
- `routeCursor` mit `bufferId`, `windowId`, `line`, `byteColumn` und
`changedtick`.

`requestFocusContext` wird nur für eine bereits authentifizierte, exakt an das
aktuell fokussierte Terminal-Control gebundene Instanz gesendet. Die Antwort
wird bei abweichender Request-ID, Instanz, Bindung oder Fokusidentität
verworfen. Der Ablauf ist fokusereignisgetrieben und verwendet kein Polling.

`routeCursor` prüft aktuelle Buffer-/Fensterkennung, `changedtick`, Zeilen- und
UTF-8-Bytespalten-Grenzen, bevor Neovims Cursor-API aufgerufen wird. Empfangener
Text wird nie als Lua- oder Ex-Code ausgeführt.

## Sicherheitsgrenze

Bei Linux übernimmt SSH Host- und Benutzer-Authentifizierung, Vertraulichkeit und
Integrität. Das eingeschränkte v2-Protokoll exponiert Neovims mächtige
MessagePack-RPC-Schnittstelle nicht bis Windows. Damit bleibt die Bridge eine
explizite Sicherheitsgrenze statt eines allgemeinen Remote-Control-Kanals.
Lokal bleibt Neovims mächtiger RPC-Port auf IPv4-Loopback beschränkt. Der
Zugriff liegt damit innerhalb des angemeldeten Windows-Benutzerkontexts; er ist
kein Ferntransport und wird nicht als frei konfigurierbarer RPC-Zugang
angeboten.
