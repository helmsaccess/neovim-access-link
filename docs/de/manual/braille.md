# Braille-Unterstützung

Nach dem Verbinden zeigt Neovim Access Link die aktuelle Neovim-Zeile auf der
Braillezeile an. Die Brailleübersetzung, der Brailletreiber und die Darstellung
des Cursors werden weiterhin in NVDA eingestellt.

Die Funktionen wurden praktisch mit einer Papenmeier BRAILLEX EL 80c mit
80 Braillemodulen getestet. Sie verwenden NVDAs normale Brailletreiber- und
Navigationsbefehle und sind nicht auf dieses Modell beschränkt; andere von
NVDA unterstützte Braillezeilen sollten entsprechend funktionieren.

Die Anzeige enthält nur die für die Arbeit in Neovim wichtigen Informationen.
Bezeichnungen von Windows Terminal wie „Windows PowerShell“, Statuszeilen und
Inhalte anderer Terminalbereiche werden nicht vor den Editortext gesetzt.

## Was auf der Braillezeile erscheint

Im Editor zeigt die Braillezeile:

- den Text der aktuellen Zeile,
- die Cursorposition,
- eine Visual-Auswahl auf der aktuellen Zeile,
- Tabulatoren, die nach Neovims `tabstop`-Wert in Leerzellen aufgelöst werden,
- Einrückung,
- vorübergehende Meldungen, beispielsweise einen Rechtschreibvorschlag.

In unterstützten Dateimanagern erscheinen statt dekorierter Pluginzeilen der
Name, der Typ und der Zustand des aktuellen Eintrags. Weitere Informationen
dazu stehen im Kapitel
[Eingebettetes Terminal und Dateimanager](terminals-and-file-managers.md).

NVDA sollte für die normale Editoranzeige auf „Cursor verfolgen“ eingestellt
sein. Bei „Sprachausgabe anzeigen“ gibt die Braillezeile wie von NVDA
vorgesehen die gesprochene Ausgabe wieder und folgt nicht dauerhaft der
Editorzeile.

Bewegt sich der Neovim-Cursor außerhalb des gerade sichtbaren Ausschnitts,
schiebt NVDA die Brailleanzeige automatisch nach. Das gilt auch beim Schreiben
einer langen Zeile im Insert-Modus und beim Bewegen des Cursors in der
Neovim-Befehlszeile. Ein zuvor mit Links oder Rechts gewählter Ausschnitt bleibt
erhalten, solange der Cursor darin sichtbar ist.

## Braille-Einstellungen des Add-ons

Neovim Access Link besitzt im Einstellungsdialog eine eigene Registerkarte
`Braille`. Dort stehen ausschließlich Einstellungen, die das Add-on selbst
ergänzt:

| Einstellung | Standard | Bedeutung |
| --- | --- | --- |
| Braillezeile folgt der Position des Sprachexplorationsmodus | Ein | Zeigt die virtuelle Sprachposition vorübergehend auch auf Braille. |
| Doppelte Routingbetätigung auf einem Wort | Nur Cursor setzen | Kann wahlweise `cw` oder `dw` ausführen. |
| Dreifache Routingbetätigung auf einer Zeile | Nur Cursor setzen | Kann wahlweise `c$` oder `d$` ausführen. |
| Start der dreifachen Zeilenaktion | Routingposition | Beginnt an der Routingtaste, an der Einrückung oder am absoluten Zeilenanfang. |
| Rechtschreibvorschläge ab Braillemodul anzeigen | 1 | Verschiebt nur den vorübergehenden Rechtschreibvorschlag. |

