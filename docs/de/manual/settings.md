# Handbuch: Einstellungen des NVDA-Add-ons

Dieser Abschnitt beschreibt den Einstellungsdialog von Neovim Access Link aus
Anwendersicht.

## Einstellungsdialog öffnen

Der Dialog wird über `NVDA-Menü → Optionen → Einstellungen… → Neovim
Access Link` geöffnet. Das Add-on fügt keinen redundanten direkten
Einstellungs-Menüpunkt hinzu.

Die Kategorie enthält drei Registerkarten:

- `General` für die globale Rückmeldungsart und die Ausgabe beim erneuten
  Sitzungsfokus;
- `Feedback` für Rückmeldungen einzelner Editoraktionen;
- `Connections` für Linux-Rechner und Linux-Benutzerkonten.

Mit `OK` werden die Einstellungen gespeichert und der Dialog geschlossen. Mit
`Apply` werden sie gespeichert, während der Dialog geöffnet bleibt. `Cancel`
verwirft Änderungen, die seit dem letzten Speichern im Einstellungsdialog
vorgenommen wurden.

Die Add-on-Einstellungen gehören zu NVDAs normaler Konfiguration. Ist beim
Speichern ein NVDA-Konfigurationsprofil aktiv, speichert NVDA geänderte
Add-on-Werte in diesem Profil. Nicht geänderte Werte werden wie bei anderen
NVDA-Kategorien geerbt. Das Add-on wählt oder aktiviert selbst kein Profil.

## Registerkarte General

NVDA-Konfigurationsprofile werden über `NVDA-Menü → Konfigurationsprofile verwalten…`
erstellt, aktiviert und mit Auslösern verbunden. Um eigene Neovim-Werte zu
speichern, wird zuerst das gewünschte NVDA-Profil aktiviert und anschließend
dieser Einstellungsdialog geöffnet. Änderungen auf allen drei Registerkarten
werden dann von NVDAs normalem Profilmechanismus verwaltet.

Ein Profil kann beispielsweise Add-on-Rückmeldungen zusammen mit Zeichen- und
Wortecho, Einrückungsansage, Rechtschreibung, Satzzeichenausführlichkeit,
Braille und Sprache anpassen. Beim Wechsel des NVDA-Profils lädt das Add-on die
wirksamen Werte automatisch neu. Es ruft weder `manualActivateProfile` noch
eine eigene Rückkehr zur Basiskonfiguration auf.

### Gruppe Global action feedback

#### Global action feedback

Diese Einstellung ist der Hauptschalter für Rückmeldungen, die das Add-on
selbst für Editoraktionen erzeugt. Verfügbar sind:

| Auswahl | Wirkung |
| --- | --- |
| `Off` | Weder Sprache noch Aktionsklang des Add-ons. |
| `Speech` | Nur die zugehörige Sprachausgabe. |
| `Tones` | Nur der zugehörige Klang oder Ersatzton. |
| `Both Speech and Tones` | Sprache und Klang. |

Der globale Wert wird mit jedem Einzelwert auf der Registerkarte `Feedback`
kombiniert. Er ist damit eine Obergrenze und überschreibt nicht einfach den
Einzelwert.

Beispiele:

- Global `Speech`, Löschen `Both Speech and Tones`: Beim Löschen bleibt nur die
  Sprache übrig.
- Global `Tones`, Löschen `Speech`: Für das Löschen erfolgt weder Sprache noch
  Klang, weil beide Einstellungen keine gemeinsame Ausgabeart erlauben.
- Global `Both Speech and Tones`, Löschen `Tones`: Nur der Löschklang wird
  ausgegeben.

Gültigkeitsbereich: Dieser Hauptschalter betrifft nur die in diesem Dialog
aufgeführten, vom Add-on kontrollierten Aktionsrückmeldungen. Er schaltet weder
NVDA insgesamt stumm noch verändert er Zeichen-/Wortecho, Einrückung,
Rechtschreibung, Braille oder Vorschlagsmeldungen.

### Gruppe Session focus

#### When focusing a Neovim session

