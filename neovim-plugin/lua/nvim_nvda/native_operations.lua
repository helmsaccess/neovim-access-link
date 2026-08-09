local M = {}

local MAX_TRACKED_BUFFERS = 2048
local MAX_PREVIEW_LINES = 2048
local MAX_PREVIEW_BYTES = 256 * 1024
local MAX_CHANGED_LINE_RANGES = 2048
local SEARCH_PREVIEW_DELAY_MS = 35
local SUBSTITUTE_PREVIEW_DELAY_MS = 35
local LSP_RENAME_SETTLE_MS = 500
local LSP_OBSERVATION_TIMEOUT_MS = 10000
local SUBSTITUTE_CONFIRM_PROMPT = "Replace this match? Y yes, N no, A all, Q quit, L last"

local emit
local emit_prebuilt
local emit_event
local preview_difference
local substitute_argument_ready
local command_snapshot
local active_command
local substitute_prompt_snapshot
local open_substitute_prompt_snapshot
local substitute_prompt_open = false
local search_generation = 0
local last_search_preview
local search_origin
local last_search_match
local search_highlight_generation = 0
local substitute_preview_generation = 0
local substitute_preview
local attached_buffers = {}
local rename_observation
local rename_generation = 0
local rename_event_tail

local substitute_commands = {
  substitute = true,
  smagic = true,
  snomagic = true,
  ["&"] = true,
  ["~"] = true,
}

local bulk_scopes = {
  cdo = "quickfixEntries",
  cfdo = "quickfixFiles",
  ldo = "locationEntries",
  lfdo = "locationFiles",
  argdo = "arguments",
  bufdo = "buffers",
}

local result_commands = {
  vimgrep = "quickfix",
  vimgrepadd = "quickfix",
  grep = "quickfix",
  grepadd = "quickfix",
  lvimgrep = "locationList",
  lvimgrepadd = "locationList",
  lgrep = "locationList",
  lgrepadd = "locationList",
}

local function parse_command(command)
  if type(command) ~= "string" or command == "" then return nil end
  local ok, parsed = pcall(vim.api.nvim_parse_cmd, command, {})
  return ok and type(parsed) == "table" and parsed or nil
end

local function nested_command(parsed)
  if type(parsed.args) ~= "table" or #parsed.args == 0 then return nil end
  return parse_command(table.concat(parsed.args, " "))
end

function M.classify(command)
  local parsed = parse_command(command)
  if not parsed or type(parsed.cmd) ~= "string" then return nil end
  if substitute_commands[parsed.cmd] then
    return { kind = "substitute", scope = "buffer", command = parsed.cmd }
  end
  if parsed.cmd == "nohlsearch" then
    return { kind = "searchHighlight", command = parsed.cmd }
  end
  local scope = bulk_scopes[parsed.cmd]
  if scope then
    local nested = nested_command(parsed)
    if nested and substitute_commands[nested.cmd] then
      return {
        kind = "substitute",
        scope = scope,
        command = parsed.cmd,
        nestedCommand = nested.cmd,
      }
    end
    return nil
  end
  local list_kind = result_commands[parsed.cmd]
  if list_kind then
    return { kind = "resultList", listKind = list_kind, command = parsed.cmd }
  end
  return nil
end

local function search_highlighting()
  local ok, value = pcall(function() return vim.o.hlsearch and tonumber(vim.v.hlsearch) == 1 end)
  return ok and value == true
end

local function position_at_or_before(current, origin)
  return current[1] < origin[1] or (current[1] == origin[1] and current[2] <= origin[2])
end

local function position_at_or_after(current, origin)
  return current[1] > origin[1] or (current[1] == origin[1] and current[2] >= origin[2])
end

local function actual_search_forward(direction)
  if direction == "/" then return true end
  if direction == "?" then return false end
  local forward = tonumber(vim.v.searchforward) == 1
  if direction == "next" then return forward end
  if direction == "previous" then return not forward end
  return nil
end

