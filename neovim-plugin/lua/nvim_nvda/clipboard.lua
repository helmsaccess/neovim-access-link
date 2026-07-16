local M = {}

local MAX_TEXT_BYTES = 256 * 1024
local MAX_REQUEST_ID = 2147483647
local visual_modes = { v = true, V = true, ["\22"] = true }

local function integer(value)
  return type(value) == "number" and value >= 0 and value <= MAX_REQUEST_ID
    and value == math.floor(value)
end

local function expected_state(payload)
  if type(payload) ~= "table" or not integer(payload.requestId) then return false end
  for _, name in ipairs({ "bufferId", "windowId", "tabpageId", "changedtick" }) do
    if not integer(payload[name]) then return false end
  end
  return type(payload.modeRaw) == "string" and #payload.modeRaw > 0 and #payload.modeRaw <= 16
end

local function current_state_matches(payload)
  return vim.api.nvim_get_current_buf() == payload.bufferId
    and vim.api.nvim_get_current_win() == payload.windowId
    and vim.api.nvim_get_current_tabpage() == payload.tabpageId
    and vim.api.nvim_buf_get_changedtick(payload.bufferId) == payload.changedtick
    and vim.api.nvim_get_mode().mode == payload.modeRaw
end

local function result(payload, ok, code, extra)
  local value = {
    requestId = type(payload) == "table" and payload.requestId or -1,
    ok = ok,
    resultCode = code,
  }
  for key, item in pairs(extra or {}) do value[key] = item end
  return value
end

local function bounded_text(text)
  return type(text) == "string" and text ~= "" and not text:find("\0", 1, true)
    and #text <= MAX_TEXT_BYTES
end

local function joined_region(lines, register_type)
  local text = table.concat(lines or {}, "\n")
  if register_type == "V" and text ~= "" then text = text .. "\n" end
  return text
end

function M.copy_text(payload)
  if not expected_state(payload)
    or (payload.source ~= "visualSelection" and payload.source ~= "yankRegister") then
    return result(payload, false, "invalidRequest")
  end
  if not current_state_matches(payload) then
    return result(payload, false, "staleState")
  end
  local text, register_type, line_count
  if payload.source == "visualSelection" then
    if not visual_modes[payload.modeRaw] then
      return result(payload, false, "visualSelectionRequired")
    end
    local ok, lines = pcall(vim.fn.getregion, vim.fn.getpos("v"), vim.fn.getpos("."), {
      type = payload.modeRaw,
      exclusive = vim.o.selection == "exclusive",
    })
    if not ok or type(lines) ~= "table" then
      return result(payload, false, "selectionUnavailable")
    end
    register_type = payload.modeRaw
    line_count = #lines
    text = joined_region(lines, register_type)
  else
    local ok, info = pcall(vim.fn.getreginfo, "0")
    if not ok or type(info) ~= "table" or type(info.regcontents) ~= "table" then
      return result(payload, false, "registerUnavailable")
    end
    register_type = type(info.regtype) == "string" and info.regtype or "v"
    line_count = #info.regcontents
    text = joined_region(info.regcontents, register_type)
  end
  if not bounded_text(text) then
    return result(payload, false, text == "" and "emptyText" or "textTooLarge")
  end
  return result(payload, true, "copied", {
    source = payload.source,
    clipboardText = text,
    copiedCharacterCount = vim.fn.strchars(text),
    copiedLineCount = line_count,
    registerType = register_type,
  })
end

function M.paste_text(payload)
  if not expected_state(payload) or not bounded_text(payload.text) then
    return result(payload, false, "invalidRequest")
  end
  if not current_state_matches(payload) then
    return result(payload, false, "staleState")
  end
  local buf = vim.api.nvim_get_current_buf()
  local mode = payload.modeRaw:sub(1, 1)
  if mode ~= "n" and mode ~= "i" then
    return result(payload, false, "unsupportedMode")
  end
  if vim.bo[buf].buftype ~= "" or not vim.bo[buf].modifiable or vim.bo[buf].readonly then
    return result(payload, false, "bufferNotEditable")
  end
  if require("nvim_nvda.file_manager").current() then
    return result(payload, false, "unsupportedContext")
  end
  local before = vim.api.nvim_buf_get_changedtick(buf)
  local ok, accepted = pcall(vim.api.nvim_paste, payload.text, true, -1)
  if not ok or accepted == false then
    return result(payload, false, "pasteRejected")
  end
  return result(payload, true, "pasted", {
    insertedBytes = #payload.text,
    insertedLines = select(2, payload.text:gsub("\n", "\n")) + 1,
    changedtickBefore = before,
    changedtickAfter = vim.api.nvim_buf_get_changedtick(buf),
  })
end

function M.set_register(payload)
  if not expected_state(payload) or not bounded_text(payload.text) then
    return result(payload, false, "invalidRequest")
  end
  if not current_state_matches(payload) then
    return result(payload, false, "staleState")
  end
  local text = payload.text:gsub("\r\n", "\n")
  local register_type = text:sub(-1) == "\n" and "V" or "v"
  -- The unnamed register is a pointer, not independent storage.  Use the
  -- fixed yank register as its backing store instead of overwriting a named
  -- user register, and point the unnamed register to it for normal `p`.
  local ok, set_result = pcall(vim.fn.setreg, "0", text, register_type .. '"')
  if not ok or set_result ~= 0 then
    return result(payload, false, "registerRejected")
  end
  local newline_count = select(2, text:gsub("\n", "\n"))
  return result(payload, true, "registerStored", {
    registerType = register_type,
    storedBytes = #text,
    storedLineCount = newline_count + (register_type == "V" and 0 or 1),
  })
end

return M
