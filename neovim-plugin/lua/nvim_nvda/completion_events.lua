local menu = require("nvim_nvda.menu")
local adapters = require("nvim_nvda.completion_adapters")
local native_completion = require("nvim_nvda.native_completion")

local M = {}

function M.new(emit)
  assert(type(emit) == "function", "event emitter required")

  local instance = {}
  local completion_menu = menu.new()
  local adapter_menu = menu.new()
  local adapter_info

  local function emit_menu_events(events, reason)
    for _, menu_event in ipairs(events) do
      emit(menu_event.type, reason, menu_event.payload)
    end
  end

  function instance.setup(group)
    native_completion.stop()
    adapters.stop()
    vim.api.nvim_create_autocmd("CompleteChanged", {
      group = group,
      callback = function(event)
        local info = vim.fn.complete_info({ "mode", "pum_visible", "items", "selected" })
        emit_menu_events(completion_menu:update(info), event.event)
        if (tonumber(info.selected) or -1) >= 0 then
          native_completion.resolve(info, function(refreshed_info)
            emit_menu_events(
              completion_menu:update(refreshed_info),
              "completionDetailRefresh"
            )
          end, event.buf)
        else
          native_completion.stop()
        end
      end,
    })
    vim.api.nvim_create_autocmd("CompleteDonePre", {
      group = group,
      callback = function(event)
        native_completion.stop()
        emit_menu_events(completion_menu:close("completionDone"), event.event)
      end,
    })
    vim.api.nvim_create_autocmd("InsertLeave", {
      group = group,
      callback = function(event)
        native_completion.stop()
        emit_menu_events(completion_menu:close("insertLeave"), event.event)
      end,
    })
    vim.schedule(function() adapters.setup(instance, group) end)
  end

  function instance.test_menu_update(info)
    emit_menu_events(completion_menu:update(info), "testMenu")
  end

  function instance.test_menu_close()
    emit_menu_events(completion_menu:close("testDone"), "testMenu")
  end

  -- Public adapter for plugins which draw a custom menu instead of using
  -- Neovim's built-in completion popup. Items use complete-item fields.
  function instance.accessible_menu_begin(options)
    options = options or {}
    adapter_info = {
      mode = options.kind or "plugin",
      pum_visible = true,
      selected = -1,
      item_count = 0,
    }
    emit_menu_events(adapter_menu:begin({
      mode = adapter_info.mode,
      item_count = options.item_count or 0,
    }), "pluginMenu")
  end

  function instance.accessible_menu_open(items, options)
    options = options or {}
    adapter_info = {
      mode = options.kind or "plugin",
      pum_visible = true,
      selected = (options.selected or 1) - 1,
      items = items or {},
    }
    emit_menu_events(adapter_menu:update(adapter_info), "pluginMenu")
  end

  -- Efficient adapter boundary for custom completion menus. Only the selected
  -- raw item crosses this boundary; item_count remains the complete menu size.
  function instance.accessible_menu_update(item, options)
    options = options or {}
    adapter_info = {
      mode = options.kind or "plugin",
      pum_visible = true,
      selected = (options.selected or 0) - 1,
      selected_item = item,
      item_count = options.item_count or 0,
    }
    emit_menu_events(adapter_menu:update(adapter_info), "pluginMenu")
  end

  function instance.accessible_menu_select(one_based_index)
    if not adapter_info then return end
    adapter_info.selected = (tonumber(one_based_index) or 0) - 1
    emit_menu_events(adapter_menu:update(adapter_info), "pluginMenu")
  end

  function instance.accessible_menu_close()
    adapter_info = nil
    emit_menu_events(adapter_menu:close("pluginClosed"), "pluginMenu")
  end

  return instance
end

return M
