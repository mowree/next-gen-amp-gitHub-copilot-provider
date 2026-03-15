# GOLDEN VISION: Next-Generation GitHub Copilot Provider for Amplifier

**Author**: The Vision Crystallizer (Agent 30, Wave 3)  
**Date**: 2026-03-08  
**Status**: Round 1 Synthesis — Draft for Council Review  
**Sources**: 18 expert analyses across 3 waves (8 Wave 1 + 10 Wave 2)

---

## 1. Executive Summary

We are building a **self-maintaining GitHub Copilot provider** — an Amplifier module that bridges the Copilot SDK's opinionated agent loop with Amplifier's sovereignty-preserving kernel, and that is designed from day one to be written, tested, healed, and evolved by AI agents with minimal human intervention. The current v1.0.4 provider (5,286 lines across 13 modules) successfully implements the "Deny + Destroy" pattern that preserves Amplifier's non-negotiables: FIC context compaction, session persistence, agent delegation, hook-driven observability, and tool execution sovereignty. But the 1,799-line `provider.py` monolith embeds policies as mechanisms, resists AI-friendly editing, and has no formal contract with the SDK it depends on. The next generation decomposes this monolith into AI-editable modules of 200-500 lines each, separates all 23 identified policies from mechanisms, wraps every SDK assumption in a canary test, instruments every observable action through an OTEL-aligned event bridge, and orchestrates its own maintenance through declarative recipes with human approval gates at architectural boundaries. This is not a rewrite — it is a disciplined evolution from a correct but rigid first generation into a system that can survive SDK changes, heal its own breakages, and prove its correctness through structured evidence.

---

## 2. Core Philosophy

### The Five Principles

**Principle 1: Mechanism, Not Policy**  
The provider is a device driver. It translates between Amplifier's unified protocol and the Copilot SDK's transport layer. Like a Linux filesystem driver that implements `struct file_operations` without deciding I/O scheduling, the provider implements the 5-method Provider protocol without deciding retry counts, timeout values, model preferences, or correction strategies. Twenty-three policies currently embedded in the provider have been catalogued and must be extracted to Amplifier's configuration layer, where different teams can make different choices. The litmus test is always: "Could two teams want different behavior?" If yes, it's policy. If no, it's mechanism.

**Principle 2: Sovereignty Preservation (Deny + Destroy)**  
Amplifier's value proposition depends on five non-negotiables: FIC context compaction, session persistence, agent delegation, hook-driven observability, and tool execution sovereignty. The Copilot SDK has its own opinions on all five. The provider's fundamental architectural commitment is that Amplifier wins every conflict. The SDK never accumulates conversation history (ephemeral sessions). The SDK never executes tools (preToolUse deny hook). The SDK never manages context (single-call sessions). The SDK never controls the agent loop (abort after first-turn tool capture). This is not adversarial — it is the only design that preserves Amplifier's ability to switch providers, apply custom policies, and enforce safety gates.

**Principle 3: AI-Editable Architecture**  
Every module must be readable in full by an AI agent without context window truncation. The target is 200-500 lines per module, with explicit interfaces via `typing.Protocol`, zero circular dependencies enforced by a strict dependency DAG, and `from __future__ import annotations` in every file. The module decomposition follows a "bricks and studs" philosophy: each module is a self-contained brick with a well-defined stud interface. An AI agent should be able to regenerate any single module from its contract specification without understanding the rest of the system. The current 1,799-line `provider.py` is an anti-pattern — a monolith that requires holding the entire file in context to make any local change.

**Principle 4: Evidence-Based Trust**  
AI-written code earns trust through structured proof, not faith. Every behavior has a corresponding test. Every SDK assumption has a canary test. Every adaptation has a recorded outcome. The test architecture follows an "AI-Code Test Diamond" — thick in the middle with SDK assumption tests and behavioral contract tests that don't exist in typical human-written projects. Property-based testing validates invariants across random inputs. Snapshot testing detects behavioral drift. The system doesn't just pass tests; it produces evidence that can be audited, queried, and used to improve future adaptations.

