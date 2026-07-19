from __future__ import annotations

import gettext
import pathlib
import tempfile
import unittest

from tools.gettext_catalog import (
    POT_PATH,
    PRODUCT_NAME,
    compile_mo,
    extract_messages,
    parse_po,
    render_catalog,
    update_catalog,
    validate_catalog,
    validate_template,
    validate_translation,
)


ROOT = pathlib.Path(__file__).resolve().parents[2]
GERMAN_PO = ROOT / "nvda-addon" / "locale" / "de" / "LC_MESSAGES" / "nvda.po"
NVDA_TRANSLATION_MODULES = (
    ROOT / "nvda-addon" / "addon" / "globalPlugins" / "NeovimAccessLink" / "__init__.py",
    ROOT / "nvda-addon" / "addon" / "globalPlugins" / "NeovimAccessLink" / "nvda_ui.py",
    ROOT / "nvda-addon" / "addon" / "appModules" / "windowsterminal.py",
)


class GettextCatalogTests(unittest.TestCase):
    def test_template_and_german_catalog_match_extracted_source(self) -> None:
        validate_template()
        source = set(extract_messages())
        template, _header = parse_po(POT_PATH)
        german = validate_catalog(GERMAN_PO, require_complete=True)
        self.assertEqual(source, set(template))
        self.assertEqual(source, set(german) - {""})

    def test_german_catalog_translates_ui_and_semantic_speech(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mo_path = pathlib.Path(temporary) / "nvda.mo"
            compile_mo(GERMAN_PO, mo_path)
            with mo_path.open("rb") as stream:
                translations = gettext.GNUTranslations(stream)
        self.assertEqual("Verbindungen", translations.gettext("Connections"))
        self.assertEqual("Normalmodus", translations.gettext("normal mode"))
        self.assertEqual(
            "Lokale Neovim-Sitzungen konnten nicht aufgelistet werden",
            translations.gettext("Could not list local Neovim sessions"),
        )
        self.assertEqual(
            "Treffer 2 von 4",
            translations.gettext("match {index} of {count}").format(index=2, count=4),
        )

    def test_nvda_modules_initialize_their_gettext_builtins(self) -> None:
        for path in NVDA_TRANSLATION_MODULES:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIn("addonHandler.initTranslation()", source)

    def test_compilation_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            first = root / "first.mo"
            second = root / "second.mo"
            compile_mo(GERMAN_PO, first)
            compile_mo(GERMAN_PO, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_untranslated_entries_are_omitted_for_english_fallback(self) -> None:
        translations, header = parse_po(GERMAN_PO)
        messages = extract_messages()
        for msgid, message in messages.items():
            message.msgstr = translations[msgid]
        fallback_message = "Could not list local Neovim sessions"
        messages[fallback_message].msgstr = ""
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            po_path = root / "nvda.po"
            mo_path = root / "nvda.mo"
            po_path.write_text(
                render_catalog(
                    messages,
                    language="de",
                    include_translations=True,
                    header=header,
                ),
                encoding="utf-8",
            )
            compile_mo(po_path, mo_path)
            with mo_path.open("rb") as stream:
                compiled = gettext.GNUTranslations(stream)
        self.assertEqual(fallback_message, compiled.gettext(fallback_message))

    def test_translation_must_preserve_named_placeholders(self) -> None:
        with self.assertRaisesRegex(ValueError, "placeholders differ"):
            validate_translation("{name} connected", "{server} verbunden")

    def test_catalog_update_preserves_translator_metadata(self) -> None:
        custom_header = (
            f"Project-Id-Version: {PRODUCT_NAME}\n"
            "Last-Translator: Example Translator\n"
            "Language: de\n"
            "Content-Type: text/plain; charset=UTF-8\n"
        )
        messages = extract_messages()
        messages["Connections"].msgstr = "Verbindungen"
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "nvda.po"
            path.write_text(
                render_catalog(
                    messages,
                    language="de",
                    include_translations=True,
                    header=custom_header,
                ),
                encoding="utf-8",
            )
            update_catalog(path, language="de")
            translations, header = parse_po(path)
        self.assertIn("Last-Translator: Example Translator", header)
        self.assertEqual("Verbindungen", translations["Connections"])


if __name__ == "__main__":
    unittest.main()
