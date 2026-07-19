# Repository-Struktur

Die Verzeichnisse folgen Laufzeit- und Vertrauensgrenzen. Sie sind nicht alle
eigene Programme: Zur Laufzeit existieren ein Neovim-Prozess, bei SSH zusätzlich
ein Bridge-Prozess und unter Windows der NVDA-Prozess. `protocol/python/` und
`nvda-addon/core/` sind gemeinsam verwendete Bibliotheksschichten.

## Quellbereiche und Einstiegspunkte

| Pfad | Verantwortung | Wichtige Einstiegspunkte |
| --- | --- | --- |
| `neovim-plugin/` | Neovim-Zustand, semantische Ereignisse, Sitzungsdateien und Pluginadapter | `plugin/nvim_nvda.lua`, `lua/nvim_nvda/init.lua`, `lua/nvim_nvda/session.lua`, `lua/nvim_nvda/state.lua` |
| `bridge/python/` | Verbindung genau einer entfernten Linux-Neovim-Sitzung mit SSH-stdin/stdout | `nvim_nvda_bridge/__main__.py`, `bridge.py`, `session_registry.py`, `stdio.py` |
| `protocol/python/` | MessagePack-Framing, Nachrichtenvalidierung, Sequenzierung sowie lokale und SSH-Clients | `codec.py`, `messages.py`, `session.py`, `nvim_rpc.py`, `local_client.py`, `stdio_client.py` |
| `nvda-addon/core/` | NVDA-unabhängige Verbindungsmodelle und -koordination, Dienstregistrierung, Gate, Discovery sowie Sprach- und Brailleplanung | `connection_coordinator.py`, `service_registrar.py`, `gate.py`, `connection_instances.py`, `speech.py`, `braille.py` |
| `nvda-addon/addon/` | NVDA-Global-Plugin, Windows-Terminal-AppModule, UI- und Präsentationsdienste, Ressourcen und Übersetzungskataloge | `globalPlugins/NeovimAccessLink/__init__.py`, `globalPlugins/NeovimAccessLink/nvda_ui.py`, `globalPlugins/NeovimAccessLink/nvda_presentation.py`, `appModules/windowsterminal.py` |
| `packaging/` | rootlose Installation der Linux-Benutzerkomponenten | `install_user.py` |
| `tools/` | reproduzierbare Paket-, Dokumentations-, Katalog- und Testwerkzeuge | `build_nvda_addon.py`, `build_user_package.py`, `build_documentation.sh`, `test_neovim_plugin.sh` |
| `docs/de/manual/` | deutsche Anwenderdokumentation | `README.md`, `quick-guide.md` |
| `docs/de/development/` | deutsche Entwicklererklärung, Referenz und Nachweise | diese Datei und die Übersicht `README.md` |
| `docs/en/` | englische Anwender- und Entwicklerdokumentation | `README.md` |

Die ausführliche Beziehung dieser Bereiche erklärt die
[Architektur](architecture.md). Insbesondere darf NVDA-spezifischer Code nicht
in den Sprachplaner oder das Transportprotokoll wandern.

## Quellen, Paketlayout und erzeugte Ergebnisse

`buildVars.py` ist die einzige gepflegte Quelle für Produkt-ID, numerische
Store-Version, branchlokale Entwicklungsbuildnummer, Autor und unterstützte
NVDA-Versionen.

Der Add-on-Build kopiert die gepflegten Python-Module aus `protocol/python/`
und `nvda-addon/core/` unter das Global Plugin. Das Layout in einer gebauten
`.nvda-addon` ist deshalb bewusst anders als das Entwicklungs-Repository. Das
Linux-Benutzerpaket wird ebenfalls während des Builds aus Bridge, Protokoll,
Plugin und Installer erzeugt und anschließend als Ressource in das Add-on
eingebettet. Änderungen gehören immer in die oben genannten Quellverzeichnisse,
nicht in einen entpackten Build.

Erzeugte oder private Dateien haben feste Orte:

- `dist/`: installierbare, eindeutig versionierte Pakete;
- `build/`: erzeugte HTML-Dokumentation und andere reproduzierbare Ergebnisse;
- `tmp/`: lokale, private und kurzlebige Untersuchungen.

Diese Verzeichnisse sind keine alternativen Quellen der Wahrheit.

## Wo Tests liegen

- `neovim-plugin/tests/` prüft Lua-Zustand und echte Headless-Neovim-Abläufe.
- `protocol/python/tests/` prüft Nachrichten, Framing, Sequenzen und Clients.
- `bridge/python/tests/` prüft Discovery, RPC-Bridge und stdio-Transport.
- `nvda-addon/tests/` prüft Core, Speech/Braille, Paketinhalt und NVDA-nahe
  Adapter mit Testdoubles.

Die Auswahl und Ausführung der Suiten steht in [testing.md](testing.md).

## Namen und Dokumentationsorte

Öffentliche Community-Dateien verwenden die von GitHub erkannten Namen
`README.md`, `LICENSE`, `CONTRIBUTING.md` und `SECURITY.md`. Vorlagen liegen
unter `.github/`. Neue Python- und Lua-Dateien verwenden grundsätzlich
`snake_case`, Dokumente `lowercase-kebab-case`. `buildVars.py` behält den Namen
der offiziellen NVDA-Add-on-Vorlage und ist die begründete Ausnahme.

Dauerhafte Entscheidungen gehören in die sprachlich passende ADR-Struktur
unter `docs/de/development/adr/` beziehungsweise
`docs/en/development/adr/`. Der verifizierte Ist-Stand gehört in
`current-status.md`, reproduzierbare Nachweise in `testing.md` und historische
Änderungen in `changelog.md`.
