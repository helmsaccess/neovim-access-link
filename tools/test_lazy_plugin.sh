#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! -d "$1/lua/lazy" ]]; then
  echo "usage: $0 PATH_TO_PINNED_LAZY_NVIM" >&2
  exit 2
fi

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
lazy_input=$(cd "$1" && pwd)
workspace=$(mktemp -d "${TMPDIR:-/tmp}/access-link-lazy-test.XXXXXX")
trap 'rm -rf "$workspace"' EXIT
mkdir -p "$workspace/lazy.nvim"
cp -a "$lazy_input/." "$workspace/lazy.nvim/"
lazy_source="$workspace/lazy.nvim"

for mode in install update sync; do
  XDG_CONFIG_HOME="$workspace/xdg-config-$mode" \
    XDG_DATA_HOME="$workspace/xdg-data-$mode" \
    XDG_STATE_HOME="$workspace/xdg-state-$mode" \
    XDG_CACHE_HOME="$workspace/xdg-cache-$mode" \
    nvim --headless -u NONE -l \
    "$root/tests/human/framework/lazy_operations_probe.lua" \
    "$mode" "$lazy_source" "$root/neovim-plugin" "$workspace/$mode"
done
