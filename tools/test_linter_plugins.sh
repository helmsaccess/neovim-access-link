#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$#" -ne 2 ]]; then
  echo "usage: $0 NVIM_LINT_CHECKOUT ALE_CHECKOUT" >&2
  exit 2
fi
if [[ ! -d "$1/lua/lint" || ! -f "$2/plugin/ale.vim" ]]; then
  echo "the arguments must be nvim-lint and ALE source checkouts" >&2
  exit 2
fi

ruff_version="$(ruff --version)"
shellcheck_version="$(shellcheck --version | sed -n 's/^version: //p')"
clang_tidy_version="$(clang-tidy --version)"
staticcheck_version="$(staticcheck -version)"
clippy_version="$(cargo clippy --version)"
rubocop_version="$(rubocop --version)"
markdownlint_version="$(markdownlint-cli2 --version | sed -n '1p')"
[[ "$ruff_version" == "ruff 0.15.4" ]] || {
  echo "expected ruff 0.15.4, got: $ruff_version" >&2
  exit 1
}
[[ "$shellcheck_version" == "0.11.0" ]] || {
  echo "expected ShellCheck 0.11.0, got: $shellcheck_version" >&2
  exit 1
}
[[ "$clang_tidy_version" == *"LLVM version 22.1.8"* ]] || {
  echo "expected Clang-Tidy 22.1.8, got: $clang_tidy_version" >&2
  exit 1
}
[[ "$staticcheck_version" == "staticcheck 2026.1 (v0.7.0)" ]] || {
  echo "expected Staticcheck 2026.1 (v0.7.0), got: $staticcheck_version" >&2
  exit 1
}
[[ "$clippy_version" == clippy\ 0.1.97* ]] || {
  echo "expected Clippy 0.1.97 from Rust 1.97.1, got: $clippy_version" >&2
  exit 1
}
[[ "$rubocop_version" == "1.88.2" ]] || {
  echo "expected RuboCop 1.88.2, got: $rubocop_version" >&2
  exit 1
}
[[ "$markdownlint_version" == "markdownlint-cli2 v0.23.2 (markdownlint v0.41.1)" ]] || {
  echo "expected markdownlint-cli2 0.23.2, got: $markdownlint_version" >&2
  exit 1
}

test_state="$(mktemp -d)"
cleanup() {
  rubocop --server-stop >/dev/null 2>&1 || true
  rm -rf "$test_state"
}
trap cleanup EXIT
export XDG_CACHE_HOME="$test_state/cache"
export XDG_CONFIG_HOME="$test_state/config"
export XDG_DATA_HOME="$test_state/data"
export XDG_STATE_HOME="$test_state/state"
mkdir -p "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"
export NVIM_NVDA_NVIM_LINT_ROOT="$1"
export NVIM_NVDA_ALE_ROOT="$2"
export NVIM_NVDA_LINTER_TEST_ROOT="$test_state/fixtures"
export GOFLAGS="-buildvcs=false"
mkdir -p "$NVIM_NVDA_LINTER_TEST_ROOT"

for provider in nvim-lint ale; do
  NVIM_NVDA_LINTER_PROVIDER="$provider" \
    nvim --headless -n -u NONE -i NONE --cmd "set packpath=" \
      -l "$root/neovim-plugin/tests/linter_plugins_integration.lua"
done
