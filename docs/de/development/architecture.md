# Architektur

Dieses Kapitel vertieft den [Überblick für neue Entwickler](overview.md). Es
setzt dessen Grundmodell voraus und folgt derselben Reihenfolge: beteiligte
Prozesse und Datenwege, Begriffe und Verbindungslebenszyklus, Zuständigkeiten
im Add-on sowie spezialisierte Teilsysteme. Wer das Projekt zum ersten Mal
liest, sollte deshalb mit dem Überblick beginnen und dieses Kapitel danach vor
dem Protokoll und den einzelnen ADRs lesen.

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

Empfangsthreads rufen NVDA nicht direkt auf. Sie stellen geprüfte Ereignisse
mit `queueHandler` in NVDAs Ereigniswarteschlange. Nur dort werden
Editorzustand und Ausgabeplan aktualisiert sowie Sprache, Klänge, Braille und
UI angesteuert.

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
| Neovim-Plugin | Editorsemantik, Buffer-/Fenster-/Tabidentität, UTF-8-Bytespalten, Menüs, Meldungen, Dateimanagerzustand und flüchtige rein lesende Explorationsposition | Windows-Fokus, Sprache, SSH-Lebenszyklus oder Bewegung des echten Cursors für Exploration |
| Bridge | Unix-RPC-Verbindung, stdio-Framing, begrenzte Weiterleitung | freie RPC- oder Befehlsausführung, Präsentation |
| Protokollclient | Größen-, Typ-, Sitzungs-, Sequenz-, Heartbeat- und Resyncprüfung | Entscheidung über Sprache oder Terminalfokus |
| `ConnectionInstanceManager` | Instanzen und Bindung von `TerminalIdentity` zu Instanz | Erraten einer Bindung aus Titel oder Terminaltext |
| `ConnectionCoordinator` | Instanzmanager, aktiver Client, Gate, Authentifizierung, Zuordnungen, korrelierte Anfragen sowie Zuordnung und Lebensdauer getrennter Laufzeitzustände | fachliche Mutation des Editorzustands, NVDA-Ereignisse, `nextHandler`, Dialoge oder konkrete NVDA-Ausgabe |
| `service_registry.py` / `ServiceRegistrar` | identitätsgeprüfte prozessweite Veröffentlichung des vollständig initialisierten `TerminalIntegrationService` | Global-Plugin-Objekt, Lebenszyklusentscheidung oder Terminalereignisse |
| `AddonRuntime` | späte Dienstveröffentlichung und feste, wiederholbare Abbaureihenfolge der zusammengesetzten prozessweiten Dienste | Anwendungsevents, Editorplanung, Fokusentscheidungen, Dialoge oder freie Dienstsuche |
| `TerminalIntegrationService` | schmaler öffentlicher Vertrag für Fokus, feste Terminalbefehle, F12-Claims, Sprachexplorationsmodus und strukturierte Brailleinteraktion | Global-Plugin-Objekt, Anwendungsevents, `nextHandler`, dynamische Methodennamen oder Zugriff auf private Laufzeitzustände |
| `TerminalFocusService` | konkrete Terminalidentität, Fokusgeneration, AppModule-/Adapterkorrelation, Fokusabschluss und konservative Bereinigung geschlossener Controls | Global-Plugin-Instanz, Netzwerk-I/O, Anwendungsevents oder `nextHandler` |
| `SessionClaimService` | einmalige F12-Autorisierung, Claim-Generationen und Claim-Inventarzustand | Global-Plugin-Instanz, NVDA-Dialoge, synchrone Discovery oder Kopien des Verbindungslaufzeitstands |
| `EditorSessionController` | fachliche Mutation und Zurücksetzung des aktiven instanzgetrennten Editorzustands, Runtimewechsel, Modus-/Menü-/Transport-/Passthroughzustand, Zugriff auf Completion-Dokumentation, Normalisierung des Verbindungsnamens, neutrale Tippechoaktionen sowie validierte ausgehende Zwischenablage-, Terminal- und Explorationspläne mit Antwortkorrelation | konkrete NVDA-Ausgabe, Fokusbindung oder Authentifizierung, Windows-Zwischenablage, Netzwerk-I/O oder Instanzlebensdauer |
| `ControlDispatcher` | begrenztes asynchrones Senden vorbereiteter Steuerpayloads | NVDA-Ereignisse, Fokusentscheidung, Payload-Erzeugung oder unbegrenzte Warteschlange |
| `SettingsService` | Laden, Normalisieren, Speichern und Profilwechsel der Add-on-Einstellungen sowie unveränderliche Änderungsberichte | Dialogzustand, Terminalereignisse, Fokus oder Verbindungen |
| `SessionGate` | Entscheidung, ob native Terminalausgabe unterdrückt werden darf | Editorsemantik und Transport |
| Speech-/Brailleplanung | lokalisierte, priorisierte Präsentation | Netzwerk, Neovim-RPC und Fokusbindung |
| `NvdaPresentation` | NVDA-spezifische Ausgabe geplanter Sprache, Braillemeldungen, Töne und Add-on-Klänge | Sprachplanung, Transport, Fokusbindung oder Dialoge |
| `nvda_braille.py` | NVDA-Brailleregion, Terminaloverlay, Übersetzung von Braillepositionen und Abruf des veröffentlichten Terminaldienstes | Global-Plugin-Objekt, Verbindungsbesitz oder Fokusentscheidung |
| Global Plugin | NVDA-Prozesslebenszyklus, Zusammensetzung gemeinsamer Dienste, prozessweite Registrierung und Aufruf von `AddonRuntime.close()` | Anwendungsevents, frei belegbare Terminalbefehle, `nextHandler`, Overlayauswahl, Implementierung von Einstellungen, Werkzeugen, Präsentationsausgabe oder Abbaureihenfolge |
| `NvdaUiManager` | einmalige und symmetrische Registrierung von Einstellungen und Werkzeugen, Verbindungsformulare, Komponenteninstallation und -entfernung | Global-Plugin-Instanz, Terminalereignisse, Fokusbindung und Unterdrückung |
| Windows-Terminal-AppModule | UIA-Ereignisse, Overlayauswahl, konkreter Terminalfokus, frei belegbare Terminalbefehle, kontextbezogene Gesten des Sprachexplorationsmodus und deren physischer Tastenlebenszyklus, jeder Aufruf von `nextHandler` sowie Übergabe oder Unterdrückung nativer Ausgabe | allgemeine Zielauswahl, eigene Gestenauflösung oder Transport |

