# THE HYBRID ARCHITECTURE: Code + Config in Harmony

**Version**: 1.0 — Final Synthesis  
**Date**: 2026-03-08  
**Authority**: Synthesized from 31+ documents across 3 waves, 3 rounds of adversarial debate, 2 Golden Vision drafts, and 27 expert analyses  
**Status**: Definitive Architectural Resolution

---

## Preface: Why a Hybrid?

Thirty-one documents. Three waves. Three rounds. One skeptic who nearly burned the vision to the ground — and made it stronger. After digesting every word, every diagram, every adversarial challenge, one truth crystallizes: **neither camp was entirely right, and neither was entirely wrong.**

The Code-First camp (led by the Codebase Explorer, Python Architecture, and Modular Architecture agents) correctly identified that a GitHub Copilot provider is fundamentally a *translation engine* — mechanical protocol conversion that demands precise, testable Python code. You cannot YAML your way through JSON-RPC parsing, streaming event accumulation, or the preToolUse deny hook that preserves Amplifier's sovereignty.

The Config-First camp (implicit in the Kernel Philosophy, Observability Architecture, and Self-Healing Design agents) correctly identified that *policies are not code* — retry thresholds, error classification mappings, SDK event routing decisions, and model capability declarations are data, not logic. Encoding them as Python means every policy change requires a code review, a test run, and a deployment. That's organizational friction masquerading as engineering rigor.

The Hybrid Architecture resolves this tension. It draws a bright line: **mechanical translation is code; behavioral policy is config; contractual specification is markdown.** Each medium does what it does best. The result is a provider where the Python core is genuinely small (~300 lines of irreducible logic), the YAML configs declare all tunable behavior, and the markdown contracts serve as both human documentation and AI-readable specifications.

This is not a compromise. It is a synthesis — and it is the architecture that the 31-document debate was converging toward all along, even when individual agents couldn't see the whole picture.

---

## 1. What the Code-First Camp Got Right

### 1.1 Module Boundaries Are Essential

The unanimous consensus across all 31 documents — literally zero dissent — is that the 1,799-line `provider.py` monolith must die. The Codebase Explorer (Wave 1) measured the damage: cyclomatic complexity of 47, 14 cross-cutting concerns interleaved, 3 functions over 100 lines, and the infamous 305-turn infinite loop bug caused directly by structural entanglement.

The Code-First camp was right that this decomposition requires *code*, not configuration. You cannot extract `error_translation.py`, `tool_parsing.py`, `session_factory.py`, `streaming.py`, and `completion.py` by writing YAML files. These are mechanical translation modules where Python's type system, pattern matching, and async/await primitives are irreplaceable. The Module Specifications document (Round 3) proved this by defining contracts so precise that an AI agent can regenerate any module from its specification alone — but the specification describes *Python code*, not configuration.

**The lasting contribution**: The flat package structure with 17-18 modules, each under 400 lines, with a strict downward-only dependency DAG. This is a code architecture decision, and it was the right one. The Modular Architecture agent (Wave 2) defeated the nested subpackage proposal with five compelling arguments, and every subsequent agent adopted the flat approach. The consensus was decisive and correct.

### 1.2 Contract Testing as Executable Specification

The Code-First camp's strongest insight was that *tests ARE the specification*. The Contract Architecture agent (Wave 2) and Testing Reconciliation mediator (Round 2) converged on the Contract-Anchored Diamond — a testing shape deliberately thick in the middle where SDK assumption tests and behavioral contract tests live.

This is fundamentally a code-first idea: the contract between the provider and the SDK is expressed as executable Python tests, not as documentation that can drift. When the SDK changes `message.text` to `message.content`, a canary test fails immediately. No amount of YAML configuration catches this. The 20+ SDK assumption tests planned for Week 2 of the roadmap are pure code — `isinstance` checks, attribute assertions, behavioral validations against recorded responses.

**The lasting contribution**: Every SDK assumption encoded as a test. Every Provider Protocol requirement encoded as a compliance test. Every invariant encoded as a property-based test (Hypothesis). The testing strategy (20% pure unit, 10% property-based, 20% integration, 25% contract compliance, 15% SDK assumption, 5% live smoke) is a code-first achievement that the Hybrid Architecture preserves wholesale.

### 1.3 The SDK Boundary Membrane

