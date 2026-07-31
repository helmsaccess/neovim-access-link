local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local events = {}
local original_rpcnotify = vim.rpcnotify
vim.rpcnotify = function(_, method, event)
  if method == "nvim_nvda_event" then events[#events + 1] = event end
  return true
end

local plugin = require("nvim_nvda")
plugin.setup()
plugin.register_channel(1)
events = {}

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "zero", "one", "two", "three" })
local namespace = vim.api.nvim_create_namespace("nvim_nvda_diagnostic_navigation")
vim.diagnostic.set(namespace, 0, {
  {
    lnum = 0, col = 0, end_lnum = 0, end_col = 4,
    message = "first", source = "gopls", code = "G001",
  },
  {
    lnum = 2, col = 0, end_lnum = 2, end_col = 3,
    message = "last", source = "rust-analyzer", code = "R001",
  },
})
vim.wait(50)

local function diagnostic_events()
  local result = {}
  for _, event in ipairs(events) do
    if event.type == "diagnosticMoved" then result[#result + 1] = event end
  end
  return result
end

local semantic_navigation_types = {
  diagnosticMoved = true,
  cursorMoved = true,
  characterMoved = true,
  wordMoved = true,
  lineChanged = true,
}

local function run(command)
  events = {}
  vim.cmd(command)
  vim.wait(500, function() return #diagnostic_events() > 0 end)
  local result = diagnostic_events()
  equal(1, #result, command .. " emits one semantic event")
  local navigation_count = 0
  for _, event in ipairs(events) do
    if semantic_navigation_types[event.type] then navigation_count = navigation_count + 1 end
  end
  equal(1, navigation_count, command .. " suppresses a generic cursor duplicate")
  return result[1]
end

vim.api.nvim_win_set_cursor(0, { 2, 0 })
local next_event = run("NvimNvdaDiagnosticNext")
equal(3, next_event.payload.cursor.line, "next command moves to following diagnostic")
equal("last", next_event.payload.diagnostic.message, "next command reports target")

local previous_event = run("NvimNvdaDiagnosticPrevious")
equal(1, previous_event.payload.cursor.line, "previous command moves back")
equal("first", previous_event.payload.diagnostic.message, "previous command reports target")

local last_event = run("NvimNvdaDiagnosticLast")
equal("last", last_event.payload.diagnostic.message, "last command")
local wrapped_next = run("NvimNvdaDiagnosticNext")
equal("first", wrapped_next.payload.diagnostic.message, "next command wraps")
local wrapped_previous = run("NvimNvdaDiagnosticPrevious")
equal("last", wrapped_previous.payload.diagnostic.message, "previous command wraps")
local first_event = run("NvimNvdaDiagnosticFirst")
equal("first", first_event.payload.diagnostic.message, "first command")
local current_event = run("NvimNvdaDiagnosticCurrent")
equal("first", current_event.payload.diagnostic.message, "current command")

if type(vim.diagnostic.jump) == "function" then
  vim.api.nvim_win_set_cursor(0, { 2, 0 })
  events = {}
  vim.api.nvim_feedkeys("]d", "xt", false)
  vim.wait(500, function() return #diagnostic_events() > 0 end)
  equal(1, #diagnostic_events(), "native next mapping emits one diagnostic event")
  equal("last", diagnostic_events()[1].payload.diagnostic.message, "native mapping target")

  vim.keymap.set("n", "]d", function()
    vim.diagnostic.jump({ count = 1, on_jump = function() end })
  end)
  vim.api.nvim_win_set_cursor(0, { 2, 0 })
  events = {}
  vim.api.nvim_feedkeys("]d", "xt", false)
  vim.wait(500, function() return #diagnostic_events() > 0 end)
  equal(1, #diagnostic_events(), "per-call jump callback still emits one diagnostic event")
  equal("last", diagnostic_events()[1].payload.diagnostic.message,
    "per-call jump callback target")
  vim.keymap.del("n", "]d")

  events = {}
  vim.api.nvim_feedkeys("]D", "xt", false)
  vim.wait(500, function() return #diagnostic_events() > 0 end)
  equal(1, #diagnostic_events(), "native last mapping emits one diagnostic event")
  equal("last", diagnostic_events()[1].payload.diagnostic.message, "native last target")

  events = {}
  vim.api.nvim_feedkeys("[D", "xt", false)
  vim.wait(500, function() return #diagnostic_events() > 0 end)
  equal(1, #diagnostic_events(), "native first mapping emits one diagnostic event")
  equal("first", diagnostic_events()[1].payload.diagnostic.message, "native first target")

  vim.keymap.set("n", "<F6>", function() vim.diagnostic.jump({ count = -1 }) end)
  events = {}
  vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<F6>", true, false, true), "xt", false)
  vim.wait(500, function() return #diagnostic_events() > 0 end)
  equal(1, #diagnostic_events(), "custom native jump mapping observed")
  equal("first", diagnostic_events()[1].payload.diagnostic.message, "custom mapping target")
  vim.keymap.del("n", "<F6>")
end

vim.diagnostic.reset(namespace, 0)
vim.wait(50)
local empty_event = run("NvimNvdaDiagnosticCurrent")
equal(nil, empty_event.payload.diagnostic, "empty state reported explicitly")
equal(0, empty_event.payload.diagnosticCount, "empty diagnostic count")

vim.rpcnotify = original_rpcnotify
for _, name in ipairs({
  "NvimNvdaDiagnosticPrevious",
  "NvimNvdaDiagnosticNext",
  "NvimNvdaDiagnosticFirst",
  "NvimNvdaDiagnosticLast",
  "NvimNvdaDiagnosticCurrent",
}) do
  pcall(vim.api.nvim_del_user_command, name)
end

print(string.format("diagnostic navigation tests: %d assertions passed", assertions))
vim.cmd("qa!")
