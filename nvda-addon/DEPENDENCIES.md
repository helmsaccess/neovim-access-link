# Gebündelte Abhängigkeiten

## msgpack-python 1.1.1

- Zweck: MessagePack-Decoding des versionierten Anwendungsprotokolls
- Lizenz: Apache-2.0
- Quelle: <https://msgpack.org/> / Rocky-EPEL-RPM `python3-msgpack-1.1.1`
- Wartungsstand: Version 1.1.1, auf dem Zielsystem paketiert
- Paketinhalt: ausschließlich der portable Python-Fallback und Lizenztext;
  keine Linux-C-Erweiterung
- Laufzeit: Socket-Thread, nicht NVDA-Hauptthread
- Installation: vollständig im `.nvda-addon`; keine globale Python-Installation
  unter Windows erforderlich

Der Build bricht ab, wenn nicht exakt Version 1.1.1 vorliegt oder native
Bibliotheken beziehungsweise Bytecode in das Archiv geraten würden.
