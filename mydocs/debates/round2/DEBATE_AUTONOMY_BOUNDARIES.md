# DEBATE ROUND 2: Autonomy Boundaries — The Decision Tree

**Author**: The Zen Architect  
**Date**: 2026-03-08  
**Status**: Round 2 Position Paper  
**Context**: Builds on Round 1 Golden Vision Draft (Section 4: Autonomous Development Machine, Section 7: Self-Healing Design)

---

## Preamble: Why This Matters

Autonomy without boundaries is recklessness. Boundaries without autonomy is bureaucracy. The entire value proposition of an AI-maintained provider — one that detects SDK changes, adapts its own code, heals its own breakages — collapses if we get the boundary wrong in either direction. Too much autonomy and we deploy broken code at machine speed. Too little autonomy and we've built an expensive linter that still needs a human for every commit.

The Round 1 vision established that this provider is designed for AI-primary maintenance. But "AI-primary" is not "AI-only." The question this document answers is: **where exactly does the AI stop and the human start?**

The answer is not a spectrum. It is a decision tree with concrete detection criteria, confidence thresholds, and escalation paths. An AI agent executing a recipe should be able to walk this tree at every decision point and know — with zero ambiguity — whether to proceed or pause.

---

## The Four Tiers of Autonomy

### Tier 1: FULL AUTONOMY — AI Proceeds Without Human Involvement

**Definition**: The AI agent executes, validates, and commits without any human review. The human learns about the change after it lands, through logs, dashboards, or notification digests.

**What belongs here:**

| Action | Example | Why It's Safe |
|--------|---------|---------------|
| **Formatting and style fixes** | Running `ruff format`, fixing import order, normalizing whitespace | Zero semantic change. Deterministic tools. Reversible in one command. |
| **Dependency version pinning (patch)** | `copilot-sdk 0.2.1 → 0.2.2` when all canary tests pass | Patch versions are bug fixes by semver contract. Canary suite validates compatibility. Rollback is instant. |
| **Canary test execution** | Running the SDK assumption test suite on schedule or trigger | Read-only operation. Produces a report. No code changes. |
| **Test suite execution** | Running the full test suite as part of CI | Read-only validation. No code changes. |
| **Documentation regeneration** | Regenerating API docs from module docstrings and contracts | Generated output. Source of truth is code. Regeneration is idempotent. |
| **Cache invalidation** | Clearing the model metadata cache after SDK version change | Stateless operation. Cache rebuilds on next request. |
| **Health check responses** | Restarting CLI subprocess after health check failure | Operational recovery. Already designed for automatic restart. No code change. |
| **Metrics collection and emission** | Emitting OTEL traces, updating streaming metrics | Observability is append-only. Cannot corrupt application state. |
| **Log level adjustment** | Increasing debug logging during incident investigation | Reversible configuration change. No behavioral impact. |
| **Type stub regeneration** | Regenerating `.pyi` stubs from implementation | Derived artifact. Source of truth is the implementation. |

**Detection criteria — ALL must be true:**

```
IS_FULL_AUTONOMY(action) → boolean:
  action.changes_behavior == false
  AND action.changes_public_interface == false
  AND action.is_reversible_in_under_60_seconds == true
  AND action.affects_security == false
  AND action.blast_radius_files <= 3
  AND action.has_deterministic_validation == true
  AND action.validation_passes == true
```

**Confidence threshold**: Not applicable. These actions are validated by deterministic tooling (linters, test suites, type checkers), not by AI judgment. If the tool says it's clean, it's clean.

**Escalation path**: If any detection criterion fails, the action moves to Tier 2. There is no "maybe" — the criteria are binary.

**Concrete workflow:**

```
1. AI detects trigger (schedule, event, CI signal)
2. AI executes action
3. AI runs deterministic validation (tests, linter, type check)
4. IF validation passes → commit, log, notify digest
5. IF validation fails → DO NOT commit, escalate to Tier 2
```

---

### Tier 2: SEMI-AUTONOMY — AI Writes, Human Approves Before Merge

**Definition**: The AI agent writes the code, runs all validations, and produces a complete PR with evidence. A human reviews and approves before merge. The AI does the work; the human provides the judgment gate.

