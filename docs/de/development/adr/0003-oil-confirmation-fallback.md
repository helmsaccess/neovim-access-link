# ADR-0003: Eng begrenzter Fallback für Oil-Bestätigungen

## Status

Angenommen für den Entwicklungsstand nach 0.93.0. Vor jeder Freigabe gegen die
unterstützten Oil-Versionen erneut zu prüfen.

## Kontext

Oil veröffentlicht Abschlussereignisse für Dateiaktionen, aber vor dem
Ausführen keine öffentliche semantische Meldung für seinen eigenen
Bestätigungs-Float. Der Float enthält vollständige Pfade. Eine rohe Ausgabe
würde unnötige Daten sprechen und den Dialog nicht zuverlässig als
Bestätigung kennzeichnen.

## Entscheidung

Das Neovim-Plugin darf ausschließlich einen echten Float mit exakt
`filetype=oil_preview` als Oil-Bestätigung erkennen. Es liest ereignisgetrieben
höchstens 200 bereits gerenderte Zeilen, akzeptiert nur die festen Aktionen
`CHANGE`, `COPY`, `CREATE`, `DELETE`, `MOVE`, `PURGE`, `RESTORE` und `TRASH`
nach optionaler Einrückung und veröffentlicht lediglich Aktion, Anzahl sowie
„Y yes, N no“ als `promptOpened`. Dateinamen, Pfade und rohe Zeile werden nicht
übertragen. Die direkt getippte sichtbare Wahl `y` oder `n` wird nur beobachtet,
nicht abgefangen. Beim Verlassen oder Schließen folgt ereignisgesteuert
`promptClosed` mit `accepted=true` beziehungsweise `accepted=false`; unbekannte
oder historische Alternativtasten erzeugen keine erfundene Auswahl.

Unbekannte Darstellung, anderer Dateityp, normales Fenster oder Parserfehler
fallen offen auf das allgemeine Verhalten zurück. Es gibt keine Timerabfrage,
kein Dateisystemlesen und keinen allgemeinen Popup-Parser. Öffentliche
Oil-Abschlussereignisse bleiben für das Aktionsergebnis maßgeblich.

## Folgen

- Vorteil: Die Bestätigung ist vor der Aktion verständlich und pfadfrei.
- Risiko: `oil_preview` und das gerenderte Aktionsformat sind private
  Plugin-Details und können sich ändern.
- Absicherung: Vor einer Freigabe muss ein isolierter echter Oil-Test Öffnen,
  Umbenennen, Duplizieren, Löschen, Y/N, genau ein Öffnen/Schließen, fehlende
  Rohereignisse und die erwartete Änderung beziehungsweise Nichtänderung der
  Testdateien belegen.
- Ablöseplan: Sobald Oil ein geeignetes öffentliches Vor-Aktionsereignis
  anbietet, wird dieser Fallback entfernt.
