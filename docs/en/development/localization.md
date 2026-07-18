# Localization with gettext

Neovim Access Link uses NVDA's public add-on localization mechanism. Each
Python module containing translatable NVDA text calls
`addonHandler.initTranslation()`; NVDA then loads gettext domain `nvda` from
`locale/<language>/LC_MESSAGES/nvda.mo`. A missing catalog or entry deliberately
falls back to the English source text.

The NVDA-independent speech planner imports neither NVDA nor gettext. Its
constructor only receives the active translation callable. Without that
callback it remains English and independently testable. Visible dialog,
status, and speech templates are marked by literal `_()`, `self._translate()`,
or `translatable()` calls. Protocol values, document contents, names, paths,
and messages originating in Neovim or third-party tools are not translated.

## Files and workflow

- `nvda-addon/locale/NeovimAccessLink.pot` is the extracted template.
- `nvda-addon/locale/de/LC_MESSAGES/nvda.po` is the German source catalog.
- `nvda-addon/locale/de/manifest.ini` localizes manifest fields which NVDA may
  display before Python code is loaded.
- The `.nvda-addon` contains only `locale/de/LC_MESSAGES/nvda.mo` and the
  translated manifest, never PO or POT sources.

After changing visible text, run from the repository root:

```bash
python3 tools/gettext_catalog.py update
python3 tools/gettext_catalog.py check
python3 tools/build_nvda_addon.py
```

`update` extracts literal messages only and preserves existing translations.
`check` requires exactly one PO entry for each source message, rejects obsolete
entries, and compares named Python format placeholders. Untranslated entries
are allowed and intentionally fall back to English. The MO compiler omits them
from the binary just like GNU `msgfmt`; an empty translation must never remove
visible text. The build compiles catalogs deterministically with the Python
standard library, so GNU gettext tools are not a build dependency.

The initial tool handles singular messages with named `str.format` fields.
True plural forms (`ngettext`) and contextual translations (`pgettext`) will
be introduced when source messages require them; until then these calls must
not be used in the extracted modules.

Automated tests load the resulting MO with `gettext.GNUTranslations`, compare
reproducible bytes, and inspect the actual built archive. Practical acceptance
must cover NVDA in English and German, including dialogs, focus announcements,
mode changes, file and terminal buffers, and error/fail-open paths.
