# F-007: Completion Lifecycle

**Status**: Ready  
**Module**: completion.py  
**Contract**: streaming-contract.md, deny-destroy.md  
**Depends On**: F-003 (Session Factory), F-006 (Streaming Handler), F-002 (Error Translation)

## Overview

Full LLM call lifecycle: create ephemeral session, stream response events, accumulate to final response, destroy session. This is the core orchestration that ties together session management, streaming, and error handling.

## Acceptance Criteria

### AC-001: Session Lifecycle
- MUST create ephemeral session via session_factory
- MUST destroy session after completion (success or error)
- MUST use try/finally to ensure cleanup

### AC-002: Streaming Integration
- MUST iterate over SDK events from session
- MUST translate each event via translate_event()
- MUST accumulate domain events via StreamingAccumulator
- MUST yield domain events to caller (async generator pattern)

### AC-003: Error Handling
- MUST catch all SDK exceptions during streaming
- MUST translate SDK errors via translate_sdk_error()
- MUST ensure session destroyed even on error
- MUST propagate translated errors to caller

### AC-004: Response Construction
- MUST return AccumulatedResponse when stream completes
- MUST include text_content, thinking_content, tool_calls, usage
- MUST set finish_reason from TURN_COMPLETE event

### AC-005: Async Generator Interface
```python
async def complete(
    request: CompletionRequest,
    *,
    config: CompletionConfig | None = None,
) -> AsyncIterator[DomainEvent]:
    """
    Execute completion lifecycle.
    
    Yields:
        DomainEvent for each bridged SDK event.
        
    Returns:
        Final AccumulatedResponse via .asend() or separate method.
    """
```

## Interface

### Input Types

```python
@dataclass
class CompletionRequest:
    """Request for LLM completion."""
    prompt: str
    model: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    max_tokens: int | None = None
    temperature: float | None = None

@dataclass  
class CompletionConfig:
    """Configuration for completion lifecycle."""
    session_config: SessionConfig | None = None
    error_config: ErrorConfig | None = None
    event_config: EventConfig | None = None
```

### Output Types

Uses existing types from streaming.py:
- `DomainEvent` - yielded during streaming
- `AccumulatedResponse` - final result

## Implementation Notes

1. **Pattern**: Async generator that yields events and can return final result
2. **Session scope**: Create at start, destroy in finally block
3. **Config loading**: Load configs once at module level or accept injected
4. **Error boundary**: All SDK errors translated, none leak to caller

## Test Cases

1. Happy path: complete() yields events, accumulates to final response
2. Error during streaming: session destroyed, error translated and raised
3. Empty response: accumulator handles zero events gracefully
4. Tool calls in response: accumulated correctly
5. Thinking content: separated from text content
6. Session cleanup: verified destroyed even on exception

## File Structure

```
src/amplifier_module_provider_github_copilot/
└── completion.py (~150 lines)
```

## Dependencies

- session_factory.py: create_ephemeral_session, destroy_session
- streaming.py: translate_event, StreamingAccumulator, DomainEvent
- error_translation.py: translate_sdk_error, load_error_config
- sdk_adapter/types.py: SessionConfig
