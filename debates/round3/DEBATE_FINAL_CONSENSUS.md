# FINAL CONSENSUS: Next-Generation GitHub Copilot Provider Architecture

**Author**: The Zen Architect (Consensus Authority)  
**Date**: 2026-03-08  
**Inputs**: 31 documents across Wave 1 (8 agents), Wave 2 (10 agents), Wave 3 (8 agents), Round 2 (5 mediations)  
**Status**: FINAL — Foundation for Golden Vision

---

## 1. Unanimous Agreement

These positions were reached independently by every agent that examined the relevant domain. Zero dissent.

### 1.1 Decompose `provider.py` — The Monolith Must Die

**Agents in agreement**: Codebase Explorer (W1-A10), Python Architecture (W1-A6), Kernel Internals (W1-A3), Testing Architecture (W1-A8), Modular Architecture (W2-A20), Synthesis (W3-A29), Phased Approach (R2)

The 1799-line `provider.py` is an AI-hostile monolith. It concentrates 23 functions with a cyclomatic complexity of 47 and 14 cross-cutting concerns interleaved. An AI agent editing it must hold the entire file in context to understand even one function. The decomposition target is 5 extracted modules:

1. **`error_translation.py`** (~200 lines) — SDK → Kernel error mapping
2. **`tool_parsing.py`** (~250 lines) — parse tool calls, detect fakes, repair missing results
3. **`session_factory.py`** (~250 lines) — session configuration building
4. **`streaming.py`** (~200 lines) — streaming event handler and accumulator
5. **`completion.py`** (~350 lines) — LLM call lifecycle orchestration

The residual `provider.py` becomes a thin orchestration layer (~150–300 lines) that delegates to these modules. The existing 10 well-structured modules (`client.py`, `sdk_driver.py`, `converters.py`, `model_cache.py`, `model_naming.py`, `exceptions.py`, `_constants.py`, `_permissions.py`, `_platform.py`, `tool_capture.py`) remain unchanged — they are already correctly sized and well-bounded.

**Success criterion**: All existing tests pass with only import path changes. No module exceeds 400 lines (soft cap) or 600 lines (hard cap). Every common change touches ≤3 modules.

### 1.2 Flat Package Structure Over Nested Subpackages

**Agents in agreement**: Modular Architecture (W2-A20) explicitly rejected nested subpackages proposed by Python Architecture (W1-A6). Every subsequent agent adopted the flat approach. Synthesis (W3-A29) confirmed: "The consensus is decisive: 17 flat modules, not nested subpackages."

The package is already flat with 13 modules. Adding 5 more yields 18 flat modules with self-documenting names. Flat is easier for AI to navigate (no directory traversal), matches the existing codebase convention, and aligns with the kernel philosophy that self-contained directories should be modules, not hierarchies.

### 1.3 The "Deny + Destroy" Pattern Is Architecturally Sound

**Agents in agreement**: Kernel Internals (W1-A3), Streaming Architecture (W2-A19), Modular Architecture (W2-A20), Codebase Explorer (W1-A10), Performance Architecture (W2-A16), SDK Boundary Design (R2)

The Deny + Destroy pattern — capturing tool calls from SDK events, denying SDK tool execution via `preToolUse` hook, and destroying the ephemeral session — is the provider's most architecturally distinctive feature and is correct. It prevents the "Two Orchestrators" problem where both the Copilot SDK's internal agent loop and Amplifier's orchestrator try to execute tools.

**Critical implication**: Session pooling and session reuse are explicitly anti-patterns. The Performance Architecture agent called this out directly: "Don't try to pool sessions — it will break tool capture."

### 1.4 Contract-First Design Is Non-Negotiable

**Agents in agreement**: Contract Architecture (W2-A13), Testing Architecture (W1-A8), Self-Healing Design (W2-A12), CI/CD Architecture (W2-A18), Testing Reconciliation (R2), Synthesis (W3-A29)

Contracts are the immune system of the provider. Every SDK surface the provider touches gets a corresponding assumption test (canary). Every Provider Protocol requirement gets a compliance test. Contracts are defined before implementation, tested continuously, and serve as the SDK compatibility safety net.

The reconciled testing shape is the **Contract-Anchored Diamond**: contracts define WHAT to test, the diamond defines HOW MUCH, evidence captures WHAT HAPPENED, and properties guard WHAT MUST ALWAYS HOLD.

