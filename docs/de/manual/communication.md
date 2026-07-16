# Handbuch: Kommunikation, Verbindung und Sitzungszuordnung

Dieses Kapitel erklärt, wie Neovim Access Link die richtige Neovim-Instanz
findet, wer eine Verbindung zu wem aufbaut und welche Aufgabe F12 dabei hat.
Es gilt für lokales Neovim unter Windows und für Neovim auf Linux über SSH.

## Das einfache Grundmodell

Bei der Arbeit sind drei Dinge voneinander zu unterscheiden:

1. **Windows Terminal:** Hier liegt der Tastaturfokus. Das aktuelle Control in
   einem Fenster, Tab oder Pane kann ein lokales `nvim.exe` oder eine sichtbare
   SSH-Sitzung anzeigen.
2. **Die gewünschte Neovim-Instanz:** In ihr läuft das Lua-Plugin. Es kennt
   Modi, Cursor, Buffer, Auswahl und Completion aus Neovims APIs.
3. **Die Accessibility-Verbindung:** Sie überträgt diese strukturierten Daten
   zum NVDA-Add-on. Sie ist nicht dasselbe wie die sichtbare Terminalsitzung.

Das Add-on liest nicht den Terminalbildschirm, um eine Instanz zu erraten. Ein
Windows-Terminal-Control wird ausdrücklich einer laufenden Neovim-Instanz
zugeordnet. Erst dann darf NVDA die native Terminalausgabe dieses Controls
unterdrücken und stattdessen strukturierte Editorereignisse ausgeben.

## Beteiligte Komponenten

### Auf Windows

- Windows Terminal stellt Fenster, Tabs und gegebenenfalls Panes bereit.
- Das anwendungsspezifische NVDA-AppModule wird ausschließlich für Windows
  Terminal geladen. Es verarbeitet Fokus und die zugehörigen Eingabegesten.
- Der gemeinsame Add-on-Dienst verwaltet Einstellungen, Verbindungen, Sprache,
  Braille, Klänge und die sichere Terminalunterdrückung.
- Windows OpenSSH wird für entfernte Linux-Ziele verwendet.
- Ein lokaler RPC-Client wird für lokales Windows-Neovim verwendet.

### In jeder Neovim-Instanz

Das Lua-Plugin erzeugt semantische Ereignisse aus Neovims APIs. Es legt einen
benutzerbezogenen Registryeintrag für die laufende Instanz an. Darin stehen
technische Sitzungsdaten wie Endpunkt, Startzeit, optionaler Name und eine
Zuordnungsnummer. Der Registryeintrag enthält keinen Editorinhalt.

### Zusätzlich auf einem Linux-Ziel

Die rootlos installierte Bridge verbindet sich mit dem privaten Unix-RPC-Socket
der ausgewählten Neovim-Instanz. Sie überträgt die Ereignisse als begrenztes
Protokoll v2 über SSH-stdin/stdout und öffnet keinen Netzwerkport.

## Installation ist nicht Verbindung

Der Komponentenbefehl unter `NVDA-Menü → Werkzeuge` kopiert das Plugin lokal
und/oder Plugin, Bridge und Konfiguration auf ausgewählte Linux-Konten. Er
stellt Dateien bereit, verbindet aber noch keinen Terminal-Tab mit Neovim.
Nach einem Update muss Neovim einmal neu gestartet werden. Danach genügt ein
normaler Start:

```text
nvim.exe datei
```

oder auf Linux:

```text
ssh benutzer@rechner
tmux                 # optional
nvim datei
```

Ein besonderer Wrapper ist nicht erforderlich.

## Was beim Aktivieren passiert

Der frei belegbare NVDA-Aktivierungsbefehl schaltet den gemeinsamen Dienst ein
oder wieder aus.
Beim ersten Einschalten geschieht Folgendes:

1. Das Windows-Terminal-AppModule übernimmt unmittelbar das aktuell fokussierte
   Terminalobjekt. Das gilt auch, wenn Windows Terminal schon vorher fokussiert
   war und deshalb kein neues NVDA-Fokusereignis eintrifft.
2. Das Add-on liest im Hintergrund die lokale Windows-Registry und die
   Sitzungslisten aller automatisch erreichbaren gespeicherten SSH-Ziele.
3. Es merkt sich die aktuelle Zuordnungsnummer jeder Sitzung als Ausgangswert.
4. NVDA meldet, dass die Erfassung bereit ist und F12 gedrückt werden kann.

