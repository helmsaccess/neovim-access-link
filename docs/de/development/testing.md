# Teststrategie

Dieses Kapitel beschreibt dauerhaft gültige Prüfungen. Ergebnisse vergangener
Builds stehen im `changelog.md`; der aktuell bestätigte Umfang steht in
`current-status.md`. Testzahlen werden nicht hier dupliziert, weil sie nach
jeder Änderung veralten.

Die nachfolgenden Listen definieren wichtige Nachweise und wiederholbare
Prüfabläufe. Sie bedeuten nicht, dass jede denkbare Kombination geprüft wurde
oder dass jeder Punkt der praktischen Matrix für jeden Build erneut ausgeführt
wird. Nur ausdrücklich in `current-status.md` als praktisch bestätigt
aufgeführte Fälle gelten als solche; Lücken und neue Fehler bleiben möglich.

## Testziele

Die Tests sollen nicht nur zeigen, dass eine Funktion im Normalfall arbeitet.
Sie müssen insbesondere belegen, dass:

- eine Sitzung niemals Zustand oder Ausgabe einer anderen Sitzung übernimmt;
- ungebundene Terminal-Controls vollständig NVDAs native Unterstützung
  behalten;
- Fehler, Fokusunsicherheit und Disconnects fail-open wirken;
- untrusted Protokolldaten weder Code ausführen noch unbegrenzte Ressourcen
  verbrauchen;
- Byte-, Unicode-, virtuelle und visuelle Spalten nicht verwechselt werden;
- Netzwerk, SSH, Reconnect, Parsing und Installation NVDAs Hauptthread nicht
  blockieren;
- Pakete aus den tatsächlich ausgelieferten Dateien funktionieren;
- automatisierte Nachweise und praktische Bestätigung klar getrennt bleiben.

Ein automatisierter Test mit Attrappen ist keine praktische Freigabe eines
realen Plugins, Terminalfrontends oder Brailletreibers.

## Testebenen

| Ebene | Zweck | Typischer Ort |
|---|---|---|
| Protokoll | Framing, Schema, Grenzen, Sequenzen, Resync und Steuerpayloads | `protocol/python/tests/` |
| Bridge | Session-Discovery, Neovim-RPC, SSH-stdio und Allowlist | `bridge/python/tests/` |
| Core | kanonischer Zustand, Speech, Braille und Fail-open-Gate ohne NVDA | `nvda-addon/tests/` |
| Add-on-Integration | Global Plugin, AppModule, Fokus, Gesten, Installation und Paketlayout mit NVDA-Attrappen | `nvda-addon/tests/` |
| Lua-Spezifikationen | echte Neovim-APIs, Zustandsereignisse und Adapter | `neovim-plugin/tests/*_spec.lua` |
| TUI-/RPC-Integration | echte wegwerfbare Neovim-Instanz, Pseudoterminal und dauerhafter RPC-Kanal | `bridge/python/tests/` und Plugin-Tests |
| Build | tatsächlich gebautes Add-on, eingebettetes Linux-Paket, gettext und HTML | Build- und Pakettests |
| Praxis | NVDA, Windows Terminal, lokales Neovim, SSH, tmux und später Braillehardware | dokumentierte manuelle Matrix |

TUI-, Socket- und SSH-Tests dürfen niemals an eine bestehende Neovim- oder
tmux-Sitzung des Anwenders angehängt werden. Sie verwenden eigene temporäre
Verzeichnisse, Sockets, Prozesse und Testkonten.

## Standardprüfung eines Checkouts

Vom Repository-Wurzelverzeichnis:

```bash
ruff check .
ruff format --check .
tools/run_tests.py all-safe
python3 tools/build_nvda_addon.py
python3 tools/gettext_catalog.py check
tools/build_documentation.sh
git diff --check
```

`tools/run_tests.py` startet unabhängige Dateien beziehungsweise
Integrationsfälle in getrennten Prozessen. Jeder Prozess erhält ein eigenes
temporäres Verzeichnis und ein eigenes `XDG_RUNTIME_DIR`; standardmäßig laufen
bis zu acht Jobs parallel. Die importintensiven Paket-Shards verwenden
zusätzlich einen eigenen Python-Bytecode-Cache. Kurze Jobs erzeugen keine
Bytecode-Dateien. `-j N` begrenzt die Parallelität, `--list` zeigt die Auswahl
ohne Ausführung.

| Gruppe oder Preset | Inhalt |
|---|---|
| `unit` | reine und mit Attrappen isolierte Python-Tests |
| `package` | gebautes Add-on, Paketinhalt und NVDA-Integrationsattrappen in zwei isolierten Prozess-Shards; innerhalb jedes Shards seriell |
| `lua` | Headless-Neovim-Spezifikationen ohne Listener |
| `ssh` | separat ausführbare SSH-Kommando-, Askpass- und Fehlerpfade; alle externen Prozesse sind in diesen automatisierten Tests ersetzt |
| `socket` | echte wegwerfbare Neovim-TUI-, RPC-, TCP- und Unix-Socket-Fälle |
| `quick` | schnelle Rückmeldung; entspricht `unit` |
| `safe` | Standard: `quick`, `package` und `lua` |
| `all-safe` | `safe` plus die ersetzten SSH-Fälle |
| `all` | alle Gruppen; echte Socket-Fälle folgen in einer eigenen Phase |

Die beiden Paket-Shards bauen und entpacken jeweils genau ein tatsächliches
Add-on. Normale Tests verwenden diese unveränderte Extraktion gemeinsam; ein
Fingerabdruck über Namen und Inhalte erkennt unbeabsichtigte Schreibzugriffe.
Nur die beiden Tests, die Konfiguration beziehungsweise gebündelte Klänge
absichtlich verändern oder löschen, erhalten eine eigene frische Extraktion.

Der `socket`-Lauf benötigt eine Umgebung, die lokale Listener und Unix-Sockets
zulässt, und wird deshalb bewusst separat ausgeführt:

