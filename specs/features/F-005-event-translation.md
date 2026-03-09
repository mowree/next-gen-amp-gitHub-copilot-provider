# Feature Spec: F-005 Event Translation

**Feature ID:** F-005
**Module:** `src/amplifier_module_provider_github_copilot/streaming.py`
**Config:** `config/events.yaml`
**Contract:** `contracts/event-vocabulary.md`
**Priority:** P0 (Foundation)
**Estimated Size:** ~100 lines

---

## Summary

Config-driven event classification: translate SDK events into domain events using BRIDGE/CONSUME/DROP classification from `config/events.yaml`.

---

## Acceptance Criteria

1. **Event translation module:** `streaming.py`
   - `translate_event(sdk_event) -> DomainEvent | None`
   - Config-driven classification

2. **Three event classifications:**
   - **BRIDGE**: Translate SDK event → DomainEvent (pass through)
   - **CONSUME**: Process internally, do not emit
   - **DROP**: Ignore completely

3. **Config file:** `config/events.yaml`
   - Declares which SDK events map to which domain events
   - Uses pattern matching for wildcards (e.g., `tool_result_*`)

4. **Domain event types (from GOLDEN_VISION_V2.md):**
   - `CONTENT_DELTA` - text/thinking content
   - `TOOL_CALL` - tool use complete
   - `USAGE_UPDATE` - token usage
   - `TURN_COMPLETE` - message complete
   - `SESSION_IDLE` - session idle
   - `ERROR` - error event

---

## Interfaces

```python
# src/amplifier_module_provider_github_copilot/streaming.py

from enum import Enum
from dataclasses import dataclass
from typing import Any

class DomainEventType(Enum):
    """Domain event types per event-vocabulary.md."""
    CONTENT_DELTA = "CONTENT_DELTA"
    TOOL_CALL = "TOOL_CALL"
    USAGE_UPDATE = "USAGE_UPDATE"
    TURN_COMPLETE = "TURN_COMPLETE"
    SESSION_IDLE = "SESSION_IDLE"
    ERROR = "ERROR"


class EventClassification(Enum):
    """How to handle SDK events."""
    BRIDGE = "bridge"    # Translate to domain event
    CONSUME = "consume"  # Process internally
    DROP = "drop"        # Ignore


@dataclass
class DomainEvent:
    """
    Domain event emitted from SDK event translation.
    
    Contract: event-vocabulary.md
    """
    type: DomainEventType
    data: dict[str, Any]
    block_type: str | None = None  # For CONTENT_DELTA: TEXT, THINKING


@dataclass
class EventConfig:
    """Configuration for event translation."""
    bridge_mappings: dict[str, tuple[DomainEventType, str | None]]  # sdk_type -> (domain_type, block_type)
    consume_patterns: list[str]
    drop_patterns: list[str]


def load_event_config(config_path: str = "config/events.yaml") -> EventConfig:
    """Load event classification config from YAML."""
    ...


def classify_event(sdk_event_type: str, config: EventConfig) -> EventClassification:
    """Classify SDK event type using config."""
    ...


def translate_event(sdk_event: Any, config: EventConfig) -> DomainEvent | None:
    """
    Translate SDK event to domain event.
    
    Contract: event-vocabulary.md
    
    - BRIDGE events → DomainEvent
    - CONSUME events → None (processed internally)
    - DROP events → None (ignored)
    
    Args:
        sdk_event: Raw SDK event
        config: Event classification config
        
    Returns:
        DomainEvent if BRIDGE, None otherwise
    """
    ...
```

---

## Config File: events.yaml

Already exists in `config/events.yaml` (from architecture docs). Key structure:

```yaml
event_classifications:
  bridge:
    - sdk_type: text_delta
      domain_type: CONTENT_DELTA
      block_type: TEXT
    - sdk_type: thinking_delta
      domain_type: CONTENT_DELTA
      block_type: THINKING
    - sdk_type: tool_use_complete
      domain_type: TOOL_CALL
    - sdk_type: message_complete
      domain_type: TURN_COMPLETE
    # ...

  consume:
    - tool_use_start
    - tool_use_delta
    - session_created
    - session_destroyed

  drop:
    - tool_result_*
    - mcp_*
    - heartbeat
    - debug_*
```

