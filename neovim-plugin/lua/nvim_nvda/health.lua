local M = {}

function M.check()
  vim.health.start("Neovim Access Link file-manager adapters")
  local diagnostics = require("nvim_nvda.file_manager").diagnostics()
  if #diagnostics == 0 then
    vim.health.ok("No file-manager adapter has run in this Neovim process")
  else
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
  end
  vim.health.info(
    "Optional adapters must be synchronous, bounded, and free of I/O and polling; "
      .. "three repeated errors or calls over 5 ms trigger a five-second per-buffer cooldown"
  )

  vim.health.start("Neovim Access Link completion adapters")
  local completion = require("nvim_nvda.completion_adapters").diagnostics()
  local details = string.format(
    "%d errors, %d slow ticks, maximum %.2f ms, %d ms interval",
    completion.errorCount,
    completion.slowTickCount,
    completion.maximumTickNanoseconds / 1000000,
    completion.pollIntervalMilliseconds
  )
  if completion.activeKind then
    details = string.format(
      "%s active through %s; %s",
      completion.activeKind, completion.apiVariant or "unknown API", details
    )
  end
  if completion.errorCount > 0 or completion.slowTickCount > 0 then
    vim.health.warn(details)
  else
    vim.health.ok(details)
  end
end

return M