The SDK Boundary Design document (Round 2) defined the architecture's most important code-level decision: **No SDK type crosses the boundary. Ever.** The Contract-First Membrane pattern — where domain types are defined independently, and the adapter layer translates between SDK reality and domain contracts — is irreducibly a code architecture.

The three-layer stack (Adapter → Driver → Raw SDK) cannot be expressed in configuration. The `translate_sdk_error()` function, the `EventTranslator` class, the `ToolCallAccumulator` state machine — these are algorithms, not policies. The decompose-don't-wrap rule (a `copilot.Message` becomes a `list[ContentBlock]`, not a `MessageWrapper(sdk_message)`) is a code design pattern that protects the entire system from SDK coupling.

**The lasting contribution**: The opaque `SessionHandle` pattern, the reverse translation for outbound types, the architecture fitness test that scans imports and fails CI if SDK types leak beyond the adapter. These are code mechanisms that the Hybrid Architecture not only preserves but elevates as the non-negotiable foundation.

---

## 2. What the Config-First Camp Got Right

### 2.1 Policies Should Not Be Code

The Skeptic's critique (Wave 3) landed a devastating blow on the original vision's handling of mechanism vs. policy: "Is retry 'policy'? Yes. But does a provider need a default retry strategy? Also yes." The Rebuttal (Round 2) conceded the point and produced the most important table in the entire debate — the mechanism/policy/pure-policy classification.

But the Rebuttal didn't go far enough. Consider the error translation table from the SDK Boundary Design document:

```
SDK AuthenticationError       → CopilotAuthError          False
SDK RateLimitError            → CopilotRateLimitError     True, extract retry_after
SDK TimeoutError              → CopilotTimeoutError       True
```

This mapping is *data*, not *logic*. The `translate_sdk_error()` function's 50-line chain of `isinstance` checks is encoding a lookup table as imperative code. When the SDK adds `copilot.QuotaExhaustedError` (which it will — the SDK is pre-1.0), someone must modify Python code, run tests, and deploy. But the *decision* — "quota exhaustion maps to rate limiting, which is retryable" — is a policy choice that belongs in a YAML file:

```yaml
# config/errors.yaml
error_mappings:
  - sdk_pattern: "AuthenticationError|InvalidTokenError|PermissionDeniedError"
    domain_error: CopilotAuthError
    retryable: false
  - sdk_pattern: "RateLimitError|QuotaExceededError|QuotaExhaustedError"
    domain_error: CopilotRateLimitError
    retryable: true
    extract_retry_after: true
  - sdk_pattern: "TimeoutError|RequestTimeoutError"
    domain_error: CopilotTimeoutError
    retryable: true
```

The Python code becomes a generic mapper that reads this config. Adding a new SDK error type becomes a one-line YAML change — no code review for the translation logic, no risk of introducing a bug in the `isinstance` chain. The AI agent maintaining this system edits a data file, not an algorithm.

**The lasting contribution**: The recognition that 23 policies currently embedded in the monolith should be externalized — but externalized as *config with sensible defaults*, not as bare extension points. Every policy ships with a default that makes the provider safe and correct out-of-the-box.

### 2.2 Markdown Contracts Are More AI-Friendly Than Code Comments

The Module Specifications document (Round 3) is the debate's most impressive technical artifact. It defines three modules with such precision that an AI agent can implement them without reading other files. But consider: the specification is *markdown*, not code.

The specification works because it uses structured natural language to express contracts:

> "Contract: translate_sdk_error() MUST NEVER raise. MUST preserve original exception as .original attribute. MUST set retryable correctly per the classification table."

An AI agent reading this markdown understands the contract faster and more reliably than it would by reading the Python implementation. The markdown *is* the specification; the Python *is* the implementation. Conflating them (as docstrings attempt to do) creates a maintenance burden — the docstring must stay synchronized with the code, and when they drift, the docstring lies.

The Hybrid Architecture formalizes this insight: contracts live in markdown files under `contracts/`, and they are the source of truth. Python docstrings reference the contract file and clause, but they don't duplicate the specification. When an AI agent needs to regenerate a module, it reads the contract markdown, not the existing implementation.

**The lasting contribution**: Markdown as a first-class specification format for AI-maintained systems. Not documentation-as-afterthought, but specification-as-primary-artifact. The contract files are versioned, tested (by the compliance test suite), and treated as the authoritative definition of behavior.

### 2.3 The 300-Line Core Is Achievable with Config

