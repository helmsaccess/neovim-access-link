local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local operations = require("nvim_nvda.native_operations")
local assertions = 0

local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

equal(
  { kind = "substitute", scope = "buffer", command = "substitute" },
  operations.classify("1,1s/old/new/g"),
  "Neovim parser canonicalizes ranged substitute"
)
equal(
  {
    kind = "substitute", scope = "quickfixFiles", command = "cfdo",
    nestedCommand = "substitute",
  },
  operations.classify("cfdo %s/old/new/g"),
  "Neovim parser identifies nested quickfix-file replacement"
)
equal(
  {
    kind = "substitute", scope = "buffers", command = "bufdo",
    nestedCommand = "substitute",
  },
  operations.classify("bufdo %s/old/new/ge"),
  "Neovim parser identifies nested buffer-list replacement"
)
equal(
  {
    kind = "substitute", scope = "arguments", command = "argdo",
    nestedCommand = "substitute",
  },
  operations.classify("argdo %s/old/new/ge"),
  "Neovim parser identifies nested argument-list replacement"
)
equal(
  { kind = "substitute", scope = "buffer", command = "&" },
  operations.classify("&"),
  "repeat substitution is canonical"
)
equal(
  { kind = "resultList", listKind = "quickfix", command = "vimgrep" },
  operations.classify("vimgrep /old/gj **/*.lua"),
  "native project search owns quickfix result classification"
)
equal(
  { kind = "searchHighlight", command = "nohlsearch" },
  operations.classify("nohlsearch"),
  "native nohlsearch is classified without parsing rendered messages"
)
equal(nil, operations.classify("cdo normal! x"),
  "unrelated do command is not treated as replacement")

