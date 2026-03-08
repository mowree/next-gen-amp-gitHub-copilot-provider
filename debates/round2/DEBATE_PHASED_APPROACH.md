# DEBATE ROUND 2: Phased Architecture — Simplicity Wins, Comprehensiveness Earns Its Way In

**Author**: The Zen Architect (Mediator)  
**Date**: 2026-03-08  
**Status**: Round 2 Mediation  
**Sources**: 26 documents across Waves 1-3, Golden Vision Draft, Skeptic Critique  
**Method**: YAGNI filter applied to every proposed feature — "What failure mode does this prevent?"

---

## The Core Tension

The debate has two poles:

**Team Comprehensive** (Observability Agent, Self-Healing Agent, Contract Agent, CI/CD Agent) proposes: 58-event bridge, OTEL spans, self-healing adaptation engine, 5 recipe pipelines, test evidence system, session replay, pattern recognition knowledge base, AI confidence scoring, compatibility matrix CI jobs, and a provider health dashboard.

**Team Simple** (Skeptic, Modular Architecture Agent, Synthesis Agent) counters: decompose `provider.py`, write contract tests, set up basic CI, pin SDK versions, and ship. Everything else is speculative infrastructure for problems that haven't materialized.

**My verdict**: Team Simple is right about *sequencing*. Team Comprehensive is right about *direction*. The fatal mistake would be building the autonomy layer before the provider reliably works. The second fatal mistake would be building the provider without the hooks that make future autonomy *possible*.

The resolution is phased delivery with a strict YAGNI gate: every feature must answer **"What failure mode does this prevent, and has that failure actually occurred or is it structurally inevitable?"**

---

## Phase 0: Minimum Viable Architecture (Now)

**Goal**: A decomposed, testable, CI-gated provider that works correctly and can be safely modified by AI agents.

**Duration**: This is the "stop debating and ship" phase.

### What We Build

#### 1. Decompose `provider.py` (1799 → ~300 lines)

**Failure mode prevented**: AI agents cannot safely edit a 1799-line file. Every modification risks unintended mutations to unrelated code. This is not speculative — it is a structural certainty given context window constraints.

Extract 5 modules following the Modular Architecture agent's phased plan:
1. `error_translation.py` (~200 lines) — SDK→Kernel error mapping
2. `tool_parsing.py` (~250 lines) — parse, detect fakes, repair missing results
3. `session_factory.py` (~250 lines) — session config building
4. `streaming.py` (~200 lines) — streaming event handler
5. `completion.py` (~350 lines) — LLM call lifecycle

**Flat package structure.** No nested subpackages. The Modular Architecture agent won this argument decisively: 17 flat modules with clear names beat 7 nested packages for a codebase this size. The existing 10 well-structured modules (`client.py`, `sdk_driver.py`, `converters.py`, etc.) remain unchanged.

**Layering rules enforced**: imports flow down only. `from __future__ import annotations` in every file. No circular dependencies. Coordinator reference passed via constructors, not module-level imports.

**Success criterion**: All existing tests pass with only import path changes. No module exceeds 400 lines (soft cap) or 600 lines (hard cap). Every common change touches ≤3 modules.

#### 2. SDK Contract Tests (Canary Suite)

**Failure mode prevented**: SDK changes silently break the provider. This is not speculative — the SDK is pre-1.0 and actively evolving. The Golden Vision correctly identifies this as the highest-probability risk.

Write assumption tests for every SDK surface we touch:
- **Type shape tests**: Do the types we import still exist with expected fields?
- **Function signature tests**: Do functions accept the arguments we pass?
- **Behavioral contract tests**: Does streaming produce events in expected format?
- **Error contract tests**: Do auth failures produce expected error types?

**What we do NOT build**: The full 58-event catalog, the evidence capture system, the baseline comparison engine, the test evidence JSON storage, or the regression detection pipeline. Those are Phase 1+ concerns. Right now we need ~20 focused canary tests that answer: "Does the SDK still behave as we expect?"

