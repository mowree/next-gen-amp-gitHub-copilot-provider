# Contract: SDK Boundary (The Membrane)

## Version
- **Current:** 1.0
- **Module Reference:** src/amplifier_module_provider_github_copilot/sdk_adapter/
- **Status:** Non-Negotiable Constraint

---

## Overview

The SDK Adapter is **THE MEMBRANE** — the only place in the codebase where SDK imports are allowed. No SDK type crosses this boundary. Domain code never imports from SDK.

This contract ensures the provider remains testable, maintainable, and isolated from SDK changes.

---

## The Import Quarantine

### MUST Constraints

1. **MUST** confine ALL SDK imports to `sdk_adapter/` package
2. **MUST** have exactly ONE file (`_imports.py`) that imports from `github_copilot_sdk`
3. **MUST NOT** allow SDK imports in ANY other module
4. **MUST NOT** export SDK types from `sdk_adapter/__init__.py`
5. **MUST** fail at import time with a clear error if `github-copilot-sdk` is not installed (eager dependency check)

### Directory Structure

```
sdk_adapter/
├── __init__.py      # Exports ONLY domain types
├── _imports.py      # THE ONLY FILE with SDK imports
├── _types.py        # Domain type definitions
├── events.py        # SDK event → domain event translation
└── errors.py        # SDK error → domain error translation
```

---

## Type Translation Rules

### MUST Constraints

1. **MUST** translate SDK types to domain types at the boundary
2. **MUST** use decomposition, not wrapping
3. **MUST NOT** pass SDK types through the boundary
4. **MUST** use opaque handles (strings) instead of SDK object references

### Decomposition Pattern

**WRONG — Wrapping:**
```python
# ❌ SDK type leaks through wrapper
class SessionWrapper:
    def __init__(self, sdk_session: CopilotSession):
        self._session = sdk_session  # SDK type stored
```

**RIGHT — Decomposition:**
```python
# ✓ SDK type decomposed to domain primitives
SessionHandle = str  # Opaque UUID, not SDK reference

@dataclass
class DomainEvent:
    type: str
    data: dict[str, Any]  # Decomposed, not SDK object
```

---

## Domain Types

### SessionHandle

```python
# Opaque handle — UUID string, NOT SDK session reference
SessionHandle = str
```

- **MUST** be generated UUID, not SDK session ID
- **MUST NOT** be the actual SDK session object
- **MUST** map to SDK session via internal registry

### DomainEvent

```python
@dataclass
class DomainEvent:
    type: str  # "CONTENT_DELTA", "TOOL_CALL", etc.
    data: dict[str, Any]
```

- **MUST** be a pure Python dataclass
- **MUST NOT** contain SDK event objects
- **MUST** use primitive types and dicts

### SessionConfig

```python
@dataclass
class SessionConfig:
    model: str
    system_message: str | None = None
    tools: list[dict[str, Any]] | None = None
    reasoning_effort: str | None = None
```

- **MUST** use primitives (str, dict, list)
- **MUST NOT** use SDK config types

---

## Translation Functions

### Event Translation

```python
def translate_sdk_event(sdk_event: Any, config: EventConfig) -> DomainEvent | None:
    """
    Translate SDK event to domain event.
    
    - MUST classify per config (BRIDGE/CONSUME/DROP)
    - MUST return None for DROP events
    - MUST NOT expose SDK event internals
    """
```

### Error Translation

```python
def translate_sdk_error(exc: Exception, config: ErrorConfig) -> CopilotProviderError:
    """
    Translate SDK exception to domain exception.
    
    - MUST NOT raise (always returns)
    - MUST preserve original in .original attribute
    - MUST use config patterns (no hardcoded mappings)
    """
```

---

## Session Configuration Contract

The dict passed to `client.create_session()` MUST satisfy these constraints:

### MUST Constraints

1. **MUST** set `available_tools: []` to disable SDK built-in tools (F-045)
2. **MUST** use `system_message.mode: "replace"` when system_message is provided (F-044)
3. **MUST** set `on_permission_request` handler on every session (F-033)
4. **MUST** set `streaming: true` for event-based tool capture
5. **MUST** register `preToolUse` deny hook after session creation
6. **MUST NOT** include keys that are not in SDK's SessionConfig TypedDict

### Rationale

- **available_tools=[]**: SDK exposes bash/view/edit by default. These crash the Copilot CLI when called because they expect a different calling convention. Disabling them prevents the LLM from ever requesting them.
- **mode="replace"**: With "append", SDK injects "You are GitHub Copilot CLI..." before our system message. With "replace", our bundle persona takes precedence.
- **on_permission_request**: SDK v0.1.33+ requires this handler. We deny all permission requests as the first line of defense.
- **streaming=true**: Required for event-based tool capture. Non-streaming mode cannot capture tool calls.

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `sdk-boundary:Membrane:MUST:1` | All SDK imports in adapter only |
| `sdk-boundary:Membrane:MUST:2` | Only _imports.py has SDK imports |
| `sdk-boundary:Types:MUST:1` | No SDK types cross boundary |
| `sdk-boundary:Types:MUST:2` | Domain types are dataclasses/primitives |
| `sdk-boundary:Types:MUST:3` | SessionHandle is opaque string |
| `sdk-boundary:Translation:MUST:1` | Events translated to DomainEvent |
| `sdk-boundary:Translation:MUST:2` | Errors translated to domain exceptions |
| `sdk-boundary:Membrane:MUST:5` | Fail at import time if SDK not installed |
| `sdk-boundary:Config:MUST:1` | available_tools is empty list |
| `sdk-boundary:Config:MUST:2` | system_message mode is replace |
| `sdk-boundary:Config:MUST:3` | on_permission_request always set |
| `sdk-boundary:Config:MUST:4` | streaming is true |
| `sdk-boundary:Config:MUST:5` | deny hook registered post-creation |
| `sdk-boundary:Config:MUST:6` | no unknown keys in config |

---

## Why This Matters

1. **Testability** — Domain code testable without SDK installation
2. **Maintainability** — SDK changes isolated to adapter
3. **Clarity** — Clear boundary between "our code" and "SDK code"
4. **Safety** — SDK bugs can't leak through abstraction

---

## Verification

To verify this contract:

```bash
# Should find SDK imports ONLY in _imports.py
grep -r "from github_copilot_sdk" src/provider_github_copilot/
grep -r "import copilot" src/provider_github_copilot/
```

Expected: Only `sdk_adapter/_imports.py` matches.
