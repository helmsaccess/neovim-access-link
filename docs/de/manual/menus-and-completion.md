# Menüs und Autovervollständigung

Neovim Access Link gibt Vervollständigungslisten als zugängliche Menüs aus.
NVDA meldet den ausgewählten Eintrag, seine Position und – soweit vorhanden –
Typ, Signatur und Kurzbeschreibung. Sprache und Braille verwenden denselben
Menüzustand.

## Unterstützte Menüs

Direkt unterstützt wird Neovims eingebautes Popup-Menü. Dazu gehören unter
anderem:

- Schlüsselwort- und Puffervervollständigung,
- Datei- und Wörterbuchvervollständigung,
- `completefunc` und `omnifunc`,
- Neovims LSP-Vervollständigung,
- Plugins, die ihre Kandidaten über Neovims Funktion `complete()` anzeigen.

Zusätzliche Adapter sind für `nvim-cmp` und `blink.cmp` enthalten. Da diese
Plugins eigene Oberflächen und unterschiedliche Versionen besitzen, sollte ihr
Verhalten mit der konkret installierten Konfiguration geprüft werden.

Beliebige frei gezeichnete Floating Windows sind nicht automatisch ein
zugängliches Menü. Das erzeugende Plugin muss dafür Neovims Standardmenü oder
eine unterstützte Adapter-Schnittstelle verwenden.

## Bedienung

Das Menü wird mit den normalen Neovim-Tasten bedient. Die konkrete Belegung
hängt von der Neovim-Konfiguration ab. Bei Neovims Standardvervollständigung
sind häufig:

- `Ctrl+N`: nächster Eintrag,
- `Ctrl+P`: vorheriger Eintrag,
- `Ctrl+Y`: Auswahl übernehmen,
- `Esc`: Menü schließen beziehungsweise Insert-Modus verlassen.

Das Add-on ersetzt diese Tasten nicht. Es beobachtet nur den von Neovim
gemeldeten Menüzustand. Eigene Mappings eines Completion-Plugins bleiben daher
wirksam.

Beim Öffnen und Schließen können NVDAs übliche Vorschlagsklänge abgespielt
werden. Dafür gilt NVDAs Einstellung zur akustischen Meldung automatischer
Vorschläge.

## Gesprochene Informationen

Ein Eintrag kann beispielsweise so ausgegeben werden:

```text
printf, 1 von 5, Funktion, Parameter format, arguments
```

Nicht jedes Completion-System liefert alle Felder. Eine fehlende Signatur oder
Beschreibung ist daher nicht automatisch ein Fehler des Add-ons.

Identische Auswahlereignisse werden nicht wiederholt. Dadurch wird derselbe
Eintrag nicht mehrfach gesprochen, wenn ein Completion-Plugin seine Oberfläche
ohne tatsächlichen Auswahlwechsel neu zeichnet.

## Ausführliche Dokumentation lesen

Längere Dokumentation wird nicht bei jedem Auswahlwechsel vollständig
gesprochen. Unter „NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link“
kann dem Befehl zum Lesen der Dokumentation des ausgewählten
Vervollständigungseintrags eine eigene Tastenkombination zugewiesen werden.

Der Befehl funktioniert nur, solange ein Eintrag ausgewählt ist und das
Completion-System Dokumentation bereitstellt.

## Wenn keine Auswahl angesagt wird

1. Prüfen, ob die Neovim-Sitzung tatsächlich verbunden ist.
2. Mit Neovims eingebauter Vervollständigung testen, um ein Problem des
   verwendeten Completion-Plugins auszuschließen.
3. Prüfen, ob das Menü wirklich eine Auswahl besitzt. Manche Plugins öffnen
   zunächst eine Liste ohne markierten Eintrag.
4. Bei `nvim-cmp` oder `blink.cmp` das Plugin und Neovim Access Link
   aktualisieren und Neovim neu starten.
5. Einen Diagnosebericht kopieren, während das Menü geöffnet ist und ein
   Auswahlversuch stattgefunden hat.

Command-line-Wildmenu, `vim.ui.select` und weitere frei gezeichnete Menüs sind
noch nicht in jeder Konfiguration vollständig abgedeckt.
