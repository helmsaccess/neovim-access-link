# Add-on-Einstellungen

Die Kategorie „Neovim Access Link“ erscheint im normalen
NVDA-Einstellungsdialog. Eigene semantische Rückmeldungen verwenden dasselbe
Modell wie „Zeileneinrückung ansagen“ unter „Dokument-Formatierungen“:

- Aus
- Sprache
- Töne
- Sprache und Töne

Die Seite verwendet drei zugängliche Registerkarten: „General“ mit globaler
Rückmeldung, „Feedback“ mit den Einzelaktionen und „Connections“ mit
lokalem Windows-Neovim sowie Linux-Verbindungen. Innerhalb der Registerkarten sorgen
beschriftete Gruppen für eine nachvollziehbare Tab-Reihenfolge.

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

Folgende Funktionen werden bewusst nicht dupliziert:

| Funktion | Zuständige NVDA-Einstellung |
| --- | --- |
| Einrückung | Optionen → Einstellungen… → Dokument-Formatierungen → Zeileneinrückung ansagen |
| Rechtschreibung und Grammatik | Optionen → Einstellungen… → Dokument-Formatierungen → Rechtschreib- und Grammatikfehler |
| Vorschlagsmenüs | Optionen → Einstellungen… → Objekt-Darstellung → Automatische Vorschläge mit Klang melden |
| Zeichen- und Wortecho | Tastatur, eingegebene Zeichen/Wörter ansagen |

Die Werte werden im Abschnitt `nvimNvdaAccess` von NVDAs regulärer
Konfiguration als Zahlen von 0 bis 3 gespeichert. Unbekannte oder ungültige
Werte werden verworfen und im redigierten Diagnosebericht gemeldet.

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
NVDA-Profilwechsel nicht unterbrochen. Das bisherige `nvimNvdaAccess.json` wird
bei einem Upgrade einmalig in die NVDA-Konfiguration übernommen und danach nur
noch als Sicherheitskopie behalten.

## SSH-Verbindungsprofile

Das versionierte Schema 2 trennt Anzeigename, Host beziehungsweise OpenSSH-
Alias, Port, Linux-Benutzer und optionale Schlüsseldatei. Der lokale Windows-
Benutzername wird an keiner Stelle als Linux-Benutzername eingesetzt. Ein
leeres Benutzerfeld bedeutet ausschließlich, dass OpenSSH den Benutzer aus
seiner Konfiguration bestimmen soll.

Bestehende Werte wie `linux-user@example-host` werden verlustfrei in ein Profil mit
explizitem Linux-Benutzer migriert. Ein alter reiner Alias wie `example-host` bleibt
ein Alias ohne abgeleiteten Benutzer. Profilkennungen, Hosts, Ports,
Benutzernamen, Schlüsselpfade und Authentifizierungsart werden vor Benutzung
validiert; doppelte Kennungen und Optionsinjektion werden abgewiesen.

Lokales Windows-Neovim wird ohne gespeichertes Profil automatisch erkannt; dafür
werden weder Host noch Konto oder Port eingegeben. Für die Komponenteninstallation wird bei jedem Aufruf
ausdrücklich aus dem lokalen Rechner und allen gespeicherten Linux-
Verbindungen gewählt. Ein
abweichender Port wird mit `ssh -p`, eine Schlüsseldatei als separates
`-i`-Argument übergeben; Pfade mit Leerzeichen bleiben dadurch ein einzelnes
Argument.

In der Gruppe „Saved SSH connections“ können Linux-Verbindungen hinzugefügt, bearbeitet
und entfernt werden. Hinzufügen und Bearbeiten öffnet jeweils genau ein
beschriftetes Formular für Anzeigename, Host/Alias, Linux-Benutzer, Port,
optionale Schlüsseldatei und Anmeldeart. Ein Abbruch lässt die Settings
unverändert; ein Validierungsfehler öffnet dasselbe Formular mit den bisherigen
Eingaben erneut.
Erst „OK“ beziehungsweise „Übernehmen“ im NVDA-Dialog schreibt atomisch auf
Datenträger. Änderungen an der Liste starten bei aktivierter Barrierefreiheit
eine neue Hintergrunderfassung, ohne bereits laufende Editorverbindungen zu
beenden.

Im Formular heißen die Anmeldearten „Use OpenSSH setup“ und „Ask for the SSH
password“. Die erste, empfohlene Auswahl verwendet die normale Windows-
OpenSSH-Konfiguration, Schlüsseldateien oder ssh-agent und eignet sich, wenn
`ssh` unter Windows bereits ohne Passwortdialog funktioniert. Die zweite
Auswahl erklärt, dass der Linux-SSH-Server Passwortanmeldung erlauben muss.
NVDA fragt beim ersten Verbindungsaufbau der Aktivierung zugänglich nach dem
Passwort. Es wird nur im Arbeitsspeicher gehalten, für Reconnects derselben
Aktivierung wiederverwendet und beim Deaktivieren oder Beenden verworfen.

