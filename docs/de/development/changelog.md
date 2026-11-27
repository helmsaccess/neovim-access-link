# Changelog

Dieses Changelog fasst abgeschlossene Änderungen nach Produktversion zusammen.
Die [detaillierte Historie](changelog-history.md) bewahrt frühere Entwicklungs-
und Testbuild-Einträge bis zum 5. August 2026.

## Unveröffentlicht

- Aktualisiert die NVDA- und Neovim-Referenzstände und dokumentiert die
  bestätigten Windows-Gastprüfungen für alle 18 geführten Fälle. Die endgültige
  Codeanalyse und der Reaudit bleiben als historische Berichte erhalten.
  GitHub Actions prüft den Windows-Desktop getrennt vom vollständigen
  Gastlauf, den ein privates Testlabor per wiederverwendbarem Workflow ausführt.
- Bewahrt in C1 eine Aufnahme mit fehlender QEMU-Startmarke auf, wiederholt
  den betroffenen Ablauf nach bestandener Gast- und WASAPI-Prüfung mit einem
  frisch gestarteten Gast einmal und prüft beide Versuche nach. Der
  Actions-Job führt unabhängige Fälle nach einem Fehler weiter aus und fährt
  seinen Testgast nach der Suite herunter.
- Prüft QEMU-Referenzmarken für C1 und D1 anhand getrennter Wellenformabschnitte mit
  begrenztem Zeitversatz und ergänzt Gegenproben für Rauschen, unvollständige
  und verschobene Marken sowie doppelte Signale.
- Startet den verwalteten Gast zwischen den unabhängigen P2-Fixtures neu
  und erkennt ein QEMU-Ende beim Warten auf die Desktop-Bereitschaft.
- Führt die geführten Aufgaben in optionale Desktop- und Audiogruppen
  mit isolierter Windows-VM und überprüften Gegenproben über.
- Gibt beim Auf- und Zuklappen eines lazy.nvim-Eintrags die Zustandsansage
  ohne zusätzliche Buchstabenansage durch die verschobene Cursorspalte aus.
- Öffnet in Aufgabe L4 die Quickfix-Liste bereits mit F3. Ein
  Regressionstest prüft den Fokus auf den ersten Treffer.
- Wartet in den geführten Python-Diagnosetests auf Ruff und Pyright. Die
  Fixture überlässt Importwarnungen Ruff, sodass verspätete Pyright-Befunde
  die Reihenfolge nach der Bereitschaftsmeldung nicht verändern.
- Prüft geführte Suche, Ersetzung, LSP, Completion, Diagnosen und das
  Lazy-Fenster über echte Neovim-Eingabe und authentifiziertes RPC. Prüft
  Signatur- und Diagnosekontext ohne Cursorbewegung. Ergänzt Gegenproben für
  unvollständige Ersetzung, veralteten Diagnosekontext und Lazy-Git-Prüfungen.
  Korrigiert den Cursorweg über ein Dezimalargument in Aufgabe L2.
- Führt die in den Windows-Prüfungen verwendete NVDA-API 2026.3.1 als zuletzt getestet im Manifest.
- Benötigt Pull Requests für Änderungen an `main`, auch zur Releasevorbereitung.
  Dokumentiert semantische Produktversionen, datierte Changelogs,
  GitHub-Releaseentwürfe und die Store-Upgradebasis. Der Paketbuild erkennt
  die neuen Überschriften und funktioniert mit leerem unveröffentlichtem
  Abschnitt. Die PR-Vorlage verlangt ein Changelog zum gesamten Diff.
- Verwendet SCons für den Add-on-Build und das Gettext-Template. Basismanifest
  und Sprachmanifeste folgen der Vorlagenstruktur des NVDA-AddonTemplates.
  Name und Beschreibung im Sprachmanifest stammen aus dem Gettext-Katalog.
- Vereinheitlicht ZIP-Metadaten und die Zeilenenden gebündelter Python-Dateien,
  damit Windows und Linux dieselben Paketdaten verarbeiten.
- Prüft F12-Zuordnung, Editieren, Panes, Tabs, Fensterwechsel und
  Wiederherstellung nach dem Beenden eines Editors auf einem aktiven
  Windows-Gastdesktop mit den aktuellen und den Mindestversionen von NVDA
  und Neovim. Die Windows-Einrichtung beschreibt die optionale
  Visual-C++-Laufzeit für ein frisches System.
