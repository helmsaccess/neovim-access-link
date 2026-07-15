#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for spec in "$root"/neovim-plugin/tests/*_spec.lua; do
  arguments=(--headless -n -u NONE -i NONE --cmd "set packpath=")
  if [[ "$(basename "$spec")" == "file_manager_spec.lua" ]]; then
    # Neovim 0.12 ships netrw as an optional runtime package. Keep user
    # packages isolated while making the distribution runtime available.
    arguments+=(
      --cmd "set packpath^=\$VIMRUNTIME"
      --cmd "if isdirectory(\$VIMRUNTIME . '/pack/dist/opt/netrw') | packadd netrw | else | runtime plugin/netrwPlugin.vim | endif"
    )
  fi
  # -l propagates an uncaught Lua error through Neovim's process exit status.
  # A trailing `-c qa!` would mask startup/spec errors by exiting successfully.
  nvim "${arguments[@]}" -l "$spec"
done
