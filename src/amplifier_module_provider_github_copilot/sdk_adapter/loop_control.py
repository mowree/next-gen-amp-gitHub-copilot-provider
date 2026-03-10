"""
Loop Controller for SDK internal agent loop.

Controls the SDK's internal agent loop: tracks turn count, signals abort,
enforces circuit breaker limits.

Evidence:
- Session a1a0af17: 305 turns, 607 tools (SDK denial_behavior=RETRY runaway)
- Solution: Capture first turn, abort immediately after

Contract: contracts/sdk-boundary.md
Feature: F-011
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

SDK_MAX_TURNS_DEFAULT = 3
SDK_MAX_TURNS_HARD_LIMIT = 10


class LoopExitMethod(Enum):
    """Method used to exit the SDK agent loop."""

    ABORT = "abort"
    DISCONNECT = "disconnect"


@dataclass
class LoopState:
    """Current state of the SDK's internal agent loop.

    Attributes:
        turn_count: Number of turns completed so far.
        first_turn_captured: Whether the first turn has been processed.
        start_time: Monotonic time when loop started.
        abort_requested: Whether an abort has been signalled.
        error: Any error that caused the loop to stop.
    """

    turn_count: int = 0
    first_turn_captured: bool = False
    start_time: float = field(default_factory=time.time)
    abort_requested: bool = False
    error: Exception | None = None

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time


class LoopController:
    """Controls the SDK's internal agent loop.

    Responsibilities:
    - Track turn count
    - Invoke abort callback when circuit breaker trips
    - Enforce hard turn limit (prevent runaway loops)

    Usage::

        controller = LoopController(max_turns=3)
        controller.set_abort_callback(session.abort)

        # Called on each ASSISTANT_TURN_START event:
        if not controller.on_turn_start():
            # Circuit breaker tripped; abort callback already invoked
            break
    """

    def __init__(
        self,
        max_turns: int = SDK_MAX_TURNS_DEFAULT,
        exit_method: LoopExitMethod = LoopExitMethod.ABORT,
    ) -> None:
        # Cap at hard limit to prevent configuration mistakes
        self.max_turns = min(max_turns, SDK_MAX_TURNS_HARD_LIMIT)
        self.exit_method = exit_method
        self.state = LoopState()
        self._abort_callback: Callable[[], None] | None = None
        self._abort_callback_invoked = False

    def set_abort_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when abort is needed."""
        self._abort_callback = callback

    def on_turn_start(self) -> bool:
        """Called when ASSISTANT_TURN_START event fires.

        Increments turn counter. If count exceeds max_turns, trips the
        circuit breaker and invokes the abort callback exactly once.

        Returns:
            True if the turn should proceed, False if it should be aborted.
        """
        self.state.turn_count += 1
        logger.debug(f"[LOOP] Turn {self.state.turn_count}/{self.max_turns} started")

        if self.state.turn_count > self.max_turns:
            logger.warning(
                f"[LOOP] Circuit breaker tripped! "
                f"Turn {self.state.turn_count} exceeds max {self.max_turns}"
            )
            self.state.abort_requested = True
            self._invoke_abort_callback()
            return False

        return True

    def should_abort(self) -> bool:
        """Check whether the loop should abort."""
        return self.state.abort_requested

    def request_abort(self, reason: str = "external") -> None:
        """Request loop abort from external caller."""
        logger.info(f"[LOOP] Abort requested: {reason}")
        self.state.abort_requested = True
        self._invoke_abort_callback()

    def _invoke_abort_callback(self) -> None:
        """Invoke abort callback exactly once, swallowing any exceptions."""
        if self._abort_callback is not None and not self._abort_callback_invoked:
            self._abort_callback_invoked = True
            try:
                self._abort_callback()
            except Exception as e:
                logger.error(f"[LOOP] Abort callback raised: {e}")
