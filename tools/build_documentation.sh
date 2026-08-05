#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
product_name="$(cd "$root" && python3 -c 'import buildVars; print(buildVars.addon_info["summary"])')"
product_slug="$(cd "$root" && python3 -c 'import buildVars; print(buildVars.product_slug())')"
output_dir="${1:-$root/build/docs}"
output_dir="$(realpath -m "$output_dir")"
archive_dir="${2:-$root/dist}"
archive_dir="$(realpath -m "$archive_dir")"
artifact_version="$(cd "$root" && python3 -c 'import buildVars; print(buildVars.artifact_version())')"

quick_output="$output_dir/$product_slug-quick-guide-de.html"
handbook_output="$output_dir/$product_slug-handbook-de.html"
developer_output="$output_dir/$product_slug-developer-documentation-de.html"
human_testing_output="$output_dir/$product_slug-human-testing-de.html"
quick_en_output="$output_dir/$product_slug-quick-guide-en.html"
handbook_en_output="$output_dir/$product_slug-handbook-en.html"
developer_en_output="$output_dir/$product_slug-developer-documentation-en.html"
human_testing_en_output="$output_dir/$product_slug-human-testing-en.html"
documentation_archive="$archive_dir/$product_slug-$artifact_version-documentation.zip"

quick_sources=(
  docs/de/manual/quick-guide.md
)

handbook_sources=(
  docs/de/manual/README.md
  docs/de/manual/basics.md
  docs/de/manual/communication.md
  docs/de/manual/speech-exploration.md
  docs/de/manual/braille.md
  docs/de/manual/menus-and-completion.md
  docs/de/manual/terminals-and-file-managers.md
  docs/de/manual/ssh-and-tmux.md
  docs/de/manual/language-tools.md
  docs/de/manual/example-configuration.md
  docs/de/manual/commands.md
  docs/de/manual/settings.md
  docs/de/manual/sounds.md
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
  docs/de/development/adr/0005-contextual-exploration-input.md
  docs/de/development/adr/0006-local-tcp-and-ssh-stdio-transports.md
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
  docs/de/development/dependencies.md
  docs/de/development/plan.md
  docs/de/development/changelog.md
  docs/de/development/quality-review-global-plugin-slimming-2026-07-19.md
  docs/de/development/code-analysis-global-plugin-slimming-v0.94.2-2026-07-21.md
  docs/de/development/global-plugin-appmodule-audit-2026-08-04.md
)

developer_archive_sources=(
  docs/de/development/changelog-history.md
)

human_testing_sources=(
  docs/de/development/human-testing.md
)

quick_en_sources=(
  docs/en/manual/quick-guide.md
)

handbook_en_sources=(
  docs/en/manual/README.md
  docs/en/manual/basics.md
  docs/en/manual/communication.md
  docs/en/manual/speech-exploration.md
  docs/en/manual/braille.md
  docs/en/manual/menus-and-completion.md
  docs/en/manual/terminals-and-file-managers.md
  docs/en/manual/ssh-and-tmux.md
  docs/en/manual/language-tools.md
  docs/en/manual/example-configuration.md
  docs/en/manual/commands.md
  docs/en/manual/settings.md
  docs/en/manual/sounds.md
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
  docs/en/development/adr/0005-contextual-exploration-input.md
  docs/en/development/adr/0006-local-tcp-and-ssh-stdio-transports.md
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
  docs/en/development/global-plugin-appmodule-audit-2026-08-04.md
)

developer_en_archive_sources=(
  docs/en/development/changelog-history.md
)

human_testing_en_sources=(
  docs/en/development/human-testing.md
)

command -v pandoc >/dev/null || {
  echo "error: pandoc is required (tested with 3.1.11.1)" >&2
  exit 1
}

python3 "$root/tools/sync_documentation_examples.py" --check

