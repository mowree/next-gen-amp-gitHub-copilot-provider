# F-050: Mandatory Deny Hook Installation

**Status:** ready
**Priority:** P1
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-003

## Problem Statement
Both `provider.py:256-257` and `client.py:241-243` install the deny hook conditionally via `if hasattr(session, "register_pre_tool_use_hook")`. If the SDK session lacks this method, the deny hook is silently not installed — no error, no warning, no exception. This violates `deny-destroy:DenyHook:MUST:1`: "MUST install a preToolUse deny hook on every SDK session."

## Success Criteria
- [ ] When `register_pre_tool_use_hook` is absent, a `ProviderUnavailableError` is raised
- [ ] Error message clearly states deny hook could not be installed
- [ ] Both code paths (provider.py and client.py) enforce this
- [ ] Tests verify the raise behavior when method is absent
- [ ] Tests verify hook is installed when method is present (existing behavior preserved)

## Implementation Approach
1. Replace `if hasattr(...)` silent fallback with mandatory registration
2. If `register_pre_tool_use_hook` is absent, raise `ProviderUnavailableError` with a clear message
3. Add tests using mock sessions without the method to verify the error is raised

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (lines 256-257)
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (lines 241-243)

## Tests Required
- `tests/test_deny_hook_mandatory.py` or additions to existing deny-hook tests:
  - Test: session without `register_pre_tool_use_hook` → raises `ProviderUnavailableError`
  - Test: session with `register_pre_tool_use_hook` → hook registered (existing behavior)

## Contract Traceability
- `contracts/deny-destroy.md` — `DenyHook:MUST:1`: "MUST install a preToolUse deny hook on every SDK session"

## Not In Scope
- Changing the deny hook logic itself
- SDK version detection or graceful degradation strategies

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
