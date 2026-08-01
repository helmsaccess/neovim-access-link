# Geführte Praxistests mit NVDA

## Zweck und Umfang

Diese Praxistests prüfen einen fertigen Neovim-Access-Link-Build nur dort, wo
ein automatisierter Test nicht zuverlässig entscheiden kann: reale
NVDA-Sprache, hörbare Klänge, eine physische Braillezeile, gehaltene
NVDA-Gesten und den tatsächlichen Fokus in Windows Terminal. Pro Aufgabe wird
genau eine solche Beobachtung bewertet. LSP-Antworten, Diagnosebereiche,
Sprungziele, Adapterzustände und Dateiformate bleiben automatisierten Tests
überlassen.

Die Fixtures liefern trotzdem bewusst echte Auswahlmöglichkeiten: mindestens
drei Completion-Kandidaten, zwei Funktionssignaturen mit jeweils drei
Parametern sowie zwei Diagnosen auf der ersten Diagnosezeile. Dadurch bedeutet
„durchschalten“ in einer Aufgabe immer einen sichtbaren Inhaltswechsel. Die
Audioaufgaben der Smoke-Suite prüfen alle vier unterschiedlichen Klänge dieses
Bereichs: Completion-Menü geöffnet, Completion-Menü geschlossen,
Diagnosewarnung und Diagnosefehler. Informationen und Hinweise besitzen
absichtlich keinen eigenen Diagnoseklang und werden deshalb nicht als weitere
Klangart ausgegeben.

Der Runner ist auch für Tester gedacht, die Neovim kaum kennen. Vor jeder
Aufgabe zeigt er diese Orientierung:

| Anzeige | Aussage |
| --- | --- |
| **Wo du bist** | aktueller Windows-Terminal-Tab und aktuelles Programm |
| **Was du jetzt tun sollst** | als Nächstes zu drückende Tasten und auszuführende Handlung |
| **Woran du das richtige Ergebnis erkennst** | erwartete wahrnehmbare Ausgabe |
| `Escape`, dann `F2` | aktuelle Aufgabe in Neovim erneut anzeigen und ausgeben |
| `Escape`, dann `F10` | Test-Neovim sicher schließen und zur Runner-PowerShell zurückkehren |

Es werden keine Neovim-Befehle mit Doppelpunkt benötigt. Die persönliche
`init.lua`, Lazy-Konfiguration und Neovim-Datenverzeichnisse werden nicht
verändert.

## Welche Suite ist sinnvoll?

| Suite | Inhalt | Wann ausführen? |
| --- | --- | --- |
| `smoke` | nativer LSP und Completion, Ruff-Diagnosen, Fokusisolation und Fail-open | üblicher Praxistest; empfohlen, etwa 15 bis 20 Minuten |
| `compatibility` | Completion-Menüs von nvim-cmp und blink.cmp | nach Änderungen an diesen Plugins, ihren Adaptern oder Abhängigkeiten |
| `all` | beide Suiten in einem Ergebnis | nur wenn beide Bereiche betroffen sind |

Die Standardaufgaben laufen immer in dieser Reihenfolge: nativer LSP,
Diagnosen, danach Fokusisolation. Fehlende Audioausgabe oder eine fehlende
Braillezeile verhindert die übrigen Aufgaben nicht. Der Runner markiert nur
die davon abhängigen Aufgaben automatisch als `notApplicable`.

## Zwei Ansichten im selben Terminal-Tab

Für den Ablauf ist dieser Unterschied wichtig:

| Ansicht | Was dort geschieht | Wie man sie verlässt |
| --- | --- | --- |
| **Runner-PowerShell** | `run.ps1` starten, Anweisung lesen und nach der Aufgabe das Ergebnis auswählen | Eingabetaste startet die angekündigte Aufgabe in Test-Neovim |
| **Test-Neovim** | genau die eine angekündigte Aufgabe durchführen | `Escape`, dann `F10` beendet nur Test-Neovim; dieselbe Runner-PowerShell erscheint wieder |

