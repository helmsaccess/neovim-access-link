local M = {}

local MAX_ITEMS = 128
local MAX_TEXT_BYTES = 65536
local MAX_ITEM_BYTES = 4096

local function bounded_utf8(value, maximum)
  if type(value) ~= "string" or #value > maximum then return nil end
  return value
end

function M.spell_suggestions(text)
  if not bounded_utf8(text, MAX_TEXT_BYTES) then return nil end
  local items = {}
  local started = false
  local native_prompt_seen = false
  for line in (text .. "\n"):gmatch("(.-)\n") do
    local number, item = line:match('^%s*(%d+)%s+"([^"]*)"')
    if number then
      if native_prompt_seen then return nil end
      local expected = #items + 1
      if tonumber(number) ~= expected or item == ""
        or not bounded_utf8(item, MAX_ITEM_BYTES) or expected > MAX_ITEMS then
        return nil
      end
      started = true
      items[expected] = item
    elseif started and line:find("<Enter>", 1, true) and line:match(":%s*$") then
      if native_prompt_seen then return nil end
      native_prompt_seen = true
    elseif started and line:match("%S") then
      return nil
    end
  end
  return #items > 0 and items or nil
end

return M
