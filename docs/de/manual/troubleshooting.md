# Fehlerdiagnose und Diagnosebericht

Bei einem Fehler sollte zuerst geklärt werden, ob das Neovim-Plugin geladen ist,
die gewünschte Sitzung gefunden wird oder erst der eigentliche Transport
scheitert. Neovim Access Link enthält dafür einen kopierbaren Diagnosebericht.

## Diagnosebericht kopieren

Der Befehl befindet sich unter „NVDA-Menü → Optionen → Tastenbefehle… → Neovim
Access Link“. Standardmäßig ist `NVDA+Alt+D` zugewiesen. Der Bericht wird in die
Windows-Zwischenablage kopiert.

Editortext, Auswahl, Registerinhalt, Passwörter und Tokens werden durch
Platzhalter ersetzt. Technische Installationsmeldungen können dennoch lokale
Pfade, Profilnamen oder SSH-Ziele enthalten. Vor dem Weitergeben muss der
Bericht deshalb auf persönliche Systemangaben geprüft werden.

## Das Add-on reagiert nicht

1. Prüfen, ob Windows Terminal fokussiert ist. Das Add-on greift absichtlich
   nicht in Notepad, PuTTY oder andere Anwendungen ein.
2. Unter „NVDA-Menü → Optionen → Tastenbefehle…“ prüfen, ob dem
   Aktivierungsbefehl eine Geste zugewiesen wurde.
3. NVDA neu starten und erneut testen.
4. Prüfen, ob „Neovim Access Link“ in NVDAs Liste installierter Add-ons
   aktiviert ist.

## Das lokale Plugin wird nicht gefunden

Neovim nach jeder Komponenteninstallation vollständig schließen und neu
starten. Ein bereits laufendes Neovim verwendet weiterhin die Pluginfassung,
die beim Start geladen wurde.

Im lokalen Neovim prüfen:

```vim
:echo exists(':NvimNvdaSessionName')
```

Die erwartete Ausgabe ist `2`. Bei einem anderen Wert:

1. alle lokalen Neovim-Instanzen schließen,
2. im Komponentenmenü ausschließlich „This computer“ aktualisieren,
3. das Ergebnis prüfen,
4. Neovim neu starten.

## F12 stellt keine Verbindung her

1. Nach dem Aktivieren die Bereitschaftsmeldung abwarten.
2. Das gewünschte Neovim fokussieren.
3. F12 einmal drücken und bis zu zwei Sekunden warten.
4. Nicht mehrfach schnell hintereinander drücken; jeder neue Tastendruck startet
   eine neue Zuordnungsauflösung.
5. Den manuellen Befehl „Server wählen und dieses Terminal mit einer neuen
   Neovim-Sitzung verbinden“ testen.

Im Diagnosebericht sind besonders diese Kategorien hilfreich:

- `claimInventoryReady`: Anzahl gefundener lokaler und entfernter Sitzungen,
- `sessionClaimGestureReceived`: F12 hat das Windows-Terminal-AppModule erreicht,
- `automaticLocalClaimChecked`: Ergebnis der lokalen Nachsuche,
- `automaticClaimResolutionCompleted`: Anzahl eindeutiger Treffer,
- `localTcpStart` oder `sshProcessStart`: der Transport wurde gestartet.

Fehlt `sessionClaimGestureReceived`, war entweder nicht Windows Terminal
fokussiert oder die F12-Geste erreichte das AppModule nicht. Werden null lokale
Sitzungen gemeldet, ist meist das lokale Plugin nicht geladen.

## SSH-Verbindung schlägt fehl

Die gleiche Anmeldung zuerst außerhalb des Add-ons in Windows Terminal prüfen:

```text
ssh benutzer@example.invalid
```

Dabei müssen Hostschlüssel bestätigt, Schlüsseldateien lesbar und eventuelle
Schlüsselpassphrasen über `ssh-agent` oder die normale OpenSSH-Abfrage
verfügbar sein. Bei Passwortprofilen muss der Server Passwortanmeldung für das
betreffende Konto erlauben.

Das Add-on ändert weder die Windows-SSH-Konfiguration noch `sshd_config` auf dem
Server. Ein Fehler wie „Host key verification failed“ muss daher zuerst mit dem
normalen Windows-OpenSSH-Client behoben werden.

## Die falsche Sitzung ist verbunden

1. Den betroffenen Tab fokussieren.
2. Die Verbindung für diesen Tab trennen oder die temporäre Terminalbindung
   vergessen.
3. Das gewünschte Neovim fokussieren und erneut F12 drücken.
4. Bei identischen Arbeitsverzeichnissen freiwillige Sitzungsnamen verwenden.

Beispiel unter Linux:

```text
NVIM_NVDA_SESSION_NAME=Dokumentation nvim
```

Bereits verbundene Sitzungen werden im manuellen Dialog entsprechend
gekennzeichnet.

## Terminalfragmente werden gesprochen

Bei einer korrekt verbundenen, fokussierten Neovim-Sitzung unterdrückt das
Add-on die native Terminalausgabe und verwendet strukturierte Ereignisse. Die
Unterdrückung ist absichtlich nicht global. Sie endet insbesondere:

- nach einer Deaktivierung oder einem Verbindungsabbruch,
- in einem nicht zugeordneten Tab,
- bei einem eingebetteten `:terminal` im direkten Terminalmodus,
- wenn das Sitzungs- oder Fokus-Gate die Zuordnung nicht sicher bestätigen kann.

Treten Fragmente nur nach einem Tabwechsel auf, im Diagnosebericht die
Terminalidentität und die ausgewählte Verbindungsinstanz prüfen. Der Bericht
sollte unmittelbar nach dem unerwünschten Fragment kopiert werden.

## NVDA reagiert nach einem Dialog nicht

Komponenteninstallation und SSH-Abfragen laufen im Hintergrund. Ein sichtbarer
Ergebnisdialog darf NVDA nicht blockieren. Falls NVDA dennoch nicht reagiert:

1. mit `Alt+Tab` nach einem offenen Ergebnis- oder Passwortdialog suchen,
2. den Dialog schließen oder abbrechen,
3. falls nötig NVDA neu starten,
4. anschließend Diagnosebericht und NVDAs vorheriges Protokoll sichern.

NVDAs Protokolle können über den normalen NVDA-Protokollbetrachter geöffnet
werden. Zugangsdaten oder vertraulicher Editortext dürfen nicht ungeprüft
weitergegeben werden.
