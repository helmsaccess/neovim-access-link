# Aktueller Status

Stand: 20. Juli 2026. Produktversion im Quellstand: 0.95.0.

Der Quellstand ist für Version 0.95.0 vorbereitet. Der zugehörige
GitHub-Veröffentlichungslink steht prominent in `README.md`. Die vom Projekt
festgelegte Reife bleibt zwischen Alpha und Beta. Diese Dokumentation leitet
aus Testumfang, Versionsnummer oder Funktionsmenge keine höhere
Stabilitätseinstufung ab.

Der Prüfansatz ist risikoorientiert und nach bestem Wissen, nicht vollständig.
Automatisierte Suiten und praktische Referenzabläufe können nicht jede
Kombination aus NVDA, Windows Terminal, Neovim, SSH, Plugins und Benutzerdaten
vorwegnehmen. Fehlerberichte werden nach Möglichkeit zeitnah reproduziert,
priorisiert und korrigiert; dieses Kapitel verspricht weder Fehlerfreiheit noch
feste Reaktionszeiten.

Dieses Kapitel ist eine Momentaufnahme. Die Entstehung einzelner Funktionen
steht im `changelog.md`; geplante Arbeit steht in `plan.md`. Alte
Featurebranch-Berichte und zwischenzeitliche Testbuilds sind keine Beschreibung
des aktuellen Produkts und werden hier deshalb nicht chronologisch wiederholt.

## Referenzumgebung

Der hauptsächliche praktische Pfad wurde mit dieser Umgebung geprüft:

- Windows 11 25H2, 64 Bit;
- NVDA 2026.1.1;
- Windows Terminal 1.24.x;
- `OpenSSH_for_Windows_9.5p2` mit LibreSSL 3.8.2 und Schlüsselanmeldung;
- Rocky Linux 10.2;
- Neovim 0.10.1 und Python 3.12.13 auf Linux.

Lokales `nvim.exe` unter Windows ist automatisiert mit Neovim 0.10.1 geprüft.
Die F12-Zuordnung, parallele lokale und SSH-Sitzungen sowie Oil wurden praktisch
auch mit Neovim 0.12.3 geprüft. Das macht 0.12.3 nicht zur alleinigen
Referenzversion; optionale neuere APIs bleiben durch Featuretests abgesichert.

Die vollständigen Plattformgrenzen stehen in `compatibility.md`.

## Implementierter Gesamtpfad

### Installation und Verbindungen

- Das `.nvda-addon` enthält das NVDA-Add-on, das lokale Neovim-Plugin und ein
  rootloses Linux-Benutzerpaket mit Plugin, Bridge, Protokoll und Installer.
- Der Komponenten-Dialog kann lokale und gespeicherte SSH-Ziele installieren,
  aktualisieren und entfernen. Zur Zielmaschine ist kein Laufzeitdownload
  erforderlich.
- Lokale Windows-Sitzungen verwenden einen dynamischen, ausschließlich an
  `127.0.0.1` gebundenen Neovim-RPC-Port.
- Entfernte Linux-Sitzungen verwenden Protokoll v2 über SSH-stdin/stdout und
  einen privaten Unix-RPC-Socket auf dem Ziel.
- Die dateibasierte Session-Registry entdeckt laufende Neovim-Instanzen. Sie
  ist nicht die Windows-Registry.
- Ein physischer F12-Druck ordnet die fokussierte Neovim-Sitzung dem konkreten
  Windows-Terminal-Control zu. Tabs, Panes und Fenster können getrennte lokale
  oder entfernte Verbindungen halten.
- Nonce, Sitzungskennung, Sequenznummern, Heartbeats, Resync und der erste
  gültige `fullState` begrenzen und authentifizieren den dauerhaften Pfad.
- Fokusverlust, Deaktivierung, Protokollfehler und Transportende geben native
  Terminalausgabe fail-open wieder frei.
- Das Windows-Terminal-AppModule und das strukturierte Braille-Overlay greifen
  über einen schmalen `TerminalIntegrationService` auf den gemeinsamen Dienst
  zu. Feste Befehlswerte und unveränderliche Fokus- und Claim-Ergebnisse
  verhindern private oder dynamische Aufrufe über die AppModule-Grenze.
- Ein eigener `SettingsService` besitzt Laden, Normalisierung, Speichern und
  NVDA-Profilwechsel. Präsentation und Werkzeugdialoge erhalten nur Snapshots
  oder schmale Operationen; der `NvdaUiManager` kennt keine Global-Plugin-
  Instanz.
