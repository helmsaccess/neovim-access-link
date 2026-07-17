local selection = require("nvim_nvda.selection")
local spelling = require("nvim_nvda.spelling")
local file_manager = require("nvim_nvda.file_manager")
local M = {}

local visual_modes = { v = true, V = true, ["\22"] = true }
local modern_string_indices = vim.fn.has("nvim-0.11") == 1

local function character_column(line, byte_column)
  if modern_string_indices then
    return vim.str_utfindex(line, "utf-32", byte_column, false)
  end
  return vim.str_utfindex(line, byte_column)
end

function M.normalize_mode(raw)
  if raw:sub(1, 2) == "no" then return "operatorPending" end
  -- Neovim reports Terminal-Normal as "nt". It accepts Normal-mode
  -- commands, but is a distinct terminal context and must not be collapsed
  -- into an ordinary file buffer's Normal mode.
  if raw:sub(1, 2) == "nt" then return "terminalNormal" end
  if raw == "v" then return "visualCharacter" end
  if raw == "V" then return "visualLine" end
  if raw == "\22" then return "visualBlock" end
  if raw == "s" then return "selectCharacter" end
  if raw == "S" then return "selectLine" end
  if raw == "\19" then return "selectBlock" end
  local first = raw:sub(1, 1)
  if first == "n" then return "normal" end
  if first == "i" then return "insert" end
  if first == "R" then return "replace" end
  if first == "c" then return "commandLine" end
  if first == "t" then return "terminal" end
  return "unknown"
end

local function character_at(line, byte_column)
  if byte_column >= #line then return "" end
  local finish = byte_column + 1
  while finish < #line do
    local byte = string.byte(line, finish + 1)
    if not byte or byte < 0x80 or byte >= 0xC0 then break end
    finish = finish + 1
  end
  return string.sub(line, byte_column + 1, finish)
end

local function current_word(line, byte_column)
  local character = character_at(line, byte_column)
  -- `expand("<cword>")` searches forward when the cursor is on punctuation.
  -- For a Vim word motion punctuation is its own target, so returning the
  -- following identifier here would produce combinations such as
  -- "wie, comma" although the cursor is still on the comma.
  if character ~= "" and vim.fn.match(character, [[\k]]) < 0 then
    return character
  end
  local ok, word = pcall(vim.fn.expand, "<cword>")
  return ok and type(word) == "string" and word or ""
end

local severity_names = { [1] = "error", [2] = "warning", [3] = "information", [4] = "hint" }

local function diagnostic_state(buf, line_number, byte_column)
  local all = vim.diagnostic.get(buf)
  table.sort(all, function(a, b)
    if a.lnum ~= b.lnum then return a.lnum < b.lnum end
    return (a.col or 0) < (b.col or 0)
  end)
  local current, current_index
  for index, diagnostic in ipairs(all) do
    local last_line = diagnostic.end_lnum or diagnostic.lnum
    local start_column = diagnostic.col or 0
    local end_column = diagnostic.end_col or start_column + 1
    local inside = line_number - 1 >= diagnostic.lnum and line_number - 1 <= last_line
    if inside and (line_number - 1 ~= diagnostic.lnum or byte_column >= start_column)
      and (line_number - 1 ~= last_line or byte_column < math.max(end_column, start_column + 1)) then
      current, current_index = diagnostic, index
      break
    end
  end
  if not current then return nil, #all end
  return {
    message = type(current.message) == "string" and current.message:sub(1, 2048) or "",
    severity = severity_names[current.severity] or "error",
    source = current.source,
    code = current.code,
    line = current.lnum + 1,
    byteColumn = current.col or 0,
    endLine = (current.end_lnum or current.lnum) + 1,
    endByteColumn = current.end_col or current.col or 0,
    index = current_index,
    count = #all,
  }, #all
end

