# DEV-MACHINE-READY: All Phases Implementation Guide

**Authority:** Expert Panel Synthesis (superpowers, zen-architect, core-expert, integration-specialist)
**Date:** 2026-03-15
**Status:** READY FOR AUTONOMOUS EXECUTION

---

## Executive Summary

**41 implementable features** across 9 phases, ready for autonomous dev-machine execution.

| Metric | Count |
|--------|-------|
| Total features tracked | 91 |
| Features READY | 43 |
| Features COMPLETED | 48 |
| Dropped/Superseded | 3 |
| **Implementable this run** | **41** |

---

## Expert Panel Documents (Reference)

| Document | Expert | Purpose |
|----------|--------|---------|
| `mydocs/deep-review/AMPLIFIER-DIRECTIVE-2026-03-15.md` | Principal | **THE CONSTITUTION** — source of truth |
| `mydocs/PHASE-ARCHITECTURE-NOTES.md` | zen-architect | Phase-by-phase architectural guidance |
| `mydocs/deep-review/KERNEL-COMPLIANCE-CHECKLIST.md` | core-expert | Kernel type compliance per feature |
| `mydocs/DEPENDENCY-GRAPH-PHASE9.md` | integration-specialist | Dependency graph and safe ordering |

---

## Phase Implementation Summary

### Phase 1: Zero-Risk Cleanups + Sovereignty (~1 iteration)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | **F-049** | P0 | Fix architecture test paths + contract paths |
| 2 | **F-050** | P1 | Deny hook enforcement (sovereignty invariant) |
| 3 | F-077 | P3 | Delete tombstone test files |
| 4 | F-079 | P2 | Add py.typed marker |
| 5 | F-084 | P3 | Remove redundant Path import |

**Exit Criteria:** All tests pass, contracts have correct paths, deny hook enforced

---

### Phase 2: Config Foundation (~1 iteration)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | **F-074** | P1 | Contract path standardization |
| 2 | F-078 | P2 | Event config foundation |
| 3 | F-081 | P2 | Error config foundation |
| 4 | F-082 | P2 | Retry config foundation |

**Exit Criteria:** Config files exist and load without errors

---

### Phase 3: SDK Integration Core (~2-3 iterations)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | **F-072** | P0 | Error translation in complete() |
| 2 | F-073 | P1 | Tests for F-072 |
| 3 | **F-052** | P0 | Real SDK streaming pipeline |
| 4 | F-051 | P0 | Event config safety |

**Exit Criteria:** SDK streaming works end-to-end with config-driven error translation

---

### Phase 4: Error Hardening (~1 iteration)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | F-085 | P1 | Add timeout enforcement (real SDK path) |
| 2 | F-086 | P1 | Fix edge cases in error translation |

**Exit Criteria:** All error paths tested and translated correctly

---

### Phase 5: Event System (~1 iteration)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | F-053 | P1 | Event bridge implementation |
| 2 | F-054 | P2 | Event validation |

**Exit Criteria:** Events emit correctly per contract vocabulary

---

### Phase 6: Provider Protocol (~1 iteration)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | F-055 | P1 | Provider info method |
| 2 | F-056 | P2 | Model listing |
| 3 | F-057 | P2 | Capability negotiation |

**Exit Criteria:** Provider protocol fully implemented per contracts

---

### Phase 7: Structural Refactoring (~2 iterations)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | **F-067** | P3 | Test quality improvements (MOVED from Phase 9) |
| 2 | **F-088** | P2 | Create _imports.py SDK quarantine |
| 3 | F-063 | P2 | Extend SDK quarantine |
| 4 | F-069 | P2 | Remove complete_fn dead code |
| 5 | F-070 | P2 | Cleanup deferred imports |
| 6 | **F-089** | P2 | Align SessionConfig (absorbs F-071) |
| 7 | F-087 | P2 | Strengthen complete parameter type |

**Exit Criteria:** SDK quarantine complete, dead code removed, clean imports

---

### Phase 8: Provider Decomposition (~2 iterations)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | **F-065** | P2 | Provider decomposition |
| 2 | F-066 | P2 | Module boundaries |
| 3 | F-068 | P2 | Documentation |

**Exit Criteria:** Provider.py ≤300 lines, modules have clear boundaries

---

### Phase 9: Test & Packaging Polish (~1-2 iterations)

| Order | Feature | Priority | Description |
|-------|---------|----------|-------------|
| 1 | F-062 | P2 | Architecture test hardening |
| 2 | F-076 | P3 | Async mock warning fix |
| 3 | F-083 | P3 | Enum type fix |
| 4 | F-091 | P1 | Ephemeral session tests |
| 5 | F-064 | P2 | PyPI readiness |
| 6 | F-080 | P2 | Bundle.md metadata |

**Exit Criteria:** All tests pass, package ready for PyPI

---

## Critical Invariants (NEVER VIOLATE)

1. **Deny Hook Always Installed** — SDK session MUST have deny hook before any tool execution
2. **SDK Quarantine** — All SDK imports through `_imports.py`, no direct SDK imports elsewhere
3. **Three-Medium Architecture** — Python=mechanism, YAML=policy, Markdown=contracts
4. **Kernel Types Only** — Use `amplifier_core.llm_errors` types, no custom exceptions
5. **Contract Traceability** — Every test traces to a contract clause

---

## Kernel Type Reference (Quick Reference)

```python
# Correct imports
from amplifier_core.llm_errors import (
    LLMError, RateLimitError, AuthenticationError, ContextLengthError,
    ContentFilterError, InvalidRequestError, ProviderUnavailableError,
    LLMTimeoutError, NotFoundError, StreamError, AbortError,
    InvalidToolCallError, ConfigurationError
)

# WRONG — these don't exist
# LLMProviderError ❌
# ProviderError ❌
# CustomProviderException ❌
```

---

## Dev-Machine Commands

```bash
# Start the machine (run all phases)
cd /home/mowrim/projects/next-get-provider-github-copilot
amplifier recipe execute .dev-machine/build.yaml

# Run a single iteration
amplifier recipe execute .dev-machine/iteration.yaml

# Fix build/test errors
amplifier recipe execute .dev-machine/health-check.yaml

# Check current status
cat STATE.yaml | head -20
```

---

## Enforcement Scripts

All 4 scripts integrated with `tightened-iteration.yaml`:

| Script | Purpose | Threshold |
|--------|---------|-----------|
| `check-loc.py` | Python LOC limit | ≤300 lines per file |
| `check-hardcoded-policy.py` | Policy in config, not code | Zero hardcoded values |
| `check-magicmock.py` | No MagicMock in tests | Zero MagicMock usage |
| `check-contract-coverage.py` | Contract traceability | 100% MUST clauses covered |

---

## Ready for Execution

The dev-machine has all information needed to implement all 41 features across 9 phases:

- ✅ Constitution (AMPLIFIER-DIRECTIVE v1.2)
- ✅ Architectural guidance (PHASE-ARCHITECTURE-NOTES.md)
- ✅ Kernel compliance (KERNEL-COMPLIANCE-CHECKLIST.md)
- ✅ Dependency ordering (DEPENDENCY-GRAPH-PHASE9.md)
- ✅ Enforcement scripts verified

**Start the machine when ready.**
