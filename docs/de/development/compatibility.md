# Kompatibilität

## Bestätigte Zielplattform

- Rocky Linux 10.2 (Red Quartz), Kernel 6.12.0-211.28.1.el10_2
- RPM: `neovim-0.10.1-4.el10_0.x86_64`
- Neovim 0.10.1, LuaJIT 2.1.1720049189
- Python 3.12.13 für die mitgelieferte Linux-Bridge
- vorhanden: `ModeChanged`, `CursorMoved`, `nvim_get_mode`,
  `nvim_win_get_cursor`, `nvim_buf_get_text`
- Windows 11 25H2, 64 Bit
- NVDA 2026.1.1
- `OpenSSH_for_Windows_9.5p2`, gebaut mit `LibreSSL 3.8.2`, mit
  schlüsselbasierter Anmeldung
- Windows Terminal 1.24.x als derzeit einzig freigegebenes Terminalfrontend

Neovim 0.10.1 ist vorläufig die Mindestversion. Jede neuere optionale API muss
per Featuretest abgesichert werden.

Completion-API-Vertragstests verwenden `nvim-cmp`
`2ffe79f1f021def8dd1fcd81deb16f1bb0d989f3` und `blink.cmp` v1.10.2 auf
Neovim 0.10.1 sowie 0.12.3. Der vorläufige `blink.cmp`-v2-Stand
`d33327a0ed7bfe3cd5dfa2fdd2738ad74f9e0ea3` wird zusammen mit `blink.lib`
`5876dd95deeb70aadbe9f1c0b7117a135061cdac` ausschließlich auf Neovim 0.12.3
geprüft. Die Checkouts werden nicht mit dem Add-on ausgeliefert. Der Test
bestätigt Modul- und API-Anbindung mit injizierten Auswahlwerten, nicht jede
praktische Darstellung oder NVDA-Konfiguration.

Diagnose-Provider-Vertragstests verwenden `nvim-lint`
`a219b2c9e5b4765e5c845aba119dad55806fcaf1` und ALE
`9e2efaa4d348b1f93200b24e5540c670eb6fdd3f` sowie `none-ls.nvim`
`01f8e62ea11603e59ad9ff7afcfa94fd183f76d6` mit `plenary.nvim`
`74b06c6c75e4eeb3108ec01852001636d85a932b` auf Neovim 0.10.1 und 0.12.3.
Dabei laufen Clang-Tidy 22.1.8 für C, Ruff 0.15.4 für Python, ShellCheck 0.11.0
für Bash, Staticcheck 2026.1 für Go, Clippy aus Rust 1.97.1, RuboCop 1.88.2
für Ruby und `markdownlint-cli2` 0.23.2 für Markdown wirklich und publizieren
über `vim.diagnostic`. Checkouts, Laufzeiten und Werkzeuge sind ausschließlich
Testabhängigkeiten und werden nicht ausgeliefert. Eine eingebaute
none-ls-Quelle bestätigt zusätzlich den LSP-Brückenpfad ohne externes
Werkzeug. Das bestätigt den semantischen Linux-Vertrag, nicht Installation,
Projektkonfiguration oder praktische Windows-/NVDA-Ausgabe.

Sprachen sind nicht fest im Add-on verdrahtet. Die eigenständigen
Go-/Rust-Linter sind damit automatisiert belegt; die später gebündelt praktisch
zu prüfenden LSP-Server `gopls` und `rust-analyzer` verwenden denselben
Vertrag. Weitere Kombinationen gelten erst nach einem realen gepinnten
Vertragstest als praktisch automatisiert abgedeckt.

## NVDA und Windows

Ziel ist NVDA 2026.1.x; die offizielle Downloadablage führt 2026.1.1 als
stabilen Stand vom 20. Mai 2026. Der offizielle Quelltag bestätigt 64-Bit-Python
3.13.12. Verwendet werden ein anwendungsspezifisches
`appModuleHandler.AppModule`, ein Global Plugin ohne globale Ereignis- oder
Overlay-Hooks, dekorierte Scripts, `queueHandler.queueFunction`/`eventQueue`
und öffentliche Speech-Funktionen. Frei konfigurierbare Terminalbefehle liegen
im Windows-Terminal-AppModule. Sie erscheinen im Tastenbefehldialog zunächst
nach zuvor fokussiertem Windows Terminal und werden nicht in fremden
Anwendungen aufgelöst. Nach dem Laden der Klasse kann NVDAs Benutzergestenkarte
eine gespeicherte Zuordnung andernorts weiter anzeigen; beim Aufruf werden
konkrete AppModule- und Control-Identität erneut geprüft.
Manifestwerte sind `minimumNVDAVersion = 2026.1` und
`lastTestedNVDAVersion = 2026.1.1`. Installation, Add-on-Start,
Serverinstallation, SSH-stdio-Verbindung, Sprach- und Soundausgabe sowie die
grundlegende Bedienung wurden mit Windows 11 25H2 und NVDA 2026.1.1 praktisch
getestet. NVDA definiert für diese Serie
`BACK_COMPAT_TO = (2026, 1, 0)`; 2026.1 ist wegen Python 3.13 und der
64-Bit-Migration bewusst die Mindestversion.

