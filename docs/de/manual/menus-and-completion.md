# Suche, Menüs, Completion und Diagnosen

Access Link gibt Neovims strukturierte Menüs und Entwicklungsinformationen über
Sprache und Braille aus. Die Tasten ohne NVDA-Taste bleiben Neovim- oder
Plugin-Befehle. Kombinationen mit NVDA-Taste öffnen ausschließlich die
dokumentierten Access-Link-Ansichten.

## Completion-Menüs

Unterstützt sind:

- Neovims eingebautes Popup-Menü mit `complete()`, `completefunc`, `omnifunc`
  und LSP-Completion;
- `nvim-cmp` über seine öffentliche Auswahl-API;
- `blink.cmp` über öffentliche APIs.

Der genaue automatisierte Prüfstand nach Plugin- und Neovim-Version steht in
der [Kompatibilitätsübersicht](../development/compatibility.md).

Frei gezeichnete Floating Windows und Ghost Text ohne sichtbares Auswahlmenü
sind nicht automatisch zugängliche Menüs.

### Menü bedienen

Neovim oder das Completion-Plugin verarbeitet die Menütasten. Bei Neovims
Standard-Completion sind dies häufig:

- `Ctrl+n`: nächster Eintrag;
- `Ctrl+p`: vorheriger Eintrag;
- `Ctrl+y`: Auswahl übernehmen;
- `Esc`: Menü schließen oder Insert-Modus verlassen.

Access Link ersetzt diese Tasten nicht. Es spricht den von Neovim ausgewählten
Eintrag, Position, Typ, Quelle, Signatur und Kurzbeschreibung, soweit das
Completion-System diese Angaben liefert. Sprache und Braille verwenden
dieselbe Auswahl.

Nach dem letzten Eintrag besitzt Neovims eingebautes Menü einen Zustand ohne
ausgewählten Vorschlag. Der ursprünglich eingegebene Text bleibt erhalten;
`Ctrl+n` wählt danach wieder den ersten Eintrag. Access Link meldet diesen
Zustand ausdrücklich.

NVDAs Einstellung für akustische automatische Vorschläge steuert die Klänge
beim Öffnen und Schließen des Menüs.

### Ausführliche Dokumentation lesen

Weisen Sie unter `NVDA-Menü → Optionen → Tastenbefehle… → Neovim Access Link`
dem Befehl `Dokumentation für den ausgewählten Neovim-Completion-Eintrag oder
LSP-Hover lesen` eine Geste zu.

Der Befehl liest längere Dokumentation, solange der ausgewählte Eintrag oder
der aktuelle LSP-Hover Inhalt bereitstellt. Eine fehlende Beschreibung ist
nicht automatisch ein Fehler: Nicht jedes Completion-System liefert
Dokumentation über seine öffentliche Schnittstelle.

## LSP-Status prüfen

Geben Sie in Neovim ein:

```vim
:NvimNvdaLspStatus
```

Der Befehl nennt die LSP-Clients des aktuellen Buffers oder meldet, dass kein
Client verbunden ist. Er ist ein Neovim-Befehl und enthält keine NVDA-Taste.

## Suchen und Ersetzen

Neovim führt Suche und Ersetzung weiterhin selbst aus. Access Link ergänzt
die zugängliche Rückmeldung:

- Bei aktivem `incsearch` nennt `/Muster` beziehungsweise `?Muster` schon
  während der Eingabe den von Neovim angezeigten Vorschautreffer. Die Meldung
  enthält Trefferposition und -anzahl. Sie nennt außerdem, wenn Neovim die
  Zählung begrenzt hat oder die Suche am anderen Pufferende fortsetzt. Nach
  `Enter` arbeiten `n` und `N` wie in Neovim üblich.
- Bei aktivem `inccommand` gibt eine eingegebene `:substitute`-Ersetzung die
  von Neovim dargestellte Vorschauzeile und die Anzahl betroffener Zeilen über
  Sprache und Braille aus. Das gilt für `inccommand=nosplit` und
  `inccommand=split`. Bei großen Puffern kennzeichnet die Meldung eine
  unvollständige Zählung. Neovim bietet diese Livevorschau nur für einen
  direkten Ersetzungsbefehl im aktuellen Buffer, nicht für `:bufdo`, `:argdo`
  oder Ergebnislisten-Schleifen.
- Nach einer bestätigten Suche meldet Access Link eine aktive
  Suchhervorhebung. `:nohlsearch` oder `:set nohlsearch` melden, dass sie
  aufgehoben wurde.
- Ein bestätigtes Ersetzen wie `:%s/alt/neu/gc` nennt in jeder nativen
  `y/n/a/q/l`-Abfrage die betroffene Zeile und Position. Die Antwort verarbeitet
  ausschließlich Neovim.
- Nach einer Ersetzung verwendet Access Link Neovims eigene Ergebnismeldung.
  Liefert Neovim wegen seiner `report`-Einstellung keine Anzahl, nennt die
  Meldung stattdessen die beobachtete Anzahl geänderter Zeilen. Diese Anzahl
  ist keine selbst berechnete Zahl einzelner Ersetzungen.
- `:vimgrep` und `:grep` melden die Größe ihrer Quickfix-Liste;
  `:lvimgrep` und `:lgrep` entsprechend die Positionsliste. In einem geöffneten
  Ergebnisfenster nennt die Navigation die aktuelle Trefferposition.
