# Rootlose Installation und SSH-stdio-Transport

## Unterstützter Zustand

Der Anwender installiert die Linux-Komponenten ohne Root-Rechte einmal nach
`~/.local` und startet danach ausschließlich normales Neovim:

```text
nvim datei
```

Das NVDA-Add-on startet bei Aktivierung selbst:

```text
ssh.exe -T -o BatchMode=yes <ssh-alias> nvim-nvda-bridge
```

Bridge-Ereignisse laufen als gerahmtes MessagePack direkt über stdout; Kontrolle
läuft über stdin. Der SSH-Prozess endet bei Deaktivierung oder NVDA-Ende. Damit
entfallen TCP-Forward, fester Port und gemeinsames Anwendungstoken.

## Rootloses Paket

Das Benutzerpaket ist ein `tar.gz` mit:

```text
bin/nvim-nvda-bridge
config/linux-components.json
share/nvim/site/pack/nvim-nvda/start/nvim-nvda/
install.py
```

`nvim-nvda-bridge` ist eine ausführbare Python-Zipapp, keine Shell-Hülle. Sie
enthält Bridge, Protokollcodec und den reinen Python-MessagePack-Fallback. Der
Installer kopiert ausschließlich nach einem frei wählbaren Präfix, standardmäßig
`~/.local`, und benötigt weder RPM noch `sudo`.

Ein RPM kann später als optionale systemweite Distributionsform ergänzt werden.
Das kombinierte Archiv ist der unterstützte reproduzierbare,
distributionsunabhängige Installationsweg.

Beim Bau der `.nvda-addon` erzeugt `tools/build_user_package.py` dieses Archiv
direkt aus den versionierten Verzeichnissen `bridge/`, `protocol/`,
`neovim-plugin/` und `packaging/install_user.py`. Anschließend wird es als
`globalPlugins/nvimNvdaAccess/resources/server-user.tar.gz` in das Add-on
eingebettet. Der Menüinstaller liest genau diese Ressource und überträgt ihre
Bytes über SSH-stdin; die Zielmaschine greift weder auf das Repository noch auf
einen Downloadserver zu.

`linux-components.json` ist der gemeinsame, versionierte Vertrag zwischen
Add-on und Linux-Komponenten. Er deklariert derzeit denselben Bezeichner für
Neovims Sitzungsmarkierung und NVDAs ausschließlich beobachtete Geste,
standardmäßig `<F12>` und `kb:f12`. Das ist keine NVDA-Skriptbindung und kein
Neovim-Keymapping; beide Seiten erkennen denselben physischen Tastendruck an
ihren jeweiligen öffentlichen Eingabeschnittstellen.
Der Paketbau akzeptiert nur zusammenpassende Funktionstasten F1 bis F24. Das
Plugin liest seine installierte Kopie; eine zusätzliche Kopie liegt zur
Diagnose unter `~/.local/share/nvim-nvda/linux-components.json`. Änderungen
sind als Paketänderung vorzunehmen: Konfiguration ändern, Add-on neu bauen und
danach die Linux-Komponenten über das NVDA-Menü aktualisieren. Eine isolierte
Änderung nur auf dem Linux-Ziel würde die beiden Seiten auseinanderbringen und
ist daher nicht unterstützt.

## Neovim-Sitzungsregistry

Das installierte Plugin startet über `serverstart()` selbst einen privaten
Unix-RPC-Socket und registriert PID, Socket, monotone und reale Startzeit,
Arbeitsverzeichnis sowie einen optionalen Sitzungsnamen unter
`$XDG_RUNTIME_DIR/nvim-nvda/sessions`. Die stdio-Bridge kann eine explizit
ermittelte lebende Sitzung öffnen. Dadurch blockiert eine ältere, etwa in einem
anderen tmux-Fenster laufende Neovim-Instanz die Verbindung nicht. Das Add-on
listet Sitzungen und hält ihre numerischen IDs von der Bedienoberfläche fern.

Bei nichtinteraktiven SSH-Befehlen fehlt `XDG_RUNTIME_DIR` auf manchen Servern.
Die Bridge prüft dann das dem Benutzer gehörende Standardverzeichnis
`/run/user/UID`, bevor sie auf ein privates Verzeichnis unter `/tmp` ausweicht.

## SSH-Startausgaben

