# Bundled dependencies

MessagePack Python 1.1.1 is bundled under the Apache License 2.0 for protocol
encoding/decoding. Its source and license are copied into the built add-on and
Linux bridge package. It avoids requiring a target-side MessagePack RPM.

Build-only tools include Python 3, ConfigObj for NVDA-compatible manifest
validation, and Pandoc for standalone HTML documentation. They are not runtime
dependencies of the installed add-on or plugin. Dependency additions require
documented purpose, license, maintenance, size, latency, and packaging impact.
