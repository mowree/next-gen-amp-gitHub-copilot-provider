# F-055: StreamingAccumulator Completion Guard

**Status:** ready
**Priority:** P1
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-006

## Problem Statement
`StreamingAccumulator.add()` in `streaming.py:78-95` continues processing events after `TURN_COMPLETE` or `ERROR` sets `is_complete = True`. Spurious text deltas arriving after a tool_use stop corrupt the accumulated response by appending to `text_content`.

## Success Criteria
- [ ] Events after `TURN_COMPLETE` are ignored (early return)
- [ ] Events after `ERROR` are ignored (early return)
- [ ] Normal event accumulation is unaffected
- [ ] Test covers late events after completion

## Implementation Approach
1. Add `if self.is_complete: return` guard at the top of `add()`

## Files to Modify
- `amplifier_module_provider_github_copilot/streaming.py` (line 78, `add()` method)

## Contract Traceability
- `contracts/streaming-contract.md` — accumulator must respect completion semantics

## Tests Required
- `tests/test_streaming_accumulator.py` (new) or additions to `tests/test_streaming.py`:
  - Test: CONTENT_DELTA after TURN_COMPLETE is ignored
  - Test: CONTENT_DELTA after ERROR is ignored
  - Test: normal accumulation sequence works (regression)

## Not In Scope
- Logging late events
- Changing accumulator data structures

## 7. Test Strategy (TDD)

Write tests BEFORE implementation:

| Test | Type | What it verifies | Contract Anchor |
|------|------|------------------|-----------------|
| `test_happy_path` | Unit | Primary behavior | `<contract>:<Section>:MUST:N` |
| `test_error_case` | Unit | Error handling | `<contract>:<Section>:MUST:N` |
| `test_edge_case` | Unit | Boundary conditions | `<contract>:<Section>:SHOULD:N` |

**Test file:** `tests/test_<module_name>.py`

Tests MUST:
- Reference contract clause in docstring
- Use `ConfigCapturingMock` for SDK boundary tests
- Fail before implementation (Red phase)
