# Terminal und Dateimanager

## Eingebettetes Terminal

In einem mit `:terminal` geöffneten Buffer beendet das Add-on automatisch nur
die Unterdrückung der normalen Windows-Terminal-Ausgabe. NVDA liest dadurch die
eingebettete Shell oder eine darin laufende TUI über seine bewährte native
Terminalunterstützung. SSH-Verbindung, Neovim-Sitzung und Aktivierung bleiben
erhalten. Sobald ein normaler Neovim-Buffer wieder aktiv ist, übernimmt die
strukturierte Ausgabe automatisch erneut.

Nach `Ctrl+\`, `Ctrl+N` endet der Passthrough im Terminal-Normalmodus. Dort
übernimmt wieder die strukturierte Neovim-Ausgabe, damit Navigation,
Visual-Auswahl und Kopierbefehle zugänglich sind. Mit `i` beginnt erneut die
direkte Terminalsteuerung und damit der native Passthrough.

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

## Weitere Dateimanager

Andere Dateimanager sind nicht automatisch zugänglich, nur weil sie in einem
Floating Window oder mit ähnlichen Symbolen erscheinen. Sie benötigen einen
Adapter, der den aktuellen Eintrag über eine stabile Plugin-API bereitstellt.
Fehlt ein solcher Adapter, bleibt die normale Neovim-Navigation erhalten, aber
semantischer Typ, Markierung und Baumzustand können unvollständig sein.
