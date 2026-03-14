# Enforcement Framework: Textbook-Perfect Implementation Standards

**Status**: ACTIVE — All new features MUST comply  
**Version**: 1.0  
**Created**: 2026-03-14  
**Authority**: 6-Agent Expert Panel (zen-architect, integration-specialist, amplifier-expert, explorer, bug-hunter, recipe-author)

---

## Executive Summary

This framework establishes the enforcement standards that will prevent F-044/F-045 class bugs from ever recurring. It synthesizes findings from 6 expert agents into actionable governance for the autonomous development machine.

**The Core Problem We're Solving**:
- F-044 and F-045 survived 42 feature implementations
- TDD was applied to internal code, not SDK boundary
- MagicMock forgiveness let wrong values pass
- Tests codified bugs instead of catching them

**The Solution**:
- 6 pre/post implementation gates
- 5-expert quorum approval for every feature
- ConfigCapturingMock to replace MagicMock forgiveness
- Contract anchors for every MUST clause
- Tightened recipes with enforcement scripts

---

## Part 1: Gate Architecture

### Pre-Implementation Gates

| Gate | Name | What Must Exist | Enforcement |
|------|------|-----------------|-------------|
| **G-0** | Contract Anchor | Feature spec has `contract:Section:MUST:N` anchors | Recipe checks spec format |
| **G-1** | RED Test | Failing test exists for each acceptance criterion | Recipe verifies test failure |

### Post-Implementation Gates

| Gate | Name | What Is Checked | Enforcement |
|------|------|-----------------|-------------|
| **G-2** | Boundary Contract | SDK boundary tests pass | `pytest tests/test_sdk_boundary*.py` |
| **G-3** | Code Quality | LOC limits + no hardcoded policy + no MagicMock abuse | Enforcement scripts |
| **G-4** | Full Suite | All tests pass | `pytest tests/ -v` |
| **G-5** | Expert Quorum | 5/5 experts approve | Recipe-driven parallel review |

### Gate Failure Handling

```
Gate fails → Feature status = "blocked"
           → Blocker recorded in STATE.yaml
           → Machine cannot mark feature "done"
           → Fix loop until gate passes
           → Re-run only failed gates
```

---

## Part 2: Expert Quorum System

### The 5 Experts

| Seat | Role | Domain | What They Check |
|------|------|--------|-----------------|
| **1** | Architecture Guardian | Structural alignment | Module boundaries, LOC budgets, Three-Medium balance |
| **2** | Contract Auditor | Contract compliance | MUST clauses tested, protocol adherence |
| **3** | SDK Integration Specialist | SDK boundary correctness | available_tools=[], mode="replace", mock fidelity |
| **4** | Bug Hunter | Defect detection | Edge cases, error paths, MagicMock with spec= |
| **5** | Security Guardian | Security posture | Deny hooks intact, no credential exposure |

### Approval Requirements

- **Unanimous required**: 5/5 APPROVE
- **Any veto blocks**: Feature cannot be marked done
- **Veto findings**: Become fix requirements
- **Re-review**: Only vetoing experts re-review after fix
- **Deadlock rule**: 3 vetoes from same expert → human escalation

### Approval Artifact

```yaml
# .dev-machine/approvals/{feature_id}.yaml
feature: F-048
approved_at: "2026-03-14T07:00:00Z"
approval_round: 2
quorum:
  - expert: architecture-guardian
    verdict: APPROVE
    evidence: "All files under 400 LOC"
  - expert: contract-auditor
    verdict: APPROVE
    evidence: "All MUST clauses mapped to tests"
  # ... etc
```

### Commit Message Format

```
feat: implement F-048 config extraction

- AC-1: Extract model list to config/models.yaml
- AC-2: Reduce provider.py from 467 to 200 lines

Quorum: 5/5 (round 2)
Approval: .dev-machine/approvals/F-048.yaml

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```

---

## Part 3: Golden Vision Compliance

### Line Count Targets

| File | Target | Hard Limit | Current | Status |
|------|--------|------------|---------|--------|
| `provider.py` | ≤200 | 400 | 467 | 🔴 OVER |
| `error_translation.py` | ≤160 | 400 | 382 | 🟡 HIGH |
| `streaming.py` | ≤160 | 400 | 273 | 🟡 HIGH |
| `tool_parsing.py` | ≤120 | 400 | 91 | ✅ OK |
| `sdk_adapter/client.py` | ≤300 | 400 | 261 | ✅ OK |

### Required YAML Config Files

| File | Purpose | Status |
|------|---------|--------|
| `config/errors.yaml` | SDK error → domain error mappings | ✅ Exists (93 lines) |
| `config/events.yaml` | Event classification (BRIDGE/CONSUME/DROP) | ✅ Exists (46 lines) |
| `config/models.yaml` | Model capabilities and defaults | 🔴 MISSING |
| `config/retry.yaml` | Retry counts, backoff, jitter | 🔴 MISSING |
| `config/circuit-breaker.yaml` | Turn limits, timeouts | 🔴 MISSING |

### Three-Medium Balance

| Medium | Target | Current | Status |
|--------|--------|---------|--------|
| Python (mechanism) | ~670 lines | ~1,213 lines | 🔴 181% |
| YAML (policy) | ~160 lines | ~139 lines | 🟡 87% |
| Markdown (contracts) | ~400 lines | 8 contracts | ✅ Complete |

---

## Part 4: Test Infrastructure Standards

### ConfigCapturingMock (Replaces MagicMock)

