local M = {}

local registry_file
local socket_path
local owns_socket = false
local registry_value
local is_windows

local function random_nonce()
  local bytes = vim.uv.random(16)
  assert(type(bytes) == "string" and #bytes == 16, "secure registry nonce unavailable")
  return (bytes:gsub(".", function(byte)
    return string.format("%02x", string.byte(byte))
  end))
end

local function linux_process_start_ticks()
  if is_windows() then return nil end
  local file = io.open("/proc/self/stat", "r")
  if not file then return nil end
  local value = file:read("*a")
  file:close()
  local fields = value:match("^%d+ %b() (.+)$")
  if not fields then return nil end
  local index = 0
  for field in fields:gmatch("%S+") do
    index = index + 1
    if index == 20 then return tonumber(field) end -- Linux /proc field 22.
  end
  return nil
end

is_windows = function()
  return vim.fn.has("win32") == 1
    or vim.g.nvim_nvda_test_windows == true
    or vim.g.nvim_nvda_test_windows == 1
    or vim.env.NVIM_NVDA_TEST_WINDOWS == "1"
end

local function normalize_name(value)
  if type(value) ~= "string" then
    return ""
  end
  value = value:gsub("[%z\1-\31\127]", " "):gsub("^%s+", ""):gsub("%s+$", "")
  if #value > 120 then
    local offset = 1
    local last_complete = 0
    while offset <= #value and offset <= 120 do
      local byte = value:byte(offset)
      local width = byte < 0x80 and 1 or byte < 0xE0 and 2 or byte < 0xF0 and 3 or 4
      if offset + width - 1 > 120 then break end
      last_complete = offset + width - 1
      offset = offset + width
    end
    value = value:sub(1, last_complete)
  end
  return value
end

local function runtime_root()
  if is_windows() then
    local root = vim.env.LOCALAPPDATA
    if not root or root == "" then
      root = vim.fn.stdpath("data")
    end
    return root .. "/nvim-nvda"
  end
  local root = vim.env.XDG_RUNTIME_DIR
  if not root or root == "" then
    root = "/tmp/nvim-nvda-" .. tostring(vim.fn.getuid())
  end
  return root .. "/nvim-nvda"
end

local function write_registry(path, value)
  local temporary = path .. ".new"
  local file = assert(io.open(temporary, "w"))
  file:write(vim.json.encode(value))
  file:write("\n")
  file:close()
  if not is_windows() then
    assert(vim.uv.fs_chmod(temporary, 384)) -- 0600
  end
  assert(vim.uv.fs_rename(temporary, path))
end

function M.start()
  if registry_file then
    return socket_path
  end
  local root = runtime_root()
  local sessions = root .. "/sessions"
  vim.fn.mkdir(sessions, "p", 448) -- 0700
  if not is_windows() then
    vim.uv.fs_chmod(root, 448)
    vim.uv.fs_chmod(sessions, 448)
  end
  local pid = vim.fn.getpid()
  local session_nonce = random_nonce()
  local transport_kind = "remoteSsh"
  local host
  local port
  if is_windows() then
    socket_path = vim.fn.serverstart("127.0.0.1:0")
    host, port = socket_path:match("^(127%.0%.0%.1):(%d+)$")
    port = tonumber(port)
    assert(host == "127.0.0.1" and port and port >= 1 and port <= 65535,
      "Neovim did not create a local IPv4 loopback RPC endpoint")
    transport_kind = "localWindowsTcp"
    owns_socket = true
  else
    socket_path = vim.v.servername
    -- A user may already have a TCP --listen address. The SSH stdio bridge uses
    -- an AF_UNIX connection, so register an additional private Unix server
    -- instead of publishing the incompatible TCP address.
    local is_unix_socket = socket_path and socket_path ~= "" and socket_path:find("/", 1, true) ~= nil
    if not is_unix_socket then
      socket_path = root .. "/nvim-" .. tostring(pid) .. "-" .. session_nonce .. ".sock"
      vim.fn.serverstart(socket_path)
      owns_socket = true
    end
  end
  -- A nonce-qualified filename prevents a stale lister from unlinking a new
  -- process's record after PID reuse.
  registry_file = sessions .. "/" .. tostring(pid) .. "-" .. session_nonce .. ".json"
  local configured_name = vim.g.nvim_nvda_session_name
  if type(configured_name) ~= "string" or configured_name == "" then
    configured_name = vim.env.NVIM_NVDA_SESSION_NAME
  end
  registry_value = {
    version = 3,
    pid = pid,
    socket = socket_path,
    transportKind = transport_kind,
    host = host,
    port = port,
    cwd = vim.fn.getcwd(),
    name = normalize_name(configured_name),
    startedMonotonic = vim.uv.hrtime(),
    startedUnix = os.time(),
    processStartTicks = linux_process_start_ticks(),
    sessionNonce = session_nonce,
    ownsSocket = owns_socket,
    claimedMonotonic = 0,
    claimSequence = 0,
  }
  write_registry(registry_file, registry_value)
  local group = vim.api.nvim_create_augroup("NvimNvdaSession", { clear = true })
  vim.api.nvim_create_autocmd("VimLeavePre", {
    group = group,
    callback = M.stop,
  })
  return socket_path
end

function M.identity()
  return registry_value and registry_value.sessionNonce or ""
end

function M.claim()
  if not registry_file or not registry_value then
    M.start()
  end
  registry_value.claimedMonotonic = vim.uv.hrtime()
  registry_value.claimSequence = registry_value.claimSequence + 1
  registry_value.cwd = vim.fn.getcwd()
  write_registry(registry_file, registry_value)
  return registry_value.claimSequence
end

function M.set_name(name)
  if not registry_file or not registry_value then
    M.start()
  end
  registry_value.name = normalize_name(name)
  vim.g.nvim_nvda_session_name = registry_value.name
  write_registry(registry_file, registry_value)
  return registry_value.name
end

function M.stop()
  if registry_file then
    os.remove(registry_file)
    registry_file = nil
    registry_value = nil
  end
  if owns_socket and socket_path then
    pcall(vim.fn.serverstop, socket_path)
    if not is_windows() then
      os.remove(socket_path)
    end
  end
  socket_path = nil
  owns_socket = false
end

return M
