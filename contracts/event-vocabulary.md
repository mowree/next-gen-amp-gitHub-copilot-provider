# Contract: Event Vocabulary

## Version
- **Current:** 1.1 (Path-Corrected)
- **Module Reference:** amplifier_module_provider_github_copilot/streaming.py
- **Correction:** 2026-03-15 — Removed erroneous `src/` prefix
- **Config:** config/events.yaml
- **Status:** Specification

---

## Overview

This contract defines the 6 stable domain events and how SDK events are classified into BRIDGE, CONSUME, or DROP categories. Event classification is config-driven.

---

## The Six Domain Events

| Event | Description | Source |
|-------|-------------|--------|
| `CONTENT_DELTA` | Text chunk from assistant | SDK assistant.message_delta |
| `THINKING_DELTA` | Reasoning chunk (extended thinking) | SDK assistant.reasoning_delta |
| `TOOL_CALL` | Tool invocation request | SDK tool.call (captured, not executed) |
| `TOOL_RESULT` | Tool execution result | Amplifier orchestrator (not SDK) |
| `USAGE_UPDATE` | Token usage statistics | SDK session.usage |
| `TURN_COMPLETE` | Assistant turn finished | SDK session.idle |

---

## Event Classification

### BRIDGE Events
Events translated to domain events and passed to Amplifier.

| SDK Event | Domain Event | Notes |
|-----------|--------------|-------|
| `assistant.message_delta` | `CONTENT_DELTA` | Text streaming |
| `assistant.reasoning_delta` | `THINKING_DELTA` | Reasoning streaming |
| `assistant.message` | `TURN_COMPLETE` | Final message |
| `session.idle` | `TURN_COMPLETE` | Turn finished |
| `session.usage` | `USAGE_UPDATE` | Token counts |

### CONSUME Events
Events processed internally but not forwarded.

| SDK Event | Action | Notes |
|-----------|--------|-------|
| `tool.call` | Capture tool request | Tool calls accumulated |
| `tool.result` | Internal state update | Not forwarded |
| `session.start` | Internal state update | Session lifecycle |
| `session.resume` | Internal state update | Session lifecycle |

### DROP Events
Events ignored entirely.

| SDK Event | Reason |
|-----------|--------|
| `debug.*` | Development only |
| `heartbeat` | Connection keepalive |
| `session.compaction.*` | Internal optimization |

---

## Domain Event Structure

```python
@dataclass
class DomainEvent:
    type: str  # One of the 6 domain events
    data: dict[str, Any]
```

### CONTENT_DELTA

```python
DomainEvent(
    type="CONTENT_DELTA",
    data={
        "text": "partial text...",
        "index": 0,  # Block index
    }
)
```

### THINKING_DELTA

```python
DomainEvent(
    type="THINKING_DELTA",
    data={
        "text": "reasoning text...",
        "index": 0,
    }
)
```

### TOOL_CALL

```python
DomainEvent(
    type="TOOL_CALL",
    data={
        "id": "call_123",
        "name": "read_file",
        "arguments": {"path": "file.py"},
    }
)
```

### USAGE_UPDATE

```python
DomainEvent(
    type="USAGE_UPDATE",
    data={
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
    }
)
```

### TURN_COMPLETE

```python
DomainEvent(
    type="TURN_COMPLETE",
    data={
        "finish_reason": "end_turn",  # or "tool_use"
        "message_id": "msg_123",
    }
)
```

---

## Finish Reason Mapping

| SDK Reason | Domain Reason |
|------------|---------------|
| `end_turn` | `STOP` |
| `stop` | `STOP` |
| `tool_use` | `TOOL_USE` |
| `max_tokens` | `LENGTH` |
| `content_filter` | `CONTENT_FILTER` |
| (default) | `ERROR` |

---

## Config Schema (events.yaml)

```yaml
version: "1.0"

event_classifications:
  bridge:
    - sdk_event: "assistant.message_delta"
      domain_event: "CONTENT_DELTA"
      extract: ["text", "index"]
    
    - sdk_event: "assistant.reasoning_delta"
      domain_event: "THINKING_DELTA"
      extract: ["text", "index"]
    
    - sdk_event: "assistant.message"
      domain_event: "TURN_COMPLETE"
      extract: ["finish_reason", "message_id"]
    
    - sdk_event: "session.idle"
      domain_event: "TURN_COMPLETE"
      extract: ["finish_reason"]
    
    - sdk_event: "session.usage"
      domain_event: "USAGE_UPDATE"
      extract: ["input_tokens", "output_tokens", "total_tokens"]
  
  consume:
    - "tool.call"
    - "tool.result"
    - "session.start"
    - "session.resume"
  
  drop:
    - "debug.*"
    - "heartbeat"
    - "session.compaction.*"

finish_reason_map:
  end_turn: STOP
  stop: STOP
  tool_use: TOOL_USE
  max_tokens: LENGTH
  content_filter: CONTENT_FILTER
  _default: ERROR
```

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `event-vocabulary:Events:MUST:1` | 6 domain events defined |
| `event-vocabulary:Bridge:MUST:1` | BRIDGE events translated |
| `event-vocabulary:Bridge:MUST:2` | Uses config classification |
| `event-vocabulary:Consume:MUST:1` | CONSUME events processed internally |
| `event-vocabulary:Drop:MUST:1` | DROP events ignored |
| `event-vocabulary:FinishReason:MUST:1` | SDK reasons mapped correctly |

---

## Implementation Checklist

- [ ] 6 domain events defined
- [ ] Config file has all classifications
- [ ] BRIDGE events produce DomainEvent
- [ ] CONSUME events update internal state
- [ ] DROP events return None
- [ ] Finish reason mapping works