Da Shell-Startdateien auf manchen Zielsystemen unerwünschte Bytes ausgeben,
sendet die Bridge vor dem Binärprotokoll eine feste ASCII-Markierung. Der
Windows-Client verwirft alles vor dieser Markierung. Nach der Markierung ist
stdout ausschließlich dem Protokoll vorbehalten; Diagnosen gehen nach stderr.

## Sicherheitsmodell

- SSH authentifiziert Benutzer und Host; bevorzugt werden Schlüssel und Agent.
- Schlüssel-/Agentanmeldung verwendet `BatchMode=yes` und verhindert damit
  unsichtbare Passwortdialoge im NVDA-Prozess.
- Ein Verbindungstest darf für Hostschlüssel- oder Schlüsselersteinrichtung ein
  sichtbares Terminal öffnen.
- Die rootlose Installation verändert keine SSH-Konfiguration. Bei der
  ausdrücklich gewählten Passwortanmeldung fragt das Add-on zugänglich nach
  und speichert das Passwort nicht.
- Der Anwenderablauf verwendet ausschließlich SSH-stdio; alte Tunnel- und
  Token-Hilfswerkzeuge sind entfernt.

## Installation aus NVDA

Nach Installation des Add-ons werden Verbindungen unter „NVDA-Menü → Optionen
→ Einstellungen… → Neovim Access Link → Connections“ verwaltet. „Add
connection“ öffnet ein
gemeinsames Formular für Name, Host oder OpenSSH-Alias, Linux-Benutzer, Port,
optionale Schlüsseldatei und verständlich erklärte Anmeldeart.

Der Menüpunkt `NVDA-Menü → Werkzeuge → Neovim Access Link: Install or update components...`
listet alle gespeicherten
Verbindungen mit Konto, Ziel, Port und Anmeldeart als zunächst leere
Checkboxliste. Einzelne oder über die initial fokussierte „Select all
connections“-Checkbox alle Ziele werden ausdrücklich ausgewählt. Danach
überträgt das Add-on sein Benutzerpaket im Hintergrund auf alle gewählten
Linux-Konten und zeigt Erfolge und Fehlschläge gesammelt an.

Die Installation läuft im Hintergrund und blockiert NVDA nicht. Die empfohlene
OpenSSH-Auswahl verwendet Schlüssel, Agent oder Windows-SSH-Konfiguration. Die
alternative Passwortauswahl verwendet den zugänglichen NVDA-Dialog und hält das
Passwort ausschließlich im Speicher. Danach ist Neovim einmal neu zu starten.
Künftige Add-on-Aktivierungen starten und beenden den SSH-stdio-Prozess
automatisch.

## Entfernung aus NVDA

`NVDA-Menü → Werkzeuge → Neovim Access Link: Remove components...` verwendet
dieselbe zunächst leere, zugänglich beschriftete Mehrfachauswahl wie die
Installation. Neovim muss auf den gewählten Zielen vorher beendet werden; das
Add-on beendet keine laufenden Neovim- oder tmux-Sitzungen. Die Arbeit läuft
außerhalb des NVDA-Hauptthreads und endet mit einer nicht blockierenden
Ergebnisübersicht pro Ziel.

Lokal wird nur
`%LOCALAPPDATA%\nvim-data\site\pack\nvim-nvda\start\nvim-nvda` gelöscht. Leere,
vom Installer angelegte Paketverzeichnisse werden anschließend aufgeräumt,
nichtleere Elternverzeichnisse aber erhalten. Über SSH löscht ein einzelner,
auf 30 Sekunden begrenzter Benutzerbefehl ausschließlich:

```text
~/.local/bin/nvim-nvda-bridge
~/.local/share/nvim/site/pack/nvim-nvda
~/.local/share/nvim-nvda
~/.cache/nvim-nvda-install
```

Der Ablauf ist idempotent. Gespeicherte Verbindungen, SSH- und
Neovim-Konfiguration, andere Plugins und Laufzeit-Sitzungsdaten gehören nicht
zu den installierten Komponenten und werden nicht gelöscht.

Installation und Laufzeit setzen `ClearAllForwardings=yes`. Dadurch werden alte
`LocalForward`-Einträge aus der 0.1-Konfiguration für diese Prozesse ignoriert
und können nicht mit einer bereits laufenden interaktiven SSH-Sitzung kollidieren.
