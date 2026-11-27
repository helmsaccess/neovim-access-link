-- Observe native editor state independently of Access Link and NVDA.
local path = assert(vim.env.NAL_FOCUS_EDITOR_STATE)
local last
local moved = 0
local signature_help, signature_requested
local signature_completed = 0
local rename_completed = 0
local buffer_enters, window_enters = 0, 0
local scenario = vim.env.NAL_FOCUS_GUIDED
vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
  callback = function() moved = moved + 1 end,
})
if scenario == "lsp-l2" or scenario == "lsp-l5" then
  vim.api.nvim_create_autocmd("LspRequest", {
    callback = function(event)
      local request = event.data.request
      if request.type == "complete" then
        if request.method == "textDocument/signatureHelp" then
          signature_completed = signature_completed + 1
        elseif request.method == "textDocument/rename" then
          rename_completed = rename_completed + 1
        end
      end
    end,
  })
end
if scenario == "lsp-l5" or scenario == "lsp-l6" then
  vim.api.nvim_create_autocmd("BufEnter", {
    callback = function() buffer_enters = buffer_enters + 1 end,
  })
  vim.api.nvim_create_autocmd("WinEnter", {
    callback = function() window_enters = window_enters + 1 end,
  })
end

local function menu_state()
  local profile = vim.env.ACCESS_LINK_HUMAN_PROFILE
  if profile == "cmp" then
    local cmp = require("cmp")
    if not cmp.visible() then return false, -1, {} end
    local selected = cmp.get_selected_entry()
    local index = -1
    local labels = {}
    for i, entry in ipairs(cmp.get_entries()) do
      labels[i] = entry:get_completion_item().label
      if entry == selected then index = i - 1 end
    end
    return true, index, labels
  elseif profile == "blink" then
    local blink = require("blink.cmp")
    if not blink.is_menu_visible() then return false, -1, {} end
    return true, (blink.get_selected_item_idx() or 0) - 1,
      vim.tbl_map(function(item) return item.label end, blink.get_items())
  end
  local info = vim.fn.complete_info({ "pum_visible", "selected", "items" })
  return info.pum_visible == 1, info.selected,
    vim.tbl_map(function(item)
      return item.abbr ~= "" and item.abbr or item.word
    end, info.items or {})
end

local function observe()
  local visible, selected, items = menu_state()
  local cursor = vim.api.nvim_win_get_cursor(0)
  local line = vim.api.nvim_get_current_line()
  local clients = vim.lsp.get_clients({ bufnr = 0, name = "pyright" })
  local client = clients[1]
  if vim.env.NAL_FOCUS_GUIDED == "held-l3" and not signature_requested
      and client and client.initialized and line:match("^total = calculate_total%(") then
    local params = vim.lsp.util.make_position_params(0, client.offset_encoding)
    params.position.character = line:find("(", 1, true)
    signature_requested = client:request("textDocument/signatureHelp", params, function(err, result)
      if not err and result and #(result.signatures or {}) > 0 then
        signature_help = result
      else
        signature_requested = false
      end
    end, 0)
  end
  local diagnostics = {}
  if vim.env.NAL_FOCUS_GUIDED == "audio-d1" or vim.env.NAL_FOCUS_GUIDED == "held-d2"
      or vim.env.NAL_FOCUS_GUIDED == "audio-d3" or vim.env.NAL_FOCUS_GUIDED == "audio-d4" then
    for _, entry in ipairs(vim.diagnostic.get(0)) do
      diagnostics[#diagnostics + 1] = {
        source = entry.source,
        code = entry.code,
        severity = entry.severity,
        message = entry.message,
        row = entry.lnum + 1,
        byteColumn = entry.col,
        endRow = entry.end_lnum + 1,
        endByteColumn = entry.end_col,
      }
    end
  end
  local buffers
  if scenario == "lsp-l4" or scenario == "lsp-l5" or scenario == "lsp-l6" then
    buffers = {}
    for _, buffer in ipairs(vim.api.nvim_list_bufs()) do
      local name = vim.fs.basename(vim.api.nvim_buf_get_name(buffer))
      if vim.api.nvim_buf_is_loaded(buffer) and (name == "lsp_features.py" or name == "lsp_rename_consumer.py") then
        buffers[name] = { lines = vim.api.nvim_buf_get_lines(buffer, 0, -1, true),
          modified = vim.bo[buffer].modified, id = buffer }
      end
    end
  end
  local quickfix
  if scenario == "lsp-l4" then
    local result = vim.fn.getqflist({ items = 0, idx = 0, id = 0, winid = 1 })
    quickfix = { index = result.idx, id = result.id, window = result.winid, items = vim.tbl_map(function(item)
      return { filename = vim.fs.basename(vim.api.nvim_buf_get_name(item.bufnr)),
        row = item.lnum, column = item.col, text = item.text }
    end, result.items) }
  end
  local lazy_lines, lazy_window
  if scenario and scenario:match("^lazy%-") and vim.bo.filetype == "lazy" then
    lazy_lines = vim.api.nvim_buf_get_lines(0, 0, -1, true)
    local windows = vim.api.nvim_tabpage_list_wins(0)
    local active = vim.api.nvim_get_current_win()
    for index, window in ipairs(windows) do
      if window == active then lazy_window = { index = index, count = #windows } end
    end
  end
  local state = vim.json.encode({
    attached = vim.iter(clients):
      any(function(client) return client.initialized end),
    line = line,
    signatureHelp = signature_help,
    signatureCompleted = signature_completed,
    renameCompleted = rename_completed,
    activeBuffer = vim.api.nvim_get_current_buf(),
    activeWindow = vim.api.nvim_get_current_win(),
    bufferEnters = buffer_enters,
    windowEnters = window_enters,
    activeName = vim.fs.basename(vim.api.nvim_buf_get_name(0)),
    quickfix = quickfix,
    lazyLines = lazy_lines,
    lazyWindow = lazy_window,
    commandType = vim.fn.getcmdtype(),
    commandText = vim.fn.getcmdline(),
    buffers = buffers,
    clients = vim.iter(vim.lsp.get_clients({ bufnr = 0 })):
      filter(function(value) return value.initialized end):
      map(function(value) return value.name end):totable(),
    filetype = vim.bo.filetype,
    row = cursor[1],
    cursorMoves = moved,
    byteColumn = cursor[2],
    diagnostics = diagnostics,
    mode = vim.api.nvim_get_mode().mode,
    changedtick = vim.api.nvim_buf_get_changedtick(0),
    modified = vim.bo.modified,
    visible = visible,
    selected = selected,
    items = items,
  })
  if state ~= last then
    local file = assert(io.open(path, "w"))
    file:write(state)
    file:close()
    last = state
  end
  vim.defer_fn(observe, 150)
end
vim.api.nvim_create_autocmd("VimEnter", {
  once = true,
  callback = function()
    if scenario == "lsp-l1" then
      vim.keymap.set("n", "<F8>", function() vim.lsp.enable("pyright", false) end)
    end
    observe()
  end,
})
