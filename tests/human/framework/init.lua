-- Isolated Neovim configuration for the guided human-test framework.
-- It is always loaded with `nvim -u`; it never replaces the user's init.lua.

local profile = (vim.env.ACCESS_LINK_HUMAN_PROFILE or "native"):lower()
local dry_run = vim.env.ACCESS_LINK_HUMAN_DRY_RUN == "1"
local valid_profiles = {
  setup = true,
  native = true,
  diagnostics = true,
  cmp = true,
  blink = true,
  focus = true,
}
assert(valid_profiles[profile], "unsupported ACCESS_LINK_HUMAN_PROFILE")

vim.g.mapleader = " "
vim.opt.expandtab = true
vim.opt.shiftwidth = 2
vim.opt.softtabstop = 2
vim.opt.tabstop = 2
vim.opt.completeopt = { "menu", "menuone", "noselect", "popup" }
vim.opt.updatetime = 250
vim.diagnostic.config({
  virtual_text = true,
  signs = true,
  underline = true,
  update_in_insert = false,
  severity_sort = true,
  float = { border = "rounded", source = "always" },
})

local function read_json(path)
  local file = assert(io.open(path, "rb"))
  local content = file:read("*a")
  file:close()
  return vim.json.decode(content)
end

local function dependency_spec(dependencies, key, name)
  local value = assert(dependencies.plugins[key], "missing dependency " .. key)
  return {
    src = assert(value.source),
    version = assert(value.revision),
    name = name,
  }
end