### 1.5 AI-Maintainability Is a First-Class Architectural Goal

**Agents in agreement**: All 31 documents reference AI agents as the primary maintainers. This manifests as:

- **Module size limits**: 400-line soft cap, 600-line hard cap
- **Self-documenting module docstrings**: every module opens with purpose, contract, dependencies
- **Structured error context**: errors carry machine-parseable diagnostic information
- **Machine-parseable telemetry**: structured events, not log lines
- **Regeneration over patching**: modules are small enough to regenerate entirely rather than surgically edit
- **`from __future__ import annotations`** in every file to prevent circular import failures

### 1.6 No SDK Type Crosses the Boundary

**Agents in agreement**: SDK Boundary Design (R2), Kernel Internals (W1-A3), Contract Architecture (W2-A13), Dependency Management (W2-A14)

The SDK adapter layer is a membrane. SDK types are translated into domain types at the boundary. Domain types are stable, versioned, and contain zero SDK imports. Only the adapter layer (`client.py`, `sdk_driver.py`, `converters.py`) imports from `@github/copilot-sdk`. Everything above speaks exclusively in Amplifier-native types.

### 1.7 Structured Observability Over Logging

**Agents in agreement**: Observability Architecture (W2-A11), Streaming Architecture (W2-A19), Performance Architecture (W2-A16), CI/CD Architecture (W2-A18), Synthesis (W3-A29)

Structured, machine-parseable events are the primary observability mechanism — not log lines. Every observation is JSON-structured, carries trace context, and is classifiable by criticality tier. This serves both human debugging and AI self-healing.

---

## 2. Majority Position

These positions were supported by the majority of agents, with specific dissenters noted.

### 2.1 Phased Delivery: Ship Simple, Earn Complexity

**Majority**: Phased Approach (R2), Skeptic Critique (W3), Skeptic Rebuttal (R2), Synthesis (W3-A29), Modular Architecture (W2-A20)  
**Dissenters**: Observability Architecture (W2-A11), CI/CD Architecture (W2-A18), Self-Healing Design (W2-A12) — who proposed comprehensive infrastructure from day one

The resolution: **Team Simple is right about sequencing. Team Comprehensive is right about direction.** Every feature must answer: "What failure mode does this prevent, and has that failure actually occurred or is it structurally inevitable?"

**Phase 0** (ship now): Decompose `provider.py`, write ~20 SDK canary tests, set up 3-gate CI (lint + types + tests), pin SDK version with manual rollback.

**Phase 1** (earn it): Property-based tests, SDK compatibility matrix, basic OTEL integration, performance benchmarks, automated SDK version diffing.

**Phase 2** (prove it): Self-healing adaptation for type changes, recipe-driven development workflows, test evidence system, expanded observability.

**Phase 3** (scale it): Full event bridge, AI confidence scoring, automated adaptation for behavioral changes, production anomaly detection.

### 2.2 Risk-Calibrated Human Involvement (Not Zero Human Review)

**Majority**: Skeptic Rebuttal (R2), Autonomy Boundaries (R2), Phased Approach (R2), Operational Excellence (W3)  
**Original position (corrected)**: Golden Vision Draft implied "minimal human intervention" which the Skeptic correctly identified as "sloppy language"

The updated position defines four tiers of autonomy:

| Tier | Human Involvement | Examples |
|------|-------------------|----------|
| **Tier 1: Full Autonomy** | None — deterministic validation only | Formatting, patch dep bumps (canary-passing), doc regen, cache invalidation |
| **Tier 2: Semi-Autonomy** | Human approves PR before merge | Bug fixes, SDK minor adaptation, new tests, policy value changes |
| **Tier 3: Guided Autonomy** | Human designs, AI implements | New features, architecture changes, security-related changes |
| **Tier 4: Human-Led** | Human does it, AI assists | SDK major version upgrades, paradigm shifts, breaking API changes |

**Security-related changes always require human review. No exceptions.**

### 2.3 Mechanism vs. Policy Is a Heuristic, Not a Religion

**Majority**: Skeptic Rebuttal (R2), Kernel Philosophy (W1-A5), Kernel Internals (W1-A3)  
**Dissenter on framing**: Skeptic Critique (W3) — called it "cargo-culting Linux"

The updated categorization acknowledges three classes:

