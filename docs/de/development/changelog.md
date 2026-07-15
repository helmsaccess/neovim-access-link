# Changelog

Dieses Changelog beschreibt auslieferbare Beta-Stände. Die zahlreichen
experimentellen Vor-Beta-Builds werden nicht einzeln fortgeführt; Git enthält
deren vollständigen Verlauf.

## 0.89.16 (Beta-Testbuild)

- Der über `typed` erkannte Claim wird mit `vim.schedule()` in Neovims normalen
  Ereigniszyklus verlagert. Der `vim.on_key`-Callback führt damit keine
  Registry-, Dateisystem- oder regulären Vim-Funktionszugriffe mehr aus.
- Der Regressionstest prüft ausdrücklich, dass die Claim-Sequenz während des
  Tastencallbacks unverändert bleibt und erst durch den geplanten Callback
  erhöht wird.

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
