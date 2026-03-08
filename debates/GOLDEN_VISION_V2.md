# The Golden Vision V2: The Config-First Evolution

**Version**: 2.1 — Kernel-Validated  
**Date**: 2026-03-08  
**Authority**: Synthesized from 43 documents across 3 waves, 4 rounds of adversarial debate, and 35 expert perspectives. **Validated against actual amplifier-core contracts by 10+ specialist agents.**  
**Status**: Implementation Constitution  
**Supersedes**: GOLDEN_VISION_FINAL.md (V1), GOLDEN_VISION_V2.md (2.0)

---

## Executive Summary

Forty-three documents. Thirty-five agent perspectives. Four rounds of adversarial debate — including a final round that nearly burned the vision to the ground and rebuilt it stronger. This document is the definitive architecture for a provider that doesn't just survive AI maintenance — it *invites* it.

The `next-get-provider-github-copilot` is a translation layer between the Amplifier kernel and the GitHub Copilot SDK. Today it is a 5,286-line codebase with a 1,799-line monolith at its center: cyclomatic complexity of 47, 14 cross-cutting concerns, and a documented 305-turn infinite loop caused by structural entanglement. It works, but it resists safe modification — by humans or machines.

Version 1 of this vision identified five innovations. The final round of debate — eight documents from the Config-First Skeptic, the Linux Kernel Lessons agent, the Bundle Architecture Expert, the Autonomous Config Maintenance analyst, and others — revealed a sixth: **the Three-Medium Architecture**. The insight is simple but transformative: not everything that governs behavior should be code. Policies are data. Contracts are prose. Only mechanical translation is code.

### The Six Innovations

1. **Contract-First SDK Boundary** — No SDK type crosses the membrane. Ever. A three-layer architecture (Adapter → Driver → Raw SDK) translates SDK reality into stable domain contracts. *(Preserved from V1)*

2. **The Deny + Destroy Pattern** — The provider's defining commitment. Every SDK session is ephemeral: a `preToolUse` hook denies all tool execution (preserving Amplifier's sovereignty), and sessions are destroyed immediately after the first turn completes. *(Preserved from V1, non-configurable)*

3. **The Three-Medium Architecture** — Python for mechanism, YAML for policy, Markdown for contracts. Each medium does what it does best. The result: a provider where the Python core approaches ~300 lines of irreducible logic, YAML configs declare all tunable behavior, and markdown contracts serve as both human documentation and AI-readable specifications. *(NEW — from final round synthesis)*

4. **Contract-Anchored Diamond Testing** — A testing strategy where every test traces to a contract clause, with a new tier for config compliance tests that verify YAML-driven behavior matches contract requirements. *(Evolved from V1)*

5. **Risk-Calibrated Human Involvement** — 60% of changes (config edits) require no human involvement; 25% (behavioral changes) require release-gate review; 10% (breaking changes) require full architectural review; 100% of security changes require human review. Config changes shift the balance dramatically toward safe autonomy. *(Evolved from V1)*

6. **Phased Delivery with Config Extraction** — Three phases, each gated on measurable criteria. Code extraction and config extraction happen simultaneously. Autonomy is earned through evidence, not assumed through architecture. *(Evolved from V1)*

### Why This Matters for the Industry

Every team building AI-assisted development tools faces the same question — how much can you trust the machine? V1 answered: trust is a spectrum calibrated to risk. V2 sharpens this: **trust is maximized when the machine edits data, not algorithms.** Config changes are bounded, validated, and reversible. Code changes are unbounded, fragile, and risky. An architecture that pushes 73% of maintenance into config changes is an architecture that earns trust 25× faster than one that requires code changes for every adaptation.

The Config-First Skeptic asked the hardest questions — about YAML hell, indirection taxes, governance overhead, and knob-creep. This vision integrates those warnings as design constraints: hard boundaries where invariants live in code, typed config models with semantic validation, effective-config explainability, and a strict litmus test for what belongs in each medium.

---

## Core Philosophy

### The Six Principles

**Principle 1: Translation, Not Framework**

The provider's job is translation — converting between the Amplifier protocol and the Copilot SDK. Every design decision must answer: "Does this add translation capability or framework complexity?" If the latter, remove it.

The provider does not manage retry logic (kernel policy), context windows (orchestrator concern), tool execution (always denied), or model selection preferences (consumer policy). It translates requests into SDK sessions, SDK events into domain events, and SDK errors into domain exceptions. The thinnest possible membrane between two systems that don't know about each other.

This principle prevents the "Two Orchestrators" problem — the most dangerous failure mode. The Copilot SDK has its own agent loop. Amplifier has its own orchestrator. If the provider starts making decisions about tool execution, conversation flow, or context management, it creates a hidden second brain. The Deny + Destroy pattern is the concrete mechanism that enforces this boundary.

**Principle 2: Three Mediums, Three Purposes**

This is the V2 evolution — the insight that emerged from 43 documents converging on the same truth from different angles:

```
┌─────────────────────────────────────────────────────────────┐
│  PYTHON — Mechanism                                         │
│  "How does the translation work?"                           │
│                                                             │
│  Control flow, state machines, async coordination,          │
│  type conversion, protocol mechanics, SDK boundary.         │
│  ~300 lines of irreducible logic.                           │
├─────────────────────────────────────────────────────────────┤
│  YAML — Policy                                              │
│  "What are the current behavioral choices?"                 │
│                                                             │
│  Error mappings, event routing, retry parameters,           │
│  timeout thresholds, model capabilities, circuit breaker    │
│  limits. ~200 lines of declarative data.                    │
├─────────────────────────────────────────────────────────────┤
│  MARKDOWN — Contracts                                       │
│  "What MUST be true?"                                       │
│                                                             │
│  Provider Protocol contract, SDK boundary rules,            │
│  Deny + Destroy invariants, error hierarchy semantics,      │
│  streaming completion signals. The source of truth.         │
└─────────────────────────────────────────────────────────────┘
```

