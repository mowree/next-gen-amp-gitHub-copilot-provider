# DEBATE ROUND 1: Linux Kernel Philosophy Analysis

## The Mechanisms vs. Policies Separation Principle Applied to the Copilot Provider

**Agent**: Linux Kernel Philosophy Expert
**Date**: 2026-03-08
**Source Code Analyzed**: `amplifier-module-provider-github-copilot` v1.0.2
**Primary File**: `provider.py` (1799 lines), `sdk_driver.py` (620 lines), `_constants.py` (312 lines)

---

## 1. MECHANISM VS. POLICY AUDIT

The Linux kernel's most profound architectural insight is the separation of **mechanisms** (how to do something) from **policies** (what to do). The kernel provides mechanisms; userspace decides policy. Let me systematically audit every policy embedded in this provider.

### 1.1 Embedded Policy Catalog

| # | Policy | Location | Current Value | Should Be |
|---|--------|----------|---------------|-----------|
| P1 | Retry count | `provider.py:322` | `max_retries=3` | Amplifier config |
| P2 | Retry initial delay | `provider.py:323` | `1.0s` | Amplifier config |
| P3 | Retry max delay | `provider.py:324` | `60.0s` | Amplifier config |
| P4 | Retry jitter | `provider.py:325` | `True` | Amplifier config |
| P5 | Default timeout | `_constants.py:46` | `3600s` | Amplifier config |
| P6 | Thinking timeout | `_constants.py:47` | `3600s` | Amplifier config |
| P7 | Fake tool call detection | `provider.py:122-129` | Regex pattern | Amplifier middleware |
| P8 | Fake tool call max retries | `provider.py:129` | `2` | Amplifier config |
| P9 | SDK max turns | `_constants.py:228` | `3` | Amplifier config |
| P10 | SDK hard turn limit | `_constants.py:229` | `10` | Provider mechanism (safety) |
| P11 | First-turn-only capture | `_constants.py:233` | `True` | Amplifier config |
| P12 | Tool deduplication | `_constants.py:237` | `True` | Amplifier config |
| P13 | Default model | `_constants.py:39` | `claude-opus-4.5` | Amplifier config |
| P14 | Rate-limit fail-fast threshold | `provider.py:988` | `> max_delay` | Amplifier config |
| P15 | Streaming default | `provider.py:306` | `True` | Amplifier config |
| P16 | Max repaired tool IDs | `_constants.py:74` | `1000` | Provider mechanism (bounded) |
| P17 | Cache staleness threshold | `_constants.py:71` | `30 days` | Amplifier config |
| P18 | Client health check timeout | `_constants.py:86` | `5.0s` | Provider mechanism |
| P19 | Client init lock timeout | `_constants.py:93` | `30.0s` | Provider mechanism |
| P20 | Built-in tool exclusion list | `_constants.py:127-171` | 28 tools | Provider mechanism |
| P21 | Tool sorting strategy | `provider.py:856` | Alphabetical | Amplifier config |
| P22 | Correction message text | `provider.py:1113-1121` | Hardcoded English | Amplifier config/i18n |
| P23 | Synthetic error result text | `provider.py:1734-1740` | Hardcoded English | Amplifier config |

### 1.2 Classification: What Is Mechanism, What Is Policy?

**TRUE MECHANISMS** (correctly in the provider):

```
MECHANISM                           WHY IT BELONGS HERE
─────────────────────────────────   ──────────────────────────────────
Session create/destroy lifecycle    SDK-specific transport
Event subscription/routing          SDK event API binding
Message format conversion           SDK protocol translation
Tool request capture from events    SDK event structure parsing
Error type translation              SDK → Kernel error mapping
Built-in tool exclusion list        SDK binary knowledge (P20)
Health check mechanism              Subprocess liveness detection (P18)
LRU bound on repaired IDs          Memory safety mechanism (P16)
Hard turn limit                     Safety valve, not policy (P10)
```

**POLICIES MASQUERADING AS MECHANISMS** (must be extracted):

