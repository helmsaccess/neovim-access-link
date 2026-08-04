-- Isolated Neovim configuration for the guided human-test framework.
-- It is always loaded with `nvim -u`; it never replaces the user's init.lua.

local profile = (vim.env.ACCESS_LINK_HUMAN_PROFILE or "native"):lower()
local step_id = (vim.env.ACCESS_LINK_HUMAN_STEP_ID or ""):lower()
local dry_run = vim.env.ACCESS_LINK_HUMAN_DRY_RUN == "1"
local language = (vim.env.ACCESS_LINK_HUMAN_LANGUAGE or "en"):lower()
local configuration_source = assert(debug.getinfo(1, "S").source)
assert(configuration_source:sub(1, 1) == "@", "human-test init path is unavailable")
local framework_root = vim.fs.dirname(configuration_source:sub(2))
local linter_readiness = dofile(vim.fs.joinpath(framework_root, "linter_readiness.lua"))
local completion_parentheses = dofile(vim.fs.joinpath(
  framework_root, "completion_parentheses.lua"))
local human_messages = language == "de" and {
  diagnostics_waiting = "%s-Diagnosen werden ermittelt. Bitte warten.",
  diagnostics_ready = "Diagnosen bereit: %d von %s. Der Cursor steht jetzt auf der ersten Testdiagnose. Jetzt F7 drücken.",
  diagnostics_not_ready = "%s-Diagnosen wurden nicht rechtzeitig bereit.",
  callable_name = "Cursor auf Funktionsname.",
  callable_open = "Cursor auf öffnender Klammer.",
  callable_close = "Cursor auf schließender Klammer.",
  callable_unavailable = "Diese Testhilfe ist nur in der Python-Funktionsdatei verfügbar.",
  insertion_unavailable = "Diese Aufgabe benötigt keine vorbereitete Eingabestelle.",
} or {
  diagnostics_waiting = "Waiting for %s diagnostics.",
  diagnostics_ready = "Diagnostics ready: %d from %s. The cursor is now on the first test diagnostic. Press F7 now.",
  diagnostics_not_ready = "%s diagnostics did not become ready in time.",
  callable_name = "Cursor on function name.",
  callable_open = "Cursor on opening parenthesis.",
  callable_close = "Cursor on closing parenthesis.",
  callable_unavailable = "This test helper is available only in the Python callable fixture.",
  insertion_unavailable = "This task does not require a prepared insertion position.",
}
local valid_profiles = {
  setup = true,
  native = true,
  diagnostics = true,
  ["c-diagnostics"] = true,
  ["markdown-diagnostics"] = true,
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
  if profile == "setup" or profile == "diagnostics"
      or profile == "c-diagnostics" or profile == "markdown-diagnostics" then
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

local function prepare_parameter_probe()
  if vim.bo.filetype ~= "python" then
    vim.notify(human_messages.callable_unavailable)
    return
  end
  local marker = "automatic_total = calculate_total()"
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)
  local line_number = nil
  for index, line in ipairs(lines) do
    if line == marker then
      line_number = index
      break
    end
  end
  if not line_number then
    local last_line = vim.api.nvim_buf_line_count(0)
    vim.api.nvim_buf_set_lines(0, last_line, last_line, false, { "", marker })
    line_number = last_line + 2
  end
  local opening = assert(marker:find("(", 1, true)) - 1
  vim.api.nvim_win_set_cursor(0, { line_number, opening + 1 })
  vim.cmd("startinsert")
end

local function prepare_current_probe()
  if step_id == "automatic-parameters" then
    prepare_parameter_probe()
    return
  end
  if step_id == "completion-presentation" then
    prepare_insert_probe("completion_probe = calculate_")
    return
  end
  vim.notify(human_messages.insertion_unavailable)
end

