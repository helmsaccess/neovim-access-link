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
| `quick` | schnelle Rückmeldung; nur `unit` |
| `all-safe` | `unit`, `package` und listenerfreies `lua` |
| `all` | `all-safe`, danach `ssh` und `socket` in getrennten Phasen |

Ohne Gruppenargument entspricht der Runner dem sicheren Preset. `-j N`
begrenzt Parallelität; `--list` zeigt die Auswahl, ohne sie auszuführen.

## Empfohlener Ablauf

Während einer Änderung:

```bash
python3 tools/run_tests.py quick
```

Vor einem Commit mindestens die betroffene Gruppe und danach den sicheren
Gesamtpfad:

```bash
ruff check .
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

In einer eingeschränkten Sandbox ist ein Listenerfehler eine
Umgebungsbegrenzung, kein erfolgreicher Test. Die Socketphase wird dann in
einer erlaubten Umgebung nachgeholt. `python3 tools/run_tests.py all` ist nur
dort sinnvoll, wo alle drei Phasen zulässig sind.

## Zuordnung nach Änderung

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
| Dokumentation | Beispiel-Synchronisierung, Sprachspiegel, Markdown-/HTML-Links und frischer Dokumentationsbuild |

Ein Fehlerbehebungscommit ergänzt nach Möglichkeit einen Regressionstest auf
der niedrigsten sinnvollen Schicht und einen Integrationsnachweis an der
Grenze, an der der Fehler sichtbar wurde.

## Spezialisierte Vertragsprüfungen

Zusätzliche Skripte prüfen reale öffentliche Plugin- und Werkzeugverträge:

- `tools/test_completion_plugins.sh` für `nvim-cmp` und `blink.cmp`;
- `tools/test_linter_plugins.sh` für `nvim-lint`, ALE und reale Linter;
- `tools/test_none_ls.sh` für die `none-ls.nvim`-LSP-Brücke;
- `tools/test_neovim_plugin.sh` für listenerfreie Lua-Spezifikationen.

Die GitHub-Matrix führt diese Verträge mit den im Workflow gepinnten
Neovim-, Plugin-, Sprach- und Werkzeugversionen aus. Die Checkouts sind reine
Testabhängigkeiten und werden nicht ausgeliefert.

## GitHub Actions

`.github/workflows/repository-tests.yml` läuft für Pushes und Pull Requests.
Die Jobs sind bewusst getrennt:

- sichere Unit-, Paket- und listenerfreie Lua-Tests;
- der PowerShell-Runner für geführte Praxistests;
- Completion-Plugin-Verträge;
- Diagnoseprovider und reale Linter;
- simulierte SSH-/Askpass-Pfade;
- echte TUI-, TCP- und Unix-Socket-Fälle;
- Build und Linkprüfung aller acht Dokumentationsdateien.

Ein grüner Matrixjob bestätigt nur seinen benannten Vertrag. Praktische
NVDA-, Windows-Terminal- und Brailleausgabe bleibt eine gesonderte Abnahme.

## Buildprüfung

Nach Codeänderungen an installierbarem Inhalt wird das Add-on aus dem
endgültigen Worktree neu gebaut:

```bash
python3 tools/build_nvda_addon.py
```

Pakettests öffnen das tatsächliche `.nvda-addon` und prüfen Manifest,
Ressourcen, gebündelte Linux-Komponenten, Lizenzen, Übersetzungskatalog und
verbotene Dateien. Ein vorher gebautes Archiv ist kein Nachweis für spätere
Quelländerungen.

Nach Dokumentationsänderungen wird die Dokumentation neu gebaut:

```bash
tools/build_documentation.sh
```

Der Build prüft die kanonische Lua-Beispielkonfiguration, deutsche und
englische Quelldateien und Überschriftenstrukturen, lokale Markdownlinks,
generierte HTML-Ziele und die acht erwarteten Dokumente im ZIP. Historische
Archive, die ausdrücklich nicht zur aktuellen Dokumentation gehören, werden
validiert, aber nicht in das HTML aufgenommen.

Ändert eine Arbeit sowohl installierbaren Inhalt als auch Dokumentation,
werden beide Artefakte aus demselben finalen Worktree erzeugt.

## Praktische Prüfung

Der geführte Runner liegt unter `tests/human/framework/` und schreibt Pläne,
Fingerprints und Ergebnisse in das ignorierte Verzeichnis
`tmp/human-test-state/`. Dieser tool-eigene Pfad ist kein Arbeitsverzeichnis
für Agenten oder manuelle Projektdateien.

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