**The litmus tests** (from the Hybrid Architecture Synthesis):

| Question | Answer |
|----------|--------|
| Does it require control flow, state, or type-safe transformation? | **Python** |
| Could two teams want different values? Is it a mapping or threshold? | **YAML** |
| Is it a requirement that implementations must satisfy? | **Markdown** |

**Anti-patterns to avoid:**

| Anti-Pattern | Why It's Wrong |
|-------------|----------------|
| Policy thresholds as Python constants | Changing `MAX_RETRIES = 3` requires code review + deploy |
| Mapping tables as `isinstance` chains | Adding a new SDK error type modifies an algorithm |
| Contracts as Python docstrings only | Docstrings drift from implementation |
| Config without defaults | Creates a policy fragmentation bomb |
| Config for control flow | `if config.use_streaming` makes code untestable |
| Markdown without tests | Unverified contracts are documentation that lies |

**Principle 3: Mechanism with Sensible Defaults**

Borrowed from kernel philosophy, applied as heuristic. The provider separates mechanism from policy — but every extracted policy ships with a sensible default. Policy extraction does not mean "leave it to the consumer." It means "provide a good default that can be overridden."

| Item | Classification | Default |
|------|---------------|---------|
| Rate limit handling (429) | **Mechanism** — API contract | Respect always |
| Backoff timing and jitter | **Policy** → YAML | Exponential with jitter |
| Token redaction in logs | **Mechanism** — security | Always redact |
| Log verbosity level | **Policy** → YAML | INFO |
| Retry count and timing | **Policy** → YAML | 3 retries, exponential |
| Deny + Destroy pattern | **Mechanism** — sovereignty | Non-configurable |
| Error classification table | **Policy** → YAML | See `config/errors.yaml` |
| Event routing decisions | **Policy** → YAML | See `config/events.yaml` |
| Circuit breaker limits | **Policy** → YAML | 3 soft, 10 hard |

**Principle 4: Design for SDK Evolution, Not SDK Stability**

The Copilot SDK is pre-1.0 and actively evolving. Historical analysis reveals: 73% of changes are type renames or field additions (config-healable), 21% are behavioral changes (partially config-healable), and 6% are breaking removals (require human intervention).

The V2 evolution: with config-driven architecture, 73% of SDK changes become YAML edits — not code changes. The architecture treats SDK changes as certainties and routes them through the safest possible change path.

| SDK Change Type | V1 Response | V2 Response |
|----------------|-------------|-------------|
| Type rename (73%) | AI edits Python, human reviews PR | AI edits YAML, auto-validated |
| Field addition (included above) | New Python code + tests | One-line YAML addition |
| Behavioral change (21%) | Human designs fix | Update contract + config, human reviews |
| Breaking removal (6%) | Full human intervention | Full human intervention (unchanged) |

**Principle 5: AI-Maintainability as First-Class Goal**

The codebase is written for AI readers first. This manifests as:

- **Module size limits**: 400-line soft cap, 600-line hard cap for Python. 50-line cap per config file.
- **Self-documenting contracts**: Every module references its contract file and clause. An AI agent reading the contract knows what the module does, what it depends on, and what it guarantees.
- **Structured error context**: Error messages include contract references, expected vs. actual values, and suggested fixes.
- **Regeneration over patching**: Modules are designed to be regenerated from their contract + config specification. When a module drifts from its spec, the correct action is regeneration, not archaeology.
- **Config as the primary maintenance surface**: 80% of expected maintenance is config edits — the safest possible change type for AI agents.

**Principle 6: Confidence-Gated Autonomy**

Every autonomous action carries an implicit or explicit confidence level. The Three-Medium Architecture adds a critical dimension: **change medium determines base confidence.**

| Medium | Base Confidence | Gate |
|--------|----------------|------|
| YAML config edit | Tier 1 (if tests pass) | Fully autonomous |
| Markdown contract update | Tier 2 | Human reviews PR |
| Python mechanism change | Tier 3 minimum | Human approves design + PR |
| Security-adjacent (any medium) | Tier 4 | Human only, always |

Trust is earned through track record: if the system successfully auto-heals 10+ config changes with zero regressions, Tier 1 scope expands. If it produces a single silent correctness regression, Tier 1 scope contracts.

### Non-Negotiable Constraints

