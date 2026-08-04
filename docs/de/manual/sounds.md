# Sounds und Earcons

Alle Audiodateien werden beim Start des Add-ons vollständig eingelesen. Beim
Auslösen eines Ereignisses erfolgt deshalb kein Dateizugriff. Fehlt eine Datei
oder kann sie nicht abgespielt werden, bleibt das Add-on funktionsfähig und
verwendet den bisherigen kurzen synthetischen Ton als Rückfall.

## Mit NVDA gelieferte Sounds

Das Add-on verwendet direkt aus dem installierten NVDA-Verzeichnis:

| Ereignis | NVDA-Datei |
| --- | --- |
| neue authentifizierte oder nach einer Trennung wiederhergestellte Neovim-Verbindung | `waves/connected.wav` |
| echte Trennung einer zuvor verbundenen, fokussierten Neovim-Instanz | `waves/disconnected.wav` |
| Insert-Modus oder direkte Terminaleingabe | `waves/focusMode.wav` |
| Normal- oder Terminal-Normalmodus nach Insert beziehungsweise direkter Terminaleingabe | `waves/browseMode.wav` |
| Neovim-Kommandozeile | kurzer synthetischer Ton mit 600 Hz |
| fehlendes Klammerpaar | `waves/error.wav` |
| Vorschlagsmenü geöffnet/geschlossen | `waves/suggestionsOpened.wav`, `waves/suggestionsClosed.wav` |
| Rechtschreib- oder Grammatikfehler | `waves/textError.wav` |

Der Kommandozeilenton benötigt keine Audiodatei. Die übrigen Dateien dieser
Tabelle werden nicht in das Add-on kopiert. Dadurch bleiben die Klänge
mit der jeweils installierten NVDA-Version konsistent.

`connected.wav` wird genau beim ersten authentifizierten vollständigen Zustand
einer Verbindungsinstanz und erneut nach einer echten Transporttrennung
ausgegeben. `disconnected.wav` meldet genau den Übergang einer zuvor
verbundenen, aktuell fokussierten Instanz in den getrennten Zustand; ein
anfänglicher oder wiederholt gemeldeter getrennter Zustand bleibt still. Beide
folgen der Klangkomponente von „Globale Aktionsrückmeldung“ und sind vom
Editormodus unabhängig. Eine wiederholte `fullState`-Synchronisierung innerhalb
derselben verbundenen Transportlaufzeit erzeugt keinen weiteren Klang.

Die Modusklänge bestätigen dagegen einen tatsächlichen Moduswechsel oder einen
korrelierten Fokuskontext. Der erste vollständige Zustand einer nach F12 neu
erzeugten Verbindungsinstanz ist kein solcher Wechsel und erzeugt daher keinen
Normalmodusklang. Ein später bestätigter Fokuskontext darf höchstens einen
zusätzlichen, semantisch getrennten Normal- oder Insertmodusklang auslösen.
Wenn Klänge abgeschaltet sind, bleiben die Ansage, dass die Neovim-Verbindung
gestartet wurde, und anschließend funktionierende semantische Ausgaben die
maßgeblichen Prüfungen.

Der Rechtschreibklang wird nach Abschluss eines fehlerhaften Wortes sowie beim
Erreichen eines betroffenen Worts durch normale Wortnavigation oder
Wortexploration im Sprachexplorationsmodus ausgegeben. Maßgeblich bleiben NVDAs Einstellungen für
Rechtschreib- und Grammatikfehler; das Add-on führt dafür keine abweichende
Option ein. Dort sind Sprache, Klang und Braille unabhängig auswählbar:
„Sprache“ steuert den lokalisierten Hinweis „Rechtschreibfehler“ oder
„Grammatikfehler“, „Signaltöne“ steuert `textError.wav`, und „Braille“ steuert nur
die Fehlermarkierung auf der Braillezeile. Normale Wortnavigation und
Wortexploration im Sprachexplorationsmodus werten dieselbe Kombination aus; das erreichte Wort wird
unabhängig davon weiterhin angesagt.

## Mitgelieferte Earcons