```
POLICY                              WHY IT DOESN'T BELONG HERE
─────────────────────────────────   ──────────────────────────────────
Retry configuration (P1-P4)         Different teams want different retry behavior
Timeout values (P5-P6)              Depends on deployment context
Fake tool call detection (P7-P8)    LLM behavior correction is orchestrator concern
SDK turn limits (P9)                Tunable per-model, per-use-case
Capture strategy (P11-P12)          Could change with SDK version
Default model (P13)                 Organizational preference
Rate-limit fail-fast (P14)          Depends on billing/cost tolerance
Streaming default (P15)             UI/integration preference
Tool sorting (P21)                  Presentation policy
Correction messages (P22-P23)       Content/i18n policy
```

### 1.3 The Kernel Analogy

In Linux, the scheduler provides mechanisms (priority queues, time slices, preemption). The **scheduling policy** (CFS, FIFO, Round-Robin) is selectable at runtime. Similarly:

```
┌─────────────────────────────────────────────────────┐
│                   AMPLIFIER (Userspace)              │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Retry Policy │  │ Timeout Pol. │  │ LLM Behav.│  │
│  │ max=3, j=T   │  │ t=3600,tt=3600│ │ fake_tc=2 │  │
│  └──────┬──────┘  └──────┬───────┘  └─────┬─────┘  │
│         │                │                 │        │
├─────────┼────────────────┼─────────────────┼────────┤
│         ▼                ▼                 ▼        │
│  ┌─────────────────────────────────────────────────┐│
│  │              PROVIDER (Kernel Space)             ││
│  │                                                  ││
│  │  retry_mechanism()  timeout_mechanism()           ││
│  │  session_lifecycle() event_routing()              ││
│  │  error_translation() format_conversion()          ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

---

## 2. KERNEL DESIGN PATTERNS

### 2.1 The Device Driver Boundary Problem

Linux's device driver model is the closest analogy to our SDK boundary problem. Consider:

```
LINUX                           AMPLIFIER
─────────────                   ────────────────
VFS layer                  →    Amplifier Core (ChatRequest/ChatResponse)
Device driver interface    →    Provider Protocol (5 methods)
Specific driver (ext4)     →    CopilotSdkProvider
Hardware device            →    Copilot CLI SDK subprocess
```

The Linux kernel defines a **struct file_operations** — a vtable of function pointers that every filesystem driver must implement. The VFS layer never knows or cares about the specific filesystem. Similarly, Amplifier defines the Provider Protocol (name, get_info, list_models, complete, parse_tool_calls).

**But here's where the analogy breaks down — and teaches us something.**

Linux device drivers do NOT embed scheduling policies. The ext4 driver doesn't decide "retry this I/O 3 times with exponential backoff." That's the block layer's job. Yet our provider embeds retry logic at `provider.py:321-326` and executes it at `provider.py:1073`:

```python
# provider.py:321-326 — POLICY embedded in MECHANISM
self._retry_config = RetryConfig(
    max_retries=int(config.get("max_retries", 3)),
    initial_delay=float(config.get("retry_min_delay", 1.0)),
    max_delay=float(config.get("retry_max_delay", 60.0)),
    jitter=bool(config.get("retry_jitter", True)),
)
```

In kernel terms, this is like a disk driver deciding its own I/O scheduling — a violation of layering. The retry mechanism should be in the provider (how to retry), but the retry **policy** (when, how many, how long) should come from Amplifier.

### 2.2 The VFS Abstraction Lesson

Linux VFS teaches us about **operation dispatch tables**. Every filesystem registers callbacks:

```c
// Linux VFS pattern
struct file_operations ext4_fops = {
    .read     = ext4_read,
    .write    = ext4_write,
    .open     = ext4_open,
    .release  = ext4_release,
    .ioctl    = ext4_ioctl,    // Extension point!
};
```

The critical insight is `ioctl` — an **escape hatch** for operations that don't fit the standard interface. Our provider has a similar need. The current 5-method protocol is clean, but there are SDK-specific capabilities (6 hooks, session resume, 58 event types) that don't map to the standard interface.

**Proposal: Provider-Specific Extension Points**

```python
# Analogous to ioctl — provider-specific operations
class ProviderExtensions:
    """Optional extension interface for SDK-specific capabilities."""
    
    def get_hooks(self) -> dict[str, HookCallback]:
        """Return available SDK hooks (like preToolUse, postToolUse)."""
        return {}
    
    def get_event_types(self) -> list[str]:
        """Return subscribable event types."""
        return []
    
    def subscribe_events(self, handler: EventHandler) -> Unsubscribe:
        """Subscribe to provider-specific events."""
        raise NotImplementedError
