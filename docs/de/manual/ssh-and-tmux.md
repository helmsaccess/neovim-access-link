# Betrieb mit SSH, tmux und Neovim

## Normaler Arbeitsablauf

Der Anwender verbindet sich von Windows per SSH mit Rocky Linux, öffnet oder
übernimmt eine tmux-Sitzung und startet Neovim normal:

```text
ssh editor@example.invalid
tmux new-session -A -s neovim
nvim [datei]
```

Neovim läuft dabei interaktiv. `nvim --headless` wird ausschließlich für
automatisierte Tests und Benchmarks verwendet.

Nach der Installation der Serverkomponenten durch das NVDA-Add-on sind weder
Wrapper, `--listen`, ein manuell gestarteter Bridgeprozess noch zusätzliche
Umgebungsvariablen erforderlich. Das installierte Neovim-Plugin erzeugt einen
privaten Unix-RPC-Socket und registriert die Sitzung automatisch.

## Kommunikation

Bei der Aktivierung verwendet das Add-on zunächst kurze, begrenzte
OpenSSH-Aufrufe, um erreichbare Sitzungen zu inventarisieren. Erst nachdem F12
oder der manuelle Ablauf eine konkrete Neovim-Sitzung bestätigt hat, startet
das Add-on für diese Sitzung einen dauerhaften, unsichtbaren und
nichtinteraktiven Windows-OpenSSH-Prozess:

```text
ssh.exe -T -o BatchMode=yes editor.example.invalid \
  "$HOME/.local/bin/nvim-nvda-bridge"
```

Über stdin und stdout dieser SSH-Verbindung läuft das gerahmte MessagePack-
Protokoll. Die Bridge verbindet sich mit der durch F12 oder den zugänglichen
Dialog ausgewählten Neovim-Sitzung. Es gibt daher:

- keinen TCP-Port und keinen SSH-`LocalForward`,
- keinen gemeinsamen Anwendungstoken,
- keinen separat zu startenden Bridgeprozess,
- keine feste Abhängigkeit von tmux.

SSH authentifiziert Benutzer und Server. Empfohlen wird eine bereits
funktionierende normale OpenSSH-Konfiguration mit Schlüssel oder `ssh-agent`.
Alternativ kann das Verbindungsformular eine zugängliche Passwortabfrage des
Add-ons wählen; das Passwort bleibt nur während der Aktivierung im Speicher.

## Installation und Aktualisierung

Unter „NVDA-Menü → Optionen → Einstellungen… → Neovim Access Link → Verbindungen“ wird die
Linux-Verbindung in einem gemeinsamen Formular gespeichert. Anschließend wählt
„NVDA-Menü → Werkzeuge → Neovim Access Link: Komponenten installieren oder aktualisieren...“ ein oder mehrere Konten über beschriftete
Checkboxen aus und installiert das rootlose Benutzerpaket jeweils nach:

```text
~/.local/bin/nvim-nvda-bridge
~/.local/share/nvim/site/pack/nvim-nvda/start/nvim-nvda
```

Root-Rechte und eine manuelle Serverinstallation sind nicht erforderlich. Nach
einer reinen Änderung am NVDA-Add-on genügt dessen Neuinstallation. Wenn Bridge
oder Neovim-Plugin geändert wurden, müssen die Serverkomponenten über das Menü
erneut aktualisiert werden.

## tmux

tmux ist optional. Es hält Shell und Neovim bei einem Abbruch der sichtbaren
Arbeitsverbindung am Leben, ist aber nicht Bestandteil der Kommunikation
zwischen NVDA und Neovim.

Eine Escape-Wartezeit von 220 ms hat sich als brauchbarer Ausgangswert erwiesen. Sie verkürzt den
Wechsel vom Insert- in den Normalmodus gegenüber dem tmux-Standard und lässt
Windows-OpenSSH zugleich genügend Zeit, Terminalantworten vollständig zu
übertragen:

```text
set -sg escape-time 220
```

Für einen bereits laufenden tmux-Server gilt die Einstellung unmittelbar:

```text
tmux set-option -sg escape-time 220
```

Ein gelegentlich als `11;rgb:...` sichtbarer Text ist eine unvollständig
erkannte OSC-11-Farbantwort des Terminals. Ein höherer `escape-time`-Wert
reduziert dieses Risiko, erhöht aber entsprechend die Escape-Latenz.

## Verhalten bei Verbindungsabbrüchen

Die sichtbare Arbeitsverbindung und der vom Add-on verwaltete SSH-Prozess sind
voneinander unabhängig:

1. Bricht die Arbeitsverbindung ab, laufen tmux und Neovim weiter.
2. Der Add-on-Prozess kann seine eigene SSH-stdio-Verbindung weiter verwenden.
3. Bricht diese Verbindung ab, hebt das Add-on die Terminalunterdrückung auf.
4. Der Client verbindet sich mit begrenztem exponentiellem Backoff erneut.
5. Nach erfolgreicher Verbindung muss `fullState` die erste akzeptierte
   Zustandsnachricht sein.

Beim Deaktivieren der Bridge sowie beim Beenden oder Neustarten von NVDA wird
der zugehörige SSH-Prozess beendet. Neovim und tmux bleiben unberührt.

## Mehrere Neovim-Sitzungen

Jede Plugininstanz registriert PID, Socket, Startzeit, Name und
Arbeitsverzeichnis unter
`$XDG_RUNTIME_DIR/nvim-nvda/sessions`. Die Bridge verwirft veraltete Einträge
und das Add-on bietet mehrere lebende Sitzungen mit Name und Arbeitsverzeichnis
an. Der frei belegbare NVDA-Befehl „Server wählen und dieses Terminal mit einer
neuen Neovim-Sitzung verbinden“ fragt Profil und bei mehreren Sitzungen Name und
Arbeitsverzeichnis ab. Eine ältere Instanz in einem anderen oder abgetrennten
tmux-Fenster blockiert die Verbindung daher nicht.

Sind auch die Arbeitsverzeichnisse gleich, kann vor dem Start ein optionaler
Name gesetzt werden: `NVIM_NVDA_SESSION_NAME="Dokumentation" nvim`.
`:NvimNvdaSessionName Programmierung` ändert ihn zur Laufzeit, ein Aufruf ohne
Argument löscht ihn. Ohne Namen zeigt die Auswahl Startzeit und laufende Nummer;
bereits mit einem Terminal verbundene Sitzungen sind gekennzeichnet. Dafür sind
weder ein weiteres SSH-Profil noch ein anderer Port erforderlich.

Bei Windows Terminal kann eine erfolgreich verbundene Instanz auf Nachfrage
bis zum Ende von NVDA oder Windows Terminal an den aktuellen Tab gebunden
bleiben. Der Wechsel zwischen bestätigten Tabs aktiviert die jeweilige laufende
Verbindung. Diese Komfortfunktion verändert weder tmux noch die SSH-Sitzung und
speichert keine dauerhaften Terminalkennungen.

## Diagnose

Der kopierbare Diagnosebericht des Add-ons enthält Verbindungszustände sowie
SSH- und Bridgefehler, redigiert aber Editorinhalte. Bei einem NVDA-Absturz kann
`tools/windows/upload_nvda_logs.ps1` zusätzlich `nvda.log` und `nvda-old.log`
in den ignorierten Ordner `debug/incoming/` kopieren.
