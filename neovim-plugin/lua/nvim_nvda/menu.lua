local M = {}

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
  [2] = "method", [3] = "function", [4] = "constructor", [5] = "field",
  [6] = "variable", [7] = "class", [8] = "interface", [9] = "module",
  [10] = "property", [13] = "enum", [14] = "keyword", [17] = "file",
  [21] = "constant", [22] = "struct", [23] = "event", [25] = "type parameter",
}

local function bounded_string(value, maximum)
  if type(value) ~= "string" then return "" end
  if #value <= maximum then return value end
  return value:sub(1, maximum)
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

local function lsp_completion_item(item)
  local user_data = item.user_data
  if type(user_data) == "string" and user_data ~= "" then
    local ok, decoded = pcall(vim.json.decode, user_data)
    if ok then user_data = decoded end
  end
  if type(user_data) ~= "table" then return nil end
  local nvim_data = user_data.nvim
  local lsp_data = type(nvim_data) == "table" and nvim_data.lsp or nil
  local completion = type(lsp_data) == "table" and lsp_data.completion_item or nil
  return type(completion) == "table" and completion or nil
end

function M.normalize_item(item)
  item = type(item) == "table" and item or {}
  local word = bounded_string(item.word, 512)
  local abbreviation = bounded_string(item.abbr, 512)
  local lsp_item = lsp_completion_item(item)
  local lsp_label = lsp_item and bounded_string(lsp_item.label, 512) or ""
  local source_label = abbreviation ~= "" and abbreviation or (lsp_label ~= "" and lsp_label or word)
  local label, parameters = signature_parts(source_label)
  local detail = lsp_item and bounded_string(lsp_item.detail, 1024) or ""
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
  local kind = bounded_string(item.kind, 64)
  if lsp_item and type(lsp_item.kind) == "number" then
    kind = lsp_kind_names[lsp_item.kind] or kind
  else
    kind = kind_names[item.kind] or kind
  end
  return {
    label = bounded_string(label, 512),
    insertText = word,
    kind = kind,
    menu = bounded_string(item.menu, 256) ~= "" and bounded_string(item.menu, 256) or detail,
    parameters = bounded_string(parameters, 1024),
    documentation = documentation,
  }
end

function M.new()
  local self = { open = false, selection_key = nil }

  function self:update(info)
    info = type(info) == "table" and info or {}
    local raw_items = type(info.items) == "table" and info.items or {}
    if not info.pum_visible or #raw_items == 0 then
      return self:close("hidden")
    end
    local items = {}
    for index = 1, math.min(#raw_items, 200) do
      items[index] = M.normalize_item(raw_items[index])
    end
    local events = {}
    if not self.open then
      self.open = true
      events[#events + 1] = {
        type = "menuOpened",
        payload = { menuKind = bounded_string(info.mode, 64), itemCount = #raw_items },
      }
    end
    local selected = tonumber(info.selected) or -1
    if selected >= 0 and selected < #items then
      local item = items[selected + 1]
      local selection_key = table.concat({
        tostring(selected), tostring(#raw_items), item.label, item.kind,
        item.menu, item.parameters, item.documentation,
      }, "\0")
      if selection_key ~= self.selection_key then
        self.selection_key = selection_key
        events[#events + 1] = {
          type = "menuSelectionChanged",
          payload = {
            menuKind = bounded_string(info.mode, 64),
            item = item,
            itemIndex = selected + 1,
            itemCount = #raw_items,
          },
        }
      end
    else
      self.selection_key = nil
    end
    return events
  end

  function self:close(reason)
    if not self.open then return {} end
    self.open = false
    self.selection_key = nil
    return {{ type = "menuClosed", payload = { reason = reason or "closed" } }}
  end

  return self
end

return M
