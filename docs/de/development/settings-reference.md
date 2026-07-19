# Add-on-Einstellungen

Die Kategorie „Neovim Access Link“ erscheint im normalen
NVDA-Einstellungsdialog. Eigene semantische Rückmeldungen verwenden dasselbe
Modell wie „Zeileneinrückung ansagen“ unter „Dokument-Formatierungen“:

- Aus
- Sprache
- Töne
- Sprache und Töne

Die Seite verwendet drei zugängliche Registerkarten: „Allgemein“ mit globaler
Rückmeldung, „Rückmeldung“ mit den Einzelaktionen und „Verbindungen“ mit
lokalem Windows-Neovim sowie Linux-Verbindungen. Innerhalb der Registerkarten sorgen
beschriftete Gruppen für eine nachvollziehbare Tab-Reihenfolge.

„Allgemein“ enthält außerdem die profilfähige Auswahl für bestätigten
Sitzungsfokus: keine Ansage, aktuelle strukturierte Zeile oder den bisherigen
Datei-/Spezialkontext mit Modus und Verbindungsname. Der bisherige Kontext ist
Standard. Die Auswahl steuert weder Fokuskorrelation noch strukturierte
Braillezeile oder die vorhandenen Modusklang-Einstellungen.

Der globale Wert wird mit dem Wert der einzelnen Aktion kombiniert. Steht der
globale Wert beispielsweise auf „Sprache“, kann keine Aktion einen Ton
ausgeben, ihre aktivierte Sprachausgabe bleibt jedoch erhalten.

Konfigurierbar sind nur Rückmeldungen, für die NVDA keine passendere bestehende
Option besitzt:

- Wechsel zwischen Insert- und Normalmodus; andere Modi bleiben immer sprachlich zugänglich
- Löschen und Backspace
- Ersetzen
- Zeilenanfang und Zeilenende
- Dateianfang und Dateiende
- Hinweis beim Überschreiten einer Zeilengrenze
- fehlendes passendes Klammerzeichen
- Erfolg beim expliziten Kopieren und Einfügen

Folgende Funktionen werden bewusst nicht dupliziert:

| Funktion | Zuständige NVDA-Einstellung |
| --- | --- |
| Einrückung | Optionen → Einstellungen… → Dokument-Formatierungen → Zeileneinrückung ansagen |
| Rechtschreibung und Grammatik | Optionen → Einstellungen… → Dokument-Formatierungen → Rechtschreib- und Grammatikfehler |
| Vorschlagsmenüs | Optionen → Einstellungen… → Objekt-Darstellung → Automatische Vorschläge mit Klang melden |
| Zeichen- und Wortecho | Tastatur, eingegebene Zeichen/Wörter ansagen |

Die Rückmeldungswerte werden im Abschnitt `NeovimAccessLink` von NVDAs regulärer
Konfiguration als Zahlen von 0 bis 3 gespeichert; die Fokusauswahl verwendet
0 bis 2. Unbekannte oder ungültige Werte werden verworfen und im redigierten
Diagnosebericht gemeldet.

Die vier Zwischenablagebefehle besitzen keine Standardgesten. Anwender weisen ihnen
in NVDAs Dialog „Tastenzuordnungen“ eigene Tastenkombinationen zu. Konfiguriert wird nur
die Erfolgsrückmeldung; Übertragungsrichtung, Register und Zielbuffer werden
nicht durch frei eingegebene Befehle oder automatische Synchronisation
gesteuert. Der Registerbefehl ersetzt fest Register 0 und lässt das unbenannte
Register darauf zeigen; benannte Benutzerregister bleiben unverändert.

## NVDA-Konfigurationsprofil

Der Add-on-Dialog besitzt keine eigene Profilwahl und aktiviert oder deaktiviert
keine NVDA-Profile. Seine Werte sind stattdessen native, validierte
`config.conf`-Einstellungen. Wird der Dialog bei einem aktiven
NVDA-Konfigurationsprofil mit „Übernehmen“ oder „OK“ gespeichert, schreibt NVDA
geänderte Add-on-Werte in genau dieses Profil. Nicht geänderte Werte werden wie
andere NVDA-Einstellungen aus darunterliegenden Profilen beziehungsweise der
Basiskonfiguration geerbt.

