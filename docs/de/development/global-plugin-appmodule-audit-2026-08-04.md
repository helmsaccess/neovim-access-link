# Anhang C: Reaudit von GlobalPlugin, Windows-Terminal-AppModule und gemeinsamen Diensten

Erstellt: 4. August 2026

Geprüfter Stand: Branch `feature/lsp`, Commit
`e9c8abb122c0`

Frühere Vergleichsbasis: Abschlussaudit auf Commit
`b4195f3d900187f085275981d2ec1b0011a1952f`

Repository: Neovim Access Link

## Anlass und Fragestellung

Der Bericht prüft erneut, ob der globale NVDA-Teil nur wirklich prozessweite
Aufgaben enthält und ob anwendungsspezifische Verarbeitung weiterhin im
Windows-Terminal-AppModule liegt. Anlass ist das Wachstum durch LSP-,
Diagnose-, Braille-, Entwicklerkontext- und Bindungsfunktionen seit dem
früheren Abschlussaudit.

Die Prüfung unterscheidet bewusst drei Bereiche. Eine Zweiteilung nur in
„Global Plugin“ und „AppModule“ wäre fachlich falsch:

| Bereich | Soll-Zuständigkeit |
|---|---|
| `GlobalPlugin` als NVDA-Einstieg | einmalige Komposition, Veröffentlichung, globale Registrierungen und geordneter Abbau |
| Windows-Terminal-AppModule | Anwendungsevents, Overlayauswahl, konkreter Fokus, kontextbezogene Skripte und Gesten, physischer Tastenlebenszyklus und jeder `nextHandler` |
| gewöhnliche gemeinsame Dienste | Verbindungen, Authentifizierung, Gate, Editor-, Claim- und Fokuszustand, Protokoll, UI, Präsentationsplanung und Ausgabeabläufe mit Prozesslebensdauer |

Gemeinsame Verbindungen oder Editorzustände dürfen nicht in einzelne
AppModule-Instanzen verschoben werden. Das würde bei mehreren
Windows-Terminal-Prozessen, Tabs oder Panes doppelte Eigentümer, veraltete
Referenzen und Reload-Rennen erzeugen. „Nicht im AppModule“ bedeutet deshalb
nicht „muss als Methode auf `GlobalPlugin` stehen“.

## Kurzfassung

Das Ergebnis hat zwei klar zu trennende Seiten:

1. **Die NVDA-Zuständigkeitsgrenze ist weiterhin korrekt.** Im
   `GlobalPlugin` befinden sich keine Windows-Terminal-Ereigniseinstiege,
   keine Overlayauswahl, kein `nextHandler`, keine frei belegbaren
   NVDA-Skripte und keine Registrierung der prozessweit aufgerufenen
   Eingabebeobachter. Diese Teile liegen im Windows-Terminal-AppModule und
   fallen bei fehlendem, veraltetem oder fehlerhaftem Dienst offen auf NVDAs
   Standardverhalten zurück.
2. **Die Klasse `GlobalPlugin` ist nicht wörtlich minimal.** Sie umfasst 2.857
   Zeilen und 126 Methoden. Neben Konstruktion und Lebenszyklus enthält sie
   umfangreiche prozessweite Ablaufsteuerung für Verbindungen, Claims,
   Dialoge, Zwischenablage, Netzwerkereignisse, Präsentation und
   Brailleaktualisierung. Diese Logik gehört überwiegend nicht in das
   AppModule, könnte aber schrittweise in gewöhnliche, prozessweit besessene
   Controller oder Dienste wechseln.

Es wurde kein kritischer oder hoher Scope-Fehler gefunden. Der wichtigste
Befund ist eine mittlere Architektur- und Dokumentationsabweichung: Die
sicherheitsrelevante Trennung zum AppModule ist erhalten, die in ADR-0004
beschriebene ausschließlich aus Komposition und Lebenszyklus bestehende
Global-Plugin-Klasse ist dagegen noch Zielarchitektur und kein vollständig
erreichter Ist-Zustand.

## Untersuchungsumfang und Methode

Geprüft wurden insbesondere:

- die Global-Plugin-Klasse und die Laufzeit-, Registry-, Terminal-, Fokus-,
  Claim-, Editor-, Braille-, Präsentations-, UI- und Einstellungsdienste;
