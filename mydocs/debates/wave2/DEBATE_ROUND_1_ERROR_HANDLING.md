# Error Handling Architecture for AI-Maintained GitHub Copilot Provider

**Wave 2, Agent 15 — Error Handling Philosophy Expert**
**Date**: 2026-03-08

---

## Executive Summary

Error handling in an AI-maintained system must serve two masters: the runtime (which needs to recover gracefully) and the AI maintainer (which needs structured, machine-readable information to diagnose and fix issues). The current provider mixes concerns — retry logic embedded as behavior rather than policy, rate limit detection via brittle string matching, and an error hierarchy that conflates SDK internals with domain semantics. This document defines a complete error handling architecture built on three principles: **classify precisely**, **preserve everything**, and **fail intelligently**.

---

## 1. Error Taxonomy

### 1.1 Classification Dimensions

Every error in the system is classified along four independent dimensions:

| Dimension | Values | Purpose |
|-----------|--------|---------|
| **Origin** | `sdk`, `network`, `provider`, `kernel`, `configuration` | Where the error originated |
| **Severity** | `transient`, `degraded`, `fatal` | How bad is it |
| **Recoverability** | `retryable`, `retryable_with_backoff`, `non_retryable` | Can we try again |
| **Audience** | `internal`, `user_facing`, `telemetry_only` | Who needs to see this |

### 1.2 Complete Error Classification

```
ProviderError (abstract base)
├── NetworkError
│   ├── ConnectionTimeoutError        [transient, retryable, internal]
│   ├── ConnectionRefusedError        [transient, retryable, internal]
│   ├── DNSResolutionError            [degraded, retryable_with_backoff, internal]
│   └── TLSError                      [fatal, non_retryable, user_facing]
│
├── AuthenticationError
│   ├── TokenExpiredError             [transient, retryable, internal]
│   ├── TokenInvalidError             [fatal, non_retryable, user_facing]
│   ├── TokenRefreshFailedError       [degraded, retryable_with_backoff, user_facing]
│   └── InsufficientScopeError        [fatal, non_retryable, user_facing]
│
├── RateLimitError
│   ├── ModelRateLimitError           [transient, retryable_with_backoff, internal]
│   ├── AccountRateLimitError         [degraded, retryable_with_backoff, user_facing]
│   └── GlobalRateLimitError          [degraded, retryable_with_backoff, telemetry_only]
│
├── ModelError
│   ├── ModelNotFoundError            [fatal, non_retryable, user_facing]
│   ├── ModelOverloadedError          [transient, retryable_with_backoff, internal]
│   ├── ContextLengthExceededError    [fatal, non_retryable, user_facing]
│   ├── ContentFilterError            [fatal, non_retryable, user_facing]
│   └── ModelResponseMalformedError   [transient, retryable, internal]
│
├── StreamError
│   ├── StreamInterruptedError        [transient, retryable, internal]
│   ├── StreamParseError              [transient, retryable, internal]
│   └── StreamTimeoutError            [transient, retryable, internal]
│
├── ConfigurationError
│   ├── InvalidEndpointError          [fatal, non_retryable, user_facing]
│   ├── MissingConfigurationError     [fatal, non_retryable, user_facing]
│   └── InvalidModelMappingError      [fatal, non_retryable, user_facing]
│
└── InternalError
    ├── TranslationError              [fatal, non_retryable, telemetry_only]
    ├── StateCorruptionError          [fatal, non_retryable, telemetry_only]
    └── UnexpectedSDKError            [transient, retryable, telemetry_only]
```

### 1.3 Retryable vs Non-Retryable Decision Matrix

The retryability classification is **not** a property of the error class alone — it depends on context:

| Error | 1st occurrence | 2nd occurrence | 3rd+ occurrence |
|-------|---------------|----------------|-----------------|
| ConnectionTimeout | retry immediately | retry with backoff | escalate to degraded |
| ModelOverloaded | retry with backoff | retry with longer backoff | fail with user message |
| TokenExpired | refresh + retry | fail if refresh fails | — |
| StreamInterrupted | retry from last checkpoint | retry full request | fail |
| RateLimit | wait for `retry-after` | wait with jitter | fail with cooldown info |

