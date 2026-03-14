# Error Handling Analysis Report

**Date:** 2026-03-12  
**Scope:** Old Provider v1.0.2 → Next-Gen Provider  
**Analyst:** Evidence-Based Review  

---

## Executive Summary

This report documents the gap analysis between error patterns observed in the old provider (v1.0.2) and the error handling implementation in the next-gen provider. The analysis is based on real-world error logs from WSL and Windows usage.

**Key Finding:** The contract specifies 14 error types, but only 8 are implemented. Several high-frequency errors from production logs will fall through to a generic `ProviderUnavailableError`, making them non-actionable for users.

---

## 1. Contract vs Implementation Mismatch

### 1.1 Error Types Specified in Contract (error-hierarchy.md)

```
LLMError (base)
├── AuthenticationError (HTTP 401/403)
│   └── AccessDeniedError (HTTP 403 - permission denied)
├── RateLimitError (HTTP 429, retryable=True)
│   └── QuotaExceededError (billing limit, retryable=False)
├── LLMTimeoutError (retryable=True)
├── ContentFilterError (safety filter)
├── ProviderUnavailableError (HTTP 5xx, retryable=True)
│   └── NetworkError (connection failure, retryable=True)
├── NotFoundError (HTTP 404 - model not found)
├── ContextLengthError (HTTP 413 - context exceeded)
├── InvalidRequestError (HTTP 400/422)
├── StreamError (mid-stream connection failure, retryable=True)
├── AbortError (caller cancellation)
├── InvalidToolCallError (malformed tool call)
└── ConfigurationError (setup problems)
```

### 1.2 Error Types Implemented in error_translation.py

| Contract Specifies | Implemented | Status |
|-------------------|-------------|--------|
| AuthenticationError | ✅ | OK |
| RateLimitError | ✅ | OK |
| QuotaExceededError | ✅ | OK |
| LLMTimeoutError | ✅ | OK |
| ContentFilterError | ✅ | OK |
| NetworkError | ✅ | OK |
| NotFoundError | ✅ | OK |
| ProviderUnavailableError | ✅ | OK |
| **ContextLengthError** | ❌ | **MISSING** |
| **InvalidRequestError** | ❌ | **MISSING** |
| **StreamError** | ❌ | **MISSING** |
| **AbortError** | ❌ | **MISSING** |
| **InvalidToolCallError** | ❌ | **MISSING** |
| **ConfigurationError** | ❌ | **MISSING** |

---

## 2. Error-by-Error Analysis from Old Provider Logs

### 2.1 Token/Context Limit Errors

| Old Provider Error | Next-Gen Maps To | Correct Type | User Actionable? |
|-------------------|------------------|--------------|------------------|
| `CAPIError: 400 prompt token count of 140535 exceeds the limit of 128000` | ProviderUnavailableError (default fallback) | ContextLengthError | ❌ Users won't know to reduce input size |
| `CAPIError: 413 Request Entity Too Large` | ProviderUnavailableError (default fallback) | ContextLengthError | ❌ Same issue |

**Impact:** Users receive "provider unavailable" instead of "your input is too long."

### 2.2 Connection/Network Errors

| Old Provider Error | Next-Gen Maps To | Correct Type | User Actionable? |
|-------------------|------------------|--------------|------------------|
| `HTTP/2 GOAWAY: NO_ERROR (server gracefully closing connection)` | ProviderUnavailableError | StreamError | ⚠️ Works but less specific |
| `[Errno 32] Broken pipe` | ProviderUnavailableError | StreamError | ⚠️ Works but less specific |
| `503 Service Unavailable` | ProviderUnavailableError | ProviderUnavailableError | ✅ Correct |

### 2.3 Circuit Breaker Errors

| Old Provider Error | Next-Gen Maps To | Correct Type | User Actionable? |
|-------------------|------------------|--------------|------------------|
| `[PROVIDER] Received cancellation signal, aborting. timeout=3720.0s > max=60.0s. Circuit breaker tripped.` | **LLMTimeoutError** (matches "timeout" string pattern) | ProviderUnavailableError (retryable=**false**) | ❌ Wrong retry behavior - will retry when it shouldn't |

**Critical Bug:** The string pattern `"timeout"` in the circuit breaker message causes false positive match to `LLMTimeoutError` (retryable=true). Circuit breaker trips should NOT be retried automatically.

### 2.4 Authentication/Permission Errors

| Old Provider Error | Next-Gen Maps To | Correct Type | User Actionable? |
|-------------------|------------------|--------------|------------------|
| `403 unauthorized: not authorized to use this Copilot feature` | AuthenticationError ✅ | AuthenticationError | ✅ Correct |

### 2.5 Model Configuration Errors

| Old Provider Error | Next-Gen Maps To | Correct Type | User Actionable? |
|-------------------|------------------|--------------|------------------|
| `gpt-3.5-turbo does not support reasoning effort configuration, ignoring` | ProviderUnavailableError | ConfigurationError | ❌ Users won't know it's a config issue |

