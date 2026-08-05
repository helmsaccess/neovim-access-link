# Settings reference

Open `NVDA menu > Preferences > Settings... > Neovim Access Link`. The dialog
contains the `General`, `Feedback`, `Navigation`, `Braille`, and `Connections`
tabs.

Settings belong to the active NVDA configuration profile. `Apply` saves
changes and keeps the dialog open; `OK` saves and closes it. `Cancel` discards
changes that have not been applied.

## General

### Global action feedback

`Global action feedback` controls general messages such as activation,
connection, disconnection, and errors.

| Choice | Effect |
| --- | --- |
| `Off` | no speech or sound |
| `Speech` | spoken message only |
| `Tones` | sound only |
| `Both Speech and Tones` | message and sound; default |

Individual actions on the `Feedback` tab have their own values and are not
replaced by this choice.

### Session focus

`When focusing or changing buffers in a Neovim session` controls output after
a confirmed focus or buffer change.

| Choice | Effect |
| --- | --- |
| `No announcement` | no additional focus announcement |
| `Current line` | structured cursor line |
| `Current context, mode and connection name` | file or special context, mode, and connection; default |

The choice also applies when returning from Neovim's command line and when
leaving an embedded terminal for an editor buffer.

`Automatically speak the active function parameter while typing` is enabled by
default. When LSP signature help is available, Access Link speaks the active
parameter on entering or changing an argument. Movement within the same
argument remains silent. This feature uses speech; Braille remains on source
text.

## Feedback

Most entries offer `Off`, `Speech`, `Tones`, and `Both Speech and Tones`.
Diagnostic entries offer only `Off` and `Tones`.

| UI entry | Default | Event controlled |
| --- | --- | --- |
| `Insert and normal mode changes` | `Both Speech and Tones` | Insert, Normal, Terminal, and Command-line modes |
| `Deleting text` | `Both Speech and Tones` | character and text deletion |
| `Replacing text` | `Both Speech and Tones` | text replacement |
| `Copy and paste` | `Both Speech and Tones` | Access Link clipboard commands |
| `Line boundaries` | `Tones` | beginning and end of line, and speech-exploration origin |
| `File boundaries` | `Both Speech and Tones` | beginning and end of file |
| `Crossing into another line` | `Tones` | horizontal movement across a line boundary |
| `Missing matching bracket` | `Both Speech and Tones` | missing bracket pair |
| `Diagnostics when entering a line` | `Tones` | entering a diagnostic line |
| `Diagnostics at the cursor position` | `Tones` | cursor inside a diagnostic or an explicit empty query |

Typing echo, indentation, suggestions, spelling, and grammar follow the
corresponding NVDA settings. Access Link does not add a second configuration
for them.

## Navigation

This tab controls additional speech after normal Neovim navigation and after
releasing the NVDA key in speech exploration mode.

### Normal navigation

| UI entry | Choices | Default |
| --- | --- | --- |
| `Word navigation` | `Word only`; `Word and cursor character` | `Word and cursor character` |
| `Line navigation` | `Line only`; `Line and current word`; `Line and cursor character`; `Line, current word and cursor character` | `Line and cursor character` |

Neovim's `w`, `b`, `j`, `k`, and other movement commands continue to move the
real cursor. These settings change only the resulting output.

### Speech exploration mode release

| UI entry | Choices | Default |
| --- | --- | --- |
| `After word exploration in speech exploration mode` | `Word only`; `Word and cursor character` | `Word and cursor character` |
| `After line exploration in speech exploration mode` | the same four line choices as above | `Line and cursor character` |

The virtual position spoken during exploration is independent of these
choices. See [Speech exploration mode](speech-exploration.md).

## Braille

### Speech exploration mode

`Braille display follows the speech exploration mode position` is enabled by
default. During `NVDA+h`, `NVDA+j`, `NVDA+k`, `NVDA+l`, and the word variants,
the display shows the virtual reading position. Releasing the NVDA key returns
it to the real cursor. Disable the option to keep Braille at the real cursor
during speech exploration.

### Routing keys

`Double routing press on a word` offers:

- `Route only` (default),
- `Change word (cw)`,
- `Delete word (dw)`.

`Triple routing press on a line` offers:

- `Route only` (default),
- `Change to end of line (c$)`,
- `Delete to end of line (d$)`.

`Start triple-press line action at` offers:

- `Routed position` (default),
- `First non-blank character`,
- `Beginning of line`.

Repeat detection uses NVDA's multiple key press timeout from the Keyboard
settings.

### Spelling suggestions

`Start spelling suggestions at Braille cell` uses a one-based cell number. The
default is 1. When the complete suggestion does not fit to the right, Access
Link moves it left and aligns it as close to the right edge as possible. A
position beyond the connected display uses cell 1.

### Developer information

`Start temporary developer information at Braille cell` controls the position
of held signature, parameter, and diagnostic views. The default is 1. The same
safe alignment as spelling suggestions applies to insufficient space and an
invalid position.

See [Braille support](braille.md) for complete operation.

## Connections

This tab contains saved SSH targets. Local Windows Neovim needs no connection
entry.

`Saved connections` shows the chosen name, SSH target, and a port that differs
from the default 22. There is no default connection.

### Add, edit, or remove a connection

- `Add connection...` opens an empty Linux connection form.
- `Edit connection...` opens the selected entry.
- `Remove connection` deletes the entry from the current NVDA profile after
  `Apply` or `OK`.

Removing a profile does not uninstall components, delete keys, or change
OpenSSH configuration.

### Linux connection fields

| UI field | Content |
| --- | --- |
| `Connection name` | freely chosen unique label |
| `Server name, address or SSH alias` | DNS name, IP address, or OpenSSH alias |
| `Linux username (optional when defined by SSH config)` | account running Neovim and the bridge |
| `SSH port` | number from 1 through 65535; default 22 |
| `Private key file (optional)` | key file for OpenSSH; empty uses configuration, default keys, or `ssh-agent` |
| `Sign-in method` | OpenSSH setup or password prompt |

`Use OpenSSH setup (recommended: keys, ssh-agent or SSH config)` uses normal
Windows OpenSSH configuration.

`Ask for the SSH password when connecting (password is not saved)` prompts
accessibly for the Linux password when needed. The password remains in memory
only for the current NVDA process. The SSH server must allow password login for
that account.

Install or remove components through the two `Neovim Access Link: ...` entries
in NVDA's `Tools` menu. The [Quick Guide](quick-guide.md) describes the
procedure.

## Recommended starting point

The defaults provide a directly usable starting point:

- general actions, modes, editing, file boundaries, bracket errors, and
  clipboard actions use speech and sounds;
- line boundaries, line changes, and diagnostics use short sounds;
- focus announces context, mode, and connection name;
- word and line navigation include the cursor character;
- repeated Braille routing performs no editing action;
- Braille follows speech exploration.

Begin by changing only feedback that is concretely too frequent or too brief
in your NVDA configuration.