```bash
tools/run_tests.py socket
```

In eingeschränkten Sandboxes darf sein Fehlschlagen mit `operation not
permitted` nicht als Produktfehler umgedeutet werden. Ein Lauf außerhalb der
Sandbox bleibt vor Push oder Release verpflichtend, wenn Socket-, Sitzungs-
oder TUI-Code betroffen ist. Die Gruppe `ssh` öffnet in der automatisierten
Suite keine echte SSH-Verbindung; praktische SSH-Prüfungen verwenden weiterhin
ein wegwerfbares Testkonto nach den Regeln dieses Kapitels.

Für die beiden Ruff-Befehle wird wie in NVDA 2026.1 Ruff 0.14.5 verwendet.
Die Konfiguration in `pyproject.toml` begrenzt die Prüfung auf die direkt von
NVDA geladenen Python-Module unter `nvda-addon/addon/`; andere Komponenten
behalten ihren eigenen konsistenten Stil.

`tools/test_neovim_plugin.sh` bleibt der serielle Kompatibilitätslauf mit der
verfügbaren unterstützten Neovim-Version. Für Änderungen an Versionsgrenzen
sollten die Lua- und TUI-Suiten zusätzlich mit Neovim 0.10.1 und 0.12.3
laufen. Eine installierte Pluginversion darf den Checkout nicht überdecken;
die Testskripte isolieren deshalb `packpath`.

## Was die automatisierten Suiten belegen

### Protokoll und Transport

Pflichtfälle sind:

- Protokoll v2, SSH-Startmarker und längenbegrenztes MessagePack-Framing;
- Ablehnung von v1, übergroßen Frames, ungültigen Typen und beschädigtem UTF-8;
- Sitzungskennung, monotone Sequenz, Heartbeat, Lücke, Resync und `fullState`;
- lokaler Client nur für den registrierten Port auf exakt `127.0.0.1`;
- Nonce-Prüfung auf dem danach dauerhaft verwendeten RPC-Kanal vor `setup()`;
- feste Steuer-Allowlist mit Feld-, Größen- und Zustandsprüfung;
- keine Wiederholung einer bereits abgesandten zustandsändernden Aktion.
- streng validierte Explorationsaktionen, IDs, Ursprung, Textgrenzen und
  Verwerfen fremder oder verspäteter Ergebnisse;
- Ende-zu-Ende-Bestätigung der Pluginfähigkeit: Ein älteres installiertes oder
  noch laufendes Plugin darf Exploration weder anbieten noch Befehle erhalten.

### Session-Registry, Claim und Bindung

Die Tests unterscheiden ausdrücklich:

1. physische F12-Markierung im fokussierten Control;
2. monotonen Claim im privaten Sitzungsdatensatz;
3. eindeutige Auflösung gegenüber der Aktivierungsbaseline;
4. Bindung der vollständigen `TerminalIdentity` an eine
   `ConnectionInstance`;
5. Authentifizierung durch den ersten gültigen `fullState`.

Zu prüfen sind alte oder fehlende Claims, gleichzeitig sichtbare Kandidaten,
Fokuswechsel während einer ausstehenden Auswertung, zwei Controls mit gleichem
Prozess und Fensterhandle aber unterschiedlichen Runtime-IDs sowie parallele
lokale und SSH-Instanzen. Ohne frischen eindeutigen Claim dürfen keine Bindung,
Unterdrückung, Auswahl oder Verbindungsansage entstehen.
Der NVDA-Decider wird außerdem gegen F12 in einer fremden Anwendung, ein
fremdes oder veraltetes AppModule, einen zweiten WT-Prozess und einen schnellen
Fokuswechsel vor der Hauptthreadauswertung geprüft. Die realen TUI-Tests müssen
im Normal- und Insert-Modus einen Claim erhalten; im Insert-Modus darf weder
`<F12>` noch ein Teil der Terminalsequenz im Buffer verbleiben. Diese Matrix
läuft gegen Neovim 0.10.1 und 0.12.3.

Graceful Exit, SIGKILL, PID-/Endpoint-/Nonce-Wiederverwendung, tote oder
unklare Sessiondateien, eigene und fremde Sockets sowie geschlossene
Windows-Terminal-Controls müssen nicht-destruktiv geprüft werden. Cleanup darf
weder Neovim noch tmux beenden.

Die NVDA-seitigen Windows-Adapter unterscheiden automatisiert lebende und
beendete Prozesse, ungültige PIDs, Zugriffsverweigerung und unklare Fehler.
Nur ein sicher beendeter Prozess darf einen eigenen Sitzungsdatensatz löschen;
eine geschlossene Terminalidentität wird weiterhin erst nach zwei sicheren
negativen Lifecycle-Prüfungen bereinigt.

### Editor, Präsentation und Fokus

Core- und Add-on-Tests decken Modi, Navigation, Bearbeitung, Auswahl,
Completion, Signaturhilfe, Suche, Diagnostics, Rechtschreibung, Einrückung,
Meldungen, Terminal, Dateimanager, Speech, Klänge und Braille ab.

Besonders wichtig sind:

- UTF-8-Text mit kombinierenden Zeichen, breiten Zeichen, Emoji und Tabs;
- überlappende `TextChanged`-Differenzen ohne doppeltes Tippecho;
- korrelierte Fokusantworten und Verwerfen verspäteter Antworten;
- alle drei Fokusausgaben ohne zusätzliches Zeichenfragment oder doppelten
  Modus;
- native Ausgabe bei Shell, falscher UIA-Klasse, leerer Runtime-ID,
  deaktiviertem Add-on und Disconnect;
- vollständiger Ereignis-, Overlay- und `nextHandler`-Besitz im
  Windows-Terminal-AppModule;
- genau ein nativer Fokusaufruf vor strukturierter Sprachunterdrückung,
  fail-open ohne Wiederholung bei frühen und späten Fehlern;
