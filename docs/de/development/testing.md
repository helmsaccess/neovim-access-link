# Teststrategie

Die Tests trennen Protokoll, Bridge, Neovim-Plugin und NVDA-Integration. Python-
Kernlogik läuft ohne NVDA; Lua wird mit einem echten `nvim --headless` geprüft.
TUI-, Socket- und SSH-Tests dürfen auf einem isolierten Rocky-Linux-Testkonto
laufen, ohne bestehende tmux- oder Neovim-Sitzungen zu berühren.

Die Mehrfachsitzungstests decken gleiche Profile und Konten, identische
Arbeitsverzeichnisse, optionale Namen, Startzeit-/Nummern-Fallbacks,
„bereits verbunden“-Kennzeichnung und das sichere Ersetzen einer Zuordnung im
selben Terminal ab. Die Terminalunterdrückung umfasst Text-, UIA-, Live-Region-,
Namens-, Wert- und Beschreibungsänderungen und bleibt bei fremden Tabs fail-open.
Ein eigener Regressionstest verzögert die Reaktivierung eines gemerkten Tabs
bis zur stabilen UIA-Fokussierung. Das Tippecho prüft überlappende, von Neovim
zusammengefasste UTF-8-Diffs und darf bereits verarbeitete Präfixe nicht
wiederholen.

## Automatisierte Python-Tests

Vom Repository-Wurzelverzeichnis:

```bash
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
python3 -m unittest discover -s protocol/python/tests -v
python3 -m unittest discover -s bridge/python/tests -v
python3 -m unittest discover -s nvda-addon/tests -v
```

Die Protokolltests prüfen v2-Pflichtfelder, Größenlimits, UTF-8, Framing,
Sequenzierung, Resync, den SSH-stdio-Marker sowie den streng auf
`127.0.0.1` begrenzten lokalen Client. Protokoll v1 wird ausdrücklich
abgewiesen. Die Bridge-Tests prüfen die Registry v3, Neovim-RPC, semantische
Ereignisse, Steuerbefehle und Braille-Routing. Alte TCP-Listener, Tokens und
Kompatibilitätstests sind absichtlich entfernt.

Die Add-on-/Core-Tests decken unter anderem Speech, Braille, Visual-Modi,
Navigation, Bearbeitung, Completion, Menüs, Diagnostics, Rechtschreibung,
Einrückung, Dateimanager, Terminalmodus, Profile, parallele Verbindungen,
Sitzungswahl, SSH- und lokale Plugininstallation, Passwort-Askpass,
Diagnoseredaktion und das
extrahierte Add-on-Paket ab.

Die Einstellungstests prüfen den registrierten `config.conf`-Abschnitt,
Validierung und einmalige Migration der bisherigen JSON-Datei. Ein simulierter
`post_configProfileSwitch` muss Rückmeldungen und künftige Verbindungswerte neu
laden, darf aber eine bereits laufende Verbindung nicht stoppen. Quell- und
UI-Tests schließen eine eigene Profilwahl sowie Aufrufe von
`manualActivateProfile` aus.

