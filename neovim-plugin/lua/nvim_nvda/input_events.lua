local state_snapshot = require("nvim_nvda.state")
local text = require("nvim_nvda.text")
local signature_help = require("nvim_nvda.signature_help")
local file_manager = require("nvim_nvda.file_manager")
local completion_adapters = require("nvim_nvda.completion_adapters")
local native_operations = require("nvim_nvda.native_operations")
local diagnostics = require("nvim_nvda.diagnostics")

local M = {}

local motion_events = {
  h = "characterMoved", l = "characterMoved",
  ["<Left>"] = "characterMoved", ["<Right>"] = "characterMoved",
  w = "wordMoved", W = "wordMoved", b = "wordMoved", B = "wordMoved",
  e = "wordMoved", E = "wordMoved",
  ["<C-Left>"] = "wordMoved", ["<C-Right>"] = "wordMoved",
  j = "lineChanged", k = "lineChanged",
  ["<Down>"] = "lineChanged", ["<Up>"] = "lineChanged",
  ["<C-N>"] = "lineChanged", ["<C-P>"] = "lineChanged",
  ["0"] = "lineStart", ["^"] = "lineStart", ["<Home>"] = "lineStart",
  ["$"] = "lineEnd", ["<End>"] = "lineEnd",
  G = "fileEnd",
  n = "searchMatchChanged", N = "searchMatchChanged",
  ["%"] = "matchingPairMoved",
  i = "suppress", I = "suppress", a = "suppress", A = "suppress",
  o = "suppress", O = "suppress",
  ["<Esc>"] = "suppress",
}

-- Printable keys have a completely different meaning in Insert mode. Only
-- keys which genuinely move the Insert-mode cursor are accepted here.
local insert_motion_events = {
  ["<Left>"] = "characterMoved", ["<Right>"] = "characterMoved",
  ["<C-Left>"] = "wordMoved", ["<C-Right>"] = "wordMoved",
  ["<Down>"] = "lineChanged", ["<Up>"] = "lineChanged",
  ["<C-N>"] = "lineChanged", ["<C-P>"] = "lineChanged",
  ["<Home>"] = "lineStart", ["<End>"] = "lineEnd",
}

local fold_actions = {
  c = "close", o = "open", a = "toggle", C = "closeRecursive", O = "openRecursive",
  M = "closeAll", R = "openAll", j = "next", k = "previous",
}

local function fold_at_cursor()
  local line = vim.api.nvim_win_get_cursor(0)[1]
  local first = vim.fn.foldclosed(line)
  if first < 0 then return { line = line, level = vim.fn.foldlevel(line), closed = false } end
  return {
    line = line, level = vim.fn.foldlevel(line), closed = true,
    startLine = first, endLine = vim.fn.foldclosedend(line),
  }
end

local function is_word_terminator(key)
  return type(key) == "string" and #key == 1 and key ~= "'"
    and (key:match("%s") ~= nil or key:match("[%p]") ~= nil)
end

local function error_ending_at(snapshot, byte_column)
  local nearest
  for _, item in ipairs(snapshot.spellingErrors or {}) do
    if item.endByteColumn == byte_column then nearest = item end
  end
  return nearest
end

