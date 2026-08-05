# Neovim Access Link – Quick Guide

Dieser Quick Guide führt erfahrene NVDA-Nutzer mit wenig Neovim-Erfahrung von
der Installation bis zu einer bestätigten ersten Verbindung. Die vollständige
Bedienung steht im [Handbuch](README.md).

Access Link unterstützt Neovim in Windows Terminal lokal unter Windows und
entfernt auf Linux über SSH. Mehrere Fenster, Tabs und geteilte Panes dürfen
lokale Neovim-Sitzungen, entfernte Neovim-Sitzungen und normale Shells mischen.
Andere Terminalprogramme und grafische Neovim-Oberflächen sind nicht
unterstützt.

Der entfernte Pfad verwendet Linux, Python 3 und OpenSSH. Praktisch bestätigt
ist Rocky Linux 10.2; weitere Linux-Systeme sind nicht praktisch bestätigt.

## 1. Voraussetzungen prüfen

Erforderlich sind:

- Windows 11;
- NVDA 2026.1.x;
- Windows Terminal;
- Neovim 0.10.1 oder neuer.

Öffnen Sie Windows Terminal und prüfen Sie die lokale Installation:

```text
nvim.exe --version
```

Für Neovim auf Linux benötigen Sie zusätzlich Python 3 auf dem Linux-Ziel, den
Windows-OpenSSH-Client und eine funktionierende SSH-Anmeldung. Prüfen Sie diese
Anmeldung vor der Access-Link-Einrichtung:

```text
ssh benutzer@example.invalid
```

Schlüssel, `ssh-agent`, eine OpenSSH-Konfiguration oder eine vom Add-on
angeforderte Passwortanmeldung sind unterstützt.

## 2. Add-on installieren

1. Öffnen Sie `NeovimAccessLink-<Version>.nvda-addon` unter Windows.
2. Bestätigen Sie die Installation in NVDA.
3. Starten Sie NVDA neu.

Nach dem Neustart enthält `NVDA-Menü → Optionen → Einstellungen…` die Kategorie
`Neovim Access Link`.

## 3. Aktivierungsgeste zuweisen

1. Fokussieren Sie Windows Terminal.
2. Öffnen Sie `NVDA-Menü → Optionen → Tastenbefehle…`.
3. Öffnen Sie die Kategorie `Neovim Access Link`.
4. Weisen Sie dem Befehl `Neovim-Barrierefreiheit ein- oder ausschalten und
   konfigurierte Verbindungen erkennen` eine gut erreichbare Geste zu.

Verwenden Sie nicht `Ctrl+Alt+N`, wenn diese Kombination in Ihrer
NVDA-Installation NVDA neu startet.

Die zugewiesene Geste ist ein **NVDA-Befehl**: NVDA verarbeitet sie bei
fokussiertem Windows Terminal. `F12` ist dagegen keine Aktivierungsgeste.
Access Link reicht F12 an Neovim weiter und verwendet den Tastendruck danach,
um die fokussierte Neovim-Sitzung eindeutig auszuwählen.

## 4. Komponenten installieren

Schließen Sie vor einer Installation oder Aktualisierung alle betroffenen
Neovim-Instanzen.

1. Öffnen Sie `NVDA-Menü → Werkzeuge → Neovim Access Link: Komponenten
   installieren oder aktualisieren...`.
2. Markieren Sie `Dieser Computer – lokales Neovim` für lokales
   Windows-Neovim.
3. Markieren Sie gespeicherte Linux-Verbindungen für entfernte Sitzungen.
4. Bestätigen Sie mit `OK`.
5. Prüfen Sie im Ergebnisdialog jedes ausgewählte Ziel.

Access Link installiert seine mitgelieferte Plugin-Kopie in Neovims
Standarddatenverzeichnis. Eine einfache Neovim-Konfiguration lädt dieses
Start-Plugin beim nächsten Neovim-Start automatisch. Ein Plugin-Manager, der
Neovims `packpath` oder Start-Plugins ersetzt, muss die bereits installierte
lokale Kopie ausdrücklich laden. Installieren Sie keine zweite Access-Link-
Kopie aus einem Plugin-Repository. Das optionale
[Lazy-Beispiel](example-configuration.md) zeigt die passende Einbindung.

## 5. Optional: Linux-Verbindung speichern

Überspringen Sie diesen Abschnitt für lokales Windows-Neovim.

1. Öffnen Sie `NVDA-Menü → Optionen → Einstellungen… → Neovim Access Link`.
2. Öffnen Sie die Registerkarte `Verbindungen`.
3. Wählen Sie `Verbindung hinzufügen...`.
4. Tragen Sie Verbindungsname, Server oder SSH-Alias und SSH-Port ein.
5. Tragen Sie den Linux-Benutzernamen ein, sofern die OpenSSH-Konfiguration ihn
   nicht festlegt.