Diese Grenzen sind absichtlich redundant. Eine gültige Nachricht allein reicht
nicht; auch Instanz, Fokus und Gate müssen passen.

`AddonRuntime.start()` registriert zuerst den Profilcallback, danach
Einstellungen und Werkzeuge und veröffentlicht erst zuletzt den
Terminaldienst. Schlägt einer dieser Schritte fehl, verwendet die Runtime
unmittelbar ihren vollständigen, wiederholbaren Teardown. Dieser entfernt den
Dienst, schließt den veröffentlichten Dienst, bricht verzögerte
Hauptthreadaufrufe ab, öffnet das Gate, meldet den Profilcallback ab, stoppt
Verbindungen genau einmal über den Coordinator-Eigentümer, löscht dessen
Runtime-/Fokus-/Requestzustand genau einmal und schließt zuletzt UI und
Präsentation. Claim- und Terminalfokusgenerationen werden vor dem Clientstopp
ungültig. Jeder Schritt fällt getrennt aus, damit ein Bereinigungsfehler keine
späteren Ressourcen aktiv lässt.
Der Callback zum Leeren der nur im Global Plugin gehaltenen Sitzungspasswörter
bleibt als schmale, eigentumsbezogene Abbaugrenze bestehen.

Der geschlossene `TerminalIntegrationService` ist eine Fail-open-Schranke für
zurückgehaltene Referenzen: Er unterdrückt keine nativen Ereignisse oder
Brailleausgabe, autorisiert keine Geste und erzeugt keine Diagnosewirkung.
Claim-, Managed-Connection-, Netzwerk-, Braille- und verzögerte
Hauptthreadcallbacks laufen zusätzlich durch eine Runtimeprüfung, die auch
zwischen Einreihen und Ausführung erfolgtes Unpublish berücksichtigt.

Das Global Plugin bietet keine Kompatibilitätseigenschaften für Editorplaner,
kanonischen Zustand, Modus, strukturierten Tippechozustand,
Completion-Dokumentation oder Transport-Capabilities mehr an. Tests und
interne Aufrufer verwenden die ausdrückliche Besitzgrenze von
`EditorSessionController` und `ConnectionCoordinator`. Dadurch bleibt keine
zweite schreibbare Editorzustandsschnittstelle erhalten.

Es bietet auch keine Kompatibilitätseigenschaften für ausstehende Claims,
Inventarzustand, Baselines, zulässige Ziele, Inventarfehler oder
Discovery-Generation mehr an. Tests verwenden `SessionClaimService` direkt;
damit besitzt Claimzustand einen schreibbaren Eigentümer und eine ausdrückliche
Prüfgrenze.

Passive Kompatibilitätssichten für Präsentations-Sound-Caches, gemerkte
Bindungen und Angebote, Runtime- und Requestcontainer sowie
AppModule-/Adapterfokusdaten sind ebenfalls entfernt. Ihre Tests prüfen
`NvdaPresentation`, `ConnectionCoordinator` oder `TerminalFocusService`
direkt. Aktive NVDA-Wirkungen oder Terminalereignisbesitz werden dadurch nicht
in diese Tests verschoben.

