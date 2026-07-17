# Changelog

Begriffshinweis: „Registry“ bezeichnet in allen historischen Einträgen die
dateibasierte Neovim-Sitzungsregistrierung aus kurzlebigen JSON-Dateien, niemals
die Windows-Registry. Das Produkt verwendet keine Schlüssel unter `HKCU` oder
`HKLM`.

## 0.93.0 (Beta)

- Die Produktversion wurde auf ausdrückliche Vorgabe auf `0.93.0` angehoben.
  Der Releasekanal bleibt unverändert `beta`; der Gesamtstand bleibt zwischen
  Alpha und Beta und wird nicht als stabil eingestuft.
- Enthält die praktisch bestätigten Terminal- und Bufferwechsel-Härtungen,
  strukturierte Kommandozeilen- und Prozessmeldungen, semantische
  Fenster-/Tab-Kontextausgabe sowie die korrigierte erneute F12-Zuordnung von
  einer beendeten lokalen zu einer SSH-Neovim-Sitzung.

## 0.92.0-dev.11 (Featurebranch-Testbuild)

- Eine getrennte, aber noch gemerkte lokale Verbindung zwingt eine neue
  F12-Zuordnung nicht mehr in die lokale Sitzungssuche. Nur eine weiterhin
  authentifizierte Bindung darf ihren lokalen oder SSH-Zieltyp vorgeben. Nach
  dem Ende von lokalem Neovim kann dasselbe WT-Control daher per frischem F12
  wieder gegen alle inventarisierten lokalen und SSH-Sitzungen aufgelöst
  werden; die neue Verbindung ersetzt die veraltete Instanz kontrolliert.
- Die Diagnose unterscheidet nun `selected` von `selectedAuthenticated`, damit
  eine vorhandene Zuordnung nicht mehr mit einer lebenden Neovim-Verbindung
  verwechselt wird. Temporäre Transportabbrüche bleiben fail-open und werden
  nicht allein durch einen Netzwerkstatus automatisch umgebunden.
- Die praktische Abnahme bestätigte die erneute Zuordnung vom beendeten lokalen
  Neovim zur SSH-Sitzung im selben WT-Control ohne weitere Auffälligkeiten.

## 0.92.0-dev.10 (Featurebranch-Testbuild)

- Die Kontextwahl fasst beim Wechsel zwischen Neovim-Fenstern und -Tabs
  Zielposition, Datei- oder Spezialkontext, Änderungs-/Schreibschutzstatus,
  Modus und Verbindungsname in genau einer Ansage zusammen. Ein
  vorausgehendes Modusereignis bleibt dabei sprachlich still; der unabhängige
  Modusklang bleibt erhalten. `No announcement` und `Current line` ändern
  ihr Verhalten nicht.
- Kurze Dateinamen werden mit `file` eindeutig bezeichnet, beispielsweise
  `file T, modified, normal mode`. Terminalpuffer nennen nur den semantischen
  Modus, also `terminal mode` oder `terminal-normal mode`, statt der doppelten
  Form `terminal, terminal mode`. Bereits vorhandene Terminalfenster werden
  nicht mehr mit einem neu durch `:terminal` erzeugten Puffer verwechselt.

## 0.92.0-dev.9 (Featurebranch-Testbuild)

- Die Kontextwahl beim Einstieg über `:terminal` bleibt jetzt auch dann exakt
  einmalig, wenn `contextChanged` vor dem abschließenden
  `terminalNormal`-Modusereignis eintrifft. Initialer Terminaltext und das
  automatische Cursorereignis können danach kein einzelnes „T“, „M“ oder
  anderes Zeilenzeichen ergänzen.
- Der Neovim-Tastenbeobachter behandelt Text in Kommandozeile und direkter
  Terminaleingabe nicht mehr als mögliche Normalmodusbewegung. Damit kann
  etwa das abschließende `l` aus `:terminal` kein späteres Cursorereignis als
  ausdrücklich ausgelöste Zeichenbewegung fehlklassifizieren.

## 0.92.0-dev.8 (Featurebranch-Testbuild)

- Der mit `:terminal` erzeugte Terminalbuffer verwendet beim Einstieg dieselbe
  profilfähige Auswahl wie andere Bufferwechsel. „Keine Ansage“ bleibt still,
  „Aktuelle Zeile“ wartet ereignisgetrieben auf die erste tatsächliche
  Terminalzeile und die Kontextwahl meldet Terminal-Normalmodus und
  Verbindung. Ein automatisches Folge-Cursorereignis kann die Zeile nicht mehr
  durch ihr erstes Zeichen ersetzen.
- Beim anschließenden Eintritt in die direkte Terminaleingabe mit `i` wird die
  vollständige Zeile am Terminalcursor einmal ausgegeben. Sie ersetzt dort
  eine konkurrierende gesprochene Modusansage; der Insert-/Fokusklang und der
  fail-open Passthrough bleiben erhalten.

## 0.92.0-dev.7 (Featurebranch-Testbuild)

- Bei `:bp`, `:bn` und den entsprechenden vollständigen Bufferbefehlen werden
  kurzlebige gesprochene Rückkehrmodi nicht mehr vor die konfigurierte
  Zielausgabe gestellt. „Keine Ansage“ bleibt nach dem Kommando still,
  „Aktuelle Zeile“ spricht nur die vollständige Zielzeile und die Kontextwahl
  spricht Ziel, Modus und Verbindung genau einmal. Der unabhängige Modusklang
  und die Ansage beim Eintritt in die Kommandozeile bleiben erhalten.
- `commandLineType` unterscheidet Ex-Befehle von gleich geschriebenen Suchmustern;
  `/bn` löst daher keine Bufferwechsel-Unterdrückung aus. Ein wirkungsloser
  Bufferbefehl im einzigen Terminalbuffer spricht weiterhin seinen
  strukturierten Hinweis, aber keinen abgebrochenen „terminal-normal mode“.

## 0.92.0-dev.6 (Featurebranch-Testbuild)

- Ein nach `BufEnter`/`BufWinEnter` automatisch folgendes `cursorMoved` kann
  die konfigurierte Zielzeile nicht mehr durch das einzelne Zeichen an der
  Zielspalte ersetzen. Die Ansage ist damit unabhängig von der Cursorposition
  im Ausgangsbuffer.
- `textChanged` vergleicht keine Zeilen verschiedener Buffer mehr. Ein beim
  Sichtbarwerden des Zielbuffers eintreffendes Änderungsereignis wird nicht
  als Eingabe oder Ersetzung des Ausgangstextes ausgegeben.

## 0.92.0-dev.5 (Featurebranch-Testbuild)

- Erfolgreiche Bufferwechsel im selben Tab und Fenster, etwa mit `:bp` oder
  `:bn`, verwenden nun ebenfalls die profilfähige Fokusauswahl: keine Ansage,
  aktuelle Zielzeile oder Zielkontext mit Modus und gespeichertem
  Verbindungsnamen. Die Quelle bleibt `BufEnter`/`contextChanged`; Polling wird
  nicht eingeführt.