Der Menüpunkt `NVDA-Menü → Werkzeuge → Neovim Access Link: Install or update components...`
öffnet vor jeder Installation eine Checkboxliste aus „This computer“ und allen gespeicherten
Linux-Verbindungen. Jeder Eintrag
nennt Anzeigename, Linux-Konto, Host, Port und verständliche Anmeldeart. Keine
Verbindung ist vorausgewählt. Die initial fokussierte Checkbox „Select all
connections“ markiert beziehungsweise demarkiert alle Ziele; alternativ lassen
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

`F12` ist standardmäßig mit „Fokussierte Neovim-Sitzung markieren und
verbinden“ belegt. NVDA fängt die Geste technisch ab, reicht sie zuerst
unverändert an Windows Terminal und Neovim weiter und startet nur in einem
erkannten Windows-Terminal-Tab die zum gebundenen Ziel passende Abfrage. Bei
einem ungebundenen Tab vergleicht es die Claim-Sequenzen der lokalen Registry
und aller automatisch erfassten SSH-Verbindungen. Das Plugin schreibt ohne
sichtbare Neovim-Meldung eine monotone Markierung in seine private
Session-Registry; das Add-on wählt lokal beziehungsweise über SSH nur die jüngste, höchstens
15 Sekunden alte Markierung. Dadurch ist
auch bei identischen Konten, Arbeitsverzeichnissen und Sitzungsnamen keine ID-
Eingabe und kein Raten anhand des Terminalinhalts nötig. Nach einer
Komponentenaktualisierung muss Neovim neu gestartet werden, damit die
F12-Belegung verfügbar ist.

Der Aktivierungsbefehl startet die Hintergrunderfassung. Wird F12 vorher
gedrückt, aktiviert es die Barrierefreiheit und fordert nach Abschluss der
Erfassung zu einem zweiten Tastendruck auf. Der gesonderte Befehl „Server wählen und dieses
Terminal mit einer neuen Neovim-Sitzung verbinden“ behält bewusst seine Dialoge.

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

Die SSH-Abfrage verwendet das aktuell aktive Verbindungsprofil. Neovim kann vor
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

Beim Aktivieren ermittelt das Add-on die laufenden Neovim-Sitzungen des aktiven
Profils. Gibt es genau eine, wird sie automatisch mit dem fokussierten Terminal
verbunden. Bei mehreren erscheint eine kurze Auswahl mit Name und
Arbeitsverzeichnis; numerische Sitzungs-IDs müssen nicht eingegeben werden.
Der Befehl „Server wählen und dieses Terminal mit einer neuen Neovim-Sitzung verbinden“ lässt
sich in NVDAs Dialog „Eingaben“ frei mit einer Taste belegen. Er fragt immer
ausdrücklich nach dem Profil und zeigt bei mehreren Sitzungen eine kurze Auswahl
mit Name und Arbeitsverzeichnis. Interne IDs werden nicht angezeigt, und das
Add-on versucht keine Zuordnung anhand von Fenstertiteln oder Terminaltext.

Ein Profil reicht für mehrere parallele Neovim-Instanzen desselben Kontos.
Bei gleichen Arbeitsverzeichnissen können sie mit
`NVIM_NVDA_SESSION_NAME="Name" nvim` oder später mit
`:NvimNvdaSessionName Name` benannt werden. Ohne Namen ergänzt die Auswahl
Startzeit und laufende Nummer und kennzeichnet bereits verbundene Sitzungen.

Der Verbindungsbefehl erzeugt eine eigene Laufzeitinstanz.
Nach deren erstem gültigen `fullState` kann der Anwender eine ausschließlich im
RAM gehaltene Zuordnung zum aktuellen Windows-Terminal-Tab bestätigen. Sie
verwendet die UIA-Runtime-ID statt Titel oder Terminaltext. Ein eigener
NVDA-Befehl vergisst die Zuordnung wieder. Abgelehnte oder veraltete IDs lösen
keine automatische Verbindung aus.
Jede Instanz behält ihren eigenen SSH-Prozess und Reconnectzustand. Laufende
Instanzen erscheinen im schnellen Auswahldialog. Alternativ kann „nächste
Neovim-Verbindung“ in NVDAs Dialog „Eingaben“ mit einer eigenen Taste belegt
werden. „Ausgewählte Instanz trennen“ beendet nur die an dieses Terminal
gebundene Verbindung. Beim Umschalten fordert das Add-on den vollständigen
Neovim-Zustand neu an.