function M.snapshot(reason)
  local win = vim.api.nvim_get_current_win()
  local buf = vim.api.nvim_get_current_buf()
  local cursor = vim.api.nvim_win_get_cursor(win)
  local mode_info = vim.api.nvim_get_mode()
  local mode_raw = mode_info.mode
  local line = vim.api.nvim_buf_get_lines(buf, cursor[1] - 1, cursor[1], true)[1] or ""
  local tabs, tab_index = vim.api.nvim_list_tabpages(), 1
  for index, tab in ipairs(tabs) do if tab == vim.api.nvim_get_current_tabpage() then tab_index = index end end
  local windows, window_index = vim.api.nvim_tabpage_list_wins(0), 1
  for index, window in ipairs(windows) do if window == win then window_index = index end end
  local window_info = vim.fn.getwininfo(win)[1] or {}
  local command_line = ""
  local command_line_position = 0
  if mode_raw:sub(1, 1) == "c" then
    command_line = vim.fn.getcmdline()
    command_line_position = vim.fn.getcmdpos() - 1
  end
  local result = {
    reason = reason,
    mode = M.normalize_mode(mode_raw),
    modeRaw = mode_raw,
    modeBlocking = mode_info.blocking == true,
    bufferId = buf,
    windowId = win,
    tabpageId = vim.api.nvim_get_current_tabpage(),
    tabIndex = tab_index,
    tabCount = #tabs,
    windowIndex = window_index,
    windowCount = #windows,
    windowType = window_info.loclist == 1 and "locationList"
      or (window_info.quickfix == 1 and "quickfix" or "normal"),
    bufferName = vim.api.nvim_buf_get_name(buf),
    filetype = vim.bo[buf].filetype,
    buftype = vim.bo[buf].buftype,
    modified = vim.bo[buf].modified,
    modifiable = vim.bo[buf].modifiable,
    readonly = vim.bo[buf].readonly,
    cursor = {
      line = cursor[1],
      byteColumn = cursor[2],
      characterColumn = character_column(line, cursor[2]),
      virtualColumn = vim.fn.virtcol(".") - 1,
    },
    lineText = line,
    tabstop = vim.bo[buf].tabstop,
    shiftwidth = vim.bo[buf].shiftwidth > 0 and vim.bo[buf].shiftwidth or vim.bo[buf].tabstop,
    indentation = vim.fn.indent(cursor[1]),
    character = character_at(line, cursor[2]),
    word = current_word(line, cursor[2]),
    commandLine = command_line,
    commandLinePosition = command_line_position,
    changedtick = vim.api.nvim_buf_get_changedtick(buf),
    lineCount = vim.api.nvim_buf_line_count(buf),
    selection = nil,
    fileManager = file_manager.current(),
  }
  result.spellingErrors, result.spellingError = spelling.for_line(buf, cursor[1], line, cursor[2])
  result.diagnostic, result.diagnosticCount = diagnostic_state(buf, cursor[1], cursor[2])
  if visual_modes[mode_raw] then
    local position = vim.fn.getpos("v")
    local anchor = { line = position[2], byteColumn = math.max(0, position[3] - 1) }
    local first_line = math.min(anchor.line, cursor[1])
    local last_line = math.max(anchor.line, cursor[1])
    local lines = vim.api.nvim_buf_get_lines(buf, first_line - 1, last_line, true)
    local indexed = {}
    for index, text in ipairs(lines) do
      indexed[first_line + index - 1] = text
    end
    result.selection = selection.from_positions(
      indexed,
      mode_raw,
      anchor,
      { line = cursor[1], byteColumn = cursor[2] },
      vim.o.selection
    )
    local region
    if mode_raw == "V" then
      region = {}
      for line_number = first_line, last_line do
        region[line_number - 1] = { 0, #(indexed[line_number] or "") }
      end
    elseif mode_raw == "\22" then
      region = {}
      local anchor_virtual = vim.fn.virtcol({ anchor.line, anchor.byteColumn + 1 })
      local cursor_virtual = vim.fn.virtcol({ cursor[1], cursor[2] + 1 })
      local left_virtual = math.min(anchor_virtual, cursor_virtual)
      local right_virtual = math.max(anchor_virtual, cursor_virtual)
      for line_number = first_line, last_line do
        local text = indexed[line_number] or ""
        local start_one_based = vim.fn.virtcol2col(win, line_number, left_virtual)
        local end_one_based = vim.fn.virtcol2col(win, line_number, right_virtual)
        local start_column = start_one_based > 0 and start_one_based - 1 or #text
        local end_column = end_one_based > 0 and end_one_based - 1 or #text
        if vim.o.selection ~= "exclusive" then
          end_column = character_at(text, end_column) == "" and #text
            or end_column + #character_at(text, end_column)
        end
        region[line_number - 1] = { start_column, end_column }
      end
    else
      region = vim.region(
        buf,
        { anchor.line - 1, anchor.byteColumn },
        { cursor[1] - 1, cursor[2] },
        mode_raw,
        vim.o.selection ~= "exclusive"
      )
    end
    local current = region[cursor[1] - 1]
    local exact_text = vim.fn.getregion(
      vim.fn.getpos("v"), vim.fn.getpos("."),
      { type = mode_raw, exclusive = vim.o.selection == "exclusive" }
    )
    local selected_lines = {}
    for line_number = first_line, last_line do
      local range = region[line_number - 1]
      local text = indexed[line_number] or ""
      if range then
        local start_column = math.max(0, math.min(range[1], #text))
        local end_column = range[2]
        if end_column < 0 then end_column = #text end
        end_column = math.max(start_column, math.min(end_column, #text))
        table.insert(selected_lines, {
          line = line_number,
          text = exact_text[line_number - first_line + 1]
            or string.sub(text, start_column + 1, end_column),
        })
      end
    end
    result.selection.selectedLines = selected_lines
    local selected_text = {}
    for _, item in ipairs(selected_lines) do table.insert(selected_text, item.text) end
    result.selection.text = table.concat(selected_text, "\n")
    if current then
      result.selection.currentLine = {
        startByteColumn = math.min(current[1], #line),
        endByteColumn = math.min(current[2], #line),
      }
    end
  end
  return result
end

return M
