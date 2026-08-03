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

local ready, count, position_count = evaluate("diagnostics", {
  { source = "Ruff", code = "F401", severity = severity.WARN, lnum = 0 },
  { source = "ruff", code = "F401", severity = severity.WARN, lnum = 0 },
  { source = "ruff", code = "F821", severity = severity.ERROR, lnum = 5 },
  { source = "pyright", code = "reportUndefinedVariable", severity = severity.ERROR, lnum = 5 },
})
equal(ready, true, "complete Ruff fixture is ready")
equal(count, 3, "only Ruff diagnostics are counted")
equal(position_count, 2, "both warnings at the test position are counted")

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

print(string.format("human-test linter readiness specs passed: %d assertions", assertions))
vim.cmd("qa!")
