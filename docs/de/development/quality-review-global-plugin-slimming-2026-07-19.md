# Anhang A: Qualitätsreview der Global-Plugin-Verschlankung

Reviewdatum: 19. Juli 2026, 20:04:03 CEST (UTC+02:00)

Vergleich: `feature/global-plugin-slimming` gegen `main`

Produktstand des geprüften Testbuilds: `0.94.2-dev.13`

## Warum dieser Bericht existiert

Neovim Access Link besteht auf NVDA-Seite aus einem Windows-Terminal-AppModule,
einem Global Plugin und gemeinsam genutzten Diensten. In einer fachlichen
Diskussion zur NVDA-Add-on-Architektur wurde zu Recht gefragt, ob das Global
Plugin mehr Verantwortung und prozessweite Reichweite besitzt als nötig.

Daraufhin wurde der Featurebranch `feature/global-plugin-slimming` angelegt.
Er soll die Zuständigkeitsgrenzen an NVDAs übliche Erweiterungspunkte annähern,
ohne die bereits praktisch bestätigte Zuordnung mehrerer Windows-Terminal-
Fenster, Tabs und Panes oder das Fail-open-Verhalten zu gefährden. Dieses
Review wurde vor einer späteren Zusammenführung mit `main` erstellt, um:

1. die tatsächlichen Unterschiede zu `main` zu prüfen;
2. Behauptungen der Architekturdokumentation mit dem Code abzugleichen;
3. Regressionen und unnötige NVDA-weite Eingriffe zu finden;
4. verbleibende Arbeit nach Risiko zu ordnen.

Der Bericht bewertet Quellcode, Tests und dokumentierte Praxisergebnisse. Er
ist keine Stabilitätsfreigabe und kein Nachweis, dass jede Kombination aus
NVDA, Windows Terminal, Neovim, SSH, Plugins und Braillehardware geprüft wurde.

## Vergleichsbasis und Umfang

Ausgangsbasis des Reviews:

- `main`: `60569a648d363c1a9acc2872b3c81a148ddb6584`
- Featurebranch: `888522c7dc83b9356e9f8596efe22ff8bf9397f9`
- Unterschied zu diesem Zeitpunkt: 16 Commits, 67 geänderte Dateien,
  7.916 Einfügungen und 4.836 Löschungen

Während des Reviews wurden die unter „Direkt behobene Befunde“ beschriebenen
Korrekturen für Dev-Build 13 in denselben Featurebranch aufgenommen. Die oben
genannten Commit-IDs bleiben als reproduzierbare Ausgangsbasis erhalten; die
Gesamtbewertung und die Liste offener Punkte beschreiben den korrigierten
Dev-13-Stand.

Als NVDA-Referenz diente vorrangig der lokale NVDA-Quellstand unter
`/tmp/nvda-source-2026.1.1`. Geprüft wurden insbesondere NVDAs
Entwicklerdokumentation, `inputCore.decide_executeGesture`, die
Extension-Point-Implementierung, AppModule-Beispiele, Windows-Wrapper und die
Verwendung des Gesture-Deciders im NVDA-Remote-Code. Zusätzlich wurden die
Projektquellen, ADRs, Pakettests und die gebauten Artefakte untersucht.

## Kurzfassung

Der Featurebranch ist gegenüber `main` ein deutlicher architektonischer
Fortschritt:

- Windows-Terminal-Ereignisse, `nextHandler`, Overlayauswahl und frei
  belegbare Terminalbefehle gehören nun dem AppModule.
- Eigene `ctypes`-/DLL-Bindings wurden durch vorhandene NVDA-Wrapper ersetzt.
- F12 prüft die konkrete AppModule-Instanz, das fokussierte TermControl und
  nach einem Threadwechsel erneut den Fokus.
- UI, Präsentation, Verbindungskoordination und Dienstregistrierung sind besser
  voneinander getrennt.
- Der direkt von NVDA geladene Python-Code folgt NVDAs Stil mit Tabs, LF,
  110 Zeichen und Ruff 0.14.5.
- Reload, mehrere AppModules, Fokusrennen, Fail-open und F12 sind breiter
  automatisiert geprüft als in `main`.

