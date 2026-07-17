local M = {}

function M.check()
  vim.health.start("Neovim Access Link file-manager adapters")
  local diagnostics = require("nvim_nvda.file_manager").diagnostics()
  if #diagnostics == 0 then
    vim.health.ok("No file-manager adapter has run in this Neovim process")
    return
  end
  for _, value in ipairs(diagnostics) do
    local details = string.format(
      "%s: %d failures, %d slow calls, %d cooldowns",
      value.name, value.failureCount, value.slowCallCount, value.cooldownCount
    )
    if value.disabledBuffers > 0 then
      vim.health.warn(details .. string.format(
        "; temporarily disabled in %d buffer(s)", value.disabledBuffers
      ))
    elseif value.failureCount > 0 or value.slowCallCount > 0 then
      vim.health.warn(details)
    else
      vim.health.ok(details)
    end
  end
  vim.health.info(
    "Optional adapters must be synchronous, bounded, and free of I/O and polling; "
      .. "three repeated errors or calls over 5 ms trigger a five-second per-buffer cooldown"
  )
end

return M
