# The Golden Vision: Next-Generation GitHub Copilot Provider Architecture

**Version**: 1.0 — Definitive  
**Date**: 2026-03-08  
**Authority**: Synthesized from 31 documents across 3 waves, 3 rounds of adversarial debate, and 27 expert analyses  
**Status**: Implementation Constitution

---

## Executive Summary

The software industry stands at an inflection point. AI systems now write, review, and maintain code — but the codebases they maintain were designed for human cognition. This document defines the architecture for a provider that inverts that assumption: **code written for AI readers first, human readers second**, maintained by autonomous agents operating within explicit safety boundaries.

The `next-get-provider-github-copilot` is a translation layer between the Amplifier kernel and the GitHub Copilot SDK. Today it is a 1,799-line monolith with 14 cross-cutting concerns, cyclomatic complexity of 47, and a documented history of entanglement-caused bugs including a 305-turn infinite loop. It works, but it resists safe modification — by humans or machines.

This vision defines five innovations that transform it into an AI-first maintainable system:

1. **Contract-First SDK Boundary** — No SDK type crosses the membrane. Ever. A three-layer architecture (Adapter → Driver → Raw SDK) translates 58 SDK event types into 6 stable domain events, 27 SDK error types into 8 domain exceptions, and 12 SDK import paths into zero public-facing SDK dependencies.

2. **The Deny + Destroy Pattern** — The provider's defining architectural commitment. Every SDK session is ephemeral: a `preToolUse` hook denies all tool execution (preserving Amplifier's sovereignty), and sessions are destroyed immediately after the first turn completes. No state accumulates. No second orchestrator emerges.

3. **Contract-Anchored Diamond Testing** — A five-tier testing strategy where every test traces to a contract clause, every tier has enforced speed limits, and every run produces structured evidence. The diamond is widest at Tiers 2-3 (integration + contract compliance = 45% of tests) because that's where AI-generated code most often breaks silently.

4. **Risk-Calibrated Human Involvement** — Not "zero human review" — that was imprecise language corrected under adversarial pressure. Instead: 60% of changes (type renames) require no human involvement; 30% (behavioral changes) require release-gate review; 10% (breaking changes) require full architectural review; 100% of security changes require human review, no exceptions.

5. **Phased Delivery with Kill Gates** — Three phases, each gated on measurable success criteria. Autonomy is earned through evidence, not assumed through architecture. If Phase 1 doesn't produce a working decomposed provider, the vision was theater. If the adversarial benchmark on Day 20 shows <50% success, autonomy investment is cancelled.

**Why this matters for the industry**: Every team building AI-assisted development tools faces the same question — how much can you trust the machine? This architecture provides a concrete, measurable answer: trust is a spectrum calibrated to risk, earned through track record, and enforced through contracts. The provider is the proving ground for a development methodology where AI agents are first-class maintainers operating within explicit safety boundaries.

---

## Core Philosophy

### The Five Principles

**Principle 1: Translation, Not Framework**

The provider's job is translation — converting between the Amplifier protocol and the Copilot SDK. Every design decision must answer: "Does this add translation capability or framework complexity?" If the latter, remove it.

The provider does not manage retry logic (kernel policy), context windows (orchestrator concern), tool execution (always denied), or model selection preferences (consumer policy). It translates requests into SDK sessions, SDK events into domain events, and SDK errors into domain exceptions. The thinnest possible membrane between two systems that don't know about each other.

This principle prevents the "Two Orchestrators" problem — the most dangerous architectural failure mode. The Copilot SDK has its own agent loop. Amplifier has its own orchestrator. If the provider starts making decisions about tool execution, conversation flow, or context management, it creates a hidden second brain that conflicts with Amplifier's orchestrator. The Deny + Destroy pattern is the concrete mechanism that enforces this boundary.

**Principle 2: Mechanism with Sensible Defaults**

Borrowed from kernel philosophy, but applied as a heuristic, not a religion. The provider separates mechanism (how things work) from policy (how things should behave) — but every extracted policy ships with a sensible default. Policy extraction does not mean "leave it to the consumer." It means "provide a good default that can be overridden."

