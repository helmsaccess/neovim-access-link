# Eingebettetes Terminal und Dateimanager

## Eingebettetes Terminal verwenden

`:terminal` öffnet einen Neovim-Terminalbuffer. Während direkter Eingabe gibt
Access Link NVDAs native Windows-Terminal-Ausgabe frei. Shells und darin
laufende TUI-Anwendungen bleiben dadurch über NVDAs normale
Terminalunterstützung bedienbar. Die Access-Link-Sitzung und ihre Zuordnung
bleiben bestehen.

Der Beginn direkter Terminaleingabe verwendet den Insert-Modusklang. Verlassen
Sie die direkte Eingabe mit `Ctrl+\`, danach `Ctrl+n`. Neovim wechselt in den
Terminal-Normalmodus, Access Link übernimmt wieder strukturierte Navigation
und verwendet den Normalmodusklang.

Wenn die Tastenfolge auf Ihrem Layout schwer erreichbar ist, weisen Sie unter
`NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link` dem Befehl
`Direkte Eingabe im aktiven Neovim-Terminal verlassen` eine NVDA-Geste zu.
Dieser NVDA-Befehl wirkt nur im verbundenen und fokussierten Terminalbuffer.

`i` ohne NVDA-Taste ist anschließend wieder ein Neovim-Befehl und beginnt die
direkte Terminaleingabe. Access Link beendet weder Shell noch Terminalbuffer.

Ein laufender Terminaljob verhindert normales `:bd`. Neovim meldet `E89`.
`:bd!` beendet den Job ausdrücklich. Öffnen Sie einen Terminalbuffer mit
`:new | terminal`, wenn der vorherige Editorbuffer sichtbar erhalten bleiben
soll.

## Neovim-Befehlszeile und Meldungen

`:` öffnet Neovims Befehlszeile. Access Link meldet den Befehlszeilenmodus,
Eingabe, Fehler und die strukturierte Ergebnismeldung. Nach der Ausführung gilt
die Einstellung unter `Allgemein → Sitzungsfokus`:

- `Keine Ansage` belässt es bei der Meldung.
- `Aktuelle Zeile` ergänzt die Cursorzeile.
- `Aktueller Kontext, Modus und Verbindungsname` ergänzt den Zielkontext.

Erzeugt ein Befehl nur eine Meldung und kehrt in denselben Modus zurück, spielt
Access Link trotzdem den passenden Rückkehrklang. Eine später eintreffende
asynchrone Meldung wird nicht diesem Befehl zugerechnet.

## Dateimanager und Prüfstand

Access Link führt Dateioperationen nicht selbst aus. Der jeweilige
Dateimanager öffnet, erstellt, benennt um, kopiert, verschiebt oder löscht
Dateien. Access Link macht den ausgewählten Eintrag, Typ, Zustand und
Bestätigungsdialog zugänglich.

| Dateimanager | Access-Link-Stand |
| --- | --- |
| Oil | praktisch unter Windows mit NVDA und Neovim 0.12 bestätigt |
| netrw | Adapter automatisiert mit Neovim 0.10.1 und 0.12.3 geprüft |
| nvim-tree | Adapter gegen öffentliche Plugin-API automatisiert geprüft |
| Neo-tree | Adapter gegen öffentliche Plugin-API automatisiert geprüft |
| mini.files | Adapter gegen öffentliche Plugin-API automatisiert geprüft |

Nur Oil besitzt damit eine praktische Freigabe aus der derzeitigen
Windows-/NVDA-Prüfung. Die anderen Adapter bleiben nutzbar, ihre vollständigen
Arbeitsabläufe sind nicht praktisch bestätigt.

## Einträge navigieren

Bei einem erkannten Dateimanagereintrag gibt Access Link den vollständigen
Namen und den semantischen Typ aus. Dazu gehören Datei, Verzeichnis,
symbolischer Link, Socket, Pipe und Gerätedatei. Verfügbare Zustände wie
Markierung oder geöffneter Baumknoten werden ebenfalls gesprochen und auf
Braille angezeigt.

Dateinamen mit Leerzeichen, Unicode und Satzzeichen bleiben vollständig. Bei
einem Dateimanager zeigt die dauerhafte Braillezeile Name, Typ und Zustand
statt dekorativer Icons und Zusatzspalten. Routing innerhalb des echten Namens
setzt den Neovim-Cursor; synthetische Typ- und Statusangaben besitzen keine
Routingposition.

Beim Öffnen einer Datei gilt `Allgemein → Sitzungsfokus`. Access Link wiederholt
das folgende automatische Cursorereignis nicht als einzelnes Zeichen.

## Oil verwenden

Das Kapitel [Optionale Beispielkonfiguration mit Lazy und
Oil](example-configuration.md) enthält eine direkt nutzbare Einrichtung.

Oil stellt ein Verzeichnis als bearbeitbaren Buffer dar. Ein Name ändert sich
zunächst nur im Buffer. Beispiel für Umbenennen:

1. Navigieren Sie zum Eintrag.
2. Drücken Sie `0`, dann `c$`.
3. Schreiben Sie den neuen Namen und drücken Sie `Esc`.
4. Prüfen Sie den neuen Entwurfsnamen über Sprache oder Braille.
5. Speichern Sie mit `:w`.
6. Bestätigen oder verwerfen Sie Oils Rückfrage.

Access Link zeigt den bearbeiteten Namen bereits vor `:w`, meldet aber erst
nach Oils Ergebnis eine ausgeführte Dateioperation.

Setzen Sie in Oil `skip_confirm_for_simple_edits = false`. Oil fragt dann auch
vor einfachem Umbenennen oder Duplizieren. Löschungen und komplexe Aktionen
besitzen unabhängig davon eine Bestätigung.

Access Link nennt bei Oils Bestätigung Aktion, Anzahl und Y/N, aber keine
vollständigen Pfade. `y` und `n` ohne NVDA-Taste sind Eingaben an Oil. Access
Link beantwortet die Rückfrage nicht automatisch. Nach `y` meldet Oils Ergebnis
Erfolg oder Fehler; `n` wird als Abbruch ausgegeben.

## Prompts anderer Dateimanager

Für strukturierte Auswahl- und Eingabeprompts verwenden Sie bei nvim-tree
`select_prompts = true` und bei Neo-tree `use_popups_for_input = false`. Diese
Optionen führen die Prompts über Neovims zentrale Auswahl- beziehungsweise
Eingabe-API. Access Link ändert die Pluginoptionen nicht.

mini.files verwendet für gemeinsame Änderungen eine zugängliche
Ja-/Nein-/Abbruchabfrage. Wenn ein Dateimanager kein semantisches Ergebnis
liefert, bleibt seine eigene Meldung maßgeblich; Access Link meldet keinen
erfundenen Erfolg.

Andere Dateimanager erhalten normale Neovim-Navigation. Semantischer Dateityp,
Markierung und Baumzustand sind ohne eigenen Adapter nicht zugesagt.