Nur die Fokusaufgabe verlangt zusätzlich einen zweiten Windows-Terminal-Tab.
Der Runner sagt genau an dieser Stelle, wann er geöffnet und wieder verlassen
werden soll. Ansonsten bleibt der Tester immer im ursprünglichen Tab.

## Voraussetzungen

| Voraussetzung | Wofür sie benötigt wird |
| --- | --- |
| Windows 11, Windows Terminal und NVDA mit dem zu prüfenden Add-on | eigentlicher Praxistest |
| über das NVDA-Menü aktuell installierte lokale Neovim-Komponenten | Verbindung zwischen Neovim und Access Link |
| Neovim 0.12.x, Git für Windows, Node.js LTS und Python 3.12 | isolierte Testumgebung, LSP, Linter und Completion-Plugins |
| Internetzugang bei der ersten Einrichtung | Download der festgelegten Testabhängigkeiten |
| Audioausgabe | nur Klangaufgaben; ohne Audio werden diese als `notApplicable` markiert |
| physische Braillezeile | nur Brailleaufgaben; ohne Braillezeile werden diese als `notApplicable` markiert |

Der Runner vergleicht den Laufzeitcode des installierten Neovim-Plugins mit
dem aktuellen Repository. Bei einer Abweichung muss im NVDA-Menü zuerst die
Installation der lokalen Komponenten erneut ausgeführt werden. Dadurch wird
nicht versehentlich ein alter Plugin-Stand bewertet.

## Start für Einsteiger

### 1. PowerShell im richtigen Ordner öffnen

Eine normale PowerShell in Windows Terminal öffnen. In den Wurzelordner des
Repositories wechseln, also in den Ordner, der unter anderem `tests`, `docs`,
`neovim-plugin` und `nvda-addon` enthält. Beispiel:

```powershell
Set-Location "C:\Pfad\zum\Repository"
Get-ChildItem tests\human\framework\run.ps1
```

Der zweite Befehl muss die Datei `run.ps1` anzeigen. Tut er das nicht, ist die
PowerShell noch im falschen Ordner.

### 2. Runner starten

```powershell
.\tests\human\framework\run.ps1
```

