# Sicherheit und Datenschutz

## Transport und Vertrauensgrenzen

- Der einzige unterstützte Ferntransport ist Protokoll v2 über
  Windows-OpenSSH-stdin/stdout.
- Für lokales Windows-Neovim existiert genau ein von Neovim dynamisch
  angelegter MessagePack-RPC-Port auf `127.0.0.1`. Es gibt keine Listener auf
  LAN-Adressen, Portweiterleitungen oder Anwendungstokens.
- `ClearAllForwardings=yes` verhindert unerwartete Forwardings aus der
  Benutzerkonfiguration; OpenSSH führt normale Host-Key-Prüfung aus.
- Direkter Neovim-MessagePack-RPC bleibt lokal: unter Linux zwischen Bridge und
  privatem Unix-Socket, unter Windows zwischen Add-on und IPv4-Loopback-Port.
- Empfangene Nachrichten werden typ- und größenvalidiert. Text aus einer
  Nachricht wird niemals als Python-, Lua- oder Ex-Code ausgeführt.

Die Bereinigung der dateibasierten Sitzungsregistrierung beendet keinen Prozess.
Diese JSON-Dateien sind keine Windows-Registry-Daten; das Produkt verwendet
weder `HKCU` noch `HKLM`. Schema-3-Dateien sind durch
PID plus zufällige Nonce eindeutig. Nur eine zweifelsfrei tote oder durch die
Prozessstartkennung widerlegte Datei wird entfernt. Die Nonce-Prüfung erfolgt
erst auf dem ausgewählten dauerhaften RPC-Kanal und löscht bei einem
Unterschied nichts. Ein Socket wird nur bei `ownsSocket=true`
und dem exakt zu PID plus Nonce gehörenden Pluginpfad entfernt; übernommene und
benutzerdefinierte Pfade bleiben unangetastet. Timeout, SSH-/UIA-Fehler oder
Zugriffsunsicherheit bleiben nicht-destruktiv.

## SSH-Anmeldung

Empfohlen sind Windows-OpenSSH-Konfiguration, Schlüssel und ssh-agent. Ein
optionaler Schlüsselpfad wird als separates Argument übergeben; Host, Benutzer,
Port und Pfad werden gegen Options- und Steuerzeicheninjektion validiert.

Bei bewusst gewählter Passwortanmeldung:

- fragt NVDA auf dem Hauptthread zugänglich nach;
- wird das Passwort nicht persistiert;
- erscheint es nicht in der Prozesskommandozeile;
- erhält ausschließlich der kurzlebige OpenSSH-Prozess das Passwort in seiner
  Umgebung;
- liest `ssh-askpass.cmd` diese Variable, ohne selbst ein Geheimnis zu
  enthalten;
- wird der Speicher beim Deaktivieren oder Beenden geleert;
- ist nur ein Passwortversuch pro Prozess erlaubt.

Add-on-Einstellungen liegen in NVDAs normaler profilfähiger Konfiguration.
Verbindungsprofile enthalten nur Zielparameter und gegebenenfalls den Pfad zu
einer Schlüsseldatei; Passwörter und Schlüsselmaterial werden auch bei
NVDA-Profilwechseln niemals in `config.conf` geschrieben.

Die automatische Zielerfassung öffnet keinen Anmeldedialog. OpenSSH-Ziele
werden im Hintergrund mit der normalen nichtinteraktiven Konfiguration geprüft;
Passwortziele nehmen nur teil, wenn das Passwort bereits im flüchtigen Speicher
dieser NVDA-Laufzeit vorliegt. Die Erfassung ist auf vier parallele Arbeiter
begrenzt. Ein fehlgeschlagenes oder nicht erreichbares Ziel darf weder eine
andere Zuordnung vortäuschen noch den NVDA-Hauptthread blockieren.

## Sitzungsdateien und Installation

Das Verzeichnis der dateibasierten Sitzungsregistrierung und seine JSON-Dateien
liegen im privaten Linux-Laufzeitverzeichnis beziehungsweise unter
`%LOCALAPPDATA%\nvim-nvda\sessions`. Es handelt sich nicht um die Windows-
Registry. Linux-
Einträge benötigen lebende PIDs und private Unix-Sockets; Windows-Einträge
benötigen lebende PIDs, den Typ `localWindowsTcp` und exakt `127.0.0.1`.
Die Windows-PID-Prüfung fordert ausschließlich lesende Prozessrechte an.

