if vim.g.loaded_nvim_nvda_access then
  return
end
vim.g.loaded_nvim_nvda_access = true

require("nvim_nvda").setup()
local session = require("nvim_nvda.session")
session.start()
vim.api.nvim_create_user_command("NvimNvdaSessionName", function(options)
  local name = session.set_name(options.args)
  if name == "" then
    vim.notify("Neovim NVDA session name cleared")
  else
    vim.notify("Neovim NVDA session name: " .. name)
  end
end, { nargs = "*", desc = "Set the accessible name of this Neovim session" })