- verspätetes `loseFocus` und reentrante Fokusabschlüsse ohne Löschen des
  neueren WT-Fokus oder Verlust eines wartenden `fullState`;
- globale unbelegte Gestenmetadaten, aber Ausführung nur im exakt validierten
  und gebundenen Windows-Terminal-Control;
- Weitergabe der Originalgeste außerhalb dieses Controls genau einmal.
- ausschließlich NVDAs normale Skriptauflösung für die sechs festen
  Explorationskombinationen, exakte Pane-Autorisierung, passiver Raw-Key-
  Callback mit ständigem `True`, schnelle Freigabe und Autorepeat-Sperre;
- virtueller Zeichen-, Zeilen- und Wortcursor ohne Änderung von echtem
  Cursor, Buffer, `changedtick`, Modus oder Fensteransicht;
- Strukturtests am gebauten Paket halten alle Anwendungseinstiege aus dem
  Global Plugin heraus und verwerfen Global-Plugin-Abhängigkeiten in den
  ausgelagerten Runtime-, UI-, Fokus-, Claim-, Editor-, Braille-, Registry-
  und Terminaldienstmodulen.

### Terminal und Kommandozeile

Automatisierte TUI- und Add-on-Tests müssen unterscheiden:

- Dateibuffer-Normal, `terminalNormal`, direkte Terminaleingabe und
  Kommandozeilenmodus;
- Insert-/Normal-Earcon, Kommandozeilenton und Passthrough-Reihenfolge;
- `stopinsert` als einzige Operation des Terminal-Ausstiegsbefehls;
- vollständige Kommandozeilen-Zeichenwiedergabe mit UTF-8-Byteposition;
- unmittelbare Ex-Rückkehrmeldung gegenüber einer späteren asynchronen
  Meldung;
- `:bp`, `:bn`, `:terminal`, Fenster- und Tabwechsel unter allen drei
  Fokusausgaben;
- `E89` bei `:bd` eines laufenden Terminaljobs und `TermClose` mit Exitstatus;
- Neovim-0.12-UI-Ereignisse außerhalb des Fast-Event-Kontexts.

### Dateimanager und Prompts

Die Suiten prüfen netrw, Oil, mini.files, nvim-tree und Neo-tree nur im jeweils
belegten Umfang ihrer öffentlichen APIs. Dazu gehören:

- UTF-8-sichere Bytegrenzen für Namen, Pfade und Wurzeln;
- Eintragsart, Markierung, Copy/Cut, Expansion und Zustandsänderung ohne
  Cursorbewegung;
- Deduplizierung, Zusammenfassung schneller Renderereignisse und Verwerfen
  inaktiver Ziele;
- Erstellen, Umbenennen, Kopieren, Verschieben, Löschen, Wiederherstellen,
  Bündelung, Fehler und Abbruch, soweit öffentlich belegbar;
- `vim.ui.input`, `vim.ui.select` und `vim.fn.confirm` mit Annahme und Abbruch;
- Oils enger `oil_preview`-Fallback ohne Pfad- oder Namensübertragung;
- Entwurfsname vor `:w` gegenüber bestätigter Pfadidentität;
- semantische Braillezeile und Routing nur auf einen eindeutig abgebildeten
  Namensbereich.

Ein reales Plugin aus einem fremden Hauptzweig darf in Tests nur in einem
wegwerfbaren, versionsfest dokumentierten Arbeitsbaum verwendet werden. Ein
solcher isolierter Lauf ersetzt nicht die Windows-/NVDA-Abnahme.

## Build- und Dokumentationsprüfung

Der Pakettest muss das tatsächlich erzeugte `.nvda-addon` entpacken, das darin
enthaltene `server-user.tar.gz` öffnen und die Linux-Komponenten in ein
temporäres Präfix installieren. Ein Test nur gegen Repositoryquellen reicht
nicht aus.

Geprüft werden mindestens:

- übereinstimmende Komponenten- und F12-Konfiguration auf beiden Paketseiten;
- ausschließlich vorgesehene Add-on-, Plugin-, Bridge- und Protokolldateien;
- deutsches Manifest und `locale/de/LC_MESSAGES/nvda.mo`, aber keine PO/POT-
  Quellen im Archiv;
- bytegleiche wiederholte MO-Kompilierung und gleiche benannte Platzhalter;
- Quick Guide, Handbuch und Entwicklerdokumentation auf Deutsch und Englisch;
- genau eine H1 pro HTML, gültige interne Sprungziele und keine verbliebenen
  `.md`-Links;
- ausdrückliche Zuordnung jeder veröffentlichten Markdown-Quelle zu einem
  HTML-Build.

## Regeln für praktische Tests

Ein praktisches Protokoll enthält:

- Datum, Betriebssystem, NVDA-, Windows-Terminal-, Neovim- und
  OpenSSH-Version;
- lokalen oder entfernten Transport und relevante Add-on-Einstellungen;
- Ausgangszustand, genaue Befehle und Tasten;
- erwartete und tatsächliche Sprache, Klänge und Braille;
- Ergebnis und redigierten Diagnoseausschnitt bei Abweichung.

Keine echten Hostnamen, Konten, Domains, Schlüsselpfade, Passwörter oder
vertraulichen Editorinhalte eintragen. Bestehende Neovim- und tmux-Sitzungen
nicht für destruktive Tests verwenden.

## Praktische End-to-End-Matrix

Diese Matrix ist ein risikoorientierter Prüfkatalog für Änderungen und
Freigabekandidaten, keine Behauptung einer bereits vollständig ausgeführten
Gesamtabnahme. Je nach Änderung werden die betroffenen und angrenzenden Pfade
ausgewählt; sicherheits-, isolations- und datenverändernde Pfade haben Vorrang.

### Installation und Grundverbindung

1. Add-on installieren, NVDA neu starten und lokale sowie ein wegwerfbares
   gespeichertes SSH-Ziel über den Werkzeugdialog aktualisieren.
