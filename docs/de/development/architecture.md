# Architektur

Dieses Kapitel erklärt zuerst das Gesamtbild und folgt danach einer Verbindung
von ihrem Start bis zur Ausgabe. Spezialfälle stehen bewusst am Ende. Wer das
Projekt zum ersten Mal liest, sollte dieses Kapitel vor dem Protokoll und den
einzelnen ADRs lesen.

## Ziel und Grundprinzipien

Neovim Access Link macht nicht die sichtbare Terminaloberfläche zugänglich.
Stattdessen beschreibt das Neovim-Plugin den Editorzustand mit semantischen
Ereignissen: Modus, Cursor, aktuelle Zeile, Menüauswahl, Meldung oder
Dateimanagereintrag. Das NVDA-Add-on wandelt diese Daten in Sprache, Klänge und
Braille um.

Aus diesem Ansatz folgen fünf Regeln:

1. Neovim ist die Quelle für Editorsemantik; Screen-Scraping ist nur ein enger
   Fallback, wenn keine zuverlässige API oder Ereignisquelle existiert.
2. Transport, Protokollprüfung, kanonischer Zustand, Präsentation und Fokus
   bleiben getrennte Schichten.
3. Netzwerk-, SSH-, Reconnect-, Parsing- und Installationsarbeit blockiert nie
   NVDAs Hauptthread.
4. Eine Ausgabe oder Unterdrückung gilt nur für die konkret zugeordnete
   Neovim-Sitzung und das konkret gebundene Windows-Terminal-Control.
5. Fehler öffnen den normalen NVDA-Terminalpfad wieder: Das System fällt offen
   aus, nicht still.

Die Entscheidung für diese Integration ist in
`adr/0001-neovim-integration-point.md` begründet.

## Laufzeitmodell: drei Prozesse

Zur Laufzeit sind höchstens drei Prozesse beteiligt:

| Prozess | Läuft wo? | Verantwortung |
|---|---|---|
| Neovim mit Lua-Plugin | lokal unter Windows oder entfernt unter Linux | Erzeugt semantische Zustände und registriert die Sitzung. |
| Python-Bridge | nur bei einer entfernten SSH-Verbindung auf Linux | Verbindet den privaten Neovim-RPC-Socket mit einem begrenzten Protokoll über SSH-stdin/stdout. |
| NVDA mit Add-on | Windows | Verwaltet Verbindungen und Fokus, prüft Ereignisse und plant Sprache, Klänge und Braille. |

`protocol/python/` und `nvda-addon/core/` sind keine weiteren Prozesse. Es sind
Bibliotheken, die in Bridge beziehungsweise Add-on eingebunden werden. Die
genauen Quellverzeichnisse und Einstiegspunkte stehen in
`repository-layout.md`.

## Zwei Datenwege

### Lokales Neovim unter Windows

```text
Neovim + Lua-Plugin
  │ semantische nvim_nvda_event-RPC-Notifications
  │ dynamischer Listener ausschließlich auf 127.0.0.1
  ▼
lokaler Protokollclient im NVDA-Add-on
  │ geprüfte Protokoll-v2-Nachrichten
  ▼
kanonischer Zustand → Sprach-/Klang-/Brailleplanung
```

Das Plugin startet den Listener mit der festen Adresse `127.0.0.1:0`.
Neovim wählt den freien Port. Der Client bildet daraus denselben begrenzten
Nachrichtenvertrag wie bei SSH; es gibt aber keinen Bridgeprozess und kein
stdio-Framing.

### Entferntes Neovim unter Linux

```text
Neovim + Lua-Plugin
  │ privater Unix-RPC-Socket
  ▼
Python-Bridge
  │ Protokoll v2, gerahmt über SSH-stdin/stdout
  ▼
SSH-Client im NVDA-Add-on
  │ geprüfte Nachrichten
  ▼
kanonischer Zustand → Sprach-/Klang-/Brailleplanung
```

Das Add-on startet Windows-OpenSSH mit `-T`. Die Bridge verbindet sich mit dem
privaten Unix-Socket der gewählten Neovim-Sitzung. Sie exponiert nicht Neovims
allgemeine RPC-Schnittstelle, sondern nur die in `protocol.md` dokumentierten
Ereignisse und Steuerbefehle. Es gibt keinen Tunnel-Port, allgemeinen
TCP-Listener oder Laufzeitdownload.