**What belongs here:**

| Action | Example | Why It Needs Review |
|--------|---------|---------------------|
| **Bug fixes with clear reproduction** | Fix for the 305-turn loop bug: change circuit breaker threshold | Behavioral change. Even with tests passing, a human should verify the fix matches the intent. |
| **SDK minor version adaptation (auto-healed)** | SDK 0.2.x → 0.3.0: field rename `message.text → message.content`, AI generates mapping | Auto-heal succeeded, but behavioral change crosses module boundaries. Human verifies the mapping is semantically correct, not just syntactically valid. |
| **Type change adaptations** | SDK renames `CopilotEvent → CopilotStreamEvent`, AI updates all references | Mechanical change, but touches many files. Human verifies completeness and that no semantic drift occurred. |
| **New test additions** | AI writes new canary tests after discovering undocumented SDK behavior | Tests are specifications. Adding a test is adding a contract. Human should agree with the contract. |
| **Policy value changes** | Changing circuit breaker threshold from 3 to 5 turns based on observed data | Policy changes affect user experience. Even data-driven changes need human judgment. |
| **Performance optimizations** | AI identifies and implements a caching optimization in model_cache.py | Optimization trades one resource for another. Human verifies the trade-off is acceptable. |
| **Error message changes** | Improving error messages based on user feedback patterns | User-facing text requires human judgment about tone, clarity, and completeness. |
| **Adapter shim generation** | AI generates a compatibility shim for a behavioral SDK change | Shims are technical debt by design. Human must approve the debt and its expiry timeline. |
| **Configuration schema changes** | Adding a new configuration key for a newly extracted policy | Schema changes are public API changes. Even additive ones can break consumers. |
| **Dependency version bumps (minor)** | `copilot-sdk 0.2.x → 0.3.0` when canary tests pass but behavioral tests show minor differences | Minor versions can add features and change non-breaking behavior. Canary tests may not catch everything. |

**Detection criteria — ANY triggers Tier 2:**

```
IS_SEMI_AUTONOMY(action) → boolean:
  action.changes_behavior == true
  AND action.blast_radius_files <= 10
  AND action.blast_radius_percent <= 30%
  AND action.has_complete_test_coverage == true
  AND action.all_tests_pass == true
  AND action.changes_public_interface == false OR action.interface_change_is_additive == true
  AND action.affects_security == false
  AND action.auto_heal_confidence >= 0.8
```

**Confidence threshold**: **0.8 (80%)**. The AI must express confidence that its change is correct. Confidence is measured by:

- **Test coverage**: Every changed line has a corresponding test assertion
- **Behavioral equivalence**: Before/after behavioral contract tests produce identical results for identical inputs
- **Blast radius containment**: Changes are localized to the expected modules
- **Precedent match**: The change pattern matches a previously successful adaptation (from the knowledge base)

If confidence is below 0.8 but above 0.5, the AI still produces the PR but flags it as **LOW CONFIDENCE** with specific concerns listed. The human reviewer knows to scrutinize more carefully.

If confidence is below 0.5, the action escalates to Tier 3.

**Escalation path:**

```
IF auto_heal_confidence < 0.5 → escalate to Tier 3
IF blast_radius_percent > 30% → escalate to Tier 3
IF changes_public_interface AND NOT additive → escalate to Tier 3
IF affects_security → escalate to Tier 4
IF human rejects PR → AI captures rejection reason, updates knowledge base, 
                       may retry with different approach (max 2 retries)
```

**Concrete workflow:**

```
1. AI detects trigger (canary failure, bug report, SDK update, recipe step)
2. AI analyzes the problem, identifies affected modules
3. AI writes the fix/adaptation on a branch
4. AI runs full validation suite (unit + behavioral + property + integration)
5. AI calculates confidence score
6. AI creates PR with:
   - Problem description
   - Change summary
   - Confidence score and rationale
   - Test results (all green or explicitly noted failures)
   - Before/after behavioral comparison
   - Rollback instructions
7. Human reviews and approves/rejects
8. IF approved → merge, update knowledge base with success
9. IF rejected → capture reason, update knowledge base, optionally retry
```

