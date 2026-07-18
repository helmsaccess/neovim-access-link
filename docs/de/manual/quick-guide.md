# Neovim Access Link – Quick Guide

Dieser Quick Guide führt von der Installation bis zur ersten funktionierenden
Verbindung. Er beschreibt den aktuellen Alpha- bis Beta-Stand für NVDA 2026.1.x unter
Windows 11. Unterstützt wird Neovim in Windows Terminal:

- lokal als Windows-Programm `nvim.exe`,
- entfernt auf Linux über eine normale SSH-Sitzung,
- mit mehreren Windows-Terminal-Tabs und -Fenstern,
- optional innerhalb von tmux auf dem Linux-Rechner.

Andere Terminalprogramme und grafische Neovim-Oberflächen werden derzeit nicht
unterstützt.

Der aktuelle Stand liegt zwischen Alpha und Beta. Nicht alle Funktionen wurden
bereits ausführlich praktisch getestet. Insbesondere die Brailleunterstützung
wurde noch nicht mit einer echten Braillezeile geprüft und enthält sehr
wahrscheinlich Fehler. Braille ist ein wichtiges, ausdrücklich eingeplantes
Arbeitsgebiet, aber noch keine belastbare Funktionszusage.

## 1. Voraussetzungen

Für alle Verbindungen werden benötigt:

- Windows 11,
- NVDA 2026.1.x,
- Windows Terminal,
- Neovim 0.10.1 oder neuer.

Für ein Linux-Ziel werden zusätzlich benötigt:

- Python 3 auf dem Linux-Rechner,
- der Windows-OpenSSH-Client,
- eine funktionierende SSH-Anmeldung. Empfohlen werden ein SSH-Schlüssel,
  `ssh-agent` oder ein bereits eingerichteter SSH-Alias. Eine zugängliche
  Passwortabfrage ist ebenfalls möglich.

## 2. Add-on installieren

Bei einem Wechsel von einem Build mit der früheren internen ID
`nvimNvdaAccess` zuerst dieses alte Add-on deinstallieren und NVDA neu starten.
Andernfalls können beide Global Plugins gleichzeitig geladen werden. Alte
Einstellungen und Tastenzuweisungen werden nicht übernommen.

1. Die Datei `NeovimAccessLink-<Version>.nvda-addon` unter Windows öffnen.
2. Die Installation in NVDA bestätigen.
3. NVDA neu starten.

Nach dem Neustart erscheint unter „NVDA-Menü → Optionen → Einstellungen…“ die
Kategorie „Neovim Access Link“. Unter „NVDA-Menü → Optionen →
Tastenbefehle…“ gibt es ebenfalls eine gleichnamige Kategorie für die
Tastenzuweisungen. Die frei belegbaren Befehle werden dort unabhängig davon
angezeigt, welche Anwendung vor dem Öffnen des Dialogs fokussiert war.

## 3. Eigene Aktivierungstaste festlegen

1. „NVDA-Menü → Optionen → Tastenbefehle…“ öffnen.
2. Die Kategorie „Neovim Access Link“ suchen.
3. Dem Befehl „Neovim-Barrierefreiheit ein- oder ausschalten und konfigurierte
   Verbindungen erkennen“ eine gut erreichbare Tastenkombination zuweisen.

`Ctrl+Alt+N` sollte nicht verwendet werden, weil Windows diese Kombination je
nach NVDA-Installation für einen NVDA-Neustart verwenden kann.

`F12` muss nicht als Aktivierungstaste eingerichtet werden. F12 dient nur dazu,
die gerade fokussierte Neovim-Instanz eindeutig mit dem aktuellen
Windows-Terminal-Control zu verbinden. Bei eingeschaltetem Dienst autorisiert
jeder physische F12-Druck genau einen Zuordnungsversuch für das gerade
fokussierte Control.

Für die Zwischenablage stehen in derselben Kategorie vier weitere Befehle ohne
Standardbelegung bereit:

