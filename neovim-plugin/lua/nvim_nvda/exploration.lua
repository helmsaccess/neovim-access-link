local M = {}

local MAX_INTEGER = 2147483647
local MAX_REPEAT = 64
local MAX_SCAN_LINES = 256
local MAX_SCAN_BYTES = 65536
local MAX_RESULT_BYTES = 16384
local modern_string_indices = vim.fn.has("nvim-0.11") == 1

local actions = {
  characterLeft = { unit = "character", kind = "character", direction = -1 },
  characterRight = { unit = "character", kind = "character", direction = 1 },
  lineUp = { unit = "line", kind = "line", direction = -1 },
  lineDown = { unit = "line", kind = "line", direction = 1 },
  wordPrevious = { unit = "word", kind = "word", direction = -1 },
  wordNext = { unit = "word", kind = "word", direction = 1 },
}

local active

local function integer(value)
  return type(value) == "number" and value >= 0 and value <= MAX_INTEGER
    and value == math.floor(value)
end

local function safe_integer(value)
  return integer(value) and value or -1
end

local function character_column(line, byte_column)
  if modern_string_indices then
    return vim.str_utfindex(line, "utf-32", byte_column, false)
  end
  return vim.str_utfindex(line, byte_column)
end

local function character_at(line, byte_column)
  if byte_column < 0 or byte_column >= #line then return "" end
  local finish = byte_column + 1
  while finish < #line do
    local byte = line:byte(finish + 1)
    if not byte or byte < 0x80 or byte >= 0xc0 then break end
    finish = finish + 1
  end
  return line:sub(byte_column + 1, finish)
end

