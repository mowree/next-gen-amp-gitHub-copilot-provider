# F-069: Remove `_complete_fn` Dead Code

**Status:** ready
**Priority:** P2
**Source:** deep-review/code-intel.md

## Problem Statement

The `_complete_fn` attribute is initialized at provider.py line 35 but is never set after `__init__` — no setter exists and no code path assigns to it. The actual completion injection mechanism uses the `sdk_create_fn` kwarg. This dead attribute creates confusion about how completion injection works.

## Success Criteria

- [ ] `_complete_fn` attribute removed from provider `__init__`
- [ ] Any references to `_complete_fn` removed
- [ ] No behavioral change to provider functionality
- [ ] Existing tests pass without modification (or with trivial removal of dead-code references)

## Implementation Approach

1. Remove the `_complete_fn` attribute assignment from `__init__`
2. Search for any remaining references and remove them
3. Verify no tests depend on this attribute

## Files to Modify

- amplifier_module_provider_github_copilot/provider.py

## Tests Required

- Verify existing test suite passes after removal
- No new tests needed — this is dead code removal

## Contract Traceability
- N/A — dead code removal, no contract implications

## Not In Scope

- Refactoring the `sdk_create_fn` injection mechanism
- Changes to the completion lifecycle beyond removing the dead attribute