**Principle 5: Graceful Degradation Over Catastrophic Failure**  
When things go wrong — and they will, because the SDK will change — the system degrades gracefully. It pins to last-known-good versions. It generates adapter shims for type changes. It escalates to humans with full diagnostic context when it can't self-heal. It never crashes the kernel. It never silently corrupts state. The `mount()` function returns `None` on missing credentials instead of throwing. The circuit breaker trips at 3 turns with a hard limit of 10. The provider timeout fires 5 seconds before the SDK timeout so the provider controls the error narrative.

### Non-Negotiable Constraints

| Constraint | Rationale | Enforcement |
|-----------|-----------|-------------|
| Amplifier owns conversation state | FIC compaction requires full context control | Ephemeral SDK sessions, no state accumulation |
| Amplifier executes all tools | Safety gates (hook:pre deny, approval gates) | preToolUse deny hook, tool capture from events |
| Provider implements exactly 5 methods | Kernel protocol compliance, no feature creep | `@runtime_checkable` Protocol validation at mount |
| No SDK types in public interface | Provider boundary must be SDK-version-independent | Translation layer at SDK boundary |
| All failures are non-interfering | Module failures must not crash kernel | Exception catching at every boundary, graceful `None` returns |
| Every SDK assumption has a test | Self-healing requires detection before adaptation | `tests/sdk_assumptions/` canary suite |

---

## 3. Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AMPLIFIER KERNEL (Rust+PyO3)                     │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ Orchestrator  │  │   Context    │  │     Hook Registry         │ │
│  │ (tool loop,   │  │   Manager    │  │  (observe, block, modify, │ │
│  │  agent deleg.) │  │   (FIC)     │  │   inject, ask_user)       │ │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬──────────────┘ │
│         │                  │                       │                 │
│         ▼                  ▼                       ▼                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Provider Protocol (5 methods)                    │   │
│  │  name | get_info | list_models | complete | parse_tool_calls  │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              NEXT-GEN GITHUB COPILOT PROVIDER                       │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ provider  │  │converters│  │  models   │  │   config         │   │
│  │ (thin     │  │(Amplifier│  │(model map │  │  (settings,      │   │
│  │  orchestr)│  │ ↔ SDK)   │  │  + cache) │  │   mechanism vs   │   │
│  └────┬─────┘  └──────────┘  └──────────┘  │   policy split)  │   │
│       │                                      └──────────────────┘   │
│  ┌────┴─────────────────────────────────┐                           │
│  │         SDK Driver Layer              │                           │
│  │  ┌─────────────┐  ┌───────────────┐  │  ┌──────────────────┐   │
│  │  │   Stream     │  │    Loop       │  │  │   Event Bridge   │   │
│  │  │ Accumulator  │  │  Controller   │  │  │  (SDK → OTEL     │   │
│  │  │ (text, think │  │  (circuit     │  │  │   aligned hooks) │   │
│  │  │  tool capture)│  │   breaker)   │  │  └──────────────────┘   │
│  │  └─────────────┘  └───────────────┘  │                           │
│  └──────────────────────────────────────┘                           │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              SDK Boundary (Translation Layer)                  │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │   │
│  │  │  client   │  │   tool   │  │exceptions│  │  platform   │  │   │
│  │  │(lifecycle,│  │  capture  │  │(error    │  │ (CLI binary │  │   │
│  │  │ health)   │  │ (deny+   │  │ transl.) │  │  discovery) │  │   │
│  │  └─────┬────┘  │  destroy) │  └──────────┘  └─────────────┘  │   │
│  │        │       └──────────┘                                   │   │
│  └────────┼──────────────────────────────────────────────────────┘   │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│           COPILOT SDK (Python, wraps CLI subprocess)                 │
│                                                                     │
│  CopilotClient → CLI subprocess (~500MB) → JSON-RPC → LLM API     │
│  CopilotSession → event subscription → send/abort/disconnect        │
│  SessionEventType: 58+ event types                                  │
│  Hooks: preToolUse, postToolUse, onError, pre/postSessionCreate,    │
│         onSessionDestroy                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Module Decomposition

The target module structure decomposes the monolithic `provider.py` into focused, AI-editable modules:

