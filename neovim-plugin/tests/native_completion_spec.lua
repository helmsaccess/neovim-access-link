local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path
local native_completion = dofile(
  root .. "/neovim-plugin/lua/nvim_nvda/native_completion.lua"
)
local menu = dofile(root .. "/neovim-plugin/lua/nvim_nvda/menu.lua")

local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local function completion_info(label, documentation)
  return {
    mode = "omni", pum_visible = true, selected = 0,
    items = {
      {
        word = label,
        user_data = {
          nvim = {
            lsp = {
              client_id = 17,
              completion_item = {
                label = label,
                kind = 3,
                documentation = documentation,
              },
            },
          },
        },
      },
    },
  }
end

local original_get_client = vim.lsp.get_client_by_id
local original_pumvisible = vim.fn.pumvisible
local original_complete_info = vim.fn.complete_info
local visible = true
local current_info = completion_info("calculate_total")
local requests = {}
local cancellations = {}
local next_request_id = 40
local client = {
  server_capabilities = {
    completionProvider = { resolveProvider = true },
  },
  request = function(_, method, params, handler, bufnr)
    next_request_id = next_request_id + 1
    requests[#requests + 1] = {
      method = method,
      params = params,
      handler = handler,
      bufnr = bufnr,
      id = next_request_id,
    }
    return true, next_request_id
  end,
  cancel_request = function(_, request_id)
    cancellations[#cancellations + 1] = request_id
    return true
  end,
}
vim.lsp.get_client_by_id = function(client_id)
  return client_id == 17 and client or nil
end
vim.fn.pumvisible = function() return visible and 1 or 0 end
vim.fn.complete_info = function() return vim.deepcopy(current_info) end

local model = menu.new()
model:update(current_info)
local events = {}
equal(true, native_completion.resolve(current_info, function(value)
  for _, event in ipairs(model:update(value)) do
    events[#events + 1] = event
  end
end, 23), "resolve request started")
equal("completionItem/resolve", requests[1].method, "public LSP method")
equal("calculate_total", requests[1].params.label, "selected raw LSP item")
equal(23, requests[1].bufnr, "request buffer")

requests[1].handler(nil, {
  label = "calculate_total",
  kind = 3,
  detail = "calculate_total(price: float, quantity: int = 1) -> float",
  documentation = {
    kind = "markdown",
    value = "Return the total price for the requested quantity.",
  },
})
equal("menuItemUpdated", events[#events].type, "resolved detail is a silent update")
equal(
  "Return the total price for the requested quantity.",
  events[#events].payload.item.documentation,
  "resolved documentation reaches the accessible menu model"
)
equal(1, native_completion.diagnostics().resolveCount, "resolve diagnostics")

local documented = completion_info("cast", { kind = "markdown", value = "Cast a value." })
equal(false, native_completion.resolve(documented, function() end, 23),
  "existing documentation needs no resolve")
equal(1, #requests, "existing documentation sends no request")

current_info = completion_info("calculate_total")
native_completion.resolve(current_info, function() end, 23)
local stale_request = requests[#requests]
native_completion.resolve(current_info, function() end, 23)
equal(stale_request.id, cancellations[#cancellations], "new selection cancels stale request")
local resolves_before_stale = native_completion.diagnostics().resolveCount
stale_request.handler(nil, {
  documentation = { kind = "markdown", value = "stale documentation" },
})
equal(resolves_before_stale, native_completion.diagnostics().resolveCount,
  "stale response is ignored")

visible = false
local hidden_request = requests[#requests]
hidden_request.handler(nil, {
  documentation = { kind = "markdown", value = "hidden documentation" },
})
equal(resolves_before_stale, native_completion.diagnostics().resolveCount,
  "hidden menu response is ignored")

visible = true
native_completion.resolve(current_info, function() end, 23)
local errors_before = native_completion.diagnostics().errorCount
requests[#requests].handler({ message = "simulated resolve failure" }, nil)
equal(errors_before + 1, native_completion.diagnostics().errorCount,
  "resolve failure is contained")

native_completion.stop()
vim.lsp.get_client_by_id = original_get_client
vim.fn.pumvisible = original_pumvisible
vim.fn.complete_info = original_complete_info

print(string.format("native completion specs passed: %d assertions", assertions))