Falls die lokale Ausführungsrichtlinie den direkten Start verhindert:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\tests\human\framework\run.ps1
```

Im Startmenü **Kurzen Standardtest starten** wählen. Bei einer falschen
Eingabe bleibt das Menü geöffnet und bittet erneut um eine gültige Nummer.

### 3. Ausstattung angeben

Die Fragen zu Audio und physischer Braillezeile wahrheitsgemäß beantworten.
Die Eingabetaste übernimmt jeweils die angezeigte Vorgabe. Eine nicht
vorhandene Braillezeile ist kein Fehler; die entsprechenden Aufgaben werden
ausgelassen.

### 4. Eine Aufgabe ausführen

Jede Aufgabe ist ein kleiner, abgeschlossener Zyklus:

```text
Anweisung in PowerShell lesen
-> Eingabetaste
-> genau diese Aufgabe in Test-Neovim durchführen
-> Escape, dann F10
-> wieder in PowerShell genau dieses Ergebnis auswählen
```

Vor dem Start nennt der Runner **Wo du bist**, **Was du jetzt tun sollst** und
**Woran du das richtige Ergebnis erkennst**. Erst danach die Eingabetaste
drücken.

Wenn Test-Neovim erscheint:

1. Einmal `Escape` drücken. Damit ist sicher der Neovim-Normalmodus aktiv;
   versehentliche Texteingabe ist ausgeschlossen.
2. Access Link bei Bedarf im NVDA-Menü einschalten.
3. Den ursprünglichen Windows-Terminal-Tab fokussieren und `F12` genau einmal
   drücken. Kurz auf die Verbindung warten.
4. Nur die gerade angezeigte Aufgabe durchführen.
5. Bei Unsicherheit zuerst `Escape`, dann `F2` drücken. Die aktuelle
   Ortsangabe, Handlung und Erwartung werden erneut als Neovim-Mitteilung
   angezeigt und durch Access Link ausgegeben.
6. Nach der Beobachtung `Escape`, danach `F10` drücken. Nun ist wieder die
   Runner-PowerShell im ursprünglichen Tab sichtbar.
7. Nur die eben ausgeführte Aufgabe als bestanden, fehlgeschlagen, blockiert
   oder übersprungen bewerten.

Für die nächste Aufgabe startet ein frisches Test-Neovim. Deshalb muss sich
niemand mehrere Prüfschritte merken oder eine Fixture von Hand zurücksetzen.

## Vom Runner verwendete Tasten

Die jeweilige Aufgabe nennt nur die tatsächlich benötigten Tasten. Diese
Übersicht dient zum Nachschlagen:

| Taste | Bedeutung im Test-Neovim |
| --- | --- |
| `Escape`, dann `F2` | aktuelle Aufgabe jederzeit erneut anzeigen und ausgeben |
| `F1` | aktiven LSP-Status durch Access Link ausgeben |
| `F3`, danach `F5` | vorbereitete Completion-Stelle mit mindestens drei Kandidaten öffnen; `F3` wechselt automatisch in den Einfügemodus |
| `F6` | Ruff für die Diagnose-Fixture erneut ausführen |
| `F7` | Diagnose an der aktuellen Position ausgeben |
| `F8` / `F9` | zur vorherigen beziehungsweise nächsten Diagnose springen |
| `Escape`, dann `F10` | Test-Neovim ohne Speichern schließen und zu PowerShell zurückkehren |

Completion wird mit `Strg+N` und `Strg+P` durchlaufen, mit `Strg+Y`
übernommen und mit `Strg+E` geschlossen. Die Brailleaufgaben nennen die
erforderliche gehaltene NVDA-Geste vollständig. Ein Wechsel in Neovims
Befehlszeilenmodus ist nie erforderlich.

## Was vor dem ersten Test automatisch geschieht

Der Runner prüft zunächst Pläne, deutsche und englische Texte sowie alle
referenzierten Dateien. Beim ersten Lauf richtet er unter
`tmp/human-test-state/` eine isolierte Umgebung ein:

| Bestandteil | Verwendung |
| --- | --- |
| festgelegte Versionen von Pyright und Ruff | reproduzierbare LSP- und Diagnoseantworten |
| festgelegte Revisionen von nvim-lint, nvim-cmp, cmp-nvim-lsp und blink.cmp | reproduzierbare Provider- und Completion-Kompatibilität |
| eigene Neovim-Konfigurations-, Daten-, Zustands- und Cacheverzeichnisse | vollständige Trennung von der persönlichen Neovim-Umgebung |

Pyright wird als festgelegtes npm-Paketarchiv bereitgestellt und vor dem
Entpacken mit SHA-512 geprüft. Der Runner vermeidet damit den `npm install`-
Ablauf, der in eingebundenen Verzeichnissen unter Windows hängen kann.

Danach startet eine technische Vorprüfung jedes Testprofils. Sie wartet
tatsächlich auf einen angehängten Pyright-Client. In den Completion-Profilen
fordert sie die drei benannten Kandidaten ab; im nativen LSP-Profil zusätzlich
mindestens zwei Signaturen mit jeweils drei Parametern. Im Diagnoseprofil
erwartet sie zwei reale Ruff-F401-Warnungen in der ersten Zeile und mindestens
einen Ruff-F821-Fehler. Ein menschlicher Tester wird erst zu einer
Wahrnehmungsaufgabe geführt, wenn diese maschinell entscheidbaren Grundlagen
funktionieren.

**Testabhängigkeiten einrichten oder reparieren** installiert die verwalteten
Plugin-Revisionen neu und wiederholt diese Vorprüfung. Die persönliche
Neovim-Umgebung bleibt auch dabei unberührt. Für Git verwendet allein die
Test-Neovim-Sitzung eine temporäre globale Konfigurationsdatei, die nur die
verwalteten Pluginverzeichnisse unter `tmp/human-test-state/` als sicher
zulässt. Die persönliche globale Git-Konfiguration wird nicht verändert.

## Ergebnisauswahl

| Auswahl | Bedeutung |
| --- | --- |
| **bestanden** | Die beobachtete Ausgabe entsprach der Erwartung. |
| **fehlgeschlagen** | Die Aufgabe war ausführbar, verhielt sich aber falsch. Das vollständige Ergebnis erhält Zustand `fail`. |
| **blockiert** | Eine äußere Voraussetzung oder ein technisches Problem verhinderte die Beobachtung. Der Lauf bleibt unvollständig. |
| **übersprungen** | Eine anwendbare Aufgabe wurde bewusst nicht geprüft. Der Lauf bleibt unvollständig. |
| `notApplicable` | Wird nur automatisch für nicht vorhandene Audio- oder Brailleausstattung gesetzt. |
| `pending` | Die Aufgabe wurde noch nicht bewertet. |

Nur **bestanden** ist positive menschliche Evidenz. Für alle anderen manuell
gewählten Zustände verlangt der Runner eine kurze Begründung. Dort keine
privaten Pfade, Kontonamen, Schlüssel oder anderen Geheimnisse eintragen.

## Unterbrechen und bequem fortsetzen

Nach jeder Aufgabe wird der Zwischenstand gespeichert. Nach einem Abbruch den
Runner erneut ohne Parameter starten und **Unvollständigen Lauf fortsetzen**
wählen. Sind mehrere unvollständige Dateien vorhanden, zeigt er
die neuesten mit Dateinamen zur Auswahl an.

Bereits bestandene oder fehlgeschlagene Aufgaben bleiben erhalten. Der Runner
fragt, ob blockierte oder übersprungene Aufgaben erneut geöffnet werden
sollen. Diese Entscheidung ist ausdrücklich; ein Ergebnis wird nicht still
umgeschrieben.

Alternativ kann eine Datei direkt angegeben werden:

```powershell
.\tests\human\framework\run.ps1 run `
  -ResultPath .\tmp\human-test-results\BEISPIEL.json
```

