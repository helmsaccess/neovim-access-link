local text = require("nvim_nvda.text")
local M = {}

local MAX_POSITION = 2147483647
local MAX_MESSAGE_BYTES = 2048
local MAX_SOURCE_BYTES = 256
local MAX_CODE_BYTES = 256
local severity_names = {
  [vim.diagnostic.severity.ERROR] = "error",
  [vim.diagnostic.severity.WARN] = "warning",
  [vim.diagnostic.severity.INFO] = "information",
  [vim.diagnostic.severity.HINT] = "hint",
}
local command_names = {
  "NvimNvdaDiagnosticPrevious",
  "NvimNvdaDiagnosticNext",
  "NvimNvdaDiagnosticFirst",
  "NvimNvdaDiagnosticLast",
  "NvimNvdaDiagnosticCurrent",
}
local current_emit
local jump_callback
local previous_jump_callback
local pending_navigation
local navigation_sequence = 0
local buffer_cache = {}
local buffer_line_cache = {}
local cache_enabled = false

local function bounded_integer(value, minimum)
  return type(value) == "number" and value % 1 == 0
    and value >= minimum and value <= MAX_POSITION
end

local function namespace_name(namespace)
  if not bounded_integer(namespace, 0)
    or type(vim.diagnostic.get_namespace) ~= "function" then
    return ""
  end
  local ok, details = pcall(vim.diagnostic.get_namespace, namespace)
  if not ok or type(details) ~= "table" then return "" end
  return text.bounded(details.name, MAX_SOURCE_BYTES)
end

local function normalized_code(value)
  if type(value) == "string" then
    local result = text.bounded(value, MAX_CODE_BYTES)
    return result ~= "" and result or nil
  end
  if bounded_integer(value, -MAX_POSITION - 1) then return value end
  return nil
end

local function normalize(value, ordinal, resolve_namespace)
  if type(value) ~= "table"
    or not bounded_integer(value.lnum, 0)
    or type(value.message) ~= "string" then
    return nil
  end
  local col = value.col == nil and 0 or value.col
  local end_lnum = value.end_lnum == nil and value.lnum or value.end_lnum
  local end_col = value.end_col == nil and col or value.end_col
  if not bounded_integer(col, 0)
    or not bounded_integer(end_lnum, value.lnum)
    or not bounded_integer(end_col, 0)
    or (end_lnum == value.lnum and end_col < col) then
    return nil
  end
  local message = text.bounded(value.message, MAX_MESSAGE_BYTES)
  if message == "" and value.message ~= "" then return nil end
  local namespace = bounded_integer(value.namespace, 0) and value.namespace or nil
  local provider = namespace and resolve_namespace(namespace) or ""
  local source = text.bounded(value.source, MAX_SOURCE_BYTES)
  if source == "" then source = provider end
  local severity = severity_names[value.severity] and value.severity
    or vim.diagnostic.severity.ERROR
  return {
    lnum = value.lnum,
    col = col,
    end_lnum = end_lnum,
    end_col = end_col,
    message = message,
    severity = severity,
    source = source,
    code = normalized_code(value.code),
    namespace = namespace,
    namespace_name = provider,
    ordinal = ordinal,
    raw = value,
  }
end

local function code_key(value)
  if type(value) == "number" then return string.format("n:%d", value) end
  return "s:" .. tostring(value or "")
end

local function ordered_before(left, right)
  if left.lnum ~= right.lnum then return left.lnum < right.lnum end
  if left.col ~= right.col then return left.col < right.col end
  if left.end_lnum ~= right.end_lnum then return left.end_lnum < right.end_lnum end
  if left.end_col ~= right.end_col then return left.end_col < right.end_col end
  if left.severity ~= right.severity then return left.severity < right.severity end
  if left.namespace_name ~= right.namespace_name then
    return left.namespace_name < right.namespace_name
  end
  if left.source ~= right.source then return left.source < right.source end
  local left_code, right_code = code_key(left.code), code_key(right.code)
  if left_code ~= right_code then return left_code < right_code end
  if left.message ~= right.message then return left.message < right.message end
  return left.ordinal < right.ordinal
end

local function contains(diagnostic, line, byte_column)
  if line < diagnostic.lnum or line > diagnostic.end_lnum then return false end
  if line == diagnostic.lnum and byte_column < diagnostic.col then return false end
  local effective_end = diagnostic.end_col
  if diagnostic.end_lnum == diagnostic.lnum and effective_end <= diagnostic.col then
    effective_end = diagnostic.col + 1
  end
  return line ~= diagnostic.end_lnum or byte_column < effective_end
end

local function preferred_current(left, right)
  if not right then return true end
  if left.severity ~= right.severity then return left.severity < right.severity end
  local left_lines = left.end_lnum - left.lnum
  local right_lines = right.end_lnum - right.lnum
  if left_lines ~= right_lines then return left_lines < right_lines end
  local left_columns = left_lines == 0 and left.end_col - left.col
    or MAX_POSITION - left.col + left.end_col
  local right_columns = right_lines == 0 and right.end_col - right.col
    or MAX_POSITION - right.col + right.end_col
  if left_columns ~= right_columns then return left_columns < right_columns end
  return ordered_before(left, right)
