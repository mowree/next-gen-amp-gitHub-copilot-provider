# F-054: Response Extraction Recursion Guard

**Status:** ready
**Priority:** P1
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-005

## Problem Statement
`extract_response_content()` in `provider.py:144-145` recursively follows `.data` attributes with no depth limit and no cycle detection. If `response.data` returns an object that also has `.data` (e.g., a deeply nested SDK structure or unspec'd MagicMock), this recurses until stack overflow.

## Success Criteria
- [ ] Recursion is bounded by a depth limit (e.g., max 5 levels)
- [ ] Exceeding depth limit returns a safe fallback (empty string or str(response))
- [ ] Normal SDK responses still extract correctly
- [ ] Test covers chained `.data` attributes

## Implementation Approach
1. Add a `_depth` parameter (default 0) to `extract_response_content()`
2. Return fallback when `_depth > MAX_DEPTH` (5 is sufficient)
3. Increment depth on recursive call

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (lines 121-157)

## Tests Required
- `tests/test_response_extraction.py` (new) or additions to `tests/test_provider.py`:
  - Test: object with `.data.data.data` chain terminates safely
  - Test: normal response extraction still works (regression)

## Not In Scope
- Changing what attributes are checked
- Schema validation of SDK responses

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