```

### 2.3 The Netfilter/iptables Pattern

The most directly applicable kernel pattern is **netfilter hooks**. Netfilter defines hook points in the network stack where modules can register callbacks:

```
PREROUTING → INPUT → FORWARD → OUTPUT → POSTROUTING
     ↑          ↑        ↑         ↑          ↑
   hooks      hooks    hooks     hooks      hooks
```

The Copilot SDK has 6 hooks, and we only use `preToolUse` (deny). This is like having netfilter but only using DROP on INPUT. The provider should **expose** all 6 hooks as a mechanism, and let Amplifier's configuration decide which to use and how:

```
SDK HOOKS (mechanism)          CURRENT USE        POTENTIAL POLICIES
────────────────────           ───────────        ──────────────────
preToolUse                     deny all           selective deny, audit, transform
postToolUse                    unused             result validation, logging
onErrorOccurred                unused             error delegation, recovery
preSessionCreate               unused             session configuration injection
postSessionCreate              unused             session monitoring setup
onSessionDestroy               unused             cleanup, metrics collection
```

### 2.4 The Module Parameter Pattern

Linux kernel modules accept parameters at load time:

```bash
modprobe ext4 max_batch_time=15000 min_batch_time=0
```

The provider partially implements this via `config` dict, but the current design mixes module parameters (mechanism configuration) with policy settings. A clean separation:

```python
# MECHANISM parameters (provider-internal, SDK-specific)
mechanism_params = {
    "cli_path": "/usr/local/bin/copilot",      # SDK binary location
    "health_check_timeout": 5.0,                # Subprocess health
    "client_init_lock_timeout": 30.0,           # Concurrency safety
    "sdk_timeout_buffer": 5.0,                  # Race condition prevention
}

