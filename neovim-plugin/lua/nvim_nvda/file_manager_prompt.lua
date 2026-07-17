local M = {}

-- Oil exposes completion events for accepted actions, but its confirmation
-- float has no public prompt event. Keep this last-resort parser deliberately
-- narrow: the plugin's dedicated float filetype, fixed action verbs, and a
-- count only. Never carry the rendered paths or names into the prompt.
local oil_actions = {
  CHANGE = { summary = "change" },
  COPY = { summary = "copy or duplicate" },
  CREATE = { summary = "create" },
  DELETE = { summary = "delete", destructive = true },
  MOVE = { summary = "rename or move" },
  PURGE = { summary = "permanently delete", destructive = true },
  RESTORE = { summary = "restore" },
  TRASH = { summary = "move to trash", destructive = true },
}

function M.oil_confirmation(lines)
  if type(lines) ~= "table" then return nil end
  local count = 0
  local single_action
  local multiple_actions = false
  local destructive = false
  for index = 1, math.min(#lines, 200) do
    local line = lines[index]
    -- Oil deliberately indents MOVE/COPY and trash actions in its private
    -- preview. Only whitespace plus a fixed allowlisted verb is accepted; the
    -- paths following it are counted but never returned.
    local verb = type(line) == "string" and line:match("^[ \t]*([A-Z]+)[ \t]") or nil
    local action = verb and oil_actions[verb] or nil
    if action then
      count = count + 1
      if single_action and single_action ~= action.summary then multiple_actions = true end
      single_action = single_action or action.summary
      destructive = destructive or action.destructive == true
    end
  end
  if count == 0 then return nil end
  local summary = count == 1 and (single_action .. " 1 item")
    or (not multiple_actions and single_action and (single_action .. " " .. count .. " items"))
    or (tostring(count) .. " file actions")
  return {
    promptKind = "confirm",
    promptClass = destructive and "delete" or "other",
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