function M.search_details(pattern, direction, preview)
  local options = { recompute = 1, maxcount = 9999, timeout = 50 }
  if preview and type(pattern) == "string" and pattern ~= "" then options.pattern = pattern end
  local ok_count, value = pcall(vim.fn.searchcount, options)
  local count = ok_count and type(value) == "table" and value or {}
  local cursor = vim.api.nvim_win_get_cursor(0)
  local buffer = vim.api.nvim_get_current_buf()
  local effective_pattern = pattern or vim.fn.getreg("/")
  local current = math.max(0, tonumber(count.current) or 0)
  local total = math.max(0, tonumber(count.total) or 0)
  local forward = actual_search_forward(direction)
  local wrapped = false
  if search_origin and search_origin.buffer == buffer
    and (direction == "/" or direction == "?") and current > 0 then
    wrapped = forward and position_at_or_before(cursor, search_origin.cursor)
      or forward == false and position_at_or_after(cursor, search_origin.cursor)
  elseif not preview and last_search_match and last_search_match.buffer == buffer
    and last_search_match.pattern == effective_pattern and total > 0
    and last_search_match.total == total and current > 0 then
    wrapped = forward and last_search_match.current == total and current == 1
      or forward == false and last_search_match.current == 1 and current == total
  end
  local details = {
    searchPattern = effective_pattern,
    searchDirection = direction,
    searchPreview = preview == true,
    searchWrapped = wrapped == true,
    searchHighlighting = search_highlighting(),
    matchIndex = current,
    matchCount = total,
    matchIncomplete = math.max(0, tonumber(count.incomplete) or 0),
    matchLine = cursor[1],
    matchByteColumn = cursor[2],
  }
  if not preview then
    last_search_match = {
      buffer = buffer, pattern = effective_pattern, current = current, total = total,
    }
    if direction == "/" or direction == "?" then search_origin = nil end
  end
  return details
end

local function preview_baseline(buffer)
  local cursor = vim.api.nvim_win_get_cursor(0)
  local line_count = vim.api.nvim_buf_line_count(buffer)
  local ok_bytes, byte_count = pcall(vim.api.nvim_buf_get_offset, buffer, line_count)
  local complete = line_count <= MAX_PREVIEW_LINES and ok_bytes
    and type(byte_count) == "number" and byte_count >= 0 and byte_count <= MAX_PREVIEW_BYTES
  local lines
  if complete then
    local ok_lines, value = pcall(vim.api.nvim_buf_get_lines, buffer, 0, -1, true)
    if ok_lines then lines = value else complete = false end
  end
  local ok_line, current = pcall(vim.api.nvim_buf_get_lines, buffer, cursor[1] - 1, cursor[1], true)
  return {
    buffer = buffer,
    cursorLine = cursor[1],
    currentLine = ok_line and current[1] or "",
    lines = lines,
    complete = complete,
    announced = false,
    identity = nil,
  }
end