- **Mechanism** (non-configurable): Rate limit respect (429 handling), token redaction, pagination execution, Deny + Destroy pattern, circuit breaker
- **Policy with sensible defaults** (configurable): Retry count/timing, backoff strategy, log verbosity, timeout values, pagination depth limits
- **Pure policy** (consumer-owned): Model selection, response formatting, conversation management

Every extracted policy gets a sensible default. The provider is safe and correct out-of-the-box.

---

## 3. Resolved Tensions

### 3.1 Nested Subpackages vs. Flat Modules → FLAT WINS

The Python Architecture agent (W1-A6) proposed 7 nested subpackages (`auth/`, `client/`, `models/`, `streaming/`, `tools/`, `config/`, `errors/`). The Modular Architecture agent (W2-A20) rejected this with five arguments: existing flat convention, manageable module count (~18), AI-friendliness, self-documenting names, and kernel philosophy alignment. Every subsequent agent adopted flat. **Resolved: 18 flat modules.**

### 3.2 Comprehensive Observability vs. YAGNI → PHASED DELIVERY

The Observability agent proposed 58 events, OTEL spans, GenAI semantic conventions, test evidence, session replay, and error correlation. The Skeptic and Phased Approach agent countered that 58 SDK event types "appear to be speculative" and building a testing framework before tests exist is premature. **Resolved: Phase 0 gets structured logging. Phase 1 gets basic OTEL. Phase 2+ earns the full event bridge, gated by proven need.**

### 3.3 Autonomy Level → FOUR-TIER MODEL WITH CONCRETE CRITERIA

Round 1 used aspirational language about "minimal human intervention." The Skeptic attacked this as a faith claim. The Autonomy Boundaries mediation (R2) produced a concrete four-tier decision tree with binary detection criteria at each level. **Resolved: Risk-calibrated autonomy with explicit escalation paths.**

### 3.4 SDK Boundary: Thin Wrapper vs. Full Adapter → CONTRACT-FIRST MEMBRANE

Dependency Management (W2-A14) favored thin wrapping. Provider Comparison (W3) showed other providers use various patterns. SDK Boundary Design (R2) resolved this: **Contract-First with Adapter Translation.** We define our own interfaces, the adapter translates. Neither too coupled (thin wrapper) nor too speculative (blind adapter). The membrane is precisely defined.

### 3.5 Testing Philosophy: Five Competing Proposals → CONTRACT-ANCHORED DIAMOND

Testing Reconciliation (R2) unified: AI-Code Test Diamond (thick middle layer), contract-first testing (MUST clauses → tests), evidence-based testing (structured proof), property-based testing (Hypothesis invariants), and SDK assumption testing (canaries). **Resolved: The Contract-Anchored Diamond with percentage allocations**: 20% pure unit, 10% property-based, 20% integration, 25% contract compliance, 15% SDK assumption, 5% live smoke, plus cross-cutting evidence capture.

### 3.6 Kernel Philosophy Applicability → HEURISTIC WITH NUANCE

The Skeptic called mechanism/policy separation "cargo-culting Linux." The Rebuttal demonstrated its concrete value: preventing the Two Orchestrators problem and enabling AI agents to modify one concern without reading 1799 lines. **Resolved: Mechanism/policy is a useful heuristic applied to THIS problem, not a general philosophy imported from Linux. The "Deny + Destroy" pattern is its strongest expression.**

---

## 4. Open Questions

### 4.1 Disk Cache for Models: Keep or Remove?

Performance Architecture recommends removing the disk cache tier (simplification). Codebase Explorer notes it's well-designed and working. **Unresolved**: needs real-world validation that bundled defaults cover all models. A new model added to the SDK but not bundled would be invisible. **Recommendation**: Keep for Phase 0, add to simplification backlog, validate before removing.

### 4.2 Observability Language: TypeScript vs. Python

The Observability Architecture (W2-A11) used TypeScript interfaces throughout. The provider is Python. **Unresolved**: All concepts are sound but must be translated to Python dataclasses/Protocols. This is a Phase 1 implementation detail, not a design disagreement.

### 4.3 58 SDK Event Types: Real or Speculative?

The Observability agent cataloged 58 events across 6 categories. The Synthesis agent flagged these as potentially speculative — "we don't know which of those 58 events actually exist in the SDK." **Unresolved**: Audit the actual SDK event types before designing the event bridge. The 58-event catalog is an aspirational target, not a confirmed inventory.

