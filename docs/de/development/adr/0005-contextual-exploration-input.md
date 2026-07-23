# ADR-0005: Kontextbezogene Eingabe für den Explorationsmodus

## Status

Umgesetzt. Automatisierte Bestätigung liegt vor; die praktische Abnahme steht
noch aus.

## Kontext

Der Explorationsmodus soll `NVDA+h/j/k/l` sowie
`Umschalt+NVDA+h/l` innerhalb einer bestätigten Neovim-Pane als rein lesende
Navigation verwenden. Derselbe Windows-Terminal-Prozess kann gleichzeitig
andere Tabs und Panes mit PowerShell, einer gewöhnlichen SSH-Shell oder einer
anderen Neovim-Sitzung enthalten. Außerhalb der exakt zugeordneten Neovim-
`TermControl` muss deshalb NVDAs unveränderte Eingabeauflösung gelten.

NVDA löst Tastaturgesten bereits über `scriptHandler.findScript` auf. Dabei
werden GlobalPlugins vor dem AppModule des Fokusobjekts und NVDAs eingebaute
`globalCommands` danach geprüft. Ein eigener Gesten-Dispatcher würde diese
Priorität duplizieren und Eingabehilfe sowie Benutzerzuweisungen umgehen.
Normale NVDA-Skripte erhalten allerdings kein späteres Key-up des Modifiers.

## Entscheidung

Das Windows-Terminal-AppModule besitzt Auswahl, Ausführung und Lebenszyklus der
sechs Explorationsaktionen und überschreibt `getScript` nur für deren
normalisierte Kennungen sowie eine eng begrenzte Autorepeat-Sperre.

- Bei einer lokal bestätigten, verbundenen und authentifizierten Zuordnung der
  exakt fokussierten Control gibt `getScript` das Explorationsskript zurück.
- Bei fehlender oder unsicherer Berechtigung delegiert es an die normale
  AppModule-Auflösung. NVDA setzt seine Suche selbst fort; das Add-on ruft weder
  `gesture.send()` auf noch bildet es den verdrängten NVDA-Befehl nach.
- Alle anderen Kennungen werden unverändert an
  `super().getScript(gesture)` delegiert.
- Das eingereihte Skript bestätigt Control, Instanz, Dienstgeneration,
  Fähigkeit und kanonischen Editorzustand erneut, bevor es eine feste
  Explorationsaktion anfordert.
- Scheitert diese zweite Prüfung nach bereits ausgewähltem Skript, wird die
  Kombination still verbraucht. Sie wird nicht als nacktes `h/j/k/l` an
  Neovim weitergereicht und kann daher den echten Cursor nicht bewegen.

Die Exploration registriert keinen Handler bei
`inputCore.decide_executeGesture`. Dessen bestehende Nutzung bleibt auf die in
ADR-0004 beschriebene F12-Zuordnung beschränkt.

Das AppModule registriert den öffentlichen
`inputCore.decide_handleRawKey`-Erweiterungspunkt symmetrisch, solange
mindestens eine seiner Instanzen besteht. Der Callback:

- gibt ausnahmslos `True` zurück und verändert damit NVDAs rohe
  Tastenverarbeitung nie;
- merkt Key-down und Key-up physischer NVDA-Tasten, damit ein bereits vor der
  Skriptausführung eingetroffenes Loslassen sicher erkennbar bleibt;
- erkennt bei aktiver Exploration das Key-up der physischen NVDA- oder
  Richtungstaste;
- reiht den Abschluss auf NVDAs Hauptthread ein und löscht begrenzten
  Autorepeat-Zustand.

Nackte Wiederholungen einer beim NVDA-Key-up noch gehaltenen Richtungstaste
werden ausschließlich im selben weiterhin bestätigten Neovim-Control über
ein temporäres No-op-AppModule-Skript verbraucht. In einem anderen Pane greift
diese Sperre nicht.

Die eigentliche Exploration ist semantisch und transportneutral. Eine
streng lesende Lua-Komponente hält einen flüchtigen virtuellen Cursor und
liefert über feste, validierte Controls nur das ausgewählte Zeichen, Wort oder
die ausgewählte Zeile. Sie bewegt niemals den echten Neovim-Cursor. Ausgehende
Controls werden außerhalb von NVDAs Hauptthread gesendet.

## Priorität und Benutzerzuweisungen

Im bestätigten Neovim-Control gewinnt das AppModule nach NVDAs normaler
Reihenfolge vor eingebauten Befehlen wie `NVDA+k` und Laptop-`NVDA+l`.
Fremde GlobalPlugins behalten ihre von NVDA vorgegebene höhere Priorität.
Explizite Benutzerzuweisungen und Aufhebungen bleiben NVDAs Gesture Map
überlassen. Ein erzwungener Vorrang vor GlobalPlugins oder Benutzerregeln ist
nicht Teil dieser Entscheidung.

## Folgen

Die Funktion nutzt NVDAs vorhandene Gestenerkennung, Eingabehilfe,
Skriptwarteschlange und Konfliktauflösung. Der einzige prozessweit aufgerufene
Zusatz ist ein passiver öffentlicher Raw-Key-Beobachter. Sein schneller
Rücklauf, das ständige `True`, symmetrischer Reload, exakte Pane-Abschottung
und Fail-open-Verhalten benötigen Struktur- und Laufzeittests.

Fokuswechsel, Disconnect, Resync, veralteter Zustand oder eine verspätete
Antwort beenden die Exploration ohne geratenen Text und ohne
Editoroperation. Eine praktische Übernahme erfolgt erst nach Tests mit
gemischten lokalen, SSH-, Neovim- und Nicht-Neovim-Panes.