```
provider_github_copilot/
├── __init__.py                  # mount() entry point, singleton client mgmt (~150 lines)
├── provider.py                  # Thin orchestration: complete(), parse_tool_calls() (~200 lines)
├── config/
│   └── settings.py              # Mechanism vs policy parameter separation (~150 lines)
├── converters/
│   ├── request.py               # Amplifier ChatRequest → SDK prompt format (~200 lines)
│   └── response.py              # SDK response → Amplifier ChatResponse (~200 lines)
├── streaming/
│   ├── accumulator.py           # StreamAccumulator state machine (~250 lines)
│   └── event_handler.py         # SdkEventHandler: event routing + emission (~200 lines)
├── sdk_driver/
│   ├── loop_controller.py       # Turn tracking, abort signaling (~150 lines)
│   ├── tool_capture.py          # ToolCaptureStrategy (first-turn-only) (~150 lines)
│   └── circuit_breaker.py       # Trip on turn count or timeout (~100 lines)
├── models/
│   ├── model_mapping.py         # CopilotModelInfo ↔ Amplifier ModelInfo (~200 lines)
│   ├── model_cache.py           # Disk-persistent metadata cache (~300 lines)
│   └── model_naming.py          # ID conventions, thinking detection (~250 lines)
├── client/
│   ├── wrapper.py               # CopilotClientWrapper lifecycle (~300 lines)
│   └── health.py                # Ping-based health checks (~100 lines)
├── events/
│   └── bridge.py                # SDK event → Amplifier hook translation (~200 lines)
├── errors/
│   └── exceptions.py            # Exception hierarchy + error detection (~250 lines)
├── _constants.py                # Mechanism constants only (~200 lines)
└── _platform.py                 # Cross-platform CLI binary discovery (~200 lines)
```

**Dependency rule**: Arrows only point DOWN. `config/` and `errors/` are leaf dependencies. No circular imports. Every module uses `from __future__ import annotations`.

### Key Interfaces

The system is held together by five critical interfaces:

1. **Provider Protocol** (5 methods, defined by Amplifier kernel): `name`, `get_info`, `list_models`, `complete`, `parse_tool_calls`
2. **StreamAccumulator** (internal state machine): `IDLE → THINKING → GENERATING → TOOLS_CAPTURED → COMPLETE`
3. **Event Bridge** (selective translation): SDK events classified as BRIDGE, CONSUME, or DROP
4. **ToolCaptureStrategy** (first-turn-only): `should_capture(turn) → bool`, `capture(turn, requests) → list`
5. **SDK Boundary** (translation layer): All SDK types are translated at the boundary; no SDK types leak into public interfaces

---

## 4. Autonomous Development Machine

### How This Code Maintains Itself

The system is designed for a world where AI agents are the primary maintainers. This means:

1. **Modules are regenerable**: Any single module can be deleted and regenerated from its contract specification. The specification includes inputs, outputs, error cases, and behavioral examples. An AI agent reading the spec and the test suite should produce a correct implementation without reading other modules.

2. **Tests are the specification**: The test suite is not just validation — it IS the specification. SDK assumption tests document what we depend on. Behavioral contract tests document what we promise. Property-based tests document invariants. An AI agent that passes all tests has, by definition, built the correct system.

3. **Recipes orchestrate everything**: Every maintenance task — implementation, testing, SDK upgrade adaptation, release validation — is encoded as a declarative YAML recipe with explicit steps, context accumulation, and approval gates.

### Recipe Architecture

Five core recipes compose into a master orchestration:

**Recipe 1: Provider Implementation (TDD Flow)**
```
analyze-sdk-interface → generate-test-suite → scaffold-provider
    → implement-provider → convergence-test-loop → refactor-pass
```
The convergence loop runs red-green-refactor cycles until all tests pass or a maximum iteration count (10) is reached. Human approval is NOT required for implementation — only for architectural decisions.

**Recipe 2: SDK Assumption Validation**
```
extract-assumptions → generate-validation-tests → run-validations → impact-analysis
```
Runs on every SDK version change. Extracts every assumption the provider makes about SDK behavior, generates focused validation tests, and produces an impact report for any violations.

