# F-065: Provider Core Decomposition

**Status:** ready
**Priority:** P2
**Source:** deep-review/spec-reviewer-part1.md
**Defect ID:** N/A

## Problem Statement
`provider.py` is 532 lines (target: ~120). It contains completion lifecycle, config loading, response extraction, helper dataclasses, and session handling — all of which the Golden Vision spec assigns to separate modules (`completion.py`, adapter/session factory layers). The `complete()` method accepts `request: Any` instead of the spec's `ChatRequest` type.

## Success Criteria
- [ ] `provider.py` reduced to thin orchestrator (~120-200 lines)
- [ ] Completion logic extracted to `completion.py`
- [ ] Response extraction extracted to appropriate module
- [ ] `complete()` type signature uses `ChatRequest` (or documented reason for `Any`)
- [ ] All existing tests still pass

## Implementation Approach
1. Extract `extract_response_content()` and helpers to a separate module
2. Extract completion logic to `completion.py`
3. Keep `GitHubCopilotProvider` as thin orchestrator
4. Tighten type signatures where possible

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (decompose)
- New: `amplifier_module_provider_github_copilot/completion.py`
- New: `amplifier_module_provider_github_copilot/response.py` (optional)

## Tests Required
- All existing tests must pass (refactor, not behavior change)
- Import tests updated for new module locations

## Not In Scope
- Changing behavior of any existing function
- New features or bug fixes (pure refactor)