Das Review fand zunächst eine echte Braille-Regression: Das AppModule griff
auf einen unbeabsichtigten `controlTypes`-Reexport des Global Plugins zu. Nach
dessen Entfernung wurde die strukturierte Braille-Overlayklasse still nicht
mehr eingesetzt. Dev-Build 13 behebt dies durch einen direkten Import im
AppModule und Tests des tatsächlichen NVDA-Overlay-Hooks.

Die wesentliche verbleibende Architekturarbeit ist kleiner und weniger akut:
Das Global Plugin ist noch keine minimale Kompositionswurzel, sondern weiterhin
eine große Fachfassade. Das ist keine nachgewiesene Laufzeitregression und soll
nur schrittweise geändert werden. Außerdem fehlen noch Übersetzerkommentare;
Buildparallelität und CI-Abdeckung können verbessert werden.

**Empfehlung:** Die Richtung des Branches beibehalten. Vor einer
Zusammenführung die vollständige serielle Prüfung und einen erneuten
Windows-/NVDA-Praxistest durchführen. Die weitere Verkleinerung des Global
Plugins anschließend in kleinen, getrennt testbaren Schritten fortsetzen.

## Bewertung nach Qualitätsbereich

| Bereich | Gegenüber `main` | Stand am Reviewabschluss |
|---|---|---|
| Besitz von Anwendungsevents | deutlich besser | AppModule besitzt Einstieg, Overlayliste und `nextHandler` |
| Windows-API | deutlich besser | NVDA-Wrapper statt eigener DLL-Bindings |
| F12-Abschottung | deutlich besser | prozessweiter öffentlicher Decider, aber strikte AppModule-, Fokus- und Control-Prüfung |
| Fail-open | besser | Fehler und unklare Identitäten geben native Verarbeitung frei |
| Reload und Lebenszyklus | besser | identitätsgeprüfte Veröffentlichung und frühes Unpublish |
| Trennung der Zuständigkeiten | besser, noch unvollständig | mehrere Dienste extrahiert; Global Plugin bleibt große Fachfassade |
| Braille-Overlayauswahl | Regression behoben | echter Hook und Fehlerpfad automatisiert geprüft |
| NVDA-Python-Stil | deutlich besser | Ruff, EditorConfig und CI-Stilprüfung vorhanden |
| Lokalisierung | Kataloge konsistent | Übersetzerkommentare fehlen noch |
| Tests | breiter | vollständige lokale Suiten bestehen seriell |
| Paketierung | funktional | parallele Builds auf denselben Zielpfad bleiben unsicher |
| Sicherheit und Threading | kein neuer kritischer Befund | I/O bleibt außerhalb des NVDA-Hauptthreads; Gate fällt offen aus |

## Direkt behobene Befunde

### Strukturierte Braille-Overlayklasse wurde nicht eingesetzt

Vor der Korrektur verwendete
`appModules/windowsterminal.py` den Ausdruck
`NeovimAccessLink.controlTypes.Role.TERMINAL`. Das Global-Plugin-Modul
importierte `controlTypes` nach einer Stilbereinigung jedoch nicht mehr. Der
dadurch entstehende `AttributeError` wurde absichtlich vom Fail-open-Pfad
abgefangen. NVDA stürzte deshalb nicht ab und native Terminalausgabe blieb
verfügbar, aber `StructuredTerminalBrailleOverlay` wurde nicht in NVDAs
Overlayklassenliste eingefügt.

Der Fehler blieb in der bisherigen Suite unsichtbar, weil ein Test die
Overlayklasse direkt erzeugte, aber keiner den echten
`AppModule.chooseNVDAObjectOverlayClasses`-Hook aufrief.

Dev-Build 13 korrigiert den Besitz der Abhängigkeit:

- Das Windows-Terminal-AppModule importiert `controlTypes` direkt.
- Die Rollenprüfung verwendet `controlTypes.Role.TERMINAL`.
- Ein Regressionstest ruft den echten Hook mit einem passenden und einem
  unpassenden Control auf.
- Ein weiterer Test erzwingt einen Identitätsfehler und bestätigt: keine
  Overlayeinfügung, Gate fail-open, Diagnose vorhanden, keine Ausnahme nach
  außen.

Damit ist die konkret gefundene Regression automatisiert behoben. Eine echte
Braillezeile stand für dieses Review nicht zur Verfügung; Hardware-, Treiber-
und Routingverhalten bleiben daher praktisch offen.

### Technischer Umfang des F12-Deciders war zu absolut beschrieben

