# Geführte Praxistests mit NVDA

## Zweck und Umfang

Die 18 Aufgabenkarten beschreiben reproduzierbare Bedienabläufe für einen
fertigen Neovim-Access-Link-Build. Die Testgruppen `guided-desktop` und
`guided-audio` führen die technisch prüfbaren Teile aller Karten in einem
isolierten Windows-Gast aus. Sie erfassen unter anderem Windows-Fokus,
gehaltene NVDA-Gesten, Sprachsequenzen vor der Synthese, digitale
Braille-Zellen und gerenderte Audiosignale. `tests/guided/windows/README.md`
beschreibt den automatisierten Lauf und seine Nachweise.

Der interaktive Runner bleibt für Fragen zur subjektiven Sprach- und
Klangwahrnehmung, Reaktionszeit und Bedienung einer physischen Braillezeile
verfügbar. Eine Karte bündelt zusammengehörige Beobachtungen derselben
Bedienhandlung. Bei automatischen Parameterhinweisen prüfen die Tests echte
Pyright-Übergänge, die gesprochene Sequenz und die Quelltextzeile in Braille.
Resolver, Verschachtelung, Überladungen, Rückkehr in einen bereits ausgefüllten
Parameter, Deduplizierung, Grenzen und veraltete Antworten besitzen getrennte
automatisierte Regressionen.

Die Fixtures liefern trotzdem bewusst echte Auswahlmöglichkeiten: mindestens
drei Completion-Kandidaten, zwei Funktionssignaturen mit jeweils drei
Parametern sowie zwei Diagnosen auf der ersten Diagnosezeile. Dadurch bedeutet
„durchschalten“ in einer Aufgabe immer einen sichtbaren Inhaltswechsel. Die
Audioanteile der Smoke-Suite prüfen alle fünf unterschiedlichen Klänge dieses
Bereichs: Completion-Menü geöffnet, Completion-Menü geschlossen,
Diagnosewarnung, Diagnosefehler und die Bestätigung einer ausdrücklichen
Diagnoseabfrage ohne Treffer. Informationen und Hinweise besitzen absichtlich
keinen eigenen Diagnoseklang und werden deshalb nicht als weitere Klangart
ausgegeben.

Der Runner ist auch für Tester gedacht, die Neovim kaum kennen. Vor jeder
Aufgabe gliedert er die Anleitung so:

| Anzeige | Aussage |
| --- | --- |
| **Zweck dieses Tests** | geprüfte Funktion und Grund der Prüfung |
| **Tasten und Schritte** | kurze nummerierte Bedienfolge mit Wirkung der Tasten |
| **Bestanden, wenn** | erwartete wahrnehmbare Ausgabe |
| `Escape`, dann `F2` | Test-ID, Zweck, Schritte und Bestehenskriterium in Neovim erneut anzeigen und ausgeben |
| `Escape`, dann `F10` | Test-Neovim sicher schließen und zur Runner-PowerShell zurückkehren |

Feste Umbrüche trennen nur nummerierte Schritte. Längere Zeilen bricht Windows
Terminal passend zur aktuellen Fensterbreite um; ein maximiertes Fenster nutzt
den vorhandenen Platz. Längere native Abläufe liegen auf den in der Aufgabe
genannten Funktionstasten, sodass keine Doppelpunktbefehle eingegeben werden
müssen. Die persönliche `init.lua`, Lazy-Konfiguration und die
Neovim-Datenverzeichnisse werden nicht verändert.

## Welche Suite ist sinnvoll?

| Suite | Inhalt | Wann ausführen? |
| --- | --- | --- |
| `smoke` | nativer LSP, Suche, Ersetzung und Completion, Ruff-Diagnosen, Fokusisolation und Fail-open | üblicher Praxistest; empfohlen, etwa 20 bis 30 Minuten |
| `compatibility` | Completion-Menüs von nvim-cmp und blink.cmp, C-/Clang-Tidy- und Markdown-/markdownlint-Diagnosen sowie lazy.nvim-Pluginverwaltung | nach Änderungen an Adaptern, Linterintegration, Pluginverwaltung oder Abhängigkeiten |
| `all` | beide Suiten in einem Ergebnis | nur wenn beide Bereiche betroffen sind |
| individuelle Auswahl | einzelne Aufgaben, im Menü nach Kategorien gruppiert | gezielte Nachprüfung eines betroffenen Bereichs; spart Zeit und unnötige Downloads |