| Item | Classification | Default |
|------|---------------|---------|
| Rate limit handling (429) | **Mechanism** — API contract obligation | Respect always |
| Backoff timing and jitter | **Policy** — teams may prefer different approaches | Exponential with jitter |
| Token redaction in logs | **Mechanism** — security invariant | Always redact |
| Log verbosity level | **Policy** — operational preference | INFO |
| Pagination execution | **Mechanism** — must handle multi-page responses | Fetch all pages |
| Pagination depth limit | **Policy** — cost/completeness tradeoff | 10 pages |
| Retry on transient error | **Mechanism** — basic reliability | Retry up to 3 times |
| Retry count and timing | **Policy** — urgency/cost tradeoff | 3 retries, exponential backoff |
| Deny + Destroy pattern | **Mechanism** — sovereignty preservation | Non-configurable |

**Principle 3: Design for SDK Evolution, Not SDK Stability**

The Copilot SDK is pre-1.0 and actively evolving. Historical analysis of 18 months of changelog data reveals: 73% of changes are type renames or field additions (auto-healable), 21% are behavioral changes (partially auto-healable), and 6% are breaking removals (require human intervention). The architecture treats SDK changes as certainties to design for, not risks to avoid.

Every SDK assumption is encoded as a test. Every test failure triggers classification. The system auto-heals what it can and honestly escalates what it can't. This is not optimism — it is engineering for the actual probability distribution of changes.

**Principle 4: AI-Maintainability as First-Class Goal**

The codebase is written for AI readers first. This manifests as:

- **Module size limits**: 400-line soft cap, 600-line hard cap. An AI agent's context window is the bottleneck — not human reading speed.
- **Self-documenting contracts**: Every module has a docstring that serves as its specification. An AI agent reading the docstring knows what the module does, what it depends on, and what it guarantees.
- **Structured error context**: Error messages include contract references, expected vs. actual values, and suggested fixes. "AssertionError: False is not True" is unacceptable. "Contract violation: complete() MUST include usage metadata. Response had 3 choices but usage=None. Fix: Ensure SDK response.usage is mapped." is required.
- **Regeneration over patching**: Modules are designed to be regenerated from their specification, not incrementally patched. When a module drifts from its spec, the correct action is regeneration, not archaeology.

**Principle 5: Confidence-Gated Autonomy**

Every autonomous action carries an implicit or explicit confidence level. The level determines human involvement:

| Confidence | Action | Example |
|-----------|--------|---------|
| **Tier 1** (Deterministic) | Fully autonomous | Lint fixes, format changes, type renames with passing tests |
| **Tier 2** (High confidence) | AI writes, human approves PR | Module extraction, new test contracts, behavioral code |
| **Tier 3** (Medium confidence) | Human designs, AI implements | Architectural changes, new module creation, SDK boundary decisions |
| **Tier 4** (Human-only) | Never autonomous | Security changes, breaking API changes, sovereignty-critical code |

Trust is earned through track record: if the system successfully auto-heals 10+ type changes with zero regressions, Tier 1 scope expands. If it produces a single silent correctness regression, Tier 1 scope contracts. The system's autonomy level is a living parameter, not a fixed architectural decision.

### Non-Negotiable Constraints

1. **No SDK type crosses the adapter boundary.** Domain code never imports from the SDK.
2. **preToolUse deny hook on every session.** No exceptions. No configuration. The SDK never executes tools.
3. **Sessions are ephemeral.** Create, use once, destroy. No state accumulation.
4. **Security changes always require human review.** No confidence score overrides this.
5. **Tests must trace to contracts.** No orphan tests. No "test this because it seems important."

---

## Architecture

### Module Decomposition

The provider decomposes from a 1,799-line monolith into focused modules within a flat package structure:

