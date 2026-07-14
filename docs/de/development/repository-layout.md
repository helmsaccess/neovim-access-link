# Repository-Struktur

Die Verzeichnisse folgen den Laufzeitgrenzen des Produkts:

| Pfad | Inhalt |
| --- | --- |
| `neovim-plugin/` | Lua-Plugin, semantische Ereignisse, Sitzungsregistry und Adapter |
| `bridge/python/` | Verbindung einer Linux-Neovim-Sitzung mit SSH-stdio |
| `protocol/python/` | Framing, Validierung, Sequenzierung und Unicode-Hilfen |
| `nvda-addon/core/` | NVDA-unabhängige Verbindungs-, Zustands-, Sprach- und Braillelogik |
| `nvda-addon/addon/` | NVDA-Oberfläche, Windows-Terminal-AppModule und Paketressourcen |
| `packaging/` | rootloser Installer für Linux-Benutzerkomponenten |
| `tools/` | reproduzierbare Builds, Tests und Prüfwerkzeuge |
| `docs/de/manual/` | deutsche Anwenderdokumentation |
| `docs/de/development/` | Erklärung, Architektur, Referenz und Nachweise |
| `docs/en/` | englische Quick-Guide-, Handbuch- und Entwicklerquellen |

`buildVars.py` ist die einzige gepflegte Quelle für Produktname, Version,
Buildnummer, Autor und NVDA-Kompatibilitätsangaben.

## Quellen und Ergebnisse

Gepflegte Quellen und Markdown-Dokumente gehören in Git. Erzeugte oder private
Dateien haben feste Orte:

- `dist/`: installierbare, eindeutig versionierte Pakete;
- `build/`: erzeugte Dokumentation und andere reproduzierbare Ergebnisse;
- `tmp/`: lokale, private und kurzlebige Testunterlagen.

Diese Verzeichnisse sind keine alternativen Quellen der Wahrheit.

## Dateinamen und GitHub

Öffentliche Community-Dateien verwenden die von GitHub erkannten Namen
`README.md`, `LICENSE`, `CONTRIBUTING.md` und `SECURITY.md`. Vorlagen liegen
unter `.github/`. Neue Python- und Lua-Dateien verwenden grundsätzlich
`snake_case`, Dokumente `lowercase-kebab-case`. `buildVars.py` behält den Namen
der offiziellen NVDA-Add-on-Vorlage und ist die begründete Ausnahme.

## Architekturregel

Neue Transport- oder Frontendpfade erhalten eigene typisierte Adapter.
Dauerhafte Entscheidungen gehören in `docs/adr/`, der verifizierte Ist-Stand
in `current-status.md` und reproduzierbare Nachweise in `testing.md`.