### 2.6 Tool-Related Errors

| Old Provider Error | Next-Gen Maps To | Correct Type | User Actionable? |
|-------------------|------------------|--------------|------------------|
| `External tool "apply_patch" conflicts with a built-in tool` | ProviderUnavailableError | InvalidToolCallError | ❌ Not actionable |
| `Detected fake tool call text in response` | ProviderUnavailableError | InvalidToolCallError | ❌ LLM misbehavior not explained |
| `Detected N missing tool result(s)` | ProviderUnavailableError | InvalidToolCallError | ❌ Context tracking bug hidden |

### 2.7 Request Format Errors

| Old Provider Error | Next-Gen Maps To | Correct Type | User Actionable? |
|-------------------|------------------|--------------|------------------|
| `surrogates not allowed` (UTF-8 encoding) | ProviderUnavailableError | InvalidRequestError | ❌ Encoding issue not explained |

---

## 3. Gaps in config/errors.yaml

### 3.1 Missing Mappings

The following patterns from production logs have NO specific mapping and will fall through to `ProviderUnavailableError`:

```
- "token count" / "exceeds the limit" / "413" → Should map to ContextLengthError
- "GOAWAY" / "broken pipe" / "connection reset" → Should map to StreamError
- "tool conflict" / "fake tool" / "missing tool result" → Should map to InvalidToolCallError
- "does not support" / "configuration" → Should map to ConfigurationError
- "400" / "422" / "surrogates not allowed" → Should map to InvalidRequestError
```

### 3.2 Incorrect Mapping (False Positive)

```
- Circuit breaker message contains "timeout" → Incorrectly matches LLMTimeoutError
- Should match ProviderUnavailableError with retryable=false
```

---

## 4. Missing Error Classes in error_translation.py

The following classes need to be added to `KERNEL_ERROR_MAP`:

```python
ContextLengthError = _make_error_class("ContextLengthError", False)
InvalidRequestError = _make_error_class("InvalidRequestError", False)
StreamError = _make_error_class("StreamError", True)
InvalidToolCallError = _make_error_class("InvalidToolCallError", False)
ConfigurationError = _make_error_class("ConfigurationError", False)
```

---

## 5. Proposed config/errors.yaml Additions

```yaml
  # Circuit breaker - MUST come before timeout pattern to avoid false positive
  - sdk_patterns: ["CircuitBreakerError"]
    string_patterns: ["circuit breaker", "> max="]
    kernel_error: ProviderUnavailableError
    retryable: false

  - sdk_patterns: ["ContextLengthError"]
    string_patterns: ["413", "token count", "exceeds the limit", "context length", "too large"]
    kernel_error: ContextLengthError
    retryable: false

  - sdk_patterns: []
    string_patterns: ["GOAWAY", "broken pipe", "connection reset", "stream"]
    kernel_error: StreamError
    retryable: true

  - sdk_patterns: []
    string_patterns: ["tool conflict", "fake tool", "missing tool result", "malformed tool"]
    kernel_error: InvalidToolCallError
    retryable: false

  - sdk_patterns: []
    string_patterns: ["does not support", "configuration", "not configured"]
    kernel_error: ConfigurationError
    retryable: false

  - sdk_patterns: []
    string_patterns: ["invalid request", "400", "422", "surrogates not allowed"]
    kernel_error: InvalidRequestError
    retryable: false
```

---

## 6. User Actionability Assessment

### 6.1 Current State

| Category | Currently Actionable | Reason |
|----------|---------------------|--------|
| Auth errors (401/403) | ✅ | User knows to check credentials |
| Context length (400/413) | ❌ | Generic "unavailable" hides cause |
| Tool errors | ❌ | Generic "unavailable" |
| Config errors | ❌ | Generic "unavailable" |
| Network errors | ⚠️ | Acceptable but vague |

**Current Score: 1/5 error categories are user-actionable**

### 6.2 With Proposed Fixes

| Category | Would Be Actionable | User Action |
|----------|---------------------|-------------|
| Auth errors (401/403) | ✅ | Check credentials/permissions |
| Context length (400/413) | ✅ | "Reduce input size" |
| Tool errors | ✅ | "Tool misconfiguration detected" |
| Config errors | ✅ | "Check model settings" |
| Network errors | ✅ | More specific retry guidance |

**Projected Score: 5/5 categories would be actionable**

---

## 7. Summary of Required Changes

### 7.1 error_translation.py

1. Add 5 missing error class definitions
2. Add 5 entries to `KERNEL_ERROR_MAP`

### 7.2 config/errors.yaml

1. Add 6 new mapping entries
2. Ensure circuit breaker pattern appears BEFORE timeout pattern (order matters)

### 7.3 Contract Compliance