Ein Lauf kann nur mit exakt derselben Testdefinition fortgesetzt werden. Der
Validator vergleicht dafür einen SHA-256-Fingerabdruck von Plänen,
Übersetzungen, Fixtures, Abhängigkeiten, Runner, Validator und
Test-Neovim-Konfiguration.

## JSON-Ergebnisse und maschinelle Prüfung

Neue Dateien liegen unter `tmp/human-test-results/`. Der Dateiname enthält
Zeitstempel, Suite und eine kurze Zufallskomponente, sodass auch zwei schnell
hintereinander gestartete Läufe nicht kollidieren. Nach jeder Auswahl wird
die Datei atomar ersetzt.

Aufgezeichnet werden:

| Bereich | Aufgezeichnete Angaben |
| --- | --- |
| Lauf | Lauf-ID, Erstellungs- und Abschlusszeit |
| Auswahl | Suite, Sprache und angegebene Audio-/Brailleausstattung |
| Quellstand | Git-Commit und Dirty-Zustand des Repositorys |
| Laufzeitversionen | Neovim-, installierte Add-on- und laufende NVDA-Version, soweit auffindbar |
| Konsistenz | Fingerabdrücke der Testdefinition und des installierten Neovim-Plugins |
| Ergebnisse | stabile Plan-/Aufgaben-IDs, Status und Begründungen |

Editorinhalte, Hostnamen und Zugangsdaten werden nicht automatisch erfasst.
Die Dateien im ignorierten `tmp/` werden weder committet noch hochgeladen oder
von CI eingesammelt.