2. Prüfen, dass der Dialog bedienbar bleibt, Ziele getrennt meldet und ein
   fehlerhaftes Ziel andere Ziele nicht blockiert.
3. Lokales `nvim.exe` und entferntes Neovim starten. Add-on aktivieren,
   Inventur abwarten und jede Sitzung mit einem physischen F12-Druck binden.
4. Normal, Insert, Visual, Navigation, Eingabe und eine Meldung prüfen.
5. Deaktivieren und Transportende prüfen: Native Terminalausgabe muss sofort
   und global wieder verfügbar sein.

### Windows-Terminal-Isolation

Mindestens verwenden:

- ein gebundenes lokales Neovim-Control;
- ein gebundenes SSH-Neovim-Control;
- einen ungebundenen PowerShell-, Eingabeaufforderungs- oder WSL-Tab;
- horizontale und vertikale Split-Panes;
- nach Möglichkeit zwei Windows-Terminal-Fenster.

Zwischen allen Controls langsam und schnell wechseln. Erwartet wird:

- strukturierte Ausgabe nur aus der exakt fokussierten gebundenen Instanz;
- keine Ausgabe, Bindung oder Unterdrückung aus einer fremden aktiven Instanz;
- F12 in einer Shell ohne frischen Neovim-Claim bleibt wirkungslos;
- eine gemerkte Bindung öffnet das Gate erst nach passender korrelierter
  Fokusantwort;
- geschlossene Tabs oder Fenster stoppen nur ihren NVDA-Client;
- ein Disconnect bindet keine andere Sitzung automatisch;
- eine neue Sitzung im selben Control erfordert erneut den physischen Claim;
- ungebundene Controls behalten Fokus-, Text-, LiveText- und Brailleverhalten
  von NVDA.

UIA-Klasse und vollständige Runtime-ID müssen im redigierten Testprotokoll
festgehalten werden, damit Tab, Pane und Fenster nicht verwechselt werden.

### Sprachexplorationsmodus

Komponenten aktualisieren und alle laufenden Neovim-Instanzen neu starten.
Mit gedrückter physischer NVDA-Taste `h/l`, `k/j` und
`Umschalt+h/l` prüfen. Erwartet wird:

- Zeichen, Zeilen und Wörter folgen nur der virtuellen Position; echter
  Cursor, Buffer, Modus, `changedtick` und Ansicht bleiben unverändert;
- nach gemischten Bewegungen spricht das Loslassen am echten Cursor je nach
  zuletzt genutzter Einheit das Zeichen beziehungsweise die konfigurierten
  Wort-/Zeilendetails;
- auf der Registerkarte „Navigation“ werden nur Wort gegenüber Wort plus
  Cursorzeichen und alle vier Zeilenkombinationen getrennt für normale
  Navigation und Explorationsabschluss geprüft; gemeinsam aktiv ist die
  Reihenfolge Zeile, aktuelles Wort, Cursorzeichen;
- schnelles Loslassen, Autorepeat und Loslassen von NVDA vor der Richtungstaste
  geben kein nacktes `h/j/k/l` an Neovim weiter;
- Normal, Insert, Replace, Visual, Operator-Pending, Kommandozeile,
  Terminal-Normal und direkte Terminaleingabe bleiben lesbar;
- Grenzen, leere und kurze Zeilen, Tabs, Umlaute, kombinierende Zeichen, breite
  Zeichen und Emoji bleiben stabil;
- die rückwärtige Wortexploration hält am vorherigen Wort einer anderen
  Zeile und verbindet Schlüsselwortzeichen nie über einen Zeilenumbruch hinweg;
- Entfernen und Zurückkehren zum ursprünglichen Zeichen, Wort oder zur
  ursprünglichen Zeile spielt genau einen kurzen Doppelton; Verbleiben an
  dieser Einheit wiederholt ihn nicht;
- lokales und SSH-Neovim funktionieren auch in gemischten Tabs, Split-Panes
  und Fenstern;
- dieselben Kombinationen behalten in jeder ungebundenen Shell, einem fremden
  Pane/Tab und anderen Anwendungen ihr normales NVDA-Verhalten;
- Fokuswechsel, Disconnect oder Neovim-Kontextwechsel beenden den Sprachexplorationsmodus
  still und können keine verspätete Ausgabe in der neuen Sitzung erzeugen.

Am 23. Juli 2026 wurde dieser Grundpfad unter Windows/NVDA praktisch geprüft.
Zeichen-, Wort- und Zeilenexploration, rückwärtige Wortbewegung,
Ursprungsdoppelton, Abschlussansage sowie die getrennten Wort- und
Zeilenoptionen für normale Navigation und Exploration zeigten dabei keinen
festgestellten Fehler. Dieser Nachweis ergänzt die automatisierte Matrix; er
ersetzt keine weiteren Prüfungen mit anderen Tastaturlayouts, Sprachen,
GlobalPlugins oder physischer Braillehardware.

### Eingebaute Rechtschreibvorschläge

Die Neovim-Komponenten aktualisieren, Neovim neu starten und in einem
Testbuffer `:set spell` aktivieren. Ein falsch geschriebenes Wort fokussieren
und `z=` drücken. Erwartet wird:

- eine kurze Sprachmeldung kündigt die verfügbare, nicht leere Liste einmalig
  an;
- `NVDA+j/k` wählt bei weiterhin gedrückter NVDA-Taste zyklisch Vorschläge;
  Sprache und Braille enthalten den Vorschlag, aber keine Nummer;
- im NVDA-Braillemodus „Cursor verfolgen“ wechselt NVDAs vorübergehende
  Braillemeldung unmittelbar bei jedem Schritt; beim Test sind Braillemeldungen
  in NVDA aktiviert. Der Modus „Sprachausgabe anzeigen“ folgt stattdessen der
  gesprochenen Ausgabe und prüft keine feste Modulposition;