| Kategorie der Einzelauswahl | Beispiele |
| --- | --- |
| LSP und Sprachintelligenz | LSP-Status, automatische aktive Parameter, gehaltene Funktionssignaturen, native Suche/Ersetzung und LSP-Rename |
| Vervollständigung | native Completion, nvim-cmp und blink.cmp |
| Diagnosen und Linter | Ruff, Clang-Tidy und markdownlint |
| Sitzung und Terminalintegration | Fokusisolation und Fail-open |
| Plugin-Verwaltung | lazy.nvim-Fenster, Installation, Aktualisierung und Synchronisierung |

### Stabile Test-IDs

Jede Aufgabe besitzt eine eindeutige zweistellige ID. Der erste Buchstabe
bezeichnet die Kategorie (`L` LSP/Sprachintelligenz, `C` Completion, `D`
Diagnosen, `S` Sitzung, `P` Plugin-Verwaltung); das zweite Zeichen unterscheidet die Aufgaben. Diese
IDs werden nie umnummeriert oder erneut vergeben. Sie erscheinen im
Auswahlmenü, vor jeder Aufgabe, in der JSON-Ergebnisdatei und bei `F2` in
Test-Neovim. Damit genügt beispielsweise „Fehler in D3“ als eindeutige
Referenz.

| ID | Aufgabe |
| --- | --- |
| `L1` | LSP-Status |
| `L2` | automatische aktive Parameter |
| `L3` | gehaltene Funktionssignaturen und Parameter |
| `L4` | native Suche, Quickfix und projektweite Ersetzung |
| `L5` | native LSP-Umbenennung über mehrere Dateien |
| `L6` | native Ersetzung über gelistete Buffer |
| `C1` | native Completion |
| `C2` | nvim-cmp |
| `C3` | blink.cmp |
| `D1` | Python-/Ruff-Diagnosen |
| `D2` | gehaltene Diagnosen |
| `D3` | C-/Clang-Tidy-Diagnosen |
| `D4` | Markdown-/markdownlint-Diagnosen |
| `S1` | Fokusisolation und Verbindungsabbruch |
| `P1` | lazy.nvim-Fenster und Navigation |
| `P2` | Installation eines isolierten Test-Plugins |
| `P3` | Aktualisierung eines isolierten Test-Plugins |
| `P4` | Synchronisierung mit Installation, Aktualisierung und Bereinigung |

Die Standardaufgaben laufen immer in dieser Reihenfolge: nativer LSP,
Diagnosen, danach Fokusisolation. Fehlende Audioausgabe oder eine fehlende
Braillezeile verhindert die übrigen Aufgaben nicht. Ohne Audio werden die
ausdrücklich bedingten Klanganteile nicht bewertet; die JSON-Umgebung hält
dies fest. Ausschließlich von Braillehardware abhängige Aufgaben markiert der
Runner automatisch als `notApplicable`.

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
| Audioausgabe | Klanganteile der Completion- und Diagnoseabläufe; ohne Audio werden nur Sprache und Bedienbarkeit bewertet |
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

Im Startmenü **Neuen kurzen Standardtest starten** wählen. Dieser Menüpunkt
beginnt bewusst eine neue JSON-Datei; nach einem Abbruch stattdessen
**Unvollständigen Lauf fortsetzen** wählen. Bei einer falschen
Eingabe bleibt das Menü geöffnet und bittet erneut um eine gültige Nummer.
Für eine gezielte Nachprüfung stattdessen **Einzelne Testaufgaben nach
Kategorie auswählen** wählen. Eine Nummer schaltet die jeweilige Aufgabe ein
oder aus; `S` startet nur die markierten Aufgaben.

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

Vor dem Start nennt der Runner **Zweck dieses Tests**, **Tasten und Schritte**
und **Bestanden, wenn**. Erst danach die Eingabetaste drücken.

Wenn Test-Neovim erscheint:

1. Einmal `Escape` drücken. Damit ist sicher der Neovim-Normalmodus aktiv;
   versehentliche Texteingabe ist ausgeschlossen.
2. Access Link bei Bedarf im NVDA-Menü einschalten.
3. Den ursprünglichen Windows-Terminal-Tab fokussieren und `F12` genau einmal
   drücken. Kurz auf die Verbindung warten.
