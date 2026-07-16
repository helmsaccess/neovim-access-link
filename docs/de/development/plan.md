# Aktiver Plan

Stand: 2026-07-16

Kernarchitektur, Protokoll v2, SSH-stdio, lokale Windows-CLI, explizite
F12-Claim-Handshake und -Zuordnung, parallele Sitzungen sowie rootlose Komponenteninstallation und
-entfernung sind
implementiert. Der verifizierte Funktionsstand steht in
[Aktueller Status](current-status.md); abgeschlossene Änderungen stehen im
[Changelog](changelog.md).

## Aktuell: explizites Copy/Paste

Der Branch `feature/copy-paste` ergänzt vier in NVDAs Eingabedialog frei
belegbare Befehle ohne Standardgesten: Visual-Auswahl kopieren, Register 0
kopieren, Windows-Zwischenablagentext einfügen oder in Neovims unbenanntem
Register für normales `p` speichern. NVDAs öffentliche
Zwischenablage-API bleibt der einzige Windows-Zugriff; lokal und über SSH
werden nur feste, typisierte Neovim-Steuerungen übertragen.

Umgesetzt sind korrelierte Anfrage-/Ergebnisereignisse, eine 256-KiB-Grenze,
UTF-8-/NUL-Prüfung, unmittelbare Zustandsprüfung in Neovim, `nvim_paste` ohne
automatische Wiederholung, Ausschluss von Spezial-, Terminal-, Datei-Manager-,
Readonly- und nicht veränderbaren Buffern sowie Entfernung einmaliger
Copy-Texte aus allen Zustands-Caches und Diagnosen. Eine profilfähige
Copy/Paste-Erfolgsrückmeldung verwendet das bestehende
Aus/Sprache/Töne/Beides-Modell; Fehler bleiben hörbar. Offene Anfragen sind
begrenzt.

Nach dem Praxishinweis, dass die Produktkategorie außerhalb von Windows
Terminal im Tastenbefehldialog fehlte, werden die frei belegbaren Befehle als
globale unbelegte Skriptmetadaten angeboten. Die Ausführung bleibt durch eine
erneute exakte WT-`TermControl`-Prüfung abgeschottet; außerhalb davon wird die
Originalgeste unverändert weitergegeben. Automatisierte Regressionen sind
umgesetzt; der praktische `dev.4`-Test bestätigte Sichtbarkeit, Durchleitung
außerhalb WT und Ausführung im gebundenen Neovim-Control ohne Probleme.

Alle vier Befehle einschließlich Windows-Text → unbenanntes Paste-Register
wurden im bereitgestellten `dev.4`-Build praktisch ohne Probleme bestätigt.
Die Featureabnahme ist damit abgeschlossen; ein Merge bleibt eine getrennte
Benutzerentscheidung.

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