# POLICY parameters (should come from Amplifier config)
policy_params = {
    "max_retries": 3,
    "retry_delay": 1.0,
    "timeout": 3600,
    "thinking_timeout": 3600,
    "fake_tool_call_retries": 2,
    "sdk_max_turns": 3,
    "capture_strategy": "first_turn_only",
    "default_model": "claude-opus-4.5",
    "streaming": True,
}
```

---

## 3. THE LITMUS TEST: "Could Two Teams Want Different Behavior?"

This is the canonical test for mechanism vs. policy separation, from the seminal Saltzer & Schroeder paper (1975). Let me apply it rigorously.

### 3.1 Retry Configuration (P1-P4)

**Test**: Could two teams want different retry behavior?

**ABSOLUTELY YES.**

- **Team A** (interactive CLI tool): Wants 1 retry with 0.5s delay. Users see latency directly.
- **Team B** (background batch processor): Wants 5 retries with 30s max delay. Reliability over latency.
- **Team C** (cost-sensitive deployment): Wants 0 retries. Every retry burns tokens.

**Verdict**: POLICY. Must be externalized.

**Current state** (`provider.py:321-326`): Partially externalized via config dict, but defaults are hardcoded. The `RetryConfig` construction should accept a policy object from Amplifier, not build one internally.

### 3.2 Timeout Selection (P5-P6)

**Test**: Could two teams want different timeouts?

**YES.**

- **Interactive pair programming**: 60s timeout. User is waiting.
- **Autonomous agent task**: 3600s timeout. Agent works unattended.
- **CI/CD pipeline**: 120s timeout. Pipeline has SLAs.

**Verdict**: POLICY.

**Current state** (`provider.py:815-832`): Complex timeout selection logic embeds the POLICY of when to use which timeout. The mechanism should be "apply timeout T to request." The policy of WHICH timeout should come from Amplifier based on context.

### 3.3 Fake Tool Call Detection (P7-P8)

**Test**: Could two teams want different fake tool call behavior?

**YES, and this is the most contentious one.**

- **Team A**: Wants aggressive detection and re-prompting. Values correct tool usage.
- **Team B**: Wants to pass through and let the orchestrator handle it. The LLM's text output might be useful even if it contains fake tool patterns.
- **Team C**: Wants to log but not retry. Monitoring-first approach.

**Verdict**: POLICY. The detection mechanism (regex, code-block awareness) can live in the provider or a shared library. But the DECISION of what to do (retry, pass-through, log) is policy.

**Current state** (`provider.py:1084-1138`): 55 lines of policy-laden code embedded directly in the `complete()` method. This is the equivalent of a network driver deciding to resend packets — that's TCP's job, not the NIC driver's.

### 3.4 SDK Loop Control (P9-P12)

**Test**: Could two teams want different loop behavior?

**YES.**

- **Conservative team**: max_turns=2, first_turn_only=True. Minimize SDK interaction.
- **Experimental team**: max_turns=5, all_turns=True. Exploring SDK capabilities.
- **Performance team**: max_turns=1, no dedup. Absolute minimum overhead.

**Verdict**: POLICY for the tuning knobs. MECHANISM for the circuit breaker hard limit (`_constants.py:229`, `SDK_MAX_TURNS_HARD_LIMIT=10`). The hard limit is like the kernel's OOM killer — a safety mechanism, not a policy choice.

### 3.5 Built-in Tool Exclusion (P20)

**Test**: Could two teams want different built-in tool exclusion?

**PARTIALLY.**

The exclusion list (`_constants.py:127-171`) is derived from **empirical forensic analysis** of the SDK binary. This is domain knowledge about the SDK's internals — mechanism, not policy. You can't "want" a different list because the list is what the SDK contains.

However, the STRATEGY of "exclude all when user tools present" (`provider.py:877`) vs. "exclude only overlapping" is a policy choice.

**Verdict**: List is MECHANISM (SDK knowledge). Strategy is POLICY.

### 3.6 Streaming Default (P15)

**Test**: Could two teams want different streaming defaults?

**YES.**

- **Terminal UI**: Streaming for real-time display.
- **API server**: Non-streaming for simpler response handling.
- **Testing**: Non-streaming for deterministic assertions.

**Verdict**: POLICY. Currently at `provider.py:306` with a hardcoded default of `True`.

### 3.7 Summary Matrix

```
ASPECT               LITMUS     VERDICT      CONFIDENCE
─────────────────    ────────   ──────────   ──────────
Retry config         2+ teams   POLICY       HIGH
Timeout values       2+ teams   POLICY       HIGH
Fake TC detection    2+ teams   POLICY       HIGH
SDK turn limits      2+ teams   POLICY       HIGH
Capture strategy     2+ teams   POLICY       MEDIUM
Built-in tool list   SDK fact   MECHANISM    HIGH
Exclusion strategy   2+ teams   POLICY       MEDIUM
Streaming default    2+ teams   POLICY       HIGH
Default model        2+ teams   POLICY       HIGH
Error translation    SDK fact   MECHANISM    HIGH
Session lifecycle    SDK fact   MECHANISM    HIGH
Format conversion    SDK fact   MECHANISM    HIGH
Health check TO      SDK impl   MECHANISM    HIGH
Hard turn limit      Safety     MECHANISM    HIGH
```

---

## 4. INTERFACE CONTRACTS

### 4.1 The Provider Contract (Mechanism Layer)

```
┌─────────────────────────────────────────────────────────────┐
│                    PROVIDER CONTRACT                         │
│                                                             │
│  INPUTS (from Amplifier):                                    │
│  ├── ChatRequest (messages, tools, config)                   │
│  ├── PolicyBundle:                                           │
│  │   ├── retry: RetryPolicy                                 │
│  │   ├── timeout: TimeoutPolicy                              │
│  │   ├── behavior: BehaviorPolicy                            │
│  │   └── sdk: SdkTuningPolicy                               │
│  └── Coordinator (hooks, events)                             │
│                                                             │
│  OUTPUTS (to Amplifier):                                     │
│  ├── ChatResponse (content, tool_calls, usage)               │
│  ├── Events (llm:request, llm:response, provider:*)         │
│  └── Errors (typed, with retryable flag)                     │
│                                                             │
│  GUARANTEES:                                                 │
│  ├── Session isolation (ephemeral, no state leakage)         │
│  ├── Error classification (typed errors with context)        │
│  ├── Event emission (before/after API calls)                 │
│  └── Resource cleanup (close() releases everything)          │
│                                                             │
│  NON-GUARANTEES (policy-dependent):                          │
│  ├── Number of retries (depends on RetryPolicy)              │
│  ├── Timeout duration (depends on TimeoutPolicy)             │
│  ├── Fake tool call handling (depends on BehaviorPolicy)     │
│  └── SDK loop behavior (depends on SdkTuningPolicy)         │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Policy Types