**Recipe 3: Integration Testing (Staged)**
```
Stage 1: setup-test-env → smoke-test [APPROVAL GATE]
Stage 2: streaming-tests + error-handling-tests + concurrency-tests → report [APPROVAL GATE]
```
Human approval gates between stages. Smoke tests must pass before full integration suite runs.

**Recipe 4: Release Validation**
```
Stage 1: type-check + lint-check + test-check + security-scan + package-integrity
Stage 2: [HUMAN REVIEW GATE] → publish
```
Final quality gate before any release. Security scan is non-optional.

**Recipe 5: SDK Upgrade Adaptation**
```
check-sdk-updates → diff-analysis → [APPROVAL GATE for BREAKING changes]
    → run-assumption-tests → auto-adapt-or-escalate → validate → deploy-or-rollback
```
Automatic for patch/minor changes. Human approval required for breaking changes.

### State Management

Recipe state flows through three layers:

1. **Context accumulation**: Each recipe step's output becomes context for subsequent steps via `{{step_id}}` template variables
2. **Checkpoint persistence**: Recipes checkpoint after each step for resumability — if an agent crashes, execution resumes from the last checkpoint
3. **Approval gates**: Staged recipes pause at approval boundaries, presenting accumulated context to human reviewers with structured pass/fail summaries

---

## 5. Testing Strategy

### The AI-Code Test Diamond

Traditional test pyramids assume humans understand intent implicitly. AI-written code requires a different shape — thick in the middle where SDK assumptions and behavioral contracts live:

```
          /\
         /  \        Live Integration (5%) — Real API smoke tests
        /    \
       /──────\      SDK Assumption Tests (20%) — Do our SDK expectations hold?
      /        \
     /──────────\    Behavioral Contract Tests (25%) — Does code match spec?
    /            \
   /──────────────\  Pure Function Unit Tests (30%) — Transformations, parsing
  /                \
 /──────────────────\ Property-Based Tests (10%) — Invariants across random inputs
/                    \
\────────────────────/ Evidence Capture Tests (10%) — Structured proof of behavior
```

### SDK Assumption Tests

These are the canary tests that make self-healing possible. For every assumption the provider makes about the SDK:

| Category | What It Tests | Example |
|----------|--------------|---------|
| **Type Shape** | SDK exports the types we import | `CopilotRequestPayload` has `messages` field |
| **Function Signature** | Functions accept the args we pass | `createAckEvent()` takes no args |
| **Behavioral Contract** | SDK behaves as we expect | Streaming sends valid SSE events |
| **Error Contract** | Errors look like we expect | Auth failures return 401 |
| **Integration Point** | Glue code works with SDK | Handler receives parsed payload |
| **Event Ordering** | Events arrive in expected order | Deltas before complete message |

Each assumption test is tagged with:
- `Last verified: <date>`
- `SDK version: <version>`
- `Risk if violated: <high|medium|low>`
- `Auto-healable: <yes|no>`

### Property-Based Testing

Exceptionally valuable for AI-written code because AI handles happy paths well but misses edge cases:

```python
# Property: model list normalization never loses models
@given(st.lists(st.dictionaries(keys=st.text(min_size=1), values=st.text())))
def test_normalize_models_preserves_count(raw_models):
    normalized = normalize_model_list(raw_models)
    assert len(normalized) == len(raw_models)

# Property: token counting is monotonically non-decreasing
@given(st.text(), st.text())
def test_token_count_monotonic(text_a, text_b):
    if len(text_a) <= len(text_b):
        assert count_tokens(text_a) <= count_tokens(text_b) + 1

# Property: serialized requests always produce valid JSON
@given(st.builds(CompletionRequest, ...))
def test_request_serialization_always_valid_json(request):
    serialized = request.to_api_payload()
    parsed = json.loads(json.dumps(serialized))
    assert parsed["model"] == request.model
```

### Evidence-Based Testing

Every test produces structured evidence — not just pass/fail, but machine-readable proof:

```python
@evidence(
    contract="Provider.complete() returns ChatResponse with valid usage",
    category="behavioral_contract",
    sdk_version="0.2.0",
)
def test_complete_returns_valid_usage(provider, mock_session):
    response = await provider.complete(request)
    assert response.usage.input_tokens >= 0
    assert response.usage.output_tokens >= 0
    assert response.usage.total_tokens == response.usage.input_tokens + response.usage.output_tokens
```

