# Gebündelte Abhängigkeiten

## msgpack-python 1.1.2

- Zweck: MessagePack-Decoding des versionierten Anwendungsprotokolls
- Lizenz: Apache-2.0
- Quelle: <https://msgpack.org/> / <https://github.com/msgpack/msgpack-python>
- Wartungsstand: Version 1.1.2 mit Binärpaketen für Python 3.14; gegenüber
  1.1.1 unveränderter Quellcode
- Paketinhalt: ausschließlich der portable Python-Fallback und Lizenztext;
  keine Linux-C-Erweiterung
- Laufzeit: Socket-Thread, nicht NVDA-Hauptthread
- Installation: vollständig im `.nvda-addon`; keine globale Python-Installation
  unter Windows erforderlich

Der Build bricht ab, wenn nicht exakt Version 1.1.2 vorliegt oder native
Bibliotheken beziehungsweise Bytecode in das Archiv geraten würden.
