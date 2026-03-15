# F-089: Align SessionConfig Shape with Contract

**Status:** ready
**Priority:** P2 (MEDIUM)
**Source:** manual-review

## Problem Statement

The `SessionConfig` dataclass in `sdk_adapter/types.py` has different field names than the sdk-boundary.md contract specifies, creating a contract/code mismatch.

## Evidence

- Contract sdk-boundary.md requires: `system_message`, `tools`, `reasoning_effort`
- Actual types.py has: `system_prompt`, `max_tokens`, `tool_config`

## Success Criteria

- [ ] `SessionConfig` field names are documented relative to the contract
- [ ] Either code or contract is updated so they agree
- [ ] If names differ for SDK compatibility, a docstring explains the mapping
- [ ] All existing tests pass
- [ ] Type checker (pyright) passes without new errors

## Implementation Approach

Recommended approach (align contract to reality):

1. Add docstring to `SessionConfig` explaining the mapping between contract names and actual field names
2. Update sdk-boundary.md to reflect the actual field names used in code
3. Document why names differ if they are SDK-driven

Alternative approach (align code to contract):

1. Rename `system_prompt` → `system_message`
2. Rename `tool_config` → `tools`
3. Add `reasoning_effort` field
4. Update all references throughout the codebase

The recommended approach is safer since the current field names may be driven by SDK compatibility constraints.

## Files to Modify

- `amplifier_module_provider_github_copilot/sdk_adapter/types.py` (add docstring mapping)
- `contracts/sdk-boundary.md` (update SessionConfig shape to match reality)

## Contract Traceability

- **sdk-boundary.md** — SessionConfig shape specification

## Tests Required

- Verify existing tests pass after changes
- Verify pyright accepts any renamed fields without errors

## Not In Scope

- Adding new fields to SessionConfig beyond what the contract specifies
- Refactoring SessionConfig consumers beyond field name updates
- Runtime validation of SessionConfig values