Steuert die zusätzliche Ausgabe, nachdem ein gebundenes Neovim-Control erneut
Fokus erhalten hat und die Sitzung strukturiert bestätigt wurde:

| Auswahl | Wirkung |
| --- | --- |
| `No announcement` | Keine zusätzliche Fokusansage. |
| `Current line` | Die aktuelle strukturierte Zeile oder „blank“. |
| `Current context, mode and connection name` | Datei beziehungsweise Spezialkontext, Modus und gespeicherter Verbindungsname wie bisher. |

Der letzte Wert ist Standard. Die Auswahl ändert nur diese Fokusansage und
deren vorübergehende Braillemeldung. Die strukturierte Braillezeile und die
sichere Sitzungsbestätigung bleiben immer aktiv. Beim bestätigten Fokus werden
für Insert- und Normalmodus außerdem die Modusklänge ausgegeben, sofern
`Global action feedback` und `Insert and normal mode changes` Klänge erlauben.

## Registerkarte Feedback

Alle Einstellungen dieser Registerkarte besitzen dieselben vier Werte `Off`,
`Speech`, `Tones` und `Both Speech and Tones`. Ihre tatsächliche Ausgabe wird
zusätzlich durch `Global action feedback` begrenzt.

### Insert and normal mode changes

Steuert die Add-on-Rückmeldung beim Wechsel zwischen Insert Mode und Normal
Mode. Sprache nennt den neuen Modus; die Klangkomponente verwendet kurze,
bereits beim Add-on-Start in den Arbeitsspeicher geladene Modusklänge.
Dieselben Klänge bestätigen auch den aktuellen Insert- oder Normalmodus beim
erneuten Fokus einer gebundenen Sitzung.

Der Wechsel von Insert nach Normal unterbricht eine noch laufende gewöhnliche
Navigationsausgabe, damit die Modusrückmeldung nicht hinter veraltetem Text
wartet.

Gültigkeitsbereich: Diese Einstellung gilt für die häufigen Wechsel zwischen
Insert und Normal. Andere wichtige Modi wie Visual, Command-line, Replace oder
Terminal bleiben aus Gründen der sicheren Orientierung sprachlich zugänglich
und werden nicht vollständig durch diesen Schalter verborgen.

### Deleting text

Steuert Sprache und Klang für semantisch erkannte Löschaktionen. Dazu gehören
unter anderem Backspace, Zeichenlöschung und Operatoren wie `d` oder `dd`,
sofern Neovim die Änderung zuverlässig als Löschung klassifizieren kann.

Bei einer zeilenweisen Löschung wird zusätzlich die Zeile ausgegeben, auf der
der Cursor anschließend steht. Der Löschklang ist eine Rückmeldung über die
Aktion und kein Ersatz für den gesprochenen Ergebnistext.

Gültigkeitsbereich: Die Rückmeldung wird nur für echte Löschänderungen erzeugt.
Ein im Insert Mode eingegebener Buchstabe `d` ist keine Löschaktion.

### Replacing text

Steuert Sprache und Klang für Ersetzen beziehungsweise Ändern von Text, etwa
bei Änderungsoperatoren wie `cw` oder bei zuverlässig erkannten
Ersetzungsereignissen.

### Copy and paste

Steuert die Erfolgsrückmeldung der vier frei belegbaren NVDA-Befehle zum
Kopieren der aktuellen Visual-Auswahl, zum Kopieren von Neovims letztem Yank
und zum Einfügen von Windows-Zwischenablagentext sowie zum Ersetzen von Neovims
aktuellem unbenannten Register. Fehler bleiben unabhängig von dieser Auswahl
hörbar. Es gibt keine automatische Synchronisation und keine feste
Tastenkombination.

Kopieren liest ausschließlich die aktuelle Visual-Auswahl oder Neovims
Register 0. Einfügen verwendet Neovims strukturierte Paste-API und ist auf
normale veränderbare Editorbuffer im Normal- oder Insertmodus beschränkt.
Terminalbuffer, Dateimanager, schreibgeschützte und nicht veränderbare Buffer
werden abgewiesen. Der Registerbefehl verändert keinen Buffer. Er ersetzt
Register 0 und lässt das unbenannte Register darauf zeigen; normales `p` und
`"0p` verwenden danach den übertragenen Text. Lokal und über SSH gilt dasselbe
Verhalten.