**What the PR must contain (non-negotiable):**

Every AI-generated PR includes a structured evidence block:

```markdown
## AI Change Evidence

**Trigger**: [What caused this change]
**Confidence**: [0.0-1.0] — [Rationale]
**Blast Radius**: [N files, M lines, P% of codebase]
**Tests**: [X passed, Y failed, Z new]
**Behavioral Equivalence**: [Yes/No — if No, explain what changed]
**Rollback**: `git revert <sha>` or `pip install copilot-sdk==<previous>`
**Precedent**: [Link to similar past change, or "No precedent"]
**Knowledge Base Entry**: [Auto-generated entry ID for tracking]
```

---

### Tier 3: GATED AUTONOMY — Human Designs, AI Implements

**Definition**: The AI cannot proceed without human architectural guidance. The AI may analyze the problem, propose options, and prototype solutions, but a human must make the design decision before the AI implements. The AI does the heavy lifting; the human provides the direction.

**What belongs here:**

| Action | Example | Why It Needs Human Design |
|--------|---------|---------------------------|
| **New module creation** | Adding a `retry/` module for retry policy extraction | New modules change the dependency DAG. Architectural decision about where responsibility lives. |
| **Interface changes (non-additive)** | Changing the `ToolCaptureStrategy` protocol to support multi-turn capture | Protocol changes ripple through all implementations. Breaking change to internal contracts. |
| **SDK major version adaptation** | SDK 0.x → 1.0: fundamental API redesign | Major versions can change paradigms. Auto-heal is explicitly not designed for this. |
| **New integration points** | Adding support for a new SDK hook type (e.g., `onModelSwitch`) | Integration points are architectural joints. Wrong placement creates coupling debt. |
| **Cross-module refactoring** | Splitting `streaming/accumulator.py` into separate text and tool accumulators | Module decomposition decisions define the system's bones. AI shouldn't restructure bones alone. |
| **Error handling strategy changes** | Switching from exception-based to Result-type error handling | Paradigm shifts affect every module. Design decision, not implementation decision. |
| **New recipe creation** | Creating a recipe for "provider health dashboard generation" | Recipes encode process. Process decisions are organizational, not technical. |
| **Dependency additions** | Adding a new library (e.g., `tenacity` for retry logic) | Every dependency is a long-term commitment. Supply chain risk assessment required. |
| **Breaking changes to config schema** | Removing or renaming a configuration key | Breaking changes to public APIs need migration planning. |
| **Multi-module behavioral changes** | Changing how the event bridge classifies SDK events (BRIDGE/CONSUME/DROP) | Classification decisions affect observability, debugging, and system understanding. |

**Detection criteria — ANY triggers Tier 3:**

```
IS_GATED_AUTONOMY(action) → boolean:
  action.creates_new_module == true
  OR action.changes_dependency_dag == true
  OR action.changes_non_additive_interface == true
  OR action.blast_radius_percent > 30%
  OR action.adds_new_dependency == true
  OR action.changes_error_handling_paradigm == true
  OR action.creates_new_recipe == true
  OR action.is_major_version_adaptation == true
  OR action.auto_heal_confidence < 0.5
  OR action.requires_new_abstraction == true
  OR (action.retry_count >= 2 AND action.previous_attempts_rejected == true)
```

**Confidence threshold**: Not applicable in the traditional sense. The AI's confidence in its *analysis* should be high (>0.8), but confidence in the *correct design choice* is explicitly acknowledged as insufficient. The AI presents options; the human chooses.

**What the AI provides to the human:**

```markdown
## Design Decision Required

**Problem**: [Clear problem statement]
**Impact**: [What breaks or degrades if we do nothing]
**Urgency**: [Immediate / This sprint / Backlog]

### Option A: [Name]
- Approach: [Description]
- Pros: [List]
- Cons: [List]
- Blast radius: [Files/modules affected]
- Estimated complexity: [Low/Medium/High]
- Precedent: [Similar decisions in this or other projects]

### Option B: [Name]
- [Same structure]

### Option C: Do Nothing
- Risk: [What happens if we defer]
- Timeline: [How long can we defer safely]

### AI Recommendation
[Which option and why, with explicit statement of uncertainty]

### What I Need From You
[Specific decision points: "Choose A, B, or C" / "Approve the interface change" / etc.]
```

