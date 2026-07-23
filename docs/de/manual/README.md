# Neovim Access Link – Handbuch

Neovim Access Link verbindet Neovim in Windows Terminal mit NVDA. Statt das
wechselnde Terminalbild auszulesen, erhält das Add-on strukturierte Daten
direkt von Neovim. Dadurch kann NVDA Editorzustände wie Modus, Cursorposition,
Textänderungen, Auswahl, Einrückung, Vervollständigung und Diagnosen gezielt
ausgeben. Ein Explorationsmodus liest Zeichen, Wörter und Zeilen vorübergehend,
ohne den echten Neovim-Cursor zu bewegen.

Das Handbuch beschreibt den aktuellen Alpha- bis Beta-Stand für NVDA 2026.1.x unter
Windows 11. Unterstützt werden:

- lokales Windows-Neovim als `nvim.exe` in Windows Terminal,
- Neovim auf Linux über SSH,
- mehrere Windows-Terminal-Fenster, -Tabs und geteilte Panes,
- mehrere parallele lokale und entfernte Neovim-Instanzen,
- gemischte Neovim- und normale Shell-Panes,
- tmux innerhalb einer SSH-Sitzung.

Noch nicht unterstützt werden andere Terminalprogramme wie PuTTY, grafische
Neovim-Oberflächen und automatisch erkannte portable oder durch `NVIM_APPNAME`
getrennte Windows-Datenverzeichnisse.

## Reifegrad und wichtiger Braillehinweis

Das Add-on befindet sich in einem Alpha- bis Beta-Zustand. Die grundlegenden
lokalen und entfernten Verbindungswege wurden praktisch geprüft, aber noch
nicht jede beschriebene Editorfunktion wurde ausführlich in allen Modi und
Konfigurationen getestet. Fehler und unvollständige Rückmeldungen sind daher
zu erwarten.

Die Entwicklung versucht, wichtige Arbeitsabläufe, Sicherheitsgrenzen und
bekannte Fehler sorgfältig zu prüfen. Daraus folgt keine Zusage, dass jede
Kombination aus Editorfunktion, Plugin, Terminalaufteilung und Umgebung
abgedeckt ist. Gemeldete Fehler werden nach Möglichkeit zeitnah untersucht und
behoben; feste Reaktions- oder Behebungszeiten werden nicht zugesagt.

Die Braillefunktionen wurden bislang nicht mit einer echten Braillezeile
getestet und enthalten sehr wahrscheinlich Fehler. Braille ist für das Projekt
selbstverständlich wichtig und als priorisierte weitere Test- und
Korrekturarbeit eingeplant.

## Für wen welches Dokument gedacht ist

Wer das Add-on erstmals einrichtet, beginnt mit dem separaten
[Quick Guide](neovim-access-link-quick-guide-de.html). Er enthält nur die
nötigen Schritte von der Installation bis zur ersten lokalen oder entfernten
Verbindung.

Dieses Handbuch erklärt anschließend die derzeit unterstützten Einstellungen,
Kommunikationswege und Bedienkonzepte im Zusammenhang. Technische Implementierungsdetails, Testnachweise
und Architekturentscheidungen gehören nicht zum Anwenderhandbuch und bleiben
in der Entwicklungsdokumentation des Quellprojekts.

## Grundbegriffe

### Add-on

Das NVDA-Add-on läuft unter Windows. Es verwaltet Einstellungen, Verbindungen,
Sprache, Braille und die sichere Unterdrückung der normalen Terminalausgabe,
sobald eine Neovim-Sitzung eindeutig verbunden ist.

### Neovim-Plugin

Das Plugin läuft in jeder unterstützten Neovim-Instanz. Es liest Editorzustände
über Neovims APIs und erzeugt semantische Ereignisse. Das Plugin wird über den
Komponentenbefehl des Add-ons installiert und nach einem Neovim-Neustart
automatisch geladen.

### Bridge

Bei einer Linux-Verbindung übersetzt die Bridge zwischen Neovims RPC-Protokoll
und dem begrenzten Nachrichtenstrom über SSH. Sie wird pro Benutzer ohne
root-Rechte installiert. Für lokales Windows-Neovim ist keine separate Bridge
nötig; das Add-on verbindet sich direkt mit dem lokalen Neovim-RPC-Port auf
`127.0.0.1`.

### Verbindung

Eine gespeicherte Linux-Verbindung enthält nur Angaben zum SSH-Ziel und zur
Anmeldeart. Sie bezeichnet noch keine bestimmte laufende Neovim-Instanz. Für
lokales Windows-Neovim ist kein gespeicherter Verbindungseintrag erforderlich.

### Sitzung

Eine Sitzung ist eine konkrete laufende Neovim-Instanz. Auf demselben Rechner
können mehrere Sitzungen parallel existieren, auch mit identischem
Arbeitsverzeichnis.