## Zentrale Begriffe

Die Begriffe beschreiben verschiedene Stufen und dürfen nicht
gleichgesetzt werden:

| Begriff | Bedeutung |
|---|---|
| Sitzung | Eine laufende Neovim-Instanz mit geladenem Plugin und eigenem Registryeintrag. |
| Session-Registry | Privates Verzeichnis mit JSON-Sitzungsdateien. Es ist ausdrücklich nicht die Windows-Registry. |
| Verbindungsprofil | Gespeicherte Angaben für ein SSH-Ziel; die lokale Windows-Verbindung ist ein eigener fester Zieltyp. |
| Sitzungsmarkierung | Ausdrücklicher physischer Tastendruck im fokussierten Neovim, standardmäßig F12. |
| Claim | Monotoner Zähler und Zeitwert im Sitzungsdatensatz, der diese Markierung maschinenlesbar belegt. |
| Zuordnung oder Binding | Bindung einer konkreten Windows-Terminal-Identität an eine Verbindungsinstanz im Arbeitsspeicher des Add-ons. |
| Verbindung | Dauerhafter lokaler RPC- oder SSH-stdio-Transport zu genau einer Neovim-Sitzung. |

Die dateibasierte Session-Registry registriert Neovim-Sitzungen, nicht
Windows-Terminal-Fenster, Tabs oder Panes. Unter Windows liegt sie normalerweise
unter `%LOCALAPPDATA%\nvim-nvda\sessions`, unter Linux unter
`$XDG_RUNTIME_DIR/nvim-nvda/sessions` oder einem privaten, benutzerbezogenen
Fallback unter `/tmp`. Sie verwendet keine Schlüssel unter `HKCU` oder `HKLM`.

Eine `TerminalIdentity` bezeichnet das konkrete per UI Automation erkannte
Terminal-Control. In Windows Terminal kann das der Inhalt eines Tabs oder
eines einzelnen Panes sein. Ein Fensterhandle allein wäre dafür nicht präzise
genug.

## Lebenszyklus einer Verbindung

### 1. Das Plugin registriert die Neovim-Sitzung

Beim Start lädt `plugin/nvim_nvda.lua` das Lua-Modul. `session.lua` legt einen
Schema-3-JSON-Datensatz atomar an. Er enthält unter anderem Sitzungskennung,
Nonce, Prozessdaten, RPC-Endpunkt und Claim-Zähler. Unter Linux gehören Socket
und Datensatz dem aktuellen Benutzer; unter Windows ist der RPC-Endpunkt fest
an IPv4-Loopback gebunden.

Die Datei ist Discovery-Metadaten, noch keine Vertrauensentscheidung. Ein alter
oder fremder Datensatz darf deshalb allein weder Ausgabe aktivieren noch ein
Terminal binden.

### 2. Aktivierung erstellt nur eine Inventur

Beim manuellen Aktivieren liest das Add-on lokale Sitzungsdateien und fragt
konfigurierte SSH-Ziele im Hintergrund ab. Es merkt die vorhandenen
Claim-Zähler als Baseline. Diese Inventur stellt keine dauerhafte Verbindung
her und ordnet auch kein Terminal automatisch zu.

Passwortprofile, die nicht automatisiert geprüft werden können, bleiben über
die manuelle Zielauswahl erreichbar. Auch dann ist die physische
Sitzungsmarkierung erforderlich.

### 3. F12 weist das fokussierte Terminal einer Sitzung zu

Die F12-Mechanik verbindet zwei voneinander unabhängige Beobachtungen:

1. Nach einem Treffer der Claim-Taste fragt die Windows-Terminal-AppModule an
   NVDAs öffentlicher `decide_executeGesture`-Grenze das aktuelle Fokusobjekt
   ab. Nur dessen konkrete registrierte AppModule-Instanz darf die vollständige
   `TermControl`-Identität gegen das Gate autorisieren. Die physische Taste
   läuft unverändert an die Anwendung weiter.