**Escalation path:**

```
IF human doesn't respond within SLA → reminder at 24h, 48h, then auto-pin to 
   last-known-good and create HIGH priority issue
IF human chooses an option → AI implements (may produce Tier 2 PR for review)
IF human rejects all options → AI captures constraints, re-analyzes with 
   new constraints, presents new options (max 2 re-analysis cycles)
IF re-analysis fails → issue stays open, system runs on last-known-good
```

**Concrete workflow:**

```
1. AI detects trigger (failing adaptation, new requirement, architectural gap)
2. AI performs deep analysis:
   - Reads all affected modules
   - Maps dependency impact
   - Identifies 2-3 viable approaches
   - Prototypes each approach (may write spike code)
3. AI creates Design Decision Issue with structured format above
4. AI STOPS and waits for human input
5. Human provides direction (choice, modification, or rejection)
6. AI implements chosen direction
7. AI creates Tier 2 PR for the implementation
8. Normal Tier 2 review process applies
```

---

### Tier 4: NEVER AUTONOMOUS — Human-Only Territory

**Definition**: The AI must not take these actions under any circumstances. The AI may provide analysis, recommendations, and tooling support, but the action itself must be performed by a human or explicitly authorized by a human with full understanding of consequences.

**What belongs here:**

| Action | Example | Why It's Never Autonomous |
|--------|---------|---------------------------|
| **Security-related changes** | Modifying authentication flow, credential handling, token management | Security bugs can expose user data. The cost of a wrong AI decision is catastrophic and potentially irreversible. |
| **Production deployment** | Deploying a new provider version to production | Deployment affects all users simultaneously. Human must verify readiness. |
| **Data deletion or migration** | Dropping a cache schema, migrating stored model metadata | Data loss is irreversible. Even with backups, restoration has cost. |
| **License or legal changes** | Adding a GPL dependency, changing license headers | Legal implications require human judgment and potentially legal review. |
| **Access control changes** | Modifying who can approve PRs, changing CI permissions | Trust boundary changes. Meta-level changes to the autonomy system itself. |
| **Autonomy boundary changes** | Modifying THIS document or the detection criteria | Self-modifying autonomy rules is a recursive trust problem. Humans must own the rules about rules. |
| **Rollback of human-approved changes** | Reverting a change that a human explicitly approved | Overriding human judgment requires human authorization. |
| **External API contract changes** | Changing the Provider Protocol's 5-method interface | Provider Protocol is defined by the Amplifier kernel. Changes affect all providers, not just this one. |
| **Secrets management** | Rotating API keys, updating credential stores | Secrets are the keys to the kingdom. One mistake = breach. |
| **Incident response decisions** | Deciding whether to page on-call, declare an incident | Organizational decisions with human communication implications. |
| **Removing safety mechanisms** | Disabling the circuit breaker, removing the preToolUse deny hook | Safety mechanisms are the guardrails that make autonomy possible. Removing them requires meta-level trust. |
| **Cross-system changes** | Changes that affect both the provider AND the Amplifier kernel | Blast radius extends beyond the AI's domain of understanding. |

**Detection criteria — ANY triggers Tier 4:**

```
IS_NEVER_AUTONOMOUS(action) → boolean:
  action.affects_security == true
  OR action.is_production_deployment == true
  OR action.deletes_or_migrates_data == true
  OR action.changes_legal_status == true
  OR action.changes_access_control == true
  OR action.modifies_autonomy_rules == true
  OR action.overrides_human_decision == true
  OR action.changes_external_api_contract == true
  OR action.manages_secrets == true
  OR action.is_incident_response_decision == true
  OR action.removes_safety_mechanism == true
  OR action.crosses_system_boundary == true
```

**Confidence threshold**: **Irrelevant.** Even if the AI is 100% confident, these actions are never autonomous. Confidence does not override the categorical prohibition.

