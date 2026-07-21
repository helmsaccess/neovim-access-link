#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
product_name="$(cd "$root" && python3 -c 'import buildVars; print(buildVars.addon_info["summary"])')"
product_slug="$(cd "$root" && python3 -c 'import buildVars; print(buildVars.product_slug())')"
output_dir="${1:-$root/build/docs}"
output_dir="$(realpath -m "$output_dir")"

quick_output="$output_dir/$product_slug-quick-guide-de.html"
handbook_output="$output_dir/$product_slug-handbook-de.html"
developer_output="$output_dir/$product_slug-developer-documentation-de.html"
quick_en_output="$output_dir/$product_slug-quick-guide-en.html"
handbook_en_output="$output_dir/$product_slug-handbook-en.html"
developer_en_output="$output_dir/$product_slug-developer-documentation-en.html"

quick_sources=(
  docs/de/manual/quick-guide.md
)

handbook_sources=(
  docs/de/manual/README.md
  docs/de/manual/settings.md
  docs/de/manual/communication.md
  docs/de/manual/ssh-and-tmux.md
  docs/de/manual/menus-and-completion.md
  docs/de/manual/terminals-and-file-managers.md
  docs/de/manual/sounds.md
  docs/de/manual/braille.md
  docs/de/manual/troubleshooting.md
)

developer_sources=(
  docs/de/development/README.md
  docs/de/development/overview.md
  docs/de/development/architecture.md
  docs/de/development/repository-layout.md
  docs/de/development/getting-started.md
  docs/de/development/current-status.md
  docs/de/development/compatibility.md
  docs/de/development/localization.md
  docs/de/development/adr/0001-neovim-integration-point.md
  docs/de/development/adr/0002-nvda-api-boundaries.md
  docs/de/development/adr/0003-oil-confirmation-fallback.md
  docs/de/development/adr/0004-nvda-lifetime-and-event-ownership.md
  docs/de/development/security.md
  docs/de/development/latency.md
  docs/de/development/protocol.md
  docs/de/development/settings-reference.md
  docs/de/development/component-installation.md
  docs/de/development/testing.md
  docs/de/development/accessibility.md
  docs/de/development/release-and-build.md
  docs/de/development/nvda-2026.1-api-notes.md
  docs/de/development/licensing-and-contributions.md
  nvda-addon/DEPENDENCIES.md
  docs/de/development/plan.md
  docs/de/development/changelog.md
  docs/de/development/quality-review-global-plugin-slimming-2026-07-19.md
  docs/de/development/code-analysis-global-plugin-slimming-v0.94.2-2026-07-21.md
)

quick_en_sources=(
  docs/en/manual/quick-guide.md
)

handbook_en_sources=(
  docs/en/manual/README.md
  docs/en/manual/settings.md
  docs/en/manual/communication.md
  docs/en/manual/ssh-and-tmux.md
  docs/en/manual/menus-and-completion.md
  docs/en/manual/terminals-and-file-managers.md
  docs/en/manual/sounds.md
  docs/en/manual/braille.md
  docs/en/manual/troubleshooting.md
)

developer_en_sources=(
  docs/en/development/README.md
  docs/en/development/overview.md
  docs/en/development/architecture.md
  docs/en/development/repository-layout.md
  docs/en/development/getting-started.md
  docs/en/development/current-status.md
  docs/en/development/compatibility.md
  docs/en/development/localization.md
  docs/en/development/adr/0001-neovim-integration-point.md
  docs/en/development/adr/0002-nvda-api-boundaries.md
  docs/en/development/adr/0003-oil-confirmation-fallback.md
  docs/en/development/adr/0004-nvda-lifetime-and-event-ownership.md
  docs/en/development/security.md
  docs/en/development/latency.md
  docs/en/development/protocol.md
  docs/en/development/settings-reference.md
  docs/en/development/component-installation.md
  docs/en/development/testing.md
  docs/en/development/accessibility.md
  docs/en/development/release-and-build.md
  docs/en/development/nvda-2026.1-api-notes.md
  docs/en/development/licensing-and-contributions.md
  docs/en/development/dependencies.md
  docs/en/development/plan.md
  docs/en/development/changelog.md
  docs/en/development/quality-review-global-plugin-slimming-2026-07-19.md
  docs/en/development/code-analysis-global-plugin-slimming-v0.94.2-2026-07-21.md
)

command -v pandoc >/dev/null || {
  echo "error: pandoc is required (tested with 3.1.11.1)" >&2
  exit 1
}

validate_source() {
  local source="$1"
  local path="$root/$source"
  [[ -f "$path" ]] || {
    echo "error: configured Markdown source is missing: $source" >&2
    exit 1
  }
  local first_heading
  first_heading="$(awk '/^#/ { print; exit }' "$path")"
  [[ "$first_heading" == "# "* && "$first_heading" != "## "* ]] || {
    echo "error: Markdown source must begin its heading structure with H1: $source" >&2
    exit 1
  }
}

