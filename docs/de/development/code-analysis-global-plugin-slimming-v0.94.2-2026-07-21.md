# Anhang B: Codeanalyse von `feature/global-plugin-slimming` gegenüber `v0.94.2`

Erstellt: 21. Juli 2026, 01:11:58 CEST (UTC+02:00)

Ausgangsstand: Tag `v0.94.2`, Commit `60569a648d363c1a9acc2872b3c81a148ddb6584`

Vergleichsstand: Branch `feature/global-plugin-slimming`, Commit
`b4195f3d900187f085275981d2ec1b0011a1952f`

Repository: Neovim Access Link

## Anlass und Fragestellung

Der Bericht prüft, ob der Feature-Branch sein Ziel erreicht hat: Der globale
NVDA-Bereich sollte schlanker werden, anwendungsspezifische Zuständigkeiten
sollten in das Windows-Terminal-AppModule wechseln, und gemeinsam genutzte
Zustände sollten klaren, normal testbaren Diensten gehören. Dabei durften die
Zuverlässigkeit, die F12-Zuordnung sowie der parallele Betrieb lokaler und
entfernter Neovim-Sitzungen über Fenster, Tabs und Panes nicht verloren gehen.

Die zentrale Frage ist daher nicht nur, ob weniger Code in der Klasse
`GlobalPlugin` steht. Entscheidend ist, ob Zuständigkeiten klarer, Fehlerpfade
sicherer und Änderungen besser prüfbar geworden sind, und ob der dafür neu
eingeführte Strukturaufwand gerechtfertigt ist.

## Kurzfassung

Das fachliche Ziel des Branches ist weitgehend erreicht. Der globale Einstieg
ist nicht minimal, aber er ist deutlich weniger zustandsreich und besitzt
keine Windows-Terminal-Ereignisse und keine `nextHandler`-Verantwortung mehr.
Die Ereignisse, Overlays und frei belegbaren Befehle liegen jetzt im
Windows-Terminal-AppModule. Gemeinsame Verbindungs-, Fokus-, F12-, Editor-,
UI-, Präsentations- und Lebenszykluszustände haben jeweils benannte Besitzer.
Der veröffentlichte AppModule-Vertrag ist eng und kann geschlossen werden,
sodass veraltete Referenzen nach einem Add-on-Neustart wirkungslos bleiben.

Die Verschlankung ist allerdings keine Verringerung der gesamten Codebasis:
Der Python-Produktionscode im untersuchten Kernbereich wuchs um 41,2 Prozent,
die Zahl der Klassen um 114 Prozent und die Zahl der Produktionsmodule um 14.
Ein großer Anteil davon sind kleine, unveränderliche Ergebnisobjekte, Enums,
Dienste und explizite Übergänge. Gleichzeitig sank die mittlere lokale
Verzweigungskomplexität um rund 23 Prozent, die 90. Perzentile von 12 auf 9,
und die größte frühere Global-Plugin-Methode wurde von einem Score von 134 auf
25 reduziert. Die Klasse `GlobalPlugin` selbst schrumpfte um 36,9 Prozent und
ihre selbst verwalteten Attribute von 58 auf 12.

Die zusätzliche strukturelle Komplexität ist überwiegend gerechtfertigt. Sie
modelliert reale Lebenszyklen, Besitzverhältnisse und asynchrone Rennen, die im
alten monolithischen Zustand ebenfalls vorhanden waren, dort aber implizit in
einer Klasse zusammenliefen. Die Vorteile sind daher real: bessere
AppModule-Konformität, isolierbare Zustandsübergänge, zuverlässigeres
Fail-open-Verhalten, deterministischer Start und Abbau sowie bessere
Regressionstests. Der Preis sind mehr Dateien, Datentypen, Konstruktorverdrahtung
und ein längerer Navigationsweg beim Debuggen.

Der größte neu sichtbare Qualitätsnachteil liegt inzwischen weniger im
Produktionscode als in der Testorganisation: `test_built_addon.py` ist auf
7.852 Zeilen und 62 Prozent des Python-Testcodes angewachsen. Der Testbestand
ist wesentlich stärker, aber die zentrale Testdatei ist zu groß und der
NVDA-Testlauf dauert in derselben Umgebung etwa doppelt so lange wie beim
0.94.2-Stand. Eine Aufteilung nach Architekturgrenzen wäre sinnvoll, ohne die
Produktionsarchitektur erneut umzubauen.

Praktisch wurden auf dem Vergleichsstand mehrere Windows-Terminal-Fenster,
Tabs und horizontale sowie vertikale Panes mit gemischten lokalen und
SSH-Verbindungen einschließlich Zwischenablagepfaden ohne gemeldeten Fehler
getestet. Automatisierte Tests und diese Praxisprüfung stützen die
Robustheitsaussage, beweisen aber keine Fehlerfreiheit. Praktische
Braille-Hardwaretests fehlen weiterhin.

## Untersuchungsumfang und Methode

### Vergleichsgrenze