F12 ist kein NVDA-Skript und kein roher globaler Tastatur-Hook. Der verwendete
`inputCore.decide_executeGesture`-Extension-Point wird von NVDA technisch aber
prozessweit aufgerufen, sobald der Callback registriert ist.

Die Dokumentation beschreibt nun präzise:

- Das Windows-Terminal-AppModule besitzt Registrierung und Abmeldung.
- Der Callback existiert nur, solange mindestens eine solche AppModule-Instanz
  lebt.
- Andere Tasten kehren ohne Fokusabfrage sofort zurück.
- F12 wird nur bei exakt passender AppModule-Instanz und TermControl-Identität
  ausgewertet.
- Vor der Zuordnung wird derselbe Fokus auf NVDAs Hauptthread erneut geprüft.
- Die Originalgeste läuft unverändert weiter.

Diese Einordnung unterscheidet den öffentlichen NVDA-Extension-Point klar von
einem selbst installierten systemweiten Tastatur-Hook.

### Kleine Konventionsbereinigungen

- Die dateiweite Ruff-Ausnahme für `E402` wurde durch einzelne, begründete
  Ausnahmen an den tatsächlich späten Imports ersetzt.
- `AppModule.terminate` erwartet beim Abmelden des Deciders nicht länger einen
  von NVDAs `HandlerRegistrar.unregister` nicht verwendeten `LookupError`.
- Plan, ADRs und Changelog unterscheiden den ursprünglichen Befund vom
  korrigierten Dev-13-Stand.

## Verbleibende Befunde

### 1. Mittel: Die Minimalrolle des Global Plugins ist noch nicht erreicht

ADR-0004 beschreibt als Ziel ein kleines Global Plugin für wirklich globale
Registrierung und Lebensdauer. Der Branch nähert sich diesem Ziel, erfüllt es
aber noch nicht vollständig.

Messbare Veränderung der Ausgangsbasis:

- `GlobalPlugin`: 3.961 auf 3.556 Zeilen
- Methoden in `GlobalPlugin`: 154 auf 147
- neue Bausteine: `NvdaUiManager`, `NvdaPresentation`,
  `ConnectionCoordinator` und `ServiceRegistrar`

Das Global Plugin koordiniert weiterhin Claim-Inventar, Sitzungsauflösung,
Verbindungsdialoge, Instanzwechsel, Netzwerkereignisse, Lifecycle-Sweeps,
Zwischenablage und Teile der Fokuslogik. `ServiceRegistrar` veröffentlicht
noch die konkrete Plugininstanz; das AppModule verwendet mehrere private
Methoden und Attribute dieser Klasse.

Das ist eine Wartbarkeitsgrenze, kein aktuell nachgewiesener Funktionsfehler.
Ein großer Umbau wäre riskanter als der jetzige Zustand.

**Empfehlung:** Eine kleine benannte Dienstfassade oder ein `Protocol` für das
AppModule definieren und danach jeweils einen fachlichen Ablauf extrahieren.
Mehrfenster-, Tab-, Pane-, Reload- und Fail-open-Tests müssen nach jedem Schritt
bestehen. Bis zur Umsetzung muss die Dokumentation die Minimalrolle als Ziel,
nicht als bereits abgeschlossenen Zustand bezeichnen.

### 2. Mittel: NVDA-Übersetzerkommentare fehlen

POT und deutsche PO-Datei sind synchron, und die deutschen Formulare wurden
praktisch angezeigt. Im NVDA-seitigen Quellcode fehlen jedoch die bei NVDA
üblichen `# Translators:`-Kommentare vor Meldungen, Befehlsbeschreibungen und
komplexen UI-Texten.

Dies ist überwiegend geerbter Bestand und keine Laufzeitregression.

**Empfehlung:** Zuerst neue oder verschobene Texte kommentieren, danach den
Bestand mit inhaltlich hilfreichen Kommentaren ergänzen. Keine bedeutungslosen
Standardkommentare erzeugen. Anschließend gettext-, Paket- und
Dokumentationstests wiederholen.

### 3. Niedrig: Parallele Built-Add-on-Tests verwenden denselben Zielpfad

Zwei gleichzeitig gestartete Add-on-Suiten können dasselbe Archiv mit
`ZipFile(..., "w")` beschreiben. Im Review entstanden dadurch CRC- und
`BadZipFile`-Fehler; die serielle Wiederholung bestand vollständig. Der
Buildpfad ist bereits in `main` so aufgebaut und daher keine Regression dieses
Branches.

