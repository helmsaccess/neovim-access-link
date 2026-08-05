# Kompatibilität

Diese Seite trennt freigegebene Plattformgrenzen, automatisierte
Pluginverträge und praktische Referenzprüfungen. Ein automatisierter Vertrag
ist keine Zusage für jede Benutzereinstellung oder Darstellung.

## Bestätigte Referenzplattform

| Komponente | Referenzstand |
|---|---|
| Windows | Windows 11 25H2, 64 Bit |
| NVDA | 2026.1.1; Manifestminimum 2026.1 |
| Terminalfrontend | Windows Terminal 1.24.x |
| Lokales Neovim | 0.12.3 praktisch; 0.10.1 automatisiert |
| SSH-Client | OpenSSH für Windows 9.5p2 mit schlüsselbasierter Anmeldung |
| Linux | Rocky Linux 10.2, Kernel 6.12.0-211.28.1.el10_2 |
| Entferntes Neovim | 0.10.1 und 0.12.3 |
| Linux-Bridge | Python 3.12.13 in der Referenzumgebung |

Neovim 0.10.1 ist die vorläufige Mindestversion. Neuere optionale APIs werden
nur nach Featureprüfung verwendet. Unter Neovim 0.10 richtet das Plugin für
ein unbelegtes F12 im Insert-Modus eine stille `<Ignore>`-Zuordnung ein, weil
erst Neovim 0.11 Tasten über den Rückgabewert von `vim.on_key` konsumieren
kann. Bestehende Benutzerbelegungen bleiben unverändert.

## Freigegebener Umfang und Grenzen

- Windows Terminal ist das einzige freigegebene Frontend. Andere Terminals und
  grafische Neovim-Oberflächen benötigen eigene Identitäts-, Fokus-, Ausgabe-
  und Fail-open-Adapter.
- Unter Windows wird das normale `%LOCALAPPDATA%\nvim-data`-Layout unterstützt.
  Portable Installationen und getrennte Datenpfade über `NVIM_APPNAME` sind
  nicht freigegeben.
- Lokales Windows-Neovim, Linux-Neovim über SSH sowie tmux innerhalb einer
  SSH-Sitzung sind implementiert. Gemischte lokale und entfernte Tabs, Panes
  und Fenster wurden praktisch geprüft.
- Frei belegbare Terminalbefehle gehören zum Windows-Terminal-AppModule. Ihre
  Ausführung wird erneut gegen die konkrete AppModule- und Control-Identität
  geprüft.
- Die Prüfung ist risikoorientiert und nicht erschöpfend. Andere Windows-,
  NVDA-, Neovim-, SSH-, Sprach- und Braillekombinationen können unentdeckte
  Fehler enthalten.

## Plugin- und Werkzeugverträge

Die Testmatrix führt die in den Testwerkzeugen gepinnten Versionen auf
Neovim 0.10.1 und 0.12.3 aus. Dazu gehören:

- `nvim-cmp` und `blink.cmp` für Completion;
- `nvim-lint`, ALE und `none-ls.nvim` für providerneutrale Diagnosen über
  `vim.diagnostic`;
- Clang-Tidy, Ruff, ShellCheck, Staticcheck, Clippy, RuboCop und
  `markdownlint-cli2` als reale Linterprozesse.

Die Checkouts, Sprachlaufzeiten und Werkzeuge sind Testabhängigkeiten und
werden nicht ausgeliefert. Sprachen sind nicht im Add-on fest verdrahtet. Ein
weiterer Sprachserver oder Linter gilt erst dann als automatisiert abgedeckt,
wenn ein realer gepinnter Vertragstest denselben semantischen Pfad bestätigt.

Oil, netrw, mini.files, nvim-tree und Neo-tree verwenden öffentliche APIs oder
dokumentierte Ereignisse. Fehlt ein erforderliches Ereignis oder ändert sich
eine öffentliche API inkompatibel, bleibt die cursorbasierte Ausgabe aktiv;
das Add-on startet kein allgemeines Polling als Ersatz. Nur Oil ist unter
Windows/NVDA praktisch geprüft. Die anderen Dateimanager besitzen
automatisierte oder isolierte Abdeckung.

## Brailleumfang

Braille-Routing, Standardnavigation, Sprachexploration, Braille-Exploration
und die `z=`-Vorschlagsansicht wurden im Referenzpfad mit einer Papenmeier
BRAILLEX EL 80c praktisch geprüft. Automatisierte Tests decken weitere
Zustands-, Unicode-, Tabulator-, Ausschnitts- und Mehrsitzungsfälle ab.

Das belegt eine Hardware- und Treiberkombination, nicht jede Anzeige,
Übersetzungstabelle oder Eingabebelegung. Die Brailleplanung löst Tabs anhand
von `tabstop` und Textpositionen auf. Zeichen mit Terminalbreite null oder zwei
können deshalb die Zahl sichtbarer Leerzellen gegenüber Neovims virtueller
Bildschirmspalte verändern; die UTF-8-Routingposition bleibt korrekt.

## Build- und Dokumentationsabhängigkeiten

MessagePack Python 1.1.1 wird in Add-on und Linux-Komponentenpaket gebündelt.
Das Linux-Ziel benötigt deshalb kein separates MessagePack- oder pynvim-Paket.

Python 3, ConfigObj und Pandoc werden nur für Tests oder Builds verwendet.
ConfigObj prüft das Add-on-Manifest mit NVDA-kompatibler INI-Semantik; Pandoc
erzeugt die eigenständigen HTML-Dokumente. Diese Werkzeuge werden nicht in das
installierte Plugin oder Add-on übernommen. Einzelheiten stehen unter
[Abhängigkeiten](dependencies.md) und [Teststrategie](testing.md).

## Primärquellen

- [Neovim API](https://neovim.io/doc/user/api/)
- [Neovim Lua Guide](https://neovim.io/doc/user/lua-guide/)
- [NVDA Developer Guide](https://download.nvaccess.org/documentation/developerGuide.html)
- [NVDA-Quellcode](https://github.com/nvaccess/nvda)

Die projektspezifischen NVDA-Annahmen stehen in den
[NVDA-API-Grenzen](nvda-2026.1-api-notes.md).
