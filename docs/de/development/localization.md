# Lokalisierung mit gettext

Neovim Access Link verwendet NVDAs öffentliche Add-on-Lokalisierung. Jedes
Python-Modul mit übersetzbaren NVDA-Texten ruft
`addonHandler.initTranslation()` auf; NVDA lädt anschließend die gettext-Domain
`nvda` aus `locale/<Sprache>/LC_MESSAGES/nvda.mo`. Fehlt ein Eintrag oder ein
Katalog, bleibt der englische Quelltext erhalten.

Die NVDA-unabhängige Speech-Planung importiert weder NVDA noch gettext. Sie
erhält beim Erzeugen des `SpeechPlanner` lediglich die aktive Übersetzungsfunktion.
Ohne Callback bleibt sie identisch englisch und separat testbar. Sichtbare
Dialog-, Status- und Sprachtemplates werden als literale `_()`,
`self._translate()` oder `translatable()`-Aufrufe markiert. Protokollwerte,
Dateiinhalte, Namen, Pfade und fremde Neovim-Meldungen werden nicht übersetzt.

## Dateien und Arbeitsablauf

- `nvda-addon/locale/NeovimAccessLink.pot` ist die extrahierte Vorlage.
- `nvda-addon/locale/de/LC_MESSAGES/nvda.po` ist der deutsche Quellkatalog.
- `nvda-addon/locale/de/manifest.ini` lokalisiert die von NVDA vor dem Laden
  des Python-Codes angezeigten Manifestfelder.
- Das `.nvda-addon` enthält nur `locale/de/LC_MESSAGES/nvda.mo` und das
  übersetzte Manifest, nicht PO oder POT.

Nach Änderungen sichtbarer Texte ist aus der Repositorywurzel auszuführen:

```bash
python3 tools/gettext_catalog.py update
python3 tools/gettext_catalog.py check
python3 tools/build_nvda_addon.py
```

`update` extrahiert ausschließlich literale Nachrichten und erhält vorhandene
Übersetzungen. `check` verlangt für jeden Quelltext genau einen PO-Eintrag,
weist veraltete Einträge ab und vergleicht benannte Python-Formatplatzhalter.
Unübersetzte Einträge sind zulässig und fallen absichtlich auf Englisch
zurück. Der MO-Compiler lässt sie dafür wie GNU `msgfmt` aus der Binärdatei
weg; eine leere Übersetzung darf niemals einen sichtbaren Text entfernen. Der
Build kompiliert deterministisch mit der Python-Standardbibliothek;
GNU-gettext-Werkzeuge sind keine Buildabhängigkeit.

Der erste Werkzeugstand verarbeitet einfache Nachrichten mit benannten
`str.format`-Feldern. Echte Pluralformen (`ngettext`) und kontextabhängige
Übersetzungen (`pgettext`) werden erst eingeführt, wenn Quelltexte sie
benötigen; bis dahin dürfen diese Aufrufe nicht in den extrahierten Modulen
verwendet werden.

Automatisierte Tests laden das erzeugte MO mit `gettext.GNUTranslations`,
prüfen reproduzierbare Bytes und untersuchen das tatsächlich gebaute Archiv.
Die praktische Abnahme muss NVDA einmal auf Englisch und einmal auf Deutsch
umfassen, einschließlich Dialogen, Fokusansage, Moduswechsel, Datei- und
Terminalpuffern sowie Fehler-/Fail-open-Pfaden.