- Tab- und Fensterwechsel behalten ihre eigenen Kontextansagen. Modusklänge
  bleiben unabhängig von der gewählten Fokus-/Bufferwechselausgabe.

## 0.92.0-dev.4 (Featurebranch-Testbuild)

- UI-Protokollmeldungen werden unter Neovim 0.12 erst nach Verlassen des
  `vim.ui_attach`-Fast-Event-Callbacks ausgewertet. Dadurch erzeugen
  Zustandsabfragen weder `E5560` noch einen versteckten Enter-Hinweis; Befehle,
  Suche und nachfolgende Meldungen bleiben bedienbar.
- Der lange reale TUI-Test leert den PTY-Ausgabepuffer vor weiteren physischen
  Tasten. Neovim 0.12 kann dadurch nicht mehr an Testausgabe blockieren; das
  ist eine Härtung des Testtreibers, keine Produktverzögerung.

## 0.92.0-dev.3 (Featurebranch-Testbuild)

- Der Eintritt in die Neovim-Kommandozeile besitzt einen eigenen kurzen
  600-Hz-Ton. Der Rückweg aus der Kommandozeile im Terminalkontext verwendet
  den Normalmodusklang; der Zwischenzustand beim Erzeugen eines neuen
  Terminalbuffers erzeugt weiterhin keinen doppelten Klang.
- Ein exaktes `:bd` auf einem noch laufenden Terminaljob meldet vor Neovims
  blockierendem Enter-Hinweis strukturiert `E89`, dass der Buffer nicht
  geschlossen wurde. `:bd!` bleibt eine ausdrücklich destruktive
  Nutzerentscheidung und wird nie automatisch ausgeführt.
- Buffer-Navigationsbefehle wie `:bp` oder `:bn` melden im Terminalkontext
  verständlich, wenn kein anderer gelisteter Buffer vorhanden ist. Bei einem
  tatsächlichen Wechsel bleibt `BufEnter` die ereignisgetriebene Quelle der
  Zielansage; Polling und Terminal-Screen-Scraping werden nicht eingeführt.

## 0.92.0-dev.2 (Featurebranch-Testbuild)

- `modeRaw=nt` wird nicht länger mit dem Normalmodus eines Dateibuffers
  zusammengefasst, sondern als eigener kanonischer `terminalNormal`-Zustand
  gesprochen und mit genau einem Normalmodusklang bestätigt.
- Das Zeichen-Echo der Neovim-Kommandozeile verwendet nun deren eigene
  UTF-8-Byteposition statt der unveränderten Editor-Cursorspalte. Dadurch
  werden Folgetext und Unicode gemäß NVDAs Zeichen-/Wortecho ausgegeben.
- Ein frei belegbarer NVDA-Befehl ohne Standardgeste verlässt direkte
  Terminaleingabe über die feste Neovim-Operation `stopinsert`. Lokaler und
  SSH-Pfad prüfen Anfrage-ID, Instanz, fokussierte Control-Bindung, Buffer,
  Fenster, Tab und exakten Terminalmodus; beliebiger Lua-/Ex-Code ist nicht
  übertragbar. `changedtick` wird bewusst nicht verlangt, weil asynchrone
  Terminalausgabe den Buffer laufend ändert und die Operation keinen Text
  liest oder verändert.
- `TermClose` meldet das Ende des Terminalprozesses mit Exit-Status
  ereignisgetrieben als strukturierte Meldung. Terminal-Screen-Scraping oder
  Polling wird nicht eingeführt.
- Der reale TUI-Test verwendet isolierte XDG- und Runtime-Pfade, damit ein
  lokal installiertes älteres Plugin den getesteten Branch nicht überlagert.

## 0.92.0-dev.1 (Featurebranch-Testbuild)

- Direkte Eingabe in einem eingebetteten Terminal verwendet nun den
  Insert-/Fokusklang; der Übergang in den Terminal-Normalmodus verwendet den
  Normalmodusklang. Der Passthrough-Gate wird jeweils vor der optionalen
  Rückmeldung fail-open umgestellt.
- Der Command-line-Modus bleibt unabhängig von deaktivierter Insert-/Normal-
  Sprachrückmeldung hörbar. Nach Befehlen erscheinende nichtleere
  `msg_show`-Meldungen werden auch bei leerer oder neuer UI-Klassifikation als
  gewöhnliche Meldung in Sprache und Braille ausgegeben; Suchzähler behalten
  ihren eigenen strukturierten Pfad.

## 0.92.0 (Beta-Vorabveröffentlichung)

- Die Produktversion wurde auf ausdrückliche Vorgabe auf `0.92.0` angehoben.
  Der GitHub-Eintrag wird als Pre-Release veröffentlicht.
- Der Releasekanal bleibt `beta`; der Gesamtstand bleibt zwischen Alpha und
  Beta und wird nicht als stabil eingestuft.
- Enthält die einstellbare Fokusausgabe für gebundene Neovim-Sitzungen, die
  control-spezifische Windows-Terminal-Abschottung sowie die ausdrücklich
  ausgelösten Zwischenablagebefehle für lokale und SSH-Verbindungen.

## 0.91.0-dev.4 (unveröffentlichter Featurebranch-Testbuild)

- Ergänzt vier frei belegbare NVDA-Befehle ohne Standardgesten: aktuelle
  Visual-Auswahl nach Windows kopieren, Neovims Register 0 kopieren und
  Windows-Zwischenablagentext über `nvim_paste` einfügen oder in Neovims
  Register 0 speichern und Neovims unbenanntes Register für normales `p`
  darauf zeigen lassen.
- Lokaler und SSH-Pfad verwenden dieselben festen, korrelierten Steuerungen.
  Fokus, Control-Bindung, Instanz, Anfrage-ID, Buffer, Fenster, Tab,
  `changedtick` und Modus werden geprüft; Text ist NUL-frei und auf 256 KiB
  UTF-8 begrenzt. Es gibt kein Polling, Auto-Sync oder Auto-Retry.
- Paste ist auf normale veränderbare Editorbuffer beschränkt. Einmalig
  übertragener Copy-Text wird aus Cache und redigierter Diagnose entfernt.
  Die Erfolgsrückmeldung ist profilfähig als Aus/Sprache/Töne/Beides; Fehler
  bleiben hörbar. Offene Anfragen sind begrenzt.
- Alle vier Befehle wurden im bereitgestellten `dev.4`-Build praktisch ohne
  Probleme bestätigt.
- Frei belegbare Befehle sind im Tastenbefehldialog nun unabhängig von der
  zuvor fokussierten Anwendung sichtbar. Außerhalb eines exakt erkannten
  Windows-Terminal-Controls wird eine zugewiesene Geste unverändert
  weitergegeben; Ereignisse, F12, Overlays und Standardgesten bleiben im
  WT-AppModule. Bereits in früheren Featurebuilds gespeicherte Gestenzuweisungen
  bleiben über undokumentierte Kompatibilitätsaliase wirksam.