```
provider_github_copilot/
├── _types.py              ← Shared domain types (zero SDK imports)
├── provider.py            ← Thin 5-method Provider Protocol delegation (~300 lines)
├── completion.py          ← LLM call lifecycle orchestrator (~350 lines)
├── error_translation.py   ← SDK→domain error boundary (~200 lines)
├── tool_parsing.py        ← Tool call extraction + streaming accumulator (~250 lines)
├── session_factory.py     ← Ephemeral session lifecycle + deny hook (~250 lines)
├── streaming.py           ← Streaming event handler + metrics (~200 lines)
├── sdk_adapter/           ← THE MEMBRANE: all SDK imports live here
│   ├── types.py           ← SDK type translation (decompose, don't wrap)
│   ├── events.py          ← SDK event → domain event translation
│   └── errors.py          ← SDK exception → domain exception translation
├── client.py              ← SDK subprocess management (existing, preserved)
├── sdk_driver.py          ← SDK session communication (existing, preserved)
├── converters.py          ← Message format conversion (existing, preserved)
├── model_cache.py         ← Model list caching (existing, preserved)
├── model_naming.py        ← Model ID normalization (existing, preserved)
├── config.py              ← Provider configuration (existing, preserved)
└── health.py              ← Health check mechanism (existing, preserved)
```