Evidence is stored as structured JSON records, queryable for auditing, pattern recognition, and improvement feedback loops.

---

## 6. Observability Architecture

### Event Bridge

The provider sits at the junction of two event systems: the Copilot SDK's 58+ event types and Amplifier's hook-based emission system. The Event Bridge selectively translates between them:

```
SDK EVENT STREAM                    ACTION           AMPLIFIER EVENT
────────────────                    ──────           ───────────────
ASSISTANT_MESSAGE_DELTA          →  BRIDGE        →  llm:content_block
ASSISTANT_REASONING_DELTA        →  BRIDGE        →  llm:thinking_block
ASSISTANT_MESSAGE                →  BRIDGE        →  llm:response
SESSION_IDLE                     →  CONSUME       →  (internal control flow)
ERROR                            →  BRIDGE        →  provider:error
USAGE                            →  CONSUME       →  (accumulated into response)
preToolUse (hook)                →  CONSUME       →  (always DENY)
SESSION_START                    →  BRIDGE        →  sdk:session_start
SESSION_END                      →  CONSUME       →  (cleanup signal)
All other events                 →  DROP          →  (logged at debug level)
```

**Design principle**: Not a blind passthrough. Only events with meaningful Amplifier equivalents are bridged. SDK-internal control flow events are consumed. Irrelevant events are dropped.

**Fire-and-forget emission**: Streaming events use `loop.create_task()` without await to prevent hook backpressure from stalling token delivery. Hooks MUST NOT introduce backpressure on the streaming pipeline.

### OTEL Integration

The provider adopts OpenTelemetry GenAI Semantic Conventions (v1.34.0) for standardized observability:

```
Span Structure:
  amplifier.orchestrator.turn (parent)
    └── gen_ai.chat (CLIENT span)
        ├── Attributes:
        │   gen_ai.system = "github-copilot"
        │   gen_ai.request.model = "claude-opus-4.5"
        │   gen_ai.response.model = "claude-opus-4.5"
        │   gen_ai.request.max_tokens = 32000
        │   gen_ai.response.finish_reasons = ["stop"]
        │   gen_ai.usage.input_tokens = 1500
        │   gen_ai.usage.output_tokens = 800
        │   gen_ai.operation.name = "chat"
        │
        ├── Events (opt-in):
        │   gen_ai.content.prompt (redacted)
        │   gen_ai.content.completion (redacted)
        │
        └── Metrics:
            gen_ai.client.token.usage (histogram)
            gen_ai.client.operation.duration (histogram)
            copilot.stream.ttft_ms (gauge)
            copilot.stream.tokens_per_sec (gauge)
```

### Streaming Metrics

Per-request streaming metrics captured by the StreamAccumulator:

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `ttft_ms` | Time to first token | >5000ms warning |
| `ttft_text_ms` | Time to first text token (after thinking) | >60000ms for thinking models |
| `total_stream_ms` | Total stream duration | Context-dependent |
| `thinking_ms` | Duration of thinking phase | Informational |
| `tokens_per_sec` | Output generation speed | <5 tok/s warning |
| `delta_count` | Total delta events received | 0 with content = error |
| `max_gap_ms` | Maximum inter-event gap | >5000ms warning, >30000ms error |
| `turns_used` | SDK turns before completion | >1 unexpected, >3 circuit breaker |
| `text_buffer_peak_bytes` | Peak text accumulation | >100KB warning, >1MB error |

### Provider Health Dashboard

```
PROVIDER HEALTH STATUS
━━━━━━━━━━━━━━━━━━━━━
SDK Version:        pinned (last-known-good)
Canary Status:      ✅ All passing (last run: 2h ago)
Behavioral Drift:   0.0%
Adapter Count:      0
Next Compat Check:  scheduled

INTEGRATION POINTS:
  ├─ Payload Parsing:     ✅ Healthy
  ├─ Auth Verification:   ✅ Healthy
  ├─ SSE Streaming:       ✅ Healthy
  ├─ Tool Capture:        ✅ Healthy
  └─ Error Handling:      ✅ Healthy
```