Der Ersetzungsklang unterscheidet sich vom Löschklang. Nachfolgende Navigation
oder Texteingabe wird nicht fälschlich als Teil des vorherigen Operators
behandelt.

### Line boundaries

Steuert die Rückmeldung beim bewussten Erreichen von Zeilenanfang oder
Zeilenende. Die Klangkomponente verwendet unterschiedliche kurze Signale für
Anfang und Ende.

Gültigkeitsbereich: Zeilengrenzklänge werden bei Navigation im Normal Mode
erzeugt. Normales Schreiben am Ende einer Zeile soll dadurch nicht ständig
einen Grenzklang auslösen. Die Einstellung ist nicht die Einrückungsansage und
meldet nicht jeden vertikalen Zeilenwechsel.

### File boundaries

Steuert die Rückmeldung beim Erreichen von Dateianfang oder Dateiende. Anfang
und Ende besitzen unterschiedliche Klänge. Sprache kann die entsprechende
Grenze zusätzlich nennen.

Gültigkeitsbereich: Gemeint sind Grenzen des aktiven Neovim-Buffers, nicht der
Anfang oder das Ende der sichtbaren Terminalseite.

### Crossing into another line

Steuert einen kurzen Hinweis, wenn eine Bewegung, die normalerweise Zeichen,
Wörter oder ein anderes nicht zeilenweises Ziel liest, dabei in eine andere
Zeile wechselt.

Beispiel: Eine Wortbewegung springt vom letzten Wort einer Zeile zum ersten
Wort der nächsten Zeile. Das Zielwort wird weiterhin ausgegeben; der zusätzliche
Hinweis macht den Zeilenwechsel hörbar.

Gültigkeitsbereich: Der Hinweis ergänzt nicht zeilenweise Navigation. Bei
normaler Zeilennavigation wird stattdessen direkt die neue Zeile ausgegeben.

### Missing matching bracket

Steuert die Rückmeldung, wenn für eine Matching-Pair-Bewegung, beispielsweise
mit `%`, kein passendes Klammerzeichen gefunden wird.

Sprache meldet den Fehler, die Klangkomponente verwendet den Fehlerklang. Ein
erfolgreicher Sprung zum Gegenzeichen wird weiterhin mit Gegenzeichen,
Zeilennummer und gegebenenfalls Zeilenwechselhinweis ausgegeben.

## Von vorhandenen NVDA-Einstellungen übernommene Funktionen

Der Add-on-Dialog dupliziert Einstellungen nicht, wenn NVDA bereits eine
passende und etablierte Option besitzt. Dadurch gelten dieselben Gewohnheiten
wie in anderen zugänglichen Anwendungen.

| Funktion | Zuständige NVDA-Einstellung | Wirkung in Neovim Access Link |
| --- | --- | --- |
| Zeichen während der Eingabe | `Optionen → Einstellungen… → Tastatur → Eingegebene Zeichen ansagen` | Steuert das Zeichen-Tippecho. |
| Wörter während der Eingabe | `Optionen → Einstellungen… → Tastatur → Eingegebene Wörter ansagen` | Steuert das Wort-Tippecho. |
| Einrückung | `Optionen → Einstellungen… → Dokument-Formatierungen → Zeileneinrückung ansagen` | Verwendet NVDA-Modi Aus, Sprache, Töne oder beides; Ausgabe nur bei geänderter Einrückung. |
| Rechtschreibung und Grammatik | `Optionen → Einstellungen… → Dokument-Formatierungen → Rechtschreib- und Grammatikfehler` | Steuert Sprache, NVDA-Fehlerklang und Braillemarkierung. |
| Automatische Vorschläge | `Optionen → Einstellungen… → Objekt-Darstellung → Automatische Vorschläge mit Klang melden` | Steuert die NVDA-eigenen Öffnen-/Schließen-Klänge für Vorschlagslisten. |
| Satzzeichen und Symbole | NVDA-Satzzeichen-/Symbolausführlichkeit | Gilt für normale Zeilen- und Textausgabe; Zeichen-, Wort- und Auswahloperationen erzwingen nötige Symboldetails zur eindeutigen Orientierung. |