Die Fokus- und Mehrverbindungstests modellieren außerdem zwei Windows-Terminal-
Tabs mit identischem Prozess und Fensterhandle, aber verschiedenen stabilen
UIA-Runtime-IDs. Geprüft werden Zustimmung, Ablehnung, Tabwechsel, veraltete
Zuordnungen und getrennte Transporttypen für zukünftiges lokales Windows-Neovim.
Die Paket- und Strukturtests prüfen, dass NVDA die Anwendung über das AppModule
`windowsterminal` begrenzt. Die Identitätstests innerhalb dieses AppModules
verlangen eine freigegebene UIA-Klasse und eine nichtleere Runtime-ID. PuTTY,
unbekannte oder nur ähnlich benannte UIA-Controls und selbst künstlich gebundene
Fremd-Frontends müssen vollständig fail-open bleiben. Eine Richtlinie darf
keinen nicht implementierten Adapter allein per Konfiguration aktivieren.
Das Paket muss `appModules/windowsterminal.py` enthalten. Nur dieses AppModule
darf Fokusereignisse, Overlays und Eingabeskripte bereitstellen; die globale
Dienstklasse darf keine `event_*`-, `script_*`- oder
`chooseNVDAObjectOverlayClasses`-Hooks besitzen und keinen globalen Fokus
abfragen. `event_appModule_loseFocus` muss Fokus und Unterdrückung löschen,
darf aber ein inzwischen fokussiertes zweites Windows-Terminal-AppModule nicht
durch ein verspätetes Fokusverlustereignis des ersten Fensters abwählen.
Die F12-Tests prüfen zusätzlich, dass bei identischen Sitzungsmerkmalen nur die
jüngste frische Registry-Markierung verbunden und eine alte oder fehlende
Markierung abgewiesen wird. Der vollständige Gestenpfad prüft außerdem, dass
NVDAs Windows-Terminal-AppModule die ungebundene F12-Geste nur bei aktivierter
Unterstützung über `decide_executeGesture` beobachtet, den ursprünglichen
physischen Tastendruck normal zum Betriebssystem durchlaufen lässt und die
Claim-Auswertung getrennt einreiht. Bei deaktivierter Unterstützung darf kein
Add-on-Dialog oder Scan entstehen. Neovim muss den unveränderten `typed`-Wert
erkennen, den Registry-Schreibzugriff aus `vim.on_key` heraus planen und darf
keinen sichtbaren TUI-Hinweis erzeugen. Wiederholtes F12 verwendet denselben
Bridge-Transport. Bei einem ungebundenen Tab muss
die einzige gegenüber der Aktivierungsinventur erhöhte Claim-Sequenz über
lokale Registry und alle automatisch erreichbaren SSH-Profile gewählt werden.
Ein zurückgehaltener künstlicher `wx.CallLater` muss bis zur Ausführung stark
referenziert bleiben, genau einmal aufrufen und danach freigegeben werden.
Aktivierung, manuelle Verbindung und F12 müssen außerdem unmittelbar den vom
Windows-Terminal-AppModule gelieferten aktuellen Fokus verwenden, auch wenn
zuvor kein neues `gainFocus`-Ereignis eingetroffen ist.
Zwei lokale
Session-IDs müssen gleichzeitig an zwei verschiedene Terminalidentitäten
gebunden bleiben und parallel zu SSH laufen. Eine zeitlich noch junge lokale
Markierung von vor dem aktuellen Tastendruck darf keinen neuen Treffer
erzeugen. Die Aktivierung muss die Inventur außerhalb des Hauptthreads starten
und anschließend verständlich zur F12-Markierung auffordern; der explizite Dialogbefehl behält
seine Profilauswahl.

## Lua und echte Neovim-Integration

Alle Dateien unter `neovim-plugin/tests/*_spec.lua` werden mit dem unterstützten
Neovim ausgeführt. Die Tests modellieren und integrieren Completion,
Pluginadapter, Visual-Auswahl, Spell/Diagnostics, Dateimanager und die atomare
Session-Registry v3. TUI-Tests verwenden eine eigene temporäre Neovim-Instanz
und ein Pseudoterminal; sie hängen sich niemals an eine Sitzung des Anwenders.
Registry-Regressionen decken geordnetes Ende, SIGKILL, PID-/Endpoint-/Nonce-
Wiederverwendung, ausgeblendete Altschemata, passive und begrenzte Inventur,
Berechtigungsunsicherheit, begrenzte Dateianzahlen, UTF-8-sichere Namen,
nonce-eindeutige eigene Sockets und nicht-destruktive Fehlerpfade ab.
Reale RPC-Tests verlangen außerdem, dass die Nonce auf dem dauerhaften Kanal
vor `setup()` geprüft wird und ein Unterschied ohne Wiederverbindung endet.

Eine bereits installierte Pluginversion darf den Checkout nicht überdecken.
Deshalb wird bei den Spezifikationen `--cmd "set packpath="` verwendet; der
Dateimanager-Test ergänzt `$VIMRUNTIME` zum isolierten `packpath` und lädt das
seit Neovim 0.12 optionale Paket mit `packadd netrw`.