- Der `dev.4`-Praxistest bestätigte die Produktkategorie beim Öffnen des
  Tastenbefehldialogs aus einer Fremdanwendung, unveränderte Gestenweitergabe
  außerhalb WT und korrekte Ausführung im gebundenen Neovim-Control.
- 38 Protokoll-, 28 Bridge-, 244 Add-on/Core-/Pakettests und alle
  Lua-Spezifikationen einschließlich 28 Zwischenablageassertionen bestehen;
  Add-on und sechs HTML-Dokumente bauen erfolgreich.

## 0.91.0-dev.1 (unveröffentlichter Featurebranch-Testbuild)

- Ergänzt eine profilfähige Fokusauswahl: keine Ansage, aktuelle strukturierte
  Zeile oder der bisherige Datei-/Spezialkontext mit Modus und Verbindungsname.
  Das bisherige Verhalten bleibt Standard.
- Bestätigter Sitzungsfokus gibt für Insert und Normal unabhängig von der
  Fokusauswahl den durch die vorhandenen Modusklang-Einstellungen erlaubten
  Klang aus.
- Fokuskorrelation, Gate, strukturierte Braillezeile und fail-open Verhalten
  bleiben immer aktiv. Automatisierte Tests decken alle Auswahlwerte,
  Unicode-/Leerzeilen, Braille, Klangtrennung, NVDA-Profile und eine sichere
  Schema-5-Migration ohne erneuten Altdateiimport ab.
- Der praktische NVDA-/WT-Test bestätigte die drei Auswahlwerte und die
  Modusklänge mit lokaler sowie entfernter SSH-Sitzung ohne Probleme.

## 0.91.0 (Beta-Veröffentlichung)

- Übernimmt die control-spezifische Windows-Terminal-Abschottung mit
  fail-open Fokuswechseln und ohne aktivitätsbasierte Umbindung.
- Der Aktivierungsbefehl bleibt überall globaler Ein-/Ausschalter; F12
  autorisiert jeweils genau einen Zuordnungsversuch für das fokussierte
  Terminal-Control.
- Lokale und entfernte Verbindungen in mehreren Tabs sowie horizontale und
  vertikale Split-Panes wurden praktisch ohne Fehler bestätigt.
- Der Gesamtstand bleibt zwischen Alpha und Beta und wird nicht als stabil
  eingestuft.

## 0.90.0-dev.3 (unveröffentlichter Featurebranch-Testbuild)

- Der Praxistest von `dev.1` zeigte zwei gekoppelte Regressionen: F12 blieb im
  zweiten WT-Tab wirkungslos, und der Aktivierungsbefehl konnte dort den Dienst
  nicht mehr ausschalten. Das Vorab-Arming wurde deshalb entfernt.
- Der Aktivierungsbefehl ist wieder in jedem Control der globale
  Ein-/Ausschalter. Bei eingeschaltetem Dienst autorisiert jeder physische
  F12-Druck genau einen Zuordnungsversuch für das exakt fokussierte Control.
- Ohne frischen Neovim-Claim bleibt dieser ausdrückliche Versuch still und
  erzeugt weder Auswahl, Bindung noch Unterdrückung. Regressionstests decken
  den zweiten Tab, die globale Deaktivierung und den stillen Shell-Fall ab.
- Der praktische `dev.3`-Test bestätigte die lokale Zuordnung im ersten Tab,
  eine entfernte F12-Zuordnung im zweiten Tab ohne erneute Aktivierung und die
  globale Deaktivierung aus diesem zweiten Tab vollständig.
- Horizontale und vertikale WT-Split-Panes funktionierten im anschließenden
  Praxistest bei parallelen lokalen und SSH-Verbindungen in anderen Tabs
  fehlerfrei und ohne Querzuordnung.

## 0.90.0-dev.1 (bereitgestellter Featurebranch-Testbuild)

- F12 bleibt der physische Neovim-/Registry-Handshake, wird aber nur noch für
  genau ein zuvor ausdrücklich vorbereitetes WT-`TermControl`, einmalig und
  höchstens 60 Sekunden ausgewertet. Andere Shell-Panes bleiben auch bei
  laufender Unterstützung ohne Suche, Dialog oder Bindung.
- Ein erneuter Aktivierungsbefehl in einem ungebundenen Control armiert dieses
  Control, ohne bestehende lokale oder entfernte Verbindungen in anderen Tabs,
  Split-Panes oder Fenstern zu beenden. Im gebundenen Control bleibt der Befehl
  die globale Deaktivierung.
- WT-AppModule-Instanzen teilen eine einzige Gestenbeobachterregistrierung.
  Netzwerkaktivität einer anderen Instanz kann keine ungebundene Pane mehr
  umbinden oder dort einen Bestätigungsdialog öffnen.
- Fokusverlust suspendiert Unterdrückung fail-open. Gemerkte Verbindungen werden
  beim Wechsel erst nach einer zu Control, Instanz und Request-ID passenden
  frischen Kontextantwort reaktiviert. Mehrere Tabs und Fenster behalten dabei
  getrennte Verbindungen und Editor-Laufzeitzustände.
- Automatisierte Negativ-, Mehrcontrol- und Mehrfenstertests sind ergänzt; der
  praktische NVDA-/WT-Test steht aus. Ein zusätzlicher unabhängiger Nachweis des
  Vordergrundprogramms innerhalb desselben Controls bleibt Folgearbeit.

## 0.90.0 (Beta-Veröffentlichung)

- Übernimmt die praktisch bestätigte Fokus-Kontextansage einschließlich
  Dateiname, Modus und konfiguriertem Verbindungsnamen.
- Der Gesamtstand bleibt zwischen Alpha und Beta und wird nicht als stabil
  eingestuft.

## 0.89.0-dev.3 (unveröffentlichter Featurebranch-Testbuild)

- Fokusansagen nennen zusätzlich den in den Einstellungen vergebenen
  Verbindungsnamen, beispielsweise „on Tessa“. Lokale Windows-Sitzungen werden
  als „on local“ bezeichnet; technische Hostnamen werden nicht zusätzlich
  offengelegt.

## 0.89.0-dev.2 (unveröffentlichter Featurebranch-Testbuild)

- Beim Rückwechsel aus einer anderen Anwendung in dasselbe registrierte
  WT-Control wird die Fokus-Kontextabfrage nun tatsächlich ausgelöst. Der
  vorherige Frühabbruch hielt die erhaltene authentifizierte Bindung
  fälschlich für ein Fokusereignis innerhalb desselben Controls.

## 0.89.0-dev.1 (unveröffentlichter Featurebranch-Testbuild)

- Ein erneut fokussiertes, authentifiziertes und registriertes WT-Control kann
  Datei beziehungsweise Spezialbuffer, Status und Modus kompakt ausgeben.