- Begrenzt Verbindungsaufbau und Empfang im gemeinsamen Neovim-RPC-Client.
  Ungültige RPC-Nachrichten lösen einen Disconnect aus. Controls werden erst
  über den geprüften, registrierten Kanal gesendet.
- Prüft den lokalen Python-Client gegen echtes Neovim einschließlich
  Sitzungsanmeldung, vollständigem Zustand und Cursor-Routing.
- Beendet den eigenen SSH-Prozess bei Protokollfehlern und beim Abbruch
  während des Prozessstarts, bevor eine weitere Verbindung aufgebaut wird.
- Richtet parallele Testläufe an den verfügbaren logischen Prozessoren aus.
  Bis zu zwölf isolierte Blöcke verkürzen die Pakettests auf Rechnern mit
  vielen Kernen. `-j` bleibt die Grenze pro Lauf.
- Ermöglicht die lokale Windows-Entwicklung mit Git-Abgleich über `origin`.
  `build.cmd` verwendet einen sauberen lokalen Branch. Die Python- und
  Lua-Tests unterstützen native Windows-Pfade und Testprozesse. Der Windows-
  Socketlauf prüft den lokalen TCP-Pfad. Unix-Sockets und PTY laufen unter Linux.

- Verwendet die aktuellen NVDA-Importpfade für Braille-Regionen und behält
  den Rückgriff für NVDA 2026.1 bei. Das gebaute Add-on startet unter
  NVDA 2026.3.1. Die Lua- und Windows-TCP-Tests verwenden Neovim 0.12.6.
- Vereinheitlicht Add-on und Dokumentations-ZIP über einen isolierten
  Buildkern. Der Windows-Build erkennt den offiziellen Pandoc 3.1.11.1
  auch bei Windows-Zeilenenden. Der Linux-Releasebuild verwendet einen
  sauberen, freigegebenen `main`-Stand. Der frühere Git-Ref-Abgleich war
  Bestandteil des Linux-Entwicklungsworkflows. MessagePack 1.1.2 stellt
  offizielle Binärpakete für Python 3.14 bereit.
- Ersetzt den separaten Abgleich generierter und installierter Dokumentation
  durch eine interne Layoutbibliothek und entfernt den ungenutzten Windows-
  Helfer zum Hochladen von NVDA-Logs.
- Repariert die Lazy-Praxistest-Vorbereitung auf gemeinsam genutzten oder
  gemappten Repositorylaufwerken: Die isolierte Git-Konfiguration führt die
  konkreten Fixture-Repositories statt eines Wildcards auf. Die Vorbereitung
  bricht beim ersten fehlerhaften Werkzeug- oder Profiltest mit dem direkten
  Grund ab. Vorhandene Pyright-Installationen werden anhand von Paket,
  Serverdatei und echtem CLI-Aufruf erkannt und direkt über Node gestartet.
  Die Vorbereitung lädt nur die für die Auswahl benötigten Plugins, startet
  jeden Linter genau einmal und wertet dessen eigenen Diagnoseraum aus.
  Der Zustand unterscheidet, welche ausgewählten Profile bereits erfolgreich
  vorgeprüft wurden.
  Konkrete Wiederverwendungs-, Aktualisierungs- und Providerfehler ersetzen
  mehrdeutige Sammelmeldungen.
- Beginnt nach der Beta-Vorabveröffentlichung 0.98.0 die Entwicklungslinie
  0.99.0 mit Entwicklungsbuild 1.
- Vereinfacht den Laufzeitzustand des Neovim-Plugins: Die öffentliche
  Root-Fassade komponiert jetzt eindeutige Besitzer für Ereigniskanal,
  Eingabe, Completion, Befehlszeile, UI-Prompts, Oil-Bestätigungen und
  Kontextwechsel. Öffentliche RPC-/Adapterfunktionen und semantische
  Ereignisse bleiben unverändert. Ein eigener Verhaltenstest belegt den
  Fail-open-Kanalabbau; der Pakettest prüft identische getestete Module statt
  interner Quelltextfragmente. Dieser installierbare Stand ist
  Entwicklungsbuild 2.
- Stabilisiert reale TUI-Regressionstests, indem eine gemeinsame Sendehilfe
  ausstehende PTY-Ausgabe vor jedem physischen Tastenschritt leert. Damit
  blockiert ein voller Test-Ausgabepuffer nicht mehr Neovims Eingabepolling.