Der reproduzierbare Einstiegspunkt berücksichtigt beide Bedingungen:

```bash
tools/test_neovim_plugin.sh
```

## Buildprüfungen

```bash
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
git diff --check
```

Der Dokumentations-Build muss Quick Guide, Handbuch und
Entwicklerdokumentation jeweils auf Deutsch und Englisch erzeugen. Jede der
sechs HTML-Dateien muss genau eine H1, ein
eigenes Inhaltsverzeichnis, keine verbliebenen `.md`-Links und keine fehlenden
internen Sprungziele besitzen. Jede veröffentlichte Markdown-Datei unter
`docs/de/manual` und `docs/de/development` muss ausdrücklich einem der Builds
zugeordnet sein. Ignorierte private Arbeitsunterlagen dürfen nicht enthalten
sein.

Der Add-on-Test entpackt das tatsächlich erzeugte `.nvda-addon`, öffnet das
darin enthaltene `server-user.tar.gz`, vergleicht die Konfiguration beider
Paketseiten und installiert die Linux-Komponenten in ein temporäres Präfix.
Damit wird ausgeschlossen, dass ein Build nur auf nicht mitgelieferte
Repositorydateien verweist. Der
Dokumentationsbuild prüft, dass jede Anwender-Markdown-Datei ausdrücklich dem
Quick Guide oder Handbuch zugeordnet ist, jede Quelle mit H1 beginnt, genau
eine H1 je HTML-Datei entsteht und keine `.md`-Links zurückbleiben.

## Manuelle Plattformtests

Praktische End-to-End-Tests liefen unter Windows 11 25H2 mit NVDA 2026.1.1,
Windows Terminal 1.24.x und `OpenSSH_for_Windows_9.5p2` mit `LibreSSL 3.8.2`
gegen Rocky Linux 10.2, Python 3.12.13 und Neovim 0.10.1. Installation,
SSH-stdio, Aktivierung,
Modi, Navigation, Bearbeitung, Auswahl, Einrückung und Completion funktionierten
grundsätzlich. Der Stand eignet sich zur produktiven Erprobung, ist jedoch noch
nicht erschöpfend über Terminals, Sprachen, SSH-Varianten und Braillehardware
getestet.

Für manuelle Tests sind Voraussetzungen, exakte Befehle und Tasten, erwartete
und tatsächliche Ausgabe sowie Ergebnis festzuhalten. Passwörter, Editorinhalt
und andere vertrauliche Daten gehören nicht in Testartefakte oder Logs.

### Bestätigter lokaler und entfernter Mehrfachbetrieb

Voraussetzungen des Tests vom 13. Juli 2026 waren Windows 11 25H2, NVDA
2026.1.1, Windows Terminal, lokales Windows-Neovim sowie Rocky Linux 10.2 mit
Neovim 0.10.1. Geöffnet wurden zwei lokale Neovim-Instanzen in zwei Tabs und
eine entfernte Neovim-Instanz über SSH in einem weiteren Windows-Terminal-
Fenster; zusätzliche erfolgreiche Durchläufe verwendeten tmux und verschiedene
Linux-Konten.

Testschritte: Windows Terminal bereits vor der Add-on-Aktivierung fokussieren,
Aktivierungsgeste ausführen, Bereitschaft abwarten und im ersten Tab F12
drücken. Danach den zweiten lokalen Tab sowie das andere Windows-Terminal-
Fenster fokussieren und dort jeweils F12 verwenden. In jeder gebundenen Sitzung
Insert/Normal, Texteingabe und Navigation prüfen, zwischen Fenstern und Tabs
wechseln, den manuellen Verbindungsdialog aufrufen und das Aktivierungs-Toggle
aus- und wieder einschalten.

Erwartet wurden eindeutige Zuordnung ohne IDs oder Ports, strukturierte Ausgabe
nur aus der jeweils fokussierten Instanz, keine sichtbare F12-Meldung in
Neovim, keine Terminalfragmente, funktionierende lokale und SSH-Verbindungen
sowie Erhalt der sichtbaren SSH-/tmux-Sitzungen. Das tatsächliche Ergebnis
entsprach diesen Erwartungen; lokaler und entfernter Mehrfachbetrieb gelten für
dev.42 als praktisch bestätigt.

