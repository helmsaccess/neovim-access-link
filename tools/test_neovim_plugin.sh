#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for spec in "$root"/neovim-plugin/tests/*_spec.lua; do
  arguments=(--headless -n -u NONE -i NONE --cmd "set packpath=")
  if [[ "$(basename "$spec")" == "file_manager_spec.lua" ]]; then
    arguments+=(--cmd "runtime plugin/netrwPlugin.vim")
  fi
  nvim "${arguments[@]}" -c "lua dofile('$spec')" -c "qa!"
done