- aktive Neovim-Visual-Auswahl in die Windows-Zwischenablage kopieren;
- Neovims letzten Yank aus Register 0 in die Windows-Zwischenablage kopieren;
- Windows-Zwischenablagentext in den aktiven Neovim-Buffer einfügen;
- Windows-Zwischenablagentext in Neovims aktuelles unbenanntes Register
  übertragen, damit er anschließend mit `p` verwendet werden kann.

Diese Befehle müssen bei Bedarf mit eigenen NVDA-Tastenkombinationen belegt
werden. Sie wirken nur in der ausdrücklich gebundenen und aktuell fokussierten
Neovim-Sitzung. Außerhalb eines eindeutig erkannten Windows-Terminal-Controls
wird eine solche eigene Tastenkombination unverändert an die fokussierte
Anwendung weitergegeben; normales Windows-Terminal-Copy-and-Paste bleibt
unverändert.

## 4. Komponenten installieren

Vor der Aktualisierung alle laufenden Neovim-Instanzen auf den ausgewählten
Rechnern schließen. Dadurch ist ausgeschlossen, dass eine bereits geladene
alte Pluginfassung bis zum nächsten Neovim-Neustart weiterläuft.

1. „NVDA-Menü → Werkzeuge → Neovim Access Link: Install or update components...“
   öffnen.
2. Für lokales Windows-Neovim „This computer“ markieren.
3. Gewünschte Linux-Verbindungen markieren. Anfangs ist absichtlich kein Ziel
   ausgewählt; „Select all connections“ markiert alle Ziele.
4. Mit „OK“ starten.
5. Die Ergebnisübersicht prüfen. Jedes Ziel wird als erfolgreich oder
   fehlgeschlagen aufgeführt.
6. Neovim anschließend neu starten.

Das Add-on bringt Plugin, Bridge und Konfiguration selbst mit. Die Zielrechner
laden während der Installation nichts aus dem Internet. Unter Linux erfolgt
die Installation ohne root-Rechte in das Home-Verzeichnis des jeweiligen
Benutzers.

Zum vollständigen Entfernen zuerst Neovim auf den gewünschten Zielen beenden
und „NVDA-Menü → Werkzeuge → Neovim Access Link: Remove components...“ öffnen.
Ziele wie bei der Installation ausdrücklich markieren und die Ergebnisübersicht
prüfen. Verbindungsprofile, Neovim- und SSH-Konfiguration sowie andere Plugins
bleiben erhalten.

## 5. Linux-Verbindung anlegen

Dieser Schritt entfällt für lokales Windows-Neovim.

1. „NVDA-Menü → Optionen → Einstellungen… → Neovim Access Link“ öffnen.
2. Auf der Seite „Connections“ „Add connection“ wählen.
3. Einen verständlichen Namen, Server oder SSH-Alias, Linux-Benutzernamen und
   SSH-Port eintragen.
4. Als Anmeldeart möglichst „Use OpenSSH setup“ wählen. Dann gelten die normale
   SSH-Konfiguration, Schlüssel und `ssh-agent`.
5. Alternativ „Ask for the SSH password“ wählen. Das Passwort wird nur für die
   aktuelle NVDA-Laufzeit verwendet und nicht gespeichert.
6. Die Einstellungen speichern und danach die Komponenten für diese Verbindung
   wie in Abschnitt 4 installieren.

Vor dem ersten Add-on-Test sollte eine normale Anmeldung in Windows Terminal
funktionieren, beispielsweise:

```text
ssh benutzer@example.invalid
```

## 6. Erste lokale Verbindung

1. In Windows Terminal `nvim.exe` starten.
2. Die selbst festgelegte Aktivierungstaste drücken.
3. Die Meldung abwarten, dass die Verbindungen bereit sind.
4. Das gewünschte Neovim fokussieren und F12 genau einmal drücken.
5. Bis zu zwei Sekunden auf die Verbindungsbestätigung warten.

Das lokale Plugin öffnet selbst einen dynamischen Port ausschließlich auf
`127.0.0.1`. Ein fester Port, `nvim --listen`, ein Wrapper oder ein manuell
gestarteter Hilfsprozess ist nicht erforderlich.

## 7. Erste SSH-Verbindung