Ein zusätzlicher Versuch mit einer älteren Neovim-Version auf Rocky Linux 9
führte dagegen nicht zu einer funktionierenden aktuellen Integration. Die
genaue Versionsgrenze wurde nicht bestimmt; dieser Rückwärtskompatibilitätstest
ist derzeit nachrangig und begründet keine Unterstützungszusage.

### Mehrfachaktualisierung der Komponenten

Für die praktische Prüfung mindestens zwei gespeicherte Verbindungen verwenden,
die gefahrlos aktualisiert werden dürfen. Unter `NVDA-Menü → Werkzeuge` „Neovim
Access Link: Install or update components...“ öffnen. Direkt im Untermenü
`NVDA-Menü → Optionen` darf kein
zusätzlicher direkter Add-on-Einstellungsbefehl stehen. Erwartet werden eine
initial fokussierte, nicht markierte
Checkbox „Select all connections“, „This computer“ sowie eine vollständig unmarkierte und
als „Connections to update“ beschriftete Verbindungsliste sowie „OK“ und
„Abbrechen“. „OK“ ohne Auswahl muss im Dialog bleiben und zur Auswahl
auffordern. Danach einzelne Ziele sowie in einem zweiten Durchlauf „Select all
connections“ prüfen. NVDA muss jede Verbindung mit Name, Konto, Host, Port und
Anmeldeart lesen. Werden alle Ziele einzeln markiert, muss sich „Select all
connections“ automatisch aktivieren; beim Demarkieren eines Ziels wieder
deaktivieren. Während SSH arbeitet und während der Ergebnisdialog geöffnet ist,
muss NVDA bedienbar bleiben. Der Ergebnisdialog muss jedes ausgewählte Ziel
genau einmal unter „Successful“ oder „Failed“ nennen; ein abgebrochener
Passwortdialog darf andere ausgewählte OpenSSH-Ziele nicht verhindern. Wird
„This computer“ gewählt, muss die Ergebnisübersicht die lokale Installation
getrennt nennen. Nach jedem Ziel muss NVDA Name und Fortschritt sprechen; nach
dem letzten Ziel muss unabhängig vom sichtbaren Dialog immer die Anzahl
erfolgreicher und fehlgeschlagener Aktualisierungen gesprochen werden. Ein
absichtlich hängendes SSH-Ziel muss nach spätestens 60 Sekunden je Upload- oder
Installationsschritt als Fehler abgeschlossen werden.

### Lokale Windows-CLI

Dieser Pfad ist vor dem Merge praktisch zu prüfen:

1. Aktuellen Beta-Build installieren und NVDA neu starten.
2. Unter `NVDA-Menü → Werkzeuge → Neovim Access Link: Install or update
   components` ausschließlich „This computer“ markieren und aktualisieren.
3. Alle laufenden lokalen Neovim-Instanzen schließen, danach in Windows
   Terminal `nvim.exe` starten.
4. Den Aktivierungsbefehl ausführen, die Bereitschaftsmeldung abwarten, das
   lokale Neovim fokussieren und F12 drücken.
5. Erwartet werden Verbindungsbestätigung, Modusklang sowie strukturierte
   Ausgabe bei Insert-, Normal- und Visual-Navigation. Es darf kein SSH-Prozess
   oder manueller Port nötig sein.
6. Zusätzlich einen zweiten Windows-Terminal-Tab mit SSH-Neovim verbinden und
   zwischen beiden Tabs wechseln. Lokale und entfernte Inhalte dürfen sich
   weder mischen noch native Terminalfragmente erzeugen.
7. Parallel mindestens zwei gespeicherte OpenSSH-Ziele erreichbar halten. Ein
   noch ungebundener Tab muss per F12 sowohl eine lokale als auch jede der
   entfernten Sitzungen finden können, unabhängig von Reihenfolge oder
   Einstellungsposition.
