# Abhängigkeiten

## Gebündelte Laufzeitabhängigkeit

MessagePack Python 1.1.1 wird unter der Apache-Lizenz 2.0 für die Kodierung und
Dekodierung des Protokolls gebündelt. Quellcode und Lizenz werden in das Add-on
und das Linux-Komponentenpaket kopiert. Auf dem Zielsystem ist deshalb kein
separates MessagePack-Paket erforderlich.

Der Add-on-Build akzeptiert genau Version 1.1.1 und übernimmt nur die portablen
Python-Dateien und den Lizenztext. Native Bibliotheken und Bytecode werden
nicht paketiert.

## Buildabhängigkeiten

Python 3, ConfigObj für die NVDA-kompatible Manifestprüfung und Pandoc für die
eigenständige HTML-Dokumentation werden nur beim Build verwendet. Sie sind
keine Laufzeitabhängigkeiten des installierten Add-ons oder Plugins.

Neue Abhängigkeiten benötigen einen dokumentierten Zweck sowie eine Prüfung
von Lizenz, Wartung, Größe, Latenz und Paketierung.

## Maßgebliche Quellen und Prüfung

`tools/build_nvda_addon.py` und `tools/build_user_package.py` legen die
akzeptierte MessagePack-Version fest und besitzen Auswahl, Lizenzprüfung und
Paketziele. Die gepinnten Build- und Testwerkzeuge stehen in
`tools/requirements-ci.txt`, `tools/requirements-linter-ci.txt` und dem
Repository-Testworkflow. Pakettests untersuchen die erzeugten Archive; diese
Seite wiederholt nur die für Entwickler relevante Rolle der Abhängigkeiten.
