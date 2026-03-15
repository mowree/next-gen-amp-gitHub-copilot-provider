# F-063: SDK Boundary Structure Compliance

**Status:** ready
**Priority:** P2
**Source:** deep-review/spec-reviewer-part2.md, deep-review/integration-specialist.md
**Defect ID:** N/A

## Problem Statement
The `sdk_adapter/` directory structure diverges from the contract (`contracts/sdk-boundary.md`):
1. No `_imports.py` — SDK imports live in `client.py` instead of a single quarantine file
2. No `events.py` or `errors.py` in `sdk_adapter/` — they live at package root
3. `__init__.py` exports `CopilotClientWrapper` (SDK-coupled, not a domain type)
4. `SDKSession = Any` instead of opaque UUID-based `SessionHandle`

## Success Criteria
- [ ] `_imports.py` created as single SDK import point
- [ ] SDK imports moved from `client.py` to `_imports.py`
- [ ] `__init__.py` exports only domain types
- [ ] Architecture fitness test updated to enforce `_imports.py` quarantine

## Implementation Approach
1. Create `sdk_adapter/_imports.py` with all `from copilot import ...` statements
2. Update `client.py` to import from `_imports.py`
3. Update `__init__.py` exports to domain types only
4. Add architecture test: SDK imports only in `_imports.py`

## Files to Modify
- New: `amplifier_module_provider_github_copilot/sdk_adapter/_imports.py`
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py`
- `amplifier_module_provider_github_copilot/sdk_adapter/__init__.py`

## Tests Required
- Architecture test: no `from copilot` or `import copilot` outside `_imports.py`

## Contract Traceability
- `contracts/sdk-boundary.md` — SDK boundary structure and import quarantine rules

## Not In Scope
- Moving `error_translation.py`/`streaming.py` into `sdk_adapter/`
- Implementing UUID-based SessionHandle (larger refactor)

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
