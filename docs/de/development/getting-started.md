# Einstieg für Entwicklung und Tests

Dieses Dokument führt von einem neuen Checkout zur ersten sinnvollen Prüfung.
Vor einer Architekturänderung sollte zuerst die [Architektur](architecture.md)
gelesen werden. Die Bedienung des installierten Add-ons steht im
[Anwenderhandbuch](../manual/README.md).

## Was tatsächlich läuft

Zur Laufzeit sind höchstens drei Prozesse beteiligt:

1. Neovim lädt das Lua-Plugin.
2. Bei einer entfernten Linux-Sitzung verbindet eine Python-Bridge genau diese
   Neovim-Instanz mit SSH-stdin/stdout. Lokal unter Windows entfällt sie.
3. NVDA lädt das Global Plugin und – nur für Windows Terminal – das AppModule.

Protokoll, Verbindungsmodelle sowie Sprach- und Brailleplanung sind
Bibliotheken innerhalb dieser Prozesse, keine weiteren Dienste. Die
[Repository-Struktur](repository-layout.md) ordnet die Quellpfade zu.

## Laufzeitvoraussetzungen

Für den Windows-Betrieb werden Windows 11, NVDA 2026.1.x, Windows Terminal und
entweder lokales Neovim oder Windows OpenSSH benötigt.

Ein entferntes Linux-Ziel benötigt Neovim 0.10.1 oder einen nachweislich
kompatiblen neueren Stand, `python3`, einen erreichbaren SSH-Dienst und ein
beschreibbares Benutzerverzeichnis unter `~/.local`. Das installierte Paket
bringt MessagePack selbst mit. Auf dem Ziel sind daher weder
`python3-msgpack`, `pynvim`, Root-Rechte noch ein Internetdownload erforderlich.

Die derzeit bestätigte Umgebung steht in [compatibility.md](compatibility.md).
Sie ist ein Testnachweis und keine pauschale Aussage über jede neuere oder
ähnliche Plattform.

## Entwicklungswerkzeuge

Für die vollständige lokale Prüfung werden benötigt:

- Python 3;
- `msgpack` exakt in Version 1.1.1 für Protokolltests und Paketbau;
- ConfigObj für die NVDA-kompatible Manifestprüfung im Add-on-Build; die
  bestätigte Umgebung verwendet 5.0.8;
- Neovim für die echten Lua-Suiten;
- Pandoc für den HTML-Build; bestätigt ist 3.1.11.1;
- Git für Diff- und Whitespace-Prüfungen.

NVDA selbst wird für die reinen Python- und Lua-Tests nicht importiert. Die
NVDA-nahen Tests verwenden kontrollierte Testdoubles und prüfen zusätzlich den
Inhalt des gebauten Add-ons.

## Erste Prüfung eines Checkouts

Zuerst die NVDA-unabhängigen Python-Suiten ausführen:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
python3 -m unittest discover -s protocol/python/tests
python3 -m unittest discover -s bridge/python/tests
python3 -m unittest discover -s nvda-addon/tests
```

Danach die Lua-Spezifikationen mit einem echten Headless-Neovim ausführen:

```bash
tools/test_neovim_plugin.sh
```

Für Änderungen an Paket, Metadaten, Übersetzungen oder Dokumentation außerdem:

```bash
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
git diff --check
```

Der Add-on-Build ist selbst Teil der Prüfung: Pakettests müssen das erzeugte
Archiv untersuchen und dürfen sich nicht nur auf den Quellbaum verlassen.

## Wo eine Änderung beginnt

| Aufgabe | Zuerst ansehen | Mindestens passende Prüfung |
| --- | --- | --- |
| Neovim-Ereignis oder Moduserkennung | `neovim-plugin/lua/nvim_nvda/init.lua`, `state.lua` | betroffene Lua-Spezifikation und Speech-Regression |
| Nachrichtenfeld oder Steuerbefehl | `protocol/python/nvim_nvda_protocol/`, `protocol.md` | Protokoll-, Bridge- und Add-on-Tests |
| SSH-Discovery oder Bridge | `bridge/python/nvim_nvda_bridge/`, `ssh_sessions.py` | Bridge-, Protokoll- und Security-Tests |
| lokale Windows-Sitzung | `session.lua`, `local_sessions.py`, `local_client.py` | lokale Lua-, Protokoll- und Add-on-Tests |
| Fokus, WT-Zuordnung oder Unterdrückung | `appModules/windowsterminal.py`, `gate.py`, Global Plugin | Gate-, Isolation-, Paket- und praktische WT-Negativtests |
| Sprache, Braille oder Klänge | `speech.py`, `braille.py`, `globalPlugins/NeovimAccessLink/nvda_presentation.py` | Planer-, Unicode-, Paket- und praktische NVDA-Tests |
| Einstellungen oder Werkzeugdialoge | `globalPlugins/NeovimAccessLink/nvda_ui.py` und `settings-reference.md` | Einstellungs-, Lokalisierungs- und Pakettests |
| Installation oder Build | `tools/`, `packaging/`, Installerklassen | gebautes Add-on, Installations- und Archivtests |

Die vollständige Zuordnung steht in [testing.md](testing.md). Ein einzelner
grüner Test ist keine Freigabe für andere Komponenten oder Plattformen.

## Praktische Tests sicher durchführen

- Für erste Versuche einen Testbuffer und eine entbehrliche Testdatei verwenden.
- Bestehende tmux- oder Neovim-Sitzungen nicht für destruktive Tests beenden
  oder verändern.
- Lokale und entfernte Komponenten vor einem Test vollständig aktualisieren und
  Neovim danach neu starten.
- Neben dem Erfolgsweg immer prüfen, dass ein ungebundenes Windows-Terminal-
  Control normale NVDA-Ausgabe behält und ein Disconnect fail-open endet.
- Reale Hostnamen, Konten, Domains, Schlüsselpfade, Passwörter und Editorinhalt
  weder in Tests noch in versionierte Diagnosebeispiele übernehmen.

Vor einer Änderung anschließend den [aktuellen Status](current-status.md), die
betroffene Referenzseite und die zugehörigen ADRs lesen. Plan und Changelog
sind Kontext, aber kein Ersatz für Code und aktuelle Tests.
