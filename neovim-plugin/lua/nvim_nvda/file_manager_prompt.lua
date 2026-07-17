local M = {}

-- Oil exposes completion events for accepted actions, but its confirmation
-- float has no public prompt event. Keep this last-resort parser deliberately
-- narrow: the plugin's dedicated float filetype, fixed action verbs, and a
-- count only. Never carry the rendered paths or names into the prompt.
local oil_actions = {
  CHANGE = "change",
  COPY = "copy",
  CREATE = "create",
  DELETE = "delete",
  MOVE = "move",
}

function M.oil_confirmation(lines)
  if type(lines) ~= "table" then return nil end
  local count = 0
  local single_action
  local multiple_actions = false
  for index = 1, math.min(#lines, 200) do
    local line = lines[index]
    local action = type(line) == "string" and oil_actions[line:match("^([A-Z]+)%s")] or nil
    if action then
      count = count + 1
      if single_action and single_action ~= action then multiple_actions = true end
      single_action = single_action or action
    end
  end
  if count == 0 then return nil end
  local summary = count == 1 and (single_action .. " 1 item")
    or (not multiple_actions and single_action and (single_action .. " " .. count .. " items"))
    or (tostring(count) .. " file actions")
  return {
    promptKind = "confirm",
    promptClass = single_action == "delete" and "delete" or "other",
    prompt = "Oil confirmation, " .. summary .. ". Y yes, N no",
    itemCount = 2,
  }
end

function M.current_oil_confirmation()
  if vim.bo.filetype ~= "oil_preview" then return nil end
  local ok, config = pcall(vim.api.nvim_win_get_config, 0)
  if not ok or type(config) ~= "table" or config.relative == "" then return nil end
  local lines_ok, lines = pcall(vim.api.nvim_buf_get_lines, 0, 0, 200, false)
  return lines_ok and M.oil_confirmation(lines) or nil
end

return M