- das Windows-Terminal-AppModule;
- strukturelle und dynamische Tests des gebauten Add-ons;
- ADR-0004, Architektur, aktueller Status und die Anhänge A und B.

Die Prüfung kombinierte AST-basierte Größen- und Eigentümeranalyse,
Quelltextsuche nach NVDA-Hooks und Rückreferenzen, Inspektion tatsächlicher
Aufrufpfade sowie gezielte Tests des aus dem geprüften Arbeitsbaum gebauten
Add-ons.

## Quantitativer Stand

| Baustein | Physische Zeilen | Methoden | direkt in `__init__` gesetzte Felder |
|---|---:|---:|---:|
| gesamte Global-Plugin-Datei | 3.232 | – | – |
| Klasse `GlobalPlugin` | 2.857 | 126 | 15 |
| Windows-Terminal-`AppModule` | 1.076 | 58 | 13 |
| `TerminalIntegrationService` | 1.403 | 59, davon 47 nicht privat benannt | 28 |

Der frühere Abschlussaudit maß 2.499 Zeilen in der Global-Plugin-Datei, 112
GlobalPlugin-Methoden und 352 AppModule-Zeilen. Das Wachstum ist durch die
neuen Funktionen fachlich erklärbar, verlangt aber eine erneute Bewertung der
damaligen Entscheidung, weitere Extraktionen zu stoppen.

Die heutige GlobalPlugin-Klasse gliedert sich grob so:

| Zeilenbereich | Umfang | Inhalt |
|---|---:|---|
| 377–639 | etwa 263 Zeilen | Komposition, Start/Ende, Scheduler- und Callback-Grundlage |
| 641–2309 | etwa 1.669 Zeilen | Befehle, Claims, Discovery, Dialoge, Zwischenablage und temporäre Bindungen |
| 2311–2766 | etwa 456 Zeilen | Managed-Client-Ereignisse, Ergebniszuordnung, Fokus- und Netzwerkübergänge |
| 2768–3156 | etwa 389 Zeilen | Ereignislieferung, Diagnoseklänge, Sprache, Braille und Entwicklerkontexte |
| 3159–3232 | etwa 74 Zeilen | Einstellungen, Sitzungspasswörter und aktiver Clientabbau |

Rund 91 Prozent der Klassenzeilen liegen damit außerhalb des ersten
Kompositions-/Lebenszyklusblocks. Das ist kein Beleg für falschen
Anwendungsscope, aber ein klarer Beleg dafür, dass die Klasse wesentlich mehr
als eine minimale Kompositionswurzel ist.

## Bestätigte Zuständigkeitsgrenzen

### Anwendungsevents und native Weitergabe

Das Windows-Terminal-AppModule besitzt Overlayauswahl, Fokusgewinn und
-verlust sowie Ereignisse für Text, Zeichen, UIA-Benachrichtigungen,
Live-Region, Wert, Name und Beschreibung. Dort liegt auch jeder
`nextHandler`-Aufruf. Das Global-Plugin-Paket enthält keinen
AppModule-Ereigniseinstieg; unsicherer Zustand erlaubt native Verarbeitung.

### Skripte und konkrete Anwendungsgesten

Aktivierung, Brailleexploration, Completion-Dokumentation,
Zwischenablagebefehle, Verbindungsverwaltung, Diagnosebericht sowie gehaltene
Funktions- und Diagnosekontexte sind AppModule-Skripte. Methoden mit dem Präfix
`action_` im Global Plugin sind nicht als NVDA-Skript dekoriert und besitzen
keine globale Gestenzuordnung; sie sind feste Prozess-Callbacks des
`TerminalIntegrationService`.

### Prozessweit aufgerufene Eingabebeobachter

Die Registrierung von `inputCore.decide_executeGesture` und
`inputCore.decide_handleRawKey` gehört dem AppModule: Die erste Instanz
registriert, die letzte meldet symmetrisch ab, und jeder Pfad prüft die
konkrete fokussierte AppModule-Instanz. Nicht betroffene Gesten bleiben frei;
der Raw-Key-Pfad beobachtet nur den physischen Tastenlebenszyklus und fällt
auch bei Fehlern offen aus.

