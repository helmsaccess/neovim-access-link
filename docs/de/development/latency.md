# Latenz

## Messmodell und Ziel

Messungen trennen Neovim-Callback bis Send, Transport, Parsing und Dispatch,
Aufruf der NVDA-Ausgabequeue und Gesamtpipeline. Sie verwenden monotone,
hochauflösende Uhren. Zeitstempel verschiedener Rechner werden ohne
Synchronisationsmodell nicht direkt voneinander abgezogen.

Das Ziel vom Neovim-Ereignis bis zum Speech-Aufruf lautet Median unter 20 ms,
p95 unter 40 ms und p99 unter 75 ms. Ein synthetischer Messwert belegt nur den
gemessenen Abschnitt; die praktische Wahrnehmung unter NVDA bleibt eine eigene
Prüfung.

## Nicht blockierender NVDA-Pfad

NVDAs Hauptthread wartet nie auf SSH, Socket-I/O, DNS, Reconnect,
Installation, Parsing oder Logging. Eingabe- und Regionscallbacks validieren
kleine unveränderliche Payloads und legen sie ohne Warten in begrenzte Queues.
Worker führen Transportzugriffe aus; Ergebnisse kehren über NVDAs
Ereignisqueue zur Präsentation zurück.

Eine volle oder geschlossene Queue, ein veraltetes Ergebnis oder ein
Fokuswechsel verwirft eine optionale Steueraktion fail-open. Beim Loslassen
einer Explorationstaste verwendet die Ausgabe bereits vorhandenen kanonischen
Zustand und wartet nicht auf einen Roundtrip.

## Begrenzte Hochfrequenzpfade

- Cursor-, Text- und UI-Ereignisse dürfen nur zusammengefasst werden, wenn
  Reihenfolge, Sitzungsidentität und neuester semantischer Zustand erhalten
  bleiben. Eine Sequenzlücke fordert `fullState` an.
- Dateimanager-Renderereignisse und synchrone Aktionsresultate werden innerhalb
  genau eines Neovim-Schedulerzyklus zusammengefasst. Es gibt keine
  periodische Datei- oder Adapterabfrage.
- Externe Dateimanager-Detektoren besitzen ein Budget von 5 ms. Wiederholte
  Fehler oder Überschreitungen aktivieren eine bufferlokale, ereignisgetriebene
  Abkühlung.
- Der Oil-Bestätigungsfallback liest nur bei vorhandenen Ereignissen und
  höchstens 200 Bufferzeilen.
- Sprachexploration begrenzt Antworten auf 16 KiB, Wortsuche auf 256 Zeilen
  beziehungsweise 64 KiB und Wiederholung auf 64 Schritte.
- Braille-Routing, Braille-Zeilennavigation und Braille-Exploration verwenden
  denselben begrenzten Control-Dispatcher. Übersetzung und Planung auf NVDAs
  Hauptthread führen kein Transport-I/O aus.

Die erste Routingbetätigung bleibt unmittelbar. Nur wenn konfigurierte Doppel-
und Dreifachaktionen unterschieden werden müssen, hält `core.callLater` einen
bereits lokal geplanten Auftrag bis zum Ablauf von NVDAs
Mehrfachbetätigungsfrist zurück. Der Callback schläft nicht und führt kein I/O
aus.

## Reproduzierbare Messungen

`tools/latency/serialization_benchmark.py` vergleicht MessagePack und kompaktes
JSON mit einem repräsentativen Zustandsereignis:

```bash
python3 tools/latency/serialization_benchmark.py
```

Ergebnisse werden nur zusammen mit Plattform, Versionen, Transport, Workload,
Stichprobenzahl, Perzentilen und Fehlern interpretiert. Die Mikrobenchmarks,
die zur ursprünglichen Wahl des semantischen Lua-Pfads führten, bleiben als
Entscheidungskontext in [ADR-0001](adr/0001-neovim-integration-point.md).

## Praktische Abnahme

Vor einer Veröffentlichung werden wahrgenommene Navigation, Completion,
Diagnoseausgabe, lokale Verbindungen und SSH-Verbindungen unter NVDA geprüft.
Die automatisierten Tests sichern Nichtblockierung, Begrenzungen, Korrelation
und Rückfallpfade; sie ersetzen keine praktische Prüfung von Sprachsynthese,
Braillehardware oder realer Netzwerklatenz.
