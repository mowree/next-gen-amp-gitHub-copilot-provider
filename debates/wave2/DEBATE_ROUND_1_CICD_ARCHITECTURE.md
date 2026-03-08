# CI/CD Architecture: Autonomous Release Pipeline

**Wave 2, Agent 18 — CI/CD & Release Expert**
**Date**: 2026-03-08

---

## Executive Summary

This document defines the CI/CD architecture for `next-get-provider-github-copilot` — a provider that must detect upstream SDK changes, implement fixes, validate them, and release new versions **autonomously**. The pipeline is designed around a simple principle: **automate the boring, gate the dangerous**. Human intervention is required only when the AI's confidence is low or when releasing breaking changes.

---

## 1. Pipeline Architecture

### 1.1 Pipeline Stages Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TRIGGER LAYER                                    │
│  ┌──────────┐  ┌───────────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ git push │  │ SDK Change    │  │ Schedule  │  │ Manual Dispatch  │  │
│  │          │  │ Detection     │  │ (cron)    │  │                  │  │
│  └────┬─────┘  └──────┬────────┘  └────┬─────┘  └───────┬──────────┘  │
│       └───────────┬────┴───────────────┬┘                │             │
└───────────────────┼────────────────────┼────────────────┼──────────────┘
                    ▼                    ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: VALIDATE           (Sequential — must pass before anything)  │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌─────────────────────────┐ │
│  │ Lint     │ │ Type     │ │ Format     │ │ Security Scan           │ │
│  │ (ruff)   │ │ (pyright)│ │ Check      │ │ (bandit + safety + pip- │ │
│  │          │ │          │ │            │ │  audit)                 │ │
│  └──────────┘ └──────────┘ └────────────┘ └─────────────────────────┘ │
│  Gate: ALL must pass. Zero tolerance.                                  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: TEST                (Parallel matrix — fan out)              │
│  ┌────────────────────────────────────────────┐                        │
│  │           TEST MATRIX (see §2)             │                        │
│  │  Python 3.10 │ 3.11 │ 3.12 │ 3.13         │                        │
│  │  ────────────┼──────┼──────┼──────         │                        │
│  │  ubuntu      │  ✓   │  ✓   │  ✓   │  ✓    │                        │
│  │  macos       │      │  ✓   │  ✓   │       │                        │
│  │  windows     │      │  ✓   │  ✓   │       │                        │
│  └────────────────────────────────────────────┘                        │
│  Parallel tracks: Unit │ Integration │ Contract │ Performance          │
│  Gate: ≥95% matrix pass. Core cells MUST pass.                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: QUALITY GATES       (Sequential — verdict)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ Coverage     │ │ Performance  │ │ Compatibility│ │ License      │ │
│  │ ≥90% lines   │ │ p99 < 500ms │ │ SDK compat   │ │ Check        │ │
│  │ ≥85% branch  │ │ no regrssn  │ │ matrix pass  │ │              │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ │
│  Gate: ALL thresholds met. No exceptions for autonomous release.       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: RELEASE DECISION    (AI-driven routing)                      │
│                                                                         │
│  ┌─────────────────────────────────────────────────────┐               │
│  │  Classify change:                                    │               │
│  │  ┌─────────┐  ┌─────────────┐  ┌────────────────┐  │               │
│  │  │ PATCH   │  │ MINOR       │  │ MAJOR          │  │               │
│  │  │ Auto ✓  │  │ Auto ✓      │  │ Human Gate 🛑  │  │               │
│  │  └─────────┘  └─────────────┘  └────────────────┘  │               │
│  └─────────────────────────────────────────────────────┘               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: PUBLISH             (Sequential — irreversible)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Version  │ │ Build    │ │ Publish  │ │ GitHub   │ │ Post-      │ │
│  │ Bump     │ │ Dist     │ │ to PyPI  │ │ Release  │ │ Release    │ │
│  │          │ │          │ │ (test →  │ │ + Tag    │ │ Validation │ │
│  │          │ │          │ │  prod)   │ │          │ │            │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
│  Gate: TestPyPI install succeeds before production PyPI.               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 6: MONITOR             (Continuous — post-release)              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐  │
│  │ Install Test │ │ Smoke Tests  │ │ Error Rate Monitoring        │  │
│  │ (pip install │ │ (canary)     │ │ (24h window)                 │  │
│  │  from PyPI)  │ │              │ │                              │  │
│  └──────────────┘ └──────────────┘ └──────────────────────────────┘  │
│  Trigger: Auto-rollback if error rate > threshold.                    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Trigger Sources