Manuelle und automatisch ausgelöste NVDA-Profilwechsel laden die wirksamen
Add-on-Werte unmittelbar neu. Rückmeldungsoptionen gelten sofort;
Verbindungswerte gelten für den nächsten Verbindungsaufbau. Eine bereits
authentifizierte laufende Editorverbindung wird durch einen bloßen
NVDA-Profilwechsel nicht unterbrochen. Es gibt keinen separaten JSON-
Einstellungsspeicher und keinen Import aus älteren Add-on-IDs.

## SSH-Verbindungsprofile

Ein SSH-Verbindungsprofil trennt Anzeigename, Host beziehungsweise OpenSSH-
Alias, Port, Linux-Benutzer und optionale Schlüsseldatei. Der lokale Windows-
Benutzername wird an keiner Stelle als Linux-Benutzername eingesetzt. Ein
leeres Benutzerfeld bedeutet ausschließlich, dass OpenSSH den Benutzer aus
seiner Konfiguration bestimmen soll.

Host und Benutzer müssen in getrennten Feldern stehen; kombinierte Altwerte
wie `linux-user@example-host` werden nicht migriert. Profilkennungen, Hosts, Ports,
Benutzernamen, Schlüsselpfade und Authentifizierungsart werden vor Benutzung
validiert; doppelte Kennungen und Optionsinjektion werden abgewiesen.

Lokales Windows-Neovim wird ohne gespeichertes Profil automatisch erkannt; dafür
werden weder Host noch Konto oder Port eingegeben. Für die Komponenteninstallation wird bei jedem Aufruf
ausdrücklich aus dem lokalen Rechner und allen gespeicherten Linux-
Verbindungen gewählt. Ein
abweichender Port wird mit `ssh -p`, eine Schlüsseldatei als separates
`-i`-Argument übergeben; Pfade mit Leerzeichen bleiben dadurch ein einzelnes
Argument.

In der Gruppe „Gespeicherte SSH-Verbindungen“ können Linux-Verbindungen hinzugefügt, bearbeitet
und entfernt werden. Hinzufügen und Bearbeiten öffnet jeweils genau ein
beschriftetes Formular für Anzeigename, Host/Alias, Linux-Benutzer, Port,
optionale Schlüsseldatei und Anmeldeart. Ein Abbruch lässt die Settings
unverändert; ein Validierungsfehler öffnet dasselbe Formular mit den bisherigen
Eingaben erneut.
Erst „OK“ beziehungsweise „Übernehmen“ im NVDA-Dialog schreibt atomisch auf
Datenträger. Änderungen an der Liste starten bei aktivierter Barrierefreiheit
eine neue Hintergrunderfassung, ohne bereits laufende Editorverbindungen zu
beenden.

Im Formular heißen die Anmeldearten „OpenSSH-Einrichtung verwenden (empfohlen:
Schlüssel, ssh-agent oder SSH-Konfiguration)“ und „Beim Verbinden nach dem
SSH-Passwort fragen (Passwort wird nicht gespeichert)“. Die erste Auswahl verwendet die normale Windows-
OpenSSH-Konfiguration, Schlüsseldateien oder ssh-agent und eignet sich, wenn
`ssh` unter Windows bereits ohne Passwortdialog funktioniert. Die zweite
Auswahl erklärt, dass der Linux-SSH-Server Passwortanmeldung erlauben muss.
NVDA fragt beim ersten Verbindungsaufbau der Aktivierung zugänglich nach dem
Passwort. Es wird nur im Arbeitsspeicher gehalten, für Reconnects derselben
Aktivierung wiederverwendet und beim Deaktivieren oder Beenden verworfen.

Der Menüpunkt `NVDA-Menü → Werkzeuge → Neovim Access Link: Komponenten installieren oder aktualisieren...`
öffnet vor jeder Installation eine Checkboxliste aus „Dieser Computer“ und allen gespeicherten
Linux-Verbindungen. Jeder Eintrag
nennt Anzeigename, Linux-Konto, Host, Port und verständliche Anmeldeart. Keine
Verbindung ist vorausgewählt. Die initial fokussierte Checkbox „Alle
Verbindungen auswählen“ markiert beziehungsweise demarkiert alle Ziele; alternativ lassen
sich einzelne Verbindungen ankreuzen. Sind dadurch alle Einzelziele markiert,
aktiviert sich die Sammelcheckbox ebenfalls; beim Demarkieren eines Ziels wird
sie wieder deaktiviert. „OK“ akzeptiert nur eine nichtleere Auswahl. Das
lokale Plugin beziehungsweise das kombinierte Linux-Benutzerpaket wird im
Hintergrund ohne Administrator- oder Root-Rechte installiert. Der abschließende Dialog listet
kompakt und ohne NVDA zu blockieren getrennt auf, welche Verbindungen
erfolgreich aktualisiert wurden und welche mit welchem kurzen Grund
fehlgeschlagen sind.

