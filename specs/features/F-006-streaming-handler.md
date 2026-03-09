# Feature Spec: F-006 Streaming Handler

**Feature ID:** F-006
**Module:** `src/amplifier_module_provider_github_copilot/streaming.py`
**Contract:** `contracts/streaming-contract.md`
**Priority:** P0 (Foundation)
**Estimated Size:** ~80 lines (extends existing streaming.py)

---

## Summary

Accumulate streaming domain events into a final response structure. Takes the stream of `DomainEvent` objects from event translation and assembles them into accumulated content, tool calls, and usage statistics.

---

## Acceptance Criteria

1. **StreamingAccumulator class:**
   - Accumulates `CONTENT_DELTA` events into text/thinking content
   - Collects `TOOL_CALL` events
   - Tracks `USAGE_UPDATE` events
   - Detects `TURN_COMPLETE` as finish signal
   - Handles `ERROR` events

2. **Accumulated result structure:**
   - `text_content: str` - accumulated text deltas
   - `thinking_content: str` - accumulated thinking deltas (if any)
   - `tool_calls: list[dict]` - collected tool call data
   - `usage: dict | None` - final usage statistics
   - `finish_reason: str | None` - from TURN_COMPLETE event

3. **Event ordering:**
   - Events processed in order received
   - Accumulator handles interleaved content types

4. **Error handling:**
   - ERROR events captured with details
   - Accumulator can report error state

---

## Interfaces

```python
# Extends: src/amplifier_module_provider_github_copilot/streaming.py

from dataclasses import dataclass, field
from typing import Any

@dataclass
class AccumulatedResponse:
    """
    Accumulated response from streaming events.
    
    Contract: streaming-contract.md
    """
    text_content: str = ""
    thinking_content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    error: dict[str, Any] | None = None
    is_complete: bool = False


class StreamingAccumulator:
    """
    Accumulates streaming domain events into final response.
    
    Contract: streaming-contract.md
    
    Usage:
        accumulator = StreamingAccumulator()
        for event in domain_events:
            accumulator.add(event)
        result = accumulator.get_result()
    """
    
    def __init__(self) -> None:
        """Initialize empty accumulator."""
        ...
    
    def add(self, event: DomainEvent) -> None:
        """
        Add domain event to accumulator.
        
        Contract:
        - CONTENT_DELTA with TEXT block_type -> append to text_content
        - CONTENT_DELTA with THINKING block_type -> append to thinking_content
        - TOOL_CALL -> append to tool_calls
        - USAGE_UPDATE -> update usage
        - TURN_COMPLETE -> set finish_reason, mark complete
        - ERROR -> set error, mark complete
        
        Args:
            event: Domain event from translate_event()
        """
        ...
    
    def get_result(self) -> AccumulatedResponse:
        """
        Get accumulated response.
        
        Returns:
            AccumulatedResponse with all accumulated data.
        """
        ...
    
    @property
    def is_complete(self) -> bool:
        """True if TURN_COMPLETE or ERROR received."""
        ...
```

---

## Implementation Notes

### Delta Accumulation

```python
def add(self, event: DomainEvent) -> None:
    """Add event to accumulator."""
    if event.type == DomainEventType.CONTENT_DELTA:
        text = event.data.get("text", "")
        if event.block_type == "THINKING":
            self._thinking_content += text
        else:  # TEXT or None
            self._text_content += text
    
    elif event.type == DomainEventType.TOOL_CALL:
        self._tool_calls.append(event.data)
    
    elif event.type == DomainEventType.USAGE_UPDATE:
        self._usage = event.data
    
    elif event.type == DomainEventType.TURN_COMPLETE:
        self._finish_reason = event.data.get("finish_reason", "stop")
        self._is_complete = True
    
    elif event.type == DomainEventType.ERROR:
        self._error = event.data
        self._is_complete = True
```

### Finish Reason Mapping

From config/events.yaml `finish_reason_map`:
- `end_turn` -> `STOP`
- `stop` -> `STOP`
- `tool_use` -> `TOOL_USE`
- `max_tokens` -> `LENGTH`
- `content_filter` -> `CONTENT_FILTER`
- `_default` -> `ERROR`

