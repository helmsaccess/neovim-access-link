# Aktueller Status

Stand: 2026-07-15, Beta-Testbuild 0.89.5

## Gesamtbewertung

Das Add-on wurde unter Windows 11 25H2 mit NVDA 2026.1.1,
`OpenSSH_for_Windows_9.5p2` mit `LibreSSL 3.8.2` und Windows Terminal 1.24.x
praktisch getestet;
die Gegenstelle lief auf Rocky Linux 10.2 mit Neovim 0.10.1. Installation aus
dem NVDA-Menü, die vom Add-on verwaltete SSH-stdio-Verbindung und die Nutzung
in einer bestehenden SSH-/tmux-Sitzung funktionieren grundsätzlich. Der Stand
eignet sich für vorsichtige Erprobung, ist aber insgesamt noch im Alpha- bis
Beta-Zustand, nicht erschöpfend getestet und nicht stabil veröffentlicht.

Die deutsche Anwenderdokumentation liegt als kurzer Einstieg und vollständiges
Handbuch in getrennten Markdown-Quellen vor. Der reproduzierbare Build erzeugt
`neovim-access-link-quick-guide-de.html` und
`neovim-access-link-handbook-de.html`. Die Entwicklerdokumentation wird als
`neovim-access-link-developer-documentation-de.html` gebaut. Quick Guide,
Handbuch und Entwicklerdokumentation werden zusätzlich auf Englisch erzeugt.

## Aktueller technischer Stand

- Protokoll v2 ist die einzige unterstützte Neovim-NVDA-Schnittstelle.
- Entfernte Linux-Sitzungen verwenden ausschließlich längenbegrenztes
  MessagePack-Protokoll v2 über SSH-stdin/stdout. Lokale Windows-Sitzungen
  verwenden Neovims MessagePack-RPC über einen dynamischen, exakt an
  `127.0.0.1` gebundenen Port. Allgemeine Netzwerklistener, Tunnelports,
  Anwendungstokens und v1-Aushandlung bleiben ausgeschlossen.
- Bridge und Plugin werden rootlos pro Linux-Benutzer aus dem NVDA-Menü
  installiert. Das vollständige, beim Add-on-Build erzeugte Linux-Paket ist im
  Add-on eingebettet; zur Zielmaschine wird kein externer Download benötigt.
  Mehrere gespeicherte Verbindungen können ausdrücklich per Checkbox in einem
  Durchlauf gewählt werden; die Sammelcheckbox folgt auch manuellen
  Einzelmarkierungen. Jedes abgeschlossene Ziel erhält eine kurze
  Fortschrittsmeldung; eine abschließende Sprachausgabe und eine nicht
  blockierende kompakte Ergebnisübersicht trennen erfolgreiche und
  fehlgeschlagene Aktualisierungen. SSH-Upload und entfernte Installation sind
  jeweils auf 60 Sekunden begrenzt. Der Aktualisierungsbefehl
  liegt unter NVDAs „Tools“-Menü; die Add-on-Einstellungen werden ausschließlich
  als reguläre NVDA-Einstellungskategorie angeboten.
  Ein zweiter Werkzeugmenüeintrag entfernt die Komponenten im Hintergrund von
  ausdrücklich ausgewählten lokalen oder entfernten Zielen. Er bewahrt
  Verbindungsprofile, Benutzerkonfiguration, SSH-Dateien und fremde Plugins und
  meldet jedes Ziel in einer nicht blockierenden Ergebnisübersicht.
  Die validierte Paketkonfiguration hält Neovims Zuordnungstaste und NVDAs
  korrespondierende Geste konsistent. Ein normales `nvim datei` genügt
  anschließend.
- Mehrere Verbindungsprofile, Hosts, Benutzer und parallele Neovim-Sitzungen
  werden getrennt verwaltet. F12 markiert die tatsächlich fokussierte
  Neovim-Instanz kurzzeitig und bindet genau sie an den fokussierten
  Windows-Terminal-Tab; interne IDs müssen nicht eingegeben werden. Für einen
  bereits gebundenen Tab gilt dessen Ziel. Beim Aktivieren erfasst ein
  begrenzter Hintergrundscan die lokale Registry und alle ohne Passwortdialog
  erreichbaren gespeicherten SSH-Verbindungen. In einem ungebundenen Tab sucht
  F12 die veränderte Claim-Sequenz über diesen gesamten Bestand; ein
  Standardziel gibt es nicht. Passwortprofile ohne Laufzeitpasswort und
  Sonderfälle bleiben ausdrücklich über den Verbindungsdialog erreichbar.
- Die native Windows-CLI `nvim.exe` in Windows Terminal ist als eigener
  Verbindungstyp implementiert. Das eingebettete Plugin kann über denselben
  Komponenten-Dialog lokal installiert werden, registriert lokale Sitzungen
  unter `%LOCALAPPDATA%\nvim-nvda` und wird per F12 eindeutig zugeordnet.
  Lokale und SSH-Sitzungen können parallel an unterschiedliche Tabs gebunden
  sein. Der Grundpfad sowie lokale und SSH-Tabs parallel wurden unter Windows
  praktisch bestätigt. Zwei gleichzeitige lokale Tabs, mehrere Windows-
  Terminal-Fenster, tmux, die zielübergreifende Discovery und der Wechsel
  zwischen lokalen und entfernten Sitzungen funktionieren praktisch. Auch die
  dev.42-Korrektur für ein bereits vor der Aktivierung fokussiertes Terminal,
  der normale F12-AppModule-Pfad, das globale Aktivierungs-Toggle, verzögerte
  Claim-Callbacks und das Lesen aggregierter NVDA-Konfiguration wurden praktisch
  bestätigt.
