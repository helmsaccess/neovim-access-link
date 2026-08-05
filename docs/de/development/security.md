# Sicherheit und Datenschutz

## Transport und Anmeldedaten

Entfernte Verbindungen verwenden Windows OpenSSH mit Standard-Ein- und
-Ausgabe. SSH authentifiziert Host und Benutzer; normale
Hostschlüsselprüfung bleibt aktiv. `ClearAllForwardings=yes` verhindert
geerbte Portweiterleitungen. Schlüssel und `ssh-agent` sind der empfohlene
Pfad.

Optional eingegebene Passwörter werden zugänglich abgefragt, nur im Speicher
gehalten und ausschließlich dem kurzlebigen SSH-Prozess über Askpass
bereitgestellt. Sie erscheinen nicht in Argumenten, Dateien oder Logs und
werden bei Deaktivierung oder Ende verworfen.

Lokales RPC verbindet ausschließlich einen vom Plugin registrierten,
dynamischen Endpunkt auf `127.0.0.1`. Benutzer können keine andere Adresse
konfigurieren.

## Sitzungsdateien und Installation

Die dateibasierte Sitzungsregistrierung liegt in einem privaten
Benutzerverzeichnis. Unter Linux prüft die Bridge Verzeichnis- und
Dateieigentümer, Prozessstart, PID, Nonce und Socket. Unter Windows prüft das
Add-on Schema, noncegebundenen Dateinamen, lebende PID und den ausschließlich
an IPv4-Loopback gebundenen Endpunkt. Die Datensätze sind keine
Windows-Registry-Schlüssel.

Bereinigung beendet keinen Prozess. Ein Socket wird nur entfernt, wenn der
Datensatz ihn ausdrücklich als plugin-eigen kennzeichnet und Pfad, PID und
Nonce übereinstimmen. Geerbte oder benutzerdefinierte Pfade bleiben
unangetastet. Timeout, SSH-Fehler, Fokusverlust oder unklare Zugriffsrechte
führen zu einem nicht destruktiven Rückfall.

Installation und Entfernung verwenden nur festgelegte Benutzerpfade und
zeitlich begrenzte Befehle. Das Schließen eines Windows-Terminal-Tabs beendet
nur den zugehörigen NVDA-Client, nie Neovim oder tmux.

## Protokoll und Steuerbefehle

Protokollnachrichten sind größenbegrenzt, schemageprüft und an Sitzung sowie
Sequenz gebunden. Eingehende Daten werden nicht ausgeführt und gewähren keinen
allgemeinen Neovim-RPC-Zugang.

Die Rückrichtung besitzt eine feste Allowlist für Zustandsanforderung,
Cursor-Routing, begrenzte Brailleaktionen, read-only Exploration, ausdrückliche
Zwischenablagebefehle, Terminal-Normalmodus und kontextbezogene nummerierte
Auswahlen. Jeder zustandsändernde Befehl prüft je nach Vorgang Sitzung,
Control, Instanz, Buffer, Fenster, Tab, `changedtick`, Modus, Cursor und
Anfrage-ID erneut.

- Routing und Brailleaktionen enthalten feste Bezeichner, keine Lua-, Ex- oder
  Tastaturtexte. Schreibaktionen prüfen Modifizierbarkeit und Read-only-Status.
- Exploration bewegt nur eine begrenzte virtuelle Position. Sie verändert
  weder Cursor noch Buffer und wird bei Fokus- oder Kontextwechsel verworfen.
- Rechtschreibauswahl sendet nur den intern validierten numerischen Index an
  einen weiterhin identischen aktiven Prompt. Vorschlagstext wird nicht
  ausgeführt oder zurückgesendet.
- Zwischenablagezugriff beginnt nur durch frei belegbare NVDA-Befehle. Quellen,
  Register und Zieloperationen sind fest; Paste ist NUL-frei und auf 256 KiB
  UTF-8 begrenzt.

Die vollständigen Payloads und Grenzen stehen in [Protokoll](protocol.md).

## Fokus und Unterdrückung

Ein Terminalpfad wird nur für eine authentifizierte, aktive, fokussierte und
exakt gebundene Neovim-Sitzung unterdrückt. Fehler, Timeout, Disconnect,
Reload, Deaktivierung oder Identitätsabweichung fallen sofort auf NVDAs native
Terminalbehandlung zurück.

Ein physischer F12-Druck autorisiert genau einen Zuordnungsversuch für das
aktuell fokussierte `TerminalIdentity`. Fokusobjekt, registrierte
AppModule-Instanz, vollständige Control-Identität und Gate werden vor Beginn
und erneut auf NVDAs Hauptthread geprüft. Ein Fokuswechsel oder eine Aktivität
aus einer anderen Neovim-Instanz kann keine Bindung verschieben.

Konfigurierbare Befehle gehören dem Windows-Terminal-AppModule. Auch wenn
NVDAs Benutzergestenkarte eine gespeicherte Zuordnung außerhalb der Anwendung
anzeigt, verlangt die Ausführung dieselbe konkrete AppModule- und
Control-Identität. Fokusgenerationen und Adaptertoken verwerfen verspätete
Antworten.

## Diagnose und vertraulicher Text

Diagnoseberichte schwärzen Textinhalte, Tokens, Zwischenablagedaten und andere
potenziell vertrauliche Payloads. Logs sind rein diagnostisch und keine
Voraussetzung für Korrektheit. Protokollfehler werden mit Typ und Grenze, nicht
mit vollständigem Benutzertext, festgehalten.

Agenteneigene Reproduktionen, Downloads und Berichte liegen außerhalb des
Repositorys unter `/nfs/src/nal-tmp/` und werden nie versioniert. Vom Projekt
selbst erzeugte Laufzeit- oder Testausgaben verwenden ausschließlich ihre
dokumentierten, ignorierten Pfade.

## Verbleibende Grenze

Eine bestätigte RPC-Sitzung beweist nicht allein, dass innerhalb eines bereits
gebundenen `TermControl` weiterhin Neovim sichtbar ist, wenn eine Shell oder
ein tmux-Client den Vordergrund ersetzt. Unsichere oder ungebundene Controls
erhalten dadurch keine Berechtigung; eine Lösung darf nicht auf allgemeinem
Terminal-Screen-Scraping beruhen. Der Umfang wird in
[Kompatibilität](compatibility.md) als nicht freigegebene Breite behandelt.
