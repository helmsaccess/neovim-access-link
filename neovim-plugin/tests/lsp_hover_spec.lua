local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local method = "textDocument/hover"
local original_handler = vim.lsp.handlers[method]
local original_request_all = vim.lsp.buf_request_all
local legacy_calls = 0
vim.lsp.handlers[method] = function()
  legacy_calls = legacy_calls + 1
  return "legacy-hover"
end
vim.lsp.buf_request_all = function(bufnr, requested_method, params, handler)
  if requested_method == method then
    handler({
      [2] = { result = { contents = "Second client detail" } },
      [1] = { result = {
        contents = { kind = "markdown", value = "## `print(value)`\n\nPrint one value." },
      } },
    }, { bufnr = vim.api.nvim_get_current_buf() })
  else
    handler({ passthrough = true })
  end
  return "cancel-hover"
end

package.loaded["nvim_nvda.lsp_hover"] = nil
local hover = require("nvim_nvda.lsp_hover")
local events = {}
hover.setup(function(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end)

local legacy_result = vim.lsp.handlers[method](nil, {
  contents = {
    { language = "lua", value = "vim.api.nvim_get_current_buf()" },
    "Returns the current buffer.",
  },
}, { bufnr = vim.api.nvim_get_current_buf() }, {})
equal("legacy-hover", legacy_result, "legacy return preserved")
equal(1, legacy_calls, "legacy handler called")
equal("hoverChanged", events[#events].type, "legacy hover emitted")
equal("vim.api.nvim_get_current_buf()", events[#events].payload.summary, "legacy summary")
equal(1, events[#events].payload.sourceCount, "legacy source count")

local event_count = #events
vim.lsp.handlers[method]({ message = "simulated hover failure" }, {
  contents = "must not be emitted",
}, { bufnr = vim.api.nvim_get_current_buf() }, {})
equal(event_count, #events, "legacy hover error is ignored")
vim.lsp.handlers[method](nil, {
  contents = "other buffer",
}, { bufnr = vim.api.nvim_get_current_buf() + 1 }, {})
equal(event_count, #events, "legacy hover for another buffer is ignored")

hover._test_single_result({
  contents = {
    { language = "lua", value = "vim.api.nvim_get_current_buf()" },
    "Returns the current buffer.",
  },
})
equal(event_count, #events, "duplicate hover suppressed")

local callback_results
local cancel = vim.lsp.buf_request_all(0, method, {}, function(results)
  callback_results = results
end)
equal("cancel-hover", cancel, "request-all return preserved")
equal(true, callback_results[1].result ~= nil, "request-all callback preserved")
equal("print(value)", events[#events].payload.summary, "markdown heading simplified")
equal(2, events[#events].payload.sourceCount, "combined source count")
equal(true, events[#events].payload.documentation:find(
  "Second client detail", 1, true
) ~= nil, "combined documentation")

local passthrough
vim.lsp.buf_request_all(3, "textDocument/signatureHelp", {}, function(results)
  passthrough = results.passthrough
end)
equal(true, passthrough, "unrelated request unchanged")

hover._test_combined_results({})
equal("hoverClosed", events[#events].type, "empty result closes hover")
local closed_count = #events
hover._test_combined_results({})
equal(closed_count, #events, "duplicate close suppressed")

vim.lsp.handlers[method] = original_handler
vim.lsp.buf_request_all = original_request_all

print(string.format("LSP hover tests: %d assertions passed", assertions))
vim.cmd("qa!")
