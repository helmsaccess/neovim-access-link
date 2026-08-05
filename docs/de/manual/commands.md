# Befehlsreferenz

Diese Referenz trennt NVDA-Befehle von Neovim-Befehlen. Öffnen Sie für frei
belegbare NVDA-Befehle zuerst Windows Terminal und danach
`NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link`.

## NVDA-Befehle mit fester Geste

Diese Kombinationen enthalten die NVDA-Taste. Access Link übernimmt sie nur in
dem angegebenen verbundenen Neovim-Kontext. In anderen Anwendungen, Shells und
unverbundenen Panes gelten NVDAs normale Befehle.

| Geste | Kontext | Funktion |
| --- | --- | --- |
| `NVDA+Alt+D` | Windows Terminal | redigierten Diagnosebericht kopieren |
| `NVDA+h` / `NVDA+l` | verbundene Neovim-Pane | vorheriges / nächstes Zeichen erkunden |
| `Umschalt+NVDA+h` / `Umschalt+NVDA+l` | verbundene Neovim-Pane | vorheriges / nächstes Wort erkunden |
| `NVDA+k` / `NVDA+j` | verbundene Neovim-Pane | vorherige / nächste Zeile erkunden |
| `NVDA+Leertaste`, NVDA-Taste weiter halten | Position mit Signaturhilfe | Signaturen und Parameter anzeigen |
| `NVDA+Umschalt+Leertaste`, NVDA-Taste weiter halten | Position oder Zeile mit Diagnosen | Diagnosen anzeigen |
| `NVDA+j` / `NVDA+k` bei geöffneter `z=`-Liste | Rechtschreibvorschläge | nächsten / vorherigen Vorschlag anzeigen |
| `NVDA+Eingabe` bei gewähltem Vorschlag | Rechtschreibvorschläge | Vorschlag übernehmen |

Während einer gehaltenen Signaturansicht wechseln `NVDA+h` und `NVDA+l`
zwischen Parametern sowie `NVDA+k` und `NVDA+j` zwischen Signaturen. Während
einer gehaltenen Diagnoseansicht wechseln `NVDA+k` und `NVDA+j` zwischen
Diagnosen. Das Loslassen der NVDA-Taste beendet die vorübergehende Ansicht.

## Frei belegbare NVDA-Befehle

Diese Befehle besitzen keine Standardgeste:

| UI-Name | Funktion |
| --- | --- |
| `Neovim-Barrierefreiheit ein- oder ausschalten und konfigurierte Verbindungen erkennen` | Dienst aktivieren oder deaktivieren |
| `Braillezeilen-Navigation zwischen Braille-Cursormodus und Braille-Explorationsmodus umschalten` | Braillemodus der aktuellen Sitzung wechseln |
| `Dokumentation für den ausgewählten Neovim-Completion-Eintrag oder LSP-Hover lesen` | verfügbare Completion- oder Hover-Dokumentation ausgeben |
| `Aktive visuelle Neovim-Auswahl in die Windows-Zwischenablage übertragen` | aktuelle Visual-Auswahl kopieren |
| `Zuletzt in Neovim kopierten Text in die Windows-Zwischenablage übertragen` | Neovims Register 0 kopieren |
| `Text aus der Windows-Zwischenablage in den aktiven Neovim-Puffer einfügen` | Text an der Neovim-Position einfügen |
| `Text aus der Windows-Zwischenablage im unbenannten Neovim-Register speichern` | Text für Neovims `p` bereitstellen |
| `Direkte Eingabe im aktiven Neovim-Terminal verlassen` | aus direkter Terminaleingabe in Terminal-Normalmodus wechseln |
| `Einen Server auswählen und dieses Terminal mit einer neuen Neovim-Sitzung verbinden` | zugänglichen Sitzungsdialog öffnen |
| `Ausgewählte Neovim-Verbindungsinstanz trennen` | Access-Link-Verbindung beenden |
| `Temporäre Neovim-Verbindung für das fokussierte Terminal vergessen` | gemerkte Tab-Zuordnung entfernen |

Frei belegbare Befehle werden vor jeder Ausführung erneut gegen fokussiertes
Windows Terminal, das konkrete Control und die aktive Neovim-Zuordnung geprüft.

## F12-Zuordnung

F12 ist kein NVDA-Befehl und keine Aktivierungsgeste. Windows Terminal und
Neovim erhalten den Tastendruck normal. Das Neovim-Plugin markiert die aktuelle
Sitzung; der eingeschaltete Access-Link-Dienst verwendet diesen frischen
Treffer danach für die Zuordnung.

## Häufig verwendete Neovim-Befehle

Diese Eingaben enthalten keine NVDA-Taste. Neovim führt sie aus; Access Link
meldet ihre semantische Wirkung.

| Eingabe | Neovim-Funktion |
| --- | --- |
| `i` | Insert-Modus beginnen |
| `Esc` | in den Normalmodus zurückkehren oder eine Neovim-Abfrage abbrechen |
| `h`, `j`, `k`, `l` | links, abwärts, aufwärts, rechts navigieren |
| `w` / `b` | zum nächsten / vorherigen Wort navigieren |
| `0` / `$` | zum Zeilenanfang / Zeilenende navigieren |
| `gg` / `G` | zum Dateianfang / Dateiende navigieren |
| `v` | Visual-Auswahl beginnen |
| `y` | Auswahl in Neovim kopieren |
| `p` | Inhalt eines Neovim-Registers einfügen |
| `z=` | Rechtschreibvorschläge für das aktuelle Wort öffnen |
| `:w` | Buffer speichern |
| `:q` | Neovim-Fenster beenden, sofern keine ungespeicherten Änderungen vorliegen |
| `:terminal` | Terminalbuffer öffnen |
| `Ctrl+\`, danach `Ctrl+n` | direkte Terminaleingabe verlassen |

Weitere Neovim-Befehle stehen in `:Tutor`, `:help quickref` und der
[offiziellen Neovim-Hilfe](https://neovim.io/doc/user/).