- Braillemodul 1 fügt standardmäßig keinen Abstand ein; ein vorhandenes
  eingestelltes Modul wie 40 positioniert den vorübergehenden Vorschlag dort,
  während ein Wert jenseits der angeschlossenen Braillezeile ignoriert wird
  und auf Modul 1 zurückfällt; passt der mit der aktiven Brailletabelle
  übersetzte Vorschlag rechts nicht vollständig, wird sein Start bis zur
  spätesten vollständig passenden Position nach links begrenzt;
- das Loslassen der letzten NVDA-Taste verwirft nur die lokale Auswahl, stellt
  die Editor-Braillezeile wieder her und lässt Neovims Abfrage offen;
- erneutes Erkunden und `NVDA+Eingabe` übernimmt genau den gewählten Vorschlag;
- `NVDA+Eingabe` ohne lokale Auswahl meldet „Kein Eintrag ausgewählt“ und
  führt insbesondere keinen eventuell dort belegten Zwischenablagebefehl aus;
- NVDAs Eingabehilfe beschreibt Gesten, ohne eine Auswahl zu bewegen oder
  anzunehmen;
- `Esc` bricht die native Abfrage ab; Fokus-, Modus-, Buffer-, Tab-,
  Pane- und Verbindungswechsel hinterlassen keine flüchtige Auswahl;
- außerhalb der belegten `z=`-Abfrage, in einer Shell oder einem anderen
  Control behalten J, K, Enter und eigene Add-on-Belegungen ihr bisheriges
  Verhalten.

Zusätzlich mit NVDAs Dokumentformatierung für Rechtschreib- und
Grammatikfehler auf „Klang“ oder „Sprache und Klang“ prüfen: Normale
Wortnavigation und `Umschalt+NVDA+h/l`-Wortexploration spielen beim Erreichen
eines fehlerhaften Worts `textError.wav`. Ein korrektes Wort löst den Klang
nicht aus.

Automatisierte Parser-, Protokoll-, Transport-, Controller-, AppModule-,
Braille- und gebaute-Add-on-Tests decken positive und negative Pfade ab. Dazu
gehören der unmittelbare Nachrichtenpuffer, zellgenaue Positionierung,
gezieltes Wiederherstellen des Editorpuffers und der Schutz einer inzwischen
von anderer Stelle ausgegebenen Braillemeldung. Eine
Regression prüft außerdem, dass die asynchrone `focusContext`-Bestätigung einen
vollständigen Fokusregionsaufbau auslöst und dessen Diagnose den öffentlichen
Braillemodus `followCursors` sowie den Tether `focus` enthält. Regionsanforderung
und Routingeintritt besitzen eigene textfreie Diagnosen. Eine
echte TUI-/RPC-Matrix prüft außerdem den blockierenden Neovim-0.10-Prompt und
den eingeplanten Neovim-0.12-Pfad einschließlich Annahme des nativen Indexes.
Der Vorschlagspfad wurde unter Windows/NVDA mit einer physischen Braillezeile
erfolgreich praktisch geprüft; eine breitere Hardwarematrix steht aus.
Davon getrennt blieben physische Cursor-Routingtasten in zwei praktischen
`dev.10`-Versuchen in Normal- und Insert-Modus ohne Reaktion; die Berichte
enthielten keinen Routingeintritt. Da beide geänderten Pakete fälschlich
dieselbe Dev-Kennung trugen, beginnt die eindeutige Nachprüfung mit `dev.11`.
Dieser Test bestätigte `dev.11` und zeigte `structuredOverlay: false` bei
ansonsten korrektem NVDA-Braillemodus, Fokus-Tether und Neuaufbau. Die
Regression für `dev.12` bildet NVDAs Konstruktionsreihenfolge nach: Das
provisorische Objekt trägt noch keine Terminalrolle, während eine von NVDA
bereits gewählte Klasse in `clsList` die Terminalrolle bereitstellt. Nur diese
Klassenliste darf das inaktive Add-on-Overlay einfügen; eine vorläufige
Objektrolle allein darf es nicht. Die `dev.16`-Regression führt diese
Komposition ausdrücklich vor Veröffentlichung des gemeinsamen Dienstes aus
und prüft, dass die erste authentifizierte `fullState` die bereits vorhandene
Fokusregion über `handleGainFocus(..., shouldAutoTether=False)` neu aufbaut,
ohne ein neues Fokusobjekt oder einen Fensterwechsel zu benötigen.
Der praktische `dev.12`-Test bestätigt anschließend Normalmodus-Routing und
zeigt im Insert-Modus angenommene Anfragen ohne unmittelbares Cursorereignis.
Die Regression für `dev.13` startet echtes Neovim, setzt eine UTF-8-Position
im Insert-Modus und erwartet sofort ein `cursorMoved` mit Rohmodus `i`.
Danach öffnet sie eine strukturierte `:`-Befehlszeile, routet innerhalb ihres
UTF-8-Inhalts und erwartet unmittelbar `commandLineChanged` mit der neuen
`commandLinePosition`, ohne den Befehlszeilentext auszuführen.
Der praktische Test bestätigte die Cursorbewegung, zeigte unter `dev.13` aber
eine falsche Meldung über gelöschten Befehlszeilentext. `dev.14` verschärft
deshalb die Regression: Zwischen Routinganfrage und bestätigter Position darf
kein einziges `commandLineChanged` einen vom ursprünglichen Inhalt
abweichenden Text tragen. `dev.15` prüft zusätzlich eine virtuelle Endzelle:
Im Insert-Modus muss der Braillecursor nach Unicode- und Tabinhalt auf einer
vorhandenen Leerzelle direkt hinter dem letzten Zeichen stehen; ihre
Routingtaste muss die exakte UTF-8-Bytespalte am Zeilenende senden. Leere
Insert-Zeilen und die Befehlszeilen-Endposition sind ebenfalls abgedeckt. Der
echte RPC-Test setzt diese Position mit Neovim 0.10.1 und 0.12.3.
Der praktische `dev.15`-Test bestätigte diese Normal-, Insert-,
Befehlszeilen- und Endpositionspfade. Das anschließend beobachtete Verbleiben
der nativen „PowerShell“-Region direkt nach F12 ist die durch `dev.16`
abgedeckte Startreihenfolge-Regression. Der praktische Folgetest zeigte einen
engeren leeren Startfall: Ein striktes NVDA-Modell verwirft eine Region mit
Cursorposition 0 und null Zellen als `No such position`. Die `dev.18`-
Regression startet deshalb mit einer leeren Normalmodus-`fullState`, erwartet
eine einzelne Zelle bei Cursorposition 0 und prüft `focusToHardLeft` sowie
`hidePreviousRegions`. Der Fokusaufbau darf keine `brailleError`-Diagnose
erzeugen.