- Ein `TerminalFocusService` besitzt Terminalidentität, Fokusgeneration,
  AppModule-/Adapterkorrelation und den periodischen Lifecycle-Sweep. Unsichere
  UIA-Ergebnisse fallen offen aus; geschlossene, nicht fokussierte Controls
  werden erst nach zwei eindeutigen Negativprüfungen bereinigt.
- Der erste V2-4-Schnitt übergibt `SessionClaimService` die alleinige
  Zuständigkeit für einmalige F12-Autorisierung, Claim-Generationen und Claim-
  Inventarzustand. Lokale und SSH-Inventar- und Sitzungslisten-Worker,
  Discovery-Generation sowie Kandidatenauswertung laufen hinter diesem Dienst.
  Er entscheidet außerdem unveränderlich zwischen lokaler, entfernter und
  automatischer Auflösung sowie den Ergebnissen einer Sitzungssuche. Aus dem
  gemeinsamen Instanzzustand plant er jetzt auch Wiederverwendung oder Start
  lokaler und entfernter Sitzungen einschließlich einer gegebenenfalls zu
  ersetzenden Instanz. Einen aktuellen Wiederverwendungsplan wendet er auf die
  Instanzbindungen an und liefert verdrängte Terminalidentitäten zur
  NVDA-seitigen Fokusbereinigung zurück. Start, Bindung und Runtime-Auswahl
  neuer Instanzen bilden dort ebenfalls einen Übergang; Rückrollen und das
  Stilllegen einer ersetzten Instanz beenden Clients asynchron. NVDA-Meldungen,
  Dialoge, Clientkonstruktion und fokusbezogene Nebenwirkungen behalten ihre
  bisherigen Hauptthreadgrenzen.

### Editorausgabe

Der semantische Pfad deckt unter anderem ab:

- Normal-, Insert-, Replace-, Visual-, Kommandozeilen- und Terminalmodi;
- zeichen-, wort- und zeilenweise Navigation sowie Datei- und Zeilengrenzen;
- Eingabe, Löschen, Ersetzen, Auswahl und Suchtreffer;
- eingebaute Completion, Signaturhilfe, Diagnosen, Folds und Meldungen;
- typisierte Kommandozeile und korrelierte Rückkehrmeldung eines Ex-Befehls;
- konfigurierbare Fokusausgabe: keine Ansage, aktuelle Zeile oder Kontext mit
  Modus und gespeichertem Verbindungsnamen;
- getrennte Sprach-, Klang- und dauerhafte Brailleplanung.

Die Funktionstabelle und bekannte Unterschiede stehen in
`accessibility.md`.

### Terminal- und Dateimanagerpfade

- Terminal-Insert und `terminalNormal` sind eigene Zustände. Direkte
  Terminaleingabe aktiviert Passthrough; ein frei belegbarer NVDA-Befehl kann
  über den festen `stopinsert`-Pfad in Terminal-Normal zurückkehren.
- Kommandozeilentext, Rückkehrmodus, Meldungen, Bufferwechsel sowie
  Fenster-/Tabwechsel werden strukturiert korreliert, nicht aus sichtbarem
  Terminaltext geraten.
- Oil, netrw, mini.files, nvim-tree und Neo-tree besitzen normalisierte
  Dateimanagereinträge und automatisierte Workflowabdeckung. Navigation,
  bearbeitete Namen, Grenzklänge und Bestätigungsabläufe wurden praktisch
  bislang nur für Oil unter Windows/NVDA geprüft.
- Oil bildet eine brauchbare praktische Grundlage. Für die anderen Manager ist
  die vorhandene automatisierte oder isolierte Abdeckung keine praktische
  Freigabeempfehlung.

### Zwischenablage

Vier frei belegbare Befehle des Windows-Terminal-AppModules können:

- die aktive Visual-Auswahl nach Windows kopieren;
- Neovims Register 0 nach Windows kopieren;
- Windows-Zwischenablagentext über `nvim_paste` einfügen;
- oder Register 0 ersetzen und das unbenannte Register darauf zeigen lassen.

Lokal und über SSH gilt derselbe korrelierte, größenbegrenzte Pfad. Es gibt
keine automatische Synchronisation und keine automatische Wiederholung. Diese
und die übrigen frei belegbaren Terminalbefehle erscheinen im
Tastenbefehldialog zunächst, wenn Windows Terminal vor dessen Öffnen fokussiert
war; in fremden Anwendungen werden sie nicht aufgelöst. Sobald die AppModule-
Klasse geladen ist, kann NVDA eine gespeicherte Zuordnung während dieses Laufs
andernorts weiter auflisten, ohne ihre Ausführung global zu machen.

