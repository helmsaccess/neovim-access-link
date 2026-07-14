# Braille-Unterstützung

> **Wichtiger Testhinweis:** Dieser Bereich wurde noch nicht mit einer echten
> Braillezeile geprüft und enthält sehr wahrscheinlich Fehler. Die folgenden
> Abschnitte beschreiben das beabsichtigte und automatisiert geprüfte Modell,
> keine belastbar bestätigte Hardwareunterstützung. Praktische Brailletests und
> Korrekturen sind ein wichtiges priorisiertes TODO.

Neovim Access Link zeigt die aktuelle Neovim-Zeile über NVDAs normale
Brailleverarbeitung an. Dadurch gelten weiterhin die in NVDA ausgewählte
Übersetzungstabelle, Cursorform, Wortumbruch- und Anzeigeeinstellungen.

## Angezeigte Informationen

Die Braillezeile enthält:

- den strukturierten Text der aktuellen Neovim-Zeile,
- die Cursorposition,
- den auf der aktuellen Zeile liegenden Teil einer Visual-Auswahl,
- führende und innere Einrückung,
- kurze Meldungen zu Menüs, Diagnosen und Dateimanager-Einträgen.

Editorstatuszeile, tmux-Statuszeile und andere sichtbare Terminalbestandteile
werden nicht in die strukturierte Braillezeile übernommen.

## Tabs und Einrückung

Neovim übermittelt den bufferlokalen Wert von `tabstop`. Das Add-on expandiert
Tabulatoren für die Brailledarstellung bis zum richtigen Tabstopp. Cursor und
Auswahl bleiben dadurch auch bei gemischten Tabs und Leerzeichen an der
passenden Textposition.

Die Art zusätzlicher Einrückungsmeldungen richtet sich nach NVDAs Einstellungen
für Zeileneinrückung. Sprachansage und Einrückungstöne können unabhängig von
der Brailledarstellung konfiguriert werden.

## Visual-Auswahl

Zeichen-, zeilen- und blockweise Auswahl werden aus Neovims tatsächlichem
Auswahlbereich berechnet. Bei einer mehrzeiligen Auswahl markiert die
Braillezeile jeweils nur den Abschnitt auf der aktuellen Zeile. Ob und wie
NVDA ausgewählten Text mit Punkten 7 und 8 hervorhebt, bestimmt die normale
NVDA-Braillekonfiguration.

## Cursor-Routing

Routingtasten setzen den Neovim-Cursor auf das entsprechende Zeichen der
aktuellen Zeile. Vor der Ausführung werden Sitzung, Buffer, Fenster,
Änderungsstand, Zeile und UTF-8-Zeichengrenze geprüft. Veraltete oder nicht
eindeutige Routinganforderungen werden verworfen.

Bei Tabs verweist jede durch die Expansion entstandene Brailleposition auf die
zugehörige Stelle im ursprünglichen Text. Breite Unicode-Zeichen, kombinierende
Zeichen und Emoji werden nicht als einfache Byteposition behandelt.

## Eingebettetes Terminal

Im direkten Eingabemodus eines mit `:terminal` geöffneten Buffers verwendet
NVDA wieder seine native Windows-Terminal-Unterstützung. Nach dem Wechsel in
den Terminal-Normalmodus übernimmt erneut die strukturierte Neovim-Anzeige.

## Bekannte Grenzen

Die Basisanzeige von Zeile, Einrückung, Cursor, Auswahl und Routing ist
implementiert. Noch nicht breit praktisch geprüft sind:

- verschiedene physische Braillezeilen und Displaygrößen,
- kontrahierte Brailleschriften und weitere Übersetzungstabellen,
- Brailleeingabe über unterschiedliche Braillekeyboards,
- lange horizontal gescrollte Zeilen,
- Visual-Block-Auswahl mit Tabs, breiten Zeichen und Emoji auf realer Hardware.

Vor produktiver Nutzung sollte die eigene Braillekonfiguration deshalb in
einem Testpuffer geprüft werden.