2. Das Neovim-Plugin erkennt dieselbe unveränderte Taste mit `vim.on_key`.
   Außerhalb des Eingabe-Callbacks erhöht es atomar `claimSequence` und
   aktualisiert den monotonen Zeitwert seiner Sitzungsdatei. Ein ansonsten
   unbelegtes F12 wird nur im Insert-Modus nach dieser Beobachtung konsumiert,
   damit kein `<F12>` in den Buffer gelangt; Neovim 0.10 benötigt dafür eine
   schmale Insert-Mode-Zuordnung.
3. Das Add-on liest die Kandidaten erneut. Nur ein gegenüber der Baseline
   frischer, eindeutiger Claim darf die Zuordnung auslösen. Kein Treffer bleibt
   wirkungslos; mehrere Treffer erfordern eine Auswahl.

Der Claim selbst öffnet keinen Transport und authentifiziert keine Sitzung. Er
belegt nur, welche Neovim-Instanz den Tastendruck gesehen hat. Die eigentliche
Zuordnung bleibt ausschließlich im Speicher des Add-ons und kann für mehrere
Tabs, Panes und Fenster getrennt bestehen.

### 4. Der dauerhafte Transport wird authentifiziert

Nach der Zuordnung startet genau eine `ConnectionInstance` den lokalen RPC-
oder SSH-stdio-Transport. Auf dem dauerhaften Neovim-RPC-Kanal wird die Nonce
des Sitzungsdatensatzes geprüft, bevor das Plugin diesen Kanal registriert und
semantische Ereignisse sendet. Discovery öffnet keine kurzlebigen
Editor-RPC-Verbindungen.

Der erste gültige `fullState` ist der Authentifizierungspunkt auf der
Add-on-Seite. Erst danach darf die Instanz strukturierte Ausgabe übernehmen.
Bei SSH kommen zusätzlich Host- und Benutzer-Authentifizierung durch OpenSSH,
ein festes Protokoll-v2-Markerformat, Sequenzprüfung und Heartbeats hinzu.

### 5. Ereignisse werden zu Ausgabe

Das Plugin veröffentlicht kleine, typisierte Ereignisse. Protokollclient und
Bridge begrenzen und validieren sie, bevor ein kanonischer Zustands-Cache
aktualisiert wird. Der `SpeechPlanner` und der dauerhafte Brailleplan erhalten
diesen Zustand; sie führen keine Netzwerk- oder Neovim-Aufrufe aus.

Empfangsthreads rufen NVDA nicht direkt auf. Sie stellen fertige Ergebnisse
mit `queueHandler` in NVDAs Ereigniswarteschlange. Nur dort werden Sprache,
Klänge, Braille und UI aktualisiert.

### 6. Fokuswechsel fordert einen bestätigten Kontext an

Beim Wechsel zwischen Windows-Terminal-Controls prüft der
`ConnectionInstanceManager` die exakte `TerminalIdentity`. Eine gemerkte
Zuordnung reicht nicht sofort zur Unterdrückung: Das Gate wird zunächst
geschlossen und die zugeordnete, bereits authentifizierte Instanz erhält eine
`requestFocusContext`-Anfrage.

Nur eine Antwort mit passender Anfrage-ID, Instanz, Bindung und weiterhin
identischem Fokus öffnet das Gate wieder. So kann ein anderer Tab, ein anderes
Pane oder ein Shell-Control im selben Fenster nicht versehentlich den Zustand
einer früheren Neovim-Sitzung übernehmen.

### 7. Trennung und Deaktivierung fallen offen aus

Bei Protokollfehlern, Sequenzlücken, ungültigem Zustand, Transportende,
Fokusverlust oder manueller Deaktivierung verliert die betroffene Instanz ihre
Authentifizierung. Das Gate gibt die native Terminalausgabe wieder frei.
Reconnects laufen mit begrenztem Backoff im Hintergrund; sie dürfen die
Ausgabe nicht während eines unbestätigten Zustands erneut schließen.

## Zuständigkeiten der Schichten