Die native Windows-CLI von Neovim in Windows Terminal ist implementiert und
automatisiert gegen Neovim 0.10.1 geprüft. Die automatische F12-Zuordnung und
die anschließende RPC-Verbindung wurden außerdem praktisch mit Neovim 0.12.3
unter Windows bestätigt. Der lokale Grundpfad sowie parallele lokale und
SSH-Tabs wurden unter Windows praktisch bestätigt. Die zielübergreifende
Discovery und zwei parallele
lokale Tabs, mehrere Windows-Terminal-Fenster und tmux wurden ebenfalls
praktisch bestätigt.
Unterstützt wird vorerst nur Neovims
normales `%LOCALAPPDATA%\nvim-data`-Layout, nicht `NVIM_APPNAME`, portable
Installationen oder GUI-Frontends.

Eine ältere, auf Rocky Linux 9 vorhandene Neovim-Version konnte mit dem
aktuellen Stand nicht erfolgreich verbunden werden. Ein sehr früher
Entwicklungsstand hatte dort funktioniert; Ursache und genaue Versionsgrenze
sind bislang nicht untersucht und haben derzeit keine Priorität. Daraus wird
keine Kompatibilitätszusage abgeleitet. Neovim 0.10.1 auf Rocky Linux 10.2
bleibt die vorläufige Mindest- und Referenzversion.
Da erst Neovim 0.11 eine Taste über den Rückgabewert von `vim.on_key`
konsumieren kann, richtet das Plugin unter 0.10 ausschließlich für ein zuvor
unbelegtes F12 im Insert-Modus eine stille `<Ignore>`-Zuordnung ein. Sie hält
den physischen Claim nachweisbar, ohne `<F12>` in den Buffer einzufügen;
vorhandene Benutzerbelegungen bleiben unangetastet.

Die Prüfung war nicht erschöpfend. Andere Windows-Versionen, NVDA-Versionen,
Sprachprofile und reale Braillezeilen sind noch nicht breit in einer
Kompatibilitätsmatrix getestet. Andere Terminalprogramme sind derzeit nicht
freigegeben: Es baut dort keine Neovim-Bindung auf, aktiviert keine
Terminalunterdrückung und löst keine Windows-Terminal-AppModule-Befehle aus.
PuTTY und weitere Frontends benötigen jeweils einen
eigenen Identitäts-, Fokus-, Ausgabe- und Fail-open-Adapter mit praktischer
Prüfung.

Der `z=`-Vorschlagspfad einschließlich Rückkehr zur Editorzeile wurde mit einer
physischen Braillezeile erfolgreich geprüft. Automatisierte Brailletests
bestätigen weitere Zustands- und Planungsfälle; hardwarespezifische Probleme
außerhalb des praktisch geprüften Pfads können trotzdem unentdeckt sein.
Der neutrale Brailleplan löst Tabulatoren anhand von `tabstop` und der
vorhergehenden Unicode-Codepointposition auf. Stehen vor einem Tabulator
Zeichen mit Terminalbreite null oder zwei, kann die Anzahl der angezeigten
Leerzellen deshalb von Neovims virtueller Bildschirmspalte abweichen. Die
Routingzuordnung zur UTF-8-Textposition bleibt dabei korrekt. Eine spätere
exakte Bildschirmbreitenabbildung muss als semantische Neovim-Angabe erfolgen,
nicht durch Screen-Scraping oder eine zweite Unicode-Breitentabelle im Add-on.
Insgesamt ist der Stand Beta. Auch in diesem Reifegrad besitzen weitere
Add-on-Funktionen noch keine erschöpfende praktische Abnahme.