local function next_character_start(line, byte_column)
  if byte_column >= #line then return #line end
  local next_column = byte_column + #character_at(line, byte_column)
  return math.min(next_column, #line)
end

local function previous_character_start(line, byte_column)
  if byte_column <= 0 then return 0 end
  local previous = math.min(byte_column - 1, #line - 1)
  while previous > 0 do
    local byte = line:byte(previous + 1)
    if not byte or byte < 0x80 or byte >= 0xc0 then break end
    previous = previous - 1
  end
  return previous
end

local function last_character_start(line)
  return #line == 0 and 0 or previous_character_start(line, #line)
end

local function valid_byte_column(line, byte_column)
  if not integer(byte_column) or byte_column > #line then return false end
  if byte_column == #line then return true end
  local byte = line:byte(byte_column + 1)
  return byte ~= nil and (byte < 0x80 or byte >= 0xc0)
end

local function current_line(buffer, line_number)
  return vim.api.nvim_buf_get_lines(buffer, line_number - 1, line_number, true)[1] or ""
end

local function virtual_column(window, line_number, byte_column)
  if #current_line(vim.api.nvim_win_get_buf(window), line_number) == 0 then return 0 end
  return math.max(0, vim.fn.virtcol({ line_number, byte_column + 1 }) - 1)
end

local function byte_column_for_virtual(window, buffer, line_number, desired)
  local line = current_line(buffer, line_number)
  if line == "" then return 0 end
  local one_based = vim.fn.virtcol2col(window, line_number, desired + 1)
  if type(one_based) ~= "number" or one_based <= 0 then return last_character_start(line) end
  local byte_column = one_based - 1
  if byte_column >= #line then return last_character_start(line) end
  return valid_byte_column(line, byte_column) and byte_column or previous_character_start(line, byte_column)
end

local function keyword_character(character)
  return character ~= "" and vim.fn.match(character, [[\k]]) >= 0
end

local function whitespace_character(character)
  return character ~= "" and vim.fn.match(character, [[\s]]) >= 0
end

local function word_at(buffer, line_number, byte_column)
  local line = current_line(buffer, line_number)
  local character = character_at(line, byte_column)
  if character == "" or whitespace_character(character) then return "" end
  if not keyword_character(character) then return character end
  local first = byte_column
  while first > 0 do
    local candidate = previous_character_start(line, first)
    if not keyword_character(character_at(line, candidate)) then break end
    first = candidate
  end
  local finish = next_character_start(line, byte_column)
  while finish < #line and keyword_character(character_at(line, finish)) do
    finish = next_character_start(line, finish)
  end
  return line:sub(first + 1, finish)
end

local function result(payload, ok, code, extra)
  local value = {
    requestId = type(payload) == "table" and safe_integer(payload.requestId) or -1,
    explorationId = type(payload) == "table" and safe_integer(payload.explorationId) or -1,
    actionIndex = type(payload) == "table" and safe_integer(payload.actionIndex) or -1,
    action = type(payload) == "table" and actions[payload.action] and payload.action or "",
    ok = ok,
    resultCode = code,
  }
  for key, item in pairs(extra or {}) do value[key] = item end
  return value
end

local function valid_request(payload)
  if type(payload) ~= "table" or not actions[payload.action] then return false end
  for _, name in ipairs({
    "requestId", "explorationId", "actionIndex", "bufferId", "windowId",
    "tabpageId", "changedtick", "cursorLine", "cursorByteColumn", "cursorVirtualColumn",
  }) do
    if not integer(payload[name]) then return false end
  end
  if payload.requestId == 0 or payload.explorationId == 0
    or payload.actionIndex == 0 or payload.cursorLine == 0 then
    return false
  end
  local count = payload.count == nil and 1 or payload.count
  return integer(count) and count >= 1 and count <= MAX_REPEAT
    and type(payload.modeRaw) == "string" and #payload.modeRaw > 0 and #payload.modeRaw <= 16
end

local function current_context_matches(payload)
  if not vim.api.nvim_buf_is_valid(payload.bufferId)
    or not vim.api.nvim_win_is_valid(payload.windowId)
    or not vim.api.nvim_tabpage_is_valid(payload.tabpageId) then
    return false
  end
  if vim.api.nvim_get_current_buf() ~= payload.bufferId
    or vim.api.nvim_get_current_win() ~= payload.windowId
    or vim.api.nvim_get_current_tabpage() ~= payload.tabpageId
    or vim.api.nvim_buf_get_changedtick(payload.bufferId) ~= payload.changedtick
    or vim.api.nvim_get_mode().mode ~= payload.modeRaw then
    return false
  end
  local cursor = vim.api.nvim_win_get_cursor(payload.windowId)
  if cursor[1] ~= payload.cursorLine or cursor[2] ~= payload.cursorByteColumn then return false end
  local line = current_line(payload.bufferId, cursor[1])
  return valid_byte_column(line, cursor[2])
    and virtual_column(payload.windowId, cursor[1], cursor[2]) == payload.cursorVirtualColumn
end

local function same_origin(payload, state)
  for _, name in ipairs({
    "bufferId", "windowId", "tabpageId", "changedtick", "modeRaw",
    "cursorLine", "cursorByteColumn", "cursorVirtualColumn",
  }) do
    if payload[name] ~= state[name] then return false end
  end
  return true
end

local function initialize(payload)
  active = {
    explorationId = payload.explorationId,
    actionIndex = 0,
    bufferId = payload.bufferId,
    windowId = payload.windowId,
    tabpageId = payload.tabpageId,
    changedtick = payload.changedtick,
    modeRaw = payload.modeRaw,
    cursorLine = payload.cursorLine,
    cursorByteColumn = payload.cursorByteColumn,
    cursorVirtualColumn = payload.cursorVirtualColumn,
    line = payload.cursorLine,
    byteColumn = payload.cursorByteColumn,
    desiredVirtualColumn = payload.cursorVirtualColumn,
  }
end

local function move_character(state, direction)
  local line = current_line(state.bufferId, state.line)
  if direction < 0 then
    if state.byteColumn <= 0 then return false, "boundary" end
    state.byteColumn = previous_character_start(line, state.byteColumn)
  else
    if state.byteColumn >= #line then return false, "boundary" end
    local next_column = next_character_start(line, state.byteColumn)
    if next_column >= #line then return false, "boundary" end
    state.byteColumn = next_column
  end
  state.desiredVirtualColumn = virtual_column(state.windowId, state.line, state.byteColumn)
  return true, "moved"
end

local function move_line(state, direction)
  local target = state.line + direction
  local line_count = vim.api.nvim_buf_line_count(state.bufferId)
  if target < 1 or target > line_count then return false, "boundary" end
  state.line = target
  state.byteColumn = byte_column_for_virtual(
    state.windowId,
    state.bufferId,
    state.line,
    state.desiredVirtualColumn
  )
  return true, "moved"
end

local function scan_position(state, direction, line_number, byte_column, budget)
  local line = current_line(state.bufferId, line_number)
  if direction > 0 then
    if byte_column < #line then
      local next_column = next_character_start(line, byte_column)
      budget.bytes = budget.bytes + math.max(1, next_column - byte_column)
      return line_number, next_column, budget.bytes <= MAX_SCAN_BYTES
    end
    if line_number >= vim.api.nvim_buf_line_count(state.bufferId) then return nil, nil, true end
    budget.lines = budget.lines + 1
    budget.bytes = budget.bytes + 1
    return line_number + 1, 0, budget.lines <= MAX_SCAN_LINES and budget.bytes <= MAX_SCAN_BYTES
  end
  if byte_column > 0 then
    local previous = previous_character_start(line, byte_column)
    budget.bytes = budget.bytes + math.max(1, byte_column - previous)
    return line_number, previous, budget.bytes <= MAX_SCAN_BYTES
  end
  if line_number <= 1 then return nil, nil, true end
  budget.lines = budget.lines + 1
  budget.bytes = budget.bytes + 1
  local previous_line = current_line(state.bufferId, line_number - 1)
  return line_number - 1, last_character_start(previous_line),
    budget.lines <= MAX_SCAN_LINES and budget.bytes <= MAX_SCAN_BYTES
end

local function move_word_next(state)
  local line_number, byte_column = state.line, state.byteColumn
  local budget = { lines = 0, bytes = 0 }
  local line = current_line(state.bufferId, line_number)
  local character = character_at(line, byte_column)
  if keyword_character(character) then
    repeat
      local within_limit
      line_number, byte_column, within_limit = scan_position(
        state,
        1,
        line_number,
        byte_column,
        budget
      )
      if not within_limit then return false, "scanLimit" end
      if not line_number then return false, "boundary" end
      line = current_line(state.bufferId, line_number)
      character = character_at(line, byte_column)
    until not keyword_character(character)
  elseif character ~= "" and not whitespace_character(character) then
    local within_limit
    line_number, byte_column, within_limit = scan_position(
      state,
      1,
      line_number,
      byte_column,
      budget
    )
    if not within_limit then return false, "scanLimit" end
    if not line_number then return false, "boundary" end
  end
  while true do
    line = current_line(state.bufferId, line_number)
    character = character_at(line, byte_column)
    if character ~= "" and not whitespace_character(character) then break end
    local next_line, next_column, within_limit = scan_position(
      state,
      1,
      line_number,
      byte_column,
      budget
    )
    if not within_limit then return false, "scanLimit" end
    if not next_line then return false, "boundary" end
    line_number, byte_column = next_line, next_column
  end
  state.line, state.byteColumn = line_number, byte_column
  state.desiredVirtualColumn = virtual_column(state.windowId, state.line, state.byteColumn)
  return true, "moved"
end

local function move_word_previous(state)
  local budget = { lines = 0, bytes = 0 }
  local line_number, byte_column, within_limit = scan_position(
    state,
    -1,
    state.line,
    state.byteColumn,
    budget
  )
  if not within_limit then return false, "scanLimit" end
  if not line_number then return false, "boundary" end
  local line = current_line(state.bufferId, line_number)
  local character = character_at(line, byte_column)
  while character == "" or whitespace_character(character) do
    line_number, byte_column, within_limit = scan_position(
      state,
      -1,
      line_number,
      byte_column,
      budget
    )
    if not within_limit then return false, "scanLimit" end
    if not line_number then return false, "boundary" end
    line = current_line(state.bufferId, line_number)
    character = character_at(line, byte_column)
  end
  if keyword_character(character) then
    while true do
      local previous_line, previous_column, allowed = scan_position(
        state,
        -1,
        line_number,
        byte_column,
        budget
      )
      if not allowed then return false, "scanLimit" end
      if not previous_line then break end
      if previous_line ~= line_number then break end
      local previous_text = current_line(state.bufferId, previous_line)
      if not keyword_character(character_at(previous_text, previous_column)) then break end
      line_number, byte_column = previous_line, previous_column
    end
  end
  state.line, state.byteColumn = line_number, byte_column
  state.desiredVirtualColumn = virtual_column(state.windowId, state.line, state.byteColumn)
  return true, "moved"
end

local function move_word(state, direction)
  if direction < 0 then return move_word_previous(state) end
  return move_word_next(state)
end

local function selected_text(state, unit)
  local line = current_line(state.bufferId, state.line)
  if unit == "line" then return line end
  if unit == "character" then return character_at(line, state.byteColumn) end
  return word_at(state.bufferId, state.line, state.byteColumn)
end

function M.step(payload)
  if not valid_request(payload) or not current_context_matches(payload) then
    active = nil
    return result(payload, false, "invalidOrStaleRequest")
  end
  if not active or active.explorationId ~= payload.explorationId then
    if payload.actionIndex ~= 1 then
      active = nil
      return result(payload, false, "outOfOrder")
    end
    initialize(payload)
  elseif not same_origin(payload, active) or payload.actionIndex ~= active.actionIndex + 1 then
    active = nil
    return result(payload, false, "outOfOrder")
  end

  local definition = actions[payload.action]
  local moved, code = false, "boundary"
  for _ = 1, payload.count or 1 do
    if definition.kind == "character" then
      moved, code = move_character(active, definition.direction)
    elseif definition.kind == "line" then
      moved, code = move_line(active, definition.direction)
    else
      moved, code = move_word(active, definition.direction)
    end
    if not moved then break end
  end
  active.actionIndex = payload.actionIndex
  local text = selected_text(active, definition.unit)
  if #text > MAX_RESULT_BYTES then
    return result(payload, false, "textTooLarge", {
      unit = definition.unit,
      line = active.line,
      byteColumn = active.byteColumn,
      characterColumn = character_column(current_line(active.bufferId, active.line), active.byteColumn),
      virtualColumn = virtual_column(active.windowId, active.line, active.byteColumn),
    })
  end
  return result(payload, code ~= "scanLimit", code, {
    unit = definition.unit,
    text = text,
    line = active.line,
    byteColumn = active.byteColumn,
    characterColumn = character_column(current_line(active.bufferId, active.line), active.byteColumn),
    virtualColumn = virtual_column(active.windowId, active.line, active.byteColumn),
  })
end

function M.finish(payload)
  if type(payload) ~= "table" or not integer(payload.requestId) or payload.requestId == 0
    or not integer(payload.explorationId) or payload.explorationId == 0 then
    return false
  end
  if active and active.explorationId == payload.explorationId then active = nil end
  return true
end

function M.reset()
  active = nil
end

function M._test_active()
  return active and vim.deepcopy(active) or nil
end

return M
