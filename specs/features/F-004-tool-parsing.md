# Feature Spec: F-004 Tool Parsing Module

**Feature ID:** F-004
**Module:** `src/amplifier_module_provider_github_copilot/tool_parsing.py`
**Contract:** `contracts/provider-protocol.md`
**Priority:** P0 (Foundation)
**Estimated Size:** ~120 lines

---

## Summary

Extract tool calls from SDK response and return as kernel ToolCall types. This is the `parse_tool_calls()` method of the Provider Protocol (4 methods + 1 property).

---

## Acceptance Criteria

1. **Tool parsing module created:** `tool_parsing.py`
   - `parse_tool_calls(response: ChatResponse) -> list[ToolCall]`
   - Extract tool calls from response content blocks

2. **ToolCall type matches kernel contract:**
   - `id: str` - unique identifier
   - `name: str` - tool name
   - `arguments: dict[str, Any]` - parsed arguments (NOT `input`)

3. **Handles edge cases:**
   - Empty response → empty list
   - No tool calls → empty list
   - Multiple tool calls → all returned
   - Invalid JSON arguments → raise appropriate error

4. **Pure function (no side effects)**

---

## Interfaces

```python
# src/amplifier_module_provider_github_copilot/tool_parsing.py

from typing import Any
from dataclasses import dataclass

@dataclass
class ToolCall:
    """
    Tool call extracted from LLM response.
    
    Contract: provider-protocol.md (E3 correction)
    
    NOTE: Uses `arguments` not `input` per kernel contract.
    """
    id: str
    name: str
    arguments: dict[str, Any]


def parse_tool_calls(response: "ChatResponse") -> list[ToolCall]:
    """
    Extract tool calls from response.
    
    Contract: provider-protocol.md
    
    - MUST return ToolCall with `arguments` field (not `input`)
    - MUST handle empty/missing tool_calls gracefully
    - MUST parse JSON string arguments if needed
    
    Args:
        response: ChatResponse from completion
        
    Returns:
        List of ToolCall objects (may be empty)
        
    Raises:
        ValueError: If tool call has invalid JSON arguments
    """
    ...
```

---

## Implementation Notes

### From SDK Response

```python
def parse_tool_calls(response: ChatResponse) -> list[ToolCall]:
    """Extract tool calls from ChatResponse."""
    if not response.tool_calls:
        return []
    
    result = []
    for tc in response.tool_calls:
        # Handle both dict and string arguments
        args = tc.arguments
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in tool call arguments: {e}")
        
        result.append(ToolCall(
            id=tc.id,
            name=tc.name,
            arguments=args,
        ))
    
    return result
```

### Content Block Extraction

If tool calls are embedded in content blocks:

```python
def extract_tool_calls_from_content(content: list[ContentBlock]) -> list[ToolCall]:
    """Extract tool calls from content blocks."""
    return [
        block.tool_call
        for block in content
        if block.type == "tool_call" and block.tool_call is not None
    ]
```

---

## Test Cases

```python
# tests/test_tool_parsing.py

import pytest
from amplifier_module_provider_github_copilot.tool_parsing import (
    parse_tool_calls,
    ToolCall,
)


def test_empty_response_returns_empty_list():
    """No tool_calls in response → empty list."""
    response = ChatResponse(content=[], tool_calls=None)
    result = parse_tool_calls(response)
    assert result == []


def test_single_tool_call_parsed():
    """Single tool call extracted correctly."""
    response = ChatResponse(
        content=[],
        tool_calls=[
            MockToolCall(id="tc1", name="read_file", arguments={"path": "test.py"})
        ],
    )
    result = parse_tool_calls(response)
    assert len(result) == 1
    assert result[0].name == "read_file"
    assert result[0].arguments == {"path": "test.py"}


def test_multiple_tool_calls_parsed():
    """Multiple tool calls all extracted."""
    response = ChatResponse(
        content=[],
        tool_calls=[
            MockToolCall(id="tc1", name="read_file", arguments={"path": "a.py"}),
            MockToolCall(id="tc2", name="write_file", arguments={"path": "b.py"}),
        ],
    )
    result = parse_tool_calls(response)
    assert len(result) == 2


def test_string_arguments_parsed_as_json():
    """String arguments are JSON-parsed."""
    response = ChatResponse(
        content=[],
        tool_calls=[
            MockToolCall(id="tc1", name="bash", arguments='{"command": "ls -la"}')
        ],
    )
    result = parse_tool_calls(response)
    assert result[0].arguments == {"command": "ls -la"}


def test_invalid_json_raises_value_error():
    """Invalid JSON arguments raise ValueError."""
    response = ChatResponse(
        content=[],
        tool_calls=[
            MockToolCall(id="tc1", name="bash", arguments='{invalid json}')
        ],
    )
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_tool_calls(response)


def test_tool_call_has_arguments_not_input():
    """ToolCall uses 'arguments' field per kernel contract (E3)."""
    tc = ToolCall(id="1", name="test", arguments={"key": "value"})
    assert hasattr(tc, "arguments")
    assert not hasattr(tc, "input")
```

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `src/amplifier_module_provider_github_copilot/tool_parsing.py` | Create | ~80 |
| `tests/test_tool_parsing.py` | Create | ~100 |

---

## Dependencies

- F-001 (SDK Adapter skeleton) - for ChatResponse, ContentBlock types

---

## Contract References

- `provider-protocol:parse_tool_calls:MUST:1` — Returns list[ToolCall]
- `provider-protocol:ToolCall:MUST:1` — Uses `arguments` not `input` (Errata E3)