4. Nur die gerade angezeigte Aufgabe durchführen.
5. Bei Unsicherheit zuerst `Escape`, dann `F2` drücken. Test-ID, Zweck,
   nummerierte Schritte und Bestehenskriterium werden erneut als
   Neovim-Mitteilung angezeigt und durch Access Link ausgegeben.
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
| `Escape`, dann `F2` | ID, Zweck, Schritte und Bestehenskriterium jederzeit erneut anzeigen und ausgeben |
| `F3` bei L1 | aktiven LSP-Status durch Access Link ausgeben |
| `F3` bei Eingabe- und Completion-Aufgaben | die vorbereitete Eingabestelle öffnen und automatisch in den Einfügemodus wechseln; bei der Completion-Aufgabe danach `F5` drücken |
| `F3`, `F4`, `F5` bei L4 | die native Projektsuche ausführen und ihre Quickfix-Liste öffnen, dann innerhalb der Liste den nächsten und vorherigen Treffer auswählen |
| `F6` bei L4 | die native projektweite Ersetzung mit Neovims Bestätigungsabfragen starten |
| `F3`, `F4` bei L5 | ein leeres Namensfeld öffnen, die Eingabe an Neovims native LSP-Umbenennung übergeben und danach beide umbenannten Referenzzeilen nacheinander ausgeben |
| `F3`, `F4` bei L6 | die vorbereitete `bufdo`-Ersetzung ausführen und danach beide tatsächlich geänderten Dateien nacheinander ausgeben |
| `F5` im Diagnoseprofil | auf eine vorbereitete fehlerfreie Position wechseln und dort ausdrücklich die aktuelle Diagnose abfragen |
| `F6` | den ausgewählten Linter ausführen, auf dessen Bereitschaft warten und den Cursor auf die erste erwartete Testdiagnose setzen |
| `F7` | Diagnose an der aktuellen Position ausgeben |
| `F8` / `F9` | zur vorherigen beziehungsweise nächsten Diagnose springen |
| `F3`, `F4`, `F5` bei P1 bis P4 | lazy.nvim öffnen, die vorbereitete öffentliche Verwaltungsaktion starten und den tatsächlichen isolierten Git-Endzustand prüfen; P1 benötigt nur F3 und Lazys normale Tasten |
| `Escape`, dann `F10` | Test-Neovim ohne Speichern schließen und zu PowerShell zurückkehren |

Completion wird mit `Strg+N` und `Strg+P` durchlaufen, mit `Strg+Y`
übernommen und mit `Strg+E` geschlossen. Die Brailleaufgaben nennen die
erforderliche gehaltene NVDA-Geste vollständig. L4 verwendet bewusst die kurze
Schrägstrichsuche; längere Doppelpunktbefehle müssen nicht eingegeben werden,
weil die aufgabenspezifischen Funktionstasten die vorbereiteten nativen Befehle
direkt ausführen. Neovim behält die Ausführung und jede Bestätigungsabfrage;
erzeugte Befehlszeichen werden nicht als Eingabe ausgegeben. Bei L4 meldet
`F3` die Trefferzahl und `F4` beziehungsweise `F5` die vollständige
Trefferzeile samt Position. Auch bei wiederholter Auswahl bleibt das
Quickfix-Fenster geöffnet; Quelldateien und Fenster werden dabei nicht als
Fokuswechsel angesagt. Ein weiterer Druck am ersten oder letzten Treffer
meldet die erreichte Grenze; dabei darf weder ein einzelnes Zeichen noch
Neovims Meldung „No more items“ ausgegeben werden. `F6` gibt jede native
Bestätigungsabfrage aus, bevor eine Antwort erforderlich ist, und danach genau
eine Gesamtsumme; intern besuchte Dateien oder Fenster dürfen nicht als
Fokuswechsel erscheinen. `F1` und `F11` werden bewusst nicht verwendet: F1
öffnet in Neovim die Hilfe, F11 schaltet in Windows Terminal standardmäßig den
Vollbildmodus um.

Bei L5 ist die bekannte Referenzdatei bereits vor der Interaktion geladen.
`F3` nimmt dadurch nur den neuen Namen entgegen; Neovim, Pyright und Neovims
normaler `WorkspaceEdit`-Handler besitzen weiterhin die Umbenennung. Jeder
Druck auf `F4` gibt die nächste tatsächlich geänderte Referenzzeile aus, ohne
den aktuellen Puffer zu wechseln. Ein automatisierter TUI-/RPC-Test führt
diese physischen Funktionstasten mit einem deterministischen Test-Sprachserver
aus und schließt zusätzliche Text-, Cursor- und Kontextmeldungen aus.
Der geführte Gasttest erfasst die NVDA-Sprachsequenzen bei der Umbenennung
mit echtem Pyright.

