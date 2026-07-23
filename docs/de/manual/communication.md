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
stellt Dateien bereit, verbindet aber noch kein Terminal-Control mit Neovim.
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

## Begriff: dateibasierte Sitzungsregistrierung

Die in dieser Dokumentation erwähnte „Registry“ ist **nicht die Windows-
Registry**. Neovim Access Link liest und schreibt weder `HKCU` noch `HKLM` und
legt keine Windows-Registry-Schlüssel an. Gemeint ist ausschließlich eine vom
Neovim-Plugin verwaltete, dateibasierte Sitzungsregistrierung aus kurzlebigen
JSON-Dateien:

- unter Windows normalerweise
  `%LOCALAPPDATA%\nvim-nvda\sessions\<PID>-<Nonce>.json`;
- unter Linux unter
  `$XDG_RUNTIME_DIR/nvim-nvda/sessions/<PID>-<Nonce>.json`, mit einem privaten
  benutzerbezogenen Verzeichnis unter `/tmp` als Fallback.

Die Dateien enthalten nur die für Discovery und F12-Zuordnung erforderlichen
Sitzungs- und Endpunktmetadaten. Sie werden beim normalen Neovim-Ende entfernt;
eindeutig veraltete eigene Dateien können begrenzt bereinigt werden.
Sie speichern keine Windows-Terminal-Fenster-, Tab- oder Pane-Zuordnung. Diese
Bindung hält das NVDA-Add-on nur für seine aktuelle Laufzeit im Arbeitsspeicher.

## Was beim Aktivieren passiert

Der nur bei fokussiertem Windows Terminal auflösbare, frei belegbare
NVDA-Aktivierungsbefehl schaltet den gemeinsamen Dienst ein oder wieder aus.
Beim ersten Einschalten geschieht Folgendes:

1. Das Windows-Terminal-AppModule übernimmt unmittelbar das aktuell fokussierte
   Terminalobjekt. Das gilt auch, wenn Windows Terminal schon vorher fokussiert
   war und deshalb kein neues NVDA-Fokusereignis eintrifft.
2. Das Add-on liest im Hintergrund die lokalen JSON-Sitzungsdateien und die
   Sitzungslisten aller automatisch erreichbaren gespeicherten SSH-Ziele.
3. Es merkt sich die aktuelle Zuordnungsnummer jeder Sitzung als Ausgangswert.
4. NVDA meldet, dass die Erfassung bereit ist und F12 gedrückt werden kann.

Solange der Dienst eingeschaltet ist, autorisiert jeder physische F12-Druck
genau einen Zuordnungsversuch für die vollständige UIA-Identität des aktuell
fokussierten Controls. Der Aktivierungsbefehl schaltet den gemeinsamen Dienst
aus jedem fokussierten Windows-Terminal-Control ein oder aus. Weitere Fenster,
Tabs oder Panes werden deshalb direkt mit F12 zugeordnet; bestehende
Verbindungen bleiben erhalten.

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
   in seine Sitzungsdatei. Es zeigt keine Statusmeldung an.
6. Nach einer kurzen Verzögerung liest das Add-on die zuvor erfassten lokalen
   und entfernten Sitzungen erneut.
7. Nur eine gegenüber dem Ausgangswert erhöhte `claimSequence` gilt als
   ausdrückliche Auswahl dieses Tastendrucks.
8. Bei genau einem Treffer baut das Add-on die passende Verbindung auf und
   bindet sie an das fokussierte `TermControl`, also je nach Layout an einen
   Tabinhalt oder ein Pane. Bei mehreren Treffern erscheint eine zugängliche
   Auswahl. Ohne Treffer wird nicht geraten.

Die Freigabe gilt nur für diesen einen Tastendruck und genau dieses Control.
Der anschließend entstehende dateibasierte Sitzungs-Claim wird nur in seinem kurzen
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

## Text erkunden, ohne den Neovim-Cursor zu bewegen

In einem verbundenen und bestätigten Neovim-Control kann Text mit fest
belegten NVDA-Kombinationen gelesen werden. Die NVDA-Taste bleibt dabei
gedrückt:

| Taste | Virtuelle Lesebewegung |
|---|---|
| `NVDA+h` / `NVDA+l` | vorheriges / nächstes Zeichen |
| `NVDA+k` / `NVDA+j` | vorherige / nächste Zeile |
| `Umschalt+NVDA+h` / `Umschalt+NVDA+l` | vorheriges / nächstes Wort |

Zu Beginn wird die flüchtige Leseposition aus dem echten Cursor gebildet; die
angeforderte Bewegung verändert danach nur diese virtuelle Position. Buffer,
Modus, Fensteransicht und echter Cursor bleiben unverändert. Jede Bewegung
spricht das Zeichen, Wort oder die Zeile an der virtuellen Position.

Beim Loslassen der NVDA-Taste kehrt die Ausgabe zum unveränderten echten Cursor
zurück. Nach Zeichenexploration wird dessen Zeichen gesprochen. Nach Wort- oder
Zeilenexploration gelten die jeweils unter `Einstellungen → Neovim Access Link
→ Navigation → Abschluss der Exploration` gewählten Details. Wortausgabe kann
das Cursorzeichen ergänzen; Zeilenausgabe kann das aktuelle Wort, das
Cursorzeichen, beides in dieser Reihenfolge oder keines von beiden ergänzen.
Die Grundausgabe des Wortes beziehungsweise der Zeile bleibt immer erhalten.
Diese beiden Werte sind von den entsprechenden Einstellungen für normale
Navigation unabhängig.

