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

## Expliziter Zwischenablagepfad

Die Windows-Zwischenablage bleibt Eigentum von NVDA. Vier frei belegbare,
global auffindbare NVDA-Skripte lesen oder schreiben sie über NVDAs
`api.copyToClip` und `api.getClipData`; Bridge und Neovim erhalten keinen
allgemeinen Zugriff auf Windows. Neovim stellt nur zwei feste Copy-Quellen
bereit – aktive Visual-Auswahl und Register 0 – sowie einen festen
`nvim_paste`-Einstiegspunkt und Register 0 als festen Speicher für das
unbenannte Paste-Register. Das Schreiben verändert weder einen Buffer noch ein
benanntes Benutzerregister.

Jede Aktion trägt eine Anfrage-ID und die erwartete Buffer-, Fenster-, Tab-,
`changedtick`- und Modusidentität. NVDA akzeptiert das Ergebnis nur für die
weiterhin fokussierte, authentifizierte und gebundene Instanz. Der einmalig
übertragene Copy-Text wird vor Aktualisierung des kanonischen Client-/Bridge-
Zustands entfernt. Offene Anfragen sind begrenzt. Der Pfad ist
ereignisgetrieben; es gibt weder Polling noch
automatische Zwischenablagesynchronisation oder automatische Wiederholung.

## Ereignisgetriebene Dateimanageradapter

`file_manager.lua` gewinnt und normalisiert den aktuellen semantischen
Eintrag. Die davon getrennte Schicht `file_manager_events.lua` abonniert nur
öffentliche Ereignisse der unterstützten Plugins: `OilMutationComplete`,
mini.files-Buffer-/Aktionsereignisse, nvim-trees `TreeRendered` sowie
Neo-trees Render- und Clipboardereignisse. Ein Callback liest ausschließlich
den weiterhin aktiven Buffer beziehungsweise das aktive Fenster über den
Adapter neu ein. Ein zentraler Vergleich verwirft gleiche Zustände; mehrere
Callbacks im selben Neovim-Schedulerzyklus ergeben höchstens eine
Neuauswertung. Fehlende oder inkompatible Plugin-APIs fallen auf die bereits
vorhandene Navigation zurück. Es gibt keine Timerabfrage, kein
Dateisystempolling und kein Screen Scraping.

Der Zustand unterscheidet Auswahlmarkierung, Plugin-Clipboard mit Copy/Cut und
Expansion. Das Plugin sendet nur Festwerte; der NVDA-Sprachplaner bildet für
denselben Eintrag Zustandsdifferenzen und verwendet dieselbe kompakte Meldung
auch für Braille. Diese Ereignisschicht ändert weder Terminalzuordnung noch
Gate oder native Ausgabe.

Öffentliche Abschlussereignisse werden getrennt als
`fileManagerActionResult` normalisiert. Vor dem Transport werden Quell- und
Zielpfade auf einen optionalen Basename reduziert; Aktion, Ergebnis und Typ
stammen aus kleinen erlaubten Wertemengen. Synchrone Massenaktionen im selben
Ziel werden in einem Schedulerzyklus zusammengefasst. Vor der Ausgabe werden
Buffer, Fenster, Tab und Manager erneut geprüft. Nur Oil stellt in der aktuell
geprüften API auch Abschlussfehler beziehungsweise einzelne erkennbare
Abbrüche bereit; für andere Plugins wird ein fehlendes Fehlerereignis nicht
erraten.

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
`TerminalIdentity` des fokussierten Windows-Terminal-Controls an eine neu gestartete
`ConnectionInstance`. Erst deren erfolgreicher TCP- oder SSH-Handshake ergibt
eine **Verbindung** und erlaubt strukturierte Ausgabe beziehungsweise native
Terminalunterdrückung. Die manuelle Zielauswahl schränkt die Suche auf das
gewählte Profil ein, verlangt danach aber dieselbe physische Markierung und
frische Claim-Auswertung, bevor sie den typisierten Verbindungs- und
Zuordnungspfad startet.

## Dateibasierte Neovim-Sitzungsregistrierung

„Registry“ ist hier ein historischer Kurzname für ein privates Verzeichnis mit
JSON-Sitzungsdateien und ausdrücklich **nicht** die Windows-Registry. Der Code
verwendet keine Schlüssel unter `HKCU` oder `HKLM`. Unter Windows liegen die
Dateien normalerweise in `%LOCALAPPDATA%\nvim-nvda\sessions`, unter Linux in
`$XDG_RUNTIME_DIR/nvim-nvda/sessions` beziehungsweise im benutzerbezogenen
Fallback-Verzeichnis unter `/tmp`. Die Dateien registrieren Neovim-Sitzungen,
nicht Windows-Terminal-Fenster, -Tabs oder -Panes. Deren konkrete Bindung an
eine Verbindung existiert ausschließlich im Arbeitsspeicher des NVDA-Add-ons.