Solange der Dienst eingeschaltet ist, autorisiert jeder physische F12-Druck
genau einen Zuordnungsversuch für die vollständige UIA-Identität des aktuell
fokussierten Controls. Der Aktivierungsbefehl bleibt dagegen überall der
globale Ein-/Ausschalter. Weitere Fenster, Tabs oder Panes werden deshalb direkt
mit F12 zugeordnet; bestehende Verbindungen bleiben erhalten.

Diese Erfassung öffnet noch keine dauerhafte Editorverbindung. Es gibt keine
Standardverbindung und keine Priorität zwischen lokalem Windows und SSH.

SSH-Profile mit Schlüssel, ssh-agent oder nichtinteraktiver OpenSSH-
Konfiguration können automatisch erfasst werden. Der Hintergrundscan öffnet
niemals ungefragt einen Passwortdialog. Passwortprofile ohne bereits flüchtig
vorliegendes Passwort bleiben über den manuellen Verbindungsdialog erreichbar.

## Die Aufgabe von F12

F12 ist eine **kurzlebige Sitzungsmarkierung**, kein Profil und kein
Ein-/Ausschalter. Bei eingeschaltetem Dienst gilt der physische Tastendruck
selbst als einmalige, control-spezifische Freigabe. In einer normalen Shell,
einem Dateimanager oder einem anderen ungebundenen Control bleibt F12 eine
gewöhnliche Taste. Die daraufhin nur einmal ausgeführte Claim-Prüfung bleibt
ohne frischen Neovim-Treffer still und löst weder Bindung noch Dialog noch
Unterdrückung aus.

1. Der Anwender fokussiert den gewünschten Tab oder das gewünschte Pane und
   drückt F12.
2. Das nur für Windows Terminal geladene NVDA-AppModule empfängt die Geste und
   aktualisiert die aktuelle Terminalidentität.
3. NVDA reicht F12 unverändert an Windows Terminal weiter.
4. Windows Terminal liefert die Taste an das laufende Programm. Bei SSH und
   tmux läuft sie durch diese sichtbare Sitzung bis zu Neovim.
5. Das Plugin erhöht still seine `claimSequence` und schreibt den Wert atomar
   in seinen Registryeintrag. Es zeigt keine Statusmeldung an.
6. Nach einer kurzen Verzögerung liest das Add-on die zuvor erfassten lokalen
   und entfernten Sitzungen erneut.
7. Nur eine gegenüber dem Ausgangswert erhöhte `claimSequence` gilt als
   ausdrückliche Auswahl dieses Tastendrucks.
8. Bei genau einem Treffer baut das Add-on die passende Verbindung auf und
   bindet sie an den fokussierten Tab. Bei mehreren Treffern erscheint eine
   zugängliche Auswahl. Ohne Treffer wird nicht geraten.

Die Freigabe gilt nur für diesen einen Tastendruck und genau dieses Control.
Der anschließend entstehende Registry-Claim wird nur in seinem kurzen
Frischefenster akzeptiert. Interne Sitzungs-IDs, Fenstertitel und Terminaltext
werden nicht benötigt. Für jedes weitere ungebundene Control genügt bei bereits
eingeschaltetem Dienst ein neuer physischer F12-Druck.

## Wechsel zwischen Fenstern, Tabs und Panes

Die Zuordnung verwendet Prozess, Fensterhandle und die vollständige UIA-
Runtime-ID des jeweiligen `TermControl`. Deshalb können mehrere Verbindungen im
gleichen Windows-Terminal-Fenster und in getrennten Fenstern parallel bestehen.
Beim Fokuswechsel wird die bisherige Unterdrückung sofort aufgehoben. Für ein
gemerktes, verbundenes Control fordert das Add-on über dessen authentifizierte
Verbindung einen neuen Fokuskontext an. Erst die passend korrelierte Antwort
aktiviert Sprache, Braille, Klänge und Unterdrückung wieder. Antworten einer
anderen oder zuvor fokussierten Verbindung werden verworfen. Ein ungebundenes
Control bleibt nativ.

## Lokaler Kommunikationsweg unter Windows

Bei einem lokalen `nvim.exe` ist Neovim selbst der lokale Server:

```text
Tastatur → Windows Terminal → lokales nvim.exe und Lua-Plugin

NVDA-Add-on
  → direkter MessagePack-RPC-Client
  → 127.0.0.1, dynamischer Port der ausgewählten Neovim-Instanz

Lua-Plugin
  → semantische nvim_nvda_event-Benachrichtigungen
  → lokaler RPC-Client
  → NVDA-Sprache, Braille und Klänge
```