Dateimanager-Unterstützung verwendet die öffentlichen APIs der zum 12. Juli
2026 geprüften Hauptzweige von Oil, nvim-tree, Neo-tree und mini.files. Adapter
werden nur geladen, wenn der jeweilige Dateimanagerbuffer aktiv ist. netrw wird
mit der in Neovim 0.10.1 enthaltenen Version 173 geprüft.
Praktisch unter Windows/NVDA wurde bislang nur Oil mit Neovim 0.12 getestet;
dieser Pfad einschließlich Navigation, bearbeitetem Namen, Klängen und
Bestätigung funktioniert und bildet eine solide Grundlage. netrw, mini.files,
nvim-tree und Neo-tree sind noch nicht praktisch unter Windows abgenommen und
werden nach und nach ergänzt. Ihre nachfolgend genannten Nachweise sind
automatisiert oder isoliert, sofern nicht ausdrücklich anders angegeben.
Die am 18. Juli 2026 erneut geprüfte Ereignisschicht verwendet
`OilMutationComplete`, mini.files-User-Autocmds, nvim-trees öffentliches
`api.events` und Neo-trees öffentliches Ereignismodul. Fehlt ein Ereignis oder
ändert ein Plugin seine öffentliche API inkompatibel, bleibt die normale
cursorbasierte Adapterausgabe fail-open erhalten; es wird kein Polling als
Ersatz gestartet.
Der netrw-Fallback wird automatisiert mit Version 184 aus Neovim 0.12.3 und
Version 173 aus der Referenzversion Neovim 0.10.1 in schmaler, langer, breiter
und Baumdarstellung geprüft. Eine breitere praktische Matrix ist unter
Windows/NVDA noch nicht bestätigt.
Die öffentlichen Optionen `select_prompts = true` von nvim-tree und
`use_popups_for_input = false` von Neo-tree führen deren Dialoge über
`vim.ui.select/input`; Access Link ändert sie nicht automatisch. Oil verwendet
weiterhin einen eigenen Bestätigungs-Float ohne öffentliche Promptquelle. Ein
enger Fallback für `oil_preview` in einem echten Float ist mit dem realen
Oil-Hauptzweig auf Neovim 0.12.3 für Umbenennen, Duplizieren, Löschen und Y/N
geprüft; er überträgt nur feste Aktion und Anzahl, nie gerenderte Pfade.
mini.files- und andere
Lua-Aufrufe von `vim.fn.confirm` werden auf beiden Neovim-Referenzständen
semantisch erfasst. Die öffentlichen Aktionsformen einschließlich der langen
Typnamen `directory` und `symbolicLink` werden normalisiert; eine vollständige
praktische Operationsmatrix steht dennoch aus.

Details der Quellprüfung: `nvda-2026.1-api-notes.md`.

## Primärquellen

- [Neovim API](https://neovim.io/doc/user/api/)
- [Neovim Lua Guide](https://neovim.io/doc/user/lua-guide/)
- [Neovim Remote Plugins](https://neovim.io/doc/user/remote_plugin/)
- [NVDA 2026.1-Releases](https://download.nvaccess.org/releases/)
- [NVDA Developer Guide](https://download.nvaccess.org/documentation/developerGuide.html)
- [NVDA-Quellcode](https://github.com/nvaccess/nvda)

## Build- und Dokumentationsabhängigkeiten

MessagePack 1.1.1 wird beim Build in Bridge und Add-on gebündelt. Das
Linux-Ziel benötigt deshalb nur `python3`; `python3-msgpack` und
`python3-pynvim` sind dort keine Laufzeitabhängigkeiten.

`pandoc-3.1.11.1-34.el10_2` und `pandoc-common` aus EPEL dienen ausschließlich
dem HTML-Dokumentationsbuild. Pandoc ist ein aktiv gepflegter universeller
Markup-Konverter; die RPM-Lizenzen sind GPL-2.0-or-later beziehungsweise die im
Common-Paket ausgewiesene GPL/BSD/WTFPL-Kombination. Installiert belegen beide
Pakete ungefähr 196 MB. Sie sind keine Laufzeitabhängigkeit von Plugin, Bridge
oder Add-on, beeinflussen deren Latenz und Packaging nicht und werden auf
Windows nicht benötigt.

`python3-configobj-5.0.8-10.el10` wird nur im Add-on-Build verwendet, um das
Manifest mit derselben INI-Semantik wie NVDA zu parsen und Listen statt
erwarteter Stringwerte früh zu erkennen. Es wird nicht in das Add-on gebündelt
und beeinflusst dessen Laufzeit nicht.