| Schicht | Besitzt | Besitzt ausdrücklich nicht |
|---|---|---|
| Neovim-Plugin | Editorsemantik, Buffer-/Fenster-/Tabidentität, UTF-8-Bytespalten, Menüs, Meldungen, Dateimanagerzustand | Windows-Fokus, Sprache, SSH-Lebenszyklus |
| Bridge | Unix-RPC-Verbindung, stdio-Framing, begrenzte Weiterleitung | freie RPC- oder Befehlsausführung, Präsentation |
| Protokollclient | Größen-, Typ-, Sitzungs-, Sequenz-, Heartbeat- und Resyncprüfung | Entscheidung über Sprache oder Terminalfokus |
| `ConnectionInstanceManager` | Instanzen und Bindung von `TerminalIdentity` zu Instanz | Erraten einer Bindung aus Titel oder Terminaltext |
| `ConnectionCoordinator` | Instanzmanager, aktiver Client, Gate und aktiver Sprachplaner, Authentifizierung, Zuordnungen, korrelierte Anfragen, getrennte Laufzeitzustände sowie Auswahl, Fokusbestätigung und Zustandsbereinigung einer Instanz | NVDA-Ereignisse, `nextHandler`, Dialoge oder konkrete NVDA-Ausgabe |
| `ServiceRegistrar` | identitätsgeprüfte Veröffentlichung des vollständig initialisierten `TerminalIntegrationService` | Lebenszyklusentscheidung oder Terminalereignisse |
| `TerminalIntegrationService` | schmaler öffentlicher Vertrag für Fokus, feste Terminalbefehle, F12-Claims und strukturierte Brailleinteraktion | Anwendungsevents, `nextHandler`, dynamische Methodennamen oder Zugriff auf private Laufzeitzustände |
| `TerminalFocusService` | konkrete Terminalidentität, Fokusgeneration, AppModule-/Adapterkorrelation, Fokusabschluss und konservative Bereinigung geschlossener Controls | Global-Plugin-Instanz, Netzwerk-I/O, Anwendungsevents oder `nextHandler` |
| `SettingsService` | Laden, Normalisieren, Speichern und Profilwechsel der Add-on-Einstellungen sowie unveränderliche Änderungsberichte | Dialogzustand, Terminalereignisse, Fokus oder Verbindungen |
| `SessionGate` | Entscheidung, ob native Terminalausgabe unterdrückt werden darf | Editorsemantik und Transport |
| Speech-/Brailleplanung | lokalisierte, priorisierte Präsentation | Netzwerk, Neovim-RPC und Fokusbindung |
| `NvdaPresentation` | NVDA-spezifische Ausgabe geplanter Sprache, Braillemeldungen, Töne und Add-on-Klänge | Sprachplanung, Transport, Fokusbindung oder Dialoge |
| Global Plugin | NVDA-Prozesslebenszyklus sowie Zusammensetzung und Beenden gemeinsamer Dienste | Anwendungsevents, frei belegbare Terminalbefehle, `nextHandler`, Overlayauswahl, Implementierung von Einstellungen, Werkzeugen oder Präsentationsausgabe |
| `NvdaUiManager` | einmalige und symmetrische Registrierung von Einstellungen und Werkzeugen, Verbindungsformulare, Komponenteninstallation und -entfernung | Global-Plugin-Instanz, Terminalereignisse, Fokusbindung und Unterdrückung |
| Windows-Terminal-AppModule | UIA-Ereignisse, Overlayauswahl, konkreter Terminalfokus, frei belegbare Terminalbefehle, jeder Aufruf von `nextHandler` sowie Übergabe oder Unterdrückung nativer Ausgabe | allgemeine Zielauswahl oder Transport |

Diese Grenzen sind absichtlich redundant. Eine gültige Nachricht allein reicht
nicht; auch Instanz, Fokus und Gate müssen passen.

Das AppModule und das Braille-Overlay erhalten ausschließlich den
`TerminalIntegrationService`. Das konkrete Global Plugin bleibt hinter diesem
Vertrag verborgen. Terminalbefehle verwenden eine feste Enum statt frei
aufgelöster Methodennamen; Fokusentscheidungen und F12-Autorisierungen sind
unveränderliche Werte. Fehlt der Dienst, wurde er beim Add-on-Neuladen ersetzt
oder verletzt er den Vertrag, übergibt das AppModule die Originalgeste oder das
native NVDA-Ereignis fail-open.

Der `TerminalIntegrationService` delegiert seine Fokusoperationen direkt an
den `TerminalFocusService`. Dieser erhält Identitätsbildung, UIA-Lebensprüfung,
Hauptthread-Scheduler und wenige fachliche Callbacks explizit injiziert. Ein
geschlossenes, nicht fokussiertes Control wird erst nach zwei eindeutigen
Negativprüfungen entfernt; unklare UIA-Fehler gelten nicht als Schließung.