`v0.94.2` ist der tatsächlich veröffentlichte, annotierte Tag und ein Vorfahr
des Branches. Zwischen dem Tag und dem Vergleichsstand liegen 51
Nicht-Merge-Commits. Der vollständige Diff umfasst:

- 81 geänderte Dateien;
- 15.937 hinzugefügte und 5.798 entfernte Zeilen;
- netto 10.139 zusätzliche Zeilen einschließlich Tests, Dokumentation,
  Übersetzungen und Build-Metadaten.

Der Vergleich enthält deshalb nicht ausschließlich mechanische
Global-Plugin-Extraktionen. Er enthält die vollständige Entwicklung seit
0.94.2 bis zum 0.95.0-Feature-Stand, darunter die schrittweise AppModule-
Umstellung, F12-Härtung, NVDA-Stilanpassung, neue Zustandsdienste,
Lebenszyklusarbeit, Dokumentation und zusätzliche Tests. Gesamtänderungszahlen
dürfen daher nicht einem einzelnen Refactoring-Schritt zugerechnet werden.

### Metrikdefinition

Die Produktions-Python-Messung umfasst:

- `protocol/python/nvim_nvda_protocol/`;
- `bridge/python/nvim_nvda_bridge/`;
- `nvda-addon/core/nvim_nvda_core/`;
- `nvda-addon/addon/appModules/`;
- `nvda-addon/addon/globalPlugins/NeovimAccessLink/`.

Die Testmessung umfasst die zugehörigen drei Python-Testverzeichnisse. Lua
wurde für Plugin- und Testumfang separat gezählt. Bei LOC handelt es sich um
physische Zeilen einschließlich Kommentare und Leerzeilen. Der
Komplexitätswert ist ein reproduzierbarer AST-basierter, McCabe-ähnlicher
Verzweigungsscore: Basiswert eins plus Kontrollverzweigungen, Handler,
Comprehensions, Assertions und boolesche Teilbedingungen. Verschachtelte
Funktionen werden separat gezählt. Er ist als Trendindikator gedacht, nicht
als exakter Ersatz für ein fest eingeführtes Werkzeug wie Radon.

LOC, Klassenanzahl und Komplexität sind keine Qualitätsurteile für sich. Sie
werden zusammen mit Besitzverhältnissen, Fehlerpfaden, Tests und praktischen
Ergebnissen bewertet. Eine Zeilenabdeckung wurde nicht gemessen, weil im
Projekt keine vergleichbare Coverage-Baseline eingerichtet ist. Latenz und
CPU-Kosten wurden in diesem Vergleich ebenfalls nicht neu vermessen.

## Quantitative Ergebnisse

### Produktionscode

| Metrik | `v0.94.2` | Branch | Veränderung |
|---|---:|---:|---:|
| Python-Dateien | 32 | 46 | +14 / +43,8 % |
| Python-LOC | 8.551 | 12.070 | +3.519 / +41,2 % |
| Lua-LOC | 3.134 | 3.163 | +29 / +0,9 % |
| Python und Lua zusammen | 11.685 | 15.233 | +3.548 / +30,4 % |
| Python-Klassen | 43 | 92 | +49 / +114,0 % |
| Python-Funktionen und Methoden | 390 | 601 | +211 / +54,1 % |
| mittlere Funktionslänge | 19,29 | 17,06 | -11,6 % |
| Median der Funktionslänge | 10 | 9 | -10,0 % |
| 90. Perzentile der Funktionslänge | 43 | 39 | -9,3 % |
| maximale Funktionslänge | 447 | 447 | unverändert |
| mittlerer Verzweigungsscore | 6,35 | 4,87 | -23,3 % |
| Median des Verzweigungsscores | 3 | 3 | unverändert |
| 90. Perzentile des Verzweigungsscores | 12 | 9 | -25,0 % |
| Funktionen mit Score > 10 | 46 / 11,8 % | 51 / 8,5 % | absolut +5, Anteil besser |
| Funktionen mit Score > 20 | 19 / 4,9 % | 21 / 3,5 % | absolut +2, Anteil besser |

Die absoluten Zahlen komplexerer Funktionen steigen leicht, weil es wesentlich
mehr Funktionen gibt. Ihr Anteil sinkt jedoch um etwa 28 Prozent. Das ist für
diesen Umbau aussagekräftiger als die absolute Anzahl: Logik wurde auf mehr,
im Mittel kleinere und lokal einfachere Einheiten verteilt.

Das gebaute Add-on wuchs von 349.521 auf 376.259 Byte, also um rund 7,6
Prozent. Die Paketgröße steigt damit wesentlich weniger als die
Quellcodezeilen, bleibt aber ein realer Preis der zusätzlichen Struktur.

### Der globale Einstieg und das AppModule