Die Dateimanager-Regression für `dev.19` liefert einen
`fileManagerEntryChanged`-Zustand für ein Oil-Verzeichnis. Die Navigation muss
weiter gesprochen werden, darf aber `braille.handler.message` nicht aufrufen.
Die parallel aktualisierte dauerhafte Region muss Name und lokalisierten Typ
anzeigen. Ein separater Core-Test injiziert dazu eine Übersetzungsfunktion und
prüft lokalisierte Typ-, Markierungs- und Baumzustände.

Der Braille-Architekturaudit nach der praktischen Abnahme ergänzt zwei
Fail-open-Regressionen. Erstens darf `StructuredLineRegion.routeTo` weder den
lokalen noch den SSH-Client direkt aufrufen; es muss den unveränderlichen
`routeCursor`-Payload in den begrenzten `ControlDispatcher` legen. Der Test
verwendet deshalb einen Client, dessen `send_control` bei einem direkten
Aufruf fehlschlägt, und prüft ausschließlich den Dispatcherauftrag. Zweitens
darf ein wirkungsloser öffentlicher `braille.handler.message()`-Aufruf keine
bereits sichtbare fremde Braillemeldung als eigene übernehmen, deren Timer
stoppen oder sie später schließen. Nur eine nach dem Aufruf neu erzeugte und
weiterhin identische letzte Nachrichtenregion gilt als Eigentumsnachweis.

Der automatische Cursor-Nachlauf besitzt eine Paketregression: Eine
semantische Cursoränderung muss den öffentlichen
`braille.handler.handleCaretMove`-Pfad verwenden, während reine
Inhaltsaktualisierungen bei `handleUpdate` bleiben. Die strukturierte Region
muss eine `TextInfoRegion` sein, ihren Neovim-Inhalt jedoch über
`Region.update()` übersetzen. Dadurch kann NVDAs eigener Puffer den sichtbaren
Ausschnitt erst wiederherstellen und anschließend nur bei Bedarf zum
Braillecursor scrollen.

Die Braillezeilennavigation besitzt Abdeckung auf vier Ebenen:

- Protokolltests verwerfen zusätzliche Felder, unbekannte Richtungen,
  Zielregeln, Befehlszeilen-/Terminalmodi und übergroße virtuelle Spalten;
- lokale und SSH-Transporte handeln `brailleLineNavigation` nur mit einem
  entsprechend neuen Plugin aus und leiten ausschließlich den festen
  `moveBrailleLine`-Einstiegspunkt weiter;
- der gebaute Add-on-Test ruft NVDAs öffentliche Regionsmethoden
  `previousLine()` und `nextLine()` auf, unterscheidet direktes Auf/Ab von
  horizontalen Zeilenübergängen und erwartet Dispatcheraufträge statt
  Hauptthread-I/O. Die Abwärtsmarkierung ist exakt gebunden, einmalig,
  input-help-sicher und läuft im nächsten Ereigniszyklus aus;
- Lua- und echte RPC-Tests bewegen im Normal- und Insert-Modus über eine kurze
  Zwischenzeile. `curswant` muss die bevorzugte virtuelle Spalte behalten und
  sie auf der nächsten längeren Zeile wiederherstellen. Horizontale
  Zeilenübergänge müssen dagegen vorheriges Ende beziehungsweise nächsten
  Anfang wählen. Leerzeilen, Tabs, UTF-8-/Breitzeichen, Puffergrenzen,
  veralteter `changedtick` und Normal-/Insert-Zeilenende sind eingeschlossen.

Praktisch sind auf der BRAILLEX EL 80c horizontales Verschieben langer Zeilen,
Auf/Ab in Normal- und Insert-Modus, kurze Zwischenzeilen sowie Pufferanfang
und -ende zu prüfen. Diese Hardwareprüfung ist bis zur Rückmeldung nicht als
bestanden zu dokumentieren.

Der getrennte Braille-Explorationsmodus ergänzt folgende automatisierte
Ebenen:

- Validatoren akzeptieren nur feste Zeilenaktionen, vollständige
  Ursprungsidentität, begrenzte gewünschte Spalte, eine der drei festen
  Zielregeln und korrelierte Ergebnisse;
- Controllerprüfungen decken Toggle, Grenzen, UTF-8, veraltete oder
  überholte Antworten, begrenzte Pending-Queues, Dispatchfehler und die
  unveränderte kanonische Editorposition ab. Sie halten die virtuelle Anzeige
  bei echten Cursor- und Modusbewegungen sowie Änderungen auf anderen Zeilen
  fest. Auf der explorierten echten Cursorzeile übernehmen sie den
  vollständigen neuen zeilenbezogenen Zustand, einschließlich einer
  anschließenden Rückkehr vom Einfüge- in den Normalmodus, ohne virtuelle
  Zeile, Lesespalte oder Ausschnitt neu zu verankern. Routing verlangt für
  angezeigten Inhalt und kanonischen Zustand denselben aktuellen
  `changedtick`; veralteter Inhalt nach einer Änderung an anderer Stelle
  bleibt sichtbar, kann aber nicht geroutet werden. Sie schreiben
  `changedtick` nur im selben Kontext fort und lehnen Navigation im Befehls-
  und Terminalmodus weiterhin ab;
