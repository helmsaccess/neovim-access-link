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
Auswahlansage nicht. Bei Neovims eingebauter LSP-Completion kann diese
Dokumentation nach dem letzten `CompleteChanged`-Ereignis eintreffen und nur
im internen Vorschaufenster landen. Wenn der ursprüngliche LSP-Kandidat noch
keine Dokumentation enthält, löst Access Link deshalb genau den ausgewählten
Kandidaten zusätzlich über die öffentliche LSP-Schnittstelle
`completionItem/resolve` auf. Ein Auswahlwechsel oder das Schließen des Menüs
verwirft die alte Anfrage. Öffnen, Auswahl, Schließen und Klänge bleiben
vollständig an Neovims Menüereignisse gebunden.

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

Bei Neovims eingebauter LSP-Completion löst Access Link fehlende Dokumentation
selbst über `completionItem/resolve` auf. Der `nvim-cmp`-Adapter liest dagegen
den vom Plugin bereits aufgelösten öffentlichen `entry.completion_item`.
`blink.cmp` stellt seine intern aufgelöste Kopie derzeit nicht über eine
öffentliche API bereit. Dort ist ursprünglich am Kandidaten vorhandene
Dokumentation zugänglich; ausschließlich nachgeladene Dokumentation kann bis
zu einer Upstream-Erweiterung fehlen.

Ghost Text ohne sichtbares Completion-Menü ist kein zugängliches Auswahlmenü
und wird von den beiden Adaptern nicht angesagt.

## LSP-Serverstatus

`:NvimNvdaLspStatus` gibt die Namen der LSP-Clients aus, die am aktuellen
Buffer hängen. Ohne Client meldet der Befehl diesen Zustand ausdrücklich.
Automatischer LSP-Fortschritt wird nicht fortlaufend gesprochen; Fehler und
Ergebnisse bleiben über Diagnostics und Neovim-Meldungen zugänglich.

## Funktionsparameter auf Abruf

Mit `NVDA+Umschalt+P` fragt Access Link die Signaturhilfe an der aktuellen
Cursorposition ab. Solange mindestens eine NVDA-Taste gedrückt bleibt, stehen
die Informationen dauerhaft auf der Braillezeile. `NVDA+h/l` schaltet durch
die Parameter, `NVDA+k/j` durch mehrere Signaturen. Die echte Cursorposition
bleibt unverändert. Beim Loslassen der letzten NVDA-Taste wird die Anzeige
geschlossen und die normale Editorzeile wiederhergestellt.

Beim Öffnen spricht Access Link nur die ausgewählte Signatur und ihre
vorhandene Dokumentation. `NVDA+h/l` spricht und zeigt ausschließlich den
vorherigen beziehungsweise nächsten Parameter dieser Signatur;
`NVDA+k/j` spricht und zeigt ausschließlich die vorherige beziehungsweise
nächste Signatur samt ihrer Dokumentation. Jede Signatur besitzt eine eigene
Parameterauswahl, die bei Parameter 1 beginnt und beim Signaturwechsel nicht
mit einer anderen Signatur vermischt wird. Sprache und Braille zeigen damit
immer dieselbe, gerade gewählte Achse. Da die Signaturansicht keinen Parameter
zeigt, blendet der erste Druck auf `NVDA+h` oder `NVDA+l` zunächst den für
diese Signatur ausgewählten Parameter ein; erst weitere Betätigungen wechseln
vorwärts oder rückwärts. Passt der Inhalt nicht vollständig
auf die Braillezeile, blättern sowohl
die üblichen Vor-/Zurück-Tasten als auch die Befehle für die nächste oder
vorherige Braillezeile ausschließlich innerhalb dieser Information. Am ersten
und letzten Teil bleibt die Anzeige stehen; erst das Loslassen der NVDA-Taste
stellt den Quelltext wieder her.

Access Link verwendet zuerst die öffentliche LSP-Signaturhilfe. Liefert sie
nichts, dient LSP-Hover als unstrukturierter Rückfall. Die Antwort wird nur
angenommen, wenn Instanz, Terminal, Buffer, Fenster, Tab, Textstand und
Cursorposition noch exakt der Anfrage entsprechen.

## Linter und Diagnostics

Access Link verarbeitet Diagnosen aus Neovims öffentlicher
`vim.diagnostic`-API. Dabei ist unerheblich, ob sie von einem LSP-Server,
`nvim-lint`, ALE, `none-ls.nvim` oder einem anderen Diagnoseproduzenten
stammen. Das Add-on installiert und startet selbst keine Linter. Der Linter,
seine ausführbare Datei und die Zuordnung zu Dateitypen werden in Neovim
eingerichtet.

Automatisierte reale Läufe decken derzeit diese Mindestmatrix ab:

- C mit Clang-Tidy;
- Python mit Ruff;
- Bash mit ShellCheck;
- Go mit Staticcheck;
- Rust mit Clippy;
- Ruby mit RuboCop;
- Markdown mit `markdownlint-cli2`;
- jeweils über `nvim-lint` und ALE unter Neovim 0.10.1 und 0.12.3;
- außerdem den LSP-Brückenpfad von `none-ls.nvim` mit einer eingebauten
  Diagnosequelle auf beiden Neovim-Versionen.

Quelle, Schwere, vorhandener Code, Meldung und Position werden beim
Diagnosesprung gemeinsam in Sprache und Braille ausgegeben. Änderungen eines
Linters im Hintergrund lösen keine fortlaufende Sprachmeldung aus.

Mit `NVDA+Umschalt+E` werden zuerst Diagnosen direkt am Cursor und danach
weitere Diagnosen auf derselben Zeile abgefragt. Solange die NVDA-Taste
gehalten wird, schaltet `NVDA+k/j` zyklisch durch die Einträge, ohne den
Editorcursor zu bewegen. Fehler und Warnungen können außerdem beim Betreten
einer betroffenen Zeile und an jeder durch ausdrückliche Cursornavigation
erreichten Position innerhalb eines exakten Diagnosebereichs einen kurzen
Klang auslösen. Tippen und reine Hintergrundaktualisierungen bleiben stumm.

Für eigene Neovim-Mappings stehen folgende Befehle bereit:

- `:NvimNvdaDiagnosticPrevious`;
- `:NvimNvdaDiagnosticNext`;
- `:NvimNvdaDiagnosticFirst`;
- `:NvimNvdaDiagnosticLast`;
- `:NvimNvdaDiagnosticCurrent`.

Sie ändern keine vorhandenen Mappings. Unter neueren Neovim-Versionen werden
auch Sprünge über die öffentliche native Diagnostic-API erkannt. Direkt
getippte `[d`-/`]d`-Sprünge bleiben erkennbar, wenn das Mapping einen
aufrufspezifischen Callback verwendet. Die Access-Link-Befehle durchlaufen
jede einzelne Diagnose in der angekündigten Reihenfolge. Liefern mehrere
Provider Diagnosen an derselben Position, bleiben diese deshalb einzeln mit
Quelle, Index und Gesamtzahl erreichbar. Nach dem letzten Eintrag wird zum
ersten umgebrochen und umgekehrt. Produzenten,
die Ergebnisse ausschließlich in einer privaten Liste oder nur als
Bildschirmdekoration halten, sind erst zugänglich, wenn sie diese nach
`vim.diagnostic` spiegeln.

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