| Metrik | `v0.94.2` | Branch | Bewertung |
|---|---:|---:|---|
| `GlobalPlugin.__init__.py` LOC | 3.961 | 2.499 | -36,9 % |
| direkte `GlobalPlugin`-Methoden | 154 | 112 | -27,3 % |
| in der Klasse zugewiesene `self`-Attribute | 58 | 12 | -79,3 % |
| bereits in `__init__` gesetzte Attribute | 49 | 12 | -75,5 % |
| Global-Plugin-Methoden mit `nextHandler` | 8 | 0 | Zuständigkeit entfernt |
| absichtliche Kompositions-Properties | 0 | 2 | `_gate`, `_instanceManager` |
| AppModule-LOC | 207 | 352 | +70,0 % |
| AppModule-Methoden | 19 | 31 | +63,2 % |
| AppModule-Skripte insgesamt | 1 | 11 | Terminalbefehle in richtigen Bereich verschoben |

Die Größenverschiebung in das AppModule ist kein Rückschritt. Die dort
hinzugekommenen Methoden sind anwendungsspezifische Ereignisse und Befehle,
die NVDA genau dort erwartet. Im 0.94.2-Stand nahm das AppModule die Ereignisse
entgegen, reichte aber einschließlich einer geschützten `nextHandler`-
Funktion an private Methoden des Global Plugins weiter. Jetzt entscheidet das
AppModule selbst über native Weitergabe und ruft `nextHandler` im eigenen
Ereignispfad auf. Der gemeinsame Dienst liefert nur Entscheidungen.

Besonders deutlich ist die Änderung an der früheren zentralen Methode:

- `GlobalPlugin._handleEvent`: 245 Zeilen und Score 134 in 0.94.2;
- `GlobalPlugin._handleEvent`: 87 Zeilen und Score 25 im Branch.

Der größte unveränderte Komplexitätsschwerpunkt ist
`SpeechPlanner.plan` mit 447 Zeilen und Score 178. Er liegt im neutralen
Sprachplaner und war nicht Ziel dieser Verschlankung. Seine Größe bleibt eine
separate technische Schuld, wird durch diesen Branch aber weder verschärft
noch verdeckt.

### Größte Dateien im neuen NVDA-Bereich

| Datei | LOC | Hauptverantwortung |
|---|---:|---|
| `globalPlugins/NeovimAccessLink/__init__.py` | 2.499 | Komposition und verbleibende NVDA-/Transportgrenzen |
| `session_claim.py` | 1.380 | F12, Inventar, Auswahl und transaktionale Verbindungsübergänge |
| `nvda_ui.py` | 892 | Einstellungen, Tools-Menü und Komponentenformulare |
| `editor_session.py` | 772 | isolierter Editorzustand und neutrale Aktionspläne |
| `appModules/windowsterminal.py` | 352 | App-Ereignisse, Overlays, Befehle und `nextHandler` |
| `terminal_focus.py` | 327 | Identität, Fokusgeneration und Lebenszyklusprüfung |
| `terminal_integration.py` | 319 | enger öffentlicher AppModule-/Braille-Vertrag |
| `connection_coordinator.py` | 309 | Verbindungs- und Laufzeitzustand |
| `nvda_presentation.py` | 250 | konkrete NVDA-Ausgabe |

Die Dateien sind noch nicht alle klein. Sie sind jedoch nach einer
fachlichen Zuständigkeit geschnitten. Besonders `session_claim.py` und der
verbleibende Kompositionsroot verdienen bei künftigen Änderungen Beobachtung.
Eine weitere Aufteilung allein zur Senkung der Zeilenzahl wäre nicht
automatisch sinnvoll: Sie müsste einen neuen eindeutigen Besitzer, eine
kleinere öffentliche Schnittstelle oder einen direkt prüfbaren Fehlerpfad
schaffen.

## Testmetriken und ausgeführte Verifikation

### Python-Tests

Beide Python-Stände wurden in der aktuellen Linux-Umgebung tatsächlich
ausgeführt:

| Suite | `v0.94.2` | Branch |
|---|---:|---:|
| Protokoll | 42 bestanden | 42 bestanden |
| Bridge/RPC | 31 bestanden | 31 bestanden |
| NVDA/Add-on einschließlich gebautem Archiv | 287 bestanden | 362 bestanden |
| Gesamt | 360 bestanden | 435 bestanden |

Der Branch besitzt 75 zusätzliche Python-Tests, alle im NVDA-/Add-on-Bereich.
Die Tests des Vergleichsstands liefen unmittelbar für diesen Bericht erneut.
Der vollständige aktuelle Lua-Lauf bestand ebenfalls: Zwischenablage,
Completion, Dateimanager und deren Arbeitsabläufe, Menüs, Auswahl/Zustand,
Sitzungsregistrierung sowie Rechtschreib- und Diagnosepfade wurden ausgeführt.

Der vollständige Lua-Lauf des extrahierten 0.94.2-Baums ließ sich in dieser
Sandbox nicht vergleichbar zu Ende führen: Nach mehreren bestandenen Suiten
wurde der simulierte Windows-Loopback-`serverstart` durch die Umgebung mit
„operation not permitted“ blockiert. Deshalb wird aus diesem Lauf kein
vergleichender Lua-Erfolgswert abgeleitet. Die statische Lua-Testgröße stieg
lediglich von 1.459 auf 1.488 Zeilen.

