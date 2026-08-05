# Add-on-Einstellungen

## Maßgebliche Quellverträge

Das NVDA-Konfigurationsschema und seine Standards stehen in
[`__init__.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/addon/globalPlugins/NeovimAccessLink/__init__.py).
[`settings_service.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/addon/globalPlugins/NeovimAccessLink/settings_service.py)
besitzt Normalisierung, Profilwechsel und Speicherung;
[`nvda_ui.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/addon/globalPlugins/NeovimAccessLink/nvda_ui.py)
besitzt die sichtbaren Controls. Paket- und Profiltests in
[`test_built_addon.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/tests/test_built_addon.py)
prüfen Schema, Defaults, UI-Werte und Speicherung. Diese Seite ist die
entwicklerseitige Lesereferenz, nicht eine zweite Schemaquelle.

## Speicherung und Profile

Die Kategorie „Neovim Access Link“ verwendet den Abschnitt
`config.conf["NeovimAccessLink"]` und damit NVDAs normale
Konfigurationsprofile. „Übernehmen“ oder „OK“ schreibt geänderte Werte in das
aktive Profil; nicht gesetzte Werte werden wie andere NVDA-Einstellungen
geerbt. Es gibt keinen separaten JSON-Einstellungsspeicher.

`SettingsService` lädt, normalisiert und speichert eine vollständige Kopie der
wirksamen Werte. Ungültige Typen oder Bereiche werden durch Standardwerte
ersetzt und ohne vertraulichen Inhalt diagnostiziert. Ein Profilwechsel lädt
Rückmeldung sofort neu. Verbindungsänderungen gelten für neue Verbindungen und
beenden keine bereits authentifizierte Editorsitzung.

## Oberfläche und Zuständigkeit

Der NVDA-Einstellungsdialog enthält fünf Registerkarten:

- „Allgemein“ für globale Rückmeldung, Sitzungsfokus und automatische
  Parameteransage;
- „Rückmeldung“ für einzelne Sprach- und Klangereignisse;
- „Navigation“ für Details nach normaler Navigation und Sprachexploration;
- „Braille“ für Exploration, Routingaktionen und flüchtige Ansichten;
- „Verbindungen“ für lokales Windows-Neovim und gespeicherte SSH-Ziele.

Das Add-on dupliziert keine geeignete NVDA-Einstellung. Tastaturecho kommt aus
„Tastatur“, Einrückung sowie Rechtschreibung und Grammatik aus
„Dokument-Formatierungen“, automatische Vorschlagsklänge aus
„Objekt-Darstellung“ und Übersetzung, Treiber sowie Cursorform aus „Braille“.

## Rückmeldung

Rückmeldungswerte verwenden `0 = Aus`, `1 = Sprache`, `2 = Töne` und
`3 = Sprache und Töne`. Der globale Wert begrenzt die einzelnen Aktionen.
`diagnosticLine` und `diagnosticPosition` erlauben nur Aus oder Töne.

| Schlüssel | Standard | Zweck |
|---|---:|---|
| `global` | 3 | Obergrenze aller Add-on-Rückmeldungen |
| `mode`, `delete`, `replace` | 3 | Moduswechsel und Bearbeitung |
| `lineBoundary`, `lineCrossed` | 2 | Zeilengrenzen und Zeilenwechsel |
| `fileBoundary`, `matchingError` | 3 | Dateigrenzen und fehlendes Gegenzeichen |
| `diagnosticLine`, `diagnosticPosition` | 2 | gezielte Fehler-/Warnungsklänge |
| `clipboard` | 3 | Erfolg ausdrücklicher Zwischenablagebefehle |

`focusAnnouncement` verwendet `0 = keine Ansage`, `1 = aktuelle Zeile` und
`2 = aktueller Datei- oder Spezialkontext mit Modus und Verbindungsname`.
Standard ist 2. `automaticParameterHints` ist standardmäßig aktiv und steuert
nur kurze validierte Sprachhinweise zum aktiven Funktionsparameter.

## Navigationsdetails

`navigationDetails` hält getrennte Werte für normale Navigation und die
Abschlussansage der Sprachexploration:

