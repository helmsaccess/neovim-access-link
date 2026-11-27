# Teststrategie

Diese Seite erklärt, welche Prüfung zu einer Änderung gehört und was ein
grüner Lauf tatsächlich belegt. Ausführliche Bedienfolgen stehen nicht hier,
sondern im eigenständigen Leitfaden für
[geführte Praxistests](human-testing.md).

## Ziele und Evidenzarten

Die Teststrategie schützt vor allem:

- blockierendem I/O auf NVDAs Hauptthread;
- Vermischung von Sitzungen, Fenstern, Tabs oder Panes;
- Ausgabe oder Unterdrückung ohne bestätigten Fokus und Zustand;
- ungültigen, übergroßen oder nicht ausgehandelten Protokolldaten;
- Regressionen in Sprache, Braille, Lokalisierung und Paketinhalt;
- Abweichungen zwischen dokumentiertem und gebautem Verhalten.

Automatisierte Tests, praktische NVDA-Prüfung und Code-/Quellprüfung sind
unterschiedliche Evidenzarten. Keine davon allein bestätigt jede Plattform,
Hardware oder Benutzerkonfiguration. Status und Kompatibilität nennen deshalb
jeweils den tatsächlich geprüften Umfang.

## Testgruppen und Presets

`tools/run_tests.py` inventarisiert die Testdateien und führt unabhängige Jobs
in getrennten temporären Verzeichnissen aus.

| Gruppe oder Preset | Inhalt |
|---|---|
| `unit` | reine und mit Attrappen isolierte Python-Tests |
| `package` | gebautes Add-on, Archivinhalt und NVDA-Integrationsattrappen |
| `lua` | Headless-Neovim-Spezifikationen ohne Listener |
| `ssh` | simulierte SSH-, Askpass-, Kommando- und Fehlerpfade |
| `socket` | echte wegwerfbare TUI-, RPC-, TCP- und Unix-Socket-Fälle |
| `guided-desktop` | Windows-VM mit Fokus-, Sprach- und Brailleprüfungen |
| `guided-audio` | Windows-VM mit PCM-Aufnahmen und Stumm-Gegenproben |
| `quick` | schnelle Rückmeldung; nur `unit` |
| `all-safe` | `unit`, `package` und listenerfreies `lua` |
| `all` | `all-safe`, danach `ssh` und `socket` in getrennten Phasen |

Ohne Gruppenargument entspricht der Runner dem sicheren Preset. Standardmäßig
richtet sich die Zahl paralleler Jobs nach den für Python verfügbaren logischen
Prozessoren. `-j N` setzt die Grenze für einen Lauf. Die Pakettests verteilen
sich auf bis zu zwölf unabhängige Blöcke. Jeder Block baut sein eigenes Paket.
`--list` zeigt die Auswahl, ohne sie auszuführen. Jeder isolierte Job läuft in
einer eigenen Prozessgruppe. Nach 180 Sekunden beendet der Runner die gesamte
Gruppe einschließlich gestarteter Neovim- und Hilfsprozesse und meldet den
Job als fehlgeschlagen.
Die reale TUI-Sendehilfe begrenzt das Leeren des Pseudoterminals zusätzlich auf
eine Sekunde und 8 MiB je physischem Tastenschritt.
Die kompakte Ausgabe nennt für jeden Job und in der Gesamtsumme auch
übersprungene Fälle und Python-Warnungen. Für jeden Fund folgt eine `SKIP`-
oder `WARN`-Zeile mit Job und Grund beziehungsweise Warntext; ein grüner Lauf
mit `0 skipped, 0 warnings` belegt damit ausdrücklich, dass nichts verborgen
übersprungen oder gewarnt wurde.

## Empfohlener Ablauf

Während einer Änderung:

```bash
python3 tools/run_tests.py quick
```

Vor einem Commit mindestens die betroffene Gruppe und danach den sicheren
Gesamtpfad:

