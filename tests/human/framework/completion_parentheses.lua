-- Small, dependency-free completion normalization used only by the isolated
-- guided human-test profiles.  It lets native LSP completion, nvim-cmp, and
-- blink.cmp exercise the same accepted function text without changing the
-- user's normal Neovim configuration.

local M = {}

local kinds = vim.lsp.protocol.CompletionItemKind
local formats = vim.lsp.protocol.InsertTextFormat

local function is_callable(item)
  return type(item) == "table"
    and (item.kind == kinds.Function or item.kind == kinds.Method)
end

local function insertion_text(item)
  if type(item.textEdit) == "table" and type(item.textEdit.newText) == "string" then
    return item.textEdit.newText
  end
  if type(item.insertText) == "string" then return item.insertText end
  return type(item.label) == "string" and item.label or nil
end

function M.native_convert(item)
  if not is_callable(item) or item.insertTextFormat == formats.Snippet then return {} end
  local word = insertion_text(item)
  if not word or word:find("(", 1, true) then return {} end
  return { word = word .. "()" }
end

function M.plan(line, column, item)
  if type(line) ~= "string" or type(column) ~= "number" or not is_callable(item) then
    return line, column, false
  end
  if item.insertTextFormat == formats.Snippet then return line, column, false end

  -- The insertion point is a zero-based byte column.  Normalize all common
  -- provider outcomes and leave the cursor between an empty bracket pair.
  if line:sub(column + 1, column + 1) == "(" then
    return line, column + 1, false
  end
  if column >= 2 and line:sub(column - 1, column) == "()" then
    return line, column - 1, false
  end
  if column >= 1 and line:sub(column, column) == "(" then
    return line, column, false
  end
  local inserted = insertion_text(item)
  local opening = inserted and inserted:find("(", 1, true) or nil
  if opening then
    local start = column - #inserted
    if start >= 0 and line:sub(start + 1, column) == inserted then
      return line, start + opening, false
    end
    -- The provider owns non-empty bracket text even if its text edit cannot be
    -- reconstructed from the final line. Never append a second call.
    return line, column, false
  end
  return line:sub(1, column) .. "()" .. line:sub(column + 1), column + 1, true
end

function M.apply(item)
  if not is_callable(item) then return false end
  local window = vim.api.nvim_get_current_win()
  local buffer = vim.api.nvim_get_current_buf()
  local cursor = vim.api.nvim_win_get_cursor(window)
  local lines = vim.api.nvim_buf_get_lines(buffer, cursor[1] - 1, cursor[1], true)
  local line = lines[1]
  if type(line) ~= "string" then return false end
  local replacement, column, changed = M.plan(line, cursor[2], item)
  if changed then
    vim.api.nvim_buf_set_lines(buffer, cursor[1] - 1, cursor[1], true, { replacement })
  end
  if column ~= cursor[2] then vim.api.nvim_win_set_cursor(window, { cursor[1], column }) end
  return changed or column ~= cursor[2]
end

return M