Unter Linux startet oder übernimmt jede Neovim-Instanz einen privaten
Unix-RPC-Socket. Unter Windows startet sie zusätzlich einen dynamischen
`127.0.0.1`-RPC-Port. Beide schreiben eine JSON-Sitzungsdatei mit Schema 3,
Transporttyp, PID, Endpoint, Startzeit, Name und Arbeitsverzeichnis. Die
Sitzungsregistrierung liegt im privaten Laufzeitverzeichnis des Linux-Benutzers
beziehungsweise unter `%LOCALAPPDATA%\nvim-nvda\sessions`.

Aktuelle Einträge enthalten zusätzlich eine zufällige `sessionNonce`, den
Besitzstatus des Endpoints und unter Linux die Prozessstartkennung aus `/proc`.
Schema-3-Dateinamen enthalten PID und Nonce, sodass die Bereinigung eines alten
Eintrags niemals die Datei eines Prozesses mit wiederverwendeter PID trifft.
Discovery prüft PID, Prozessstart und Registrystruktur passiv. Erst nach der
Auswahl prüft der anschließend dauerhaft verwendete RPC-Kanal seine Nonce vor
Plugin-Setup und Registrierung. Ein Unterschied trennt fail-open ohne
Wiederverbindung. Eindeutig tote Einträge und exakt nonce-eindeutige eigene Pluginsockets
werden entfernt; übernommene oder benutzerdefinierte Socketpfade nie.
Timeouts und Zugriffsfehler bleiben nicht-destruktiv. Ältere Registry-Schemata
werden wegen fehlender Prozess-/Endpointidentität nicht mehr zur Auswahl
angeboten; laufende ältere Neovim-Instanzen müssen nach dem Komponentenupdate
neu gestartet werden. Die Bridge kann eine
Sitzung über die interne PID auswählen. Das
Add-on listet Sitzungen mit Anzeigename und Arbeitsverzeichnis; IDs bleiben
interne Transportdaten.

Die bevorzugte Zuordnung erfolgt über die konfigurierte Markierungstaste. Beim
Aktivieren erfasst ein begrenzter Hintergrundscan die lokalen Sitzungsdateien und alle
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

Frei belegbare Befehle ohne Standardgeste liegen als globale Skriptmetadaten
vor, damit NVDA sie unabhängig von der vor dem Eingabedialog fokussierten
Anwendung immer auflistet. Bei ihrer Ausführung liest die globale Dienstklasse
einmal das aktuelle Fokusobjekt. Nur eine vollständig freigegebene
Windows-Terminal-`TermControl`-Identität wird an die Aktion delegiert und als
aktueller Fokus übernommen. Außerhalb davon wird die Benutzer-Geste unverändert
mit `gesture.send()` weitergegeben; Gate, Bindungen und Unterdrückung bleiben
unverändert. F12, Fokusereignisse, Overlays und der standardbelegte
Diagnosebefehl bleiben ausschließlich im Windows-Terminal-AppModule.
Undokumentierte AppModule-Aliase erhalten bereits vor dieser Umstellung
gespeicherte Gestenzuweisungen, bilden aber keine zweite Konfigurationsfläche.

Nach einer expliziten Verbindung kann der Anwender das Merken bestätigen. Die
Zuordnung `TerminalIdentity → ConnectionInstance` lebt ausschließlich im RAM.
Bei unbekannter, abgelehnter, verschwundener oder nicht mehr gebundener ID wird
nichts geraten und keine Verbindung automatisch erzeugt. Der Transporttyp
hält lokales Windows-Neovim dabei strikt von `remoteSsh` getrennt.

Solange Verbindungen bestehen, prüft ausschließlich ein fünfminütiger
Wartungslauf HWND, Prozess-ID und UIA-Runtime-ID. Diese Prüfung läuft nie aus
Editorereignissen, Verbindungsstatus, Fokusbehandlung oder Aktionen heraus.
Die fokussierte Identität ist ein positiver Lebensnachweis; ein inaktiver Tab
wird erst nach zwei aufeinanderfolgenden negativen Wartungsprüfungen getrennt.
Damit kann eine einzelne vorübergehende UIA-Lücke keine aktive oder inaktive
Zuordnung zerstören. Das Stoppen des zugehörigen Clients geschieht außerhalb
des NVDA-Hauptthreads und beendet weder Neovim noch tmux.

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
Ereignisse, F12 und die Standardgeste für den Diagnosebericht entgegen; der
gemeinsame Dienst führt Speech-, Sound- und Braille-APIs aus. Das Global Plugin
besitzt keine Ereignishandler oder Overlays. Seine unbelegten Skriptadapter
machen konfigurierbare Befehle global auffindbar und delegieren erst nach
strikter WT-Fokusprüfung. Braille verwendet einen eigenen Planer und überlässt
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

