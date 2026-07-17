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
kurz auf Braille. Die native Ausgabe einer eingebetteten Shell wird davon nicht
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

Beim Navigieren werden Name und semantischer Typ ausgegeben. Verzeichnisse,
symbolische Links, Sockets, Pipes und Gerätedateien sind damit nicht von Farbe
oder Symbolschrift abhängig. Wenn die API es bereitstellt, werden außerdem
Markierung sowie geöffneter oder geschlossener Baumzustand angesagt und als
Braillemeldung ausgegeben.
Sehr lange Namen und Pfade werden für die Übertragung bytebegrenzt, jedoch nie
mitten in einem Unicode-Zeichen abgeschnitten. Liefert ein fremder Adapter
ungültigen UTF-8-Text, wird ein optionales Feld ignoriert; bei einem ungültigen
erforderlichen Namen entfällt nur der semantische Eintrag. Die normale
Neovim-Navigation bleibt in beiden Fällen verfügbar.

## Weitere Dateimanager

Andere Dateimanager sind nicht automatisch zugänglich, nur weil sie in einem
Floating Window oder mit ähnlichen Symbolen erscheinen. Sie benötigen einen
Adapter, der den aktuellen Eintrag über eine stabile Plugin-API bereitstellt.
Fehlt ein solcher Adapter, bleibt die normale Neovim-Navigation erhalten, aber
semantischer Typ, Markierung und Baumzustand können unvollständig sein.