Eine Datei wird im Startmenü über **Vorhandene JSON-Ergebnisdatei prüfen**
oder direkt geprüft:

```powershell
.\tests\human\framework\run.ps1 verify `
  -ResultPath .\tmp\human-test-results\BEISPIEL.json
```

Plattformunabhängig:

```bash
python3 tests/human/framework/validate.py result tmp/human-test-results/BEISPIEL.json
```

| Exitcode | Gesamtzustand |
| --- | --- |
| `0` | vollständig; alle anwendbaren Aufgaben bestanden |
| `1` | strukturell ungültig oder nicht mit den aktuellen Definitionen vereinbar |
| `2` | vollständig, aber mindestens eine Aufgabe fehlgeschlagen |
| `3` | offen, blockiert oder übersprungen und daher unvollständig |

## Optionale Completion-Kompatibilität

Nach Änderungen an nvim-cmp, blink.cmp oder den Access-Link-Adaptern im
Startmenü **Optionale Completion-Kompatibilität testen** wählen. Jede Aufgabe
startet auch dort einzeln. Die wichtigsten direkten Aufrufe sind:

| Ziel | PowerShell-Aufruf |
| --- | --- |
| Standard- und Kompatibilitätsaufgaben gemeinsam | `.\tests\human\framework\run.ps1 run -Suite all` |
| Benutzeroberfläche ausdrücklich auf Deutsch setzen | `.\tests\human\framework\run.ps1 -Language de` |
| Benutzeroberfläche ausdrücklich auf Englisch setzen | `.\tests\human\framework\run.ps1 -Language en` |

## Aufräumen und typische Probleme

**Heruntergeladene Testabhängigkeiten entfernen** löscht ausschließlich
`tmp/human-test-state/`. JSON-Ergebnisse bleiben erhalten.

Wenn Access Link nicht verbindet:

1. prüfen, ob der aktuelle Add-on-Build in NVDA installiert und aktiviert ist;
2. im NVDA-Menü die lokalen Neovim-Komponenten installieren oder aktualisieren;
3. sicherstellen, dass der ursprüngliche Tab mit Test-Neovim fokussiert ist;
4. dort `F12` genau einmal drücken und kurz warten;
5. mit `Escape`, `F2` prüfen, ob die aktuelle Aufgabe ausgegeben wird.

Wenn Pyright, Ruff oder ein Completion-Plugin fehlt, den Menüpunkt
**Testabhängigkeiten einrichten oder reparieren** verwenden. Schlägt dessen
technische Vorprüfung fehl, ist das ein Einrichtungsproblem und noch kein
menschlich zu bewertender Testfehler.

## Pflege des Frameworks

Die kompakte Implementierung liegt unter `tests/human/`:

| Pfad | Inhalt |
| --- | --- |
| `plans/` | ausschließlich deklarative Aufgabenkarten |
| `locales/` | synchrone deutsche und englische Texte |
| `fixtures/` | kleine, kontrollierte Testdateien |
| `dependencies.json` | festgelegte Fremdversionen und Revisionen |
| `framework/` | Runner, Validator und isolierte Neovim-Konfiguration |

Eine neue menschliche Aufgabe benötigt einen Grund, der nicht zuverlässig
automatisierbar ist, und verweist auf verwandte automatisierte Evidenz. Kann
Code das Ergebnis eindeutig entscheiden, gehört der Fall in einen
automatisierten Test. Definitionen werden geprüft mit:

```bash
python3 tests/human/framework/validate.py plans
python3 tools/run_tests.py quick
```

GitHub Actions führt den PowerShell-Runner zusätzlich unter Windows aus. Das
findet PowerShell-spezifische Parser- und Laufzeitfehler, erklärt aber niemals
Sprache, Klänge, Braille oder Fokus als menschlich bestanden.
