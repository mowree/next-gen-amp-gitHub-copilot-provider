# Contract: Streaming

## Version
- **Current:** 1.1 (v2.2 Kernel-Corrected)
- **Module Reference:** amplifier_module_provider_github_copilot/streaming.py
- **Kernel Types:** `amplifier_core.message_models` (Pydantic, NOT content_models dataclass)
- **Status:** Specification
- **Correction:** 2026-03-15 — Expert panel (core-expert) verified: ChatResponse.content uses message_models types

---

## Overview

This contract defines how streaming events are accumulated into a complete response. The streaming callback is provider-internal — the kernel protocol uses `**kwargs`, not a named callback parameter.

---

## Kernel Content Types

Use types from `amplifier_core.message_models` (Pydantic models, NOT content_models dataclasses):

```python
from amplifier_core import (
    TextBlock,
    ThinkingBlock,
    ToolCall,
)
```

> **IMPORTANT:** The kernel has TWO content type systems:
> - `content_models`: TextContent, ThinkingContent (dataclass) — for internal kernel use
> - `message_models`: TextBlock, ThinkingBlock (Pydantic) — for ChatResponse.content
>
> Providers MUST use message_models types because ChatResponse.content is typed as `list[TextBlock | ThinkingBlock | RedactedThinkingBlock | ToolCall]`.

### TextBlock (Pydantic)
```python
class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    text: str
```

### ThinkingBlock (Pydantic)
```python
class ThinkingBlock(BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str
```

### ToolCall (Pydantic)
```python
class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]
```

---

## Streaming Flow

```
SDK Event Stream
    │
    ├─→ Event Handler
    │   ├─→ BRIDGE: Translate → Accumulate → (internal callback)
    │   ├─→ CONSUME: Process internally
    │   └─→ DROP: Ignore
    │
    └─→ Final ChatResponse
        ├─→ content: [TextContent, ThinkingContent, ToolCallContent...]
        ├─→ tool_calls: [ToolCall...]
        └─→ usage: {token counts}
```

---

## Content Accumulation

### MUST Constraints

1. **MUST** accumulate text deltas in order
2. **MUST** use kernel content types (`TextContent`, `ThinkingContent`, `ToolCallContent`)
3. **MUST** maintain block boundaries
4. **MUST** handle out-of-order deltas gracefully
5. **MUST NOT** lose deltas during accumulation
6. **MUST NOT** define custom content types

### Accumulator State

```python
@dataclass
class StreamAccumulator:
    text_blocks: list[str]              # Accumulated text per block
    thinking_blocks: list[str]          # Accumulated thinking per block
    tool_calls: list[ToolCallContent]   # Captured tool calls
    usage: Usage | None                 # Token usage
    finish_reason: str                  # Final finish reason
```

---

## Internal Streaming (Provider Implementation)

The provider MAY implement internal streaming callbacks for real-time UI updates. This is NOT part of the kernel protocol.

```python
# Internal implementation detail — not protocol
async def _stream_completion(
    self,
    request: ChatRequest,
    on_event: Callable[[ContentBlock], None] | None = None,
) -> ChatResponse:
    """Provider-internal streaming implementation."""
```

---

## Tool Call Handling

### MUST Constraints

1. **MUST** capture tool calls from SDK events
2. **MUST NOT** execute tool calls (deny-destroy.md)
3. **MUST** return tool calls as `ToolCallContent` in response
4. **MUST** preserve tool call IDs for correlation

### Tool Call Accumulation

```python
def handle_tool_call_event(self, event: DomainEvent) -> None:
    tool_call = ToolCallContent(
        id=event.data["id"],
        name=event.data["name"],
        arguments=event.data["arguments"],
    )
    self.tool_calls.append(tool_call)
```

---

## Circuit Breaker

### MUST Constraints

1. **MUST** respect circuit breaker limits from config/retry.yaml
2. **MUST** track turn count during streaming
3. **MUST** raise `ProviderUnavailableError(retryable=False)` at hard limit
4. **SHOULD** warn at soft limit

### Config Values

```yaml
circuit_breaker:
  soft_turn_limit: 3    # Warn after 3 turns
  hard_turn_limit: 10   # Error after 10 turns
```

---

## Final Response Assembly

```python
from amplifier_core.content_models import TextContent, ThinkingContent, ToolCallContent

def assemble_response(accumulator: StreamAccumulator) -> ChatResponse:
    """
    Assemble final response from accumulated state.
    
    Uses kernel content types, not custom types.
    """
    content_blocks: list[ContentBlock] = []
    
    for text in accumulator.text_blocks:
        if text:
            content_blocks.append(TextContent(text=text))
    
    for thinking in accumulator.thinking_blocks:
        if thinking:
            content_blocks.append(ThinkingContent(text=thinking))
    
    for tc in accumulator.tool_calls:
        content_blocks.append(tc)  # Already ToolCallContent
    
    return ChatResponse(
        content=content_blocks,
        tool_calls=[...],  # Converted to ToolCall list
        usage=accumulator.usage,
        finish_reason=accumulator.finish_reason,
    )
```

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `streaming:ContentTypes:MUST:1` | Uses kernel content types |
| `streaming:Accumulation:MUST:1` | Deltas accumulated in order |
| `streaming:Accumulation:MUST:2` | Block boundaries maintained |
| `streaming:ToolCapture:MUST:1` | Tool calls captured |
| `streaming:ToolCapture:MUST:2` | Tool calls in final response |
| `streaming:CircuitBreaker:MUST:1` | Respects hard limit |
| `streaming:Response:MUST:1` | Final response uses kernel types |

---

## SDK Response Extraction (F-043)

### MUST Constraints

1. **MUST** extract `.content` from SDK `Data` objects — NOT `str(Data(...))`
2. **MUST** unwrap `.data` wrapper first before checking `.content`
3. **MUST** handle dict responses for backward compatibility
4. **MUST** return empty string for None responses

See `contracts/sdk-response.md` for full extraction specification.

---

## Implementation Checklist

- [ ] Import content types from `amplifier_core.content_models`
- [ ] StreamAccumulator tracks all state
- [ ] Text deltas accumulated per block
- [ ] Thinking deltas accumulated per block
- [ ] Tool calls captured as ToolCallContent
- [ ] Circuit breaker tracks turn count
- [ ] Final response uses kernel content types
- [ ] No custom content types defined
- [ ] SDK response extraction uses `extract_response_content()` (F-043)
