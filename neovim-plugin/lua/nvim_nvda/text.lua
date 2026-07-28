local M = {}

local function utf8_sequence_length(value, offset)
  local first = value:byte(offset)
  if not first then return nil end
  if first <= 0x7f then return 1 end

  local second = value:byte(offset + 1)
  if first >= 0xc2 and first <= 0xdf then
    return second and second >= 0x80 and second <= 0xbf and 2 or nil
  end

  local third = value:byte(offset + 2)
  if first == 0xe0 then
    return second and second >= 0xa0 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf and 3 or nil
  end
  if (first >= 0xe1 and first <= 0xec) or (first >= 0xee and first <= 0xef) then
    return second and second >= 0x80 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf and 3 or nil
  end
  if first == 0xed then
    return second and second >= 0x80 and second <= 0x9f
      and third and third >= 0x80 and third <= 0xbf and 3 or nil
  end

  local fourth = value:byte(offset + 3)
  if first == 0xf0 then
    return second and second >= 0x90 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf
      and fourth and fourth >= 0x80 and fourth <= 0xbf and 4 or nil
  end
  if first >= 0xf1 and first <= 0xf3 then
    return second and second >= 0x80 and second <= 0xbf
      and third and third >= 0x80 and third <= 0xbf
      and fourth and fourth >= 0x80 and fourth <= 0xbf and 4 or nil
  end
  if first == 0xf4 then
    return second and second >= 0x80 and second <= 0x8f
      and third and third >= 0x80 and third <= 0xbf
      and fourth and fourth >= 0x80 and fourth <= 0xbf and 4 or nil
  end
  return nil
end

-- Return a valid UTF-8 prefix no longer than maximum bytes. Invalid input is
-- rejected instead of placing malformed strings on the protocol boundary.
function M.bounded(value, maximum)
  if type(value) ~= "string" or type(maximum) ~= "number" or maximum < 0 then return "" end
  local offset, boundary = 1, 0
  while offset <= #value do
    local sequence_length = utf8_sequence_length(value, offset)
    if not sequence_length then return "" end
    local sequence_end = offset + sequence_length - 1
    if sequence_end > maximum then break end
    boundary = sequence_end
    offset = sequence_end + 1
  end
  return boundary == #value and value or value:sub(1, boundary)
end

-- LSP signature parameter ranges use UTF-16 code units, not UTF-8 bytes.
-- Reject ranges which split a surrogate pair or malformed input.
function M.utf16_slice(value, start_offset, end_offset, maximum)
  if type(value) ~= "string"
    or type(start_offset) ~= "number" or start_offset < 0 or start_offset % 1 ~= 0
    or type(end_offset) ~= "number" or end_offset < start_offset or end_offset % 1 ~= 0 then
    return ""
  end
  local offset, units = 1, 0
  local start_byte = start_offset == 0 and 1 or nil
  local end_byte = end_offset == 0 and 0 or nil
  while offset <= #value do
    local sequence_length = utf8_sequence_length(value, offset)
    if not sequence_length then return "" end
    local next_units = units + (sequence_length == 4 and 2 or 1)
    if not start_byte and next_units == start_offset then start_byte = offset + sequence_length end
    if not end_byte and next_units == end_offset then end_byte = offset + sequence_length - 1 end
    if next_units > start_offset and not start_byte then return "" end
    if next_units > end_offset and not end_byte then return "" end
    units = next_units
    offset = offset + sequence_length
  end
  if not start_byte and units == start_offset then start_byte = #value + 1 end
  if not end_byte and units == end_offset then end_byte = #value end
  if not start_byte or not end_byte then return "" end
  return M.bounded(value:sub(start_byte, end_byte), maximum or #value)
end

return M
