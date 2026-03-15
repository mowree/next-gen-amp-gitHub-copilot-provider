# F-084: Remove Redundant Path Import

**Status:** ready
**Priority:** P3
**Source:** deep-review/python-dev.md, principal-review

## Problem Statement

`provider.py` has two imports of `Path` from `pathlib` — one at the module level (line 27) and a redundant duplicate inside a function (line 233). This violates the DRY principle and creates confusion.

## Evidence

**provider.py line 27 — MODULE-LEVEL IMPORT:**
```python
from pathlib import Path
```

**provider.py line 233 — REDUNDANT DUPLICATE:**
```python
from pathlib import Path
```

The module-level import is sufficient. The function-level import is redundant and serves no purpose (it's not a conditional or lazy import pattern).

## Success Criteria

- [ ] Only one `from pathlib import Path` import remains (the module-level one at line 27)
- [ ] The redundant import at line 233 is removed
- [ ] All existing tests pass
- [ ] No runtime behavior changes

## Implementation Approach

1. Delete the `from pathlib import Path` line at line 233 in `provider.py`

## Files to Modify

- `amplifier_module_provider_github_copilot/provider.py` (remove line 233)

## Contract Traceability

- DRY principle — no duplicate imports
- Code quality standards

## Tests Required

No new tests needed — this is a no-op cleanup. Verify existing tests still pass.

## Not In Scope

- Auditing other files for duplicate imports
- Reorganizing the import block

## 7. Test Strategy

N/A — cleanup/refactor feature, no behavioral tests required.

