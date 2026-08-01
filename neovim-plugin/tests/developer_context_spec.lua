local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local developer_context = require("nvim_nvda.developer_context")
local assertions = 0

local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

vim.api.nvim_buf_set_lines(0, 0, -1, true, { "calculate_total(price, quantity)" })
vim.api.nvim_win_set_cursor(0, { 1, 0 })
local function request()
  return {
    requestId = 7,
    bufferId = vim.api.nvim_get_current_buf(),
    windowId = vim.api.nvim_get_current_win(),
    tabpageId = vim.api.nvim_get_current_tabpage(),
    changedtick = vim.api.nvim_buf_get_changedtick(0),
    line = 1,
    byteColumn = 0,
  }
end

local emitted
local function emit(event_type, reason, payload)
  emitted = { event_type = event_type, reason = reason, payload = payload }
end

local original_params = vim.lsp.util.make_position_params
local original_request_all = vim.lsp.buf_request_all
local position_ok, actual_position = pcall(original_params, 0, "utf-16")
equal(true, position_ok, "public position parameters work on this Neovim version")
equal("table", type(actual_position), "public position parameters are a table")
vim.lsp.util.make_position_params = function()
  return { position = { line = 0, character = 0 } }
end
vim.lsp.buf_request_all = function(_, method, params, handler)
  equal("textDocument/signatureHelp", method, "signature requested first")
  equal(16, params.position.character, "callable name queries inside opening parenthesis")
  handler({
    [3] = {
      result = {
        activeSignature = 0,
        activeParameter = 1,
        signatures = {
          {
            label = "calculate_total(price: number, quantity: number)",
            documentation = { kind = "markdown", value = "Calculate a total." },
            parameters = {
              { label = "price: number", documentation = "Unit price." },
              { label = "quantity: number", documentation = "Item count." },
            },
          },
        },
      },
    },
  })
