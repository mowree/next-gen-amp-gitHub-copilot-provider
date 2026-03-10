# F-024: Code Quality Improvements

**Priority**: MEDIUM
**Source**: python-dev, code-intel, code-navigator
**Estimated Lines**: ~60 changes

## Objective

Address code quality issues identified by the expert panel.

## Acceptance Criteria

### AC-1: Fix complete() Return Type

**Problem**: Return type is `AsyncIterator[DomainEvent]` but should be `AsyncGenerator[DomainEvent, None]`.

**Fix**:
```python
async def complete(...) -> AsyncGenerator[DomainEvent, None]:
```

### AC-2: Fix _make_error_class Return Type

**Problem**: Returns `type` but should return `type[LLMError]`.

**Note**: This is obsoleted by F-020 AC-5 (importing kernel types). Mark as dependent/skip.

### AC-3: Move Inline Imports to Module Level

**Problem**: `Path`, `ProviderUnavailableError` imported inside functions.

**Fix**: Move to top of file:
```python
from pathlib import Path
from .error_translation import (
    ErrorConfig,
    ProviderUnavailableError,  # Add this
    load_error_config,
    translate_sdk_error,
)
```

### AC-4: Replace lambda Default Factories

**Problem**: `field(default_factory=lambda: [])` should be `field(default_factory=list)`.

**Fix** in `streaming.py`:
```python
data: dict[str, Any] = field(default_factory=dict)
tool_calls: list[dict[str, Any]] = field(default_factory=list)
```

### AC-5: Remove Unnecessary Helper Functions

**Problem**: `_empty_str_list`, `_empty_mapping_list` can be replaced.

**Fix**: Delete functions, use `field(default_factory=list)` directly:
```python
# Before:
sdk_patterns: list[str] = field(default_factory=_empty_str_list)

# After:
sdk_patterns: list[str] = field(default_factory=list)
```

### AC-6: Fix CopilotClientWrapper._error_config Type

**Problem**: Typed as `Any`, should be `ErrorConfig | None`.

**Fix**:
```python
_error_config: ErrorConfig | None = None
```

### AC-7: Add Logging to Silent Exception Handler

**Problem**: `_load_error_config_once` swallows exceptions silently.

**Fix**:
```python
def _load_error_config_once() -> ErrorConfig:
    try:
        return load_error_config(_CONFIG_PATH)
    except Exception as e:
        logger.warning("Failed to load error config: %s", e)
        return ErrorConfig()
```

### AC-8: Fix create_deny_hook Import Path

**Problem**: Imported directly from `sdk_adapter.client`, bypassing `__init__.py`.

**Fix**: Export from `sdk_adapter/__init__.py`:
```python
from .client import CopilotClientWrapper, create_deny_hook
from .types import SessionConfig

__all__ = ["CopilotClientWrapper", "SessionConfig", "create_deny_hook"]
```

Then in provider.py:
```python
from .sdk_adapter import create_deny_hook  # Not from .sdk_adapter.client
```

## Files to Modify

- `src/amplifier_module_provider_github_copilot/provider.py`
- `src/amplifier_module_provider_github_copilot/streaming.py`
- `src/amplifier_module_provider_github_copilot/error_translation.py`
- `src/amplifier_module_provider_github_copilot/sdk_adapter/__init__.py`
- `src/amplifier_module_provider_github_copilot/sdk_adapter/client.py`

## Dependencies

- F-020 (obsoletes AC-2)

## NOT IN SCOPE

- Major refactoring
- Performance optimization
