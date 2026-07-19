# ADR-0004: NVDA-Lebensdauer und Besitz von Anwendungsevents

## Status

Als Zielarchitektur für eine schrittweise Migration angenommen. Der gemeinsame
Dienst wird inzwischen über einen identitätsgeprüften Registrar gefunden.
Terminalereignisse, Overlayauswahl und `nextHandler` liegen im
Windows-Terminal-AppModule. Diese Stufe ist automatisiert sowie praktisch mit
lokalen und entfernten Verbindungen in mehreren WT-Fenstern, Tabs und Panes
bestätigt; eine praktische Brailleprüfung war nicht möglich. Für
frei belegbare Befehle ist das Windows-Terminal-AppModule das Ziel; ihre
eigentliche Verlagerung bleibt ein getrennt zu prüfender Migrationsschritt.

## Kontext

NVDA lädt das Global Plugin einmal pro NVDA-Prozess, ein Windows-Terminal-
AppModule dagegen für den jeweiligen Anwendungsprozess. Einstellungen,
Werkzeuge sowie gemeinsame lokale und SSH-Verbindungen benötigen deshalb eine
einmalige, geordnet beendete Lebensdauer. Windows-Terminal-Ereignisse,
Overlayauswahl und `nextHandler` gehören dagegen zum AppModule.

Die frühere Implementierung besaß die öffentlichen Ereigniseinstiege im
AppModule, delegierte Entscheidung und `nextHandler` aber an eine große
GlobalPlugin-Instanz. Diese Delegation wurde entfernt; der gemeinsame Dienst
liefert dem AppModule nur noch fachliche Fokus- und Suppressionsentscheidungen.

## Entscheidung

Ein minimales Global Plugin bleibt als prozessweite Kompositions- und
Lebenszykluswurzel. Es darf ausschließlich:

- Einstellungen und Werkzeuge einmalig und symmetrisch registrieren;
- gemeinsame Dienste aufbauen, verfügbar machen und geordnet beenden;
- vorläufig die Metadaten frei belegbarer Befehle bereitstellen, bis sie in
  einem getrennten Schritt in das Windows-Terminal-AppModule verlagert sind.

Verbindung, Zuordnung, Gate, Protokollzustand und Präsentationsplanung liegen
in normalen Diensten ohne Vererbung von `GlobalPlugin`. Ihr Vertrag nimmt
konkrete Terminalidentitäten und fachliche Daten entgegen und liefert
Entscheidungen oder Ausgabepläne zurück. Er übernimmt weder öffentliche
AppModule-Ereignisse noch `nextHandler` oder die Overlayliste.

Das Windows-Terminal-AppModule besitzt:

- alle anwendungsspezifischen NVDA-Ereigniseinstiege;
- die Auswahl und Entfernung eigener Overlays;
- jeden Aufruf von `nextHandler`, höchstens einmal pro Ereignis;
- die fail-open-Entscheidung, wenn Dienst, Identität oder Zustand fehlen,
  veraltet, mehrdeutig oder fehlerhaft sind.

Beim Laden wird ein gemeinsamer Dienst erst nach vollständiger Initialisierung
veröffentlicht. Beim Neuladen oder Beenden wird er zuerst als nicht verfügbar
markiert; danach werden ausstehende Fokusentscheidungen verworfen,
Unterdrückung deaktiviert, Verbindungen beendet und UI-Registrierungen
symmetrisch entfernt. AppModules dürfen keine ungeprüfte alte Dienstinstanz
weiterverwenden. Die aktuelle Umsetzung veröffentlicht die vollständig
initialisierte Instanz über einen identitätsgeprüften Registrar und entfernt
sie vor dem übrigen Abbau.

## F12-Ausnahme

F12 bleibt das ausdrückliche Zuordnungssignal, ist aber weder ein globaler
Eingabe-Hook noch ein NVDA-Skript. Nur das Windows-Terminal-AppModule beobachtet
die physische Taste. Nach dem F12-Treffer müssen NVDAs aktuelles Fokusobjekt,
dessen konkrete registrierte AppModule-Instanz und die daraus gebildete
Control-Identität mit dem Gate übereinstimmen; ein bloß einzig vorhandenes
AppModule ist kein Ersatznachweis. Die Zuordnung darf erst beginnen, wenn
zusätzlich erneut auf NVDAs Hauptthread dasselbe konkrete fokussierte
Windows-Terminal-Control bestätigt ist. Jede Abweichung fällt ohne Zuordnung
auf native Verarbeitung zurück.

## Nicht verhandelbare Invarianten

- Fehler, Disconnect, Reload und unklarer Fokus fallen sofort offen auf NVDAs
  native Terminalbehandlung zurück.
- Tabs, Split-Panes, Fenster und mehrere Windows-Terminal-Prozesse bleiben über
  die konkrete Control-Identität getrennt.
- Lokale und SSH-Sitzungen dürfen gemeinsame Lebensdauer besitzen, aber keine
  Ausgabe, Fokusantwort oder Bindung untereinander übernehmen.
- Netzwerk-I/O, Reconnect, Parsing und Logging blockieren nie NVDAs
  Hauptthread.
- Die für LiveText notwendige native Fokusbehandlung bleibt erhalten; ihre
  Reihenfolge ist festgelegt: Fokus vorbereiten, `nextHandler` genau einmal
  ausführen und erst danach Sprachunterdrückung sowie wartenden `fullState`
  abschließen. Adaptertoken und Fokusgeneration verwerfen verspätete
  Abschlüsse.

## Befehls-Scope

NVDA 2026.1.1 erzeugt den Tastenbefehldialog aus dem vor dem Öffnen
fokussierten Objekt und dessen AppModule. Bei zuvor fokussiertem Windows
Terminal sind Befehle des Windows-Terminal-AppModules damit auffindbar. Sie
sollen deshalb in einer eigenen Migrationsstufe dorthin verschoben werden und
sind bei der Ausführung automatisch enger auf den aktuellen Anwendungskontext
begrenzt. Bis dahin bleiben die vorhandenen global sichtbaren, unbelegten
Skriptmetadaten bestehen. Es werden keine neuen globalen Standardgesten
eingeführt.

## Folgen

Die globale Lebensdauer bleibt dort erhalten, wo sie Doppelregistrierungen und
mehrfache Verbindungen verhindert. Anwendungsevents werden enger an NVDAs
AppModule-Modell gebunden. Die Umstellung erfolgt phasenweise; eine Phase wird
nur übernommen, wenn automatisierte und praktische Prüfungen mindestens die
bisherige Mehrfenster-, Fokus- und Fail-open-Zuverlässigkeit belegen.

ADR-0002 bleibt für private NVDA-API-Ausnahmen maßgeblich. Diese ADR
konkretisiert deren Verantwortungsgrenze, ohne neue private API-Nutzung zu
erlauben.
