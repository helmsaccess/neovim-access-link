# Einstieg für Entwicklung und Tests

Dieses Dokument führt von einem neuen Checkout zur ersten sinnvollen Prüfung.
Wer das Projekt noch nicht kennt, beginnt mit dem
[Überblick](overview.md). Vor einer Architekturänderung sollte außerdem die
[Architektur](architecture.md) gelesen werden. Die Bedienung des installierten
Add-ons steht im [Anwenderhandbuch](../manual/README.md).

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
- ConfigObj 5.0.8 für die NVDA-kompatible Manifestprüfung im Add-on-Build;
- Pexpect 4.9.0 für die Bridge- und TUI-Integrationstests;
- Ruff 0.14.5 entsprechend NVDA 2026.1;
- Neovim für die echten Lua-Suiten;
- für die erweiterte reale Lintermatrix zusätzlich Go, Rust mit Clippy, Ruby
  und Node.js in den unter `testing.md` festgelegten Versionen;
- Pandoc für den HTML-Build; bestätigt ist 3.1.11.1;
- Git für Diff- und Whitespace-Prüfungen.

Die allgemeinen Python-Abhängigkeiten des GitHub-Testworkflows stehen
versionsfest in `tools/requirements-ci.txt`; die Python-Werkzeuge der realen
Lintermatrix stehen getrennt in `tools/requirements-linter-ci.txt`. Deren
Go-, Rust-, Ruby- und Node-Abhängigkeiten werden im GitHub-Workflow ebenfalls
explizit versioniert.

NVDA selbst wird für die reinen Python- und Lua-Tests nicht importiert. Die
NVDA-nahen Tests verwenden kontrollierte Testdoubles und prüfen zusätzlich den
Inhalt des gebauten Add-ons.

## Erste Prüfung eines Checkouts

Für eine schnelle Rückmeldung ohne Paketbau und echte Listener:

```bash
tools/run_tests.py quick
```

Der normale vollständige, sandbox-taugliche Ablauf ist:

```bash
ruff check .
ruff format --check .
tools/run_tests.py all-safe
tools/run_tests.py ssh
python3 tools/build_nvda_addon.py
python3 tools/gettext_catalog.py check
tools/build_documentation.sh
git diff --check
```

Echte lokale Listener und Unix-Sockets benötigen eine geeignete Umgebung und
laufen deshalb separat:

```bash
tools/run_tests.py socket
```

`tools/run_tests.py all` führt die sandbox-taugliche, die simulierte SSH- und die
Socket-Phase nacheinander aus. Ohne Gruppenargument entspricht der Runner dem
Preset `safe`. `-j N` begrenzt die parallelen Prozesse; `--list` zeigt die
Auswahl ohne Ausführung.

| Gruppe oder Preset | Kompakter Zweck |
| --- | --- |
| `unit` | reine und mit Attrappen isolierte Python-Tests |
| `package` | gebautes Add-on, Paketinhalt und NVDA-Integrationsattrappen |
| `lua` | Headless-Neovim-Spezifikationen ohne Listener |
| `ssh` | simulierte SSH-Kommando-, Askpass- und Fehlerpfade, ohne echte Verbindung |
| `socket` | echte wegwerfbare TUI-, RPC-, TCP- und Unix-Socket-Fälle |
| `quick` | schnelle Rückmeldung; entspricht `unit` |
| `safe` | Standard ohne Argument: `quick`, `package` und `lua` |
| `all-safe` | vollständige listenerfreie Suite; Alias von `safe` |
| `all` | alle Gruppen in getrennten Phasen: `all-safe`, `ssh`, `socket` |

Der Add-on-Build ist selbst Teil der Prüfung: Pakettests untersuchen das
tatsächlich erzeugte Archiv und nicht nur den Quellbaum. Details zu Isolation,
Sandbox-Grenzen und den nachgewiesenen Eigenschaften stehen in
[testing.md](testing.md).

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

Die vollständige Zuordnung steht ebenfalls in [testing.md](testing.md). Ein
einzelner grüner Test ist keine Freigabe für andere Komponenten oder
Plattformen.

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