Auch fokussiertes Terminalobjekt und Zeitwert des Lifecycle-Sweeps besitzen
keine Global-Plugin-Kompatibilitätssicht mehr. Brailleaktualisierung und
Lifecycletests verwenden den besitzenden `TerminalFocusService`;
Fokusentscheidungen und UIA-Lebensbehandlung bleiben dort gekapselt.

Auch aktiver Client- und Instanzzustand, Verbindungsstatus, Verfolgung
authentifizierter Instanzen, instanzbezogener Terminal-Passthrough und
zurückgestellte Full-States besitzen keine
Global-Plugin-Kompatibilitätseigenschaften mehr. Das Global Plugin verbindet
Wirkungen am NVDA-Rand direkt über `ConnectionCoordinator`; dieser Coordinator
bleibt alleiniger schreibbarer Eigentümer dieser Felder.

Das AppModule und das Braille-Overlay erhalten ausschließlich den
`TerminalIntegrationService`. Das konkrete Global Plugin bleibt hinter diesem
Vertrag verborgen. Terminalbefehle verwenden eine feste Enum statt frei
aufgelöster Methodennamen; Fokusentscheidungen und F12-Autorisierungen sind
unveränderliche Werte. Fehlt der Dienst, wurde er beim Add-on-Neuladen ersetzt
oder verletzt er den Vertrag, übergibt das AppModule die Originalgeste oder das
native NVDA-Ereignis fail-open.

Die prozessweite Dienstinstanz liegt in der neutralen `service_registry.py`.
Das Global Plugin veröffentlicht und entfernt den Dienst über denselben
identitätsgeprüften `ServiceRegistrar`, den AppModule und Braillemodul nur
lesen. `nvda_braille.py` besitzt Region und Overlay und importiert kein Global
Plugin; `__init__.py` exportiert ihre Klassennamen lediglich für das
Windows-Terminal-AppModule weiter.

Der Dienst besitzt keine breite `_runtime`-Referenz. Die Kompositionswurzel
übergibt genau einen Handler für jeden `TerminalCommand` sowie getrennte
Callbacks für Diagnose, Fail-open, F12-Abschluss und Braillepräsentation. Der
Konstruktor kopiert die Befehlszuordnung und lehnt fehlende, zusätzliche oder
nicht aufrufbare Einträge ab. Damit kann der öffentliche Dienst keine anderen
Methoden oder Zustände des Global Plugins erreichen.

Der `TerminalIntegrationService` delegiert seine Fokusoperationen direkt an
den `TerminalFocusService`. Dieser erhält Identitätsbildung, UIA-Lebensprüfung,
Hauptthread-Scheduler und wenige fachliche Callbacks explizit injiziert. Ein
geschlossenes, nicht fokussiertes Control wird erst nach zwei eindeutigen
Negativprüfungen entfernt; unklare UIA-Fehler gelten nicht als Schließung.

Der `TerminalIntegrationService` autorisiert und verwirft physische F12-Claims
außerdem direkt über `SessionClaimService`. Dieser Dienst besitzt den
veränderlichen Claim- und Inventarzustand, lokale/SSH-Inventarworker und die
Kandidatenauswertung. Er besitzt außerdem Discovery, Auswahl,
Wiederverwendung, Verbindungsstart, Trennung und gemerkte Bindungen. Das Global
Plugin verbindet seine unveränderlichen Ergebnisse nur mit NVDAs
Hauptthread-, Dialog-, Meldungs- und Transportgrenzen. Es hält keine
schreibbare Kopie des Claimzustands. Der Fokusverlust der optionalen modalen
Merkabfrage wird durch genau eine an Terminal und Instanz korrelierte
Reaktivierung überbrückt; ein abweichender Terminalfokus verwirft sie.

