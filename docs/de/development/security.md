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
an. Zustandsändernd sind ausschließlich validiertes `routeCursor`,
`brailleRouteAction`, `moveBrailleLine`, die unten
beschriebenen Zwischenablagebefehle, `leaveTerminalInputRequest` mit der
festen Operation `stopinsert` sowie die rein lesenden Explorationsbefehle.

Vor dem Aufruf der Neovim-Cursor-API prüft `routeCursor` festes Ziel, Buffer,
Fenster, `changedtick`, exakten Rohmodus, Zeile, UTF-8-Bytespalte und
Zeichenrand. Ein veralteter Braille-Routingbefehl wird verworfen. Für die
aktive Befehlszeile werden zusätzlich der höchstens 16 KiB große Inhalt und
der strukturierte Typ exakt verglichen. `setcmdline()` erhält ausschließlich
den bereits exakt abgeglichenen, unveränderten Text und die validierte
Ganzzahlposition; eine erneute Prüfung folgt direkt nach dem Aufruf.
Befehlszeilentext wird weder ausgeführt noch unredigiert in die Diagnose
übernommen. `leaveTerminalInputRequest` prüft
Anfrage-ID, aktive Control-/Instanzbindung, Buffer, Fenster, Tab und den rohen
Terminalmodus `t`; frei wählbarer Lua- oder Ex-Text wird nicht übertragen.
`exploreTextRequest` akzeptiert nur sechs feste Bewegungen, korreliert den
vollständigen Editorursprung und verändert weder Cursor noch Buffer. Ergebnis,
Wiederholung und Wortsuche sind begrenzt; Fokus- oder Kontextwechsel verwerfen
den flüchtigen Zustand.

`brailleRouteAction` verlangt die eigene ausgehandelte Capability und erlaubt
nur vier feste Aktionskennungen sowie drei feste Zeilenstarts. Der Payload
enthält keinen auszuführenden Text. Zusätzlich zu den Routingprüfungen werden
die exakte Cursorposition, Änderbarkeit und Schreibschutz unmittelbar vor
der Ausführung geprüft; Wortaktionen auf Leerraum oder Zeilenende werden
verworfen. Ein alter Timer oder ein inzwischen veränderter Buffer scheitert
spätestens an `changedtick`, Modus oder Cursoridentität. Die interne Abbildung
auf feste Normalbefehle ist keine allgemeine RPC- oder Tasteneinspeisung.

`moveBrailleLine` akzeptiert ausschließlich `previous` oder `next`, verlangt
die ausgehandelte Capability `brailleLineNavigation` und korreliert Buffer,
Fenster, Ausgangszeile, `changedtick` und exakten Rohmodus. Die bevorzugte
virtuelle Spalte ist eine begrenzte Ganzzahl. Das Plugin bewegt höchstens um
eine Zeile, verwirft Puffergrenzen sowie Befehlszeilen- und Terminalmodus und
verwendet keinen übertragenen Lua- oder Ex-Text.

Der getrennte `brailleExploreLineRequest` akzeptiert ausschließlich eine
benachbarte Zeile und eine begrenzte gewünschte virtuelle Spalte. Er verlangt
die unabhängige Capability `brailleExploration`, besitzt einen eigenen
Korrelations- und Lua-Zustand und verändert weder den Sprachexplorationsmodus noch den
echten Cursor. Die erste Anfrage muss den vollständigen echten Ursprung
treffen. Folgeanfragen dürfen nur bei unverändertem Buffer, Fenster und Tab
von einer inzwischen anderen echten Cursor-, Modus- oder Textposition
abweichen. `changedtick` darf auf den im selben Buffer aktuell geprüften Wert
fortgeschrieben werden; Ursprungsidentität, Explorations-ID und Aktionsfolge
bleiben exakt.
Die lokale abgeleitete Brailleansicht übernimmt neuen Zeileninhalt nur bei
gültigem begrenztem Text und exakter Übereinstimmung von echter Cursorzeile
und virtueller Anzeigezeile. Das erweitert weder Protokollbefugnisse noch
Schreibzugriffe und verändert den kanonischen Zustand nicht.
Der Ausschnittserhalt verwendet ausschließlich die öffentliche
`TextInfoRegion.pendingCaretUpdate`-Markierung der eigenen strukturierten
Region. Er greift nicht auf NVDAs private Buffer- oder Fensterfelder zu und
verändert keine fremden Regionen.
Nur ein späterer, erneut vollständig validierter
`routeCursor`-Auftrag darf die virtuelle Position übernehmen. Ergebnisse
werden weder im Bridge- noch im Client-Zustand zwischengespeichert.

`acceptNumberedChoiceRequest` akzeptiert nur einen bereits strukturiert
erkannten, aktiven Auswahleintrag mit exakter Prompt- und Editoridentität. Für
Rechtschreibvorschläge wird ausschließlich die feste Neovim-Eingabe aus
internem Index und `Enter` erzeugt. Vorschlagstext wird weder ausgeführt noch
zurückgesendet. Ein Fokuswechsel oder das Schließen der Abfrage verwirft den
flüchtigen Auswahlzustand.

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
Ereignisse, Overlays, F12, frei belegbare Befehle und der standardbelegte
Diagnosebefehl gehören ausschließlich zum von NVDA an
`windowsterminal.exe` gebundenen AppModule. NVDA zeigt die frei belegbaren
Befehle zunächst an, wenn Windows Terminal vor dem Öffnen des Eingabedialogs
fokussiert war. Sobald das Modul geladen ist, kann NVDAs globale
Benutzergestenkarte eine gespeicherte Zuordnung auch aus einer anderen
Anwendung heraus auflisten; bei der Laufzeitauflösung wird sie dort trotzdem
nicht ausgewählt. Beim Aufruf verlangt der Adapter zusätzlich genau seine
konkrete AppModule-Instanz und ein vollständig validiertes Windows-Terminal-
Control. Ein Fokusrennen gibt die Originalgeste unverändert weiter und
verändert weder Gate noch Bindungen oder Unterdrückung. Globale
Ereignishandler existieren nicht.
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
AppModule-Instanzen teilen eine Beobachterregistrierung. Sie prüft nach einem
F12-Treffer NVDAs aktuelles Fokusobjekt und akzeptiert ausschließlich genau
dessen noch registrierte AppModule-Instanz sowie dieselbe vollständige
Control-Identität im Gate; einen Einzeladapter-Fallback gibt es nicht. Die
einmalige Generation verhindert doppelte Verarbeitung. Im Insert-Modus
konsumiert das Plugin nur ein ansonsten unbelegtes Claim-F12 nach der
Beobachtung; vorhandene Benutzerbelegungen werden nicht überschrieben. Vor
der ersten Verbindung kann Neovim NVDAs Autorisierungszustand nicht kennen.
Diese Reservierung gilt deshalb innerhalb Neovims für jedes konfigurierte,
unbelegte Insert-Claim-F12, bleibt aber auf genau diese Taste und diesen Modus
beschränkt; NVDA selbst konsumiert die physische Taste nie.
Netzwerkaktivität darf keine Umbindung an ein ungebundenes Control anbieten
oder durchführen.

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
