# Module Spec: SDK Adapter

**Module:** `src/provider_github_copilot/sdk_adapter/`
**Contract:** `contracts/sdk-boundary.md`
**Target Size:** ~200 lines total

---

## Purpose

The SDK Adapter is **THE MEMBRANE** — the only place in the codebase where SDK imports are allowed. It translates between SDK types and domain types.

---

## Files

| File | Lines | Responsibility |
|------|-------|----------------|
| `__init__.py` | ~10 | Public exports |
| `types.py` | ~80 | SDK → domain type translation |
| `events.py` | ~60 | Config-driven event translation |
| `errors.py` | ~50 | Config-driven error translation |

---

## Public API

```python
# sdk_adapter/__init__.py

from .types import SessionHandle, DomainEvent, SessionConfig
from .events import translate_sdk_event
from .errors import translate_sdk_error

__all__ = [
    "SessionHandle",
    "DomainEvent", 
    "SessionConfig",
    "translate_sdk_event",
    "translate_sdk_error",
]
```

---

## Key Types

### SessionHandle
```python
# Opaque handle — UUID string, NOT an SDK session reference
SessionHandle = str
```

### DomainEvent
```python
@dataclass
class DomainEvent:
    type: str  # CONTENT_DELTA, TOOL_CALL, USAGE_UPDATE, etc.
    data: dict[str, Any]
```

### SessionConfig
```python
@dataclass
class SessionConfig:
    model: str
    system_message: str | None
    tools: list[ToolDefinition] | None
    reasoning_effort: str | None  # "low", "medium", "high"
```

---

## Translation Strategy

**Decompose, don't wrap:**
- A `copilot.Message` becomes a `list[ContentBlock]`, not a `MessageWrapper(sdk_message)`
- SDK sessions become `SessionHandle` (UUID string), not SDK references

**Config-driven mappings:**
- `events.py` reads `config/events.yaml` for event classification
- `errors.py` reads `config/errors.yaml` for error mapping

---

## Invariants

1. **MUST NOT:** Export any SDK types
2. **MUST NOT:** Allow SDK imports outside this package
3. **MUST:** All translation functions are pure (no side effects)
4. **MUST:** Use config for all mappings (no hardcoded tables)

---

## Dependencies

```
sdk_adapter/
├── imports: @github/copilot-sdk (THE ONLY PLACE)
├── reads: config/errors.yaml, config/events.yaml
└── exports: Domain types only
```

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Pure function tests for each translator |
| Property | Hypothesis tests: all valid SDK types map to domain types |
| Config | Verify config mappings produce correct outputs |
| Contract | Each MUST clause in sdk-boundary.md has a test |