end

function M.normalized(values, resolve_namespace)
  local result = {}
  resolve_namespace = resolve_namespace or namespace_name
  if type(values) ~= "table" then return result end
  for ordinal, value in ipairs(values) do
    local diagnostic = normalize(value, ordinal, resolve_namespace)
    if diagnostic then result[#result + 1] = diagnostic end
  end
  table.sort(result, ordered_before)
  return result
end

local function snapshot_normalized(all, line_number, byte_column)
  if not bounded_integer(line_number, 1) or not bounded_integer(byte_column, 0) then
    return nil, #all
  end
  local current, current_index
  local line = line_number - 1
  for index, diagnostic in ipairs(all) do
    if contains(diagnostic, line, byte_column)
      and preferred_current(diagnostic, current) then
      current, current_index = diagnostic, index
    end
  end
  if not current then return nil, #all end
  return {
    message = current.message,
    severity = severity_names[current.severity],
    source = current.source,
    code = current.code,
    line = current.lnum + 1,
    byteColumn = current.col,
    endLine = current.end_lnum + 1,
    endByteColumn = current.end_col,
    index = current_index,
    count = #all,
  }, #all
end

function M.snapshot_values(values, line_number, byte_column, resolve_namespace)
  return snapshot_normalized(
    M.normalized(values, resolve_namespace),
    line_number,
    byte_column
  )
end

local function normalized_for_buffer(buf)
  if buf == 0 then buf = vim.api.nvim_get_current_buf() end
  if not cache_enabled then
    local ok, values = pcall(vim.diagnostic.get, buf)
    return M.normalized(ok and values or {})
  end
  local cached = buffer_cache[buf]
  if cached then return cached end
  local ok, values = pcall(vim.diagnostic.get, buf)
  cached = M.normalized(ok and values or {})
  buffer_cache[buf] = cached
  return cached
end

local function normalized_for_line(buf, line_number)
  if buf == 0 then buf = vim.api.nvim_get_current_buf() end
  local cursor_line = line_number - 1
  local cached = cache_enabled and buffer_line_cache[buf] or nil
  if cached and cached.line == cursor_line then return cached.values end
  local values = {}
  for _, diagnostic in ipairs(normalized_for_buffer(buf)) do
    local ends_after_line = diagnostic.end_lnum > cursor_line
      or (diagnostic.end_lnum == cursor_line
        and (diagnostic.end_col > 0 or diagnostic.end_lnum == diagnostic.lnum))
    if diagnostic.lnum <= cursor_line and ends_after_line then
      values[#values + 1] = diagnostic
    end
  end
  if cache_enabled then
    buffer_line_cache[buf] = { line = cursor_line, values = values }
  end
  return values
end

function M.snapshot(buf, line_number, byte_column)
  return snapshot_normalized(normalized_for_buffer(buf), line_number, byte_column)
end

local function public_diagnostic(diagnostic, at_cursor)
  return {
    message = diagnostic.message,
    severity = severity_names[diagnostic.severity],
    source = diagnostic.source,
    code = diagnostic.code == nil and vim.NIL or diagnostic.code,
    line = diagnostic.lnum + 1,
    byteColumn = diagnostic.col,
    endLine = diagnostic.end_lnum + 1,
    endByteColumn = diagnostic.end_col,
    atCursor = at_cursor,
  }
end

function M.context(buf, line_number, byte_column)
  local all = normalized_for_line(buf, line_number)
  local cursor_line = line_number - 1
  local at_cursor, on_line = {}, {}
  for _, diagnostic in ipairs(all) do
    if contains(diagnostic, cursor_line, byte_column) then
      at_cursor[#at_cursor + 1] = public_diagnostic(diagnostic, true)
    else
      on_line[#on_line + 1] = public_diagnostic(diagnostic, false)
    end
  end
  while #at_cursor > 100 do table.remove(at_cursor) end
  for _, diagnostic in ipairs(on_line) do
    if #at_cursor >= 100 then break end
    at_cursor[#at_cursor + 1] = diagnostic
  end
  return at_cursor
end

function M.summary(buf, line_number, byte_column)
  local all = normalized_for_line(buf, line_number)
  local cursor_line = line_number - 1
  local line_count, position_count = 0, 0
  local line_severity, position_severity
  local position_identity = ""
  for _, diagnostic in ipairs(all) do
    line_count = line_count + 1
    if not line_severity or diagnostic.severity < line_severity then
      line_severity = diagnostic.severity
    end
    if contains(diagnostic, cursor_line, byte_column) then
      position_count = position_count + 1
      if not position_severity or diagnostic.severity < position_severity then
        position_severity = diagnostic.severity
        position_identity = table.concat({
          tostring(diagnostic.severity),
          tostring(diagnostic.lnum),
          tostring(diagnostic.col),
          tostring(diagnostic.end_lnum),
          tostring(diagnostic.end_col),
        }, ":")
      end
    end
  end
  return {
    lineCount = line_count,
    lineSeverity = severity_names[line_severity] or "",
    positionCount = position_count,
    positionSeverity = severity_names[position_severity] or "",
    positionIdentity = position_identity,
  }
end

local function emit_moved(reason)
  if type(current_emit) ~= "function" then return end
  vim.schedule(function() current_emit("diagnosticMoved", reason) end)
end

local function record_navigation(reason)
  navigation_sequence = navigation_sequence + 1
  local cursor = vim.api.nvim_win_get_cursor(0)
  local token = {
    sequence = navigation_sequence,
    buffer = vim.api.nvim_get_current_buf(),
    window = vim.api.nvim_get_current_win(),
    line = cursor[1],
    byte_column = cursor[2],
    reason = reason,
  }
  pending_navigation = token
  vim.defer_fn(function()
    if pending_navigation ~= token then return end
    pending_navigation = nil
    if type(current_emit) == "function" then current_emit("diagnosticMoved", reason) end
  end, 20)
end

local function diagnostics_for_current_buffer()
  return normalized_for_buffer(vim.api.nvim_get_current_buf())
end

local function direct_cursor_jump(diagnostic)
  if not diagnostic then return false end
  local ok = pcall(vim.api.nvim_win_set_cursor, 0, {
    diagnostic.lnum + 1,
    diagnostic.col,
  })
  if ok then pcall(vim.cmd, "normal! zv") end
  return ok
end

local function move(kind)
  local all = diagnostics_for_current_buffer()
  if kind == "current" or #all == 0 then
    emit_moved("diagnosticCommand")
    return
  end
  local moved = false
  if kind == "first" or kind == "last" then
    local target = kind == "first" and all[1] or all[#all]
    if type(vim.diagnostic.jump) == "function" then
      moved = pcall(vim.diagnostic.jump, {
        diagnostic = target.raw,
        on_jump = function() end,
      })
    else
      moved = direct_cursor_jump(target)
    end
  elseif type(vim.diagnostic.jump) == "function" then
    moved = pcall(vim.diagnostic.jump, {
      count = kind == "next" and 1 or -1,
      on_jump = function() end,
      wrap = true,
    })
  else
    local legacy = kind == "next" and vim.diagnostic.goto_next or vim.diagnostic.goto_prev
    if type(legacy) == "function" then
      moved = pcall(legacy, { float = false, wrap = true })
    end
  end
  if moved then
    record_navigation("diagnosticCommand")
  else
    emit_moved("diagnosticCommandFailed")
  end
end

function M.consume_navigation()
  local token = pending_navigation
  if not token then return false end
  if token.buffer ~= vim.api.nvim_get_current_buf()
    or token.window ~= vim.api.nvim_get_current_win() then
    pending_navigation = nil
    return false
  end
  local cursor = vim.api.nvim_win_get_cursor(0)
  pending_navigation = nil
  return token.line == cursor[1] and token.byte_column == cursor[2]
end

local function install_jump_hook()
  if type(vim.diagnostic.jump) ~= "function" then return end
  local ok, config = pcall(vim.diagnostic.config)
  if not ok or type(config) ~= "table" or type(config.jump) ~= "table" then return end
  local existing = config.jump.on_jump
  if existing ~= jump_callback then previous_jump_callback = existing end
  jump_callback = function(diagnostic, bufnr)
    if type(previous_jump_callback) == "function" then
      pcall(previous_jump_callback, diagnostic, bufnr)
    end
    if bufnr == vim.api.nvim_get_current_buf() then record_navigation("diagnosticJump") end
  end
  local jump = vim.deepcopy(config.jump)
  jump.on_jump = jump_callback
  pcall(vim.diagnostic.config, { jump = jump })
end

function M.setup(emit, group)
  current_emit = emit
  buffer_cache = {}
  buffer_line_cache = {}
  cache_enabled = group ~= nil
  if group then
    vim.api.nvim_create_autocmd({ "DiagnosticChanged", "BufWipeout" }, {
      group = group,
      callback = function(event)
        buffer_cache[event.buf] = nil
        buffer_line_cache[event.buf] = nil
      end,
    })
  end
  install_jump_hook()
  for _, name in ipairs(command_names) do pcall(vim.api.nvim_del_user_command, name) end
  local commands = {
    NvimNvdaDiagnosticPrevious = { "previous", "Move to the previous accessible diagnostic" },
    NvimNvdaDiagnosticNext = { "next", "Move to the next accessible diagnostic" },
    NvimNvdaDiagnosticFirst = { "first", "Move to the first accessible diagnostic" },
    NvimNvdaDiagnosticLast = { "last", "Move to the last accessible diagnostic" },
    NvimNvdaDiagnosticCurrent = { "current", "Report the current accessible diagnostic" },
  }
  for name, command in pairs(commands) do
    vim.api.nvim_create_user_command(name, function() move(command[1]) end, {
      desc = command[2],
    })
  end
end

return M