for source in "${quick_sources[@]}" "${handbook_sources[@]}" "${developer_sources[@]}" \
  "${quick_en_sources[@]}" "${handbook_en_sources[@]}" "${developer_en_sources[@]}"; do
  validate_source "$source"
done

declare -A included_manual=()
for source in "${quick_sources[@]}" "${handbook_sources[@]}"; do
  included_manual["$source"]=1
done
while IFS= read -r discovered; do
  relative="${discovered#./}"
  [[ -n "${included_manual[$relative]:-}" ]] || {
    echo "error: manual Markdown source is not assigned to an HTML document: $relative" >&2
    exit 1
  }
done < <(cd "$root" && find docs/de/manual -maxdepth 1 -type f -name '*.md' | sort)

declare -A included_developer=()
for source in "${developer_sources[@]}"; do
  [[ "$source" == docs/de/development/* ]] && included_developer["$source"]=1
done
while IFS= read -r discovered; do
  relative="${discovered#./}"
  [[ -n "${included_developer[$relative]:-}" ]] || {
    echo "error: developer Markdown source is not assigned to its HTML document: $relative" >&2
    exit 1
  }
done < <(cd "$root" && find docs/de/development -type f -name '*.md' | sort)

declare -A included_en_manual=()
for source in "${quick_en_sources[@]}" "${handbook_en_sources[@]}"; do
  included_en_manual["$source"]=1
done
while IFS= read -r discovered; do
  relative="${discovered#./}"
  [[ -n "${included_en_manual[$relative]:-}" ]] || {
    echo "error: English manual source is not assigned to an HTML document: $relative" >&2
    exit 1
  }
done < <(cd "$root" && find docs/en/manual -maxdepth 1 -type f -name '*.md' | sort)

declare -A included_en_developer=()
for source in "${developer_en_sources[@]}"; do
  included_en_developer["$source"]=1
done
while IFS= read -r discovered; do
  relative="${discovered#./}"
  [[ -n "${included_en_developer[$relative]:-}" ]] || {
    echo "error: English developer source is not assigned to its HTML document: $relative" >&2
    exit 1
  }
done < <(cd "$root" && find docs/en/development -type f -name '*.md' | sort)

validate_html() {
  local output="$1"
  if grep -Eiq 'href="[^"]*\.md([#?"][^"]*)?' "$output"; then
    echo "error: generated HTML still contains links to Markdown sources: $output" >&2
    exit 1
  fi

  python3 - "$output" <<'PY'
from html.parser import HTMLParser
from pathlib import Path
import sys

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.references = set()

    def handle_starttag(self, _tag, attributes):
        values = dict(attributes)
        if "id" in values:
            self.ids.add(values["id"])
        if values.get("href", "").startswith("#"):
            self.references.add(values["href"][1:])

links = Links()
links.feed(Path(sys.argv[1]).read_text(encoding="utf-8"))
missing = sorted(links.references - links.ids)
if missing:
    raise SystemExit("error: generated HTML has missing internal targets: " + ", ".join(missing))
PY

  local h1_count
  h1_count="$(grep -Eoc '<h1([ >])' "$output")"
  [[ "$h1_count" -eq 1 ]] || {
    echo "error: generated HTML must contain exactly one H1, found $h1_count: $output" >&2
    exit 1
  }
}

build_html() {
  local output="$1"
  local title="$2"
  local use_link_filter="$3"
  shift 3
  local sources=("$@")
  local extra=()
  local language=de
  [[ "$output" == *-en.html ]] && language=en
  if [[ "$use_link_filter" == "yes" ]]; then
    extra+=(--file-scope --lua-filter=docs/markdown-links.lua)
  elif [[ "$use_link_filter" == "development" ]]; then
    extra+=(--file-scope --lua-filter=docs/development-links.lua)
  elif [[ "$use_link_filter" == "english" ]]; then
    extra+=(--file-scope --lua-filter=docs/english-links.lua)
  fi
  (cd "$root" && pandoc \
    --from=gfm \
    --to=html5 \
    --standalone \
    --embed-resources \
    --shift-heading-level-by=1 \
    --metadata title="$title" \
    --metadata lang="$language" \
    --toc \
    --toc-depth=4 \
    --section-divs \
    "${extra[@]}" \
    --css=docs/documentation.css \
    --output="$output" \
    "${sources[@]}")
  validate_html "$output"
  echo "built $output ($(wc -c < "$output") bytes) from ${#sources[@]} Markdown sources"
}

mkdir -p "$output_dir"
build_html \
  "$quick_output" "$product_name – Quick Guide" no \
  "${quick_sources[@]}"
build_html \
  "$handbook_output" "$product_name – Handbuch" yes \
  "${handbook_sources[@]}"
build_html \
  "$developer_output" "$product_name – Entwicklerdokumentation" development \
  "${developer_sources[@]}"
build_html \
  "$quick_en_output" "$product_name – Quick Guide" no \
  "${quick_en_sources[@]}"
build_html \
  "$handbook_en_output" "$product_name – User Manual" english \
  "${handbook_en_sources[@]}"
build_html \
  "$developer_en_output" "$product_name – Developer Documentation" english \
  "${developer_en_sources[@]}"