Für Löschen, Ersetzen, Zeilen- und Dateigrenzen sowie einen Zeilenwechsel gibt
es in NVDA keine eindeutig passenden öffentlichen Standardsounds. Das Add-on
liefert dafür sieben kurze, latenzarme Earcons aus Kenney UI Audio 1.0 mit. Sie
stehen unter CC0-1.0; Herkunft und Zuordnung stehen zusätzlich in der
mitgelieferten `resources/sounds/LICENSE.txt`.

Der Lösch- und Backspace-Klang verwendet den bewusst dezenten `click3`: rund
86 ms lang und mit etwa −27,6 dB RMS deutlich leiser als der zuvor verwendete
`click2`.

Für Diagnosefehler, -warnungen und die ausdrückliche leere Diagnoseabfrage
werden drei kurze Accessibility Signals aus dem MIT-lizenzierten
Code-OSS-Quellstand von Visual Studio Code verwendet.
Der genaue Commit, Quell- und Zielprüfsummen, die WAV-Dekodierung
sowie der vollständige MIT-Lizenztext liegen im Add-on unter
`resources/sounds/`. Wie in VS Code verwenden Zeilen- und Positionssignal je
Schweregrad dieselbe Datei. Die in den dekodierten Dateien enthaltene bis zu
rund 0,9 Sekunden lange digitale Stille am Ende ist verlustfrei bis auf einen
5-ms-Ausklang entfernt; kein von null verschiedenes PCM-Frame wurde verändert
oder verworfen. Vor jedem gezielt ausgelösten Diagnosesignal wird außerdem
der bereits im RAM gehaltene Player neu gestartet. Dadurch erhält auch
der nächste gleichartige Eintrag derselben Zeile sofort einen eigenen Klang. Bei
ausdrücklicher Cursornavigation erklingt das Zeilensignal einmal beim Eintritt
in eine Diagnosezeile und das Positionssignal an jeder erreichten
Cursorposition innerhalb eines Diagnosebereichs. Tippen
und asynchrone `DiagnosticChanged`-Aktualisierungen bleiben stumm: Anders als
VS Code erhält das Add-on über das Terminal keine gleichwertige
editorinterne Information für dessen Marker-Timer und Tipp-Debounce. Die
Einstellungen „Diagnosezeile“ und „Diagnoseposition“ können beide Signalarten
getrennt abschalten.

Visual Studio Codes Diagnosenavigation beendet eine leere Suche still. Das
dort vorhandene, aber sachlich andere Signal „keine Inlay-Hinweise“ verwendet
sogar dieselbe Audiodatei wie ein Diagnosefehler. Access Link verwendet daher
für ein ausdrücklich abgefragtes leeres Ergebnis stattdessen den
unverwechselbaren Code-OSS-Klang `clear.mp3`, auf rund 262 ms mit 5 ms
Ausklang gekürzt. Er folgt bei `NvimNvdaDiagnosticCurrent` und den übrigen
Diagnosebefehlen der Einstellung „Diagnoseposition“, bei einer leeren
gehaltenen Abfrage mit `NVDA+Umschalt+Leertaste` der Einstellung „Diagnosezeile“.
Bloße Cursorbewegung über fehlerfreie Zeilen bleibt still. Informationen und
Hinweise bleiben ebenfalls klanglos; der neue Klang bezeichnet kein Problem,
sondern bestätigt nur eine aktive Abfrage ohne Treffer.

## Einrückung

Die Einrückungstöne bleiben unverändert. Sie folgen NVDA: 220 Hz Grundton,
Vierteltonschritte je Leerzeichen, vier Schritte je Tabulator sowie die in NVDA
konfigurierte Tondauer. Sie werden nur bei einer Änderung der Einrückung
ausgegeben und richten sich nach den Einstellungen unter
„Dokument-Formatierungen“.

## Diagnose

Laden, Abspielen und Fehler werden als `editorSoundLoaded`,
`editorSoundPlayed`, `editorSoundLoadError` oder `editorSoundPlayError` in den
kopierbaren Add-on-Diagnosebericht geschrieben. Textinhalte bleiben redigiert.
