# ADR-0001: Hybrider Neovim-Andockpunkt

- Status: akzeptiert
- Datum: 2026-07-11

## Kontext und Messung

| Modell | n | p50 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|---:|
| A: Lua-Zustandsaufnahme | 10.001 | 1,19 µs | 4,63 µs | 8,68 µs | 70,95 µs |
| B: externer Snapshot, 6 RPC-Requests | 10.000 | 193,25 µs | 281,80 µs | 456,42 µs | 3,88 ms |
| C: Lua-Snapshot, 1 RPC-Übergang | 10.000 | 68,92 µs | 103,92 µs | 135,36 µs | 951,29 µs |

C wurde konservativ als synchroner Request gemessen. Produktive Notifications
vermeiden den Request-Teil; diese Annahme wird bei der Integration geprüft.

## Entscheidung

Wir verwenden Modell C:

1. Ein kleines Lua-Plugin registriert Autocommands und Buffer-Callbacks, liest
   konsistente semantische Zustände und sendet gebündelte RPC-Notifications.
2. Eine externe Linux-Bridge registriert ihre RPC-Channel-ID beim Plugin,
   empfängt Push-Ereignisse und nutzt optional `nvim_ui_attach()` für
   Commandline, Meldungen und Completion.
3. Die Bridge führt Sequenzierung, Session-ID, Queue, Heartbeat, Framing und
   Resynchronisation aus. Sie lauscht für das eingeschränkte Protokoll nur auf
   Loopback.
4. NVDA verbindet sich über einen SSH-Local-Forward als Client. Der bestehende
   bidirektionale Stream trägt danach Linux→Windows-Push-Ereignisse.

## Begründung

A ist am schnellsten, würde jedoch Netzwerk und Reconnect in Neovims Prozess
ziehen. B isoliert Fehler gut, benötigt ohne Lua-Ereignisse mehrere Roundtrips
oder verliert Semantik. C bleibt weit unter dem Gesamtziel, erhält semantische
Daten und isoliert langsame Clients. Windows erhält keinen allgemeinen
Neovim-RPC-Zugang.

## Folgen

- Ein zusätzlicher Prozess und RPC-Kanal werden paketiert und überwacht.
- Lua wartet nie synchron auf Transport oder NVDA.
- UI- und semantische Ereignisse benötigen Deduplikation.
- Externe UI-Fähigkeiten für Meldungen und Popup-Menüs werden nur während eines
  registrierten, authentifizierten Bridge-Kanals angehängt. Vor der Verbindung
  und nach einer Trennung bleibt die native TUI zuständig, damit
  Wiederherstellungs- und Bestätigungsabfragen fail-open sichtbar bleiben.
- Reconnect registriert den Channel neu und fordert `fullState` an.