- Schließt die kritische Nachprüfung des Neovim-Plugin-Refactorings ab: Der
  Ereigniskanal schützt nun auch ungültige Snapshots, Payload- und
  Versandfehler. Eingabepräfixe bilden einen einzelnen
  markierten Zustand, sodass gekoppelte `g`-Befehle nicht als unabhängige
  Makro-, Register- oder Editbefehle fehlklassifiziert werden; Reconnects
  verwerfen alte geplante Eingabeereignisse. Regressionstests decken diese
  Übergänge, wiederholtes Setup und begrenzte PTY-Entleerung ab. Der Test-Runner
  begrenzt außerdem jeden isolierten Job. Dieser installierbare Stand ist
  Entwicklungsbuild 3.
- Korrigiert die bei einer unabhängigen Lifecycle-Nachprüfung gefundenen
  Restlücken: Jeder interne Publikationsfehler schließt jetzt auch den realen
  RPC-Transport. Eine Verbindungsgeneration verwirft geplante UI-,
  Befehlszeilen-, Kontext-, Diagnose- und Dateimanagerereignisse der alten
  Verbindung; transiente Menü-, Prompt- und Controllerzustände werden vor dem
  nächsten `fullState` still zurückgesetzt. Geplante UI-Abbauten können keine
  neuere UI-Anbindung mehr entfernen. Der Runner beendet bei seinem Zeitlimit
  die vollständige Prozessgruppe statt nur des direkten Testprozesses. Reale
  RPC-, Reconnect-, Menülebenszyklus- und Kindprozess-Regressionstests decken
  diese Grenzen ab. Dieser installierbare Stand ist Entwicklungsbuild 4.
- Vereinfacht die Python-Laufzeit des NVDA-Add-ons nach einem vollständigen
  Architekturaudit. Das Global Plugin ist von mehr als 3200 auf wenige Dutzend
  Zeilen reduziert und verwaltet nur noch die Lebensdauer einer transaktional
  aufgebauten Runtime.
  Verbindungsworkflow, Terminalaktionen, Ereignislieferung, Präsentation und
  zeitversetzte Arbeit haben eindeutige Besitzer; AppModule und
  Braille-Adapter verwenden schmale öffentliche Verträge statt privater
  Global-Plugin-Details. Ein einzelner Dispatcher serialisiert ausgehende
  Steuerdaten, und ein begrenzter Hintergrundworker beendet Clients, ohne den
  NVDA-Hauptthread auf Transportabschluss warten zu lassen. Architektur-,
  Rollback-, Nebenläufigkeits- und Besitztests sichern diese Grenzen; die
  Python-Stilprüfung erfasst nun auch sämtliche Add-on-Tests. Dieser erste
  installierbare Stand des neuen Entwicklungszweigs ist Entwicklungsbuild 1.
- Härtet den Python-Laufzeitumbau nach einer unabhängigen Seniorprüfung. Der
  `ControlDispatcher` hält die Reihenfolge je Client ein, isoliert unabhängige
  Clients mit einem festen Workerpool und lässt den lokalen RPC-Stopp einen
  blockierten Socketversand unterbrechen. Der `ClientStopper` übernimmt jeden
  angenommenen abgetrennten Client statt ihn bei voller Queue besitzlos zu
  lassen. Auswahl- und Passwortdialoge verwenden NVDAs öffentliche modale
  Lebensdauerverwaltung; veraltete Passwörter werden verworfen. Der Lifecycle
  delegiert den vollständigen Verbindungsabbau an genau einen Workflow, während
  die Zustandsmaschine temporär gemerkter Bindungen einen eigenen Controller
  besitzt. Direkte Queue-, Reihenfolge-, Isolation-, Abbruch-, Dialog- und
  Besitztests decken die neuen Grenzen ab. Dieser installierbare Stand ist
  Entwicklungsbuild 2.
- Verbessert die Rückfrage nach einer temporären F12-Tab-Zuordnung: `Ja` besitzt
  wieder den Standardfokus. Ein neues Ankreuzfeld speichert die ausdrücklich
  gewählte Antwort im aktiven NVDA-Konfigurationsprofil; die Einstellung
  `Temporäre Terminalverbindungen` kann anschließend zwischen erneutem Fragen,
  automatischem Merken und automatischem Nichtmerken wechseln. Profilwechsel,
  `Ja`- und `Nein`-Entscheidungen, Abbruch, Dialogfokus und die dialogfreie
  Wiederverwendung sind durch Pakettests abgedeckt. Dieser installierbare Stand
  ist Entwicklungsbuild 3.
