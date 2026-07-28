local M = {}

local owner
local active_kind
local active_generation = 0
local timer
local last_signature
local cmp_hooked = false
local diagnostics = {
  activeKind = nil,
  apiVariant = nil,
  errorCount = 0,
  slowTickCount = 0,
  maximumTickNanoseconds = 0,
  pollIntervalMilliseconds = 35,
}

local kind_names = {
  [1] = "text", [2] = "method", [3] = "function", [4] = "constructor",
  [5] = "field", [6] = "variable", [7] = "class", [8] = "interface",
  [9] = "module", [10] = "property", [11] = "unit", [12] = "value",
  [13] = "enum", [14] = "keyword", [15] = "snippet", [16] = "color",
  [17] = "file", [18] = "reference", [19] = "folder", [20] = "enum member",
  [21] = "constant", [22] = "struct", [23] = "event", [24] = "operator",
  [25] = "type parameter",
}

local function text(value)
  if type(value) == "string" then return value end
  if type(value) == "table" then return value.value or value.kind or "" end
  return ""
end

function M.normalize_item(item, source_name, stable_id)
  item = type(item) == "table" and item or {}
  local label = item.label or item.word or item.abbr or item.insertText or ""
  local kind = item.kind
  local source = item.source_name or source_name
  if type(source) ~= "string" then source = "" end
  return {
    stableId = stable_id,
    word = item.word or item.insertText or label,
    abbr = item.abbr or label,
    kind = type(kind) == "number" and (kind_names[kind] or "") or (kind or ""),
    source = source,
    menu = item.menu or item.detail or source,
    detail = item.detail,
    info = text(item.documentation or item.info),
    user_data = item.user_data,
  }
end

local function selected_signature(kind, selected, item_count, item)
  return vim.inspect({
    kind,
    selected,
    item_count,
    item and item.stableId,
    item and item.word,
    item and item.abbr,
    item and item.kind,
    item and item.source,
    item and item.menu,
    item and item.detail,
    item and item.info,
  })
end

local function publish(kind, raw_item, source_name, stable_id, selected, item_count)
  local item = selected > 0 and M.normalize_item(raw_item, source_name, stable_id) or nil
  local signature = selected_signature(kind, selected, item_count, item)
  if signature == last_signature then return end
  last_signature = signature
  if type(owner.accessible_menu_update) == "function" then
    owner.accessible_menu_update(item, {
      kind = kind,
      selected = selected,
      item_count = item_count,
    })
  else
    -- Compatibility for consumers of the original public adapter boundary.
    local items = {}
    if item then items[selected] = item end
    owner.accessible_menu_open(items, { kind = kind, selected = selected })
  end
end

local function close(kind, generation)
  if kind and active_kind ~= kind then return end
  if generation and active_generation ~= generation then return end
  if timer then timer:stop(); timer:close(); timer = nil end
  if active_kind then owner.accessible_menu_close() end
  active_kind, last_signature = nil, nil
  diagnostics.activeKind = nil
end

local function start_poll(kind, api_variant, callback)
  if active_kind then close() end
  active_generation = active_generation + 1
  local generation = active_generation
  active_kind = kind
  diagnostics.activeKind = kind
  diagnostics.apiVariant = api_variant
  timer = vim.uv.new_timer()
  timer:start(0, diagnostics.pollIntervalMilliseconds, vim.schedule_wrap(function()
    if generation ~= active_generation or kind ~= active_kind then return end
    local started = vim.uv.hrtime()
    local ok, visible, item, source_name, stable_id, selected, item_count = pcall(callback)
    local elapsed = vim.uv.hrtime() - started
    diagnostics.maximumTickNanoseconds = math.max(diagnostics.maximumTickNanoseconds, elapsed)
    if elapsed > 5 * 1000 * 1000 then
      diagnostics.slowTickCount = diagnostics.slowTickCount + 1
    end
    if not ok then
      diagnostics.errorCount = diagnostics.errorCount + 1
      close(kind, generation)
      return
    end
    if not visible then
      close(kind, generation)
      return
    end
    publish(
      kind, item, source_name, stable_id, tonumber(selected) or 0,
      math.max(0, tonumber(item_count) or 0)
    )
  end))
end

local function cmp_entry_item(entry)
  if type(entry) ~= "table" then return nil, "", "" end
  local item = type(entry.completion_item) == "table" and entry.completion_item or nil
  if not item and type(entry.get_completion_item) == "function" then
    item = entry:get_completion_item()
  end
  local source = type(entry.source) == "table" and entry.source.name or ""
  local stable_id = entry.id and ("entry:" .. tostring(entry.id)) or ""
  return item, source, stable_id
end

local function setup_nvim_cmp()
  if cmp_hooked then return true end
  local ok, cmp = pcall(require, "cmp")
  if not ok or type(cmp) ~= "table" or type(cmp.event) ~= "table" then return false end
  cmp.event:on("menu_opened", function()
    start_poll("nvim-cmp", "public-entry", function()
      if vim.fn.pumvisible() == 1 then return false end -- native_menu uses the standard path.
      local entries = type(cmp.get_entries) == "function" and cmp.get_entries() or {}
      local selected_entry = type(cmp.get_selected_entry) == "function"
        and cmp.get_selected_entry() or nil
      local selected = 0
      for index, entry in ipairs(entries) do
        if entry == selected_entry then selected = index; break end
      end
      local item, source, stable_id = cmp_entry_item(selected_entry)
      -- menu_closed is the authoritative lifetime event. An empty retained
      -- view still closes defensively without a third cmp.sync() call.
      return #entries > 0, item, source, stable_id, selected, #entries
    end)
  end)
  cmp.event:on("menu_closed", function() close("nvim-cmp") end)
  cmp_hooked = true
  return true
end

local function setup_blink(group)
  vim.api.nvim_create_autocmd("User", {
    group = group, pattern = "BlinkCmpMenuOpen",
    callback = function()
      local ok, blink = pcall(require, "blink.cmp")
      if not ok then return end
      start_poll("blink.cmp", "public-selected-index", function()
        local visible = type(blink.is_menu_visible) ~= "function" or blink.is_menu_visible()
        local items = type(blink.get_items) == "function" and blink.get_items() or {}
        local selected = type(blink.get_selected_item_idx) == "function"
          and tonumber(blink.get_selected_item_idx()) or nil
        if not selected then
          local selected_item = type(blink.get_selected_item) == "function"
            and blink.get_selected_item() or nil
          selected = 0
          for index, item in ipairs(items) do
            if item == selected_item then selected = index; break end
          end
        end
        selected = selected or 0
        local item = items[selected]
        local stable_id = type(item) == "table"
          and table.concat({
            tostring(item.source_id or ""),
            tostring(item.label or ""),
            tostring(item.sortText or ""),
            tostring(item.insertText or ""),
          }, "\0") or ""
        return visible and #items > 0, item, item and item.source_name or "",
          stable_id, selected, #items
      end)
    end,
  })
  vim.api.nvim_create_autocmd("User", {
    group = group, pattern = "BlinkCmpMenuClose",
    callback = function() close("blink.cmp") end,
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

function M.diagnostics()
  return vim.deepcopy(diagnostics)
end

function M.stop() close() end

return M