Der in V2-5 eingeführte `EditorSessionController` verwendet die vom
`ConnectionCoordinator` verwaltete aktive Runtime, ist aber allein für deren
fachliche Mutation zuständig. Er übernimmt Zustands- und Modusübergänge,
Transportfähigkeiten, Menü-Dokumentation, Verbindungszustand,
instanzgetrennten Terminal-Passthrough und Tippecho. Bei einem bereits
validierten Fokus-/Kontextereignis ergänzt er den gespeicherten
Verbindungsnamen vor Zustands- und Sprachplanung in einer Kopie; er entscheidet
nicht, ob das Ereignis zum fokussierten Terminal gehört. Seine geordneten
neutralen Tippechoaktionen werden erst am NVDA-Rand als Sprache ausgegeben. Für
jedes validierte Ereignis bündelt
ein unveränderlicher Plan den Zustandsübergang, den fachlichen
Terminal-Passthrough, höchstens einen Modusklang und die geordneten neutralen
Sprachaktionen. Das Global Plugin wendet den Passthrough am Gate an und reicht
Klang- und Sprachplan an `NvdaPresentation` weiter. Der Controller vergibt außerdem die
begrenzten Anfrage-IDs für Zwischenablage, Register und Terminalsteuerung,
bindet sie an Instanz und `TerminalIdentity` und verwirft fremde oder
verspätete Antworten. Einmaliger Zwischenablagetext wird nur als geprüftes
Ergebnis an den NVDA-Rand gegeben und aus dem sicheren Folgeereignis entfernt.
Vor dem Senden prüft derselbe Controller ausgehandelte Capability und
kanonischen Buffer-/Moduszustand. Er liefert entweder einen unveränderlichen
ausgehenden Allowlist-Plan oder genau einen begrenzten Ablehnungsgrund und
erzeugt nur für eine gültige Aktion einen ausstehenden Request. Exakte
Fokus-/Gate-Prüfung, Transportaufruf, Windows-Zwischenablage, Diagnostik und
konkrete Präsentation bleiben getrennt. Auch das Zurücksetzen des semantischen
Planers und der Zugriff auf die Completion-Dokumentation der aktiven Instanz
verwenden diese Controllergrenze. NVDAs eigener Wortpuffer und die
Sprachausgabe bleiben am NVDA-Rand.

Die Runtime jeder verwalteten Neovim-Instanz enthält außerdem ihren eigenen
Braille-Explorationscontroller, ihren eigenen Controller für nummerierte
native Auswahllisten und einen `HeldContextController` für lesende Funktions-
und Diagnoseabfragen. Damit kann ein Tab oder Pane den gewählten Braillemodus,
Vorschlagszustand oder gehaltenen Entwicklerkontext einer anderen lokalen oder
entfernten Sitzung weder anzeigen noch verändern. Ein Runtimewechsel aktiviert nur den Zustand der
zugeordneten Sitzung. Virtuelle Zeile, Lesespalte und NVDAs öffentlicher
`windowStartPos` bleiben in dieser Runtime erhalten. Mehrfach-Routingfolgen und
Fokusmeldungen werden beim Controlwechsel verworfen. Ein Disconnect setzt
ausschließlich die betroffene Runtime zurück.

Für Braille kopiert der Controller den aktiven kanonischen Zustand in einen
`BrailleSessionPlan`; spätere Editorereignisse verändern diesen Plan nicht.
Ein `BrailleRoutePlan` enthält entweder einen vollständig validierten festen
`routeCursor`-Payload samt Zielart, exaktem Rohmodus und UTF-8-sicherem
Quellzeichen oder einen begrenzten Ablehnungsgrund. Im Befehlszeilenmodus
liefert der Brailleplan das strukturierte Präfix und den Inhalt; nur
Inhaltszellen und eine virtuelle Endzelle besitzen eine Zuordnung zur
Befehlszeilen-Bytespalte. Im Insert-Modus ergänzt der Plan ebenfalls genau eine
virtuelle Leerzelle hinter dem unveränderten Zeilentext. Sie gibt NVDAs
Cursorpunkten 7+8 eine vorhandene Zelle und bildet beim Routing auf die
UTF-8-Bytespalte direkt hinter dem letzten Zeichen ab; der Neovim-Puffer wird
dabei nicht erweitert. Eine leere Normalmoduszeile erhält ebenfalls eine
einzige virtuelle Zelle bei Bytespalte 0, weil NVDAs Braillepuffer eine
cursortragende Region ohne Zellen nicht fokussieren kann. Nicht leere
Normalmoduszeilen erhalten keine zusätzliche Endzelle. Die strukturierte
Region setzt `focusToHardLeft` und `hidePreviousRegions`, sodass sie NVDAs
vorangestellte Windows-Terminal-Fokuskontexte vollständig ersetzt. Das
öffentliche Terminalservice prüft zuvor das konkrete
Terminal und protokolliert das Ergebnis. Das Overlay rechnet nur NVDAs
übersetzte Brailleposition in die semantische Bytespalte um. Der Dienst legt
den unveränderlichen festen Payload in denselben begrenzten
`ControlDispatcher`, den Exploration und nummerierte Auswahl verwenden.
Dessen Worker ruft den lokalen oder SSH-Transport auf; eine volle Queue oder
ein geschlossener Dispatcher verwirft die optionale Aktion fail-open. Damit
führen weder Routingtaste noch NVDA-Regionscallback Socket-, SSH- oder
`stdin.flush()`-I/O auf NVDAs Hauptthread aus. Erst nach erfolgreichem
Einreihen liefert `NvdaPresentation` das Zeichen abhängig von NVDAs
öffentlicher Einstellung `braille.speakOnRouting` über
`speech.speakSpelling` aus. Die private NVDA-Hilfe `_speakOnRouting` wird nicht
verwendet.