- Behebt einen Fokusrennenfehler der F12-Merkabfrage. Die Autorisierung der
  Dialogentscheidung und die einmalige Fokuswiederherstellung besitzen nun
  getrennte Lebensdauern. Ein zwischenzeitlich verbrauchter Fokus-Rücksprung
  verwirft ein späteres `Ja` nicht mehr; bis zur erneuten korrelierten
  Vordergrundbestätigung bleiben Unterdrückung und strukturiertes Tippecho aus,
  sodass andere Windows-Terminal-Fenster ihr natives Tippecho behalten.
  Regressionstests decken mehrfachen Fokuswechsel bei geöffneter Frage ab. Der
  praktische Lauf unter NVDA 2026.2beta10 deckte den Fehler auf und prüfte den
  umgebenden Fokuspfad; das Manifest setzt die zuletzt getestete NVDA-Version
  auf 2026.2. Der korrigierte Build benötigt noch den abschließenden manuellen
  Wiederholungstest. Dieser installierbare Stand ist Entwicklungsbuild 1.
- Verhindert falsche SSH-Wiederverbindungen nach dem Beenden der gebundenen
  entfernten Neovim-Instanz. Eine weiterlaufende Bridge beantwortet
  fokusbedingte Zustandsabfragen zwar weiterhin, doch ein `fullState` mit
  `connection.neovim=disconnected` kann die Transportinstanz nicht mehr
  authentifizieren. Damit lösen Fokuswechsel zwischen einem lokalen und dem
  beendeten SSH-Pane keine wiederholten Verbindungs- und Trennungsklänge mehr
  aus. Direkte Protokolltests decken wiederholte getrennte Zustandsabbilder,
  den anfänglich getrennten Zustand und einen echten späteren Reconnect ab.
  Der praktische Zwei-Pane-Test unter NVDA 2026.2beta10 deckte den Fehler auf;
  der korrigierte Build benötigt noch den manuellen Wiederholungstest. Dieser
  installierbare Stand ist Entwicklungsbuild 2.
- Entfernt die fehleranfällige Rückfrage nach dem Merken einer neuen
  F12-Zuordnung einschließlich Ankreuzfeld, Profilwert und Einstellung. Eine
  erfolgreiche, noch exakt fokussierte Zuordnung wird jetzt automatisch nur
  für die laufende NVDA-/Windows-Terminal-Sitzung gemerkt; der vorhandene
  Vergessen-Befehl entfernt sie weiterhin vorzeitig. Derselbe WT-Pane bleibt
  auch dann zugeordnet, wenn dessen UIA-Provider zwischen den unter
  NVDA 2026.2beta10 beobachteten Runtime-ID-Formen wechselt. Diese
  Normalisierung verlangt gemeinsam denselben Prozess, dasselbe Fensterhandle,
  dieselbe freigegebene Klasse und dieselben Pane-Endkomponenten sowie NVDAs
  positive UIA-Elementgleichheit; andere Panes bleiben getrennt. Direkte und
  Paketregressionstests decken automatisches Merken, Fokusrennen, Aliaswechsel
  und getrennte Panes ab. Der manuelle Wiederholungstest des korrigierten
  Builds unter NVDA 2026.2beta10 bestätigte bei häufigen Wechseln zwischen
  lokalem Pane, SSH-Pane und einem weiteren WT-Fenster stabile, getrennte
  Bindungen, natives Tippecho außerhalb der aktiven Sitzung sowie das
  Ausbleiben falscher Wiederverbindungen nach dem Ende von Remote-Neovim.
  Dieser installierbare Stand ist Entwicklungsbuild 3.
- Härtet nach der vollständigen Unit-Test-Nachprüfung die Protokollgrenzen.
  Boolesche und negative Sequenzen oder Zeitstempel werden bereits in der
  Nachrichtenhülle verworfen. Eine neue Transport-Sitzung beginnt ausschließlich
  mit `fullState` und Sequenz 0; Resync akzeptiert weder alte Zustandsabbilder
  noch fremde Sitzungen mit fortgesetzter Sequenz. Direkte Grenzwert- und
  Negativtests prüfen außerdem MessagePack-Fragmentierung, Textspalten,
  Cursor-Routing und das Entfernen flüchtiger Ergebnisfelder. Dieser erste
  installierbare Stand des Test-Review-Zweigs ist Entwicklungsbuild 1.
