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
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
ruff check .
ruff format --check .
python3 -m unittest discover -s protocol/python/tests -v
python3 -m unittest discover -s bridge/python/tests -v
python3 -m unittest discover -s nvda-addon/tests -v
tools/test_neovim_plugin.sh
python3 tools/build_nvda_addon.py
python3 tools/gettext_catalog.py check
tools/build_documentation.sh
git diff --check
```

Für die beiden Ruff-Befehle wird wie in NVDA 2026.1 Ruff 0.14.5 verwendet.
Die Konfiguration in `pyproject.toml` begrenzt die Prüfung auf die direkt von
NVDA geladenen Python-Module unter `nvda-addon/addon/`; andere Komponenten
behalten ihren eigenen konsistenten Stil.

`tools/test_neovim_plugin.sh` verwendet die verfügbare unterstützte
Neovim-Version. Für Änderungen an Versionsgrenzen sollten die Lua- und
TUI-Suiten zusätzlich mit Neovim 0.10.1 und 0.12.3 laufen. Eine installierte
Pluginversion darf den Checkout nicht überdecken; die Testskripte isolieren
deshalb `packpath`.

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

### Explorationsmodus

Komponenten aktualisieren und alle laufenden Neovim-Instanzen neu starten.
Mit gedrückter physischer NVDA-Taste `h/l`, `k/j` und
`Umschalt+h/l` prüfen. Erwartet wird:

- Zeichen, Zeilen und Wörter folgen nur der virtuellen Position; echter
  Cursor, Buffer, Modus, `changedtick` und Ansicht bleiben unverändert;
- nach gemischten Bewegungen spricht das Loslassen genau die zuletzt genutzte
  Einheit am echten Cursor;
- schnelles Loslassen, Autorepeat und Loslassen von NVDA vor der Richtungstaste
  geben kein nacktes `h/j/k/l` an Neovim weiter;
- Normal, Insert, Visual, Kommandozeile, Terminal-Normal und direkte
  Terminaleingabe bleiben lesbar;
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
- Fokuswechsel, Disconnect oder Neovim-Kontextwechsel beenden die Exploration
  still und können keine verspätete Ausgabe in der neuen Sitzung erzeugen.

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

Sobald Hardware verfügbar ist, aktuelle Zeile, Auswahl, Unicode, Tabs,
Meldungen, Dateimanagersegmente und Routing auf mehreren Braillezeilen prüfen.
Bis dahin bleibt jede Hardwareaussage ausdrücklich unbestätigt.

## Bewertung eines Fehlers

Eine falsche Sitzung, blockierter Hauptthread, unredigierter vertraulicher
Text, wiederholte Mutation oder Unterdrückung in einem ungebundenen Control ist
ein sicherheits- beziehungsweise isolationsrelevanter Defekt. Bei unklarem
Fokus- oder Lebenszustand ist fehlende Zusatzfunktion akzeptabler als das
Schließen des nativen NVDA-Pfads.
