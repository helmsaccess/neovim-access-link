# Architektur

## Gewählte Integration

Neovim Access Link verwendet eine hybride Architektur:

```text
Neovim Lua-Plugin
  → semantische nvim_nvda_event-RPC-Notifications
Linux-Bridge über privaten Unix-RPC-Socket
  → MessagePack-Protokoll v2 über SSH-stdin/stdout
Windows-NVDA-Add-on
  → Speech, Braille und sitzungsbezogene Terminalunterdrückung

Native Windows-CLI in Windows Terminal
  → dasselbe Lua-Plugin und semantische RPC-Notifications
  → dynamischer Neovim-RPC-Port ausschließlich auf 127.0.0.1
  → direkter lokaler Client im NVDA-Add-on
```

Das Lua-Plugin besitzt den besten Zugriff auf Modi, Auswahl, Completion,
Meldungen und Aktionen. Die externe Bridge isoliert Neovim von SSH-Lebenszyklus,
Framing und Abbrüchen. Das NVDA-Add-on bleibt für Fokus, Ausgabe und
Fail-open-Verhalten zuständig. Die ursprüngliche Variantenbewertung und
Messungen stehen in `adr/0001-neovim-integration-point.md`.

## Unterstützte Transportgrenzen

Für entfernte Linux-Sitzungen werden nur SSH-stdio und Protokoll v2
unterstützt. Das Add-on startet Windows-OpenSSH, und die Bridge verwendet
dessen stdin/stdout. Für die lokale Windows-CLI verbindet sich ein eigener
Client direkt mit dem vom Plugin angelegten Neovim-RPC-Port. Dieser muss exakt
`127.0.0.1` verwenden und wird niemals aus einer frei eingegebenen Adresse
gebildet. Es gibt keinen allgemeinen TCP-Listener, Tunnel-Port,
Anwendungstoken, `hello`-Handshake oder Kompatibilitätsmodus.

SSH authentifiziert Host und Linux-Konto. `ClearAllForwardings=yes` verhindert,
dass Benutzerkonfiguration unbeabsichtigt Forwardings in den Bridgeprozess
übernimmt. ServerAlive und begrenzter Backoff behandeln Abbrüche.

## Verteilung der Linux-Komponenten

Der Add-on-Build erzeugt aus den versionierten Bridge-, Protokoll-, Plugin- und
Installerquellen ein rootloses Benutzerarchiv und bettet es als
`resources/server-user.tar.gz` in die `.nvda-addon` ein. Die Installation auf
ein gespeichertes SSH-Ziel überträgt ausschließlich diese eingebetteten Bytes;
es existiert kein Laufzeitdownload und keine zweite, möglicherweise
abweichende Paketquelle.

Eine validierte JSON-Komponenten-Konfiguration wird sowohl neben dem Archiv im
Add-on als auch im Linux-Paket ausgeliefert. Sie bindet die Neovim-Taste zur
expliziten Sitzungsmarkierung an die korrespondierende NVDA-Geste. Der Build
verhindert widersprüchliche Werte, damit beide Enden nach einer gemeinsamen
Installation denselben Handshake verwenden.

Das unveränderte Neovim-Plugin liegt zusätzlich als
`resources/neovim-plugin` im Add-on. Der Komponenten-Dialog installiert dieses
lokal atomar in
`%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda`; die lokale
Installation benötigt weder SSH noch Administratorrechte.

## Begriffe: Markierung, Claim, Zuordnung und Verbindung

Eine **Sitzungsmarkierung** ist die ausdrückliche Benutzeraktion im
fokussierten Neovim, standardmäßig ein physischer Druck auf F12. Sie ist nicht
mit Neovims Editor-**Marks** wie `ma` oder `'a` zu verwechseln.

Ein **Claim** ist ausschließlich der flüchtige, maschinenlesbare Nachweis
dieser Sitzungsmarkierung im privaten Registryeintrag der Neovim-Instanz:
`claimSequence` wird monoton erhöht und `claimedMonotonic` aktualisiert. Ein
Claim öffnet noch keinen Transport, authentifiziert keine Gegenstelle, wählt
keinen Terminal-Tab dauerhaft aus und wird nach einem Pluginneustart nicht
beibehalten.