---

## 7. Self-Healing Design

### Detection Mechanisms

Self-healing operates through three detection layers, ordered from cheapest to most expensive:

**Layer 1: Static Detection (pre-install, near-zero cost)**
- Package version diff via semver analysis
- Changelog parsing for BREAKING CHANGES
- TypeScript type signature diff for SDK exports
- Triggers: Dependabot PRs, Renovate updates, manual upgrades

**Layer 2: Canary Tests (post-install, low cost)**
- SDK assumption test suite (20% of all tests)
- Behavioral snapshot comparison against known-good outputs
- Contract verification across all integration points
- Runs: Every PR, nightly, and on SDK version change

**Layer 3: Runtime Monitoring (production, continuous)**
- Error rate anomaly detection (>2x baseline = alert)
- Response shape validation against expected patterns
- Latency deviation alerts (>2σ from baseline)
- Event type distribution monitoring (new/missing types flagged)

### Adaptation Strategies

When canary tests fail after an SDK upgrade, the system enters an adaptation pipeline:

```
TEST FAILS → CLASSIFY FAILURE → {TYPE_CHANGE | BEHAVIOR_CHANGE | BREAKING}
                                        │              │              │
                                   AUTO-ADAPT      ANALYZE &      ESCALATE
                                   via mapping     ATTEMPT FIX    TO HUMAN
                                        │              │
                                   VALIDATE        VALIDATE
                                        │              │
                                   Pass? → DEPLOY  Pass? → DEPLOY
                                   Fail? → RETRY   Fail? → ESCALATE
                                   (max 3)
```

**Type 1 — Shape Changes (60% of changes, 98% auto-healable)**:
- Field renames: `message.text` → `message.content`
- Type renames: `CopilotEvent` → `CopilotStreamEvent`
- Fix: AST-level transformations using auto-generated migration maps

**Type 2 — Behavioral Changes (30% of changes, 30% auto-healable)**:
- Response format changes, timing shifts, default value changes
- Fix: Generate adapter shim that normalizes new behavior to expected behavior
- Adapter shims carry deprecation comments and expiry dates

**Type 3 — Breaking/Removal (10% of changes, never auto-healable)**:
- Entire API removed, paradigm shift, security model change
- Fix: Human escalation with full diagnostic context

### Human Escalation

The system recognizes its limits through concrete signals:

```
CAN_AUTO_HEAL(failure) → boolean:
  IF failure.type == REMOVAL → false
  IF failure.blastRadius > 30% of codebase → false
  IF failure.hasMappableReplacement == false → false
  IF failure.isSecurityRelated → false
  IF failure.retryCount >= 3 → false
  IF failure.requiresNewAbstraction → false
  ELSE → true
```

Escalation produces a structured payload delivered via GitHub Issue:
- Severity classification
- SDK version delta
- Failed test list with line numbers
- Attempted fixes with results
- Recommended human action
- Rollback status (always active — running on last-known-good)
- Time pressure (SDK EOL dates)

### Rollback Strategy

Rollback is version pinning — always available, always fast (<5 minutes):

1. Revert `package.json` / `pyproject.toml` to pinned last-known-good version
2. Revert any auto-generated adapter code
3. Run full test suite to confirm clean state
4. Deploy the rollback
5. Log the failure for learning
6. Schedule retry with human review

The system maintains a **compatibility matrix** — auto-updated by CI — showing which SDK versions work with which provider versions.

---

## 8. Implementation Roadmap

### Phase 1: Foundation

**Goal**: Decompose the monolith. Establish the module structure, dependency DAG, and basic test infrastructure.

**Deliverables**:
1. Module decomposition from 1,799-line `provider.py` into target structure (13+ focused modules)
2. Dependency DAG enforcement (no circular imports, strict layering)
3. Policy extraction: Move all 23 identified policies to `config/settings.py` with Amplifier config pass-through
4. SDK boundary formalization: All SDK types translated at boundary, no leakage
5. Basic test infrastructure: pytest configuration, fixture hierarchy, test categorization
6. SDK assumption test suite: Canary tests for all known SDK assumptions
7. CI pipeline: lint + type check + unit tests on every commit

