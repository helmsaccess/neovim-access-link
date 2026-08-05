# Einstellungsreferenz

Öffnen Sie `NVDA-Menü → Optionen → Einstellungen… → Neovim Access Link`.
Der Dialog enthält die Registerkarten `Allgemein`, `Rückmeldung`, `Navigation`,
`Braille` und `Verbindungen`.

Die Einstellungen gehören zum aktiven NVDA-Konfigurationsprofil. `Übernehmen`
speichert Änderungen und lässt den Dialog geöffnet; `OK` speichert und schließt
ihn. `Abbrechen` verwirft noch nicht übernommene Änderungen.

## Allgemein

### Globale Aktionsrückmeldung

`Globale Aktionsrückmeldung` steuert allgemeine Meldungen wie Aktivierung,
Verbindungsaufbau, Trennung und Fehler.

| Auswahl | Wirkung |
| --- | --- |
| `Aus` | keine Sprache und kein Klang |
| `Sprache` | nur gesprochene Meldung |
| `Töne` | nur Klang |
| `Sprache und Töne` | Meldung und Klang; Standard |

Einzelne Aktionen auf der Registerkarte `Rückmeldung` besitzen eigene Werte und
werden nicht durch diese Auswahl ersetzt.

### Sitzungsfokus

`Beim Fokussieren oder Wechseln von Puffern in einer Neovim-Sitzung` legt fest,
was Access Link nach einem bestätigten Fokus- oder Bufferwechsel ausgibt.

| Auswahl | Wirkung |
| --- | --- |
| `Keine Ansage` | keine zusätzliche Fokusansage |
| `Aktuelle Zeile` | strukturierte Cursorzeile |
| `Aktueller Kontext, Modus und Verbindungsname` | Datei- oder Spezialkontext, Modus und Verbindung; Standard |

Die Auswahl gilt auch für die Rückkehr aus der Neovim-Befehlszeile und für den
Wechsel aus einem eingebetteten Terminal zurück in einen Editorbuffer.

`Aktiven Funktionsparameter beim Tippen automatisch ansagen` ist standardmäßig
aktiv. Bei verfügbarer LSP-Signaturhilfe spricht Access Link den aktiven
Parameter beim Betreten oder Wechseln eines Arguments. Bewegung innerhalb
desselben Arguments bleibt still. Diese Funktion verwendet Sprache; die
Braillezeile bleibt beim Quelltext.

## Rückmeldung

Für die meisten Einträge stehen `Aus`, `Sprache`, `Töne` und `Sprache und Töne`
zur Verfügung. Diagnoseeinträge bieten nur `Aus` und `Töne`.

| UI-Eintrag | Standard | Gesteuertes Ereignis |
| --- | --- | --- |
| `Wechsel zwischen Einfüge- und Normalmodus` | `Sprache und Töne` | Insert-, Normal-, Terminal- und Befehlszeilenmodus |
| `Text löschen` | `Sprache und Töne` | Zeichen- und Textlöschung |
| `Text ersetzen` | `Sprache und Töne` | Ersetzen von Text |
| `Kopieren und Einfügen` | `Sprache und Töne` | Access-Link-Zwischenablagebefehle |
| `Zeilengrenzen` | `Töne` | Zeilenanfang, Zeilenende und Ursprung der Sprachexploration |
| `Dateigrenzen` | `Sprache und Töne` | Dateianfang und Dateiende |
| `Wechsel in eine andere Zeile` | `Töne` | horizontale Bewegung über eine Zeilengrenze |
| `Fehlende zusammengehörige Klammer` | `Sprache und Töne` | fehlendes Klammerpaar |
| `Diagnosen beim Betreten einer Zeile` | `Töne` | Eintritt in eine Diagnosezeile |
| `Diagnosen an der Cursorposition` | `Töne` | Cursorposition in einer Diagnose oder ausdrückliche leere Abfrage |

Tippecho, Einrückung, Vorschläge, Rechtschreibung und Grammatik folgen den
jeweiligen NVDA-Einstellungen. Access Link fügt dafür keine zweite
Konfiguration hinzu.

## Navigation

Diese Registerkarte bestimmt ergänzende Sprache nach normaler
Neovim-Navigation und nach dem Loslassen der NVDA-Taste im
Sprachexplorationsmodus.

### Normale Navigation

| UI-Eintrag | Auswahl | Standard |
| --- | --- | --- |
| `Wortnavigation` | `Nur Wort`; `Wort und Cursorzeichen` | `Wort und Cursorzeichen` |
| `Zeilennavigation` | `Nur Zeile`; `Zeile und aktuelles Wort`; `Zeile und Cursorzeichen`; `Zeile, aktuelles Wort und Cursorzeichen` | `Zeile und Cursorzeichen` |

Neovims `w`, `b`, `j`, `k` und andere Bewegungsbefehle bewegen weiterhin den
echten Cursor. Diese Einstellungen ändern nur die anschließende Ausgabe.

### Abschluss des Sprachexplorationsmodus

| UI-Eintrag | Auswahl | Standard |
| --- | --- | --- |
| `Nach Wortexploration im Sprachexplorationsmodus` | `Nur Wort`; `Wort und Cursorzeichen` | `Wort und Cursorzeichen` |
| `Nach Zeilenexploration im Sprachexplorationsmodus` | dieselben vier Zeilenoptionen wie oben | `Zeile und Cursorzeichen` |

Die während der Exploration gelesene virtuelle Position bleibt davon
unabhängig. Details stehen unter
[Sprachexplorationsmodus](speech-exploration.md).