Die **Claim-Auswertung** vergleicht die nach dem Tastendruck gelesenen Werte
mit der bei der Aktivierung erfassten Baseline. Nur genau ein frischer Treffer
darf zur **Zuordnung** führen. Diese Zuordnung bindet die stabile
`TerminalIdentity` des fokussierten Windows-Terminal-Tabs an eine neu gestartete
`ConnectionInstance`. Erst deren erfolgreicher TCP- oder SSH-Handshake ergibt
eine **Verbindung** und erlaubt strukturierte Ausgabe beziehungsweise native
Terminalunterdrückung. Die manuelle Profil- und Sitzungsauswahl überspringt
Markierung und Claim-Auswertung, erzeugt danach aber denselben typisierten
Verbindungs- und Zuordnungspfad.

## Neovim-Sitzungsregistry

Unter Linux startet oder übernimmt jede Neovim-Instanz einen privaten
Unix-RPC-Socket. Unter Windows startet sie zusätzlich einen dynamischen
`127.0.0.1`-RPC-Port. Beide schreiben eine Registrydatei mit Schema 2,
Transporttyp, PID, Endpoint, Startzeit, Name und Arbeitsverzeichnis. Die
Registry liegt im privaten Laufzeitverzeichnis des Linux-Benutzers
beziehungsweise unter `%LOCALAPPDATA%\nvim-nvda`.

Die Bridge akzeptiert ausschließlich aktuelle Schema-2-Einträge, prüft
Prozess und Socket und kann eine Sitzung über die interne PID auswählen. Das
Add-on listet Sitzungen mit Anzeigename und Arbeitsverzeichnis; IDs bleiben
interne Transportdaten.

Die bevorzugte Zuordnung erfolgt über die konfigurierte Markierungstaste. Beim
Aktivieren erfasst ein begrenzter Hintergrundscan die lokale Registry und alle
ohne Passwortdialog erreichbaren gespeicherten SSH-Ziele. Das Windows-Terminal-
App-Modul beobachtet F12 am öffentlichen Erweiterungspunkt
`decide_executeGesture`, ohne ein Skript zu binden. NVDAs normale Auflösung
endet daher mit `NoInputGestureAction`, und der Keyboard-Hook lässt den
ursprünglichen physischen Tastendruck direkt zu Windows Terminal und Neovim
durch. Der Beobachter stellt nur die begrenzte Claim-Auswertung getrennt in
NVDAs Ereigniswarteschlange und bleibt bei deaktivierter Unterstützung inaktiv.
Neovim erkennt die konfigurierte Claim-Taste am unveränderten `typed`-Wert von
`vim.on_key` statt über eine terminalcodeabhängige Zuordnung. Den Registry-
Schreibzugriff stellt es mit `vim.schedule()` in den normalen Ereigniszyklus,
sodass der Tastencallback keine Dateisystem- oder regulären Vim-Funktionszugriffe
ausführt. Anschließend vergleicht das Add-on die
monotone Claim-Sequenz jeder erfassten Sitzung mit ihrer Baseline. Genau eine
veränderte Sitzung wird gebunden. Für lokale Sitzungen gilt zusätzlich der
für den beobachteten Tastendruck erfasste monotone Zeitanker; dadurch wird
genau der zu diesem F12-Druck gehörende Registry-Claim erkannt. Mehrere echte Treffer werden zugänglich zur
Auswahl angeboten und kein Treffer führt zu keiner geratenen Verbindung. Eine
Standardverbindung existiert nicht. Alternativ wählen NVDA-Dialoge Ziel und
gegebenenfalls Sitzung mit verständlichen Namen. Fenstertitel werden nicht
ausgewertet.

## Verbindungsprofile und Laufzeitinstanzen

Ein `ConnectionProfile` beschreibt ein Linux-Zielkonto: Name, Host/Alias,
Benutzer, Port, optionale Schlüsseldatei und Anmeldeart. Es ist keine laufende
Verbindung und trägt keine Priorität oder Standardrolle. Das lokale Windows-
Ziel ist implizit verfügbar und benötigt kein gespeichertes Profil.