Optionale Mehrfachbetätigungen bleiben innerhalb derselben Schichten. Der
reine `BrailleRoutingRepeatController` erkennt nur identische Zielsignaturen
und verwendet NVDAs öffentliche `keyboard.multiPressTimeout`-Einstellung. Der
erste Druck erzeugt weiterhin sofort `routeCursor`; nur die doppelte
Wortaktion wird verzögert, wenn eine dritte Betätigung noch eine Zeilenaktion
ersetzen kann. `core.callLater` plant ausschließlich diesen lokalen
Hauptthread-Callback, führt aber kein Transport-I/O aus. Ein
`BrailleRoutingActionPlan` erlaubt nur Normal- und Insert-Modus sowie vier
feste Aktionen. Der unveränderliche `brailleRouteAction`-Payload durchläuft
denselben begrenzten Dispatcher. Das Neovim-Plugin prüft Buffer, Fenster,
Zeile, Bytespalte, `changedtick`, Rohmodus, Änderbarkeit und UTF-8-Grenze
erneut und bildet die Aktionskennung erst dort auf `cw`, `dw`, `c$` oder `d$`
mit einem festen Zeilenstart ab. Es wird kein Lua-, Ex- oder Normalbefehlstext
übertragen.

Vertikale Braillezeilennavigation folgt derselben Grenze. NVDAs öffentliche
Regionsmethoden planen nur eine Richtung. Ein unveränderlicher
`BrailleLineNavigationPlan` bindet sie an Capability, aktiven Client,
Buffer, Fenster, `changedtick`, Rohmodus, Ausgangszeile und Neovims
bevorzugte virtuelle Spalte. Der Dispatcher sendet daraus den festen
`moveBrailleLine`-Auftrag. Die feste Zielregel `preferred`, `start` oder `end`
unterscheidet direktes Auf/Ab von horizontalem Weiterschalten über eine
Zeilengrenze. Erst das Neovim-Plugin berechnet mit den
öffentlichen Funktionen `winsaveview()`, `virtcol2col()` und
`winrestview()` die gültige Bytespalte der benachbarten Zeile. `curswant`
bleibt dabei erhalten, sodass eine kurze Zwischenzeile die gewünschte
horizontale Position bei `preferred` nicht verliert. `start` setzt Spalte und
Wunschspalte auf null; `end` wählt im Normalmodus das letzte Zeichen und im
Insert-Modus die Einfügeposition dahinter. Die Befehlszeile und direkte
Terminaleingabe sind ausgeschlossen. Horizontales Braille-Scrolling innerhalb
einer Zeile bleibt unverändert in NVDA; nur das Überschreiten einer
Zeilengrenze erzeugt einen semantischen Transportauftrag.

Der Regionsaufruf übergibt absichtlich nur Richtung und eine der drei festen
Zielregeln. NVDAs `start`-Parameter trennt Aufwärtsnavigation vom
Rückwärtsschalten; für den parameterlosen Abwärtsaufruf liefert das
Windows-Terminal-AppModule eine exakt gebundene, nach einem Eingabezyklus
auslaufende Markierung des öffentlichen globalen Braillebefehls. Hinter
der Service-/Controllergrenze wählt der eigenständige
`BrailleExplorationController` zwischen zwei Strategien. Im Cursormodus
entsteht der beschriebene `moveBrailleLine`-Auftrag. Im
Braille-Explorationsmodus entsteht stattdessen ein korrelierter
`brailleExploreLineRequest`. Dessen `desiredVirtualColumn`, `targetColumn` und
vollständige kanonische Ursprungsidentität werden im Neovim-Plugin auf eine
flüchtige Zeilenposition abgebildet; Buffer und echter Cursor bleiben
unverändert. Die erste Anfrage muss dem echten Cursor und Modus exakt
entsprechen. Danach bleibt die virtuelle Position bei echten Cursor-, Modus-
und Textänderungen bestehen. Erhöht sich `changedtick`, übernimmt der
Controller den neuen Zeilentext und die davon abgeleiteten Darstellungsfelder
nur dann in die abgeleitete Ansicht, wenn die echte Cursorzeile gerade der
explorierten Zeile entspricht. Virtuelle Zeile, Lesespalte und
Brailleausschnitt bleiben dabei unverändert. Änderungen auf anderen Zeilen
aktualisieren nur die Korrelation, nicht die angezeigte Exploration.
Jede Folgeanfrage muss weiterhin die
ursprüngliche Identität, Explorations-ID und nächste Aktionsnummer tragen;
Buffer, Fenster und Tab müssen unverändert sein. `changedtick` darf
ausschließlich auf den aktuell validierten Wert desselben Buffers
fortgeschrieben werden.
Das Ergebnis verändert nur eine abgeleitete Brailleansicht im
`EditorSessionController`, niemals den kanonischen Verbindungszustand.
Routing plant anschließend aus dieser Ansicht und setzt den echten Cursor
absichtlich auf die explorierte Zeile, ohne dadurch den weiterhin gewählten
Braille-Explorationsmodus umzuschalten. Zielzeile und Bytespalte stammen aus
dieser abgeleiteten Ansicht; Buffer-/Fensteridentität, Modus,
Transportfähigkeiten und `changedtick` stammen dagegen aus dem aktuellen
kanonischen Zustand. Routing ist nur verfügbar, wenn der abgeleitete
Zeileninhalt zu demselben `changedtick` gehört. Dadurch bleibt ein manuell
verschobener NVDA-Ausschnitt stabil, ohne dass eine Änderung oder ein
Moduswechsel einen alten Anzeigestand in einen scheinbar erfolgreichen
Routingauftrag verwandelt.

