-- Pure readiness checks for the guided human-test linter profiles.

local M = {}

local function text(value)
  return tostring(value or "")
end

function M.evaluate(profile, diagnostics, severity)
  assert(type(diagnostics) == "table", "diagnostics must be a table")
  assert(type(severity) == "table", "severity must be a table")

  if profile == "diagnostics" then
    local warning_count = 0
    local first_line_warnings = 0
    local error_found = false
    local count = 0
    for _, diagnostic in ipairs(diagnostics) do
      if text(diagnostic.source):lower():find("ruff", 1, true) then
        count = count + 1
        if text(diagnostic.code) == "F401" and diagnostic.severity == severity.WARN then
          warning_count = warning_count + 1
          if diagnostic.lnum == 0 then
            first_line_warnings = first_line_warnings + 1
          end
        elseif text(diagnostic.code) == "F821" and diagnostic.severity == severity.ERROR then
          error_found = true
        end
      end
    end
    return warning_count >= 2 and error_found and first_line_warnings >= 2,
      count, first_line_warnings
  end

  if profile == "c-diagnostics" then
    local count = 0
    local at_test_position = 0
    for _, diagnostic in ipairs(diagnostics) do
      if diagnostic.source == "clang-tidy"
          and text(diagnostic.code) == "clang-diagnostic-error"
          and diagnostic.severity == severity.ERROR then
        count = count + 1
        if diagnostic.lnum == 1 then at_test_position = at_test_position + 1 end
      end
    end
    return count >= 1 and at_test_position >= 1, count, at_test_position
  end

  if profile == "markdown-diagnostics" then
    local count = 0
    local at_test_position = 0
    for _, diagnostic in ipairs(diagnostics) do
      if diagnostic.source == "markdownlint"
          and diagnostic.severity == severity.WARN
          and text(diagnostic.message):find("MD025", 1, true) then
        count = count + 1
        if diagnostic.lnum == 2 then at_test_position = at_test_position + 1 end
      end
    end
    return count >= 1 and at_test_position >= 1, count, at_test_position
  end

  error("unsupported linter profile: " .. text(profile))
end

return M