local events = {}
local prebuilt_events = {}
local group = vim.api.nvim_create_augroup("NvimNvdaNativeOperationsSpec", { clear = true })
operations.set_prebuilt_emitter(function(event_type, payload, extra)
  local combined = vim.deepcopy(payload)
  for key, value in pairs(extra or {}) do combined[key] = value end
  prebuilt_events[#prebuilt_events + 1] = { type = event_type, payload = combined }
  return true
end)
operations.setup(function(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end, group)

local original_getcmdtype = vim.fn.getcmdtype
local original_getcmdline = vim.fn.getcmdline
local original_searchcount = vim.fn.searchcount
local original_incsearch = vim.o.incsearch
local searchcount_options = {}
vim.o.incsearch = true
vim.fn.getcmdtype = function() return "/" end
vim.fn.getcmdline = function() return "calculate_tip" end
vim.fn.searchcount = function(options)
  searchcount_options[#searchcount_options + 1] = vim.deepcopy(options)
  return { current = 1, total = 2, incomplete = 0 }
end
operations.command_line_enter("/")
operations.command_line_changed("/", "calculate_tip")
equal(true, vim.wait(1000, function() return #events == 1 end, 10),
  "incremental search preview is emitted")
equal(true, vim.iter(searchcount_options):any(function(options)
  return options.pattern == "calculate_tip" and options.recompute == 1
    and options.maxcount == 9999 and options.timeout == 50
end),
  "incremental search count uses the provisional pattern with bounded work")
equal("searchMatchChanged", events[1].type,
  "incremental search emits the semantic search event")
equal(2, events[1].payload.matchCount,
  "incremental search reports the recomputed match count")
operations.command_line_leave("/", "calculate_tip")
vim.fn.getcmdtype = original_getcmdtype
vim.fn.getcmdline = original_getcmdline
vim.fn.searchcount = original_searchcount
vim.o.incsearch = original_incsearch
events = {}

local first = vim.api.nvim_get_current_buf()
local second = vim.api.nvim_create_buf(true, false)
vim.api.nvim_buf_set_lines(first, 0, -1, true, { "old first" })
vim.api.nvim_buf_set_lines(second, 0, -1, true, { "old second" })
vim.bo[first].modified = false
vim.bo[second].modified = false

operations.command_line_enter(":")
operations.command_line_changed(":", "cfdo %s/old/new/g")
equal(true, operations.command_line_leave(":", "cfdo %s/old/new/g"),
  "replacement command is observed before execution")
equal(true, operations.consume_text_change(),
  "native replacement suppresses intermediate generic text events")
equal(true, operations.consume_intermediate_update("context"),
  "bulk replacement suppresses intermediate context and navigation events")
equal(true, operations.is_active(), "bulk replacement remains active before completion")
vim.api.nvim_buf_set_lines(first, 0, 1, true, { "new first" })
vim.api.nvim_buf_set_lines(second, 0, 1, true, { "new second" })
local recognized, emitted = operations.finish_command("2 substitutions on 2 lines")
equal({ true, true }, { recognized, emitted }, "replacement completion is emitted")
local replacement = events[#events]
equal("replacementPerformed", replacement.type, "replacement event type")
equal(2, replacement.payload.changedBufferCount, "two changed buffers")
equal(2, replacement.payload.modifiedBufferCount, "two unsaved changed buffers")
equal("quickfixFiles", replacement.payload.replacementScope, "replacement scope")
equal(false, operations.consume_intermediate_update("context"),
  "bulk context suppression ends with the replacement observation")
equal(false, operations.is_active(), "replacement completion clears active state")

vim.api.nvim_set_current_buf(first)
vim.api.nvim_buf_set_lines(first, 0, -1, true, { "old old old" })
vim.bo[first].modified = false
operations.command_line_enter(":")
operations.command_line_changed(":", "s/old/new/g")
equal(true, operations.command_line_leave(":", "s/old/new/g"),
  "current-line replacement is observed")
vim.cmd("s/old/new/g")
recognized, emitted = operations.finish_command(vim.v.statusmsg)
equal({ true, true }, { recognized, emitted },
  "current-line replacement emits its completion")
equal(1, events[#events].payload.changedLineCount,
  "current-line replacement counts the changed line through buffer updates")
vim.api.nvim_buf_set_lines(first, 0, -1, true, { "new first" })
vim.bo[first].modified = false

operations.command_line_enter(":")
operations.command_line_changed(":", "nohlsearch")
equal(true, operations.command_line_leave(":", "nohlsearch"),
  "native nohlsearch is observed")
vim.cmd("nohlsearch")
recognized, emitted = operations.finish_command("")
equal({ true, true }, { recognized, emitted },
  "native nohlsearch emits its semantic state")
equal("searchHighlightChanged", events[#events].type,
  "native nohlsearch reports the persistent highlight state")

local original_hlsearch = vim.o.hlsearch
vim.cmd("set hlsearch")
local before_option_events = #events
vim.cmd("set nohlsearch")
equal(true, vim.wait(1000, function() return #events > before_option_events end, 10),
  "disabling hlsearch emits its visible state")
equal({ "searchHighlightChanged", "OptionSet", false }, {
  events[#events].type, events[#events].reason,
  events[#events].payload.searchHighlighting,
}, "hlsearch option changes use the semantic highlight event")

operations.command_line_enter(":")
operations.command_line_changed(":", "%s/new/confirmed/gc")
equal(true, operations.command_line_leave(":", "%s/new/confirmed/gc"),
  "confirmed replacement is observed")
operations.command_line_enter("-")
equal("promptOpened", events[#events].type,
  "native confirmation opens before an answer is required")
equal("confirmSub", events[#events].payload.promptKind,
  "native confirmation uses the structured substitute prompt kind")
equal(false, operations.command_line_leave("-", ""),
  "native confirmation leave is not classified as a separate command")
equal("promptClosed", events[#events].type,
  "native confirmation closes after the answer")
equal(true, operations.consume_text_change(),
  "native confirmation command line preserves the replacement observation")
equal(false, operations.consume_intermediate_update("context"),
  "buffer-local confirmation does not suppress unrelated context events")
local original_get_mode = vim.api.nvim_get_mode
vim.api.nvim_get_mode = function() return { mode = "r?", blocking = false } end
recognized, emitted = operations.finish_command("")
equal({ true, true }, { recognized, emitted },
  "raw confirmation mode keeps replacement observation open")
equal(true, operations.consume_text_change(),
  "blocking confirmation keeps generic text changes suppressed")
vim.api.nvim_get_mode = original_get_mode
vim.api.nvim_buf_set_lines(first, 0, 1, true, { "confirmed first" })
recognized, emitted = operations.finish_command("1 substitution on 1 line")
equal({ true, true }, { recognized, emitted },
  "confirmed replacement completes after native prompt closes")
equal(1, events[#events].payload.changedBufferCount,
  "confirmed replacement reports its final changed buffer")

operations.command_line_enter(":")
operations.command_line_changed(":", "%s/confirmed/final/gc")
equal(true, operations.command_line_leave(":", "%s/confirmed/final/gc"),
  "legacy confirmed replacement is observed")
equal(true, operations.capture_substitute_prompt_snapshot({
  lineText = "first target", cursor = { line = 2, byteColumn = 3 },
}), "legacy prompt retains a snapshot captured outside the UI callback")
equal(true, operations.open_legacy_substitute_prompt(),
  "legacy public UI event opens its prompt synchronously")
equal("promptOpened", prebuilt_events[1].type,
  "legacy prompt uses the fast-safe prebuilt emitter")
equal("first target", prebuilt_events[1].payload.lineText,
  "legacy prompt carries the captured target line")
operations.capture_substitute_prompt_snapshot({
  lineText = "second target", cursor = { line = 5, byteColumn = 1 },
})
equal(true, operations.open_legacy_substitute_prompt(),
  "next legacy prompt replaces the preceding prompt")
equal("promptClosed", prebuilt_events[2].type,
  "next legacy prompt closes the preceding prompt")
equal("promptOpened", prebuilt_events[3].type,
  "next legacy prompt opens before its answer")
equal("second target", prebuilt_events[3].payload.lineText,
  "next legacy prompt uses its new target snapshot")
operations.cancel_command()
equal("promptClosed", events[#events].type,
  "canceling a legacy replacement closes its final prompt")

vim.fn.setqflist({
  { bufnr = first, lnum = 1, col = 1, text = "first" },
  { bufnr = second, lnum = 1, col = 1, text = "second" },
}, "r")
operations.command_line_enter(":")
equal(true, operations.command_line_leave(":", "vimgrep /new/gj **/*.lua"),
  "native project search is observed")
recognized, emitted = operations.finish_command("")
equal({ true, true }, { recognized, emitted }, "result-list summary is emitted")
local results = events[#events]
equal("resultListChanged", results.type, "result-list event type")
equal("quickfix", results.payload.listKind, "quickfix list kind")
equal(2, results.payload.itemCount, "quickfix result count")

vim.bo[first].modified = false
vim.bo[second].modified = false
local before_rename_events = #events
operations.lsp_request({
  buf = first,
  data = {
    client_id = 7,
    request_id = 11,
    request = { type = "pending", method = "textDocument/rename", bufnr = first },
  },
})
equal(true, operations.consume_text_change(),
  "active LSP rename suppresses intermediate generic text events")
equal(true, operations.consume_intermediate_update("context"),
  "active LSP rename suppresses intermediate context and navigation events")
vim.api.nvim_buf_set_lines(first, 0, 1, true, { "renamed first" })
vim.api.nvim_buf_set_lines(second, 0, 1, true, { "renamed second" })
operations.lsp_request({
  buf = first,
  data = {
    client_id = 7,
    request_id = 11,
    request = { type = "complete", method = "textDocument/rename", bufnr = first },
  },
})
equal(true, vim.wait(2000, function() return #events > before_rename_events end, 10),
  "rename completion follows a quiet period after the public handler returns")
local rename = events[#events]
equal("lspRenameCompleted", rename.type, "rename result event type")
equal("changesObserved", rename.payload.renameResult, "rename result is evidence-based")
equal(2, rename.payload.changedBufferCount, "rename observes both changed buffers")
equal(true, operations.consume_text_change(),
  "rename completion consumes one delayed generic text event")
equal(false, operations.consume_text_change(),
  "rename completion does not suppress a second generic text event")
equal(true, operations.consume_intermediate_update("cursor"),
  "rename completion consumes one delayed cursor event")
equal(false, operations.consume_intermediate_update("cursor"),
  "rename completion does not suppress a second cursor event")
equal(true, operations.consume_intermediate_update("context"),
  "rename completion consumes one delayed context event")
equal(false, operations.consume_intermediate_update("context"),
  "rename completion does not suppress a second context event")

local before_message = #events
operations.lsp_request({
  buf = first,
  data = {
    client_id = 7,
    request_id = 12,
    request = { type = "pending", method = "textDocument/rename", bufnr = first },
  },
})
operations.note_notification()
operations.lsp_request({
  buf = first,
  data = {
    client_id = 7,
    request_id = 12,
    request = { type = "complete", method = "textDocument/rename", bufnr = first },
  },
})
vim.wait(750, function() return false end, 10)
equal(before_message, #events,
  "native no-change notification remains authoritative without duplicate summary")
operations.clear_post_rename_updates()

local fixture_pattern = root
  .. "/neovim-plugin/tests/fixtures/native_operations_search_*.txt"
operations.command_line_enter(":")
equal(true, operations.command_line_leave(
  ":", "vimgrep /native target/gj " .. fixture_pattern
), "real native project search is observed")
vim.cmd("silent vimgrep /native target/gj " .. fixture_pattern)
recognized, emitted = operations.finish_command(vim.v.statusmsg)
equal({ true, true }, { recognized, emitted },
  "real native project search emits its result list")
equal(2, events[#events].payload.itemCount,
  "real native project search reports both fixture results")

operations.command_line_enter(":")
operations.command_line_changed(":", "cfdo %s/native target/replaced target/g")
equal(true, operations.command_line_leave(
  ":", "cfdo %s/native target/replaced target/g"
), "real native quickfix-file replacement is observed")
vim.cmd("silent cfdo %s/native target/replaced target/g")
recognized, emitted = operations.finish_command(vim.v.statusmsg)
equal({ true, true }, { recognized, emitted },
  "real native quickfix-file replacement emits one summary")
equal(2, events[#events].payload.changedBufferCount,
  "real native quickfix-file replacement reports both changed buffers")
equal(true, events[#events].payload.bulkReplacement,
  "real native quickfix-file replacement is marked as bulk")

local original_hidden = vim.o.hidden
vim.o.hidden = true
local buffer_first = vim.api.nvim_create_buf(true, false)
local buffer_second = vim.api.nvim_create_buf(true, false)
vim.api.nvim_buf_set_lines(buffer_first, 0, -1, true, { "buffer target one" })
vim.api.nvim_buf_set_lines(buffer_second, 0, -1, true, { "buffer target two" })
vim.bo[buffer_first].modified = false
vim.bo[buffer_second].modified = false
vim.api.nvim_set_current_buf(buffer_first)
local bufdo_command = string.format(
  "%d,%dbufdo %%s/buffer target/buffer changed/ge", buffer_first, buffer_second)
operations.command_line_enter(":")
operations.command_line_changed(":", bufdo_command)
equal(true, operations.command_line_leave(":", bufdo_command),
  "real buffer-list replacement is observed")
vim.cmd(bufdo_command)
recognized, emitted = operations.finish_command(vim.v.statusmsg)
equal({ true, true }, { recognized, emitted },
  "real buffer-list replacement emits one summary")
equal({ "buffers", 2, 2 }, {
  events[#events].payload.replacementScope,
  events[#events].payload.changedBufferCount,
  events[#events].payload.modifiedBufferCount,
}, "real buffer-list replacement reports both unsaved buffers")
equal("buffer changed one", vim.api.nvim_buf_get_lines(buffer_first, 0, 1, true)[1],
  "real buffer-list replacement changes the first buffer")
equal("buffer changed two", vim.api.nvim_buf_get_lines(buffer_second, 0, 1, true)[1],
  "real buffer-list replacement changes the second buffer")
vim.api.nvim_set_current_buf(first)
pcall(vim.api.nvim_buf_delete, buffer_first, { force = true })
pcall(vim.api.nvim_buf_delete, buffer_second, { force = true })

for _, item in ipairs(vim.fn.getqflist()) do
  if item.bufnr > 0 and item.bufnr ~= first and item.bufnr ~= second then
    pcall(vim.api.nvim_buf_delete, item.bufnr, { force = true })
  end
end
vim.fn.setqflist({}, "r")

local fixture_a = root .. "/neovim-plugin/tests/fixtures/native_operations_search_a.txt"
local fixture_b = root .. "/neovim-plugin/tests/fixtures/native_operations_search_b.txt"
vim.cmd("args " .. vim.fn.fnameescape(fixture_a) .. " " .. vim.fn.fnameescape(fixture_b))
local argument_buffers = {
  vim.fn.bufnr(fixture_a),
  vim.fn.bufnr(fixture_b),
}
equal(true, vim.api.nvim_buf_is_loaded(argument_buffers[1]),
  "first argument buffer starts loaded")
equal(false, vim.api.nvim_buf_is_loaded(argument_buffers[2]),
  "second argument buffer starts unloaded")
local argdo_command = "argdo %s/native target/argument changed/ge"
operations.command_line_enter(":")
operations.command_line_changed(":", argdo_command)
equal(true, operations.command_line_leave(":", argdo_command),
  "real argument-list replacement is observed")
vim.cmd(argdo_command)
recognized, emitted = operations.finish_command(vim.v.statusmsg)
equal({ true, true }, { recognized, emitted },
  "real argument-list replacement emits one summary")
equal({ "arguments", 2, 2 }, {
  events[#events].payload.replacementScope,
  events[#events].payload.changedBufferCount,
  events[#events].payload.modifiedBufferCount,
}, "real argument-list replacement reports loaded and initially unloaded files")
equal(true, vim.api.nvim_buf_is_loaded(argument_buffers[2]),
  "argument-list replacement lets Neovim load the second file")
vim.api.nvim_set_current_buf(first)
for _, buffer in ipairs(argument_buffers) do
  pcall(vim.api.nvim_buf_delete, buffer, { force = true })
end
vim.o.hidden = original_hidden

operations.reset()
pcall(vim.api.nvim_del_augroup_by_id, group)
vim.o.hlsearch = original_hlsearch
pcall(vim.api.nvim_buf_delete, second, { force = true })

print(string.format("native operation tests: %d assertions passed", assertions))
vim.cmd("qa!")
