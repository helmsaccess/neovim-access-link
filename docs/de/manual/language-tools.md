# LSP, Autovervollständigung und Linter einrichten

Neovim Access Link macht vorhandene LSP- und Diagnoseinformationen für NVDA
zugänglich. Es installiert aber weder Programmiersprachen noch Sprachserver
oder Linter. Für eine funktionierende Einrichtung werden deshalb drei Teile
benötigt:

1. Ein **Sprachserver** liefert beispielsweise Definitionen, Hovertexte,
   Funktionssignaturen, Autovervollständigung und oft auch Diagnosen.
2. Ein **Linter** prüft Quelltext auf zusätzliche Fehler, Warnungen oder
   Stilprobleme. Ein separater Linter ist optional, wenn die Diagnosen des
   Sprachservers bereits genügen.
3. Die **Neovim-Konfiguration** startet diese Werkzeuge und veröffentlicht ihre
   Ergebnisse über Neovims öffentliche LSP- und `vim.diagnostic`-APIs. Access
   Link liest genau diese öffentlichen Daten.

Das vom Add-on installierte Access-Link-Plugin darf nicht noch einmal in der
`init.lua` installiert oder mit `require()` geladen werden. Der
Komponentenbefehl des Add-ons richtet es bereits ein. Die folgenden Schritte
betreffen ausschließlich die Entwicklungswerkzeuge des Benutzers.

Wer statt `vim.pack` direkt eine kleine vollständige Konfiguration mit
`lazy.nvim`, Oil, Pyright und Ruff übernehmen möchte, kann nach den
Installationshinweisen mit dem nächsten Kapitel
[Kleine Python-Konfiguration mit Lazy und Oil](example-configuration.md)
fortfahren. Dort wird Access Link wegen Lazys veränderter Plugin-Suchpfade
ausdrücklich als bereits installiertes lokales Plugin geladen.

## Auf welchem Rechner werden die Werkzeuge installiert?

Sprachserver und Linter müssen auf demselben Rechner verfügbar sein, auf dem
Neovim läuft:

| Neovim wird gestartet als | Sprachserver und Linter installieren auf |
|---|---|
| lokales `nvim.exe` in Windows Terminal | Windows |
| `nvim` nach einer SSH-Anmeldung | dem Linux-Ziel innerhalb der SSH-Sitzung |
| `nvim` in tmux auf einem Linux-Ziel | dem Linux-Ziel, nicht auf Windows |

Ein auf Windows installiertes Pyright kann beispielsweise nicht von einem
entfernten Linux-Neovim gestartet werden. Nach einer Installation das
betroffene Terminal neu öffnen, damit ein geänderter `PATH` wirksam wird.

## Empfohlener Einsteigerweg

Die vollständige Beispielkonfiguration dieses Kapitels setzt Neovim 0.12 und
Git voraus. Access Link selbst unterstützt auch Neovim 0.10.1 und neuer; die
moderne, kurze `vim.pack`- und `vim.lsp.enable`-Konfiguration ist jedoch erst
mit neueren Neovim-Versionen verfügbar. Für eine neue Konfiguration ist ein
Update auf Neovim 0.12 einfacher und weniger fehleranfällig als eine parallele
Legacy-Anleitung.

Zuerst die Versionen im Terminal prüfen:

```text
nvim --version
git --version
```

Für das Python-Beispiel werden zusätzlich Node.js mit npm, Pyright und Ruff
benötigt. Folgende Befehle installieren die Basispakete. Bereits vorhandene
Pakete müssen nicht erneut installiert werden.

### Windows mit PowerShell und WinGet

```powershell
winget install --id Neovim.Neovim -e
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
npm install --global pyright
```

