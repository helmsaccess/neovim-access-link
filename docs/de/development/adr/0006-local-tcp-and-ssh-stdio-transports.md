# ADR-0006: Lokales TCP und SSH-Standardstreams als Transporte

## Status

Akzeptiert.

Datum: 2026-08-05.

Ersetzt den Transportteil von
[ADR-0001](0001-neovim-integration-point.md). Dessen Entscheidung für semantische Ereignisse
aus einem Lua-Plugin bleibt gültig.

## Kontext

Lokale Windows-Sitzungen und entfernte Linux-Sitzungen benötigen unterschiedliche sichere
Verbindungswege. Beide Wege müssen mehrere Windows-Terminal-Fenster, Tabs und Bereiche
eindeutig zuordnen, ohne NVDA durch blockierende Netzwerkzugriffe oder unbestätigte Sitzungen zu
beeinflussen. Feste Ports, ein allgemeiner Neovim-RPC-Zugang über SSH und von Benutzerprofilen
geerbte Portweiterleitungen vergrößern die Angriffs- und Fehlerfläche.

## Entscheidung

- Lokales Neovim unter Windows veröffentlicht einen dynamischen RPC-Endpunkt ausschließlich auf
  `127.0.0.1`. Die Sitzungsregistrierung enthält eine Nonce und Prozessdaten; NVDA validiert
  diese Angaben, bevor es sich direkt verbindet. Für diesen Weg läuft keine Python-Bridge.
- Entferntes Neovim veröffentlicht RPC über einen privaten Unix-Socket. NVDA startet die
  rootlose Python-Bridge mit `ssh.exe -T`; das eingeschränkte, gerahmte MessagePack-Protokoll
  läuft über Standard-Ein- und -Ausgabe. SSH authentifiziert Host und Benutzer. Es gibt keine
  Portweiterleitung, keinen festen Port und kein gemeinsames Anwendungstoken.
- `ClearAllForwardings=yes` verhindert, dass konfigurierte SSH-Portweiterleitungen für die
  Bridge-Verbindung übernommen werden.
- Endpunkte und entdeckte Sitzungen gelten bis zur vollständigen Validierung als nicht
  vertrauenswürdig. Fähigkeiten werden ausgehandelt und Steuerbefehle nur in der bestätigten,
  fokussierten Sitzung ausgeführt. Bei Fehlern bleibt die normale NVDA- und Terminalbehandlung
  aktiv.

## Folgen

- Zwei Transportadapter teilen sich Protokollvalidierung, kanonischen Zustand und
  Präsentationsplanung.
- Die entfernte Bridge bildet eine klar begrenzte Vertrauens- und Prozessgrenze; lokales Windows
  benötigt diesen zusätzlichen Prozess nicht.
- Lokales TCP bleibt auf Loopback und entferntes RPC auf einen privaten Unix-Socket begrenzt.
- Änderungen an Fähigkeiten oder Nachrichten benötigen abgestimmte Plugin-, Bridge- und
  Add-on-Tests. Sichere Tests, SSH-Tests und Socket-Tests bleiben getrennte Prüfphasen.