| Schlüssel | Werte | Standard |
|---|---|---:|
| `navigationWord`, `explorationWord` | 0 Wort; 1 Wort und Cursorzeichen | 1 |
| `navigationLine`, `explorationLine` | 0 Zeile; 1 plus Wort; 2 plus Cursorzeichen; 3 plus Wort und Zeichen | 2 |

Die neutralen Sprachplaner erhalten bereits aufgelöste boolesche Werte und
lesen NVDAs Konfiguration nicht selbst. Explorationswerte werden beim
Loslassen der NVDA-Taste aus dem aktiven Profil gelesen; sie verändern weder
virtuelle Bewegung noch Zeichenexploration.

## Braille

| Schlüssel | Standard | Verhalten |
|---|---:|---|
| `brailleFollowSpeechExploration` | `true` | Braille folgt der virtuellen Position der Sprachexploration; der eigene Braille-Explorationsmodus hat Vorrang. |
| `brailleSuggestionStart` | 1 | einsbasierte Startzelle flüchtiger Rechtschreibvorschläge |
| `brailleDeveloperStart` | 1 | einsbasierte Startzelle gehaltener Parameter- und Diagnoseansichten |

Die Startzellen liegen im Bereich 1 bis 1000. Ist die reale Anzeige kürzer,
wird Zelle 1 verwendet. Nach der Brailleübersetzung wird der Start bei Bedarf
nach links verschoben, damit der vollständige Text möglichst auf die Anzeige
passt. Diese Werte verändern weder Sprache noch die dauerhafte Editorregion.

`brailleRouting` enthält drei Auswahlindizes:

- `wordAction`: 0 nur Routing, 1 `cw`, 2 `dw`;
- `lineAction`: 0 nur Routing, 1 `c$`, 2 `d$`;
- `lineStart`: 0 Routingposition, 1 erstes Nicht-Leerzeichen, 2 Zeilenanfang.

Alle Standards sind 0. `lineStart` wird nur bei aktivierter Zeilenaktion
verwendet. Die Wiederholungsfrist stammt ausschließlich aus NVDAs öffentlicher
Einstellung `keyboard.multiPressTimeout`.

## Verbindungen und Zuordnung

`connections` speichert eine JSON-kodierte Liste validierter SSH-Profile in
NVDAs Konfigurationsabschnitt. Ein Profil enthält interne ID, Anzeigename,
Host oder OpenSSH-Alias, optionalen Linux-Benutzer, Port, optionale
Schlüsseldatei und Anmeldeart. Host und Benutzer bleiben getrennte Felder.
Doppelte IDs, ungültige Ports und Optionsinjektion werden abgewiesen;
Passwörter sind ausschließlich Laufzeitdaten.

Lokales Windows-Neovim ist der feste Zieltyp `localWindowsTcp`. Es besitzt
kein gespeichertes Profil und keinen konfigurierbaren Port; der dynamische
Endpunkt bleibt auf `127.0.0.1`.

F12 ist die paketierte physische Zuordnungstaste und kein frei belegbares
NVDA-Skript. Bei aktiviertem Dienst autorisiert ein F12-Druck genau einen
Versuch für das fokussierte Windows-Terminal-Control. Fokusobjekt, konkrete
AppModule-Instanz, vollständige UIA-Identität, Gate und frischer
Sitzungs-Claim müssen übereinstimmen. Ohne Treffer entstehen keine Bindung,
kein Dialog und keine Unterdrückung.

Der frei belegbare Befehl „Server wählen und dieses Terminal mit einer neuen
Neovim-Sitzung verbinden“ öffnet die Profilauswahl und verlangt danach F12 in
der gewünschten Sitzung. Laufzeitbindungen verwenden UIA-Runtime-IDs, leben
nur im Speicher und werden nicht aus Fenstertiteln oder Terminaltext geraten.

## Validierungsgrenze

Einstellungswerte steuern ausschließlich Planung, UI und den Aufbau neuer
Verbindungen. Sie dürfen weder einen Capability-, Fokus-, Identitäts- oder
Protokollcheck umgehen noch frei formulierte Lua-, Ex-, Register- oder
Transportbefehle erzeugen. Schema und Standards gehören zum Add-on-Code;
diese Referenz und beide Sprachfassungen werden bei Änderungen gemeinsam mit
Schema-, Profil-, UI-, Lokalisierungs- und Pakettests aktualisiert.
