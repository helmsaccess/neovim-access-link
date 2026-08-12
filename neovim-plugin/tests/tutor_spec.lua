local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local tutor = require("nvim_nvda.tutor")
local state = require("nvim_nvda.state")
local assertions = 0
local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local events = {}
local group = vim.api.nvim_create_augroup("NvimNvdaTutorTest", { clear = true })
local function emit(event_type, reason, payload)
  events[#events + 1] = { type = event_type, reason = reason, payload = payload }
end
local enabled = tutor.setup(emit, group)
local initial_autocmds = vim.api.nvim_get_autocmds({ group = group })
local ordinary_snapshot = state.snapshot("ordinaryBuffer")
equal(nil, ordinary_snapshot.tutorExerciseStatus,
  "ordinary buffer has no Tutor protocol state")

vim.cmd("runtime plugin/tutor.vim")
vim.cmd("Tutor")
local buf = vim.api.nvim_get_current_buf()
local version = vim.version()
local supported = version.major > 0 or version.minor >= 12
equal(supported, enabled, "Tutor integration follows the Neovim 0.12 boundary")
if not supported then
  equal(nil, tutor.status(buf, 1), "Neovim before 0.12 has no Tutor status integration")
  equal({}, vim.api.nvim_get_autocmds({ group = group }),
    "Neovim before 0.12 registers no Tutor observers")
  print(string.format("Tutor tests: %d assertions passed", assertions))
  vim.cmd("qa!")
  return
end
equal(1, #initial_autocmds, "supported setup registers only the Tutor FileType gate")

local metadata = vim.b.tutor_metadata
local line, expected, original, prefix
for raw_line, value in pairs(metadata.expect or {}) do
  local candidate = tonumber(raw_line)
  local current = vim.api.nvim_buf_get_lines(buf, candidate - 1, candidate, true)[1]
  if type(value) == "string" and current ~= value then
    local common = 0
    while common < #current and common < #value
      and current:sub(common + 1, common + 1) == value:sub(common + 1, common + 1) do
      common = common + 1
    end
    if common > 0 then
      line, expected, original, prefix = candidate, value, current, common
      break
    end
  end
end
assert(line and expected, "Tutor did not expose an incomplete text exercise")
vim.api.nvim_win_set_cursor(0, { line, 0 })
vim.wait(1000, function() return tutor.status(buf, line) ~= nil end, 10)
equal(1, #vim.api.nvim_get_autocmds({
  group = group, buffer = buf, event = "TextChanged",
}), "active Tutor buffer receives one contextual TextChanged observer")
equal("incorrect", tutor.status(buf, line), "real Tutor incorrect marker")
local initial_snapshot = state.snapshot("tutorInitial")
equal(line, initial_snapshot.cursor.line, "canonical Tutor cursor line")
equal("tutor", initial_snapshot.filetype, "canonical Tutor filetype")
equal("incorrect", initial_snapshot.tutorExerciseStatus,
  "canonical Tutor status")