```bash
ruff check .
ruff check --config 'include = ["nvda-addon/tests/**/*.py"]' .
ruff format --check .
python3 tools/run_tests.py all-safe
python3 tools/run_tests.py ssh
git diff --check
```

Sockettests benötigen eine Umgebung, die Loopback-Listener, private
Unix-Sockets und kurzlebige Neovim-Prozesse erlaubt:

```bash
python3 tools/run_tests.py socket
```

Unter Windows führt der Runner in dieser Gruppe die lokalen TCP-Tests aus.
Sie prüfen die Sitzungsregistrierung und einen echten Neovim-Prozess mit
authentifiziertem Anfangszustand und Cursor-Routing über den Python-Client.
Für die vollständige Gruppe mit Unix-Sockets und Pexpect-PTY wird ein
Linux-Checkout benötigt.

In einer eingeschränkten Sandbox ist ein Listenerfehler eine
Umgebungsbegrenzung, kein erfolgreicher Test. Die Socketphase wird dann in
einer erlaubten Umgebung nachgeholt. `python3 tools/run_tests.py all` ist nur
dort sinnvoll, wo alle drei Phasen zulässig sind.

### Geführte Abläufe über echtes Neovim-RPC

Mit Neovim 0.12.x im `PATH` lädt die Socketphase zusätzlich das geführte
Testprofil in frischen Editoren. Sie reiht über `nvim_input` die tatsächlich
belegten Tasten ein und empfängt semantische Ereignisse über den
authentifizierten Produktivclient. Die Prüfungen gleichen die Ereignisse mit
nativen Puffer-, Cursor-, Quickfix-, Diagnose- und Completion-Zuständen,
externen Linter-Ausgaben oder unveränderten Testdateien ab.

L4 und L6 benötigen nur Neovim. Die weiteren Fälle verwenden Versionen aus
`tests/human/dependencies.json` und werden mit Begründung übersprungen, wenn
ein benötigtes Werkzeug oder ein Pfad fehlt. Setze vor der Socketphase:

| Variable oder Programm | Erwartete Abhängigkeit | Fälle |
| --- | --- | --- |
| `NAL_GUIDED_PYRIGHT` und `node` im `PATH` | Pyrights `langserver.index.js` und Node.js | L1–L3, L5, C1–C3, D1, D2 |
| `NAL_GUIDED_COMPLETION_ROOT` | Elternverzeichnis der fixierten Git-Checkouts `nvimCmp`, `cmpNvimLsp` und `blinkCmp` | C2, C3 |
| `NAL_GUIDED_NVIM_LINT` | Fixierter Git-Checkout von nvim-lint | D1–D4 |
| `ruff` im `PATH` | Fixiertes Ruff-Programm | D1, D2 |
| `NAL_GUIDED_CLANG_TIDY` | Fixiertes Clang-Tidy-Programm | D3 |
| `NAL_GUIDED_MARKDOWNLINT` | Fixiertes markdownlint-cli2-Programm oder Windows-Befehlswrapper | D4 |
| `NAL_GUIDED_LAZY` | Fixierter Git-Checkout von lazy.nvim | P1 |

L3 und D2 prüfen die für NVDA bereitgestellten Kontextdaten. Sie vergleichen
die echten Provider-Ergebnisse, ordnen Anfragen dem Editorzustand zu und
prüfen, dass die Abfrage den Cursor unverändert lässt. D2 schickt zusätzlich
einen veralteten Editorzustand und erwartet eine explizite Ablehnung.

Für P1 verbindet sich ein separater Client über `nvim_ui_attach` und empfängt
Neovims echte UI-Zeichenereignisse. Die Prüfung liest auch den nativen
Pufferzustand und prüft Befehlsleiste und Aufklappzustand über den
Produktivclient.
Für P2–P4 führt `bash tools/test_lazy_plugin.sh PFAD_ZU_FIXIERTEM_LAZY_NVIM`
die echten Lazy-Befehle mit temporären lokalen Git-Repositories aus. Die
Prüfung erfasst den Operationsablauf und kontrolliert Git-Revisionen und
Entfernung unabhängig davon. Der Prüfer muss auch einen tatsächlichen
Rücksprung auf einen älteren Commit und bei Sync ein erneut vorhandenes
veraltetes Verzeichnis erkennen.

