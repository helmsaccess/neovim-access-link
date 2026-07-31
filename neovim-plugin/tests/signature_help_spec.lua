local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local method = "textDocument/signatureHelp"
local original_handler = vim.lsp.handlers[method]
local original_request_all = vim.lsp.buf_request_all
local legacy_calls = 0
local request_calls = {}
vim.lsp.handlers[method] = function()
  legacy_calls = legacy_calls + 1
  return "legacy-result"
end
vim.lsp.buf_request_all = function(bufnr, requested_method, params, handler)
  request_calls[#request_calls + 1] = { bufnr = bufnr, method = requested_method, params = params }
  if requested_method == method then
    handler({
      [2] = { result = {
        signatures = {{ label = "second(other)", parameters = {{ label = "other" }} }},
      } },
      [1] = { result = {
        signatures = {
          {
            label = "first(😀x, y)",
            activeParameter = 0,
            parameters = {{ label = { 6, 9 } }, { label = "y" }},
          },
          { label = "first(value)", parameters = {{ label = "value" }} },
        },
        activeSignature = 0,
      } },
    }, { bufnr = vim.api.nvim_get_current_buf() })
  else
    handler({ passthrough = true })
  end
  return "cancel"
end

package.loaded["nvim_nvda.signature_help"] = nil
local signature_help = require("nvim_nvda.signature_help")
local events = {}
signature_help.setup(function(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end)

local legacy_result = vim.lsp.handlers[method](nil, {
  signatures = {{
    label = "call(😀x, y)",
    parameters = {{ label = { 5, 8 } }, { label = "y" }},
  }},
  activeSignature = 0,
  activeParameter = 0,
}, { bufnr = vim.api.nvim_get_current_buf() }, {})
equal("legacy-result", legacy_result, "legacy handler return preserved")
equal(1, legacy_calls, "legacy handler called")
equal("signatureChanged", events[#events].type, "legacy signature emitted")
equal("😀x", events[#events].payload.parameter, "UTF-16 parameter range decoded")

local event_count = #events
vim.lsp.handlers[method]({ message = "simulated signature failure" }, {
  signatures = {{ label = "must_not_emit()" }},
}, { bufnr = vim.api.nvim_get_current_buf() }, {})
equal(event_count, #events, "legacy signature error is ignored")
vim.lsp.handlers[method](nil, {
  signatures = {{ label = "other_buffer()" }},
}, { bufnr = vim.api.nvim_get_current_buf() + 1 }, {})
equal(event_count, #events, "legacy signature for another buffer is ignored")

vim.lsp.handlers[method](nil, {
  signatures = {{
    label = "call(😀x, y)",
    parameters = {{ label = { 5, 8 } }, { label = "y" }},
  }},
  activeSignature = 0,
  activeParameter = 0,
}, { bufnr = vim.api.nvim_get_current_buf() }, {})
equal(event_count, #events, "duplicate legacy signature suppressed")

local callback_results
local cancel = vim.lsp.buf_request_all(0, method, { position = true }, function(results)
  callback_results = results
end)
equal("cancel", cancel, "request-all return preserved")
equal(true, callback_results[1].result ~= nil, "request-all handler preserved")
equal("first(😀x, y)", events[#events].payload.signature, "first sorted client selected")
equal("😀x", events[#events].payload.parameter, "combined UTF-16 parameter")
equal(1, events[#events].payload.signatureIndex, "combined active signature index")
equal(3, events[#events].payload.signatureCount, "combined signature count")

local passthrough
vim.lsp.buf_request_all(4, "textDocument/hover", {}, function(results)
  passthrough = results.passthrough
end)
equal(true, passthrough, "unrelated request unchanged")
equal("textDocument/hover", request_calls[#request_calls].method, "unrelated method forwarded")

signature_help._test_combined_results({})
equal("signatureClosed", events[#events].type, "empty result closes signature")
local closed_count = #events
signature_help._test_combined_results({})
equal(closed_count, #events, "duplicate close suppressed")

local text = require("nvim_nvda.text")
equal("😀x", text.utf16_slice("a😀xyz", 1, 4, 512), "UTF-16 slice")
equal("", text.utf16_slice("a😀xyz", 2, 4, 512), "split surrogate rejected")
equal("", text.utf16_slice("\255bad", 0, 1, 512), "invalid UTF-8 rejected")

vim.lsp.handlers[method] = original_handler
vim.lsp.buf_request_all = original_request_all

print(string.format("signature help tests: %d assertions passed", assertions))
vim.cmd("qa!")