Wenn unterschiedliche Werte nur für Neovim gelten sollen, empfiehlt sich ein
eigenes NVDA-Konfigurationsprofil. Dieses wird mit NVDAs regulärem
Profilmechanismus aktiviert; anschließend werden die gewünschten Werte im
Add-on-Dialog gespeichert.

## Registerkarte Connections

Lokale Windows-Neovim-Instanzen benötigen keinen Verbindungseintrag und werden
im aktuellen Benutzerkonto automatisch erfasst. Die Liste enthält ausschließlich
Linux-Benutzerkonten auf entfernten Rechnern. Lokaler Rechner und SSH-Profile
bleiben ausdrückliche Ziele der Komponenteninstallation.

Verbindungen sind Vorlagen, keine laufenden SSH-Prozesse. Mehrere Einträge
dürfen denselben Host oder sogar dasselbe Konto beschreiben, beispielsweise für
unterschiedliche Schlüssel, Ports oder Arbeitsumgebungen.

### Saved connections

Die Liste dient ausschließlich zum Verwalten der gespeicherten SSH-Ziele; es
gibt keine Standardverbindung. Beim Aktivieren erfasst das Add-on lokal sowie
alle gespeicherten OpenSSH-Verbindungen parallel im Hintergrund. Ein Eintrag
zeigt den frei gewählten Namen und das tatsächliche SSH-Ziel; ein vom Standard
abweichender Port wird ebenfalls angezeigt.

Passwortprofile werden nicht ungefragt automatisch geöffnet. Solange für die
aktuelle NVDA-Laufzeit kein Passwort vorhanden ist, werden sie über den
manuellen Verbindungsbefehl ausgewählt. Eine interaktive SSH-Verbindung des
Anwenders und tmux bleiben unberührt.

Beim lokalen Ziel wird kein dauerhafter Port gespeichert. Nach Installation
und Neovim-Neustart legt das Plugin selbst einen dynamischen Port ausschließlich
auf `127.0.0.1` an. F12 markiert die fokussierte lokale Instanz; das Add-on liest
Port und interne Sitzungskennung aus der benutzerbezogenen, dateibasierten
Sitzungsregistrierung unter `%LOCALAPPDATA%\nvim-nvda\sessions`. Die Windows-
Registry wird nicht verwendet. Eigene
`NVIM_APPNAME`-Datenverzeichnisse und portable Neovim-Layouts werden in dieser
ersten Fassung noch nicht automatisch installiert.

### Add connection

Öffnet ein einziges Formular für alle Angaben. Erst nach Bestätigung wird die
neue Verbindung in die Liste des noch geöffneten NVDA-Einstellungsdialogs
übernommen. Dauerhaft gespeichert wird sie mit `Apply` oder `OK` des
übergeordneten Einstellungsdialogs.

### Edit connection

Öffnet dasselbe Formular mit den vorhandenen Werten. Die interne stabile
Kennung bleibt dabei erhalten. Ein Abbruch verwirft die Formularänderungen.

### Remove connection

Entfernt den ausgewählten Eintrag aus der Liste. Die eigentliche Speicherung
erfolgt erst mit `Apply` oder `OK`.

Das Entfernen deinstalliert keine Dateien auf Linux, löscht keine SSH-Schlüssel
und verändert keine Windows-SSH-Konfiguration.

## Formular Add Linux connection beziehungsweise Edit Linux connection

### Connection name

Ein frei wählbarer, verständlicher Anzeigename, beispielsweise `Dokumentationsserver`,
`Testserver` oder `Projektkonto auf example.org`.

Der Name dient nur der Auswahl in NVDA. Er wird nicht als Hostname oder
Linux-Benutzername verwendet. Er darf deshalb Leerzeichen enthalten.