```python
@dataclass(frozen=True)
class RetryPolicy:
    """Retry behavior for LLM calls. Provided by Amplifier."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True

@dataclass(frozen=True)
class TimeoutPolicy:
    """Timeout behavior. Provided by Amplifier."""
    default_timeout: float = 3600.0
    thinking_timeout: float = 3600.0
    # Amplifier decides which to use based on context

@dataclass(frozen=True)
class BehaviorPolicy:
    """LLM behavior correction policies. Provided by Amplifier."""
    detect_fake_tool_calls: bool = True
    fake_tool_call_max_retries: int = 2
    repair_missing_tool_results: bool = True

@dataclass(frozen=True)
class SdkTuningPolicy:
    """SDK-specific tuning. Provided by Amplifier."""
    max_turns: int = 3
    capture_first_turn_only: bool = True
    deduplicate_tools: bool = True
    builtin_exclusion_strategy: str = "all"  # "all", "overlapping", "none"
```

### 4.3 What MUST Be Mechanism

These are non-negotiable mechanism responsibilities of the provider:

1. **SDK session lifecycle**: Create, use, destroy. No Amplifier code should know about `session.send()` or `session.abort()`.

2. **Event routing**: Subscribing to SDK events and translating them. The `SdkEventHandler.on_event()` method at `sdk_driver.py:406` is pure mechanism.

3. **Error translation**: The 12-case error mapping at `provider.py:976-1049` translates SDK-specific errors to kernel error types. This is like a device driver translating hardware error codes to `errno` values.

4. **Format conversion**: `converters.py` is entirely mechanism — protocol translation between two data formats.

5. **Built-in tool knowledge**: The `COPILOT_BUILTIN_TOOL_NAMES` set at `_constants.py:127-171` is empirical SDK knowledge. This is like a driver knowing its device's register map.

6. **Safety valves**: `SDK_MAX_TURNS_HARD_LIMIT=10` at `_constants.py:229` is a safety mechanism, like the kernel's OOM killer. It exists to prevent catastrophic failure, not to implement user preference.

### 4.4 What MUST Be Policy

These MUST come from Amplifier configuration, not provider code:

1. **Retry behavior**: How many times, how long to wait, whether to jitter.
2. **Timeout selection**: Which timeout to apply and when.
3. **LLM behavior correction**: Whether to detect/retry fake tool calls.
4. **Default model selection**: Which model when none specified.
5. **Streaming preference**: Default streaming behavior.
6. **SDK tuning parameters**: Turn limits, capture strategy.

---

## 5. EVIDENCE FROM THE WILD

### 5.1 Academic Foundation

**Saltzer, J.H. and Schroeder, M.D. (1975).** "The Protection of Information in Computer Systems." _Proceedings of the IEEE, 63(9)_, pp. 1278-1308.

> "Separation of policy from mechanism... The separation of mechanism from policy has been identified as an important principle in the design of large systems."

