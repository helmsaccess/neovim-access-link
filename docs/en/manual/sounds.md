# Sounds and earcons

Access Link uses short sounds so that frequent editor states do not always
need speech. The `Feedback` tab controls speech and sounds separately for each
event. Typing echo, indentation, spelling, and grammar follow NVDA's own
settings.

## Sound overview

| Event | Sound | Setting |
| --- | --- | --- |
| connection established | NVDA's `connected.wav` | `Global action feedback` |
| active connection disconnected | NVDA's `disconnected.wav` | `Global action feedback` |
| Insert mode or direct terminal input | NVDA's focus-mode sound | `Insert and normal mode changes` |
| Normal or Terminal-Normal mode | NVDA's browse-mode sound | `Insert and normal mode changes` |
| Neovim command line | short middle tone | `Insert and normal mode changes` |
| text deletion | short deletion sound | `Deleting text` |
| text replacement | short replacement sound | `Replacing text` |
| beginning or end of line | distinct boundary sounds | `Line boundaries` |
| beginning or end of file | distinct boundary sounds | `File boundaries` |
| horizontal movement into another line | short transition sound | `Crossing into another line` |
| missing bracket pair | NVDA's error sound | `Missing matching bracket` |
| suggestion menu opened or closed | NVDA's suggestion sounds | NVDA suggestion setting |
| spelling or grammar error | NVDA's text-error sound | NVDA Document Formatting |
| diagnostic line or position | short error or warning sound | corresponding diagnostic setting |
| explicit diagnostic query with no result | short neutral confirmation sound | corresponding diagnostic setting |

A connection or mode sound plays only for the corresponding confirmed state
transition. Resynchronizing the same state does not repeat it.

## Indentation

Indentation follows NVDA's setting under `Document Formatting`. Access Link
uses NVDA's tone pitch and duration and produces an indentation tone only when
indentation changes.

## Spelling and grammar

NVDA Document Formatting controls speech, sounds, and Braille marking
independently:

- `Speech` controls the localized spelling- or grammar-error announcement.
- `Sound` controls the text-error sound.
- `Braille` controls marking on the Braille display.

The same setting applies after completing a misspelled word, during normal word
navigation, and during word exploration. The reached word is still spoken
independently of error feedback.

## Diagnostics

Errors and warnings have distinct short sounds. Access Link plays them during
deliberate navigation into a diagnostic line or diagnostic position. Typing
and background updates remain silent. Information and hint diagnostics produce
no diagnostic sound.

An explicit diagnostic query with no result uses a separate neutral sound and
the message `no diagnostic`. Ordinary navigation over text without diagnostics
remains silent.

Sources and licenses for bundled audio files are in
`resources/sounds/LICENSE.txt` in the installed add-on and in the developer
documentation.