Brailleübersetzung, Treiber, Cursorform, Auswahlmarkierung und das Ansagen des
Zeichens beim Routing bleiben normale NVDA-Einstellungen. Eine ausführliche
Beschreibung aller Auswahlwerte steht unter
[Einstellungen des NVDA-Add-ons](settings.md#registerkarte-braille).

## Cursor mit Routingtasten versetzen

Eine Routingtaste über einem Zeichen setzt den Neovim-Cursor auf dieses
Zeichen. Das funktioniert im Normal-, Insert- und Befehlszeilenmodus.

Wenn NVDA unter `Optionen → Einstellungen → Braille` die Option
„Zeichen beim Cursor-Routing in Text sprechen“ aktiviert hat, wird das
erreichte Zeichen angesagt.

Die Position hinter dem letzten Zeichen hängt vom Neovim-Modus ab:

- **Insert-Modus:** Hinter dem letzten Zeichen befindet sich eine zusätzliche
  leere Braillezelle. Ihre Routingtaste setzt die Einfügeposition ans
  Zeilenende.
- **Befehlszeilenmodus:** Auch hinter dem eingegebenen Befehl befindet sich
  eine zusätzliche leere Zelle. Damit lässt sich der Cursor hinter das letzte
  Zeichen setzen.
- **Normalmodus:** Der Cursor steht auf einem vorhandenen Zeichen. Deshalb
  gibt es hinter dem letzten Zeichen keine zusätzliche Routingposition.
- **Leere Zeile:** Auf einer vollständig leeren Zeile ist eine einzelne
  Cursorzelle vorhanden.

Die zusätzliche Zelle im Insert- und Befehlszeilenmodus fügt kein Leerzeichen
in den Text ein. Sie stellt nur die Position hinter dem Zeilenende dar.

Routing über Tabulatoren, Umlaute, breite Zeichen und Emoji wird an die
zugehörige Textposition weitergegeben. Ist eine angezeigte Information keine
Textposition, bleibt ihre Routingtaste ohne Wirkung.

## Warum der Cursor beim Verlassen des Insert-Modus nach links geht

Beim Wechsel vom Insert- in den Normalmodus scheint der Cursor häufig ein
Zeichen nach links zu springen. Das ist das normale Verhalten von Neovim und
kein Fehler von Neovim Access Link.

Im Insert-Modus bezeichnet der Cursor eine Einfügeposition zwischen Zeichen.
Diese Position darf direkt hinter dem letzten Zeichen liegen:

```text
Insert-Modus: hallo|
```

Im Normalmodus bezeichnet der Cursor dagegen das Zeichen, auf das der nächste
Befehl wirkt:

```text
Normalmodus:  hall[o]
```

Beim Drücken von `Esc` verändert Neovim den Text nicht. Es setzt den
Normalmodus-Cursor auf das Zeichen links von der bisherigen Einfügeposition.
Dadurch können Befehle wie `x` oder `r` auf das Zeichen unter dem Cursor
wirken. Mit `i` wird vor diesem Zeichen und mit `a` danach eingefügt.

Dasselbe gilt innerhalb einer Zeile:

```text
Insert-Modus: hal|lo
Normalmodus:  ha[l]lo
```

Neovim Access Link zeigt in beiden Modi die tatsächliche Neovim-Position an.
Mit `gi` kann der Insert-Modus an der zuletzt verlassenen Einfügeposition
fortgesetzt werden.

Weitere Informationen bieten die offiziellen Neovim-Hilfeseiten zu
[Insert-Modus](https://neovim.io/doc/user/insert/) und
[Cursorbewegungen](https://neovim.io/doc/user/motion/).

## Wörter und Zeilenteile mit Routingtasten bearbeiten

Eine Routingtaste kann wahlweise auch einen Neovim-Änderungs- oder
Löschbefehl auslösen, wenn dieselbe Taste schnell zwei- oder dreimal gedrückt
wird. Diese Bearbeitungsfunktionen sind zunächst ausgeschaltet. Eine einzelne
Betätigung setzt deshalb immer nur den Cursor.

Die Einstellungen stehen unter `NVDA-Menü → Optionen → Einstellungen →
Neovim Access Link → Braille`:

- **Doppelte Betätigung auf einem Wort:** Nur Cursor setzen, Wort ändern
  (`cw`) oder Wort löschen (`dw`).
- **Dreifache Betätigung auf einer Zeile:** Nur Cursor setzen, bis zum
  Zeilenende ändern (`c$`) oder bis zum Zeilenende löschen (`d$`).
- **Start der Zeilenaktion:** An der gewählten Routingposition, am ersten
  Nicht-Leerzeichen oder am absoluten Zeilenanfang.

„Wort ändern“ entfernt das Wort und bleibt im Insert-Modus, damit sofort
Ersatztext eingegeben werden kann. „Wort löschen“ verwendet Neovims normales
`dw`-Verhalten und löscht in der Regel auch den folgenden Zwischenraum.
Die Zeilenaktionen wirken einschließlich des Zeichens an ihrer Startposition
bis zum Zeilenende. Bei „erstes Nicht-Leerzeichen“ bleibt die Einrückung
erhalten; bei „Zeilenanfang“ gehört auch die Einrückung zur Aktion.

Die erste Betätigung setzt den Cursor sofort. Ist eine dreifache Aktion
eingeschaltet, wartet eine konfigurierte doppelte Wortaktion kurz, damit noch
eine dritte Betätigung erkannt werden kann. Die Wartezeit entspricht NVDAs
Einstellung `Optionen → Einstellungen → Tastatur → Zeitüberschreitung für
Mehrfachbetätigungen`.

Alle Betätigungen müssen dieselbe Routingtaste an derselben Textposition
treffen. Eine andere Position, eine Textänderung, ein Moduswechsel oder eine
überschrittene Wartezeit beginnt wieder mit einer einzelnen Cursorbewegung.
Die Bearbeitungsaktionen sind nur im Normal- und Insert-Modus verfügbar. In
der Neovim-Befehlszeile und im direkten Eingabemodus eines eingebetteten
Terminals bleibt es bei der normalen Cursorpositionierung.

## Mit den Navigationstasten der Braillezeile navigieren

Neovim Access Link verwendet die normalen Navigationsbefehle des in NVDA
gewählten Brailletreibers. Die Tasten heißen und liegen je nach Braillezeile
unterschiedlich. Bei einer Papenmeier BRAILLEX wird beispielsweise die
Navigationsleiste nach links, rechts, oben oder unten gedrückt.

Links und rechts verschieben das sichtbare Fenster innerhalb einer langen
Zeile. Eine 80-modulige Braillezeile zeigt so nacheinander die weiteren Teile
einer Zeile. Der Neovim-Cursor wird dabei nicht versetzt. Für oben und unten
stehen zwei getrennte Navigationsmodi zur Verfügung.

NVDA wechselt nach seinem üblichen Brailleverhalten auch dann zur
vorherigen oder nächsten Zeile, wenn am Anfang beziehungsweise Ende einer
Zeile nochmals horizontal weitergeschaltet wird. Links über den Zeilenanfang
zeigt das Ende der vorherigen Zeile. Rechts über das Zeilenende zeigt den
Anfang der nächsten Zeile. Kehrt man so zu einer langen Zeile zurück, beginnt
die Anzeige deshalb am Zeilenanfang und nicht beim zuvor weitergeschalteten
Ausschnitt. Oben und unten behalten dagegen nach Möglichkeit die bisherige
Spalte bei.

### Braille-Cursormodus: Cursor beim Lesen mitnehmen

Der Braille-Cursormodus ist nach dem Verbinden aktiv:

- Oben und unten setzen den Neovim-Cursor in die vorherige oder nächste
  Zeile.
- Neovim Access Link versucht, dieselbe sichtbare Spalte beizubehalten.
- Ist eine Zwischenzeile kürzer, steht der Cursor dort am erreichbaren
  Zeilenende. Auf einer späteren längeren Zeile kehrt er zur ursprünglichen
  Spalte zurück.
- Am Anfang oder Ende des Puffers bleibt der Cursor in der vorhandenen Zeile.

Dieser Modus eignet sich zum Bearbeiten: Nach Oben oder Unten steht der echte
Neovim-Cursor bereits in der gelesenen Zeile. Text kann dort sofort eingefügt
oder mit einem Normalmodus-Befehl bearbeitet werden.

### Braille-Explorationsmodus: Zeilen lesen, Cursor stehen lassen

Im Braille-Explorationsmodus lassen sich andere Zeilen lesen, ohne den
Neovim-Cursor zu verschieben:

- Oben und unten zeigen die vorherige oder nächste Pufferzeile.
- Die möglichst gleiche sichtbare Spalte wird beibehalten.
- Eine Routingtaste setzt den echten Neovim-Cursor auf die gewählte Position
  der gerade angezeigten Zeile. Der Braille-Explorationsmodus bleibt dabei
  eingeschaltet.
- Bewegungen des echten Cursors und Moduswechsel verändern die virtuelle
  Brailleposition nicht. Texteingaben und Bearbeitungen auf einer anderen
  Zeile lassen die explorierte Zeile und Lesespalte ebenfalls stehen.
- Befindet sich der echte Cursor dagegen auf der gerade explorierten Zeile,
  werden Änderungen dieser Zeile sofort auf der Braillezeile aktualisiert.
  Das gilt beispielsweise nach Routing und anschließendem Ersetzen mit `r`,
  beim Einfügen sowie beim Löschen. Sichtbar ändert sich dabei nur der gerade
  angezeigte Ausschnitt, wenn die Bearbeitung ihn betrifft. Der echte Cursor
  und Änderungen außerhalb des Ausschnitts holen die Brailleausgabe nicht zu
  sich. Die virtuelle Zeilenposition und der gewählte Ausschnitt bleiben
  erhalten.
- Routing verwendet niemals einen älteren, nicht mehr belegten Bufferstand.
  Hat sich der Buffer geändert, während der echte Cursor auf einer anderen
  Zeile stand, bleibt die explorierte Anzeige zum ungestörten Lesen stehen,
  aber ihre Routingtasten werden vorübergehend nicht ausgeführt. Mit den
  Navigationstasten eine andere Zeile anzeigen und zur gewünschten Zeile
  zurückkehren; danach stammt sie wieder aus dem aktuellen Bufferstand und
  kann geroutet werden.
- Nur die Navigationstasten der Braillezeile bewegen die virtuelle
  Leseposition.
- Die virtuelle Leseposition wird nicht als Braillecursor dargestellt. Der
  echte Neovim-Cursor erscheint nur, wenn er sich tatsächlich in der gerade
  explorierten Zeile befindet und deren angezeigter Text noch übereinstimmt.
  Dadurch gibt es nie einen zweiten, scheinbaren Cursor.
- Ein Buffer-, Neovim-Fenster- oder Neovim-Tabwechsel innerhalb derselben
  Sitzung verwirft die bisherige virtuelle Position. Der Wechsel zu einer
  anderen Windows-Terminal-Session oder Anwendung behält dagegen virtuelle
  Zeile, Lesespalte und horizontalen Ausschnitt in der zugehörigen
  Neovim-Session. Bei der Rückkehr wird genau diese Ansicht
  wiederhergestellt; die andere Session besitzt ihre eigene. Die konfigurierte
  Fokusansage bleibt dabei hörbar, erzeugt aber keine vorübergehende
  Braillemeldung, die diesen Ausschnitt bis zum Nachrichten-Timeout verdecken
  würde. Erst eine Trennung setzt die betroffene Session in den
  Braille-Cursormodus zurück.

Für den Umschalter ist absichtlich keine Tastenkombination vorgegeben. Unter
`NVDA-Menü → Optionen → Eingaben` kann in der Kategorie
`Neovim Access Link` dem Befehl „Braillezeilen-Navigation zwischen
Braille-Cursormodus und Braille-Explorationsmodus umschalten“ eine Taste
zugewiesen werden. NVDA meldet beim Umschalten „Braille-Explorationsmodus“
oder „Braille-Cursormodus“.

Dieser Modus eignet sich beispielsweise, um mehrere Zeilen oberhalb und
unterhalb der aktuellen Einfügeposition zu lesen, ohne beim anschließenden
Weiterschreiben die Stelle suchen zu müssen. Soll eine erkundete Stelle doch
zum Bearbeitungsort werden, genügt ihre Routingtaste.

Beide Braille-Navigationsmodi sind in den strukturierten Editormodi verfügbar.
In der aktiven Neovim-Befehlszeile und im direkten Eingabemodus eines
eingebetteten Terminals sind sie nicht verfügbar. Beim Trennen wird nur der
Modus der betroffenen Sitzung auf den Braille-Cursormodus zurückgesetzt. Ein
Wechsel zu einem anderen Windows-Terminal-Tab oder -Pane übernimmt niemals
Modus oder Ausschnitt der zuvor fokussierten Sitzung.

### Sprachexplorationsmodus: eine Sprachfunktion mit optionaler Brailleanzeige

Der [Sprachexplorationsmodus](speech-exploration.md) ist kein Braillemodus. Er
liest mit gehaltener NVDA-Taste Zeichen, Wörter oder Zeilen, ohne den echten
Neovim-Cursor zu bewegen. Er funktioniert vollständig ohne Braillezeile.

Eine Braillezeile kann diese Sprachfunktion optional unterstützen:
Standardmäßig zeigt sie die virtuelle Sprachposition vorübergehend mit an und
kehrt beim Loslassen der NVDA-Taste zum echten Cursor zurück. Unter
`NVDA-Menü → Optionen → Einstellungen → Neovim Access Link → Braille →
Sprachexplorationsmodus` lässt sich „Braillezeile folgt der Position des
Sprachexplorationsmodus“ ausschalten.

Der Braille-Explorationsmodus ist davon unabhängig. Er wird mit den
Navigationstasten der Braillezeile bedient, bleibt nach dem Umschalten aktiv
und besitzt eine eigene virtuelle Zeilenposition. Eine einzelne Routingtaste
kann in beiden Modi die gerade angezeigte Textposition als echten Cursor
übernehmen. Doppelte und dreifache Routing-Bearbeitungsaktionen sind während
des schreibgeschützten Sprachexplorationsmodus ausgeschaltet.

### Welche Navigation eignet sich wofür?

| Ziel | Geeignete Funktion |
| --- | --- |
| Beim Lesen mit Oben und Unten zugleich den echten Cursor versetzen | Braille-Cursormodus |
| Mehrere Zeilen auf der Braillezeile lesen, ohne den Cursor zu versetzen | Braille-Explorationsmodus |
| Kurz ein Zeichen, Wort oder eine Zeile mit Sprache erkunden und automatisch zurückkehren | Sprachexplorationsmodus mit gehaltener NVDA-Taste |
| An einer erkundeten Stelle weiterarbeiten | Einmal die Routingtaste an dieser Stelle drücken |

Braille-Explorationsmodus und Sprachexplorationsmodus besitzen getrennte virtuelle
Positionen. Das Umschalten der Braille-Navigation verändert den
Sprachexplorationsmodus nicht. Ist der Braille-Explorationsmodus aktiv, hat
seine Zeilenposition Vorrang vor der optionalen Brailleanzeige des
Sprachexplorationsmodus.

## Visual-Auswahl

Bei einer Visual-Auswahl markiert NVDA den ausgewählten Teil der aktuellen
Zeile auf Braille. Bei einer mehrzeiligen Auswahl ändert sich die Markierung
mit der angezeigten Zeile. NVDA verwendet dafür die Punkte 7 und 8. Ob
Auswahlen angezeigt werden und welche Form der Braillecursor besitzt, wird in
NVDAs Brailleeinstellungen festgelegt.

## Rechtschreibvorschläge

Neovims eingebaute Rechtschreibvorschläge lassen sich folgendermaßen bedienen:

1. Den Cursor auf ein falsch geschriebenes Wort setzen und `z=` drücken.
2. Die NVDA-Taste gedrückt halten.
3. Mit `j` und `k` durch die Vorschläge gehen.
4. Mit `NVDA+Eingabe` den ausgewählten Vorschlag übernehmen.

Sprache und Braille zeigen dabei nur den Vorschlag ohne seine Nummer. Wird die
NVDA-Taste losgelassen, kehrt die Braillezeile zur Editorzeile zurück. Neovims
Vorschlagsliste bleibt geöffnet und kann mit `Esc` geschlossen werden.

Unter `NVDA-Menü → Optionen → Einstellungen → Neovim Access Link → Braille`
kann festgelegt werden, ab welchem Braillemodul der
Vorschlag erscheinen soll. Die Zählung beginnt bei 1. Passt die gewählte
Position oder der Vorschlag nicht auf die Braillezeile, wird die Anzeige
automatisch an den verfügbaren Platz angepasst. Die normale Editorzeile wird
durch diese Einstellung nicht verschoben.

Die Verschiebung verbessert besonders dann die Ergonomie, wenn die
Feststelltaste als NVDA-Taste verwendet wird und die linke Hand während der
Auswahl darauf liegen bleibt. Hand und linker Arm können dabei den linken
Teil der Braillezeile verdecken, während die Vorschläge mit der rechten Hand
gelesen werden. Beginnt die Vorschlagsausgabe weiter rechts, bleibt sie für
die rechte Hand frei erreichbar und lässt sich wesentlich bequemer lesen.

## Eingebettetes Terminal

Im direkten Eingabemodus eines mit `:terminal` geöffneten Buffers verwendet
NVDA seine normale Windows-Terminal-Anzeige. Nach dem Wechsel in den
Terminal-Normalmodus zeigt Neovim Access Link wieder die strukturierte
Neovim-Zeile.

## Wenn die Anzeige nicht stimmt

Wenn nach dem Verbinden weiterhin „Windows PowerShell“ statt der Editorzeile
erscheint, keine Cursorzelle sichtbar ist oder eine Routingtaste an einer
Textposition nicht reagiert:

1. Prüfen, ob das richtige Windows-Terminal-Tab oder -Pane fokussiert ist.
2. Prüfen, ob die Neovim-Sitzung mit F12 verbunden wurde.
3. NVDA auf „Cursor verfolgen“ stellen.
4. Einen redigierten Diagnosebericht unmittelbar nach dem Fehler kopieren.

Weitere Schritte beschreibt das Kapitel
[Fehlerdiagnose und Diagnosebericht](troubleshooting.md).