Diese Prüfungen decken die Neovim- und Protokollanteile der Aufgaben ab.
Windows-Fokus, NVDA-Sprach- und Brailleausgabe und physische Wahrnehmung
erfordern getrennte Beobachtungen. Siehe den
[Umfang der geführten Tests](human-testing.md).

### Geführte Windows- und Audio-Prüfungen

Die optionalen Gruppen laufen nacheinander auf einem isolierten
Windows-Gast. `--list` zeigt die Aufgaben-IDs. `--guided-case` beschränkt
einen Lauf auf bestimmte Aufgaben und kann mehrfach angegeben werden.

```powershell
python tools/run_tests.py guided-desktop guided-audio --list
python tools/run_tests.py guided-desktop guided-audio --guided-config $labConfig --guided-addon $addon
```

`tests/guided/windows/README.md` beschreibt VM-Konfiguration, Werkzeuge
und Belege. Die VM-Daten bleiben im lokalen Hilfsverzeichnis. Ein
Gastbericht weist Paketprüfsumme und Aufräumquittung aus. Die Prüfungen
erfassen digitale Braille-Punktmuster, die an die Sprachsynthese
übergebenen Sequenzen und gerenderte Audiosignale. Gerätespezifische
Braille-Wahrnehmung, akustische Verständlichkeit und subjektive Latenz
liegen außerhalb dieser Messung.

## Zuordnung nach Änderung

Prüfe Betriebssystemfokus und Tastengesten in einem interaktiven, isolierten
Windows-Desktop. Ein Windows-Gast kann Win32-Vordergrund, UI-Automation-Fokus
und Tasten über das virtuelle Tastaturgerät prüfen. Der Prüfcode unter
`tests/guided/windows/` verwendet eine separate NVDA-Konfiguration und ein
portables Windows Terminal. Prüfcode in der portablen NVDA-Ausgabe
nutzt explizite Fehlerbedingungen. NVDA startet Python mit Optimierung und
lässt `assert`-Anweisungen weg.

| Änderung | Erforderliche Schwerpunkte |
|---|---|
| Protokollfeld oder Steuerbefehl | Validator, Codec, Bridge, lokaler Client, Capability-Negativpfad, Lua und Sicherheitsdokumentation |
| Neovim-Ereignis oder Adapter | betroffene Lua-Spezifikation, echter Neovim-Lauf, Zustands- und Präsentationstest |
| SSH oder Sitzungsentdeckung | `ssh`, Registry-/Eigentumsprüfungen, Timeout und nicht destruktiver Fehlerpfad |
| lokales Windows-RPC | lokaler Client, Loopback-/Nonce-/Prozessprüfung und `socket` |
| Fokus, AppModule oder Unterdrückung | Mehrinstanz-, Fokusrennen-, `nextHandler`- und fail-open-Pakettests plus praktischer WT-Negativpfad |
| Sprache, Klang oder Braille | neutraler Planer, NVDA-Adapter, Unicode-/Routing-/Regionsfälle und praktische Ausgabe |
| Einstellung oder UI | Schema, Profilwechsel, Lokalisierung, Pakettest und beide Handbuchsprachen |
| Installer oder Paketinhalt | Paket-, Installations-, Entfernungs- und gebaute Archivtests |
| Dokumentation | Beispiel-Synchronisierung, Sprachspiegel, HTML-Metadaten, Markdown-/HTML-Links und frischer Dokumentationsbuild |

Ein Fehlerbehebungscommit ergänzt nach Möglichkeit einen Regressionstest auf
der niedrigsten sinnvollen Schicht und einen Integrationsnachweis an der
Grenze, an der der Fehler sichtbar wurde.