Ein typisiertes `ConnectionTarget` trennt `remoteSsh` und `localWindowsTcp`;
das lokale Ziel ist kein vorgetäuschtes SSH-Profil. Jede
`ConnectionInstance` besitzt eine eigene Instanz-ID, Ziel-ID, Transporttyp,
interne Sitzungs-ID und einen eigenen `SshStdioClient` oder `LocalTcpClient`. Der
`ConnectionInstanceManager` bindet Terminalidentitäten ausdrücklich an
Instanzen. Ohne Bindung werden Ereignisse nicht geraten oder anhand von
Fenstertiteln zugeordnet.

Nur Ereignisse der für das fokussierte Terminal ausgewählten Instanz erreichen
Speech, Braille und das Session-Gate. Beim Umschalten werden Ausgabeplaner und
Cursorzustand geleert und `fullState` angefordert. Das Beenden einer Instanz
beendet nur deren SSH-Prozess beziehungsweise lokalen RPC-Client.

## Flüchtige Frontend-Zuordnung

`frontend-policy.json` beschreibt bekannte Frontendadapter und deren Status.
Eine Konfiguration darf nur Adapter aktivieren, die der Code tatsächlich
implementiert. Derzeit ist ausschließlich `windowsTerminal` aktiviert; PuTTY
ist nur als geplant eingetragen und besitzt noch keinen Detektor.

NVDA lädt `appModules/windowsterminal.py` ausschließlich für Windows Terminal;
damit ist die Anwendungsgrenze bereits durch das vorgesehene AppModule-Modell
festgelegt. Innerhalb dieses AppModules entsteht ein `TerminalIdentity` nur bei
einer freigegebenen UIA-Klasse `TermControl` beziehungsweise `WPFTermControl`
und einer nichtleeren UIA-Runtime-ID. Die
flüchtige Identität enthält Prozess-ID, Fensterhandle und die undurchsichtig
behandelte Runtime-ID. Dadurch bleiben Tabs oder Panes mit gleichem Prozess und
Fenster unterscheidbar. Generische Fensteridentitäten werden nicht mehr als
Terminalfrontend akzeptiert.

Vor Aktivierung, manueller Verbindung und F12-Zuordnung liest ausschließlich
dieses Windows-Terminal-AppModule das aktuell fokussierte NVDA-Objekt erneut
ein. Das ist nötig, weil bei einem bereits fokussierten Terminal kein neues
`gainFocus`-Ereignis eintreffen muss; die globale Dienstklasse fragt den Fokus
weiterhin nicht selbst ab.

Nach einer expliziten Verbindung kann der Anwender das Merken bestätigen. Die
Zuordnung `TerminalIdentity → ConnectionInstance` lebt ausschließlich im RAM.
Bei unbekannter, abgelehnter, verschwundener oder nicht mehr gebundener ID wird
nichts geraten und keine Verbindung automatisch erzeugt. Der Transporttyp
hält lokales Windows-Neovim dabei strikt von `remoteSsh` getrennt.

## Threading und Lebenszyklus

- Neovim-Callbacks erzeugen kleine Zustands-Snapshots und RPC-Notifications.
- Die Linux-Bridge liest Neovim-RPC und schreibt den SSH-stdio-Transport in
  Hintergrundthreads.
- Jeder Windows-SSH-Client besitzt einen kontrollierten Hintergrundthread.
- Jeder lokale RPC-Client besitzt ebenfalls einen kontrollierten
  Hintergrundthread; Socket-I/O läuft nie im NVDA-Hauptthread.
- SSH-Aufbau, DNS, Lesen, Reconnect und Installation laufen nie im
  NVDA-Hauptthread.
- Die Zielerfassung nutzt höchstens vier Hintergrundarbeiter. Passwortprofile
  werden nur erfasst, wenn ihr Passwort bereits flüchtig für die aktuelle
  NVDA-Laufzeit vorliegt; der Scan öffnet niemals selbst einen Passwortdialog.
- Ereignisse und Verbindungszustände gelangen über `queueHandler` zurück in den
  NVDA-Hauptthread.
- Verzögerte wx-Hauptthread-Aufrufe bleiben bis zu ihrer Ausführung im Besitz
  des Add-ons und werden bei dessen Beendigung gestoppt; insbesondere darf der
  kurze Abstand zwischen F12-Weiterleitung und Registry-Nachsuche nicht durch
  Speicherbereinigung aufgehoben werden.
