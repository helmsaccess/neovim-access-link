# ADR-0004: NVDA-Lebensdauer und Besitz von Anwendungsevents

## Status

Akzeptiert und umgesetzt.

## Kontext

NVDA lädt das Global Plugin einmal pro NVDA-Prozess und erzeugt ein
Windows-Terminal-AppModule pro Anwendungsprozess. Einstellungen, Werkzeuge und
gemeinsam genutzte lokale sowie SSH-Verbindungen benötigen eine einmalige,
geordnet beendete Lebensdauer. Windows-Terminal-Ereignisse, Overlayauswahl und
`nextHandler` gehören dagegen zum AppModule.

Prozessweit aufgerufene NVDA-Erweiterungspunkte können trotzdem nötig sein.
Sie dürfen den Anwendungsscope nicht erweitern: Ein Vorgang ist nur zulässig,
wenn das aktuelle Fokusobjekt, die registrierte AppModule-Instanz, das konkrete
Terminal-Control und der bestätigte Verbindungszustand zusammenpassen.

## Entscheidung

Das Global Plugin ist die prozessweite Kompositions- und Lebenszykluswurzel.
Es registriert Einstellungen und Werkzeuge, baut gemeinsame Dienste auf,
veröffentlicht sie erst nach vollständiger Initialisierung und beendet sie in
festgelegter Reihenfolge. Fachlicher Verbindungs-, Zuordnungs-, Gate-,
Protokoll- und Präsentationszustand liegt in gewöhnlichen Diensten ohne
Vererbung von `GlobalPlugin`.

Das Windows-Terminal-AppModule besitzt:

- alle anwendungsspezifischen NVDA-Ereigniseinstiege;
- Auswahl und Entfernung eigener Overlays;
- Metadaten und Ausführung konfigurierbarer Terminalbefehle;
- jeden Aufruf von `nextHandler`, höchstens einmal pro Ereignis;
- die fail-open-Entscheidung bei fehlendem, veraltetem, mehrdeutigem oder
  fehlerhaftem Zustand.

Der vom AppModule verwaltete Beobachter für
`inputCore.decide_executeGesture` ist nur registriert, solange mindestens ein
Windows-Terminal-AppModule lebt. Er betrachtet ausschließlich die ausdrücklich
unterstützten Kandidaten F12, kontextbezogene nummerierte Auswahllisten und den
genau identifizierten öffentlichen NVDA-Braillebefehl für die nächste Zeile.
Alle anderen Gesten bleiben unverändert. Jeder Treffer wird erneut gegen
Fokusobjekt, AppModule, Control-Identität, Dienstgeneration und Gate geprüft.

Beim Beenden oder Neuladen wird der gemeinsame Dienst zuerst als nicht
verfügbar markiert. Danach werden wartende Fokusentscheidungen verworfen,
Unterdrückung deaktiviert, Verbindungen beendet und UI-Registrierungen
symmetrisch entfernt. AppModules verwenden keine ungeprüfte alte
Dienstinstanz.

## Invarianten

- Fehler, Disconnect, Reload und unklarer Fokus fallen sofort auf NVDAs native
  Terminalbehandlung zurück.
- Tabs, Panes, Fenster und Windows-Terminal-Prozesse bleiben über die konkrete
  Control-Identität getrennt.
- Lokale und SSH-Sitzungen übernehmen keine Ausgabe, Fokusantwort oder Bindung
  voneinander.
- Netzwerk-I/O, Reconnect, Parsing und Logging blockieren nie NVDAs
  Hauptthread.
- Die native Fokusbehandlung für LiveText bleibt erhalten: Fokus vorbereiten,
  `nextHandler` genau einmal aufrufen und erst danach Sprachunterdrückung sowie
  wartenden `fullState` abschließen.

## Folgen

Anwendungsevents folgen NVDAs AppModule-Modell. Prozessweite Lebensdauer bleibt
dort erhalten, wo sie Doppelregistrierungen und konkurrierende Verbindungen
verhindert. Zusätzliche Auslagerungen aus der Kompositionswurzel sind nur
sinnvoll, wenn sie Besitz, Testbarkeit oder Fehlerisolation klar verbessern.

ADR-0002 bleibt für NVDA-API-Ausnahmen maßgeblich. Diese ADR erlaubt keine neue
private API-Nutzung.
