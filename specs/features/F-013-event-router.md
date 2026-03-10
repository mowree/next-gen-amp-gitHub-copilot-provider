# F-013: SDK Event Router

## 1. Overview

**Module:** sdk_adapter/event_handler.py
**Priority:** P0
**Depends on:** F-011-loop-controller, F-012-tool-capture-strategy

Routes SDK events to appropriate handlers. Coordinates LoopController and ToolCaptureStrategy.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/sdk_adapter/event_handler.py
from collections.abc import Callable, Awaitable
from typing import Any

from .loop_control import LoopController, ToolCaptureStrategy, CapturedToolCall
from ..streaming import DomainEvent

class SdkEventHandler:
    """Handles SDK events and coordinates loop control + tool capture."""
    
    def __init__(
        self,
        loop_controller: LoopController,
        tool_capture: ToolCaptureStrategy,
        on_domain_event: Callable[[DomainEvent], Awaitable[None]] | None = None,
    ):
        ...
    
    async def handle_event(self, event: Any) -> None:
        """Process a single SDK event.
        
        Routes to appropriate handler based on event type.
        """
        ...
    
    def get_captured_tools(self) -> list[CapturedToolCall]:
        """Get all tools captured from this request."""
        ...
    
    def should_abort(self) -> bool:
        """Check if we should abort the SDK loop."""
        ...
```

### Event Type Routing

| SDK Event Type | Handler Action |
|----------------|----------------|
| `ASSISTANT_TURN_START` | Call `loop_controller.on_turn_start()` |
| `ASSISTANT_MESSAGE` | Extract tool_requests, pass to `tool_capture.capture_from_event()` |
| `TEXT_DELTA` | Emit DomainEvent via `on_domain_event` |
| `TURN_COMPLETE` | Log completion, check abort state |
| `ERROR` | Log error, request abort |

### Behavior

- Single entry point for all SDK events
- Coordinate loop controller and tool capture
- Emit domain events for bridged event types
- Handle unknown event types gracefully (log warning, continue)

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | Routes ASSISTANT_TURN_START to loop controller | Unit test |
| AC-2 | Extracts tools from ASSISTANT_MESSAGE | Unit test |
| AC-3 | Emits TEXT_DELTA as DomainEvent | Unit test |
| AC-4 | Unknown events logged at warning | Unit test |
| AC-5 | `should_abort()` reflects loop controller state | Unit test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Event has no type attribute | Log warning, skip |
| tool_requests is None | Treat as empty list |
| on_domain_event callback raises | Log error, continue processing |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../sdk_adapter/event_handler.py` | Create | SdkEventHandler |
| `tests/test_event_handler.py` | Create | Event handler tests |

## 6. Reference

- `reference-only/amplifier-module-provider-github-copilot/.../sdk_driver.py` lines 300-450
