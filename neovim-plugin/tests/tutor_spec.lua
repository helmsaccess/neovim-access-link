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
tutor.setup(group)

vim.cmd("runtime plugin/tutor.vim")
vim.cmd("Tutor")
local buf = vim.api.nvim_get_current_buf()
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
local event = { buf = buf, event = "TextChanged" }
tutor.text_changed(event, emit)
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(1000, function() return #events == 1 end, 10)
equal("correct", tutor.status(buf, line), "real Tutor correct marker")
equal({ "tutorExerciseChanged", "correct" }, {
  events[1] and events[1].type,
  events[1] and events[1].payload.tutorExerciseStatus,
}, "incorrect-to-correct transition")

vim.api.nvim_buf_set_text(buf, line - 1, #expected, line - 1, #expected, { "x" })
tutor.text_changed(event, emit)
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(1000, function() return #events == 2 end, 10)
equal({ "tutorExerciseChanged", "incorrect" }, {
  events[2] and events[2].type,
  events[2] and events[2].payload.tutorExerciseStatus,
}, "correct-to-incorrect transition")

tutor.text_changed(event, emit)
vim.api.nvim_exec_autocmds("TextChanged", { buffer = buf, modeline = false })
vim.wait(50)
equal(2, #events, "unchanged incorrect exercise remains quiet")

vim.bo[buf].filetype = "text"
equal(nil, tutor.status(buf, line), "non-Tutor filetype is never interpreted")

print(string.format("Tutor tests: %d assertions passed", assertions))
vim.cmd("qa!")