### Server name, address or SSH alias

Der Linux-Rechner als DNS-Name, IPv4-/IPv6-Adresse oder bereits in der
Windows-OpenSSH-Konfiguration definierter Alias, beispielsweise:

```text
server.example.invalid
server.example.org
192.0.2.10
2001:db8::10
```

Kein `ssh`-Befehl und keine zusätzlichen Optionen eintragen. Werte, die wie
Kommandozeilenoptionen beginnen oder Steuer-/Leerzeichen enthalten, werden aus
Sicherheitsgründen abgewiesen.

### Linux username

Der Benutzername des Linux-Kontos, unter dem Neovim läuft und in dessen
Home-Verzeichnis die Komponenten installiert werden sollen.

Das Feld darf leer bleiben, wenn der Benutzer bereits durch einen OpenSSH-Alias
in der Windows-Datei `~/.ssh/config` festgelegt ist. Das Add-on nimmt niemals
automatisch an, dass Windows- und Linux-Benutzername gleich sind.

### SSH port

Der SSH-Port des Servers. Standard ist `22`. Zulässig sind Werte von 1 bis
65535. Ein abweichender Wert wird sowohl bei der Laufzeitverbindung als auch bei
der Installation verwendet.

### Private key file

Optionaler vollständiger Pfad zu einer privaten Schlüsseldatei auf Windows.
Das Feld kann leer bleiben, wenn OpenSSH den Schlüssel über `~/.ssh/config`,
den Standardpfad oder ssh-agent findet.

Das Feld ist nur bei `Use OpenSSH setup` aktiv. Bei Passwortanmeldung wird kein
Schlüsselpfad gespeichert oder verwendet.

### Sign-in method

#### Use OpenSSH setup

Empfohlene Auswahl. Das Add-on startet den normalen Windows-OpenSSH-Client und
verwendet:

- die Windows-OpenSSH-Konfiguration;
- den optional im Formular angegebenen privaten Schlüssel;
- ssh-agent;
- normale Host-Key-Prüfung.

Diese Auswahl ist passend, wenn ein Befehl wie der folgende unter Windows
bereits ohne Passwortdialog funktioniert:

```powershell
ssh linux-benutzer@server
```

Das Add-on speichert weder private Schlüssel noch deren Passphrasen. Ein
Schlüssel mit nicht bereits durch ssh-agent verfügbarer Passphrase kann in
einem unsichtbaren Hintergrundprozess nicht interaktiv entsperrt werden.

#### Ask for the SSH password when connecting

Diese Auswahl ist für ein Linux-Konto gedacht, dessen SSH-Server
Passwortanmeldung erlaubt.

NVDA fragt zugänglich nach dem Passwort, wenn die Verbindung oder Installation
es erstmals benötigt. Das Passwort:

- wird nicht in NVDAs Konfiguration gespeichert;
- erscheint nicht in der SSH-Kommandozeile;
- wird im Diagnosebericht redigiert;
- bleibt nur im Arbeitsspeicher;
- kann für Reconnects derselben Aktivierung wiederverwendet werden;
- wird beim Deaktivieren, Beenden oder Neustarten des Add-ons verworfen.

Die Auswahl konfiguriert den Linux-SSH-Server nicht. Ist Passwortanmeldung dort
gesperrt, schlägt die Verbindung mit einer Diagnose fehl.

## Komponenten installieren oder aktualisieren

Das Speichern einer Verbindung kopiert noch keine Dateien auf den Linux-
Rechner. Dafür dient der Menüpunkt unter `NVDA-Menü → Werkzeuge`:

```text
Neovim Access Link: Install or update components...
```

Der Ablauf ist:

1. Der Auswahldialog listet „This computer“ und alle gespeicherten Linux-
   Verbindungen als beschriftete Checkboxen. Linux-Einträge nennen Anzeigename,
   Konto, Host, Port und Anmeldeart. Anfangs ist
   keine Verbindung ausgewählt.
