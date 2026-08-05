# Fehler beheben und Diagnosebericht erstellen

Gehen Sie vom ersten fehlenden Schritt aus: Add-on aktiv, Plugin geladen,
Sitzung gefunden, Verbindung hergestellt und optionales Werkzeug eingerichtet.

## Diagnosebericht kopieren

Fokussieren Sie Windows Terminal und drücken Sie `NVDA+Alt+D`. Alternativ
finden Sie den Befehl unter `NVDA-Menü → Optionen → Tastenbefehle… → Neovim
Access Link`. Der Bericht wird in die Windows-Zwischenablage kopiert.

Editortext, Auswahl, Registerinhalt, Passwörter und Tokens werden durch
Platzhalter ersetzt. Installationsmeldungen können trotzdem lokale Pfade,
Profilnamen oder SSH-Ziele enthalten. Prüfen Sie den Bericht deshalb vor dem
Weitergeben.

## Das Add-on reagiert nicht

1. Fokussieren Sie Windows Terminal. In anderen Anwendungen greift Access Link
   nicht ein.
2. Prüfen Sie in NVDAs Liste installierter Add-ons, ob Neovim Access Link
   aktiviert ist.
3. Öffnen Sie bei fokussiertem Windows Terminal den Tastenbefehlsdialog und
   weisen Sie dem Aktivierungsbefehl eine Geste zu.
4. Starten Sie NVDA nach einer Installation oder Aktualisierung neu.

Fehlt die Kategorie im Tastenbefehlsdialog, schließen Sie den Dialog,
fokussieren Sie Windows Terminal und öffnen Sie ihn erneut.

## Das Neovim-Plugin ist installiert, aber nicht geladen

Schließen Sie alle betroffenen Neovim-Instanzen, aktualisieren Sie die
Komponenten für das richtige Ziel und starten Sie Neovim neu. Prüfen Sie dann:

```vim
:echo exists(':NvimNvdaSessionName')
```

Die erwartete Ausgabe ist `2`. Ein Plugin-Manager, der `packpath` oder das
Laden von Start-Paketen ersetzt, muss die vom Add-on installierte lokale Kopie
registrieren. Installieren Sie keine zweite Kopie. Einzelheiten und ein
`lazy.nvim`-Beispiel stehen unter
[LSP, Autovervollständigung und Linter einrichten](language-tools.md#access-link-plugin-und-plugin-manager).

## F12 stellt keine Verbindung her

1. Aktivieren Sie Access Link und warten Sie auf die Bereitschaftsmeldung.
2. Fokussieren Sie das gewünschte Neovim-Pane.
3. Drücken Sie F12 genau einmal und warten Sie bis zu zwei Sekunden.
4. Verwenden Sie als Gegenprobe den belegbaren Befehl „Server wählen und dieses
   Terminal mit einer neuen Neovim-Sitzung verbinden“.

Schnelle wiederholte F12-Eingaben starten jeweils eine neue Zuordnungsprüfung.
Kopieren Sie den Diagnosebericht direkt im betroffenen Pane, wenn die Verbindung
ausbleibt.

## Die falsche Sitzung ist verbunden

1. Fokussieren Sie das betroffene Windows-Terminal-Pane.
2. Trennen Sie seine Verbindung oder vergessen Sie seine vorübergehende
   Zuordnung.
3. Fokussieren Sie das gewünschte Neovim und drücken Sie F12 einmal.

Bei mehreren gleichartigen Sitzungen erleichtert ein freiwilliger Name die
Auswahl, zum Beispiel unter Linux:

```text
NVIM_NVDA_SESSION_NAME=Dokumentation nvim
```

## SSH-Verbindung schlägt fehl

Testen Sie dasselbe Ziel zuerst außerhalb des Add-ons in Windows Terminal:

```text
ssh benutzer@example.invalid
```

Bestätigen Sie dort den Hostschlüssel und klären Sie Schlüsseldateien,
Passphrasen, `ssh-agent` oder die serverseitige Passwortanmeldung. Access Link
ändert weder die Windows-SSH-Konfiguration noch `sshd_config` auf dem Server.
Aktualisieren Sie danach die Linux-Komponenten und starten Sie Neovim neu.

## Access Link funktioniert, aber LSP oder Diagnosen fehlen

Drücken Sie den in Ihrer Neovim-Konfiguration belegten LSP-Statusbefehl oder
führen Sie `:NvimNvdaLspStatus` aus. Meldet Access Link keinen aktiven Client,
prüfen Sie mit `:checkhealth vim.lsp` die Neovim-Konfiguration und ob der
Sprachserver auf dem Rechner gefunden wird, auf dem Neovim läuft.

Diagnosen erscheinen erst, wenn ein Sprachserver oder Linter sie über Neovims
Diagnose-API veröffentlicht. Prüfen Sie den Werkzeugbefehl im selben Terminal
und starten Sie einen manuell belegten Linterlauf. Die
[Einrichtungsanleitung](language-tools.md) enthält einen vollständigen
Python-Testweg.

## Terminalfragmente werden gesprochen

Eine verbundene und sicher zugeordnete Neovim-Sitzung verwendet strukturierte
Ausgabe. Native Terminalausgabe bleibt aktiv in einem unverbundenen Pane, bei
direkter Eingabe in `:terminal`, nach einer Trennung und immer dann, wenn Access
Link die Zuordnung nicht sicher bestätigen kann.

Treten unerwartete Fragmente nach einem Fenster-, Tab- oder Panewechsel auf,
kopieren Sie den Diagnosebericht sofort im betroffenen Pane. Deaktivieren Sie
Access Link als Sicherheitsprüfung; die normale Terminalausgabe muss dann
vollständig zurückkehren.

## NVDA reagiert nach einem Dialog nicht

Suchen Sie mit `Alt+Tab` nach einem offenen Ergebnis-, Bestätigungs- oder
Passwortdialog und schließen oder brechen Sie ihn ab. Starten Sie NVDA neu,
wenn es nicht mehr reagiert. Sichern Sie anschließend den Diagnosebericht und
NVDAs vorheriges Protokoll. Prüfen Sie beide vor dem Weitergeben auf vertrauliche
Angaben.
