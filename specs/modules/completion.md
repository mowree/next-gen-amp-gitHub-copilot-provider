# Module Spec: Completion

**Module:** `src/provider_github_copilot/completion.py`
**Contract:** `contracts/streaming-contract.md`
**Target Size:** ~150 lines

---

## Purpose

Manages the LLM call lifecycle — sending requests, handling streaming, accumulating deltas, and producing the final ChatResponse.

---

## Public API

```python
async def execute_completion(
    session: SessionHandle,
    request: ChatRequest,
    *,
    streaming: bool = True,
    on_content: Callable[[ContentDelta], None] | None = None,
) -> ChatResponse:
    """
    Execute completion and return accumulated response.
    
    Contract: streaming-contract.md
    
    - MUST accumulate deltas into complete response
    - MUST emit content deltas via on_content callback
    - MUST capture tool calls from events (not execute them)
    - MUST handle timeout via circuit breaker config
    """
```

---

## Streaming Flow

```
send(prompt)
    │
    ▼
┌─────────────────────────────────────────┐
│           Event Stream                   │
│  ┌─────────────────────────────────────┐│
│  │ text_delta → accumulate text        ││
│  │ thinking_delta → accumulate thinking ││
│  │ tool_use_complete → capture tool    ││
│  │ usage_update → capture usage        ││
│  │ message_complete → mark done        ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
    │
    ▼
ChatResponse {
    content: [TextBlock, ThinkingBlock, ToolCallBlock, ...],
    tool_calls: [...],
    usage: {...},
    finish_reason: "end_turn" | "tool_use"
}
```

---

## Event Handling (Config-Driven)

Events are classified per `config/events.yaml`:

| Classification | Action |
|----------------|--------|
| **BRIDGE** | Translate to domain event, emit to callback |
| **CONSUME** | Process internally (e.g., tool_use_start) |
| **DROP** | Ignore (e.g., heartbeat, debug_*) |

```python
# Uses streaming.py for event handling
handler = create_event_handler(config)
async for event in session.events():
    domain_event = handler.process(event)
    if domain_event and on_content:
        on_content(domain_event.to_content_delta())
```

---

## Circuit Breaker

From `config/retry.yaml`:

```yaml
circuit_breaker:
  soft_turn_limit: 3    # Warn at 3 turns
  hard_turn_limit: 10   # Error at 10 turns
  timeout_buffer_seconds: 5.0
```

The Deny + Destroy pattern prevents the SDK's retry loop, so the circuit breaker protects against other runaway conditions.

---

## Invariants

1. **MUST:** Accumulate all deltas into complete response
2. **MUST:** Capture tool calls (not execute them)
3. **MUST:** Emit content deltas via callback when provided
4. **MUST:** Respect circuit breaker limits
5. **MUST:** Use config for event classification

---

## Dependencies

```
completion.py
├── imports: streaming, sdk_adapter, _types
├── reads: config/events.yaml, config/retry.yaml
├── uses: SessionHandle (from session_factory)
└── returns: ChatResponse
```

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Delta accumulation produces correct blocks |
| Streaming | Event sequence produces expected response |
| Timeout | Circuit breaker triggers at limits |
| Contract | All streaming-contract.md MUST clauses tested |