local suffix = 0
while suffix < (#original - prefix) and suffix < (#expected - prefix)
  and original:sub(#original - suffix, #original - suffix)
    == expected:sub(#expected - suffix, #expected - suffix) do
  suffix = suffix + 1
end
vim.api.nvim_buf_set_text(
  buf,
  line - 1,
  prefix,
  line - 1,
  #original - suffix,
  { expected:sub(prefix + 1, #expected - suffix) }
)
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(1000, function() return #events == 1 end, 10)
equal("correct", tutor.status(buf, line), "real Tutor correct marker")
equal({ "tutorExerciseChanged", "correct" }, {
  events[1] and events[1].type,
  events[1] and events[1].payload.tutorExerciseStatus,
}, "incorrect-to-correct transition")

vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected, { "x" })
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(1000, function() return #events == 2 end, 10)
equal({ "tutorExerciseChanged", "incorrect" }, {
  events[2] and events[2].type,
  events[2] and events[2].payload.tutorExerciseStatus,
}, "correct-to-incorrect transition")

local namespace = vim.api.nvim_get_namespaces()["nvim.tutor.mark"]
local current_marks = vim.api.nvim_buf_get_extmarks(
  buf, namespace, { line - 1, 0 }, { line - 1, -1 }, { details = true }
)
local current_id = current_marks[1] and current_marks[1][1]
assert(current_id, "native Tutor extmark is required for disappearance test")
vim.api.nvim_buf_del_extmark(buf, namespace, current_id)
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(50)
equal(nil, tutor.status(buf, line), "disappeared Tutor marker clears current status")
equal(2, #events, "disappeared Tutor marker emits no assessment")
vim.api.nvim_buf_set_extmark(buf, namespace, line - 1, 0, {
  id = current_id,
  sign_text = "✗ ",
  sign_hl_group = "tutorX",
  invalidate = true,
})
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(50)
equal("incorrect", tutor.status(buf, line), "reappeared Tutor marker restores current status")
equal(2, #events, "reappeared Tutor marker emits no invented transition")

vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(50)
equal(2, #events, "unchanged incorrect exercise remains quiet")

local extra = vim.api.nvim_buf_set_extmark(buf, namespace, line - 1, 0, {
  sign_text = "?", sign_hl_group = "TutorExtra",
})
equal(nil, tutor.status(buf, line), "ambiguous Tutor namespace remains quiet")
vim.api.nvim_buf_del_extmark(buf, namespace, extra)
equal("incorrect", tutor.status(buf, line), "unambiguous native marker is restored")

-- Coalesce multiple changes within one input turn. The line starts and ends
-- incorrect, so no transient intermediate assessment may escape.
vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected + 1, {})
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected, { "x" })
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(50)
equal(2, #events, "same-turn edits emit no intermediate assessment")

-- Losing the Tutor context suppresses the transition announcement but must
-- still refresh the remembered state for the next edit on that line.
vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected + 1, {})
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
local other = vim.api.nvim_create_buf(false, true)
vim.api.nvim_set_current_buf(other)
vim.wait(50)
equal(2, #events, "context loss suppresses the transient assessment")
vim.api.nvim_set_current_buf(buf)
equal("correct", tutor.status(buf, line), "current assessment survives context loss")
vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected, { "x" })
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(1000, function() return #events == 3 end, 10)
equal("incorrect", events[3] and events[3].payload.tutorExerciseStatus,
  "next edit compares with the refreshed hidden state")

-- Switching to another window showing the same buffer and line is still a
-- context change. Keep the new status, but do not announce it in that window.
vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected + 1, {})
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
local edit_window = vim.api.nvim_get_current_win()
vim.cmd("split")
local other_window = vim.api.nvim_get_current_win()
assert(other_window ~= edit_window, "Tutor window-switch test requires two windows")
vim.wait(50)
equal(3, #events, "window change suppresses the transient assessment")
equal("correct", tutor.status(buf, line), "window change preserves current assessment")
vim.api.nvim_win_close(other_window, true)
vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected, { "x" })
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(1000, function() return #events == 4 end, 10)
equal("incorrect", events[4] and events[4].payload.tutorExerciseStatus,
  "next edit compares with the state refreshed across windows")

local native_marks = vim.api.nvim_buf_get_extmarks(
  buf, namespace, { line - 1, 0 }, { line - 1, -1 }, { details = true }
)
local native_id = native_marks[1] and native_marks[1][1]
assert(native_id, "native Tutor extmark is required for invalidation test")
vim.api.nvim_buf_set_lines(buf, line - 1, line, true, {})
local invalid
for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(
  buf, namespace, { 0, 0 }, { -1, -1 }, { details = true }
)) do
  if mark[1] == native_id then invalid = mark break end
end
equal(true, invalid and invalid[4].invalid, "native deleted Tutor mark becomes invalid")
local invalid_line = invalid[2] + 1
for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(
  buf, namespace, { invalid[2], 0 }, { invalid[2], -1 }, { details = true }
)) do
  if mark[1] ~= native_id then vim.api.nvim_buf_del_extmark(buf, namespace, mark[1]) end
end
equal(nil, tutor.status(buf, invalid_line),
  "invalid native Tutor mark is never exposed")

vim.bo[buf].filetype = "text"
equal(nil, tutor.status(buf, line), "non-Tutor filetype is never interpreted")

print(string.format("Tutor tests: %d assertions passed", assertions))
vim.cmd("qa!")
