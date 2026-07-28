#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -lt 2 || "$#" -gt 3 ]]; then
  echo "usage: $0 NVIM_CMP_CHECKOUT BLINK_CMP_CHECKOUT [BLINK_LIB_CHECKOUT]" >&2
  exit 2
fi
if [[ ! -d "$1/lua/cmp" || ! -d "$2/lua/blink/cmp" ]]; then
  echo "the arguments must be nvim-cmp and blink.cmp source checkouts" >&2
  exit 2
fi
if [[ "$#" -eq 3 && ! -d "$3/lua/blink/lib" ]]; then
  echo "the optional third argument must be a blink.lib source checkout" >&2
  exit 2
fi

test_state="$(mktemp -d)"
trap 'rm -rf "$test_state"' EXIT
export XDG_CACHE_HOME="$test_state/cache"
export XDG_CONFIG_HOME="$test_state/config"
export XDG_DATA_HOME="$test_state/data"
export XDG_STATE_HOME="$test_state/state"
mkdir -p "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"
export NVIM_NVDA_NVIM_CMP_ROOT="$1"
export NVIM_NVDA_BLINK_CMP_ROOT="$2"
export NVIM_NVDA_BLINK_LIB_ROOT="${3:-}"
nvim --headless -n -u NONE -i NONE --cmd "set packpath=" \
  -l "$root/neovim-plugin/tests/completion_plugins_integration.lua"
