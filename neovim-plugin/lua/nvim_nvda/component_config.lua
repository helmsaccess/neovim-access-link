local M = {}

local defaults = {
  format = 1,
  sessionClaim = { neovimKey = "<F12>", nvdaGesture = "kb:f12" },
}

local function default_path()
  local source = debug.getinfo(1, "S").source:sub(2)
  return vim.fs.dirname(vim.fs.dirname(vim.fs.dirname(source)))
    .. "/config/linux-components.json"
end

local function valid_function_key(value)
  if type(value) ~= "string" then return false end
  local number = tonumber(value:match("^<F(%d+)>$"))
  return number ~= nil and number >= 1 and number <= 24
end

function M.load(path)
  path = path or default_path()
  local ok, lines = pcall(vim.fn.readfile, path)
  if not ok then return vim.deepcopy(defaults) end
  local decoded_ok, value = pcall(vim.json.decode, table.concat(lines, "\n"))
  if not decoded_ok or type(value) ~= "table" or value.format ~= 1 then
    return vim.deepcopy(defaults)
  end
  local claim = value.sessionClaim
  if type(claim) ~= "table" or not valid_function_key(claim.neovimKey) then
    return vim.deepcopy(defaults)
  end
  local number = claim.neovimKey:match("^<F(%d+)>$")
  if claim.nvdaGesture ~= "kb:f" .. number then
    return vim.deepcopy(defaults)
  end
  return value
end

return M