## Fokus-Kontext registrierter Terminal-Controls

Erhält ein bereits authentifiziertes und gemerktes Windows-Terminal-Control
erneut Fokus, fordert das Add-on einmalig den aktuellen strukturierten Kontext
an. Lokaler Client oder SSH-Bridge antworten aus ihrem durch Neovim-Ereignisse
gepflegten Zustands-Cache. Eine Request-ID bindet die Antwort an genau dieses
Fokusereignis. Vor jeder Ausgabe werden aktuelle Fokusidentität, Instanz,
Bindung und Authentifizierung erneut geprüft. Fokusverlust verwirft offene
Anfragen. Ungebundene Controls senden keine Anfrage und empfangen keine
Add-on-Ausgabe. Dieses Verfahren ist ereignisgetrieben; Polling und
Terminal-Screen-Scraping sind dafür ausdrücklich ausgeschlossen.
Die Präsentation der bestätigten Antwort ist profilabhängig wahlweise still,
die aktuelle strukturierte Zeile oder der bisherige Datei-/Spezialkontext mit
Modus und benutzerdefiniertem Verbindungsnamen. Diese Auswahl verändert weder
die Anfrage noch ihre Gate-Wirkung. Insert- und Normalmodusklänge werden erst
nach derselben erfolgreichen Korrelation und unabhängig von der gewählten
Ansage geplant; die vorhandenen Klangschalter bleiben maßgeblich. Technische
SSH-Zieladressen gelangen nicht in den semantischen Editorzustand.

## Control-spezifische Zuordnung in Windows Terminal

Das strenge Session-Gate begrenzt die Unterdrückung nativer Ausgabe. Windows Terminal unterscheidet
Fenster, Tabs und Panes. Die aktuelle `TerminalIdentity` bezeichnet ein
UI-Automation-`TermControl` über Prozess, Fensterhandle und Runtime-ID. Bis dies
für alle unterstützten Windows-Terminal-Layouts praktisch belegt ist, muss die
Entwicklerdokumentation von Terminal-Steuerelement oder Pane sprechen und darf
nicht pauschal einen Tab annehmen.

Die erste Abschottungsstufe setzt folgende Grenzen:

- Der Aktivierungsbefehl ist in jedem Control ausschließlich der globale
  Ein-/Ausschalter. Bei eingeschaltetem Dienst autorisiert der physische
  F12-Druck selbst genau einen Zuordnungsversuch für das fokussierte
  `TermControl`; die verzögerte Hauptthread-Prüfung verwirft ihn bei jedem
  zwischenzeitlichen Identitätswechsel.
- Eine zentrale, von den WT-AppModule-Instanzen gemeinsam besessene
  Beobachterregistrierung verhindert mehrfache Add-on-Aktionen.
- In einem ungebundenen Control darf F12 als ausdrückliche Benutzeraktion eine
  einmalige, bounded Registry-/Zielprüfung starten. Ohne frischen Neovim-Claim
  entstehen keine Meldung, Auswahl, Bindung oder Unterdrückung.
- Ereignisse anderer verbundener Instanzen werden verworfen und dürfen keine
  aktivitätsbasierte Umbindung oder Add-on-Oberfläche auslösen.
- Fokusverlust suspendiert das Gate fail-open. Beim Wechsel zu einer gemerkten
  Bindung wird die vorhandene authentifizierte Verbindung nur ausgewählt. Erst
  die zu Control, Instanz und Request-ID passende frische `focusContext`-Antwort
  reaktiviert Unterdrückung. Verspätete Antworten und zwischenzeitliche
  Editorereignisse bleiben wirkungslos.
- Mehrere gebundene Tabs, Split-Panes und Fenster behalten getrennte
  Instanz- und Laufzeitzustände und können weiterhin gewechselt werden.

Folgende Pfade bleiben weiter zu untersuchen:

- `focusContext` beweist eine frische Antwort der richtigen Neovim-Instanz,
  aber noch nicht unabhängig, dass innerhalb desselben `TermControl` nicht
  inzwischen eine Shell oder ein anderes tmux-Fenster sichtbar ist. Eine
  zusätzliche ereignisgetriebene Korrelation mit Neovim `FocusGained` und
  `FocusLost` ist zu prototypisieren.
- Die Braille-Overlayklasse wird für jedes geeignete
  Windows-Terminal-Steuerelement erwogen und ist ohne gebundenen strukturierten
  Zustand auf korrektes Fallback angewiesen.

Die verbleibenden Pfade bedeuten, dass vollständige Wirkungslosigkeit in allen
Layouts erst nach praktischem Negativtest als belegt gelten kann. Terminaltext oder
Titel dürfen diese Evidenzlücke nicht durch Screen Scraping schließen;
Unsicherheit muss fail-open bleiben.

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