### Teststruktur

| Metrik | `v0.94.2` | Branch | Veränderung |
|---|---:|---:|---:|
| Python-Testdateien | 22 | 24 | +2 |
| Python-Test-LOC | 9.452 | 12.662 | +34,0 % |
| Testfunktionen | 360 | 435 | +20,8 % |
| statische Assertion-Vorkommen | 1.267 | 1.890 | +49,2 % |
| Assertions je 1.000 Produktions-LOC | 148,2 | 156,6 | +5,7 % |
| Test-/Produktions-LOC-Verhältnis | 1,105 | 1,049 | leicht niedriger |
| mittlere Testfunktionslänge | 14,72 | 16,39 | +11,3 % |
| 90. Perzentile der Testfunktionslänge | 34 | 37 | +8,8 % |
| Anteil von `test_built_addon.py` | 52,9 % | 62,0 % | deutlich konzentrierter |

Die Teststärke ist insgesamt höher: Es gibt mehr konkrete Fälle, wesentlich
mehr Assertions und direkte Tests für Teilinitialisierung, Serviceaustausch,
späte Callbacks, Fokusrennen, `nextHandler`, F12, Braille-Fallback sowie
lokale und entfernte Parallelität. Das leicht gesunkene Verhältnis von
Test- zu Produktionszeilen ist deshalb kein Hinweis auf weniger Schutz.

Die Testwartbarkeit ist jedoch gemischt. `test_built_addon.py` wuchs von 5.002
auf 7.852 Zeilen. Viele dieser Tests laden bewusst das tatsächlich gebaute
Archiv und prüfen damit eine wichtige Paketgrenze, doch 62 Prozent des
Python-Testcodes in einer Datei erschweren Navigation, gemeinsame Fixtures
und gezielte Testauswahl. Auch die mittlere Testfunktionslänge stieg.

Die gemeldeten Laufzeiten in derselben Umgebung waren:

- 0.94.2-Python-Suiten zusammen: rund 69,2 Sekunden;
- Branch-Python-Suiten zusammen: rund 137,7 Sekunden.

Der langsamere Zyklus ist hauptsächlich auf die größere NVDA-/Paket-Suite
zurückzuführen. Er ist durch zusätzliche Integrationssicherheit teilweise
gerechtfertigt, sollte aber nicht unbegrenzt wachsen. Schnelle reine
Diensttests und langsamere Archiv-/Integrationsfälle sollten künftig klar
markierbar oder getrennt aufrufbar sein.

## Bewertung des Architekturzieles

### 1. Anwendungsspezifische Ereignisse gehören dem AppModule

Erfüllt.

Das Windows-Terminal-AppModule besitzt weiterhin alle zehn
anwendungsspezifischen NVDA-Ereigniseinstiege, jetzt aber auch die Entscheidung
über native Weitergabe und jeden `nextHandler`-Aufruf. Es besitzt ferner die
Overlay-Auswahl und die zehn frei belegbaren Terminalbefehle. Das Global
Plugin hat keine Methode mehr, die `nextHandler` als Parameter annimmt.

Das ist nicht nur kosmetisch. Ein Fehler im gemeinsamen Dienst kann im
AppModule direkt auf native NVDA-Verarbeitung zurückfallen. Der bislang
unklare Übergang „AppModule empfängt, Global Plugin besitzt das Ereignis“ ist
entfernt.

### 2. Der globale Bereich enthält nur wirklich prozessweite Aufgaben

Weitgehend erfüllt.

Prozessweit bleiben sinnvollerweise:

- einmalige Registrierung von Einstellungen und Tools-Menü;
- gemeinsame lokale und SSH-Verbindungen;
- Veröffentlichung und Entzug des schmalen Terminaldienstes;
- geordneter Start und Abbau;
- konkrete NVDA-, Dialog-, Diagnose- und Transportgrenzen.

Der globale Einstieg verdrahtet diese Dienste noch und enthält verbleibende
NVDA-seitige Callbacks. Mit 2.499 Zeilen und 112 Methoden ist er weiterhin
groß. Seine eigene Zustandslast ist aber stark gesunken: Er hält zwölf
Kompositionsobjekte statt Dutzender fachlicher Zustandscontainer. Die beiden
Properties `_gate` und `_instanceManager` sind bewusst beibehaltene, häufig
benutzte Kompositionsansichten. Eine zusätzliche Weiterleitungsschicht würde
hier nur Zeilen und Sprünge erzeugen, aber keinen neuen Besitzer.

### 3. Gemeinsamer Zustand hat eindeutige Besitzer

Erfüllt für die im Branch bearbeiteten Bereiche.

- `ConnectionCoordinator` besitzt Instanzen, Gate, Laufzeitzustände und
  korrelierte Requests.
- `TerminalFocusService` besitzt Identität, Fokusgeneration,
  Adapterkorrelation und Lebenszyklusprüfung.
