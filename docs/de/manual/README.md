# Neovim Access Link – Handbuch

Neovim Access Link verbindet Neovim in Windows Terminal mit NVDA. Das Add-on
erhält strukturierte Informationen direkt von Neovim und gibt Modus, Cursor,
Textänderungen, Auswahl, Einrückung, Vervollständigung und Diagnosen gezielt
über Sprache, Sounds und Braille aus.

Dieses Handbuch richtet sich an erfahrene NVDA-Nutzer, die Neovim neu lernen
oder mit Access Link produktiv verwenden. Für die erste Installation und
Verbindung dient der [Quick Guide](quick-guide.md).

## Unterstützter Arbeitsbereich

Access Link unterstützt derzeit:

- lokales `nvim.exe` in Windows Terminal;
- Neovim auf Linux über SSH;
- Normal-, Insert-, Replace-, Visual-, Select-, Operator-Pending- und
  Befehlszeilenmodus;
- Neovims Terminal-Normalmodus und native Terminalausgabe bei direkter
  Terminaleingabe;
- mehrere Windows-Terminal-Fenster, Tabs und geteilte Panes;
- parallele lokale und entfernte Neovim-Sitzungen sowie normale Shell-Panes;
- tmux innerhalb einer SSH-Sitzung;
- strukturierte Sprache und Braille, Sprachexploration, Completion, LSP,
  Diagnosen und Neovims Rechtschreibvorschläge;
- Dateiverwaltung mit Oil; weitere Dateimanager besitzen automatisiert
  geprüfte Adapter.

Praktisch bestätigt ist die Referenzumgebung Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x und Neovim 0.10.1 beziehungsweise 0.12.3. Der entfernte
Pfad ist mit Rocky Linux 10.2 bestätigt. Die vollständigen Nachweise und offenen
Prüfbereiche stehen in der
[Kompatibilitätsübersicht](../development/compatibility.md).

Andere Terminalprogramme, grafische Neovim-Oberflächen, portable
Windows-Installationen und getrennte Datenverzeichnisse über `NVIM_APPNAME`
sind nicht unterstützt.

## Reifegrad

Das Add-on ist Beta. Die dokumentierten Referenzabläufe sind praktisch oder
automatisiert geprüft; die Kombinationen aus NVDA-Konfiguration,
Braillehardware, Neovim-Versionen und Plugins sind nicht vollständig
abgedeckt. Verwenden Sie für wichtige Dateien eine normale Versionsverwaltung
oder Sicherung.

## Wie Access Link arbeitet

Das NVDA-Add-on läuft unter Windows. Ein Neovim-Plugin liefert semantische
Editorzustände. Bei einer entfernten Sitzung überträgt eine kleine Bridge diese
Daten durch eine eigene SSH-Verbindung.

Eine Access-Link-Sitzung ist eine konkrete laufende Neovim-Instanz. Access Link
ordnet genau ein fokussiertes Windows-Terminal-Control genau einer solchen
Sitzung zu. Ein Control ist der Inhalt eines Tabs oder eines einzelnen Panes.
Dadurch bleiben in demselben Windows-Terminal-Fenster verbundene Neovim-Panes
und normale Shell-Panes unabhängig.

Das ist eine wesentliche Stärke des Add-ons: Ein Windows-Terminal-Tab kann in
mehrere Panes geteilt sein, und jedes Pane arbeitet wie ein eigenes Terminal.
Sie können zwischen lokalen Neovim-Sitzungen, entfernten SSH-Sitzungen und
normalen Shells wechseln. Access Link übernimmt nur die exakt verbundene und
fokussierte Neovim-Pane. Alle anderen Panes behalten NVDAs normales
Terminalverhalten.

Bei Deaktivierung, Trennung, ungültigen Daten oder einer nicht eindeutig
bestätigten Zuordnung unterdrückt Access Link keine Terminalausgabe. NVDA fällt
offen auf sein normales Terminalverhalten zurück.

## Zwei Arten von Tasteneingaben

Das Handbuch unterscheidet zwei klar getrennte Ebenen:

- **NVDA-Tastenkombinationen** enthalten die NVDA-Taste, zum Beispiel
  `NVDA+Alt+D` oder `NVDA+h`. NVDA entscheidet über diese Kombinationen. Access
  Link übernimmt sie nur im jeweils dokumentierten, verbundenen
  Neovim-Kontext. Außerhalb dieses Kontexts gelten NVDAs normale Befehle.
- **Neovim-Befehle** enthalten keine NVDA-Taste, zum Beispiel `i`, `Esc`, `w`,
  `z=` oder `:w`. Neovim führt diese Eingaben aus. Access Link ersetzt ihre
  Funktion nicht, sondern macht Ergebnis, Modus und Cursorbewegung zugänglich.

Eine Schreibweise mit Pluszeichen bezeichnet gleichzeitig gehaltene Tasten:
`NVDA+Alt+D`. Eine durch Kommas getrennte Folge bezeichnet nacheinander
gedrückte Tasten: `Leertaste`, `l`, `s`. Neovims `z=` bedeutet ebenfalls zwei
nacheinander gedrückte Tasten.

## Empfohlener Leseweg

1. [Neovim- und Windows-Terminal-Grundlagen](basics.md)
2. [Verbindung, täglicher Einstieg und Sitzungswechsel](communication.md)
3. [Sprachexplorationsmodus](speech-exploration.md)
4. [Braille-Unterstützung](braille.md)
5. [Menüs, Completion und Diagnosen](menus-and-completion.md)
6. [Eingebettetes Terminal und Dateimanager](terminals-and-file-managers.md)
7. [SSH und tmux](ssh-and-tmux.md)
8. [LSP, Completion und Linter einrichten](language-tools.md)
9. [Optionale Beispielkonfiguration mit Lazy und Oil](example-configuration.md)
10. [Befehlsreferenz](commands.md)
11. [Einstellungsreferenz](settings.md)
12. [Sounds und Earcons](sounds.md)
13. [Fehlerdiagnose](troubleshooting.md)

Die allgemeine Neovim-Bedienung lernen Sie mit `:Tutor`. Neovims
[offizielle Hilfe](https://neovim.io/doc/user/) enthält außerdem `nvim-intro`,
die Aufgabenanleitung und die vollständige Befehlsreferenz.
