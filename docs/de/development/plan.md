# Aktiver Plan

Stand: 2026-07-14

Kernarchitektur, Protokoll v2, SSH-stdio, lokale Windows-CLI, explizite
F12-Zuordnung, parallele Sitzungen und rootlose Komponenteninstallation sind
implementiert. Der verifizierte Funktionsstand steht in
[Aktueller Status](current-status.md); abgeschlossene Änderungen stehen im
[Changelog](changelog.md).

## Beta-Abschluss

1. Deutsche Anwender- und Entwicklungsdokumentation auf Korrektheit,
   Verständlichkeit und einheitliche Begriffe prüfen.
2. Vollständige Python-, Lua-, Paket- und Dokumentationsprüfungen ausführen.
3. Manuelle Abnahme von lokaler und entfernter Verbindung, mehreren Tabs und
   Fenstern, tmux, Deaktivierung und Fail-open dokumentieren.
4. Bekannte Grenzen und Kompatibilitätsangaben mit den Ergebnissen abgleichen.

## Danach

1. Reale Braillezeilen verschiedener Hersteller prüfen.
2. Langzeitbetrieb, große Dateien und wiederholte SSH-Abbrüche testen.
3. Englische Anwender- und Entwicklungsdokumentation erstellen und prüfen.
4. Weitere Frontends oder Neovim-Oberflächen nur über getrennte, getestete
   Adapter ergänzen.
