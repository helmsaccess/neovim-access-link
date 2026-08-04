# ADR-0004: NVDA-Lebensdauer und Besitz von Anwendungsevents

## Status

Angenommen und für den Anwendungsschnitt umgesetzt. Der gemeinsame
Dienst wird inzwischen über einen identitätsgeprüften Registrar gefunden.
Terminalereignisse, Overlayauswahl und `nextHandler` liegen im
Windows-Terminal-AppModule. Diese Stufe ist automatisiert sowie praktisch mit
lokalen und entfernten Verbindungen in mehreren WT-Fenstern, Tabs und Panes
bestätigt. Der strukturierte Regions- und Routingpfad wurde inzwischen
zusätzlich mit einer physischen Braillezeile geprüft. Frei belegbare
Terminalbefehle liegen nun ebenfalls unter automatisierter und praktischer
Abdeckung im Windows-Terminal-AppModule. Der abschließende Praxismeilenstein
ergab keinen gemeldeten Fehler in den aktuellen lokalen, SSH-, Fokus-,
Terminal-, Zwischenablage-, Dateimanager- und Reloadvarianten.

Die darüber hinaus beschriebene physisch minimale Kompositionswurzel ist ein
weiterhin geltendes Ziel, kein vollständig erreichter Ist-Zustand. Die
konkrete Global-Plugin-Klasse koordiniert derzeit zusätzlich prozessweite
NVDA-Randabläufe. Diese verbleibende Abweichung und ihre empfohlene
schrittweise Behandlung dokumentiert [Anhang C](../global-plugin-appmodule-audit-2026-08-04.md).

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

Ein minimales Global Plugin bleibt das Ziel als prozessweite Kompositions- und
Lebenszykluswurzel. Nach vollständiger Umsetzung darf es ausschließlich:

- Einstellungen und Werkzeuge einmalig und symmetrisch registrieren;
- gemeinsame Dienste aufbauen, verfügbar machen und geordnet beenden.

Verbindung, Zuordnung, Gate, Protokollzustand und Präsentationsplanung liegen
in normalen Diensten ohne Vererbung von `GlobalPlugin`. Ihr Vertrag nimmt
konkrete Terminalidentitäten und fachliche Daten entgegen und liefert
Entscheidungen oder Ausgabepläne zurück. Er übernimmt weder öffentliche
AppModule-Ereignisse noch `nextHandler` oder die Overlayliste.

Das Windows-Terminal-AppModule besitzt:

- alle anwendungsspezifischen NVDA-Ereigniseinstiege;
- die Auswahl und Entfernung eigener Overlays;
- Metadaten und Ausführung frei belegbarer Terminalbefehle;
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
Der frühere Strukturaudit bestätigt außerdem, dass ausgelagerte
Runtime-, UI-, Fokus-, Claim-, Editor-, Braille-, Registry- und
Terminaldienstmodule nicht von der `GlobalPlugin`-Klasse abhängen. Die
Klasse bleibt aktuell dennoch ein umfangreicher prozessweiter
NVDA-Randcontroller. Das ändert weder die Zuständigkeit des AppModules noch die
alleinigen fachlichen Zustandseigentümer; eine weitere Zerlegung soll
gemeinsame Abläufe nur bei klarem Besitz- und Testnutzen in gewöhnliche Dienste
verschieben.

## Begrenzter prozessweiter Gestenbeobachter

Das Windows-Terminal-AppModule besitzt die Registrierung am öffentlichen, aber
prozessweit aufgerufenen `inputCore.decide_executeGesture`-Decider. Sie besteht
nur, solange mindestens eine Instanz dieses AppModules geladen ist, wird
symmetrisch entfernt und darf ausschließlich drei eng begrenzte Fälle
beobachten:

- F12 als ausdrückliches Zuordnungssignal, das kein NVDA-Skript ist;
- `NVDA+j/k/Eingabe` sowie die noch gehaltene nackte
  `j/k`-Autorepeat-Fortsetzung einer bereits autorisierten nummerierten
  Auswahlliste;
- NVDAs öffentlichen, über Skriptname und Skriptort exakt bestätigten
  `globalCommands.GlobalCommands.braille_nextLine`-Befehl.

Alle anderen Gesten kehren unverändert zurück. Der Beobachter fragt nur für
einen der genannten Kandidaten das Fokusobjekt ab und arbeitet anschließend
ausschließlich mit dessen konkret registrierter AppModule-Instanz.

Nach einem F12-Treffer müssen NVDAs aktuelles Fokusobjekt, dessen konkrete
registrierte AppModule-Instanz und die daraus gebildete Control-Identität mit
dem Gate übereinstimmen; ein bloß einzig vorhandenes AppModule ist kein
Ersatznachweis. Die Zuordnung darf erst beginnen, wenn zusätzlich erneut auf
NVDAs Hauptthread dasselbe konkrete fokussierte Windows-Terminal-Control
bestätigt ist. Jede Abweichung fällt ohne Zuordnung auf native Verarbeitung
zurück. Die nummerierte Auswahl besitzt dieselben Identitäts- und
Generationsprüfungen und darf nur ihre festen Navigations- oder
Annahmeaktionen verbrauchen.

Die Braillezeilenbeobachtung verbraucht die Geste nicht, führt keine
Transportaktion aus und liest weder Treiberzustand noch private
Braillepuffer. Sie setzt nach exakter Fokus-, AppModule-, Ereignistoken- und
Dienstgenerationsprüfung lediglich eine einmalige Markierung für denselben
NVDA-Ereigniszug. Die Markierung wird nach Verwendung oder spätestens über
NVDAs Ereigniswarteschlange verworfen. Sie ist nötig, weil NVDAs öffentliche
`TextInfoRegion.nextLine()`-Methode sowohl für einen direkten
Zeilenwechselbefehl als auch beim horizontalen Wechsel über eine
Regionsgrenze aufgerufen wird, aber weder Geste noch Richtung erhält. Ohne
diese Markierung könnte das Add-on die gewünschte semantische Zielspalte bei
direktem Abwärtsnavigieren nicht zuverlässig von horizontalem Weiterblättern
unterscheiden. Treiber-Hooks oder private NVDA-Zustände werden dadurch
vermieden.

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
liegen nun dort und werden durch NVDAs normale Auflösung auf diese Anwendung
begrenzt. Beim Aufruf werden konkrete AppModule-Instanz und Control-Identität
zusätzlich erneut geprüft, damit ein Fokusrennen offen ausfällt. In früheren
Featurebuilds für das Global Plugin gespeicherte Belegungen müssen neu
zugewiesen werden. Es werden keine neuen globalen Standardgesten eingeführt.
Nach dem Laden der Klasse kann NVDA eine gespeicherte AppModule-Zuordnung aus
einer anderen Anwendung heraus darstellen, weil der Tastenbefehldialog zuerst
die globale Benutzergestenkarte aufzählt; die Laufzeitauflösung bleibt an die
fokussierte AppModule-Instanz gebunden.

## Folgen

Die globale Lebensdauer bleibt dort erhalten, wo sie Doppelregistrierungen und
mehrfache Verbindungen verhindert. Anwendungsevents werden enger an NVDAs
AppModule-Modell gebunden. Die Umstellung erfolgt phasenweise; eine Phase wird
nur übernommen, wenn automatisierte und praktische Prüfungen mindestens die
bisherige Mehrfenster-, Fokus- und Fail-open-Zuverlässigkeit belegen.

ADR-0002 bleibt für private NVDA-API-Ausnahmen maßgeblich. Diese ADR
konkretisiert deren Verantwortungsgrenze, ohne neue private API-Nutzung zu
erlauben.
