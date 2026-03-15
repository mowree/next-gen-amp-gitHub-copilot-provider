# Module Spec: Tool Parsing

**Module:** `amplifier_module_provider_github_copilot/tool_parsing.py`
**Contract:** `contracts/provider-protocol.md` (parse_tool_calls method)
**Target Size:** ~90 lines

---

## Purpose

Extracts tool calls from SDK/ChatResponse and returns kernel ToolCall types. Pure function with no side effects except logging.

---

## Public API

```python
from amplifier_core import ToolCall

def parse_tool_calls(response: Any) -> list[ToolCall]:
    """
    Extract tool calls from response.
    
    Contract: provider-protocol.md
    
    - MUST return ToolCall with `arguments` field (not `input`)
    - MUST handle empty/missing tool_calls gracefully
    - MUST parse JSON string arguments if needed
    """
```

---

## Input Protocol

```python
class HasToolCalls(Protocol):
    """Protocol for objects that may contain tool calls."""
    
    @property
    def tool_calls(self) -> list[Any] | None: ...
```

Accepts any object with `tool_calls` attribute (ChatResponse, SDK response, etc.).

---

## Argument Handling

| Input | Output |
|-------|--------|
| `None` | `{}` (empty dict) |
| `{}` | `{}` + WARNING log |
| `{"key": "value"}` | `{"key": "value"}` |
| `'{"key": "value"}'` | `{"key": "value"}` (parsed) |
| `'invalid json'` | `ValueError` raised |

---

## Invariants

1. **MUST:** Return kernel ToolCall from `amplifier_core`
2. **MUST:** Use `arguments` field (not `input`)
3. **MUST:** Return empty list when no tool_calls
4. **MUST:** Parse JSON string arguments
5. **MUST:** Raise ValueError on invalid JSON

---

## Dependencies

```
tool_parsing.py
├── imports: amplifier_core.ToolCall
├── imports: json, logging
├── called by: provider.py (parse_tool_calls method)
└── enforces: provider-protocol.md contract
```

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Empty/None tool_calls returns [] |
| Unit | Dict arguments preserved |
| Unit | JSON string arguments parsed |
| Negative | Invalid JSON raises ValueError |
| Contract | provider-protocol:parse_tool_calls:MUST:1-4 |