Die abgeleitete Ansicht besitzt keinen eigenen sichtbaren Braillecursor.
`EditorSessionController` übernimmt den echten Cursor nur dann in den
Brailleplan, wenn echte und explorierte Zeile sowie deren Text übereinstimmen.
Die gezielte Inhaltsaktualisierung stellt diese Übereinstimmung nach einer
Bearbeitung auf der angezeigten Zeile wieder her, ohne einen virtuellen
Zweitcursor einzuführen. Dabei wird der vollständige von der Zeile abgeleitete
Zustand ersetzt, nicht nur ihr Text; virtuelle Zeile, bevorzugte Lesespalte
und NVDA-Ausschnitt bleiben erhalten. Die Rückkehr vom Einfüge- in den
Normalmodus aktualisiert deshalb die Routingautorisierung, ohne die
Brailleansicht neu zu verankern.
Der `BrailleSessionPlan` kennzeichnet diese abgeleitete Ansicht zusätzlich
mit `preserve_viewport`. `StructuredLineRegion.update()` löscht in diesem
Fall NVDAs öffentliche `TextInfoRegion.pendingCaretUpdate`-Markierung, nachdem
die neue Region berechnet wurde. Dadurch kann ein im selben NVDA-Zyklus
eingetroffenes natives Terminal-Caretereignis nicht nach der von
`handleUpdate()` vorgesehenen Wiederherstellung des Braillefensters erneut
zum echten Cursor scrollen. Die Region wird dennoch vollständig über NVDAs
öffentliche Aktualisierung verarbeitet; Änderungen innerhalb des bestehenden
Ausschnitts erscheinen daher, ohne dass Änderungen oder der Cursor außerhalb
dieses Ausschnitts dessen Position übernehmen.

Braille-Explorationsmodus und Sprachexplorationsmodus besitzen getrennte Controller,
Request-ID-Kanäle, Explorations-IDs, Lua-Zustände und Abschlussaufträge.
Interleaving kann deshalb keine Aktionsfolge des anderen Modus verbrauchen.
Eine profilfähige Option darf den bereits validierten virtuellen Zustand des
Controllers des Sprachexplorationsmodus zusätzlich als abgeleitete Brailleansicht
projizieren. Sie vereinigt die beiden Zustandsautomaten nicht: Der kanonische
Editorzustand bleibt unverändert, der eigenständige
Braille-Explorationscontroller besitzt Vorrang, und Abschluss oder Abbruch
stellt die kanonische Brailleansicht wieder her.
Der frei belegbare Toggle bleibt als kontextbezogenes Skript im
Windows-Terminal-AppModule. Der `TerminalIntegrationService` besitzt
Controllerumschaltung und gegebenenfalls asynchron eingereihte
Remote-Bereinigung; die Prozessaktion im Global Plugin liefert nur die
NVDA-Meldung und stößt die Brailleaktualisierung an. Instanzwechsel verwerfen
die flüchtige virtuelle Position und laufende Anfragen, aktivieren bei einer
Rückkehr aber wieder den unabhängig für diese Sitzung gewählten
Braillemodus. Disconnect und Teardown setzen nur die betroffene
beziehungsweise alle besessenen Runtimes symmetrisch zurück.
Befehlszeilen- und direkter Terminalmodus sind ausgeschlossen.

