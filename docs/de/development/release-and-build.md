# Release-, Versions- und Buildprozess

## Zentrale Metadaten

`buildVars.py` ist die einzige gepflegte Quelle für Produktidentität und
Versionsdaten. Sie enthält:

- internen Add-on-Identifier und sichtbaren Produktnamen;
- Autor, numerische Produktversion und Releasekanal;
- branchlokale Entwicklungsbuildnummer;
- minimale und zuletzt getestete NVDA-Version;
- Projektadresse, Standardhilfedatei und englisches Manifest-Changelog.

`store_version()` liefert ausschließlich `MAJOR.MINOR.PATCH` für Manifest und
NVDA Add-on Store. `artifact_version()` ergänzt bei Entwicklungsständen
`-dev.N` sowie nach Möglichkeit Branch- und Commitmetadaten für Dateinamen,
Diagnosebericht und gebündelte Komponenten. Das installierte Manifest wird
beim Build aus diesen Werten und dem passenden Changelogabschnitt erzeugt und
nicht separat gepflegt. Das deutsche Lokalisierungsmanifest erhält denselben
Abschnitt aus dem deutschen Changelog.

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

Vor einem auslieferbaren Build wird der endgültige Worktree geprüft:

```bash
python3 tools/run_tests.py all
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
```

`all` führt sichere, SSH- und Socketphasen nacheinander aus; die Umgebung muss
Listener und kurzlebige Neovim-Prozesse erlauben. In eingeschränkten
Umgebungen werden `all-safe`, `ssh` und `socket` entsprechend der
[Teststrategie](testing.md) getrennt ausgeführt.

Der Add-on-Build prüft Manifest, acht installierte lokalisierte HTML-Dokumente,
gebündelte Komponenten, Abhängigkeiten und Archivinhalt. Der
Dokumentationsbuild synchronisiert ausführbare Beispiele,
prüft Markdown- und HTML-Links, die deutsche und englische Struktur sowie
Sprache, Titel und Beschreibung der Ausgabedateien und erzeugt acht
HTML-Dokumente. Er übernimmt dieselben Ergebnisse unter neutralen Dateinamen
in `nvda-addon/addon/doc/de` und `doc/en`; CI lehnt veraltete Kopien ab.

`build.cmd` ist ein zusätzlicher, parameterloser Komfortweg für Windows-Nutzer,
die einen aktuellen Entwicklungsbuild aus einem Quellcode-Download erzeugen.
Er benötigt Python 3.10 oder neuer und eine Internetverbindung, richtet die
festgelegten Buildabhängigkeiten ausschließlich in einem temporären
Python-Environment ein und legt das `.nvda-addon` in `dist` ab. Der validierte
Entwickler- und CI-Prozess oben bleibt davon unberührt.

## Releasevorbereitung

Eine freigegebene Version benötigt in einem gemeinsamen, nachvollziehbaren
Stand:

1. Produktversion, Kanal und `development_build = None` in `buildVars.py`;
2. aktuellen Release- und Changeloglink in `README.md` sowie einen aus den
   unveröffentlichten Einträgen redaktionell erstellten deutschen und
   englischen Versionsabschnitt mit allen Änderungen seit der unmittelbar
   vorherigen veröffentlichten Version;
3. aktuellen Status, kompatible Metadaten und vollständige Deutsch/Englisch-
   Dokumentation;
4. erfolgreiche vollständige Tests und frisch gebaute Artefakte;
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