local function note_changed_lines(operation, buffer, first, old_last, new_last)
  if not operation or operation.classification.scope ~= "buffer" or operation.buffer ~= buffer then
    return
  end
  local finish = math.max(tonumber(old_last) or first, tonumber(new_last) or first)
  if finish <= first then finish = first + 1 end
  local ranges = operation.changedLineRanges
  if #ranges >= MAX_CHANGED_LINE_RANGES then
    operation.changedLineCountIncomplete = true
    return
  end
  ranges[#ranges + 1] = { first = first, finish = finish }
end

local function ensure_buffer_attachment(buffer)
  if attached_buffers[buffer] or not vim.api.nvim_buf_is_loaded(buffer) then return end
  local ok, attached = pcall(vim.api.nvim_buf_attach, buffer, false, {
    preview = true,
    on_lines = function(_, changed_buffer, changedtick, first, old_last, new_last)
      if changedtick ~= nil and changedtick ~= vim.NIL then
        note_changed_lines(active_command, changed_buffer, first, old_last, new_last)
      elseif substitute_preview and substitute_preview.buffer == changed_buffer then
        -- Neovim exposes inccommand text only while this public preview
        -- callback is running. Capture the semantic result now; emitting it
        -- remains deferred so RPC and presentation never run in the callback.
        local ok_type, command_type = pcall(vim.fn.getcmdtype)
        local ok_line, command = pcall(vim.fn.getcmdline)
        if ok_type and ok_line and command_type == ":" and substitute_argument_ready(command) then
          if substitute_preview.pendingCommand ~= command then
            substitute_preview.pendingCommand = command
            substitute_preview.pendingDetails = nil
          end
          local ok_details, details = pcall(preview_difference, substitute_preview)
          if ok_details and details and details.previewHasChanges == true then
            substitute_preview.pendingDetails = details
          elseif ok_details and details and not substitute_preview.pendingDetails then
            substitute_preview.pendingDetails = details
          end
        end
      end
    end,
    on_detach = function(_, detached_buffer)
      attached_buffers[detached_buffer] = nil
    end,
  })
  if ok and attached then attached_buffers[buffer] = true end
end

local function changed_line_count(ranges)
  if type(ranges) ~= "table" or #ranges == 0 then return 0 end
  table.sort(ranges, function(left, right) return left.first < right.first end)
  local total = 0
  local first = ranges[1].first
  local finish = ranges[1].finish
  for index = 2, #ranges do
    local range = ranges[index]
    if range.first <= finish then
      finish = math.max(finish, range.finish)
    else
      total = total + finish - first
      first = range.first
      finish = range.finish
    end
  end
  return total + finish - first
end

substitute_argument_ready = function(command)
  local parsed = parse_command(command)
  if not parsed or not substitute_commands[parsed.cmd] or parsed.cmd == "&" or parsed.cmd == "~"
    or type(parsed.args) ~= "table" or type(parsed.args[1]) ~= "string" then
    return false
  end
  local argument = parsed.args[1]
  local delimiter = argument:sub(1, 1)
  if delimiter == "" then return false end
  local escaped = false
  for index = 2, #argument do
    local character = argument:sub(index, index)
    if character == delimiter and not escaped then return true end
    if character == "\\" then escaped = not escaped else escaped = false end
  end
  return false
end

preview_difference = function(session)
  local buffer = session.buffer
  if not vim.api.nvim_buf_is_valid(buffer) or not vim.api.nvim_buf_is_loaded(buffer) then return nil end
  local cursor = vim.api.nvim_win_get_cursor(0)
  local ok_line, current = pcall(vim.api.nvim_buf_get_lines, buffer, cursor[1] - 1, cursor[1], true)
  local details = {
    previewActive = true,
    previewLineText = ok_line and current[1] or "",
    previewLine = cursor[1],
    previewIncomplete = session.complete ~= true,
    inccommandMode = vim.o.inccommand,
  }
  if not session.complete or type(session.lines) ~= "table" then
    if cursor[1] == session.cursorLine then
      details.previewHasChanges = details.previewLineText ~= session.currentLine
      details.previewChangedLineCount = details.previewHasChanges and 1 or 0
    end
    return details
  end
  local line_count = vim.api.nvim_buf_line_count(buffer)
  local ok_bytes, byte_count = pcall(vim.api.nvim_buf_get_offset, buffer, line_count)
  if line_count > MAX_PREVIEW_LINES or not ok_bytes or byte_count > MAX_PREVIEW_BYTES then
    details.previewIncomplete = true
    return details
  end
  local ok_lines, lines = pcall(vim.api.nvim_buf_get_lines, buffer, 0, -1, true)
  if not ok_lines then
    details.previewIncomplete = true
    return details
  end
  local original = session.lines
  if #original == #lines then
    local changed = 0
    for index = 1, #original do
      if original[index] ~= lines[index] then
        changed = changed + 1
      end
    end
    details.previewHasChanges = changed > 0
    details.previewChangedLineCount = changed
    return details
  end
  local prefix = 0
  while prefix < #original and prefix < #lines and original[prefix + 1] == lines[prefix + 1] do
    prefix = prefix + 1
  end
  local suffix = 0
  while suffix < #original - prefix and suffix < #lines - prefix
    and original[#original - suffix] == lines[#lines - suffix] do
    suffix = suffix + 1
  end
  local removed = #original - prefix - suffix
  local added = #lines - prefix - suffix
  details.previewHasChanges = removed > 0 or added > 0
  details.previewChangedLineCount = math.max(removed, added)
  return details
end

local function close_substitute_preview(reason)
  substitute_preview_generation = substitute_preview_generation + 1
  local session = substitute_preview
  substitute_preview = nil
  if not session or not session.announced then return end
  vim.schedule(function()
    emit_event("substitutePreviewChanged", reason, { previewActive = false })
  end)
end

local function schedule_substitute_preview(command)
  if not substitute_preview or vim.o.inccommand == "" or not substitute_argument_ready(command) then
    return
  end
  substitute_preview_generation = substitute_preview_generation + 1
  local generation = substitute_preview_generation
  local session = substitute_preview
  if session.pendingCommand ~= command then
    session.pendingCommand = command
    session.pendingDetails = nil
  end
  vim.defer_fn(function()
    local current = substitute_preview
    if generation ~= substitute_preview_generation or current ~= session then return end
    local ok_type, command_type = pcall(vim.fn.getcmdtype)
    local ok_line, command_line = pcall(vim.fn.getcmdline)
    if not ok_type or not ok_line or command_type ~= ":" or command_line ~= command then return end
    local details = session.pendingDetails or {
      previewActive = true,
      previewHasChanges = false,
      previewChangedLineCount = 0,
      previewLineText = session.currentLine,
      previewLine = session.cursorLine,
      previewIncomplete = session.complete ~= true,
      inccommandMode = vim.o.inccommand,
    }
    local identity = table.concat({
      tostring(details.previewHasChanges), tostring(details.previewChangedLineCount),
      tostring(details.previewLine), tostring(details.previewLineText),
      tostring(details.previewIncomplete), tostring(details.inccommandMode),
    }, ":")
    if identity == session.identity then return end
    session.identity = identity
    session.announced = true
    emit_event("substitutePreviewChanged", "substitutePreview", details)
  end, SUBSTITUTE_PREVIEW_DELAY_MS)
end

local function buffer_value(buffer)
  if not vim.api.nvim_buf_is_valid(buffer) then return nil end
  local ok_tick, changedtick = pcall(vim.api.nvim_buf_get_changedtick, buffer)
  local ok_name, name = pcall(vim.api.nvim_buf_get_name, buffer)
  local ok_modified, modified = pcall(function() return vim.bo[buffer].modified end)
  if not ok_tick then return nil end
  return {
    changedtick = changedtick,
    name = ok_name and name or "",
    modified = ok_modified and modified == true or false,
  }
end

function M.buffer_snapshot()
  local values = {}
  local buffers = vim.api.nvim_list_bufs()
  local limited = #buffers > MAX_TRACKED_BUFFERS
  for index = 1, math.min(#buffers, MAX_TRACKED_BUFFERS) do
    local buffer = buffers[index]
    local value = buffer_value(buffer)
    if value then values[buffer] = value end
  end
  return { buffers = values, limited = limited }
end

function M.buffer_changes(before)
  before = type(before) == "table" and before or { buffers = {}, limited = true }
  local after = M.buffer_snapshot()
  local changed = 0
  local modified = 0
  local renamed = 0
  local created = 0
  local deleted = 0
  local seen = {}
  for buffer, current in pairs(after.buffers) do
    seen[buffer] = true
    local previous = before.buffers and before.buffers[buffer] or nil
    if not previous then
      created = created + 1
      changed = changed + 1
      if current.modified then modified = modified + 1 end
    elseif previous.changedtick ~= current.changedtick or previous.name ~= current.name then
      changed = changed + 1
      if current.modified then modified = modified + 1 end
      if previous.name ~= current.name then renamed = renamed + 1 end
    end
  end
  for buffer in pairs(before.buffers or {}) do
    if not seen[buffer] then
      deleted = deleted + 1
      changed = changed + 1
    end
  end
  return {
    changedBufferCount = changed,
    modifiedBufferCount = modified,
    renamedBufferCount = renamed,
    createdBufferCount = created,
    deletedBufferCount = deleted,
    observationLimited = before.limited == true or after.limited == true,
  }
end

local function result_list_details(list_kind)
  local ok, details
  if list_kind == "locationList" then
    ok, details = pcall(vim.fn.getloclist, 0, { idx = 0, size = 0 })
  else
    ok, details = pcall(vim.fn.getqflist, { idx = 0, size = 0 })
  end
  if not ok or type(details) ~= "table" then return nil end
  return {
    listKind = list_kind,
    itemCount = math.max(0, tonumber(details.size) or 0),
    itemIndex = math.max(0, tonumber(details.idx) or 0),
  }
end

emit_event = function(event_type, reason, payload)
  if type(emit) == "function" then emit(event_type, reason, payload) end
end

local function close_substitute_prompt(prebuilt)
  if not substitute_prompt_open then return end
  if prebuilt and type(emit_prebuilt) == "function"
    and type(open_substitute_prompt_snapshot) == "table" then
    emit_prebuilt("promptClosed", open_substitute_prompt_snapshot, {
      reason = "substituteConfirmation",
      promptKind = "confirmSub",
      answered = true,
    })
  else
    emit_event("promptClosed", "substituteConfirmation", {
      promptKind = "confirmSub",
      answered = true,
    })
  end
  substitute_prompt_open = false
  open_substitute_prompt_snapshot = nil
end

function M.command_line_enter(command_type)
  if command_type == "-" and active_command
    and active_command.classification.kind == "substitute" then
    -- Native :substitute confirmation uses the internal '-' command-line
    -- type. It is part of the active command, not a replacement for it.
    emit_event("promptOpened", "substituteConfirmation", {
      promptKind = "confirmSub",
      prompt = SUBSTITUTE_CONFIRM_PROMPT,
    })
    substitute_prompt_open = true
    return
  end
  active_command = nil
  command_snapshot = nil
  if command_type == "/" or command_type == "?" then
    search_generation = search_generation + 1
    last_search_preview = nil
    search_origin = {
      buffer = vim.api.nvim_get_current_buf(),
      cursor = vim.api.nvim_win_get_cursor(0),
    }
  elseif command_type == ":" then
    local buffer = vim.api.nvim_get_current_buf()
    ensure_buffer_attachment(buffer)
    substitute_preview = nil
  else
    close_substitute_preview("commandLineChanged")
  end
end

local function search_preview(command_type, pattern, generation)
  if generation ~= search_generation or not vim.o.incsearch then return end
  local ok_type, current_type = pcall(vim.fn.getcmdtype)
  local ok_line, current_line = pcall(vim.fn.getcmdline)
  if not ok_type or not ok_line or current_type ~= command_type or current_line ~= pattern then
    return
  end
  -- searchcount() otherwise uses only the last accepted search pattern. The
  -- command-line pattern is still provisional during incsearch, so pass it
  -- explicitly and let Neovim perform the bounded count for its own preview.
  local details = M.search_details(pattern, command_type, true)
  local identity = table.concat({
    tostring(vim.api.nvim_get_current_buf()),
    tostring(details.matchLine),
    tostring(details.matchByteColumn),
    tostring(details.matchIndex),
    tostring(details.matchCount),
    tostring(details.matchIncomplete),
    tostring(details.searchWrapped),
    tostring(details.searchHighlighting),
  }, ":")
  if identity == last_search_preview then return end
  last_search_preview = identity
  emit_event("searchMatchChanged", "searchPreview", details)
end

function M.command_line_changed(command_type, command)
  if command_type == "/" or command_type == "?" then
    if type(command) ~= "string" or command == "" or not vim.o.incsearch then return end
    search_generation = search_generation + 1
    local generation = search_generation
    vim.defer_fn(function() search_preview(command_type, command, generation) end,
      SEARCH_PREVIEW_DELAY_MS)
    return
  end
  if command_type ~= ":" then return end
  local classification = M.classify(command)
  if classification and classification.kind == "substitute" and not command_snapshot then
    command_snapshot = M.buffer_snapshot()
  end
  if classification and classification.kind == "substitute" then
    if not substitute_preview then
      substitute_preview = preview_baseline(vim.api.nvim_get_current_buf())
    end
    schedule_substitute_preview(command)
  elseif substitute_preview and substitute_preview.announced then
    close_substitute_preview("substitutePreviewCleared")
  end
end

function M.search_preview_key(command_type, command)
  if command_type ~= "/" and command_type ~= "?" then return end
  if type(command) ~= "string" or command == "" or not vim.o.incsearch then return end
  search_generation = search_generation + 1
  local generation = search_generation
  vim.defer_fn(function() search_preview(command_type, command, generation) end,
    SEARCH_PREVIEW_DELAY_MS)
end

function M.command_line_leave(command_type, command)
  if command_type == "-" and active_command
    and active_command.classification.kind == "substitute" then
    close_substitute_prompt(false)
    return false
  end
  search_generation = search_generation + 1
  last_search_preview = nil
  close_substitute_preview("commandLineLeave")
  if command_type ~= ":" then
    active_command = nil
    command_snapshot = nil
    return false
  end
  local classification = M.classify(command)
  if not classification then
    active_command = nil
    command_snapshot = nil
    return false
  end
  if classification.kind == "substitute" and not command_snapshot then
    command_snapshot = M.buffer_snapshot()
  end
  active_command = {
    classification = classification,
    before = command_snapshot,
    buffer = vim.api.nvim_get_current_buf(),
    changedLineRanges = {},
    changedLineCountIncomplete = false,
  }
  command_snapshot = nil
  return true
end

function M.consume_text_change()
  if rename_observation then return true end
  if rename_event_tail and rename_event_tail.text then
    rename_event_tail.text = false
    return true
  end
  return active_command ~= nil and active_command.classification.kind == "substitute"
end

function M.consume_intermediate_update(kind)
  if rename_observation then return true end
  if rename_event_tail and rename_event_tail[kind] then
    rename_event_tail[kind] = false
    return true
  end
  return active_command ~= nil
    and active_command.classification.kind == "substitute"
    and active_command.classification.scope ~= "buffer"
end

function M.is_active()
  return active_command ~= nil
end

function M.is_substitute_active()
  return active_command ~= nil and active_command.classification.kind == "substitute"
end

function M.capture_substitute_prompt_snapshot(snapshot)
  if not M.is_substitute_active() or type(snapshot) ~= "table" then return false end
  substitute_prompt_snapshot = snapshot
  return true
end

function M.open_legacy_substitute_prompt()
  if not M.is_substitute_active() or type(emit_prebuilt) ~= "function"
    or type(substitute_prompt_snapshot) ~= "table" then
    return false
  end
  close_substitute_prompt(true)
  local snapshot = substitute_prompt_snapshot
  substitute_prompt_snapshot = nil
  open_substitute_prompt_snapshot = vim.deepcopy(snapshot)
  local opened = emit_prebuilt("promptOpened", snapshot, {
    reason = "substituteConfirmation",
    promptKind = "confirmSub",
    prompt = SUBSTITUTE_CONFIRM_PROMPT,
  })
  substitute_prompt_open = opened == true
  if not substitute_prompt_open then open_substitute_prompt_snapshot = nil end
  return opened == true
end

function M.clear_post_rename_updates()
  rename_event_tail = nil
end

function M.finish_command(status)
  local operation = active_command
  local ok_mode, mode = pcall(vim.api.nvim_get_mode)
  local raw_mode = ok_mode and type(mode) == "table" and tostring(mode.mode or "") or ""
  if operation and ok_mode and type(mode) == "table"
    and (mode.blocking == true or raw_mode == "r" or raw_mode == "rm" or raw_mode == "r?") then
    -- Native confirmation prompts keep the Ex command alive.  Keep the
    -- observation open until Neovim leaves the prompt instead of reporting a
    -- partial result or taking ownership of the prompt interaction.
    return true, true
  end
  close_substitute_prompt(false)
  active_command = nil
  if not operation then return false, false end
  local classification = operation.classification
  if classification.kind == "resultList" then
    local details = result_list_details(classification.listKind)
    if not details then return true, false end
    emit_event("resultListChanged", "nativeProjectSearch", details)
    return true, true
  end
  if classification.kind == "searchHighlight" then
    emit_event("searchHighlightChanged", "nohlsearchCommand", {
      searchHighlighting = search_highlighting(),
    })
    return true, true
  end
  if classification.kind ~= "substitute" or not operation.before then return true, false end
  local details = M.buffer_changes(operation.before)
  if details.changedBufferCount <= 0 then return true, false end
  details.replacementMessage = type(status) == "string" and status or ""
  details.replacementScope = classification.scope
  details.bulkReplacement = classification.scope ~= "buffer"
  if classification.scope == "buffer" then
    details.changedLineCount = changed_line_count(operation.changedLineRanges)
    details.changedLineCountIncomplete = operation.changedLineCountIncomplete == true
  end
  emit_event("replacementPerformed", "substituteCommand", details)
  return true, true
end

function M.cancel_command()
  close_substitute_prompt(false)
  active_command = nil
  command_snapshot = nil
  substitute_prompt_snapshot = nil
  close_substitute_preview("commandCanceled")
end

local function request_key(data)
  return tostring(data.client_id or "") .. ":" .. tostring(data.request_id or "")
end

local function pending_count(requests)
  local count = 0
  for _ in pairs(requests or {}) do count = count + 1 end
  return count
end

local function finish_rename(generation)
  local observation = rename_observation
  if not observation or observation.generation ~= generation then return end
  if pending_count(observation.requests) > 0 then return end
  rename_observation = nil
  -- Neovim can publish a trailing TextChanged, CursorMoved, or context event
  -- after the public LSP request has completed. Consume at most one of each
  -- operation-owned kind. The next physical key clears anything unused, so
  -- subsequent user navigation can never be mistaken for rename fallout.
  rename_event_tail = { text = true, cursor = true, context = true }
  local details = M.buffer_changes(observation.before)
  if observation.nativeMessageSeen and details.changedBufferCount == 0 then return end
  details.renameResult = details.changedBufferCount > 0 and "changesObserved"
    or (observation.canceled and "canceled" or "noChangesObserved")
  emit_event("lspRenameCompleted", "LspRequest", details)
end

local function schedule_rename_finish(observation)
  local generation = observation.generation
  observation.completionPending = true
  observation.settleGeneration = (observation.settleGeneration or 0) + 1
  local settle_generation = observation.settleGeneration
  vim.defer_fn(function()
    if rename_observation and rename_observation.generation == generation
      and rename_observation.settleGeneration == settle_generation
      and pending_count(rename_observation.requests) == 0 then
      finish_rename(generation)
    end
  end, LSP_RENAME_SETTLE_MS)
end

function M.note_intermediate_update()
  local observation = rename_observation
  if not observation or observation.completionPending ~= true then return end
  schedule_rename_finish(observation)
end

function M.lsp_request(event)
  local data = type(event) == "table" and event.data or nil
  local request = type(data) == "table" and data.request or nil
  if type(request) ~= "table" or request.method ~= "textDocument/rename" then return end
  local request_type = request.type
  local key = request_key(data)
  if request_type == "pending" then
    if not rename_observation then
      rename_generation = rename_generation + 1
      rename_event_tail = nil
      rename_observation = {
        generation = rename_generation,
        buffer = event.buf,
        before = M.buffer_snapshot(),
        requests = {},
        canceled = false,
        nativeMessageSeen = false,
      }
      local generation = rename_generation
      vim.defer_fn(function()
        if rename_observation and rename_observation.generation == generation then
          rename_observation = nil
        end
      end, LSP_OBSERVATION_TIMEOUT_MS)
    end
    rename_observation.requests[key] = true
  elseif rename_observation and request_type == "cancel" then
    rename_observation.requests[key] = nil
    rename_observation.canceled = true
    schedule_rename_finish(rename_observation)
  elseif rename_observation and request_type == "complete" then
    rename_observation.requests[key] = nil
    schedule_rename_finish(rename_observation)
  end
end

function M.note_notification()
  if rename_observation then rename_observation.nativeMessageSeen = true end
end

function M.reset()
  substitute_prompt_open = false
  substitute_prompt_snapshot = nil
  open_substitute_prompt_snapshot = nil
  command_snapshot = nil
  active_command = nil
  search_generation = search_generation + 1
  last_search_preview = nil
  search_origin = nil
  last_search_match = nil
  search_highlight_generation = search_highlight_generation + 1
  substitute_preview_generation = substitute_preview_generation + 1
  substitute_preview = nil
  rename_generation = rename_generation + 1
  rename_observation = nil
  rename_event_tail = nil
end

function M.set_prebuilt_emitter(callback)
  emit_prebuilt = callback
end

function M.setup(callback, group)
  emit = callback
  M.reset()
  vim.api.nvim_create_autocmd("LspRequest", {
    group = group,
    callback = M.lsp_request,
  })
  vim.api.nvim_create_autocmd("OptionSet", {
    group = group,
    pattern = "hlsearch",
    callback = function()
      search_highlight_generation = search_highlight_generation + 1
      local generation = search_highlight_generation
      vim.schedule(function()
        if generation ~= search_highlight_generation then return end
        if vim.o.hlsearch and not search_highlighting() then return end
        emit_event("searchHighlightChanged", "OptionSet", {
          searchHighlighting = search_highlighting(),
        })
      end)
    end,
  })
end

return M