**Success criteria**: All existing tests pass against the decomposed structure. No behavior change. Module count increases from 13 to ~20. No module exceeds 500 lines.

### Phase 2: Core Intelligence

**Goal**: Implement the streaming state machine, event bridge, observability integration, and contract-first testing.

**Deliverables**:
1. `StreamAccumulator` as a standalone class with formal state machine (`IDLE → THINKING → GENERATING → TOOLS_CAPTURED → COMPLETE`)
2. Event Bridge with selective SDK→Amplifier translation (BRIDGE/CONSUME/DROP classification)
3. OTEL-aligned instrumentation: GenAI semantic conventions, streaming metrics
4. Behavioral contract test suite: 25% of test coverage dedicated to spec compliance
5. Property-based test suite: Hypothesis-driven invariant testing for all pure functions
6. Error handling formalization: Every SDK error code mapped, every provider error tested
7. Performance baseline: Latency budgets established, TTFT tracking, throughput benchmarks
8. Thinking model support: Full extended thinking flow with signature preservation
9. Health-based connection management: CLI subprocess crash → client unhealthy → restart

**Success criteria**: Full streaming pipeline tested in isolation. OTEL traces produced for every `complete()` call. All behavioral contracts have corresponding tests. TTFT < 2s for non-thinking models.

### Phase 3: Autonomy

**Goal**: Enable self-maintenance through recipes, self-healing, and continuous validation.

**Deliverables**:
1. Recipe suite: All 5 core recipes implemented and validated
2. Master orchestration recipe composing all sub-recipes
3. SDK upgrade detection and adaptation pipeline (automated for patch/minor)
4. Self-healing adaptation engine: type mapping, adapter shim generation, rollback
5. Knowledge capture system: Structured records of every adaptation (successful and failed)
6. Pattern recognition: Historical analysis of change types, auto-heal success rates
7. Compatibility matrix: Auto-updated CI job testing SDK versions against provider versions
8. Continuous validation schedule: nightly assumption tests, weekly compatibility matrix, monthly pre-release testing
9. Human escalation pipeline: Auto-created GitHub Issues with full diagnostic context
10. Documentation generation: Architecture docs auto-generated from module contracts

**Success criteria**: System survives a simulated SDK minor version bump without human intervention. Escalation fires correctly for simulated breaking changes. Recipe execution completes end-to-end for implementation and testing flows. Adaptation knowledge base has at least 10 recorded entries.

---

## 9. Success Criteria

### How We Know This Is Working

**Correctness Metrics**:
- All 5 Provider protocol methods pass behavioral contract tests
- SDK assumption test suite passes at 100% (any failure = detection success)
- Property-based tests find zero violations across 10,000+ random inputs
- Integration tests pass against live Copilot API (smoke level)
- No regression on the 305-turn loop bug (regression test passes)

**Architecture Metrics**:
- No module exceeds 500 lines
- Zero circular dependencies (enforced by import linter)
- All 23 policies externalized to configuration
- No SDK types in public interfaces
- Module cohesion score > 0.7 (LCOM4 metric)
- Coupling score: LOW (each module depends on ≤3 other modules)

**Autonomy Metrics**:
- Auto-heal success rate > 70% for type/field changes
- Mean time to auto-heal < 5 minutes
- Mean time to human escalation < 30 minutes (with full context)
- Recipe execution success rate > 90% for implementation flows
- SDK assumption test coverage > 95% of known assumptions

**Performance Metrics**:
- TTFT (time to first token) < 2 seconds for non-thinking models
- Total latency overhead (provider, excluding LLM) < 100ms
- Memory: < 50MB per provider instance (excluding CLI subprocess)
- CLI subprocess: single shared instance across all sessions (~500MB, amortized)
- Connection reuse: 100% (singleton client pattern)

**Observability Metrics**:
- 100% of `complete()` calls produce OTEL traces
- All streaming metrics captured per request
- Health dashboard reflects real-time provider status
- Error events include full diagnostic context

### The Junior Developer Test