---

## Implementation Notes

### Pattern Matching

```python
import fnmatch

def matches_pattern(event_type: str, patterns: list[str]) -> bool:
    """Check if event type matches any pattern (supports wildcards)."""
    return any(fnmatch.fnmatch(event_type, p) for p in patterns)
```

### Classification Logic

```python
def classify_event(sdk_event_type: str, config: EventConfig) -> EventClassification:
    """Classify SDK event."""
    # Check bridge first (exact match)
    if sdk_event_type in config.bridge_mappings:
        return EventClassification.BRIDGE
    
    # Check consume patterns
    if matches_pattern(sdk_event_type, config.consume_patterns):
        return EventClassification.CONSUME
    
    # Check drop patterns
    if matches_pattern(sdk_event_type, config.drop_patterns):
        return EventClassification.DROP
    
    # Unknown events: log warning, drop
    logger.warning(f"Unknown SDK event type: {sdk_event_type}")
    return EventClassification.DROP
```

### Translation

```python
def translate_event(sdk_event: Any, config: EventConfig) -> DomainEvent | None:
    """Translate SDK event to domain event."""
    event_type = getattr(sdk_event, "type", None) or sdk_event.get("type")
    classification = classify_event(event_type, config)
    
    if classification == EventClassification.DROP:
        return None
    
    if classification == EventClassification.CONSUME:
        # Process internally if needed (e.g., accumulate tool_use_delta)
        return None
    
    # BRIDGE: translate to domain event
    domain_type, block_type = config.bridge_mappings[event_type]
    return DomainEvent(
        type=domain_type,
        data=extract_event_data(sdk_event),
        block_type=block_type,
    )
```

---

## Test Cases

```python
# tests/test_streaming.py

import pytest
from amplifier_module_provider_github_copilot.streaming import (
    translate_event,
    classify_event,
    load_event_config,
    EventClassification,
    DomainEventType,
)


@pytest.fixture
def event_config():
    return load_event_config("config/events.yaml")


def test_text_delta_bridges_to_content_delta(event_config):
    """text_delta SDK event → CONTENT_DELTA domain event."""
    sdk_event = {"type": "text_delta", "text": "Hello"}
    result = translate_event(sdk_event, event_config)
    assert result is not None
    assert result.type == DomainEventType.CONTENT_DELTA
    assert result.block_type == "TEXT"


def test_thinking_delta_bridges_with_thinking_block_type(event_config):
    """thinking_delta → CONTENT_DELTA with block_type=THINKING."""
    sdk_event = {"type": "thinking_delta", "text": "Let me think..."}
    result = translate_event(sdk_event, event_config)
    assert result.type == DomainEventType.CONTENT_DELTA
    assert result.block_type == "THINKING"


def test_tool_use_start_consumed(event_config):
    """tool_use_start is CONSUME → returns None."""
    sdk_event = {"type": "tool_use_start", "id": "tc1"}
    result = translate_event(sdk_event, event_config)
    assert result is None


def test_heartbeat_dropped(event_config):
    """heartbeat is DROP → returns None."""
    sdk_event = {"type": "heartbeat"}
    result = translate_event(sdk_event, event_config)
    assert result is None


def test_wildcard_pattern_matching(event_config):
    """Wildcard patterns match (e.g., tool_result_*)."""
    classification = classify_event("tool_result_success", event_config)
    assert classification == EventClassification.DROP


def test_unknown_event_dropped_with_warning(event_config, caplog):
    """Unknown events are dropped with warning."""
    sdk_event = {"type": "unknown_new_event"}
    result = translate_event(sdk_event, event_config)
    assert result is None
    assert "Unknown SDK event type" in caplog.text
```

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `src/amplifier_module_provider_github_copilot/streaming.py` | Create | ~100 |
| `config/events.yaml` | Create | ~50 |
| `tests/test_streaming.py` | Create | ~120 |

---

## Dependencies

- F-001 (SDK Adapter skeleton) - for DomainEvent base

---

## Contract References

- `event-vocabulary:Classification:MUST:1` — Three classifications
- `event-vocabulary:Bridge:MUST:1` — BRIDGE events become domain events
- `event-vocabulary:Drop:MUST:1` — DROP events are ignored
