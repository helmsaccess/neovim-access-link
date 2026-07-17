# Aktiver Plan

Stand: 2026-07-17

Kernarchitektur, Protokoll v2, SSH-stdio, lokale Windows-CLI, explizite
F12-Claim-Handshake und -Zuordnung, parallele Sitzungen sowie rootlose Komponenteninstallation und
-entfernung sind
implementiert. Der verifizierte Funktionsstand steht in
[Aktueller Status](current-status.md); abgeschlossene Änderungen stehen im
[Changelog](changelog.md).

## Aktuell: Terminal- und Dateimanager-Hardening

Der Branch `feature/terminal-file-manager-hardening` prüft und härtet die
Übergänge zwischen strukturiertem Editorzustand, direkter eingebetteter
Terminaleingabe, Terminal-Normalmodus, Neovim-Kommandozeile und semantischen
Dateimanager-Adaptern. Der erste Umsetzungsschritt ergänzt Terminal-
Modusklänge mit fail-open Gate-Reihenfolge und übernimmt nach Ex-Befehlen auch
gewöhnliche UI-Meldungen ohne bekannte `msg_show`-Klassifikation. Command-line-
Modus, Meldungsreihenfolge und Terminalübergänge erhalten Regressionstests.
Der zweite Schritt trennt `terminalNormal` kanonisch von Dateibuffer-Normal,
korrigiert das UTF-8-Command-line-Echo, ergänzt einen frei belegbaren,
korrelierten `stopinsert`-Befehl und meldet `TermClose` mit Exit-Status.
Der dritte Schritt ergänzt den Kommandozeilenton, eine eindeutige Rückkehr in
den Terminal-Normalmodus sowie strukturierte Hinweise für `:bd` bei laufendem
Job und wirkungslose Buffer-Navigation.
Der vierte Schritt verschiebt die Auswertung von UI-Protokollereignissen aus
Neovims Fast-Event-Kontext und verhindert damit `E5560`-Enter-Zustände unter
Neovim 0.12, ohne Polling einzuführen.
Der fünfte Schritt wendet die vorhandene profilfähige Fokusauswahl auch auf
ereignisgetriebene Bufferwechsel im selben Tab und Fenster an. `:bp` und `:bn`
geben damit wahlweise nichts, die Zielzeile oder Zielkontext, Modus und
Verbindungsname aus; Tab-/Fensteransagen und Modusklänge bleiben unabhängig.
Der sechste Schritt trennt automatische Cursor-/Änderungsereignisse des
Zielbuffers vom Ausgangszustand, damit weder ein einzelnes Zielzeichen die
Zeilenansage überschreibt noch Text bufferübergreifend als Änderung gilt.
Der siebte Schritt fasst bei erkannten Ex-Bufferbefehlen die kurzlebige
gesprochene Modusrückkehr mit der konfigurierten Zielausgabe zusammen. Der
Modusklang bleibt unabhängig; Ex-Befehle und gleich lautende Suchmuster werden
über den strukturierten Kommandozeilentyp unterschieden.
Der achte Schritt behandelt `:terminal` als strukturierten Buffereinstieg,
wartet bei Zeilenausgabe ohne Polling auf die erste echte Terminalzeile und
unterdrückt deren automatisches Folgezeichen. Der Wechsel mit `i` in direkte
Terminaleingabe gibt stattdessen die vollständige Cursorzeile aus; der
Modusklang und fail-open Passthrough bleiben getrennt.
Der neunte Schritt macht diese Zusammenfassung unabhängig von der Reihenfolge
zwischen Terminalkontext und abschließendem Modusereignis und verhindert, dass
Kommandozeilentext als Normalmodusbewegung in den neuen Terminalbuffer gelangt.
Der zehnte Schritt fasst bei Neovim-Fenster- und -Tabwechseln die gewählte
Kontextausgabe mit Zielposition, eindeutigem Datei-/Spezialkontext, Status,
Modus und Verbindung zusammen. Modussprache wird dabei nicht vorangestellt;
der unabhängige Modusklang und die beiden anderen Fokusvarianten bleiben
unverändert.
Der elfte Schritt unterscheidet bei F12 eine bloß noch gemerkte von einer
weiterhin authentifizierten Bindung. Nach dem Ende einer lokalen Sitzung kann
dasselbe WT-Control dadurch ausdrücklich auf eine frische SSH-Sitzung
umgebunden werden, ohne automatische Zuordnung oder Polling einzuführen.
Der zwölfte Schritt beginnt das Dateimanager-Hardening mit einer gemeinsamen
UTF-8-validierenden Bytebegrenzung. Lange Namen und Pfade werden nur an
Codepointgrenzen gekürzt; ungültige Adapterwerte gelangen nicht in den
Transport. Grenztests decken Zwei-, Drei- und Vierbytezeichen sowie ungültige Folgen
ab, ohne neue Abfragen oder Polling einzuführen.
Der dreizehnte Schritt ergänzt eine getrennte ereignisgetriebene
Dateimanager-Schicht. Öffentliche Oil-, nvim-tree-, Neo-tree- und
mini.files-Ereignisse lösen eine semantische Neuauswertung ausschließlich für
den aktiven Buffer beziehungsweise das aktive Fenster aus. Gleiche Zustände
werden verworfen, schnelle Renderfolgen innerhalb eines Schedulerzyklus
zusammengefasst. Markierung und Plugin-Clipboard bleiben getrennte Festwerte;
Änderungen am selben Eintrag werden ausdrücklich ausgegeben. Polling wird
nicht verwendet.
Der vierzehnte Schritt ergänzt typisierte Dateimanager-Aktionsresultate aus
öffentlichen Abschlussereignissen. Er überträgt nur Festwerte, Anzahl,
optionalen Basename und Typ, fasst synchrone Massenaktionen zusammen und
verwirft die Meldung nach einem Fokus-/Managerwechsel. mini.files, nvim-tree
und Neo-tree belegen Erfolge; Oil kann zusätzlich Abschlussfehler und dort
erkennbare Abbrüche belegen. Wo ein Plugin kein öffentliches Ergebnis liefert,
wird nichts aus Rendern oder Text geraten.
Der fünfzehnte Schritt verbreitert den bewusst begrenzten netrw-Fallback.
Header sowie schmale, lange, breite und Baumlisten besitzen getrennte
Regressionen für Leerzeichen, Tabs, Unicode, Symlinks und Rootzeilen. Moderne
Manager werden weiterhin ausschließlich über ihre APIs integriert.
Der sechzehnte Schritt wählt eingebaute Adapter direkt nach `filetype` und
begrenzt optionale Adapterlaufzeit. Wiederholte Fehler oder Aufrufe über 5 ms
führen bufferlokal zu einer kurzen fail-open-Abkühlung; Checkhealth stellt nur
feste Zähler bereit. Fristprüfung und Aufräumen sind ereignisgetrieben und
führen kein Polling ein.
Der siebzehnte Schritt trennt Manager-/Branchwurzel und fokussierte Ebene.
nvim-tree folgt öffentlichen Elternknoten, mini.files verwendet Branchanfang
und `depth_focus`; unzuverlässige Werte werden nicht aus Eintragspfaden
abgeleitet. Leerer Fokuskontext spricht nur den letzten Verzeichnisnamen.
Der achtzehnte Schritt ersetzt in Dateimanagerbuffern die dauerhafte rohe
Braillezeile durch Name, Typ und Zustand. Nur ein eindeutig in der echten
Zeile lokalisierter Namensbereich ist routbar; Statussegmente und mehrdeutige
Namen bleiben ohne erfundene Cursorabbildung.
Der neunzehnte Schritt härtet Standardprompts in echten TUI-Tests. Eingabe,
Abbruch und Auswahl laufen über `vim.ui.input/select`. Lua-`confirm()` wird
auf Neovim 0.10.1 und 0.12.3 semantisch angekündigt und nach Antwort sicher
geschlossen, auch wenn die externe UI kein `msg_clear` liefert.
Der zwanzigste Schritt deckt Oils eigenen Bestätigungs-Float als bewusst engen
Screen-Fallback ab, weil das Plugin dafür kein öffentliches Prompt-Ereignis
bereitstellt. Nur `oil_preview` in einem echten Float und feste Aktionsverben
werden akzeptiert; ausgegeben werden Aktion/Anzahl und Y/N, während Rohzeilen,
Namen und Pfade unterdrückt bleiben. Ein isolierter Test mit dem realen
Oil-Hauptzweig belegt Öffnen, Abbruch und unveränderte Testdatei.

Die praktische Windows-/NVDA-Abnahme bestätigte Command-line-Echo,
Terminal-Normal, Ausstiegsbefehl, Prozessende, die drei Ausgabevarianten bei
`:bp`/`:bn`, Fenster-/Tabwechsel und die erneute SSH-Zuordnung ohne weitere
Probleme. Als nächste Schritte bleiben die im Analysebericht priorisierten
weitere reale Dateimanager-Plugin-Prompts, Braillehardware, Pager-Sonderfälle sowie
die vollständige negative Windows-Terminal-Matrix.

## Abgeschlossen: explizites Copy/Paste

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
