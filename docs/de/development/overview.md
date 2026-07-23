# Überblick für neue Entwickler

Diese Seite vermittelt das Grundmodell von Neovim Access Link, ohne einzelne
Klassen oder Nachrichtenfelder zu erklären. Die
[Architektur](architecture.md) vertieft anschließend dieselben Bausteine in
derselben Reihenfolge.

## Welches Problem löst das Projekt?

Ein Terminal zeigt Zeichen auf einem Bildschirmraster. Daraus kann NVDA aber
nicht immer zuverlässig erkennen, ob Neovim gerade eine Zeile bearbeitet, ein
Menü geöffnet, eine Meldung ausgegeben oder den Modus gewechselt hat. Neovim
Access Link liest deshalb nicht hauptsächlich die sichtbare Terminalfläche.
Ein Plugin fragt Neovim direkt nach der Bedeutung des aktuellen Zustands und
sendet kleine semantische Ereignisse an das NVDA-Add-on.

So kennt das Add-on beispielsweise den Unterschied zwischen „Cursor bewegt“,
„Einfügemodus betreten“ und „Menüauswahl geändert“. Erst danach entscheidet es,
ob Sprache, ein Klang oder eine Brailleaktualisierung passend ist.

## Der Gesamtweg

Der normale Datenfluss lässt sich auf vier Schritte reduzieren:

```text
Neovim-Plugin
  → Verbindung und Protokollprüfung
  → geprüfter Editorzustand und Ausgabeplanung
  → NVDA-Ausgabe für das richtig zugeordnete Terminal-Control
```

1. **Das Neovim-Plugin beschreibt den Editor.** Es beobachtet Neovim-APIs und
   erzeugt Ereignisse mit Modus, Cursor, Zeile, Meldung, Menü oder anderem
   strukturierten Zustand.
2. **Die Verbindung transportiert nur erlaubte Nachrichten.** Lokal verbindet
   sich das Add-on direkt mit Neovim. Bei einer entfernten Linux-Sitzung
   vermittelt eine kleine Bridge über SSH. Protokollcode begrenzt und prüft
   die Daten in beiden Fällen.
3. **Der Add-on-Kern merkt und plant.** Er hält einen geprüften aktuellen
   Editorzustand und leitet daraus Ausgabepläne ab. Dieser Teil kennt weder
   Sprachsynthesizer noch die sichtbare Windows-Terminal-Oberfläche.
4. **Die NVDA-Schicht gibt nur im passenden Kontext aus.** Sie verbindet die
   Pläne mit NVDAs Sprache, Klängen und Braille. Ein Fokus-Gate stellt sicher,
   dass besondere Behandlung nur für die bestätigte Neovim-Zuordnung gilt.

Die Hauptrichtung verläuft von Neovim zu NVDA. Für wenige ausdrücklich
erlaubte Funktionen, etwa Zwischenablage- und Terminalsteuerung, gibt es einen
kleinen geprüften Rückkanal. Er ist keine frei zugängliche Neovim-RPC-Konsole.
Auch die Exploration verwendet diesen engen Rückweg: Das AppModule sendet nur
eine von sechs festen Lesebewegungen, und das Plugin liefert das Ergebnis einer
flüchtigen Position zurück, ohne den echten Editorcursor zu verändern.

## Lokal und entfernt unterscheiden sich nur auf dem Transportstück

| Variante | Weg bis zum Add-on | Was danach gleich ist |
| --- | --- | --- |
| Neovim unter Windows | Neovim-Plugin → lokaler, nur an Loopback gebundener RPC-Endpunkt → Add-on | Protokollprüfung, Editorzustand, Fokusprüfung und Ausgabeplanung |
| Neovim unter Linux | Neovim-Plugin → privater Unix-Socket → Python-Bridge → SSH-stdin/stdout → Add-on | Protokollprüfung, Editorzustand, Fokusprüfung und Ausgabeplanung |

Die Bridge wird also nur für die entfernte Strecke benötigt. Sie plant keine
Sprache und trifft keine Fokusentscheidung. Nach dem Transport durchlaufen
lokale und entfernte Ereignisse möglichst denselben Code.

## Windows Terminal als flexibler Arbeitsbereich

Windows Terminal kann mehrere Fenster öffnen. Jedes Fenster kann mehrere Tabs
enthalten, und ein Tab lässt sich horizontal oder vertikal in Panes teilen. Ein
Pane ist dabei praktisch ein eigenständiger Terminalbereich mit eigener Ein-
und Ausgabe. Ein ungeteilter Tab enthält einen solchen Bereich; ein geteilter
Tab enthält mehrere:

```text
Windows-Terminal-Fenster
├── Tab 1
│   └── ein Terminalbereich
└── Tab 2
    ├── linkes Pane: ein Terminalbereich
    └── rechtes Pane: ein weiterer Terminalbereich
```

Nur ein Terminalbereich hat jeweils den Tastaturfokus. Die Bereiche dürfen
völlig unterschiedliche Inhalte haben: eine gewöhnliche PowerShell, ein
lokales Neovim, eine SSH-Sitzung mit Neovim oder eine SSH-Shell ohne Neovim.
Auch mehrere Windows-Terminal-Fenster können gleichzeitig solche gemischten
Sitzungen enthalten.

Der Partytrick des Add-ons ist zugleich eine seiner praktischen Stärken: Jeder
Neovim-Bereich kann unabhängig mit seiner eigenen lokalen oder entfernten
Neovim-Sitzung verbunden werden. Beim Wechsel zwischen Fenstern, Tabs und
Panes aktiviert das Add-on genau den dazugehörigen Editorzustand. Bereiche
ohne Neovim behalten dagegen NVDAs normale Terminalunterstützung. So kann man
beispielsweise in einem geteilten Tab links in einem entfernten Neovim
arbeiten, rechts eine gewöhnliche Shell verwenden und in einem anderen Tab zu
einem lokalen Neovim wechseln.