**Critical rule**: Retry logic is **policy**, not behavior. The error carries its classification; a separate retry policy layer decides what to do. The provider itself never retries — it reports, and the kernel's policy layer acts.

### 1.4 User-Facing vs Internal Error Contract

```python
@dataclass
class UserFacingError:
    """What the user/kernel sees."""
    code: str                    # e.g., "RATE_LIMIT_EXCEEDED"
    message: str                 # Human-readable, no internals leaked
    retryable: bool
    retry_after_seconds: float | None
    suggested_action: str | None # e.g., "Try a different model"

@dataclass
class InternalError:
    """What telemetry and AI maintainers see."""
    code: str
    message: str
    origin: ErrorOrigin
    severity: ErrorSeverity
    sdk_error_type: str | None
    sdk_error_message: str | None
    sdk_status_code: int | None
    request_context: RequestContext
    stack_trace: str | None
    timestamp: datetime
    correlation_id: str
```

---

## 2. SDK Error Translation

### 2.1 Translation Architecture

The current provider detects rate limits via string matching (`"rate limit" in str(error).lower()`). This is fragile. The translation layer must be **structural**, not textual.

```
SDK Exception → Classifier → ProviderError → Kernel Error
                    ↓
              ErrorContext (preserved original)
```

### 2.2 Translation Rules

Every SDK error maps through a deterministic translation table. The table is the **single source of truth** for error mapping:

```python
TRANSLATION_TABLE: dict[type[Exception], type[ProviderError]] = {
    # HTTP-level errors (from SDK or raw requests)
    httpx.ConnectTimeout:       ConnectionTimeoutError,
    httpx.ReadTimeout:          StreamTimeoutError,
    httpx.ConnectError:         ConnectionRefusedError,

    # OpenAI SDK errors (Copilot SDK wraps these)
    openai.AuthenticationError: TokenInvalidError,
    openai.RateLimitError:      ModelRateLimitError,
    openai.APIStatusError:      _classify_by_status_code,  # dispatcher
    openai.APIConnectionError:  ConnectionRefusedError,

    # Copilot-specific SDK errors
    CopilotAuthError:           TokenExpiredError,
    CopilotModelError:          ModelNotFoundError,
}

STATUS_CODE_TABLE: dict[int, type[ProviderError]] = {
    401: TokenInvalidError,
    403: InsufficientScopeError,
    404: ModelNotFoundError,
    429: ModelRateLimitError,
    500: UnexpectedSDKError,
    502: ConnectionRefusedError,
    503: ModelOverloadedError,
}
```

### 2.3 Information Preservation

**Zero information loss** is the rule. Every translated error carries the original:

```python
@dataclass
class ErrorContext:
    """Immutable record of the original error."""
    original_exception: Exception
    original_type: str              # fully qualified class name
    original_message: str
    original_status_code: int | None
    original_headers: dict[str, str]  # includes retry-after, x-ratelimit-*
    original_body: str | None       # response body if available
    translation_rule: str           # which rule matched
    translated_at: datetime
```

### 2.4 Error Context Enrichment

Every error is enriched with request context at the point of creation:

```python
@dataclass
class RequestContext:
    """What was happening when the error occurred."""
    correlation_id: str
    model_requested: str
    model_resolved: str | None
    endpoint: str
    method: str                     # "chat.completions", "embeddings"
    stream: bool
    token_estimate: int | None      # estimated input tokens
    elapsed_ms: float
    attempt_number: int             # which retry attempt (1-based)
    timestamp: datetime
```

### 2.5 Fallback Translation

When an SDK error doesn't match any known pattern:

1. Wrap in `UnexpectedSDKError` (preserves full original)
2. Log at WARNING level with full context
3. Classify as `transient, retryable` (optimistic default)
4. Emit a `new_error_pattern` telemetry event for AI analysis

