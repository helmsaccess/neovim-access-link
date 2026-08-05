# Kleine Python-Konfiguration mit Lazy und Oil

Dieses Kapitel bietet eine vollständige `init.lua` zum direkten Kopieren. Sie
eignet sich für Benutzer ohne umfangreiche vorhandene Neovim-Konfiguration und
enthält:

- `lazy.nvim` als Plugin-Manager;
- Oil als einfachen zugänglichen Dateimanager;
- Pyright als Python-Sprachserver;
- Neovims native LSP-Autovervollständigung;
- Ruff über `nvim-lint`;
- praktische LSP-, Linter- und Access-Link-Tasten.

Die allgemeine Funktionsweise, weitere Sprachen und alternative Einrichtung
mit `vim.pack` beschreibt das vorherige Kapitel
[LSP, Autovervollständigung und Linter einrichten](language-tools.md).

## Voraussetzungen installieren

Benötigt werden Neovim 0.12 oder neuer, Git, Node.js mit npm, Pyright, Ruff und
die durch das NVDA-Add-on installierten Access-Link-Komponenten. Oil,
`nvim-lspconfig` und `nvim-lint` lädt Lazy beim ersten Start selbst herunter.
Ein zusätzliches Python-Plugin für Neovim und ein Icon-Paket sind nicht nötig.

Die vollständigen WinGet-, apt- und dnf-Hinweise stehen im vorherigen Kapitel.
Vor dem Einrichten müssen diese Prüfungen im selben Terminal funktionieren, in
dem später Neovim läuft:

```text
nvim --version
git --version
pyright --version
ruff --version
```

Bei Neovim über SSH oder in tmux werden die Linux-Pakete auf dem Linux-Ziel
installiert. Eine Windows-Installation von Pyright oder Ruff ist für das
entfernte Neovim nicht sichtbar.

## Vorhandene Konfiguration sichern

Neovims Konfigurationsdatei liegt unter Windows in
`%LOCALAPPDATA%\nvim\init.lua` und unter Linux in
`~/.config/nvim/init.lua`. Eine vorhandene Datei zuerst sichern. Diese
Beispielkonfiguration ersetzt eine vorhandene `init.lua`; sie soll nicht
zusätzlich in eine bereits von LazyVim oder einem anderen Plugin-Manager
verwaltete Konfiguration kopiert werden.

Unter Windows kann die Datei so geöffnet werden:

```powershell
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\nvim"
nvim "$env:LOCALAPPDATA\nvim\init.lua"
```

Unter Linux:

```bash
mkdir -p ~/.config/nvim
nvim ~/.config/nvim/init.lua
```

## Vollständige init.lua