`StructuredLineRegion` ist keine parallele Brailleimplementierung. Sie
unterklasst NVDAs öffentliche Erweiterungsstelle `braille.TextInfoRegion`,
damit `braille.handler.handleCaretMove` den üblichen Cursor-Nachlauf und
`scrollToCursorOrSelection` auslösen kann. Weil ihr Text semantisch aus Neovim
kommt, ruft ihre Aktualisierung gezielt die öffentliche Basismethode
`braille.Region.update()` auf. Sie setzt nur deren dokumentierte Rohtext-,
Cursor-, Auswahl- und Regionsfelder und
überlässt Übersetzung, Unicode-Normalisierung, Cursorform, Auswahlpunkte,
Scrollfenster und Displaytreiber vollständig NVDA. Die öffentliche
`brailleToRawPos`-Abbildung führt eine physische Routingzelle zurück in den
neutralen Plan. Für Review-Tether wirft das Overlay wie von
`braille.getFocusRegions` vorgesehen `NotImplementedError`, damit NVDA seinen
nativen Pfad verwendet.

Da NVDAs nativer `gainFocus` vor der asynchronen
`focusContext`-Bestätigung läuft, ersetzt deren erfolgreicher Abschluss die
native Terminalregion ausdrücklich über `handleGainFocus(...,
shouldAutoTether=False)`; ein bloßes `handleUpdate` würde die falsche
Regionsklasse behalten und damit physische Routinggesten verlieren.
Bei `chooseNVDAObjectOverlayClasses` besitzt das provisorische UIA-Objekt noch
nicht zwingend die Rolle seiner später zusammengesetzten Klasse. Das
Windows-Terminal-AppModule prüft deshalb die von NVDA bereits ermittelte
Overlay-Klassenliste auf eine Klasse mit der öffentlichen Terminalrolle und
fügt dann das strukturierte Mixin ein. Diese Komposition darf nicht von der
Veröffentlichung des prozessweiten Terminaldienstes abhängen: NVDA kann das
Fokusobjekt bereits vorher erzeugen, und seine dynamische Klasse wird bei einer
späteren `fullState` nicht nachträglich zusammengesetzt. Das Mixin bleibt ohne
Dienst oder bestätigte Neovim-Bindung inert und delegiert fail-open an NVDAs
native Terminalimplementierung. Erst Regionsanforderung und Routing prüfen
erneut exakte Terminalidentität, Fokus, Instanz, Capability und Zustand.
Der Diagnosepfad liest dafür nur die öffentlichen Eigenschaften
`braille.handler.enabled`, `braille.handler.getTether()` und
`config.conf["braille"]["mode"]`. Overlayauswahl, Regionsanforderung und der
Eintritt in `StructuredLineRegion.routeTo` werden an den add-oneigenen Grenzen
protokolliert; für die dauerhafte Region und das Routing werden NVDAs private
Buffer- oder Gestenzustände nicht gelesen. Nur der getrennte, kurzlebige
Rechtschreibvorschlag prüft und beendet den von seinem eigenen öffentlichen
`braille.handler.message()`-Aufruf erzeugten privaten Nachrichtenpuffer
identitätsgesichert. Diese Ausnahme und alle berührten Felder sind in
[ADR-0002](adr/0002-nvda-api-boundaries.md) begründet.

Einstellungsdialog, Präsentation und Profilwechsel verwenden Snapshots oder
fachliche Operationen des `SettingsService`; kein Dialog verändert ein frei
zugängliches Plugin-Dictionary. Der `NvdaUiManager` erhält nur diesen Dienst,
einen Diagnose-Recorder und die wenigen Callbacks für Passwort- und
Komponentenabläufe. Menü und Einstellungskategorie bleiben trotzdem genau
einmal im Prozesslebenszyklus des Global Plugins registriert.
Der Dienst löst die Indizes für Navigationsdetails in boolesche Werte auf,
bevor sie die Editor- oder Explorationsschnittstelle überschreiten. Der
gemeinsame Sprachplaner bleibt dadurch von NVDAs Konfiguration unabhängig und
erzeugt für normale Navigation und Explorationsabschluss dieselbe Reihenfolge
Zeile, Wort, Zeichen. Die Werte für den Explorationsabschluss beeinflussen nur
die Ausgabe am echten Cursor beim Loslassen der NVDA-Taste; die virtuellen
Explorationsschritte und die Zeichenexploration bleiben davon unabhängig.

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
- `brailleRouteAction` führt ausschließlich eine von vier festen Wort- oder
  Zeilenaktionen an einer zuvor exakt gebundenen Routingposition aus;
- `moveBrailleLine` setzt den Editorcursor validiert in die unmittelbar
  vorherige oder nächste Zeile und bewahrt die bevorzugte virtuelle Spalte;
- `copyTextRequest`, `pasteTextRequest` und `setRegisterRequest` vermitteln
  explizite Zwischenablageaktionen;
- `leaveTerminalInputRequest` führt ausschließlich das feste Neovim-
  `stopinsert` aus.