Die Sitzungsdateibereinigung beendet keine Prozesse. Sie löscht nur einen eindeutig
toten oder durch Prozessstart/Nonce widerlegten privaten Eintrag. Ein Socket
wird nur bei `ownsSocket=true` und exakt erwartetem privaten Standardpfad
entfernt. Timeout, SSH-Ausfall, Fokusverlust oder fehlende Leserechte führen
niemals zum Löschen. Geschlossene WT-Tabs oder ganze Fenster stoppen nur den lokalen
NVDA-Client; entfernte Neovim-/tmux-Prozesse bleiben unangetastet.

Die Installation läuft ohne Root-Rechte und schreibt ausschließlich in
`~/.local` des ausdrücklich ausgewählten Linux-Kontos. Sie ändert weder
`sshd_config` noch Benutzer-SSH-Konfiguration. Systemweite Tests benötigen
separate ausdrückliche Autorisierung und eine dokumentierte Rücknahme.

Die lokale Installation ersetzt atomar nur den Add-on-eigenen Pluginordner
unter `%LOCALAPPDATA%\nvim-data\site\pack`; sie ändert keine `init.lua` und
benötigt keine Administratorrechte. Symbolische Links in der eingebetteten
Quelle werden abgewiesen.

## Protokoll und erlaubte Rückkanäle

Frames sind auf 1 MiB begrenzt. Sitzungskennung, Sequenz und `fullState`-
Resynchronisation verhindern die Ausgabe alter oder ungeordneter Ereignisse.

Die Rückrichtung ist eine feste Allowlist und keine allgemeine Neovim-RPC-
Weiterleitung. `requestFullState` und `requestFocusContext` fordern nur Zustand
an. Zustandsändernd sind ausschließlich validiertes `routeCursor`, die unten
beschriebenen Zwischenablagebefehle und `leaveTerminalInputRequest` mit der
festen Operation `stopinsert`.

Vor dem Aufruf der Neovim-Cursor-API prüft `routeCursor` Buffer, Fenster,
`changedtick`, Zeile, UTF-8-Bytespalte und Zeichenrand. Ein veralteter
Braille-Routingbefehl wird verworfen. `leaveTerminalInputRequest` prüft
Anfrage-ID, aktive Control-/Instanzbindung, Buffer, Fenster, Tab und den rohen
Terminalmodus `t`; frei wählbarer Lua- oder Ex-Text wird nicht übertragen.

Zusätzlich existiert ein eng begrenzter, ausdrücklich durch frei belegbare
NVDA-Befehle ausgelöster Zwischenablagepfad. Er akzeptiert keine frei wählbaren
Lua-, Ex- oder Registernamen: Kopieren liest nur die aktuelle Visual-Auswahl
oder Register 0, Einfügen verwendet nur Neovims Paste-API, und der
Register-Schreibbefehl verwendet fest Register 0 und lässt das unbenannte
Register darauf zeigen. Alle Richtungen
prüfen Anfrage-ID, aktive Control-Bindung, Instanz, Buffer, Fenster, Tab,
`changedtick` und Modus. Paste ist auf normale veränderbare Editorbuffer
begrenzt; Text ist NUL-frei und auf 256 KiB UTF-8 beschränkt. Fokusverlust,
Disconnect oder Zustandsabweichung verwirft die ausstehende Antwort ohne
Wiederholung. Ein bereits an die zuvor ausdrücklich fokussierte Sitzung
abgesandter Paste kann nicht nachträglich zurückgezogen werden, darf aber nie
die neue Sitzung treffen oder wiederholt werden. Copy-Text wird nie im
Bridge-/Client-Zustands-Cache behalten und in Diagnosen redigiert.

## Diagnose und vertraulicher Text

Quelltext, Zeilen, Auswahl, Registerinhalt, Passwort und sonstige Text-Payloads
werden im kopierbaren Bericht redigiert. Der Diagnosepuffer ist auf 500
Einträge begrenzt. Prozess-stderr bleibt begrenzt sichtbar, damit SSH- und
Installationsfehler diagnostizierbar sind, darf aber keine Zugangsdaten
enthalten.

