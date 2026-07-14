local M = {}

local function before(a, b)
  return a.line < b.line or (a.line == b.line and a.byteColumn <= b.byteColumn)
end

local function inclusive_char_end(line, byte_column)
  if byte_column >= #line then
    return #line
  end
  local exclusive = byte_column + 1
  while exclusive < #line do
    local byte = string.byte(line, exclusive + 1)
    if not byte or byte < 0x80 or byte >= 0xC0 then
      break
    end
    exclusive = exclusive + 1
  end
  return exclusive
end

---Normalize visual selection positions without confusing byte and character columns.
---@param lines string[]
---@param mode string `v`, `V`, or CTRL-V
---@param anchor table {line: one-based, byteColumn: zero-based}
---@param cursor table {line: one-based, byteColumn: zero-based}
---@param selection_option? string `inclusive` or `exclusive`
---@return table
function M.from_positions(lines, mode, anchor, cursor, selection_option)
  assert(mode == "v" or mode == "V" or mode == "\22", "unsupported visual mode")
  local forward = before(anchor, cursor)
  local first = forward and anchor or cursor
  local last = forward and cursor or anchor
  local kind = mode == "v" and "character" or (mode == "V" and "line" or "block")
  local result = {
    kind = kind,
    direction = forward and "forward" or "backward",
    anchor = anchor,
    cursor = cursor,
    start = { line = first.line, byteColumn = first.byteColumn },
    finish = { line = last.line, byteColumn = last.byteColumn },
    lineCount = last.line - first.line + 1,
    inclusive = selection_option ~= "exclusive",
  }

  if kind == "line" then
    result.start.byteColumn = 0
    result.finish.byteColumn = #(lines[last.line] or "")
  elseif kind == "block" then
    result.start.byteColumn = math.min(anchor.byteColumn, cursor.byteColumn)
    result.finish.byteColumn = math.max(anchor.byteColumn, cursor.byteColumn)
  elseif result.inclusive then
    result.finish.byteColumn = inclusive_char_end(lines[last.line] or "", last.byteColumn)
  end
  return result
end

return M
