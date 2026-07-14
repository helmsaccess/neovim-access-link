local M = {}

local owner
local active_kind
local timer
local last_signature
local cmp_hooked = false

local kind_names = {
  [1] = "text", [2] = "method", [3] = "function", [4] = "constructor",
  [5] = "field", [6] = "variable", [7] = "class", [8] = "interface",
  [9] = "module", [10] = "property", [13] = "enum", [14] = "keyword",
  [15] = "snippet", [17] = "file", [19] = "folder", [21] = "constant",
}

local function text(value)
  if type(value) == "string" then return value end
  if type(value) == "table" then return value.value or value.kind or "" end
  return ""
end

function M.normalize_item(item)
  item = type(item) == "table" and item or {}
  local label = item.label or item.word or item.abbr or item.insertText or ""
  local kind = item.kind
  return {
    word = label,
    abbr = item.abbr or label,
    kind = type(kind) == "number" and (kind_names[kind] or tostring(kind)) or (kind or ""),
    menu = item.menu or item.detail or item.source_name or item.source or "",
    info = text(item.documentation or item.info),
    user_data = item.user_data,
  }
end

local function publish(kind, raw_items, selected)
  local items = {}
  for _, raw in ipairs(raw_items or {}) do table.insert(items, M.normalize_item(raw)) end
  local selected_item = items[selected or 0]
  local signature = vim.inspect({ kind, selected, selected_item and selected_item.abbr, #items })
  if signature == last_signature then return end
  last_signature = signature
  if active_kind ~= kind then
    active_kind = kind
    owner.accessible_menu_open(items, { kind = kind, selected = selected or 0 })
  else
    owner.accessible_menu_open(items, { kind = kind, selected = selected or 0 })
  end
end

local function close()
  if timer then timer:stop(); timer:close(); timer = nil end
  if active_kind then owner.accessible_menu_close() end
  active_kind, last_signature = nil, nil
end

local function start_poll(callback)
  if timer then timer:stop(); timer:close() end
  timer = vim.uv.new_timer()
  timer:start(0, 35, vim.schedule_wrap(function()
    local ok, visible, items, selected = pcall(callback)
    if not ok or not visible then close(); return end
    publish(active_kind, items, selected)
  end))
end

local function setup_nvim_cmp()
  if cmp_hooked then return true end
  local ok, cmp = pcall(require, "cmp")
  if not ok or type(cmp) ~= "table" or type(cmp.event) ~= "table" then return false end
  cmp.event:on("menu_opened", function()
    active_kind = "nvim-cmp"
    start_poll(function()
      if vim.fn.pumvisible() == 1 then return false end -- native_menu uses the standard path.
      local entries = type(cmp.get_entries) == "function" and cmp.get_entries() or {}
      local selected_entry = type(cmp.get_selected_entry) == "function" and cmp.get_selected_entry() or nil
      local items, selected = {}, 0
      for index, entry in ipairs(entries) do
        local item = type(entry.get_completion_item) == "function" and entry:get_completion_item() or entry
        table.insert(items, item)
        if entry == selected_entry then selected = index end
      end
      return type(cmp.visible) ~= "function" or cmp.visible(), items, selected
    end)
  end)
  cmp.event:on("menu_closed", close)
  cmp_hooked = true
  return true
end

local function setup_blink(group)
  vim.api.nvim_create_autocmd("User", {
    group = group, pattern = "BlinkCmpMenuOpen",
    callback = function()
      local ok = pcall(require, "blink.cmp")
      if not ok then return end
      active_kind = "blink.cmp"
      start_poll(function()
        local blink = require("blink.cmp")
        local visible = type(blink.is_menu_visible) ~= "function" or blink.is_menu_visible()
        local items = type(blink.get_items) == "function" and blink.get_items() or {}
        local selected_item = type(blink.get_selected_item) == "function" and blink.get_selected_item() or nil
        local selected = 0
        for index, item in ipairs(items) do if item == selected_item then selected = index end end
        return visible, items, selected
      end)
    end,
  })
  vim.api.nvim_create_autocmd("User", {
    group = group, pattern = "BlinkCmpMenuClose", callback = close,
  })
  return true
end

function M.setup(menu_owner, group)
  owner = menu_owner
  local cmp_ready = setup_nvim_cmp()
  if not cmp_ready then
    vim.api.nvim_create_autocmd("User", {
      group = group, pattern = "CmpReady", callback = setup_nvim_cmp,
    })
  end
  return { nvim_cmp = cmp_ready, blink_cmp = setup_blink(group) }
end

function M.stop() close() end

return M