- Die Abfrage ist ereignisgetrieben und korreliert. Ungebundene Controls sowie
  verspätete oder nicht mehr passende Antworten bleiben wirkungslos; Polling
  und Terminal-Screen-Scraping werden nicht verwendet.
- Der praktische NVDA-/WT-Test steht aus. Dieser Stand ist nicht stabil und
  bleibt zwischen Alpha und Beta.

Dieses Changelog beschreibt auslieferbare Beta-Stände. Die zahlreichen
experimentellen Vor-Beta-Builds werden nicht einzeln fortgeführt; Git enthält
deren vollständigen Verlauf.

## 0.89.35 (Beta-Veröffentlichung)

- Die Härtung des Registry-Lebenszyklus und die Pflege der
  Windows-Terminal-Bindungen werden nach praktischer Prüfung mit lokalem
  Windows-Neovim und Tessa-SSH als Vorabversion veröffentlicht. Der
  Gesamtstand bleibt zwischen Alpha und Beta.
- Vollständige Wirkungslosigkeit in ungebundenen Windows-Terminal-Panes bleibt
  dokumentierte Folgearbeit; unsicherer Unterdrückungszustand bleibt fail-open.

- Die Diagnose von 0.89.34 identifiziert den vermeintlichen F12-Fehler als
  bereits aktive Swap-Datei-Bestätigung (`r?`, confirm, swap), nicht als
  Eingabe- oder RPC-Fehler.
- `ext_messages` und `ext_popupmenu` werden nicht mehr beim Neovim-Start
  angehängt. Die UI-Verantwortung wechselt erst nach Registrierung eines
  authentifizierten Kanals und geht bei Abmeldung, Snapshot- oder RPC-Fehler
  wieder an die native TUI zurück. Swap-Wiederherstellung und andere Abfragen
  vor der Verbindung bleiben dadurch sichtbar und der Terminalpfad bleibt
  fail-open.
- In Hit-Enter-, Pager- oder Bestätigungsmodi beobachtetes F12 schreibt keinen
  Session-Claim. Zuerst muss die native Abfrage beantwortet und danach F12 in
  einem Editormodus gedrückt werden; das Add-on wählt nie selbst eine
  möglicherweise destruktive Swap-Aktion.
- Der Praxistest bestätigte den vollständigen Pfad lokal und über Tessa-SSH:
  F12 während der Swap-Rückfrage lieferte keinen Kandidaten, der nächste
  F12-Druck nach ihrer Auflösung verband im Normalmodus, das erste `i` öffnete
  den Insert-Modus und die strukturierte Texteingabe lief normal weiter. Nach
  dem Schließen des ersten Editors trennte sich dessen Client;
  Wiederverbindungsversuche blieben fail-open, und das Deaktivieren der
  Unterstützung stoppte diesen Client, bevor spätere Sitzungen eigene Instanzen
  erhielten.

## 0.89.34 (Diagnose-Testbuild, durch 0.89.35 ersetzt)

- Der Praxistest von 0.89.33 bewies, dass die sichtbare F12-Zuordnung auf
  Windows-Neovims interne Funktionstastenform nicht angewendet wird. Die
  Zuordnung ist wieder entfernt.
- Neovim dokumentiert den Rohmodus `r?` ausdrücklich als `:confirm`-Abfrage.
  Der UI-Meldungsbeobachter behält dafür nur begrenzte Metadaten vor der
  Verbindung: Aktivstatus, Meldungsart, Bytelänge und eine feste Kategorie wie
  Swap, Überschreiben, ungespeicherte Änderungen, Beenden, Löschen oder
  Sonstiges. Prompttext und Pfade werden weder behalten noch gemeldet.

## 0.89.33 (nicht bestandener Korrektur-Testbuild)

- Die Diagnose von 0.89.32 grenzt den Windows-Fehler eindeutig ein: Beide
  Tastenwerte sind genau `<F12>`, Beobachter und Claim sind fehlerfrei, dennoch
  endet Neovims normale Verarbeitung dieser reservierten Taste im
  nichtblockierenden Modus `r?`.
- Die konfigurierte Claim-Taste erhält nun in jedem Neovim-Eingabemodus eine
  stille, sofortige No-op-Zuordnung. `vim.on_key` beobachtet und persistiert den
  Claim weiterhin zuerst; die Zuordnung konsumiert ausschließlich die folgende
  Standardverarbeitung. Vorhandene Benutzerzuordnungen werden nie überschrieben.
- Es wird weder Escape noch andere synthetische Eingabe eingespeist. Ein realer
  PTY-Regressionstest mit Neovim 0.12.3 sendet F12, erkennt den Claim und
  verlangt anschließend Normalmodus.

## 0.89.32 (nicht bestandener Diagnose-Testbuild)

- Der Praxistest von 0.89.31 geriet weiterhin in den blockierenden
  `r?`-/Hit-Enter-Modus. Die Beobachtermetadaten waren im Protokoll vorhanden,
  wurden aber vom expliziten Diagnosefeldfilter des Add-ons ausgelassen.
- Ereignisdiagnosen zeigen nun ausschließlich die zur Eingrenzung nötigen
  begrenzten Felder: Blockierungsstatus, feste aktuelle Fehlernummer/-klasse,
  übersetzte F12-Formen und Bytelängen, Beobachter-/Claim-Fehlerklassen sowie
  den Modus nach dem geplanten Claim. Fehlermeldung und Editorinhalt werden
  nicht zusätzlich protokolliert.
- Zustandsschnappschüsse unterscheiden Neovims Blockierungsflag vom Rohmodus.

## 0.89.31 (Diagnose- und Korrektur-Testbuild)

- Der komplette `vim.on_key`-Beobachter ist jetzt durch `pcall` gekapselt;
  auch der geplante Registry-Claim kann keine Lua-Ausnahme mehr bis in Neovims
  Eingabeschleife tragen. Fehler deaktivieren oder konsumieren keine Taste.
- Das erste `fullState` enthält ausschließlich für einen erkannten F12-Claim
  begrenzte, nicht-sensitive Metadaten: Funktionstastenübersetzung,
  Byte-Längen, feste Fehlerkategorien und den Modus nach dem geplanten Claim.
  Es werden keine normalen Tasten, Meldungstexte oder Editorinhalte erfasst.
- Ein Regressionstest erzwingt einen `keytrans`-Fehler und verlangt, dass er
  Neovims Eingabe nicht verlässt. Ein realer PTY-Test sendet die vollständige
  F12-CSI-Sequenz an Neovim 0.12.3 und prüft Claim sowie Normalmodus.

## 0.89.30 (nicht bestandener Beta-Testbuild)