- `SessionClaimService` besitzt F12-Autorisierung, Inventar, Auswahl und
  Verbindungsübergänge.
- `EditorSessionController` besitzt isolierten Editorzustand und neutrale
  Ausgabe-/Steuerpläne.
- `SettingsService`, `NvdaUiManager` und `NvdaPresentation` trennen
  Konfiguration, UI und konkrete Ausgabe.
- `AddonRuntime` besitzt Veröffentlichung, Teilinitialisierungs-Rollback und
  die feste Abbaureihenfolge.
- `service_registry.py` veröffentlicht den Dienst ohne Rückimport der
  Global-Plugin-Klasse.

Pakettests erzwingen, dass die extrahierten Laufzeit-, UI-, Fokus-, F12-,
Editor-, Braille-, Registry- und Terminaldienstmodule nicht von der Klasse
`GlobalPlugin` abhängen. Das ist ein stärkeres Ergebnis als eine reine
Dateiaufteilung.

### 4. Enge öffentliche Schnittstelle statt Global-Plugin-Zugriff

Erfüllt.

`TerminalIntegrationService` akzeptiert nur einen vollständigen, festen Satz
von `TerminalCommand`-Werten und schmale Callbacks. Das AppModule kann keine
beliebige private Global-Plugin-Methode mehr anhand eines Namens aufrufen.
Fokus-, F12- und Braille-Operationen prüfen den geschlossenen Zustand und
konkrete Identitäten. Die Dienstgeneration verhindert, dass eine nach Reload
veraltete F12-Autorisierung in die neue Laufzeit übergeht.

### 5. Zuverlässigkeit und Mehrfachbetrieb erhalten

Mit guter Evidenz erfüllt, aber nicht formal bewiesen.

Automatisiert geprüft werden unter anderem mehrere Instanzen, getrennte
Tabs/Fenster, Fokusrennen, lokale und SSH-Auswahl, Serviceersatz, verspätete
Callbacks, Abbaufehler, zwischenzeitliche Dialogfokusse, Zwischenablage und
Fail-open-Verhalten. Praktisch wurden mehrere Fenster, Tabs und Panes mit
gemischten lokalen und entfernten Verbindungen einschließlich Zwischenablage
ohne neu gemeldeten Fehler getestet.

Während der Migration wurden reale Regressionen gefunden, insbesondere ein
durch den modalen „Verbindung merken“-Dialog veränderter Fokus und später ein
F12-Angebot, das wegen dieses Fokuswechsels verworfen wurde. Die Korrektur ist
nun an Identität, Instanz und eine einmalige Reaktivierung gebunden. Dass diese
Fehler auftraten, zeigt das Risiko des Umbaus; dass sie reproduziert,
eingegrenzt, automatisiert abgesichert und anschließend praktisch erneut
getestet wurden, stärkt die heutige Lösung.

## Auswirkungen auf die Testbarkeit

### Verbesserungen

- Dienste können mit injizierten Abhängigkeiten ohne vollständige NVDA-
  Instanz geprüft werden.
- Unveränderliche Ergebnisobjekte machen Übergänge und Ablehnungsgründe
  explizit prüfbar.
- Start, Teilfehler und Abbau haben einen festen Eigentümer und eine testbare
  Reihenfolge.
- Fokusgenerationen, Adaptertokens, Dienstgeneration und Request-IDs erlauben
  gezielte Race-Tests statt zeitabhängiger Annahmen.
- Der gebaute Add-on-Inhalt wird weiterhin als Paket geprüft; Quellbaum und
  ausgeliefertes Archiv können dadurch nicht unbemerkt auseinanderlaufen.
- AppModule-Fail-open und `nextHandler` lassen sich getrennt von
  Verbindungs- und Editorlogik testen.

### Nachteile und Grenzen

- Viele Tests verwenden umfangreiche NVDA-Stubs und Strukturprüfungen. Sie
  können API-Missverständnisse nicht vollständig ersetzen.
- Die sehr große zentrale Archivtestdatei erschwert Wartung und gezielte
  Fehlersuche.
- Der vollständige NVDA-Testlauf ist merklich langsamer geworden.
- Keine gemessene Zeilen- oder Branch-Coverage erlaubt eine direkte Aussage,
  welcher Anteil des Codes tatsächlich ausgeführt wird.
- Braille-Planung und Fallback sind automatisiert geprüft, nicht aber die
  tatsächliche Bedienung mit Hardware.

Gesamturteil: Die fachliche Testbarkeit ist klar besser, die organisatorische
Testwartbarkeit sollte als Nächstes verbessert werden.

## Auswirkungen auf die Wartbarkeit

### Verbesserungen

- Zuständigkeiten sind benannt und in ADR-0004 dokumentiert.
- Änderungen an Fokus, F12, Editorzustand, UI oder Ausgabe müssen nicht mehr
  denselben großen Zustandsblock verändern.
- Der AppModule-/Global-Plugin-Grenzverlauf folgt NVDA-Konventionen besser.
- Der Wechsel auf öffentliche NVDA-Windows-Wrapper beziehungsweise
  `winBindings` entfernt parallele DLL-Bindings.