if not dry_run then
  assert(vim.version().major == 0 and vim.version().minor == 12,
    "guided human tests require Neovim 0.12.x")
  if profile ~= "setup" then
    local plugin_path = assert(vim.env.ACCESS_LINK_HUMAN_PLUGIN,
      "ACCESS_LINK_HUMAN_PLUGIN is required")
    assert(vim.uv.fs_stat(vim.fs.joinpath(plugin_path, "plugin", "nvim_nvda.lua")),
      "Neovim Access Link plugin entry point is missing")
    vim.opt.runtimepath:prepend(plugin_path)
  end

  local dependency_path = assert(vim.env.ACCESS_LINK_HUMAN_DEPENDENCIES,
    "ACCESS_LINK_HUMAN_DEPENDENCIES is required")
  local dependencies = read_json(dependency_path)
  assert(dependencies.schemaVersion == 1, "unsupported dependency schema")
  local specifications = {}
  local function add(key, name)
    specifications[#specifications + 1] = dependency_spec(dependencies, key, name)
  end
  if profile == "setup" or profile == "diagnostics" then
    add("nvimLint", "nvim-lint")
  end
  if profile == "setup" or profile == "cmp" then
    add("nvimCmp", "nvim-cmp")
    add("cmpNvimLsp", "cmp-nvim-lsp")
  end
  if profile == "setup" or profile == "blink" then
    add("blinkCmp", "blink.cmp")
  end
  if #specifications > 0 then
    vim.pack.add(specifications, { confirm = false, load = true })
    local installed = vim.pack.get(nil, { info = true })
    local revisions = {}
    for _, plugin in ipairs(installed) do
      revisions[plugin.spec.name] = plugin.rev
    end
    for _, specification in ipairs(specifications) do
      assert(revisions[specification.name] == specification.version,
        string.format("dependency %s is not at its pinned revision", specification.name))
    end
  end
end

if profile == "setup" then
  vim.g.access_link_human_setup_complete = 1
  return
end

local function access_link_command(name)
  if vim.fn.exists(":" .. name) ~= 2 then
    vim.notify("Access Link command is unavailable: " .. name, vim.log.levels.ERROR)
    return
  end
  vim.cmd(name)
end

local function prepare_insert_probe(text)
  if vim.bo.filetype ~= "python" then
    vim.notify("This test helper is available only in the Python fixture")
    return
  end
  local last_line = vim.api.nvim_buf_line_count(0)
  vim.api.nvim_buf_set_lines(0, last_line, last_line, false, { "", text })
  vim.api.nvim_win_set_cursor(0, { last_line + 2, #text })
  vim.cmd("startinsert!")
end

local function show_current_task()
  local context = vim.env.ACCESS_LINK_HUMAN_CONTEXT or ""
  local task = vim.env.ACCESS_LINK_HUMAN_TASK or ""
  local expected = vim.env.ACCESS_LINK_HUMAN_EXPECTED or ""
  local parts = vim.tbl_filter(function(value) return value ~= "" end, {
    context,
    task,
    expected,
  })
  vim.notify(table.concat(parts, "\n\n"), vim.log.levels.INFO, {
    title = "Access Link human test",
  })
end

vim.keymap.set("n", "<F1>", function()
  access_link_command("NvimNvdaLspStatus")
end, { desc = "Access Link human test: LSP status" })
vim.keymap.set({ "n", "i" }, "<F2>", show_current_task,
  { desc = "Access Link human test: repeat current task" })
vim.keymap.set("n", "<F3>", function()
  prepare_insert_probe("completion_probe = calc")
end, { desc = "Access Link human test: prepare completion" })
vim.keymap.set("n", "<F6>", function()
  if vim.fn.exists(":AccessLinkHumanLint") == 2 then
    vim.cmd("AccessLinkHumanLint")
  else
    vim.notify("This test profile does not configure a linter")
  end
end, { desc = "Access Link human test: run linter" })
vim.keymap.set("n", "<F7>", function()
  access_link_command("NvimNvdaDiagnosticCurrent")
end, { desc = "Access Link human test: current diagnostic" })
vim.keymap.set("n", "<F8>", function()
  access_link_command("NvimNvdaDiagnosticPrevious")
end, { desc = "Access Link human test: previous diagnostic" })
vim.keymap.set("n", "<F9>", function()
  access_link_command("NvimNvdaDiagnosticNext")
end, { desc = "Access Link human test: next diagnostic" })
vim.keymap.set("n", "<F10>", "<Cmd>qa!<CR>",
  { desc = "Access Link human test: exit without saving" })

vim.api.nvim_create_user_command("AccessLinkHumanTestInfo", function()
  show_current_task()
end, { desc = "Show the active guided human-test profile" })

if dry_run then
  vim.g.access_link_human_config_ready = 1
  return
end

local capabilities = vim.lsp.protocol.make_client_capabilities()
if profile == "cmp" then
  local cmp = require("cmp")
  cmp.setup({
    snippet = {
      expand = function(arguments) vim.snippet.expand(arguments.body) end,
    },
    completion = { completeopt = "menu,menuone,noselect" },
    mapping = cmp.mapping.preset.insert({
      ["<C-Space>"] = cmp.mapping.complete(),
      ["<F5>"] = cmp.mapping.complete(),
      ["<C-n>"] = cmp.mapping.select_next_item(),
      ["<C-p>"] = cmp.mapping.select_prev_item(),
      ["<C-y>"] = cmp.mapping.confirm({ select = false }),
      ["<C-e>"] = cmp.mapping.abort(),
      ["<C-k>"] = cmp.mapping(function()
        vim.lsp.buf.signature_help()
      end, { "i", "s" }),
    }),
    sources = { { name = "nvim_lsp" } },
    experimental = { ghost_text = false },
  })
  capabilities = require("cmp_nvim_lsp").default_capabilities(capabilities)
elseif profile == "blink" then
  require("blink.cmp").setup({
    keymap = {
      preset = "default",
      ["<F5>"] = { "show", "show_documentation", "hide_documentation" },
    },
    completion = {
      documentation = { auto_show = false },
      ghost_text = { enabled = false },
      list = { selection = { preselect = false, auto_insert = false } },
    },
    sources = { default = { "lsp" } },
    signature = { enabled = true },
    fuzzy = { implementation = "lua" },
  })
  capabilities = require("blink.cmp").get_lsp_capabilities(capabilities)
end

local lsp_group = vim.api.nvim_create_augroup("AccessLinkHumanLsp", { clear = true })
vim.api.nvim_create_autocmd("LspAttach", {
  group = lsp_group,
  callback = function(event)
    local options = { buffer = event.buf, silent = true }
    vim.keymap.set("n", "K", vim.lsp.buf.hover, options)
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, options)
    if profile == "native" or profile == "diagnostics" or profile == "focus" then
      local client = assert(vim.lsp.get_client_by_id(event.data.client_id))
      vim.lsp.completion.enable(true, client.id, event.buf, { autotrigger = false })
      vim.keymap.set("i", "<C-Space>", vim.lsp.completion.get, options)
      vim.keymap.set("i", "<F5>", vim.lsp.completion.get, options)
      vim.keymap.set("i", "<C-k>", vim.lsp.buf.signature_help, options)
    end
  end,
})

local pyright = assert(vim.env.ACCESS_LINK_HUMAN_PYRIGHT,
  "ACCESS_LINK_HUMAN_PYRIGHT is required")
vim.lsp.config("pyright", {
  cmd = { pyright, "--stdio" },
  capabilities = capabilities,
  root_markers = { "pyrightconfig.json" },
  settings = {
    python = {
      analysis = {
        autoSearchPaths = true,
        diagnosticMode = "openFilesOnly",
        typeCheckingMode = "strict",
        useLibraryCodeForTypes = true,
      },
    },
  },
})
vim.lsp.enable("pyright")

local run_linter = nil
if profile == "diagnostics" then
  local lint = require("lint")
  local ruff = assert(vim.env.ACCESS_LINK_HUMAN_RUFF,
    "ACCESS_LINK_HUMAN_RUFF is required")
  lint.linters_by_ft = { python = { "ruff" } }
  lint.linters.ruff.cmd = ruff
  run_linter = function()
    local filename = vim.api.nvim_buf_get_name(0)
    local directory = filename ~= "" and vim.fs.dirname(filename) or vim.uv.cwd()
    lint.try_lint(nil, { cwd = directory })
  end
  vim.api.nvim_create_user_command("AccessLinkHumanLint", run_linter, {
    desc = "Run the isolated Ruff diagnostic provider",
  })
  vim.api.nvim_create_autocmd("BufReadPost", {
    group = vim.api.nvim_create_augroup("AccessLinkHumanLint", { clear = true }),
    callback = function(event)
      vim.schedule(function()
        if vim.api.nvim_buf_is_valid(event.buf) then
          vim.api.nvim_buf_call(event.buf, run_linter)
        end
      end)
    end,
  })
end

vim.api.nvim_create_user_command("AccessLinkHumanPreflight", function()
  local attached = vim.wait(15000, function()
    return #vim.lsp.get_clients({ bufnr = 0, name = "pyright" }) > 0
  end, 50)
  assert(attached, "Pyright did not attach to the human-test fixture")
  local client = assert(vim.lsp.get_clients({ bufnr = 0, name = "pyright" })[1])
  assert(client:supports_method("textDocument/completion"),
    "Pyright does not advertise completion support")
  local insert_f5 = vim.fn.maparg("<F5>", "i", false, true)
  assert(type(insert_f5) == "table" and next(insert_f5) ~= nil,
    "the selected completion profile did not install its F5 mapping")
  if profile == "diagnostics" then
    assert(run_linter, "the diagnostic profile did not configure Ruff")
    run_linter()
    local diagnosed = vim.wait(15000, function()
      for _, diagnostic in ipairs(vim.diagnostic.get(0)) do
        if tostring(diagnostic.source):lower():find("ruff", 1, true)
            or tostring(diagnostic.code) == "F401" then
          return true
        end
      end
      return false
    end, 50)
    assert(diagnosed, "Ruff did not publish a diagnostic for diagnostics.py")
  end
  vim.g.access_link_human_preflight_ready = 1
end, { desc = "Verify real providers for the guided human-test profile" })

vim.api.nvim_create_autocmd("BufWinEnter", {
  group = vim.api.nvim_create_augroup("AccessLinkHumanStart", { clear = true }),
  callback = function(event)
    vim.schedule(function()
      if not vim.api.nvim_buf_is_valid(event.buf)
          or vim.api.nvim_get_current_buf() ~= event.buf then
        return
      end
      local name = vim.fs.basename(vim.api.nvim_buf_get_name(event.buf))
      if name == "lsp_features.py" then
        vim.api.nvim_win_set_cursor(0, { 6, 8 })
      elseif name == "diagnostics.py" then
        vim.api.nvim_win_set_cursor(0, { 1, 7 })
      end
    end)
  end,
})

vim.g.access_link_human_config_ready = 1