The Golden Vision Final set a target of `provider.py` at ~300 lines — a thin 5-method delegation layer. But achieving this target while preserving all current behavior requires moving substantial logic *somewhere*. The Code-First camp moved it into extracted Python modules. The Config-First insight is that much of that logic is actually *configurable data*:

- **Model capabilities** (context window, max tokens, supports_tools, supports_vision) — currently computed in code → YAML declarations
- **Event routing decisions** (which SDK events to BRIDGE, CONSUME, or DROP) — currently a match statement → YAML classification table
- **Retry parameters** (backoff timing, jitter, max attempts) — currently hardcoded constants → YAML policy with defaults
- **SDK type mappings** (which SDK fields map to which domain fields) — currently manual translation functions → YAML mapping declarations

When you extract these data-shaped concerns into YAML, the remaining Python code shrinks dramatically. The `error_translation.py` module drops from ~200 lines of `isinstance` chains to ~80 lines of generic mapping logic. The `streaming.py` module drops event routing from a 20-case match statement to a config-driven dispatcher. The total Python footprint for the provider core approaches ~300 lines of genuinely irreducible logic.

**The lasting contribution**: The principle that *if it looks like a lookup table in code, it should be a lookup table in config*. Code handles control flow, state management, and protocol mechanics. Config handles mappings, thresholds, classifications, and declarations.

---

## 3. The Hybrid Architecture

### 3.1 Directory Structure