- Die Registry-Inventur ist wieder rein passiv und öffnet beim Polling keine
  kurzlebigen Neovim-RPC-Kanäle mehr. Zuvor konnten innerhalb von 1,5 Sekunden
  etwa 30 Identitätsabfragen pro Kandidat Neovims Kanal-/UI-Zustand
  beeinflussen. Das ist der belastbarste konkrete Unterschied gegenüber dem
  praktisch bestätigten Stand 0.89.16 und damit die wahrscheinlichste Ursache
  der `r?`-Regression.
- Die `sessionNonce` wird mit dem ausgewählten Registryeintrag bis zum echten,
  dauerhaften RPC-Kanal getragen und dort vor `setup()` und
  `register_channel()` geprüft. Ein Unterschied trennt fail-open und wird nicht
  erneut verbunden. Endpoint-Authentisierung und TOCTOU-Schutz bleiben damit
  ohne zweiten Kanal erhalten.
- Der experimentelle verzögerte Escape aus 0.89.29 ist entfernt; der
  F12-/Eingabepfad entspricht wieder dem praktisch bestätigten Verhalten.
- Die automatisierte Matrix lief mit dem offiziellen Linux-Build von Neovim
  0.12.3. Der Testtreiber lädt dessen optionales `netrw` ausdrücklich;
  versionsabhängige Standarddialogdetails sind kein eigener Protokollvertrag.

## 0.89.29 (Beta-Testbuild)

- 0.89.28 bewies mit leerem `preConnectErrorCode` und
  `preConnectErrorKind`, dass `r?` nicht durch Lua, Snapshot, Registry oder
  Textlock entsteht, sondern als Modus von der vollständig weiterverarbeiteten
  physischen F12-Terminalsequenz zurückbleibt.
- Der bewährte Claim-Pfad bleibt unverändert. Erst 100 ms nach dem
  persistierten Claim, wenn die restlichen Bytes der Terminalsequenz
  verarbeitet sind, speist das Plugin einmal Escape ein. Das liegt deutlich
  vor NVDAs Claim-Auswertung nach 250 ms. Anders als 0.89.26 läuft Escape damit
  nicht vor den noch wartenden F12-Bytes.
- Ein Regressionstest verlangt verzögerten Claim und anschließenden
  Normalmodus; F12 bleibt weiterhin ungebunden.

## 0.89.28 (Diagnose-Testbuild, durch 0.89.29 ersetzt)

- Ergänzt am ersten `fullState` ausschließlich datensparsame Diagnosefelder
  für einen bereits vor der Verbindung gesetzten Neovim-Fehler: nur
  `preConnectErrorCode` und eine feste Fehlerkategorie, niemals Meldungstext,
  Pfade oder Editorinhalt. Damit lässt sich der weiterhin vor der ersten
  normalen Taste vorhandene `r?`-Zustand einer Phase zuordnen, ohne den
  bewährten Eingabepfad erneut zu verändern.

## 0.89.27 (nicht bestandener Beta-Testbuild)

- Stellte den Eingabepfad von `main` wieder her, der erste `fullState` war im
  Praxistest aber weiterhin bereits `r?`. Damit liegt die Ursache vor der
  normalen Eingabe, wahrscheinlich in Claim, Registry-Identitätsprüfung oder
  Verbindungsaufbau; 0.89.28 instrumentiert diese Grenze.

- Die nach 0.89.22 experimentell eingeführten Änderungen am
  `vim.on_key`-Pfad wurden gezielt entfernt: kein F12-No-op-Mapping, kein
  Rohtermcode-Sonderpfad, kein allgemeiner Callback-Wrapper und kein
  künstlich eingespeistes Escape. Der Eingabe- und Claimpfad entspricht damit
  wieder dem auf `main` praktisch bestätigten Stand 0.89.16.
- Erhalten bleiben die von der Eingabe unabhängigen Änderungen: Registry-
  Schema 3, Prozess-/Nonce-Prüfung, robuste WT-Lebenszyklusbehandlung sowie die
  notwendige Neovim-0.12-Signaturkorrektur für `vim.str_utfindex` und das
  fail-open Abbrechen eines tatsächlich fehlerhaften Snapshots.
- Der Vergleichstest verlangt wieder ausdrücklich, dass F12 ungebunden bleibt
  und der bewährte `typed`-Beobachter genau einen verzögerten Claim schreibt.

## 0.89.26 (nicht bestandener Beta-Testbuild)

- Stellte nach F12 zunächst Normalmodus her, erzeugte aber bei der ersten
  normalen Eingabe erneut `r?`. Das künstlich eingespeiste Escape und die
  übrigen experimentellen Eingabeänderungen wurden daher vollständig aus dem
  Registry-Branch entfernt.

- Nach einem erkannten F12-Claim führt das Plugin im geplanten normalen
  Ereigniszyklus Escape aus und stellt damit einen ungefährlichen Normalmodus
  her. Das ist nötig, weil `vim.on_key` nur beobachtet und die interne
  Windows-Terminal-Funktionstastensequenz nicht konsumieren kann; im
  Praxistest von 0.89.25 wurde deren Rest als `v` verarbeitet und Neovim stand
  unmittelbar nach der Verbindung im visuellen Zeichenmodus.
- Ein Regressionstest beginnt absichtlich im visuellen Modus und verlangt,
  dass der verzögerte Claim genau einmal persistiert wird und anschließend
  Normalmodus erreicht ist.

## 0.89.25 (nicht bestandener Beta-Testbuild)

- Erkannte und persistierte F12 wieder, ließ die beobachtete interne
  Tastensequenz aber normal weiterlaufen. Der erste `fullState` zeigte daher
  `modeRaw=v`; die anschließende Bedienung wirkte blockiert.

- Die F12-Erkennung vergleicht im `vim.on_key`-Callback nur noch rohe Strings
  mit einem bereits beim Pluginstart berechneten Termcode. Sie ruft dort vor
  dem Claim weder `keytrans()` noch eine andere Vim-Funktion auf. Damit bleibt
  der Claim unter Neovim 0.12 funktionsfähig, obwohl dessen Textlock solche
  Funktionsaufrufe ablehnt.
- Der Regressionstest lässt `keytrans()` während F12 absichtlich fehlschlagen
  und verlangt trotzdem genau eine verzögert persistierte Claim-Sequenz.

## 0.89.24 (nicht bestandener Beta-Testbuild)

- Verhinderte den sichtbaren Fehler aus dem Eingabebeobachter, kapselte aber
  auch die noch vor dem F12-Vergleich aufgerufene `keytrans()`-Funktion. Unter
  Neovim 0.12 blieb der Fehler dadurch unsichtbar und der Claim aus.

- Die UIA-Lebenszyklusprüfung läuft ausschließlich im periodischen
  Wartungslauf. Sie wurde aus Editorereignissen, Verbindungsstatus und
  Terminalaktionen entfernt, nachdem 0.89.23 einen aktiven fokussierten Tab
  fälschlich als geschlossen entfernt hatte.
- Ein fokussierter Tab gilt immer als lebend. Bei inaktiven Tabs führen erst
  zwei aufeinanderfolgende negative Prüfungen im Abstand von fünf Minuten zur
  Trennung; eine einzelne vorübergehende UIA-Lücke ist nicht-destruktiv.