Bei der zeichenweisen Exploration kennzeichnet ein kurzer Doppelton die
Rückkehr zur echten Cursorposition. Derselbe Ton kennzeichnet bei der Wort-
oder Zeilenexploration die Rückkehr zum ursprünglichen Wort beziehungsweise
zur ursprünglichen Zeile. Er folgt der konfigurierten Klangausgabe für
Zeilengrenzen.

Die Belegung gilt in allen vom Add-on unterstützten Neovim-Modi, darunter
Normal, Insert, Replace, Visual, Operator-Pending, Kommandozeile,
Terminal-Normal und direkte Terminaleingabe. Sie gilt aber nur für die exakt
fokussierte, authentifizierte Neovim-Pane. In einer Shell, einem ungebundenen
Pane, einem anderen Tab oder einer anderen Anwendung behalten dieselben
Kombinationen ihr normales NVDA-Verhalten. Nach Installation einer Version mit
dieser Funktion müssen die Neovim-Komponenten aktualisiert und laufende
Neovim-Instanzen neu gestartet werden.

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
in eine kurzlebige JSON-Sitzungsdatei unter
`%LOCALAPPDATA%\nvim-nvda\sessions`. Die Windows-Registry ist daran nicht
beteiligt.

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

- `modeChanged` für Einfüge-, Normal-, visuelle, Befehlszeilen- und weitere Modi;
- `characterMoved`, `wordMoved` und `lineChanged` für Navigation;
- `textChanged`, `textDeleted` und `textReplaced` für Bearbeitung;
- `selectionChanged` für visuelle Auswahl;
- `menuOpened`, `menuSelectionChanged` und `menuClosed` für Completion;
- Diagnostics, Suche, Folds, Meldungen und Fehler.

Das Add-on prüft Sitzungskennung und Sequenz. Bei einer Lücke fordert es einen
neuen `fullState` an. Veraltete, doppelte oder fremde Ereignisse werden nicht
gesprochen. In Gegenrichtung ist nur eine feste Liste typisierter Aktionen
erlaubt: Zustand oder Fokuskontext anfordern, einen validierten Braillecursor
routen, ausdrücklich angeforderten Zwischenablagentext übertragen und die
direkte Eingabe eines gebundenen Neovim-Terminals verlassen. Jede Aktion wird
zusätzlich gegen Sitzung, Fokus und passenden Editorzustand geprüft.
Empfangener Text wird nie als beliebiger Lua- oder Ex-Befehl ausgeführt.

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
einer Control-Zuordnung. Auch dieser Weg liest vor der Aktion den aktuellen
Fokus neu ein. Interne IDs und Ports müssen nicht eingegeben werden.

## Deaktivierung und sicheres Zurückfallen

Beim Ausschalten beendet das Add-on seine lokalen Clients und unsichtbaren
SSH-Prozesse. Sichtbare SSH- und tmux-Sitzungen bleiben bestehen.

Native Terminalausgabe wird nur unterdrückt, wenn Unterstützung aktiviert, das
fokussierte Control ausdrücklich gebunden und die Sitzung durch einen gültigen
`fullState` authentifiziert ist. Bei Deaktivierung, einem anderen Control,
Neovim-Ende, Transportfehler oder direkter Eingabe in einem Terminalbuffer
fällt NVDA auf normale Windows-Terminal-Ausgabe zurück. Ein Fehler darf kein
dauerhaft stummes Terminal hinterlassen.

## Datenschutz und Sicherheitsgrenzen

- Fenstertitel, Terminaltext und Shellprompt werden nicht zur Zuordnung gelesen.
- Registryeinträge enthalten technische Metadaten, keinen Buffertext und keine
  Passwörter.
- Lokale RPC-Ports sind nur über `127.0.0.1` im Windows-Benutzerkontext erreichbar.
- Linux öffnet keinen zusätzlichen Netzwerklistener.
- SSH-Passwörter werden nicht gespeichert.
- Diagnoseberichte redigieren Editorinhalt und vertrauliche Felder.

## Praktisch bestätigter Stand und bekannte Grenzen

Die Referenzpfade umfassen lokales Windows-Neovim, Neovim über SSH auf Rocky
Linux 10.2, parallele lokale und entfernte Instanzen, mehrere Tabs, Panes und
Windows-Terminal-Fenster, tmux, F12, manuelle Auswahl und Sitzungswechsel.
Diese Prüfungen sind Stichproben in dokumentierten Umgebungen und keine
erschöpfende Abnahme aller Kombinationen. Der aktuelle Nachweis und bekannte
Grenzen werden zentral in der Entwicklerdokumentation unter `current-status.md`
und `compatibility.md` gepflegt.

Bestätigte Linux-Basis ist Rocky Linux 10.2 mit Neovim 0.10.1. Eine ältere, auf
Rocky Linux 9 vorhandene Neovim-Version funktionierte mit einem aktuellen
Stand nicht. Ursache und genaue Versionsgrenze sind noch nicht untersucht;
Neovim 0.10.1 bleibt daher die vorläufige Mindestversion.

## Wenn die Zuordnung nicht gelingt

1. Komponenten aktualisieren und Neovim neu starten.
2. Den gewünschten Tab oder bei geteiltem Layout das gewünschte Pane
   fokussieren.
3. Add-on aktivieren und die Bereitschaftsmeldung abwarten.
4. F12 erneut drücken; Neovim selbst soll nichts sichtbar melden.
5. Alternativ den manuellen Verbindungsbefehl verwenden.
6. Falls nötig den redigierten Diagnosebericht kopieren.

Weitere Hilfe: [Fehlerdiagnose](troubleshooting.md),
[Einstellungen](settings.md) und [SSH und tmux](ssh-and-tmux.md).