This paper established the principle that our provider violates in at least 15 places.

**Lampson, B.W. (1983).** "Hints for Computer System Design." _ACM Operating Systems Review, 17(5)_.

> "Do one thing at a time, and do it well. An interface should capture the minimum essentials of an abstraction. Don't generalize; generalizations are generally wrong."

The current provider tries to do too many things: transport, retry, behavior correction, SDK loop control, format conversion, event emission. Each should be a separate mechanism module.

### 5.2 Linux Kernel Evidence

**Linux I/O Scheduler Evolution** (kernel.org documentation):

The Linux block layer went through multiple scheduler policies (noop, deadline, cfq, bfq, mq-deadline, kyber) without changing the block device driver interface. Drivers provide mechanisms (submit I/O, handle completion). Schedulers provide policy (ordering, fairness, latency).

Our provider should similarly support policy changes without provider code changes.

**Linux Netfilter** (nf_register_net_hook):

Netfilter's hook system allows policy modules to register at well-defined points. The network stack provides the hooks (mechanism). iptables/nftables provide the rules (policy). Our provider should expose SDK hooks as mechanism points, with Amplifier providing the hook policies.

### 5.3 Industry Examples

**gRPC Interceptors**: gRPC separates transport mechanism from policy through interceptors. Retry policy, timeout policy, and authentication are all interceptors, not embedded in the transport.

**Kubernetes Controllers**: The controller pattern separates the reconciliation mechanism from the desired-state policy. Controllers don't decide what state to achieve; they receive desired state and make it happen.

**Envoy Proxy**: Envoy explicitly separates mechanism (proxying, connection pooling, health checking) from policy (retry budgets, circuit breaking thresholds, timeout values), configured via xDS protocol.

---

## 6. CONTROVERSIAL TAKE: THE RADICAL POSITION

### 6.1 What Would a Radical Application Look Like?

If we applied kernel philosophy with absolute purity, the provider would be reduced to approximately **400 lines of code**. Here's why:

**The Radical Provider**:

```python
class CopilotSdkProvider:
    """Pure mechanism. Zero policy."""
    
    def __init__(self, config, coordinator, policies):
        self._client = CopilotClientWrapper(config)
        self._policies = policies  # ALL policy comes from outside
    
    @property
    def name(self) -> str:
        return "github-copilot"
    
    def get_info(self) -> ProviderInfo: ...      # ~20 lines
    async def list_models(self) -> list: ...      # ~20 lines
    async def complete(self, request) -> ChatResponse:
        """Pure transport. No retry. No fake TC detection. No timeout selection."""
        session = await self._client.create_session(...)
        response = await session.send(request)
        return self._convert(response)
    def parse_tool_calls(self, r) -> list: ...    # ~3 lines
```

In this radical design:
- **Retry** is handled by Amplifier's middleware layer wrapping the `complete()` call
- **Timeout** is set by Amplifier before calling `complete()`
- **Fake tool call detection** is an Amplifier post-processor
- **SDK loop control** is handled by the event handler, configured by policy
- **Error translation** is the only "smart" thing the provider does

### 6.2 Why This Is Too Radical (And What It Teaches Us)

The pure kernel approach fails here for one critical reason: **the SDK is an agentic runtime, not a passive device.**

A disk drive doesn't have opinions. It doesn't retry on its own. It doesn't run an internal agent loop that can spiral into 305 turns. The Copilot SDK is fundamentally different from a hardware device — it has its own agency.

This means the provider needs **MORE mechanism** than a typical device driver, not less. The SDK Driver (`sdk_driver.py`) is mechanism for controlling another agent — like a hypervisor controlling a guest OS. The hypervisor doesn't set guest policy, but it DOES enforce containment.

**The Teaching**: The radical position shows us that:

1. **Retry should absolutely be external.** There's no SDK-specific reason for retry to be in the provider. Amplifier's middleware can wrap any provider.

2. **Fake tool call detection should absolutely be external.** It's LLM behavior correction, not SDK transport. It works identically for any provider.