### Lokalisierung und Dokumentation

- Englisch ist die Quellsprache der Projektoberfläche; ein vollständiger
  deutscher NVDA-gettext-Katalog wird mitgebaut.
- Manifest, Einstellungen, Werkzeugdialoge, Meldungen und Speech-Plannertexte
  durchlaufen die Übersetzungsprüfung.
- Quick Guide, Handbuch und Entwicklerdokumentation werden jeweils als
  deutsches und englisches HTML erzeugt.

## Aktueller Prüfnachweis

Die gepflegten automatisierten Prüfungen umfassen:

- Lua-Spezifikationen und echte headless-Neovim-Läufe;
- Protokoll-, lokaler Client-, SSH-stdio- und Bridge-Tests;
- NVDA-unabhängige Zustands-, Sprach-, Braille- und Gate-Tests;
- Add-on-Integrations- und gebaute-Pakettests;
- Lokalisierungs-, Manifest-, Archiv- und Dokumentationsprüfungen.

Die Tests validieren unter anderem Begrenzungen, ungültiges UTF-8,
Sequenzlücken, Resync, späte Antworten, Fokuswechsel, parallele Instanzen,
Zwischenablagekorrelation, Terminalrückkehr und Dateimanagerworkflows.

Automatisierte Tests ersetzen keine Prüfung in NVDA, Windows Terminal, über
echtes SSH oder an Braillehardware. Die genaue Befehlsfolge und die praktische
Abnahmematrix stehen in `testing.md`.

## Praktisch bestätigte Nutzung

Ohne Anspruch auf eine vollständige Plattformmatrix wurden bestätigt:

- Installation und Aktualisierung lokaler und entfernter Komponenten;
- lokale und SSH-basierte F12-Zuordnung;
- parallele lokale und entfernte Sitzungen in mehreren Tabs, Panes und
  Windows-Terminal-Fenstern;
- Wechsel zwischen gemerkten Verbindungen ohne Übernahme durch fremde
  Shell-Controls;
- vorhandene SSH- und tmux-Sitzungen ohne deren Beendigung oder Umbau;
- Fokusansagen und Verbindungsnamen lokal und entfernt;
- alle vier Zwischenablagebefehle lokal und über SSH;
- Terminalmodus, Kommandozeilenrückkehr und Bufferwechsel;
- Oil-Navigation, Umbenennungsvorschau, Klänge und Bestätigungsabläufe.

## Bekannte Grenzen

- Windows Terminal ist das einzige freigegebene Terminalfrontend. Andere
  Terminals und Neovim-GUIs besitzen keine geprüften Fokus-, Identitäts- und
  Fail-open-Adapter.
- Unterstützt wird das normale `%LOCALAPPDATA%\nvim-data`-Layout. Portable
  Installationen und `NVIM_APPNAME` sind nicht freigegeben.
- Eine ältere Neovim-Version auf Rocky Linux 9 verband sich mit einem aktuellen
  Stand nicht. Ursache und genaue Versionsgrenze sind nicht untersucht; daraus
  folgt keine Kompatibilitätszusage.
- Es wurde noch keine echte Braillezeile praktisch getestet. Automatisierte
  Brailleplanung und Routingprüfung können Hardware- und Treiberprobleme nicht
  ausschließen.
- Nur Oil ist als Dateimanager praktisch unter Windows/NVDA geprüft. netrw,
  mini.files, nvim-tree und Neo-tree benötigen schrittweise reale Abnahme.
- Repräsentative negative Isolationsfälle für Shells, Tabs, Panes, Fenster,
  Fokusverlust und geschlossene Controls benötigen weitere praktische Breite.
- Lange Laufzeiten, wiederholte Reconnects, sehr große Ereignislast und viele
  parallele Sitzungen benötigen weitere Stresstests.
- Sprachprofile, Windows-/NVDA-Versionen und reale SSH-Konfigurationen sind
  noch nicht breit genug für eine allgemeine Kompatibilitätszusage geprüft.

## Nächste Orientierung

- Architektur verstehen: `architecture.md`
- konkrete Grenzen prüfen: `compatibility.md`
- offene Arbeit priorisieren: `plan.md`
- Tests ausführen oder erweitern: `testing.md`
- Änderungen historisch nachvollziehen: `changelog.md`