Es werden keine vollständigen Buffer ohne konkrete Anforderung übertragen.
Private Testkonten, temporäre Passwörter und Rücknahmebefehle gehören
ausschließlich in ignorierte Dateien unter `tmp/`.

## Temporäre Terminalidentitäten

NVDA lädt die Aktivierungs-, Zuordnungs- und Unterdrückungshandler ausschließlich
über `appModules/windowsterminal.py` für Windows Terminal. Innerhalb dieses
AppModules setzen sie eine explizit freigegebene Windows-Terminal-UIA-Klasse und
eine nichtleere Runtime-ID voraus. Das Session-Gate prüft die Frontendart
unabhängig ein zweites Mal.
Unbekannte, deaktivierte oder nur geplante Adapter bleiben fail-open; die
Konfiguration kann keinen nicht implementierten Adapter freischalten.
Ereignisse, Overlays, F12 und der standardbelegte Diagnosebefehl gehören
ausschließlich zum von NVDA an `windowsterminal.exe` gebundenen AppModule. Das
Global Plugin bietet nur unbelegte Skriptmetadaten für frei konfigurierbare
Befehle, damit diese im Eingabedialog immer sichtbar sind. Bei einem Aufruf
fragt der Adapter den Fokus einmal ab und delegiert nur für ein vollständig
validiertes Windows-Terminal-Control. In fremden Anwendungen gibt er die
Originalgeste unverändert weiter und verändert weder Gate noch Bindungen oder
Unterdrückung. Globale Ereignishandler existieren nicht.
Beim Verlassen von Windows Terminal räumt `event_appModule_loseFocus` den
fokussierten Terminal- und Unterdrückungszustand auf. Ein pro AppModule
undurchsichtiges Token verwirft verspätete Fokusverlustmeldungen eines alten
WT-Prozesses. Auch der zweiphasige Fokusabschluss ist an Token, Generation und
konkrete Terminalidentität gebunden.

Das optionale Merken eines Windows-Terminal-Controls verwendet nur Prozess-ID,
Fensterhandle, UIA-Klasse und die undurchsichtige UIA-Runtime-ID. Das Control
entspricht je nach Layout einem Tabinhalt oder einem Pane. Titel,
Terminaltext, Prompt, Hostname und Benutzername werden nicht zur Erkennung
ausgelesen. Die Zuordnung wird nicht in der Konfiguration gespeichert und nach
NVDA-Ende, Verbindungsende oder ungültiger Identität verworfen. Ohne vorherige
Zustimmung erfolgt keine automatische Wiederbindung zwischen Controls.

Der physische F12-Druck autorisiert bei eingeschaltetem Dienst genau einen
Sitzungsdatei-Claim-Versuch für die fokussierte `TerminalIdentity`. Ein
zwischenzeitlicher Fokuswechsel verwirft ihn; ohne frischen Neovim-Claim bleibt
die Prüfung ohne Bindung, Dialog, Ausgabe oder Unterdrückung. Alle WT-
AppModule-Instanzen teilen eine Beobachterregistrierung; die einmalige
Generation verhindert doppelte Verarbeitung. Netzwerkaktivität darf keine
Umbindung an ein ungebundenes Control anbieten oder durchführen.

Beim Fokusverlust wird Unterdrückung sofort suspendiert. Eine gemerkte Bindung
wird erst nach einer frischen, zu Control, Instanz und Request-ID passenden
`focusContext`-Antwort reaktiviert; bis dahin werden auch Ereignisse der
authentifizierten Instanz verworfen. Mehrere gebundene Controls in Tabs,
Split-Panes und Fenstern bleiben getrennt auswählbar.

Das Session-Gate ist trotzdem noch kein vollständiger unabhängiger Nachweis
des Vordergrundprogramms innerhalb desselben Windows-Terminal-Panes. Eine
`TerminalIdentity` belegt das fokussierte
UIA-Terminal-Steuerelement, aber allein noch nicht, dass innerhalb dieses
Steuerelements weiterhin Neovim im Vordergrund steht. Bis frische strukturierte
Evidenz, ein zusätzlicher Fokusnachweis und praktische negative Pane-Tests diese
Lücke schließen, muss jeder unklare Zustand fail-open bleiben. Die passive
Overlayauswahl bleibt ebenfalls Teil dieser Prüfung.
