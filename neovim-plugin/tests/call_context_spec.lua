local root = vim.fn.getcwd()
package.path = root .. "/neovim-plugin/lua/?.lua;" .. root
  .. "/neovim-plugin/lua/?/init.lua;" .. package.path

local call_context = require("nvim_nvda.call_context")
local assertions = 0

local function equal(expected, actual, label)
  assertions = assertions + 1
  assert(vim.deep_equal(expected, actual), string.format(
    "%s: expected %s, got %s", label, vim.inspect(expected), vim.inspect(actual)
  ))
end

local function set_lines(lines, filetype)
  vim.api.nvim_buf_set_lines(0, 0, -1, true, lines)
  vim.bo.filetype = filetype or "python"
end

local function column(line, needle, occurrence)
  local start = 1
  local found
  for _ = 1, occurrence or 1 do
    found = assert(line:find(needle, start, true), "test needle not found: " .. needle)
    start = found + 1
  end
  return found - 1
end

local function manual(line_number, byte_column, mode)
  return call_context.resolve_manual(0, line_number, byte_column, mode or "n")
end

local function automatic(line_number, byte_column)
  return call_context.resolve_automatic(0, line_number, byte_column, "i")
end

local line = "calculate_total(price, quantity)"
set_lines({ line })
local open = column(line, "(")
local close = column(line, ")")
for byte_column = 0, #"calculate_total" - 1 do
  local resolved = manual(1, byte_column, "n")
  equal("calculate_total", resolved and resolved.name, "every callable name byte resolves")
  equal(open + 1, resolved and resolved.queryByteColumn, "name queries inside call")
end
equal("open", manual(1, open, "n").source, "normal opening parenthesis resolves")
equal("close", manual(1, close, "n").source, "normal closing parenthesis resolves")
equal(nil, manual(1, open + 1, "n"), "normal argument interior is rejected")
equal(nil, manual(1, column(line, "quantity"), "n"), "normal second argument is rejected")
equal("calculate_total", manual(1, 0, "i").name, "insert callable name resolves")
equal(nil, manual(1, open, "i"), "insert nonempty opening parenthesis is rejected")
equal(nil, manual(1, close, "i"), "insert nonempty closing parenthesis is rejected")

line = "empty_call()"
set_lines({ line })
open = column(line, "(")
close = column(line, ")")
equal(true, manual(1, open, "n").empty, "normal empty call is identified")
equal(true, manual(1, open, "i").empty, "insert empty opening parenthesis resolves")
equal(true, manual(1, close, "i").empty, "insert empty closing parenthesis resolves")

line = "documented(/* no argument */)"
set_lines({ line }, "c")
open = column(line, "(")
close = column(line, ")")
equal(true, manual(1, open, "i").empty, "comment-only call is empty")
equal(true, manual(1, close, "i").empty, "comment-only closing parenthesis resolves")

line = "outer(first, inner(alpha, beta), final)"
set_lines({ line })
local outer_open = column(line, "(", 1)
local inner_open = column(line, "(", 2)
local inner_close = column(line, ")", 1)
local outer_close = column(line, ")", 2)
equal("outer", manual(1, 0, "n").name, "outer name resolves")
equal("outer", manual(1, outer_open, "n").name, "outer opening resolves")
equal("outer", manual(1, outer_close, "n").name, "outer closing resolves")
equal("inner", manual(1, column(line, "inner"), "n").name, "inner name resolves")
equal("inner", manual(1, inner_open, "n").name, "inner opening resolves")
equal("inner", manual(1, inner_close, "n").name, "inner closing resolves")
equal("outer", automatic(1, column(line, "first") + 3).name, "first outer argument resolves")
equal("inner", automatic(1, column(line, "alpha") + 3).name, "inner first argument resolves")
equal("inner", automatic(1, column(line, "beta") + 2).name, "inner second argument resolves")
equal("outer", automatic(1, inner_close + 2).name, "position after nested call returns to outer")
equal("outer", automatic(1, column(line, "final") + 2).name, "last outer argument resolves")
equal(nil, automatic(1, outer_close + 1), "position after outer call is outside")

line = "outer(inner(deep(one, two), three), four)"
set_lines({ line })
equal("deep", automatic(1, column(line, "two") + 2).name, "third nesting level resolves")
local deep_close = column(line, ")", 1)
equal("inner", automatic(1, deep_close + 2).name, "leaving deepest call restores parent")
local inner_close_second = column(line, ")", 2)
equal("outer", automatic(1, inner_close_second + 2).name, "leaving middle call restores outer")

line = 'outer("ignored(fake, close)", second)'
set_lines({ line }, "python")
equal("outer", automatic(1, column(line, "fake") + 2).name, "parentheses in strings are ignored")
equal("outer", automatic(1, column(line, "second") + 2).name, "argument after string resolves")
equal(nil, manual(1, column(line, "fake"), "n"), "call-like string content is rejected")

set_lines({
  "outer(",
  "  first, # ignored(fake)",
  "  inner(",
  "    second,",
  "    third",
  "  ),",
  "  final",
  ")",
}, "python")
equal("outer", automatic(2, 4).name, "multiline outer argument resolves")
equal("inner", automatic(4, 7).name, "multiline inner argument resolves")
equal("outer", automatic(7, 5).name, "multiline parent resumes after nested close")
equal("outer", manual(8, 0, "n").name, "multiline outer closing resolves")
equal(nil, manual(2, 19, "n"), "call-like comment content is rejected")

line = "füße(größe, anzahl)"
set_lines({ line }, "python")
open = column(line, "(")
equal("füße", manual(1, 0, "n").name, "Unicode callable name resolves")
equal(open + 1, manual(1, 0, "n").queryByteColumn, "Unicode query uses byte columns")
equal("füße", automatic(1, column(line, "anzahl") + 2).name, "Unicode argument call resolves")

for _, keyword_line in ipairs({
  "if (condition)", "while (condition)", "for (item)", "return (value)",
}) do
  set_lines({ keyword_line }, "c")
  equal(nil, manual(1, 0, "n"), "control keyword is not a callable: " .. keyword_line)
  equal(nil, automatic(1, column(keyword_line, "(") + 2),
    "control expression does not trigger automatic help")
end

line = "unfinished(value"
set_lines({ line })
open = column(line, "(")
equal("unfinished", manual(1, open, "n").name, "normal unfinished call can be queried")
equal(nil, manual(1, open, "i"), "insert unmatched parenthesis is not an empty pair")
equal("unfinished", automatic(1, #line).name, "automatic unfinished call remains available")

set_lines({ string.rep("x", 128 * 1024 + 1) .. "()" })
equal(nil, manual(1, 0, "n"), "oversized scan is rejected without unbounded work")

print(string.format("call context tests: %d assertions passed", assertions))
vim.cmd("qa!")