Den folgenden Inhalt vollständig übernehmen und speichern. Dieselbe geprüfte
Datei steht im
[GitHub-Repository](https://github.com/helmsaccess/neovim-access-link/blob/main/examples/neovim-lazy-python/init.lua).
Der Codeblock wird aus dieser echten Lua-Datei erzeugt und bleibt deshalb in
der GitHub-Ansicht und im gebauten Handbuch identisch mit der ausführbaren
Quelle.

<!-- BEGIN lazy-python-example -->
```lua
vim.g.mapleader = " "
vim.g.maplocalleader = "\\"

vim.opt.completeopt = { "menu", "menuone", "noselect", "popup" }
vim.opt.number = true
vim.opt.signcolumn = "yes"
vim.opt.updatetime = 300

vim.diagnostic.config({
  signs = true,
  underline = true,
  virtual_text = true,
  severity_sort = true,
  update_in_insert = false,
})

local uv = vim.uv or vim.loop
local data_path = vim.fn.stdpath("data")
local lazy_path = vim.fs.joinpath(data_path, "lazy", "lazy.nvim")

if not uv.fs_stat(lazy_path) then
  local output = vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "--branch=stable",
    "https://github.com/folke/lazy.nvim.git",
    lazy_path,
  })
  if vim.v.shell_error ~= 0 then
    error("Could not install lazy.nvim:\n" .. output)
  end
end

vim.opt.rtp:prepend(lazy_path)

local plugins = {
  {
    "stevearc/oil.nvim",
    lazy = false,
    opts = {
      columns = { "type", "size" },
      delete_to_trash = false,
      skip_confirm_for_simple_edits = false,
    },
    keys = {
      { "-", "<Cmd>Oil<CR>", desc = "Open parent directory" },
    },
  },
  {
    "neovim/nvim-lspconfig",
    lazy = false,
    config = function()
      vim.lsp.enable("pyright")
    end,
  },
  {
    "mfussenegger/nvim-lint",
    lazy = false,
    config = function()
      local lint = require("lint")
      lint.linters_by_ft = {
        python = { "ruff" },
      }

      local group = vim.api.nvim_create_augroup("example_python_lint", {
        clear = true,
      })
      vim.api.nvim_create_autocmd({ "BufReadPost", "BufWritePost" }, {
        group = group,
        pattern = "*.py",
        callback = function()
          lint.try_lint()
        end,
      })
    end,
  },
}

local access_link_path = vim.fs.joinpath(
  data_path,
  "site",
  "pack",
  "nvim-nvda",
  "start",
  "nvim-nvda"
)

if uv.fs_stat(access_link_path) then
  table.insert(plugins, 1, {
    dir = access_link_path,
    name = "nvim-nvda",
    lazy = false,
    priority = 1000,
  })
else
  vim.schedule(function()
    vim.notify(
      "Neovim Access Link plugin not found; install the add-on components first",
      vim.log.levels.WARN
    )
  end)
end

require("lazy").setup(plugins, {
  defaults = { lazy = false },
  install = { colorscheme = { "habamax" } },
  checker = { enabled = false },
})

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

vim.keymap.set("n", "<leader>ll", function()
  require("lint").try_lint()
end, { desc = "Run Python linter" })

vim.keymap.set("n", "[d", "<Cmd>NvimNvdaDiagnosticPrevious<CR>",
  { desc = "Previous diagnostic" })
vim.keymap.set("n", "]d", "<Cmd>NvimNvdaDiagnosticNext<CR>",
  { desc = "Next diagnostic" })
vim.keymap.set("n", "[D", "<Cmd>NvimNvdaDiagnosticFirst<CR>",
  { desc = "First diagnostic" })
vim.keymap.set("n", "]D", "<Cmd>NvimNvdaDiagnosticLast<CR>",
  { desc = "Last diagnostic" })
vim.keymap.set("n", "<leader>dd", "<Cmd>NvimNvdaDiagnosticCurrent<CR>",
  { desc = "Read diagnostic at cursor" })
vim.keymap.set("n", "<leader>ls", "<Cmd>NvimNvdaLspStatus<CR>",
  { desc = "Read LSP status" })
```
<!-- END lazy-python-example -->

## Warum Access Link ausdrücklich in der Lazy-Liste steht

`lazy.nvim` setzt standardmäßig Neovims `packpath` und `runtimepath` zurück und
deaktiviert das normale Laden von Start-Plugins. Das Add-on installiert sein
Neovim-Plugin dagegen unter Neovims Standardpfad
`stdpath("data")/site/pack/nvim-nvda/start/nvim-nvda`.

Die Beispielkonfiguration prüft diesen Pfad und übergibt ihn mit
`dir = access_link_path` als lokales Plugin an Lazy. Lazy lädt damit die bereits
vom Add-on installierte Kopie, obwohl die normale Paketsuche deaktiviert ist.
Diese Zeilen dürfen nicht entfernt und das Plugin darf nicht noch einmal aus
GitHub installiert werden.

Fehlt der Pfad, erscheint eine Warnung. Dann im NVDA-Menü zuerst den
Komponentenbefehl des Add-ons ausführen und Neovim neu starten. Der Pfad wird
mit `stdpath("data")` gebildet und funktioniert deshalb sowohl für lokales
Windows-Neovim als auch für eine auf dem Linux-Ziel installierte Komponente.

## Erster Start

Neovim nach dem Speichern vollständig schließen und erneut starten. Lazy lädt
beim ersten Start seine drei Internet-Plugins. Das kann etwas dauern. Danach
helfen diese Prüfungen:

| Prüfung | Erwartetes Ergebnis |
|---|---|
| `:checkhealth lazy` | Lazy meldet keine grundlegenden Installationsfehler |
| `:checkhealth vim.lsp` | die Pyright-Konfiguration ist aktiviert |
| `Leertaste`, `l`, `s` | Access Link nennt Pyright, sobald der Server an einer Python-Datei hängt |
| `:Lazy` | Oil, `nvim-lspconfig` und `nvim-lint` werden als geladen angezeigt |

Aktualisierungen werden in dieser Variante mit `:Lazy update` und nicht mit
`:packupdate` angestoßen. Die erzeugte `lazy-lock.json` hält die tatsächlich
verwendeten Plugin-Versionen fest. Bewahren Sie sie zusammen mit einer
gesicherten Konfiguration auf.

## Bedienung

Die Tasten in der folgenden Tabelle sind Neovim-Tasten ohne NVDA-Taste.
Neovim führt die zugeordneten Aktionen aus; Access Link macht ihre Ergebnisse
für Sprache und Braille zugänglich.

| Taste | Wirkung |
|---|---|
| `-` im Normalmodus | über Oil den Ordner der aktuellen Datei öffnen |
| `Eingabetaste` in Oil | Datei oder Unterordner öffnen |
| `-` in Oil | zum übergeordneten Ordner wechseln |
| `:write` in Oil | umbenannte, verschobene oder gelöschte Einträge nach Bestätigung anwenden |
| `K` | LSP-Hovertext anfordern |
| `g`, danach `d` | zur Definition springen |
| `Ctrl+Leertaste` im Insert-Modus | native LSP-Vervollständigung öffnen |
| `Leertaste`, `l`, `l` | Ruff sofort ausführen |
| `[d` / `]d` | vorherige / nächste Diagnose ausgeben |
| `[D` / `]D` | erste / letzte Diagnose ausgeben |
| `Leertaste`, `d`, `d` | Diagnose an der Cursorposition wiederholen |

Oil bleibt absichtlich nicht lazy-geladen, wie es dessen Upstream-Anleitung
empfiehlt. Löschungen landen in dieser kleinen portablen Konfiguration nicht
automatisch im Papierkorb; Oil zeigt vor Änderungen weiterhin seine von Access
Link zugänglich gemachten Bestätigungen.

Die kontextbezogenen NVDA-Kombinationen `NVDA+Leertaste` für
Funktionssignaturen und `NVDA+Umschalt+Leertaste` für Diagnosen sind bereits
eingebaut. Access Link übernimmt sie nur in der exakt aktiven, verbundenen
Neovim-Pane; andernorts bleibt NVDAs Standardfunktion erhalten. Sie werden
weder in dieser `init.lua` noch in NVDA neu zugewiesen. Nur für ausführliche
Completion-Dokumentation kann optional ein NVDA-Tastenbefehl zugeordnet werden,
wie im vorherigen Kapitel beschrieben.
