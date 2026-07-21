# Overview for new developers

This page provides the basic model of Neovim Access Link without explaining
individual classes or message fields. The [architecture](architecture.md) then
expands the same building blocks in the same order.

## What problem does the project solve?

A terminal displays characters on a screen grid. NVDA cannot always determine
reliably from that grid whether Neovim is editing a line, showing a menu,
reporting a message, or changing mode. Neovim Access Link therefore does not
primarily read the visible terminal surface. A plugin asks Neovim directly for
the meaning of its current state and sends small semantic events to the NVDA
add-on.

The add-on can therefore distinguish “cursor moved,” “entered Insert mode,”
and “menu selection changed.” Only then does it decide whether speech, a sound,
or a Braille update is appropriate.

## The complete path

The normal data flow can be reduced to four steps:

```text
Neovim plugin
  → connection and protocol validation
  → validated editor state and output planning
  → NVDA output for the correctly associated terminal control
```

1. **The Neovim plugin describes the editor.** It observes Neovim APIs and
   produces events containing mode, cursor, line, message, menu, or other
   structured state.
2. **The connection carries only allowed messages.** The add-on connects
   directly to local Neovim. For a remote Linux session, a small bridge carries
   data over SSH. Protocol code bounds and validates the data in both cases.
3. **The add-on core remembers and plans.** It maintains validated current
   editor state and derives output plans from it. This part knows neither the
   speech synthesizer nor the visible Windows Terminal surface.
4. **The NVDA layer presents only in the correct context.** It connects plans
   to NVDA speech, sounds, and Braille. A focus gate ensures that special
   handling applies only to the confirmed Neovim association.

The main direction is from Neovim to NVDA. A small validated return channel
exists for a few explicitly allowed features, including clipboard and terminal
control. It is not a general Neovim RPC console.

## Local and remote operation differ only in the transport segment

| Variant | Path to the add-on | What is shared afterward |
| --- | --- | --- |
| Neovim on Windows | Neovim plugin → local RPC endpoint restricted to loopback → add-on | Protocol validation, editor state, focus checks, and output planning |
| Neovim on Linux | Neovim plugin → private Unix socket → Python bridge → SSH stdin/stdout → add-on | Protocol validation, editor state, focus checks, and output planning |

The bridge is needed only for the remote segment. It does not plan speech or
make focus decisions. After transport, local and remote events use the same
code wherever possible.

## Windows Terminal as a flexible workspace

Windows Terminal can open multiple windows. Each window can contain several
tabs, and a tab can be split horizontally or vertically into panes. A pane is
effectively an independent terminal area with its own input and output. An
unsplit tab contains one such area; a split tab contains several:

```text
Windows Terminal window
├── Tab 1
│   └── one terminal area
└── Tab 2
    ├── left pane: one terminal area
    └── right pane: another terminal area
```

Only one terminal area has keyboard focus at a time. The areas may contain
entirely different sessions: an ordinary PowerShell, local Neovim, an SSH
session running Neovim, or an SSH shell without Neovim. Multiple Windows
Terminal windows may also contain these mixed sessions at the same time.

The add-on's party trick is also one of its practical strengths: each Neovim
area can be connected independently to its own local or remote Neovim session.
When focus moves between windows, tabs, and panes, the add-on activates exactly
the corresponding editor state. Areas without Neovim retain NVDA's normal
terminal support. For example, one split tab can contain remote Neovim on the
left and an ordinary shell on the right, while another tab contains local
Neovim.

The association does not depend on the current Neovim mode. Once connected,
it remains in place while moving among the semantically supported modes. These
include Normal, Insert, Replace, Visual character, line, and block selection,
Operator-pending, command-line, Terminal-normal, and direct Terminal input.
Mode changes, navigation, and editing continue to come from Neovim events.

## What associating a control means

The Neovim connection knows editor state but does not automatically know which
terminal area has focus. Windows Terminal knows focus but cannot reliably
identify the Neovim instance running there. A window title or visible text
would be too imprecise.

Windows Terminal exposes each area as a concrete UI Automation `TermControl`.
For an unsplit tab it represents that tab's terminal content; in a split tab,
each pane is identified separately. An association therefore does not cover a
whole window or tab indiscriminately. It joins exactly this focused control to
exactly one Neovim connection.

The F12 mark joins two observations: the AppModule identifies the focused
`TermControl`, while the Neovim plugin records the same physical key press in
exactly one session. Each additional Neovim control is associated once in the
same way. The add-on then keeps several associations in memory concurrently.

On each later focus change, the associated session must confirm its current
context again. Only then does the add-on use its structured output. This keeps
a shell pane or another Neovim session from accidentally inheriting the state
of the previously focused control.

## How the NVDA part is divided

Three roles are enough for the basic model:

- The Windows Terminal AppModule receives application-specific focus,
  terminal, and input events. It identifies the concrete control and decides
  whether NVDA should continue normal processing for an event.
- The shared add-on runtime exists once per NVDA process. It assembles
  settings, connections, and the other supporting areas and tears them down in
  a defined order.
- Small separate services each perform one job, such as managing connections,
  confirming focus, updating editor state, or delivering output to NVDA.

The Global Plugin is therefore only the process-wide entry point for the
shared runtime, not a general handler for every terminal event. This division
keeps Windows Terminal events, networking, editor state, and NVDA output
separate and makes the parts independently testable.

## What “fail open” means

The add-on suppresses part of normal terminal output only when connection,
authentication, association, and focus are confirmed. If any condition is
missing or an error occurs, the focus gate restores NVDA's normal terminal
path. “Fail open” here means preferring NVDA's ordinary, possibly more verbose
terminal output over a silent terminal or one incorrectly treated as Neovim.

Network, SSH, reconnect, parsing, and installation work also stays off NVDA's
main thread. Receiver threads do not call NVDA directly; they pass validated
events to NVDA's event queue. Editor state, output plans, and concrete NVDA
output are updated there.

## From this overview into detail

The following pages expand this model step by step:

1. [Architecture](architecture.md) describes processes and data paths, the
   connection lifecycle, responsibilities, the gate, and special cases.
2. [Repository layout](repository-layout.md) maps these building blocks to
   source directories and tests.
3. [Development and test onboarding](getting-started.md) starts from a checkout
   and shows where common changes begin.
4. [Protocol v2](protocol.md) and [security and privacy](security.md) explain
   the message contract and trust boundaries.
5. [Feature matrix](accessibility.md) and [test strategy](testing.md) connect
   visible behavior to its required evidence.

Detailed pages may make terms more precise, but they should not contradict the
basic flow and responsibility boundaries described here.
