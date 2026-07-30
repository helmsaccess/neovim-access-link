# Funktionsmatrix

Der Stand dieser Matrix ist Beta. Ein Eintrag bedeutet, dass die
Funktion implementiert und überwiegend automatisiert geprüft ist, nicht dass
bereits jede reale Konfiguration praktisch abgenommen wurde. Der
`z=`-Vorschlagspfad wurde mit einer physischen Braillezeile geprüft; eine
breite Hardware-, Treiber- und Übersetzungstabellenmatrix bleibt offen.

| Funktion | Ereignisquelle | benötigte Metadaten | NVDA-Ausgabe | implementiert | getestet |
|---|---|---|---|---|---|
| Windows-Terminal-Abschottung | physischer control-spezifischer F12-Nachweis, UIA-Fokus und korrelierter Neovim-Fokuskontext | Prozess, Fensterhandle, vollständige Runtime-ID, Instanz und Anfrage-ID | nativ in ungebundenen Controls; strukturiert erst nach Bestätigung | ja | automatisiert für mehrere Controls und Fenster; lokale/SSH-Tabs, horizontale/vertikale Split-Panes und mehrere Fenster praktisch bestätigt; vollständige Shell-Pane-Negativmatrix offen |
| Ausgabe beim Sitzungsfokus und Bufferwechsel | korrelierter `focusContext`; `BufEnter`-basiertes `contextChanged` bei neuem Buffer im gleichen Tab/Fenster | Zeilentext, Datei-/Spezialkontext, Modus, konfigurierter Verbindungsname; getrennte Quell-/Zielidentität | profilabhängig keine Ansage, aktuelle Zeile oder bisheriger Kontext; automatische Ziel-Cursorereignisse überschreiben die Ausgabe nicht; Tab/Fenster behalten eigene Ansagen | ja | automatisiert einschließlich verschiedener Quellspalten; Fokusauswahl und korrigierte Buffer-/Fenster-/Tabwechsel praktisch bestätigt |
| Moduswechsel | `ModeChanged` + `nvim_get_mode()` | Modus roh/kanonisch | Modus oder Ton | ja | automatisiert und Windows/NVDA |
| Cursor, Zeichen | `CursorMoved`/`CursorMovedI` | Byte-, Zeichen-, virtuelle Spalte; Zeile | Zeichen | ja | automatisiert und Windows/NVDA |
| Zeilennavigation | Cursorereignis + Zustandsdifferenz | alte/neue Position, Zeilentext, aktuelles Wort und Cursorzeichen | neue Zeile; aktuelles Wort und Cursorzeichen getrennt zuschaltbar | ja | automatisiert und Windows/NVDA einschließlich der vier Detailkombinationen |
| Wortnavigation | Zustandsdifferenz | Cursor, Wortgrenzen, Zeilentext | neues Wort; Cursorzeichen zuschaltbar | ja | automatisiert und Windows/NVDA einschließlich beider Detailkombinationen |
| Sprachexplorationsmodus | sechs feste, kontextbezogene NVDA-AppModule-Gesten + rein lesender Lua-Zustand | exakte Control-/Instanzbindung, Capability, Buffer/Fenster/Tab, `changedtick`, Modus sowie echter und virtueller Cursor | Zeichen, Zeile oder Wort an virtueller Position; beim Loslassen Zeichen beziehungsweise Wort/Zeile mit getrennt einstellbarem aktuellem Wort und Cursorzeichen am unveränderten echten Cursor | ja | Protokoll-, Lua-, Controller-, Dispatcher- und gebauter Add-on-Test; Zeichen-, Wort- und Zeilengrundpfad, rückwärtige Wortbewegung, Ursprungsklang und Detailauswahl praktisch unter Windows/NVDA bestätigt |
| Eingebaute `z=`-Rechtschreibvorschläge | belegter direkter `z=`-Befehl + begrenztes natives `msg_show`-UI-Ereignis | exakte Control-/Instanz-/Prompt-/Editoridentität, Capability, lückenlos nummerierte Einträge | kurze Öffnungsmeldung; zyklische Auswahl mit `NVDA+j/k`, Vorschlag ohne Nummer in Sprache/Braille, Annahme mit `NVDA+Eingabe`; Loslassen verwirft nur die lokale Auswahl; profilfähige einsbasierte Brailleposition mit Rückfall auf Modul 1 bei zu kurzer Anzeige und zellgenauer Linksbegrenzung, falls der übersetzte Vorschlag rechts nicht passt | ja | Parser-, Protokoll-, Transport-, Controller-, AppModule-, Braille- und gebauter Add-on-Test sowie echter Neovim-RPC-Test; praktisch unter Windows/NVDA einschließlich einer physischen Braillezeile bestätigt, breitere Hardwarematrix offen |
| Visual-Auswahl | Mode/Cursor + `getregion()`/virtuelle Spalten | Typ, Anker, Cursor, Text je Zeile | neuer/entfernter Text; vollständiger Block | ja | echtes TUI, automatisiert und Windows/NVDA |
| Explizites Copy/Paste | vier frei belegbare NVDA-Befehle + korrelierte Neovim-Steuerung | Bindung, Anfrage-ID, Buffer/Fenster/Tab, `changedtick`, Modus; Visual-Auswahl, Register 0 oder unbenanntes Register | Windows-Zwischenablage, `nvim_paste` beziehungsweise festes Register 0 als Speicher des unbenannten Paste-Registers; einstellbare Erfolgsrückmeldung | ja | Protokoll-, Lua-, Bridge- und gebauter Add-on-Test; alle vier Befehle lokal und über SSH praktisch bestätigt |
| Buffer/Fenster/Tabs | `BufEnter`/`WinEnter`/`TabEnter` | Name, Typ, Index, Anzahl, Flags | Kontext und Status | ja | echtes TUI und Speech-Test |
| Eingebettetes Terminal | `buftype=terminal`, `ModeChanged`, `TermOpen/Enter/Leave/Close`, `CmdlineLeave` + fester korrelierter Steuerbefehl | Buffer/Fenster/Tab, kanonischer `terminalNormal`-Modus, aktuelle Cursorzeile, Exit-Status, laufender Terminaljob und gelistete Buffer | profilfähiger `:terminal`-Einstieg; vollständige Zeile und nativer Passthrough mit Fokusklang bei direkter Eingabe; frei belegbarer Ausstieg, Modusklänge, `E89`-Schutz und wirkungslose Buffer-Navigation; Prozessende | ja | Protokoll-, Gate-, Add-on-, Bridge- und echter isolierter TUI-Test; Kernpfade praktisch unter NVDA bestätigt, Pager-Sonderfälle offen |
| Dateimanager | netrw-Dateisystemdaten beziehungsweise öffentliche Plugin-APIs und Ereignisse | UTF-8-sicher bytebegrenzter Name, Pfad, Typ, getrennte Markierungs-/Copy-/Cut-Zustände, Baumstatus; typisiertes Aktionsresultat nur aus belegtem Abschluss | Sprache und dauerhaft semantische, lokalisierte Braillezeile ohne verdeckende Navigationsmeldung, einschließlich Zustandsänderung am selben Eintrag und kompakter Aktion; Routing nur im eindeutig abgebildeten Namen | netrw, Oil, nvim-tree, Neo-tree, mini.files | Oil praktisch unter Windows/NVDA mit Neovim 0.12; übrige Manager automatisiert beziehungsweise isoliert und schrittweise praktisch zu prüfen; API-/Ereignisattrappen, Deduplizierung, inaktive Ziele, Erfolg/Oil-Fehler/Bündelung/Pfadminimierung sowie Unicode-/Routingfälle; Hardware-Braille offen |
| Textänderung | `TextChanged*` + Zustandsdifferenz | changedtick, alter/neuer Text | Eingabe/Löschen/Ersetzen | ja | automatisiert und Windows/NVDA |
| Meldungen und Prompts | UI-Nachrichten, Ex-Status, öffentlicher Lua-Aufruf `vim.fn.confirm()`, `vim.ui.input/select`; enger Oil-`oil_preview`-Floatfallback | Text, Priorität, Promptart, Auswahl; beim Oil-Fallback nur feste Aktion, Anzahl und Y/N | Sprache und Braille | ja; weitere pluginspezifische Floats und seltene Pager-Varianten zu prüfen | echtes TUI mit Annahme, Abbruch, Auswahl und pfadfreiem Oil-Fallback auf Neovim 0.10.1/0.12.3; reales Oil-Y/N auf 0.12.3 |
| Commandline | `ModeChanged`, `CmdlineChanged`/`CmdlineLeave`, `msg_show` | Typ (`:`, `/`, `?`), Inhalt, UTF-8-Befehlszeilenposition, Modus, Bufferstatus, UI-Meldung, unmittelbare Ex-Rückkehrmarkierung | eigener Ton, vollständiges NVDA-Zeichen-/Wortecho, eigener dauerhafter Brailleplan mit sichtbarem Präfix, Routing im Inhalt und virtueller Endzelle hinter dem letzten Zeichen, Fehler und Meldungen in Sprache/Braille; Rückkehrklang sowie profilabhängig Meldung allein, mit Zeile oder mit Kontext; Bufferwechsel mit Zielausgabe zusammengefasst | teilweise; Pager-Sonderfälle offen | gebauter Add-on-, Speech- und echter TUI-/RPC-Test einschließlich UTF-8-Routing, Endposition und Abgrenzung asynchroner Meldungen |
| Suche | `/`, `?`, `n`, `N` + `searchcount()` | Muster, Richtung, Index, Anzahl, Zeile, Spalte | Trefferzeile, Position und Zeilennummer | ja | echtes TUI und Speech-Test |
| Ersetzen | `CmdlineLeave` + `changedtick` | Substitute-Befehl, Status, Änderung | Bestätigung und Ersetzungston | ja | echtes TUI und Speech-Test |
| Matching Pairs | `%` + Cursorzustand | Gegenzeichen, Zeile, Spalte, Erfolg | Gegenzeichen/Zeile oder Fehlermeldung und Ton | ja | echtes TUI und Speech-Test |
| Folds | `z`-Befehle + `foldclosed()` | Aktion, Ebene, Start-/Endzeile | Foldstatus und Bereich | ja | echtes TUI und Speech-Test |
| Marks | `m`, `'`, `` ` `` + `getpos()` | Name, Zeile, Spalte, exakter Sprung | Setzen oder Zielzeile | ja | echtes TUI und Speech-Test |
| Register/Makros | `TextYankPost`, `RecordingEnter/Leave`, `@` | Register, Typ, Aufnahme-/Wiedergabestatus | kurze Statusausgabe | ja | echtes TUI und Speech-Test |
| Rechtschreibung/Grammatik | Neovim `spell` + `DiagnosticChanged` | Art, Quelle, Bytebereich, Wort | NVDA Sprache/Sound/Braille | ja | natives Spell, Diagnostics, TUI und NVDA-Mocks |
| allgemeine Diagnostics | `vim.diagnostic`, `DiagnosticChanged`, native Diagnostic-Navigation und fünf Access-Link-Befehle | Quelle beziehungsweise Namespace, Schwere, optionaler Code, Bytebereich, Text, Index und Anzahl | vollständige Diagnose in Sprache/Braille; Hintergrundänderungen stumm | ja | gehärteter Vertrag, Navigation und Speech; reale gepinnte nvim-lint-/ALE-Läufe für C, Python, Bash, Go, Rust, Ruby und Markdown sowie none-ls-LSP-Brücke auf Neovim 0.10.1/0.12.3; Windows/NVDA-Praxis offen |
| Braille aktuelle Zeile | strukturierter Zustand | Zeilentext, tabstop, Cursor | Liblouis-Region; im Insert-Modus virtuelle Leerzelle für Cursorpunkte 7+8 direkt hinter dem Zeilenende; auf leerer Normalmoduszeile eine einzelne cursortragende Zelle bei Bytespalte 0; Windows-Terminal-Fokuskontexte werden ausgeblendet | ja | automatisiert einschließlich Unicode, Tabs, leerer Insert-/Normalzeile und erstem authentifiziertem Fokusaufbau; mit einer physischen Braillezeile praktisch bestätigt |
| Braille Auswahl | `selectionChanged` + `vim.region()` | zeilenlokale Bytegrenzen | feste Auswahlpunkte 7+8 durch NVDA; Sichtbarkeit nach NVDAs Einstellung | ja | automatisiert; breitere praktische Auswahlmatrix offen |
| Braille Routing | Routingtaste | Braille-zu-Text-Offset, festes Ziel Editor/Befehlszeile, exakter Rohmodus, validierter Rückkanal und UTF-8-sicheres Quellzeichen | unmittelbare Cursorbewegung in Normal-, Insert- und Befehlszeilenmodus, einschließlich der virtuellen Endzelle hinter dem letzten Zeichen; bei NVDAs aktivierter Einstellung „Zeichen beim Cursor-Routing in Text sprechen“ Ansage des erreichten Zeichens | ja | automatisiert für Normal/Insert/Befehlszeile, Unicode, Tabs, leere Zeilen, Endposition, semantische Dateimanagerzeilen, deaktivierte Zeichenansage, Ablehnungswege und ausgelagerten Transport; alle drei Modi, Endposition und Startregions-Neuaufbau praktisch mit einer physischen Braillezeile bestätigt |
| Mehrfachbetätigung einer Routingtaste | dieselbe Routingtaste zwei- oder dreimal innerhalb NVDAs Mehrfachbetätigungsfrist | exakte Routingsignatur, lokaler Zähler und feste Wort-/Zeilenaktion | optional `cw`/`dw` oder `c$`/`d$` ab Routingposition, erstem Nicht-Leerzeichen oder Zeilenanfang; sichere Voreinstellung ohne Bearbeitung | ja | Zustandsautomat, Einstellungen, Protokoll, lokaler/SSH-Transport, gebautes Add-on, Lua und echter Insert-RPC automatisiert; Referenzablauf auf BRAILLEX EL 80c praktisch bestätigt, vollständige Befehls-/Zeilenstart-/Zeitablauf- und Mehrtreibermatrix offen |
| Braillezeilen-Navigation | NVDAs Standardbefehle für Scrollen und vorherige/nächste Zeile | horizontales NVDA-Fenster; an der Zeilengrenze feste Zielregel Anfang/Ende; für Auf/Ab Richtung, Ausgangszeile und bevorzugte virtuelle Spalte | Links/Rechts verschiebt die lange Zeile und wechselt über Grenzen zum vorherigen Ende beziehungsweise nächsten Anfang; Auf/Ab bewegt im Braille-Cursormodus den echten Neovim-Cursor um eine Zeile mit Spaltenerhalt über kurze Zeilen | ja | Protokoll, lokaler/SSH-Transport, Controller, gebautes Add-on, Lua und echter Insert-RPC einschließlich Leerzeilen, Tabs, UTF-8/Breitzeichen und Einmalmarkierung automatisiert; Korrektur praktisch auf BRAILLEX EL 80c bestätigt |
| Braille-Explorationsmodus | frei belegbares Windows-Terminal-AppModule-Skript und dieselben öffentlichen Regionsmethoden | pro Neovim-Instanz eigener Modus, vollständige Echtcursor-Ursprungsidentität für den Start; danach eigene Explorations-ID und Aktionsfolge bei unverändertem Buffer/Fenster/Tab sowie validiert fortgeschriebenem `changedtick`; virtuelle Zeile und gewünschte Spalte; öffentlicher `BrailleBuffer.windowStartPos`; öffentliche `TextInfoRegion.pendingCaretUpdate`-Markierung | Auf/Ab liest benachbarte Pufferzeilen ohne Echtcursorbewegung; lokale und entfernte Sessions wählen Modus, virtuelle Position und horizontalen Ausschnitt unabhängig; Control- und Anwendungswechsel stellen die Ansicht der jeweiligen Session wieder her; echte Cursor- und Modusbewegungen sowie Änderungen auf anderen Zeilen verändern die virtuelle Position nicht; Bearbeitungen auf der explorierten echten Cursorzeile aktualisieren vollständigen Inhalt und aktuellen Modus ohne Neuverankerung oder Ausschnittsprung; der gewählte Ausschnitt folgt keinem parallelen nativen Caretereignis; kein scheinbarer virtueller Braillecursor; Routing übernimmt die gewählte virtuelle Position nur aus einem zum aktuellen `changedtick` passenden Zeilenstand und wird unmittelbar vor verzögerten Mehrfachaktionen erneut validiert; unabhängig vom Sprachexplorationsmodus | ja | Validator, Controller, Capability, lokaler/SSH-Transport, gebautes Add-on, Lua und echter Insert-RPC einschließlich Interleaving, Instanzisolation, positions- und ausschnittstreuer Rückkehr, gezieltem Disconnect-Reset, Cursor- und Texteingabeentkopplung, vollständiger Zeilenaktualisierung nach Bearbeitung und Moduswechsel, Ausschnittserhalt, Ablehnung veralteten Routings und verzögerter Neuvalidierung automatisiert; grundlegender Hardwarepfad auf BRAILLEX EL 80c bestätigt, jüngste Editier-/Routing-Randfälle, praktische Mehrsession-Abnahme und breitere Hardwarematrix offen |
| Modus-Earcons | `modeChanged`, `commandLineChanged`, Terminal-`contextChanged` oder bestätigter `focusContext` | kanonischer Modus einschließlich `terminalNormal` und `commandLine` | NVDA `focusMode.wav` für Insert/direkte Terminaleingabe, `browseMode.wav` für Normal/Terminal-Normal und kurzer 600-Hz-Kommandozeilenton | ja | automatisiert; Gate-Reihenfolge und Ereignisdeduplizierung geprüft |
| Einrückung | Zeilentext + `shiftwidth` | vorherige/neue Einrückung | NVDA-Modus Sprache/Töne/Beides, semantische Ebene | ja | automatisiert |
| Completion-Menü | Lebenszyklus und Auswahl per `CompleteChanged`/`CompleteDonePre`/`InsertLeave`; bei fehlender Dokumentation ein zusätzlicher öffentlicher `completionItem/resolve`-Aufruf für den ausgewählten ursprünglichen LSP-Kandidaten | ausgewählter Kandidat, Index, Anzahl, lokalisierter Typ, Parameter, Quelle und Dokumentation | Sprache, Braille, NVDA-Vorschlagsklänge; stille Aktualisierung nachgeladener Dokumentation | ja | echtes TUI, Auswahl jenseits von Eintrag 200, UTF-8-Grenzen und alle 25 LSP-Typen; Resolve-Vertrag und Abbruch listenerfrei auf Neovim 0.10.1/0.12.3, echte Pyright-Antwort separat bestätigt, erneute Windows/NVDA-Abnahme offen |
| Command-line-Wildmenu | `ext_popupmenu` | Kandidat, Index, Anzahl | Standard-Menüausgabe und Klänge | ja | echtes TUI automatisiert |
| `vim.ui.select/input` | zentrale Neovim-API | Prompt, Einträge, Ergebnis/Abbruch | Sprache, Braille und Menüklänge | ja | echtes TUI automatisiert |
| LSP-Signatur | enger Beobachter für den Handlerpfad von Neovim 0.10 und den `buf_request_all`-Antwortcallback von 0.11/0.12 | Signatur, aktiver Parameter als Text oder UTF-16-Offsetpaar, Alternativen mehrerer Clients | Signatur und Parameter, dedupliziert; stiller Schließzustand | ja | listenerfreie Kompatibilitätstests auf Neovim 0.10.1 und 0.12.3; realer LSP-Server und Windows/NVDA noch praktisch zu prüfen |
| LSP-Hover | enger Beobachter für den Handlerpfad von Neovim 0.10 und ausschließlich `textDocument/hover` im kombinierten Antwortcallback von 0.11/0.12 | erste aussagekräftige Zeile, begrenzte vollständige Markup-/MarkedString-Dokumentation, Quellenanzahl | kurze automatische Sprache/Braille; vollständiger Inhalt über den vorhandenen Dokumentationsbefehl; stilles Schließen bei Kontextwechsel | ja | listenerfreie Parser-, Deduplizierungs-, Mehrclient- und Kompatibilitätstests auf Neovim 0.10.1/0.12.3; realer LSP-Server und Windows/NVDA offen |
| LSP-Serverstatus | expliziter Befehl `:NvimNvdaLspStatus` und `vim.lsp.get_clients()` | höchstens 32 eindeutige, UTF-8-sichere Clientnamen des aktuellen Buffers | kurze Sprache/Braille oder ausdrückliche Meldung ohne Client | ja | listenerfreier Lua- und Speech-Test auf Neovim 0.10.1/0.12.3; automatische Fortschrittsansagen bewusst vermieden |
| nvim-cmp/blink.cmp | Öffnen/Schließen per Pluginereignis; öffentliche Auswahlabfrage alle 35 ms nur solange das Menü offen ist | nur ausgewählter Kandidat, vollständige Anzahl, alle LSP-Typen, Quelle und vorhandene Dokumentation | unmittelbare Standard-Öffnen-/Schließen-Klänge, Standard-Menüausgabe und stiller Dokumentationscache | ja | Attrappentests mit verzögert verfügbaren Kandidaten plus echte Modulanbindung: aktueller `nvim-cmp` und `blink.cmp` v1.10.2 auf Neovim 0.10.1/0.12.3, vorläufiger `blink.cmp`-v2-Zweig mit `blink.lib` auf 0.12.3; vollständige TUI-/Windows-/NVDA-Abnahme offen |
| Quickfix/Location List | stabile Fensterdaten | Listentyp, aktuelle Zeile | Typ und Eintrag | ja | echtes TUI und Speech-Test |
| Ex-Fehler bei `:q` | `CmdlineLeave` + Bufferstatus | Kommando, `modified` | E37 mit Hinweis auf Speichern oder `:q!` | ja | echtes TUI automatisiert |

Der Timer in den `nvim-cmp`- und `blink.cmp`-Adaptern ist eine dokumentierte
Notlösung. Er beginnt erst nach dem jeweiligen öffentlichen Menü-Öffnen-
Ereignis und endet beim öffentlichen Schließen-Ereignis. Öffnen und Schließen
des zugänglichen Menüzustands und damit die Standardklänge hängen nicht vom
ersten erfolgreichen Tick ab. Eine während des Aufbaus kurz leere oder
unsichtbare öffentliche Itemansicht erzeugt deshalb kein falsches
Schließen-/Öffnen-Paar. Der Timer ersetzt nicht den eingebauten
Neovim-Menüpfad und läuft nie außerhalb eines geöffneten Pluginmenüs. Pro Tick
wird nur der ausgewählte Kandidat normalisiert.
`nvim-cmp` benötigt weiterhin zwei mit `cmp.sync()` umwickelte öffentliche
Abfragen. Fehler, langsame Ticks, maximale Tickdauer und aktive API-Variante
erscheinen deshalb ohne Kandidateninhalt in Diagnosebericht und
`:checkhealth`. Sobald ein verlässliches öffentliches Ereignis jede
Auswahländerung liefert, soll diese Abfrage entfallen.

Neovims eingebaute LSP-Completion schreibt aufgelöste Dokumentation über die
experimentelle interne Funktion `nvim__complete_set()` in das Vorschaufenster.
Eine reale TUI-Reproduktion bestätigt, dass der gesetzte `info`-Text danach
nicht in `complete_info().items` erscheint. Wiederholtes Lesen dieser
öffentlichen Menüansicht kann die Dokumentation daher nicht gewinnen.

Der native Access-Link-Pfad verwendet stattdessen den von Neovim im
ausgewählten Menüeintrag bereitgestellten ursprünglichen LSP-Kandidaten und
den Clientbezug. Fehlt dort Dokumentation und unterstützt der Client Resolve,
wird genau eine zusätzliche Access-Link-eigene, öffentliche und asynchrone
`completionItem/resolve`-Anfrage gestellt. Auswahlwechsel, `CompleteDonePre`
und `InsertLeave` invalidieren und stornieren eine noch laufende Anfrage. Nur
eine Antwort für die weiterhin aktuelle sichtbare Auswahl ergänzt die
Modellkopie und erzeugt ein stilles `menuItemUpdated`. Der zusätzliche
Resolve-Pfad besitzt weder
Menülebenszyklus noch Klänge und blockiert Neovim oder NVDA nicht.

Bei `nvim-cmp` wird die öffentlich zugängliche `entry.completion_item`-Tabelle
beobachtet; eine spätere Resolve-Antwort aktualisiert die Dokumentation ohne
erneute Ansage. `blink.cmp` liefert die intern aufgelöste Kopie nicht über
seine öffentliche Item-API. Ursprüngliche Dokumentation funktioniert dort,
reine Resolve-Dokumentation bleibt eine dokumentierte Upstream-Abhängigkeit.
Ghost-Text-only ohne geöffnetes Menü gehört nicht zum Adaptervertrag.

## Einrückung

Einrückung wird wie bei NVDA-Dokumenten nur gemeldet, wenn sie sich gegenüber
der vorherigen Zeile ändert. Die NVDA-Einstellung unter
„Dokument-Formatierungen“
„Zeileneinrückung“ steuert die Ausgabe:

- „Aus“ erzeugt keine zusätzliche Ausgabe.
- „Sprache“ meldet `indentation level N`; die Ebene wird aus Neovims
  `shiftwidth` berechnet.
- „Töne“ verwendet NVDA-kompatibel 220 Hz als Grundton und je Leerzeichen einen
  Viertelton beziehungsweise je Tabulator vier Vierteltöne mehr.
- „Sprache und Töne“ kombiniert beide Ausgaben.

Der 220-Hz-Grundton für keine Einrückung wird nur beim Übergang von einer
eingerückten auf eine nicht eingerückte Zeile ausgegeben, nicht fortlaufend auf
jeder Zeile der Ebene null. Die konfigurierte NVDA-Einrückungstondauer wird
übernommen.

## Rechtschreibung und Grammatik

Die Ausgabe folgt NVDA 2026.1.1 statt eine eigene Option einzuführen:

- `reportSpellingErrors2` steuert Sprache (`1`), Sound (`2`) und Braille (`4`)
  als Bitmaske unabhängig. Navigation und Exploration verwenden denselben
  Präsentationspfad für alle Werte von `0` bis `7`.
- Der Sound ist NVDA-eigenes, beim Add-on-Start in den RAM geladenes
  `waves/textError.wav`.
- Der Tippton wird nur nach Abschluss eines fehlerhaften Wortes gespielt, wenn
  NVDA „Sound für Rechtschreibfehler während der Eingabe“ aktiviert hat und der
  Sprachmodus weder „Aus“ noch „Bei Bedarf“ ist.
- Zeichenbewegung meldet Eintritt und Austritt aus einem Fehler. Jede
  semantische Wortbewegung und Wortexploration meldet den Fehlertyp am
  erreichten Wort; der lokalisierte Hinweis ergänzt dabei dieselbe unteilbare
  Ausgabe wie das Wort und kann nicht durch dessen Navigationsabbruch verloren
  gehen. Zeilenlesen meldet vorhandene Fehler, auch wenn der Cursor nicht darin
  steht.
- Braille verwendet NVDA-konform `⠑`/`⡑` für Rechtschreib- und `⠛`/`⡛` für
  Grammatikfehler.

Für die native `z=`-Vorschlagsliste hält ein eigener Controller nur die
flüchtige lokale Auswahl. Sprache und Braille entfernen die Nummer; angenommen
wird ausschließlich der intern validierte Index. Eine kurze Sprachmeldung
bestätigt einmalig die erkannte, nicht leere Liste. Die Liste ist keine
allgemeine Interpretation beliebiger Neovim-Meldungen.

Direkt unterstützt wird `:setlocal spell`. Außerdem werden Diagnostics der
Quellen Spellwarn, CSpell/cspell-lsp, Codespell, Typos, LTeX/MORFOLOGIK und
Harper erkannt. Damit ist insbesondere `spellwarn.nvim` passend: Es überführt
Neovims eigene, `spelllang`- und `spellfile`-abhängige Ergebnisse in die
offizielle Diagnostic-API. Das ältere `cspell.nvim` ist archiviert; dessen
Repository empfiehlt inzwischen cspell-lsp, Typos oder Harper. Coc-eigene
Diagnostics sind nur zugänglich, wenn sie zusätzlich nach `vim.diagnostic`
gespiegelt werden.

Andere Diagnostic-Produzenten können Fehler eindeutig kennzeichnen:

```lua
user_data = { nvim_nvda_kind = "spelling" } -- oder "grammar"
```

## Allgemeine Diagnostics und Linter

Der gemeinsame Vertrag endet an Neovims öffentlicher `vim.diagnostic`-API.
Access Link liest keine privaten Tabellen von `nvim-lint` oder ALE und startet
keine Prozesse. Diagnosen werden UTF-8-sicher begrenzt, Bereiche und Typen
validiert und über alle Namespaces deterministisch geordnet. Bei
überlappenden Bereichen entscheidet zuerst die höchste Schwere, dann der
kleinste einschließende Bereich und anschließend ein stabiler
anbieterneutraler Schlüssel. Eine fehlende Quelle fällt auf den begrenzten
Neovim-Namespace-Namen zurück. Die geordnete Liste wird pro Buffer gehalten
und bei `DiagnosticChanged` beziehungsweise `BufWipeout` verworfen; normale
Cursorbewegungen sortieren große Diagnosemengen daher nicht erneut.

Die realen Providerverträge führen Clang-Tidy, Ruff, ShellCheck, Staticcheck,
Clippy, RuboCop und `markdownlint-cli2` über `nvim-lint` sowie ALE aus und
prüfen zusätzlich die echte `none-ls.nvim`-LSP-Brücke mit einer eingebauten
Quelle. Alle drei Plugins publizieren die Ergebnisse in `vim.diagnostic`; ein
pluginspezifischer Adapter ist deshalb weder vorhanden noch erforderlich.
ALE wählt `markdownlint-cli2` über seine öffentliche
Executable-Konfiguration, da der vorhandene Markdownlint-Handler dessen
Ausgabe versteht. Dasselbe Modell kann später LSP-Diagnosen von `gopls`,
`rust-analyzer` oder `ruby-lsp` sowie weitere Linter über geeignete
Diagnoseproduzenten aufnehmen. Eine neue Sprache allein erfordert keine
Änderung an Access Link. Ein Adapter wird erst geprüft, wenn ein relevanter
Produzent nachweislich keine semantische Spiegelung anbietet.

`DiagnosticChanged` aktualisiert den Zustand ohne automatische Sprachflut.
Die fünf Befehle `:NvimNvdaDiagnosticPrevious`, `Next`, `First`, `Last` und
`Current` erzeugen eine eindeutige vollständige Ansage und verändern keine
Benutzermappings. Neovim 0.12 wird zusätzlich über den öffentlichen
`jump.on_jump`-Hook beobachtet; Neovim 0.10 verwendet die kompatiblen
`goto_prev()`-/`goto_next()`-Aufrufe und die bestehende Beobachtung seiner
nativen Vorwärts-/Rückwärtsnavigation.

## Textpositionen

Neovims Cursor-Spalte wird als nullbasierter UTF-8-Byteoffset übertragen. Der
Protokollkern validiert, dass dieser Offset keine UTF-8-Sequenz teilt, und
berechnet separat die Unicode-Codepoint- und UTF-16-Spalte. Die virtuelle Spalte
muss Neovim liefern, weil sie von Tabs und Anzeigeoptionen abhängt. Codepoints
sind noch keine Graphemcluster: eine kombinierende Marke kann daher ein eigenes
Zeichen sein; die spätere Speech-Planung muss zusammengehörige Grapheme bewusst
behandeln.

Dateimanageransagen verwenden semantischen Namen, Typ und Zustand statt
Dekorationen. Ist kein Eintrag vorhanden, wird für den Fokuskontext höchstens
der letzte Name von `currentDirectory` beziehungsweise `root` ausgegeben;
vollständige lokale, entfernte oder virtuelle Pfade werden nicht gesprochen.
Ein editierbarer Oil-Eintrag verwendet den aktuellen öffentlichen
`parsed_name`; Zeilen- und Dateigrenzbewegungen behalten ihre Klänge, ohne
Icons oder Zusatzspalten zu sprechen. Der bestätigte Pfad ändert sich erst mit
Oils eigener gespeicherter Aktion. Dieser Oil-Pfad ist unter Windows/NVDA mit
Neovim 0.12 praktisch bestätigt und bildet eine solide Grundlage. Für netrw,
mini.files, nvim-tree und Neo-tree liegt noch keine praktische Windows-Abnahme
vor.