### Berechtigt prozessweite Eigentümer

| Eigentümer | Grund für Prozesslebensdauer |
|---|---|
| `ConnectionCoordinator` und Instanzmanager | gemeinsame lokale und SSH-Verbindungen sowie eindeutige Zuordnung mehrerer Controls |
| `SessionGate` | eine fail-open Suppressionsentscheidung für den aktiven authentifizierten Control-Kontext |
| `EditorSessionController` | getrennte Laufzeitzustände je Verbindung ohne Kopien im AppModule |
| `SessionClaimService` | Generationen, Inventar und einmalige F12-Autorisierung über mehrere Ziele |
| `TerminalFocusService` | Fokusgeneration, konkrete Control-Identität und Schutz vor verspäteten Ereignissen |
| `SettingsService` und `NvdaUiManager` | einmalige Profil-, Einstellungs- und Werkzeugregistrierung |
| `NvdaPresentation` und Sound-Caches | einmal geladene Audioressourcen und zentrale NVDA-Ausgabe |
| `AddonRuntime` | späte Veröffentlichung und feste, idempotente Abbaureihenfolge |

Diese Bausteine erben nicht von `GlobalPlugin`. Keiner der geprüften
ausgelagerten Dienste referenziert die Klasse oder hält eine breite
`_plugin`-/`_runtime`-Rückreferenz. Der `ServiceRegistrar` veröffentlicht nur
den `TerminalIntegrationService`; ein Identitätstoken schützt den Ersatz beim
Reload.

## Befunde

### M1 – Mittel: keine minimale Kompositionswurzel

Die Klasse implementiert weiterhin oder inzwischen wieder vollständige
Auswahl- und Verbindungsabläufe, konkrete Dialoge, Wiederherstellung
temporärer Bindungen, Zwischenablage- und Terminal-Control-Abläufe,
Netzwerkereignisverteilung, Diagnoseklänge, Tippecho, Brailleaktualisierung,
gehaltene Entwicklerkontexte und den Sitzungspasswortdialog.

Das ist kein AppModule-Scope-Fehler. Die Abläufe sind gemeinsam und benötigen
über Fokuswechsel und mehrere AppModule-Instanzen hinweg einen Besitzer. Sie
müssen aber nicht Methoden der von NVDA geladenen Unterklasse bleiben.

### M2 – Mittel bis niedrig: sauberer, aber breiter Dienstvertrag

Der `TerminalIntegrationService` besitzt keine GlobalPlugin-Rückreferenz; das
AppModule greift auf keine privaten Dienstfelder zu. Diese wichtigste
Vertragseigenschaft ist erfüllt. Der konkrete Dienst hat jedoch 47 öffentlich
benannte Methoden. Das AppModule verwendet 26 davon, das Braillemodul zehn;
weitere Methoden sind Ergebnis- und Lebenszyklusgrenzen. „Begrenzt“ beschreibt
damit zuverlässig Vertrauen und Besitz, nicht eine kleine API.

Verbraucherbezogene Ports könnten die erlaubte Oberfläche später klarer
machen. Eine sofortige Aufteilung allein wegen der Methodenzahl ist nicht
gerechtfertigt.

### N1 – Niedrig: private Paketexporte im AppModule

Das AppModule bezieht den veröffentlichten Dienst statt der Plugininstanz,
importiert aber auch private Konstanten aus dem Paket. Das ist kein Zugriff auf
veränderlichen Laufzeitzustand, schwächt jedoch die Aussage eines vollständig
ausdrücklichen öffentlichen Adaptervertrags. Ein kleines API-Modul oder eine
statisch geprüfte Symbol-Allowlist wäre klarer.

### N2 – Niedrig: großes, aber korrekt abgegrenztes AppModule

Auch das AppModule ist mit 1.076 Zeilen und 58 Methoden groß. Ereignisse,
Skripte, Gestenauflösung, physischer Tastenlebenszyklus und Fokusrevalidierung
gehören dorthin. Bei weiterem Wachstum können zustandslose Hilfen oder ein
AppModule-eigener Eingabecontroller ausgelagert werden; NVDA-Hooks,
`nextHandler`, Overlayauswahl und die letzte Fail-open-Entscheidung müssen
dort bleiben.

