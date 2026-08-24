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
seit der unmittelbar vorherigen veröffentlichten Version; anschließend bleiben
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

Der Linux-Checkout ist die Quelle der Entwicklung. Dort laufen Tests und
Dokumentationsprüfungen ausschließlich mit automatisch gelöschten Ausgaben:

```bash
python3 tools/run_tests.py all
bash tools/build_documentation.sh --test-only
```

`all` führt sichere, SSH- und Socketphasen nacheinander aus; die Umgebung muss
Listener und kurzlebige Neovim-Prozesse erlauben. In eingeschränkten
Umgebungen werden `all-safe`, `ssh` und `socket` entsprechend der
[Teststrategie](testing.md) getrennt ausgeführt.

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

Normale Entwicklungsartefakte entstehen im synchronisierten Windows-Worktree
durch das parameterlose `build.cmd`. Das Skript setzt ein aktuelles Python 3,
Git for Windows mit Bash und eine Internetverbindung voraus. Es richtet die
festgelegten Python-Abhängigkeiten temporär ein, lädt den offiziellen
Pandoc-Windows-Binärbuild 3.1.11.1 nur dann in denselben temporären Bereich,
wenn kein lokales Pandoc der kompatiblen Reihe 3.1 vorhanden ist, und prüft
dann dessen SHA-256. Eine lokale abweichende Version wird weder verwendet noch
verändert. Branch, Commit und Synchronisierungsstand werden vor und nach dem
Build verglichen.

Windows-Entwicklungs- und Linux-Releasebuild verwenden denselben isolierten
Kernablauf. Er
rendert alle acht Dokumente, baut daraus Add-on und Dokumentations-ZIP, prüft
die exakt erwarteten Namen und verschiebt erst danach diese beiden Dateien
nach `dist`. Ein gleichzeitiger Quellwechsel bricht vor der Veröffentlichung
der Dateien ab.

## Synchronisierter Windows-Worktree

`/nfs/src/neovim-access-link` ist der über SMB als Windows-Laufwerk sichtbare,
dauerhafte Test- und Build-Worktree. Einmalig wird er vom Linux-Checkout aus
eingerichtet:

```bash
python3 tools/windows_workspace_sync.py configure /nfs/src/neovim-access-link
```

Danach übertragen lokale Git-Hooks Änderungen an Branch-Refs im Hintergrund.
Erstellung, Löschung und Wechsel von Branches sowie nicht vorwärts gerichtete
Commitänderungen werden gespiegelt. Der Ziel-Checkout verwendet einen eigenen
Staging-Ref-Namensraum und `--no-overwrite-ignore`. Die Synchronisierung
verändert ausschließlich versionierte Dateien und Git-Refs; ignorierte oder
sonstige unversionierte virtuelle Umgebungen, Human-Test-Zustände,
Werkzeuginstallationen und Buildausgaben bleiben bestehen. Änderungen an
versionierten Zieldateien oder eine Namenskollision mit einer unversionierten
Datei führen zum Abbruch. Ein manueller Wiederholungslauf ist möglich mit:

```bash
python3 tools/windows_workspace_sync.py sync
```

Verknüpfte Linux-Worktrees desselben Repositorys teilen sich eine serialisierte
Warteschlange. Der zuletzt auslösende Worktree bestimmt den ausgecheckten
Zielbranch; sämtliche lokalen Branch-Refs werden unabhängig davon gespiegelt.
Die Hooks und der Worker liegen als branchunabhängige Laufzeitkopie im
gemeinsamen Git-Verwaltungsverzeichnis. Nach Änderungen am
Synchronisierungswerkzeug oder seinen Hooks muss `configure` erneut laufen.

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
   vorherigen veröffentlichten Version;
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

Ein GitHub-Pre-Release wird aus dem freigegebenen Tag erstellt, erhält die
englische Releasebeschreibung und genau die beiden unten genannten Assets.
Danach werden Tagziel, Pre-Release-Markierung, Assetnamen und Downloads auf
GitHub erneut geprüft.

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
