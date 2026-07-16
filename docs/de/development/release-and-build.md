# Release-, Versions- und Buildprozess

## Zentrale Metadaten

`buildVars.py` ist die einzige gepflegte Quelle für Produktidentität und
Versionsdaten. Die Datei folgt bewusst dem Namens- und Strukturmuster der
offiziellen NVDA-Add-on-Vorlage.

Enthalten sind:

- interner NVDA-Identifier `nvimNvdaAccess`,
- sichtbarer Produktname „Neovim Access Link“,
- Autor Emanuel Helms `<emanuel@helmsaccess.de>`,
- vom Benutzer bestimmte Produktversion `0.92.0`,
- eine pro Featurebranch verwaltete Entwicklungsbuildnummer,
- Releasekanal `beta`,
- minimale und zuletzt getestete NVDA-Version.

Der interne Identifier bleibt trotz des neuen sichtbaren Produktnamens stabil.
Dadurch erkennt NVDA einen Beta-Build als Aktualisierung der bisherigen
Testinstallation und behält profilbezogene Add-on-Einstellungen. Er ist kein
zweiter sichtbarer Produktname.

## Abgeleitete Werte

`buildVars.store_version()` liefert ausschließlich die normale numerische
Produktversion `0.92.0` für `manifest.ini` und den NVDA Add-on Store.
`buildVars.development_version()` ergänzt für Entwicklungsstände eine
branchlokale SemVer-Kennung wie `0.92.0-dev.1` und nach Möglichkeit
Build-Metadaten aus Branch und Commit. `buildVars.artifact_version()` verwendet
diese vollständige Kennung für Pakete und Laufzeitdiagnosen. Der Store sieht
damit keine interne Buildnummer.

`development_build = None` ist ausschließlich für ein vom Benutzer
freigegebenes Release vorgesehen. Dann entspricht auch die Artefaktversion der
normalen Produktversion. Coding Agents dürfen diesen Wechsel nicht selbst als
Stabilitäts- oder Releaseentscheidung vornehmen.

Der Add-on-Builder erzeugt aus den zentralen Daten:

- `manifest.ini` im installierbaren Archiv,
- einen eindeutigen Archivnamen wie
  `nvimNvdaAccess-0.92.0-dev.1+feature.example.<commit>.nvda-addon`,
- den sichtbaren Komponentenpaketnamen
  `neovim-access-link-0.92.0-dev.1+feature.example.<commit>-user.tar.gz`,
- die Laufzeitversion in Diagnosebericht und Log,
- die Version des gebündelten Linux-Komponentenpakets.

Das Quellverzeichnis enthält absichtlich kein separat gepflegtes Manifest mit
duplizierten Werten. Zur Laufzeit verwendet das Add-on die öffentliche
`addonHandler.getCodeAddon()`-Schnittstelle und liest sein von NVDA geladenes
Manifest.

## Zuständigkeiten

- Der Benutzer bestimmt Produktversion und Releasekanal.
- Der Coding Agent erhöht die Entwicklungsbuildnummer innerhalb des jeweiligen
  Branches, sobald sich der bereitgestellte installierbare Inhalt ändert.
- Ein neuer Featurebranch beginnt mit einer eigenen Buildfolge; Branch- und
  Commit-Metadaten verhindern Verwechslungen zwischen parallelen Branches.
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