AST-basierte Add-on-Architekturtests sichern den minimalen Global-Plugin-
Einstieg, die öffentliche AppModule-API, einen azyklischen lokalen Importgraphen
und genau je einen produktiven Pfad für `send_control` und `client.stop`.
Echte Worker-Tests verwenden absichtlich blockierende Clients; Scheduler- und
Rollbacktests führen verspätete Callbacks und Fehler an jeder
ressourcenbesitzenden Konstruktionsstufe aus. Damit prüfen diese Tests die
Nebenläufigkeitsverträge statt nur Quelltextfragmente. Die zweite Ruff-Zeile
lintet alle Python-Tests ausdrücklich; der Formatcheck bleibt auf den im
Projekt konfigurierten NVDA-Produktcode begrenzt.

Die fachlichen Eigentümer `AddonRuntime`, `ManagedClientFactory`,
`TemporaryBindingWorkflow`, `EventDelivery`, `TerminalActions` und
`ConnectionWorkflow` besitzen direkte Tests mit kleinen injizierten Attrappen.
Pakettests bleiben für echte Komposition, NVDA-Registrierung, Persistenz und
vollständige Fokus-/Disconnect-Szenarien zuständig. Die Bridge folgt derselben
Grenze: mockisolierte Verträge stehen in `test_nvim_bridge_mock.py`, reale
TUI-/Socket-Szenarien in `test_nvim_bridge_socket.py`. Der Runner entdeckt und
shardet deren Methoden aus der jeweiligen Datei, statt eine zweite manuelle
Namensliste zu pflegen.

`test_contract_mutations.py` prüft vier besonders kritische Verträge gegen
temporäre, gezielt veränderte Protokollpakete. Die Suite muss das Entfernen der
Bool-Abgrenzung, eine falsche exakte Größenobergrenze, eine aufgeweichte
Feldmenge und einen gelockerten initialen Sequenzvergleich jeweils erkennen.
Das ist bewusst eine kleine deterministische Auswahl und kein allgemeines
Mutationstest-Framework oder Coverage-Prozentwert.

## Spezialisierte Vertragsprüfungen

Zusätzliche Skripte prüfen reale öffentliche Plugin- und Werkzeugverträge:

- `tools/test_completion_plugins.sh` für `nvim-cmp` und `blink.cmp`;
- `tools/test_linter_plugins.sh` für `nvim-lint`, ALE und reale Linter;
- `tools/test_none_ls.sh` für die `none-ls.nvim`-LSP-Brücke;
- `tools/test_lazy_plugin.sh PATH_ZU_LAZY_NVIM` für öffentliche lazy.nvim-
  Befehle, Lebenszyklusereignisse und lokale Git-Endzustände;
- `tools/test_neovim_plugin.sh` für den seriellen vollständigen
  Lua-Kompatibilitätslauf. Er enthält auch Session-Spezifikationen mit lokalen
  Listenern und benötigt deshalb eine dafür erlaubte Umgebung.

Die GitHub-Matrix führt diese Verträge mit den im Workflow gepinnten
Neovim-, Plugin-, Sprach- und Werkzeugversionen aus. Die Checkouts sind reine
Testabhängigkeiten und werden nicht ausgeliefert.

## GitHub Actions

`.github/workflows/repository-tests.yml` läuft für Pushes und Pull Requests.
Die Jobs sind bewusst getrennt:

- sichere Unit-, Paket- und listenerfreie Lua-Tests;
- ein gezielter Neovim-0.12.3-Vertrag für native Tutor-Extmarks und den echten
  TUI-Ereignispfad;
- der PowerShell-Runner für geführte Praxistests;
- Completion-Plugin-Verträge;
- öffentliche lazy.nvim-Verträge mit echten Installations-, Aktualisierungs-
  und Synchronisierungsvorgängen;
- Diagnoseprovider und reale Linter;
- simulierte SSH-/Askpass-Pfade;
- echte TUI-, TCP- und Unix-Socket-Fälle;
- Build und Linkprüfung aller acht Dokumentationsdateien.

