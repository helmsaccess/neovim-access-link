# Sprachexplorationsmodus

Der Sprachexplorationsmodus liest Zeichen, Wörter oder Zeilen, ohne den echten
Neovim-Cursor zu bewegen. Er ist eine Sprachfunktion des Add-ons und kein
Braillemodus. Eine angeschlossene Braillezeile kann die erkundete Position
optional zusätzlich anzeigen.

Der Modus eignet sich beispielsweise, um beim Schreiben kurz das nächste Wort
oder eine benachbarte Zeile zu prüfen. Nach dem Loslassen der NVDA-Taste kann
unmittelbar an der unveränderten Einfügeposition weitergeschrieben werden.

## Bedienung

Die NVDA-Taste bleibt während des Sprachexplorationsmodus gedrückt:

| Taste | Bewegung der virtuellen Leseposition |
| --- | --- |
| `NVDA+h` / `NVDA+l` | vorheriges / nächstes Zeichen |
| `Umschalt+NVDA+h` / `Umschalt+NVDA+l` | vorheriges / nächstes Wort |
| `NVDA+k` / `NVDA+j` | vorherige / nächste Zeile |

Die erste Bewegung beginnt am echten Neovim-Cursor. Weitere Bewegungen
verändern nur die virtuelle Leseposition. Text, Auswahl, Fensteransicht und
echter Cursor bleiben unverändert.

Die Befehle gelten in einer exakt verbundenen und fokussierten Neovim-Pane in
Normal-, Insert-, Replace-, Visual- und Operator-Pending-Modus sowie in der
Neovim-Befehlszeile, im Terminal-Normalmodus und bei direkter Terminaleingabe.
In einer Shell, einer ungebundenen Pane, einem anderen Tab oder einer anderen
Anwendung behalten dieselben Tastenkombinationen ihr normales NVDA-Verhalten.

## Sprachexplorationsmodus beenden

Beim Loslassen der NVDA-Taste endet der Sprachexplorationsmodus und die Ausgabe
kehrt zum unveränderten echten Cursor zurück:

- Nach Zeichenexploration im Sprachexplorationsmodus wird das Cursorzeichen
  gesprochen.
- Nach Wort- oder Zeilenexploration im Sprachexplorationsmodus gelten die
  Einstellungen unter
  `Neovim Access Link → Navigation → Abschluss des Sprachexplorationsmodus`.

Für Wörter kann zusätzlich das Cursorzeichen ausgegeben werden. Für Zeilen
können das aktuelle Wort, das Cursorzeichen oder beide Angaben ergänzt werden.
Diese Einstellungen beeinflussen nur die Abschlussansage, nicht die während
des Sprachexplorationsmodus gelesenen virtuellen Positionen.

Ein kurzer Doppelton kennzeichnet die Rückkehr zum ursprünglichen Zeichen,
Wort oder zur ursprünglichen Zeile. Er folgt der konfigurierten Klangausgabe
für Zeilengrenzen.

## Optionale Unterstützung durch die Braillezeile

Der Sprachexplorationsmodus funktioniert ohne Braillezeile. Standardmäßig zeigt
eine angeschlossene Braillezeile die virtuelle Leseposition jedoch
vorübergehend mit an. Beim Ende des Modus kehrt sie zum echten Cursor zurück.

Unter `Neovim Access Link → Braille → Sprachexplorationsmodus` kann
„Braillezeile folgt der Position des Sprachexplorationsmodus“ ausgeschaltet
werden. Dann bleibt die Braillezeile während der Sprachbewegungen am echten
Cursor.

Eine einzelne Routingtaste an der vorübergehend angezeigten Position übernimmt
diese Position als echten Neovim-Cursor. Doppelte und dreifache
Routing-Bearbeitungsaktionen sind während des schreibgeschützten
Sprachexplorationsmodus ausgeschaltet.

Der eigenständige
[Braille-Explorationsmodus](braille.md#braille-explorationsmodus-zeilen-lesen-cursor-stehen-lassen)
gehört dagegen zur Navigation der Braillezeile. Er wird mit den
Navigationstasten der Braillezeile bedient, bleibt nach dem Umschalten aktiv
und besitzt eine eigene virtuelle Zeilenposition. Beide Modi teilen keinen
Zustand des Sprachexplorationsmodus.

## Sprachexplorationsmodus und Braille-Explorationsmodus

| Eigenschaft | Sprachexplorationsmodus | Braille-Explorationsmodus |
| --- | --- | --- |
| Hauptausgabe | Sprache | Braillezeile |
| Bedienung | NVDA-Taste zusammen mit `h`, `j`, `k` oder `l` | Navigationstasten der Braillezeile |
| Dauer | Nur solange die NVDA-Taste gehalten wird | In jeder verbundenen Neovim-Sitzung getrennt bis zum erneuten Umschalten oder Trennen |
| Virtuelle Bewegung | Zeichen, Wörter und Zeilen | Zeilen und sichtbare Ausschnitte |
| Echter Cursor | Bleibt stehen | Bleibt bei Oben und Unten stehen; Routing kann ihn übernehmen |
| Braillezeile erforderlich | Nein | Ja |
