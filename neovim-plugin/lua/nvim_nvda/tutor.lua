local M = {}
local active = {}
local observed = {}
local pending = {}
local emit_event
local tutor_namespace

local function supported()
  local version = vim.version()
  return version.major > 0 or version.minor >= 12
end

local function tutor_buffer(buf)
  return active[buf] == true
    and vim.api.nvim_buf_is_valid(buf)
    and vim.bo[buf].filetype == "tutor"
end

local function status_from_details(details)
  if type(details) ~= "table" or details.invalid then return nil end
  local sign_text = details.sign_text
  if details.sign_hl_group == "tutorOK" and sign_text == "✓ " then
    return "correct"
  end
  if details.sign_hl_group == "tutorX" and sign_text == "✗ " then
    return "incorrect"
  end
  return nil
end

local function read_status(buf, line)
  if type(buf) ~= "number" or type(line) ~= "number" or line < 1 or not tutor_buffer(buf) then
    return nil
  end
  local marks = vim.api.nvim_buf_get_extmarks(
    buf,
    tutor_namespace,
    { line - 1, 0 },
    { line - 1, -1 },
    { details = true }
  )
  local status, count
  count = 0
  for _, mark in ipairs(marks) do
    local details = mark[4]
    if type(details) == "table" and not details.invalid then
      count = count + 1
      status = status_from_details(details)
    end
  end
  return count == 1 and status or nil
end

local function seed_observed(buf)
  if not tutor_buffer(buf) then return end
  local statuses, counts = {}, {}
  local marks = vim.api.nvim_buf_get_extmarks(
    buf, tutor_namespace, { 0, 0 }, { -1, -1 }, { details = true }
  )
  for _, mark in ipairs(marks) do
    local line = mark[2] + 1
    local details = mark[4]
    if type(details) == "table" and not details.invalid then
      counts[line] = (counts[line] or 0) + 1
      statuses[line] = status_from_details(details)
    end
  end
  for line, count in pairs(counts) do
    if count ~= 1 then statuses[line] = nil end
  end
  observed[buf] = statuses
end

local function check_changed(event)
  local buf = event.buf
  if not tutor_buffer(buf) then return end
  local line = vim.api.nvim_win_get_cursor(0)[1]
  local before = observed[buf] and observed[buf][line] or nil
  pending[buf] = pending[buf] or {}
  local generation = (pending[buf][line] or 0) + 1
  pending[buf][line] = generation
  -- Neovim updates Tutor's native extmark during the same event. Coalesce
  -- repeated edits and read the mark after all callbacks for this input turn.
  vim.schedule(function()
    if not pending[buf] or pending[buf][line] ~= generation then return end
    pending[buf][line] = nil
    if not tutor_buffer(buf) then return end
    local after = read_status(buf, line)
    observed[buf] = observed[buf] or {}
    observed[buf][line] = after
    if before and after and after ~= before
      and vim.api.nvim_get_current_buf() == buf
      and vim.api.nvim_win_get_cursor(0)[1] == line then
      emit_event("tutorExerciseChanged", event.event, { tutorExerciseStatus = after })
    end
  end)
end

local function activate(buf, group, retried)
  if active[buf] or not vim.api.nvim_buf_is_valid(buf) or vim.bo[buf].filetype ~= "tutor" then
    return
  end
  tutor_namespace = tutor_namespace or vim.api.nvim_get_namespaces()["nvim.tutor.mark"]
  if not tutor_namespace then
    -- The built-in Tutor runtime creates its namespace while loading the
    -- filetype. Retry once after that FileType turn without polling.
    if not retried then vim.schedule(function() activate(buf, group, true) end) end
    return
  end
  active[buf] = true
  observed[buf] = {}
  pending[buf] = {}
  seed_observed(buf)
  vim.api.nvim_create_autocmd({ "TextChanged", "TextChangedI" }, {
    group = group,
    buffer = buf,
    desc = "Neovim Access Link Tutor exercise changes",
    callback = check_changed,
  })
  vim.api.nvim_create_autocmd("BufWipeout", {
    group = group,
    buffer = buf,
    desc = "Neovim Access Link Tutor cleanup",
    callback = function()
      active[buf] = nil
      observed[buf] = nil
      pending[buf] = nil
    end,
  })
end

function M.status(buf, line)
  return read_status(buf, line)
end

function M.setup(emit, group)
  active, observed, pending = {}, {}, {}
  emit_event = emit
  tutor_namespace = nil
  if not supported() then return false end
  vim.api.nvim_create_autocmd("FileType", {
    group = group,
    pattern = "tutor",
    desc = "Neovim Access Link Tutor activation",
    callback = function(event) activate(event.buf, group) end,
  })
  -- Preserve support when Access Link is reloaded while Tutor buffers exist.
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(buf) and vim.bo[buf].filetype == "tutor" then
      activate(buf, group)
    end
  end
  return true
end

return M