```
provider-github-copilot/
├── bundle.md                    # Bundle definition for Amplifier ecosystem
├── config/                      # YAML policies — data, not logic
│   ├── retry.yaml               # Retry counts, backoff, jitter defaults
│   ├── errors.yaml              # SDK error → domain error mappings
│   ├── sdk-mappings.yaml        # SDK type field → domain type field maps
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
    └── provider-core/           # <300 lines Python — irreducible logic
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

### 3.2 How the Three Mediums Interact

```
┌─────────────────────────────────────────────────────────────┐
│                    contracts/*.md                            │
│  (Human + AI readable specifications — the SOURCE OF TRUTH) │
│                                                             │
│  "CopilotAuthError MUST have retryable=False"              │
│  "preToolUse deny hook MUST be installed on every session"  │
│  "Sessions MUST be ephemeral — create, use once, destroy"   │
└──────────────────────────┬──────────────────────────────────┘
                           │ specifies behavior for
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    config/*.yaml                             │
│  (Policies, mappings, thresholds — TUNABLE DATA)            │
│                                                             │
│  error_mappings:                                            │
│    - sdk_pattern: "AuthenticationError"                     │
│      domain_error: CopilotAuthError                         │
│      retryable: false    ← enforces contract clause         │
└──────────────────────────┬──────────────────────────────────┘
                           │ consumed by
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              modules/provider-core/*.py                      │
│  (Mechanical translation — IRREDUCIBLE LOGIC)               │
│                                                             │
│  def translate_sdk_error(exc, mappings):                    │
│      for mapping in mappings:                               │
│          if matches(exc, mapping.sdk_pattern):              │
│              return mapping.domain_error(str(exc), ...)     │
│      return CopilotProviderError(str(exc), retryable=False) │
└─────────────────────────────────────────────────────────────┘
```

**The flow**: Contracts specify *what must be true*. Config declares *the current policy choices* that satisfy the contracts. Code implements *the mechanical translation* that executes the policies. Tests verify *that the code + config combination satisfies the contracts*.

### 3.3 Config File Specifications

**`config/errors.yaml`** — Error classification policy:

```yaml
# Error Translation Policy
# Contract: contracts/error-hierarchy.md
# Every SDK exception maps to exactly one domain exception.
# Unknown exceptions default to CopilotProviderError(retryable=false).

version: "1.0"

error_mappings:
  - sdk_patterns:
      - "AuthenticationError"
      - "InvalidTokenError"
      - "PermissionDeniedError"
    string_patterns: ["401", "403"]
    domain_error: CopilotAuthError
    retryable: false
    extract_retry_after: false

  - sdk_patterns:
      - "RateLimitError"
      - "QuotaExceededError"
    string_patterns: ["429"]
    domain_error: CopilotRateLimitError
    retryable: true
    extract_retry_after: true

  - sdk_patterns:
      - "TimeoutError"
      - "RequestTimeoutError"
    stdlib_types: ["asyncio.TimeoutError"]
    domain_error: CopilotTimeoutError
    retryable: true

  - sdk_patterns:
      - "ContentFilterError"
      - "SafetyError"
    domain_error: CopilotContentFilterError
    retryable: false

  - sdk_patterns:
      - "ModelNotFoundError"
      - "ModelUnavailableError"
    domain_error: CopilotModelNotFoundError
    retryable: false

  - sdk_patterns:
      - "SessionCreateError"
      - "SessionDestroyError"
    domain_error: CopilotSessionError
    retryable: true

  - sdk_patterns:
      - "ConnectionError"
      - "ProcessExitedError"
    stdlib_types: ["ConnectionRefusedError"]
    domain_error: CopilotSubprocessError
    retryable: true

retry_after_pattern: "retry.after\\D*(\\d+(?:\\.\\d+)?)"

default:
  domain_error: CopilotProviderError
  retryable: false
```

**`config/events.yaml`** — SDK event routing policy:

```yaml
# Event Bridge Classification
# Contract: contracts/event-vocabulary.md
# Every SDK event is classified as BRIDGE, CONSUME, or DROP.

version: "1.0"

event_classifications:
  bridge:  # Translate to domain events
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

  consume:  # Used internally, not emitted
    - tool_use_start      # Buffered for accumulation
    - tool_use_delta      # Buffered for accumulation
    - session_created     # Internal bookkeeping
    - session_destroyed   # Internal bookkeeping
    - usage               # Accumulated into response

  drop:  # Ignored with debug logging
    - tool_result_*       # We deny all tool execution
    - mcp_*               # We don't use MCP
    - permission_*        # approve-all configured
    - context_*           # We manage our own context
    - heartbeat           # Health check only
    - debug_*             # Not domain events

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

subprocess:
  restart_backoff_ms: [1000, 2000, 4000, 8000, 16000, 30000]
  health_check_interval_seconds: 15

streaming:
  event_queue_size: 256
  ttft_warning_ms: 5000
  max_gap_warning_ms: 5000
  max_gap_error_ms: 30000
  text_buffer_warning_bytes: 102400   # 100KB
  text_buffer_error_bytes: 1048576    # 1MB
```

### 3.4 Contract File Specifications

**`contracts/deny-destroy.md`** — The sovereignty pattern:

```markdown
# Deny + Destroy Pattern

## Purpose
Preserve Amplifier's tool execution sovereignty when using the Copilot SDK.

## Non-Negotiable Invariants

1. **DENY**: The `preToolUse` hook MUST be installed on every SDK session.
   The hook MUST return a deny response. No exceptions. No configuration.

2. **DESTROY**: Every SDK session MUST be ephemeral.
   Create → use once → destroy. No session pooling. No session reuse.
   No state accumulation across requests.

3. **FIRST-TURN-ONLY**: Tool calls are captured from the first turn only.
   The SDK's internal agent loop is suppressed by the deny hook.

## Why This Exists
The Copilot SDK has its own agent loop. Amplifier has its own orchestrator.
If both execute tools, they create the "Two Orchestrators" problem —
conflicting decisions about tool execution, context management, and
conversation flow. The Deny + Destroy pattern prevents this by ensuring
the SDK is a "dumb pipe" that generates text, while Amplifier orchestrates.

## Security Classification
Tier 4 — Human-only changes. Any modification to this pattern requires
full architectural review. AI agents MUST NOT modify deny hook behavior.
```

---

## 4. Decision Criteria: When to Use What

| When to use...      | Criteria                                                         | Examples                                                          |
|----------------------|------------------------------------------------------------------|-------------------------------------------------------------------|
| **Python code**      | Mechanical translation, protocol implementation, state machines, async control flow, type definitions | `ToolCallAccumulator`, `translate_sdk_error()` (the generic mapper), session lifecycle, streaming delta handling, Provider Protocol methods |
| **YAML config**      | Policies, mappings, thresholds, classifications, capability declarations — anything that looks like a lookup table in code | Error classification table, event routing (BRIDGE/CONSUME/DROP), retry parameters, circuit breaker limits, model capabilities, observability thresholds |
| **Markdown contracts** | Specifications, behavioral requirements, architectural invariants, security boundaries — anything that defines WHAT not HOW | Provider Protocol contract, SDK boundary rules, Deny + Destroy invariants, error hierarchy semantics, streaming completion signals |

### 4.1 The Litmus Tests

**"Should this be code?"** — Ask: Does this require control flow, state management, or type-safe transformation? If removing this logic leaves the system unable to function, it's code.

**"Should this be config?"** — Ask: Could two teams want different values here? Is this a mapping, threshold, or classification? If changing this value doesn't change the algorithm, it's config.

**"Should this be a contract?"** — Ask: Is this a requirement that implementations must satisfy? Would an AI agent need to read this to understand what to build? If this defines WHAT not HOW, it's a contract.

### 4.2 Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong |
|-------------|----------------|
| Policy thresholds as Python constants | Changing `MAX_RETRIES = 3` requires code review + deploy |
| Mapping tables as `isinstance` chains | Adding a new SDK error type requires modifying an algorithm |
| Contracts as Python docstrings only | Docstrings drift from implementation; contracts should be independent artifacts |
| Config without defaults | "Leave it to the consumer" creates a policy fragmentation bomb |
| Config for control flow | `if config.use_streaming: ...` makes code untestable; streaming is mechanism, not policy |
| Markdown without tests | Unverified contracts are documentation that lies; every MUST clause needs a compliance test |

---

## 5. The Implementation Roadmap

### 5.1 From 5,200 Lines to Hybrid Architecture

The current codebase has 5,286 lines across 13 modules, with the 1,799-line `provider.py` monolith at the center. The migration follows the phased approach validated across all debate rounds, with one crucial addition: **config extraction happens alongside code extraction**.

### Phase 0: Foundation (Week 1) — "Extract and Externalize"

| Day | Deliverable | Hybrid Aspect |
|-----|-------------|---------------|
| 1 | Project scaffolding + config loader | Create `config/` directory, implement YAML config loader with schema validation, establish `contracts/` directory |
| 2 | Extract `error_translation.py` | **Simultaneously** extract error mappings to `config/errors.yaml`. The Python module becomes a generic config-driven mapper (~80 lines) instead of a hardcoded classifier (~200 lines) |
| 3 | Extract `tool_parsing.py` | Pure code extraction — tool parsing is irreducible logic, not configurable policy |
| 4 | Extract `session_factory.py` + `streaming.py` | Extract event routing to `config/events.yaml`. Streaming handler becomes config-driven event dispatcher |
| 5 | Extract `completion.py` + integration verification | Extract circuit breaker and retry params to `config/retry.yaml` and `config/circuit-breaker.yaml`. Write `contracts/deny-destroy.md` |

**Gate**: All existing tests pass. Config files load and validate. Contract files exist for all non-negotiable invariants. No module exceeds 400 lines. Python core approaches ~300 lines for new code (excluding preserved modules).

### Phase 1: Core (Week 2) — "Test the Contracts"

| Day | Deliverable | Hybrid Aspect |
|-----|-------------|---------------|
| 6-7 | 20+ SDK canary tests | Tests verify both code behavior AND config correctness — e.g., "the error mapping in `config/errors.yaml` produces the correct domain exception for each SDK error type" |
| 8 | CI pipeline | Lint + typecheck + test + **config validation** (YAML schema check) |
| 9 | Streaming metrics + architecture fitness | Add `config/observability.yaml` for metric thresholds. Fitness test validates no SDK imports outside adapter AND no hardcoded policy values outside config |
| 10 | Integration verification + contract documentation | All contracts in `contracts/` are complete. Every MUST clause has a corresponding test. `SDK_ASSUMPTIONS.md` auto-generated |

**Gate**: Config-driven modules work identically to hardcoded originals. Contract compliance tests pass. Adding a new SDK error type requires only a YAML change (validated by test).

### Phase 2: Autonomy Foundations (Weeks 3-4) — "Config-Driven Adaptation"

| Days | Deliverable | Hybrid Aspect |
|------|-------------|---------------|
| 11-12 | SDK event audit + event bridge | Audit produces actual event catalog → update `config/events.yaml` with real data (replacing speculative 58-event list) |
| 13-14 | Weekly SDK change detection | Detection job checks config mappings against SDK reality — can flag "new SDK error type not in `config/errors.yaml`" |
| 15-16 | Property-based tests | Test that config-driven mappers handle all inputs correctly for ANY valid config |
| 17-18 | Semi-automated adaptation prototype | **Key insight**: Type 1 changes (field renames) become config changes, not code changes. The adaptation script edits YAML, not Python |
| 19-20 | Adversarial validation | Test: can the system adapt to a simulated SDK error type addition by editing only `config/errors.yaml`? |

**Gate**: Adversarial validation shows >50% success rate for config-only adaptations. If <50%, fall back to code-level adaptation with human review.

### 5.2 Migration Strategy: Incremental, Not Big-Bang

The migration follows the Modular Architecture's Phase 1-6 extraction order, but each extraction has a parallel config extraction:

```
CURRENT STATE                    HYBRID TARGET
─────────────                    ─────────────
provider.py (1799 lines)    →   provider.py (~120 lines)
  ├─ error handling (scattered)  →   error_translation.py (~80 lines)
  │                                  + config/errors.yaml
  ├─ event routing (match stmt)  →   streaming.py (~100 lines)
  │                                  + config/events.yaml
  ├─ retry logic (hardcoded)     →   completion.py (~150 lines)
  │                                  + config/retry.yaml
  ├─ circuit breaker (constants) →   (in completion.py)
  │                                  + config/circuit-breaker.yaml
  └─ model capabilities (code)   →   model_cache.py (preserved)
                                     + config/models.yaml
```

Each step is independently testable. Each step preserves behavioral equivalence. Each step can be reverted independently if the config-driven version doesn't match the hardcoded original.

---

## 6. Risk Assessment

### 6.1 Migration Risks

| # | Risk | Probability | Impact | Mitigation |
|---|------|:-----------:|:------:|------------|
| **M1** | Config parsing introduces latency on startup | LOW | LOW | YAML is parsed once at module load, cached in memory. Measured overhead: <5ms for all config files combined |
| **M2** | Config schema drift from code expectations | MEDIUM | MEDIUM | JSON Schema validation on every config load. CI validates config schema on every commit |
| **M3** | Config-driven error mapping misses edge case | MEDIUM | HIGH | Property-based testing: generate random exceptions, verify config-driven mapper matches hardcoded reference implementation for ALL inputs |
| **M4** | Behavioral regression during extraction | HIGH | HIGH | Snapshot comparison on Day 5: decomposed provider must produce byte-identical responses for 5 representative requests. Stop-work criterion: revert if cause not identified within 4 hours |
| **M5** | Config files become a maintenance burden | MEDIUM | MEDIUM | Config files are smaller and simpler than the code they replace. Each config file has <50 lines. Total config: ~200 lines YAML vs ~500 lines Python it replaces |
| **M6** | Team unfamiliarity with config-driven architecture | MEDIUM | LOW | Config files are self-documenting YAML with comments referencing contract clauses. AI agents parse YAML more reliably than Python control flow |

### 6.2 Testing Strategy for the Hybrid

The Contract-Anchored Diamond is preserved, with one addition: **config compliance tests**.

```
Testing Layers (Hybrid Architecture):

TIER 1: Pure unit tests (20%)
  - Python code logic (accumulator, state machines)
  - Config loader and validator

TIER 2: Config compliance tests (NEW — 10%)
  - Every config mapping produces correct output
  - Config defaults match contract requirements
  - Config + code composition is behaviorally correct

TIER 3: Contract compliance tests (20%)
  - Every MUST clause in contracts/*.md has a test
  - Tests reference the specific contract clause they verify

TIER 4: Integration tests (15%)
  - Full flow with stubbed SDK
  - Config-driven event routing end-to-end

TIER 5: SDK assumption tests (15%)
  - Canary tests for SDK types, behavior, errors
  - Config mappings validated against real SDK

TIER 6: Property-based tests (10%)
  - Config-driven mappers handle ALL inputs
  - Invariants hold across random config variations

TIER 7: Live smoke tests (5%)
  - Real API, real tokens, real network
  - Full hybrid stack exercised

CROSS-CUTTING: Evidence capture (5%)
  - Structured proof of behavior for all tiers
```

**The key addition**: Config compliance tests verify that the YAML files produce the same behavior as the hardcoded Python they replace. During migration, both implementations run side-by-side, and tests verify they agree on every input. Once the config-driven version is validated, the hardcoded version is removed.

### 6.3 Rollback Plan

The Hybrid Architecture has three independent rollback dimensions:

**1. Code rollback**: Standard git revert. Each module extraction is an independent commit. Reverting `error_translation.py` extraction restores the inline error handling in `provider.py`.

**2. Config rollback**: Config files are versioned alongside code. Reverting `config/errors.yaml` to a previous version restores the previous error mapping policy. The code (generic mapper) doesn't change.

**3. Architecture rollback**: If the entire hybrid approach proves unworkable, the config files can be "compiled" back into hardcoded Python by replacing the config loader with static values. This is a mechanical transformation that preserves all behavior. The contracts remain as documentation even if the config-driven approach is abandoned.

**Rollback timeline**: Any single config change: <1 minute (edit YAML, restart). Any single module: <5 minutes (git revert, run tests). Full architecture rollback: <2 hours (compile configs to code, verify tests pass).

### 6.4 What Could Go Wrong (Honest Assessment)

The Skeptic's voice echoes through every section of this document. Here is what could go wrong, stated without euphemism:

1. **Config-driven mapping is slower than `isinstance` chains**. Unlikely (we're talking microseconds), but possible. Mitigation: benchmark during Phase 0. If overhead exceeds 1ms per request, optimize the config loader.

2. **YAML config files become their own maintenance burden**. If the config files grow to hundreds of lines each, we've just moved complexity from Python to YAML. Mitigation: each config file has a strict size cap (50 lines), and the config schema is validated by CI.

3. **The three-medium architecture confuses contributors**. "Where does this change go — code, config, or contract?" is a legitimate question that every contributor must answer correctly. Mitigation: the litmus tests in Section 4.1, enforced by CI (architecture fitness tests flag policy values in Python code).

4. **Contracts drift from implementation**. If `contracts/deny-destroy.md` says "MUST be installed on every session" but the code doesn't enforce it, the contract is a lie. Mitigation: every MUST clause has a corresponding test, and CI fails if a contract clause has no matching test.

5. **The adversarial validation on Day 20 shows <50% success rate**. This means the config-driven adaptation doesn't work well enough. Mitigation: per the roadmap, this gates further autonomy investment. If config-only adaptation fails, we fall back to code-level adaptation with human review — which is still better than the current monolith.

---

## 7. The Synthesis in One Paragraph

The next-generation GitHub Copilot provider is a **hybrid architecture** where Python code handles irreducible mechanical translation (~300 lines of provider core), YAML configuration declares all tunable policies (error mappings, event routing, retry thresholds, model capabilities), and markdown contracts specify the behavioral requirements that code + config must satisfy together. The Deny + Destroy pattern remains non-negotiable code. The SDK boundary membrane remains a code-level architecture. But the 23 policies identified across 31 debate documents are externalized as config with sensible defaults, making the provider simultaneously simpler (less Python to maintain), more adaptable (policy changes are data edits, not code changes), and more transparent (contracts are human-readable specifications that AI agents use as regeneration blueprints). Testing follows the Contract-Anchored Diamond with config compliance tests as a new tier, ensuring that the YAML-driven behavior matches the contracts. Migration from the current 5,200-line codebase follows the proven phased approach — extract code modules while simultaneously extracting config policies — with stop-work criteria at every gate and full rollback capability at every level.

---

## 8. Closing: The Debate's True Output

Thirty-one documents didn't produce thirty-one architectures. They produced one architecture, approached from thirty-one angles. The Code-First camp built the skeleton — module boundaries, contract tests, SDK membrane. The Config-First camp added the nervous system — externalized policies, tunable behavior, declarative specifications. The Skeptic provided the immune system — stop-work criteria, adversarial validation, honest risk assessment, accountability chains.

The Hybrid Architecture is not the average of these perspectives. It is their *product*. Code where code is needed. Config where config is earned. Contracts as the connective tissue that makes the whole system legible to both humans and machines.

The Skeptic asked the most important question in this entire debate: *"Will the machine ever actually run?"*

The answer: it runs next. With code that translates, config that adapts, and contracts that specify — in that order, each earning the right to exist by preventing a concrete failure mode. No more philosophy. Build the hybrid. Make it observable. Make it resilient.

In that order.

---

*"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away." — Antoine de Saint-Exupéry*

*Applied here: We took away the hardcoded policies (moved to config). We took away the implicit contracts (moved to markdown). What remains is the irreducible core — the code that must be code, and nothing more.*

---

**Document Control**

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-08 | Final synthesis of 31+ debate documents across 3 waves, 3 rounds, and 2 Golden Vision drafts |

*This document is the definitive architectural resolution for `next-get-provider-github-copilot`. It supersedes all previous architectural proposals by synthesizing them into a coherent hybrid that preserves the strongest contributions of each perspective while resolving their tensions.*
