# SSH und tmux verwenden

Der entfernte Access-Link-Pfad verbindet Windows Terminal mit Neovim auf einem
Linux-Ziel. Praktisch bestätigt ist Rocky Linux 10.2 mit Python 3 und OpenSSH.

## Voraussetzungen

Prüfen Sie zuerst eine normale Anmeldung im Windows Terminal:

```text
ssh benutzer@example.invalid
```

Bestätigen Sie Hostschlüssel und richten Sie Schlüssel, `ssh-agent`,
OpenSSH-Konfiguration oder erlaubte Passwortanmeldung ein, bevor Sie Access
Link aktivieren. Das Add-on verändert weder die Windows-OpenSSH-Konfiguration
noch `sshd_config` auf dem Linux-Ziel.

## Linux-Verbindung einrichten

1. Öffnen Sie `NVDA-Menü → Optionen → Einstellungen… → Neovim Access Link`.
2. Öffnen Sie `Verbindungen` und wählen Sie `Verbindung hinzufügen...`.
3. Tragen Sie SSH-Ziel, Konto, Port und Anmeldemethode ein.
4. Bestätigen Sie den Einstellungsdialog.
5. Schließen Sie laufendes Neovim auf diesem Ziel.
6. Öffnen Sie `NVDA-Menü → Werkzeuge → Neovim Access Link: Komponenten
   installieren oder aktualisieren...`.
7. Markieren Sie die gespeicherte Verbindung und prüfen Sie das Ergebnis.

Die Installation legt Plugin und Bridge im Home-Verzeichnis des Linux-Kontos
ab und benötigt keine root-Rechte.

## Entfernte Sitzung verbinden

1. Melden Sie sich im gewünschten Windows-Terminal-Tab oder -Pane per SSH an.
2. Starten Sie auf dem Linux-Ziel `nvim`.
3. Drücken Sie die zugewiesene Access-Link-Aktivierungsgeste.
4. Warten Sie auf die Bereitschaftsmeldung.
5. Fokussieren Sie Neovim und drücken Sie F12 einmal.
6. Warten Sie auf die Verbindungsbestätigung.

Die sichtbare SSH-Sitzung transportiert Ihre Shell und Tastatureingaben. Access
Link öffnet getrennt davon eine eigene SSH-Verbindung zur Bridge für
Barrierefreiheitsdaten. Der Linux-Rechner öffnet dafür keinen zusätzlichen
Netzwerkport.

## tmux verwenden

Starten Sie tmux in der sichtbaren SSH-Sitzung und danach Neovim:

```text
tmux new -s arbeit
nvim
```

Access Link ordnet die konkrete Neovim-Instanz zu, nicht das tmux-Fenster. Eine
in tmux laufende Neovim-Sitzung bleibt aktiv, wenn die sichtbare SSH-Sitzung
endet. Nach dem erneuten Anhängen fokussieren Sie das zugehörige Pane; eine
gemerkte Access-Link-Zuordnung wird nach bestätigtem Fokus wiederhergestellt.
Drücken Sie F12 erneut, wenn keine gemerkte Zuordnung besteht.

Mehrere Neovim-Instanzen innerhalb von tmux sind getrennte Access-Link-
Sitzungen. Verwenden Sie bei ähnlichen Arbeitsverzeichnissen verständliche
Sitzungsnamen:

```text
NVIM_NVDA_SESSION_NAME=Backend nvim
NVIM_NVDA_SESSION_NAME=Dokumentation nvim
```

## Verbindungsabbruch

Endet die Hintergrundverbindung, gibt Access Link die native
Windows-Terminal-Ausgabe frei. Die sichtbare SSH-Sitzung und Neovim in tmux
werden dadurch nicht beendet.

Stellen Sie zuerst die normale SSH-Erreichbarkeit wieder her. Aktivieren Sie
Access Link anschließend erneut und drücken Sie F12 in der gewünschten
Neovim-Pane. Weitere Prüfungen stehen unter
[Fehlerdiagnose](troubleshooting.md).
