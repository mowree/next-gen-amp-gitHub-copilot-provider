# F-001: SDK Adapter Skeleton

## 1. Overview

**Module:** sdk_adapter
**Priority:** P0
**Depends on:** none

Create the SDK adapter layer - the membrane where all SDK imports live. This is the foundational module that isolates SDK dependencies from domain code. No SDK type crosses this boundary.

## 2. Requirements

### Interfaces

```python
# src/amplifier_module_provider_github_copilot/sdk_adapter/__init__.py
from .types import DomainEvent, SessionConfig, SDKSession
from .driver import create_session, destroy_session

# src/amplifier_module_provider_github_copilot/sdk_adapter/types.py
from dataclasses import dataclass
from typing import Any

@dataclass
class SessionConfig:
    model: str
    system_prompt: str | None = None
    max_tokens: int | None = None

@dataclass  
class DomainEvent:
    type: str  # "text_delta", "tool_call", "thinking", etc.
    data: dict[str, Any]

# src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py
async def create_session(config: SessionConfig, deny_hook: Callable) -> SDKSession: ...
async def destroy_session(session: SDKSession) -> None: ...
```

### Behavior

- All SDK imports (`github_copilot_sdk.*`) MUST live inside `sdk_adapter/`
- Domain code (provider.py, completion.py, etc.) MUST NOT import from SDK directly
- The adapter exposes only domain types (DomainEvent, SessionConfig, SDKSession)
- SDKSession is an opaque wrapper - domain code never accesses SDK internals

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `sdk_adapter/` directory exists with __init__.py, types.py, driver.py | File existence check |
| AC-2 | No SDK imports outside of sdk_adapter/ | grep -r "from github_copilot_sdk" src/ shows only sdk_adapter/ |
| AC-3 | DomainEvent dataclass defined with type and data fields | Unit test |
| AC-4 | SessionConfig dataclass defined with model, system_prompt, max_tokens | Unit test |
| AC-5 | create_session and destroy_session stubs exist | Import test |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| SDK not installed | Import error with clear message about missing dependency |
| Invalid model name | Raise NotFoundError from kernel types |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `src/amplifier_module_provider_github_copilot/sdk_adapter/__init__.py` | Create | Re-exports domain types |
| `src/amplifier_module_provider_github_copilot/sdk_adapter/types.py` | Create | DomainEvent, SessionConfig, SDKSession |
| `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py` | Create | create_session, destroy_session stubs |
| `tests/test_sdk_adapter.py` | Create | Tests for adapter types and imports |

## 6. Dependencies

- `github-copilot-sdk>=0.1.32,<0.2.0` (already in pyproject.toml)

## 7. Notes

- This is a skeleton - full SDK integration comes in later features
- Focus on establishing the boundary, not full functionality
- Reference: contracts/sdk-boundary.md
