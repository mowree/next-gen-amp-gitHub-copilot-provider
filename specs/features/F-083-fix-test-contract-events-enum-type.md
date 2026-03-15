# F-083: Fix test_contract_events.py Enum Type Issue

**Status:** ready
**Priority:** P2
**Source:** deep-review/python-dev.md, principal-review

## Problem Statement

`test_contract_events.py` line 98 passes a string `"CONTENT_DELTA"` to `DomainEvent(type=...)` but the type annotation expects a `DomainEventType` enum value. This is technically incorrect and could mask real type issues during development.

## Evidence

**test_contract_events.py line 98 — STRING LITERAL:**
```python
DomainEvent(type="CONTENT_DELTA", data={"text": content})
```

**streaming.py — TYPE ANNOTATION:**
`DomainEvent.type` is typed as `DomainEventType` (enum), not `str`.

Pyright passes because of structural typing, but the test should use the correct enum type to catch typing errors during development.

## Success Criteria

- [ ] `test_contract_events.py` uses `DomainEventType.CONTENT_DELTA` instead of string `"CONTENT_DELTA"`
- [ ] `DomainEventType` is imported in the test file
- [ ] All existing tests pass
- [ ] Pyright reports no new errors

## Implementation Approach

1. Add `DomainEventType` to the imports in `test_contract_events.py`
2. Replace `"CONTENT_DELTA"` with `DomainEventType.CONTENT_DELTA` at line 98

## Files to Modify

- `tests/test_contract_events.py` (line 98)

## Contract Traceability

- Type safety — tests should use correct types to catch typing errors during development
- `contracts/provider-protocol.md` — domain events use typed enums

## Tests Required

No new tests needed — this is a fix to an existing test file. Verify existing tests still pass.

## Not In Scope

- Auditing other test files for similar string-vs-enum issues
- Changing `DomainEvent` to reject string values at runtime