- Symmetrische Registrierung und idempotenter Abbau reduzieren Sonderfälle bei
  Reload und Teilinitialisierung.
- Kleine, feste öffentliche Verträge begrenzen unbeabsichtigte Kopplung.

### Belastungen

- Mehr Module und fast doppelt so viele Klassen erhöhen den
  Einarbeitungsaufwand.
- Viele Dataclasses und Enums erzeugen bewusst mehr Definitionen, die beim
  Debuggen verfolgt werden müssen.
- Der Kompositionskonstruktor und seine Callback-Verdrahtung bleiben lang.
- `session_claim.py`, `nvda_ui.py`, `editor_session.py` und der verbleibende
  Global-Plugin-Root sind weiterhin große Dateien.
- Dokumentation muss die Grenzen dauerhaft konsistent halten; veraltete
  Phasenbeschreibungen könnten sonst verwirren.

Gesamturteil: Wartbarkeit verbessert sich für gezielte Änderungen und
Fehlerisolierung, während die anfängliche Orientierung aufwendiger wird. Für
dieses Add-on mit mehreren Prozessen, Transporten und Fokusidentitäten ist der
Trade-off vertretbar.

## Auswirkungen auf Robustheit und Sicherheit

### Positive Änderungen

- Unsicherheit über Fokus, Identität, Dienstgeneration oder Authentifizierung
  führt konsequent zur nativen NVDA-Verarbeitung.
- Der Dienst wird erst nach vollständiger Initialisierung veröffentlicht und
  vor dem übrigen Abbau entzogen und geschlossen.
- Späte Main-Thread-, Netzwerk-, F12- und Braille-Callbacks werden nach
  Unpublish erneut verworfen.
- Der Abbau läuft nach einem Einzelfehler mit den verbleibenden Schritten
  weiter.
- AppModule-Ereignisse behalten NVDA-LiveText durch genau einen nativen
  Fokusaufruf.
- F12 prüft das konkrete fokussierte AppModule und die vollständige
  Terminalidentität; ein einzelnes vorhandenes AppModule ist kein Ersatz für
  Fokusnachweis.
- Lokale und entfernte Zustände sind pro Instanz getrennt und korrelierte
  Antworten werden nach Fokusverlust verworfen.
- Die öffentliche Befehlsfläche ist allowlisted und kann nicht dynamisch auf
  beliebige Methoden erweitert werden.

### Verbleibende Risiken

- Die wesentliche Zustandsmaschine ist verteilt; Fehler können jetzt an
  Dienstübergängen statt innerhalb einer Klasse entstehen.
- Zusätzliche Callback-Schichten können fehlerhaft verdrahtet werden. Die
  Vollständigkeits- und Teilinitialisierungstests mindern, beseitigen dieses
  Risiko aber nicht.
- `SpeechPlanner.plan` bleibt ein großer, komplexer neutraler Hotspot.
- `SessionClaimService` bündelt weiterhin viele zusammenhängende, aber
  anspruchsvolle F12- und Verbindungsübergänge.
- Praktische Braille- und weitere nicht getestete NVDA-/WT-Kombinationen
  bleiben offen.
- Es liegt keine neue Latenz- oder Speicherbenchmark vor. Die zusätzlichen
  lokalen Methoden- und Dataclass-Übergänge sind wahrscheinlich klein
  gegenüber UIA, SSH und RPC, diese Einschätzung ist aber nicht gemessen.

Gesamturteil: Die Robustheit ist durch explizite Invarianten und Abbaupfade
besser abgesichert. Die zusätzlichen Übergänge schaffen neue mögliche
Fehlerorte, sind aber enger und gezielter testbar als der frühere gemeinsame
Zustandsblock.

## Ist die zusätzliche Komplexität gerechtfertigt?

### Ja, für die fachlichen Grenzen

Das Add-on koordiniert gleichzeitig:

- NVDA-Prozesslebensdauer und Windows-Terminal-AppModule-Lebensdauer;
- mehrere Fenster, Tabs, Panes und Prozesse;
- lokale TCP- und entfernte SSH-Sitzungen;
- asynchrone Verbindung, Fokuswechsel, Reload und verspätete Antworten;
- Sprach-, Sound- und Brailleausgabe;
- F12 als eng begrenztes, aber prozessweit beobachtetes Zuordnungssignal.

Diese Komplexität existiert unabhängig von der Zahl der Dateien. Im
0.94.2-Stand war ein großer Teil davon als veränderlicher Zustand und private
Methodenkopplung im Global Plugin verborgen. Der Branch macht sie sichtbar
und gibt ihr prüfbare Grenzen. Der starke Rückgang der Root-Attribute, der
Funktionslänge und der lokalen Verzweigungswerte bestätigt, dass nicht bloß
Code verschoben wurde.

### Nicht jede zusätzliche Abstraktion wäre weiter gerechtfertigt

