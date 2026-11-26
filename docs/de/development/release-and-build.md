# Release-, Versions- und Buildprozess

## Zentrale Metadaten

`buildVars.py` ist die einzige gepflegte Quelle für Produktidentität und
Versionsdaten. Sie enthält:

- internen Add-on-Identifier und sichtbaren Produktnamen;
- Autor, numerische Produktversion und Manifest-Update-Kanal;
- branchlokale Entwicklungsbuildnummer;
- Vergleichsversion des zuletzt im NVDA Add-on Store veröffentlichten Stands;
- minimale und zuletzt getestete NVDA-Version;
- Projektadresse, Standardhilfedatei und englisches Manifest-Changelog.
- Quelladresse, Lizenzkennung und Lizenzadresse für den NVDA Add-on Store.

`store_version()` liefert ausschließlich `MAJOR.MINOR.PATCH` für Manifest und
NVDA Add-on Store. `artifact_version()` ergänzt bei Entwicklungsständen
`-dev.N` sowie nach Möglichkeit Branch- und Commitmetadaten für Dateinamen,
Diagnosebericht und gebündelte Komponenten. Das installierte Manifest wird
beim Build aus diesen Werten und den passenden Changelogabschnitten erzeugt
und nicht separat gepflegt. Das deutsche Lokalisierungsmanifest erhält
dieselben Abschnitte aus dem deutschen Changelog. Bei einem Release verbindet
`manifest_changelog()` alle Versionsabschnitte nach
`manifest_changelog_base_version` bis einschließlich der aktuellen Version.
Damit beschreibt das Store-Manifest genau das Upgrade vom zuletzt dort
veröffentlichten Stand; die Vergleichsversion wird nach einer tatsächlichen
Store-Veröffentlichung für den nächsten Release aktualisiert.

Entwicklungsstände sammeln abgeschlossene Änderungen unter `Unveröffentlicht`
beziehungsweise `Unreleased`; ihre Manifeste verwenden diesen Abschnitt. Bei
der Release-Festlegung werden die Einträge redaktionell in den neuen deutschen
und englischen Versionsabschnitt übernommen. Dieser beschreibt nur Änderungen
seit der unmittelbar vorherigen veröffentlichten Version und zurückgesetztem unveröffentlichtem Abschnitt; anschließend bleiben
die unveröffentlichten Abschnitte für die nächste Entwicklungslinie leer. Der
Build wählt den Abschnitt aus, verändert aber keine Changelog-Quelle.

## Entwicklungsstände

`development_build` ist auf Featurebranches eine positive Ganzzahl. Der erste
geänderte installierbare Stand eines neuen Branches verwendet `1`; weitere
Änderungen an installierbarem Inhalt erhöhen den Wert innerhalb dieses
Branches. Ein unverändert reproduzierter Stand darf denselben Wert verwenden.

`development_build = None` kennzeichnet ausschließlich einen ausdrücklich
freigegebenen Releasezustand. Produktversion, Kanal, Tag und Pre-Release-Status
werden nicht aus Branchname oder bisherigem Verlauf abgeleitet.

## Prüfung und Build

Entwickelt wird im lokalen Windows-Checkout. Linux deckt zusätzlich Unix-Sockets,
PTY und SSH-Zielsysteme ab. Tests und Dokumentationsprüfungen verwenden temporäre
Ausgaben:

```bash
python3 tools/run_tests.py all
bash tools/build_documentation.sh --test-only
```

`all` führt sichere, SSH- und Socketphasen nacheinander aus; die Umgebung muss
Listener und kurzlebige Neovim-Prozesse erlauben. In eingeschränkten
Umgebungen werden `all-safe`, `ssh` und `socket` entsprechend der
[Teststrategie](testing.md) getrennt ausgeführt.