Ruff kann mit einem der in der
[offiziellen Ruff-Anleitung](https://docs.astral.sh/ruff/installation/)
beschriebenen Wege installiert werden. Wer `pipx` bereits eingerichtet hat,
kann beispielsweise `pipx install ruff` und danach einmalig `pipx ensurepath`
verwenden. Vor einem WinGet-Befehl lässt sich die aktuell verfügbare Paket-ID
mit `winget search ruff` prüfen. Das ist zuverlässiger, als eine möglicherweise
geänderte ID ungeprüft zu übernehmen.

### Debian oder Ubuntu

```bash
sudo apt update
sudo apt install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

### Fedora

```bash
sudo dnf install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

Distributionspakete können eine ältere Neovim-Version enthalten. Nach der
Installation deshalb noch einmal `nvim --version` prüfen und bei einer Version
vor 0.12 die [offiziellen Neovim-Releases](https://github.com/neovim/neovim/releases)
verwenden. Falls eine globale npm-Installation wegen der lokalen npm-Richtlinie
keine Berechtigung besitzt, die von Node.js beziehungsweise der Distribution
empfohlene benutzereigene npm-Konfiguration verwenden und nicht unbesehen mit
Administratorrechten fortfahren.

Die ausführbaren Programme müssen anschließend im selben Terminal gefunden
werden:

```text
pyright --version
ruff --version
```

Unter PowerShell zeigt `Get-Command pyright-langserver` den gefundenen Pfad;
unter Linux erfüllt `command -v pyright-langserver` denselben Zweck.

## Eine neue init.lua anlegen

Neovims Hauptkonfiguration heißt `init.lua`. Übliche Speicherorte sind:

| System | Datei |
|---|---|
| lokales Windows-Neovim | `%LOCALAPPDATA%\nvim\init.lua` |
| Linux-Neovim, auch über SSH | `~/.config/nvim/init.lua` |

Unter Windows kann der Ordner in PowerShell angelegt und die Datei direkt mit
Neovim geöffnet werden:

```powershell
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\nvim"
nvim "$env:LOCALAPPDATA\nvim\init.lua"
```

Unter Linux:

```bash
mkdir -p ~/.config/nvim
nvim ~/.config/nvim/init.lua
```

Eine vorhandene `init.lua` vorher sichern. Wer bereits einen Plugin-Manager
oder eigene LSP-Konfigurationen verwendet, übernimmt nur die passenden Teile
und installiert dieselben Plugins nicht ein zweites Mal.

## Vollständiges Minimalbeispiel für Python

Der folgende Inhalt kann als erste komplette `init.lua` verwendet werden. Er

- installiert beim ersten Start `nvim-lspconfig` und `nvim-lint` über Neovims
  eingebautes `vim.pack`;
- startet Pyright für Python-Dateien;
- aktiviert Neovims eingebaute LSP-Autovervollständigung;
- führt Ruff nach dem Speichern einer Python-Datei aus;
- legt praktische Tasten für LSP-Status, Linter und Diagnosen fest.

```lua
vim.g.mapleader = " "

vim.opt.completeopt = { "menu", "menuone", "noselect", "popup" }
vim.diagnostic.config({
  signs = true,
  underline = true,
  virtual_text = true,
  severity_sort = true,
  update_in_insert = false,
})

vim.pack.add({
  { src = "https://github.com/neovim/nvim-lspconfig" },
  { src = "https://github.com/mfussenegger/nvim-lint" },
})

-- nvim-lspconfig liefert die Serverkonfiguration; Pyright selbst muss im
-- PATH installiert sein.
vim.lsp.enable("pyright")

vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(event)
    local client = vim.lsp.get_client_by_id(event.data.client_id)
    local options = { buffer = event.buf, silent = true }

    vim.keymap.set("n", "K", vim.lsp.buf.hover, options)
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, options)

    if client and client:supports_method("textDocument/completion") then
      vim.lsp.completion.enable(true, client.id, event.buf, {
        autotrigger = true,
      })
      vim.keymap.set("i", "<C-Space>", vim.lsp.completion.get, options)
    end
  end,
})

local lint = require("lint")
lint.linters_by_ft = {
  python = { "ruff" },
}

vim.api.nvim_create_autocmd("BufWritePost", {
  callback = function()
    lint.try_lint()
  end,
})

vim.keymap.set("n", "<leader>ll", function()
  lint.try_lint()
end, { desc = "Linter jetzt ausführen" })

-- Diese Access-Link-Befehle vermeiden im Alltag Eingaben im Befehlsmodus.
vim.keymap.set("n", "[d", "<Cmd>NvimNvdaDiagnosticPrevious<CR>",
  { desc = "Vorherige Diagnose" })
vim.keymap.set("n", "]d", "<Cmd>NvimNvdaDiagnosticNext<CR>",
  { desc = "Nächste Diagnose" })
vim.keymap.set("n", "[D", "<Cmd>NvimNvdaDiagnosticFirst<CR>",
  { desc = "Erste Diagnose" })
vim.keymap.set("n", "]D", "<Cmd>NvimNvdaDiagnosticLast<CR>",
  { desc = "Letzte Diagnose" })
vim.keymap.set("n", "<leader>dd", "<Cmd>NvimNvdaDiagnosticCurrent<CR>",
  { desc = "Diagnose an der aktuellen Position" })
vim.keymap.set("n", "<leader>ls", "<Cmd>NvimNvdaLspStatus<CR>",
  { desc = "LSP-Status mit Access Link ausgeben" })
```

`vim.pack.add` lädt fehlende Plugins beim ersten Neovim-Start aus dem Internet.
Spätere normale Starts installieren sie nicht erneut. Aktualisierungen erfolgen
bewusst mit Neovims `:packupdate`-Ablauf. Für fremde oder nicht vertrauenswürdige
Quellprojekte sollte automatisches Linting abgeschaltet werden: Manche Linter,
beispielsweise ESLint, bevorzugen absichtlich eine ausführbare Datei aus dem
aktuellen Projekt und starten sie mit den Rechten des Benutzers.

Nach dem Speichern Neovim vollständig beenden und erneut starten. Der erste
Start kann wegen der beiden Plugin-Downloads länger dauern. Danach eine
Python-Datei innerhalb eines Projektordners öffnen.

## Prüfen, ob der Sprachserver läuft

Die Beispielkonfiguration belegt `Leertaste`, danach `l`, danach `s` mit dem
Access-Link-LSP-Status. NVDA sollte beispielsweise „Pyright“ melden. Die
Tasten werden nacheinander gedrückt, nicht gleichzeitig.

Für eine einmalige technische Fehlersuche kann außerdem in Neovims
Befehlsmodus `:checkhealth vim.lsp` verwendet werden. Häufige Ursachen für
einen fehlenden Client sind:

- `pyright-langserver` ist nicht im `PATH` des Rechners, auf dem Neovim läuft;
- die Datei hat nicht den erwarteten Dateityp;
- Neovim wurde vor der Installation nicht neu gestartet;
- der Sprachserver erwartet einen Projektordner oder eine Projektdatei;
- eine ältere `init.lua` startet einen zweiten, widersprüchlich konfigurierten
  Client.

Neovim erkennt ein Projekt gewöhnlich an Markern wie `.git`, `pyproject.toml`,
`package.json`, `go.mod` oder `Cargo.toml`. Für die ersten Versuche ist es am
einfachsten, Neovim im Stammordner eines kleinen Projekts zu starten.

## Autovervollständigung bedienen

Wenn ein angehängter Sprachserver Vervollständigung unterstützt, aktiviert die
Beispielkonfiguration Neovims eingebautes Menü. `autotrigger = true` bedeutet,
dass der Server das Menü an seinen vorgesehenen Auslösezeichen automatisch
öffnen darf. Das ist nicht zwingend jeder Tastendruck. `Ctrl+Leertaste` fordert
die Liste jederzeit manuell an.

| Taste im Insert-Modus | Wirkung |
|---|---|
| `Ctrl+Leertaste` | LSP-Vervollständigung manuell öffnen |
| `Ctrl+N` | nächsten Vorschlag wählen |
| `Ctrl+P` | vorherigen Vorschlag wählen |
| `Ctrl+Y` | gewählten Vorschlag übernehmen |
| `Ctrl+E` | Vervollständigung abbrechen |

Access Link spricht den gewählten Eintrag mit Position, Typ, Quelle und
vorhandenen Details. Nach dem letzten Kandidaten besitzt Neovims eingebautes
Menü absichtlich einen Zwischenschritt ohne Auswahl; ein weiterer Druck auf
`Ctrl+N` beginnt wieder beim ersten Eintrag.

Für lange Dokumentation kann unter „NVDA-Menü → Optionen → Tastenbefehle… →
Neovim Access Link“ dem Befehl „Dokumentation für den ausgewählten
Neovim-Completion-Eintrag oder LSP-Hover lesen“ eine eigene
NVDA-Tastenkombination zugewiesen werden. Die Navigation und Übernahme im Menü
bleiben dagegen normale Neovim-Tasten und benötigen keine NVDA-Zuweisung.

Weitere Completion-Plugins sind nicht nötig. Wer bereits `nvim-cmp` oder
`blink.cmp` verwendet, kann dessen vorhandene Tasten weiterverwenden; Access
Link enthält dafür Adapter. Nicht beide Plugins und Neovims native Completion
gleichzeitig neu einrichten, solange noch unklar ist, welcher Teil ein Problem
verursacht.

## Funktionssignaturen und Parameter abfragen

Im Einfügemodus spricht Access Link den jeweils aktiven Parameter automatisch,
sobald der Cursor in die Argumentliste eines Aufrufs gelangt. Nach einem Komma
folgt der vom Sprachserver ausgewählte nächste Parameter. Kehrt der Cursor in
ein bereits ausgefülltes früheres Argument zurück, wird dessen Parameter erneut
gesprochen; reine Bewegung innerhalb desselben Arguments bleibt still. Bei
verschachtelten Aufrufen gilt immer die innerste umschließende Funktion. Bei
mehreren Signaturen folgt die Ansage ausschließlich der vom Sprachserver
aktuell gewählten Signatur. Diese kurzen Hinweise sind bewusst reine Sprache:
Die Braillezeile bleibt beim Quelltext. Unter `NVDA-Menü → Optionen →
Einstellungen… → Neovim Access Link → Allgemein` lässt sich „Aktiven
Funktionsparameter beim Tippen automatisch ansagen“ profilabhängig abschalten.

Die automatische Zuordnung verwendet die strukturierte LSP-Signaturhilfe und
nicht die Anzahl sichtbarer Kommas. Dadurch bringen Zeichenketten,
verschachtelte Aufrufe und sprachspezifische Syntax die Parameterposition nicht
durcheinander. Gibt der Sprachserver keinen eindeutigen aktiven Parameter
zurück, bleibt Access Link sicherheitshalber still.

`NVDA+Leertaste` wird vom Windows-Terminal-Modul von Access Link nur in der
exakt aktiven, verbundenen Neovim-Pane übernommen und muss weder in NVDA noch
in Lua zugewiesen werden. In anderen Terminal-Panes und Anwendungen bleibt
NVDAs Standardfunktion von `NVDA+Leertaste` erhalten. Den Cursor auf den
Funktionsnamen oder auf die unmittelbar zugehörige öffnende oder schließende
Klammer des Aufrufs setzen, die Kombination drücken, nur die Leertaste
loslassen und die NVDA-Taste weiter halten:

| gehaltene Taste | Wirkung |
|---|---|
| `NVDA+h` / `NVDA+l` | vorherigen / nächsten Parameter der gewählten Signatur anzeigen |
| `NVDA+k` / `NVDA+j` | vorherige / nächste Signatur anzeigen |
| NVDA-Taste loslassen | vorübergehende Ansicht schließen |

Nach jedem Signaturwechsel beginnt die Parameterauswahl neu. Der erste Druck
auf `NVDA+h` oder `NVDA+l` nennt daher immer Parameter 1 der gewählten
Signatur; erst danach wird rückwärts beziehungsweise vorwärts geschaltet.

Diese Funktion benötigt Signaturhilfe vom Sprachserver. Wenn der Server nur
Hovertext, aber keine strukturierte Signaturhilfe liefert, kann Access Link
lediglich diesen unstrukturierten Text als Rückfall anzeigen.

Für die manuelle Abfrage gelten absichtlich eindeutige Cursorpositionen: Im
Normalmodus funktionieren Funktionsname sowie die direkt zugehörige öffnende
und schließende Klammer, nicht aber das Innere einer nichtleeren Argumentliste.
Im Einfügemodus funktionieren der Funktionsname und beide Klammern eines leeren
Aufrufs. Innerhalb einer nichtleeren Argumentliste übernimmt stattdessen die
oben beschriebene automatische Ansage des aktiven Parameters.

## Lintermeldungen bedienen

Pyright-Diagnosen erscheinen automatisch, sobald der Server sie veröffentlicht.
Ruff wird im Beispiel nach jedem Speichern ausgeführt. Mit `Leertaste`, `l`,
`l` kann Ruff zusätzlich manuell gestartet werden. Die Meldungen stammen
fertig vom Sprachserver oder Linter; Access Link lokalisiert Schweregrade und
Bedienelemente, übersetzt aber nicht den freien Meldungstext des Werkzeugs.

| Taste | Wirkung der Beispielkonfiguration |
|---|---|
| `[d` / `]d` | vorherige / nächste Diagnose, mit Umbruch |
| `[D` / `]D` | erste / letzte Diagnose |
| `Leertaste`, `d`, `d` | Diagnose an der aktuellen Position erneut ausgeben |
| `NVDA+Umschalt+Leertaste` aufrufen und NVDA halten | Diagnosen am Cursor und danach auf derselben Zeile untersuchen |
| dabei `NVDA+k` / `NVDA+j` | durch mehrere Diagnosen derselben Zeile schalten |

`NVDA+Umschalt+Leertaste` wird wie die Parameterabfrage nur im exakt aktiven
Neovim-Kontext übernommen. Dafür ist keine Lua-Funktion und keine eigene
NVDA-Zuweisung nötig. Die optionalen Lua-
Mappings benutzen bewusst Access-Links Diagnosebefehle: Dadurch bleiben auch
mehrere Meldungen verschiedener Provider an derselben Position einzeln
erreichbar. Fehler und Warnungen können Diagnoseklänge auslösen. Informationen
und Hinweise werden gesprochen und auf Braille angezeigt, besitzen aber
absichtlich keinen eigenen Diagnoseklang.

Wenn Pyright und Ruff dasselbe Problem melden, erscheinen zwei Diagnosen mit
unterschiedlicher Quelle. Das ist kein Verlust von Zuständen durch Access
Link. Bei störenden Doppelmeldungen die betreffende Regel in einem der beiden
Werkzeuge deaktivieren oder nur einen Diagnoseproduzenten verwenden.

## Weitere Sprachen hinzufügen

Für einen zusätzlichen Sprachserver genügen normalerweise zwei Schritte:

1. Die ausführbare Serverdatei nach ihrer offiziellen Anleitung installieren.
2. Den Konfigurationsnamen in `vim.lsp.enable` ergänzen.

Beispiel:

```lua
vim.lsp.enable({ "pyright", "bashls", "gopls", "rust_analyzer" })
```

Für zusätzliche Linter wird `linters_by_ft` erweitert. Nur tatsächlich
installierte Werkzeuge eintragen:

```lua
lint.linters_by_ft = {
  python = { "ruff" },
  c = { "clangtidy" },
  sh = { "shellcheck" },
  go = { "staticcheck" },
  rust = { "clippy" },
  lua = { "luacheck" },
  php = { "phpstan" },
  javascript = { "eslint" },
  typescript = { "eslint" },
  java = { "checkstyle" },
  markdown = { "markdownlint-cli2" },
}
```

Einige Werkzeuge benötigen zusätzlich eine Projektkonfiguration, zum Beispiel
ESLint eine `eslint.config.js`, Checkstyle eine Regeldatei und PHPStan eine
`phpstan.neon`. Ohne diese Datei kann der Prozess korrekt installiert sein und
trotzdem keine brauchbaren Ergebnisse liefern.

## Sprach- und Werkzeugübersicht

Access Link besitzt keine feste Liste erlaubter Programmiersprachen. Jeder
Provider sollte grundsätzlich funktionieren, wenn er gültige Daten über
Neovims LSP-Client oder `vim.diagnostic` veröffentlicht. Die folgende Tabelle
nennt verbreitete Kombinationen und den Namen für `nvim-lspconfig` sowie
`nvim-lint`.

| Sprache | verbreiteter LSP-Server / Konfigurationsname | mögliche `nvim-lint`-Namen | Stand der Access-Link-Prüfung |
|---|---|---|---|
| Python | Pyright / `pyright` | `ruff` | Pyright in Praxistests; Ruff real automatisiert und praktisch |
| C und C++ | clangd / `clangd` | `clangtidy` | Clang-Tidy real automatisiert und praktisch |
| Markdown | Marksman / `marksman` oder markdown-oxide / `markdown_oxide` | `markdownlint-cli2` | markdownlint real automatisiert und praktisch |
| Bash und POSIX-Shell | bash-language-server / `bashls` | `shellcheck` | ShellCheck real automatisiert |
| Go | gopls / `gopls` | `staticcheck` | Staticcheck real automatisiert |
| Rust | rust-analyzer / `rust_analyzer` | `clippy` | Clippy real automatisiert |
| Ruby | Ruby LSP / `ruby_lsp` | `rubocop` | RuboCop real automatisiert |
| Lua | Lua Language Server / `lua_ls` | `selene` oder `luacheck` | Provider- und Parserpfade automatisiert geprüft |
| PHP | Intelephense / `intelephense` oder Phpactor / `phpactor` | `phpstan` oder `phpcs` | Provider- und Parserpfade automatisiert geprüft |
| JavaScript und TypeScript | typescript-language-server / `ts_ls` | `eslint` | Provider- und Parserpfade automatisiert geprüft |
| Java | Eclipse JDT LS / `jdtls` | `checkstyle` | Checkstyle-SARIF und Diagnosepfad automatisiert geprüft |

„Grundsätzlich“ ist hier bewusst keine Garantie für jede Version und
Projektkonfiguration. Die realen automatisierten Läufe umfassen derzeit C,
Python, Bash, Go, Rust, Ruby und Markdown über `nvim-lint` und ALE. Bei Lua,
PHP, JavaScript und Java sind die öffentlichen Provider- und Parserverträge
abgedeckt, aber nicht jede externe Werkzeuginstallation in einer realen
Projektmatrix.

## Typische Installationsbefehle für weitere Werkzeuge

Die folgenden Beispiele installieren nur die externen Programme. In der
`init.lua` müssen anschließend weiterhin die passenden Namen aktiviert werden.

| Zweck | Windows | Debian/Ubuntu | Fedora |
|---|---|---|---|
| C/C++ mit clangd und Clang-Tidy | `winget install --id LLVM.LLVM -e` | `sudo apt install clangd clang-tidy` | `sudo dnf install clang-tools-extra` |
| ShellCheck | `winget install --id koalaman.shellcheck -e` | `sudo apt install shellcheck` | `sudo dnf install ShellCheck` |
| Go-Werkzeuge vorbereiten | `winget install --id GoLang.Go -e` | `sudo apt install golang-go` | `sudo dnf install golang` |
| Java-Laufzeit vorbereiten | mit `winget search Temurin` eine aktuelle JDK-ID wählen | `sudo apt install default-jdk` | `sudo dnf install java-21-openjdk-devel` |
| PHP und Composer vorbereiten | mit `winget search PHP` und `winget search Composer` aktuelle IDs wählen | `sudo apt install php-cli composer` | `sudo dnf install php-cli composer` |
| Lua und LuaRocks vorbereiten | mit `winget search Lua` und `winget search LuaRocks` aktuelle IDs wählen | `sudo apt install lua5.4 luarocks` | `sudo dnf install lua luarocks` |

Danach werden sprachspezifische Werkzeuge üblicherweise mit dem Paketmanager
der Sprache installiert:

```text
# Node-basierte Server und Werkzeuge
npm install --global bash-language-server
npm install --global typescript typescript-language-server
npm install --global markdownlint-cli2

# Go
go install golang.org/x/tools/gopls@latest
go install honnef.co/go/tools/cmd/staticcheck@latest

# Rust über eine vorhandene rustup-Installation
rustup component add rust-analyzer clippy

# Lua
luarocks install luacheck

# PHP innerhalb eines Projekts
composer require --dev phpstan/phpstan

# JavaScript oder TypeScript innerhalb eines Projekts
npm install --save-dev eslint
```

Für Rust ist [rustup](https://rustup.rs/) der offizielle Installationsweg. Der
Lua Language Server, Eclipse JDT LS, Marksman und andere eigenständig
veröffentlichte Server sollten nach ihrer jeweiligen Upstream-Anleitung
installiert werden. Vor dem Eintrag in `init.lua` immer prüfen, dass ihr
Startbefehl im Terminal gefunden wird. Die von `nvim-lspconfig` erwarteten
Befehle und Projektmarker stehen in Neovim unter `:help lspconfig-all`.

## Bestehende Completion- und Linter-Plugins

Access Link unterstützt neben Neovims eingebautem Menü ausdrücklich
`nvim-cmp` und `blink.cmp`. Diagnosen aus ALE und `none-ls.nvim` sind ebenfalls
zugänglich, sofern sie am Ende in `vim.diagnostic` stehen. Wer eines dieser
Systeme bereits erfolgreich verwendet, muss nicht auf das Minimalbeispiel
wechseln. Wichtig ist lediglich:

- nicht denselben Sprachserver mehrfach starten;
- nicht mehrere Completion-Systeme gleichzeitig auf dieselben Tasten legen;
- Linterergebnisse über `vim.diagnostic` veröffentlichen lassen;
- bei Fehlern zuerst mit genau einem Sprachserver, Neovims nativer Completion
  und einem Linter testen.

Die Bedienung und die von Access Link ausgegebenen Details beschreibt das
folgende Kapitel [Menüs und Autovervollständigung](menus-and-completion.md).