## Empfehlungen

### 1. Ist-Zustand und Zielarchitektur getrennt benennen

Bis zu einer weiteren Zerlegung soll die Dokumentation das Global Plugin als
„prozessweiten NVDA-Randcontroller und Kompositionswurzel“ beschreiben.
ADR-0004 bleibt die Zielentscheidung für eine minimale Wurzel. Diese
Präzisierung wurde zusammen mit diesem Bericht in Architektur, Status, Plan
und Teststrategie übernommen.

### 2. Nur in fachlichen Schnitten weiter zerlegen

Geeignete, getrennt prüfbare Kandidaten sind:

1. ein Verbindungs- und Claim-Workflow für Discovery, Auswahl, Dialoge,
   Verbindungsstart und temporäre Wiederherstellung;
2. eine NVDA-Ereignislieferung für Managed Events, Diagnoseklänge, Tippecho
   und Braille-Refresh;
3. eine Kontextpräsentationsgrenze für nummerierte Auswahl und gehaltene
   Entwicklertexte;
4. kleine benannte Adapter für Terminalidentität, Konfigurationsschema und
   öffentliche AppModule-Symbole;
5. verbraucherspezifische Ports für AppModule, Braille und interne Ergebnisse.

Jeder Schnitt muss Reload, mehrere AppModule-Instanzen, veraltete Callbacks,
Fokusrennen, Fail-open und die feste Abbaureihenfolge bewahren. Reine
Zeilenverschiebung oder ein starres LOC-Limit sind kein Qualitätsgewinn.

### 3. Vertragsgrenzen gezielt maschinell schützen

Sinnvolle Ergänzungen sind Quelltests gegen Anwendungshooks im Global Plugin,
eine Allowlist der AppModule-Paketexporte, verbraucherspezifische Test-Doubles
und die bestehende Sperre gegen GlobalPlugin-Rückreferenzen. Eine maximale
Methodenzahl wäre dagegen kein aussagekräftiger Architekturtest.

## Prüfnachweis

Die vorhandenen Pakettests prüfen unter anderem getrennte UI-Registrierung,
eindeutigen Fokus- und Claimbesitz, tokensichere Dienstveröffentlichung,
fehlertoleranten Abbau, AppModule-Besitz aller Ereignisse und Skripte,
Dienstzugriff ohne Plugininstanz, Fail-open, exakte F12-Fokusbindung,
symmetrische Observer-Registrierung und genau einmalige native Weitergabe.

Für diesen Audit liefen gegen das frisch gebaute Add-on:

- acht Architektur-, Registry-, Runtime- und Vertragsprüfungen: bestanden;
- sieben Observer-, AppModule-, Ereignis- und Fail-open-Prüfungen: bestanden.

Gesamt: **15 von 15 gezielten Tests bestanden**.

## Grenzen der Aussage

Der Audit bewertet Quellstruktur, Abhängigkeiten, das gebaute Paket und
simulierte NVDA-Verträge. Er ist kein neuer Windows-/NVDA-Praxistest und kein
Last-, Latenz- oder Braillehardwaretest. Die Scope-Trennung ist strukturell
stark abgesichert; die Empfehlung zur weiteren Verkleinerung ist eine
Wartbarkeits- und Dokumentationsfrage, kein Hinweis auf einen beobachteten
Laufzeitfehler.

## Schlussfolgerung

Alles, was zwingend zum Windows-Terminal-Anwendungskontext gehört, liegt
weiterhin im AppModule. Der globale Teil greift nicht über NVDA-Ereignisse,
`nextHandler`, Overlays oder globale Skripte in andere Anwendungen ein.

Bei strenger Lesart enthält die Klasse `GlobalPlugin` dennoch mehr als die
absolut benötigte Komposition und Lebensdauer. Dieser Rest darf nicht
pauschal in das AppModule verschoben werden. Bei konkretem Besitz- oder
Testnutzen soll er schrittweise in gewöhnliche, prozessweit besessene Dienste
wandern; damit nähert sich der Code der dokumentierten Zielarchitektur ohne
neuen Parallelpfad.