**Escalation path**: These actions are not "escalated" — they are *inherently human*. The AI's role is to:

1. **Detect** that the action falls in Tier 4
2. **Refuse** to proceed autonomously
3. **Provide** all relevant analysis and recommendations
4. **Prepare** everything the human needs to act quickly
5. **Wait** for explicit human authorization

**What the AI provides to the human:**

```markdown
## Human Action Required (Tier 4 — Never Autonomous)

**Action needed**: [Specific action]
**Why this is Tier 4**: [Which criterion triggered]
**Risk if delayed**: [Impact assessment]
**Risk if done wrong**: [Worst-case scenario]

### AI Analysis
[Complete analysis of the situation]

### AI Recommendation
[What the AI would do if it could, with full reasoning]

### Prepared Artifacts
- [ ] [Script/command ready to execute]
- [ ] [Rollback plan prepared]
- [ ] [Validation steps documented]

### Decision Required
[Exact yes/no question for the human]
```

---

## The Master Decision Tree

This is the algorithm an AI agent follows at every decision point:

```
CLASSIFY_ACTION(action) → Tier:

  // Tier 4 checks FIRST — these are hard stops
  IF action.affects_security → TIER_4
  IF action.is_production_deployment → TIER_4
  IF action.deletes_or_migrates_data → TIER_4
  IF action.changes_legal_status → TIER_4
  IF action.changes_access_control → TIER_4
  IF action.modifies_autonomy_rules → TIER_4
  IF action.overrides_human_decision → TIER_4
  IF action.changes_external_api_contract → TIER_4
  IF action.manages_secrets → TIER_4
  IF action.is_incident_response_decision → TIER_4
  IF action.removes_safety_mechanism → TIER_4
  IF action.crosses_system_boundary → TIER_4

  // Tier 3 checks SECOND — architectural decisions
  IF action.creates_new_module → TIER_3
  IF action.changes_dependency_dag → TIER_3
  IF action.changes_non_additive_interface → TIER_3
  IF action.blast_radius_percent > 30% → TIER_3
  IF action.adds_new_dependency → TIER_3
  IF action.changes_error_handling_paradigm → TIER_3
  IF action.creates_new_recipe → TIER_3
  IF action.is_major_version_adaptation → TIER_3
  IF action.auto_heal_confidence < 0.5 → TIER_3
  IF action.requires_new_abstraction → TIER_3
  IF action.retry_count >= 2 AND action.previous_rejected → TIER_3

  // Tier 1 checks THIRD — fully autonomous only if ALL criteria met
  IF action.changes_behavior == false
     AND action.changes_public_interface == false
     AND action.is_reversible_in_under_60_seconds == true
     AND action.blast_radius_files <= 3
     AND action.has_deterministic_validation == true
     AND action.validation_passes == true
     → TIER_1

  // Everything else is Tier 2
  → TIER_2
```

**Key design property**: The tree is evaluated top-down. Tier 4 always wins. An action that is both "security-related" and "auto-healable" is Tier 4, full stop. Tier 1 requires ALL criteria to be true — it's the strictest positive match. Tier 2 is the default bucket for anything that doesn't fit cleanly elsewhere. **When in doubt, escalate.**

---

## Applying the Decision Tree to Recipe Steps

Each of the five core recipes from the Golden Vision has steps that map to different tiers:

### Recipe 1: Provider Implementation (TDD Flow)

| Step | Tier | Rationale |
|------|------|-----------|
| `analyze-sdk-interface` | 1 | Read-only analysis, no code changes |
| `generate-test-suite` | 2 | Tests are specifications; human approves the contracts |
| `scaffold-provider` | 3 | Creates new modules; architectural decision |
| `implement-provider` | 2 | Behavioral code change; needs review |
| `convergence-test-loop` | 1 | Iterative execution of tests; read-only validation |
| `refactor-pass` | 2 | Behavioral preservation required; human verifies |

### Recipe 2: SDK Assumption Validation

| Step | Tier | Rationale |
|------|------|-----------|
| `extract-assumptions` | 1 | Analysis only |
| `generate-validation-tests` | 2 | New tests = new contracts |
| `run-validations` | 1 | Read-only execution |
| `impact-analysis` | 1 | Report generation |

