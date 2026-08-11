local M = {}

function M.normalize(fixture)
  assert(type(fixture) == "table", "Lazy fixture is invalid")
  if fixture.absent == nil or fixture.absent == vim.NIL then
    fixture.absent = {}
  end
  assert(type(fixture.absent) == "table", "Lazy fixture absent paths must be an array")
  return fixture
end

function M.verify(fixture)
  fixture = M.normalize(fixture)
  local git = vim.fn.exepath("git")
  if git == "" then
    return { "git unavailable" }, {}, {}
  end
  local problems = {}
  local verified_revisions = {}
  local verified_absent = {}
  for _, plugin in ipairs(fixture.plugins) do
    local directory = vim.fs.joinpath(fixture.root, plugin.name)
    if not vim.uv.fs_stat(directory) then
      problems[#problems + 1] = plugin.name .. " missing"
    else
      local result = vim.system({ git, "-C", directory, "rev-parse", "HEAD" },
        { text = true }):wait(3000)
      local revision = type(result.stdout) == "string" and vim.trim(result.stdout) or ""
      if result.code ~= 0 or revision ~= plugin.expectedRevision then
        problems[#problems + 1] = plugin.name .. " revision mismatch"
      else
        verified_revisions[#verified_revisions + 1] = plugin.name
      end
    end
  end
  for _, directory in ipairs(fixture.absent) do
    if vim.uv.fs_stat(directory) then
      problems[#problems + 1] = vim.fs.basename(directory) .. " still present"
    else
      verified_absent[#verified_absent + 1] = vim.fs.basename(directory)
    end
  end
  return problems, verified_revisions, verified_absent
end

return M
