# F-053: Unify Error Config Loading (F-036 Parity)

**Status:** ready
**Priority:** P1
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-004

## Problem Statement
`_load_error_config_once()` in `client.py:72-113` has two code paths. The importlib.resources path manually re-implements YAML parsing and was NOT updated when F-036 added context extraction support. It builds `ErrorMapping` objects without `context_extraction`. In deployed/installed scenarios where importlib.resources succeeds, F-036 context extraction is silently dropped for session-level errors.

This is a direct instance of the F-044/F-045 pattern: duplicate parsing logic diverges when only one copy is updated.

## Success Criteria
- [ ] Single source of truth for error config parsing (eliminate duplicate)
- [ ] `context_extraction` works in both file-path and importlib.resources scenarios
- [ ] `_load_error_config_once()` delegates to `load_error_config()` for all parsing
- [ ] Tests verify context extraction works when loaded via importlib path

## Implementation Approach
1. Refactor `load_error_config()` to accept either a file path OR use importlib.resources internally
2. Have `_load_error_config_once()` delegate to `load_error_config()` for all YAML parsing
3. Eliminate the duplicate parsing code in the importlib path

## Files to Modify
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (lines 72-113)
- `amplifier_module_provider_github_copilot/error_translation.py` (if `load_error_config` needs to support importlib)

## Tests Required
- `tests/test_error_config_loading.py` (new) or additions to `tests/test_error_translation.py`:
  - Test: error config loaded via importlib includes `context_extraction` fields
  - Test: error config loaded via file path still works (regression)

## Contract Traceability
- `contracts/error-hierarchy.md` — error config must produce correct kernel error types

## Not In Scope
- Changing error translation logic
- Adding new error mappings

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