The ultimate architecture success criterion: **a junior developer (or AI agent) can understand any single module by reading only that module and its direct dependencies.** No implicit knowledge required. No "you need to know about the bug we fixed in 2025" tribal knowledge. The module's tests, contract, and doc comment tell the complete story.

---

## 10. Risks and Mitigations

### Risk 1: SDK Breaking Changes

**Probability**: HIGH (the SDK is pre-1.0, actively evolving)  
**Impact**: Provider stops working  
**Mitigation**:
- Version pinning (exact versions, never ranges)
- Canary test suite detects changes before production deployment
- Automated adaptation handles 60-70% of changes
- Rollback to last-known-good in < 5 minutes
- Human escalation with full diagnostic context for breaking changes

### Risk 2: Over-Engineering the Self-Healing System

**Probability**: MEDIUM  
**Impact**: Complexity budget consumed by infrastructure instead of core functionality  
**Mitigation**:
- Apply 80/20 rule: Start with canary tests + version pinning + rollback (P0-P2)
- Defer full adapter generation (P6) and production anomaly detection (P7) until needed
- The canary test suite alone handles 80% of the problem
- Self-healing complexity must justify itself with measured auto-heal success rates

### Risk 3: AI Agent Context Window Limitations

**Probability**: HIGH (current models have 128K-200K context windows)  
**Impact**: AI agents can't hold enough context to make correct cross-module changes  
**Mitigation**:
- Module size cap at 500 lines (fits in any modern context window)
- Explicit interfaces via Protocol classes (no need to read implementations)
- Module contracts documented in docstrings (self-contained specs)
- Test suites as executable specifications (run tests to verify understanding)

### Risk 4: Recipe Execution Reliability

**Probability**: MEDIUM  
**Impact**: Autonomous workflows fail silently or produce incorrect results  
**Mitigation**:
- Convergence loops with maximum iteration caps (10 for TDD, 3 for adaptation)
- Human approval gates at architectural boundaries
- Checkpoint persistence for resumability
- Structured output validation at each step
- Escalation to human when iteration cap reached

### Risk 5: Copilot SDK CLI Subprocess Instability

**Probability**: MEDIUM (single process managing ~500MB, long-running)  
**Impact**: Provider becomes unavailable  
**Mitigation**:
- Ping-based health checks before returning cached client
- Auto-restart capability on subprocess crash detection
- Graceful degradation: health check failure → client recreation
- Provider timeout fires before SDK timeout (5s buffer) so provider controls error narrative
- Process-level singleton with reference counting prevents resource multiplication

### Risk 6: Drift Between Documentation and Implementation

**Probability**: HIGH (documentation rots faster than code)  
**Impact**: AI agents make incorrect decisions based on stale documentation  
**Mitigation**:
- Tests ARE the specification (executable, always current)
- Documentation generated from module contracts, not hand-written
- SDK assumption tests document what we depend on (machine-readable)
- Behavioral contract tests document what we promise (machine-readable)
- Evidence capture tests produce auditable proof (structured JSON)

### Risk 7: The "Two Orchestrators" Problem

**Probability**: LOW (mitigated by Deny + Destroy pattern)  
**Impact**: SDK's internal agent loop conflicts with Amplifier's orchestrator  
**Mitigation**:
- Ephemeral sessions: SDK never accumulates state
- preToolUse deny: SDK never executes tools
- First-turn-only capture: Take tools from turn 1, abort immediately
- Circuit breaker: Hard limit of 10 turns prevents runaway loops
- The SDK is treated as a "dumb pipe" — it generates, we orchestrate

---

## Closing: The Vision in One Sentence

We are building a provider that is **correct today** (passes all behavioral contracts), **resilient tomorrow** (detects and adapts to SDK changes), and **honest always** (escalates to humans when it reaches the limits of machine intelligence) — and we are building it in a way that AI agents can maintain it indefinitely, because every assumption is tested, every behavior is specified, every module is regenerable, and every adaptation is recorded.

The canary test suite is the self-healing system. Everything else is automation around the fundamental act of knowing what you depend on and checking if it still holds true.

---

*This document synthesizes the collective intelligence of 18 expert analyses. It is a living document — expected to evolve through subsequent debate rounds as consensus hardens and implementation reveals new truths.*