Die Zuordnung hängt nicht vom aktuellen Neovim-Modus ab. Nach erfolgreicher
Verbindung bleibt sie beim Wechsel zwischen den semantisch unterstützten Modi
bestehen. Dazu gehören Normal, Insert, Replace, Visual als Zeichen-, Zeilen-
oder Blockauswahl, Operator-Pending, Kommandozeile, Terminal-Normal und die
direkte Terminaleingabe. Moduswechsel, Navigation und Bearbeitung werden
weiterhin aus Neovim-Ereignissen abgeleitet.

## Was mit der Zuordnung eines Controls gemeint ist

Die Neovim-Verbindung kennt Editorzustand, aber nicht automatisch den gerade
fokussierten Terminalbereich. Windows Terminal kennt den Fokus, aber nicht
zuverlässig die darin laufende Neovim-Instanz. Fenstertitel oder sichtbarer
Text wären dafür zu ungenau.

Windows Terminal stellt jeden dieser Bereiche über UI Automation als
konkretes `TermControl` bereit. Bei einem ungeteilten Tab entspricht es dessen
Terminalinhalt; bei einem geteilten Tab wird jedes Pane getrennt erkannt. Die
Zuordnung verbindet daher nicht pauschal ein ganzes Fenster oder einen ganzen
Tab, sondern genau dieses fokussierte Control mit genau einer
Neovim-Verbindung.

Die F12-Markierung verbindet dazu zwei Beobachtungen: Das AppModule erkennt das
fokussierte `TermControl`, während das Neovim-Plugin denselben physischen
Tastendruck in genau einer Sitzung registriert. Jedes weitere Neovim-Control
wird einmal auf dieselbe Weise zugeordnet. Danach hält das Add-on mehrere
Zuordnungen parallel im Arbeitsspeicher.

Bei jedem späteren Fokuswechsel muss die zugeordnete Sitzung ihren aktuellen
Kontext erneut bestätigen. Erst dann verwendet das Add-on ihre strukturierte
Ausgabe. So übernimmt weder ein Shell-Pane noch eine andere Neovim-Sitzung
versehentlich den Zustand des zuvor fokussierten Controls.

## Wie der NVDA-Teil aufgeteilt ist

Für das Grundverständnis genügen drei Rollen:

- Das Windows-Terminal-AppModule erhält die anwendungsspezifischen Fokus-,
  Terminal- und Eingabeereignisse. Es erkennt das konkrete Control und
  entscheidet, ob NVDA ein Ereignis normal weiterverarbeitet.
- Die gemeinsame Add-on-Laufzeit besteht einmal pro NVDA-Prozess. Sie setzt
  Einstellungen, Verbindungen und die übrigen Hilfsbereiche zusammen und baut
  sie beim Beenden geordnet ab.
- Kleine, getrennte Dienste erledigen jeweils eine Aufgabe, beispielsweise
  Verbindungen verwalten, Fokus bestätigen, Editorzustand aktualisieren oder
  Ausgabe an NVDA übergeben.

Das Global Plugin ist damit nur der prozessweite Einstieg für die gemeinsame
Laufzeit, nicht der allgemeine Bearbeiter aller Terminalereignisse. Diese
Aufteilung hält Windows-Terminal-Ereignisse, Netzwerk, Editorzustand und
NVDA-Ausgabe voneinander getrennt und macht die Teile unabhängig testbar.

## Was „fail open“ bedeutet

Das Add-on unterdrückt einen Teil der normalen Terminalausgabe nur, wenn
Verbindung, Authentifizierung, Zuordnung und Fokus bestätigt sind. Fehlt eine
dieser Voraussetzungen oder tritt ein Fehler auf, gibt das Fokus-Gate den
normalen NVDA-Terminalpfad frei. „Fail open“ bedeutet hier also: lieber NVDAs
gewöhnliche, möglicherweise ausführlichere Terminalausgabe als ein stilles
oder irrtümlich als Neovim behandeltes Terminal.

Netzwerk-, SSH-, Reconnect-, Parsing- und Installationsarbeit läuft außerdem
nicht auf NVDAs Hauptthread. Empfangsthreads rufen NVDA nicht direkt auf,
sondern reichen geprüfte Ereignisse an NVDAs Ereigniswarteschlange weiter.
Erst dort werden Editorzustand, Ausgabeplan und konkrete NVDA-Ausgabe
aktualisiert.

## Von dieser Übersicht ins Detail

Die weiteren Seiten vertiefen dieses Modell schrittweise:

1. [Architektur](architecture.md) beschreibt Prozesse und Datenwege,
   Verbindungslebenszyklus, Zuständigkeiten, Gate und Spezialfälle.
2. [Repository-Struktur](repository-layout.md) ordnet diese Bausteine den
   Quellverzeichnissen und Tests zu.
3. [Einstieg für Entwicklung und Tests](getting-started.md) führt durch einen
   Checkout und zeigt, wo typische Änderungen beginnen.
4. [Protokoll v2](protocol.md) und
   [Sicherheit und Datenschutz](security.md) erklären Nachrichtenvertrag und
   Vertrauensgrenzen.
5. [Funktionsmatrix](accessibility.md) und
   [Teststrategie](testing.md) verbinden sichtbares Verhalten mit den
   erforderlichen Nachweisen.

Detailseiten dürfen Begriffe präzisieren, sollen aber diesem Grundfluss und
den hier beschriebenen Zuständigkeitsgrenzen nicht widersprechen.