This ensures the system never crashes on unknown errors while surfacing new patterns for the AI maintainer to classify.

---

## 3. Error Observability

### 3.1 Error Events

Every error emits a structured event. Events are the **primary diagnostic tool** for AI maintainers:

```python
@dataclass
class ErrorEvent:
    event_type: str              # "provider.error"
    error_code: str              # "MODEL_RATE_LIMIT"
    error_origin: ErrorOrigin
    error_severity: ErrorSeverity
    retryable: bool
    correlation_id: str
    request_context: RequestContext
    error_context: ErrorContext
    recovery_action: str | None  # "retry", "backoff", "fail", "degrade"
    recovery_result: str | None  # "succeeded", "failed", "pending"
    timestamp: datetime
```

### 3.2 Error Metrics

Counters and gauges for real-time health monitoring:

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `provider_errors_total` | counter | `code`, `origin`, `severity` | Error rate |
| `provider_errors_retried` | counter | `code`, `result` | Retry effectiveness |
| `provider_error_recovery_time_ms` | histogram | `code` | Recovery speed |
| `provider_rate_limit_remaining` | gauge | `model` | Capacity headroom |
| `provider_rate_limit_reset_seconds` | gauge | `model` | Time to capacity |
| `provider_unknown_errors_total` | counter | `sdk_error_type` | New error detection |

### 3.3 Error Correlation

Every request gets a `correlation_id` at entry. All errors, retries, and recovery attempts share this ID. This enables:

- **Request tracing**: Follow a single request through retries and fallbacks
- **Error chains**: See cascading failures (timeout → retry → rate limit → fail)
- **Session correlation**: Group errors by user session for pattern detection

```python
# Correlation chain example:
# correlation_id: "req_abc123"
#   attempt 1: ConnectionTimeoutError → retry
#   attempt 2: ModelRateLimitError → backoff 2s
#   attempt 3: Success (elapsed 4.2s)
```

### 3.4 Root Cause Analysis Support

Errors carry a `causal_chain` when one error leads to another:

```python
@dataclass
class CausalChain:
    root_error: ErrorEvent
    subsequent_errors: list[ErrorEvent]
    final_outcome: str  # "recovered", "failed", "degraded"
    total_elapsed_ms: float
```

This is critical for AI maintainers. When the AI sees `ModelRateLimitError`, the causal chain tells it whether this is a standalone issue or a symptom of a deeper problem (e.g., token refresh failures causing retries that burn through rate limits).

---

## 4. Recovery Strategies

### 4.1 Recovery Decision Tree

```
Error occurs
├── Is it retryable?
│   ├── YES: Has retry budget remaining?
│   │   ├── YES: Execute retry policy
│   │   │   ├── Immediate retry (transient network errors)
│   │   │   ├── Backoff retry (rate limits, overload)
│   │   │   └── Refresh + retry (expired tokens)
│   │   └── NO: Escalate to degraded/fail
│   └── NO: Is graceful degradation possible?
│       ├── YES: Degrade (e.g., fall back to smaller model)
│       └── NO: Fail with clear user-facing error
└── Always: Emit error event
```

### 4.2 Recovery Mechanisms

**Retry Budget**: Each request gets a finite retry budget, not infinite retries. Budget is per-request, not global:

```python
@dataclass
class RetryBudget:
    max_attempts: int = 3
    max_total_time_ms: float = 30_000
    remaining_attempts: int = 3
    elapsed_ms: float = 0
```

**Backoff Strategy**: Exponential with jitter, respecting `retry-after` headers:

```python
def compute_backoff(attempt: int, retry_after: float | None) -> float:
    if retry_after is not None:
        return retry_after + random.uniform(0, 1)  # jitter
    base = min(2 ** attempt, 30)  # cap at 30s
    return base + random.uniform(0, base * 0.1)    # 10% jitter
```