- Der gesamte `vim.on_key`-Beobachter ist nun eine ausfallsichere
  Nebenbeobachtung: API-Unterschiede oder Textlock-Fehler dürfen keine Taste
  ablehnen und keinen `r?`-/Hit-Enter-Prompt erzeugen. Auch geplante Claim- und
  Rechtschreibprüfungen geben Fehler nicht mehr in Neovims Eingabeschleife
  weiter. Ein Regressionstest simuliert die API-Ablehnung.

## 0.89.23 (nicht bestandener Beta-Testbuild)

- Die Claim-Taste wird weiterhin versionsübergreifend über `vim.on_key` und
  dessen unveränderten `typed`-Wert erkannt. Wenn Neovim `<F12>` regulär als
  Mapping auflöst, konsumiert nun zusätzlich eine stille No-op-Zuordnung die
  Taste nach der Beobachtung. Der Praxistest zeigte dennoch `r?`-/Hit-Enter-
  Prompts, weil Fehler aus dem übrigen Eingabebeobachter noch bis in Neovims
  Eingabeschleife gelangen konnten.

- Snapshots verwenden unter Neovim 0.11 und neuer die neue
  `vim.str_utfindex(text, encoding, index, strict)`-Signatur, unter Neovim 0.10
  weiterhin die alte Signatur. Damit erzeugt lokales Neovim 0.12 beim ersten
  Moduswechsel keinen Lua-/Hit-Enter-Fehler mehr.
- Unerwartete Snapshot-Fehler schließen den Plugin-RPC-Kanal ohne sichtbaren
  Neovim-Fehlerprompt; NVDA trennt dadurch fail-open zur nativen WT-Ausgabe.

- Die periodische Bereinigung geschlossener WT-Bindungen läuft nur noch alle
  fünf Minuten statt alle zwei Sekunden. Unmittelbares Fail-open bei
  Verbindungsabbruch und Registryprüfung bei Discovery bleiben unverändert.

- Die für lokale Registry-Prüfungen benötigte Datei `registry_probe.py` ist
  jetzt im NVDA-Add-on enthalten. Ein Pakettest prüft Datei und relativen
  Import ausdrücklich am extrahierten Installationsarchiv.

- Windows-Terminal-Ereignisse fallen bei jeder unerwarteten Add-on-Ausnahme
  genau einmal auf NVDA's native Verarbeitung zurück und beenden sofort die
  sitzungsbezogene Unterdrückung.
- Die Registry-Lebenszyklusprüfung läuft nicht mehr synchron vor
  `Terminal.event_gainFocus`; NVDA kann daher seine native LiveText-Überwachung
  auch bei einem Fehler in der Add-on-Verwaltung sicher starten.
- Scheitert der periodische Lebenszyklustest unerwartet, beendet er die
  Unterdrückung fail-open und plant sich nicht erneut ein.

- Registry-Schema 3 kombiniert Prozessidentität und eine per RPC bestätigte
  zufällige Sitzungs-Nonce gegen PID-, Port- und Socket-Wiederverwendung.
- Ältere Registry-Schemata ohne vollständigen Identitätsnachweis bleiben
  verborgen; nach dem Komponentenupdate ist dafür ein Neovim-Neustart nötig.
- Registrydateien und Nonce-RPC-Antworten sind absolut zeit- und
  größenbegrenzt. Berechtigungsfehler gelten niemals als Todesnachweis.
- Nur eindeutig tote private Einträge und exakt nonce-eindeutige eigene
  Pluginsockets werden bereinigt. Übernommene oder benutzerdefinierte Pfade
  bleiben unangetastet; Timeouts und Zugriffsfehler sind nicht-destruktiv.
- Geschlossene WT-Tabs und ganze Fenster verlieren ihre Bindung fail-open. Der NVDA-Client
  stoppt nach spätestens der fünfminütigen Sicherheitsprüfung außerhalb des Hauptthreads;
  Neovim- und tmux-Prozesse werden nie
  beendet.
- Mehrtab-/Mehrfenster-Regressionen sowie isolierte SIGKILL-Tests decken lokal
  und Tessa ab. Inaktive, aber offene Tabs bleiben über ihr direkt geprüftes
  UIA-Element gültig; unklare UIA-Fehler sind nicht-destruktiv.

## 0.89.22 (Beta-Testbuild, durch 0.89.23 ersetzt)

- Korrigierte die Snapshot-Signatur für Neovim 0.12, beseitigte aber nicht die
  anschließende Standardverarbeitung der beobachteten, ungebundenen F12-Taste.

## 0.89.21 (Beta-Testbuild, durch 0.89.22 ersetzt)

- Setzte die WT-Bindungsbereinigung auf fünf Minuten, enthielt aber noch den
  unter Neovim 0.12 inkompatiblen alten `vim.str_utfindex`-Aufruf.

## 0.89.20 (Beta-Testbuild, durch 0.89.21 ersetzt)

- Enthielt bereits die Paketierungs- und Fail-open-Korrekturen, verwendete für
  die reine WT-Bindungsbereinigung aber noch das unnötig kurze
  Zwei-Sekunden-Intervall.

## 0.89.18 (nicht bestandener Beta-Testbuild)

- Das Add-on konnte wegen der fehlenden gepackten Datei `registry_probe.py`
  nicht importiert werden. Einstellungen, Werkzeugmenü, Unterdrückung und der
  periodische Lebenszyklustest wurden deshalb in diesem Build nie gestartet.

## 0.89.17 (nicht bestandener Beta-Testbuild)

- Dieser Build wurde nach materiellen Registry-Änderungen irrtümlich unter
  derselben Versionsnummer erneut erzeugt. Er ist nicht mehr zur Installation
  vorgesehen.
- Im Praxistest konnte bereits das Laden des Add-ons die native Ausgabe von
  Windows Terminal verhindern. 0.89.23 ersetzt diesen Stand mit einer
  ausdrücklichen Fail-open-Barriere.

## 0.89.16 (Beta-Testbuild)

- Der über `typed` erkannte Claim wird mit `vim.schedule()` in Neovims normalen
  Ereigniszyklus verlagert. Der `vim.on_key`-Callback führt damit keine
  Registry-, Dateisystem- oder regulären Vim-Funktionszugriffe mehr aus.
- Der Regressionstest prüft ausdrücklich, dass die Claim-Sequenz während des
  Tastencallbacks unverändert bleibt und erst durch den geplanten Callback
  erhöht wird.
- Der abschließende Praxistest bestätigte wiederholte automatische
  F12-Zuordnungen sowohl mit lokalem Neovim 0.12.3 als auch mit Neovim 0.10.1
  auf Tessa. Bei deaktivierter Unterstützung blieb die Beobachtung inaktiv und
  öffnete keinen Zuordnungsdialog.