### 4.4 Recipe Architecture vs. GitHub Actions Boundary

Recipes run locally for development. Actions run in CI for release. The overlap zone (SDK change detection + AI fix) is unclear. **Partially resolved**: Actions-triggered, may invoke recipes as a step. Exact boundary deferred to Phase 1.

### 4.5 AI Auto-Fix Confidence Scoring

CI/CD proposed numeric thresholds (≥0.9 auto-merge, 0.7–0.9 create PR, <0.7 create issue). Self-Healing proposed categorical classification (type-change → auto-adapt, behavioral → attempt, removal → escalate). **Unresolved**: Recommendation is to use Self-Healing classification to SET the confidence score, then CI/CD thresholds to ACT on it. Deferred to Phase 2.

---

## 5. Key Numbers

### Architecture Metrics

| Metric | Current | Target | Source |
|--------|---------|--------|--------|
| `provider.py` lines | 1,799 | ~150–300 | W2-A20, R2-Phased |
| Total package modules | 13 | ~18 | W2-A20 |
| Max module lines (soft cap) | 1,799 | 400 | W2-A20, W1-A6 |
| Max module lines (hard cap) | 1,799 | 600 | W2-A20 |
| Max files touched per common change | Unbounded | ≤3 | W2-A20 |
| Cyclomatic complexity per module | 47 (provider.py) | ≤15 | W1-A6 |

### Performance Targets

| Metric | Current | Target | Source |
|--------|---------|--------|--------|
| Provider overhead per request | 120–475ms | <50ms | W2-A16 |
| Time-to-first-token overhead | Unknown | <100ms | W2-A16 |
| Health check cost per request | 30–100ms | 0ms (amortized) | W2-A16 |
| Session disconnect (critical path) | 20–80ms | 0ms (background) | W2-A16 |
| Event dispatch per event | 5–20ms | <1ms | W2-A16 |
| Max concurrent sessions | Unbounded | 10 (semaphore) | W2-A16 |

### Testing Targets

| Tier | % of Tests | Speed Limit | Source |
|------|-----------|-------------|--------|
| Pure unit tests | 20% | <10ms | R2-Testing |
| Property-based tests | 10% | <100ms | R2-Testing |
| Integration tests (stubbed) | 20% | <500ms | R2-Testing |
| Contract compliance tests | 25% | <100ms | R2-Testing |
| SDK assumption tests (canaries) | 15% | <200ms stubbed, <5s live | R2-Testing |
| Live smoke tests | 5% | <60s | R2-Testing |

### Autonomy Thresholds

| Criterion | Tier 1 (Auto) | Tier 2 (PR) | Tier 3 (Design) | Source |
|-----------|---------------|-------------|------------------|--------|
| Changes behavior | No | Yes | Yes | R2-Autonomy |
| Blast radius (files) | ≤3 | ≤10 | >10 | R2-Autonomy |
| Blast radius (% codebase) | — | ≤30% | >30% | R2-Autonomy |
| Changes public interface | No | Additive only | Any | R2-Autonomy |
| Affects security | No | No | Yes → always human | R2-Autonomy |
| Auto-heal confidence | — | ≥0.8 | <0.8 | R2-Autonomy |
| Max retry attempts | — | 3 | — | W2-A12 |

### Circuit Breaker Constants

| Constant | Value | Source |
|----------|-------|--------|
| SDK_MAX_TURNS_DEFAULT (soft limit) | 3 | W1-A10, W2-A19 |
| SDK_MAX_TURNS_HARD_LIMIT | 10 | W2-A19 |
| SDK_TIMEOUT_BUFFER_SECONDS | 5.0 | W1-A10 |
| Streaming event queue size | 256 | W2-A16 |
| Subprocess restart backoff | 1s, 2s, 4s, 8s, 16s, 30s | W2-A16 |
| Background heartbeat interval | 15s | W2-A16 |

---

## 6. Anti-Patterns — What We Explicitly Reject

### 6.1 Architectural Anti-Patterns

