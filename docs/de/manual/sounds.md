# Sounds und Earcons

Alle Audiodateien werden beim Start des Add-ons vollständig eingelesen. Beim
Auslösen eines Ereignisses erfolgt deshalb kein Dateizugriff. Fehlt eine Datei
oder kann sie nicht abgespielt werden, bleibt das Add-on funktionsfähig und
verwendet den bisherigen kurzen synthetischen Ton als Rückfall.

## Mit NVDA gelieferte Sounds

Das Add-on verwendet direkt aus dem installierten NVDA-Verzeichnis:

| Ereignis | NVDA-Datei |
| --- | --- |
| Insert-Modus | `waves/focusMode.wav` |
| Normalmodus nach Insert | `waves/browseMode.wav` |
| fehlendes Klammerpaar | `waves/error.wav` |
| Vorschlagsmenü geöffnet/geschlossen | `waves/suggestionsOpened.wav`, `waves/suggestionsClosed.wav` |
| Rechtschreib- oder Grammatikfehler | `waves/textError.wav` |

Diese Dateien werden nicht in das Add-on kopiert. Dadurch bleiben die Klänge
mit der jeweils installierten NVDA-Version konsistent.

## Mitgelieferte CC0-Earcons

Für Löschen, Ersetzen, Zeilen- und Dateigrenzen sowie einen Zeilenwechsel gibt
es in NVDA keine eindeutig passenden öffentlichen Standardsounds. Das Add-on
liefert dafür sieben kurze, latenzarme Earcons aus Kenney UI Audio 1.0 mit. Sie
stehen unter CC0-1.0; Herkunft und Zuordnung stehen zusätzlich in der
mitgelieferten `resources/sounds/LICENSE.txt`.

Der Lösch- und Backspace-Klang verwendet den bewusst dezenten `click3`: rund
86 ms lang und mit etwa −27,6 dB RMS deutlich leiser als der zuvor verwendete
`click2`.

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