Der Umbau sollte an der jetzigen Stelle nicht allein fortgesetzt werden, um
`GlobalPlugin.__init__.py` unter einen willkürlichen Zeilengrenzwert zu
drücken. Eine neue Schicht ist nur sinnvoll, wenn mindestens einer der
folgenden Gewinne nachweisbar ist:

- ein eindeutiger neuer Zustandsbesitzer;
- ein kleinerer oder stabilerer öffentlicher Vertrag;
- ein Fehlerpfad, der dadurch ohne NVDA testbar wird;
- Entfernung einer realen Rückkopplung oder doppelten Zustandskopie;
- messbare Verringerung von Start-, Reload- oder Fokusrisiken.

Reine Weiterleitungsmethoden oder ein zusätzlicher Fassadenname ohne eigenen
Zustand würden die Navigation verschlechtern und die Codebasis weiter
vergrößern.

## Konkrete Vorteile

1. **Korrekte NVDA-Zuständigkeit:** Ereignisse, Overlays, Befehle und
   `nextHandler` liegen im Windows-Terminal-AppModule.
2. **Weniger globaler veränderlicher Zustand:** 58 auf 12 zugewiesene
   Root-Attribute reduziert unbeabsichtigte Querverbindungen.
3. **Besserer Reload und Abbau:** Veröffentlichung, Schließen und
   idempotenter Abbau haben eine feste Reihenfolge.
4. **Robusteres Fail-open:** Ein geschlossener, veralteter oder unklarer Dienst
   fällt auf native Terminalunterstützung zurück.
5. **Bessere Parallelität:** Zustände und Requests werden pro Instanz und
   konkreter Terminalidentität korreliert.
6. **Bessere Tests:** 75 zusätzliche Python-Fälle und 49 Prozent mehr
   Assertion-Vorkommen sichern die neuen Grenzen ab.
7. **Kleinere lokale Entscheidungsblöcke:** Durchschnitt und hohe Perzentilen
   der Funktionskomplexität sind deutlich niedriger.
8. **Engere Angriffs- und Fehlerfläche:** Der AppModule-Vertrag erlaubt nur
   feste Befehle und validierte Operationen statt beliebiger privater
   Global-Plugin-Aufrufe.

## Konkrete Nachteile

1. **Mehr Gesamtcode:** Python-Produktionscode wächst um 41 Prozent.
2. **Mehr Strukturbegriffe:** Dateien, Klassen, Dataclasses und Enums erhöhen
   den Einarbeitungsaufwand.
3. **Größeres Archiv:** Das Add-on wächst um rund 7,6 Prozent.
4. **Langsamerer Testzyklus:** Die Python-Suiten benötigen in dieser Messung
   fast doppelt so lange.
5. **Testmonolith:** 62 Prozent des Python-Testcodes liegen in einer Datei.
6. **Verteiltes Debugging:** Ein Ereignis kann AppModule, Dienst, Besitzer,
   Planung und NVDA-Präsentation durchlaufen.
7. **Migration war risikoreich:** Fokus- und F12-Regressionsfälle mussten
   während der Arbeit praktisch entdeckt und korrigiert werden.
8. **Kein belegter Latenzgewinn:** Die Architektur verbessert Grenzen, nicht
   nachgewiesen die Laufzeitgeschwindigkeit.

## Qualitätsurteil nach üblichen Kriterien

| Kriterium | Urteil gegenüber `v0.94.2` | Begründung |
|---|---|---|
| Korrektheit der NVDA-Grenzen | deutlich besser | AppModule besitzt Events, Overlays, Skripte und `nextHandler` |
| Kohäsion | besser | benannte Dienste besitzen jeweils zusammengehörigen Zustand |
| Kopplung | besser an den Blättern, höher in der Komposition | Dienste importieren nicht `GlobalPlugin`; Root verdrahtet mehr Komponenten |
| lokale Komplexität | deutlich besser | mittlerer Score 6,35 auf 4,87; P90 12 auf 9 |
| strukturelle Komplexität | höher | 14 weitere Python-Dateien und 49 weitere Klassen |
| Testbarkeit | deutlich besser | injizierbare Dienste, feste Resultate, 75 neue Fälle |
| Testwartbarkeit | teilweise schlechter | sehr große zentrale Pakettestdatei und längerer Lauf |
| Robustheit | besser abgesichert | Fail-open, Dienstgeneration, Rollback, Abbau und Race-Tests |
| praktische Funktionssicherheit | bisher erhalten | gemischte lokale/SSH-Fenster, Tabs, Panes und Clipboard ohne gemeldeten Fehler |
| Performance/Latenz | offen | keine vergleichbare Laufzeitmessung des Produktpfads |
| Sicherheit/Isolation | besser | engere Befehle, exakte Identität und stale-callback fences |
| Dokumentierte Architektur | besser | ADR-0004 und parallele Entwicklerdokumentation beschreiben Eigentümer |

## Auffälligkeiten außerhalb des Kernurteils