6. Wählen Sie die Anmeldemethode.
7. Bestätigen Sie das Formular und danach den NVDA-Einstellungsdialog.
8. Installieren Sie die Komponenten für diese Verbindung wie in Abschnitt 4.

`OpenSSH-Einrichtung verwenden (empfohlen: Schlüssel, ssh-agent oder
SSH-Konfiguration)` verwendet Ihre normale Windows-OpenSSH-Einrichtung. `Beim
Verbinden nach dem SSH-Passwort fragen (Passwort wird nicht gespeichert)` hält
das eingegebene Passwort nur bis zum Ende der aktuellen NVDA-Laufzeit im
Arbeitsspeicher.

## 6. Erste Sitzung verbinden

### Lokal unter Windows

1. Starten Sie `nvim.exe` in Windows Terminal.
2. Drücken Sie die in Abschnitt 3 zugewiesene Aktivierungsgeste.
3. Warten Sie auf die Meldung, dass lokale und gespeicherte Verbindungen geprüft
   werden beziehungsweise bereitstehen.
4. Fokussieren Sie das gewünschte Neovim und drücken Sie F12 einmal.
5. Warten Sie auf die Verbindungsbestätigung.

### Auf Linux über SSH

1. Melden Sie sich im gewünschten Windows-Terminal-Tab oder -Pane per SSH an.
2. Starten Sie auf dem Linux-Ziel `nvim`.
3. Drücken Sie die Aktivierungsgeste und warten Sie auf die Bereitschaftsmeldung.
4. Fokussieren Sie das gewünschte Neovim und drücken Sie F12 einmal.
5. Warten Sie auf die Verbindungsbestätigung.

## 7. Verbindung praktisch bestätigen

Verwenden Sie einen unwichtigen Buffer:

1. Drücken Sie `i`. Access Link meldet den Insert-Modus entsprechend Ihren
   Einstellungen.
2. Schreiben Sie eine kurze Zeile.
3. Drücken Sie `Esc`. Access Link meldet den Normalmodus.
4. Navigieren Sie mit `h` und `l` zeichenweise sowie mit `j` und `k`
   zeilenweise. Neovim bewegt den Cursor; Access Link spricht die semantische
   Position und spielt konfigurierte Grenzklänge.
5. Halten Sie die NVDA-Taste und drücken Sie `h` oder `l`. Access Link liest
   Zeichen, ohne den echten Neovim-Cursor zu bewegen. Beim Loslassen der
   NVDA-Taste kehrt die Ausgabe zum echten Cursor zurück.

Die letzten beiden Schritte zeigen den Unterschied der Eingabeebenen: `h`,
`j`, `k` und `l` ohne NVDA-Taste sind normale Neovim-Befehle. Access Link macht
ihre Wirkung zugänglich. `NVDA+h`, `NVDA+j`, `NVDA+k` und `NVDA+l` sind
kontextbezogene NVDA-Befehle für die Sprachexploration.

## 8. Tabs und Panes prüfen

Ein Windows-Terminal-Tab enthält ein Terminal. Ein geteilter Tab enthält
mehrere Panes und damit mehrere getrennte Terminals.

1. Wechseln Sie in ein anderes Pane mit einer normalen Shell. NVDA verwendet
   dort seine normale Terminalausgabe; Access Link übernimmt keine
   Neovim-Tastenkombinationen.
2. Wechseln Sie zurück zur verbundenen Neovim-Pane. Access Link stellt nach der
   bestätigten Fokusantwort die strukturierte Ausgabe wieder her.
3. Starten Sie bei Bedarf Neovim in einem weiteren Tab oder Pane und drücken Sie
   dort F12. Die erste Zuordnung bleibt bestehen.

## 9. Wenn keine Verbindung entsteht

Prüfen Sie in dieser Reihenfolge:

1. Läuft Neovim in Windows Terminal?
2. Ist die Aktivierungsgeste zugewiesen und wurde sie vor F12 gedrückt?
3. Wurde Neovim nach der Komponenteninstallation vollständig neu gestartet?
4. Lädt die Neovim-Konfiguration das installierte Access-Link-Plugin?
5. Funktioniert bei Linux die normale SSH-Anmeldung außerhalb des Add-ons?

Prüfen Sie das Plugin in Neovim:

```vim
:echo exists(':NvimNvdaSessionName')
```

Die Ausgabe `2` bestätigt, dass Neovim das Plugin geladen hat. Bei einer anderen
Ausgabe schließen Sie alle betroffenen Neovim-Instanzen, aktualisieren die
Komponenten und prüfen die Plugin-Manager-Konfiguration.

`NVDA+Alt+D` kopiert den redigierten Diagnosebericht. Prüfen Sie ihn vor dem
Weitergeben trotzdem auf lokale Pfade, Profilnamen und SSH-Ziele.

Die erste Verbindung ist damit eingerichtet. Das
[Handbuch](README.md) erklärt Neovim-Grundlagen, tägliche Bedienung, Braille,
Completion, Diagnosen, Dateiverwaltung und sämtliche Einstellungen.