2. Die initial fokussierte Checkbox „Select all connections“ wählt alle Ziele
   aus oder ab. Alternativ kreuzt der Anwender eine oder mehrere Verbindungen
   einzeln an. Sobald alle einzeln markiert sind, wird auch die Sammelcheckbox
   aktiviert; beim Demarkieren eines Eintrags wird sie wieder deaktiviert.
   „OK“ verlangt mindestens eine ausdrückliche Auswahl.
3. Bei Passwortanmeldung folgt je ausgewählter Verbindung der zugängliche
   Passwortdialog. Wird eine einzelne Passwortabfrage abgebrochen, laufen die
   übrigen gewählten Aktualisierungen weiter und das ausgelassene Ziel erscheint
   als fehlgeschlagen in der Ergebnisübersicht.
4. Für „This computer“ kopiert das Add-on außerhalb des NVDA-Hauptthreads nur
   das eingebettete Plugin atomar nach
   `%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda`. Für Linux
   überträgt es das enthaltene Benutzerpaket nacheinander und installiert:

   ```text
   ~/.local/bin/nvim-nvda-bridge
   ~/.local/share/nvim/site/pack/nvim-nvda/start/nvim-nvda
   ```

5. Ein abschließender, nicht blockierender und von NVDA lesbarer Ergebnisdialog
   gruppiert erfolgreiche und fehlgeschlagene Verbindungen. Jede Zeile nennt
   Anzeigename und SSH-Ziel; bei Fehlern kommt ein kurzer Grund hinzu.

Die Installation benötigt weder Administrator- noch Root-Rechte und verändert
weder die Windows-Neovim-Konfiguration noch `sshd_config` oder die SSH-
Konfiguration. Sie gilt nur für ausdrücklich ausgewählte Ziele.

Nach einer Änderung am Neovim-Plugin oder an der Linux-Bridge muss Neovim auf
dem betreffenden Ziel einmal neu gestartet werden. Eine reine Änderung am
NVDA-seitigen Code erfordert keine erneute Linux-Installation.

## Komponenten vollständig entfernen

Der Menüpunkt unter `NVDA-Menü → Werkzeuge` lautet:

```text
Neovim Access Link: Remove components...
```

Neovim muss auf den gewählten Zielen vorher beendet werden. Das Add-on beendet
oder verändert keine laufende Neovim- oder tmux-Sitzung. Der Dialog verwendet
dieselben zugänglich beschrifteten Einzelcheckboxen und die initial fokussierte
Checkbox „Select all connections“ wie die Installation. Anfangs ist kein Ziel
ausgewählt. Passwortabfragen, Hintergrundverarbeitung, Fortschrittsmeldungen
und die abschließende Ergebnisübersicht funktionieren ebenfalls entsprechend.

Auf „This computer“ wird ausschließlich das installierte Plugin entfernt:

```text
%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda
```

Auf jedem ausgewählten Linux-Konto entfernt das Add-on ausschließlich seine
eigenen Benutzerkomponenten und den temporären Installationsbereich:

```text
~/.local/bin/nvim-nvda-bridge
~/.local/share/nvim/site/pack/nvim-nvda
~/.local/share/nvim-nvda
~/.cache/nvim-nvda-install
```

Bereits fehlende Komponenten gelten als erfolgreich entfernt. Gespeicherte
Verbindungsprofile, Neovim-Konfiguration, SSH-Schlüssel und -Konfiguration,
andere Plugins und Sitzungsdaten bleiben erhalten. Deshalb kann dieselbe
Verbindung später direkt wieder für eine Installation ausgewählt werden.

## Mehrere Hosts, Konten und Neovim-Sitzungen

Jedes gespeicherte Verbindungsprofil besitzt eigene Werte für Host, Port,
Linux-Benutzer, Schlüssel und Anmeldeart. Dadurch können unterschiedliche
Rechner und mehrere Konten auf demselben Rechner unabhängig verwaltet werden.

