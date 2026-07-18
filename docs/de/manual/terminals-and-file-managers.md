# Terminal und Dateimanager

## Eingebettetes Terminal

In einem mit `:terminal` geöffneten Buffer beendet das Add-on automatisch nur
die Unterdrückung der normalen Windows-Terminal-Ausgabe. NVDA liest dadurch die
eingebettete Shell oder eine darin laufende TUI über seine bewährte native
Terminalunterstützung. SSH-Verbindung, Neovim-Sitzung und Aktivierung bleiben
erhalten. Sobald ein normaler Neovim-Buffer wieder aktiv ist, übernimmt die
strukturierte Ausgabe automatisch erneut.

Nach `Ctrl+\`, `Ctrl+N` endet der Passthrough im Terminal-Normalmodus. Weil
diese Folge auf manchen Tastaturlayouts unzuverlässig erreichbar ist, kann
unter `NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link` zusätzlich
der Befehl „Direkte Eingabe im aktiven Neovim-Terminal verlassen“ frei belegt
werden. Er hat absichtlich keine Standardgeste und wirkt ausschließlich auf
die authentifizierte, an das fokussierte Windows-Terminal-Control gebundene
Neovim-Terminalinstanz. Dort
übernimmt wieder die strukturierte Neovim-Ausgabe, damit Navigation,
Visual-Auswahl und Kopierbefehle zugänglich sind. Mit `i` beginnt erneut die
direkte Terminalsteuerung und damit der native Passthrough.

Der Beginn der direkten Terminalsteuerung verwendet denselben Fokusklang wie
der Insert-Modus. Der Wechsel von Terminal- in Terminal-Normalmodus verwendet
den Normalmodusklang. Beide Klänge folgen der Einstellung „Insert and normal
mode changes“. Die Freigabe beziehungsweise erneute Aktivierung der nativen
Terminalausgabe erfolgt vor dieser optionalen Rückmeldung.

Der frei belegbare Ausstiegsbefehl beendet nur die direkte Terminaleingabe. Er
beendet weder den Shellprozess noch den Terminalbuffer. `:bd` verweigert
Neovim bei einem laufenden Terminaljob mit `E89`; das Add-on nennt den Grund
vor Neovims anschließendem Enter-Hinweis. Erst `:bd!` beendet den Job
absichtlich und darf deshalb nicht automatisch ausgeführt werden. `:bp` und
`:bn` wechseln nur zwischen bereits vorhandenen gelisteten Buffern. Hat
`:terminal` den einzigen leeren Buffer ersetzt, meldet das Add-on, dass kein
anderer gelisteter Buffer vorhanden ist. Wer sicher zurückwechseln möchte,
öffnet das Terminal beispielsweise mit `:new | terminal` in einem eigenen
Buffer.

## Neovim-Kommandozeile und Meldungen

Beim Öffnen der Neovim-Kommandozeile mit `:` wird „command-line mode“
gesprochen und ein kurzer mittlerer Ton abgespielt. Der Rückweg aus der
Kommandozeile im Terminalkontext verwendet den Normalmodusklang. Bei `:bp`,
`:bn` und ihren ausgeschriebenen Varianten werden kurzlebige gesprochene
Rückkehrmodi nicht zusätzlich vor die unter „Session focus“ gewählte
Zielausgabe gestellt. Der Klang bleibt erhalten; „Keine Ansage“ bleibt still.
Eingabe,
Fehler und die nach Ausführung angezeigten gewöhnlichen
Neovim-Meldungen werden strukturiert übernommen; Meldungen erscheinen außerdem
kurz auf Braille. Erzeugt ein Ex-Befehl nur eine Meldung und kehrt in denselben
Editorzustand zurück, spielt davor der passende Rückkehrklang. „Keine Ansage“
belässt es bei der Meldung, „Aktuelle Zeile“ hängt die vollständige Zeile an,
und die Kontextwahl hängt Datei- oder Spezialkontext, Modus und Verbindung an.
Eine spätere asynchrone Meldung wird nicht fälschlich diesem Befehl zugeordnet.
Die native Ausgabe einer eingebetteten Shell wird davon nicht
abgeleitet oder ausgewertet. Wenn der Terminalprozess endet, meldet das Add-on
Neovims strukturiertes `TermClose` einschließlich Exit-Status. Shellausgabe
während des Prozesses bleibt weiterhin ausschließlich native Terminalausgabe.

`:terminal` erzeugt einen neuen Terminalbuffer und verwendet dafür die unter
„Session focus“ gewählte Einstiegsansage. Bei Zeilenausgabe wartet das Add-on
ereignisgetrieben auf die erste echte Terminalzeile. Das folgende automatische
Cursorereignis wird nicht als einzelnes Anfangszeichen wiederholt. Mit `i`
beginnt die direkte Terminaleingabe; dabei wird die vollständige aktuelle
Cursorzeile gesprochen und anschließend native Terminalausgabe fail-open
freigegeben.

## Unterstützte Dateimanager

- netrw: Dateisystemmetadaten und netrw-Markierungsstatus
- Oil: `get_cursor_entry()` und `get_current_dir()`
- nvim-tree: `api.tree.get_node_under_cursor()`
- Neo-tree: öffentlicher Quellenzustand und aktueller Baumknoten
- mini.files: `get_fs_entry()` und `get_explorer_state()`

Oil ist bislang der einzige dieser Dateimanager, der unter Windows/NVDA mit
Neovim 0.12 praktisch getestet wurde. Er funktioniert dort als solide
Grundlage. Die übrigen Adapter sind automatisiert beziehungsweise isoliert
geprüft, aber noch nicht praktisch unter Windows abgenommen; diese Tests folgen
schrittweise.

Die Grundabläufe sind für Quellcodeprojekte und Schreibprojekte gleich:
Verzeichnisse navigieren und öffnen, Dateien öffnen, anlegen, umbenennen,
duplizieren beziehungsweise kopieren, verschieben, markieren und als Batch
bearbeiten sowie löschen, abbrechen oder – soweit angeboten – wiederherstellen.
Dateien mit Leerzeichen, Unicode und Satzzeichen werden als vollständige Namen
behandelt. Beim Öffnen einer Datei gilt die Einstellung „Session focus“; die
folgende automatische Cursorbewegung wiederholt kein einzelnes Zeichen.
Access Link führt keine dieser Dateioperationen selbst aus und bestätigt keine
Rückfrage automatisch. Wo ein Plugin kein öffentliches Abschlussereignis
liefert, bleibt dessen eigene Meldung maßgeblich und Access Link erfindet
keinen Erfolg.

Beim Navigieren werden Name und semantischer Typ ausgegeben. Verzeichnisse,
symbolische Links, Sockets, Pipes und Gerätedateien sind damit nicht von Farbe
oder Symbolschrift abhängig. Wenn die API es bereitstellt, werden außerdem
Markierung sowie geöffneter oder geschlossener Baumzustand angesagt und als
Braillemeldung ausgegeben. Änderungen ohne Cursorbewegung werden bei den
unterstützten öffentlichen Pluginereignissen ebenfalls erkannt: markiert,
Markierung aufgehoben, kopiert, ausgeschnitten, Dateimanager-Clipboard geleert
sowie Baumknoten geöffnet oder geschlossen. Mehrere reine Renderereignisse
werden zusammengefasst; der Zustand wird nicht regelmäßig abgefragt.
In Oil folgt der semantische Name schon beim Bearbeiten dem sichtbaren
Entwurfsnamen. Nach `0`, `c$`, neuem Namen und Escape müssen Sprache und
Braille daher den neuen Namen zeigen, obwohl die Datei erst mit `:w`
umbenannt wird. `0`, `$`, `gg` und `G` behalten zugleich ihre Zeilen- und
Dateigrenzklänge. Vor `:w` meldet Access Link ausdrücklich keinen
Umbenennungserfolg.
Bestätigte Aktionen werden kompakt als erstellt, hinzugefügt, umbenannt,
kopiert, verschoben, gelöscht, geändert oder wiederhergestellt ausgegeben.
Mehrere unmittelbar zusammengehörige Aktionen ergeben eine Sammelmeldung.
Dabei überträgt Access Link höchstens den Basename, nie den vollständigen
Quell- oder Zielpfad. Oil kann zusätzlich einen Abschlussfehler oder einzelne
Abbrüche melden. Bei den anderen Plugins bleiben Fehler- und Abbruchmeldungen
des Plugins selbst maßgeblich, solange deren öffentliche API kein eigenes
Ergebnisereignis bereitstellt; Access Link rät dann keinen Erfolg oder Fehler.
Sehr lange Namen und Pfade werden für die Übertragung bytebegrenzt, jedoch nie
mitten in einem Unicode-Zeichen abgeschnitten. Liefert ein fremder Adapter
ungültigen UTF-8-Text, wird ein optionales Feld ignoriert; bei einem ungültigen
erforderlichen Namen entfällt nur der semantische Eintrag. Die normale
Neovim-Navigation bleibt in beiden Fällen verfügbar.
netrw unterstützt seine schmale, lange, breite und Baumdarstellung. Header
werden als Dateimanagerkontext ohne erfundenen Eintrag behandelt; Leerzeichen,
Tabs und Unicode im Namen bleiben erhalten. Wenn ein optionaler Adapter
wiederholt fehlschlägt oder Neovim merklich aufhält, wird er für den
betroffenen Buffer kurz ausgesetzt und die normale Navigation bleibt aktiv.
`:checkhealth nvim_nvda` zeigt dazu Zähler, aber keine Pfade, Dateinamen oder
internen Fehlertexte.
Ist vorübergehend kein Eintrag ausgewählt, nennt die Kontextansage höchstens
den letzten Namen der fokussierten Verzeichnisebene. Vollständige lokale,
entfernte oder virtuelle Pfade werden dabei nicht vorgelesen.

Die dauerhafte Braillezeile zeigt bei einem Dateimanagereintrag Name, Typ und
Zustand statt Icons, Einrückungsdekoration und Zusatzspalten der sichtbaren
Pluginzeile. Routing ist nur innerhalb des Namens möglich, wenn dieser genau
einmal in der echten Bufferzeile vorkommt. Typ- und Statusangaben sind
synthetische Orientierung und besitzen absichtlich keine Routingfunktion.

Für möglichst gut strukturierte Eingabe- und Auswahlprompts empfiehlt sich bei
nvim-tree `select_prompts = true` und bei Neo-tree
`use_popups_for_input = false`. Damit verwenden diese Plugins Neovims zentrale
`vim.ui.select`- beziehungsweise `vim.ui.input`-API, die Access Link mit
Annahme und Abbruch erfasst. Access Link ändert diese Pluginoptionen nicht
selbst. Lua-basierte `confirm()`-Abfragen werden ebenfalls mit der gewählten
Option ausgegeben. mini.files verwendet für die gemeinsame Synchronisierung
von Umbenennen, Duplizieren und Löschen eine solche Ja-/Nein-/Abbruchabfrage.

Bei Oil sollte `skip_confirm_for_simple_edits = false` gesetzt bleiben. Dann
fragt Oil auch vor einfachem Umbenennen oder Duplizieren; Löschungen und
komplexe Aktionen fragt Oil unabhängig davon ab. Sein eigener
Bestätigungs-Float wird als bewusst enger Fallback erkannt: Access Link nennt
„rename or move“, „copy or duplicate“, Löschen beziehungsweise
Papierkorbaktionen, Anzahl sowie Y/N und spricht weder die gerenderte Rohzeile
noch vollständige Pfade. Direkt getipptes `n` wird als Abbruch ausgegeben;
nach `y` bleibt Oils öffentliches Abschlussereignis für Erfolg oder Fehler
maßgeblich. Access Link beantwortet oder wiederholt die Aktion niemals selbst.
Dieser Fallback greift ausschließlich für Oils `oil_preview` in einem echten
Floating Window; unbekannte oder veränderte Darstellungen bleiben fail-open
bei der normalen strukturierten Buffer-/Fensterausgabe. Weitere
pluginspezifische Popups müssen separat geprüft werden.

## Weitere Dateimanager

Andere Dateimanager sind nicht automatisch zugänglich, nur weil sie in einem
Floating Window oder mit ähnlichen Symbolen erscheinen. Sie benötigen einen
Adapter, der den aktuellen Eintrag über eine stabile Plugin-API bereitstellt.
Fehlt ein solcher Adapter, bleibt die normale Neovim-Navigation erhalten, aber
semantischer Typ, Markierung und Baumzustand können unvollständig sein.
Ein externer Adapter muss synchron und klein arbeiten und darf weder Datei-
oder Netzwerk-I/O noch Polling ausführen.
