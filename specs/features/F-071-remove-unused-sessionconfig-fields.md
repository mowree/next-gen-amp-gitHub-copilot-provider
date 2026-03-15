# F-071: Remove Unused SessionConfig Fields

**Status:** ready
**Priority:** P2
**Source:** deep-review/code-intel.md

## Problem Statement

`SessionConfig` in types.py defines `system_prompt` and `max_tokens` fields, but code-intel analysis shows these fields are never read or propagated to the SDK. Only the `model` field is actually set and used. These unused fields create a false API surface — callers may set them expecting behavior that never occurs.

## Success Criteria

- [ ] `system_prompt` and `max_tokens` fields removed from `SessionConfig`
- [ ] Any references to these fields in tests updated or removed
- [ ] No behavioral change (fields were already unused)
- [ ] Existing tests pass

## Implementation Approach

1. Remove `system_prompt` and `max_tokens` from the `SessionConfig` dataclass/type definition
2. Search for any references to these fields across the codebase and remove them
3. Update any test fixtures that set these fields

## Files to Modify

- amplifier_module_provider_github_copilot/types.py
- Tests referencing `system_prompt` or `max_tokens` on SessionConfig

## Tests Required

- Verify existing test suite passes after removal
- Search `tests/` for any `system_prompt` or `max_tokens` references on SessionConfig and update
- No new tests needed — this is unused field removal

## Contract Traceability
- N/A — unused field removal, no contract implications

## Not In Scope

- Adding system_prompt or max_tokens support (wiring them through to the SDK)
- Refactoring SessionConfig for other reasons
- Changes to how `model` is propagated

## 7. Test Strategy

N/A — cleanup/refactor feature, no behavioral tests required.

