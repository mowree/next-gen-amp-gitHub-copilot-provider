# F-011: Loop Controller

## 1. Overview

**Module:** sdk_adapter/loop_control.py
**Priority:** P0
**Depends on:** F-010-sdk-client-wrapper

Controls the SDK's internal agent loop. Tracks turn count, signals abort, enforces circuit breaker limits.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/sdk_adapter/loop_control.py
from dataclasses import dataclass, field
from collections.abc import Callable
from enum import Enum
import time

class LoopExitMethod(Enum):
    ABORT = "abort"
    DISCONNECT = "disconnect"

@dataclass
class LoopState:
    """Current state of SDK's internal loop."""
    turn_count: int = 0
    first_turn_captured: bool = False
    start_time: float = field(default_factory=time.time)
    abort_requested: bool = False
    error: Exception | None = None
    
    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

class LoopController:
    """Controls the SDK's internal agent loop."""
    
    def __init__(
        self,
        max_turns: int = 3,  # Default from evidence
        exit_method: LoopExitMethod = LoopExitMethod.ABORT,
    ):
        ...
    
    def set_abort_callback(self, callback: Callable[[], None]) -> None:
        """Set callback to invoke when abort is needed."""
        ...
    
    def on_turn_start(self) -> bool:
        """Called when ASSISTANT_TURN_START event fires.
        
        Returns:
            True if turn should proceed, False if should abort
        """
        ...
    
    def should_abort(self) -> bool:
        """Check if we should abort the loop."""
        ...
    
    def request_abort(self, reason: str = "external") -> None:
        """Request loop abort."""
        ...
```

### Behavior

- Count turns via `on_turn_start()` called from event handler
- Trip circuit breaker when `turn_count > max_turns`
- Invoke abort callback when tripped
- Log all state transitions at DEBUG level

### Evidence

From reference implementation:
> Session a1a0af17: 305 turns, 607 tools
> Copilot SDK denial_behavior = RETRY
> Solution: Capture first turn, abort immediately

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `LoopController` tracks turn count | Unit test |
| AC-2 | Circuit breaker trips at max_turns | Unit test |
| AC-3 | Abort callback invoked once only | Unit test |
| AC-4 | `should_abort()` returns True after trip | Unit test |
| AC-5 | Default max_turns is 3 | Config check |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| max_turns = 0 | First turn triggers abort |
| Abort callback raises | Log error, don't re-raise |
| Multiple abort requests | Callback invoked only once |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../sdk_adapter/loop_control.py` | Create | LoopController, LoopState |
| `tests/test_loop_control.py` | Create | Loop controller tests |

## 6. Reference

- `reference-only/amplifier-module-provider-github-copilot/.../sdk_driver.py` lines 80-148
