# Repository layout

| Path | Responsibility |
| --- | --- |
| `neovim-plugin/` | Lua state, semantic events, registry, adapters |
| `bridge/python/` | Linux Neovim RPC to SSH-stdio bridge |
| `protocol/python/` | framing, validation, sequencing, Unicode helpers |
| `nvda-addon/core/` | NVDA-independent state, connection, speech, Braille |
| `nvda-addon/addon/` | NVDA UI, Windows Terminal AppModule, resources |
| `packaging/` | rootless Linux user installer |
| `tools/` | reproducible builds and checks |
| `docs/` | maintained German and English documentation |

`buildVars.py` is the single maintained source for product identity, numeric
Store version, branch-local development build number, and
version metadata. Generated packages go to `dist/`, generated documentation to
`build/`, and private temporary material to ignored `tmp/`.

GitHub community files use the recognized root names `README.md`, `LICENSE`,
`CONTRIBUTING.md`, and `SECURITY.md`; templates live below `.github/`. New
Python and Lua files normally use `snake_case`, while documentation uses
`lowercase-kebab-case`. `buildVars.py` deliberately retains the official NVDA
Add-on Template filename and is the documented exception.