- Abschalten setzt Stop-Ereignisse, beendet Prozesse/Sockets und verwendet
  begrenzte Thread-Joins.

Ein verspätetes Sitzungslisting trägt eine Generationsnummer. Nach
Deaktivierung oder neuer Auswahl wird sein Ergebnis verworfen.

## Zustands- und Ausgabeschichten

Neovim ist die kanonische Quelle. Das Lua-Zustandsmodell unterscheidet UTF-8-
Bytespalten, Zeichenpositionen und virtuelle Spalten. Es überträgt begrenzte
semantische Zustände statt des gesamten Buffers.

Der NVDA-unabhängige `SpeechPlanner` wandelt Ereignisse in priorisierte
Aktionen um. Das Windows-Terminal-AppModule nimmt anwendungsspezifische NVDA-
Ereignisse und Gesten entgegen; der gemeinsame Dienst führt Speech-, Sound- und
Braille-APIs aus. Das Global Plugin besitzt selbst keine Ereignishandler,
Overlays oder Eingabeskripte und verwaltet nur Lebenszyklus, Einstellungen und
Verbindungen. Braille verwendet einen eigenen Planer und überlässt
Liblouis-Übersetzung, Cursorform und Auswahlpunkte 7/8 NVDA.

Das Add-on registriert einen validierten Abschnitt `nvimNvdaAccess` in NVDAs
`config.conf`. Dadurch übernimmt NVDAs Aggregationsschicht Vererbung und das
Schreiben in das jeweils aktive Konfigurationsprofil. Das Add-on beobachtet
`post_configProfileSwitch`, lädt die wirksamen Werte neu und aktiviert selbst
keine Profile. Rückmeldungen ändern sich unmittelbar; laufende authentifizierte
Editorverbindungen werden durch einen Profilwechsel nicht beendet.

Das `SessionGate` unterdrückt native Terminalausgabe nur, wenn manuelle
Aktivierung, authentifizierter vollständiger Zustand, Neovim-Kontext und
Terminalbindung gleichzeitig gültig sind. Disconnect, Fehler, Terminalmodus
mit direkter Eingabe und Deaktivierung stellen normale NVDA-Ausgabe wieder her.

## Sicherheitsgrenzen

- Das Anwendungsprotokoll erlaubt keinen allgemeinen Neovim-RPC-Zugriff.
- Der einzige zustandsändernde Rückkanal ist validiertes Cursorrouting.
- Profile validieren Host, Benutzer, Port, Schlüsselpfad und Anmeldeart vor dem
  Prozessstart.
- Passwörter werden nur im Speicher und in der Umgebung des kurzlebigen
  OpenSSH-Prozesses gehalten.
- Diagnosefelder mit Editorinhalt oder Geheimnissen werden redigiert und
  begrenzt.

## Implementierte lokale Erweiterung und weitere Frontends

Lokales Neovim unter Windows besitzt eine eigene typisierte Ziel- und
Transportklasse. Die CLI-Stufe verwendet einen dynamischen TCP-Endpunkt,
der ausschließlich an `127.0.0.1` gebunden ist; sie ist weder als
vorgetäuschtes SSH-Profil noch als allgemeiner Netzwerktransport modelliert.
Semantische Ereignisse, Protokollzustand, Speech, Braille, Settings und die
explizite Windows-Terminal-Bindung bleiben transportneutral. Verbindungstyp,
F12-Ablauf und Restrisiko sind hier sowie in Sicherheits- und
Protokollreferenz festgehalten; der anwenderbezogene Gesamtweg steht im
[Kommunikationshandbuch](../manual/communication.md).

Ein weiteres Windows-Terminalfrontend benötigt einen eigenen Detektor für
stabile Fenster-/Tabidentität und Fokus, dokumentierte native NVDA-Ausgabe,
ein explizit zugeordnetes NVDA-AppModule, Unterdrückungs- und Passthrough-Tests
sowie erst danach einen Statuswechsel in der Frontendrichtlinie. Ein bloßer
Konfigurationseintrag genügt bewusst nicht.