- Transporttests prüfen unabhängige Capability-Aushandlung, ausschließlich
  feste Plugin-Einstiegspunkte und das Entfernen einmaliger Ergebnisse aus
  Zustands-Caches;
- Pakettests prüfen das frei belegbare AppModule-Skript, fehlende
  Standardgeste, Off-Thread-Dispatch, exakte Fokus-/Instanzbindung,
  unabhängige Modus- und Auswahlcontroller für mehrere gleichzeitig
  verfolgte Instanzen, Wiederherstellung des sitzungseigenen Modus bei
  Rückkehr, getrennte virtuelle Zeilen und horizontale NVDA-Ausschnitte,
  deren Wiederherstellung nach Control- und Anwendungswechsel, Begrenzung
  eines gespeicherten Ausschnitts bei kürzerem Inhalt, hörbare Fokusansage
  ohne verdeckende Braillemeldung im Explorationsmodus, gezielten Reset nur
  der getrennten Runtime und das Verwerfen von Mehrfach-Routing- und
  Fokusfolgen beim Controlwechsel,
  Brailleaktualisierung, Routing aus der virtuellen Zeile, das Ausblenden
  eines scheinbaren virtuellen Cursors, den verbleibenden echten Cursor nach
  Routing und anschließender Bearbeitung derselben Zeile, das Löschen einer
  parallel gesetzten Caret-Nachlaufmarkierung nur im
  Braille-Explorationsmodus sowie das
  ausschließliche Weiterreichen nativer Caret-Navigationstasten im exakt
  unterdrückten Neovim-Control;
- Lua und echter Insert-Modus-RPC prüfen eine kurze und anschließend längere
  Zeile, das Insert-Zeilenende, einen nachträglich bewegten Echtcursor und
  Interleaving mit dem getrennten Sprachexplorationsmodus. Die allgemeine
  Navigationsspezifikation verlangt für eine Pfeiltaste genau ein
  semantisches Bewegungsereignis.

Die praktische Hardwareabnahme muss zusätzlich Umschalten, eindeutige
Modusmeldung, Auf/Ab ohne Echtcursorbewegung, Routing aus der virtuellen Zeile,
getrennte Moduswahl in mehreren lokalen und entfernten Sitzungen, Verlust der
virtuellen Position nur bei einem Neovim-internen Buffer-, Fenster- oder
Tabwechsel, Wiederherstellung von Position und horizontalem Ausschnitt nach
Sitzungs- und Anwendungswechsel, gezielten Reset nur bei Disconnect dieser
Sitzung und Unabhängigkeit von `NVDA+h/j/k/l` bestätigen.

Für den optionalen Braillenachlauf des Sprachexplorationsmodus prüfen Protokoll- und
Lua-Tests die begrenzte virtuelle Gesamtzeile. Core- und Pakettests prüfen,
dass sie nur bei aktiver Option die abgeleitete Brailleansicht ersetzt, beim
Abschluss wieder verschwindet und niemals den kanonischen Editorzustand
verändert. Der eigenständige Braille-Explorationsmodus muss Vorrang behalten;
ungültige, fehlende oder übergroße Zeilen dürfen den Brailleplan nicht
übernehmen.

Mehrfachbetätigungen derselben Routingtaste besitzen zusätzlich eine eigene
automatisierte Matrix:

- Der reine Zustandsautomat prüft unverzögerten ersten Druck, sofortige
  Wortaktion ohne konfigurierte Dreifachaktion, verzögerte Wortaktion mit
  Dreifachaktion, Ersetzung durch den dritten Druck, Tokenentwertung,
  Zeitablauf und veränderte Zielsignatur. Der Dienst validiert eine
  verzögerte Aktion unmittelbar vor dem Versand erneut gegen die aktuelle
  Instanz und den Editorzustand.
- Einstellungs- und Pakettests prüfen sichere Nullvoreinstellungen, alle
  Auswahlwerte, Profilpersistenz, NVDAs Mehrfachbetätigungsfrist sowie
  ausschließlich geplanten Dispatchertransport.
- Protokoll- und Transporttests verwerfen zusätzliche Felder, freie Befehle,
  ungültige Modi, Aktionen und Zeilenstarts, fehlende Capability und
  veralteten Zustand.
- Lua-Tests prüfen `dw`, `^d$`, `0d$`, Leerraum, Schreibschutz,
  UTF-8-Grenzen und `changedtick`. Ein echter Socket-Test prüft eine
  Wortlöschung mitten in einer Zeile mit Rückkehr in den Insert-Modus sowie
  `^c$` mit anschließendem Insert-Modus.

Der Referenzablauf für Mehrfachbetätigung wurde auf der BRAILLEX EL 80c
praktisch bestätigt. Die breitere praktische Matrix muss weiterhin jede
Kombination der drei Zeilenstarts, `cw`, `dw`, `c$`, `d$`, eine absichtlich
langsame Doppelbetätigung, einen Wechsel der Routingposition, unverändertes
Verhalten in der Befehlszeile und mehr als einen Brailletreiber abdecken.

### Fokusausgabe, Buffer und Terminal

Alle Werte von „Sitzungsfokus“ prüfen:

1. keine Ansage;
2. aktuelle Zeile;
3. aktueller Kontext, Modus und Verbindungsname.

Die Modusklänge bleiben eine getrennte Einstellung. Fokuswiederkehr,
`:bp`, `:bn`, `:terminal`, Neovim-Fenster und -Tabs dürfen weder ein einzelnes
Namenszeichen noch einen doppelten Modus sprechen. Unterschiedliche
Cursorpositionen im Ausgangsbuffer dürfen die Zielzeile nicht verändern.

Im eingebetteten Terminal zusätzlich prüfen:

- `i` in direkte Eingabe: vollständige Cursorzeile, Insertklang und native
  Shellausgabe;