**Token Refresh**: Transparent refresh on `TokenExpiredError`. The refresh itself has its own error handling — if refresh fails, we surface `TokenRefreshFailedError` (user-facing) rather than the original token expiry.

### 4.3 Graceful Degradation

When the primary path fails, degradation options (in order of preference):

| Failure | Degradation | User Impact |
|---------|-------------|-------------|
| Model unavailable | Try alternate model if configured | Possibly lower quality |
| Rate limited | Queue and delay | Increased latency |
| Stream interrupted | Return partial + signal incomplete | Partial response |
| Context too long | Truncate and retry with signal | Potentially incomplete answer |

**Degradation is always explicit**. The response metadata includes a `degraded: true` flag and a `degradation_reason` so the kernel can inform the user.

### 4.4 Circuit Breaker

For sustained failures, a circuit breaker prevents cascading damage:

```
CLOSED (normal) → error_rate > threshold → OPEN (reject fast)
OPEN → after cooldown → HALF_OPEN (allow probe request)
HALF_OPEN → probe succeeds → CLOSED
HALF_OPEN → probe fails → OPEN (reset cooldown)
```

Circuit breaker state is per-model, not global. A failing model doesn't take down the whole provider.

---

## 5. Error Documentation

### 5.1 Error Documentation for AI Maintainers

Every error class carries machine-readable documentation as class-level metadata:

```python
class ModelRateLimitError(RateLimitError):
    """Rate limit exceeded for a specific model.

    AI_CONTEXT:
        common_causes:
            - High request volume to popular models
            - Burst traffic from multiple concurrent sessions
            - Insufficient rate limit tier for workload
        investigation_steps:
            - Check `provider_rate_limit_remaining` gauge
            - Review request rate over last 5 minutes
            - Check if specific model or all models affected
        resolution_patterns:
            - If single model: consider model rotation
            - If all models: check account tier limits
            - If burst: review request queuing config
        related_errors:
            - AccountRateLimitError (escalation of this)
            - GlobalRateLimitError (may co-occur)
    """
```

### 5.2 Error Handling Contracts

Each module in the provider declares its error contract — what it throws, when, and what callers should expect:

```python
class ChatCompletionHandler:
    """
    ERROR_CONTRACT:
        throws:
            - ModelError (any subclass): on model-level failures
            - StreamError (any subclass): during streaming responses
            - AuthenticationError: never (handled by auth layer)
            - RateLimitError: never (handled by rate limit layer)
        guarantees:
            - All SDK exceptions translated before raising
            - ErrorContext always populated
            - correlation_id always present
        delegates_to:
            - AuthenticationLayer: handles all auth errors
            - RateLimitLayer: handles all rate limit errors
    """
```

### 5.3 Example Error Scenarios

Documented as structured test cases for both humans and AI:

```yaml
scenarios:
  - name: "Rate limit during streaming"
    trigger: "429 response mid-stream after 50 tokens"
    expected_flow:
      - StreamInterruptedError raised with partial_content
      - Translated to ModelRateLimitError (cause: mid-stream 429)
      - Retry policy: wait for retry-after, restart full request
      - Partial content discarded (stream restart is clean)
    user_impact: "Slight delay, full response delivered"
    
  - name: "Token expires during long completion"
    trigger: "401 response after 30s of streaming"
    expected_flow:
      - AuthenticationError from SDK
      - Translated to TokenExpiredError
      - Auth layer refreshes token transparently
      - Request retried with new token
      - If refresh fails: TokenRefreshFailedError to user
    user_impact: "Transparent if refresh works; auth prompt if not"
    
  - name: "Model removed from Copilot API"
    trigger: "404 for previously valid model"
    expected_flow:
      - SDK raises NotFoundError
      - Translated to ModelNotFoundError
      - No retry (non-retryable)
      - Error event with model name for catalog update
    user_impact: "Clear message: model unavailable, suggest alternatives"
```

---

## 6. AI-Friendly Errors

### 6.1 What AI Needs to Debug