- Schließt die strukturellen Punkte der Unit-Test-Nachprüfung. Direkte Tests
  prüfen die extrahierten NVDA-Runtime-Eigentümer ohne vollständige
  `GlobalPlugin`-Konstruktion; redundante Paketfälle wurden entfernt, während
  echte Kompositions-, Persistenz- und Fokusverträge erhalten bleiben.
  Architekturregeln verwenden Syntaxbaum-Invarianten statt fragiler
  Quelltexttreffer, Nebenläufigkeitstests Ereignisse statt kurzer
  Wandzeitgrenzen. Mock- und echte TUI-Bridge-Tests sind dateibasiert getrennt,
  der Runner zeigt Skip-Gründe und Warnungen, und vier gezielte Mutationen
  belegen kritische Protokollverträge.
- Korrigiert den eigenen GitHub-Actions-Job für Neovim-0.12-Tutor-Semantik
  nach der Trennung der Mock- und Socket-Tests. Der Job ruft wieder den
  vorhandenen echten TUI-Test mit seinem aktuellen Modul- und Klassennamen
  auf, statt nach dem erfolgreichen Lua-Test an einem veralteten Importpfad
  abzubrechen.

## 0.98.0

- Legt den offiziellen Pandoc-3.1.11.1-Binärbuild für den lokalen Referenz- und
  CI-Dokumentationsbuild fest. CI prüft das Archiv per SHA-256; das Buildskript
  lehnt abweichend paketierte Builds derselben Version ab, damit sie die
  eingecheckte installierte HTML-Hilfe nicht unterschiedlich erzeugen.
- Belegt den kontextbezogenen Aktivierungsbefehl standardmäßig mit
  `NVDA+Alt+N`. Die Geste bleibt im NVDA-Tastenbefehldialog änderbar und wird
  außerhalb eines passenden fokussierten Windows-Terminal-Controls wie bisher
  durchgereicht.
- Macht Neovims eingebauten `:Tutor` gezielt zugänglicher, ohne eine eigene
  Tutorial-Logik einzuführen. Ab Neovim 0.12 liefern eindeutig erkannte native
  Tutor-Extmarks lokalisierte Meldungen bei einer geänderten Bewertung, die
  Bewertung beim erneuten Lesen der Zeile und dauerhafte, nicht routbare
  Braillemarker. Andere Buffer und Extmarks bleiben unberührt. Ungültige
  Übergänge werden vor dem kanonischen Zustand verworfen; das gilt auch für
  strukturwidrige JSON-Werte.
  Vorhandene Braille-Routing- und Quellzuordnungen bleiben erhalten. Unter
  Neovim 0.10 ist der Tutor-Pfad ohne Beobachter vollständig inaktiv.
  Übergangsmeldungen bleiben an denselben Buffer-, Fenster- und Zeilenkontext
  gebunden. Isolierte Headless-Grenztests und ein echter
  0.12.3-TUI-Vertragstest decken den Umfang ab; der Tutor wurde unter
  Windows/NVDA stichprobenartig mit Sprache und physischer Braillezeile
  praktisch geprüft.
- Stellt nach dem Beenden einer entfernten Neovim-Instanz NVDAs normales
  Terminalverhalten sofort wieder her. Der SSH-Client behandelt den
  authentifizierten Bridge-Status `disconnected` jetzt als
  Verbindungslebenszyklus statt als gewöhnliches Editorereignis, auch wenn SSH
  und Bridge weiterlaufen. Ungültige Statuswerte werden verworfen und ein
  späterer Reconnect benötigt erneut ein gültiges `fullState`.
- Ergänzt im Komponenten-Dialog eine standardmäßig unveränderte
  Konfigurationsauswahl mit einer Grundkonfiguration aus Lazy, Oil, der
  gebündelten Access-Link-Kopie, echten Tabulatorzeichen in einem
  Zwei-Spalten-Raster auch nach dateitypspezifischen Vorgaben,
  ausgeschalteten Zeilennummern sowie Leader-Befehlen für Oil und
  Lazy. Ein isolierter Headless-Start mit lokalen Access-Link-, Lazy- und
  Oil-Verzeichnissen ist unter Neovim 0.10.1 geprüft. Vorhandene reguläre
  `init.lua` und `init.vim` werden vor dem atomaren Austausch in eindeutige
  Sicherungspfade verschoben und im Ergebnisdialog genannt; Fehler stellen die
  Originale aus den erhaltenen Sicherungen wieder her. Symlinks und
  ungewöhnliche Ziele bleiben unverändert, und die Komponentenentfernung
  löscht weder Konfiguration noch Sicherungen. Die lokale
  Windows-Grundkonfiguration wurde praktisch abgenommen.
