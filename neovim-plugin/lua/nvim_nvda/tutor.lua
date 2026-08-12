local M = {}
local observed = {}

local function tutor_buffer(buf)
  return vim.api.nvim_buf_is_valid(buf) and vim.bo[buf].filetype == "tutor"
end

local function extmark_status(buf, line)
  local namespace = vim.api.nvim_get_namespaces()["nvim.tutor.mark"]
  if not namespace then return nil end
  local marks = vim.api.nvim_buf_get_extmarks(
    buf,
    namespace,
    { line - 1, 0 },
    { line - 1, -1 },
    { details = true }
  )
  if #marks ~= 1 then return nil end
  local details = marks[1][4]
  if details.sign_hl_group == "tutorOK" and details.sign_text == "✓ " then return "correct" end
  if details.sign_hl_group == "tutorX" and details.sign_text == "✗ " then return "incorrect" end
  return nil
end

local function legacy_sign_status(buf, line)
  local placed = vim.fn.sign_getplaced(buf, { lnum = line })
  local signs = type(placed) == "table" and placed[1] and placed[1].signs or nil
  if type(signs) ~= "table" or #signs ~= 1 then return nil end
  if signs[1].name == "tutorok" then return "correct" end
  if signs[1].name == "tutorbad" then return "incorrect" end
  return nil
end

local function read_status(buf, line)
  if type(buf) ~= "number" or type(line) ~= "number" or line < 1 or not tutor_buffer(buf) then
    return nil
  end
  return extmark_status(buf, line) or legacy_sign_status(buf, line)
end

function M.status(buf, line)
  local status = read_status(buf, line)
  if status then
    observed[buf] = observed[buf] or {}
    observed[buf][line] = status
  end
  return status
end

function M.text_changed(event, emit)
  if not tutor_buffer(event.buf) then return end
  local line = vim.api.nvim_win_get_cursor(0)[1]
  local before = observed[event.buf] and observed[event.buf][line] or nil
  -- Neovim's own Tutor callback updates the native mark during this event.
  -- Read it afterwards and publish only an observed status transition.
  vim.schedule(function()
    if not tutor_buffer(event.buf)
      or vim.api.nvim_get_current_buf() ~= event.buf
      or vim.api.nvim_win_get_cursor(0)[1] ~= line then
      return
    end
    local after = read_status(event.buf, line)
    if after then
      observed[event.buf] = observed[event.buf] or {}
      observed[event.buf][line] = after
    end
    if before and after and after ~= before then
      emit("tutorExerciseChanged", event.event, { tutorExerciseStatus = after })
    end
  end)
end

function M.setup(group)
  vim.api.nvim_create_autocmd("BufWipeout", {
    group = group,
    callback = function(event) observed[event.buf] = nil end,
  })
end

return M
