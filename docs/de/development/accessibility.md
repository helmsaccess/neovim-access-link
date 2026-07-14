# Funktionsmatrix

Der Stand dieser Matrix ist Alpha bis Beta. Ein Eintrag bedeutet, dass die
Funktion implementiert und überwiegend automatisiert geprüft ist, nicht dass
bereits jede reale Konfiguration praktisch abgenommen wurde. Insbesondere
Braille wurde noch nicht mit echter Hardware getestet und enthält sehr
wahrscheinlich Fehler; Hardwaretests und Korrekturen sind ein wichtiges TODO.

| Funktion | Ereignisquelle | benötigte Metadaten | NVDA-Ausgabe | implementiert | getestet |
|---|---|---|---|---|---|
| Moduswechsel | `ModeChanged` + `nvim_get_mode()` | Modus roh/kanonisch | Modus oder Ton | ja | automatisiert und Windows/NVDA |
| Cursor, Zeichen | `CursorMoved`/`CursorMovedI` | Byte-, Zeichen-, virtuelle Spalte; Zeile | Zeichen | ja | automatisiert und Windows/NVDA |
| Zeilennavigation | Cursorereignis + Zustandsdifferenz | alte/neue Position, Zeilentext | neue Zeile | ja | automatisiert und Windows/NVDA |
| Wortnavigation | Zustandsdifferenz | Cursor, Wortgrenzen, Zeilentext | neues Wort und Cursorzeichen | ja | automatisiert und Windows/NVDA |
| Visual-Auswahl | Mode/Cursor + `getregion()`/virtuelle Spalten | Typ, Anker, Cursor, Text je Zeile | neuer/entfernter Text; vollständiger Block | ja | echtes TUI, automatisiert und Windows/NVDA |
| Buffer/Fenster/Tabs | `BufEnter`/`WinEnter`/`TabEnter` | Name, Typ, Index, Anzahl, Flags | Kontext und Status | ja | echtes TUI und Speech-Test |
| Eingebettetes Terminal | `buftype=terminal` + Modus | Buffer- und Modusstatus | nativer Passthrough bei direkter Eingabe; strukturiert im Terminal-Normalmodus | ja | Gate-, Add-on- und echter TUI-Test |
| Dateimanager | netrw-Dateisystemdaten beziehungsweise öffentliche Plugin-APIs | Name, Pfad, Typ, Markierung, Baumstatus | Sprache und Braille | netrw, Oil, nvim-tree, Neo-tree, mini.files | echtes netrw und API-Attrappen |
| Textänderung | `TextChanged*` + Zustandsdifferenz | changedtick, alter/neuer Text | Eingabe/Löschen/Ersetzen | ja | automatisiert und Windows/NVDA |
| Meldungen und Prompts | UI-Nachrichten, Ex-Status, `confirm()`, `vim.ui.input/select` | Text, Priorität, Promptart, Auswahl | Sprache und Braille | ja; seltene Pager-Varianten weiter zu prüfen | echtes TUI und Speech-Test |
| Commandline | `CmdlineChanged`/`CmdlineLeave` | Inhalt, Modus, Bufferstatus | Modus, Eingabe, Fehler | teilweise | automatisiert und Windows/NVDA |
| Suche | `/`, `?`, `n`, `N` + `searchcount()` | Muster, Richtung, Index, Anzahl, Zeile, Spalte | Trefferzeile, Position und Zeilennummer | ja | echtes TUI und Speech-Test |
| Ersetzen | `CmdlineLeave` + `changedtick` | Substitute-Befehl, Status, Änderung | Bestätigung und Ersetzungston | ja | echtes TUI und Speech-Test |
| Matching Pairs | `%` + Cursorzustand | Gegenzeichen, Zeile, Spalte, Erfolg | Gegenzeichen/Zeile oder Fehlermeldung und Ton | ja | echtes TUI und Speech-Test |
| Folds | `z`-Befehle + `foldclosed()` | Aktion, Ebene, Start-/Endzeile | Foldstatus und Bereich | ja | echtes TUI und Speech-Test |
| Marks | `m`, `'`, `` ` `` + `getpos()` | Name, Zeile, Spalte, exakter Sprung | Setzen oder Zielzeile | ja | echtes TUI und Speech-Test |
| Register/Makros | `TextYankPost`, `RecordingEnter/Leave`, `@` | Register, Typ, Aufnahme-/Wiedergabestatus | kurze Statusausgabe | ja | echtes TUI und Speech-Test |
| Rechtschreibung/Grammatik | Neovim `spell` + `DiagnosticChanged` | Art, Quelle, Bytebereich, Wort | NVDA Sprache/Sound/Braille | ja | natives Spell, Diagnostics, TUI und NVDA-Mocks |
| allgemeine Diagnostics | `DiagnosticChanged`/Diagnostic-Navigation | Quelle, Schwere, Code, Bereich, Text, Position | vollständige Diagnose in Sprache/Braille | ja | ShellCheck-Modell, echtes Neovim und Speech-Test |
| Braille aktuelle Zeile | strukturierter Zustand | Zeilentext, tabstop, Cursor | Liblouis-Region | ja | automatisiert |
| Braille Auswahl | `selectionChanged` + `vim.region()` | zeilenlokale Bytegrenzen | Punkte 7+8 durch NVDA | ja | automatisiert, nicht Hardware |
| Braille Routing | Routingtaste | Braille-zu-Text-Offset, validierter Rückkanal | Cursorbewegung | ja | automatisiert, nicht Hardware |
| Modus-Earcons | `modeChanged` | kanonischer Modus | NVDA `focusMode.wav`/`browseMode.wav`, im RAM vorgeladen | ja | automatisiert |
| Einrückung | Zeilentext + `shiftwidth` | vorherige/neue Einrückung | NVDA-Modus Sprache/Töne/Beides, semantische Ebene | ja | automatisiert |
| Completion-Menü | `CompleteChanged`/`complete_info()` | Kandidat, Index, Anzahl, Typ, Parameter | Sprache, Braille, NVDA-Vorschlagsklänge | ja | echtes TUI und Windows/NVDA |
| Command-line-Wildmenu | `ext_popupmenu` | Kandidat, Index, Anzahl | Standard-Menüausgabe und Klänge | ja | echtes TUI automatisiert |
| `vim.ui.select/input` | zentrale Neovim-API | Prompt, Einträge, Ergebnis/Abbruch | Sprache, Braille und Menüklänge | ja | echtes TUI automatisiert |
| LSP-Signatur | `textDocument/signatureHelp` | Signatur, aktiver Parameter, Alternativen | Signatur und Parameter | ja | automatisiert |
| nvim-cmp/blink.cmp | Pluginereignisse + öffentliche Abfragen | Kandidaten, Auswahl, Typ, Dokumentation | Standard-Menüausgabe | ja | API-Attrappen; reale Pluginprüfung offen |
| Quickfix/Location List | stabile Fensterdaten | Listentyp, aktuelle Zeile | Typ und Eintrag | ja | echtes TUI und Speech-Test |
| Ex-Fehler bei `:q` | `CmdlineLeave` + Bufferstatus | Kommando, `modified` | E37 mit Hinweis auf Speichern oder `:q!` | ja | echtes TUI automatisiert |

## Einrückung

Einrückung wird wie bei NVDA-Dokumenten nur gemeldet, wenn sie sich gegenüber
der vorherigen Zeile ändert. Die NVDA-Einstellung unter
„Dokument-Formatierungen“
„Zeileneinrückung“ steuert die Ausgabe:

- „Aus“ erzeugt keine zusätzliche Ausgabe.
- „Sprache“ meldet `indentation level N`; die Ebene wird aus Neovims
  `shiftwidth` berechnet.
- „Töne“ verwendet NVDA-kompatibel 220 Hz als Grundton und je Leerzeichen einen
  Viertelton beziehungsweise je Tabulator vier Vierteltöne mehr.
- „Sprache und Töne“ kombiniert beide Ausgaben.

Der 220-Hz-Grundton für keine Einrückung wird nur beim Übergang von einer
eingerückten auf eine nicht eingerückte Zeile ausgegeben, nicht fortlaufend auf
jeder Zeile der Ebene null. Die konfigurierte NVDA-Einrückungstondauer wird
übernommen.

## Rechtschreibung und Grammatik

Die Ausgabe folgt NVDA 2026.1.1 statt eine eigene Option einzuführen:

- `reportSpellingErrors2` steuert Sprache, Sound und Braille unabhängig.
- Der Sound ist NVDA-eigenes, beim Add-on-Start in den RAM geladenes
  `waves/textError.wav`.
- Der Tippton wird nur nach Abschluss eines fehlerhaften Wortes gespielt, wenn
  NVDA „Sound für Rechtschreibfehler während der Eingabe“ aktiviert hat und der
  Sprachmodus weder „Aus“ noch „Bei Bedarf“ ist.
- Zeichen- und Wortnavigation melden Eintritt und Austritt aus einem Fehler;
  Zeilenlesen meldet vorhandene Fehler, auch wenn der Cursor nicht darin steht.
- Braille verwendet NVDA-konform `⠑`/`⡑` für Rechtschreib- und `⠛`/`⡛` für
  Grammatikfehler.

Direkt unterstützt wird `:setlocal spell`. Außerdem werden Diagnostics der
Quellen Spellwarn, CSpell/cspell-lsp, Codespell, Typos, LTeX/MORFOLOGIK und
Harper erkannt. Damit ist insbesondere `spellwarn.nvim` passend: Es überführt
Neovims eigene, `spelllang`- und `spellfile`-abhängige Ergebnisse in die
offizielle Diagnostic-API. Das ältere `cspell.nvim` ist archiviert; dessen
Repository empfiehlt inzwischen cspell-lsp, Typos oder Harper. Coc-eigene
Diagnostics sind nur zugänglich, wenn sie zusätzlich nach `vim.diagnostic`
gespiegelt werden.

Andere Diagnostic-Produzenten können Fehler eindeutig kennzeichnen:

```lua
user_data = { nvim_nvda_kind = "spelling" } -- oder "grammar"
```

## Textpositionen

Neovims Cursor-Spalte wird als nullbasierter UTF-8-Byteoffset übertragen. Der
Protokollkern validiert, dass dieser Offset keine UTF-8-Sequenz teilt, und
berechnet separat die Unicode-Codepoint- und UTF-16-Spalte. Die virtuelle Spalte
muss Neovim liefern, weil sie von Tabs und Anzeigeoptionen abhängt. Codepoints
sind noch keine Graphemcluster: eine kombinierende Marke kann daher ein eigenes
Zeichen sein; die spätere Speech-Planung muss zusammengehörige Grapheme bewusst
behandeln.
