# Contract: Provider Protocol

## Version
- **Current:** 1.0 (v2.1 Kernel-Validated)
- **Module Reference:** amplifier_module_provider_github_copilot/provider.py
- **Amplifier Contract:** amplifier-core PROVIDER_CONTRACT.md
- **Status:** Specification

---

## Overview

This contract defines the **4 methods + 1 property** Provider Protocol that our provider MUST implement to integrate with Amplifier's orchestrator. The provider is a thin orchestrator that delegates to specialized modules.

---

## The Protocol (4 Methods + 1 Property)

### 1. name (property)

```python
@property
def name(self) -> str: ...
```

**Behavioral Requirements:**
- **MUST** return `"github-copilot"` (exact string)
- **MUST** be a property, not a method call
- **MUST NOT** vary based on configuration

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:name:MUST:1` | Returns "github-copilot" |
| `provider-protocol:name:MUST:2` | Is a property |

---

### 2. get_info()

```python
def get_info(self) -> ProviderInfo: ...
```

**Behavioral Requirements:**
- **MUST** return `ProviderInfo` with accurate metadata
- **MUST** include `defaults.context_window` for budget calculation
- **SHOULD** cache model info to avoid repeated API calls
- **MAY** include additional provider-specific metadata

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:get_info:MUST:1` | Returns valid ProviderInfo |
| `provider-protocol:get_info:MUST:2` | Includes context_window |

---

### 3. list_models()

```python
async def list_models(self) -> list[ModelInfo]: ...
```

**Behavioral Requirements:**
- **MUST** return all available models from SDK
- **MUST** include `context_window` and `max_output_tokens` per model
- **SHOULD** cache results for session lifetime
- **MUST** translate SDK model info to `ModelInfo` domain type

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:list_models:MUST:1` | Returns model list |
| `provider-protocol:list_models:MUST:2` | Includes context_window |

---

### 4. complete()

```python
async def complete(
    self,
    request: ChatRequest,
    **kwargs,
) -> ChatResponse: ...
```

**Note:** The kernel passes `**kwargs` for extensibility. Internal streaming callbacks are provider-internal, not part of the protocol.

**Behavioral Requirements:**
- **MUST** create ephemeral session per call (per deny-destroy.md)
- **MUST** capture tool calls (NOT execute them)
- **MUST** destroy session after first turn completes
- **MUST NOT** maintain state between calls
- **MUST** translate SDK errors to kernel errors (per error-hierarchy.md)

**Session Lifecycle:**
```
complete() called
    │
    ├─→ Create ephemeral session (with deny hook)
    │
    ├─→ Send prompt, capture response
    │
    ├─→ Capture tool calls (not execute)
    │
    └─→ Destroy session, return response
```

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:complete:MUST:1` | Creates ephemeral session |
| `provider-protocol:complete:MUST:2` | Captures tool calls |
| `provider-protocol:complete:MUST:3` | Destroys session after turn |
| `provider-protocol:complete:MUST:4` | No state between calls |

---

### 5. parse_tool_calls()

```python
def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...
```

**Note:** Returns `list[ToolCall]`, NOT `list[ToolCallBlock]`. `ToolCall` has `arguments`, not `input`.

**Behavioral Requirements:**
- **MUST** extract tool calls from response
- **MUST** return empty list if no tool calls
- **MUST NOT** execute tools (orchestrator responsibility)
- **MUST** preserve tool call IDs for result correlation

**ToolCall Structure:**
```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]  # NOT "input"
```

**Test Anchors:**
| Anchor | Clause |
|--------|--------|
| `provider-protocol:parse_tool_calls:MUST:1` | Extracts tool calls |
| `provider-protocol:parse_tool_calls:MUST:2` | Returns empty list when none |
| `provider-protocol:parse_tool_calls:MUST:3` | Preserves tool call IDs |
| `provider-protocol:parse_tool_calls:MUST:4` | Uses arguments, not input |

---

## Cross-References

- **deny-destroy.md** — Session ephemerality and deny hook requirements
- **error-hierarchy.md** — Exception translation requirements (kernel types)
- **amplifier-core PROVIDER_CONTRACT.md** — Kernel interface specification

---

## Implementation Checklist

- [ ] `name` property returns "github-copilot"
- [ ] `get_info()` returns valid ProviderInfo
- [ ] `list_models()` queries SDK and caches
- [ ] `complete()` accepts `**kwargs` (not named callback)
- [ ] `complete()` creates ephemeral session with deny hook
- [ ] `complete()` captures and returns tool calls
- [ ] `parse_tool_calls()` returns `list[ToolCall]`
- [ ] `parse_tool_calls()` uses `arguments` field
- [ ] All SDK errors translated to kernel types