### Recipe 3: Integration Testing (Staged)

| Step | Tier | Rationale |
|------|------|-----------|
| `setup-test-env` | 1 | Infrastructure setup, deterministic |
| `smoke-test` | 1 | Read-only validation |
| `APPROVAL GATE` | 3 | Human decides if full suite should run |
| `full-test-suite` | 1 | Read-only validation |
| `report` | 1 | Report generation |

### Recipe 4: Release Validation

| Step | Tier | Rationale |
|------|------|-----------|
| `type-check + lint + test + security` | 1 | Deterministic validation |
| `HUMAN REVIEW GATE` | 4 | Production deployment decision |
| `publish` | 4 | Production deployment action |

### Recipe 5: SDK Upgrade Adaptation

| Step | Tier | Rationale |
|------|------|-----------|
| `check-sdk-updates` | 1 | Read-only check |
| `diff-analysis` | 1 | Analysis only |
| `APPROVAL GATE (breaking)` | 3 | Architectural decision for breaking changes |
| `run-assumption-tests` | 1 | Read-only validation |
| `auto-adapt` | 2 | Behavioral change; needs review |
| `escalate` | 3 | AI couldn't auto-heal; needs human design |
| `validate` | 1 | Read-only validation |
| `deploy` | 4 | Production deployment |
| `rollback` | 4 | Overriding a previous deployment decision |

---

## Edge Cases and Ambiguity Resolution

### Edge Case 1: The "Simple" Fix That Isn't

**Scenario**: AI identifies a typo in an error message. Seems like Tier 1 (formatting fix). But the error message is user-facing and parsed by downstream tools.

**Resolution**: The detection criterion `action.changes_behavior == false` catches this. If any consumer parses the error message string, changing it IS a behavioral change. The AI should check: does any test assert on the exact error string? If yes → Tier 2. If no → still Tier 2, because user-facing text always requires human judgment about clarity and tone.

**Rule**: When in doubt about whether something "changes behavior," assume it does. The cost of an unnecessary review is minutes. The cost of a missed behavioral change is an incident.

### Edge Case 2: The Cascading Canary Failure

**Scenario**: SDK patch version 0.2.3 causes 12 canary tests to fail. Each individual failure is a Type 1 (shape change) that would be Tier 2. But 12 simultaneous failures suggest something deeper.

**Resolution**: Blast radius check catches this. 12 failing tests likely means >30% of the assumption suite is affected, which triggers Tier 3. Even if each fix is mechanical, the pattern suggests a paradigm shift that needs human assessment.

**Rule**: `blast_radius` is measured not just by files changed but by tests failed. If more than 30% of any test category fails simultaneously, escalate one tier regardless of individual fix simplicity.

### Edge Case 3: The Confident Wrong Answer

**Scenario**: AI adapts to an SDK change with 0.95 confidence. All tests pass. But the AI's mapping is subtly wrong — it mapped a field to a semantically different field with the same type.

**Resolution**: This is why Tier 2 exists. High confidence does not bypass human review for behavioral changes. The PR evidence block includes before/after behavioral comparison, which a human reviewer can use to spot semantic drift.

**Rule**: Confidence thresholds determine the *urgency* and *scrutiny level* of human review, not whether review happens. A 0.95 confidence PR gets a lighter review than a 0.6 confidence PR, but both get reviewed.

### Edge Case 4: The Emergency Hotfix

**Scenario**: Production is down because the SDK pushed a breaking change. The AI can fix it in 30 seconds. Waiting for human review means extended downtime.

**Resolution**: The AI applies the fix to a branch and creates the PR, but also **pins to last-known-good immediately** (Tier 1 — rollback is always autonomous). Production recovers via rollback. The fix PR goes through normal Tier 2 review. Downtime is minimized by rollback, not by bypassing review.

**Rule**: Rollback is always faster than fix-forward. The autonomy system is designed so that Tier 1 rollback + Tier 2 fix is always faster than trying to shortcut a Tier 2 action into Tier 1 under pressure.