Einstellungsdialog, Präsentation und Profilwechsel verwenden Snapshots oder
fachliche Operationen des `SettingsService`; kein Dialog verändert ein frei
zugängliches Plugin-Dictionary. Der `NvdaUiManager` erhält nur diesen Dienst,
einen Diagnose-Recorder und die wenigen Callbacks für Passwort- und
Komponentenabläufe. Menü und Einstellungskategorie bleiben trotzdem genau
einmal im Prozesslebenszyklus des Global Plugins registriert.

## Das Fail-open-Gate

`SessionGate.suppression_active` ist nur wahr, wenn gleichzeitig:

- die Funktion manuell aktiviert ist;
- die Instanz authentifiziert ist;
- Neovim aktiv ist;
- kein Terminal-Passthrough für direkte Terminaleingabe gilt;
- ein unterstütztes Terminal-Control fokussiert ist;
- und dessen vollständige Identität exakt der gebundenen Identität entspricht.

Fehlt eine Bedingung, verarbeitet NVDA das Terminal wieder auf normalem Weg.
Das Add-on wird deshalb nicht pauschal für ein ganzes Windows-Terminal-Fenster
oder für alle Tabs aktiv.

## Zustand, Reihenfolge und Spalten

Jedes Ereignis gehört zu einer Sitzung und trägt eine monotone Sequenznummer.
Lücken lösen Resync aus; `fullState` stellt einen vollständigen, validierten
Ausgangspunkt wieder her. Zustände verschiedener Verbindungsinstanzen werden
nicht vermischt.

Cursorpositionen unterscheiden:

- Zeile;
- UTF-8-Bytespalte für Neovim-APIs und Protokoll;
- Unicode-Zeichenposition für menschliche Ausgabe;
- virtuelle Spalte für Tabs und Anzeigeausrichtung;
- visuelle Spalte beziehungsweise Auswahlgrenzen, wo der Modus sie benötigt.

Eine Zahl darf nicht ohne ihren Spaltentyp zwischen diesen Ebenen übernommen
werden. Details und Feldgrenzen stehen in `protocol.md`.

## Rückrichtung: kleiner erlaubter Steuerkanal

Der Rückkanal ist eine feste Allowlist und keine allgemeine Remote-Steuerung:

- `requestFullState` und `requestFocusContext` fordern Zustand an;
- `routeCursor` setzt einen validierten Cursor aus einer Braille-Routingaktion;
- `copyTextRequest`, `pasteTextRequest` und `setRegisterRequest` vermitteln
  explizite Zwischenablageaktionen;
- `leaveTerminalInputRequest` führt ausschließlich das feste Neovim-
  `stopinsert` aus.

Zustandsändernde Anfragen tragen die erwartete Sitzungs-, Buffer-, Fenster-,
Tab-, Modus- und, wo nötig, `changedtick`-Identität. Text wird nie als Lua- oder
Ex-Code ausgeführt. Die vollständigen Payloads und Sonderregeln stehen in
`protocol.md`, die Sicherheitsannahmen in `security.md`.

## Ereignisse, Polling und Fallbacks

Der normale Editor-, Fokus-, Transport- und Dateimanagerpfad ist
ereignisgetrieben. Polling ist nur als begrenzte Notlösung zulässig, wenn keine
zuverlässige Ereignisstruktur existiert. Der aktuelle Code besitzt zwei solche
Ausnahmen:

1. Nach einer ausdrücklichen lokalen F12-Markierung liest ein Worker die
   Sitzungsdateien alle 50 ms für höchstens 1,5 Sekunden, weil der atomare
   Dateiwechsel kein zuverlässiges Ereignis in NVDA auslöst. Die Schleife ist
   benutzergesteuert, zeitlich begrenzt und öffnet keine RPC-Verbindungen.
2. Die Adapter für `nvim-cmp` und `blink.cmp` fragen im Abstand von 35 ms deren
   öffentliche Auswahl-API ab, aber nur solange das jeweilige Plugin sein Menü
   als geöffnet gemeldet hat. Die Plugins bieten derzeit kein verlässliches
   Ereignis für jede Auswahländerung. Schließen des Menüs beendet den Timer.

