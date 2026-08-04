local root = vim.fn.getcwd()
local readiness = dofile(root .. "/tests/human/framework/linter_readiness.lua")
local severity = vim.diagnostic.severity

local assertions = 0
local function equal(actual, expected, label)
  assertions = assertions + 1
  assert(actual == expected,
    string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)))
end

local function evaluate(profile, diagnostics)
  return readiness.evaluate(profile, diagnostics, severity)
end

local parser_spec
local parser = readiness.clang_tidy_parser({
  from_pattern = function(pattern, groups, severity_map, defaults)
    parser_spec = {
      pattern = pattern,
      groups = groups,
      severity_map = severity_map,
      defaults = defaults,
    }
    return parser_spec
  end,
}, severity)
equal(parser, parser_spec, "Clang-Tidy parser is built through nvim-lint")
equal(parser.defaults.source, "clang-tidy", "Clang-Tidy parser preserves its source")
equal(parser.severity_map.error, severity.ERROR, "Clang-Tidy error severity is mapped")
equal(parser.groups[1], "_file",
  "Clang-Tidy parser avoids nvim-lint's UNC path comparison")

local function parse_clang_tidy(line)
  return { line:match(parser.pattern) }
end

local drive_diagnostic = parse_clang_tidy(
  [[X:\worktrees\feature-lsp\tests\human\fixtures\diagnostics.c:2:10: error: ]] ..
  "use of undeclared identifier 'missing' [clang-diagnostic-error]"
)
equal(#drive_diagnostic, 6, "Windows drive-path diagnostic is parsed")
equal(drive_diagnostic[1],
  [[X:\worktrees\feature-lsp\tests\human\fixtures\diagnostics.c]],
  "Windows drive path remains intact")
equal(drive_diagnostic[2], "2", "Windows diagnostic line is parsed")
equal(drive_diagnostic[6], "clang-diagnostic-error", "Windows diagnostic code is parsed")

local unc_diagnostic = parse_clang_tidy(
  [[\\space.example\share\diagnostics.c:2:10: error: ]] ..
  "use of undeclared identifier 'missing' [clang-diagnostic-error]"
)
equal(#unc_diagnostic, 6, "UNC-path diagnostic is parsed")
equal(unc_diagnostic[1], [[\\space.example\share\diagnostics.c]],
  "UNC path remains intact")

local ready, count, position_count = evaluate("diagnostics", {
  { source = "Ruff", code = "F401", severity = severity.WARN, lnum = 0 },
  { source = "ruff", code = "F401", severity = severity.WARN, lnum = 0 },
  { source = "ruff", code = "F821", severity = severity.ERROR, lnum = 5 },
  { source = "pyright", code = "reportUndefinedVariable", severity = severity.ERROR, lnum = 5 },
})
equal(ready, true, "complete Ruff fixture is ready")
equal(count, 3, "only Ruff diagnostics are counted")
equal(position_count, 2, "both warnings at the test position are counted")
local primary = readiness.primary("diagnostics", {
  {
    source = "ruff", code = "F401", severity = severity.WARN,
    lnum = 0, col = 21, message = "sep",
  },
  {
    source = "ruff", code = "F821", severity = severity.ERROR,
    lnum = 4, col = 6, message = "missing_name",
  },
  {
    source = "Ruff", code = "F401", severity = severity.WARN,
    lnum = 0, col = 15, message = "path",
  },
}, severity)
equal(primary.message, "path", "F6 targets the first Ruff import warning")
equal(primary.col, 15, "F6 uses the real Ruff diagnostic column")

ready = evaluate("diagnostics", {
  { source = "ruff", code = "F401", severity = severity.WARN, lnum = 0 },
  { source = "ruff", code = "F821", severity = severity.ERROR, lnum = 5 },
})
equal(ready, false, "one Ruff import warning is insufficient")
ready = evaluate("diagnostics", {
  { source = "ruff", code = "F401", severity = severity.WARN, lnum = 0 },
  { source = "ruff", code = "F401", severity = severity.WARN, lnum = 0 },
  { source = "ruff", code = "F821", severity = severity.WARN, lnum = 5 },
})
equal(ready, false, "Ruff F821 must have error severity")

ready, count, position_count = evaluate("c-diagnostics", {
  {
    source = "clang-tidy",
    code = "clang-diagnostic-error",
    severity = severity.ERROR,
    lnum = 1,
  },
  { source = "clangd", code = "clang-diagnostic-error", severity = severity.ERROR, lnum = 1 },
})
equal(ready, true, "Clang-Tidy fixture diagnostic is ready")
equal(count, 1, "only the expected Clang-Tidy diagnostic is counted")
equal(position_count, 1, "Clang-Tidy diagnostic is at the test position")
primary = readiness.primary("c-diagnostics", {
  {
    source = "clang-tidy", code = "clang-diagnostic-error",
    severity = severity.ERROR, lnum = 1, col = 9,
  },
}, severity)
equal(primary.col, 9, "F6 uses the real Clang-Tidy diagnostic column")
ready, count, position_count = evaluate("c-diagnostics", {
  {
    source = "clang-tidy",
    code = "clang-diagnostic-error",
    severity = severity.ERROR,
    lnum = 0,
  },
})
equal(ready, false, "Clang-Tidy diagnostic on another line is not ready")
equal(count, 1, "matching Clang-Tidy diagnostic remains observable")
equal(position_count, 0, "wrong Clang-Tidy position is not counted")

ready, count, position_count = evaluate("markdown-diagnostics", {
  {
    source = "markdownlint",
    message = "MD025/single-title Multiple top-level headings",
    severity = severity.WARN,
    lnum = 2,
  },
  { source = "markdownlint", message = nil, severity = severity.WARN, lnum = 2 },
})
equal(ready, true, "markdownlint MD025 fixture diagnostic is ready")
equal(count, 1, "only markdownlint MD025 is counted")
equal(position_count, 1, "markdownlint diagnostic is at the test position")
primary = readiness.primary("markdown-diagnostics", {
  {
    source = "markdownlint", message = "MD025/single-title Multiple headings",
    severity = severity.WARN, lnum = 2, col = 0,
  },
}, severity)
equal(primary.lnum, 2, "F6 uses the real markdownlint diagnostic line")
ready = evaluate("markdown-diagnostics", {
  {
    source = "markdownlint",
    message = "MD025/single-title Multiple top-level headings",
    severity = severity.ERROR,
    lnum = 2,
  },
})
equal(ready, false, "markdownlint MD025 must have warning severity")
ready = evaluate("markdown-diagnostics", {
  {
    source = "markdownlint",
    message = "MD025/single-title Multiple top-level headings",
    severity = severity.WARN,
    lnum = 1,
  },
})
equal(ready, false, "markdownlint diagnostic on another line is not ready")

local supported, message = pcall(evaluate, "unknown-profile", {})
equal(supported, false, "unknown linter profiles are rejected")
assert(tostring(message):find("unsupported linter profile", 1, true),
  "unknown profile error is actionable")
assertions = assertions + 1
supported, message = pcall(readiness.primary, "unknown-profile", {}, severity)
equal(supported, false, "primary selection rejects unknown linter profiles")
assert(tostring(message):find("unsupported linter profile", 1, true),
  "unknown primary profile error is actionable")
assertions = assertions + 1

print(string.format("human-test linter readiness specs passed: %d assertions", assertions))
vim.cmd("qa!")