3. **SDK loop control MUST stay internal.** It's containment of the SDK's internal agent, which is SDK-specific mechanism.

4. **Timeout selection could go either way.** The mechanism of "apply timeout" stays. The policy of "which timeout" could move to Amplifier if Amplifier understands model capabilities.

### 6.3 The Heretical Question

Here's the truly provocative question: **Should the provider even OWN the retry loop?**

Look at `provider.py:1073`:
```python
response = await retry_with_backoff(_do_complete, self._retry_config, on_retry=_on_retry)
```

In kernel terms, this is like a filesystem driver implementing its own I/O retry loop instead of letting the block layer handle it. The block layer has better information (queue depth, other pending I/O, device health) to make retry decisions.

Similarly, Amplifier has better information than the provider:
- How many providers are available (failover vs. retry)
- What the user's latency budget is
- Whether this is an interactive or batch request
- Token cost implications of retrying

**My heretical recommendation**: Remove retry from the provider entirely. Let `complete()` be a single-shot operation. Let Amplifier decide whether to retry, failover, or abort.

### 6.4 The 60/30/10 Split

If I had to quantify the ideal split:

```
PROVIDER CODE (mechanism):        ~60% — SDK transport, conversion, containment
AMPLIFIER CONFIG (policy):        ~30% — Retry, timeout, behavior, tuning
SHARED LIBRARY (reusable):        ~10% — Error types, format utilities, logging
```

Currently it's more like:

```
PROVIDER CODE (mechanism+policy): ~85% — Everything embedded
AMPLIFIER CONFIG (policy):        ~10% — Only what's in config dict
SHARED LIBRARY (reusable):        ~5%  — amplifier_core types
```

---

## 7. CONCRETE RECOMMENDATIONS

### 7.1 Immediate (Next Version)

1. **Extract retry to Amplifier middleware.** Remove `retry_with_backoff` from provider. Let Amplifier wrap `complete()` with retry policy.

2. **Extract fake tool call detection to Amplifier post-processor.** The 55 lines at `provider.py:1084-1138` should be an Amplifier middleware that runs after ANY provider's `complete()`.

3. **Make all policy values configurable via Amplifier config.** No hardcoded policy defaults in `_constants.py`.

### 7.2 Medium Term

4. **Expose SDK hooks as mechanism.** Define a `ProviderHooks` interface that Amplifier can populate with policy callbacks.

5. **Extract timeout selection to Amplifier.** Provider accepts a single `timeout` parameter. Amplifier decides which value based on model, context, and user preference.

6. **Create a `PolicyBundle` type.** Single object containing all policy configuration, passed from Amplifier to provider at construction.

### 7.3 Long Term

7. **Provider as pure transport layer.** The provider does ONLY: session lifecycle, format conversion, event routing, error translation, SDK containment. Everything else is Amplifier middleware.

8. **Middleware chain architecture.** Like Linux netfilter hooks:
```
Request → [RetryMiddleware] → [TimeoutMiddleware] → [BehaviorMiddleware] → Provider → Response
```

---

## 8. CLOSING ARGUMENT

The current provider is a **monolithic device driver** — imagine if the Linux ext4 driver contained TCP retry logic, process scheduling, and memory management policy. That's roughly what we have.

The path forward is clear from 50+ years of systems design: mechanisms in the provider, policies in Amplifier. The provider should be the thinnest possible translation layer between Amplifier's world (ChatRequest/ChatResponse) and the SDK's world (sessions, events, tool requests).

Every line of policy code in the provider is a line that:
- Cannot be changed without modifying the provider
- Cannot be reused across providers
- Cannot be tested in isolation from the SDK
- Cannot be configured per-deployment

The Linux kernel succeeded not because it's the most feature-rich kernel, but because it provides the right mechanisms and lets userspace set the right policies. Our next-generation provider should follow the same path.

---

*"UNIX was not designed to stop its users from doing stupid things, as that would also stop them from doing clever things." — Doug Gwyn*

*Applied to our context: The provider should not prevent Amplifier from making policy decisions, as that would also prevent it from making good ones.*
