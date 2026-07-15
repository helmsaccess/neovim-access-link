# Changelog

Dieses Changelog beschreibt auslieferbare Beta-Stände. Die zahlreichen
experimentellen Vor-Beta-Builds werden nicht einzeln fortgeführt; Git enthält
deren vollständigen Verlauf.

## 0.89.5 (Beta-Testbuild)

- Unter `NVDA-Menü → Werkzeuge → Neovim Access Link: Remove components...`
  können die eingebetteten Komponenten auf dem lokalen Windows-Rechner und
  auf ausdrücklich ausgewählten gespeicherten Linux-Verbindungen vollständig
  entfernt werden.
- Der zugängliche Mehrfachauswahldialog, die Hintergrundverarbeitung und die
  kompakte Ergebnisübersicht entsprechen dem Installationsablauf. Gespeicherte
  Verbindungen, Neovim- und SSH-Konfiguration sowie fremde Plugins bleiben
  erhalten.

## 0.89.4 (Beta-Testbuild)

- Quick Guide, Handbuch und Entwicklerdokumentation liegen vollständig auf
  Deutsch und Englisch als Markdown-Quellen und getrennte HTML-Ausgaben vor.
- Das Projekt wird unter `GPL-2.0-only` veröffentlicht. Der unveränderte
  Lizenztext wird in beide installierbaren Pakete aufgenommen; Beitragsregeln
  und die zusätzliche Relizenzierungserlaubnis sind getrennt dokumentiert.
- Standarddateien für eine GitHub-Veröffentlichung wurden ergänzt und private
  Produktanforderungen aus dem öffentlichen Quellbaum entfernt.

## 0.89.3 (Beta-Testbuild)

- Quick Guide, Anwenderhandbuch und Entwicklerdokumentation werden als drei
  eigenständige HTML-Dateien mit eigenem Inhaltsverzeichnis und geprüften
  internen Links gebaut.
- Die lokale F12-Nachsuche wartet begrenzt auf verzögert sichtbare atomare
  Registry-Aktualisierungen. Automatische und manuelle lokale Zuordnung wurden
  mit dem installierten Beta-Build praktisch bestätigt.
- Diagnoseberichte unterscheiden lokale und entfernte Sitzungszahlen,
  Nachsuche und Auflösungsabschluss, ohne Editorinhalt offenzulegen.

## 0.89.2 (Beta-Testbuild)

- Ein durch F12 eindeutig bestätigtes lokales Windows-Neovim wird unmittelbar
  ausgewertet und wartet nicht mehr auf langsamere SSH-Sitzungsprüfungen.

## 0.89.1 (erste Beta-Vorbereitung)

- Der sichtbare Produktname lautet „Neovim Access Link“, der Autor ist Emanuel
  Helms. Produktidentität, Version, Buildnummer und NVDA-Kompatibilitätsdaten
  werden ausschließlich in `buildVars.py` gepflegt.
- Manifest, Laufzeitdiagnose und Paketnamen werden aus dieser zentralen Quelle
  abgeleitet. Der interne NVDA-Identifier `nvimNvdaAccess` bleibt zugunsten
  kompatibler Installationen und NVDA-Profile stabil.
- Die Dokumentation wurde nach Sprache und Zielgruppe gegliedert. Bekannte
  Ausnahmen von öffentlichen NVDA-APIs sind in ADR-0002 begründet.

## Zusammenfassung der Vor-Beta-Entwicklung

- Das Produkt wechselte auf Protokoll v2 mit SSH-stdio für Linux und einem
  strikt an `127.0.0.1` gebundenen lokalen Neovim-RPC-Transport für Windows.
  Alte allgemeine TCP-, Tunnel-, Token- und v1-Pfade wurden entfernt.
- Das Add-on installiert Bridge, Protokollcode, MessagePack, Plugin und
  Zuordnungskonfiguration rootlos aus dem eingebetteten Paket. Mehrere Ziele
  werden im Hintergrund aktualisiert und zugänglich zusammengefasst.
- Verbindungsprofile und Laufzeitinstanzen wurden getrennt. Mehrere lokale und
  entfernte Sitzungen, Konten, Tabs, Fenster und tmux-Kontexte können parallel
  über eine ausdrückliche F12-Markierung gebunden werden; ein Standardziel ist
  nicht erforderlich.
- Windows-Terminal-spezifische Ereignisse, Gesten und Unterdrückung wurden in
  das NVDA-AppModule verschoben. Fremde Anwendungen bleiben unberührt;
  Deaktivierung, Fehler und Verbindungsverlust öffnen die normale
  Terminalausgabe wieder.
- Strukturierte Sprache und Braille wurden um Modi, Navigation, Bearbeitung,
  Auswahl, Completion, Menüs, Suche, Diagnostics, Folds, Marks, Register,
  Makros und verbreitete Dateimanager erweitert.
- Einstellungen verwenden NVDAs reguläre Konfigurationsprofile. Komponenten-
  und Verbindungsdialoge laufen zugänglich und blockieren NVDAs Hauptthread
  nicht.
