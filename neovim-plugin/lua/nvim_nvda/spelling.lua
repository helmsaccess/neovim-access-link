local M = {}

local function lower(value)
  return type(value) == "string" and value:lower() or ""
end

function M.diagnostic_kind(diagnostic)
  if type(diagnostic) ~= "table" then return nil end
  local data = type(diagnostic.user_data) == "table" and diagnostic.user_data or {}
  local explicit = lower(data.nvim_nvda_kind or data.kind)
  if explicit == "spelling" or explicit == "grammar" then return explicit end
  local source = lower(diagnostic.source)
  local code = lower(tostring(diagnostic.code or ""))
  if source:find("spell", 1, true) or source:find("typos", 1, true)
    or code:find("morfologik", 1, true) or code:find("spelling", 1, true) then
    return "spelling"
  end
  if source:find("harper", 1, true) then return "grammar" end
  if source:find("grammar", 1, true) or code:find("grammar", 1, true) then return "grammar" end
  return nil
end

local function native_errors(line)
  local errors, offset, remaining = {}, 0, line
  while remaining ~= "" do
    local result = vim.fn.spellbadword(remaining)
    local word, spell_kind = result[1], result[2]
    if type(word) ~= "string" or word == "" then break end
    local relative = string.find(remaining, word, 1, true)
    if not relative then break end
    local start_column = offset + relative - 1
    local end_column = start_column + #word
    table.insert(errors, {
      kind = "spelling", word = word, spellKind = spell_kind,
      startByteColumn = start_column, endByteColumn = end_column,
      source = "nvim-spell",
    })
    offset = end_column
    remaining = string.sub(line, offset + 1)
  end
  return errors
end

function M.for_line(buf, line_number, line, cursor_column)
  local errors = {}
  if vim.wo.spell then
    for _, item in ipairs(native_errors(line)) do table.insert(errors, item) end
  end
  for _, diagnostic in ipairs(vim.diagnostic.get(buf, { lnum = line_number - 1 })) do
    local kind = M.diagnostic_kind(diagnostic)
    if kind and diagnostic.lnum == line_number - 1 then
      local start_column = tonumber(diagnostic.col) or 0
      local end_column = diagnostic.end_lnum == diagnostic.lnum and tonumber(diagnostic.end_col) or #line
      if not end_column or end_column <= start_column then end_column = #line end
      table.insert(errors, {
        kind = kind, startByteColumn = math.min(start_column, #line),
        endByteColumn = math.min(end_column, #line), source = diagnostic.source,
        message = type(diagnostic.message) == "string" and diagnostic.message:sub(1, 1024) or "",
      })
    end
  end
  table.sort(errors, function(a, b) return a.startByteColumn < b.startByteColumn end)
  local current
  for _, item in ipairs(errors) do
    if cursor_column >= item.startByteColumn and cursor_column < item.endByteColumn then current = item; break end
  end
  return errors, current
end

return M