L6 ergänzt L4 um Neovims Bufferliste. Die zweite Datei ist vor der Interaktion
geladen und ausdrücklich gelistet; `F3` lässt Neovim `bufdo` über beide Dateien
ausführen. Access Link soll nur eine Gesamtsumme ausgeben. `F4` prüft danach
zweimal den tatsächlichen Bufferinhalt, ohne den aktuellen Buffer zu wechseln.
Ein automatisierter echter TUI-/RPC-Test führt dieselben Funktionstasten aus
und schließt zusätzliche Text-, Cursor- und Kontextmeldungen aus.

## Was vor dem ersten Test automatisch geschieht

Der Runner prüft zunächst Pläne, deutsche und englische Texte sowie alle
referenzierten Dateien. Beim ersten Lauf richtet er unter
`tmp/human-test-state/` eine isolierte Umgebung ein:

| Bestandteil | Verwendung |
| --- | --- |
| festgelegte Versionen von Pyright, Ruff, Clang-Tidy und markdownlint-cli2 | reproduzierbare LSP- und Diagnoseantworten; installiert werden nur die für die Auswahl benötigten Werkzeuge |
| festgelegte Revisionen von nvim-lint, nvim-cmp, cmp-nvim-lsp, blink.cmp und lazy.nvim | reproduzierbare Provider-, Completion- und Plugin-Verwaltungskompatibilität; geladen werden nur die für die Auswahl benötigten Plugins |
| eigene Neovim-Konfigurations-, Daten-, Zustands- und Cacheverzeichnisse | vollständige Trennung von der persönlichen Neovim-Umgebung |

Pyright wird als festgelegtes npm-Paketarchiv bereitgestellt und vor dem
Entpacken mit SHA-512 geprüft. Der Runner vermeidet damit den `npm install`-
Ablauf, der in eingebundenen Verzeichnissen unter Windows hängen kann. Er
prüft Paketversion, Server- und CLI-Datei sowie einen echten CLI-Aufruf und
startet den JavaScript-Sprachserver anschließend ausdrücklich mit Node statt
über einen Windows-Batch-Wrapper.

Spätere Läufe vergleichen einen getrennten Umgebungsfingerabdruck, die für die
Auswahl benötigten Werkzeugversionen und Plugin-Revisionen. Änderungen nur
an Aufgabentexten, Übersetzungen oder Ergebnislogik lösen deshalb keine neue
Einrichtung aus. Stimmen die benötigten Werkzeuge und Plugins bereits, werden
sie ohne Paketinstallation wiederverwendet. Der gespeicherte Zustand enthält
zusätzlich die erfolgreich vorgeprüften Profile; neu ausgewählte Profile
durchlaufen ihre Vorprüfung auch dann, wenn ihre Dateien bereits vorhanden
sind. Clang-Tidy und markdownlint werden
bei einem normalen Smoke-Lauf nicht vorsorglich installiert. Nur die
technische Vorprüfung der tatsächlich ausgewählten Profile wird nach
relevanten Laufzeitänderungen wiederholt.

Danach prüft der Runner die echten Ausgaben aller benötigten Linter direkt mit
den festgelegten Testdateien. Anschließend startet eine technische Vorprüfung
jedes ausgewählten Testprofils. Bei
LSP-Aufgaben wartet sie tatsächlich auf einen angehängten Pyright-Client. Die
Rename-Aufgabe verlangt dessen native Rename-Fähigkeit. In den
Completion-Profilen fordert die Vorprüfung die drei benannten Kandidaten ab;
bei den Signaturaufgaben zusätzlich mindestens zwei Signaturen mit jeweils
drei Parametern. Im Diagnoseprofil
erwartet sie zwei reale Ruff-F401-Warnungen in der ersten Zeile und mindestens
einen Ruff-F821-Fehler. Dabei betrachtet die Bereitschaftsprüfung nur den
Diagnoseraum des gerade geprüften Linters; Pyright-Diagnosen können das Ruff-
Ergebnis weder erfüllen noch verdecken. Die C- und Markdown-Profile verlangen vorab eine echte
Clang-Tidy-Fehlermeldung beziehungsweise markdownlint-MD025-Warnung. Schlägt
ein direkter Werkzeugtest fehl, zeigt der Runner dessen Ausgabe. Bei einem
Linterfehler nennt er den konfigurierten Provider und ob dessen Prozess noch
läuft. Die Vorbereitung bricht beim ersten Fehler ab. Ein menschlicher Tester wird erst
zu einer Wahrnehmungsaufgabe geführt, wenn diese maschinell entscheidbaren
Grundlagen funktionieren.

