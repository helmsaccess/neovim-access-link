# Aktiver Plan

Stand: 2026-07-16

Kernarchitektur, Protokoll v2, SSH-stdio, lokale Windows-CLI, explizite
F12-Claim-Handshake und -Zuordnung, parallele Sitzungen sowie rootlose Komponenteninstallation und
-entfernung sind
implementiert. Der verifizierte Funktionsstand steht in
[Aktueller Status](current-status.md); abgeschlossene Änderungen stehen im
[Changelog](changelog.md).

## Aktuell: Abschottung pro Windows-Terminal-Control

Der Branch `feature/addon-isolation` begrenzt jeden F12-Zuordnungsversuch auf
das exakt fokussierte `TermControl`. Der physische Tastendruck ist selbst die
einmalige Autorisierung; ohne frischen Neovim-Claim bleibt der Versuch still.
Der Aktivierungsbefehl bleibt überall der globale Ein-/Ausschalter.
Netzwerkaktivität darf keine Umbindung mehr anbieten.

Bereits gebundene Tabs, Split-Panes und Fenster bleiben parallel nutzbar. Beim
Fokuswechsel bleibt native Ausgabe zunächst offen; erst eine zur fokussierten
Identität, Instanz und Request-ID passende frische Kontextantwort reaktiviert
die strukturierte Ausgabe. Automatisierte Mehrcontrol- und Mehrfenstertests
sind Bestandteil der Änderung. Der praktische Test unter NVDA/WT mit lokaler
und entfernter Sitzung in mehreren Tabs sowie horizontalen und vertikalen
Split-Panes ist bestanden. Getrennte WT-Fenster, tmux und die vollständige
Negativmatrix ungebundener Shell-Panes stehen noch aus.

## Beta-Abschluss

Vor dem Beta-Abschluss ist die neue Fokus-Kontextausgabe praktisch mit lokaler
und entfernter Verbindung, mehreren gebundenen und ungebundenen WT-Tabs und
-Panes sowie schnellen Fokuswechseln zu prüfen. Insbesondere dürfen verspätete
Antworten und reine Shell-Tabs keine Ausgabe oder Unterdrückung auslösen.

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
