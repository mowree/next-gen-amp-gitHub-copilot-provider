# F-075: retry.yaml Exists But Never Loaded

**Status:** ready
**Priority:** P2
**Source:** deep-review/code-quality-reviewer.md

## Problem Statement
`config/retry.yaml` exists but no code loads it. The `behaviors.md` contract references retry configuration, but the implementation is missing — the file is dead config.

Evidence: `grep -r "retry.yaml" amplifier_module_provider_github_copilot/` returns 0 matches.

## Success Criteria
- [ ] Decision made: wire retry.yaml to code OR delete the dead file
- [ ] If wired: retry config is loaded and used by retry logic
- [ ] If deleted: file is removed and any references cleaned up
- [ ] No dead config files remain in the config directory

## Implementation Approach
**Option A (Preferred — Delete):** Remove `config/retry.yaml` since no code uses it. If retry behavior is needed later, it can be re-added with proper wiring as part of F-060 (config-driven-retry).

**Option B (Wire):** Load retry.yaml similarly to errors.yaml and apply its values to retry logic. This overlaps significantly with F-060.

Recommendation: Delete the file. F-060 already covers config-driven retry as a proper feature with full wiring.

## Files to Modify
- `config/retry.yaml` (delete)

## TDD Anchor
- Red: `config/retry.yaml` exists but `grep -r "retry.yaml" amplifier_module_provider_github_copilot/` returns 0 matches
- Green: File deleted, grep returns 0 matches, no config references remain
- Refactor: N/A

## Contract Traceability
- `contracts/behaviors.md` — retry configuration reference (F-060 addresses proper implementation)

## Not In Scope
- Implementing config-driven retry (see F-060)
- Changing retry behavior or logic
