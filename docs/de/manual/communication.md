# Verbindung, täglicher Einstieg und Sitzungswechsel

Installation, Aktivierung und Verbindung sind getrennte Schritte:

1. Der Komponentenbefehl installiert das Neovim-Plugin und bei Linux zusätzlich
   die Bridge.
2. Die selbst zugewiesene Aktivierungsgeste schaltet den Access-Link-Dienst ein
   und sucht erreichbare Sitzungen.
3. F12 ordnet das fokussierte Windows-Terminal-Control der gerade fokussierten
   Neovim-Sitzung zu.

Eine installierte Komponente ist daher noch keine laufende Verbindung.

## Aktivierung und F12

Die Aktivierungsgeste ist ein NVDA-Befehl und enthält üblicherweise die
NVDA-Taste oder eine andere im NVDA-Tastenbefehldialog zugewiesene Kombination.
NVDA führt ihn bei fokussiertem Windows Terminal aus.

F12 gehört zum normalen Tastaturpfad von Windows Terminal und Neovim. Access
Link blockiert die Taste nicht: Neovim erhält sie und markiert die aktuelle
Sitzung kurzzeitig. Anschließend verbindet Access Link genau diesen neuen
Treffer mit dem fokussierten Control. F12 schaltet das Add-on nicht ein oder
aus.

Drücken Sie F12 einmal und warten Sie auf die Bestätigung. Mehrere schnelle
Tastendrücke beginnen mehrere getrennte Auswahlversuche.

## Die erste Arbeitssitzung

Nach der Verbindung liefert Neovim den aktuellen Buffer, Modus, Cursor und
weitere semantische Zustände. Beginnen Sie in einem unwichtigen Buffer:

1. Drücken Sie `i`, schreiben Sie Text und drücken Sie `Esc`.
2. Navigieren Sie im Normalmodus mit `h`, `j`, `k` und `l`.
3. Speichern Sie mit `:w` oder `:w dateiname`.
4. Prüfen Sie Auswahl mit `v` und Navigation.
5. Wechseln Sie in eine andere Shell-Pane und zurück.
6. Drücken Sie die Aktivierungsgeste erneut, um Access Link zu deaktivieren.

`i`, `Esc`, `h`, `j`, `k`, `l`, `v` und `:w` sind Neovim-Befehle. Neovim
verändert damit Modus, Cursor, Auswahl oder Datei. Access Link macht diese
Änderungen zugänglich.

Tastenkombinationen mit NVDA-Taste gehören zur Screenreader-Ebene. Beispiele
sind `NVDA+h` für Sprachexploration und `NVDA+Alt+D` für den Diagnosebericht.
Access Link übernimmt diese Befehle nur im dokumentierten, exakt verbundenen
Neovim-Kontext.

## Zwischen Tabs und Panes wechseln

Ein Windows-Terminal-Pane ist ein eigenes Terminal-Control. Access Link führt
für jedes Control eine getrennte Zuordnung:

- Ein verbundenes Neovim-Pane erhält strukturierte Ausgabe.
- Ein unverbundenes Neovim-Pane bleibt bei NVDAs nativer Terminalausgabe, bis
  Sie dort F12 drücken.
- Ein Shell-Pane bleibt vollständig bei NVDAs nativer Terminalausgabe.
- Ein eingebetteter Neovim-Terminalbuffer verwendet während direkter Eingabe
  ebenfalls native Terminalausgabe.

Beim Fokuswechsel übernimmt Access Link eine vorhandene Zuordnung erst nach
einer passenden Antwort der zugeordneten Neovim-Sitzung. Bis dahin bleibt die
native Terminalausgabe aktiv. Dadurch erscheinen keine Zustände aus einem
zuvor fokussierten Pane.

## Weitere Sitzungen verbinden

Starten Sie Neovim in einem weiteren Fenster, Tab oder Pane und drücken Sie
dort F12. Bereits verbundene Controls bleiben aktiv. Lokale und entfernte
Sitzungen dürfen innerhalb desselben Windows-Terminal-Fensters gemischt sein.

Bei mehreren gleich benannten Sitzungen zeigt der manuelle Verbindungsdialog
Verbindungsname, Arbeitsverzeichnis und vorhandene Zuordnung. Für zusätzliche
Orientierung lässt sich vor dem Start ein Sitzungsname setzen:

```text
NVIM_NVDA_SESSION_NAME=Dokumentation nvim
```

In PowerShell:

```powershell
$env:NVIM_NVDA_SESSION_NAME = "Dokumentation"
nvim.exe
```

Der Name dient nur der Auswahl und ändert Neovims Arbeitsverzeichnis nicht.

## Zuordnung merken oder manuell wählen

Nach einer neuen F12-Zuordnung fragt Access Link, ob sie für den
Windows-Terminal-Tab bis zum Ende von NVDA oder Windows Terminal gemerkt werden
soll. Beim späteren Tabwechsel stellt Access Link die passende laufende Sitzung
nach bestätigtem Fokus wieder her.

Folgende frei belegbare Befehle stehen in
`NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link`:

- `Einen Server auswählen und dieses Terminal mit einer neuen Neovim-Sitzung verbinden`;
- `Ausgewählte Neovim-Verbindungsinstanz trennen`;
- `Temporäre Neovim-Verbindung für das fokussierte Terminal vergessen`.

Der erste Befehl öffnet den zugänglichen Auswahldialog, wenn F12 keinen
eindeutigen Treffer liefert. Trennen beendet die ausgewählte Access-Link-
Verbindung, nicht Neovim oder SSH. Vergessen entfernt nur die gemerkte
Tab-Zuordnung der aktuellen NVDA-Laufzeit.

## Lokale und entfernte Verbindung

Lokales Windows-Neovim verbindet sich ausschließlich über den lokalen Rechner.
Entferntes Neovim verwendet zwei unabhängige SSH-Verbindungen:

- Die sichtbare Windows-Terminal-Sitzung bleibt Ihre normale Shell und
  transportiert Ihre Tastatureingaben.
- Access Link öffnet im Hintergrund eine eigene SSH-Verbindung zur installierten
  Bridge und überträgt darüber ausschließlich begrenzte Barrierefreiheitsdaten.

Die Bridge öffnet keinen zusätzlichen Netzwerkdienst auf Linux. Access Link
speichert keine Passwörter. Ein Passwortprofil hält das Passwort nur während
der aktuellen NVDA-Laufzeit im Arbeitsspeicher.

## Verhalten bei Trennung oder Fehlern

Access Link unterdrückt native Terminalausgabe nur für eine aktive,
authentifizierte und fokussierte Neovim-Zuordnung. Bei Deaktivierung,
Transportende, ungültigen Daten, Fokusunsicherheit oder einem unbekannten
Control bleibt beziehungsweise wird NVDAs native Terminalausgabe aktiv.

Die Unterdrückung gilt nie für ein ganzes Windows-Terminal-Fenster. Ein Fehler
in einer Sitzung verändert keine andere Pane-Zuordnung.

Weitere Symptome und Prüfschritte stehen unter
[Fehlerdiagnose](troubleshooting.md). Die vollständige Tastenzuordnung steht in
der [Befehlsreferenz](commands.md).