- Ergänzt als zweiten Konfigurationsweg die sichere Übernahme des vollständigen
  lokalen Windows-Konfigurationsverzeichnisses auf ausgewählte
  Linux-Verbindungen. Eine begrenzte, linkfreie Momentaufnahme wird getrennt
  vom Komponentenpaket über SSH übertragen und auf dem Ziel erneut geprüft;
  vorhandene Konfigurationen werden als vollständige Verzeichnisse vor dem
  atomaren Austausch gesichert. Windows-spezifische Inhalte und
  Ausführbarkeitsrechte werden nicht geraten oder umgeschrieben. Lazy muss die
  installierte Access-Link-Kopie weiterhin ausdrücklich als lokales Plugin
  laden.
- Härtet die Komponentenentfernung mit einer ausdrücklich zu bestätigenden,
  standardmäßig ablehnenden Warnung und einem wiederholten Ergebnishinweis.
  Plugin und Linux-Bridge werden entfernt; Neovim-Konfigurationen und
  Sicherungen bleiben unverändert, einschließlich ausdrücklich eingetragener
  Plugin-Ladeanweisungen, die der Nutzer bei Bedarf selbst entfernt.
- Ergänzt robuste Grundunterstützung für `lazy.nvim`: Access Link gibt dem
  echten Lazy-Puffer einen eindeutigen Kontextnamen und spricht beim Öffnen die
  vollständige Bedienleiste unabhängig von Leerzeile und fensterbreitenbedingtem
  Umbruch. Rein visuelle Rand- und Auffüll-Leerzeichen bleiben bei
  Zeilennavigation von der Sprachausgabe ausgenommen. Grafische Zeichen aus
  privaten Unicode-Bereichen bleiben im gesamten Lazy-Puffer einschließlich
  Sprachexploration stumm, während Braille den unveränderten Text behält.
  Ausschließlich dokumentierte
  Lebenszyklusereignisse liefern neutrale Start-/Endmeldungen über Sprache und
  Braille. Eindeutig über öffentliche Icon-Hervorhebungen erkannte Pluginzeilen
  melden beim Betreten und Umschalten NVDAs lokalisierte Zustände `eingeklappt`
  oder `ausgeklappt`; Braille zeigt die zugehörigen Baumansichtsmarker `+` und
  `-`, ohne sie beim Umschalten durch eine vorübergehende Meldung zu verdecken.
  Die vorhandene NVDA-Zeilenexploration liest die Bedienleiste bei Bedarf
  erneut. Unklare Darstellungen bleiben still. Synchronisierung fasst
  untergeordnete Vorgänge zusammen, ohne Fortschritt, Ergebnis oder Erfolg aus
  Lazys Darstellung zu erraten.
- Ergänzt vier geführte lazy.nvim-Praxistests für Fensterbedienung,
  Installation, Aktualisierung und Synchronisierung. Isolierte lokale
  Git-Fixtures und gepinnte Headless-Vertragstests prüfen die echten
  Endzustände, ohne Benutzerkonfiguration oder installierte Plugins zu ändern.
  Die Einzelauswahl führt diese Aufgaben unter Plugin-Verwaltung auf. Die
  technische Vorprüfung berücksichtigt, dass Lazy seine Oberfläche im
  Headless-Modus absichtlich nicht öffnet; lokale Fixture-Repositories laufen
  ohne Zeilenendenkonvertierung und störende Git-Fortschrittsausgaben.
  Die F5-Endprüfung behandelt eine leere optionale Pfadliste
  plattformübergreifend als Array statt als Lua-`vim.NIL` und nennt die
  tatsächlich bestätigten Revisionen und Entfernungen. Alle vier geführten
  Abläufe wurden im Windows-/NVDA-Referenzpfad praktisch bestätigt; ihre
  Abschlussmeldungen bleiben ausdrücklich neutral, bis F5 den Git-Endzustand
  belegt.
- Integriert alle acht deutschen und englischen HTML-Dokumente in das Add-on.
  Ein oberstes `Neovim Access Link`-Menü öffnet Einstellungen,
  Komponentenverwaltung und die zur NVDA-Sprache passende installierte Hilfe.
- Beschreibt im Handbuch die getrennten, frei belegbaren Befehle zum Kopieren
  von Visual-Auswahl oder Register 0 in die Windows-Zwischenablage und zum
  Einfügen der Windows-Zwischenablage in Neovim.
