# Aktiver Plan

Stand: 2026-07-16

Kernarchitektur, Protokoll v2, SSH-stdio, lokale Windows-CLI, explizite
F12-Claim-Handshake und -Zuordnung, parallele Sitzungen sowie rootlose Komponenteninstallation und
-entfernung sind
implementiert. Der verifizierte Funktionsstand steht in
[Aktueller Status](current-status.md); abgeschlossene Änderungen stehen im
[Changelog](changelog.md).

## Aktuell: einstellbare Ausgabe beim Sitzungsfokus

Der Branch `feature/focus-context-settings` macht die Präsentation einer
erfolgreich bestätigten Fokus-Kontextantwort einstellbar. Im Einstellungsdialog
enthält die Registerkarte „General“ eine profilfähige Auswahl mit drei
Werten:

1. keine Fokusansage;
2. aktuelle Zeile;
3. aktueller Datei- oder Spezialkontext, Modus und Verbindungsname wie bisher.

Der dritte Wert bleibt Standard, damit vorhandene Installationen ihr Verhalten
behalten. Die Auswahl steuert nur die Fokusansage und deren vorübergehende
Braillemeldung. Die strukturierte Braillezeile, Fokuskorrelation,
Authentifizierung, Control-Bindung und fail-open Unterdrückung bleiben davon
unabhängig. Auch bei „keine Fokusansage“ muss das Add-on deshalb weiterhin den
korrelierten `focusContext` anfordern und prüfen.

Bei jeder akzeptierten Fokus-Kontextantwort wird zusätzlich der zum aktuellen
Insert- oder Normalmodus gehörende Modusklang angeboten. Das gilt für alle drei
Auswahlwerte, bleibt aber wie andere Modusklänge durch die vorhandenen globalen
und aktionsbezogenen Klangoptionen begrenzt. Die Fokusauswahl darf weder
Moduswechselansagen noch Modusklänge umkonfigurieren.

### Umsetzungsschritte

1. Einen validierten nativen NVDA-Konfigurationswert mit kompatiblem Standard
   ergänzen und in Dialog, Speichern, Laden, Normalisierung sowie
   Profilwechsel integrieren. Bei einer Schemaerhöhung darf eine bereits
   migrierte native Konfiguration niemals erneut aus der alten JSON-Sicherung
   überschrieben werden.
2. Im NVDA-unabhängigen Speech-Planner die drei Präsentationsvarianten
   modellieren. „Aktuelle Zeile“ verwendet den strukturierten `lineText`, meldet
   eine leere Zeile eindeutig und übernimmt die vorhandene
   Einrückungsbehandlung. Der bisherige Datei-/Spezialkontext bleibt unverändert
   verfügbar.
3. Die Wiedergabe des Insert-/Normalmodusklangs für bestätigten Sitzungsfokus
   von der Sprachauswahl trennen. Pro akzeptierter Fokusantwort darf höchstens
   ein Modusklang entstehen; verspätete, ungebundene oder nicht authentifizierte
   Antworten bleiben vollständig wirkungslos.
4. Regressionstests für Standardkompatibilität, alle Auswahlwerte, leere und
   Unicode-Zeilen, lokale und entfernte Verbindungsnamen, NVDA-Profile,
   ungültige Konfiguration, Altdatei-Migration, Braille sowie getrennte
   Sprach-/Klangfreigaben ergänzen.
5. Einstellungen, Architektur, Zugänglichkeitsmatrix, Testanleitung,
   aktuellen Status und Changelog gemeinsam aktualisieren. Danach einen
   praktischen NVDA/WT-Test mit lokaler und SSH-Sitzung, gebundenen und
   ungebundenen Tabs beziehungsweise Panes sowie schnellem Fokuswechsel
   durchführen.

Alle Schritte sind umgesetzt. Der praktische NVDA-/WT-Test bestätigte alle drei
Auswahlwerte einschließlich der unabhängigen Modusklänge lokal und über SSH
ohne Probleme.

## Beta-Abschluss

Die konfigurierbare Fokus-Kontextausgabe ist lokal und über SSH praktisch
bestätigt. Die weitergehende Negativmatrix mehrerer ungebundener WT-Tabs und
-Panes sowie schneller Fokuswechsel bleibt Teil des Beta-Abschlusses.

1. Deutsche Anwender- und Entwicklungsdokumentation auf Korrektheit,
   Verständlichkeit und einheitliche Begriffe prüfen.
2. Vollständige Python-, Lua-, Paket- und Dokumentationsprüfungen ausführen.
3. Manuelle Abnahme von lokaler und entfernter Verbindung, mehreren Tabs und
   Fenstern, tmux, Deaktivierung und Fail-open dokumentieren.
4. Bekannte Grenzen und Kompatibilitätsangaben mit den Ergebnissen abgleichen.

## Danach

1. Reale Braillezeilen verschiedener Hersteller prüfen.
2. Langzeitbetrieb, große Dateien und wiederholte SSH-Abbrüche testen.
3. Deutsche und englische Anwender- und Entwicklungsdokumentation gemeinsam
   pflegen und prüfen.
4. Weitere Frontends oder Neovim-Oberflächen nur über getrennte, getestete
   Adapter ergänzen.
