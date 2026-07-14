# Einstieg für Entwicklung und Tests

Dieses Dokument beschreibt die Voraussetzungen für Änderungen am Quellcode.
Die Bedienung des fertigen Add-ons steht im
[Anwenderhandbuch](../manual/README.md).

## Was im Repository entwickelt wird

Neovim Access Link besteht aus vier getrennten Teilen:

1. Das Lua-Plugin gewinnt strukturierte Zustände und Ereignisse aus Neovim.
2. Die Python-Bridge verbindet entfernte Linux-Neovims mit SSH-stdin/stdout.
3. Der gemeinsame Python-Core validiert Protokoll, Sitzungen und Zustände.
4. Das NVDA-Add-on ordnet Windows-Terminal-Tabs zu und erzeugt Sprache,
   Braille und Sounds.

Die [Architektur](architecture.md) erklärt die Grenzen und Datenwege im Detail.

## Laufzeitvoraussetzungen

Für das Windows-System werden Windows 11 mit NVDA 2026.1.x, Windows Terminal
und entweder lokales Neovim oder der Windows-OpenSSH-Client benötigt.

Ein entferntes Linux-Ziel benötigt Neovim 0.10.1 oder einen nachweislich
kompatiblen neueren Stand, `python3`, einen erreichbaren SSH-Dienst und ein
beschreibbares Benutzerverzeichnis unter `~/.local`. Die Bridge bringt
Protokollcode und MessagePack selbst mit. Auf dem Ziel sind daher weder
`python3-msgpack`, `pynvim`, Root-Rechte noch ein Internetdownload erforderlich.

## Bestätigte Referenzumgebung

Der aktuelle Stand wurde praktisch mit Windows 11 25H2, NVDA 2026.1.1,
Windows Terminal 1.24.x und `OpenSSH_for_Windows_9.5p2` mit `LibreSSL 3.8.2`
geprüft. Als entferntes Ziel diente Rocky Linux 10.2 mit Neovim 0.10.1 und
Python 3.12.13. Lokale Tests verwendeten die Windows-CLI von Neovim 0.10.1.

Diese Angaben beschreiben die bestätigte Umgebung, nicht automatisch harte
Mindestversionen aller Hilfsprogramme. Verbindliche Zusagen und bekannte
Grenzen stehen in der [Kompatibilitätsübersicht](compatibility.md).

## Entwicklungswerkzeuge und erste Prüfung

Für Python-Tests und Paketbau wird Python 3 mit MessagePack 1.1.1 benötigt.
Der HTML-Build verwendet Pandoc. Lua-Integrationstests laufen mit einem echten
`nvim --headless`.

```bash
export PYTHONPATH=protocol/python:bridge/python:nvda-addon/core
python3 -m unittest discover -s nvda-addon/tests
python3 -m unittest discover -s protocol/python/tests
python3 -m unittest discover -s bridge/python/tests
tools/test_neovim_plugin.sh
python3 tools/build_nvda_addon.py
tools/build_documentation.sh
git diff --check
```

Welche Prüfungen für eine Änderung erforderlich sind, beschreibt die
[Teststrategie](testing.md). Neue Mitwirkende lesen anschließend den
[aktuellen Status](current-status.md), die
[Repository-Struktur](repository-layout.md) und die [Architektur](architecture.md).