1. Im gewünschten Windows-Terminal-Tab normal per SSH anmelden.
2. Optional tmux starten.
3. Auf dem Linux-Rechner Neovim starten.
4. Die Aktivierungstaste drücken und die Bereitschaftsmeldung abwarten.
5. Das gewünschte Neovim fokussieren und F12 einmal drücken.

Die sichtbare SSH-Sitzung bleibt unverändert. Das Add-on öffnet zusätzlich eine
unsichtbare SSH-stdio-Verbindung zur installierten Bridge. Es liest weder den
Fenstertitel noch den Terminalinhalt, um Server oder Neovim zu erraten.

## 8. Mehrere Fenster, Tabs, Panes und Sitzungen

Jedes Windows-Terminal-Control wird getrennt zugeordnet. Ein Control entspricht
je nach Aufbau dem Inhalt eines Tabs oder Panes:

1. Zum noch unverbundenen Fenster, Tab oder Pane wechseln.
2. Im gewünschten Neovim F12 drücken. Bereits verbundene andere Controls laufen
   dabei weiter.

Zwischen bereits verbundenen Controls kann ohne erneutes F12 gewechselt werden.
Das Add-on lässt beim Wechsel zunächst die native Terminalausgabe aktiv und
übernimmt erst nach einer passenden Neovim-Fokusantwort wieder die strukturierte
Ausgabe. Ein nicht verbundenes Control bleibt vollständig im nativen NVDA-
Terminalverhalten. F12 prüft dort nur als ausdrückliche Benutzeraktion auf einen
frischen Neovim-Claim; ohne Treffer gibt es keine Bindung, keinen Dialog und
keine Unterdrückung.

Für mehrere Neovim-Instanzen mit gleichem Arbeitsverzeichnis kann vor dem Start
ein freiwilliger Name gesetzt werden:

```text
NVIM_NVDA_SESSION_NAME=Dokumentation nvim
NVIM_NVDA_SESSION_NAME=Programmierung nvim
```

Unter PowerShell lautet die entsprechende Form:

```powershell
$env:NVIM_NVDA_SESSION_NAME = "Dokumentation"
nvim.exe
```

Der Name dient nur der verständlichen Auswahl. Eine interne Sitzungs-ID muss
niemals eingegeben werden.

## 9. Tägliche Bedienung

Nach erfolgreicher Verbindung stammen Sprache und Braille aus strukturierten
Neovim-Ereignissen. Moduswechsel, Cursorbewegung, Bearbeitung, Auswahl,
Einrückung, Rechtschreibfehler und Neovims Standard-Vervollständigung können
dadurch unabhängig vom sichtbaren Terminalbild ausgegeben werden.

F12 ist kein Ein-/Ausschalter. Zum Beenden der Unterstützung wird erneut die
selbst festgelegte Aktivierungstaste verwendet. Bei Verbindungsverlust oder
Deaktivierung fällt NVDA automatisch auf die normale Terminalausgabe zurück.

## 10. Wenn keine Verbindung entsteht

In dieser Reihenfolge prüfen:

1. Läuft Neovim wirklich in Windows Terminal?
2. Wurde Neovim nach der Komponenteninstallation vollständig neu gestartet?
3. Kam vor F12 die Bereitschaftsmeldung?
4. Wurde F12 nur einmal gedrückt und anschließend kurz gewartet?
5. Funktioniert bei Linux die normale SSH-Anmeldung außerhalb des Add-ons?

Im lokalen Neovim zeigt folgender Befehl, ob das Plugin geladen wurde:

```vim
:echo exists(':NvimNvdaSessionName')
```

Die erwartete Ausgabe ist `2`. Bei einem anderen Wert die lokalen Komponenten
bei vollständig geschlossenem Neovim erneut installieren und Neovim neu
starten.

Für eine genauere Analyse den NVDA-Befehl „Neovim-Diagnosebericht kopieren“
ausführen. Die Standardgeste ist `NVDA+Alt+D`. Der Bericht entfernt Editortext
und Zugangsdaten, bevor er in die Zwischenablage kopiert wird.

Ausführliche Erklärungen und sämtliche Einstellungen stehen im separaten
[Handbuch](neovim-access-link-handbook-de.html).