validate_source() {
  local source="$1"
  local path="$root/$source"
  [[ -f "$path" ]] || {
    echo "error: configured Markdown source is missing: $source" >&2
    exit 1
  }
  python3 - "$path" <<'PY'
from pathlib import Path
import re
import sys
from urllib.parse import unquote

path = Path(sys.argv[1])
headings = []
prose_lines = []
fence = None
for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    stripped = line.lstrip()
    if fence:
        if stripped.startswith(fence):
            fence = None
        continue
    if stripped.startswith("```"):
        fence = "```"
        continue
    if stripped.startswith("~~~"):
        fence = "~~~"
        continue
    prose_lines.append(line)
    level = len(stripped) - len(stripped.lstrip("#"))
    if 1 <= level <= 6 and len(stripped) > level and stripped[level] == " ":
        headings.append((line_number, level))

if not headings or headings[0][1] != 1:
    raise SystemExit(f"error: Markdown source must begin its heading structure with H1: {path}")
h1_lines = [line for line, level in headings if level == 1]
if len(h1_lines) != 1:
    raise SystemExit(
        f"error: Markdown source must contain exactly one H1, found {len(h1_lines)}: {path}"
    )
previous_level = headings[0][1]
for line_number, level in headings[1:]:
    if level > previous_level + 1:
        raise SystemExit(
            f"error: Markdown heading skips from H{previous_level} to H{level} "
            f"at line {line_number}: {path}"
        )
    previous_level = level

for match in re.finditer(r"\[[^]]+\]\(([^)]+)\)", "\n".join(prose_lines)):
    raw_target = match.group(1).strip()
    if raw_target.startswith("<") and ">" in raw_target:
        target = raw_target[1:raw_target.index(">")]
    else:
        target = raw_target.split(maxsplit=1)[0]
    if not target or target.startswith(("#", "http://", "https://", "mailto:")):
        continue
    target_path = target.split("#", 1)[0].split("?", 1)[0]
    if not target_path:
        continue
    resolved = (path.parent / target_path).resolve()
    if not resolved.exists():
        raise SystemExit(f"error: Markdown link target does not exist: {target} in {path}")
    if "#" in target and resolved.suffix.lower() == ".md":
        fragment = unquote(target.split("#", 1)[1])
        identifiers = set()
        identifier_counts = {}
        target_fence = None
        for target_line in resolved.read_text(encoding="utf-8").splitlines():
            target_stripped = target_line.lstrip()
            if target_fence:
                if target_stripped.startswith(target_fence):
                    target_fence = None
                continue
            if target_stripped.startswith("```"):
                target_fence = "```"
                continue
            if target_stripped.startswith("~~~"):
                target_fence = "~~~"
                continue
            target_level = len(target_stripped) - len(target_stripped.lstrip("#"))
            if not (
                1 <= target_level <= 6
                and len(target_stripped) > target_level
                and target_stripped[target_level] == " "
            ):
                continue
            heading_text = target_stripped[target_level + 1:].strip().rstrip("#").strip()
            identifier = re.sub(r"[^\w\s-]", "", heading_text.casefold())
            identifier = re.sub(r"\s+", "-", identifier)
            count = identifier_counts.get(identifier, 0)
            identifier_counts[identifier] = count + 1
            identifiers.add(identifier if count == 0 else f"{identifier}-{count}")
        if fragment not in identifiers:
            raise SystemExit(
                f"error: Markdown link has a missing heading target: {target} in {path}"
            )
PY
}

for source in "${quick_sources[@]}" "${handbook_sources[@]}" "${developer_sources[@]}" \
  "${developer_archive_sources[@]}" "${human_testing_sources[@]}" \
  "${quick_en_sources[@]}" "${handbook_en_sources[@]}" \
  "${developer_en_sources[@]}" "${developer_en_archive_sources[@]}" \
  "${human_testing_en_sources[@]}"; do
  validate_source "$source"
done

python3 - "$root/docs/de/manual" "$root/docs/en/manual" \
  "$root/docs/de/development" "$root/docs/en/development" <<'PY'
from pathlib import Path
import sys