### Edge Case 5: Accumulated Drift

**Scenario**: Over 6 months, the AI has made 47 Tier 2 changes, each individually approved. But the cumulative effect has drifted the architecture away from the original design.

**Resolution**: This is addressed by periodic Tier 3 "architectural review" gates. Every 20 merged AI PRs (configurable), the system triggers a mandatory Tier 3 review where a human assesses cumulative drift. The AI prepares a summary of all changes, module size evolution, dependency graph changes, and test coverage trends.

**Rule**: Individual correctness does not guarantee cumulative correctness. Scheduled architectural reviews are a Tier 3 gate that no number of successful Tier 2 changes can bypass.

---

## Confidence Calibration

AI confidence is only useful if it's calibrated — meaning a stated 80% confidence should be correct ~80% of the time. The system calibrates through feedback loops:

**Calibration mechanism:**

```
FOR each completed Tier 2 PR:
  record(stated_confidence, actual_outcome)
  // actual_outcome = {approved_no_changes, approved_with_changes, rejected}

WEEKLY:
  calibration_score = correlation(stated_confidence, approval_rate)
  IF calibration_score < 0.7:
    ALERT: "AI confidence is poorly calibrated"
    ACTION: Adjust confidence thresholds upward (require higher confidence)
  IF calibration_score > 0.9:
    CONSIDER: Lowering review burden for high-confidence changes (but never to Tier 1)
```

**What "confidence" actually measures:**

| Component | Weight | How It's Measured |
|-----------|--------|-------------------|
| Test coverage of changed lines | 30% | Coverage tool output |
| Behavioral equivalence verification | 25% | Before/after contract test comparison |
| Precedent match from knowledge base | 20% | Similarity score to past successful adaptations |
| Blast radius containment | 15% | % of codebase affected |
| Pattern complexity | 10% | Cyclomatic complexity of the change |

Confidence is **never** self-assessed by the AI's "feeling." It is computed from measurable signals. An AI that says "I'm 95% confident" but has 40% test coverage of changed lines gets a computed confidence of ~0.5, regardless of its self-assessment.

---

## Implementation: How the Decision Tree Becomes Code

The decision tree is not a document that agents read and interpret. It is a **runtime function** that recipe steps call:

```python
@dataclass
class ActionClassification:
    tier: Literal[1, 2, 3, 4]
    confidence: float  # 0.0-1.0, only meaningful for Tier 2
    rationale: str
    escalation_target: str  # "none", "pr_review", "design_issue", "human_only"
    blocking_criteria: list[str]  # which criteria triggered this tier

def classify_action(action: ActionDescriptor) -> ActionClassification:
    """Walk the decision tree. Tier 4 first, Tier 1 last. Default to Tier 2."""
    
    # Tier 4 — hard stops
    tier4_checks = [
        (action.affects_security, "security_related"),
        (action.is_production_deployment, "production_deployment"),
        (action.deletes_or_migrates_data, "data_deletion"),
        (action.changes_legal_status, "legal_change"),
        (action.changes_access_control, "access_control"),
        (action.modifies_autonomy_rules, "autonomy_rules"),
        (action.overrides_human_decision, "human_override"),
        (action.changes_external_api_contract, "external_api"),
        (action.manages_secrets, "secrets"),
        (action.is_incident_response_decision, "incident_response"),
        (action.removes_safety_mechanism, "safety_mechanism"),
        (action.crosses_system_boundary, "cross_system"),
    ]
    blocking = [name for check, name in tier4_checks if check]
    if blocking:
        return ActionClassification(
            tier=4, confidence=0.0, 
            rationale=f"Tier 4: {', '.join(blocking)}",
            escalation_target="human_only",
            blocking_criteria=blocking,
        )
    
    # Tier 3 — architectural gates
    tier3_checks = [
        (action.creates_new_module, "new_module"),
        (action.changes_dependency_dag, "dependency_dag"),
        (action.changes_non_additive_interface, "interface_change"),
        (action.blast_radius_percent > 30, "blast_radius"),
        (action.adds_new_dependency, "new_dependency"),
        (action.changes_error_handling_paradigm, "error_paradigm"),
        (action.creates_new_recipe, "new_recipe"),
        (action.is_major_version_adaptation, "major_version"),
        (action.auto_heal_confidence < 0.5, "low_confidence"),
        (action.requires_new_abstraction, "new_abstraction"),
        (action.retry_count >= 2 and action.previous_rejected, "repeated_rejection"),
    ]
    blocking = [name for check, name in tier3_checks if check]
    if blocking:
        return ActionClassification(
            tier=3, confidence=0.0,
            rationale=f"Tier 3: {', '.join(blocking)}",
            escalation_target="design_issue",
            blocking_criteria=blocking,
        )
    
    # Tier 1 — full autonomy (ALL criteria must pass)
    tier1_criteria = [
        (not action.changes_behavior, "no_behavior_change"),
        (not action.changes_public_interface, "no_interface_change"),
        (action.is_reversible_in_under_60_seconds, "fast_reversible"),
        (action.blast_radius_files <= 3, "small_blast_radius"),
        (action.has_deterministic_validation, "deterministic_validation"),
        (action.validation_passes, "validation_passes"),
    ]
    all_pass = all(check for check, _ in tier1_criteria)
    if all_pass:
        return ActionClassification(
            tier=1, confidence=1.0,
            rationale="Tier 1: all autonomy criteria met",
            escalation_target="none",
            blocking_criteria=[],
        )
    
    # Default: Tier 2
    confidence = compute_confidence(action)
    return ActionClassification(
        tier=2, confidence=confidence,
        rationale=f"Tier 2: behavioral change with {confidence:.0%} confidence",
        escalation_target="pr_review",
        blocking_criteria=[name for check, name in tier1_criteria if not check],
    )
```

