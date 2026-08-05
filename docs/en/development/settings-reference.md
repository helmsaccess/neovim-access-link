# Add-on settings reference

## Authoritative source contracts

The NVDA configuration schema and its defaults live in
[`__init__.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/addon/globalPlugins/NeovimAccessLink/__init__.py).
[`settings_service.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/addon/globalPlugins/NeovimAccessLink/settings_service.py)
owns normalization, profile changes, and persistence;
[`nvda_ui.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/addon/globalPlugins/NeovimAccessLink/nvda_ui.py)
owns the visible controls. Package and profile tests in
[`test_built_addon.py`](https://github.com/helmsaccess/neovim-access-link/blob/main/nvda-addon/tests/test_built_addon.py)
verify schema, defaults, UI values, and persistence. This page is the readable
developer reference, not a second schema source.

## Storage and profiles

The “Neovim Access Link” category uses
`config.conf["NeovimAccessLink"]` and therefore NVDA's normal configuration
profiles. “Apply” or “OK” writes changed values to the active profile; unset
values inherit like other NVDA settings. There is no separate JSON settings
store.

`SettingsService` loads, normalizes, and stores a complete detached copy of
effective values. Invalid types or ranges fall back to defaults and are
diagnosed without confidential content. A profile switch reloads feedback
immediately. Connection changes apply to new connections and do not stop an
already authenticated editor session.

## Interface and ownership

The NVDA Settings dialog contains five tabs:

- “General” for global feedback, session focus, and automatic parameter speech;
- “Feedback” for individual speech and cue events;
- “Navigation” for detail after normal navigation and speech exploration;
- “Braille” for exploration, routing actions, and transient views;
- “Connections” for local Windows Neovim and saved SSH targets.

The add-on does not duplicate an applicable NVDA setting. Typing echo comes
from Keyboard, indentation plus spelling and grammar from Document Formatting,
automatic suggestion cues from Object Presentation, and translation, driver,
and cursor shape from Braille.

## Feedback

Feedback values use `0 = Off`, `1 = Speech`, `2 = Tones`, and `3 = Both Speech
and Tones`. The global value bounds individual actions. The interface offers
`diagnosticLine` and `diagnosticPosition` only as Off or Tones.

| Key | Default | Purpose |
|---|---:|---|
| `global` | 3 | upper bound for all add-on feedback |
| `mode`, `delete`, `replace` | 3 | mode changes and editing |
| `lineBoundary`, `lineCrossed` | 2 | line boundaries and line transitions |
| `fileBoundary`, `matchingError` | 3 | file boundaries and missing counterpart |
| `diagnosticLine`, `diagnosticPosition` | 2 | deliberate error/warning cues |
| `clipboard` | 3 | success of explicit clipboard commands |

`focusAnnouncement` uses `0 = no announcement`, `1 = current line`, and
`2 = current file or special context with mode and connection name`. Default
is 2. `automaticParameterHints` defaults to enabled and controls only brief
validated speech for the active function parameter.

## Navigation details

`navigationDetails` keeps separate values for normal navigation and speech
exploration release output:

| Key | Values | Default |
|---|---|---:|
| `navigationWord`, `explorationWord` | 0 word; 1 word and cursor character | 1 |
| `navigationLine`, `explorationLine` | 0 line; 1 plus word; 2 plus cursor character; 3 plus word and character | 2 |

Neutral speech planners receive already resolved Boolean values and do not
read NVDA configuration. Exploration values are read from the active profile
when NVDA is released; they alter neither virtual movement nor character
exploration.

## Braille

| Key | Default | Behavior |
|---|---:|---|
| `brailleFollowSpeechExploration` | `true` | Braille follows the virtual speech-exploration position; separate Braille exploration has priority. |
| `brailleSuggestionStart` | 1 | one-based starting cell for transient spelling suggestions |
| `brailleDeveloperStart` | 1 | one-based starting cell for held parameter and diagnostic views |

Starting cells range from 1 through 1000. If the physical display is shorter,
cell 1 is used. After Braille translation, the start moves left when needed so
the complete text fits where possible. These values change neither speech nor
the persistent editor region.

`brailleRouting` contains three choice indices:

- `wordAction`: 0 route only, 1 `cw`, 2 `dw`;
- `lineAction`: 0 route only, 1 `c$`, 2 `d$`;
- `lineStart`: 0 routed position, 1 first non-blank, 2 line beginning.

Every default is 0. `lineStart` applies only when a line action is enabled.
Repeat timing comes exclusively from NVDA's public
`keyboard.multiPressTimeout` setting.

## Connections and assignment

`connections` stores a JSON-encoded list of validated SSH profiles inside the
NVDA configuration section. A profile contains internal ID, display name,
host or OpenSSH alias, optional Linux user, port, optional key file, and
authentication method. Host and user remain separate fields. Duplicate IDs,
invalid ports, and option injection are rejected; passwords are runtime-only.

Local Windows Neovim is the fixed `localWindowsTcp` target. It has no saved
profile or configurable port; its dynamic endpoint remains on `127.0.0.1`.

F12 is the packaged physical assignment key, not an assignable NVDA script.
With support enabled, one F12 press authorizes exactly one attempt for the
focused Windows Terminal control. Focus object, concrete AppModule instance,
complete UIA identity, gate, and fresh session claim must agree. Without a
match, no binding, dialog, or suppression is created.

The assignable “Select a server and connect this terminal to a new Neovim
session” command opens profile selection and then requires F12 in the desired
session. Runtime bindings use UIA runtime IDs, live only in memory, and are not
guessed from window titles or terminal text.

## Validation boundary

Settings control only planning, UI, and construction of new connections. They
cannot bypass a capability, focus, identity, or protocol check or generate
free-form Lua, Ex, register, or transport commands. Schema and defaults belong
to add-on code; this reference and both language versions change together with
schema, profile, UI, localization, and package tests.
