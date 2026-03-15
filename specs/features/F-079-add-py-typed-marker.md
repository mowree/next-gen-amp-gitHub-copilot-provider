# F-079: Add py.typed Marker File

**Status:** ready
**Priority:** P2
**Source:** packaging review

## Problem Statement
External consumers using Pyright/mypy won't get type hints from this package because there's no `py.typed` marker file.

Evidence: `grep -r "py.typed" .` returns 0 matches.

## Success Criteria
- [ ] `amplifier_module_provider_github_copilot/py.typed` exists as an empty file
- [ ] Package is recognized as PEP 561 typed by Pyright/mypy
- [ ] Existing tests pass unchanged
- [ ] No new dependencies introduced

## Implementation Approach
1. Create empty file `amplifier_module_provider_github_copilot/py.typed`
2. Verify pyproject.toml packaging includes the marker file in the wheel

## Files to Modify
- `amplifier_module_provider_github_copilot/py.typed` (create, empty)

## TDD Anchor
- Red: `pathlib.Path("amplifier_module_provider_github_copilot/py.typed").exists()` → False
- Green: Create the file → True
- Refactor: N/A

## Contract Traceability
- PEP 561 — "A package is considered typed if it contains a marker file named `py.typed`"

## Not In Scope
- Adding inline type annotations to existing code
- Running mypy/pyright CI checks (see F-025)