```python
class ConfigCapturingMock:
    """Mock SDK client that captures and validates session config."""
    
    def __init__(self) -> None:
        self.captured_configs: list[dict[str, Any]] = []
    
    async def create_session(self, config: dict[str, Any]) -> Any:
        if not isinstance(config, dict):
            raise TypeError(f"Expected dict, got {type(config).__name__}")
        self.captured_configs.append(copy.deepcopy(config))
        return self._mock_session
    
    @property
    def last_config(self) -> dict[str, Any]:
        return self.captured_configs[-1]
```

### Test Markers

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "sdk_boundary: tests SDK boundary contract",
    "sdk_assumption: tests SDK type assumptions",
    "contract: tests linked to contract clauses",
    "live: requires real API credentials",
]
```

### Contract Anchor Format

```python
def test_available_tools_always_empty_list(self) -> None:
    """deny-destroy:ToolSuppression:MUST:1
    
    available_tools MUST be [] on every session.
    """
    config = mock_client.last_config
    assert config["available_tools"] == []
```

### Anti-Patterns to Detect

| Pattern | Why It's Bad | Enforcement Script |
|---------|--------------|-------------------|
| `MagicMock()` without `spec=` | Accepts anything | `check-magicmock-abuse.py` |
| `assert_called_once()` without args | Doesn't verify values | Manual review |
| `.__class__.__name__ == "..."` | String comparison fails silently | Manual review |
| Hardcoded mappings in Python | Should be YAML | `check-hardcoded-policy.py` |

---

## Part 5: Enforcement Scripts

### Location

All enforcement scripts live in `.dev-machine/enforcement/`:

```
.dev-machine/enforcement/
├── README.md
├── check-loc.py              # Line count enforcement
├── check-hardcoded-policy.py # Policy-in-Python detector
├── check-magicmock-abuse.py  # MagicMock forgiveness detector
└── check-contract-coverage.py # Contract anchor coverage
```

### Usage

```bash
# Run all enforcement checks
python .dev-machine/enforcement/check-loc.py
python .dev-machine/enforcement/check-hardcoded-policy.py
python .dev-machine/enforcement/check-magicmock-abuse.py
python .dev-machine/enforcement/check-contract-coverage.py

# Or via tightened recipe
amplifier recipe execute .dev-machine/tightened-iteration.yaml
```

### Exit Codes

- `0` = All checks pass
- `1` = Soft limit exceeded (warning)
- `2` = Hard limit exceeded (blocking)

---

## Part 6: Tightened Recipes

### Available Recipes

| Recipe | Purpose |
|--------|---------|
| `.dev-machine/tightened-iteration.yaml` | Single iteration with 6 gates |
| `.dev-machine/tightened-build.yaml` | Full build loop calling tightened iteration |

### Gate Flow in tightened-iteration.yaml

```yaml
steps:
  - name: pre-check-spec
    # G-0: Verify contract anchors in spec
    
  - name: pre-check-red-test
    # G-1: Verify failing test exists
    
  - name: implement
    # Working session implements feature
    
  - name: post-check-boundary
    # G-2: SDK boundary tests
    
  - name: post-check-quality
    # G-3: LOC + policy + MagicMock checks
    
  - name: post-check-suite
    # G-4: Full test suite
    
  - name: quorum-review
    # G-5: 5-expert parallel approval
    
  - name: mark-done
    # Only if all gates pass
```

### Running the Machine

```bash
# Single iteration with enforcement
amplifier recipe execute .dev-machine/tightened-iteration.yaml

# Full build loop
amplifier recipe execute .dev-machine/tightened-build.yaml
```

---

## Part 7: Implementation Backlog

### Critical (Must Complete Before Any New Features)

| Feature | Priority | Status | Purpose |
|---------|----------|--------|---------|
| **F-044** | P0 | ready | System prompt replace mode |
| **F-045** | P0 | ready | Disable SDK built-in tools |
| **F-046** | P0 | ready | SDK integration testing architecture |
| **F-047** | P0 | ready | Testing course correction |
| **F-048** | P0 | ready | Config extraction (reduce Python bloat) |

### Implementation Order

```
1. F-046 (test infrastructure) 
   ↓ Creates tests that catch F-044/F-045
2. F-044 + F-045 (fixes)
   ↓ Tests fail (RED), then pass (GREEN)
3. F-048 (config extraction)
   ↓ Reduces Python LOC to targets
4. All new features follow tightened process
```

---

## Part 8: Exception Process

### When Exceptions Are Allowed

- Hard limits cannot be met due to SDK constraints
- Contract clause is impossible to test without live credentials
- Security requirement conflicts with performance requirement

### How to Request Exception

1. Document in feature spec under `## Exception Request`
2. State: what rule, why exception, what mitigation
3. Submit to quorum review
4. **4/5 experts must approve exception** (higher bar)
5. Document approval in `.dev-machine/exceptions/{feature_id}.yaml`

### Exception Artifact

```yaml
# .dev-machine/exceptions/F-049.yaml
feature: F-049
exception_requested: "LOC limit for sdk_adapter/client.py"
reason: "SDK requires verbose error handling that cannot be extracted"
mitigation: "Split into client.py + client_errors.py"
approved_by: [architecture-guardian, contract-auditor, bug-hunter, security-guardian]
rejected_by: []
decision: APPROVED
conditions: ["client_errors.py must not exceed 200 LOC"]
```

---

## Summary: The Contract

By following this framework:

1. **No feature ships without 5 expert approvals**
2. **No test uses MagicMock without spec=**
3. **No Python file exceeds 400 lines (600 hard limit)**
4. **No policy is hardcoded in Python (use YAML)**
5. **No MUST clause exists without a test anchor**
6. **No feature is "done" without passing all 6 gates**

This is the textbook-perfect implementation standard. The autonomous development machine MUST comply.

---

*Expert Panel: zen-architect, integration-specialist, amplifier-expert, explorer, bug-hunter, recipe-author*
*Date: 2026-03-14*