**Total: ~17 modules, flat structure, no nesting beyond sdk_adapter/**

### SDK Boundary Design

The boundary is a **Contract-First Membrane** — neither a thin wrapper (too coupled) nor a blind adapter (too speculative). We define what Amplifier needs, then the adapter translates the SDK's reality into our contracts.

```
┌─────────────────────────────────────────────────────────────┐
│                    AMPLIFIER CORE                           │
│  ChatRequest ─► Provider Protocol ─► ChatResponse           │
│  (our types)    (our contract)       (our types)            │
├───────────────────────── BOUNDARY ────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SDK ADAPTER LAYER (the membrane)             │   │
│  │  Inbound:  ChatRequest → SDK session config          │   │
│  │  Outbound: SDK events → ContentBlock[]               │   │
│  │  Errors:   SDK exceptions → domain exceptions        │   │
│  │  Types:    SDK types → NEVER cross this line         │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SDK DRIVER (containment)                     │   │
│  │  Session lifecycle, subprocess management,           │   │
│  │  agent loop suppression, circuit breaker             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         @github/copilot-sdk (radioactive)            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Translation strategy**: Decompose, don't wrap. A `copilot.Message` becomes a `list[ContentBlock]`, not a `MessageWrapper(sdk_message)`. Opaque handles for stateful objects — `SessionHandle` is a UUID string, not an SDK session reference. Reverse translation for outbound types — our `ToolDefinition` becomes SDK's tool format inside the adapter only.

**Event reduction**: Of ~58 SDK event types, we translate ~8 into 6 stable domain event types:

| Domain Event | SDK Source | Purpose |
|-------------|-----------|---------|
| `CONTENT_DELTA` | text_delta, thinking_delta | Streaming content |
| `TOOL_CALL` | tool_use_start/delta/complete | Complete tool call (accumulated) |
| `USAGE_UPDATE` | usage_update | Token accounting |
| `TURN_COMPLETE` | message_complete | Model finished |
| `SESSION_IDLE` | session_idle | Completion signal |
| `ERROR` | error | Translated SDK error |

All other SDK events are either consumed internally (session lifecycle), dropped with debug logging (heartbeat, MCP, permissions), or explicitly excluded (tool results — we deny all execution).

### Dependency Rules

```
Imports flow DOWN only. Never up, never sideways between peers.

    _types.py (leaf — stdlib only)
        │
    ┌───┼───────────────┐
    │   │               │
    ▼   ▼               ▼
  errors  converters  client/
          tool_parsing  session_factory
                        │
                        ▼
                    sdk_adapter/ (ONLY code that imports SDK)
```

**Enforcement**: An architecture fitness test in CI scans all `.py` files and fails if SDK imports exist outside `sdk_adapter/`. Circular import detection runs on every commit.

### Key Interfaces

The **Provider Protocol** — the immutable 5-method contract with Amplifier:

```python
class CopilotProvider(Protocol):
    @property
    def name(self) -> str: ...
    def get_info(self) -> ProviderInfo: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def complete(
        self, request: ChatRequest,
        *, on_content: Callable[[ContentDelta], None] | None = None,
    ) -> ChatResponse: ...
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCallBlock]: ...
```

The **SdkAdapter Protocol** — the internal contract between provider logic and SDK translation:

```python
class SdkAdapter(Protocol):
    async def create_session(self, config: SessionConfig) -> SessionHandle: ...
    async def send_message(
        self, session: SessionHandle, prompt: str, tools: list[ToolDefinition]
    ) -> AsyncIterator[DomainEvent]: ...
    async def destroy_session(self, session: SessionHandle) -> None: ...
    async def health_check(self) -> bool: ...
```

The **Error Hierarchy** — 8 domain exceptions with retryability classification:

```
CopilotProviderError (base, retryable=False)
├── CopilotAuthError (retryable=False, always)
├── CopilotRateLimitError (retryable=True, retry_after extracted)
├── CopilotTimeoutError (retryable=True)
├── CopilotContentFilterError (retryable=False)
├── CopilotSessionError (retryable=True)
├── CopilotModelNotFoundError (retryable=False)
├── CopilotSubprocessError (retryable=True)
└── CopilotCircuitBreakerError (retryable=False)
```

---

## The Autonomous Development Machine

### Four-Tier Autonomy Model

Autonomy is not binary. It is a spectrum calibrated to risk, earned through evidence, and enforced through gates.

```
TIER 1: FULLY AUTONOMOUS                    TIER 2: AI + HUMAN GATE
─────────────────────────                    ───────────────────────
• Format/lint fixes                          • Module extraction
• Type rename adaptation                     • New test contracts
• Dependency version bumps (patch)           • Behavioral code changes
• Documentation updates                      • Error handling changes
• Test scaffolding                           • Configuration changes

Gate: All tests pass                         Gate: Human reviews PR
Rollback: Automatic on test failure          Rollback: Human reverts PR

TIER 3: HUMAN DESIGNS, AI IMPLEMENTS        TIER 4: HUMAN ONLY
────────────────────────────────────        ────────────────────
• New module creation                        • Security changes (any)
• SDK boundary modifications                 • Breaking API changes
• Architecture changes                       • Sovereignty-critical code
• Event bridge classifications               • Incident response
• Adaptation prototype scope                 • Accountability decisions

Gate: Human approves design + PR             Gate: Human does everything
Rollback: Human decides approach             Rollback: Human manages
```

### Decision Tree for Change Classification

```
New change detected
    │
    ├─ Is it security-related? ──── YES ──► TIER 4 (human only, always)
    │
    ├─ Is it a type/field rename? ── YES ──► TIER 1 (auto-adapt if tests pass)
    │
    ├─ Is it a behavioral change? ── YES ──► TIER 2 (AI fix + human release gate)
    │
    ├─ Is it a breaking removal? ─── YES ──► TIER 3 (human designs solution)
    │
    ├─ Is it new feature work? ───── YES ──► TIER 3 (human approves design)
    │
    └─ Unknown/ambiguous? ────────── YES ──► TIER 3 (conservative default)
```

### Human Involvement Points

Humans are relocated, not eliminated. They add maximum value at:

| Point | Human Role | AI Role |
|-------|-----------|---------|
| **Architectural review** | Design module boundaries, approve SDK boundary changes | Implement designs, generate tests |
| **Release gating** | Approve deployment of behavioral changes | Generate fix + evidence package |
| **Security review** | Review all security-adjacent changes | Flag potential security implications |
| **Incident response** | Investigate, decide, communicate | Provide diagnostic context, suggest mitigations |
| **Adversarial validation** | Evaluate whether autonomy investment should continue | Execute benchmarks, report results honestly |

### Recipe Architecture

Recipes are declarative YAML workflows that encode repeatable processes. The provider starts with exactly **one recipe** (not five — earned, not assumed):

**Recipe: SDK Upgrade Adaptation**
```
detect-sdk-update → run-canary-suite → classify-failures
    → [HUMAN APPROVAL GATE] → apply-fix → validate → deploy-or-rollback
```

Additional recipes are added only after this one proves reliable across 5+ successful adaptations. The Skeptic's forcing function applies: if the first recipe doesn't work, no more recipes are built.

---

## Testing Strategy

### The Contract-Anchored Diamond

```
                    /\
                   /  \         TIER 5: Live Smoke (5%, nightly)
                  /    \        Real API, real tokens, real network
                 /──────\
                /        \      TIER 4: SDK Assumption Tests (15%, every PR)
               /          \     Recorded responses, shape validation, drift detection
              /────────────\
             /              \   TIER 3: Contract Compliance Tests (25%, every PR)
            /                \  One test per MUST clause, behavioral proof
           /──────────────────\
          /                    \ TIER 2: Integration Tests (20%, every commit)
         /                      \ Component wiring with stubs, full flows
        /────────────────────────\
       /                          \ TIER 1: Unit + Property Tests (30%, every commit)
      /                            \ Pure functions, invariants, transformations
     /──────────────────────────────\
```

The diamond is widest at Tiers 2-3 (45% combined). This is deliberate. In AI-maintained code, the most dangerous failure is "code that runs but violates the contract" — not missing edge cases in pure functions (caught by properties) and not API drift (caught by SDK assumptions). The thick middle catches the failure mode unique to AI: *syntactically correct code that misunderstands the requirement.*

### Test Categories

| Tier | Category | % | Speed Limit | When Run |
|------|----------|--:|------------|----------|
| 1a | Pure function unit tests | 20% | <10ms | Every commit |
| 1b | Property-based tests (Hypothesis) | 10% | <100ms | Every commit |
| 2 | Integration tests (stubbed I/O) | 20% | <500ms | Every commit |
| 3 | Contract compliance tests | 25% | <100ms | Every PR |
| 4 | SDK assumption tests (canary) | 15% | <200ms stubbed, <5s live | Every PR / nightly |
| 5 | Live smoke tests | 5% | <60s | Nightly |
| ∞ | Evidence capture (cross-cutting) | 100% | Zero overhead | Always |

**Speed tiers are enforced at runtime**, not by convention. A test that exceeds its declared tier fails the build. A test without a tier marker fails the build. No exceptions.

### AI-Friendly Test Design

Five properties define AI-friendly tests:

1. **Contract-anchored**: Every test docstring cites the exact contract clause it verifies. `"Contract: provider_protocol.py:55 — MUST include usage metadata in response."`

2. **Evidence-producing**: Tests emit structured data (inputs, expected, actual, passed), not just pass/fail. Machine-parseable, not log-scrapeable.

3. **Self-diagnosing**: Failure messages tell the AI agent exactly what contract was violated, what was expected, what was observed, and where to look for the fix. Zero investigation needed.

4. **Deterministic and isolated**: Stubbed I/O ports, deterministic clocks, no shared mutable state. Any test, any order, same result.

5. **Speed-declared**: `@pytest.mark.pure`, `@pytest.mark.stubbed`, `@pytest.mark.local`, `@pytest.mark.live`. An AI agent knows instantly whether a test is safe for tight-loop development or requires special setup.

### CI Pipeline

```
STAGE 1: Fast Feedback (every commit, <90s)
  ├── ruff check + ruff format --check
  ├── pyright (strict)
  └── pytest -m "pure or stubbed" --timeout=90

STAGE 2: Integration (every PR, <5min)
  ├── Cross-platform matrix (ubuntu + windows, Python 3.11 + 3.12)
  ├── pytest -m "local" --timeout=300
  └── SDK assumption tests (stubbed mode)

STAGE 3: Evidence (every PR merge)
  └── Behavioral diff against baseline — surfaced in PR comments

STAGE 4: Live Smoke (nightly)
  ├── Live API tests with real tokens
  ├── SDK assumptions (live mode)
  └── Auto-create snapshot update PR if API shape changed
```

---

## Implementation Roadmap

### Phase 0: Foundation (Week 1) — "Make It Work"

| Day | Deliverable | Success Criterion |
|-----|-------------|-------------------|
| 1 | Project scaffolding, dependency setup, speed tier enforcement | `pip install -e ".[dev]"` succeeds, `pytest --collect-only` runs |
| 2 | Extract `error_translation.py` (~200 lines) | 6+ unit tests pass, module ≤250 lines |
| 3 | Extract `tool_parsing.py` (~250 lines) | Fake tool filtering works, malformed JSON ≤ empty dict |
| 4 | Extract `session_factory.py` + `streaming.py` | Deny hook always installed, deltas accumulate correctly |
| 5 | Extract `completion.py` + full integration verification | **ALL existing tests pass, no module >400 lines, behavioral equivalence on 5 representative requests** |

**Gate**: If behavioral equivalence cannot be demonstrated on Day 5 and the cause cannot be identified within 4 hours, STOP. Revert everything. The monolith's behavior is the source of truth.

### Phase 1: Core (Week 2) — "Make It Detectable"

| Day | Deliverable | Success Criterion |
|-----|-------------|-------------------|
| 6-7 | 20+ SDK canary tests (type shape + behavioral + error) | Tests run in <10s total, each cites specific SDK assumption |
| 8 | CI pipeline (lint → typecheck → test) | Pipeline blocks merge on failure |
| 9 | Streaming metrics (TTFT, gap detection) + architecture fitness tests | SDK boundary violations auto-detected |
| 10 | Integration verification + documentation | `SDK_ASSUMPTIONS.md` lists all assumptions |

**Gate**: 20+ canary tests passing, CI blocks merge, streaming metrics logged. All Week 1 criteria still hold.

### Phase 2: Autonomy Foundations (Weeks 3-4) — "Make It Resilient"

*Contingent on Phase 0-1 success. If Phase 0 didn't preserve behavior, fix the foundation. If canary tests couldn't be written, research SDK testability.*

| Days | Deliverable | Success Criterion |
|------|-------------|-------------------|
| 11-12 | SDK event audit + selective event bridge (~10-15 events) | Real event catalog, not speculative |
| 13-14 | Weekly SDK change detection CI job | Creates GitHub Issue on new SDK version |
| 15-16 | Property-based tests for pure functions (Hypothesis) | 8+ property tests, each <100ms |
| 17-18 | Semi-automated type change adaptation prototype | Handles field renames, creates PR for human review |
| 19-20 | **Adversarial validation** on 3-5 historical/simulated SDK changes | Honest results determine future investment |

**Gate**: If adversarial validation success rate <50%, autonomy investment is cancelled. Adopt targeted improvements path. Either outcome is a success — one validates the vision, the other saves months of misguided investment.

### The Kill List — What We Explicitly Do NOT Build

| Item | Status | Reason |
|------|--------|--------|
| AI auto-merge without human review | **KILLED** | No confidence score substitutes for human judgment on security and correctness |
| Adapter shim generation engine | **KILLED** | Shims are auto-generated technical debt. Direct fixes instead. |
| Custom production APM | **KILLED** | Use existing tools (Datadog, Grafana). Don't build bespoke monitoring for one provider. |
| Runtime event catalog validation | **KILLED** | Testing concern, not runtime concern. Validate at build time. |
| Multi-version SDK compatibility matrix | **KILLED** | We pin one version. No partial deployments across SDK versions. |
| Nested subpackage structure | **KILLED** | Flat package with clear naming. Decisively rejected. |
| ABCs for internal interfaces | **KILLED** | Single-implementation interfaces are premature abstraction. |
| Full 58-event bridge | **DEFERRED** | Audit first, bridge reality not imagination. Likely 15-20 events, not 58. |
| Full self-healing engine | **DEFERRED** | Contingent on adversarial validation results. |
| 5 recipe pipelines | **DEFERRED** | Start with 1. Earn the rest. |
| Test evidence JSON storage | **DEFERRED** | pytest output is the evidence for now. |

---

## Risks and Mitigations

### Top 5 Risks

| # | Risk | Probability | Impact | Mitigation |
|---|------|:-----------:|:------:|------------|
| **R1** | Decomposition introduces subtle behavioral regression | HIGH | HIGH | Snapshot comparison on Day 5 against 5 representative requests. Full test suite as safety net. Stop-work criterion: revert if cause not identified within 4 hours. |
| **R2** | SDK breaking change during implementation | MEDIUM | HIGH | Exact version pin in `pyproject.toml`. Do not upgrade during Weeks 1-2. Canary tests (Week 2+) detect future changes. |
| **R3** | Canary tests can't be written (SDK not testable) | LOW | HIGH | Fallback: test against CLI subprocess output instead of Python SDK types. Decision point on Day 6 attempt. |
| **R4** | Adaptation prototype gives false confidence in autonomy | MEDIUM | HIGH | Adversarial validation on Day 20 with honest reporting. The Skeptic's benchmark is the gate. If <50% success, cancel autonomy investment. |
| **R5** | Scope creep — adding features not in this roadmap | HIGH | MEDIUM | This document is the scope. If it's not listed here, it's not in scope. No more debates until Phase 0 ships. |

### Concrete Mitigations

**For silent correctness drift** (the scariest failure mode — code that returns plausible but subtly wrong results): Contract compliance tests at Tier 3 encode every MUST clause as a test. Property-based tests at Tier 1b guard invariants across the entire input space. Evidence capture enables behavioral diffing in PRs — "This PR changed the actual output of 3 tests" is surfaced automatically.

**For the Two Orchestrators problem**: The Deny + Destroy pattern is preserved in `session_factory.py` and validated by an architecture fitness test that checks deny hook registration on every session creation. This is a Tier 4 concern — if it breaks, all work halts immediately.

**For accountability in autonomous changes**: Every AI-generated change creates a PR with structured evidence: trigger (which test failed), confidence score, proposed changes (diff), test results, and rollback instruction. A human approves or rejects. The approval creates an explicit accountability chain *before* deployment, not after incident.

---

## Closing Vision

We are building something that doesn't quite exist yet: a codebase that is *designed* to be maintained by AI agents, where human involvement is deliberately concentrated at the points of maximum leverage — architectural decisions, security review, and accountability — rather than spread thin across mechanical code review.

This is not a bet against human developers. It is a bet on *relocating* human judgment to where it matters most. The 73% of SDK changes that are mechanical type renames don't need a human staring at a diff. The 6% that are breaking removals absolutely do. The architecture makes this distinction explicit, measurable, and enforceable.

The skeptic asked the most important question in this entire debate: **"Will the machine ever actually run?"** The answer is: it runs next. Not after another round of philosophy. Phase 0 ships a decomposed, tested, CI-gated provider. Phase 1 ships canary tests and change detection. Phase 2 ships the first autonomous adaptation — or proves it shouldn't be built. Either outcome is a success.

The vision is not autonomy for its own sake. The vision is a system where the center stays still so the edges can move fast. Where contracts define what matters, tests prove it holds, and machines do the work that machines do best — while humans do the work that only humans can do.

Build the provider. Make it observable. Make it resilient. In that order.

---

*"Make the simple things simple, and the hard things possible." — Larry Wall*

*Applied here: The simple thing is Amplifier consuming uniform domain types. The hard thing is taming an agentic SDK while earning trust for autonomous maintenance. The architecture makes both possible — but only if we build the foundation before we build the future.*

---

**Document Control**

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-08 | Definitive synthesis of 31 debate documents across 3 waves and 3 rounds |

*This document replaces all previous vision documents and roadmaps. It is the implementation constitution for `next-get-provider-github-copilot`. No feature not listed here is in scope until Phase 0 ships.*