8. F12 einmal vor Abschluss der Erfassung drücken. Der physische Tastendruck
   darf Neovim bereits markieren, aber NVDA darf diesen Claim ohne fertige
   Baseline nicht zur Verbindung auswerten und muss zum Warten und erneuten
   Drücken auffordern. Nach der Bereitschaftsmeldung muss der zweite Versuch
   gelingen.
9. Ein Passwortprofil ohne bereits für diese NVDA-Laufzeit eingegebenes
   Passwort darf keinen Dialog aus dem Hintergrund öffnen. Es muss weiterhin
   über den manuellen Verbindungsdialog erreichbar sein.
10. Bei bereits aktiver Unterstützung in einen noch ungebundenen zweiten Tab
    wechseln und den Aktivierungsbefehl erneut ausführen. Bestehende lokale
    und SSH-Verbindungen müssen weiterlaufen; NVDA muss stattdessen zum
    Drücken von F12 auffordern. Im gebundenen Tab schaltet der Befehl die
    Unterstützung weiterhin aus.
11. Ein Diagnosebericht darf beim Start keinen `configError` für
    `nvdaConfig` und keine erneute `legacyConfigMigrated`-Meldung enthalten.

Eigene `NVIM_APPNAME`-Datenverzeichnisse, portable Layouts und GUI-Neovim sind
in dieser ersten Fassung ausdrücklich außerhalb des Testumfangs.

### Verpflichtende Isolationsprüfungen für Windows Terminal

Vollständige Wirkungslosigkeit in ungebundenen Windows-Terminal-Steuerelementen
ist ein offener Prüfbereich und noch keine belegte Garantie. Eine spätere
Abschottung braucht soweit möglich automatisierte Regressionstests sowie
praktische Negativtests für alle folgenden Fälle:

1. Ungebundene PowerShell-, Eingabeaufforderungs- und WSL-Panes behalten bei
   aktivierter Add-on-Unterstützung ihr natives Fokus-, Text-, Eingabe-,
   Sprach-, LiveText- und Brailleverhalten.
2. F12 in einer ungebundenen Shell startet weder Suche noch Ansage, Bindung oder
   Dialog, sofern nicht exakt dieses Terminal-Steuerelement zuvor ausdrücklich
   in einen Zuordnungszustand versetzt wurde.
3. Ereignisse einer anderen verbundenen Neovim-Instanz bieten in einer
   unabhängigen Shell-Pane keine Wiederbindung an und führen keine aus.
4. Eine gemerkte Identität darf native Ausgabe nicht vor frischem
   strukturiertem Zustand unterdrücken. Das gilt insbesondere, wenn in der Pane
   inzwischen eine Shell statt Neovim sichtbar ist, der RPC-Kanal aber weiterlebt.
5. Getrennte Windows-Terminal-Prozesse, Fenster, Tabs und Split-Panes dürfen
   weder quergebunden werden noch Gestenbeobachter mehrfach registrieren.
6. Das Add-on-Overlay darf natives Braille- oder LiveText-Fallback in
   ungebundenen Steuerelementen nicht verändern.

Die Tests müssen fokussierte UIA-Klasse und Runtime-Identität festhalten, damit
Pane- und Tabverhalten nicht verwechselt werden. Jedes unklare Ergebnis gilt
als fail-open-Defekt und bleibt dokumentiert, bis es praktisch reproduziert
und korrigiert ist.

Praktischer Regressionstest am 14. Juli 2026: Build 0.89.3 wurde unter NVDA
2026.1.1 installiert, lokales CLI-Neovim in Windows Terminal neu gestartet und
nach der Bereitschaftsmeldung per F12 sowie über die manuelle lokale Auswahl
verbunden. Erwartet waren wiederholbar eine eindeutige Verbindung und keine
lautlosen Fehlversuche durch einen zu frühen Registry-Snapshot. Tatsächlich
arbeiteten beide Wege zuverlässig; Ergebnis: bestanden.

## Aktueller Nachweis

Die exakten Testzahlen werden nach jeder strukturellen Änderung aus den
tatsächlich ausgeführten Läufen in `current-status.md` übernommen. Zahlen
werden hier bewusst nicht dupliziert, damit veraltete Teststände nicht wie ein
aktueller Nachweis wirken.