| Trigger | Pipeline Scope | Frequency |
|---------|---------------|-----------|
| Push to `main` | Full pipeline (Stages 1–6) | On merge |
| Pull request | Stages 1–3 only (no release) | On PR update |
| SDK change detected | Full pipeline + AI fix stage | Cron: every 6 hours |
| Scheduled health check | Stages 1–3 | Daily at 03:00 UTC |
| Manual dispatch | Configurable (any subset) | On demand |

### 1.3 Stage Dependencies — Sequential vs Parallel

**Sequential (strict ordering):**
- Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5 → Stage 6
- Rationale: Each stage is a gate. Failing early saves compute and prevents bad releases.

**Parallel within stages:**
- Stage 1: All checks run in parallel (lint, type-check, format, security)
- Stage 2: Full matrix fans out — every cell runs independently
- Stage 3: Quality gate checks run in parallel, aggregated at the end
- Stage 5: Version bump → build → publish is strictly sequential (dependency chain)

---

## 2. Test Matrix

### 2.1 Dimensions

```
Python Versions:  3.10  │  3.11  │  3.12  │  3.13
OS Platforms:     ubuntu-latest │ macos-latest │ windows-latest
SDK Versions:     current │ current-1 │ latest-dev (canary)
Test Types:       unit │ integration │ contract │ performance
```

### 2.2 Full Matrix Definition

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]
    os: [ubuntu-latest, macos-latest, windows-latest]
    sdk-version: [current, previous, canary]
    exclude:
      # Reduce matrix — only test extremes on non-Linux
      - os: macos-latest
        python-version: "3.10"
      - os: macos-latest
        python-version: "3.13"
      - os: windows-latest
        python-version: "3.10"
      - os: windows-latest
        python-version: "3.13"
      # Canary SDK only on Linux + latest Python
      - sdk-version: canary
        os: macos-latest
      - sdk-version: canary
        os: windows-latest
      - sdk-version: canary
        python-version: "3.10"
      - sdk-version: canary
        python-version: "3.11"
```

**Total matrix cells**: ~24 (reduced from 48 by excluding low-value combinations).

### 2.3 Core Cells (Must Pass for Release)

These cells are **non-negotiable**. If any fails, release is blocked:

| Python | OS | SDK | Rationale |
|--------|----|-----|-----------|
| 3.11 | ubuntu | current | Most common production environment |
| 3.12 | ubuntu | current | Latest stable Python |
| 3.12 | ubuntu | previous | Backward compatibility |
| 3.11 | windows | current | Windows user base |
| 3.12 | macos | current | macOS developer base |

### 2.4 Test Type Breakdown

| Type | Scope | Timeout | Parallelism |
|------|-------|---------|-------------|
| **Unit** | Individual functions, classes | 5 min | Full parallel |
| **Integration** | Provider ↔ SDK interaction | 15 min | Limited (API rate limits) |
| **Contract** | API response shape validation | 5 min | Full parallel |
| **Performance** | Latency benchmarks, memory | 10 min | Sequential (stable measurements) |

### 2.5 Integration Test Environments

```
┌─────────────────────────────────────────────┐
│  Integration Environments                    │
│                                              │
│  1. Mock Environment (always available)      │
│     - WireMock/responses-based stubs         │
│     - Deterministic, fast                    │
│     - Used for: PR checks, unit tests        │
│                                              │
│  2. Sandbox Environment (rate-limited)       │
│     - Real GitHub Copilot API, test tenant   │
│     - Used for: Pre-release validation       │
│     - Rate limit: 100 req/hour               │
│                                              │
│  3. Production Canary (post-release)         │
│     - Real API, real traffic sample          │
│     - Used for: Post-release smoke tests     │
│     - 5% traffic for 1 hour                  │
└─────────────────────────────────────────────┘
```

---

## 3. Release Automation

### 3.1 Version Bumping Strategy

**Semantic Versioning** with commit-message-driven automation:

```
Commit Prefix → Version Impact:
  fix:      → PATCH  (0.0.x)   — bug fixes, SDK compat fixes
  feat:     → MINOR  (0.x.0)   — new capabilities, new SDK features
  feat!:    → MAJOR  (x.0.0)   — breaking changes (human gate)
  chore:    → NO RELEASE        — docs, CI, internal refactors