Das Passwort erscheint weder in JSON noch Kommandozeile oder Diagnose. Windows
OpenSSH erhält es mit `SSH_ASKPASS_REQUIRE=force` über einen mitgelieferten
Helfer, dessen Datei selbst kein Geheimnis enthält. Der SSH-Prozess erlaubt nur
einen Passwortversuch und deaktiviert in diesem Modus Public-Key-Fallback.

Profile sind gespeicherte Linux-Zielkonten und dürfen dieselben Werte besitzen. Zwei
Profile können daher beispielsweise beide `editor@example-host` verwenden und bleiben
durch ihre interne ID getrennt. Parallele SSH-Laufzeitverbindungen sind als
eigene Instanzen umgesetzt. Lokale Windows-Sitzungen sind als eigener Typ
`localWindowsTcp` umgesetzt. Ihr dynamischer Port ist ausschließlich an
`127.0.0.1` gebunden und wird niemals manuell konfiguriert.

Hostwerte dürfen DNS-Namen, OpenSSH-Aliase, IPv4- oder IPv6-Literale sein.
Mehrere unterschiedliche Hosts können parallel verbunden und explizit an
verschiedene Terminals gebunden werden. SSH-Port, Schlüssel und
Authentifizierung gelten je Profil und werden nicht global geteilt.

`F12` ist die fest konfigurierte Zuordnungstaste des installierten Plugins und
kein frei belegbarer NVDA-Befehl. Bei eingeschaltetem Dienst autorisiert jeder physische
F12-Druck genau einen Zuordnungsversuch für die vollständige UIA-Identität des
fokussierten Windows-Terminal-Controls. NVDA reicht die Geste unverändert an
Windows Terminal und Neovim weiter und vergleicht danach die Claim-Sequenzen
der lokalen JSON-Sitzungsdateien und aller automatisch erfassten
SSH-Verbindungen. Diese dateibasierte Sitzungsregistrierung ist keine Windows-
Registry. Das Plugin schreibt ohne sichtbare Neovim-Meldung eine monotone
Markierung in seine private Sitzungsdatei; das Add-on wählt lokal
beziehungsweise über SSH nur die jüngste, höchstens
15 Sekunden alte Markierung. Dadurch ist
auch bei identischen Konten, Arbeitsverzeichnissen und Sitzungsnamen keine ID-
Eingabe und kein Raten anhand des Terminalinhalts nötig. Nach einer
Komponentenaktualisierung muss Neovim neu gestartet werden, damit die
F12-Erkennung verfügbar ist.
Das Windows-Terminal-App-Modul beobachtet F12 mit
`decide_executeGesture`, ohne ein NVDA-Skript zu binden. NVDA lässt dadurch den
ursprünglichen physischen Tastendruck direkt zu Neovim durch; der Beobachter
stellt die Claim-Auswertung getrennt in die Ereigniswarteschlange. Neovim
vergleicht den unveränderten `typed`-Wert statt einer terminalcodeabhängigen
Zuordnung. Bei ausgeschaltetem Dienst ist der Beobachter inaktiv. Bei
eingeschaltetem Dienst aktualisiert das Add-on nach F12 die Terminalzuordnung
und sucht nach genau dem dadurch neu entstandenen Claim; ohne Treffer bleibt
die Prüfung still und ohne Bindung, Dialog oder Unterdrückung.
Vor der Autorisierung müssen das aktuelle NVDA-Fokusobjekt, genau dessen
Windows-Terminal-AppModule-Instanz, die vollständige UIA-Control-Identität und
das Gate übereinstimmen. Ein einzelnes noch lebendes AppModule genügt nicht als
Fallback. Im Insert-Modus bleibt F12 als physischer Claim sichtbar, erzeugt bei
ansonsten unbelegter Taste danach aber keinen Text. Bestehende
Insert-Mode-Belegungen werden nicht ersetzt. Da vor der ersten Verbindung kein
Rückkanal von NVDA zu dieser Neovim-Instanz besteht, gilt diese schmale
Reservierung innerhalb Neovims auch dann, wenn NVDA den Tastendruck nicht für
eine Zuordnung autorisiert; außerhalb von Neovim bleibt F12 unverändert.