Jede lokale Neovim-Instanz legt einen eigenen dynamischen RPC-Port an, der
exakt an IPv4-Loopback `127.0.0.1` gebunden ist. Host und Port sind nicht frei
konfigurierbar und werden nicht dauerhaft gespeichert. Das Plugin schreibt sie
in die Registry unter `%LOCALAPPDATA%\nvim-nvda`.

Nach der Zuordnung verbindet sich das Add-on direkt zu diesem Port und
registriert seinen RPC-Kanal beim Plugin. Das Plugin sendet danach `fullState`
und weitere Ereignisse. Bridge, SSH und Portweiterleitung sind lokal nicht
beteiligt.

## Kommunikationsweg über SSH

Bei Linux-Neovim existieren zwei unabhängige SSH-Wege.

### Die sichtbare Arbeitssitzung

Diese Verbindung hat der Anwender selbst geöffnet:

```text
Tastatur
  → Windows Terminal
  → sichtbarer OpenSSH-Prozess
  → optional tmux
  → Neovim und Lua-Plugin
```

Über diesen Weg werden normale Tasten und F12 an Neovim geliefert. Das Add-on
übernimmt oder verändert diese Arbeitssitzung nicht.

### Die unsichtbare Accessibility-Verbindung

Nach eindeutiger Zuordnung startet das Add-on einen weiteren OpenSSH-Prozess:

```text
NVDA-Add-on
  → eigener Windows-OpenSSH-Prozess
  → ~/.local/bin/nvim-nvda-bridge --session …
  → privater Unix-RPC-Socket der ausgewählten Neovim-Instanz

Neovim-Lua-Plugin
  → semantische Ereignisse
  → Linux-Bridge
  → Protokoll v2 über SSH-stdin/stdout
  → NVDA-Add-on
```

Diese zweite Verbindung benötigt kein Terminalfenster, keine SSH-
Portweiterleitung und keinen TCP-Listener auf Linux. SSH übernimmt Hostprüfung,
Anmeldung, Verschlüsselung und Integrität. Die Bridge spricht auf Linux nur mit
Neovims privatem Unix-Socket.

Wird Neovim beendet oder der Transport ungültig, verwirft das Add-on die
Sitzung und gibt die normale Terminalausgabe wieder frei. Die sichtbare Shell
des Anwenders wird vom Add-on weder beendet noch ersetzt.

## Welche Ereignisse übertragen werden

Zuerst muss `fullState` eintreffen. Dieser vollständige Zustand authentifiziert
die konkrete Accessibility-Sitzung und enthält unter anderem Modus, Cursor,
aktuelle Zeile, Buffer- und Fensterkennung sowie Transportfähigkeiten.

Danach sendet Neovim kleine semantische Ereignisse, beispielsweise:

- `modeChanged` für Insert, Normal, Visual, Command-line und weitere Modi;
- `characterMoved`, `wordMoved` und `lineChanged` für Navigation;
- `textChanged`, `textDeleted` und `textReplaced` für Bearbeitung;
- `selectionChanged` für visuelle Auswahl;
- `menuOpened`, `menuSelectionChanged` und `menuClosed` für Completion;
- Diagnostics, Suche, Folds, Meldungen und Fehler.

Das Add-on prüft Sitzungskennung und Sequenz. Bei einer Lücke fordert es einen
neuen `fullState` an. Veraltete, doppelte oder fremde Ereignisse werden nicht
gesprochen. In Gegenrichtung sind nur `requestFullState` und validiertes
Braille-Cursorrouting vorgesehen. Empfangener Text wird nie als beliebiger
Lua- oder Ex-Befehl ausgeführt.

## Fenster, Tabs, Panes und tmux

Praktisch bestätigt sind:

- zwei lokale Windows-Neovim-Instanzen in zwei Tabs;
- ein lokaler und ein SSH-Neovim-Tab im selben Fenster;
- ein weiteres Windows-Terminal-Fenster mit anderem SSH-Konto;
- SSH mit tmux und mehreren Neovim-Instanzen;
- parallele lokale und entfernte Accessibility-Verbindungen.

Das Add-on bildet aus UIA-Runtime-ID, Prozess und Fensterhandle eine flüchtige
Terminalidentität. So bleiben Tabs oder unterstützte Panes auch im gleichen
Windows-Terminal-Prozess getrennt.

