local M = {}
local text = require("nvim_nvda.text")

local kind_names = {
  f = "function",
  m = "method",
  v = "variable",
  c = "class",
  i = "interface",
  M = "module",
  p = "property",
  k = "keyword",
  t = "type",
  e = "enum",
  F = "file",
}

local lsp_kind_names = {
  [1] = "text", [2] = "method", [3] = "function", [4] = "constructor", [5] = "field",
  [6] = "variable", [7] = "class", [8] = "interface", [9] = "module",
  [10] = "property", [11] = "unit", [12] = "value", [13] = "enum",
  [14] = "keyword", [15] = "snippet", [16] = "color", [17] = "file",
  [18] = "reference", [19] = "folder", [20] = "enum member", [21] = "constant",
  [22] = "struct", [23] = "event", [24] = "operator", [25] = "type parameter",
}

local function bounded_string(value, maximum)
  return text.bounded(value, maximum)
end

local function signature_parts(label)
  local start = label:find("(", 1, true)
  if not start then return label, "" end
  local depth = 0
  for index = start, #label do
    local character = label:sub(index, index)
    if character == "(" then
      depth = depth + 1
    elseif character == ")" then
      depth = depth - 1
      if depth == 0 then
        local name = label:sub(1, start - 1):gsub("%s+$", "")
        return name ~= "" and name or label, label:sub(start + 1, index - 1)
      end
    end
  end
  return label, ""
end

local function lsp_completion_data(item)
  local user_data = item.user_data
  if type(user_data) == "string" and user_data ~= "" then
    local ok, decoded = pcall(vim.json.decode, user_data)
    if ok then user_data = decoded end
  end
  if type(user_data) ~= "table" then return nil, nil end
  local nvim_data = user_data.nvim
  local lsp_data = type(nvim_data) == "table" and nvim_data.lsp or nil
  local completion = type(lsp_data) == "table" and lsp_data.completion_item or nil
  return type(completion) == "table" and completion or nil,
    type(lsp_data) == "table" and tonumber(lsp_data.client_id) or nil
end

function M.normalize_item(item)
  item = type(item) == "table" and item or {}
  local word = bounded_string(item.word, 512)
  local abbreviation = bounded_string(item.abbr, 512)
  local lsp_item, lsp_client_id = lsp_completion_data(item)
  local lsp_label = lsp_item and bounded_string(lsp_item.label, 512) or ""
  local source_label = abbreviation ~= "" and abbreviation or (lsp_label ~= "" and lsp_label or word)
  local label, parameters = signature_parts(source_label)
  local detail = lsp_item and bounded_string(lsp_item.detail, 1024)
    or bounded_string(item.detail, 1024)
  if parameters == "" and detail ~= "" then
    local _, detail_parameters = signature_parts(detail)
    parameters = detail_parameters
  end
  local documentation = bounded_string(item.info, 2048)
  if documentation == "" and lsp_item then
    if type(lsp_item.documentation) == "string" then
      documentation = bounded_string(lsp_item.documentation, 2048)
    elseif type(lsp_item.documentation) == "table" then
      documentation = bounded_string(lsp_item.documentation.value, 2048)
    end
  end
  local raw_kind = lsp_item and lsp_item.kind or item.kind
  local kind = bounded_string(raw_kind, 64)
  if type(raw_kind) == "number" then
    kind = lsp_kind_names[raw_kind] or ""
  else
    kind = kind_names[raw_kind] or kind
  end
  local source = bounded_string(item.source_name, 256)
  if source == "" then source = bounded_string(item.source, 256) end
  if source == "" and lsp_client_id and vim.lsp and type(vim.lsp.get_client_by_id) == "function" then
    local ok, client = pcall(vim.lsp.get_client_by_id, lsp_client_id)
    if ok and type(client) == "table" then source = bounded_string(client.name, 256) end
  end
  local menu_label = bounded_string(item.menu, 256)
  return {
    label = bounded_string(label, 512),
    insertText = word,
    kind = kind,
    source = source,
    menu = menu_label ~= "" and menu_label or detail,
    detail = detail,
    parameters = bounded_string(parameters, 1024),
    documentation = documentation,
  }
end

function M.new()
  local self = { open = false, selection_key = nil, detail_key = nil }

  function self:begin(info)
    if self.open then return {} end
    info = type(info) == "table" and info or {}
    local item_count = tonumber(info.item_count) or 0
    item_count = math.max(0, math.min(math.floor(item_count), 2147483647))
    self.open = true
    self.selection_key = nil
    self.detail_key = nil
    return {{
      type = "menuOpened",
      payload = {
        menuKind = bounded_string(info.mode, 64),
        itemCount = item_count,
      },
    }}
  end

  function self:update(info)
    info = type(info) == "table" and info or {}
    local raw_items = type(info.items) == "table" and info.items or {}
    local item_count = tonumber(info.item_count) or #raw_items
    item_count = math.max(0, math.min(math.floor(item_count), 2147483647))
    if not info.pum_visible or item_count == 0 then
      return self:close("hidden")
    end
    local events = self:begin({ mode = info.mode, item_count = item_count })
    local selected = tonumber(info.selected) or -1
    local raw_item = type(info.selected_item) == "table" and info.selected_item
      or raw_items[selected + 1]
    if selected >= 0 and selected < item_count and type(raw_item) == "table" then
      local item = M.normalize_item(raw_item)
      local stable_id = bounded_string(raw_item.stableId, 512)
      local selection_key = table.concat({
        tostring(selected), tostring(item_count), stable_id, item.label,
        item.insertText, item.kind, item.source,
      }, "\0")
      local detail_key = table.concat({
        selection_key, item.menu, item.detail, item.parameters, item.documentation,
      }, "\0")
      if selection_key ~= self.selection_key then
        self.selection_key = selection_key
        self.detail_key = detail_key
        events[#events + 1] = {
          type = "menuSelectionChanged",
          payload = {
            menuKind = bounded_string(info.mode, 64),
            item = item,
            itemIndex = selected + 1,
            itemCount = item_count,
          },
        }
      elseif detail_key ~= self.detail_key then
        self.detail_key = detail_key
        events[#events + 1] = {
          type = "menuItemUpdated",
          payload = {
            menuKind = bounded_string(info.mode, 64),
            item = item,
            itemIndex = selected + 1,
            itemCount = item_count,
          },
        }
      end
    else
      if self.selection_key ~= nil then
        events[#events + 1] = {
          type = "menuSelectionCleared",
          payload = {
            menuKind = bounded_string(info.mode, 64),
            itemCount = item_count,
          },
        }
      end
      self.selection_key = nil
      self.detail_key = nil
    end
    return events
  end

  function self:close(reason)
    if not self.open then return {} end
    self.open = false
    self.selection_key = nil
    self.detail_key = nil
    return {{ type = "menuClosed", payload = { reason = reason or "closed" } }}
  end

  return self
end

return M