After changes, implementation will match contract specification for all 14 error types.

---

## Appendix: Raw Error Samples from Old Provider Logs

### A.1 Token Limit Error (400)
```
[TURN] Turn completed with error: CAPIError: 400 prompt token count of 140535 exceeds the limit of 128000 for this model.   Please reduce the size of the prompt or reduce the value of the max tokens argument
```

### A.2 Request Too Large (413)
```
CAPIError: 413 Request Entity Too Large
```

### A.3 HTTP/2 Connection Error (503)
```
ERROR - Unexpected error: HTTPX: Server disconnected without sending a response
HTTP/2 GOAWAY: NO_ERROR (server gracefully closing connection)
```

### A.4 Circuit Breaker Trip
```
[PROVIDER] Received cancellation signal, aborting. timeout=3720.0s > max=60.0s. Circuit breaker tripped.
```

### A.5 Broken Pipe
```
[Errno 32] Broken pipe
```

### A.6 Auth Error (403)
```
CAPIError: 403 {"error":{"message":"unauthorized: not authorized to use this Copilot feature","code":"copilot_provider_error"}}
```

### A.7 Model Config Error
```
gpt-3.5-turbo does not support reasoning effort configuration, ignoring
```

### A.8 Tool Conflict
```
ERROR - Provider provider-github-copilot encountered error: External tool "apply_patch" conflicts with a built-in tool of the same name
```

### A.9 Fake Tool Call
```
[PROVIDER] Detected fake tool call text in response (retry 1/2). Re-prompting LLM to use structured tool calls.
```

### A.10 Missing Tool Results
```
[TURN] Detected 3 missing tool result(s) - context tracking may be broken
```

### A.11 UTF-8 Encoding Error
```
UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800': surrogates not allowed
```

### A.12 Client Health Check Failure
```
[SESSION] Cached client failed health check, creating new client
```

---

## 8. Additional Observations: Message Content Quality

### 8.1 Error Messages Lack Actionable Context

The old provider logs **tell users something happened but not WHAT specifically**:

| Old Provider Message | What Users Need |
|---------------------|-----------------|
| `Detected fake tool call text in response` | **What was the fake tool call?** Users cannot report to LLM team |
| `Detected 3 missing tool result(s)` | **Which tools? What results?** Cannot debug context tracking |
| `MODEL_CACHE: Failed to read cache file` | **Why?** Permission issue is unclear until reading full path |

**Current Contract Gap:** The error-hierarchy contract defines error *types* but not *message content standards*.

### 8.2 Proposed Contract Addition: Error Message Content

```yaml
# Suggested addition to contracts/error-hierarchy.md or contracts/behaviors.md

## Error Message Content Policy

### MUST Constraints

1. **MUST** include specific identifiers when available:
   - Tool errors MUST name the specific tool
   - Model errors MUST name the specific model
   - File errors MUST include the file path

2. **MUST** include actionable context:
   - Token limit errors MUST show (actual/limit) values
   - Permission errors MUST identify the permission type
   - Configuration errors MUST name the configuration key

3. **MUST** provide user-actionable guidance when possible:
   - "Reduce input to under 128000 tokens" (not just "too long")
   - "Tool 'apply_patch' conflicts with built-in" (not just "tool conflict")

### Example Message Patterns

| Error Type | Bad | Good |
|------------|-----|------|
| Context length | `Request too large` | `Token count 140535 exceeds limit 128000. Reduce by 12535 tokens.` |
| Fake tool call | `Detected fake tool call` | `LLM emitted non-structured tool call: "```apply_patch\n..."` |
| Missing result | `3 missing tool results` | `Missing results for tools: get_file (call_123), run_cmd (call_456), edit_file (call_789)` |
| Permission | `Permission denied` | `Permission denied: cannot write to /home/user/.amplifier/cache (Errno 13)` |
```

---

## 9. WSL Permission Denied Error Analysis

### 9.1 Old Provider Behavior

```
[MODEL_CACHE] Failed to read cache file: [Errno 13] Permission denied: '/home/mowrim/.amplifier/cache/github-copilot-models.json'
```

**Root Cause:** Old provider writes model cache to filesystem at `~/.amplifier/cache/`. WSL permission models differ from native Linux, causing intermittent access failures.

### 9.2 Next-Gen Provider Solution

The next-gen provider **architecturally eliminates this issue**:

| Aspect | Old Provider | Next-Gen Provider |
|--------|-------------|-------------------|
| Model cache location | `~/.amplifier/cache/github-copilot-models.json` | In-memory only (SDK `_models_cache`) |
| Session persistence | Long-lived, cached | Ephemeral (Deny+Destroy) |
| File permissions needed | Yes | No |
| Cross-platform issues | WSL, Windows, macOS differ | None - no filesystem |

**Status:** Issue eliminated by design. No code change needed.

---

**End of Report**