Nach erfolgreicher Verbindung kann das Add-on fragen, ob die Zuordnung für die
aktuelle Laufzeit gemerkt werden soll. Sie bleibt nur im Arbeitsspeicher. Beim
Tabwechsel wird die passende laufende Instanz ausgewählt und ein aktueller
`fullState` angefordert. Die Zuordnung endet mit NVDA oder Windows Terminal.

tmux liegt innerhalb der sichtbaren Arbeitssitzung und ändert den
Accessibility-Transport nicht. Entscheidend ist, dass F12 das beabsichtigte
Neovim erreicht. Empfohlen wird `escape-time 220`.

## Manuelle Verbindung als Ausweichweg

Der frei belegbare manuelle Verbindungsbefehl öffnet eine Zielauswahl. Zur Wahl
stehen der lokale Rechner und gespeicherte SSH-Verbindungen. Bei Bedarf werden
mehrere Sitzungen mit Name, Arbeitsverzeichnis, Startreihenfolge und
Verbindungsstatus angeboten.

Der Dialog ist besonders nützlich bei Passwortprofilen, mehreren ähnlichen
Sitzungen, einer verpassten F12-Markierung oder beim ausdrücklichen Ersetzen
einer Tabzuordnung. Auch dieser Weg liest vor der Aktion den aktuellen Fokus
neu ein. Interne IDs und Ports müssen nicht eingegeben werden.

## Deaktivierung und sicheres Zurückfallen

Beim Ausschalten beendet das Add-on seine lokalen Clients und unsichtbaren
SSH-Prozesse. Sichtbare SSH- und tmux-Sitzungen bleiben bestehen.

Native Terminalausgabe wird nur unterdrückt, wenn Unterstützung aktiviert, der
fokussierte Tab ausdrücklich gebunden und die Sitzung durch einen gültigen
`fullState` authentifiziert ist. Bei Deaktivierung, falschem Tab, Neovim-Ende,
Transportfehler oder direkter Eingabe in einem Terminalbuffer fällt NVDA auf
normale Windows-Terminal-Ausgabe zurück. Ein Fehler darf kein dauerhaft
stummes Terminal hinterlassen.

## Datenschutz und Sicherheitsgrenzen

- Fenstertitel, Terminaltext und Shellprompt werden nicht zur Zuordnung gelesen.
- Registryeinträge enthalten technische Metadaten, keinen Buffertext und keine
  Passwörter.
- Lokale RPC-Ports sind nur über `127.0.0.1` im Windows-Benutzerkontext erreichbar.
- Linux öffnet keinen zusätzlichen Netzwerklistener.
- SSH-Passwörter werden nicht gespeichert.
- Diagnoseberichte redigieren Editorinhalt und vertrauliche Felder.

## Praktisch bestätigter Stand und bekannte Grenze

Mit dem Stand vor Beta-Build 0.89.1 wurden unter Windows 11 25H2 und NVDA 2026.1.1 lokales
Windows-Neovim, Neovim über SSH auf Rocky Linux 10.2, parallele lokale und
entfernte Instanzen, mehrere Tabs, mehrere Windows-Terminal-Fenster, tmux,
F12, manuelle Auswahl und Sitzungswechsel praktisch bestätigt.

Bestätigte Linux-Basis ist Rocky Linux 10.2 mit Neovim 0.10.1. Eine ältere, auf
Rocky Linux 9 vorhandene Neovim-Version funktionierte mit dem aktuellen Stand
nicht, obwohl ein sehr früher Entwicklungsstand dort einmal lief. Ursache und
genaue Versionsgrenze sind noch nicht untersucht und haben derzeit keine
Priorität. Neovim 0.10.1 bleibt daher die vorläufige Mindestversion.

## Wenn die Zuordnung nicht gelingt

1. Komponenten aktualisieren und Neovim neu starten.
2. Den gewünschten Windows-Terminal-Tab fokussieren.
3. Add-on aktivieren und die Bereitschaftsmeldung abwarten.
4. F12 erneut drücken; Neovim selbst soll nichts sichtbar melden.
5. Alternativ den manuellen Verbindungsbefehl verwenden.
6. Falls nötig den redigierten Diagnosebericht kopieren.

Weitere Hilfe: [Fehlerdiagnose](troubleshooting.md),
[Einstellungen](settings.md) und [SSH und tmux](ssh-and-tmux.md).