| Anti-Pattern | Why We Reject It | Agents Who Flagged It |
|-------------|------------------|----------------------|
| **Session pooling/reuse** | Incompatible with Deny + Destroy. Breaks tool capture. | W2-A16, W2-A19 |
| **Speculative session pre-creation** | Wastes resources for requests that may never come | W2-A16 |
| **LLM response caching** | Non-deterministic outputs. Semantically incorrect to cache. | W2-A16 |
| **Connection multiplexing** | CLI subprocess handles one JSON-RPC stream. Don't multiplex. | W2-A16 |
| **Synchronous fallbacks** | Never use `run_in_executor()` for operations that should be async. | W2-A16 |
| **Nested subpackages** | AI-hostile navigation, unnecessary for 18 modules. | W2-A20, W3-A29 |
| **Policy embedded in mechanism** | Creates hidden contracts, prevents independent modification. | W1-A5, R2-Rebuttal |
| **Multiple CLI subprocesses** | Each is ~500MB. Singleton pattern is mandatory. | W1-A10, W2-A16 |

### 6.2 Process Anti-Patterns

| Anti-Pattern | Why We Reject It | Agents Who Flagged It |
|-------------|------------------|----------------------|
| **Zero human review** | Faith claim, not engineering. Security always needs human judgment. | W3-Skeptic, R2-Rebuttal |
| **Building autonomy before reliability** | "Autonomy without ops maturity is automated self-harm" | W3-Skeptic, R2-Phased |
| **Testing framework before tests** | Evidence system, baseline comparison, regression detection are Phase 1+. Write tests first. | R2-Phased |
| **58-event bridge before auditing actual SDK events** | Speculative infrastructure for events that may not exist. | R2-Phased, W3-A29 |
| **Confidence thresholds without operational data** | AI confidence scoring requires historical track record. | R2-Phased |
| **Adapters without expiry dates** | Shims are technical debt by design. Must have explicit expiry. | W2-A12 |

### 6.3 Testing Anti-Patterns

| Anti-Pattern | Why We Reject It | Agents Who Flagged It |
|-------------|------------------|----------------------|
| **"Make tests pass" as sole success metric** | Goodhart's Law — AI will implement the wrong fix if tests are incomplete. | W3-Skeptic |
| **Traditional test pyramid for AI-written code** | Doesn't account for the "code that runs but misunderstands the requirement" failure mode. | W1-A8 |
| **Testing only happy paths** | AI handles happy paths well but misses edge cases. Property-based testing catches these. | W1-A8 |
| **Time-based cache invalidation on hot path** | Adds TTL-check overhead to every request. Use event-based invalidation. | W2-A16 |

### 6.4 Design Anti-Patterns

| Anti-Pattern | Why We Reject It | Agents Who Flagged It |
|-------------|------------------|----------------------|
| **SDK types crossing the boundary** | Creates coupling that makes SDK upgrades a full-codebase event. | R2-SDK-Boundary |
| **Awaiting hook emission in streaming** | Creates backpressure from hooks to SDK transport. Use fire-and-forget. | W2-A19 |
| **Multi-turn tool deduplication** | SDK retry behavior produces different tool calls on subsequent turns. First-turn-only is simpler and more predictable. | W2-A19 |
| **Event sourcing for stream accumulation** | Adds memory and CPU overhead. Mutable accumulator is O(n) tokens with O(1) state queries. | W2-A19 |
| **Premature optimization of message conversion** | At <5ms for typical conversations, it's not the bottleneck. Optimize session lifecycle first. | W2-A16 |

---

## 7. The Consensus in One Paragraph

The next-generation GitHub Copilot provider is a **flat-packaged, contract-first, AI-maintainable** Amplifier module built on the **Deny + Destroy** pattern. The 1799-line monolith is decomposed into ~18 flat modules under 400 lines each, with a strict SDK boundary membrane where no SDK type crosses into domain code. Testing follows the **Contract-Anchored Diamond** — thick middle layer of contract compliance and SDK assumption tests, anchored by property-based invariants at the base and live smoke tests at the apex. Human involvement is **risk-calibrated across four tiers**, from full autonomy for deterministic tasks to human-led design for breaking changes, with security always requiring human review. Infrastructure is delivered in **phases gated by proven need** — decomposition and canary tests now, observability and self-healing only after the provider reliably works. The architecture optimizes for **AI agents as primary maintainers**: small modules, structured events, explicit contracts, and regeneration over patching.

---

*This consensus document is the foundation for the Golden Vision. Every architectural decision made hereafter must be traceable to a position established in this document or must explicitly override one with stated justification.*
