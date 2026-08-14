local M = {}

local function integer(value, minimum)
  return type(value) == "number" and value % 1 == 0 and value >= (minimum or 0)
end

local function set_preferred_virtual_column(preferred)
  local view = vim.fn.winsaveview()
  view.curswant = preferred
  return pcall(vim.fn.winrestview, view)
end

local function utf8_boundary(value, byte_column)
  if type(value) ~= "string" or not integer(byte_column) or byte_column > #value then
    return false
  end
  if byte_column == #value then return true end
  local byte = value:byte(byte_column + 1)
  return byte < 0x80 or byte >= 0xc0
end

local function previous_character_start(value, byte_column)
  if byte_column <= 0 or #value == 0 then return 0 end
  local previous = math.min(byte_column - 1, #value - 1)
  while previous > 0 do
    local byte = value:byte(previous + 1)
    if not byte or byte < 0x80 or byte >= 0xc0 then break end
    previous = previous - 1
  end
  return previous
end

local word_commands = {
  changeWord = "cw",
  deleteWord = "dw",
}

local line_commands = {
  changeLine = "c$",
  deleteLine = "d$",
}

local line_prefixes = {
  routing = "",
  indentation = "^",
  beginning = "0",
}

local function exact_fields(payload, expected)
  local count = 0
  for key in pairs(payload) do
    count = count + 1
    if not expected[key] then return false end
  end
  return count == vim.tbl_count(expected)
end

local function character_at(value, byte_column)
  if byte_column >= #value then return "" end
  local finish = byte_column + 1
  while finish < #value do
    local byte = value:byte(finish + 1)
    if not byte or byte < 0x80 or byte >= 0xc0 then break end
    finish = finish + 1
  end
  return value:sub(byte_column + 1, finish)
end

function M.new(emit)
  assert(type(emit) == "function", "event emitter required")
  local instance = {}

  function instance.route_cursor(payload)
    if type(payload) ~= "table"
      or not integer(payload.bufferId)
      or not integer(payload.windowId)
      or not integer(payload.byteColumn)
      or not integer(payload.changedtick)
      or type(payload.modeRaw) ~= "string"
      or #payload.modeRaw < 1 or #payload.modeRaw > 16
      or vim.api.nvim_get_current_buf() ~= payload.bufferId
      or vim.api.nvim_get_current_win() ~= payload.windowId
      or vim.api.nvim_buf_get_changedtick(payload.bufferId) ~= payload.changedtick
      or vim.api.nvim_get_mode().mode ~= payload.modeRaw then
      return false
    end

    if payload.target == "commandLine" then
      if payload.modeRaw:sub(1, 1) ~= "c"
        or type(payload.commandLine) ~= "string"
        or #payload.commandLine > 16384
        or type(payload.commandLineType) ~= "string"
        or #payload.commandLineType < 1 or #payload.commandLineType > 8
        or vim.fn.getcmdline() ~= payload.commandLine
        or vim.fn.getcmdtype() ~= payload.commandLineType
        or not utf8_boundary(payload.commandLine, payload.byteColumn) then
        return false
      end
      -- setcmdpos() alone only takes effect from a command-line expression.
      -- setcmdline() is the public direct API for atomically retaining the
      -- already verified text while changing its byte position.
      local ok, result = pcall(
        vim.fn.setcmdline,
        payload.commandLine,
        payload.byteColumn + 1
      )
      if not ok or result ~= 0
        or vim.fn.getcmdline() ~= payload.commandLine
        or vim.fn.getcmdpos() ~= payload.byteColumn + 1 then
        return false
      end
      pcall(vim.cmd, "redraw")
      emit("commandLineChanged", "brailleRoute", {
        commandLineType = payload.commandLineType,
      })
      return true
    end

    if payload.target ~= "editor"
      or payload.modeRaw:sub(1, 1) == "c"
      or not integer(payload.line, 1)
      or payload.line > vim.api.nvim_buf_line_count(payload.bufferId) then
      return false
    end
    local line = vim.api.nvim_buf_get_lines(
      payload.bufferId, payload.line - 1, payload.line, true
    )[1] or ""
    if not utf8_boundary(line, payload.byteColumn) then return false end
    local ok = pcall(
      vim.api.nvim_win_set_cursor,
      payload.windowId,
      { payload.line, payload.byteColumn }
    )
    if not ok then return false end
    local preferred = payload.byteColumn == #line
        and vim.fn.strdisplaywidth(line)
      or math.max(0, vim.fn.virtcol({ payload.line, payload.byteColumn + 1 }) - 1)
    set_preferred_virtual_column(preferred)
    pcall(vim.cmd, "redraw")
    emit("cursorMoved", "brailleRoute")
    return true
  end

  function instance.route_action(payload)
    local action = type(payload) == "table" and payload.action or nil
    local word_command = word_commands[action]
    local line_command = line_commands[action]
    local expected = {
      bufferId = true,
      windowId = true,
      line = true,
      byteColumn = true,
      changedtick = true,
      modeRaw = true,
      action = true,
    }
    if line_command then expected.lineStart = true end
    if type(payload) ~= "table"
      or (not word_command and not line_command)
      or not exact_fields(payload, expected)
      or not integer(payload.bufferId)
      or not integer(payload.windowId)
      or not integer(payload.line, 1)
      or not integer(payload.byteColumn)
      or not integer(payload.changedtick)
      or type(payload.modeRaw) ~= "string"
      or #payload.modeRaw < 1 or #payload.modeRaw > 16
      or (payload.modeRaw:sub(1, 1) ~= "n" and payload.modeRaw:sub(1, 1) ~= "i")
      or vim.api.nvim_get_current_buf() ~= payload.bufferId
      or vim.api.nvim_get_current_win() ~= payload.windowId
      or vim.api.nvim_buf_get_changedtick(payload.bufferId) ~= payload.changedtick
      or vim.api.nvim_get_mode().mode ~= payload.modeRaw
      or not vim.bo[payload.bufferId].modifiable
      or vim.bo[payload.bufferId].readonly
      or payload.line > vim.api.nvim_buf_line_count(payload.bufferId) then
      return false
    end
    local cursor = vim.api.nvim_win_get_cursor(payload.windowId)
    if cursor[1] ~= payload.line or cursor[2] ~= payload.byteColumn then return false end
    local line = vim.api.nvim_buf_get_lines(
      payload.bufferId, payload.line - 1, payload.line, true
    )[1] or ""
    if not utf8_boundary(line, payload.byteColumn) then return false end

    local command
    if word_command then
      local character = character_at(line, payload.byteColumn)
      if character == "" or vim.fn.match(character, [[\s]]) >= 0 then return false end
      command = word_command
    else
      local prefix = line_prefixes[payload.lineStart]
      if not prefix then return false end
      if payload.lineStart == "routing" and payload.byteColumn >= #line then
        return false
      end
      command = prefix .. line_command
    end

    local insert_mode = payload.modeRaw:sub(1, 1) == "i"
    if insert_mode then
      local return_to_routed_character = payload.byteColumn > 0
        and (word_command or payload.lineStart == "routing")
      command = "<C-\\><C-N>"
        .. (return_to_routed_character and "l" or "")
        .. command
      if action:sub(1, 6) == "delete" then command = command .. "gi" end
    end
    local keys = vim.api.nvim_replace_termcodes(command, true, false, true)
    return pcall(vim.api.nvim_feedkeys, keys, "n", false)
  end

  function instance.move_line(payload)
    if type(payload) ~= "table"
      or not integer(payload.bufferId)
      or not integer(payload.windowId)
      or not integer(payload.line, 1)
      or not integer(payload.changedtick)
      or not integer(payload.preferredVirtualColumn)
      or payload.preferredVirtualColumn > 2147483647
      or type(payload.modeRaw) ~= "string"
      or #payload.modeRaw < 1 or #payload.modeRaw > 16
      or payload.modeRaw:sub(1, 1) == "c"
      or payload.modeRaw:sub(1, 1) == "t"
      or (payload.direction ~= "previous" and payload.direction ~= "next")
      or (
        payload.targetColumn ~= "preferred"
        and payload.targetColumn ~= "start"
        and payload.targetColumn ~= "end"
      )
      or vim.api.nvim_get_current_buf() ~= payload.bufferId
      or vim.api.nvim_get_current_win() ~= payload.windowId
      or vim.api.nvim_buf_get_changedtick(payload.bufferId) ~= payload.changedtick
      or vim.api.nvim_get_mode().mode ~= payload.modeRaw then
      return false
    end
    local cursor = vim.api.nvim_win_get_cursor(payload.windowId)
    if cursor[1] ~= payload.line then return false end
    local delta = payload.direction == "previous" and -1 or 1
    local target_line = payload.line + delta
    if target_line < 1 or target_line > vim.api.nvim_buf_line_count(payload.bufferId) then
      return false
    end
    local line = vim.api.nvim_buf_get_lines(
      payload.bufferId, target_line - 1, target_line, true
    )[1] or ""
    local preferred = payload.preferredVirtualColumn
    local target_column = 0
    if payload.targetColumn == "start" then
      preferred = 0
    elseif payload.targetColumn == "end" then
      if #line == 0 then
        preferred = 0
      elseif payload.modeRaw:sub(1, 1) == "i" then
        target_column = #line
        preferred = vim.fn.strdisplaywidth(line)
      else
        target_column = previous_character_start(line, #line)
        preferred = math.max(0, vim.fn.virtcol({ target_line, target_column + 1 }) - 1)
      end
    elseif #line > 0 then
      if payload.modeRaw:sub(1, 1) == "i" and preferred >= vim.fn.strdisplaywidth(line) then
        target_column = #line
      else
        local one_based = vim.fn.virtcol2col(payload.windowId, target_line, preferred + 1)
        target_column = one_based > 0 and one_based - 1 or #line
      end
    end
    local ok = pcall(
      vim.api.nvim_win_set_cursor,
      payload.windowId,
      { target_line, target_column }
    )
    if not ok then return false end
    set_preferred_virtual_column(preferred)
    pcall(vim.cmd, "redraw")
    emit("cursorMoved", "brailleLineNavigation")
    return true
  end

  return instance
end

return M