**The Self-Healing agent got this exactly right**: "The canary test suite IS the self-healing system. Everything else is automation around the fundamental act of knowing what you depend on and checking if it still holds true." We build the canaries. The automation comes later.

#### 3. Basic CI Pipeline

**Failure mode prevented**: Broken code reaches the main branch. Regressions go undetected.

Three gates, cheapest first:
1. **Lint + Format** (ruff) — catches style issues in <5 seconds
2. **Type Check** (pyright) — catches type errors in <15 seconds  
3. **Test Suite** (pytest) — unit tests + canary tests in <60 seconds

**What we do NOT build**: Matrix testing across Python versions and SDK versions. Nightly schedules. Performance benchmarks. Security scanning pipelines. AI auto-fix workflows. Those are Phase 1+ concerns.

One Python version. One SDK version (pinned). Three gates. That's it.

#### 4. SDK Version Pinning + Manual Rollback

**Failure mode prevented**: An SDK upgrade breaks production with no recovery path.

- Pin exact SDK version in `pyproject.toml` (never ranges)
- Document the rollback procedure (revert pin, re-run tests, deploy)
- That's it. No automated rollback. No compatibility matrix. No version diffing CI job.

**Why manual is fine for now**: How often does the SDK actually change? If it's monthly, a manual process that takes 15 minutes is adequate. Automation is justified when the frequency or blast radius exceeds human capacity. We don't have evidence that it does yet.

### What We Explicitly Skip in Phase 0

