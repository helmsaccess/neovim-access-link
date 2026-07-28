# Menüs und Autovervollständigung

Neovim Access Link gibt Vervollständigungslisten als zugängliche Menüs aus.
NVDA meldet den ausgewählten Eintrag, seine Position und – soweit vorhanden –
Typ, Signatur, Quelle und Kurzbeschreibung. Die standardisierten LSP-Typen
werden lokalisiert. Sprache und Braille verwenden denselben Menüzustand.

## Unterstützte Menüs

Direkt unterstützt wird Neovims eingebautes Popup-Menü. Dazu gehören unter
anderem:

- Schlüsselwort- und Puffervervollständigung,
- Datei- und Wörterbuchvervollständigung,
- `completefunc` und `omnifunc`,
- Neovims LSP-Vervollständigung,
- Plugins, die ihre Kandidaten über Neovims Funktion `complete()` anzeigen.

Zusätzliche Adapter sind für `nvim-cmp` und `blink.cmp` enthalten.
Automatisierte API-Vertragstests decken den aktuellen `nvim-cmp`-Hauptzweig,
`blink.cmp` v1.10.2 und den vorläufigen v2-Zweig ab. `blink.cmp` v2 benötigt
Neovim 0.12 und `blink.lib`; v1 bleibt die stabile Empfehlung. Diese Tests
ersetzen keine praktische Abnahme jeder individuellen Quellen-, Darstellungs-
und Tastenkonfiguration.

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
Vorschläge. Das gilt gleichermaßen für Neovims eingebautes Menü, `nvim-cmp`
und `blink.cmp`. Bei den beiden Pluginadaptern folgt der jeweilige Klang direkt
dem öffentlichen Öffnen- beziehungsweise Schließen-Ereignis, auch wenn die
Kandidaten erst kurz danach verfügbar sind.

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

Nur der ausgewählte Kandidat wird verarbeitet. Auch eine Auswahl jenseits der
ersten 200 Listeneinträge bleibt dadurch zugänglich. Später eintreffende
Dokumentation aktualisiert den Dokumentationsbefehl still und wiederholt die
Auswahlansage nicht.

## Ausführliche Dokumentation lesen

Längere Dokumentation wird nicht bei jedem Auswahlwechsel vollständig
gesprochen. Unter „NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link“
kann dem Befehl zum Lesen der Dokumentation des ausgewählten
Vervollständigungseintrags oder des aktuellen LSP-Hovers eine eigene
Tastenkombination zugewiesen werden. Beim LSP-Hover wird nur die erste
aussagekräftige Zeile automatisch gesprochen und auf Braille angezeigt; der
Befehl liest den vollständigen Inhalt.

Der Befehl funktioniert nur, solange ein Eintrag ausgewählt ist und das
Completion-System Dokumentation bereitstellt oder der aktuelle LSP-Hover
Inhalt enthält.

Bei `nvim-cmp` wird auch nachträglich über `completionItem/resolve` ergänzte
Dokumentation übernommen. `blink.cmp` stellt seine intern aufgelöste Kopie
derzeit nicht über eine öffentliche API bereit. Dort ist ursprünglich am
Kandidaten vorhandene Dokumentation zugänglich; ausschließlich nachgeladene
Dokumentation kann bis zu einer Upstream-Erweiterung fehlen.

Ghost Text ohne sichtbares Completion-Menü ist kein zugängliches Auswahlmenü
und wird von den beiden Adaptern nicht angesagt.

## LSP-Serverstatus

`:NvimNvdaLspStatus` gibt die Namen der LSP-Clients aus, die am aktuellen
Buffer hängen. Ohne Client meldet der Befehl diesen Zustand ausdrücklich.
Automatischer LSP-Fortschritt wird nicht fortlaufend gesprochen; Fehler und
Ergebnisse bleiben über Diagnostics und Neovim-Meldungen zugänglich.

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