def heading_levels(path):
    levels = []
    fence = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if fence:
            if stripped.startswith(fence):
                fence = None
            continue
        if stripped.startswith("```"):
            fence = "```"
            continue
        if stripped.startswith("~~~"):
            fence = "~~~"
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if 1 <= level <= 6 and len(stripped) > level and stripped[level] == " ":
            levels.append(level)
    return levels

def validate_mirror(de_directory, en_directory, label):
    de_names = {
        path.relative_to(de_directory)
        for path in de_directory.rglob("*.md")
    }
    en_names = {
        path.relative_to(en_directory)
        for path in en_directory.rglob("*.md")
    }
    if de_names != en_names:
        missing_en = sorted(str(path) for path in de_names - en_names)
        missing_de = sorted(str(path) for path in en_names - de_names)
        raise SystemExit(
            f"error: German and English {label} source sets differ; "
            f"missing English={missing_en}, missing German={missing_de}"
        )
    for name in sorted(de_names):
        de_levels = heading_levels(de_directory / name)
        en_levels = heading_levels(en_directory / name)
        if de_levels != en_levels:
            raise SystemExit(
                f"error: German and English {label} heading structures differ: {name}"
            )

validate_mirror(Path(sys.argv[1]), Path(sys.argv[2]), "manual")
validate_mirror(Path(sys.argv[3]), Path(sys.argv[4]), "developer")
PY

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
for source in "${developer_sources[@]}" "${developer_archive_sources[@]}" \
  "${human_testing_sources[@]}"; do
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
for source in "${developer_en_sources[@]}" "${developer_en_archive_sources[@]}" \
  "${human_testing_en_sources[@]}"; do
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
  python3 - "$output" <<'PY'
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import urlsplit

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.references = set()
        self.targets = set()

    def handle_starttag(self, _tag, attributes):
        values = dict(attributes)
        if "id" in values:
            self.ids.add(values["id"])
        target = values.get("href", "")
        if target:
            self.targets.add(target)
        if target.startswith("#"):
            self.references.add(target[1:])

links = Links()
links.feed(Path(sys.argv[1]).read_text(encoding="utf-8"))
missing = sorted(links.references - links.ids)
if missing:
    raise SystemExit("error: generated HTML has missing internal targets: " + ", ".join(missing))
relative_markdown = sorted(
    target
    for target in links.targets
    if not urlsplit(target).scheme
    and urlsplit(target).path.lower().endswith(".md")
)
if relative_markdown:
    raise SystemExit(
        "error: generated HTML still contains links to Markdown sources: "
        + ", ".join(relative_markdown)
    )
PY

  local h1_count
  h1_count="$(grep -Eoc '<h1([ >])' "$output")"
  [[ "$h1_count" -eq 1 ]] || {
    echo "error: generated HTML must contain exactly one H1, found $h1_count: $output" >&2
    exit 1
  }
}