| Proposed Feature | YAGNI Verdict | Reasoning |
|-----------------|---------------|-----------|
| 58-event bridge | **Skip** | We don't know which of those 58 events actually exist in the SDK. The Synthesis agent flagged this: "The 58 SDK event types listed appear to be speculative." Audit first, bridge later. |
| OTEL integration | **Skip** | No failure mode prevented. Useful for debugging, but structured logging covers Phase 0 needs. |
| Self-healing adaptation engine | **Skip** | Requires canary tests (Phase 0) + historical data (doesn't exist yet) + proven patterns (no track record). The Skeptic is right: "autonomy without ops maturity is automated self-harm." |
| Recipe pipelines | **Skip** | Five recipes for a system that doesn't exist yet is premature. Ship the provider first. |
| Test evidence system | **Skip** | JSON-structured test evidence with baseline comparison is a testing *framework*. We need tests, not a testing framework. |
| Health dashboard | **Skip** | No users are monitoring this dashboard. Build it when someone asks for it. |
| Property-based testing | **Skip** | High value but Phase 1. Canary tests + unit tests are the Phase 0 priority. |
| AI confidence scoring | **Skip** | No autonomous decisions are being made. Confidence scores for what? |
| Session replay | **Skip** | Debug tool for a system that isn't in production yet. |
| Documentation generation | **Skip** | Module docstrings are the documentation. Auto-generation is premature optimization of a process that isn't bottlenecked. |

---

## Phase 1: Hardening (1-2 Weeks After Phase 0)

**Goal**: The provider survives its first SDK change without human panic. Observability exists where it prevents real debugging pain.

**Prerequisite**: Phase 0 is complete and the decomposed provider passes all tests.

### What We Build

#### 1. SDK Event Audit + Selective Event Bridge

**Failure mode prevented**: We design an observability system for events that don't exist, or miss events that matter.

Before building any event bridge, **hook into a real SDK session and log every event type, payload structure, and ordering**. The Synthesis agent correctly flagged that the 58-event catalog is speculative. We need ground truth.

After the audit, build a selective bridge for **Critical + Important tier events only** — the ones that actually matter for debugging production issues. Based on what we know today, that's approximately:
- `ASSISTANT_MESSAGE_DELTA` → streaming content (this is the core data path)
- `ASSISTANT_MESSAGE` → complete response
- `ERROR` → error events
- `USAGE` → token accounting
- `SESSION_IDLE` → control flow signal
- `preToolUse` → deny hook (already implemented)

Maybe 10-15 events, not 58. The bridge classifies events as BRIDGE (translate to Amplifier hooks), CONSUME (use internally), or DROP (log at debug level). This is the Golden Vision's design, but scoped to reality.

**What we do NOT build**: The full OTEL span tree, GenAI semantic conventions, metrics histograms, Prometheus endpoint, or exporter configuration. Those are Phase 2 concerns.

#### 2. Streaming Metrics (Lightweight)

**Failure mode prevented**: Streaming breaks silently — no tokens arrive, TTFT degrades, gaps appear — and nobody notices until users complain.

Add lightweight instrumentation to the StreamAccumulator:
- **TTFT** (time to first token): If this regresses, something is wrong
- **Total stream duration**: Context for debugging
- **Delta count**: Zero deltas with content = definite error
- **Max inter-event gap**: Detects stalls

These are counters and timestamps, not a metrics framework. Log them. Don't build a dashboard.

#### 3. Property-Based Tests for Pure Functions

**Failure mode prevented**: Edge cases in converters, model naming, tool parsing that example-based tests miss.

The converters module, model naming module, and tool parsing module contain pure functions that transform data. These are ideal Hypothesis targets:
- Model list normalization preserves count
- Message conversion roundtrips correctly
- Tool call parsing handles malformed input gracefully
- Error detection regex matches known error patterns

**Why Phase 1 not Phase 0**: Property-based tests require the decomposed modules to exist (Phase 0 deliverable). They also require understanding which functions are pure — the decomposition clarifies this.

#### 4. Automated SDK Change Detection (CI Only)

**Failure mode prevented**: An SDK update is available and we don't know about it until something breaks.

A weekly CI job that:
1. Checks if a new SDK version is available
2. Runs the canary test suite against the new version
3. Reports pass/fail as a GitHub Issue

**No auto-fix. No auto-deploy. No adaptation engine.** Just detection. A human reads the issue and decides what to do. The Self-Healing agent's P0-P2 priorities are exactly right: canary tests (Phase 0) + version pinning (Phase 0) + static detection in CI (this).

**Why not auto-fix**: The Skeptic's challenge is unanswered: "Pick 10 real historical provider bugs / SDK upgrades. Attempt AI-only fixes. Measure." Until we have that data, auto-fix is wishcasting.

#### 5. Error Translation Hardening

**Failure mode prevented**: Unstructured SDK error messages aren't recognized, leading to generic "unknown error" responses instead of actionable rate-limit or content-filter errors.

The `error_translation.py` module (extracted in Phase 0) gets additional detection patterns based on production error data. This is iterative improvement of an existing module, not new infrastructure.

### What We Explicitly Skip in Phase 1

| Proposed Feature | YAGNI Verdict | Reasoning |
|-----------------|---------------|-----------|
| Full OTEL stack | **Skip** | No OTEL collector deployed. No traces being consumed. Build when there's a consumer. |
| Auto-adaptation engine | **Skip** | Zero historical adaptation data. The learning loop has nothing to learn from. |
| Compatibility matrix CI | **Skip** | One SDK version is pinned. Testing against multiple versions solves a problem we don't have. |
| Recipe pipelines | **Skip** | Still premature. The manual workflow is fast enough for a single provider. |
| Knowledge capture system | **Skip** | Requires adaptations to have occurred. They haven't. |
| AI auto-fix pipeline | **Skip** | The Skeptic's point stands: prove it on historical cases first. |
| Session replay | **Skip** | Build when debugging a production issue that can't be reproduced. |

---

## Phase 2: Full Vision (1 Month After Phase 0)

**Goal**: The provider can survive an SDK minor version bump with minimal human intervention. Observability is comprehensive. The autonomous maintenance loop has its first real data.

**Prerequisite**: Phase 1 is complete. The provider has been in use for at least 2 weeks. At least one SDK change has been detected and handled (manually or semi-automatically).

### What We Build

#### 1. OTEL Integration (If Amplifier Has a Collector)

**Failure mode prevented**: Debugging production issues requires correlating provider behavior with kernel behavior across distributed traces.

**Only build this if Amplifier's OTEL infrastructure exists.** If there's no collector, no trace viewer, no metrics backend — OTEL spans are emitted into the void. The Observability agent's design is sound, but infrastructure must precede instrumentation.

If the infrastructure exists:
- GenAI semantic conventions on the `complete()` span
- Token usage histograms
- TTFT and streaming metrics as OTEL gauges
- Trace context propagation from Amplifier parent spans

#### 2. Semi-Automated SDK Adaptation

**Failure mode prevented**: SDK patch/minor changes require human effort that could be automated for common cases (field renames, type renames).

By Phase 2, we should have:
- Canary test data from Phase 0
- At least 1-2 real SDK changes detected by Phase 1's CI job
- Empirical understanding of what kinds of changes actually occur

**Start with the Self-Healing agent's P3**: Type-change auto-adaptation using migration maps. When a canary test fails because a field was renamed, the system proposes a fix. A human approves or rejects via PR review. Not autonomous — semi-automated with human gate.

**Graduate to more autonomy only with evidence**: Track auto-heal success rate. If it's >90% for type changes after 5+ successful adaptations, consider removing the human gate for that category. The confidence-gated autonomy model from the Synthesis agent is correct: trust is earned through track record, not architecture.

#### 3. Performance Baseline + Regression Detection

**Failure mode prevented**: Performance degrades gradually and nobody notices until it's 3x slower.

By Phase 2, we have enough usage data to establish baselines:
- TTFT baseline per model
- Total completion latency baseline
- Token throughput baseline
- Memory usage baseline

CI checks that baselines aren't violated. Not a dashboard — a CI gate.

#### 4. Recipe for SDK Upgrade (Single Recipe, Not Five)

**Failure mode prevented**: SDK upgrade process is ad-hoc, inconsistent, and error-prone.

One recipe. Not five. The SDK Upgrade Adaptation recipe from the Golden Vision, simplified:

```
detect-sdk-update → run-canary-suite → classify-failures → [HUMAN APPROVAL] → apply-fix → validate → deploy-or-rollback
```

This is the minimum viable autonomous loop the Skeptic demanded: detect, patch, prove safety, gate, deploy, monitor. Build it for the one workflow that matters most (SDK upgrades), prove it works, then consider extending to other workflows.

#### 5. Expanded Contract Coverage

**Failure mode prevented**: New SDK features or behavioral changes aren't covered by existing canary tests.

By Phase 2, the contract test suite should cover:
- Every SDK type we import
- Every SDK function we call
- Every event type we handle
- Every error condition we catch

The Contract Architecture agent's vision of contracts-as-specification is correct, but the implementation should be iterative: add contracts as we discover dependencies, not speculatively for imagined ones.

### What We Explicitly Skip Even in Phase 2

| Proposed Feature | YAGNI Verdict | Reasoning |
|-----------------|---------------|-----------|
| Full 58-event bridge | **Defer** | Build for the events that actually exist after the Phase 1 audit. Likely 20-30 events, not 58. |
| Knowledge capture system | **Defer** | Needs 10+ adaptation records to be useful. We might have 2-3 by Phase 2. |
| Pattern recognition engine | **Defer** | Premature until the knowledge base has meaningful volume. |
| 5 recipe pipelines | **Defer** | Start with 1 (SDK upgrade). Add others when the first proves reliable. |
| Session replay | **Defer** | Build on-demand when debugging requires it. |
| AI confidence scoring | **Defer** | Implicit in the human gate. Explicit scoring adds complexity without changing behavior when a human is reviewing anyway. |
| Documentation generation | **Defer** | Module docstrings are sufficient. Auto-generation is a nice-to-have. |
| Test evidence JSON storage | **Defer** | pytest output is the evidence. Structured JSON adds a maintenance burden for marginal benefit. |

---

## The Kill List: What We Should Explicitly NOT Build

These items appeared in the Wave 1-3 analyses but fail the YAGNI test entirely. They should be explicitly rejected, not deferred.

### 1. ❌ AI Auto-Merge Without Human Review

**Proposed by**: CI/CD Architecture (confidence ≥0.9 → auto-merge)

**Kill reason**: The Skeptic's argument is decisive. "Zero human review is not a technical goal; it's an organizational gamble." No confidence score can substitute for human judgment on security implications, behavioral correctness under load, or alignment with shifting organizational priorities. Auto-merge removes accountability without removing risk.

**What to do instead**: AI proposes PRs. Humans review and merge. The speed bottleneck is almost never "waiting for human to click merge" — it's "figuring out what to change." AI already handles the expensive part.

### 2. ❌ Adapter Shim Generation Engine

**Proposed by**: Self-Healing Design (generate adapter layers for behavioral changes)

**Kill reason**: Adapter shims are technical debt generators. The Self-Healing agent acknowledges this: "Adapter shims carry deprecation comments and expiry dates." A system that auto-generates technical debt is a system that auto-generates future maintenance burden. If a behavioral change can't be handled by a direct code update, it needs human design judgment — not a compatibility shim.

**What to do instead**: When a behavioral change occurs, create a GitHub Issue with diagnostic context. A human (or AI with human review) makes a direct fix. No shims.

### 3. ❌ Production Anomaly Detection (Runtime Layer 3)

**Proposed by**: Self-Healing Design (error rate anomaly detection, response shape validation, latency deviation alerts)

**Kill reason**: This is an APM system. Building a custom APM for a single provider is over-engineering by definition. If Amplifier needs production monitoring, it should use an existing APM tool (Datadog, New Relic, Grafana) — not a bespoke provider-level anomaly detector.

**What to do instead**: Emit structured logs. Use Amplifier's existing hook system for observability. If production monitoring is needed, integrate with the organization's existing monitoring stack.

### 4. ❌ Event Catalog Runtime Validation

**Proposed by**: Contract Architecture (emitting an unlisted event raises `ContractViolationError` in development mode)

**Kill reason**: This is a testing concern disguised as a runtime concern. If a developer emits an unlisted event, the test suite should catch it — not a runtime wrapper that adds overhead and complexity to every event emission. The development/production mode split adds a class of "works in dev, breaks in prod" bugs.

**What to do instead**: Lint rule or test that validates emitted events against a catalog. Catch at build time, not runtime.

### 5. ❌ Multi-Version Compatibility Matrix CI

**Proposed by**: Self-Healing Design, CI/CD Architecture

**Kill reason**: We pin one SDK version. We test against one SDK version. Testing against N versions solves a problem we don't have (supporting multiple SDK versions simultaneously). When we upgrade, we upgrade fully — there's no partial deployment where different instances run different SDK versions.

**What to do instead**: Single-version CI. When upgrading, test against the new version. If it passes, switch the pin. If not, stay on the old pin.

### 6. ❌ Nested Subpackage Structure

**Proposed by**: Python Architecture (Wave 1)

**Kill reason**: Decisively rejected by the Modular Architecture agent with five concrete arguments. The existing codebase is flat, the module count is manageable (17), AI agents work better with flat structures, the names are self-documenting, and the kernel philosophy demands thin concerns.

**What to do instead**: Flat package with clear naming. Already decided.

### 7. ❌ Abstract Base Classes for Internal Interfaces

**Proposed by**: Python Architecture (Wave 1)

**Kill reason**: Single-implementation interfaces are premature abstraction. The Modular Architecture agent is correct: "We use Protocol only where structural typing genuinely simplifies testing (e.g., EventCallback)." ABCs for internal module interactions add indirection without benefit.

**What to do instead**: Direct imports between modules. Protocol classes only for cross-module callbacks where the caller and implementer are in different modules.

---

## Decision Framework: How to Evaluate Future Proposals

For every feature proposed after Phase 0, apply this filter:

### Gate 1: Failure Mode
> "What specific failure mode does this prevent?"

If the answer is vague ("improves reliability," "enables better debugging," "future-proofs"), **reject**. If the answer is concrete ("prevents SDK field renames from breaking production," "detects when TTFT exceeds 5 seconds"), proceed to Gate 2.

### Gate 2: Evidence
> "Has this failure actually occurred, or is it structurally inevitable?"

"Structurally inevitable" means: the SDK is pre-1.0 and will change (canary tests are structurally inevitable). "Has actually occurred" means: we have a bug report, a production incident, or a near-miss. Speculative failures ("what if the SDK changes its auth model") are **deferred** until evidence emerges.

### Gate 3: Simplest Solution
> "What is the simplest thing that prevents this failure?"

If the answer is "a 200-line module," build it. If the answer is "an event bridge + OTEL integration + metrics histograms + Prometheus endpoint + Grafana dashboard," you've probably over-scoped. Find the 20% solution that handles 80% of the problem.

### Gate 4: Existing Solutions
> "Does an existing tool already solve this?"

Don't build a custom APM when Datadog exists. Don't build a custom CI orchestrator when GitHub Actions exists. Don't build a custom metrics system when OTEL collectors exist. The provider's job is translation, not infrastructure.

---

## Summary: The Phased Architecture at a Glance

```
PHASE 0 (NOW)                    PHASE 1 (1-2 WEEKS)              PHASE 2 (1 MONTH)
─────────────                    ────────────────────              ─────────────────
✅ Decompose provider.py          ✅ SDK event audit               ✅ OTEL (if infra exists)
   5 modules, flat, layered          Real events, not speculative     GenAI conventions
                                                                      
✅ Canary test suite              ✅ Selective event bridge         ✅ Semi-auto SDK adaptation
   ~20 SDK assumption tests          10-15 critical events            Human-gated, type changes
                                                                      
✅ Basic CI                       ✅ Lightweight streaming metrics  ✅ Performance baselines
   lint → typecheck → test           TTFT, duration, gap detection    CI regression gates
                                                                      
✅ SDK version pinning            ✅ Property-based tests           ✅ 1 recipe (SDK upgrade)
   Exact pin, manual rollback        Pure functions via Hypothesis    Detect→fix→gate→deploy
                                                                      
                                  ✅ Weekly SDK change detection    ✅ Expanded contract coverage
                                     CI job, human-handled              Iterative, evidence-based

KILL LIST (Never Build)
──────────────────────
❌ AI auto-merge without review
❌ Adapter shim generation
❌ Custom production APM
❌ Runtime event validation
❌ Multi-version compat matrix
❌ Nested subpackages
❌ ABCs for internal interfaces
```

---

## Closing: What the Skeptic Got Right

The Skeptic asked the most important question in the entire debate: **"Will the machine ever actually run?"**

Every proposed feature — the 58-event bridge, the self-healing engine, the recipe pipelines, the knowledge capture system — is irrelevant if the provider doesn't reliably complete LLM calls, capture tool calls, translate errors, and stream content. Phase 0 is about making the machine run. Phase 1 is about knowing when it stops running. Phase 2 is about teaching it to restart itself.

The Skeptic also got this right: "Autonomy is not a feature; it's a multiplicative factor on every other feature's failure modes." Self-healing that auto-fixes the wrong thing is worse than no self-healing. Semi-automated with human gates is the right starting posture. Full autonomy is earned through evidence, not architecture.

The Comprehensive camp designed a beautiful system. The Simple camp asked whether it was necessary. The answer is: **some of it is necessary (canary tests, decomposition, CI), some of it will become necessary (event bridge, SDK detection, performance baselines), and some of it may never be necessary (adapter generation, production APM, AI auto-merge).** Phase the work. Earn trust. Kill the speculative stuff ruthlessly.

Build the provider. Then make it observable. Then make it resilient. In that order.

---

*This document resolves the Simplicity vs. Comprehensiveness tension by phasing delivery according to evidence of need. Features graduate from the kill list to deferred to Phase 2 to Phase 1 to Phase 0 as evidence accumulates. The architecture is not designed top-down from a vision — it grows bottom-up from failure modes.*