Ein grüner Matrixjob bestätigt den jeweils benannten Vertrag. Der gesamte
Desktop- und Audionachweis verwendet den isolierten Windows-Gast.

Der gehostete Workflow `.github/workflows/guided-windows-hosted.yml`
baut das Add-on, lädt es in portabler NVDA und prüft das fokussierte
`TermControl`-Steuerelement sowie die Tastatureingabe bis zum Konsolenprozess.
S1 prüft zusätzlich, dass F12 den Editor bindet und F10 im ursprünglichen
PowerShell-Tab native Terminalereignisse, Eingabe am Cursor und digitale
Brailleausgabe wiederherstellt. In der Gegenprobe fehlt F10, sodass die
Prüfung genau an diesem Schritt scheitern muss. Der gemessene `windows-2025`-Runner
hatte keinen WASAPI-Standardausgang.
Die Gastaufnahmen verwenden den Render-Endpunkt im Windows-Gast.
[Gehostete NVDA-Fokus- und S1-Nachweise](https://github.com/helmsaccess/neovim-access-link/actions/runs/46000887969)

Der wiederverwendbare Workflow `.github/workflows/guided-windows-vm.yml`
führt alle 18 Fälle und die vollständige Nachprüfung in einem vorbereiteten
Windows-Labor aus. Ein privates Repository desselben Besitzers bindet den
Workflow an eine geprüfte Commit-SHA. Nur der Besitzer startet ihn manuell
vom Standardbranch. Der eigene Windows-Runner ist auf das private Repository
beschränkt. Der Workflow benötigt keine GitHub-gehosteten Minuten.
Rohprotokolle, Gastmedien und Audiomitschnitte bleiben im Labor.
Einrichtung und Aufruf stehen in `tests/guided/windows/README.md`.
Das Labor führt nach einem fehlgeschlagenen Fall die übrigen unabhängigen
Fälle aus und fährt seinen Gast am Ende der Suite herunter. Ein
fehlgeschlagener Fall lässt die vollständige Nachprüfung scheitern. Wenn C1
im Gast und in WASAPI besteht, aber die Startmarke in der QEMU-Aufnahme fehlt,
startet das Labor den Gast neu und wiederholt die betroffene Audioeinstellung
einmal. Der Abschlussprüfer wertet die verworfene und die neue vollständige
Aufzeichnung mit denselben Anforderungen aus.
Bei einem kurzen Zeitversatz in einer C1-QEMU-Referenzmarke kann der Prüfer
die Marke anhand von vier von fünf getrennten Wellenformabschnitten erkennen.
Jeder Abschnitt muss mindestens 0,92 Korrelation erreichen. Die daraus
ermittelten Startzeiten dürfen höchstens 26 ms auseinanderliegen. Der Bericht
hält Abschnittszahl und Zeitspanne fest. Für die Hinweistöne der Anwendung
und die unabhängige WASAPI-Aufnahme prüft er die vollständigen Wellenformen.
Das verwaltete Labor startet den Gast zwischen den beiden unabhängigen
P2-Fixtures neu. Wenn QEMU vor dem Bereitschaftssignal des Desktops endet,
erkennt das Labor den Abbruch und startet denselben Gast einmal erneut.
Der vollständige Gastlauf ist lokal bestätigt. Der Actions-Aufruf setzt
einen bereitgestellten privaten Labor-Runner voraus.

## Buildprüfung

Pakettests bauen das Add-on mit einem expliziten temporären
Ausgabeverzeichnis, öffnen das tatsächliche `.nvda-addon` und prüfen Basis- und
Lokalisierungsmanifest streng gegen die zutreffenden Felder des offiziellen
NVDA-AddonTemplates sowie
Ressourcen, alle acht lokalisierten installierten HTML-Dokumente, gebündelte
Linux-Komponenten, Lizenzen, Übersetzungskatalog und verbotene Dateien. Ein
vorher gebautes Archiv ist kein Nachweis für spätere Quelländerungen. Der
Linux-Entwicklungscheckout erhält dabei weder ein auslieferbares Add-on noch
dauerhafte Buildausgaben.

Nach Dokumentationsänderungen wird die vollständige Dokumentation temporär
gerendert und geprüft:

```bash
bash tools/build_documentation.sh --test-only
```

Linux-Releasebuild und CI-Prüfjob verwenden den jeweiligen offiziellen
Binärbuild von Pandoc 3.1.11.1 aus einem Archiv mit festgelegter
SHA-256-Prüfsumme. Der Windows-Entwicklungsbuild verwendet ein vorhandenes
Pandoc 3.1.11.1 mit den erwarteten Buildmerkmalen. Sonst lädt er den
prüfsummengesicherten offiziellen Binärbuild in sein temporäres Buildverzeichnis.

Der Build prüft die kanonische Lua-Beispielkonfiguration, deutsche und
englische Quelldateien und Überschriftenstrukturen, lokale Markdownlinks,
generierte HTML-Ziele, Sprach-, Titel- und Beschreibungsmetadaten sowie die
acht erwarteten Dokumente. Das Skript löscht seine Ausgaben nach der Prüfung;
CI veröffentlicht keine Endanwenderartefakte.
Historische Archive, die ausdrücklich nicht
zur aktuellen Dokumentation gehören, werden validiert, aber nicht in das HTML
aufgenommen.

Nach vollständiger Prüfung erzeugt `build.cmd` im lokalen
Windows-Checkout die Entwicklungsartefakte. Der freigegebene Linux-Stand
erzeugt mit `python3 tools/build_release.py` die später veröffentlichten
Releaseartefakte. Beide Einstiegspunkte verwenden denselben isolierten Kern
und bauen Add-on und Dokumentations-ZIP aus einem stabilen Branch- und
Commitstand. Details zu Werkzeugvoraussetzungen und Abbruchbedingungen stehen unter
[Release-, Versions- und Buildprozess](release-and-build.md).

## Praktische Prüfung

Der geführte Runner liegt unter `tests/human/framework/`; seine versionierten
Pläne liegen unter `tests/human/plans/`. Eingerichtete Werkzeuge und
Setup-Fingerprints schreibt er nach `tmp/human-test-state/`, Ergebnisse
dagegen nach `tmp/human-test-results/`. Diese tool-eigenen Pfade sind keine
Arbeitsverzeichnisse für Agenten oder manuelle Projektdateien.

Praktische Prüfschwerpunkte werden risikoorientiert gewählt. Bei Änderungen an
Verbindung oder Fokus gehören mindestens dazu:

1. ein verbundener lokaler oder entfernter Erfolgsweg;
2. ein ungebundenes Shell-Control im selben Windows-Terminal-Umfeld;
3. Wechsel zwischen relevanten Tabs, Panes oder Fenstern;
4. Disconnect oder unklarer Fokus mit nativer fail-open-Ausgabe.

Braille-, Sprach-, Plugin- oder LSP-Änderungen verwenden die dafür passenden
Suiten im Leitfaden. Ergebnisse nennen Hardware, Versionen und nicht geprüfte
Breite; sie werden nicht als erschöpfende Freigabe formuliert.

## Fehler einordnen

1. Den kleinsten reproduzierbaren Test und seine Gruppe bestimmen.
2. Prüfen, ob die Umgebung erforderliche Listener, Binaries, Plugins oder
   Sprachserver tatsächlich bereitstellt.
3. Bei einem echten Fehler die zuständige Schicht isolieren: Produzent,
   Transport, Validierung, Zustand, Fokus oder Präsentation.
4. Regressionstest hinzufügen und erst danach den nächstbreiteren relevanten
   Lauf wiederholen.
5. Bei geänderter Aussage Status, Kompatibilität, Architektur oder Referenz in
   beiden Sprachen aktualisieren.

Logs helfen bei der Diagnose, sind aber niemals Teil des korrekten
Steuerpfads. Private Inhalte werden auch in Reproduktionen und Fehlermeldungen
nicht versioniert.
