# Contract: Behaviors

## Version
- **Current:** 1.0 (v2.1 Kernel-Validated)
- **Module Reference:** Multiple modules
- **Config:** config/retry.yaml
- **Kernel Errors:** `amplifier_core.llm_errors`
- **Status:** Specification

---

## Overview

This contract defines behavioral policies that are config-driven. Unlike mechanism (Python), these behaviors can be tuned via YAML configuration.

---

## Retry Policy

### Config Schema

```yaml
retry:
  max_attempts: 3
  backoff:
    strategy: exponential_with_jitter
    base_delay_ms: 1000
    max_delay_ms: 30000
    jitter_factor: 0.1
```

### MUST Constraints

1. **MUST** respect max_attempts
2. **MUST** apply backoff between retries
3. **MUST** add jitter to prevent thundering herd
4. **MUST** only retry errors with `retryable=True`
5. **MUST NOT** retry errors with `retryable=False`
6. **MUST** honor `retry_after` when present

### Retryable Errors (Kernel Types)

| Kernel Error Type | Retryable | Notes |
|-------------------|-----------|-------|
| `AuthenticationError` | No | Invalid credentials |
| `AccessDeniedError` | No | Permission denied |
| `RateLimitError` | Yes | Has retry_after |
| `QuotaExceededError` | No | Billing limit |
| `LLMTimeoutError` | Yes | Transient |
| `ContentFilterError` | No | Content blocked |
| `ProviderUnavailableError` | Yes | Service down |
| `NetworkError` | Yes | Connection failure |
| `NotFoundError` | No | Model doesn't exist |
| `ContextLengthError` | No | Request too large |
| `InvalidRequestError` | No | Malformed request |
| `StreamError` | Yes | Mid-stream failure |
| `AbortError` | No | User cancellation |
| `InvalidToolCallError` | No | Malformed tool call |
| `ConfigurationError` | No | Setup problems |

---

## Circuit Breaker Policy

### Config Schema

```yaml
circuit_breaker:
  soft_turn_limit: 3     # Warn after N turns
  hard_turn_limit: 10    # Error after N turns
  timeout_buffer_seconds: 5.0
```

### MUST Constraints

1. **MUST** track turns within a single complete() call
2. **MUST** raise `ProviderUnavailableError(retryable=False)` at hard limit
3. **SHOULD** log warning at soft limit
4. **MUST** reset turn count on new complete() call

### Rationale

The Deny + Destroy pattern prevents the SDK from executing tools, but the SDK may retry after denial. The circuit breaker prevents infinite retry loops.

Evidence: Session a1a0af17 documented 305 turns from a single request.

---

## Streaming Timing Policy

### Config Schema

```yaml
streaming:
  event_queue_size: 256
  ttft_warning_ms: 5000      # Time to first token
  max_gap_warning_ms: 5000   # Max gap between tokens
  max_gap_error_ms: 30000    # Error threshold
```

### MUST Constraints

1. **MUST** warn if TTFT exceeds threshold
2. **MUST** warn if inter-token gap exceeds warning threshold
3. **MAY** raise `LLMTimeoutError` if gap exceeds error threshold
4. **MUST NOT** block on queue full (drop oldest)

---

## Model Selection Policy

### Config Schema (models.yaml)

```yaml
models:
  default: "claude-sonnet-4"
  
  aliases:
    fast: "gpt-4.1-mini"
    smart: "claude-opus-4.5"
    reasoning: "o3"
  
  capabilities:
    claude-opus-4.5:
      context_window: 200000
      max_output_tokens: 8192
      supports_vision: true
      supports_reasoning: true
```

### MUST Constraints

1. **MUST** resolve aliases to model IDs
2. **MUST** use default if no model specified
3. **SHOULD** validate model exists before request
4. **MUST** raise `NotFoundError` for invalid models

---

## Logging Policy

### MUST Constraints

1. **MUST** log errors at ERROR level
2. **SHOULD** log warnings at WARN level
3. **MAY** log debug info at DEBUG level
4. **MUST NOT** log sensitive data (tokens, prompts in production)
5. **MUST** include correlation IDs for tracing

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `behaviors:Retry:MUST:1` | Respects max_attempts |
| `behaviors:Retry:MUST:2` | Applies backoff |
| `behaviors:Retry:MUST:3` | Only retries retryable errors |
| `behaviors:Retry:MUST:4` | Honors retry_after |
| `behaviors:CircuitBreaker:MUST:1` | Tracks turn count |
| `behaviors:CircuitBreaker:MUST:2` | Errors at hard limit |
| `behaviors:Streaming:MUST:1` | Warns on slow TTFT |
| `behaviors:Models:MUST:1` | Resolves aliases |
| `behaviors:Models:MUST:2` | Raises NotFoundError for invalid |

---

## Implementation Checklist

- [ ] Retry policy reads from config
- [ ] Backoff with jitter implemented
- [ ] Only retry errors with `retryable=True`
- [ ] Circuit breaker tracks turns
- [ ] Circuit breaker raises ProviderUnavailableError at limit
- [ ] Streaming timing warnings work
- [ ] Model aliases resolved
- [ ] NotFoundError for invalid models
- [ ] Logging follows policy