- Ergänzt im Manifest Standardhilfedatei und das aus dem aktuellen deutschen
  beziehungsweise englischen Changelogabschnitt erzeugte Änderungsprotokoll.
  Entwicklungsbuilds verwenden den unveröffentlichten Abschnitt; bei Releases
  wird er redaktionell in die Version überführt und anschließend zurückgesetzt.
- Prüft das gebaute Basis- und Lokalisierungsmanifest streng gegen die
  Feldmenge des offiziellen NVDA-AddonTemplates. Fehlende, leere, unbekannte
  oder fehlerhaft formatierte Angaben sowie eine fehlende englische
  Standardhilfe brechen den Paketbuild ab.
## 0.97.0

- Ergänzt die HTTPS-Projektadresse im Add-on-Manifest.
- Ergänzt einen optionalen parameterlosen Windows-Build aus dem Quellcode. Ein
  temporäres Python-Environment schützt die Systeminstallation; das
  eingebettete Linux-Paket erhält portable Python-Module und reproduzierbare
  Unix-Metadaten.
- Ergänzt LSP-Parameteransagen im Insert-Modus sowie gehaltene, rein lesende
  Ansichten für Signaturen, Parameter und Diagnosen mit korrelierter Sprache
  und Braille.
- Härtet native Completion, `nvim-cmp` und `blink.cmp`, einschließlich
  Dokumentationsauflösung, Menüklängen und dem Zustand ohne ausgewählten
  Kandidaten. Behebt zudem die falsche Ablehnung der bewusst deaktivierten
  automatischen Blink-Menüöffnung durch die Praxistest-Vorprüfung.
- Macht native inkrementelle Suche, `inccommand`-Ersetzungsvorschauen,
  Quickfix-/Positionslisten, Ersetzungsabfragen, Mehrbuffer-Ersetzungen und
  LSP-Rename-Abschlüsse zugänglich. Neovim und der Sprachserver behalten die
  Ausführung; Access Link bündelt interne Buffer-, Cursor- und Kontextwechsel
  zu einer belegbaren Abschlussmeldung. Automatisierte Mehrdateitests decken
  Quickfix-Dateien, gelistete Buffer und Argumentdateien ab; die geführten
  L4- bis L6-Abläufe isolieren die verbleibende praktische NVDA-Prüfung.
- Vereinheitlicht Diagnosen aus LSP, `nvim-lint`, ALE und `none-ls.nvim`,
  erweitert Navigationsbefehle und ergänzt getrennte Fehler-, Warn- und
  Leerbestätigungsklänge. Der Clang-Tidy-Praxistest startet unter Windows
  direkt das gepinnte Programm, verwendet einen festgelegten C-Modus und die
  mitgelieferte Testkonfiguration und wertet beide Ausgabekanäle aus. Eine
  einheitliche begrenzte Wartezeit berücksichtigt kalte Providerstarts auf
  Windows und Netzlaufwerken. Markdownlint prüft die absolute Testdatei
  statt eines unzuverlässigen stdin-Kaltstarts. Die Einrichtung prüft reale
  Linterausgaben vorab und sammelt Fehler aller ausgewählten Profile in einem
  Lauf.
- Behebt Linux-Sitzungserkennung mit abweichenden Laufzeitumgebungen und ohne
  `XDG_RUNTIME_DIR` sowie Fokus- und Merkpfade nach der optionalen
  F12-Rückfrage.
- Trennt sichere, SSH- und Socket-Prüfungen in unabhängige Testphasen und
  erweitert die reproduzierbaren Completion-, LSP-, Linter- und geführten
  Praxistests. Kompakte Aufgabenkarten nennen Zweck, nummerierte Schritte und
  Bestehenskriterium; F2 wiederholt die Aufgabe, während F1 und F11 wegen der
  Standardbelegungen von Neovim und Windows Terminal frei bleiben.
- Aktualisiert Auswahl- und LSP-Test-APIs für Neovim 0.12, ohne die
  Kompatibilität mit Neovim 0.10 aufzugeben.
- Ordnet Quick Guide und Handbuch nach Leseraufgaben neu. Eine echte, getestete
  Lua-Beispielkonfiguration erzeugt identische Codeblöcke für GitHub und die
  deutschen und englischen HTML-Handbücher.
