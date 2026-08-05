# Neovim- und Windows-Terminal-Grundlagen

Dieses Kapitel erklärt nur die Begriffe und Neovim-Befehle, die für die
weiteren Access-Link-Abläufe erforderlich sind. Es ersetzt keinen allgemeinen
Neovim-Kurs.

## Windows Terminal verstehen

Windows Terminal ordnet Terminals in drei Ebenen an:

- Ein **Fenster** ist das gesamte Windows-Terminal-Fenster.
- Ein **Tab** ist eine Registerkarte innerhalb dieses Fensters.
- Ein **Pane** ist ein geteilter Bereich innerhalb eines Tabs. Jedes Pane ist
  ein eigenes Terminal mit eigenem Inhalt und Fokus.

Ein Tab ohne Teilung enthält ein Terminal-Control. Ein geteilter Tab enthält
mehrere Terminal-Controls, je eines pro Pane. Access Link speichert die
Neovim-Zuordnung für jedes Control getrennt. Ein Pane kann lokales Neovim
enthalten, ein zweites Neovim über SSH und ein drittes eine normale Shell.

Beim Wechsel prüft Access Link das exakt fokussierte Control. Nur ein
verbundenes Neovim-Control erhält strukturierte Ausgabe. Eine Shell oder ein
unverbundenes Pane verhält sich wie Windows Terminal ohne das Add-on.

## Neovims Inhalt verstehen

Neovim besitzt innerhalb eines Terminal-Controls eigene Strukturen:

- Ein **Buffer** enthält Text. Er kann zu einer Datei gehören oder noch keinen
  Dateinamen besitzen.
- Ein **Neovim-Fenster** zeigt einen Buffer. Mehrere Neovim-Fenster können
  gleichzeitig in demselben Terminal-Control sichtbar sein.
- Ein **Neovim-Tab** gruppiert eine Anordnung aus Neovim-Fenstern.

Ein Windows-Terminal-Tab und ein Neovim-Tab sind daher verschiedene Dinge. Das
Handbuch schreibt den vollständigen Begriff, wenn eine Verwechslung möglich
ist.

## Die wichtigsten Modi

Neovim reagiert abhängig vom aktuellen Modus unterschiedlich:

| Modus | Zweck | Einstieg oder Rückkehr |
| --- | --- | --- |
| Normalmodus | navigieren und Befehle ausführen | Neovim startet hier; `Esc` kehrt hierher zurück |
| Insert-Modus | Text eingeben | `i` beginnt die Eingabe |
| Replace-Modus | vorhandenen Text überschreiben | `R` beginnt das Ersetzen |
| Visual-Modus | Text auswählen | `v` beginnt eine zeichenweise Auswahl |
| Select-Modus | Auswahl mit anschließender Eingabe ersetzen | wird meist durch ein Mapping oder Plugin geöffnet |
| Befehlszeilenmodus | Ex-Befehle eingeben | `:` öffnet die Befehlszeile |
| Operator-Pending-Modus | auf das Ziel eines Befehls warten | beispielsweise nach `d` oder `c` |
| Terminal-Normalmodus | in einem Terminalbuffer mit Neovim navigieren | `Ctrl+\`, danach `Ctrl+n` |

Access Link meldet die unterstützten Moduswechsel strukturiert. Die
Modusbefehle selbst gehören zu Neovim.

## Ein erster sicherer Bearbeitungsablauf

Starten Sie Neovim mit einer unwichtigen Testdatei oder ohne Dateinamen:

1. Drücken Sie `i`. Neovim wechselt in den Insert-Modus.
2. Schreiben Sie eine kurze Zeile.
3. Drücken Sie `Esc`. Neovim kehrt in den Normalmodus zurück.
4. Navigieren Sie mit `h` und `l` zeichenweise oder mit `j` und `k`
   zeilenweise.
5. Geben Sie `:w dateiname.txt` ein und drücken Sie `Eingabe`, um einen bisher
   namenlosen Buffer zu speichern.
6. Geben Sie `:q` ein und drücken Sie `Eingabe`, um Neovim zu beenden.

Bei einer vorhandenen Datei speichert `:w` unter ihrem aktuellen Namen.
Neovim verhindert `:q`, wenn ungespeicherte Änderungen vorhanden sind.

## Tastenkombination oder Tastenfolge

Ein Pluszeichen bedeutet gleichzeitig gehaltene Tasten. `NVDA+Alt+D` ist ein
NVDA-Befehl; `Ctrl+w` ist eine von Neovim oder Windows Terminal ausgewertete
Kombination, abhängig vom Kontext.

Kommas oder eine direkt geschriebene Neovim-Folge bedeuten nacheinander
gedrückte Tasten. `z=` öffnet Neovims Rechtschreibvorschläge. `Leertaste`, `l`,
`s` ruft in der Beispielkonfiguration den LSP-Status auf.

Die NVDA-Taste kennzeichnet die Screenreader-Ebene. Ohne NVDA-Taste bleibt die
Eingabe bei Neovim beziehungsweise Windows Terminal. Access Link beobachtet
Neovims semantisches Ergebnis und macht es zugänglich; es erfindet keine zweite
Editorbedienung.

## Neovim weiter lernen

Geben Sie `:Tutor` ein und drücken Sie `Eingabe`, um Neovims interaktiven Kurs
zu starten. Mit `:help nvim-intro` öffnet Neovim seine Einführung. Die
[offizielle Online-Hilfe](https://neovim.io/doc/user/) enthält dieselben
Grundlagen und weiterführende Kapitel.