- `exploreTextRequest` bewegt nur eine flüchtige Leseposition, und
  `endExplorationRequest` verwirft sie; beide verändern den echten Cursor nie.
- `acceptNumberedChoiceRequest` bestätigt ausschließlich den bereits
  validierten Index einer aktiven nativen Auswahlliste.

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

### Nummerierte native Auswahllisten

Ein pro Instanz-Runtime gehaltener neutraler `NumberedChoiceController` hält
ausschließlich flüchtige Auswahlzustände. Der erste strikte Adapter gilt für
Neovims eingebaute
`z=`-Rechtschreibliste: Das Lua-Plugin belegt den unmittelbar eingegebenen
Befehl und parst nur eine zusammenhängend nummerierte, begrenzte Liste aus
Neovims UI-Ereignis. Die Listeneinträge gelangen weder in den kanonischen
Editorzustand noch in Diagnosen.

Neovim 0.12 erlaubt die vollständige Kontextprüfung im eingeplanten
UI-Ereignispfad. Neovim 0.10 blockiert dagegen bereits im nativen Prompt; dort
erfasst das Plugin den begrenzten Editor-Snapshot unmittelbar beim belegten
`z=` und veröffentlicht ausschließlich die dazugehörige native Liste über
einen fast-callback-sicheren RPC-Hinweis. Die zusätzliche native
Eingabeanweisung am Listenende wird nur in ihrer engen Form akzeptiert.

Das Windows-Terminal-AppModule verwendet NVDAs normale kontextbezogene
Gestenauflösung für `NVDA+j/k/Enter`. Dienst und Controller prüfen erneut
Fokus, Control, Instanz, Capability und Editoridentität. Nur der interne
nullbasierte Index wird bestätigt; angezeigter Text wird niemals als Eingabe
zurückgesendet. Loslassen der NVDA-Taste verwirft die lokale Auswahl, nicht
Neovims Prompt. Weitere Abfragetypen benötigen jeweils einen eigenen strikten
Adapter.

### Gehaltene Entwicklerkontexte

Das Windows-Terminal-AppModule besitzt den physischen Lebenszyklus der
NVDA-Taste und fängt nur die festen Gesten für Parameter- oder
Diagnosenavigation ab. Der instanzbezogene `HeldContextController` korreliert
die lesende Anfrage mit Fokus, Terminal-Control, Instanz, Buffer, Fenster,
Tab, `changedtick`, Zeile und UTF-8-Bytespalte. Das Lua-Plugin liest
Signaturhilfe, Hover oder `vim.diagnostic`, verändert aber weder Cursor noch
Buffer. Jede Abweichung vor der Antwort oder während der Anzeige verwirft den
Zustand und stellt die normale Braillezeile wieder her. Transport-I/O bleibt
im begrenzten `ControlDispatcher`.

Für Braille verwendet der NVDA-Adapter den von NVDA vorgesehenen
vorübergehenden Nachrichtenpuffer. Derselbe öffentliche Pfad wird im
NVDA-Quellcode für Vorschlags- und Auswahlmeldungen verwendet und schreibt die
Anzeige unmittelbar, statt auf ein Fokusereignis zu warten. Vorher bestimmt
eine gewöhnliche NVDA-Region die Breite mit der aktiven Übersetzungstabelle;
die eingestellte Startposition wird dann auf den letzten vollständig passenden
Start begrenzt. Beim Loslassen wird ausschließlich die nachweislich eigene
Nachrichtenregion geschlossen und der darunter erhaltene Editorpuffer
aktualisiert. Die dafür nötige eng begrenzte private Gegenfunktion ist in
[ADR-0002](adr/0002-nvda-api-boundaries.md) dokumentiert.

### Dateimanager

`file_manager.lua` normalisiert den aktiven Eintrag; getrennte Adapter
abonnieren öffentliche Ereignisse von Oil, netrw, mini.files, nvim-tree und
Neo-tree, soweit verfügbar. Sie übertragen typisierte Namen, Arten, Zustände
und Aktionsresultate statt dekorierter Bildschirmzeilen. Fehlende Plugin-APIs
fallen auf vorhandene Navigation zurück. Die Funktionsmatrix und der praktische
Teststand stehen in `accessibility.md` und `current-status.md`.

Der Brailleplan bildet den kanonischen Dateimanagerzustand als dauerhafte
Region ab. Navigations- und Zustandsansagen bleiben reine Sprachaktionen und
erzeugen keine zweite NVDA-Braillemeldung, die diese Region bis zum
Meldungszeitende verdecken würde. Der Controller übergibt dem
NVDA-unabhängigen Brailleplaner dafür ausschließlich die
Übersetzungsfunktion; Namen und Routingpositionen bleiben unverändert,
während typisierte Arten und Zustände erst am NVDA-Rand lokalisiert werden.

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