Der schnellste Verbindungsweg ist F12 im fokussierten Neovim. NVDA fängt diese
Geste technisch ab, reicht sie zuerst an Windows Terminal, tmux und Neovim
weiter und prüft anschließend die passende lokale oder entfernte
dateibasierte Sitzungsregistrierung. Neovim markiert seine private
JSON-Sitzungsdatei dabei still; es
erscheint keine Neovim-Statusmeldung. Nur die jüngste, höchstens 15 Sekunden
alte Markierung wird verbunden. Interne Sitzungs-IDs, Fenstertitel und
Terminaltext werden nicht ausgewertet.

Bei eingeschaltetem Dienst autorisiert jeder physische F12-Druck genau einen
Zuordnungsversuch für das fokussierte Windows-Terminal-Control. Bei einem neuen
Control vergleicht das Add-on die Claim-Sequenz der lokalen Sitzungsdateien und aller
bei der Aktivierung erfolgreich erfassten SSH-Profile. Nur die durch den
aktuellen Tastendruck veränderte Sitzung wird verbunden. Ohne frischen Treffer
bleiben Shells und Dateimanager nativ: keine Bindung, kein Dialog und keine
Unterdrückung.

Nach der Zielauswahl und dem physischen F12-Nachweis fragt das Add-on den
gewählten Host nach frisch markierten Neovim-Sitzungen:

- genau eine Sitzung wird automatisch verwendet;
- bei mehreren Sitzungen erscheint eine Auswahl mit Name und
  Arbeitsverzeichnis;
- bei gleichen Arbeitsverzeichnissen kann ein optionaler Name über
  `NVIM_NVDA_SESSION_NAME` oder `:NvimNvdaSessionName` gesetzt werden;
- unbenannte gleiche Sitzungen erhalten Startzeit und laufende Nummer, bereits
  verwendete Sitzungen den Zusatz „bereits verbunden“;
- interne numerische Sitzungskennungen müssen nicht eingegeben werden.

Der NVDA-Befehl „Server wählen und dieses Terminal mit einer neuen Neovim-Sitzung verbinden“ kann
unter „NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link“ frei belegt werden. Er
fragt zuerst das Verbindungsziel ab und gibt danach genau das fokussierte
Control für den nächsten physischen F12-Nachweis vor. So bleibt der Nachweis auch bei
Passwortprofilen und Sonderfällen erhalten. Erst der frische Claim bestimmt die
Sitzung; bei mehreren echten Treffern kann eine Auswahl nach Name und
Arbeitsverzeichnis erscheinen. Interne IDs und Fenstertitel werden nicht
verwendet.

Die frei belegbaren Befehle dieser Kategorie sind auch sichtbar, wenn der
Dialog aus einer anderen Anwendung geöffnet wurde. Bei der Ausführung prüft
das Add-on das aktuell fokussierte UIA-Control erneut. Außerhalb eines
eindeutig erkannten Windows-Terminal-Controls wird die eigene Tastenkombination
unverändert weitergegeben und keine Neovim-Aktion ausgelöst.

Nach erfolgreicher Verbindung fragt das Add-on bei Windows Terminal optional,
ob diese Verbindung für das Terminal-Control gemerkt werden soll. Bei „Ja“ kann
anschließend zwischen so verbundenen Fenstern, Tabs und Panes gewechselt werden, ohne den Dialog
erneut zu öffnen. Die Zuordnung gilt nur bis NVDA oder Windows Terminal beendet
wird und wird nicht in einem Einstellungsprofil gespeichert. „Nein“ lässt den
bisherigen expliziten Ablauf unverändert.

Der frei belegbare Befehl „Temporäre Neovim-Verbindung für das fokussierte
Terminal vergessen“ entfernt die Zustimmung für den aktuellen Tab. Kann keine
stabile `TermControl`-Runtime-ID gelesen werden, erscheint die Nachfrage nicht.

Weitere Befehle zum ausdrücklichen Verbinden, Trennen und Vergessen einer
temporären Terminalbindung können unter `NVDA-Menü → Optionen → Tastenbefehle…
→ Neovim Access Link` mit eigenen Tastenkombinationen belegt werden.