**Empfehlung:** Zunächst keine Add-on-Suiten parallel im selben Arbeitsbaum
starten. Später in eine eindeutige temporäre Datei bauen und atomar ersetzen
oder pro Testlauf ein separates Artefakt verwenden.

### 4. Niedrig: CI prüft derzeit nur NVDA-Python-Stil

Der neue Workflow ist eng berechtigt, pinnt Abhängigkeiten und prüft Ruff
0.14.5. Protokoll-, Bridge-, Add-on-, gettext-, Dokumentations- und
Neovim-Tests laufen jedoch nicht als GitHub-Merge-Checks.

**Empfehlung:** Suiten schrittweise in CI aufnehmen. Built-Add-on-Tests müssen
seriell oder mit getrennten Buildpfaden laufen.

### 5. Niedrig, aus `main` geerbt: `vim.region` ist in Neovim 0.12 veraltet

Die Neovim-0.12.3-Suite besteht, meldet aber für
`neovim-plugin/lua/nvim_nvda/state.lua` eine Deprecation-Warnung. Vor einer
künftigen Kompatibilitätsanhebung sollte eine öffentliche Ersatz-API geprüft
werden. Eine ungeprüfte Änderung gehört nicht in diesen Architekturbranch.

### 6. Niedrig: Sehr spät gesetzte Insert-F12-Belegungen sind ein Randfall

Das Neovim-Plugin prüft bei `setup()`, ob Insert-F12 bereits belegt ist, und
erhält vorhandene Benutzermappings. Eine erst danach dynamisch gesetzte
Belegung, etwa durch ungewöhnliches Lazy-Loading, ist nicht abgedeckt. Vor
einer Änderung muss ein echter Neovim-Test das Zusammenspiel von `vim.on_key`
und dem späteren Mapping klären.

## Positive Detailbefunde

### Ereignisbesitz und Fail-open

Das AppModule ruft `nextHandler` selbst auf. Beim Fokuswechsel bereitet der
gemeinsame Dienst eine unveränderliche Entscheidung vor, das AppModule führt
NVDAs native Verarbeitung genau einmal aus, und der Dienst schließt die
strukturierte Behandlung nur bei weiterhin passender Generation und Identität
ab. Fehler und mehrdeutige Terminalidentitäten geben native Verarbeitung frei.

Der veröffentlichte Dienst wird beim Beenden früh aus dem Registrar entfernt.
Instanz und Token verhindern, dass ein verspätetes `terminate` einer alten
Instanz einen neu veröffentlichten Dienst entfernt. Danach werden Gate,
Clients, geplante Aufrufe, UI und Caches kontrolliert abgebaut.

### Threading und Latenz

Im Diff wurde kein neuer blockierender Netzwerkpfad auf NVDAs Hauptthread
gefunden. Lokale und entfernte Sitzungssuche, Claim-Wartezeiten sowie
Komponenteninstallation laufen in Worker-Threads. Ergebnisse, Dialoge,
Sprache und Brailleaktualisierung kehren über `queueHandler` oder
`wx.CallAfter` auf die passenden UI-Pfade zurück.

### NVDA-API und Python-Stil

Fenster- und Prozessprüfung verwenden `winUser`, `winBindings` und
`winKernel`. Fehler liefern einen unklaren Zustand und lösen keine destruktive
Bereinigung aus. Handle-Cleanup ist ausnahmegesichert und getestet.

Die NVDA-Stilzone ist auf `nvda-addon/addon/**/*.py` begrenzt. Core, Bridge,
Protokoll, Tests und Werkzeuge behalten ihren jeweils konsistenten Stil. Damit
wird NVDAs Tab-Konvention nicht unnötig auf fremde Komponenten übertragen.

### Sicherheit

Im Branch-Diff wurden keine realen Zugangsdaten oder produktiven Hostnamen
gefunden. Passwörter werden nicht gespeichert. Sitzungskennung, Nonce,
Sequenznummern, Request-IDs, Größenlimits und Fokusidentität bleiben validiert.
Die Extraktionen weichen diese Grenzen nicht auf.

## Prüfnachweise am Abschlussstand

