"""Pure state machine for repeated presses of one Braille routing key."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Hashable


WORD_ACTIONS = frozenset({"none", "changeWord", "deleteWord"})
LINE_ACTIONS = frozenset({"none", "changeLine", "deleteLine"})
LINE_STARTS = frozenset({"routing", "indentation", "beginning"})


@dataclass(frozen=True)
class BrailleRoutingActions:
    """Normalized actions selected in the add-on settings."""

    word_action: str = "none"
    line_action: str = "none"
    line_start: str = "routing"

    def __post_init__(self) -> None:
        if self.word_action not in WORD_ACTIONS:
            raise ValueError("invalid repeated-routing word action")
        if self.line_action not in LINE_ACTIONS:
            raise ValueError("invalid repeated-routing line action")
        if self.line_start not in LINE_STARTS:
            raise ValueError("invalid repeated-routing line start")

    @property
    def enabled(self) -> bool:
        return self.word_action != "none" or self.line_action != "none"


class BrailleRoutingPressKind(Enum):
    ROUTE = "route"
    WAIT = "wait"
    WORD = "word"
    LINE = "line"
    NONE = "none"


@dataclass(frozen=True)
class BrailleRoutingPressPlan:
    kind: BrailleRoutingPressKind
    token: int | None = None
    delay_ms: int | None = None
    action: str | None = None
    line_start: str | None = None


class BrailleRoutingRepeatController:
    """Recognize double and triple presses without delaying the first route."""

    def __init__(self) -> None:
        self._identity: Hashable | None = None
        self._pressCount = 0
        self._deadlineMs = 0
        self._nextToken = 0
        self._pendingToken: int | None = None
        self._pendingWordAction = "none"

    def reset(self) -> None:
        self._identity = None
        self._pressCount = 0
        self._deadlineMs = 0
        self._pendingToken = None
        self._pendingWordAction = "none"

    def press(
        self,
        identity: Hashable,
        *,
        now_ms: int,
        timeout_ms: int,
        actions: BrailleRoutingActions,
    ) -> BrailleRoutingPressPlan:
        if not isinstance(now_ms, int) or isinstance(now_ms, bool) or now_ms < 0:
            raise ValueError("now_ms must be a non-negative integer")
        if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool) or timeout_ms < 1:
            raise ValueError("timeout_ms must be a positive integer")
        if not actions.enabled:
            self.reset()
            return BrailleRoutingPressPlan(BrailleRoutingPressKind.ROUTE)
        if (
            self._identity != identity
            or self._pressCount == 0
            or now_ms > self._deadlineMs
        ):
            self._identity = identity
            self._pressCount = 1
            self._deadlineMs = now_ms + timeout_ms
            self._pendingToken = None
            self._pendingWordAction = "none"
            return BrailleRoutingPressPlan(BrailleRoutingPressKind.ROUTE)

        self._deadlineMs = now_ms + timeout_ms
        self._pressCount += 1
        if self._pressCount == 2:
            if actions.line_action == "none":
                self.reset()
                if actions.word_action == "none":
                    return BrailleRoutingPressPlan(BrailleRoutingPressKind.ROUTE)
                return BrailleRoutingPressPlan(
                    BrailleRoutingPressKind.WORD,
                    action=actions.word_action,
                )
            self._nextToken += 1
            self._pendingToken = self._nextToken
            self._pendingWordAction = actions.word_action
            return BrailleRoutingPressPlan(
                BrailleRoutingPressKind.WAIT,
                token=self._pendingToken,
                delay_ms=timeout_ms,
            )

        if self._pressCount == 3:
            self.reset()
            return BrailleRoutingPressPlan(
                BrailleRoutingPressKind.LINE,
                action=actions.line_action,
                line_start=actions.line_start,
            )

        self.reset()
        return BrailleRoutingPressPlan(BrailleRoutingPressKind.ROUTE)

    def expire(self, token: int) -> BrailleRoutingPressPlan:
        """Complete a pending double press unless a third press superseded it."""
        if token != self._pendingToken or self._pressCount != 2:
            return BrailleRoutingPressPlan(BrailleRoutingPressKind.NONE)
        action = self._pendingWordAction
        self.reset()
        if action == "none":
            return BrailleRoutingPressPlan(BrailleRoutingPressKind.NONE)
        return BrailleRoutingPressPlan(
            BrailleRoutingPressKind.WORD,
            action=action,
        )
