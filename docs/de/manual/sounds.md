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
ausgegeben. Er folgt der Klangkomponente von „Globale Aktionsrückmeldung“ und
ist vom Editormodus unabhängig. Eine wiederholte `fullState`-Synchronisierung
innerhalb derselben verbundenen Transportlaufzeit erzeugt ihn nicht erneut.

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

Für Diagnosefehler und -warnungen werden zwei kurze Accessibility Signals aus
dem MIT-lizenzierten Code-OSS-Quellstand von Visual Studio Code verwendet.
Der genaue Commit, Quell- und Zielprüfsummen, die WAV-Dekodierung
sowie der vollständige MIT-Lizenztext liegen im Add-on unter
`resources/sounds/`. Wie in VS Code verwenden Zeilen- und Positionssignal je
Schweregrad dieselbe Datei. Bei ausdrücklicher Cursornavigation erklingt das
Zeilensignal einmal beim Eintritt in eine Diagnosezeile und das Positionssignal
an jeder erreichten Cursorposition innerhalb eines Diagnosebereichs. Tippen
und asynchrone `DiagnosticChanged`-Aktualisierungen bleiben stumm: Anders als
VS Code erhält das Add-on über das Terminal keine gleichwertige
editorinterne Information für dessen Marker-Timer und Tipp-Debounce. Die
Einstellungen „Diagnosezeile“ und „Diagnoseposition“ können beide Signalarten
getrennt abschalten.

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