- Ersetzungen über `:cdo`, `:cfdo`, `:ldo`, `:lfdo`, `:argdo` oder `:bufdo`
  werden nach Abschluss einmal zusammengefasst. Die Meldung nennt beobachtete
  geänderte und noch ungespeicherte Buffer, nicht jede Zwischenänderung. Die
  dabei von Neovim intern durchlaufenen Buffer werden nicht als Fokuswechsel
  ausgegeben. Neovim bestimmt weiterhin selbst, welche Quickfix-Dateien,
  Argumente oder gelisteten Buffer der jeweilige Befehl besucht.

Diese Unterstützung gilt für Neovims native Befehle. Eigene Suchoberflächen
eines Plugins benötigen einen öffentlichen strukturierten Zustand oder einen
eigenen Adapter.

## Symbole mit LSP umbenennen

Verwenden Sie Neovims vorhandenen LSP-Rename-Befehl oder Ihr eigenes Mapping;
in Neovim 0.12 ist dafür standardmäßig `grn` vorgesehen. Der verbundene
Sprachserver muss `textDocument/rename` unterstützen.

Access Link ersetzt weder den Rename-Dialog noch den LSP-Handler. Es beobachtet
Neovims öffentliche `LspRequest`-Ereignisse und die tatsächlich geänderten
Buffer. Nach Abschluss nennt es die beobachtete Anzahl geänderter und noch
ungespeicherter Buffer, ohne interne Text-, Cursor- oder Fokuswechsel einzeln
auszugeben. Ohne beobachtete Änderung behauptet es keinen Erfolg.

## Funktionsparameter beim Schreiben

Wenn ein LSP-Server Signaturhilfe liefert, spricht Access Link im Insert-Modus
den aktiven Parameter beim Eintritt in einen Funktionsaufruf und beim Wechsel
des Arguments. Bewegung innerhalb desselben Arguments bleibt still. Bei
verschachtelten Aufrufen gilt der innerste Aufruf.

Die automatische Ausgabe ist reine Sprache. Schalten Sie sie unter
`Allgemein → Aktiven Funktionsparameter beim Tippen automatisch ansagen` aus,
wenn Sie diese Rückmeldung nicht benötigen.

## Signaturen und Parameter auf Abruf

Setzen Sie den Cursor auf einen Funktionsnamen oder die zugehörige öffnende oder
schließende Klammer:

1. Drücken Sie `NVDA+Leertaste`.
2. Lassen Sie nur die Leertaste los und halten Sie die NVDA-Taste weiter.
3. Verwenden Sie `NVDA+h` und `NVDA+l` für Parameter.
4. Verwenden Sie `NVDA+k` und `NVDA+j` für mehrere Signaturen.
5. Verwenden Sie die Braille-Navigationstasten, um lange Inhalte zu lesen.
6. Lassen Sie die NVDA-Taste los, um zur Editorzeile zurückzukehren.

Die erste Parameterbewegung nach dem Öffnen oder einem Signaturwechsel zeigt
Parameter 1. Der echte Neovim-Cursor bewegt sich nicht. Sprache nennt die
vollständigen Bezeichnungen; Braille verwendet nur für Strukturangaben kurze
Präfixe wie `S 1 von 2`, `P 1 von 3` und `D:`.

## Diagnosen lesen

Access Link verarbeitet Diagnosen aus Neovims öffentlicher `vim.diagnostic`-
API. Die Daten dürfen von LSP, `nvim-lint`, ALE, `none-ls.nvim` oder einem
anderen Provider stammen. Access Link installiert und startet selbst keine
Linter.

Bei einem Diagnosesprung nennt Access Link Quelle, Schwere, vorhandenen Code,
Meldung und Position. Hintergrundaktualisierungen und Tippen bleiben still.
Fehler und Warnungen dürfen bei gezielter Navigation einen konfigurierten
Klang auslösen; Informationen und Hinweise bleiben klanglos.

### Diagnosen ohne Cursorbewegung erkunden

1. Drücken Sie `NVDA+Umschalt+Leertaste`.
2. Lassen Sie nur die Leertaste los und halten Sie die NVDA-Taste weiter.
3. Wechseln Sie mit `NVDA+k` und `NVDA+j` zwischen Diagnosen am Cursor und auf
   der aktuellen Zeile.
4. Lassen Sie die NVDA-Taste los, um zur Editorzeile zurückzukehren.

Ohne Treffer meldet Access Link `keine Diagnose` und spielt den konfigurierten
neutralen Bestätigungsklang. Der echte Neovim-Cursor bleibt stehen.

### Neovim-Diagnosebefehle

Für eigene Neovim-Mappings stehen bereit:

- `:NvimNvdaDiagnosticPrevious`;
- `:NvimNvdaDiagnosticNext`;
- `:NvimNvdaDiagnosticFirst`;
- `:NvimNvdaDiagnosticLast`;
- `:NvimNvdaDiagnosticCurrent`.

Diese Befehle ändern keine vorhandenen Mappings. Mehrere Diagnosen derselben
Position bleiben einzeln erreichbar; die Navigation springt nach dem letzten
Eintrag wieder zum ersten und umgekehrt.

## Wenn ein Menü oder LSP still bleibt

1. Prüfen Sie die Access-Link-Verbindung.
2. Prüfen Sie mit `:NvimNvdaLspStatus`, ob der aktuelle Buffer einen LSP-Client
   besitzt.
3. Testen Sie Neovims eingebautes Completion-Menü, um ein Problem des
   Completion-Plugins einzugrenzen.
4. Prüfen Sie, ob das Menü tatsächlich einen ausgewählten Eintrag besitzt.
5. Kopieren Sie den Diagnosebericht, solange das betroffene Menü geöffnet ist.

Die Einrichtung von Servern und Lintern steht unter
[LSP, Completion und Linter einrichten](language-tools.md).