---

## Test Cases

```python
# tests/test_streaming.py (extends existing)

class TestStreamingAccumulator:
    """Tests for StreamingAccumulator."""
    
    def test_accumulator_starts_empty(self):
        """New accumulator has empty state."""
        accumulator = StreamingAccumulator()
        result = accumulator.get_result()
        assert result.text_content == ""
        assert result.tool_calls == []
        assert not result.is_complete
    
    def test_content_delta_accumulates_text(self):
        """CONTENT_DELTA events accumulate text."""
        accumulator = StreamingAccumulator()
        accumulator.add(DomainEvent(
            type=DomainEventType.CONTENT_DELTA,
            data={"text": "Hello "},
            block_type="TEXT",
        ))
        accumulator.add(DomainEvent(
            type=DomainEventType.CONTENT_DELTA,
            data={"text": "world"},
            block_type="TEXT",
        ))
        result = accumulator.get_result()
        assert result.text_content == "Hello world"
    
    def test_thinking_delta_accumulates_separately(self):
        """THINKING block_type accumulates to thinking_content."""
        accumulator = StreamingAccumulator()
        accumulator.add(DomainEvent(
            type=DomainEventType.CONTENT_DELTA,
            data={"text": "Let me think"},
            block_type="THINKING",
        ))
        result = accumulator.get_result()
        assert result.thinking_content == "Let me think"
        assert result.text_content == ""
    
    def test_tool_call_collected(self):
        """TOOL_CALL events collected in list."""
        accumulator = StreamingAccumulator()
        accumulator.add(DomainEvent(
            type=DomainEventType.TOOL_CALL,
            data={"id": "tc1", "name": "read_file", "arguments": {"path": "x.py"}},
        ))
        result = accumulator.get_result()
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "read_file"
    
    def test_usage_update_stored(self):
        """USAGE_UPDATE event stored."""
        accumulator = StreamingAccumulator()
        accumulator.add(DomainEvent(
            type=DomainEventType.USAGE_UPDATE,
            data={"input_tokens": 100, "output_tokens": 50},
        ))
        result = accumulator.get_result()
        assert result.usage["input_tokens"] == 100
    
    def test_turn_complete_marks_done(self):
        """TURN_COMPLETE marks accumulator complete."""
        accumulator = StreamingAccumulator()
        accumulator.add(DomainEvent(
            type=DomainEventType.TURN_COMPLETE,
            data={"finish_reason": "stop"},
        ))
        result = accumulator.get_result()
        assert result.is_complete
        assert result.finish_reason == "stop"
    
    def test_error_marks_complete_with_error(self):
        """ERROR event marks complete with error data."""
        accumulator = StreamingAccumulator()
        accumulator.add(DomainEvent(
            type=DomainEventType.ERROR,
            data={"message": "Rate limit exceeded"},
        ))
        result = accumulator.get_result()
        assert result.is_complete
        assert result.error is not None
        assert "Rate limit" in result.error["message"]
    
    def test_interleaved_content_handled(self):
        """Interleaved text and thinking accumulate correctly."""
        accumulator = StreamingAccumulator()
        accumulator.add(DomainEvent(DomainEventType.CONTENT_DELTA, {"text": "A"}, "TEXT"))
        accumulator.add(DomainEvent(DomainEventType.CONTENT_DELTA, {"text": "T"}, "THINKING"))
        accumulator.add(DomainEvent(DomainEventType.CONTENT_DELTA, {"text": "B"}, "TEXT"))
        result = accumulator.get_result()
        assert result.text_content == "AB"
        assert result.thinking_content == "T"
```

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `src/amplifier_module_provider_github_copilot/streaming.py` | Extend | +80 |
| `tests/test_streaming.py` | Extend | +80 |

---

## Dependencies

- F-005 (Event Translation) - for DomainEvent, DomainEventType

---

## Contract References

- `streaming-contract:Accumulation:MUST:1` — Deltas accumulate in order
- `streaming-contract:Completion:MUST:1` — TURN_COMPLETE signals completion
- `streaming-contract:Error:MUST:1` — ERROR events captured with details