Der Build folgt dem offiziellen NVDA-AddonTemplate mit `sconstruct`, getrennten
Vorlagen für das Basismanifest und übersetzte Manifeste, dem Ziel `pot` und
Gettext-Katalogen unter `nvda-addon/addon/locale/`. Ein direkter Aufruf von
`python -m SCons` erzeugt ein Prüfarchiv unter `build/scons/` mit den im Checkout
vorhandenen HTML-Dateien. `build.cmd` und der Linux-Releasebuilder übergeben
SCons frisch gerenderte Dokumentation und halten ihre Zwischendateien getrennt.
[NVDA AddonTemplate](https://github.com/nvdaaddons/AddonTemplate/tree/30318eae085fa81fe3a39045956c7a0516a0f981)

Pakettests bauen das Add-on in ihrem temporären Testverzeichnis und prüfen
Manifest, acht installierte lokalisierte HTML-Dokumente,
gebündelte Komponenten, Abhängigkeiten und Archivinhalt. Der
Manifestvertrag folgt der Feldmenge des offiziellen NVDA-AddonTemplates:
Alle zutreffenden Felder müssen als getrimmte Skalare vorliegen; unbekannte,
leere oder fehlerhaft formatierte Angaben, eine fehlende englische
Standardhilfe und unvollständige Lokalisierungsmanifeste brechen den Build ab.
Ein Feld darf nur entfallen, wenn es für das Projekt tatsächlich nicht
zutrifft. Die temporäre Dokumentationsprüfung synchronisiert ausführbare Beispiele,
prüft Markdown- und HTML-Links, die deutsche und englische Struktur sowie
Sprache, Titel und Beschreibung der Ausgabedateien und erzeugt acht
HTML-Dokumente, bevor sie wieder gelöscht werden. CI veröffentlicht oder
aktualisiert dabei keine Endanwenderartefakte.

Normale Entwicklungsartefakte entstehen mit dem parameterlosen `build.cmd`
aus einem sauberen, lokal ausgecheckten Windows-Branch mit Entwicklungsbuildnummer.
Python 3, Git Bash und eine Internetverbindung für die gepinnten
Python-Abhängigkeiten werden benötigt. Git Bash über `PATH`, die
Standardinstallation von Git für Windows oder `NAL_GIT_BASH` bereitstellen.
Der Build verwendet ein lokales Pandoc 3.1.11.1 oder lädt den offiziellen
Windows-Binärbuild 3.1.11.1 temporär und prüft dessen SHA-256.

Windows-Entwicklungsbuild und Linux-Releasebuild rendern die acht HTML-Dateien
und verpacken sie über denselben isolierten Kern. Branch, Commit und Sauberkeit
der versionierten Dateien werden vor und nach dem Build geprüft. Erst danach
gelangen das Add-on und das Dokumentations-ZIP mit den erwarteten Namen nach
`dist`. Für den Abgleich mit einem vorhandenen Repository dient `git fetch origin`.

## Releasebuild auf Linux

Der endgültige, später getaggte und auf GitHub veröffentlichte Stand wird im
Linux-Checkout gebaut. Nach vollständiger Prüfung, der Freigabe der
Release-Metadaten und dem Merge auf `main` wird ausgeführt:

```bash
python3 tools/build_release.py
```

Der parameterlose Befehl akzeptiert ausschließlich einen sauberen
`main`-Worktree mit `development_build = None`. Er lädt den offiziellen
Pandoc-3.1.11.1-Linux-Binärbuild in ein temporäres Verzeichnis, prüft dessen
SHA-256 und verwendet wie der Windows-Einstiegspunkt eine temporäre
Python-Umgebung mit den festgelegten Buildabhängigkeiten. Vor und nach dem
Build werden Branch, Commit und versionierte Sauberkeit verglichen. Nur das
Add-on und das Dokumentations-ZIP des unveränderten Stands gelangen nach
`dist`; Pandoc, Umgebung und Zwischenprodukte werden anschließend entfernt.

Im Windows-Worktree heißen die beiden Dateien
`NeovimAccessLink-<artifact_version>.nvda-addon` und
`neovim-access-link-<artifact_version>-documentation.zip`; bei einem
Entwicklungsstand enthält `<artifact_version>` `-dev.N` sowie nach Möglichkeit
Branch- und Commitmetadaten. Der Linux-Releasebuild verwendet dagegen die
reine Produktversion, beispielsweise `NeovimAccessLink-0.99.0.nvda-addon`.

Der erfolgreiche Build verändert keine versionierte Datei. Anschließend wird
genau sein `HEAD` als `vMAJOR.MINOR.PATCH` getaggt, Commit und Tag werden nach
Freigabe gepusht und die beiden Dateien aus dem Linux-`dist` mit
`gh release create --verify-tag` veröffentlicht. `build.cmd` ist kein
Releaseursprung, sondern erzeugt vorab die entsprechenden versionierten
Entwicklungsartefakte für die praktische Windows-Prüfung.

## Releasevorbereitung

Eine freigegebene Version benötigt in einem gemeinsamen, nachvollziehbaren
Stand:

1. Produktversion, Manifest-Update-Kanal,
   `manifest_changelog_base_version` und `development_build = None` in
   `buildVars.py`;
2. aktuellen Release- und Changeloglink in `README.md` sowie einen aus den
   unveröffentlichten Einträgen redaktionell erstellten deutschen und
   englischen Versionsabschnitt mit allen Änderungen seit der unmittelbar
   vorherigen veröffentlichten Version und zurückgesetztem unveröffentlichtem Abschnitt;
3. aktuellen Status, kompatible Metadaten und vollständige Deutsch/Englisch-
   Dokumentation;
4. erfolgreiche vollständige Tests und mit `tools/build_release.py` frisch
   aus diesem Linux-Stand gebaute Artefakte;
5. einen Commit und ein annotiertes oder leichtgewichtiges Tag `vMAJOR.MINOR.PATCH`
   auf genau diesem Commit.

Push, Tag und GitHub-Veröffentlichung erfolgen nur nach ausdrücklicher
Freigabe. Vor dem Tag wird geprüft, dass Worktree, Version, README-Links und
Artefaktnamen zusammenpassen.

## Abbruchbedingungen

Die Freigabe wird vor Tag oder Veröffentlichung abgebrochen, wenn Tests oder
Builds fehlschlagen, der Worktree unerwartete Änderungen enthält, Version und
Links nicht zusammenpassen, ein Artefakt nicht aus dem getaggten Stand stammt
oder eine erforderliche praktische Prüfung offen ist. Ein vorhandener Tag wird
nicht still verschoben; eine Korrektur erhält nach Entscheidung des Nutzers
eine neue Produktversion oder einen ausdrücklich neu aufgebauten, noch nicht
veröffentlichten Tag.

## GitHub und Add-on Store

Nach ausdrücklicher Freigabe den vorbereiteten Release-Commit auf sauberem
Linux-`main` bauen und Commit sowie vorhandenes Tag zuerst zu GitHub pushen.
Vor der Veröffentlichung die gebauten Basis- und Lokalmanifeste gegen das
aktuelle offizielle NVDA AddonTemplate prüfen. Jedes zutreffende Feld muss
gültig und befüllt sein. Die englischen Versionshinweise fassen die Änderungen
seit der letzten veröffentlichten Version zusammen, nennen Prüf- und
Kompatibilitätsgrenzen, verlinken Dokumentation am Tag und erklären beide
Downloads. Die temporäre Datei liegt unter `../nal-aux/`.

```bash
gh release create "v<VERSION>" "dist/NeovimAccessLink-<VERSION>.nvda-addon" \
  "dist/neovim-access-link-<VERSION>-documentation.zip" \
  --repo helmsaccess/neovim-access-link --verify-tag --fail-on-no-commits \
  --title "Neovim Access Link <VERSION>" --notes-file "<RELEASE_NOTES_FILE>" <STATUS_FLAGS>
```

Für Versionen unter 1.0.0 gelten `--prerelease --latest=false`, ab 1.0.0
`--latest`. Das Serverpaket steckt bereits im Add-on. Danach Tagziel, Titel,
Entwurfs-, Pre-Release- und Latest-Status, Hinweise, die beiden Dateinamen und
deren Downloads prüfen.

Die Einreichung in den NVDA Add-on Store ist ein getrennter Vorgang im
Add-on-Datastore. Sie verweist auf einen bereits veröffentlichten,
unveränderlichen Stand und folgt dessen aktueller Einreichungsprüfung. Nach
einer Store-Einreichung werden Tag und Assets nicht ersetzt; eine Korrektur
erhält eine neue Produktversion.

## Veröffentlichungsartefakte

Eine GitHub-Veröffentlichung enthält genau zwei herunterladbare Dateien:

- `NeovimAccessLink-<version>.nvda-addon`;
- `neovim-access-link-<version>-documentation.zip` mit Quick Guide, Handbuch,
  Entwicklerdokumentation und geführten Praxistests in Deutsch und Englisch.

Die Releasebeschreibung fasst die Änderungen seit der vorherigen
Produktversion zusammen, nennt wichtige Grenzen und verlinkt bei Bedarf eine
dauerhafte technische Analyse. Release- und Zusammenarbeitstext ist Englisch.

Die unveränderte GPL-v2-Lizenz wird in Add-on und Benutzerkomponentenpaket
aufgenommen. Weitere Angaben stehen unter
[Lizenzierung und Beiträge](licensing-and-contributions.md) und
[Abhängigkeiten](dependencies.md).
