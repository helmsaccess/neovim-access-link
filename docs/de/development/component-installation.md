# Komponenteninstallation und SSH-stdio

## Laufzeitmodell

Anwender installieren die Linux-Komponenten ohne Root-Rechte nach `~/.local`
und starten danach normales Neovim. Bei einer entfernten Aktivierung startet
das Add-on selbst einen nichtinteraktiven SSH-Prozess:

```text
ssh.exe -T -o BatchMode=yes <ssh-alias> nvim-nvda-bridge
```

Gerahmtes MessagePack läuft über Standardausgabe, Steuerung über
Standardeingabe. Bei Deaktivierung oder NVDA-Ende wird der SSH-Prozess beendet.
Es gibt keine Portweiterleitung, keinen festen Port und kein gemeinsames
Anwendungstoken.

## Rootloses Benutzerpaket

`tools/build_user_package.py` erzeugt aus den versionierten Bridge-, Protokoll-
und Pluginquellen ein `tar.gz` mit:

```text
bin/nvim-nvda-bridge
config/linux-components.json
share/nvim/site/pack/nvim-nvda/start/nvim-nvda/
install.py
```

Die Bridge ist eine Python-Zipapp mit Protokollcodec und portablem
MessagePack. Das Archiv liegt im Add-on unter
`globalPlugins/NeovimAccessLink/resources/server-user.tar.gz`. Der
Menüinstaller überträgt genau diese Bytes über SSH-stdin; das Ziel benötigt
Python 3, aber keinen Repositoryzugriff, externen Download, RPM oder `sudo`.

`linux-components.json` hält Neovims Sitzungsmarkierung und NVDAs beobachtete
F12-Geste konsistent. Änderungen werden im Quellpaket vorgenommen, danach
werden Add-on und Zielkomponenten zusammen neu gebaut beziehungsweise
aktualisiert. Eine isolierte Änderung einer installierten Kopie wird nicht
unterstützt.

## Sitzungsregistrierung

Das Plugin startet mit `serverstart()` einen privaten Unix-RPC-Socket und legt
pro Neovim-Instanz einen kurzlebigen JSON-Datensatz im privaten
Benutzerlaufzeitverzeichnis an. Enthalten sind nur die zur Erkennung und
Validierung benötigten Prozess-, Zeit-, Endpunkt- und Sitzungsangaben. Diese
Dateien sind keine Windows-Registry-Einträge.

Interaktives Neovim und ein späterer nichtinteraktiver SSH-Prozess können
unterschiedliche `XDG_RUNTIME_DIR`-Werte sehen. Die Bridge prüft deshalb das
konfigurierte Laufzeitverzeichnis, das dem Benutzer gehörende `/run/user/UID`
und den privaten Fallback unter `/tmp`. Sie liest nur private Verzeichnisse des
aktuellen Benutzers, führt identische Datensätze zusammen und validiert
Prozess, Nonce, Endpunkt, Eigentümer und Protokoll vor jeder Verwendung.

## SSH-Stream und Sicherheit

Die Bridge sendet vor dem Binärprotokoll eine feste ASCII-Markierung. Der
Windows-Client verwirft Shell-Startausgaben vor dieser Markierung; danach ist
stdout ausschließlich dem Protokoll vorbehalten und Diagnostik geht nach
stderr.

- SSH authentifiziert Host und Benutzer. Schlüssel, Agent oder gespeicherte
  OpenSSH-Konfiguration sind der Standardpfad.
- `BatchMode=yes` verhindert unsichtbare Passwortabfragen im NVDA-Prozess.
  Für ausdrücklich konfigurierte Passwortanmeldung verwendet das Add-on einen
  zugänglichen Dialog und speichert das Passwort nicht.
- `ClearAllForwardings=yes` verhindert die Übernahme konfigurierter
  Portweiterleitungen.
- Installation, Verbindung und Entfernung laufen außerhalb von NVDAs
  Hauptthread und besitzen Zeitgrenzen.

## Installation und Aktualisierung

Verbindungen werden unter „NVDA-Menü → Optionen → Einstellungen… → Neovim
Access Link → Verbindungen“ verwaltet. „Verbindung hinzufügen…“ erfasst Name,
Host oder OpenSSH-Alias, Linux-Benutzer, Port, optionale Schlüsseldatei und
Anmeldeart.

„NVDA-Menü → Werkzeuge → Neovim Access Link: Komponenten installieren oder
aktualisieren…“ bietet „Dieser Computer“ und alle gespeicherten
Linux-Verbindungen als zunächst leere Mehrfachauswahl an. Ausgewählte Ziele
werden im Hintergrund bearbeitet; eine Ergebnisübersicht meldet jeden Erfolg
und Fehler. Lokal wird das Plugin atomar unter
`%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda` ersetzt.
Neovim muss nach einer Installation oder Aktualisierung neu gestartet werden.

## Entfernung

„NVDA-Menü → Werkzeuge → Neovim Access Link: Komponenten entfernen…“ verwendet
dieselbe Mehrfachauswahl. Neovim muss auf den gewählten Zielen beendet sein;
das Add-on beendet keine Neovim- oder tmux-Sitzung.

Lokal wird nur das installierte Pluginverzeichnis entfernt. Über SSH entfernt
ein zeitlich begrenzter Benutzerbefehl ausschließlich:

```text
~/.local/bin/nvim-nvda-bridge
~/.local/share/nvim/site/pack/nvim-nvda
~/.local/share/nvim-nvda
~/.cache/nvim-nvda-install
```

Der Ablauf ist idempotent. Gespeicherte Verbindungen, SSH- und
Neovim-Konfiguration, andere Plugins und Laufzeit-Sitzungsdaten bleiben
erhalten.

## Zuständiger Code und Tests

Paketbau und Installation liegen in `tools/build_user_package.py`,
`packaging/install_user.py` und den Installationsdiensten des Add-ons. Die
Bridge-Einstiege liegen unter `bridge/`, die Sitzungsregistrierung im
Neovim-Plugin. Paket-, SSH- und Sockettests werden getrennt ausgeführt; die
zugehörigen Befehle stehen in [Teststrategie](testing.md).