Der Aktivierungsbefehl startet die Hintergrunderfassung. F12 wird erst nach der
Bereitschaftsmeldung zur Zuordnung ausgewertet. Der gesonderte Befehl „Server wählen und dieses
Terminal mit einer neuen Neovim-Sitzung verbinden“ wählt ein Ziel und bereitet
danach denselben control-spezifischen F12-Nachweis vor.

Diese Befehle werden derzeit ausschließlich in eindeutig erkanntem Windows
Terminal aktiv. Die ausgelieferte `frontend-policy.json` führt Windows Terminal
als aktiviert und PuTTY lediglich als geplant. Die Richtlinie ist keine
Benutzereinstellung: Ein weiteres Terminal kann erst nach Implementierung und
Prüfung eines passenden Adapters freigegeben werden. In allen anderen Fenstern
bleiben Verbindungsaufbau, strukturierte Ausgabe, Braille-Overlay und
Terminalunterdrückung aus.
Auch F12 ist keine globale Add-on-Belegung: Die Geste gehört zum von NVDA nur
für `windowsterminal.exe` geladenen AppModule. Notepad, PuTTY und andere
Anwendungen laden diesen Eingabescriptpfad überhaupt nicht. Beim Verlassen von
Windows Terminal löscht NVDAs AppModule-Lebenszyklus den aktiven
Unterdrückungszustand.

Die SSH-Abfrage verwendet das ausdrücklich gewählte Verbindungsprofil. Neovim kann vor
der ersten Bridgeverbindung nicht selbst aus der entfernten SSH-Sitzung zum
Windows-Add-on zurückrufen. Für ein anderes Konto oder einen anderen Host muss
daher zuerst das passende Profil aktiviert oder der dialogbasierte
Verbindungsbefehl verwendet werden.

Über NVDAs Dialog „Eingaben“ können Anwender zusätzlich eine eigene Tastenkombination für
„Server wählen und dieses Terminal mit einer neuen Neovim-Sitzung verbinden“
vergeben. Dieser Befehl öffnet immer die Profilauswahl. Die früher angebotenen,
leicht verwechselbaren Befehle zum Auswählen oder zyklischen Wechseln einer
bereits laufenden Verbindung sind nicht mehr öffentlich. Es gibt keine
kollisionsanfällige Standardbelegung für diesen dialogbasierten Zusatzbefehl
und keine heuristische Zuordnung anhand von Fenstertiteln. Die Auswahl gilt für
das beim Aufruf fokussierte Terminal.

Der Befehl „Server wählen und dieses Terminal mit einer neuen Neovim-Sitzung verbinden“ lässt
sich in NVDAs Dialog „Eingaben“ frei mit einer Taste belegen. Er fragt immer
ausdrücklich nach dem Profil, verlangt danach F12 im gewünschten Neovim und
zeigt nur bei mehreren frisch markierten Sitzungen eine kurze Auswahl mit Name
und Arbeitsverzeichnis. Interne IDs werden nicht angezeigt, und das
Add-on versucht keine Zuordnung anhand von Fenstertiteln oder Terminaltext.

Ein Profil reicht für mehrere parallele Neovim-Instanzen desselben Kontos.
Bei gleichen Arbeitsverzeichnissen können sie mit
`NVIM_NVDA_SESSION_NAME="Name" nvim` oder später mit
`:NvimNvdaSessionName Name` benannt werden. Ohne Namen ergänzt die Auswahl
Startzeit und laufende Nummer und kennzeichnet bereits verbundene Sitzungen.

Der Verbindungsbefehl erzeugt eine eigene Laufzeitinstanz.
Nach deren erstem gültigen `fullState` kann der Anwender eine ausschließlich im
RAM gehaltene Zuordnung zum aktuellen Windows-Terminal-Control bestätigen. Sie
verwendet die UIA-Runtime-ID statt Titel oder Terminaltext. Ein eigener
NVDA-Befehl vergisst die Zuordnung wieder. Abgelehnte oder veraltete IDs lösen
keine automatische Verbindung aus.
Jede Instanz behält ihren eigenen SSH-Prozess und Reconnectzustand. Laufende
Instanzen erscheinen im schnellen Auswahldialog. Alternativ kann „nächste
Neovim-Verbindung“ in NVDAs Dialog „Eingaben“ mit einer eigenen Taste belegt
werden. „Ausgewählte Instanz trennen“ beendet nur die an dieses Terminal
gebundene Verbindung. Beim Umschalten fordert das Add-on den vollständigen
Neovim-Zustand neu an.