local function callable_fixture_positions()
  if vim.bo.filetype ~= "python" then return nil end
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)
  for line_number, line in ipairs(lines) do
    local call = line:find("total = calculate_total", 1, true)
    if call then
      local name = call - 1 + #"total = "
      local opening = assert(line:find("(", name + 1, true)) - 1
      local closing = assert(line:find(")", opening + 2, true)) - 1
      return {
        { cursor = { line_number, name }, message = human_messages.callable_name },
        { cursor = { line_number, opening }, message = human_messages.callable_open },
        { cursor = { line_number, closing }, message = human_messages.callable_close },
      }
    end
  end
  return nil
end

local callable_position_index = 1
local function cycle_callable_fixture_position()
  local positions = callable_fixture_positions()
  if not positions then
    vim.notify(human_messages.callable_unavailable)
    return
  end
  callable_position_index = callable_position_index % #positions + 1
  local selected = positions[callable_position_index]
  vim.api.nvim_win_set_cursor(0, selected.cursor)
  vim.notify(selected.message)
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

local run_linter = nil
local run_linter_with_feedback = nil
local linter_diagnostics_ready = nil
local linter_display_name = nil

vim.keymap.set("n", "<F1>", function()
  access_link_command("NvimNvdaLspStatus")
end, { desc = "Access Link human test: LSP status" })
vim.keymap.set({ "n", "i" }, "<F2>", show_current_task,
  { desc = "Access Link human test: repeat current task" })
vim.keymap.set("n", "<F3>", prepare_current_probe,
  { desc = "Access Link human test: prepare current insertion task" })
vim.keymap.set("n", "<F4>", cycle_callable_fixture_position,
  { desc = "Access Link human test: cycle callable cursor position" })
if profile == "diagnostics" then
  vim.keymap.set("n", "<F5>", function()
    vim.api.nvim_win_set_cursor(0, { 2, 0 })
    access_link_command("NvimNvdaDiagnosticCurrent")
  end, { desc = "Access Link human test: query a clean diagnostic position" })
end
vim.keymap.set("n", "<F6>", function()
  if run_linter_with_feedback then
    run_linter_with_feedback()
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
  cmp.event:on("confirm_done", function(event)
    completion_parentheses.apply(event.entry.completion_item)
  end)
  vim.g.access_link_human_cmp_auto_parentheses = 1
  capabilities = require("cmp_nvim_lsp").default_capabilities(capabilities)
elseif profile == "blink" then
  require("blink.cmp").setup({
    keymap = {
      preset = "default",
      ["<F5>"] = { "show", "show_documentation", "hide_documentation" },
    },
    completion = {
      accept = { auto_brackets = { enabled = true } },
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
      vim.lsp.completion.enable(true, client.id, event.buf, {
        autotrigger = false,
        convert = completion_parentheses.native_convert,
      })
      local bracket_group = vim.api.nvim_create_augroup(
        "AccessLinkHumanNativeCompletion" .. event.buf, { clear = true })
      vim.api.nvim_create_autocmd("CompleteDone", {
        group = bracket_group,
        buffer = event.buf,
        callback = function()
          local item = vim.tbl_get(
            vim.v.completed_item, "user_data", "nvim", "lsp", "completion_item")
          completion_parentheses.apply(item)
        end,
        desc = "Place the cursor inside accepted function parentheses",
      })
      vim.keymap.set("i", "<C-Space>", vim.lsp.completion.get, options)
      vim.keymap.set("i", "<F5>", vim.lsp.completion.get, options)
      vim.keymap.set("i", "<C-k>", vim.lsp.buf.signature_help, options)
    end
  end,
})

local uses_pyright = profile == "native" or profile == "diagnostics"
  or profile == "cmp" or profile == "blink" or profile == "focus"
if uses_pyright then
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
          diagnosticSeverityOverrides = {
            reportUnusedImport = "none",
          },
          typeCheckingMode = "strict",
          useLibraryCodeForTypes = true,
        },
      },
    },
  })
  vim.lsp.enable("pyright")
end