## 0.89.15 (nicht bestandener Beta-Testbuild)

- Das Neovim-Plugin erkennt die konfigurierte Claim-Taste nun am unveränderten
  `typed`-Wert seines bestehenden `vim.on_key`-Beobachters. Es verlässt sich
  nicht mehr darauf, dass Neovim 0.10.1 den internen Terminalcode als
  `<F12>`-Mapping auflöst.
- Ein isolierter Tessa-Test bewies den Unterschied: Neovim meldete zweimal
  `typed=<F12>`, intern aber `key=<t_…>`; die `<F12>`-Zuordnung lief keinmal
  und der Test endete im Timeout.
- Der NVDA-Beobachter ist bei deaktivierter Unterstützung vollständig inaktiv.
  F12 bleibt dann ein normaler Tastendruck und öffnet keinen Add-on-Dialog.
- Der praktische Test bestätigte die automatische Tessa-Verbindung und den
  inaktiven Beobachter bei deaktivierter Unterstützung. Lokales Neovim 0.12.3
  wurde ebenfalls automatisch gefunden und kurz verbunden, wechselte aber
  unmittelbar in den `r?`-/Hit-Enter-Zustand und verlor danach seinen RPC-
  Server. 0.89.16 verschiebt den Registry-Schreibzugriff aus `vim.on_key`.

## 0.89.14 (nicht bestandener Beta-Testbuild)

- F12 ist nicht mehr als NVDA-Skript gebunden und wird nicht mehr synthetisch
  wiedereingespeist. Das nur für Windows Terminal geladene App-Modul beobachtet
  die Geste am öffentlichen `decide_executeGesture`-Erweiterungspunkt, reicht
  sie unverändert an NVDAs normale Auflösung weiter und startet die Claim-Suche
  getrennt über NVDAs Ereigniswarteschlange.
- Ohne gebundenes Skript endet NVDAs Auflösung für F12 mit
  `NoInputGestureAction`; der Keyboard-Hook lässt deshalb den ursprünglichen
  physischen Tastendruck direkt zum Betriebssystem durch. Ein Kontrolltest
  bestätigte drei echte Claims in derselben Tessa-Sitzung.
- Der praktische Test bestätigte die automatische lokale Zuordnung, Tessa
  blieb jedoch ohne Claim. Die erfolgreiche Verbindung im Bericht stammte von
  der manuellen Profil- und Sitzungsauswahl. Der isolierte Folgetest
  lokalisierte den verbleibenden Fehler in Neovims Terminalcode-zu-Mapping-
  Auflösung.

## 0.89.13 (nicht bestandener Beta-Testbuild)

- F12 wird in Windows Terminal nun erst nach Rückkehr aus NVDAs Eingabe-Hook
  mit einer kurzen GUI-Schleifenverzögerung weitergegeben. Dadurch verarbeitet
  das Terminal die Funktionstaste außerhalb des noch laufenden NVDA-Skripts;
  die begrenzte Claim-Suche beginnt weiterhin erst danach.
- Ein praktischer 0.89.12-Lauf bestätigte lokale Claims und einmalig auch eine
  SSH-Verbindung zu Tessa. Beim folgenden Fehlversuch blieben jedoch beide
  Register der tatsächlich laufenden Tessa-Neovims unverändert auf
  `claimSequence=0`; Aktivierung und Deaktivierung hatten ihre Clients dagegen
  ordnungsgemäß beendet und neu erfasst.
- Die verzögerte synthetische Weitergabe blieb im praktischen Test erfolglos.
  Die manuelle Auswahl verband dieselbe Sitzung, und ein anschließend bei
  deaktivierter Unterstützung direkt durchgelassener physischer Tastendruck
  sowie weitere Versuche erhöhten deren Register dagegen bis
  `claimSequence=3`. 0.89.14 entfernt daher die synthetische Weitergabe.

## 0.89.12 (Beta-Testbuild)

- Die lokale automatische Zuordnung übernimmt nun wie der manuelle Pfad einen
  unmittelbar vor der F12-Weitergabe erfassten monotonen Zeitanker. Ein Claim
  gilt als frisch, wenn seine Sequenz gegenüber der Aktivierungsbaseline
  gestiegen ist oder er nach genau diesem Tastendruck geschrieben wurde.
- Ein interaktiver Test von 0.89.11 bestätigte die vollständige Tastenkette bis
  zum erfolgreichen Registry-Claim und begrenzte den verbleibenden Fehler auf
  die Add-on-Auswertung.

## 0.89.11 (nicht bestandener Beta-Testbuild)

- Ein unveränderter interaktiver Test der originalen Produktzuordnung bewies,
  dass F12 bei aktiver NVDA-Unterstützung Neovim überhaupt nicht erreichte.
  Der Rohtasten-Decider wurde deshalb entfernt.
- F12 ist wieder ausschließlich im Windows-Terminal-App-Modul gebunden. Das
  Skript gibt die Originalgeste mit NVDAs öffentlichem `gesture.send()` zuerst
  an Neovim weiter und startet danach die begrenzte Claim-Auswertung.
- Die in 0.89.9 und 0.89.10 erprobten, als Ursache widerlegten Änderungen an
  Neovims Zuordnung wurden zurückgenommen.
- Die Weitergabe und der Neovim-Claim funktionierten praktisch, die alleinige
  Sequenzbaseline der automatischen lokalen Auswertung erkannte den Claim aber
  weiterhin nicht zuverlässig. 0.89.12 ergänzt den tastendruckgebundenen
  Zeitanker.

## 0.89.10 (nicht bestandener Beta-Testbuild)

- Die F12-Zuordnung wird nun wie im erfolgreichen interaktiven Prüflauf für
  jeden Neovim-Modus einzeln registriert. Unter dem getesteten Windows-
  Terminalpfad war die bisherige gemeinsame Mehrmodus-Zuordnung zwar über
  `maparg()` sichtbar, reagierte aber nicht auf die intern als Terminalcode
  dargestellte Funktionstaste.
- Regressionstests prüfen Beschreibung, `nowait` und ausführbaren Callback
  getrennt für Normal-, Insert-, Visual-, Select-, Operator-, Befehlszeilen-
  und Terminalmodus.
- Der praktische Test mit sicher aktualisierten Komponenten schlug weiterhin
  fehl. Ein unveränderter Mapping-Prüflauf zeigte anschließend, dass F12 nicht
  bis zu Neovim gelangte; die Mapping-Änderung war daher nicht ursächlich.

## 0.89.9 (nicht bestandener Beta-Testbuild)

- Die Neovim-Zuordnung für die Sitzungsauswahl wird nun ausdrücklich ohne
  Wartezeit ausgewertet. Ein interaktiver Test zeigte, dass Windows Terminal
  F12 korrekt an Neovim lieferte und der Claim selbst funktionierte, während
  die bisherige dauerhafte Zuordnung in Neovims Mapping-Auflösung hängen
  bleiben konnte.