### Terminalzuordnung

Die Zuordnung verbindet genau ein Windows-Terminal-Control – je nach Aufbau
ein Tab oder Pane – mit genau einer laufenden Neovim-Sitzung. Sie wird nicht aus Fenstertiteln oder Terminaltext
erraten. Standardmäßig bestätigt der Benutzer die fokussierte Sitzung mit F12.

## Das wichtigste Bedienmodell

Der normale Ablauf besteht aus vier getrennten Schritten:

1. Das Add-on und die Komponenten werden installiert.
2. Der Aktivierungsbefehl erfasst erreichbare lokale und gespeicherte entfernte
   Ziele im Hintergrund. Dabei entsteht noch keine dauerhafte Editorverbindung.
3. F12 markiert die gerade fokussierte Neovim-Instanz kurzzeitig und still.
4. Das Add-on findet genau diesen neuen Claim und bindet die Sitzung an das
   fokussierte Windows-Terminal-Control, also je nach Layout an den Inhalt
   eines Tabs oder an ein Pane.

F12 ist daher weder ein Ein-/Ausschalter noch ein SSH-Verbindungsprofil. Die
Taste wird von NVDAs ausschließlich für Windows Terminal geladenem AppModule
erkannt, unverändert an Windows Terminal und Neovim weitergereicht und danach
zur eindeutigen Auswahl ausgewertet. In anderen Anwendungen greift das Add-on
nicht auf F12 zu.

Wenn der automatische Weg nicht passt, kann dem Befehl „Server wählen und
dieses Terminal mit einer neuen Neovim-Sitzung verbinden“ eine eigene
NVDA-Geste zugewiesen werden. Der zugängliche Dialog zeigt verständliche Namen
und Arbeitsverzeichnisse; interne Sitzungs-IDs müssen nicht eingegeben werden.

## Sicherheit und Verhalten bei Fehlern

Lokale RPC-Verbindungen sind ausschließlich an IPv4-Loopback `127.0.0.1`
gebunden. Entfernte Verbindungen verwenden SSH-stdin/stdout und öffnen keine
zusätzlichen Netzwerkports. Passwörter werden weder im Profil noch im
Diagnosebericht gespeichert.

Normale Terminalausgabe wird nur unterdrückt, wenn das fokussierte
Windows-Terminal-Control einer authentifizierten und aktiven Neovim-Sitzung
zugeordnet ist. Bei Deaktivierung, Verbindungsabbruch, ungültigen Ereignissen
oder unbekanntem Control fällt NVDA auf die normale Terminalausgabe zurück.

## Handbuchkapitel

1. [Einstellungen und Verbindungsprofile](settings.md)
2. [Kommunikation, Verbindungen und Sitzungszuordnung](communication.md)
3. [Betrieb mit SSH und tmux](ssh-and-tmux.md)
4. [Menüs und Vervollständigung](menus-and-completion.md)
5. [Eingebettetes Terminal und Dateimanager](terminals-and-file-managers.md)
6. [Sounds und Earcons](sounds.md)
7. [Braille-Unterstützung](braille.md)
8. [Fehlerdiagnose und Diagnosebericht](troubleshooting.md)

## Empfohlene erste Funktionsprüfung

Nach Installation und Einrichtung sollte nicht sofort mit einer wichtigen
Datei begonnen werden. Zuerst in einem Testpuffer prüfen:

1. Insert-, Normal- und Visual-Modus wechseln.
2. Zeichen, Wörter und Zeilen navigieren.
3. Mit gedrückter NVDA-Taste Zeichen, Wörter und Zeilen explorieren und prüfen,
   dass der echte Cursor stehen bleibt.
4. Text einfügen und löschen.
5. Zwischen zwei verbundenen Tabs wechseln.
6. Das Add-on deaktivieren und sicherstellen, dass NVDA wieder die normale
   Terminalausgabe verwendet.

Bei mehreren Sitzungen muss NVDA stets nur den Inhalt des aktuell fokussierten
und zugeordneten Neovim ausgeben. Terminalstatuszeilen, Inhalte anderer Tabs
und Ereignisse einer früheren Sitzung dürfen nicht gesprochen werden.

## Versions- und Testhinweis

Der aktuelle Stand wurde mit Windows 11 25H2, NVDA 2026.1.1, Rocky Linux 10.2
und Neovim 0.10.1 praktisch erprobt. Der Reifegrad bleibt zwischen Alpha und
Beta; aus diesem praktischen Referenztest folgt keine allgemeine
Stabilitätszusage. Vor wichtiger Arbeit
sind normale Backups und ein schrittweiser Test mit der eigenen SSH-, tmux-,
Braille- und Neovim-Konfiguration sinnvoll.
