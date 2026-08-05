# LSP, Autovervollständigung und Linter einrichten

Neovim Access Link macht die Informationen zugänglich, die Neovim bereits von
Sprachservern und Lintern erhält. Das Add-on installiert diese Werkzeuge nicht.

- Ein **Sprachserver (LSP)** liefert unter anderem Vervollständigungen,
  Funktionssignaturen, Hovertexte, Definitionen und Diagnosen.
- Ein **Linter** meldet zusätzliche Fehler, Warnungen oder Stilprobleme. Er ist
  optional, wenn die Diagnosen des Sprachservers genügen.
- Die **Neovim-Konfiguration** startet die Werkzeuge. Access Link liest die
  Ergebnisse über Neovims öffentliche LSP- und Diagnose-APIs.

Sprachserver und Linter laufen auf demselben Rechner wie Neovim:

| Neovim läuft | Werkzeuge installieren auf |
|---|---|
| lokal als `nvim.exe` in Windows Terminal | Windows |
| nach einer SSH-Anmeldung | dem Linux-Ziel |
| in tmux auf dem Linux-Ziel | dem Linux-Ziel |

Ein auf Windows installiertes Pyright steht einem entfernten Linux-Neovim nicht
zur Verfügung. Öffnen Sie das Terminal nach einer Installation neu, damit ein
geänderter `PATH` wirksam wird.

## Access-Link-Plugin und Plugin-Manager

Der Komponentenbefehl des Add-ons installiert das Access-Link-Plugin bereits.
Installieren Sie keine zweite Kopie aus einem Plugin-Repository und laden Sie es
nicht zusätzlich mit `require()`.

Eine unveränderte oder einfache Neovim-Konfiguration lädt die installierte Kopie
als Start-Paket. Ein Plugin-Manager, der `packpath` oder das Laden von
Start-Paketen ersetzt, muss stattdessen genau diese lokale Kopie registrieren.
Das Kapitel [Kleine Python-Konfiguration mit Lazy und Oil](example-configuration.md)
zeigt diesen Sonderfall für `lazy.nvim`.

Prüfen Sie nach einem Neovim-Neustart, ob das Plugin geladen ist:

```vim
:echo exists(':NvimNvdaSessionName')
```

Die Ausgabe `2` bestätigt den geladenen Befehl.

## Empfohlener Einsteigerweg für Python

Das folgende Beispiel verwendet Neovim 0.12, Git, Pyright und Ruff. Access Link
unterstützt Neovim ab 0.10.1; die kurze Konfiguration mit `vim.pack` und
`vim.lsp.enable` setzt jedoch die neuere Neovim-API voraus.

Prüfen Sie zuerst:

```text
nvim --version
git --version
```

### Werkzeuge installieren

Unter Windows mit PowerShell und WinGet:

```powershell
winget install --id Neovim.Neovim -e
winget install --id Git.Git -e
winget install --id OpenJS.NodeJS.LTS -e
npm install --global pyright
```

