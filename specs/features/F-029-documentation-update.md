# F-029: Documentation Update

## 1. Overview

**Module:** docs
**Priority:** P1
**Depends on:** none

Update README.md and add essential documentation files to reflect production-ready status. The current README shows "Scaffold phase" but the project has completed Phase 3 with 29 features implemented.

## 2. Requirements

### Files to Update

**README.md** - Complete rewrite:
- Update status from "Scaffold phase" to "Production Ready"
- Add quick-start guide with token configuration
- Add configuration section (environment variables)
- Add test markers documentation
- Add troubleshooting section

**DEVELOPMENT.md** - New file:
- Local development setup
- Running tests (unit, contract, live SDK)
- Test markers explanation (@contract, @live, @sdk_assumption)
- Code quality tools (ruff, pyright)
- Contributing guidelines

### Behavior

- README must be concise (<100 lines) with links to detailed docs
- DEVELOPMENT.md must cover the full dev workflow
- All code examples must use `uv` commands

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | README.md status updated to "Production Ready" | Manual review |
| AC-2 | README.md includes token configuration (GITHUB_TOKEN) | Grep for GITHUB_TOKEN |
| AC-3 | README.md includes test command with markers | Grep for pytest markers |
| AC-4 | DEVELOPMENT.md exists with setup instructions | File exists check |
| AC-5 | DEVELOPMENT.md covers all test tiers | Grep for Tier 6, Tier 7 |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Missing token | README explains skip behavior for live tests |
| CI vs local | README distinguishes CI workflow from local dev |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `README.md` | Modify | Updated status, quick-start, configuration |
| `DEVELOPMENT.md` | Create | Full development workflow documentation |

## 6. Dependencies

- No new dependencies

## 7. Notes

- Keep README focused on "how to use"
- Keep DEVELOPMENT.md focused on "how to contribute"
- Reference contracts/ for behavioral specifications
