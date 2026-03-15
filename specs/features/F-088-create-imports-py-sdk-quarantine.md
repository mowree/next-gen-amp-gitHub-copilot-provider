# F-088: Create _imports.py for SDK Import Quarantine

**Status:** ready
**Priority:** P2 (MEDIUM)
**Source:** manual-review

## Problem Statement

The sdk-boundary.md contract requires all SDK imports to be quarantined in `sdk_adapter/_imports.py`, but this file does not exist. SDK imports are currently in client.py directly.

## Evidence

- sdk-boundary.md line ~30: "All SDK imports MUST be quarantined in `_imports.py`"
- File search: No `_imports.py` file exists anywhere in the codebase
- Current state: SDK imports like `from copilot.client import Client` are in client.py:1-10

## Success Criteria

- [ ] `sdk_adapter/_imports.py` exists with all SDK imports quarantined
- [ ] Module docstring explains the quarantine purpose
- [ ] `__all__` exports all quarantined symbols
- [ ] `client.py` imports SDK symbols from `._imports` instead of directly
- [ ] All existing tests pass
- [ ] Type checker (pyright) passes without new errors

## Implementation Approach

Create `sdk_adapter/_imports.py`:

```python
"""SDK Import Quarantine.

All SDK imports are isolated here per sdk-boundary.md contract.
This enables:
- Easy SDK version tracking
- Single point for SDK compatibility shims
- Clear boundary for membrane violations
"""

from copilot.client import Client
from copilot.api import Session
# ... other SDK imports discovered in client.py

__all__ = ["Client", "Session", ...]
```

Then update `client.py` to import from the quarantine module:

```python
from ._imports import Client, Session
```

## Files to Modify

- `amplifier_module_provider_github_copilot/sdk_adapter/_imports.py` (create)
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (update imports)

## Contract Traceability

- **sdk-boundary.md** — "All SDK imports MUST be quarantined in `_imports.py`"

## Tests Required

- Verify existing tests pass with imports redirected through `_imports.py`
- Verify pyright accepts the new import paths without errors

## Not In Scope

- Adding new SDK imports beyond what client.py currently uses
- Refactoring SDK adapter internals beyond import redirection
- SDK version compatibility shims (future work)
