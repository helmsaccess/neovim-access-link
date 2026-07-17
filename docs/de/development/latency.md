# Latenz

## Messdefinition

Getrennt gemessen werden Neovim-Callback bis Send, Transport, Parsing/Dispatch,
Speech-Queue-Aufruf und Gesamtpipeline. Monotone hochauflösende Uhren sind
Pflicht; Uhren verschiedener Rechner werden nicht ohne Synchronisationsmodell
direkt subtrahiert.

Ziele bis Speech-Aufruf: Median <20 ms, p95 <40 ms, p99 <75 ms.

## Vorläufige lokale Ergebnisse (2026-07-11)

| Modell | n | p50 | p95 | p99 | Maximum |
|---|---:|---:|---:|---:|---:|
| Lua-Zustandsaufnahme im Prozess | 10.001 | 1,19 µs | 4,63 µs | 8,68 µs | 70,95 µs |
| externer RPC-Snapshot, 6 Requests | 10.000 | 195,29 µs | 277,63 µs | 418,74 µs | 2.062,81 µs |
| hybrider Lua-Snapshot, 1 RPC-Request | 10.000 | 68,92 µs | 103,92 µs | 135,36 µs | 951,29 µs |

Der Test läuft headless auf dem lokalen Rocky-System. Er misst sechs Kernfelder
in einer Lua-Funktion, aber weder Socket-Senden noch Ereignisdispatch oder NVDA.
LAN-/SSH- und NVDA-Werte bleiben bis zum Zugriff auf das Zielsystem offen.

Der externe RPC-Test lief über SSH außerhalb der Sandbox auf demselben
Zielsystem. Die sechs synchronen Roundtrips sind ein konservativer Basisfall;
ein produktiver Client bündelt Aufrufe oder verwendet Push-Ereignisse.

Dateimanager-Renderereignisse werden ohne Warte-Timer innerhalb genau eines
Neovim-Schedulerzyklus zusammengefasst. Danach wird der aktive Adapterzustand
einmal gelesen und nur bei einer echten semantischen Änderung gesendet.
Inaktive Ziele werden vor und nach dem Schedulerwechsel verworfen. Es gibt
keine periodische Adapter- oder Dateisystemabfrage.
Synchrone Aktionsresultate desselben aktiven Ziels verwenden denselben
Schedulerzyklus zur Bündelung. Das ist kein Wartefenster: Nach Ablauf dieses
Zyklus wird sofort genau eine typisierte Sammelmeldung geplant.

## Serialisierung

| Format | n | Bytes | Encode Median | Decode Median |
|---|---:|---:|---:|---:|
| MessagePack | 100.000 | 289 | 2,83 µs | 3,59 µs |
| kompaktes JSON/UTF-8 | 100.000 | 353 | 10,71 µs | 10,64 µs |

CBOR wurde nicht gemessen, weil es eine weitere Python- und Lua-Abhängigkeit
erfordert. Direkte Neovim-RPC-Nachrichten verwenden MessagePack, sind aber kein
ausreichend eingeschränktes Protokoll für den Windows-Endpunkt.

## Push-Durchsatz

Der produktionsnahe Prototyp übertrug 10.000 Lua-`rpcnotify`-Ereignisse an den
Python-Bridgeclient in 316,68 ms (31.578 Ereignisse/s); ein Wiederholungslauf
erreichte 29.309 Ereignisse/s. Das ist ein Burst-Durchsatztest, keine
Einzelereignis-Latenzmessung. Er belegt ausreichende Reserve, ersetzt aber nicht
Queue-, SSH- und Speech-Latenzmessungen.
