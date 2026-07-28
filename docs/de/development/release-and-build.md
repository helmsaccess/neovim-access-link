# Release-, Versions- und Buildprozess

## Zentrale Metadaten

`buildVars.py` ist die einzige gepflegte Quelle für Produktidentität und
Versionsdaten. Die Datei folgt bewusst dem Namens- und Strukturmuster der
offiziellen NVDA-Add-on-Vorlage.

Enthalten sind:

- interner NVDA-Identifier `NeovimAccessLink`,
- sichtbarer Produktname „Neovim Access Link“,
- Autor Emanuel Helms `<emanuel@helmsaccess.de>`,
- bewusst festgelegte Produktversion,
- eine pro Featurebranch verwaltete Entwicklungsbuildnummer,
- bewusst festgelegter Releasekanal,
- minimale und zuletzt getestete NVDA-Version.

Seit dem Cleanup für 0.94 lautet der interne Identifier `NeovimAccessLink`.
Dieser Wechsel ist ein bewusster Schnitt: NVDA behandelt einen älteren Stand
mit der ID `nvimNvdaAccess` als anderes Add-on. Vor einem Praxistest muss der
alte Stand deshalb deinstalliert und NVDA neu gestartet werden. Einstellungen,
Profile und Gestenzuweisungen der alten ID werden nicht übernommen. Der
Identifier ist kein zweiter sichtbarer Produktname.

## Abgeleitete Werte

`buildVars.store_version()` liefert ausschließlich die in `buildVars.py`
eingetragene numerische Produktversion für `manifest.ini` und den NVDA Add-on
Store. `buildVars.development_version()` ergänzt für Entwicklungsstände eine
branchlokale SemVer-Kennung wie `1.2.3-dev.1` und nach Möglichkeit
Build-Metadaten aus Branch und Commit. `buildVars.artifact_version()` verwendet
diese vollständige Kennung für Pakete und Laufzeitdiagnosen. Der Store sieht
damit keine interne Buildnummer.

`development_build = None` kennzeichnet ausschließlich einen bewusst
freigegebenen Releasezustand. Dann entspricht auch die Artefaktversion der
normalen Produktversion. Der Wert darf nicht beiläufig aus Branchname,
Buildumgebung oder bisherigem Versionsverlauf abgeleitet werden.

Der Add-on-Builder erzeugt aus den zentralen Daten:

- `manifest.ini` im installierbaren Archiv,
- einen eindeutigen Archivnamen wie
  `NeovimAccessLink-1.2.3-dev.1+feature.example.<commit>.nvda-addon`,
- den sichtbaren Komponentenpaketnamen
  `neovim-access-link-1.2.3-dev.1+feature.example.<commit>-user.tar.gz`,
- die Laufzeitversion in Diagnosebericht und Log,
- die Version des gebündelten Linux-Komponentenpakets.

Das Quellverzeichnis enthält absichtlich kein separat gepflegtes Manifest mit
duplizierten Werten. Zur Laufzeit verwendet das Add-on die öffentliche
`addonHandler.getCodeAddon()`-Schnittstelle und liest sein von NVDA geladenes
Manifest.

## Versions- und Freigaberegeln

- Produktversion und Releasekanal werden als ausdrückliche
  Freigabeentscheidung festgelegt und nicht automatisch hergeleitet.
- Die Entwicklungsbuildnummer wird innerhalb des jeweiligen Branches erhöht,
  sobald sich der bereitgestellte installierbare Inhalt ändert.
- Ein neuer Featurebranch beginnt mit einer eigenen Buildfolge; Branch- und
  Commit-Metadaten verhindern Verwechslungen zwischen parallelen Branches.
- Ein unverändert reproduzierter Stand darf denselben Namen behalten.
- Tags, stabile Releases und Änderungen der Produktversion benötigen eine
  ausdrückliche Freigabeentscheidung.

Vor einem neuen Build werden alte Artefakte aus `dist/` entfernt. Anschließend
erzeugt `python3 tools/build_nvda_addon.py` das Add-on. Tests extrahieren das
tatsächliche Archiv und vergleichen Manifest, Dateiname und Laufzeitmetadaten
mit `buildVars.py`.

`tools/build_documentation.sh` erzeugt die deutschen und englischen Fassungen
von Quick Guide, Handbuch und Entwicklerdokumentation. Der Build prüft
ausdrücklich, dass beide Handbücher ihr Braille-Kapitel enthalten, und bündelt
alle sechs HTML-Dateien zusätzlich in genau einem versionierten
Dokumentations-ZIP unter `dist/`.

Das unveränderte GPL-v2-Lizenzdokument wird in das Add-on und das Paket der
Benutzerkomponenten aufgenommen. Einzelheiten zu Projekt- und
Beitragslizenzierung stehen unter [Lizenzierung und Beiträge](licensing-and-contributions.md).
