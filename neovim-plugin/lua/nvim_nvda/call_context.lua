local M = {}

local MAX_SCAN_LINES = 512
local MAX_SCAN_BYTES = 128 * 1024
local MAX_TREE_NODES = 20000
local document_cache = {}

local control_keywords = {
  ["assert"] = true,
  ["catch"] = true,
  ["do"] = true,
  ["else"] = true,
  ["elseif"] = true,
  ["except"] = true,
  ["finally"] = true,
  ["for"] = true,
  ["foreach"] = true,
  ["if"] = true,
  ["match"] = true,
  ["return"] = true,
  ["sizeof"] = true,
  ["switch"] = true,
  ["synchronized"] = true,
  ["then"] = true,
  ["throw"] = true,
  ["try"] = true,
  ["typeof"] = true,
  ["unless"] = true,
  ["using"] = true,
  ["while"] = true,
  ["with"] = true,
}

local hash_comment_filetypes = {
  bash = true, conf = true, fish = true, make = true, perl = true,
  php = true, python = true, r = true, ruby = true, sh = true,
  toml = true, yaml = true, zsh = true,
}

local slash_comment_filetypes = {
  c = true, cpp = true, cs = true, dart = true, go = true, java = true,
  javascript = true, javascriptreact = true, jsonc = true, kotlin = true,
  php = true, rust = true, scala = true, swift = true, typescript = true,
  typescriptreact = true,
}

local dash_comment_filetypes = { haskell = true, lua = true, sql = true }

local function integer(value, minimum)
  return type(value) == "number" and value % 1 == 0
    and value >= minimum and value <= 2147483647
end

local function identifier_byte(value)
  return value and (
    value >= 128
    or value >= string.byte("0") and value <= string.byte("9")
    or value >= string.byte("A") and value <= string.byte("Z")
    or value == string.byte("_")
    or value >= string.byte("a") and value <= string.byte("z")
  )
end

local function build_document(bufnr, cursor_line)
  if not vim.api.nvim_buf_is_valid(bufnr) then return nil end
  local line_count = vim.api.nvim_buf_line_count(bufnr)
  if not integer(cursor_line, 1) or cursor_line > line_count then return nil end
  local changedtick = vim.api.nvim_buf_get_changedtick(bufnr)
  local filetype = tostring(vim.bo[bufnr].filetype or ""):lower()
  local cached = document_cache[bufnr]
  if cached and cached.changedtick == changedtick and cached.filetype == filetype
    and cursor_line >= cached.first_line and cursor_line <= cached.last_line then
    return cached
  end
  local half = math.floor(MAX_SCAN_LINES / 2)
  local first = math.max(1, cursor_line - half)
  local last = math.min(line_count, first + MAX_SCAN_LINES - 1)
  first = math.max(1, math.min(first, last - MAX_SCAN_LINES + 1))
  local lines = vim.api.nvim_buf_get_lines(bufnr, first - 1, last, true)
  local offsets = {}
  local size = 0
  for index, line in ipairs(lines) do
    offsets[index] = size
    size = size + #line
    if index < #lines then size = size + 1 end
    if size > MAX_SCAN_BYTES then return nil end
  end
  local document = {
    bufnr = bufnr,
    first_line = first,
    last_line = last,
    lines = lines,
    line_offsets = offsets,
    text = table.concat(lines, "\n"),
    filetype = filetype,
    changedtick = changedtick,
  }
  document_cache[bufnr] = document
  return document
end

local function position_offset(document, line, byte_column)
  if not integer(line, 1) or not integer(byte_column, 0)
    or line < document.first_line or line > document.last_line then
    return nil
  end
  local index = line - document.first_line + 1
  local value = document.lines[index]
  if type(value) ~= "string" or byte_column > #value then return nil end
  return document.line_offsets[index] + byte_column
end