- Der Regressionstest prüft neben dem wiederholten Claim nun auch die für
  Terminal-Funktionstasten erforderliche `nowait`-Eigenschaft.
- Der praktische Test zeigte, dass `nowait` allein nicht genügte. 0.89.10
  übernimmt zusätzlich die einzelne Registrierung je Modus aus dem
  erfolgreichen interaktiven Prüflauf.

## 0.89.8 (nicht bestandener Beta-Testbuild)

- Die F12-Skriptbindung und künstliche Tastenwiedereinspeisung wurden entfernt.
  Das Windows-Terminal-App-Modul beobachtet die unveränderte physische Taste
  über den öffentlichen NVDA-Erweiterungspunkt `decide_handleRawKey` und lässt
  sie immer normal zu Neovim weiterlaufen.
- Das Add-on wertet den anschließend von Neovim atomar geschriebenen Claim nur
  bei aktivierter Unterstützung und fokussiertem Windows Terminal aus. Andere
  Anwendungen und andere Tasten lösen keine Add-on-Aktion aus.
- Ein interaktiver Prüflauf bewies anschließend, dass die unveränderte Taste
  Neovim erreichte, aber die dauerhafte Neovim-Zuordnung nicht ausgelöst wurde.
  0.89.9 korrigiert diese letzte Zuordnungsstufe.

## 0.89.7 (nicht bestandener Beta-Testbuild)

- Leitete F12 vor der Fokusaktualisierung künstlich wieder ein. Praktische
  Tests zeigten weiterhin zustandsabhängig unveränderte Claim-Zähler; 0.89.8
  entfernt die Wiedereinspeisung vollständig.
- Die in 0.89.6 erprobte aggressive Erneuerung der Neovim-Belegung wurde
  verworfen: Der praktische Test zeigte unveränderte Claim-Zähler und damit
  einen Fehler vor der Neovim-Belegung. Benutzerdefinierte Belegungen werden
  nicht wiederholt überschrieben.

## 0.89.6 (nicht bestandener Beta-Testbuild)

- Erprobte eine wiederholte Erneuerung der F12-Belegung. Der praktische Test
  widerlegte die zugrunde liegende Ursache; dieser Ansatz ist in 0.89.7 wieder
  entfernt.

## 0.89.5 (Beta-Testbuild)

- Unter `NVDA-Menü → Werkzeuge → Neovim Access Link: Remove components...`
  können die eingebetteten Komponenten auf dem lokalen Windows-Rechner und
  auf ausdrücklich ausgewählten gespeicherten Linux-Verbindungen vollständig
  entfernt werden.
- Der zugängliche Mehrfachauswahldialog, die Hintergrundverarbeitung und die
  kompakte Ergebnisübersicht entsprechen dem Installationsablauf. Gespeicherte
  Verbindungen, Neovim- und SSH-Konfiguration sowie fremde Plugins bleiben
  erhalten.

## 0.89.4 (Beta-Testbuild)

- Quick Guide, Handbuch und Entwicklerdokumentation liegen vollständig auf
  Deutsch und Englisch als Markdown-Quellen und getrennte HTML-Ausgaben vor.
- Das Projekt wird unter `GPL-2.0-only` veröffentlicht. Der unveränderte
  Lizenztext wird in beide installierbaren Pakete aufgenommen; Beitragsregeln
  und die zusätzliche Relizenzierungserlaubnis sind getrennt dokumentiert.
- Standarddateien für eine GitHub-Veröffentlichung wurden ergänzt und private
  Produktanforderungen aus dem öffentlichen Quellbaum entfernt.

## 0.89.3 (Beta-Testbuild)

- Quick Guide, Anwenderhandbuch und Entwicklerdokumentation werden als drei
  eigenständige HTML-Dateien mit eigenem Inhaltsverzeichnis und geprüften
  internen Links gebaut.
- Die lokale F12-Nachsuche wartet begrenzt auf verzögert sichtbare atomare
  Registry-Aktualisierungen. Automatische und manuelle lokale Zuordnung wurden
  mit dem installierten Beta-Build praktisch bestätigt.
- Diagnoseberichte unterscheiden lokale und entfernte Sitzungszahlen,
  Nachsuche und Auflösungsabschluss, ohne Editorinhalt offenzulegen.

## 0.89.2 (Beta-Testbuild)

- Ein durch F12 eindeutig bestätigtes lokales Windows-Neovim wird unmittelbar
  ausgewertet und wartet nicht mehr auf langsamere SSH-Sitzungsprüfungen.

## 0.89.1 (erste Beta-Vorbereitung)

- Der sichtbare Produktname lautet „Neovim Access Link“, der Autor ist Emanuel
  Helms. Produktidentität, Version, Buildnummer und NVDA-Kompatibilitätsdaten
  werden ausschließlich in `buildVars.py` gepflegt.
- Manifest, Laufzeitdiagnose und Paketnamen werden aus dieser zentralen Quelle
  abgeleitet. Der interne NVDA-Identifier `nvimNvdaAccess` bleibt zugunsten
  kompatibler Installationen und NVDA-Profile stabil.
- Die Dokumentation wurde nach Sprache und Zielgruppe gegliedert. Bekannte
  Ausnahmen von öffentlichen NVDA-APIs sind in ADR-0002 begründet.

## Zusammenfassung der Vor-Beta-Entwicklung

- Das Produkt wechselte auf Protokoll v2 mit SSH-stdio für Linux und einem
  strikt an `127.0.0.1` gebundenen lokalen Neovim-RPC-Transport für Windows.
  Alte allgemeine TCP-, Tunnel-, Token- und v1-Pfade wurden entfernt.
- Das Add-on installiert Bridge, Protokollcode, MessagePack, Plugin und
  Zuordnungskonfiguration rootlos aus dem eingebetteten Paket. Mehrere Ziele
  werden im Hintergrund aktualisiert und zugänglich zusammengefasst.
- Verbindungsprofile und Laufzeitinstanzen wurden getrennt. Mehrere lokale und
  entfernte Sitzungen, Konten, Tabs, Fenster und tmux-Kontexte können parallel
  über eine ausdrückliche F12-Markierung gebunden werden; ein Standardziel ist
  nicht erforderlich.
- Windows-Terminal-spezifische Ereignisse, Gesten und Unterdrückung wurden in
  das NVDA-AppModule verschoben. Fremde Anwendungen bleiben unberührt;
  Deaktivierung, Fehler und Verbindungsverlust öffnen die normale
  Terminalausgabe wieder.
- Strukturierte Sprache und Braille wurden um Modi, Navigation, Bearbeitung,
  Auswahl, Completion, Menüs, Suche, Diagnostics, Folds, Marks, Register,
  Makros und verbreitete Dateimanager erweitert.
- Einstellungen verwenden NVDAs reguläre Konfigurationsprofile. Komponenten-
  und Verbindungsdialoge laufen zugänglich und blockieren NVDAs Hauptthread
  nicht.
