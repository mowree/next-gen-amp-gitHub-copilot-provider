# F-012: Tool Capture Strategy

## 1. Overview

**Module:** sdk_adapter/loop_control.py (extend)
**Priority:** P0
**Depends on:** F-011-loop-controller

Captures tool calls from SDK events with first-turn-only strategy and deduplication.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/sdk_adapter/loop_control.py (extend)
from dataclasses import dataclass
import json

@dataclass
class CapturedToolCall:
    """A tool call captured from SDK events."""
    id: str
    name: str
    arguments: dict[str, Any]
    turn: int  # Which turn this was captured from
    
    def __hash__(self) -> int:
        """Hash for deduplication (by name + arguments)."""
        args_str = json.dumps(self.arguments, sort_keys=True)
        return hash((self.name, args_str))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CapturedToolCall):
            return NotImplemented
        return self.name == other.name and self.arguments == other.arguments

class ToolCaptureStrategy:
    """Captures tool calls with configurable strategy."""
    
    def __init__(
        self,
        first_turn_only: bool = True,
        deduplicate: bool = True,
    ):
        ...
    
    def set_current_turn(self, turn: int) -> None:
        """Update current turn number."""
        ...
    
    def capture_from_event(self, tool_requests: list[Any]) -> list[CapturedToolCall]:
        """Process tool requests from ASSISTANT_MESSAGE event.
        
        Returns:
            List of newly captured tools (may be empty if filtered)
        """
        ...
    
    def get_captured_tools(self) -> list[CapturedToolCall]:
        """Get all captured tools."""
        ...
    
    def reset(self) -> None:
        """Reset capture state for new request."""
        ...
```

### Behavior

- FIRST_TURN_ONLY (default): Capture from first ASSISTANT_MESSAGE only
- Deduplication by (name, arguments) hash
- Parse arguments string to dict if needed
- Ignore tools from subsequent turns

### Evidence

From reference:
> 607 tools captured from 305 turns = accumulation bug
> First turn had the valid 2 tools
> Subsequent turns were retries of the same tools

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | First turn tools captured | Unit test |
| AC-2 | Subsequent turn tools ignored (first_turn_only=True) | Unit test |
| AC-3 | Duplicate tools deduplicated | Unit test |
| AC-4 | String arguments parsed to dict | Unit test |
| AC-5 | Hash equality works for dedup | Unit test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty tool_requests | Return empty list |
| Arguments as string | Parse JSON, fallback to {"raw": str} |
| Invalid JSON in arguments | Use {"raw": str} fallback |
| Same tool, different args | Capture both (not duplicates) |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/.../sdk_adapter/loop_control.py` | Modify | Add ToolCaptureStrategy, CapturedToolCall |
| `tests/test_tool_capture.py` | Create | Tool capture tests |

## 6. Reference

- `reference-only/amplifier-module-provider-github-copilot/.../sdk_driver.py` lines 150-240