validate_required_section() {
  local output="$1"
  local section_id="$2"
  [[ "$(grep -Fc "id=\"$section_id\"" "$output")" -eq 1 ]] || {
    echo "error: generated HTML does not contain required section $section_id: $output" >&2
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
  elif [[ "$use_link_filter" == "quick" ]]; then
    extra+=(--lua-filter=docs/quick-links.lua)
  elif [[ "$use_link_filter" == "quick-en" ]]; then
    extra+=(--lua-filter=docs/quick-links-en.lua)
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
  "$quick_output" "$product_name – Quick Guide" quick \
  "${quick_sources[@]}"
build_html \
  "$handbook_output" "$product_name – Handbuch" yes \
  "${handbook_sources[@]}"
build_html \
  "$developer_output" "$product_name – Entwicklerdokumentation" development \
  "${developer_sources[@]}"
build_html \
  "$human_testing_output" "$product_name – Geführte Praxistests mit NVDA" no \
  "${human_testing_sources[@]}"
build_html \
  "$quick_en_output" "$product_name – Quick Guide" quick-en \
  "${quick_en_sources[@]}"
build_html \
  "$handbook_en_output" "$product_name – User Manual" english \
  "${handbook_en_sources[@]}"
build_html \
  "$developer_en_output" "$product_name – Developer Documentation" english \
  "${developer_en_sources[@]}"
build_html \
  "$human_testing_en_output" "$product_name – Guided Practical Tests with NVDA" no \
  "${human_testing_en_sources[@]}"

python3 - "$quick_output" "$handbook_output" "$developer_output" \
  "$human_testing_output" "$quick_en_output" "$handbook_en_output" \
  "$developer_en_output" "$human_testing_en_output" <<'PY'
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys

class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, _tag, attributes):
        values = dict(attributes)
        if "id" in values:
            self.ids.add(values["id"])
        if "href" in values:
            self.links.append(values["href"])

documents = {}
for argument in sys.argv[1:]:
    path = Path(argument).resolve()
    document = Document()
    document.feed(path.read_text(encoding="utf-8"))
    documents[path] = document

for source, document in documents.items():
    for href in document.links:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (source.parent / unquote(parsed.path)).resolve()
        if target.suffix.lower() != ".html":
            continue
        if target not in documents:
            raise SystemExit(
                f"error: generated HTML links to a missing document: {href} in {source}"
            )
        if parsed.fragment and parsed.fragment not in documents[target].ids:
            raise SystemExit(
                f"error: generated HTML link has a missing target: {href} in {source}"
            )
PY

validate_required_section \
  "$handbook_output" \
  "docs__de__manual__language-toolsmd__lsp-autovervollständigung-und-linter-einrichten"
validate_required_section \
  "$handbook_output" \
  "docs__de__manual__basicsmd__neovim--und-windows-terminal-grundlagen"
validate_required_section \
  "$handbook_output" \
  "docs__de__manual__commandsmd__befehlsreferenz"
validate_required_section \
  "$handbook_output" \
  "docs__de__manual__example-configurationmd__kleine-python-konfiguration-mit-lazy-und-oil"
validate_required_section \
  "$handbook_output" \
  "docs__de__manual__braillemd__braille-unterstützung"
validate_required_section \
  "$handbook_output" \
  "docs__de__manual__speech-explorationmd__sprachexplorationsmodus"
validate_required_section \
  "$handbook_en_output" \
  "docs__en__manual__language-toolsmd__setting-up-lsp-completion-and-linters"
validate_required_section \
  "$handbook_en_output" \
  "docs__en__manual__basicsmd__neovim-and-windows-terminal-basics"
validate_required_section \
  "$handbook_en_output" \
  "docs__en__manual__commandsmd__command-reference"
validate_required_section \
  "$handbook_en_output" \
  "docs__en__manual__example-configurationmd__small-python-configuration-with-lazy-and-oil"
validate_required_section \
  "$handbook_en_output" \
  "docs__en__manual__braillemd__braille-support"
validate_required_section \
  "$handbook_en_output" \
  "docs__en__manual__speech-explorationmd__speech-exploration-mode"
validate_required_section \
  "$human_testing_output" \
  "geführte-praxistests-mit-nvda"
validate_required_section \
  "$human_testing_en_output" \
  "guided-practical-tests-with-nvda"

mkdir -p "$archive_dir"
published_outputs=(
  "$quick_output"
  "$handbook_output"
  "$developer_output"
  "$human_testing_output"
  "$quick_en_output"
  "$handbook_en_output"
  "$developer_en_output"
  "$human_testing_en_output"
)
python3 - "$documentation_archive" "${published_outputs[@]}" <<'PY'
from pathlib import Path
import sys
import zipfile

output = Path(sys.argv[1])
sources = [Path(value) for value in sys.argv[2:]]
staged = output.with_name(f".{output.name}.tmp")
with zipfile.ZipFile(
    staged,
    "w",
    compression=zipfile.ZIP_DEFLATED,
    compresslevel=9,
) as archive:
    for source in sources:
        info = zipfile.ZipInfo(source.name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, source.read_bytes(), compresslevel=9)
staged.replace(output)
output.chmod(0o644)
PY
echo "built $documentation_archive ($(wc -c < "$documentation_archive") bytes) from ${#published_outputs[@]} HTML files"