end
equal(true, developer_context.request_callable(request(), emit), "callable request accepted")
equal("callableContextResult", emitted.event_type, "callable result emitted")
equal(true, emitted.payload.ok, "callable result succeeds")
equal(1, #emitted.payload.items, "one signature returned")
equal(1, emitted.payload.activeParameter, "zero-based active parameter retained")
equal(
  "quantity: number: Item count.",
  emitted.payload.items[1].parameters[2],
  "parameter documentation retained"
)

vim.lsp.buf_request_all = function(_, _, _, handler)
  handler({
    [1] = {
      result = {
        activeSignature = 0,
        activeParameter = 0,
        signatures = {
          { label = "first_client(selected)", parameters = { { label = "selected" } } },
        },
      },
    },
    [2] = {
      result = {
        activeSignature = 0,
        activeParameter = 0,
        signatures = {
          { label = "second_client(other)", parameters = { { label = "other" } } },
        },
      },
    },
  })
end
emitted = nil
developer_context.request_callable(request(), emit)
equal(0, emitted.payload.activeItem, "first deterministic client remains active")
equal(
  "first_client(selected)",
  emitted.payload.items[emitted.payload.activeItem + 1].signature,
  "active item belongs to first deterministic client"
)

local parameters = {}
for index = 1, 110 do parameters[index] = { label = "parameter" .. index } end
vim.lsp.buf_request_all = function(_, _, _, handler)
  handler({
    [1] = {
      result = {
        activeSignature = 1,
        activeParameter = 99,
        signatures = {
          { label = "\255invalid" },
          {
            label = "unicode(😀value)",
            parameters = {
              { label = { 8, 15 }, documentation = "Unicode parameter." },
              unpack(parameters),
            },
          },
        },
      },
    },
  })
end
emitted = nil
developer_context.request_callable(request(), emit)
equal(1, #emitted.payload.items, "malformed UTF-8 signature is discarded")
equal(
  "😀value: Unicode parameter.",
  emitted.payload.items[1].parameters[1],
  "UTF-16 parameter range and documentation are decoded"
)
equal(100, #emitted.payload.items[1].parameters, "parameter list is bounded")
equal(99, emitted.payload.activeParameter, "bounded active parameter remains valid")

local oversized_signatures = {}
for index = 1, 100 do
  oversized_signatures[index] = {
    label = "signature" .. index,
    documentation = string.rep("d", 8192),
  }
end
vim.lsp.buf_request_all = function(_, _, _, handler)
  handler({ [1] = { result = { signatures = oversized_signatures } } })
end
emitted = nil
developer_context.request_callable(request(), emit)
local total_text = 0
for _, item in ipairs(emitted.payload.items) do
  total_text = total_text + #item.signature + #item.documentation
  for _, parameter in ipairs(item.parameters) do total_text = total_text + #parameter end
end
equal(true, total_text <= 256 * 1024, "aggregate callable text is bounded")
equal(true, #emitted.payload.items < 100, "aggregate bound stops oversized signature list")

local calls = 0
vim.lsp.buf_request_all = function(_, method, _, handler)
  calls = calls + 1
  if calls == 1 then
    equal("textDocument/signatureHelp", method, "empty signature request")
    handler({})
  else
    equal("textDocument/hover", method, "hover fallback request")
    handler({ [1] = { result = { contents = { kind = "markdown", value = "hover signature" } } } })
  end
end
emitted = nil
developer_context.request_callable(request(), emit)
equal("hover signature", emitted.payload.items[1].signature, "hover fallback retained")

vim.lsp.buf_request_all = function(_, _, _, handler) handler({}) end
emitted = nil
developer_context.request_callable(request(), emit)
equal("noResult", emitted.payload.resultCode, "empty signature and hover results are explicit")

local pending_handler
vim.lsp.buf_request_all = function(_, method, _, handler)
  equal("textDocument/signatureHelp", method, "stale asynchronous signature request")
  pending_handler = handler
end
local pending_request = request()
emitted = nil
equal(true, developer_context.request_callable(pending_request, emit), "async request accepted")
vim.api.nvim_win_set_cursor(0, { 1, 1 })
pending_handler({
  [1] = {
    result = {
      signatures = {
        { label = "stale(value)", parameters = { { label = "value" } } },
      },
    },
  },
})
equal("invalidOrStaleRequest", emitted.payload.resultCode, "moved cursor rejects async result")
vim.api.nvim_win_set_cursor(0, { 1, 0 })

vim.lsp.util.make_position_params = function() error("simulated position failure") end
emitted = nil
equal(false, developer_context.request_callable(request(), emit), "position failure is contained")
equal("requestFailed", emitted.payload.resultCode, "position failure result")
vim.lsp.util.make_position_params = function() return {} end

vim.lsp.buf_request_all = function() error("simulated signature API failure") end
emitted = nil
equal(false, developer_context.request_callable(request(), emit), "signature API failure is contained")
equal("requestFailed", emitted.payload.resultCode, "signature API failure result")

local api_calls = 0
vim.lsp.buf_request_all = function(_, _, _, handler)
  api_calls = api_calls + 1
  if api_calls == 1 then handler({}) else error("simulated hover API failure") end
end
emitted = nil
equal(true, developer_context.request_callable(request(), emit), "signature request remains accepted")
equal("requestFailed", emitted.payload.resultCode, "hover API failure is contained")

local namespace = vim.api.nvim_create_namespace("developer-context-spec")
vim.diagnostic.set(namespace, 0, {
  {
    lnum = 0, col = 0, end_lnum = 0, end_col = 9,
    message = "test problem", severity = vim.diagnostic.severity.ERROR,
    source = "test-linter",
  },
})
emitted = nil
equal(
  true,
  developer_context.request_diagnostics(request(), emit),
  "diagnostic context accepted"
)
equal("diagnosticContextResult", emitted.event_type, "diagnostic result emitted")
equal("test problem", emitted.payload.items[1].message, "diagnostic message retained")
equal(true, emitted.payload.items[1].atCursor, "diagnostic cursor containment retained")
equal(vim.NIL, emitted.payload.items[1].code, "missing diagnostic code remains explicit")

local stale = request()
stale.changedtick = stale.changedtick - 1
emitted = nil
equal(false, developer_context.request_diagnostics(stale, emit), "stale context rejected")
equal("invalidOrStaleRequest", emitted.payload.resultCode, "stale result code")

vim.lsp.util.make_position_params = original_params
vim.lsp.buf_request_all = original_request_all

print(string.format("developer context tests: %d assertions passed", assertions))
vim.cmd("qa!")