## Braille

### Sprachexplorationsmodus

`Braillezeile folgt der Position des Sprachexplorationsmodus` ist standardmäßig
aktiv. Die Braillezeile zeigt während `NVDA+h`, `NVDA+j`, `NVDA+k`, `NVDA+l`
und der wortweisen Varianten die virtuelle Leseposition. Nach dem Loslassen der
NVDA-Taste kehrt sie zum echten Cursor zurück. Deaktivieren Sie die Option,
damit Braille während der Sprachexploration am echten Cursor bleibt.

### Routingtasten

`Routingtaste auf einem Wort zweimal drücken` bietet:

- `Nur Cursor setzen` (Standard),
- `Wort ändern (cw)`,
- `Wort löschen (dw)`.

`Routingtaste auf einer Zeile dreimal drücken` bietet:

- `Nur Cursor setzen` (Standard),
- `Bis Zeilenende ändern (c$)`,
- `Bis Zeilenende löschen (d$)`.

`Zeilenaktion bei Dreifachbetätigung beginnen an` bietet:

- `Routingposition` (Standard),
- `Erstes Zeichen nach der Einrückung`,
- `Zeilenanfang`.

Die Erkennung mehrfacher Betätigungen verwendet NVDAs Zeitlimit für mehrfachen
Tastendruck aus den Tastatureinstellungen.

### Rechtschreibvorschläge

`Rechtschreibvorschläge ab Braillemodul anzeigen` verwendet eine mit 1
beginnende Modulnummer. Standard ist 1. Passt der Vorschlag rechts davon nicht
vollständig, verschiebt Access Link ihn nach links und richtet ihn möglichst am
rechten Rand aus. Eine Position außerhalb der angeschlossenen Braillezeile
verwendet Modul 1.

### Entwicklerinformationen

`Temporäre Entwicklerinformationen ab Braillemodul anzeigen` steuert die
Position für gehaltene Signatur-, Parameter- und Diagnoseansichten. Standard
ist 1. Für Platzmangel und ungültige Positionen gilt dieselbe sichere
Ausrichtung wie bei Rechtschreibvorschlägen.

Die vollständige Bedienung steht unter [Braille-Unterstützung](braille.md).

## Verbindungen

Die Registerkarte enthält gespeicherte SSH-Ziele. Lokales Windows-Neovim
benötigt keinen Verbindungseintrag.

`Gespeicherte Verbindungen` zeigt den gewählten Namen, das SSH-Ziel und einen
vom Standard 22 abweichenden Port. Es gibt keine Standardverbindung.

### Verbindung hinzufügen, bearbeiten oder entfernen

- `Verbindung hinzufügen...` öffnet ein leeres Linux-Verbindungsformular.
- `Verbindung bearbeiten...` öffnet den ausgewählten Eintrag.
- `Verbindung entfernen` löscht den Eintrag nach `Übernehmen` oder `OK` aus dem
  aktuellen NVDA-Profil.

Das Entfernen eines Profils deinstalliert keine Komponenten, löscht keine
Schlüssel und ändert keine OpenSSH-Konfiguration.

### Felder des Linux-Verbindungsformulars

| UI-Feld | Inhalt |
| --- | --- |
| `Verbindungsname` | frei gewählte, eindeutige Bezeichnung |
| `Servername, Adresse oder SSH-Alias` | DNS-Name, IP-Adresse oder OpenSSH-Alias |
| `Linux-Benutzername (optional, wenn in der SSH-Konfiguration festgelegt)` | Konto, unter dem Neovim und Bridge laufen |
| `SSH-Port` | Zahl von 1 bis 65535; Standard 22 |
| `Datei mit privatem Schlüssel (optional)` | Schlüsseldatei für OpenSSH; leer verwendet Konfiguration, Standardschlüssel oder `ssh-agent` |
| `Anmeldemethode` | OpenSSH-Einrichtung oder Passwortabfrage |

`OpenSSH-Einrichtung verwenden (empfohlen: Schlüssel, ssh-agent oder
SSH-Konfiguration)` verwendet die normale Windows-OpenSSH-Konfiguration.

`Beim Verbinden nach dem SSH-Passwort fragen (Passwort wird nicht gespeichert)`
fragt bei Bedarf zugänglich nach dem Linux-Passwort. Das Passwort bleibt nur im
Arbeitsspeicher der aktuellen NVDA-Laufzeit. Der SSH-Server muss
Passwortanmeldung für dieses Konto erlauben.

Installieren oder entfernen Sie Komponenten anschließend über die beiden
Einträge `Neovim Access Link: …` im NVDA-Menü `Werkzeuge`. Der
[Quick Guide](quick-guide.md) beschreibt den Ablauf.

## Empfohlener Ausgangspunkt

Die Standardwerte ergeben einen direkt nutzbaren Ausgangspunkt:

- allgemeine Aktionen, Modus, Bearbeitung, Dateigrenzen, Klammerfehler und
  Zwischenablage über Sprache und Töne;
- Zeilengrenzen, Zeilenwechsel und Diagnosen als kurze Töne;
- Fokus als Kontext, Modus und Verbindungsname;
- Wort- und Zeilennavigation mit Cursorzeichen;
- keine Bearbeitungsaktion durch mehrfaches Braille-Routing;
- Braille folgt der Sprachexploration.

Ändern Sie zunächst nur Rückmeldungen, die sich in Ihrer NVDA-Konfiguration
konkret als zu häufig oder zu knapp erweisen.