```

**Implementation**: Use `python-semantic-release` or a minimal custom script that:
1. Reads commits since last tag
2. Determines bump type from conventional commit prefixes
3. Updates `__version__` in `__init__.py`
4. Updates `pyproject.toml` version field
5. Commits the version bump with `[skip ci]` to prevent loops

### 3.2 Changelog Generation

Automated from conventional commits:

```
## [1.3.0] - 2026-03-08

### Added
- feat: Support for Copilot SDK v2.4 streaming responses (#142)

### Fixed
- fix: Handle rate limit headers correctly for SDK v2.3+ (#139)
- fix: Token refresh race condition under concurrent requests (#141)

### SDK Compatibility
- Tested against: copilot-sdk 2.3.x, 2.4.x
- Minimum supported: copilot-sdk 2.2.0
```

**Generation process**:
1. Parse commits since last tag using conventional-commit format
2. Group by type (Added, Fixed, Changed, Removed, SDK Compatibility)
3. Include PR numbers and links
4. Prepend to `CHANGELOG.md`
5. For AI-generated fixes, annotate with `[auto-fix]` tag

### 3.3 PyPI Publishing Pipeline

```
Version Bump
    │
    ▼
Build sdist + wheel
    │  (python -m build)
    ▼
Verify package
    │  (twine check dist/*)
    ▼
Publish to TestPyPI
    │  (twine upload --repository testpypi)
    ▼
Install from TestPyPI in clean venv
    │  (pip install --index-url https://test.pypi.org/simple/)
    ▼
Run smoke tests against TestPyPI install
    │  Gate: smoke tests pass
    ▼
Publish to Production PyPI
    │  (twine upload)
    ▼
Verify production install
    │  (pip install next-get-provider-github-copilot==X.Y.Z)
    ▼
Done ✓
```

**Credentials**: PyPI trusted publisher (OIDC) — no stored API tokens. GitHub Actions identity is the auth mechanism.

### 3.4 GitHub Release Creation

After successful PyPI publish:
1. Create git tag `vX.Y.Z`
2. Create GitHub Release with:
   - Title: `vX.Y.Z`
   - Body: Extracted changelog section for this version
   - Assets: `sdist` and `wheel` attached
   - Pre-release flag: `true` if version contains `rc`, `beta`, `alpha`
3. Notify downstream consumers via GitHub webhook (if configured)

---

## 4. Quality Gates

### 4.1 Gate Matrix

| Gate | Threshold | Enforcement | Bypass |
|------|-----------|-------------|--------|
| **Lint** (ruff) | 0 errors | Block merge | None |
| **Type check** (pyright) | 0 errors | Block merge | None |
| **Format** (ruff format) | No diff | Block merge | None |
| **Security** (bandit) | 0 high/critical | Block merge | Human override + justification |
| **Dependency audit** (pip-audit) | 0 known vulns | Block release | Human override + timeline |
| **Unit test pass rate** | 100% | Block merge | None |
| **Integration test pass rate** | 100% core cells | Block release | None |
| **Line coverage** | ≥ 90% | Block release | Human override (with reason) |
| **Branch coverage** | ≥ 85% | Block release | Human override (with reason) |
| **Performance** | No p99 regression > 10% | Block release | Human override |
| **SDK compatibility** | Current + previous pass | Block release | None |
| **Package install** | Clean install succeeds | Block release | None |
| **License check** | No copyleft in deps | Block release | Human review required |

### 4.2 Coverage Requirements

```python
# pytest.ini / pyproject.toml
[tool.coverage.report]
fail_under = 90
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.",
    "@overload",
]

[tool.coverage.run]
branch = true
```

### 4.3 Performance Baseline

Benchmarks stored in `benchmarks/` and tracked across releases:

| Metric | Threshold | Measured Against |
|--------|-----------|-----------------|
| Provider initialization | < 100ms | Cold start |
| Simple completion request | p50 < 200ms, p99 < 500ms | Mock API |
| Streaming first token | < 150ms | Mock API |
| Memory per request | < 50MB | 100 concurrent |
| SDK version detection | < 50ms | Import time |

Regressions > 10% on any metric block the release.

---

## 5. Rollback Capability

### 5.1 Automated Rollback Triggers

```
Post-Release Monitoring (24h window)
    │
    ├── Install failure rate > 5%        → AUTO ROLLBACK
    ├── Import error detected            → AUTO ROLLBACK
    ├── Smoke test failure               → AUTO ROLLBACK
    ├── Error rate spike > 3x baseline   → AUTO ROLLBACK
    └── User-reported critical bug       → HUMAN DECISION
```

### 5.2 Rollback Procedure

```
ROLLBACK SEQUENCE:

1. YANK bad version from PyPI
   │  (prevents new installs — existing installs unaffected)
   ▼
2. Publish previous known-good version as new PATCH
   │  e.g., 1.3.0 is bad → publish 1.3.1 with 1.2.x code + version bump
   ▼
3. Create GitHub Issue tagged [rollback]
   │  Include: failed version, trigger reason, affected matrix cells
   ▼
4. Run full test suite against rollback version
   │  Gate: all core cells pass
   ▼
5. Update GitHub Release
   │  Mark failed version as "yanked" with explanation
   ▼
6. Notify maintainers
   │  Slack/email with rollback summary
   ▼
7. AI begins root cause analysis
   │  Opens investigation branch
   ▼
Done — system is stable on known-good version
```

### 5.3 Post-Rollback Validation

After every rollback:
1. **Verify PyPI state**: `pip install next-get-provider-github-copilot` installs the correct version
2. **Run full matrix**: Ensure rollback version passes all gates
3. **Check downstream**: Verify dependent packages still work
4. **Root cause**: AI agent opens investigation branch, runs bisect-style analysis
5. **Prevention**: Add regression test for the failure mode before next release

### 5.4 Version Pinning Safety

The rollback strategy works because:
- We **never delete** PyPI versions — we yank them (soft-delete)
- We **always move forward** — rollback is a new patch, not a re-upload
- We **track known-good versions** in a `.known-good` file in the repo

---

## 6. AI-Driven CI

This is the core differentiator: the pipeline doesn't just detect failures — it **fixes them**.

### 6.1 AI Failure Interpretation

```
Test Failure Detected
    │
    ▼
┌─────────────────────────────────────────────┐
│  AI TRIAGE AGENT                             │
│                                              │
│  Input:                                      │
│  - Failed test output (stdout + stderr)      │
│  - Test source code                          │
│  - Recent git diff                           │
│  - SDK changelog (if SDK-triggered)          │
│                                              │
│  Output:                                     │
│  - Failure classification:                   │
│    ┌────────────────┐                        │
│    │ FLAKY          │ → Retry (max 2x)       │
│    │ ENV_ISSUE      │ → Retry on fresh runner │
│    │ SDK_BREAKING   │ → Route to AI fix       │
│    │ OUR_BUG        │ → Route to AI fix       │
│    │ INFRA_FAILURE  │ → Alert, skip release   │
│    │ UNKNOWN        │ → Human review          │
│    └────────────────┘                        │
│  - Confidence score (0–1)                    │
│  - Suggested fix (if applicable)             │
└─────────────────────────────────────────────┘
```

### 6.2 AI Fix Proposal Pipeline

When the triage agent classifies a failure as `SDK_BREAKING` or `OUR_BUG` with confidence ≥ 0.7:

```
AI Fix Pipeline:

1. ANALYZE
   │  Read failing test, implementation, SDK diff
   │  Identify root cause
   ▼
2. PROPOSE
   │  Generate fix as a git patch
   │  Generate new/updated tests for the fix
   ▼
3. VALIDATE (autonomous)
   │  Apply patch to clean branch
   │  Run full test matrix
   │  Verify fix doesn't break other tests
   │  Verify coverage doesn't drop
   ▼
4. CONFIDENCE CHECK
   │
   ├── Confidence ≥ 0.9 AND patch-only fix AND tests pass
   │   → AUTO-MERGE (patch release, no human needed)
   │
   ├── Confidence 0.7–0.9 OR minor feature change
   │   → CREATE PR (human review within 24h, auto-merge after)
   │
   └── Confidence < 0.7 OR major change
       → CREATE ISSUE (human investigation required)
```

### 6.3 AI Validation Loop

The AI doesn't just propose — it validates its own work:

```python
# Pseudocode for AI validation
class AIFixValidator:
    MAX_ATTEMPTS = 3

    def validate_fix(self, fix: Patch) -> ValidationResult:
        for attempt in range(self.MAX_ATTEMPTS):
            # Apply fix
            branch = create_branch(f"ai-fix/{fix.id}/attempt-{attempt}")
            apply_patch(branch, fix)

            # Run tests
            result = run_test_matrix(branch, subset="core-cells")

            if result.all_pass:
                # Check for regressions
                regression = compare_with_baseline(branch)
                if not regression:
                    return ValidationResult(
                        status="validated",
                        confidence=calculate_confidence(fix, result),
                        branch=branch,
                    )

            # If failed, AI analyzes why and refines
            fix = self.refine_fix(fix, result.failures)

        # Exhausted attempts
        return ValidationResult(status="needs_human", fix_attempts=self.MAX_ATTEMPTS)
```

### 6.4 Human Approval Gates

**When humans MUST be involved:**

| Scenario | Gate Type | SLA |
|----------|-----------|-----|
| Breaking API change (MAJOR bump) | Approval required | No auto-timeout |
| AI confidence < 0.7 on any fix | Review required | 48h, then escalate |
| Security vulnerability in fix | Security team review | 24h |
| New dependency added | Approval required | 24h, then auto-deny |
| Rollback of a rollback | Approval required | No auto-timeout |
| First release after major SDK update | Approval required | 48h |

**When humans are NOT involved:**

| Scenario | Action |
|----------|--------|
| Patch fix, AI confidence ≥ 0.9, all tests pass | Auto-merge + auto-release |
| Minor feature, AI confidence ≥ 0.9, all tests pass | Auto-merge + auto-release |
| Flaky test retry succeeds | Continue pipeline |
| Scheduled health check passes | No action |
| SDK canary compatible, no changes needed | No action |

### 6.5 AI Feedback Loop

Every AI action feeds back into future decisions:

```
┌──────────────────────────────────────────────────┐
│  AI LEARNING LOOP                                 │
│                                                   │
│  For every AI fix:                                │
│  1. Record: failure type, fix type, confidence    │
│  2. Track: was fix accepted? Did it hold?         │
│  3. If fix was rejected or rolled back:           │
│     - Lower confidence for similar patterns       │
│     - Add to "needs human" heuristic              │
│  4. If fix held for 7 days:                       │
│     - Increase confidence for similar patterns    │
│     - Add pattern to "safe auto-fix" list         │
│                                                   │
│  Storage: JSON log in repo (ai-fix-history.json)  │
│  Used by: Triage agent for confidence calibration │
└──────────────────────────────────────────────────┘
```

---

## 7. GitHub Actions Workflow Structure

### 7.1 Workflow Files

```
.github/workflows/
├── ci.yml                    # PR checks (Stages 1-3)
├── release.yml               # Full pipeline (Stages 1-6)
├── sdk-watch.yml             # SDK change detection + AI fix
├── scheduled-health.yml      # Daily health check
├── rollback.yml              # Manual rollback trigger
└── ai-fix.yml                # AI fix proposal pipeline
```

### 7.2 Concurrency Controls

```yaml
# release.yml
concurrency:
  group: release
  cancel-in-progress: false  # Never cancel an in-progress release

# ci.yml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true   # Cancel outdated PR checks
```

### 7.3 Secrets and Permissions

| Secret/Permission | Used By | Scope |
|-------------------|---------|-------|
| PyPI Trusted Publisher (OIDC) | release.yml | PyPI upload |
| `GITHUB_TOKEN` (default) | All workflows | Repo read/write |
| `AI_SERVICE_TOKEN` | ai-fix.yml, sdk-watch.yml | AI agent API |
| `TESTPYPI_TOKEN` | release.yml | TestPyPI upload |

No long-lived secrets stored. OIDC federation wherever possible.

---

## 8. SDK Change Detection

The most critical autonomous capability — detecting and responding to upstream changes.

### 8.1 Detection Mechanism

```
Every 6 hours (cron):

1. Check PyPI for new copilot-sdk versions
   │  (pip index versions copilot-sdk)
   ▼
2. Compare against pinned version in pyproject.toml
   │
   ├── No change → Exit
   │
   └── New version detected
       │
       ▼
3. Install new SDK version in isolated venv
   │
   ▼
4. Run contract tests against new SDK
   │
   ├── All pass → Update pin, open auto-merge PR
   │
   └── Failures detected
       │
       ▼
5. Route to AI Fix Pipeline (§6.2)
```

### 8.2 SDK Compatibility Matrix Tracking

Maintained in `sdk-compat.json`:

```json
{
  "supported": {
    "copilot-sdk": {
      "minimum": "2.2.0",
      "current": "2.4.1",
      "tested": ["2.2.0", "2.3.0", "2.3.5", "2.4.0", "2.4.1"]
    }
  },
  "known_incompatible": ["2.1.x", "1.x"],
  "last_checked": "2026-03-08T10:30:00Z"
}
```

---

## 9. Design Principles

1. **Gate early, gate hard**: Cheap checks (lint, format) run first. Expensive checks (integration, performance) run last. A formatting error should never consume 30 minutes of matrix compute.

2. **Forward-only releases**: Never re-upload a version. Rollback means publishing a new patch with known-good code. This is simpler, auditable, and PyPI-compatible.

3. **Confidence-driven autonomy**: The AI earns trust through a track record. New failure patterns start with low confidence (human review). Patterns with proven fixes graduate to full autonomy.

4. **Observable by default**: Every pipeline run produces a structured JSON summary. Every AI decision is logged with inputs, reasoning, and confidence. Humans can audit any decision after the fact.

5. **Blast radius minimization**: TestPyPI before production PyPI. Core matrix cells before full matrix. Canary traffic before full traffic. Each step limits the damage of a bad release.

---

## 10. Open Questions for Debate

1. **Confidence threshold for auto-merge**: Is 0.9 too conservative? Too aggressive? Should it be calibrated per failure type?

2. **SDK canary testing**: Should we test against SDK `main` branch (pre-release), or only published versions? Pre-release gives earlier warning but higher noise.

3. **Multi-provider coordination**: If multiple providers release simultaneously against the same SDK change, should there be a coordination mechanism?

4. **Rollback automation scope**: Should rollback be fully automated (no human), or should it always require human confirmation? The current design auto-rolls-back on clear signals but requires humans for ambiguous cases.

5. **AI fix iteration limit**: 3 attempts is arbitrary. Should this be configurable? Should the AI be allowed to escalate to a different strategy after N failures?