function M.new(options)
  assert(type(options) == "table", "input event options required")
  assert(type(options.emit) == "function", "event emitter required")
  assert(type(options.command_line_state) == "function", "command-line state callback required")
  assert(type(options.observe_oil_key) == "function", "Oil key callback required")
  assert(type(options.oil_confirmation_active) == "function", "Oil state callback required")
  assert(type(options.emit_oil_confirmation) == "function", "Oil prompt callback required")
  assert(type(options.set_spell_candidate) == "function", "spell candidate callback required")
  assert(type(options.search_details) == "function", "search details callback required")
  assert(type(options.classify_error) == "function", "error classifier required")

  local emit = options.emit
  local key_namespace = vim.api.nvim_create_namespace("nvim_nvda_keys")
  local current = {
    navigation_scheduled = false,
    motion = nil,
    motion_details = nil,
    search_direction = nil,
    matching = nil,
    edit = nil,
    suppress_next_text_change = false,
    prefix = {
      g = false,
      bracket = nil,
      z = nil,
      mark = nil,
      macro = false,
      register = false,
    },
    diagnostics = { observerErrorCount = 0 },
  }
  local instance = {}

  local function clear_motion()
    current.motion = nil
    current.motion_details = nil
    current.search_direction = nil
  end

  local function emit_typed_spelling_error(before)
    local snapshot = state_snapshot.snapshot("spellingTypingCheck")
    local cursor = snapshot.cursor or {}
    local nearest = error_ending_at(snapshot, math.max(0, (cursor.byteColumn or 0) - 1))
      or error_ending_at(before or {}, ((before or {}).cursor or {}).byteColumn)
    if nearest then
      emit("spellingErrorTyped", "spellingTypingCheck", { spellingError = nearest })
    end
  end

  local function schedule_navigation(reason)
    if current.navigation_scheduled then return end
    current.navigation_scheduled = true
    local motion = current.motion
    local motion_details = current.motion_details
    local search_direction = current.search_direction
    clear_motion()
    vim.schedule(function()
      current.navigation_scheduled = false
      if options.oil_confirmation_active() then return end
      local raw = vim.api.nvim_get_mode().mode
      if raw:sub(1, 1) == "i" and not motion then return end
      if motion == "suppress" then return end
      local event_type = (raw == "v" or raw == "V" or raw == "\22") and "selectionChanged"
        or motion or "cursorMoved"
      if motion == "matchingPairMoved" then current.matching = nil end
      local extra
      if event_type == "searchMatchChanged" then
        extra = options.search_details(nil, search_direction)
      elseif motion_details then
        extra = motion_details
      end
      if file_manager.current() then
        extra = extra or {}
        extra.fileManagerMotion = event_type
        event_type = "fileManagerEntryChanged"
      end
      emit(event_type, reason, extra)
    end)
  end

  function instance.diagnostics()
    return vim.deepcopy(current.diagnostics)
  end

  function instance.set_prompt_diagnostics(details)
    for key, value in pairs(details or {}) do current.diagnostics[key] = value end
  end

  function instance.clear_prompt_diagnostics()
    current.diagnostics.promptActive = false
    current.diagnostics.promptKind = nil
    current.diagnostics.promptClass = nil
    current.diagnostics.promptLength = nil
  end

  function instance.reset_navigation()
    current.navigation_scheduled = false
    clear_motion()
    current.matching = nil
  end

  function instance.setup(group, component_config)
    local version = vim.version()
    local supports_key_consumption = version.major > 0 or version.minor >= 11
    local claim_key = component_config.sessionClaim.neovimKey
    local insert_claim_key_unmapped = vim.fn.maparg(claim_key, "i") == ""
    if not supports_key_consumption and insert_claim_key_unmapped then
      -- Neovim 0.10 cannot consume a key from vim.on_key. Reserve only the
      -- otherwise-unmapped Insert-mode claim key.
      vim.keymap.set("i", claim_key, "<Ignore>", {
        desc = "Neovim Access Link session claim",
        nowait = true,
        silent = true,
      })
    end

    vim.on_key(function(key, typed)
      local observer_ok, observer_result = pcall(function()
        local translated = vim.fn.keytrans(key)
        local typed_translated = vim.fn.keytrans(typed or "")
        if typed_translated ~= "" then native_operations.clear_post_rename_updates() end
        if options.observe_oil_key(typed_translated) then return end
        if typed_translated:lower() == claim_key:lower() then
          current.diagnostics.keyByteLength = #key
          current.diagnostics.typedByteLength = #(typed or "")
          current.diagnostics.translatedKey = translated
          current.diagnostics.translatedTyped = typed_translated
          local claim_mode = vim.api.nvim_get_mode().mode
          if claim_mode:sub(1, 1) == "r" then
            current.diagnostics.claimSkippedMode = claim_mode
            return
          end
          current.diagnostics.claimSkippedMode = ""
          vim.schedule(function()
            local claim_ok, claim_error = pcall(require("nvim_nvda.session").claim)
            current.diagnostics.claimErrorKind = claim_ok and ""
              or options.classify_error(claim_error)
            local mode_ok, mode_value = pcall(vim.api.nvim_get_mode)
            current.diagnostics.modeAfterClaim = mode_ok and mode_value.mode or "unavailable"
          end)
          if supports_key_consumption and insert_claim_key_unmapped
            and claim_mode:sub(1, 1) == "i" then
            current.diagnostics.claimKeyConsumed = true
            return ""
          end
          current.diagnostics.claimKeyConsumed = not supports_key_consumption
            and insert_claim_key_unmapped and claim_mode:sub(1, 1) == "i"
          return
        end

        local command_line = options.command_line_state()
        if command_line.generated_keys and (typed == nil or typed == "") then
          current.motion = nil
          return
        end
        if command_line.active and (command_line.type == "/" or command_line.type == "?")
          and (translated == "<C-G>" or translated == "<C-T>") then
          native_operations.search_preview_key(command_line.type, command_line.text)
        end
        local raw_mode = vim.api.nvim_get_mode().mode
        local operator_context = raw_mode:sub(1, 1) == "n" and not command_line.active
        local visual_context = not command_line.active
          and (raw_mode == "v" or raw_mode == "V" or raw_mode == "\22")
        local prefix = current.prefix

        if operator_context and prefix.register then
          prefix.register = false
          if #translated == 1 then
            emit("registerSelected", "registerCommand", {
              registerName = translated,
              registerType = vim.fn.getregtype(translated),
              registerText = text.bounded(vim.fn.getreg(translated), 2048),
            })
          end
          return
        elseif operator_context and translated == '"' then
          prefix.register = true
          return
        end
        if operator_context and prefix.macro then
          prefix.macro = false
          if #translated == 1 or translated == "@" then
            local name = translated == "@" and vim.fn.reg_executing() or translated
            vim.defer_fn(function()
              emit("macroPlayed", "macroCommand", { registerName = name ~= "" and name or "last" })
            end, 20)
          end
          return
        elseif operator_context and translated == "@" then
          prefix.macro = true
          return
        end
        if (operator_context or visual_context) and prefix.z then
          local action = fold_actions[translated]
          local before = prefix.z.before
          prefix.z = nil
          if translated == "=" then
            local snapshot_ok, snapshot = pcall(state_snapshot.snapshot, "spellSuggestions")
            options.set_spell_candidate({
              timestamp = vim.uv.hrtime(),
              bufferId = snapshot_ok and snapshot.bufferId or nil,
              windowId = snapshot_ok and snapshot.windowId or nil,
              tabpageId = snapshot_ok and snapshot.tabpageId or nil,
              changedtick = snapshot_ok and snapshot.changedtick or nil,
              snapshot = snapshot_ok and snapshot or nil,
            })
          end
          if action == "next" or action == "previous" then
            current.motion = "foldMoved"
            current.motion_details = { foldAction = action }
          elseif action then
            vim.defer_fn(function()
              local details = fold_at_cursor()
              details.foldAction = action
              if not details.closed and before and before.closed then
                details.startLine, details.endLine = before.startLine, before.endLine
              end
              emit("foldChanged", "foldCommand", details)
            end, 20)
          end
          return
        elseif (operator_context or visual_context) and translated == "z" then
          prefix.z = { before = fold_at_cursor() }
          return
        end
        if operator_context and prefix.mark then
          local mark_prefix = prefix.mark
          prefix.mark = nil
          if #translated == 1 then
            if mark_prefix == "m" then
              vim.defer_fn(function()
                local position = vim.fn.getpos("'" .. translated)
                emit("markSet", "markCommand", {
                  markName = translated,
                  markLine = position[2],
                  markByteColumn = math.max(0, position[3] - 1),
                })
              end, 20)
            else
              current.motion = "suppress"
              vim.defer_fn(function()
                emit("markMoved", "markCommand", {
                  markName = translated, markExact = mark_prefix == "`",
                })
              end, 20)
            end
          end
          return
        elseif operator_context
          and (translated == "m" or translated == "'" or translated == "`") then
          prefix.mark = translated
          return
        end

        if operator_context and translated == "d" then
          if current.edit and current.edit.operator == "d" then
            current.edit.linewise = true
          else
            current.edit = {
              operator = "d", kind = "textDeleted", beforeText = vim.api.nvim_get_current_line(),
            }
          end
        elseif operator_context and translated == "c" then
          if current.edit and current.edit.operator == "c" then
            current.edit.linewise = true
          else
            current.edit = {
              operator = "c", kind = "textReplaced", beforeText = vim.api.nvim_get_current_line(),
            }
          end
        elseif operator_context and translated == "C" then
          current.edit = {
            operator = "c", kind = "textReplaced", beforeText = vim.api.nvim_get_current_line(),
          }
        elseif translated == "<Esc>" then
          if current.edit and vim.api.nvim_get_current_line() ~= current.edit.beforeText then
            emit(current.edit.kind, "operatorEscape", {
              beforeText = current.edit.beforeText,
              linewise = current.edit.linewise or false,
            })
            current.suppress_next_text_change = true
          end
          current.edit = nil
        end
        if translated == "g" then
          if prefix.g then
            current.motion = "fileStart"
            prefix.g = false
          else
            prefix.g = true
          end
          return
        end
        if operator_context and (translated == "[" or translated == "]") then
          prefix.bracket = translated
          return
        elseif operator_context and prefix.bracket then
          if translated == "d" or translated == "D" then
            current.motion = "diagnosticMoved"
          elseif translated == "s" then
            current.motion = "wordMoved"
          end
          prefix.bracket = nil
          return
        end

        if raw_mode:sub(1, 1) == "i" then
          local physical_key = typed_translated ~= "" and typed_translated or translated
          local completion_active = completion_adapters.is_active() or vim.fn.pumvisible() == 1
          if completion_active and completion_adapters.is_selection_key(physical_key) then
            current.motion = "suppress"
            completion_adapters.expect_selection_edit()
          else
            current.motion = insert_motion_events[translated]
          end
        elseif current.edit and operator_context then
          current.motion = "suppress"
        elseif operator_context or visual_context then
          current.motion = motion_events[translated]
        else
          current.motion = nil
        end
        if operator_context and translated == "n" then current.search_direction = "next" end
        if operator_context and translated == "N" then current.search_direction = "previous" end
        if operator_context and translated == "%" then
          local attempt = {}
          current.matching = attempt
          vim.defer_fn(function()
            if current.matching == attempt then
              current.matching = nil
              emit("matchingPairNotFound", "percentMotion")
            end
          end, 30)
        end
        if raw_mode:sub(1, 1) == "i" and is_word_terminator(key) then
          local before = state_snapshot.snapshot("beforeSpellingTerminator")
          vim.defer_fn(function() emit_typed_spelling_error(before) end, 50)
        end
        if raw_mode:sub(1, 1) == "i" then signature_help.note_insert_key(key, typed) end
        prefix.g = false
      end)
      if not observer_ok then
        current.diagnostics.observerErrorCount = current.diagnostics.observerErrorCount + 1
        current.diagnostics.observerErrorKind = options.classify_error(observer_result)
        return
      end
      return observer_result
    end, key_namespace)

    vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
      group = group,
      callback = function(event)
        if native_operations.consume_intermediate_update("cursor") then
          if native_operations.is_substitute_active() then
            local snapshot_ok, snapshot = pcall(state_snapshot.snapshot, "substitutePromptContext")
            if snapshot_ok then native_operations.capture_substitute_prompt_snapshot(snapshot) end
          end
          native_operations.note_intermediate_update()
          clear_motion()
          return
        end
        local diagnostic_navigation = diagnostics.consume_navigation()
        if diagnostic_navigation then
          current.motion = "diagnosticMoved"
          if type(diagnostic_navigation) == "table" then
            current.motion_details = diagnostic_navigation
          end
        end
        schedule_navigation(event.event)
      end,
    })

    vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI", "TextChangedP" }, {
      group = group,
      callback = function(event)
        if options.emit_oil_confirmation() then return end
        if current.suppress_next_text_change then
          current.suppress_next_text_change = false
          return
        end
        if native_operations.consume_text_change() then
          if native_operations.is_substitute_active() then
            local snapshot_ok, snapshot = pcall(state_snapshot.snapshot, "substitutePromptContext")
            if snapshot_ok then native_operations.capture_substitute_prompt_snapshot(snapshot) end
          end
          native_operations.note_intermediate_update()
          return
        end
        if event.event == "TextChangedP" and vim.fn.pumvisible() == 1 then
          completion_adapters.consume_selection_edit()
          return
        end
        if event.event ~= "TextChanged" and completion_adapters.consume_selection_edit() then
          return
        end
        if current.edit then
          emit(current.edit.kind, event.event, {
            beforeText = current.edit.beforeText,
            linewise = current.edit.linewise or false,
          })
          current.edit = nil
        else
          emit("textChanged", event.event)
        end
      end,
    })
  end

  return instance
end

return M
