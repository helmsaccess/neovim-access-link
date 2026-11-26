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
dieselben Abschnitte aus dem deutschen Changelog. `manifest_changelog()` verbindet bei einem Release die Abschnitte nach
`manifest_changelog_base_version` bis zur aktuellen Version. Die Basis im
Store für den vorgesehenen Upgrade-Pfad prüfen. Bei stabilen Releases zählt
die vorige stabile Store-Version, auch wenn eine neuere Beta existiert.
Für den ersten stabilen Release die älteste veröffentlichte Version wählen,
für die der vorgesehene Upgrade-Pfad gilt. Relevante Änderungen aus
zwischenzeitlichen Betas und reinen GitHub-Releases einbeziehen.

## Regeln für Version und Changelog

Produktversionen folgen [SemVer](https://semver.org/spec/v2.0.0.html).
PATCH steht für kompatible Korrekturen und MINOR für kompatible Funktionen
und angekündigte Abkündigungen. Ab 1.0.0 steht MAJOR für Brüche zugesagter
Kompatibilität, etwa bei unterstützten Plattformen, dauerhaft gespeicherten
Einstellungen oder dem Protokoll zwischen separat aktualisierbaren Komponenten.
Vor 1.0.0 einen bewussten Kompatibilitätsbruch mit MINOR kennzeichnen und in
den Release Notes erläutern. Vor der Freigabe von 1.0.0 unterstützte
Versionen und Upgrade-Verhalten festlegen.

Der Nutzer gibt Produktversion und Kanal frei. Die numerische Version muss
über alle Kanäle hinweg eindeutig sein. Vor der Freigabe Git-Tags,
GitHub-Releases und Einträge im NVDA Store abgleichen.
[Versions- und Kanalregeln des NVDA Stores](https://github.com/nvaccess/addon-datastore/blob/master/docs/design/jsonMetadata.md)

Relevante Änderungen im selben Stand in beide Changelogs unter
`Unveröffentlicht` und `Unreleased` aufnehmen. Auswirkungen beschreiben und
bei Bedarf nach Neu, Geändert, Veraltet, Entfernt, Behoben und Sicherheit
gliedern. Zum Release die Änderungen seit dem vorigen Release derselben
Linie unter `## [X.Y.Z] - YYYY-MM-DD` zusammenfassen, die Version mit ihrem
Tag verlinken und beide unveröffentlichten Abschnitte leeren. Ein leerer
Abschnitt ergibt einen lokalisierten Hinweis in Entwicklungsmanifesten.
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

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

Ein erfolgreicher Build verändert keine versionierte Datei. Lokale
Windows-Entwicklungsartefakte aus `build.cmd` in isolierten NVDA-Profilen
testen. Der Build-Zusatz unterscheidet Pakete und Diagnoseausgaben. NVDA
sieht die numerische Manifestversion, daher benötigen Upgradetests
unterschiedliche numerische Versionen.

## Releasevorbereitung

1. Den Release in einem GitHub-Pull-Request gegen `main` vorbereiten.
   Freigegebene Version, Kanal, Store-Basis und `development_build = None`
   in `buildVars.py` setzen. Die minimale NVDA-API entspricht der
   Support-Untergrenze. Die zuletzt getestete API richtet sich nach
   erfolgreichen Tests. Stabile Releases benötigen eine stabile NVDA-API.
2. Beide Changelogs, die Release-Links im README und die deutschen und
   englischen Status- und Kompatibilitätsseiten abschließen. Den PR nach
   Freigabe und erfolgreichen erforderlichen Prüfungen zusammenführen.
3. Aus sauberem Linux-`main` am gemergten Commit die vollständigen Tests
   und `python3 tools/build_release.py` ausführen. Basis- und Lokalmanifeste
   gegen das aktuelle NVDA AddonTemplate prüfen und beide Artefakte sowie
   die relevanten Installations- und Upgrade-Pfade verifizieren.
4. Nach Freigabe ein annotiertes Tag `vMAJOR.MINOR.PATCH` auf exakt dem
   gebauten Commit setzen und dieses Tag pushen. Der Commit gelangt per
   Pull Request auf GitHub-`main`. Vor dem Entwurf das entfernte Tag-Ziel
   prüfen.

Bei fehlgeschlagenen Prüfungen, fehlender Freigabe, einer bereits verwendeten
Version oder Abweichungen zwischen Tag, Manifesten, Links und Dateien
abbrechen. Veröffentlichte Tags und Dateien bleiben unveränderlich.
Paketkorrekturen erhalten eine neue Version.

## GitHub und Add-on Store

Nach Veröffentlichungsfreigabe einen Entwurf für das vorhandene Tag anlegen.
Englische Hinweise aus dem Changelog seit dem vorigen GitHub-Release
derselben Linie ableiten. Kompatibilität, Migration, Prüfgrenzen und
Dokumentationslinks am Tag aufnehmen. Die Notizdatei liegt unter `../nal-aux/`.

```bash
gh release create "v<VERSION>" "dist/NeovimAccessLink-<VERSION>.nvda-addon" \
  "dist/neovim-access-link-<VERSION>-documentation.zip" \
  --repo helmsaccess/neovim-access-link --draft --verify-tag --fail-on-no-commits \
  --title "Neovim Access Link <VERSION>" --notes-file "<RELEASE_NOTES_FILE>" <STATUS_FLAGS>
```

Vorschauen verwenden `--prerelease --latest=false`, die aktuelle stabile
Linie `--latest` und ältere stabile Wartungsreleases `--latest=false`.
Im Entwurf Tag-Ziel, Hinweise, Dateinamen und SHA-256 beider Downloads
prüfen. Danach den öffentlichen Release kontrollieren. Als Repository-Schutz
[unveränderliche Releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
nutzen.

Die Store-Einreichung benötigt eine eigene Freigabe. Die direkte HTTPS-URL
und den SHA-256 des geprüften veröffentlichten Add-ons verwenden. Den
tatsächlichen Store-Eintrag bestätigen, bevor er als Basis dient.
Experimentelle NVDA-API-Versionen erfordern im Store den Kanal Beta oder Dev.
[NVDA-Einreichungsregeln](https://github.com/nvaccess/addon-datastore/blob/master/docs/submitters/submissionGuide.md)

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
