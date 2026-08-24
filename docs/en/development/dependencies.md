# Bundled dependencies

## Bundled runtime dependency

MessagePack Python 1.1.2 is bundled under the Apache License 2.0 for protocol
encoding/decoding. Its source and license are copied into the built add-on and
Linux bridge package. It avoids requiring a target-side MessagePack RPM.

The add-on build accepts exactly version 1.1.2 and includes only portable
Python files and the license text. Native libraries and bytecode are not
packaged. Version 1.1.2 changes only the published wheels relative to 1.1.1,
allowing the isolated build to run with Python 3.14 without local compiler
tools.

## Build dependencies

Build-only tools include Python 3, ConfigObj for NVDA-compatible manifest
validation, and Pandoc for standalone HTML documentation. They are not runtime
dependencies of the installed add-on or plugin. Dependency additions require
documented purpose, license, maintenance, size, latency, and packaging impact.

## Authoritative sources and validation

`tools/build_nvda_addon.py` and `tools/build_user_package.py` define the
accepted MessagePack version and own selection, license validation, and
package destinations. `tools/distribution_build.py` owns the shared isolated
Windows/Linux build flow and the checksum-pinned official Pandoc archives.
The Windows path may also use an installed Pandoc with the matching major and
minor version. Pinned build and test tools live in `tools/requirements-build.txt`,
`tools/requirements-ci.txt`, `tools/requirements-linter-ci.txt`, and the
repository test workflow. Package tests inspect the resulting archives; this
page only repeats the dependency roles relevant to developers.
