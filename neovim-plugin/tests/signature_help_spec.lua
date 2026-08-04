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

local resolved = {
  name = "calculate_total",
  openLine = 7,
  openByteColumn = 15,
}
local automatic = {
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
      activeParameter = 1,
      parameters = {
        { label = "subtotal: float" },
        { label = "tax: float" },
      },
    },
  },
  activeSignature = 0,
  activeParameter = 0,
}
signature_help._test_clear_automatic()
event_count = #events
equal(true, signature_help._test_publish_automatic(automatic, resolved, 9),
  "initial automatic parameter emitted")
equal(event_count + 1, #events, "one initial automatic event")
equal("activeParameterChanged", events[#events].type, "automatic event type")
equal("callEntered", events[#events].payload.hintReason, "initial call reason")
equal("price: float", events[#events].payload.parameter, "initial parameter label")
equal(3, events[#events].payload.parameterCount, "selected signature parameter count")
equal(false, signature_help._test_publish_automatic(automatic, resolved, 9),
  "same argument movement is silent")
equal(event_count + 1, #events, "duplicate automatic parameter suppressed")

automatic.activeParameter = 1
equal(true, signature_help._test_publish_automatic(automatic, resolved, 9),
  "moving to second parameter emits")
equal("parameterChanged", events[#events].payload.hintReason, "parameter change reason")
equal(2, events[#events].payload.activeParameter, "second parameter identity")
automatic.activeParameter = 0
equal(true, signature_help._test_publish_automatic(automatic, resolved, 9),
  "returning to already filled first parameter emits again")
equal(1, events[#events].payload.activeParameter, "returned first parameter identity")

automatic.activeSignature = 1
automatic.activeParameter = 0
equal(true, signature_help._test_publish_automatic(automatic, resolved, 9),
  "overload change emits")
equal("signatureChanged", events[#events].payload.hintReason, "overload change reason")
equal(2, events[#events].payload.signatureIndex, "active overload index")
equal(2, events[#events].payload.activeParameter,
  "signature-level active parameter overrides global index")
equal("tax: float", events[#events].payload.parameter,
  "parameter belongs only to selected overload")

local same_labels = {
  signatures = {{
    label = "same(value, value)",
    parameters = {{ label = "value" }, { label = "value" }},
  }},
  activeParameter = 0,
}
signature_help._test_clear_automatic()
equal(true, signature_help._test_publish_automatic(same_labels, resolved, 9),
  "first duplicate label emitted")
same_labels.activeParameter = 1
equal(true, signature_help._test_publish_automatic(same_labels, resolved, 9),
  "position identity emits even when parameter labels match")
equal(2, events[#events].payload.activeParameter, "same-label position retained")

local invalid = vim.deepcopy(same_labels)
invalid.activeParameter = 2
equal(false, signature_help._test_publish_automatic(invalid, resolved, 9),
  "out-of-range active parameter rejected")
equal(nil, signature_help._test_first_result({
  [1] = { result = { signatures = {} } },
  [2] = { result = { signatures = "invalid" } },
}), "invalid provider results rejected")
local selected_result = signature_help._test_first_result({
  [10] = { result = { signatures = {{ label = "later()" }} } },
  [2] = { result = { signatures = {{ label = "first()" }} } },
})
equal("first()", selected_result.signatures[1].label, "numeric client order is deterministic")

local many = { signatures = {}, activeParameter = 0 }
for signature_index = 1, 101 do
  local parameters = {}
  for parameter_index = 1, 101 do
    parameters[#parameters + 1] = { label = "p" .. parameter_index }
  end
  many.signatures[#many.signatures + 1] = {
    label = "overload" .. signature_index .. "(" .. string.rep("x", 3000) .. ")",
    parameters = parameters,
  }
end
signature_help._test_clear_automatic()
equal(true, signature_help._test_publish_automatic(many, resolved, 9),
  "bounded large response still publishes")
equal(100, events[#events].payload.signatureCount, "signature count bounded")
equal(100, events[#events].payload.parameterCount, "parameter count bounded")
equal(true, #events[#events].payload.signature <= 2048, "signature text bounded")

vim.lsp.handlers[method] = original_handler
vim.lsp.buf_request_all = original_request_all

print(string.format("signature help tests: %d assertions passed", assertions))
vim.cmd("qa!")