An AI maintainer diagnosing errors needs structured data, not prose. Every error must provide:

1. **Classification tags** (not free text) — so the AI can pattern-match
2. **Full causal chain** — so the AI sees root cause, not symptoms
3. **Request context** — so the AI can reproduce conditions
4. **Historical frequency** — so the AI knows if this is new or recurring
5. **Related errors** — so the AI can see correlated failures

### 6.2 Structured Error Data Format

```json
{
  "error": {
    "code": "MODEL_RATE_LIMIT",
    "origin": "sdk",
    "severity": "transient",
    "recoverability": "retryable_with_backoff",
    "audience": "internal"
  },
  "context": {
    "correlation_id": "req_abc123",
    "model": "gpt-4",
    "endpoint": "chat/completions",
    "stream": true,
    "attempt": 2,
    "elapsed_ms": 1250
  },
  "sdk_original": {
    "type": "openai.RateLimitError",
    "status_code": 429,
    "message": "Rate limit exceeded",
    "headers": {
      "retry-after": "2",
      "x-ratelimit-remaining": "0",
      "x-ratelimit-reset": "1709890000"
    }
  },
  "recovery": {
    "action": "backoff_retry",
    "backoff_ms": 2150,
    "budget_remaining": 1
  },
  "ai_hints": {
    "investigation_steps": [
      "Check rate_limit_remaining gauge for gpt-4",
      "Review request volume last 5 minutes",
      "Check if retry-after headers are being respected"
    ],
    "similar_recent_errors": 12,
    "first_seen": "2026-03-08T10:30:00Z",
    "pattern": "burst_rate_limit"
  }
}
```

### 6.3 Error Pattern Recognition

The system maintains an error pattern registry — named patterns that the AI can learn and reference:

| Pattern Name | Signature | Likely Cause | Auto-Resolution |
|-------------|-----------|--------------|-----------------|
| `burst_rate_limit` | >5 rate limits in 10s, single model | Concurrent requests spike | Queue + backoff |
| `auth_cascade` | TokenExpired → RefreshFailed → multiple 401s | Token service down | Alert, circuit break auth |
| `model_degradation` | Increasing latency → timeouts → 503s | Model service degrading | Switch to fallback model |
| `stream_instability` | Repeated StreamInterrupted, varying positions | Network instability | Increase timeout, reduce stream |
| `config_drift` | ModelNotFound after deployment | Model catalog changed | Trigger model catalog refresh |

These patterns are defined declaratively so the AI can:
- Match current errors against known patterns
- Detect new patterns from error clusters
- Apply known resolutions automatically
- Propose new pattern definitions for review

### 6.4 Error Diff for AI Review

When error behavior changes between versions, the system generates an error diff:

```
Error Behavior Diff (v1.2.0 → v1.3.0):
  NEW:    ContentFilterError — previously returned as generic ModelError
  CHANGED: RateLimitError detection — was string matching, now status code
  REMOVED: CopilotProviderError (replaced by specific subtypes)
  MOVED:   Retry logic — from provider to kernel policy layer
```

---

## 7. Design Principles Summary

1. **Errors are data, not exceptions.** They carry structured, machine-readable information.
2. **Translation is a table, not logic.** Deterministic mapping from SDK errors to provider errors.
3. **Retry is policy, not behavior.** The provider classifies; the kernel decides.
4. **Zero information loss.** Original error always preserved in ErrorContext.
5. **Errors are observable.** Every error emits a structured event with full context.
6. **Patterns are named.** Recurring error combinations get identifiers for AI recognition.
7. **Contracts are explicit.** Every module declares what it throws and what it handles.
8. **Degradation is explicit.** Users always know when they're getting a degraded response.
9. **Unknown errors are opportunities.** New patterns are surfaced, not swallowed.
10. **AI reads structure, not strings.** Classification tags, causal chains, and investigation steps — not log messages.

---

*This architecture ensures that errors are not just handled, but understood — by both the runtime and the AI that maintains it.*