- `Ctrl+\`, `Ctrl+N` sowie die frei belegte Ausstiegsgeste: genau ein
  Normal-Earcon und strukturierte Terminal-Normal-Navigation;
- `:echo`, `:lua print`, eine spätere `vim.notify`-Meldung und Unicode-
  Kommandozeilenecho;
- `:bd` bei laufendem Job, wirkungslose `:bp`/`:bn`, tatsächlicher
  Bufferwechsel, `exit` und Exitstatus.

### Frei belegbare Befehle

Windows Terminal fokussieren und erst danach NVDAs Tastenbefehldialog öffnen.
Die Produktkategorie und ihre frei belegbaren Befehle müssen dort sichtbar
sein. Nach Fokus auf eine fremde Anwendung dürfen sie nicht aus deren
AppModule-Skriptmenge aufgelöst werden. Nach Zuweisung einer Geste und Laden
der AppModule-Klasse darf NVDAs globale Benutzergestenkarte die gespeicherte
Zuordnung im Dialog andernorts weiter auflisten; ihre Ausführung muss trotzdem
begrenzt bleiben. Ein Fokuswechsel zwischen Auflösung und Ausführung muss die
Originalgeste genau einmal durchlassen; zwei Windows-Terminal-AppModule-
Instanzen dürfen keine Befehle füreinander ausführen. Nach dem Wechsel von
einem Build mit GlobalPlugin-Skripten werden die gewünschten Gesten einmal neu
zugewiesen.

### Zwischenablage

Die Produktkategorie muss in NVDAs Tastenbefehldialog auch aus einer fremden
Anwendung sichtbar sein. Eine dort zugewiesene Geste muss außerhalb eines
gültigen Neovim-Controls unverändert weiterlaufen.

Lokal und über SSH prüfen:

- zeichen-, zeilen- und blockweise Visual-Auswahl mit ASCII, Unicode, Emoji,
  Tabs und mehreren Zeilen;
- Register 0 nach `yy` und anderen Yanks;
- ein- und mehrzeiligen Windows-Text mit CRLF über `nvim_paste`;
- Register 0 mit und ohne abschließenden Zeilenumbruch und anschließendes `p`;
- Fokus-, Buffer-, Tab-, Pane- oder Moduswechsel während einer Anfrage;
- Ablehnung in Shell, Terminalbuffer, Dateimanager, readonly und
  `nomodifiable`;
- redigierte Diagnosen ohne übertragenen Text.

Jede Aktion darf höchstens einmal wirken. Es darf keine automatische
Synchronisation oder Wiederholung geben.

### Dateimanager

Für jeden praktisch zu bestätigenden Manager ein wegwerfbares Projekt mit
Quellcode, Tests, Notizen, Kapiteln und Medien verwenden. Namen enthalten
Leerzeichen, Umlaute, nichtlateinische Zeichen und Satzzeichen.

1. Verzeichnisse betreten oder aufklappen, Geschwister navigieren und Dateien
   öffnen.
2. Datei und Ordner erstellen, umbenennen, duplizieren, verschieben und
   löschen.
3. Mehrere Einträge markieren und eine Massenaktion ausführen.
4. Überschreiben oder Löschen mit Nein/Abbruch und danach mit Ja beantworten.
5. Konflikt, ungültigen Namen, readonly Ziel und Fokuswechsel während der
   Aktion prüfen.
6. Zwischen Manager, Datei, Terminal, WT-Tab, Pane und Fenster wechseln.

Bei Oil zusätzlich Entwurfsnamen vor `:w`, Grenzklänge mit `0`, `$`, `gg` und
`G` sowie den eigenen Bestätigungs-Float prüfen. Für nvim-tree kann
`select_prompts = true`, für Neo-tree `use_popups_for_input = false` deren
öffentliche `vim.ui`-Pfade nutzbar machen; das Add-on ändert diese Optionen
nicht selbst.

Erfolg darf nur aus einem belegten Abschlussereignis stammen. Nein oder Abbruch
muss das Projekt unverändert lassen. Vollständige Pfade oder Namen anderer
Einträge dürfen weder in kompakte Aktionsmeldungen noch Diagnosen gelangen.

### Lokalisierung und Braille

Mit englischem und deutschem NVDA mindestens Einstellungen, Werkzeugdialoge,
Aktivierung, Fehler, Fokusausgabe, Modi, Zwischenablage und Dateimanager
vergleichen. Dokumentinhalt und fremde Neovim-Meldungen werden nicht vom Add-on
übersetzt.

Eine physische Braillezeile bestätigt aktuelle Zeile, Unicode, Tabs, leere
Zeile, virtuelle Endposition, Startregions-Neuaufbau, Meldungen und Routing in
Normal-, Insert- und Befehlszeilenmodus. Auswahl, Dateimanagersegmente,
unterschiedliche Übersetzungstabellen, Treiber und weitere Braillezeilen
bleiben Teil der breiteren Matrix.
Beim Routing NVDAs Einstellung „Zeichen beim Cursor-Routing in Text sprechen“
jeweils ein- und ausschalten: Nur eine angenommene Routingaktion darf das
UTF-8-sicher erreichte Zeichen ansagen; abgelehnte Statussegmente,
Capability-/Fokusfehler und die ausgeschaltete Einstellung bleiben still. Nach
Rückkehr aus einer anderen Anwendung oder einem anderen Terminaltab muss die
asynchrone Fokusbestätigung die strukturierte Region vollständig neu aufbauen;
Routing ist anschließend in Normal- und Insert-Modus zu prüfen.

## Bewertung eines Fehlers

Eine falsche Sitzung, blockierter Hauptthread, unredigierter vertraulicher
Text, wiederholte Mutation oder Unterdrückung in einem ungebundenen Control ist
ein sicherheits- beziehungsweise isolationsrelevanter Defekt. Bei unklarem
Fokus- oder Lebenszustand ist fehlende Zusatzfunktion akzeptabler als das
Schließen des nativen NVDA-Pfads.