Der fünfminütige Terminal-Lifecycle-Sweep ist davon zu unterscheiden. Er ist
eine langsame Wartungsprüfung für geschlossene Windows-Terminal-Controls, nicht
die Quelle für Editorzustand oder Fokusaktionen. Zwei negative
Lebensnachweise sind erforderlich, bevor eine Bindung entfernt wird; Fehler
öffnen das Gate.

Dateimanager verwenden Pluginereignisse. Nur Oils Bestätigungs-Float benötigt
den in `adr/0003-oil-confirmation-fallback.md` beschriebenen, eng begrenzten
Parser. Er wird durch Buffer-/Fensterereignisse ausgelöst und pollt weder
Bildschirm noch Dateisystem.

## Spezialisierte Teilsysteme

### Kommandozeile, Terminal und Meldungen

Neovim liefert den Kommandozeilentyp und -inhalt strukturiert. Eine
`CmdlineLeave`-Korrelation verbindet nur die unmittelbar belegte Meldung eines
Ex-Befehls mit dem bereits erreichten Rückkehrmodus. Zeitabstände werden nicht
als Semantik interpretiert. Terminal-Insert, `terminalNormal` und normaler
Dateibuffer-Modus bleiben unterschiedliche Zustände; Passthrough öffnet das
Gate während direkter Terminaleingabe.

### Zwischenablage

Die Windows-Zwischenablage bleibt Eigentum von NVDA. Frei belegbare NVDA-
Befehle übertragen nur auf ausdrückliche Aktion eine Visual-Auswahl oder
Register 0 nach Windows, Windows-Text über `nvim_paste` nach Neovim oder in das
feste Register 0. Anfrage-ID und erwarteter Editor-/Fokuszustand verhindern,
dass eine verspätete Antwort auf eine andere Sitzung angewendet wird. Es gibt
keine automatische Synchronisation oder Wiederholung.

### Dateimanager

`file_manager.lua` normalisiert den aktiven Eintrag; getrennte Adapter
abonnieren öffentliche Ereignisse von Oil, netrw, mini.files, nvim-tree und
Neo-tree, soweit verfügbar. Sie übertragen typisierte Namen, Arten, Zustände
und Aktionsresultate statt dekorierter Bildschirmzeilen. Fehlende Plugin-APIs
fallen auf vorhandene Navigation zurück. Die Funktionsmatrix und der praktische
Teststand stehen in `accessibility.md` und `current-status.md`.

### Lokalisierung und Paketierung

Nur die NVDA-Seite lokalisiert Benutzertexte. Bridge, Protokoll und Plugin
übertragen typisierte Werte und Dokumentinhalt ohne Kenntnis der aktiven
Sprache. Der Build kompiliert PO-Dateien in NVDAs gettext-Domain und bettet
außerdem Bridge, Protokoll, Plugin und Installer als rootloses Linux-
Benutzerpaket in das Add-on ein. Die Remoteinstallation verwendet dieses
eingebettete Paket und lädt zur Laufzeit nichts nach.

## Regeln für Erweiterungen

Neue Funktionen sollten in dieser Reihenfolge entworfen werden:

1. zuverlässige öffentliche Neovim- oder Plugin-Ereignisse suchen;
2. einen kleinen typisierten Zustand im Plugin erzeugen;
3. Grenzen und Korrelation im Protokoll definieren und testen;
4. Transport unverändert weiterleiten lassen;
5. Ausgabe im NVDA-unabhängigen Planer modellieren;
6. Fokus- und Fail-open-Bedingungen im Add-on prüfen;
7. nur bei belegter Ereignislücke einen engen Fallback oder begrenztes Polling
   mit dokumentierter Ablösung ergänzen.

Private APIs benötigen vor einer Veröffentlichung ein ADR. Rohtextheuristiken,
allgemeine RPC-Durchleitung und automatische Zuordnung aus Fenstertiteln sind
keine zulässigen Abkürzungen.

## Weiterführende Kapitel

- `protocol.md`: Nachrichten, Felder, Grenzen, Sequenzen und Steuerbefehle
- `security.md`: Vertrauensgrenzen und Bedrohungsmodell
- `latency.md`: Threading, Budgets und Messung
- `accessibility.md`: Funktionsmatrix und Fallbacks
- `testing.md`: automatisierte und praktische Nachweise
- `adr/`: begründete Architekturentscheidungen
