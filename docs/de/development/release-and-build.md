# Release-, Versions- und Buildprozess

## Zentrale Metadaten

`buildVars.py` ist die einzige gepflegte Quelle für Produktidentität und
Versionsdaten. Die Datei folgt bewusst dem Namens- und Strukturmuster der
offiziellen NVDA-Add-on-Vorlage.

Enthalten sind:

- interner NVDA-Identifier `nvimNvdaAccess`,
- sichtbarer Produktname „Neovim Access Link“,
- Autor Emanuel Helms `<emanuel@helmsaccess.de>`,
- vom Benutzer bestimmte Produktversion `0.89`,
- vom Coding Agent fortlaufend verwaltete Buildnummer,
- Releasekanal `beta`,
- minimale und zuletzt getestete NVDA-Version.

Der interne Identifier bleibt trotz des neuen sichtbaren Produktnamens stabil.
Dadurch erkennt NVDA einen Beta-Build als Aktualisierung der bisherigen
Testinstallation und behält profilbezogene Add-on-Einstellungen. Er ist kein
zweiter sichtbarer Produktname.

## Abgeleitete Werte

`buildVars.version()` verbindet Produktversion und Buildnummer. Der aktuelle
Beta-Testbuild lautet daher `0.89.5`. Dieses rein numerische Dreierformat
entspricht der Validierung des NVDA Add-on Store und bleibt korrekt sortierbar.

Der Add-on-Builder erzeugt aus den zentralen Daten:

- `manifest.ini` im installierbaren Archiv,
- den Archivnamen `nvimNvdaAccess-0.89.5.nvda-addon`,
- den sichtbaren Komponentenpaketnamen
  `neovim-access-link-0.89.5-user.tar.gz`,
- die Laufzeitversion in Diagnosebericht und Log,
- die Version des gebündelten Linux-Komponentenpakets.

Das Quellverzeichnis enthält absichtlich kein separat gepflegtes Manifest mit
duplizierten Werten. Zur Laufzeit verwendet das Add-on die öffentliche
`addonHandler.getCodeAddon()`-Schnittstelle und liest sein von NVDA geladenes
Manifest.

## Zuständigkeiten

- Der Benutzer bestimmt Produktversion und Releasekanal.
- Der Coding Agent erhöht nur die Buildnummer, sobald sich installierbarer
  Inhalt seit dem letzten bereitgestellten Build geändert hat.
- Ein unverändert reproduzierter Stand darf denselben Namen behalten.
- Tags, stabile Releases und Änderungen der Produktversion benötigen eine
  ausdrückliche Freigabe des Benutzers.

Vor einem neuen Build werden alte Artefakte aus `dist/` entfernt. Anschließend
erzeugt `python3 tools/build_nvda_addon.py` das Add-on. Tests extrahieren das
tatsächliche Archiv und vergleichen Manifest, Dateiname und Laufzeitmetadaten
mit `buildVars.py`.

Das unveränderte GPL-v2-Lizenzdokument wird in das Add-on und das Paket der
Benutzerkomponenten aufgenommen. Einzelheiten zu Projekt- und
Beitragslizenzierung stehen unter [Lizenzierung und Beiträge](licensing-and-contributions.md).