- Präzisiert nach erneutem Architekturaudit die verbleibende prozessweite
  Rolle des Global Plugins, ohne den AppModule-eigenen Ereignispfad zu
  verbreitern.
- Ordnet die Entwicklerdokumentation nach Einstieg, aktuellen Erklärungen,
  Aufgaben, Referenzen und Entscheidungen neu, entfernt veraltete
  Transportaussagen und ergänzt einen eigenen CI-Build mit automatischer
  Struktur- und HTML-Metadatenprüfung der deutschen und englischen Fassungen.

## 0.96.0

- Ergänzt strukturierte Braillezeilen, Cursor-Routing, Standardnavigation und
  einen pro Sitzung gespeicherten Braille-Explorationsmodus.
- Macht Neovims eingebaute `z=`-Rechtschreibvorschläge über Sprache,
  Braille und kontextbezogene NVDA-Befehle zugänglich.
- Gleicht Rechtschreibfeedback an NVDAs Dokumentformatierung an und stabilisiert
  Brailleausschnitte bei Fokus-, Sitzungs- und Textwechseln.

## 0.95.2

- Führt den Sprachexplorationsmodus für Zeichen, Wörter und Zeilen ein, ohne
  den echten Neovim-Cursor zu bewegen.
- Ergänzt Ursprungsklänge und getrennte Detailoptionen für normale Navigation
  und Explorationsabschluss.

## 0.95.1

- Verschlankt das Global Plugin zu einer Kompositionswurzel mit ausgelagerten
  Diensten für Fokus, Zuordnung, Editorzustand, Verbindungen, Einstellungen,
  Braille und Laufzeit.
- Erhält lokale und SSH-Sitzungen über mehrere Windows-Terminal-Fenster, Tabs
  und Panes einschließlich Zwischenablage und Komponentenverwaltung.

## 0.95.0 (Beta)

- Verlegt Windows-Terminal-Ereignisse, Overlayauswahl, `nextHandler` und frei
  belegbare Terminalbefehle in das AppModule.
- Begrenzt F12 auf die konkrete AppModule- und `TermControl`-Identität und
  verhindert ein eingefügtes `<F12>` bei einer Zuordnung im Insert-Modus.
- Verwendet NVDAs Windows-Bindings und Stilkonventionen im NVDA-seitigen Code.

## 0.94.2

- Strukturiert Anwender- und Entwicklerdokumentation von Grundbegriffen bis zu
  Architektur, aktuellem Status, Plan und Verlauf.
- Gleicht UI-Bezeichnungen mit Gettext-Katalog und NVDA-Quellcode ab und
  beschreibt Prüfung und Support als risikobasierten Best-Effort-Prozess.

## 0.94.1

- Liefert den vollständigen deutschen Gettext-Katalog samt reproduzierbaren
  Katalog-, MO- und Paketprüfungen aus.

## 0.94.0 (Vorabversion)

- Vereinheitlicht Produkt-ID, Paketnamen, Konfigurationsabschnitt und
  Artefaktpräfix unter `NeovimAccessLink`.

## 0.93.0 (Vorabversion)

- Härtet Terminal- und Bufferwechsel, strukturierte Kommandozeilen- und
  Prozessmeldungen sowie Fenster- und Tab-Kontextausgabe.
- Korrigiert die erneute F12-Zuordnung von einer beendeten lokalen zu einer
  SSH-Neovim-Sitzung.

## 0.92.0 (Beta-Vorabveröffentlichung)

- Ergänzt einstellbare Fokusausgabe, control-spezifische
  Windows-Terminal-Abschottung und ausdrückliche Zwischenablagebefehle für
  lokale und SSH-Verbindungen.

## 0.91.0 (Beta-Veröffentlichung)

- Führt control-spezifische Windows-Terminal-Zuordnung mit fail-open
  Fokuswechseln und einmaliger F12-Autorisierung ein.
- Bestätigt lokale und entfernte Verbindungen in mehreren Tabs und geteilten
  Panes praktisch.

## 0.90.0 (Beta-Veröffentlichung)

- Ergänzt die praktisch bestätigte Fokus-Kontextansage mit Datei, Modus und
  konfiguriertem Verbindungsnamen.

## 0.89.35 (Beta-Veröffentlichung)

- Härtet Sitzungsregistrierung und Windows-Terminal-Bindungen für lokale und
  entfernte Neovim-Sitzungen.
- Übernimmt Neovims externe UI erst nach authentifizierter Registrierung und
  gibt sie bei Fehlern fail-open an die native TUI zurück.
