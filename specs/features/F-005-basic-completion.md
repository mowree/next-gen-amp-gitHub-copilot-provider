# Feature Spec: F-005 Basic Completion Lifecycle

**Feature ID:** F-005
**Module:** `src/provider_github_copilot/completion.py`
**Contract:** `contracts/provider-protocol.md`
**Priority:** P0 (Foundation)
**Estimated Size:** ~100 lines (non-streaming subset)

---

## Summary

Implement the basic (non-streaming) completion lifecycle. This establishes the request → session → response flow without streaming complexity.

---

## Acceptance Criteria

1. **Completion module created:** `completion.py`
   - `execute_completion()` function
   - Non-streaming mode only (streaming in F-009)

2. **Request → Response flow:**
   - Receives ChatRequest
   - Uses session factory to create ephemeral session
   - Sends prompt to SDK
   - Captures response (text and tool calls)
   - Returns ChatResponse

3. **Tool call capture:**
   - Tool calls captured from response
   - NOT executed (per deny-destroy.md)
   - Returned in ChatResponse.tool_calls

4. **Error handling:**
   - SDK errors translated to domain exceptions
   - Uses error_translation module

---

## Interfaces

```python
# src/provider_github_copilot/completion.py

from typing import Any
from .sdk_adapter import SessionHandle, SessionConfig, DomainEvent
from ._types import ChatRequest, ChatResponse

async def execute_completion(
    client: Any,  # CopilotClient
    request: ChatRequest,
    config: SessionConfig,
) -> ChatResponse:
    """
    Execute a completion request (non-streaming).
    
    Contract: provider-protocol.md
    
    - MUST use ephemeral session (via session_factory)
    - MUST capture tool calls (not execute them)
    - MUST translate SDK errors to domain exceptions
    
    Args:
        client: The Copilot SDK client
        request: Chat request with messages and tools
        config: Session configuration
        
    Returns:
        ChatResponse with content and tool_calls
    """
    ...
```

---

## Request → Response Flow

```
ChatRequest
    │
    ▼
┌─────────────────────────────┐
│ create_ephemeral_session()  │  ← F-004
│   with deny hook installed  │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Convert messages to prompt  │
│ Extract system message      │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ session.send(prompt)        │
│ await response              │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│ Convert SDK response to     │
│ ChatResponse                │
│ - Extract text content      │
│ - Extract tool calls        │
│ - Extract usage             │
└─────────────┬───────────────┘
              │
              ▼
ChatResponse
```

---

## ChatRequest / ChatResponse Types

```python
# src/provider_github_copilot/_types.py

from dataclasses import dataclass, field
from typing import Any

@dataclass
class ChatRequest:
    """Request for LLM completion."""
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None

@dataclass
class ToolCall:
    """A tool call from the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class ContentBlock:
    """Content block in response."""
    type: str  # "text", "thinking", "tool_call"
    text: str | None = None
    tool_call: ToolCall | None = None

@dataclass
class Usage:
    """Token usage."""
    input_tokens: int
    output_tokens: int
    total_tokens: int

@dataclass
class ChatResponse:
    """Response from LLM completion."""
    content: list[ContentBlock] = field(default_factory=list)
    tool_calls: list[ToolCall] | None = None
    usage: Usage | None = None
    finish_reason: str = "end_turn"
```

---

## Implementation Notes

### Message Conversion

```python
def convert_messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    """Convert Amplifier messages to SDK prompt format."""
    # Extract and format messages
    # Handle multi-turn conversations
    ...

def extract_system_message(messages: list[dict[str, Any]]) -> str | None:
    """Extract system message from message list."""
    for msg in messages:
        if msg.get("role") == "system":
            return msg.get("content", "")
    return None
```

### Response Conversion

```python
def convert_sdk_response(sdk_response: Any) -> ChatResponse:
    """Convert SDK response to domain ChatResponse."""
    content_blocks = []
    tool_calls = []
    
    # Extract text content
    if sdk_response.text:
        content_blocks.append(ContentBlock(type="text", text=sdk_response.text))
    
    # Extract tool calls (captured, not executed)
    for tc in sdk_response.tool_calls or []:
        tool_call = ToolCall(id=tc.id, name=tc.name, arguments=tc.arguments)
        tool_calls.append(tool_call)
        content_blocks.append(ContentBlock(type="tool_call", tool_call=tool_call))
    
    return ChatResponse(
        content=content_blocks,
        tool_calls=tool_calls if tool_calls else None,
        usage=...,
        finish_reason=...,
    )
```

---

## Test Cases

```python
# tests/test_completion.py

import pytest
from provider_github_copilot.completion import execute_completion
from provider_github_copilot._types import ChatRequest, ChatResponse


@pytest.mark.asyncio
@pytest.mark.contract("provider-protocol:complete:MUST:2")
async def test_tool_calls_captured_not_executed(mock_client):
    """Tool calls are captured and returned, not executed."""
    request = ChatRequest(
        messages=[{"role": "user", "content": "Read a file"}],
        tools=[{"name": "read_file", "description": "..."}],
    )
    
    # Mock SDK returns tool_call
    mock_client.configure_response(tool_calls=[
        {"id": "tc1", "name": "read_file", "arguments": {"path": "test.py"}}
    ])
    
    response = await execute_completion(mock_client, request, config)
    
    assert response.tool_calls is not None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "read_file"


@pytest.mark.asyncio
async def test_text_response_extracted(mock_client):
    """Text content is extracted from SDK response."""
    request = ChatRequest(
        messages=[{"role": "user", "content": "Hello"}],
    )
    
    mock_client.configure_response(text="Hello! How can I help?")
    
    response = await execute_completion(mock_client, request, config)
    
    assert len(response.content) == 1
    assert response.content[0].type == "text"
    assert "Hello" in response.content[0].text
```

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `src/provider_github_copilot/completion.py` | Create | ~100 |
| `src/provider_github_copilot/_types.py` | Create | ~60 |
| `tests/test_completion.py` | Create | ~80 |
| `tests/conftest.py` | Update | ~30 (mock client fixture) |

---

## Dependencies

- F-001 (SDK Adapter skeleton) — for domain types
- F-003 (Error hierarchy) — for exception translation
- F-004 (Session factory) — for ephemeral sessions

---

## Contract References

- `provider-protocol:complete:MUST:1` — Creates ephemeral session
- `provider-protocol:complete:MUST:2` — Captures tool calls
- `deny-destroy:NoExecution:MUST:2` — Tool requests returned to orchestrator