---

## The Social Contract

This decision tree encodes a social contract between humans and AI agents:

**The AI promises to:**
1. Never bypass Tier 4 restrictions, regardless of urgency or confidence
2. Always provide complete evidence for Tier 2 changes
3. Present honest options (not just its preferred option) for Tier 3 decisions
4. Escalate immediately when detection criteria trigger, not after attempting a fix
5. Record every decision, outcome, and learning for calibration
6. Default to the higher tier when classification is ambiguous

**The human promises to:**
1. Review Tier 2 PRs within agreed SLA (default: 24 hours)
2. Respond to Tier 3 design decisions within agreed SLA (default: 48 hours)
3. Provide clear, specific feedback when rejecting AI work (not just "no")
4. Not blame the AI for Tier 2 changes that pass review — review is shared responsibility
5. Periodically audit the decision tree itself (quarterly) to adjust boundaries based on evidence
6. Trust the AI within its authorized tiers — don't micromanage Tier 1 actions

**The system promises to:**
1. Always have a rollback path (last-known-good pinning)
2. Never deploy without human authorization (Tier 4)
3. Degrade gracefully when humans are unavailable (pin and wait)
4. Improve over time through calibrated confidence and knowledge base growth
5. Make the autonomy boundary visible — every action's tier classification is logged and auditable

---

## Summary: The One-Page Reference

| Tier | Name | Who Decides | Examples | Confidence Required | Escalation If Wrong |
|------|------|-------------|----------|--------------------|--------------------|
| **1** | Full Autonomy | AI alone | Formatting, cache clear, test runs, patch pins | N/A (deterministic) | → Tier 2 |
| **2** | Semi-Autonomy | AI writes, human approves | Bug fixes, minor adaptations, policy tweaks | ≥ 0.8 | → Tier 3 (if < 0.5) |
| **3** | Gated Autonomy | Human designs, AI implements | New modules, major SDK versions, architecture | N/A (human decides) | → Tier 4 (if security) |
| **4** | Never Autonomous | Human only | Security, deployment, secrets, legal, data | Irrelevant | System halts |

**The golden rule**: When the tier is ambiguous, go up. The cost of unnecessary escalation is time. The cost of insufficient escalation is trust.

---

*This document is itself a Tier 4 artifact. Changes to autonomy boundaries require human review and approval. The AI may propose changes to this document but must never apply them autonomously.*