1. **No SDK type crosses the adapter boundary.** Domain code never imports from the SDK.
2. **preToolUse deny hook on every session.** No exceptions. No configuration. The SDK never executes tools.
3. **Sessions are ephemeral.** Create, use once, destroy. No state accumulation.
4. **Security changes always require human review.** No confidence score overrides this.
5. **Tests must trace to contracts.** No orphan tests. No "test this because it seems important."
6. **Deny + Destroy is NEVER configurable.** This is mechanism, not policy. No YAML knob. *(NEW — from Config-First Skeptic's warning about knob-creep)*
7. **Every YAML config file has a schema.** Validated in CI on every commit. *(NEW — from Config-First Skeptic)*
8. **Effective config must be explainable.** Provenance per key, origin file, override layer. *(NEW — from Config-First Skeptic)*

---

## Architecture

### The Hybrid Directory Structure

```
provider-github-copilot/
├── bundle.md                    # Bundle definition for Amplifier ecosystem
├── config/                      # YAML policies — data, not logic
│   ├── retry.yaml               # Retry counts, backoff, jitter defaults
│   ├── errors.yaml              # SDK error → domain error mappings
│   ├── events.yaml              # SDK event classification (BRIDGE/CONSUME/DROP)
│   ├── models.yaml              # Model capabilities, naming, defaults
│   ├── circuit-breaker.yaml     # Turn limits, timeout buffers, thresholds
│   └── observability.yaml       # Metrics, alerting thresholds, log levels
├── contracts/                   # Markdown specifications — AI-readable truth
│   ├── provider-protocol.md     # The 5-method Provider Protocol contract
│   ├── sdk-boundary.md          # The membrane: what crosses, what doesn't
│   ├── error-hierarchy.md       # Domain exception taxonomy + retryability
│   ├── event-vocabulary.md      # The 6 stable domain event types
│   ├── deny-destroy.md          # The sovereignty pattern specification
│   ├── streaming-contract.md    # Delta accumulation, completion signals
│   └── behaviors.md             # Cross-cutting behavioral requirements
└── modules/
    └── provider-core/           # Python — irreducible mechanism
        ├── __init__.py           # mount() entry point
        ├── provider.py           # 5-method thin orchestrator (~120 lines)
        ├── completion.py         # LLM call lifecycle (~150 lines)
        ├── _types.py             # Shared domain types (zero SDK imports)
        ├── error_translation.py  # Config-driven error boundary (~80 lines)
        ├── tool_parsing.py       # Tool call extraction + accumulator (~120 lines)
        ├── session_factory.py    # Ephemeral session + deny hook (~100 lines)
        ├── streaming.py          # Config-driven event handler (~100 lines)
        ├── sdk_adapter/          # THE MEMBRANE — all SDK imports here
        │   ├── types.py          # SDK → domain type translation
        │   ├── events.py         # Config-driven event translation
        │   └── errors.py         # Config-driven error translation
        ├── client.py             # SDK subprocess management (preserved)
        ├── sdk_driver.py         # SDK session communication (preserved)
        ├── converters.py         # Message format conversion (preserved)
        ├── model_cache.py        # Model list caching (preserved)
        ├── model_naming.py       # Model ID normalization (preserved)
        ├── config.py             # YAML config loader + validation
        └── health.py             # Health check mechanism (preserved)
```

### The Three-Medium Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    contracts/*.md                                │
│  (Human + AI readable specifications — the SOURCE OF TRUTH)     │
│                                                                 │
│  "CopilotAuthError MUST have retryable=False"                  │
│  "preToolUse deny hook MUST be installed on every session"      │
│  "Sessions MUST be ephemeral — create, use once, destroy"       │
└──────────────────────────────┬──────────────────────────────────┘
                               │ specifies behavior for
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    config/*.yaml                                 │
│  (Policies, mappings, thresholds — TUNABLE DATA)                │
│                                                                 │
│  error_mappings:                                                │
│    - sdk_patterns: ["AuthenticationError"]                      │
│      domain_error: CopilotAuthError                             │
│      retryable: false    ← enforces contract clause             │
└──────────────────────────────┬──────────────────────────────────┘
                               │ consumed by
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              modules/provider-core/*.py                          │
│  (Mechanical translation — IRREDUCIBLE LOGIC)                   │
│                                                                 │
│  def translate_sdk_error(exc, mappings):                        │
│      for mapping in mappings:                                   │
│          if matches(exc, mapping.sdk_pattern):                  │
│              return mapping.domain_error(str(exc), ...)         │
│      return CopilotProviderError(str(exc), retryable=False)     │
└─────────────────────────────────────────────────────────────────┘
```

**The flow**: Contracts specify *what must be true*. Config declares *the current policy choices* that satisfy the contracts. Code implements *the mechanical translation* that executes the policies. Tests verify *that the code + config combination satisfies the contracts*.

### SDK Boundary Design

The boundary is a **Contract-First Membrane** — neither a thin wrapper (too coupled) nor a blind adapter (too speculative). We define what Amplifier needs, then the adapter translates the SDK's reality into our contracts.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AMPLIFIER CORE                                │
│  ChatRequest ─► Provider Protocol ─► ChatResponse               │
│  (our types)    (our contract)       (our types)                │
├───────────────────────── BOUNDARY ──────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐     │
│  │         SDK ADAPTER LAYER (the membrane)               │     │
│  │  Inbound:  ChatRequest → SDK session config            │     │
│  │  Outbound: SDK events → ContentBlock[]                 │     │
│  │  Errors:   SDK exceptions → domain exceptions          │     │
│  │  Types:    SDK types → NEVER cross this line           │     │
│  │  Config:   errors.yaml, events.yaml drive mappings     │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │         SDK DRIVER (containment)                       │     │
│  │  Session lifecycle, subprocess management,             │     │
│  │  agent loop suppression, circuit breaker               │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │         @github/copilot-sdk (radioactive)              │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

**Translation strategy**: Decompose, don't wrap. A `copilot.Message` becomes a `list[ContentBlock]`, not a `MessageWrapper(sdk_message)`. Opaque handles for stateful objects — `SessionHandle` is a UUID string, not an SDK session reference.

**Event reduction**: Of ~58 SDK event types, we translate ~8 into 6 stable domain event types, driven by `config/events.yaml`:

| Domain Event | SDK Source | Classification |
|-------------|-----------|----------------|
| `CONTENT_DELTA` | text_delta, thinking_delta | BRIDGE |
| `TOOL_CALL` | tool_use_complete | BRIDGE |
| `USAGE_UPDATE` | usage_update | BRIDGE |
| `TURN_COMPLETE` | message_complete | BRIDGE |
| `SESSION_IDLE` | session_idle | BRIDGE |
| `ERROR` | error | BRIDGE |
| *(internal)* | tool_use_start/delta, session_created/destroyed | CONSUME |
| *(dropped)* | tool_result_*, mcp_*, heartbeat, debug_* | DROP |

### Key Interfaces

The **Provider Protocol** — the immutable 4-method + 1 property contract with Amplifier:

> **CORRECTION (v2.1)**: The kernel protocol uses `**kwargs` for provider-specific options, not a named `on_content` callback. Return type is `ToolCall`, not `ToolCallBlock`. Streaming is provider-internal policy.

```python
class CopilotProvider(Protocol):
    @property
    def name(self) -> str: ...
    def get_info(self) -> ProviderInfo: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def complete(
        self, request: ChatRequest,
        **kwargs,  # Provider-specific options; streaming handled internally
    ) -> ChatResponse: ...
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...  # ToolCall, NOT ToolCallBlock
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

The **Error Hierarchy** — USE KERNEL TYPES, not custom exceptions:

> **CORRECTION (v2.1)**: The provider MUST raise `amplifier_core.llm_errors.*` types so orchestrators and hooks can catch them generically. Do NOT create a parallel hierarchy like `CopilotAuthError`. Map SDK errors directly to kernel error types.

```
# FROM amplifier_core.llm_errors (USE THESE):
LLMError (base)
├── AuthenticationError (retryable=False)      # SDK auth failures → this
├── RateLimitError (retryable=True)            # SDK 429/quota → this
├── LLMTimeoutError (retryable=True)           # SDK timeouts → this
├── ContentFilterError (retryable=False)       # SDK safety → this
├── NotFoundError (retryable=False)            # SDK model not found → this
├── ProviderUnavailableError (retryable=True)  # SDK session/subprocess → this
├── NetworkError (retryable=True)              # SDK connection → this
└── AbortError (retryable=False)               # User abort → this

# Classification still driven by config/errors.yaml, but domain_error values
# reference kernel types, not custom CopilotXxxError classes.
```

### Config File Specifications

**`config/errors.yaml`** — Error classification policy:

```yaml
# Error Translation Policy
# Contract: contracts/error-hierarchy.md
version: "1.0"

error_mappings:
  - sdk_patterns: ["AuthenticationError", "InvalidTokenError", "PermissionDeniedError"]
    string_patterns: ["401", "403"]
    domain_error: CopilotAuthError
    retryable: false

  - sdk_patterns: ["RateLimitError", "QuotaExceededError"]
    string_patterns: ["429"]
    domain_error: CopilotRateLimitError
    retryable: true
    extract_retry_after: true

  - sdk_patterns: ["TimeoutError", "RequestTimeoutError"]
    domain_error: CopilotTimeoutError
    retryable: true

  - sdk_patterns: ["ContentFilterError", "SafetyError"]
    domain_error: CopilotContentFilterError
    retryable: false

  - sdk_patterns: ["ModelNotFoundError", "ModelUnavailableError"]
    domain_error: CopilotModelNotFoundError
    retryable: false

  - sdk_patterns: ["SessionCreateError", "SessionDestroyError"]
    domain_error: CopilotSessionError
    retryable: true

  - sdk_patterns: ["ConnectionError", "ProcessExitedError"]
    domain_error: CopilotSubprocessError
    retryable: true

default:
  domain_error: CopilotProviderError
  retryable: false
```

**`config/events.yaml`** — SDK event routing policy:

```yaml
# Event Bridge Classification
# Contract: contracts/event-vocabulary.md
version: "1.0"

event_classifications:
  bridge:
    - sdk_type: text_delta
      domain_type: CONTENT_DELTA
      block_type: TEXT
    - sdk_type: thinking_delta
      domain_type: CONTENT_DELTA
      block_type: THINKING
    - sdk_type: tool_use_complete
      domain_type: TOOL_CALL
    - sdk_type: message_complete
      domain_type: TURN_COMPLETE
    - sdk_type: usage_update
      domain_type: USAGE_UPDATE
    - sdk_type: session_idle
      domain_type: SESSION_IDLE
    - sdk_type: error
      domain_type: ERROR

  consume:
    - tool_use_start
    - tool_use_delta
    - session_created
    - session_destroyed
    - usage

  drop:
    - tool_result_*
    - mcp_*
    - permission_*
    - context_*
    - heartbeat
    - debug_*

finish_reason_map:
  end_turn: STOP
  stop: STOP
  tool_use: TOOL_USE
  max_tokens: LENGTH
  content_filter: CONTENT_FILTER
  _default: ERROR
```

**`config/retry.yaml`** — Retry and resilience policy:

```yaml
# Retry and Circuit Breaker Policy
# Contract: contracts/behaviors.md
version: "1.0"

retry:
  max_attempts: 3
  backoff:
    strategy: exponential_with_jitter
    base_delay_ms: 1000
    max_delay_ms: 30000
    jitter_factor: 0.1

circuit_breaker:
  soft_turn_limit: 3
  hard_turn_limit: 10
  timeout_buffer_seconds: 5.0

streaming:
  event_queue_size: 256
  ttft_warning_ms: 5000
  max_gap_warning_ms: 5000
  max_gap_error_ms: 30000
```

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
                        │
                        ▼
                    config/*.yaml (read at startup, cached)
```

**Enforcement**: An architecture fitness test in CI scans all `.py` files and fails if SDK imports exist outside `sdk_adapter/`. A second fitness test fails if hardcoded policy values exist outside `config/`.

---

## The Autonomous Development Machine

### Four-Tier Autonomy Model

Autonomy is not binary. It is a spectrum calibrated to risk, earned through evidence, and enforced through gates. The Three-Medium Architecture adds a critical insight: **change medium is the primary risk classifier.**

```
TIER 1: FULLY AUTONOMOUS                    TIER 2: AI + HUMAN GATE
─────────────────────────────                ────────────────────────────
• YAML config edits (any)                    • Module extraction
• Format/lint fixes                          • New test contracts
• Type rename in config                      • Behavioral code changes
• Dependency version bumps (patch)           • Error handling changes
• Documentation/contract updates             • New config file creation

Gate: Schema valid + all tests pass          Gate: Human reviews PR
Rollback: Instant (file swap)               Rollback: Human reverts PR

TIER 3: HUMAN DESIGNS, AI IMPLEMENTS        TIER 4: HUMAN ONLY
────────────────────────────────────        ────────────────────────
• New module creation                        • Security changes (any)
• SDK boundary modifications                 • Breaking API changes
• Architecture changes                       • Deny+Destroy modifications
• New config schema additions                • Sovereignty-critical code
• Protocol changes                           • Incident response

Gate: Human approves design + PR             Gate: Human does everything
Rollback: Human decides approach             Rollback: Human manages
```

### Config Change vs Code Change Matrix

This is the V2 evolution — the matrix that emerged from the Autonomous Config Maintenance document and the 300-Line Challenge:

| Change Type | Medium | Code Needed? | Risk | Autonomy Tier |
|---|---|---|---|---|
| Retry policy adjustment | YAML | NO | Minimal | Tier 1 |
| Timeout value change | YAML | NO | Minimal | Tier 1 |
| New SDK error type mapping | YAML | NO | Low | Tier 1 |
| SDK type rename | YAML | NO | Minimal | Tier 1 |
| Event routing classification | YAML | NO | Low | Tier 1 |
| Model capability update | YAML | NO | Low | Tier 1 |
| Circuit breaker threshold | YAML | NO | Low | Tier 1 |
| Contract clause update | Markdown | NO | Low-Medium | Tier 2 |
| New pass-through SDK field | YAML + Python | MAYBE | Medium | Tier 2 |
| Streaming behavior change | Python | YES | Medium | Tier 3 |
| New authentication flow | Python | YES | High | Tier 3 |
| Breaking API restructure | All three | YES | High | Tier 3 |
| Deny hook modification | Python | YES | Critical | Tier 4 |
| Security boundary change | Python | YES | Critical | Tier 4 |

**The key insight from this matrix**: 8 of 14 change types (57%) are pure config changes. With the 73/21/6 SDK change distribution, approximately **73% of real-world SDK adaptations are config-only Tier 1 changes**.

### Quantified Risk Reduction

From the Autonomous Config Maintenance analysis:

| Dimension | Code Change | Config Change | Improvement |
|---|---|---|---|
| P(logic error) | 5-15% | 0% (no logic) | ∞ safer |
| P(behavioral regression) | 5-20% | 0-1% | 10-20× safer |
| Rollback time | Minutes to hours | Seconds | 60-3600× faster |
| Blast radius | Potentially unbounded | Bounded by schema | Fundamentally safer |
| **Composite risk per change** | **0.75%** | **0.03%** | **25× safer** |

Over 100 changes: code path gives ~75% chance of at least one production incident. Config path gives ~3%.

### Human Involvement Points

Humans are relocated, not eliminated. They add maximum value at:

| Point | Human Role | AI Role |
|-------|-----------|---------| 
| **Architectural review** | Design boundaries, approve SDK boundary changes | Implement designs, generate tests |
| **Config schema review** | Approve new config schemas (Tier 3) | Edit existing configs autonomously (Tier 1) |
| **Release gating** | Approve deployment of behavioral changes | Generate fix + evidence package |
| **Security review** | Review all security-adjacent changes | Flag potential security implications |
| **Adversarial validation** | Evaluate whether autonomy investment should continue | Execute benchmarks, report results |
| **Contract authorship** | Write and approve new contract clauses | Update existing contracts, verify compliance |

### Recipe Architecture

Recipes are declarative YAML workflows that encode repeatable processes. The provider starts with exactly **one recipe** (not five — earned, not assumed):

**Recipe: SDK Upgrade Adaptation**
```
detect-sdk-update → run-canary-suite → classify-failures
    → [CONFIG CHANGES: auto-apply + validate]
    → [CODE CHANGES: HUMAN APPROVAL GATE]
    → apply-fix → validate → deploy-or-rollback
```

The V2 evolution: the recipe now has a **config fast-path**. Changes classified as config-only skip human approval and proceed directly through schema validation → semantic validation → test suite → auto-deploy. Only code changes hit the human gate.

Additional recipes are added only after this one proves reliable across 5+ successful adaptations.

---

## Testing Strategy

### The Contract-Anchored Diamond (V2)

```
                    /\
                   /  \         TIER 7: Live Smoke (5%, nightly)
                  /    \        Real API, real tokens, real network
                 /──────\
                /        \      TIER 6: SDK Assumption Tests (10%, every PR)
               /          \     Recorded responses, shape validation, drift
              /────────────\
             /              \   TIER 5: Property-Based Tests (10%, every PR)
            /                \  Config-driven mappers handle ALL inputs
           /──────────────────\
          /                    \ TIER 4: Contract Compliance (20%, every PR)
         /                      \ One test per MUST clause, behavioral proof
        /────────────────────────\
       /                          \ TIER 3: Config Compliance (NEW, 10%)
      /                            \ Every config mapping produces correct output
     /──────────────────────────────\
    /                                \ TIER 2: Integration Tests (15%, every commit)
   /                                  \ Component wiring with stubs, full flows
  /────────────────────────────────────\
 /                                      \ TIER 1: Unit + Pure Function (25%, commit)
/                                        \ Pure functions, invariants, transforms
/──────────────────────────────────────────\

CROSS-CUTTING: Evidence capture (5%) — structured proof for all tiers
```

The diamond is widest at Tiers 3-4 (30% combined). This is deliberate. In AI-maintained code, the most dangerous failure is "code that runs but violates the contract" — and in a config-driven system, "config that parses but produces wrong behavior."

### Config Compliance Tests (NEW Tier)

The V2 addition. These tests verify that YAML-driven behavior matches contracts:

```python
class TestErrorConfigCompliance:
    """Verify config/errors.yaml satisfies contracts/error-hierarchy.md."""

    def test_auth_errors_not_retryable(self, error_config):
        """Contract: CopilotAuthError MUST have retryable=False."""
        auth_mapping = find_mapping(error_config, "CopilotAuthError")
        assert auth_mapping["retryable"] is False

    def test_all_sdk_patterns_have_domain_mapping(self, error_config):
        """Contract: Every SDK exception maps to exactly one domain exception."""
        for mapping in error_config["error_mappings"]:
            assert "domain_error" in mapping
            assert mapping["domain_error"] in VALID_DOMAIN_ERRORS

    def test_config_matches_hardcoded_reference(self, error_config):
        """Migration safety: config-driven mapper matches hardcoded original."""
        for sdk_error, expected_domain in REFERENCE_MAPPINGS.items():
            actual = config_driven_translate(sdk_error, error_config)
            assert type(actual).__name__ == expected_domain
```

During migration, both config-driven and hardcoded implementations run side-by-side. Tests verify they agree on every input. Once validated, the hardcoded version is removed.

### Test Categories (V2)

| Tier | Category | % | Speed Limit | When Run |
|------|----------|--:|------------|----------|
| 1 | Pure function unit tests | 15% | <10ms | Every commit |
| 1b | Property-based (Hypothesis) | 10% | <100ms | Every commit |
| 2 | Integration tests (stubbed) | 15% | <500ms | Every commit |
| 3 | **Config compliance tests** | **10%** | **<100ms** | **Every commit** |
| 4 | Contract compliance tests | 20% | <100ms | Every PR |
| 5 | Property-based (config-driven) | 10% | <100ms | Every PR |
| 6 | SDK assumption tests (canary) | 10% | <200ms stubbed | Every PR |
| 7 | Live smoke tests | 5% | <60s | Nightly |
| ∞ | Evidence capture | 100% | Zero overhead | Always |

### AI-Friendly Test Design

Five properties (preserved from V1, plus config awareness):

1. **Contract-anchored**: Every test cites the exact contract clause AND config file it verifies.
2. **Evidence-producing**: Structured data (inputs, expected, actual, config version), not just pass/fail.
3. **Self-diagnosing**: Failure messages tell the AI agent what contract was violated, what config produced the wrong result, and where to look.
4. **Deterministic and isolated**: Stubbed I/O, deterministic clocks, no shared mutable state.
5. **Speed-declared**: `@pytest.mark.pure`, `@pytest.mark.config`, `@pytest.mark.stubbed`, `@pytest.mark.live`.

### CI Pipeline (V2)

```
STAGE 1: Fast Feedback (every commit, <90s)
  ├── ruff check + ruff format --check
  ├── pyright (strict)
  ├── YAML schema validation (all config/*.yaml)      ← NEW
  └── pytest -m "pure or config or stubbed" --timeout=90

STAGE 2: Integration (every PR, <5min)
  ├── Cross-platform matrix (ubuntu + windows, Python 3.11 + 3.12)
  ├── pytest -m "local" --timeout=300
  ├── SDK assumption tests (stubbed mode)
  ├── Config compliance: verify YAML matches contracts   ← NEW
  └── Architecture fitness: no policy in Python code     ← NEW

STAGE 3: Evidence (every PR merge)
  ├── Behavioral diff against baseline
  └── Config diff annotated with contract references     ← NEW

STAGE 4: Live Smoke (nightly)
  ├── Live API tests with real tokens
  ├── SDK assumptions (live mode)
  └── Auto-create config update PR if API shape changed  ← NEW
```

---

## Implementation Roadmap

### Phase 0: Foundation + Config Extraction (Week 1) — "Extract and Externalize"

| Day | Deliverable | Success Criterion |
|-----|-------------|-------------------|
| 1 | Project scaffolding + config loader + `config/` directory + `contracts/` directory | `pip install -e ".[dev]"` succeeds, YAML schema validation runs, `contracts/deny-destroy.md` exists |
| 2 | Extract `error_translation.py` + `config/errors.yaml` | Config-driven mapper (~80 lines) matches hardcoded original on all inputs. 6+ unit tests pass |
| 3 | Extract `tool_parsing.py` | Pure code extraction — tool parsing is irreducible logic, not config. Module ≤250 lines |
| 4 | Extract `session_factory.py` + `streaming.py` + `config/events.yaml` | Deny hook always installed. Event routing config-driven. Deltas accumulate correctly |
| 5 | Extract `completion.py` + `config/retry.yaml` + `config/circuit-breaker.yaml` + integration verification | **ALL existing tests pass. Config files load and validate. No module >400 lines. Behavioral equivalence on 5 representative requests** |

**Gate**: If behavioral equivalence cannot be demonstrated on Day 5 and the cause cannot be identified within 4 hours, STOP. Revert everything. The monolith's behavior is the source of truth.

### Phase 1: Test the Contracts (Week 2) — "Make It Detectable"

| Day | Deliverable | Success Criterion |
|-----|-------------|-------------------|
| 6-7 | 20+ SDK canary tests + config compliance tests | Tests verify BOTH code behavior AND config correctness. Run in <10s total |
| 8 | CI pipeline with config validation | Pipeline blocks merge on YAML schema failure, Python lint failure, or test failure |
| 9 | Streaming metrics + architecture fitness tests | SDK boundary violations AND hardcoded policy values auto-detected |
| 10 | Contract documentation complete | All contracts in `contracts/` complete. Every MUST clause has a corresponding test. Adding a new SDK error type requires ONLY a YAML change (validated by test) |

**Gate**: Config-driven modules work identically to hardcoded originals. Contract compliance tests pass. SDK error adaptation is config-only.

### Phase 2: Config-Driven Adaptation (Weeks 3-4) — "Make It Resilient"

*Contingent on Phase 0-1 success.*

| Days | Deliverable | Success Criterion |
|------|-------------|-------------------|
| 11-12 | SDK event audit + event bridge | Audit produces actual event catalog → update `config/events.yaml` with real data |
| 13-14 | Weekly SDK change detection CI job | Detection job checks config mappings against SDK reality. Creates GitHub Issue on drift |
| 15-16 | Property-based tests for config-driven mappers | Test that mappers handle ALL inputs correctly for ANY valid config |
| 17-18 | Semi-automated adaptation prototype | **Key V2 insight**: Type 1 changes become config changes. Adaptation script edits YAML, not Python |
| 19-20 | **Adversarial validation** on 3-5 historical/simulated SDK changes | Test: can the system adapt to a simulated SDK error type addition by editing only `config/errors.yaml`? |

**Gate**: If adversarial validation success rate <50% for config-only adaptations, fall back to code-level adaptation with human review. Either outcome is a success — one validates the vision, the other saves months of misguided investment.

### The Kill List — What We Explicitly Do NOT Build

| Item | Status | Reason |
|------|--------|--------|
| AI auto-merge without human review | **KILLED** | No confidence score substitutes for human judgment on security |
| Adapter shim generation engine | **KILLED** | Shims are auto-generated technical debt. Direct fixes instead |
| Custom production APM | **KILLED** | Use existing tools (Datadog, Grafana) |
| Runtime event catalog validation | **KILLED** | Testing concern, not runtime concern |
| Multi-version SDK compatibility matrix | **KILLED** | We pin one version |
| Nested subpackage structure | **KILLED** | Flat package with clear naming |
| ABCs for internal interfaces | **KILLED** | Single-implementation interfaces are premature abstraction |
| Hot-reload config at runtime | **KILLED** | Config loaded at startup, cached. Restart for changes. Avoids complexity the Skeptic warned about |
| Config templating/expressions | **KILLED** | YAML is data, not a programming language. The Skeptic's "three languages" warning |
| Environment-specific config overlays | **DEFERRED** | Start with single config set. Earn overlays after proving base works |
| Full 58-event bridge | **DEFERRED** | Audit first, bridge reality not imagination |
| Full self-healing engine | **DEFERRED** | Contingent on adversarial validation results |
| 5 recipe pipelines | **DEFERRED** | Start with 1. Earn the rest |

### The 300-Line Target

Elon's challenge from the final round — "If limited to 300 lines, everything else is policy that shouldn't be in the provider" — is the TARGET, not a constraint.

**Current state**: 5,286 lines across 13 files.

**V2 target for new code** (excluding preserved modules like `client.py`, `sdk_driver.py`):

| Component | Target Lines | Medium |
|-----------|-------------|--------|
| `provider.py` | ~120 | Python |
| `completion.py` | ~150 | Python |
| `error_translation.py` | ~80 | Python |
| `tool_parsing.py` | ~120 | Python |
| `session_factory.py` | ~100 | Python |
| `streaming.py` | ~100 | Python |
| **Python subtotal** | **~670** | |
| `config/errors.yaml` | ~40 | YAML |
| `config/events.yaml` | ~40 | YAML |
| `config/retry.yaml` | ~25 | YAML |
| `config/models.yaml` | ~30 | YAML |
| `config/circuit-breaker.yaml` | ~10 | YAML |
| `config/observability.yaml` | ~15 | YAML |
| **YAML subtotal** | **~160** | |
| `contracts/*.md` | ~400 | Markdown |
| **Total new content** | **~1,230** | |

The 670 lines of new Python is higher than the 300-line aspiration because it includes the config loader, schema validation, and the adapter layer. The provider core — `provider.py` + `completion.py` — is ~270 lines. Elon's challenge is met for the translation mechanism itself.

---

## Risks and Mitigations

### Original Risks (Preserved from V1)

| # | Risk | P | I | Mitigation |
|---|------|:-:|:-:|------------|
| **R1** | Decomposition introduces behavioral regression | HIGH | HIGH | Snapshot comparison on Day 5. Stop-work: revert if cause not identified within 4 hours |
| **R2** | SDK breaking change during implementation | MEDIUM | HIGH | Exact version pin. Do not upgrade during Weeks 1-2. Canary tests detect future changes |
| **R3** | Canary tests can't be written (SDK not testable) | LOW | HIGH | Fallback: test against CLI subprocess output. Decision point on Day 6 |
| **R4** | Adaptation prototype gives false confidence | MEDIUM | HIGH | Adversarial validation on Day 20. If <50% success, cancel autonomy investment |
| **R5** | Scope creep | HIGH | MEDIUM | This document is the scope. No more debates until Phase 0 ships |

### Config-Specific Risks (NEW — from Config-First Skeptic)

| # | Risk | P | I | Mitigation |
|---|------|:-:|:-:|------------|
| **C1** | Config parsing introduces startup latency | LOW | LOW | YAML parsed once at load, cached. Measured overhead target: <5ms for all files |
| **C2** | Config schema drift from code expectations | MEDIUM | MEDIUM | JSON Schema validation on every config load. CI validates on every commit |
| **C3** | Config-driven error mapping misses edge case | MEDIUM | HIGH | Property-based testing: generate random exceptions, verify config-driven mapper matches hardcoded reference for ALL inputs |
| **C4** | "YAML hell" — two languages to debug | MEDIUM | MEDIUM | Config files capped at 50 lines each. No templating. No expressions. No inheritance. Pure declarative data |
| **C5** | Knob-creep — invariants become configurable | LOW | CRITICAL | Deny+Destroy is NEVER configurable. Architecture fitness test checks that non-negotiable constraints have no config path. The Skeptic's warning is an architecture test |
| **C6** | Config change bricks the system | LOW | HIGH | Schema validation prevents invalid YAML from loading. Rollback is instant file swap. Previous config archived automatically |
| **C7** | "Where does this value come from?" labyrinth | MEDIUM | MEDIUM | Single config layer — no overlays, no env-specific overrides (deferred). Effective config logged at startup with provenance |

### The Skeptic's Seven Questions — Answered

The Config-First Skeptic demanded answers, not hand-waves:

1. **Explainability**: Effective config logged at startup with provenance per key. `amplifier config explain` shows origin file and line.
2. **Semantic validation**: Config compliance tests verify cross-field constraints. Property-based tests verify all valid configs produce correct behavior.
3. **Migration**: Config files are versioned alongside code. Schema versions tracked in each file header. Migration is a YAML edit, not a code rewrite.
4. **Tooling parity**: YAML schema provides autocomplete in VS Code. Config files are small enough (<50 lines) that full IDE support is not critical.
5. **Testing strategy**: Config compliance tests (Tier 3) test behavior driven by config, not just data shape. Property-based tests verify correctness across the config space.
6. **Blast radius**: No hot-reload. Config loaded at startup. Changes require restart. Schema validation prevents invalid configs from loading.
7. **Security posture**: Deny+Destroy has no config knob. Architecture fitness test enforces this. Non-negotiable constraints are identified and protected.

### Concrete Mitigations

**For silent correctness drift** (the scariest failure mode): Contract compliance tests at Tier 4 encode every MUST clause. Config compliance tests at Tier 3 verify that YAML-driven behavior matches contracts. Property-based tests guard invariants across the config space. Evidence capture enables behavioral diffing — "This PR changed the actual output of 3 tests" is surfaced automatically.

**For the Two Orchestrators problem**: The Deny + Destroy pattern is preserved in `session_factory.py`, validated by an architecture fitness test, and **explicitly excluded from config**. This is a Tier 4 concern — if it breaks, all work halts immediately.

**For config-code drift**: During migration, both config-driven and hardcoded implementations run side-by-side. Tests verify they agree on every input. The hardcoded version is only removed after the config-driven version is proven equivalent.

**For accountability in autonomous changes**: Config changes create a PR with: trigger (which SDK change), config diff, schema validation result, test results, and rollback instruction. Config-only changes auto-merge if all gates pass. Code changes always require human approval.

---

## Closing Vision

We are building something that doesn't quite exist yet: a codebase maintained through **three mediums in harmony**. Python handles the irreducible mechanics of translation — the 300 lines that must be code because they are algorithms, state machines, and protocol bridges. YAML handles the tunable policies — the mappings, thresholds, and classifications that change when the SDK evolves but don't change how translation works. Markdown handles the contracts — the specifications that define what "correct" means, readable by humans and AI alike, testable through generated compliance suites.

This is not a compromise between the Code-First and Config-First camps. It is their synthesis — and it is the architecture that 43 documents were converging toward all along, even when individual agents couldn't see the whole picture. The Code-First camp built the skeleton: module boundaries, contract tests, SDK membrane. The Config-First camp added the nervous system: externalized policies, tunable behavior, declarative specifications. The Skeptic provided the immune system: stop-work criteria, adversarial validation, honest risk assessment, hard boundaries on what must never be configurable.

The future this enables: when the Copilot SDK ships v0.2.0 with three renamed types, two new error classes, and a changed event name, an AI agent reads the changelog, edits five lines of YAML, runs the test suite, and auto-deploys — all in under 60 seconds, with zero human involvement and bounded risk. The 6% of changes that are breaking removals still require human architects. But the 73% that are mechanical — the changes that currently consume engineering hours for mechanical translation — are absorbed by configuration.

The Skeptic asked the most important question: **"Will the machine ever actually run?"**

The answer: it runs next. With code that translates, config that adapts, and contracts that specify — in that order, each earning the right to exist by preventing a concrete failure mode.

Build the hybrid. Make it observable. Make it resilient. In that order.

---

*"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away." — Antoine de Saint-Exupéry*

*Applied here: We took away the hardcoded policies (moved to config). We took away the implicit contracts (moved to markdown). What remains is the irreducible core — the code that must be code, and nothing more.*

---

**Document Control**

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-08 | Definitive synthesis of 31 debate documents across 3 waves and 3 rounds |
| 2.0 | 2026-03-08 | Config-First Evolution: integrated 8 final-round documents (43 total), Three-Medium Architecture, config compliance testing, Skeptic's constraints, 300-line target, quantified risk reduction |
| **2.1** | **2026-03-08** | **Kernel Contract Validation: 10 specialist agents cross-referenced against actual amplifier-core. 7 corrections applied (see Errata below)** |

---

## Errata (v2.1) — Corrections from Multi-Agent Kernel Validation

The following errors were identified by dispatching 10 specialist agents (foundation:explorer, foundation:zen-architect, amplifier:amplifier-expert, core:core-expert, foundation:foundation-expert, python-dev:code-intel) against the actual amplifier-core contracts at `reference-only/amplifier-core/`.

| # | Original (v2.0) | Corrected (v2.1) | Severity | Source |
|---|-----------------|------------------|----------|--------|
| **E1** | "5-method Provider Protocol" | **4 methods + 1 property**: `name` (property), `get_info`, `list_models`, `complete`, `parse_tool_calls` | Critical | core:core-expert |
| **E2** | `complete(request, *, on_content=...)` | `complete(request, **kwargs)` — kernel uses `**kwargs`, not named streaming callback | Critical | amplifier:amplifier-expert |
| **E3** | `parse_tool_calls() -> list[ToolCallBlock]` | `parse_tool_calls() -> list[ToolCall]` — `ToolCall` has `arguments`, not `input` | Moderate | core:core-expert |
| **E4** | `ContentDelta` type for streaming | **Does not exist** — use `TextContent`, `ThinkingContent`, `ToolCallContent` from `content_models.py` | Moderate | core:core-expert |
| **E5** | Custom error hierarchy (`CopilotAuthError`, etc.) | **Must use kernel types** from `amplifier_core.llm_errors.*` — custom types break cross-provider error handling | Significant | amplifier:amplifier-expert |
| **E6** | Project name `provider-github-copilot` | Should be `amplifier-module-provider-github-copilot` per ecosystem convention | Moderate | foundation:foundation-expert |
| **E7** | No entry points in pyproject.toml | Must add `[project.entry-points."amplifier.modules"]` for kernel discovery | Critical | foundation:foundation-expert |

### Original Text (v2.0) — Preserved for Reference

<details>
<summary>Click to expand original Provider Protocol (before v2.1 correction)</summary>

```python
# ORIGINAL (v2.0) — DO NOT USE
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

</details>

<details>
<summary>Click to expand original Error Hierarchy (before v2.1 correction)</summary>

```
# ORIGINAL (v2.0) — DO NOT USE
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

</details>

*This document supersedes GOLDEN_VISION_FINAL.md (V1) and all previous vision documents. It is the implementation constitution for `next-get-provider-github-copilot`. It preserves everything V1 got right — Contract-First Membrane, Deny+Destroy, Testing Strategy, Four-Tier Autonomy — and integrates the config-first revolution that the final round of debate demanded.*

*No feature not listed here is in scope until Phase 0 ships.*
