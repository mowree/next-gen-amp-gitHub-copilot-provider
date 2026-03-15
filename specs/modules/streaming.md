# Module Spec: Streaming

**Module:** `amplifier_module_provider_github_copilot/streaming.py`
**Contracts:** `contracts/streaming-contract.md`, `contracts/event-vocabulary.md`
**Config:** `config/events.yaml`
**Target Size:** ~210 lines

---

## Purpose

Manages event translation and streaming accumulation — translating SDK events into domain events, accumulating deltas, and producing the final ChatResponse.

---

## Public API

```python
from amplifier_core import ChatResponse

class StreamingAccumulator:
    """Accumulates streaming domain events into final response."""
    
    def add(self, event: DomainEvent) -> None:
        """Add domain event to accumulator."""
    
    def get_result(self) -> AccumulatedResponse:
        """Get accumulated response."""
    
    def to_chat_response(self) -> ChatResponse:
        """
        Convert accumulated response to kernel ChatResponse.
        
        Contract: streaming-contract.md
        
        - MUST accumulate deltas into complete response
        - MUST use kernel types (TextBlock, ThinkingBlock, ToolCall)
        - MUST capture tool calls from events (not execute them)
        """

def translate_event(sdk_event: Any, config: EventConfig) -> DomainEvent | None:
    """Translate SDK event to domain event (config-driven)."""
```

---

## Streaming Flow

```
SDK session.events()
    │
    ▼
┌─────────────────────────────────────────┐
│           Event Translation              │
│  ┌─────────────────────────────────────┐│
│  │ ASSISTANT_MESSAGE_DELTA → CONTENT    ││
│  │ REASONING_DELTA → THINKING          ││
│  │ TOOL_CALL_START → TOOL_CALL         ││
│  │ SESSION_IDLE → TURN_COMPLETE        ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
    │
    ▼
StreamingAccumulator.add(domain_event)
    │
    ▼
StreamingAccumulator.to_chat_response()
    │
    ▼
ChatResponse {
    content: [TextBlock, ThinkingBlock, ...],
    tool_calls: [ToolCall, ...],
    usage: Usage,
    finish_reason: "stop" | "tool_use"
}
```
```

---

## Event Handling (Config-Driven)

Events are classified per `config/events.yaml`:

| Classification | Action |
|----------------|--------|
| **BRIDGE** | Translate to domain event, emit to accumulator |
| **CONSUME** | Process internally (e.g., tool_use_start) |
| **DROP** | Ignore (e.g., heartbeat, debug_*) |

```python
class DomainEventType(Enum):
    CONTENT_DELTA = "CONTENT_DELTA"
    TOOL_CALL = "TOOL_CALL"
    USAGE_UPDATE = "USAGE_UPDATE"
    TURN_COMPLETE = "TURN_COMPLETE"
    SESSION_IDLE = "SESSION_IDLE"
    ERROR = "ERROR"

def translate_event(sdk_event: Any, config: EventConfig) -> DomainEvent | None:
    """Config-driven SDK event translation."""
    sdk_type = sdk_event.type  # or similar
    
    if sdk_type in config.bridge_mappings:
        domain_type, block_type = config.bridge_mappings[sdk_type]
        return DomainEvent(type=domain_type, data=extract_data(sdk_event), block_type=block_type)
    elif sdk_type in config.consume:
        # Process internally
        return None
    else:
        # DROP
        return None
```

---

## Invariants

1. **MUST:** Accumulate all deltas into complete response
2. **MUST:** Capture tool calls (not execute them)
3. **MUST:** Use kernel types: TextBlock, ThinkingBlock, ToolCall, Usage
4. **MUST:** Use config for event classification
5. **MUST NOT:** Define custom content types (use kernel types only)

---

## Dependencies

```
streaming.py
├── imports: amplifier_core (ChatResponse, TextBlock, ThinkingBlock, ToolCall, Usage)
├── reads: config/events.yaml
├── exports: DomainEvent, DomainEventType, StreamingAccumulator, EventConfig
└── returns: ChatResponse
```

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Delta accumulation produces correct blocks |
| Streaming | Event sequence produces expected response |
| Timeout | Circuit breaker triggers at limits |
| Contract | All streaming-contract.md and event-vocabulary.md MUST clauses tested |