**Testabhängigkeiten einrichten oder reparieren** ist die ausdrückliche
Reparaturfunktion: Sie installiert die für die Auswahl benötigten verwalteten
Plugin-Revisionen neu und
wiederholt diese Vorprüfung. Der normale Standardtest führt diese erzwungene
Neuinstallation nicht aus. Die persönliche
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
| `notApplicable` | Wird automatisch gesetzt, wenn eine Aufgabe zwingend nicht vorhandene Hardware benötigt, derzeit die Brailleaufgaben. |
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
| Auswahl | Suite, exakte zweistellige Test-IDs, Sprache und angegebene Audio-/Brailleausstattung |
| Quellstand | Git-Commit und Dirty-Zustand des Repositorys |
| Laufzeitversionen | Neovim-, installierte Add-on- und laufende NVDA-Version, soweit auffindbar |
| Konsistenz | Fingerabdrücke der Testdefinition und des installierten Neovim-Plugins |
| Ergebnisse | zweistellige Test-ID, technischer Aufgabenschlüssel, Status und Begründung |

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

## Optionale Kompatibilitäts- und Einzeltests

Nach Änderungen an nvim-cmp, blink.cmp, der Linterintegration oder den
Access-Link-Adaptern im Startmenü **Optionale Kompatibilitätstests starten
(Completion, C und Markdown)** wählen. Sie enthält zusätzlich je einen kleinen C- und
Markdown-Realitätscheck. Jede Aufgabe startet einzeln. Die wichtigsten
direkten Aufrufe sind:

| Ziel | PowerShell-Aufruf |
| --- | --- |
| Standard- und Kompatibilitätsaufgaben gemeinsam | `.\tests\human\framework\run.ps1 run -Suite all` |
| genau den C-Diagnosetest ausführen | `.\tests\human\framework\run.ps1 run -Suite custom -TestId D3` |
| zwei bestimmte Aufgaben ausführen | `.\tests\human\framework\run.ps1 run -Suite custom -TestId L1,D4` |
| Benutzeroberfläche ausdrücklich auf Deutsch setzen | `.\tests\human\framework\run.ps1 -Language de` |
| Benutzeroberfläche ausdrücklich auf Englisch setzen | `.\tests\human\framework\run.ps1 -Language en` |

Die älteren technischen Langformen wie
`c-diagnostics.clang-tidy-presentation` bleiben als Kompatibilitätsalias
gültig. Für neue Berichte und Aufrufe ausschließlich die kurze Test-ID
verwenden.

## Aufräumen und typische Probleme

**Heruntergeladene Testabhängigkeiten entfernen** löscht ausschließlich
`tmp/human-test-state/`. JSON-Ergebnisse bleiben erhalten.

Wenn Access Link nicht verbindet:

1. prüfen, ob der aktuelle Add-on-Build in NVDA installiert und aktiviert ist;
2. im NVDA-Menü die lokalen Neovim-Komponenten installieren oder aktualisieren;
3. sicherstellen, dass der ursprüngliche Tab mit Test-Neovim fokussiert ist;
4. dort `F12` genau einmal drücken und kurz warten;
5. mit `Escape`, `F2` prüfen, ob Test-ID, Zweck, Schritte und
   Bestehenskriterium ausgegeben werden.

Wenn Pyright, ein Linter oder ein Completion-Plugin fehlt, den Menüpunkt
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

Eine neue menschliche Aufgabe erhält eine der fünf festen Kategorien und
benötigt einen Grund, der nicht zuverlässig
automatisierbar ist, und verweist auf verwandte automatisierte Evidenz. Kann
Code das Ergebnis eindeutig entscheiden, gehört der Fall in einen
automatisierten Test. Definitionen werden geprüft mit:

```bash
python3 tests/human/framework/validate.py plans
python3 tools/run_tests.py quick
```

GitHub Actions prüft im Repository-Workflow den PowerShell-Runner unter
Windows mit Definitionen und Trockenläufen. Die Ergebnisse der
automatisierten Gasttests stehen in separaten Berichten.
