#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -ne 2 ]]; then
  echo "usage: $0 NONE_LS_CHECKOUT PLENARY_CHECKOUT" >&2
  exit 2
fi
if [[ ! -f "$1/lua/null-ls/init.lua" || ! -f "$2/lua/plenary/init.lua" ]]; then
  echo "the arguments must be none-ls.nvim and plenary.nvim source checkouts" >&2
  exit 2
fi

test_state="$(mktemp -d)"
trap 'rm -rf "$test_state"' EXIT
export XDG_CACHE_HOME="$test_state/cache"
export XDG_CONFIG_HOME="$test_state/config"
export XDG_DATA_HOME="$test_state/data"
export XDG_STATE_HOME="$test_state/state"
mkdir -p "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"
export NVIM_NVDA_NONE_LS_ROOT="$1"
export NVIM_NVDA_PLENARY_ROOT="$2"
export NVIM_NVDA_NONE_LS_TEST_ROOT="$test_state/fixtures"
mkdir -p "$NVIM_NVDA_NONE_LS_TEST_ROOT"

nvim --headless -n -u NONE -i NONE --cmd "set packpath=" \
  -l "$root/neovim-plugin/tests/none_ls_integration.lua"