| Prüfung | Ergebnis |
|---|---|
| `git diff --check` | bestanden |
| Ruff 0.14.5 `check` | bestanden |
| Ruff 0.14.5 `format --check` | bestanden |
| Protokolltests | 42 Tests, bestanden |
| Bridge-Tests | 31 Tests, bestanden |
| Add-on- und Pakettests, seriell | 316 Tests, bestanden |
| gettext-Katalogprüfung | bestanden |
| deutsche und englische HTML-Dokumentation | 6 Dateien gebaut |
| Neovim-Plugin mit 0.10.1 | bestanden |
| Neovim-Plugin mit 0.12.3 | bestanden; `vim.region`-Warnung |
| Dev-13-Archiv mit `unzip -t` | bestanden |

Beim Review erzeugtes Dev-Artefakt:

```text
NeovimAccessLink-0.94.2-dev.13+feature.global-plugin-slimming.888522c7.nvda-addon
SHA-256: 9f94446b8eeb0f7bba3d6fc45b60c5f7ea71660105f302f0f3e1971f8959a2d1
```

Der Commit-Suffix bezeichnet den Branch-HEAD der Ausgangsbasis. Die
Dev-13-Datei enthält zusätzlich die während dieses Reviews vorbereiteten,
damals noch nicht committeden Korrekturen. Nach einem späteren Commit muss ein
neues Artefakt mit dessen eigener Buildkennung erzeugt werden.

## Praktische Nachweise und Grenzen

Im Entwicklungsverlauf wurden lokale und entfernte Verbindungen gemischt in
mehreren Windows-Terminal-Fenstern, Tabs und horizontalen sowie vertikalen
Panes praktisch verwendet. Fokuswechsel, F12, frei belegbare Befehle und die
deutsche Oberfläche wurden ohne gemeldeten Fehler geprüft.

Die Dev-13-Korrekturen wurden in diesem Review automatisiert und durch den
gebauten Paketinhalt geprüft, aber noch nicht erneut unter Windows/NVDA
praktisch abgenommen. Eine Braillezeile stand nicht zur Verfügung.
Automatisierte Mocks ersetzen außerdem keine Langzeitprüfung mit realem UIA,
SSH und Benutzerkonfigurationen.

## Handlungsempfehlung und Reihenfolge

### Vor einer Zusammenführung mit `main`

1. Dev-Build 13 praktisch unter Windows Terminal und NVDA prüfen,
   einschließlich F12, Fokuswechsel, mehreren Tabs/Panes und nativer Ausgabe
   außerhalb der gebundenen Neovim-Controls.
2. Wenn Hardware verfügbar ist, Braille-Overlay und Routing praktisch prüfen;
   fehlende Hardware allein blockiert die übrige Architekturprüfung nicht,
   muss aber als Grenze dokumentiert bleiben.
3. Nach dem Commit ein neues eindeutig gekennzeichnetes Paket bauen und die
   seriellen Suiten, gettext, Dokumentation und Archivprüfung wiederholen.
4. Keine weitere große Extraktion in denselben Abnahmeschritt aufnehmen.

### Danach in getrennten Folgeschritten

1. neutrale AppModule-Dienstfassade statt konkreter GlobalPlugin-Instanz;
2. verbleibende Fachkoordination schrittweise extrahieren;
3. Übersetzerkommentare ergänzen;
4. atomare beziehungsweise testlaufbezogene Paketbuilds;
5. vollständige Suiten in CI;
6. `vim.region` und dynamische F12-Mappings separat untersuchen.

## Schlussfolgerung

`feature/global-plugin-slimming` folgt NVDAs Add-on-Grenzen deutlich besser
als der verglichene `main`-Stand. Das AppModule besitzt nun
anwendungsspezifische Ereignisse und Befehle, der globale Anteil verwendet
öffentliche NVDA-Schnittstellen enger, und Zuständigkeiten sind nachvollziehbar
getrennt. Die während des Reviews gefundene Braille-Regression ist in
Dev-Build 13 korrigiert und durch den tatsächlichen Overlay-Hook abgesichert.

Die Verschlankung ist noch nicht vollständig: Das Global Plugin bleibt eine
große Fachfassade. Dieser Rest rechtfertigt jedoch keinen riskanten Komplettumbau
vor der Zusammenführung. Mit einer erneuten praktischen Abnahme und kleinen,
einzeln testbaren Folgeänderungen ist der Branch eine tragfähige Grundlage für
ein schmaleres und konventionsnäheres NVDA-Add-on.
