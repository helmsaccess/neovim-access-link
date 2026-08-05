# Sounds und Earcons

Access Link verwendet kurze Klänge, damit häufige Editorzustände nicht jedes
Mal gesprochen werden müssen. Die Registerkarte `Rückmeldung` schaltet Sprache
und Töne je Ereignis getrennt. Tippecho, Einrückung, Rechtschreibung und
Grammatik folgen NVDAs eigenen Einstellungen.

## Klangübersicht

| Ereignis | Klang | Einstellung |
| --- | --- | --- |
| Verbindung hergestellt | NVDAs `connected.wav` | `Globale Aktionsrückmeldung` |
| aktive Verbindung getrennt | NVDAs `disconnected.wav` | `Globale Aktionsrückmeldung` |
| Insert-Modus oder direkte Terminaleingabe | NVDAs Fokusmodusklang | `Wechsel zwischen Einfüge- und Normalmodus` |
| Normal- oder Terminal-Normalmodus | NVDAs Lesemodusklang | `Wechsel zwischen Einfüge- und Normalmodus` |
| Neovim-Befehlszeile | kurzer mittlerer Ton | `Wechsel zwischen Einfüge- und Normalmodus` |
| Text löschen | kurzer Löschklang | `Text löschen` |
| Text ersetzen | kurzer Ersetzungsklang | `Text ersetzen` |
| Zeilenanfang oder -ende | unterschiedliche Grenzklänge | `Zeilengrenzen` |
| Dateianfang oder -ende | unterschiedliche Grenzklänge | `Dateigrenzen` |
| horizontale Bewegung in eine andere Zeile | kurzer Übergangsklang | `Wechsel in eine andere Zeile` |
| fehlendes Klammerpaar | NVDAs Fehlerklang | `Fehlende zusammengehörige Klammer` |
| Vorschlagsmenü geöffnet oder geschlossen | NVDAs Vorschlagsklänge | NVDA-Einstellung für Vorschläge |
| Rechtschreib- oder Grammatikfehler | NVDAs Textfehlerklang | NVDA-Dokumentformatierung |
| Diagnosezeile oder Diagnoseposition | kurzer Fehler- oder Warnklang | jeweilige Diagnoseeinstellung |
| ausdrückliche Diagnoseabfrage ohne Treffer | kurzer neutraler Bestätigungsklang | jeweilige Diagnoseeinstellung |

Ein Verbindungs- oder Modusklang wird nur für den entsprechenden bestätigten
Zustandswechsel ausgegeben. Eine erneute Synchronisierung desselben Zustands
wiederholt ihn nicht.

## Einrückung

Einrückung folgt NVDAs Einstellung unter `Dokument-Formatierungen`. Access Link
verwendet NVDAs Tonhöhe und Tondauer und gibt einen Einrückungston nur bei
geänderter Einrückung aus.

## Rechtschreibung und Grammatik

NVDAs Dokumentformatierung steuert Sprache, Signaltöne und Braillemarkierung
unabhängig:

- `Sprache` steuert den lokalisierten Hinweis auf Rechtschreib- oder
  Grammatikfehler.
- `Signaltöne` steuert den Textfehlerklang.
- `Braille` steuert die Markierung auf der Braillezeile.

Dieselbe Einstellung gilt beim Abschluss eines fehlerhaften Wortes, bei
normaler Wortnavigation und bei Wortexploration. Das erreichte Wort wird
unabhängig von der Fehlerrückmeldung weiterhin gesprochen.

## Diagnosen

Fehler und Warnungen besitzen getrennte kurze Klänge. Access Link spielt sie
bei gezielter Navigation in eine Diagnosezeile oder an eine Diagnoseposition.
Tippen und reine Hintergrundaktualisierungen bleiben still. Informationen und
Hinweise erzeugen keinen Diagnoseklang.

Eine ausdrücklich gestartete Diagnoseabfrage ohne Treffer verwendet einen
eigenen neutralen Klang und die Meldung `keine Diagnose`. Normale Navigation
über fehlerfreien Text bleibt still.

Die Quellen und Lizenzen aller mitgelieferten Audiodateien stehen in
`resources/sounds/LICENSE.txt` des installierten Add-ons und in der
Entwicklerdokumentation.