`git diff --check v0.94.2..HEAD` meldet vier Stellen mit nachgestellten
Leerzeichen in den deutschen und englischen Qualitätsberichten vom 19. Juli.
Sie sehen wie Markdown-Zeilenumbrüche mit zwei Leerzeichen aus, verhindern
aber einen vollständig sauberen `diff --check`-Lauf. Vor einem Merge sollte
entschieden werden, ob diese harten Umbrüche durch normalen Absatztext oder
eine andere Markdown-Struktur ersetzt werden. Dies ist kein funktionaler
Fehler des Add-ons.

Hinweis bei Aufnahme als Anhang: Die vier Warnungen wurden am 21. Juli 2026
durch normale Absätze in Anhang A beseitigt. Der Befund bleibt hier erhalten,
weil er zum dokumentierten Vergleichszeitpunkt bestand.

## Handlungsempfehlung

1. **Architekturstand beibehalten.** Der Branch erfüllt das fachliche
   Verschlankungsziel. Eine Rückkehr zum 0.94.2-Monolithen würde reale
   Eigentums- und Reload-Vorteile verlieren.
2. **Nicht nach LOC weiter extrahieren.** Weitere Produktionsaufteilung nur bei
   konkretem Zuständigkeits-, Test- oder Robustheitsgewinn.
3. **Tests modularisieren.** `test_built_addon.py` nach stabilen Bereichen wie
   AppModule/Fokus, Laufzeit/Teardown, F12/Verbindung, Editor/Clipboard,
   UI/Übersetzung und Paketinhalt aufteilen. Gemeinsame NVDA-Stubs als kleine
   Testhilfe kapseln.
4. **Schnelle und langsame Tests trennbar machen.** Reine Diensteinheitstests
   sollten schnell auswählbar bleiben; Archiv- und echte Neovim-RPC-Tests
   bleiben Pflicht vor Push oder Release.
5. **Komplexitätshotspots beobachten.** `SpeechPlanner.plan` separat planen;
   `SessionClaimService` nur bei konkretem Änderungsdruck weiter schneiden.
6. **Praktischen Testbestand fortführen.** Das bewährte Raster aus mehreren
   Fenstern, Tabs und Panes, lokal/SSH, Fokuswechsel, F12, Clipboard, Terminal
   und Reload vor Merge beziehungsweise Release nochmals ausführen.
7. **Braille-Lücke offen dokumentieren.** Automatisierte Planung ist kein
   Ersatz für Hardwaretests; keine weitergehende Stabilitätsaussage ableiten.
8. **Optional Latenzbaseline ergänzen.** Für spätere Architekturänderungen
   Fokusreaktion, Ereignisplanung und Main-Thread-Zeit mit einer kleinen,
   reproduzierbaren Messung erfassen.
9. **Vier `diff --check`-Warnungen bereinigen**, falls ein sauberer
   Whitespace-Check Teil der Merge-Anforderung sein soll.

## Schlussfolgerung

Wenn „Verschlankung“ ausschließlich weniger Gesamtzeilen bedeutet, hat der
Branch das Ziel nicht erreicht. Diese Definition wäre für die vorliegende
Aufgabe jedoch zu eng. Nach den relevanten Architektur- und Qualitätszielen
ist der Branch erfolgreich: Der globale Einstieg besitzt wesentlich weniger
eigenen Zustand, anwendungsspezifische NVDA-Verantwortung liegt im AppModule,
gemeinsame Zustände haben normale Besitzer, und Reload-, Race- und
Fail-open-Pfade sind expliziter und besser testbar.

Die erhöhte strukturelle Komplexität ist durch diese Vorteile überwiegend
gerechtfertigt. Sie sollte nun stabilisiert, nicht aus Prinzip weiter erhöht
werden. Der sinnvollste nächste Qualitätsgewinn liegt in der Aufteilung und
Beschleunigung der Tests sowie in gezielten Messungen der verbleibenden
Hotspots, nicht in einer weiteren rein kosmetischen Zerlegung des Global
Plugins.

## Nachweise im Repository

- Architekturentscheidung: [`ADR-0004`](adr/0004-nvda-lifetime-and-event-ownership.md)
- aktueller Implementierungsstand: [`current-status.md`](current-status.md)
- aktiver Plan: [`plan.md`](plan.md)
- Windows-Terminal-AppModule: [`windowsterminal.py`](../../../nvda-addon/addon/appModules/windowsterminal.py)
- öffentlicher Terminalvertrag: [`terminal_integration.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/terminal_integration.py)
- geordneter Lebenszyklus: [`addon_runtime.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/addon_runtime.py)
- F12- und Auswahlbesitzer: [`session_claim.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/session_claim.py)
- Editorzustand: [`editor_session.py`](../../../nvda-addon/addon/globalPlugins/NeovimAccessLink/editor_session.py)
- Verbindungsbesitzer: [`connection_coordinator.py`](../../../nvda-addon/core/nvim_nvda_core/connection_coordinator.py)
- zentrale Paket-/NVDA-Tests: [`test_built_addon.py`](../../../nvda-addon/tests/test_built_addon.py)
