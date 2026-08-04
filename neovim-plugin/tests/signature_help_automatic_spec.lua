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

local method = "textDocument/signatureHelp"
local original_mode = vim.api.nvim_get_mode
local original_request_all = vim.lsp.buf_request_all
local original_get_clients = vim.lsp.get_clients
local mocked_mode = "n"
vim.api.nvim_get_mode = function() return { mode = mocked_mode, blocking = false } end

local requests = {}
local cancel_count = 0
vim.lsp.buf_request_all = function(bufnr, requested_method, params, handler)
  requests[#requests + 1] = {
    bufnr = bufnr,
    method = requested_method,
    params = vim.deepcopy(params),
    handler = handler,
  }
  return function() cancel_count = cancel_count + 1 end
end
vim.lsp.get_clients = function()
  return {{
    id = 7,
    server_capabilities = {
      signatureHelpProvider = {
        triggerCharacters = { "(" },
        retriggerCharacters = { "," },
      },
    },
  }}
end

package.loaded["nvim_nvda.signature_help"] = nil
package.loaded["nvim_nvda.call_context"] = nil
local signature_help = require("nvim_nvda.signature_help")
local events = {}
local group = vim.api.nvim_create_augroup("nvim-nvda-automatic-signature-spec", { clear = true })
signature_help.setup(function(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end, group)

local function set_line(value, column)
  vim.api.nvim_buf_set_lines(0, 0, -1, true, { value })
  vim.bo.filetype = "python"
  vim.api.nvim_win_set_cursor(0, { 1, column or #value })
end

local function respond(request_index, active_parameter, active_signature)
  requests[request_index].handler({
    [7] = { result = {
      activeSignature = active_signature or 0,
      activeParameter = active_parameter,
      signatures = {
        {
          label = "calculate_total(price: float, quantity: int, tax: float)",
          parameters = {
            { label = "price: float" },
            { label = "quantity: int" },
            { label = "tax: float" },
          },
        },
        {
          label = "calculate_total(subtotal: float, tax: float)",
          parameters = {
            { label = "subtotal: float" },
            { label = "tax: float" },
          },
        },
      },
    } },
  })
end

set_line("calculate_total( ")
mocked_mode = "i"
signature_help.set_connected(true)
equal(true, vim.wait(1000, function() return #requests == 1 end, 5),
  "connection schedules initial request")
equal(method, requests[1].method, "automatic request uses SignatureHelp")
equal(16, requests[1].params.position.character, "request uses exact insert cursor")
equal(1, requests[1].params.context.triggerKind, "initial request is invoked")
equal(false, requests[1].params.context.isRetrigger, "initial request is not a retrigger")
respond(1, 0)
equal("activeParameterChanged", events[#events].type, "initial parameter published")
equal("callEntered", events[#events].payload.hintReason, "initial reason")

local initial_events = #events
vim.api.nvim_exec_autocmds("CursorMovedI", { buffer = 0 })
equal(true, vim.wait(1000, function() return #requests == 2 end, 5),
  "same-argument cursor movement retriggers LSP")
respond(2, 0)
equal(initial_events, #events, "same parameter identity stays silent")
equal(3, requests[2].params.context.triggerKind, "content retrigger carries active help")
equal(true, requests[2].params.context.isRetrigger, "active call is marked as retrigger")
equal("table", type(requests[2].params.context.activeSignatureHelp),
  "bounded prior SignatureHelp is forwarded")

set_line("calculate_total(first, ")
signature_help.note_insert_key(",", ",")
vim.api.nvim_exec_autocmds("TextChangedI", { buffer = 0 })
equal(true, vim.wait(1000, function() return #requests == 3 end, 5),
  "comma content change requests next parameter")
equal(2, requests[3].params.context.triggerKind, "comma uses trigger-character context")
equal(",", requests[3].params.context.triggerCharacter, "comma trigger is retained")
equal(true, requests[3].params.context.isRetrigger, "comma is a retrigger")
respond(3, 1)
equal(2, events[#events].payload.activeParameter, "server-selected second parameter published")

-- Start one request, then alter the exact editor snapshot before it responds.
vim.api.nvim_exec_autocmds("CursorMovedI", { buffer = 0 })
equal(true, vim.wait(1000, function() return #requests == 4 end, 5),
  "stale-response request starts")
set_line("calculate_total(first, second, third)", #"calculate_total(fi")
vim.api.nvim_exec_autocmds("TextChangedI", { buffer = 0 })
local before_stale = #events
respond(4, 1)
equal(before_stale, #events, "superseded LSP response is ignored")
equal(true, cancel_count >= 1, "superseded request is cancelled when possible")
equal(true, vim.wait(1000, function() return #requests == 5 end, 5),
  "newest editor generation requests help")
respond(5, 0)
equal(1, events[#events].payload.activeParameter,
  "returning to filled first parameter is announced again")

-- Leaving Insert mode invalidates even a response that was already requested.
vim.api.nvim_exec_autocmds("CursorMovedI", { buffer = 0 })
equal(true, vim.wait(1000, function() return #requests == 6 end, 5),
  "request before InsertLeave starts")
mocked_mode = "n"
vim.api.nvim_exec_autocmds("InsertLeave", { buffer = 0 })
local before_leave = #events
respond(6, 1)
equal(before_leave, #events, "response after InsertLeave is ignored")

vim.api.nvim_del_augroup_by_id(group)
vim.api.nvim_get_mode = original_mode
vim.lsp.buf_request_all = original_request_all
vim.lsp.get_clients = original_get_clients

print(string.format("automatic signature help tests: %d assertions passed", assertions))
vim.cmd("qa!")