Installieren Sie Ruff nach der
[offiziellen Ruff-Anleitung](https://docs.astral.sh/ruff/installation/), zum
Beispiel mit `pipx install ruff`, wenn `pipx` eingerichtet ist.

Unter Debian oder Ubuntu:

```bash
sudo apt update
sudo apt install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

Unter Fedora:

```bash
sudo dnf install neovim git nodejs npm pipx
npm install --global pyright
pipx install ruff
pipx ensurepath
```

Distributionspakete enthalten teilweise eine ältere Neovim-Version. Prüfen Sie
`nvim --version` und verwenden Sie für dieses Beispiel Neovim 0.12. Prüfen Sie
anschließend im selben Terminal:

```text
pyright --version
ruff --version
```

PowerShell zeigt den gefundenen Server mit `Get-Command pyright-langserver`.
Unter Linux verwenden Sie `command -v pyright-langserver`.

### init.lua anlegen

Neovims Hauptkonfiguration liegt üblicherweise hier:

| System | Datei |
|---|---|
| Windows | `%LOCALAPPDATA%\nvim\init.lua` |
| Linux, auch über SSH | `~/.config/nvim/init.lua` |

Sichern Sie eine vorhandene Konfiguration. Wenn bereits ein Plugin-Manager oder
eine LSP-Einrichtung vorhanden ist, übernehmen Sie nur die benötigten Teile und
starten Sie denselben Sprachserver nicht mehrfach.

Die folgende minimale `init.lua` installiert `nvim-lspconfig` und `nvim-lint`,
startet Pyright, aktiviert Neovims eingebaute Vervollständigung und führt Ruff
nach dem Speichern einer Python-Datei aus:

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

`vim.pack.add` lädt die beiden fehlenden Plugins beim ersten Start. Beenden Sie
Neovim nach dem Speichern vollständig, starten Sie es neu und öffnen Sie eine
Python-Datei im Stammordner eines kleinen Projekts.

Automatisches Linting führt Werkzeuge mit Ihren Benutzerrechten aus. Verwenden
Sie es nur in vertrauenswürdigen Projekten. Einige Linter bevorzugen bewusst
eine ausführbare Datei aus dem aktuellen Projekt.

## Einrichtung prüfen

Die Beispielkonfiguration belegt die Tastenfolge `Leertaste`, `l`, `s` mit dem
LSP-Status. Drücken Sie die drei Tasten nacheinander. NVDA nennt den aktiven
Client, beispielsweise Pyright.

Die Folge ist ein **Neovim-Befehl ohne NVDA-Taste**: Neovim führt ihn aus,
Access Link macht das Ergebnis zugänglich. Kombinationen mit der NVDA-Taste
gehören dagegen zur Screenreader-Bedienung und werden nur im passenden,
verbundenen Neovim-Kontext von Access Link übernommen.

Wenn kein Client aktiv ist, prüfen Sie:

1. `pyright-langserver` wird auf dem Rechner gefunden, auf dem Neovim läuft.
2. Die geöffnete Datei besitzt den Dateityp `python`.
3. Neovim wurde nach der Installation neu gestartet.
4. Neovim wurde im Projektordner geöffnet.
5. Eine vorhandene Konfiguration startet keinen zweiten, widersprüchlichen
   Client.

Für technische Details zeigt `:checkhealth vim.lsp` Neovims eigenen LSP-Status.

## Completion und Diagnosen verwenden

Die Beispielkonfiguration verwendet folgende Neovim-Tasten ohne NVDA-Taste:

| Taste oder Folge | Aufgabe |
|---|---|
| `Ctrl+Leertaste` | Completion im Insert-Modus anfordern |
| `Ctrl+N` / `Ctrl+P` | nächsten / vorherigen Eintrag auswählen |
| `Ctrl+Y` / `Ctrl+E` | Auswahl übernehmen / Menü schließen |
| `[d` / `]d` | vorherige / nächste Diagnose |
| `[D` / `]D` | erste / letzte Diagnose |
| `Leertaste`, `d`, `d` | Diagnose an der aktuellen Position ausgeben |
| `Leertaste`, `l`, `l` | Ruff sofort ausführen |

Access Link spricht und zeigt die von Neovim gelieferten Informationen auf
Braille. Die vollständige Bedienung von Completion, Funktionssignaturen und
Diagnosen steht unter [Menüs, Completion und Diagnosen](menus-and-completion.md).

## Weitere Sprachen und vorhandene Plugins

Access Link verarbeitet gültige Completion-, LSP- und `vim.diagnostic`-Daten,
die Neovim bereitstellt. Für eine weitere Sprache installieren Sie den Server
nach dessen offizieller Anleitung und aktivieren den passenden
`nvim-lspconfig`-Namen. Beispiel:

```lua
vim.lsp.enable({ "pyright", "bashls", "gopls", "rust_analyzer" })
```

Unter anderem sind Pyright und Ruff praktisch geprüft. Weitere reale oder
isolierte automatisierte Prüfungen decken C/C++, Markdown, Shell, Go, Rust,
Ruby, Lua, PHP, JavaScript/TypeScript und Java ab. Das ist keine Garantie für
jede Werkzeugversion und Projektkonfiguration. Der aktuelle Prüfstand steht in
der [Kompatibilitätsübersicht](../development/compatibility.md).

Vorhandene Einrichtungen mit `nvim-cmp`, `blink.cmp`, ALE oder `none-ls.nvim`
können weiterverwendet werden, wenn sie ihre Ergebnisse über die von Access
Link unterstützten Neovim-Schnittstellen bereitstellen. Verwenden Sie für
denselben Buffer nur ein Completion-System und starten Sie denselben
Sprachserver nicht mehrfach.