local uses_linter = profile == "diagnostics" or profile == "c-diagnostics"
  or profile == "markdown-diagnostics"
if uses_linter then
  local lint = require("lint")
  local linter_name
  local process_directory = vim.env.TEMP or vim.env.TMP or vim.uv.cwd()

  if profile == "diagnostics" then
    linter_name = "ruff"
    linter_display_name = "Ruff"
    lint.linters_by_ft = { python = { linter_name } }
    lint.linters.ruff.cmd = assert(vim.env.ACCESS_LINK_HUMAN_RUFF,
      "ACCESS_LINK_HUMAN_RUFF is required")
    table.insert(lint.linters.ruff.args, 2, "--isolated")
    table.insert(lint.linters.ruff.args, 3, "--no-cache")
  elseif profile == "c-diagnostics" then
    linter_name = "clangtidy"
    linter_display_name = "Clang-Tidy"
    lint.linters_by_ft = { c = { linter_name } }
    lint.linters.clangtidy.cmd = assert(vim.env.ACCESS_LINK_HUMAN_CLANG_TIDY,
      "ACCESS_LINK_HUMAN_CLANG_TIDY is required")
    lint.linters.clangtidy.parser = linter_readiness.clang_tidy_parser(
      require("lint.parser"), vim.diagnostic.severity)
  else
    linter_name = "markdownlint-cli2"
    linter_display_name = "markdownlint"
    lint.linters_by_ft = { markdown = { linter_name } }
    local markdownlint = lint.linters["markdownlint-cli2"]
    markdownlint.cmd = assert(vim.env.ACCESS_LINK_HUMAN_MARKDOWNLINT,
      "ACCESS_LINK_HUMAN_MARKDOWNLINT is required")
    markdownlint.args = {
      "--config", vim.fs.joinpath(vim.fn.getcwd(), ".markdownlint.json"), "-",
    }
  end

  linter_diagnostics_ready = function()
    return linter_readiness.evaluate(
      profile,
      vim.diagnostic.get(0),
      vim.diagnostic.severity
    )
  end

  run_linter = function()
    -- cmd.exe cannot reliably use a UNC directory as its working directory.
    -- Every configured provider receives either an absolute filename or stdin.
    lint.try_lint(linter_name, { cwd = process_directory })
  end

  local readiness_pending = false
  local function move_to_primary_linter_diagnostic()
    local values = vim.diagnostic.get(0)
    local diagnostic = linter_readiness.primary(
      profile, values, vim.diagnostic.severity)
    if not diagnostic then return false end
    local column = type(diagnostic.col) == "number" and diagnostic.col or 0
    vim.api.nvim_win_set_cursor(0, { diagnostic.lnum + 1, column })
    local current = require("nvim_nvda.diagnostics").snapshot_values(
      values, diagnostic.lnum + 1, column)
    return current ~= nil
  end
  run_linter_with_feedback = function()
    if readiness_pending then
      vim.notify(string.format(human_messages.diagnostics_waiting, linter_display_name))
      return
    end
    readiness_pending = true
    vim.notify(string.format(human_messages.diagnostics_waiting, linter_display_name))
    run_linter()
    vim.schedule(function()
      local ready = vim.wait(15000, function()
        return linter_diagnostics_ready()
      end, 50)
      readiness_pending = false
      if ready then
        local _, count = linter_diagnostics_ready()
        if move_to_primary_linter_diagnostic() then
          vim.notify(string.format(
            human_messages.diagnostics_ready, count, linter_display_name
          ))
        else
          vim.notify(string.format(
            human_messages.diagnostics_not_ready, linter_display_name
          ), vim.log.levels.ERROR)
        end
      else
        vim.notify(string.format(
          human_messages.diagnostics_not_ready, linter_display_name
        ), vim.log.levels.ERROR)
      end
    end)
  end
  vim.api.nvim_create_user_command("AccessLinkHumanLint", run_linter, {
    desc = "Run the isolated diagnostic provider",
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

local function request_payload(request_id)
  local cursor = vim.api.nvim_win_get_cursor(0)
  local buffer = vim.api.nvim_get_current_buf()
  return {
    requestId = request_id,
    bufferId = buffer,
    windowId = vim.api.nvim_get_current_win(),
    tabpageId = vim.api.nvim_get_current_tabpage(),
    changedtick = vim.api.nvim_buf_get_changedtick(buffer),
    line = cursor[1],
    byteColumn = cursor[2],
  }
end

local function fixture_cursor(name)
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)
  if name == "lsp_features.py" then
    local positions = callable_fixture_positions()
    return positions and positions[1].cursor or nil
  elseif name == "diagnostics.py" then
    return { 1, 15 }
  elseif name == "diagnostics.c" then
    for line_number, line in ipairs(lines) do
      local byte = line:find("missing", 1, true)
      if byte then return { line_number, byte - 1 } end
    end
  elseif name == "diagnostics.md" then
    return { 3, 2 }
  end
  return nil
end

local function move_to_fixture_cursor(name)
  local cursor = fixture_cursor(name)
  assert(cursor, "the human-test fixture does not contain its cursor marker")
  vim.api.nvim_win_set_cursor(0, cursor)
end

local function assert_callable_choices_ready()
  local positions = assert(callable_fixture_positions(),
    "the human-test fixture does not contain its callable positions")
  for index, position in ipairs(positions) do
    vim.api.nvim_win_set_cursor(0, position.cursor)
    local result = nil
    local request = request_payload(index)
    local accepted = require("nvim_nvda.developer_context").request_callable(
      request,
      function(_, _, payload) result = payload end
    )
    assert(accepted, "Access Link did not accept callable fixture position " .. index)
    assert(vim.wait(15000, function() return result ~= nil end, 50),
      "Pyright did not answer callable fixture position " .. index)
    assert(result.ok, "callable fixture position " .. index
      .. " did not produce signature help")
    for key, value in pairs(request) do
      assert(result[key] == value,
        "the callable fixture result omitted its correlated editor snapshot")
    end
    local rich_signatures = 0
    for _, item in ipairs(result.items) do
      if #item.parameters >= 3 then rich_signatures = rich_signatures + 1 end
    end
    assert(rich_signatures >= 2,
      "callable fixture position " .. index
        .. " did not produce two signatures with three parameters")
  end
  vim.api.nvim_win_set_cursor(0, positions[1].cursor)
end

local function completion_labels(results)
  local labels = {}
  for _, response in pairs(type(results) == "table" and results or {}) do
    local result = type(response) == "table" and response.result or nil
    local items = type(result) == "table" and (result.items or result) or {}
    for _, item in ipairs(type(items) == "table" and items or {}) do
      if type(item) == "table" and type(item.label) == "string" then
        labels[item.label] = true
      end
    end
  end
  return labels
end

local function assert_completion_choices_ready()
  local line_count = vim.api.nvim_buf_line_count(0)
  local original_cursor = vim.api.nvim_win_get_cursor(0)
  local probe = "completion_probe = calculate_"
  vim.api.nvim_buf_set_lines(0, line_count, line_count, false, { "", probe })
  vim.api.nvim_win_set_cursor(0, { line_count + 2, #probe })
  local results = nil
  local params = vim.lsp.util.make_position_params(0, "utf-16")
  params.context = { triggerKind = vim.lsp.protocol.CompletionTriggerKind.Invoked }
  vim.lsp.buf_request_all(0, "textDocument/completion", params, function(value)
    results = value
  end)
  local answered = vim.wait(15000, function() return results ~= nil end, 50)
  vim.api.nvim_buf_set_lines(0, line_count, line_count + 2, false, {})
  vim.api.nvim_win_set_cursor(0, original_cursor)
  assert(answered, "Pyright did not answer the completion fixture request")
  local labels = completion_labels(results)
  for _, expected in ipairs({ "calculate_total", "calculate_tax", "calculate_tip" }) do
    assert(labels[expected], "the completion fixture is missing candidate " .. expected)
  end
end

local function assert_completion_profile_ready()
  if profile == "cmp" then
    -- nvim-cmp intentionally installs its real insert-mode keymaps on the
    -- first InsertEnter.  Inspect the effective configuration here so the
    -- normal-mode preflight does not reject that deferred setup.
    local cmp_config = require("cmp.config")
    local cmp_keymap = require("cmp.utils.keymap")
    local mapping = cmp_config.get().mapping[cmp_keymap.normalize("<F5>")]
    assert(type(mapping) == "table" and type(mapping.i) == "function",
      "nvim-cmp did not configure its F5 completion mapping")
    assert(cmp_config.get_source_config("nvim_lsp") ~= nil,
      "nvim-cmp did not configure its LSP completion source")
    assert(vim.g.access_link_human_cmp_auto_parentheses == 1,
      "nvim-cmp did not enable the expected automatic function parentheses")
    return
  end

  if profile == "blink" then
    -- blink.cmp also applies buffer-local insert mappings on InsertEnter.
    -- Resolve its preset plus overrides without forcing a synthetic mode
    -- transition during the provider preflight.
    local blink_config = require("blink.cmp.config")
    local mappings = require("blink.cmp.keymap").get_mappings(
      blink_config.keymap, "default")
    local f5 = mappings["<F5>"]
    assert(type(f5) == "table" and vim.tbl_contains(f5, "show"),
      "blink.cmp did not configure its F5 completion mapping")
    assert(type(blink_config.sources.default) == "table"
        and vim.tbl_contains(blink_config.sources.default, "lsp"),
      "blink.cmp did not configure its LSP completion source")
    assert(blink_config.completion.accept.auto_brackets.enabled == true,
      "blink.cmp did not enable the expected automatic function brackets")
    return
  end

  local insert_f5 = vim.fn.maparg("<F5>", "i", false, true)
  assert(type(insert_f5) == "table" and next(insert_f5) ~= nil,
    "the native completion profile did not install its F5 mapping")
  local bracket_autocmds = vim.api.nvim_get_autocmds({
    event = "CompleteDone", buffer = 0,
  })
  local bracket_autocmd_found = false
  for _, autocmd in ipairs(bracket_autocmds) do
    if autocmd.desc == "Place the cursor inside accepted function parentheses" then
      bracket_autocmd_found = true
      break
    end
  end
  assert(bracket_autocmd_found,
    "native completion did not enable automatic function parentheses")
end

vim.api.nvim_create_user_command("AccessLinkHumanPreflight", function()
  if uses_pyright then
    local attached = vim.wait(15000, function()
      return #vim.lsp.get_clients({ bufnr = 0, name = "pyright" }) > 0
    end, 50)
    assert(attached, "Pyright did not attach to the human-test fixture")
    local client = assert(vim.lsp.get_clients({ bufnr = 0, name = "pyright" })[1])
    assert(client:supports_method("textDocument/completion"),
      "Pyright does not advertise completion support")
    assert_completion_profile_ready()
    if profile == "native" then
      assert_callable_choices_ready()
    end
    if profile == "native" or profile == "cmp" or profile == "blink" then
      assert_completion_choices_ready()
    end
  end
  if uses_linter then
    assert(run_linter, "the diagnostic profile did not configure its linter")
    run_linter()
    local categorized = vim.wait(15000, function()
      return linter_diagnostics_ready()
    end, 50)
    assert(categorized, linter_display_name .. " did not publish the expected diagnostic")
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
      if name == "lsp_features.py" or name == "diagnostics.py"
          or name == "diagnostics.c" or name == "diagnostics.md" then
        move_to_fixture_cursor(name)
      end
    end)
  end,
})

vim.g.access_link_human_config_ready = 1
