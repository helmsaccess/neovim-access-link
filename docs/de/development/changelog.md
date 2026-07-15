# Changelog

Dieses Changelog beschreibt auslieferbare Beta-Stände. Die zahlreichen
experimentellen Vor-Beta-Builds werden nicht einzeln fortgeführt; Git enthält
deren vollständigen Verlauf.

## 0.89.35 (Korrektur-Testbuild)

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