local function offset_position(document, offset)
  if not integer(offset, 0) or offset > #document.text then return nil end
  local low, high = 1, #document.lines
  while low <= high do
    local middle = math.floor((low + high) / 2)
    local start = document.line_offsets[middle]
    local finish = start + #document.lines[middle]
    if offset < start then
      high = middle - 1
    elseif offset > finish and middle < #document.lines then
      low = middle + 1
    else
      return {
        line = document.first_line + middle - 1,
        byteColumn = math.min(offset - start, #document.lines[middle]),
      }
    end
  end
  return nil
end

local function ignored_node_type(value)
  value = tostring(value or ""):lower()
  return value:find("comment", 1, true)
    or value:find("string", 1, true)
    or value:find("heredoc", 1, true)
    or value:find("template", 1, true)
end

local function mark_range(document, ignored, start_row, start_column, end_row, end_column)
  local start = position_offset(document, start_row + 1, start_column)
  local finish = position_offset(document, end_row + 1, end_column)
  if not start and start_row + 1 < document.first_line then start = 0 end
  if not finish and end_row + 1 > document.last_line then finish = #document.text end
  if not start or not finish then return end
  for offset = math.max(0, start), math.min(#document.text, finish) - 1 do
    ignored[offset] = true
  end
end

local function tree_ignored(document, ignored)
  if not vim.treesitter or type(vim.treesitter.get_parser) ~= "function" then return false end
  local ok, parser = pcall(vim.treesitter.get_parser, document.bufnr)
  if not ok or not parser then return false end
  local parsed, trees = pcall(function() return parser:parse() end)
  if not parsed or type(trees) ~= "table" or not trees[1] then return false end
  local root_ok, root = pcall(function() return trees[1]:root() end)
  if not root_ok or not root then return false end
  local visited = 0
  local complete = true
  local function visit(node)
    visited = visited + 1
    if visited > MAX_TREE_NODES then complete = false; return end
    local range_ok, start_row, start_column, end_row, end_column = pcall(node.range, node)
    if not range_ok or end_row < document.first_line - 1
      or start_row > document.last_line - 1 then
      return
    end
    local type_ok, node_type = pcall(node.type, node)
    if type_ok and ignored_node_type(node_type) then
      mark_range(document, ignored, start_row, start_column, end_row, end_column)
      return
    end
    local children_ok, iterator, iterator_state, iterator_initial = pcall(
      node.iter_children, node
    )
    if not children_ok or not iterator then return end
    for child in iterator, iterator_state, iterator_initial do
      if not complete then return end
      visit(child)
    end
  end
  visit(root)
  return complete
end

local function mark_bytes(ignored, first, last)
  for offset = first, last do ignored[offset] = true end
end

-- Tree-sitter is authoritative when available. This bounded lexer supplements
-- it for incomplete strings and provides a conservative fallback on systems
-- without a parser for the current language.
local function lexical_ignored(document, ignored)
  local value = document.text
  local filetype = document.filetype
  local hash_comments = hash_comment_filetypes[filetype] == true
  local slash_comments = slash_comment_filetypes[filetype] == true
  local dash_comments = dash_comment_filetypes[filetype] == true
  local index = 1
  while index <= #value do
    local first = value:sub(index, index)
    local pair = value:sub(index, index + 1)
    local triple = value:sub(index, index + 2)
    if hash_comments and first == "#" then
      local finish = value:find("\n", index, true) or (#value + 1)
      mark_bytes(ignored, index - 1, finish - 2)
      index = finish
    elseif slash_comments and pair == "//" then
      local finish = value:find("\n", index + 2, true) or (#value + 1)
      mark_bytes(ignored, index - 1, finish - 2)
      index = finish
    elseif slash_comments and pair == "/*" then
      local finish = value:find("*/", index + 2, true)
      finish = finish and finish + 1 or #value
      mark_bytes(ignored, index - 1, finish - 1)
      index = finish + 1
    elseif dash_comments and pair == "--" then
      local long = filetype == "lua" and value:sub(index + 2, index + 3) == "[["
      local finish = long and value:find("]]", index + 4, true) or nil
      if long then
        finish = finish and finish + 1 or #value
      else
        finish = value:find("\n", index + 2, true) or (#value + 1)
        finish = finish - 1
      end
      mark_bytes(ignored, index - 1, finish - 1)
      index = finish + 1
    elseif filetype == "lua" and pair == "[[" then
      local finish = value:find("]]", index + 2, true)
      finish = finish and finish + 1 or #value
      mark_bytes(ignored, index - 1, finish - 1)
      index = finish + 1
    elseif first == "'" or first == '"' or first == "`" then
      local quote = first
      local delimiter = quote
      if (filetype == "python" or filetype == "ruby")
        and (triple == "'''" or triple == '\"\"\"') then
        delimiter = triple
      end
      local finish = index + #delimiter
      local escaped = false
      while finish <= #value do
        if not escaped and value:sub(finish, finish + #delimiter - 1) == delimiter then
          finish = finish + #delimiter - 1
          break
        end
        local character = value:sub(finish, finish)
        if character == "\n" and #delimiter == 1 and quote ~= "`" then
          finish = finish - 1
          break
        end
        if character == "\\" and not escaped then
          escaped = true
        else
          escaped = false
        end
        finish = finish + 1
      end
      finish = math.min(finish, #value)
      mark_bytes(ignored, index - 1, finish - 1)
      index = finish + 1
    else
      index = index + 1
    end
  end
end

local function ignored_offsets(document)
  if document.ignored_offsets then return document.ignored_offsets end
  local ignored = {}
  tree_ignored(document, ignored)
  lexical_ignored(document, ignored)
  document.ignored_offsets = ignored
  return ignored
end

local function character(document, offset)
  if offset < 0 or offset >= #document.text then return "" end
  return document.text:sub(offset + 1, offset + 1)
end

local function significant(document, ignored, offset)
  local value = character(document, offset)
  return value ~= "" and not ignored[offset] and value:match("%s") == nil
end

local function name_before_open(document, ignored, open_offset)
  if ignored[open_offset] then return nil end
  local finish = open_offset - 1
  while finish >= 0 and (
    ignored[finish] or character(document, finish):match("%s")
  ) do
    finish = finish - 1
  end
  if finish < 0 or ignored[finish]
    or not identifier_byte(document.text:byte(finish + 1)) then
    return nil
  end
  local first = finish
  while first > 0 and not ignored[first - 1]
    and identifier_byte(document.text:byte(first)) do
    first = first - 1
  end
  local name = document.text:sub(first + 1, finish + 1)
  if name == "" or control_keywords[name:lower()] then return nil end
  return { first = first, last = finish + 1, text = name }
end

local function matching_close(document, ignored, open_offset)
  local depth = 0
  for offset = open_offset + 1, #document.text - 1 do
    if not ignored[offset] then
      local value = character(document, offset)
      if value == "(" then
        depth = depth + 1
      elseif value == ")" then
        if depth == 0 then return offset end
        depth = depth - 1
      end
    end
  end
  return nil
end

local function matching_open(document, ignored, close_offset)
  local depth = 0
  for offset = close_offset - 1, 0, -1 do
    if not ignored[offset] then
      local value = character(document, offset)
      if value == ")" then
        depth = depth + 1
      elseif value == "(" then
        if depth == 0 then return offset end
        depth = depth - 1
      end
    end
  end
  return nil
end

local function enclosing_open(document, ignored, cursor_offset)
  local depth = 0
  for offset = cursor_offset - 1, 0, -1 do
    if not ignored[offset] then
      local value = character(document, offset)
      if value == ")" then
        depth = depth + 1
      elseif value == "(" then
        if depth == 0 then return offset end
        depth = depth - 1
      end
    end
  end
  return nil
end

local function empty_arguments(document, ignored, open_offset, close_offset)
  if not close_offset then return false end
  for offset = open_offset + 1, close_offset - 1 do
    if significant(document, ignored, offset) then return false end
  end
  return true
end

local function context(document, ignored, open_offset, cursor_offset, source)
  local name = name_before_open(document, ignored, open_offset)
  if not name then return nil end
  local close_offset = matching_close(document, ignored, open_offset)
  local open_position = offset_position(document, open_offset)
  local name_position = offset_position(document, name.first)
  if not open_position or not name_position then return nil end
  local query_offset = source == "close" and close_offset or (
    source == "automatic" and cursor_offset or open_offset + 1
  )
  local query_position = offset_position(document, query_offset)
  if not query_position then return nil end
  return {
    source = source,
    name = name.text,
    nameLine = name_position.line,
    nameByteColumn = name_position.byteColumn,
    openLine = open_position.line,
    openByteColumn = open_position.byteColumn,
    closeLine = close_offset and offset_position(document, close_offset).line or nil,
    closeByteColumn = close_offset and offset_position(document, close_offset).byteColumn or nil,
    queryLine = query_position.line,
    queryByteColumn = query_position.byteColumn,
    empty = empty_arguments(document, ignored, open_offset, close_offset),
  }
end

local function identifier_at(document, ignored, cursor_offset)
  if ignored[cursor_offset] or not identifier_byte(document.text:byte(cursor_offset + 1)) then
    return nil
  end
  local first = cursor_offset
  while first > 0 and not ignored[first - 1]
    and identifier_byte(document.text:byte(first)) do
    first = first - 1
  end
  local finish = cursor_offset + 1
  while finish < #document.text and not ignored[finish]
    and identifier_byte(document.text:byte(finish + 1)) do
    finish = finish + 1
  end
  local open_offset = finish
  while open_offset < #document.text and (
    ignored[open_offset] or character(document, open_offset):match("%s")
  ) do
    open_offset = open_offset + 1
  end
  if character(document, open_offset) ~= "(" then return nil end
  local name = name_before_open(document, ignored, open_offset)
  if not name or name.first ~= first or name.last ~= finish then return nil end
  return open_offset
end

function M.resolve_manual(bufnr, line, byte_column, mode_raw)
  local first_mode = tostring(mode_raw or ""):sub(1, 1)
  if first_mode ~= "n" and first_mode ~= "i" then return nil end
  local document = build_document(bufnr, line)
  if not document then return nil end
  local cursor_offset = position_offset(document, line, byte_column)
  if not cursor_offset then return nil end
  local ignored = ignored_offsets(document)
  local source
  local open_offset = identifier_at(document, ignored, cursor_offset)
  if open_offset then
    source = "name"
  elseif not ignored[cursor_offset] and character(document, cursor_offset) == "(" then
    source = "open"
    open_offset = cursor_offset
  elseif not ignored[cursor_offset] and character(document, cursor_offset) == ")" then
    source = "close"
    open_offset = matching_open(document, ignored, cursor_offset)
  end
  if not open_offset then return nil end
  local resolved = context(document, ignored, open_offset, cursor_offset, source)
  if not resolved then return nil end
  if first_mode == "i" and source ~= "name" and not resolved.empty then return nil end
  return resolved
end

function M.resolve_automatic(bufnr, line, byte_column, mode_raw)
  if tostring(mode_raw or ""):sub(1, 1) ~= "i" then return nil end
  local document = build_document(bufnr, line)
  if not document then return nil end
  local cursor_offset = position_offset(document, line, byte_column)
  if not cursor_offset then return nil end
  local ignored = ignored_offsets(document)
  local open_offset = enclosing_open(document, ignored, cursor_offset)
  if not open_offset then return nil end
  local resolved = context(document, ignored, open_offset, cursor_offset, "automatic")
  if not resolved then return nil end
  local close_offset = matching_close(document, ignored, open_offset)
  if close_offset and cursor_offset > close_offset then return nil end
  return resolved
end

function M.clear_cache(bufnr)
  if type(bufnr) == "number" then
    document_cache[bufnr] = nil
  else
    document_cache = {}
  end
end

return M