- In 0.89.3 wird ein frischer lokaler F12-Claim vor SSH geprüft und unmittelbar
  verbunden. Eine bis zu 1,5 Sekunden begrenzte Nachsuche fängt verzögert
  sichtbare atomare Registry-Updates ab. Die automatisierten Regressionstests
  sind bestanden; die lokale automatische und manuelle Zuordnung wurde mit
  dem installierten Beta-Build praktisch als zuverlässig bestätigt.
- Der Aktivierungsbefehl erfasst mögliche Ziele, öffnet aber noch keine
  dauerhaften Bridgeverbindungen. Nach der Bereitschaftsmeldung verbindet F12
  den eindeutigen Treffer; der explizite Dialogweg bleibt für Passwort- und
  Sonderfallauswahl.
- Add-on-Rückmeldungen und Verbindungswerte liegen in einem validierten nativen
  NVDA-Konfigurationsabschnitt. NVDAs reguläre Profile, Vererbung und Auslöser
  gelten dadurch ohne eine eigene Profilwahl des Add-ons. Profilwechsel laden
  wirksame Werte neu, unterbrechen aber keine laufende Editorverbindung.
- Optionales, ausdrücklich bestätigtes Merken von Windows-Terminal-Tabs über
  stabile UIA-Runtime-IDs; nur im RAM, ohne Titel-/Textauswertung und mit
  sicherem Fallback auf den Verbindungsdialog.
- Aktivierung, Verbindung, strukturierte Ausgabe, Braille-Overlay und native
  Terminalunterdrückung liegen im ausschließlich für Windows Terminal geladenen
  NVDA-AppModule. Darin müssen freigegebene UIA-Klasse und stabile Runtime-ID
  gemeinsam passen. PuTTY ist in der Frontendrichtlinie nur als geplant
  vermerkt und kann ohne implementierten Adapter nicht freigeschaltet werden.
  Ereignisse, Overlays und F12-Zuordnung liegen im ausschließlich für
  `windowsterminal.exe` geladenen NVDA-AppModule. Das globale Dienstmodul fragt
  fremde Fenster nicht ab und besitzt keine globalen Eingabeskripte.
- Strukturierte Sprache und Braille decken Modi, Navigation, Bearbeitung,
  Visual Character/Line/Block, Einrückung, Completion und Menüs, Suche,
  Diagnostics und Rechtschreibung, Folds, Marks, Register, Makros, Terminal-
  Normalmodus sowie verbreitete Dateimanager ab.
- Bei Deaktivierung, falscher Sitzung oder Verbindungsverlust fällt das Add-on
  auf die normale NVDA-Terminalausgabe zurück.
- Das Repository enthält genau zwei typisierte Produktpfade: SSH-stdio für
  Linux und IPv4-Loopback-RPC für lokales Windows-Neovim. Historische
  allgemeine TCP-/Tokenimplementierungen und Benchmarkprototypen bleiben
  entfernt.

Die detaillierte Funktionsmatrix steht in [accessibility.md](accessibility.md),
die Architektur in [architecture.md](architecture.md) und die Bedienung im
[Anwenderhandbuch](../manual/README.md).

## Verifikation dieses Branches

- 239 Python-Tests: 199 Add-on/Core einschließlich Repositoryrichtlinien,
  26 Protokoll und 14 Bridge
- 148 Lua-Assertions mit echtem Neovim
- alle Bridge-/TUI-/Sockettests bestanden; vier in der eingeschränkten
  Socket-Sandbox erwartbar gescheiterte Fälle wurden isoliert außerhalb dieser
  Sandbox vollständig und erfolgreich wiederholt
- Add-on-Archiv 0.89.5, getrennte deutsche und englische HTML-Dokumente, zentrale Metadatenableitung,
  Manifestversion und interne Links wurden automatisiert geprüft
- Die vollständige Komponentenentfernung wurde mit dem installierten
  Testbuild praktisch bestätigt.

Reproduzierbare Befehle stehen in [testing.md](testing.md).

## Bekannte Grenzen und nächste Arbeit

1. Die Brailleunterstützung wurde noch mit keiner echten Braillezeile geprüft
   und enthält sehr wahrscheinlich Fehler. Hardwaretests verschiedener
   Hersteller einschließlich Punkte 7/8 und Routingtasten sowie anschließende
   Korrekturen sind ein wichtiges priorisiertes TODO.
2. Lange Arbeitsläufe, wiederholte SSH-Abbrüche, große Dateien und schnelle
   Ereignisfolgen brauchen weitere Belastungstests.
3. Weitere Windows-Terminals, SSH-Konfigurationen, NVDA-Profile, Sprachen und
   Neovim-Versionen gehören in eine breitere Kompatibilitätsmatrix.
4. Frei gezeichnete Plugin-Oberflächen benötigen eine Standard-API oder einen
   Adapter; nicht jede beliebige TUI-Darstellung ist automatisch zugänglich.
5. Lokales Neovim unter Windows ist für die CLI-Version in Windows Terminal
   [implementiert, dokumentiert und praktisch bestätigt](../manual/communication.md).
   `NVIM_APPNAME`, portable
   Installationen und die GUI-Version sind noch nicht unterstützt.
6. Eine ältere Neovim-Version auf Rocky Linux 9 funktionierte mit dem aktuellen
   Stand nicht. Die genaue Versionsgrenze und Ursache sind nicht untersucht;
   Neovim 0.10.1 auf Rocky Linux 10.2 bleibt die bestätigte Basis. Diese
   Rückwärtskompatibilität hat derzeit keine Priorität.
7. Auch außerhalb von Braille wurden noch nicht alle Add-on-Funktionen
   ausführlich praktisch geprüft. Lokalisierung, Releaseprüfung und ein
   erschöpfender stabiler Abnahmelauf stehen noch aus.