Dort werden auch die vier Copy/Paste-Befehle frei belegt. Sie ersetzen weder
Windows-Terminals eigene Auswahl noch dessen `Ctrl+Shift+C`/`Ctrl+Shift+V`.
Jeder Aufruf ist eine einzelne, auf die aktuelle Terminal-Control-Bindung und
den aktuellen Neovim-Zustand korrelierte Aktion. Bei einem Fokus-, Tab-, Pane-,
Buffer- oder Moduswechsel wird eine verspätete Antwort verworfen.

## Speicherung und Datenschutz

Die Add-on-Einstellungen werden im nativen Abschnitt `nvimNvdaAccess` der
NVDA-Benutzerkonfiguration gespeichert und unterstützen dadurch Vererbung,
manuelle Profile und Profil-Auslöser. Enthalten sind unter anderem:

- Rückmeldungsmodi;
- Auswahl der Ausgabe beim Sitzungsfokus;
- gespeicherte Verbindungsprofile;

Nicht gespeichert werden:

- SSH-Passwörter;
- private Schlüsseldateien selbst;
- Schlüsselpassphrasen;
- Editor- oder Buffertext als Teil der Einstellungen.

Der eingetragene Schlüsselpfad ist lediglich ein Verweis auf eine vorhandene
Windows-Datei. Diagnoseberichte enthalten Verbindungszustände und Fehlerarten,
redigieren aber Passwörter, Tokens und Editorinhalte.

## Empfohlene Grundeinstellung

Für einen ersten Test empfiehlt sich:

1. Ein eigenes NVDA-Konfigurationsprofil für Neovim anlegen, falls Zeichen-,
   Wort-, Einrückungs- oder Rechtschreiboptionen von anderen Anwendungen
   abweichen sollen.
2. Dieses Profil über NVDAs regulären Profilmechanismus aktivieren und erst
   danach den Add-on-Einstellungsdialog öffnen.
3. `Global action feedback` zunächst auf `Both Speech and Tones` stellen.
4. Einzelne zu häufige Rückmeldungen danach gezielt auf `Speech`, `Tones` oder
   `Off` reduzieren.
5. Für lokales Neovim „This computer“ wählen. Für Linux eine Verbindung mit
   `Use OpenSSH setup` anlegen, wenn Windows-SSH bereits ohne Passwort
   funktioniert; sonst bewusst die Passwortoption wählen.
6. Die Komponenten über den separaten Installationsmenüpunkt auf genau diesem
   Ziel installieren.

## Fehlerbehebung

### Die Verbindungsliste ist leer

Mit `Add connection...` zunächst mindestens eine Linux-Verbindung anlegen und
den übergeordneten Einstellungsdialog mit `Apply` oder `OK` speichern.

### Installation meldet, dass zuerst eine Verbindung angelegt werden muss

Das Installationsmenü verwendet ausschließlich gespeicherte Verbindungen.
Wurde eine Verbindung gerade im noch geöffneten Einstellungsdialog angelegt,
muss sie zuerst mit `Apply` oder `OK` gespeichert werden.

### OpenSSH-Anmeldung schlägt fehl

Die Anmeldung zunächst in Windows PowerShell mit demselben Benutzer, Host und
Port prüfen. Hostschlüssel und Schlüsselpassphrasen müssen dort bereits
bestätigt beziehungsweise über ssh-agent verfügbar sein.

### Passwortanmeldung schlägt fehl

Prüfen, ob dasselbe Konto mit Passwort über Windows OpenSSH erreichbar ist und
ob der Server Passwortanmeldung zulässt. Das Add-on nimmt keine Änderung an der
Serverkonfiguration vor.

### Die falsche Neovim-Sitzung ist aktiv

Das gewünschte Terminal beziehungsweise tmux-Fenster fokussieren und den frei
belegten NVDA-Befehl zum Verbinden aufrufen. Danach Server und gegebenenfalls
Sitzung im Dialog auswählen.

### Diagnoseinformationen kopieren

Unter `NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link` kann dem
Befehl zum Kopieren des Diagnoseberichts eine Tastenkombination zugewiesen
werden. Der Bericht ist für Supportanfragen vorgesehen und redigiert
Quelltextzeilen sowie Zugangsdaten.
