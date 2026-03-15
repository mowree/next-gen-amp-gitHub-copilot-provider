# Wave 3, Agent 24: Developer Experience Analysis

**Agent Role**: User Experience Expert  
**Date**: 2026-03-08  
**Subject**: Developer experience of configuring, using, debugging, and recovering from failures in the GitHub Copilot Provider for Amplifier

---

## Executive Summary

The GitHub Copilot Provider is a technically sophisticated piece of software — 5,286 lines across 13 modules — that bridges two systems never designed to work together this way. The developer experience reflects that tension: **configuration is reasonable but under-documented, error messages are structured but often opaque, observability is present but fragmented, and failure recovery demands knowledge the provider never teaches you.** The core UX problem isn't any single deficiency — it's the gap between the provider's internal complexity and the simplicity developers expect from a `mount()` call.

This analysis examines six dimensions of developer experience, grades each, and provides specific, actionable improvement recommendations.

---

## 1. Configuration UX

### 1.1 Current State

The provider exposes configuration through the `mount()` function and `CopilotSdkProvider.__init__`. The surface is reasonable — 18 parameters for the provider plus 4 for the client wrapper:

```python
mount(
    coordinator,
    model="claude-opus-4.5",       # sensible default
    timeout=3600.0,                # 1 hour — generous
    use_streaming=True,            # correct default
    debug=False,                   # correct default
    max_retries=3,                 # reasonable
    sdk_max_turns=3,               # arcane — what does this mean to a user?
    # ... 11 more parameters
)
```

**What works well:**
- `mount()` is a single entry point — clean API surface
- Most defaults are sensible (`use_streaming=True`, `timeout=3600`, `max_retries=3`)
- The default model (`claude-opus-4.5`) is a good choice for the current moment
- Environment variable fallback chain for GitHub tokens (4 levels) is pragmatic

**What doesn't work:**

1. **`sdk_max_turns` is user-hostile.** This parameter controls the circuit breaker for the Deny + Destroy pattern — an internal implementation detail. A developer shouldn't need to know what "SDK turns" means. The name leaks the abstraction. If this must be exposed, it should be renamed to something like `max_internal_retries` with a docstring explaining when and why to change it.

2. **`thinking_timeout` vs `timeout` is confusing.** Both default to 3600 seconds. When would a user set them differently? The answer requires understanding extended thinking models, which is not explained at the configuration surface. A user who doesn't know about thinking models (most users) sees two timeout parameters with identical defaults and no guidance.

3. **`priority`** (default: 100) is Amplifier orchestrator plumbing. Developers configuring a single provider will never need this. It should be hidden from the primary configuration surface.

4. **`raw`** (default: False) — "Include raw payloads in events." What events? What payloads? This is a debug toggle masquerading as a feature flag, with no explanation of what it enables.

5. **`debug_truncate_length`** (default: 180) — exposed as a top-level config parameter. This is a logging detail that belongs in a debug sub-config, not alongside model selection and timeouts.

6. **No configuration validation with actionable messages.** If a user passes `model="gpt-nonexistent"`, when do they find out? Not at `mount()` time — at the first `complete()` call. Configuration errors should fail fast with clear messages.

### 1.2 Auth Configuration Experience

The token discovery chain is pragmatic but invisible:

```
1. config["github_token"]     — explicit config
2. COPILOT_GITHUB_TOKEN       — provider-specific env
3. GH_TOKEN                   — GitHub CLI env
4. GITHUB_TOKEN               — generic GitHub env
5. SDK stored OAuth creds     — gh auth login
```

**Problem:** If auth fails, the user gets a `CopilotAuthenticationError` that doesn't tell them which sources were checked and which were empty. The error should say: "Authentication failed. Checked: config['github_token'] (not set), COPILOT_GITHUB_TOKEN (not set), GH_TOKEN (not set), GITHUB_TOKEN (found but invalid), SDK OAuth (not found). Run `gh auth login` to authenticate."

### 1.3 Configuration UX Grade: C+

Sensible defaults carry this, but the configuration surface mixes user concerns with internal plumbing, and provides no validation or guidance at mount time.

### 1.4 Recommendations

| Priority | Recommendation |
|----------|---------------|
| P0 | Add mount-time configuration validation with actionable error messages |
| P0 | Add auth source discovery logging — tell users which token sources were checked |
| P1 | Rename `sdk_max_turns` to `max_internal_retries` or hide it entirely |
| P1 | Group debug parameters (`debug`, `debug_truncate_length`, `raw`) into a `debug_config` dict |
| P2 | Add a `mount()` docstring with a "Getting Started" example showing minimal vs full config |
| P2 | Hide `priority` from primary config surface (accept but don't advertise) |
| P2 | Add a "config dump" debug log at mount time showing resolved configuration (redacting tokens) |

---

## 2. Error Experience

### 2.1 Error Message Quality

The provider has a well-structured exception hierarchy (8 exception classes), but the **user-facing quality** of error messages varies dramatically:

**Good error messages:**
- Rate limit errors extract `retry_after` values and provide timing information
- The error hierarchy maps cleanly to Kernel error types with appropriate retryability flags
- Error translation preserves original SDK errors as `__cause__`

**Bad error messages:**

1. **String-matching error detection is brittle and produces vague errors.** Rate limit detection scans for substrings like "rate limit", "429", "too many requests" in error messages. When detection fails (new error format), the error falls through to a generic `KernelProviderUnavailableError` that tells the user nothing useful:

   ```
   CopilotProviderError: SDK error during completion
   ```

   This message doesn't tell the user: What went wrong? Is it their fault? Can they retry? What should they do?

2. **`CopilotSdkLoopError` is incomprehensible to users.** When the circuit breaker trips:

   ```
   CopilotSdkLoopError: SDK exceeded maximum turns (3)
   ```

   A developer sees this and asks: "What are SDK turns? Why is there a maximum? Did my request fail? Is my data lost?" The error should explain: "The model attempted to use tools but the provider's internal retry limit was reached. This is usually temporary — retry the request. If it persists, the model may be stuck in a tool-calling loop."

3. **`CopilotContentFilterError` is defined but never raised.** This means content filtering errors are silently misclassified as generic errors. A user whose content was filtered gets a confusing generic error instead of a clear "Your request or the model's response was blocked by content policy."

4. **Model not found detection uses string matching** (`"model" AND ("not found" OR "invalid")`). If the SDK changes its error format, model-not-found errors become generic errors with no guidance.

### 2.2 Error Chain Visibility

When errors propagate through the translation layer, the chain is:
```
SDK Exception → CopilotProviderError → KernelLLMError
```

The original SDK error is preserved via `__cause__`, which is good for debugging but invisible to users. In practice, users see only the final `KernelLLMError` message, which often loses context.

### 2.3 Error Experience Grade: B-

The error hierarchy design is solid, but the user-facing messages are often developer-hostile. The gap between "well-structured exceptions" and "helpful error messages" is the core problem.

### 2.4 Recommendations

| Priority | Recommendation |
|----------|---------------|
| P0 | Wire up `CopilotContentFilterError` in the error translation layer |
| P0 | Add human-readable `suggested_action` field to all user-facing errors |
| P1 | Replace string-matching error detection with structural detection (status codes, error types) where possible |
| P1 | Rewrite `CopilotSdkLoopError` message to explain the situation in user terms |
| P1 | Add "What happened / Why / What to do" structure to all error messages |
| P2 | Log the full error chain at DEBUG level for troubleshooting |
| P2 | Add error documentation with common causes and resolutions |

---

## 3. Observability UX

### 3.1 What Users Can See

The provider uses Python's standard `logging` module. Observability is gated by the `debug` config flag:

- **`debug=False` (default):** Minimal logging. Errors and warnings only. Users see almost nothing during normal operation — which is correct for production but unhelpful when something goes wrong.

- **`debug=True`:** Verbose logging with truncated payloads (default 180 chars). This dumps SDK event details, session lifecycle events, and timing information.

**The gap:** There's no middle ground. Users who want to understand "why is this slow?" or "what model am I actually hitting?" must enable full debug mode, which floods logs with SDK internal details they don't care about.

### 3.2 Log Readability

Debug logs are functional but not designed for human consumption:

```
DEBUG provider: SDK event ASSISTANT_MESSAGE_DELTA received, data={'content': 'Here is the imp...'}
DEBUG sdk_driver: Turn 1 complete, tools_captured=2, circuit_breaker=ok
DEBUG client: Session a1b2c3 created, model=claude-opus-4.5, tools=5
```

**Problems:**
- No visual hierarchy — everything is `DEBUG` level
- No timestamps relative to request start (elapsed time would be more useful than wall clock)
- No correlation between related log lines (no request ID visible)
- SDK internal details (turn counting, circuit breaker state) leak into user-visible logs
- The `debug_truncate_length=180` default cuts off useful information while still showing irrelevant details

### 3.3 What's Missing

1. **No request-level summary.** After a `complete()` call, users don't get a one-line summary: "Model: claude-opus-4.5, Input: 1523 tokens, Output: 847 tokens, Time: 3.2s, Tools: 2 captured." This single log line would answer 80% of debugging questions.

2. **No slow-request alerts.** If a request takes 30+ seconds with no tokens, there's no indication of what's happening. The user stares at silence until the response arrives or timeout fires.

3. **No health status.** Users can't ask "is the provider healthy?" There's no health endpoint, no status summary, no way to verify the CLI subprocess is running and authenticated without making an actual completion request.

4. **Hook events are fire-and-forget with no visibility.** The provider emits events via `coordinator.hooks.emit()`, but users have no way to see these events without writing custom hook handlers. There's no built-in event viewer or event log.

### 3.4 Observability UX Grade: C

Logging exists but is binary (off/firehose), not layered. The absence of request summaries and health status makes debugging unnecessarily difficult.

### 3.5 Recommendations

| Priority | Recommendation |
|----------|---------------|
| P0 | Add INFO-level request summary log after every `complete()` call (model, tokens, time, tools) |
| P0 | Add a `get_health()` method that returns provider health status without making an LLM call |
| P1 | Add a `verbose` log level between silent and debug (shows request lifecycle without SDK internals) |
| P1 | Add elapsed-time prefixes to debug log lines |
| P1 | Add request correlation IDs to all log lines within a `complete()` call |
| P2 | Add a "slow request" warning at 10s with no tokens received |
| P2 | Add startup summary log: "Copilot provider mounted. Model: X, CLI: /path/to/cli, Auth: token from GH_TOKEN" |

---

## 4. Performance Perception

### 4.1 What Feels Fast vs Slow

The provider has **120–475ms of overhead per request** (excluding LLM time), based on the Wave 2 performance analysis. This overhead is invisible to users — they experience it as "the model is slow" without understanding the provider is adding latency.

**What feels fast:**
- Streaming responses — token-by-token delivery gives immediate feedback
- Model listing — if cached, returns instantly

**What feels slow:**
- **First request after mount:** Cold start includes CLI subprocess launch (~1-2s), initial health check, and session creation. Users experience a noticeable delay before the first response.
- **Thinking model responses:** Extended thinking (10-60+ seconds of silence before text appears) with no progress indication. The user sees nothing — no "model is thinking" indicator, no progress bar, no elapsed time display.
- **Tool capture with abort:** The Deny + Destroy pattern adds latency (SDK retry loop + abort). Users see the model "pause" between generating text and returning tool calls, with no explanation.
- **Recovery from dead CLI process:** If the subprocess crashes, the next request triggers health check → restart → retry, adding 2-5 seconds of unexplained delay.

### 4.2 Progress Indicators

**There are none.** The provider provides zero progress feedback between "request sent" and "first token received." For thinking models, this gap can be 60+ seconds.

The streaming architecture emits `llm:thinking_block` events during reasoning, which is good — but only if something is listening. The default user experience has no consumer for these events.

### 4.3 Timeout Handling UX

The timeout configuration is generous (3600s default) but the timeout experience is poor:

- **No warning before timeout.** At 3500 seconds, nothing. At 3600 seconds, sudden `CopilotTimeoutError`.
- **Partial response handling is good** (returns accumulated content on timeout), but the user doesn't know they got a partial response unless they check `finish_reason`.
- **The 5-second SDK timeout buffer** is invisible to users. They configure 3600s, but the SDK gets 3605s. This is correct engineering but adds confusion if users ever notice the discrepancy in logs.

### 4.4 Performance Perception Grade: C+

Streaming saves this from a lower grade. Everything else — cold start, thinking delays, progress feedback, timeout UX — leaves users in the dark.

### 4.5 Recommendations

| Priority | Recommendation |
|----------|---------------|
| P0 | Emit an INFO log when thinking begins: "Model is reasoning (extended thinking enabled)..." |
| P0 | Add cold-start warning: "First request may be slow while CLI subprocess initializes" |
| P1 | Add elapsed-time logging every 30s during long requests: "Request in progress: 30s elapsed, 245 tokens received" |
| P1 | Emit a structured event when TTFT (time to first token) is measured |
| P2 | Add a timeout warning at 80% of configured timeout |
| P2 | Document expected latency ranges for different models and thinking configurations |

---

## 5. Documentation UX

### 5.1 Current State

Based on the codebase exploration, documentation lives in:
- Docstrings within source modules (variable quality)
- `_constants.py` with inline comments explaining values
- `BUG FIX` comments scattered through `provider.py`
- SDK assumption test files that double as behavioral documentation
- No standalone README, getting-started guide, or troubleshooting guide observed in the provider package

### 5.2 Getting Started Experience

A new developer wanting to use this provider must:

1. **Discover** that `mount()` is the entry point (from `__init__.py` exports)
2. **Understand** that a GitHub token is needed (from environment variable scanning in `client.py`)
3. **Know** that the Copilot CLI binary must be installed (from `_platform.py` auto-discovery)
4. **Figure out** which models are available (from `list_models()` or `BUNDLED_MODEL_LIMITS`)
5. **Hope** that default configuration works (it usually does)

**Steps 1-4 are undiscoverable without reading source code.** There's no "Getting Started in 5 Minutes" guide. There's no error message at mount time that says "CLI binary not found — install it with `npm install -g @github/copilot-cli`" (or whatever the install command is).

### 5.3 Troubleshooting Experience

When something goes wrong, the developer's debugging journey is:

1. See a vague error message
2. Enable `debug=True` and reproduce
3. Get flooded with SDK internal logs
4. Search source code for the error message string
5. Find scattered `BUG FIX` comments that explain past issues
6. Guess at a solution

**There's no troubleshooting guide.** Common issues like:
- "Auth failed" → check token sources
- "Model not found" → check available models with `list_models()`
- "Timeout" → thinking models need longer timeouts
- "SDK loop error" → internal issue, retry
- "CLI not found" → install instructions

...are all answerable but nowhere collected.

### 5.4 API Documentation

The provider protocol (5 methods: `name`, `get_info()`, `list_models()`, `complete()`, `parse_tool_calls()`) is not documented with examples. A developer can't answer:
- What does `complete()` return for a streaming vs non-streaming response?
- What format should `messages` be in?
- How are tool calls represented?
- What happens when thinking is enabled?

### 5.5 Documentation UX Grade: D+

The code is well-commented internally, but there's a near-complete absence of user-facing documentation. Developers are expected to read source code to use the provider.

### 5.6 Recommendations

| Priority | Recommendation |
|----------|---------------|
| P0 | Create a "Getting Started" section in the package docstring or README |
| P0 | Add CLI binary discovery failure message with install instructions |
| P1 | Create a troubleshooting guide covering the top 5 error scenarios |
| P1 | Add `mount()` function docstring with minimal and full configuration examples |
| P1 | Document the auth token discovery chain with setup instructions |
| P2 | Add model selection guide (which models support thinking, tool use, etc.) |
| P2 | Add per-method docstrings with input/output examples for the 5-method protocol |
| P3 | Create an architecture overview for contributors (currently in Wave 1 analysis, not in repo) |

---

## 6. Failure Modes

### 6.1 Auth Fails

**Current experience:**
```
CopilotAuthenticationError: Authentication failed
→ KernelAuthenticationError (not retryable)
```

**What the user needs:** Which auth method was tried? What specifically failed (expired token, invalid token, no token)? How to fix it?

**Recovery guidance:** None. User must know to check environment variables or run `gh auth login`.

**Grade: D** — The most common setup failure has the least helpful error message.

### 6.2 SDK Is Unavailable (CLI Binary Not Found)

**Current experience:** The `_platform.py` module auto-discovers the CLI binary across Windows/Unix/macOS paths. If not found:

```
CopilotConnectionError: Failed to start Copilot CLI
→ KernelNetworkError (retryable — but retrying won't help)
```

**Problems:**
- Classified as "retryable" — but retrying a missing binary is pointless
- No install instructions in the error message
- No indication of which paths were searched

**Grade: D** — A missing dependency should produce a clear "install X" message, not a retryable connection error.

### 6.3 Model Doesn't Exist

**Current experience:**
```
CopilotModelNotFoundError: Model 'gpt-nonexistent' not found
→ KernelNotFoundError (not retryable)
```

**What's missing:** List of available models. The error should say: "Model 'gpt-nonexistent' not found. Available models: claude-opus-4.5, gpt-4o, ... Use `list_models()` to see all options."

**Grade: C** — The error is clear but doesn't help the user recover.

### 6.4 Rate Limited

**Current experience:**
```
CopilotRateLimitError: Rate limit exceeded (retry after 30s)
→ KernelRateLimitError (retryable with backoff)
```

**This is actually good.** The provider extracts `retry_after` values, classifies the error correctly, and the kernel's retry policy handles backoff. The user may experience a brief delay but requests eventually succeed.

**Grade: B+** — Best failure mode UX in the provider. Could improve by logging which model/account hit the limit.

### 6.5 The 305-Turn Loop Bug (Historical)

**Current experience:** The SDK Driver and circuit breaker prevent this from recurring. If it somehow triggers:

```
CopilotSdkLoopError: SDK exceeded maximum turns (3)
→ KernelProviderUnavailableError (not retryable)
```

**Problem:** "Not retryable" is too aggressive. The user should retry with a different prompt or model. The error message should suggest this.

**Grade: C-** — Protected against the catastrophic case, but the error UX is unhelpful.

### 6.6 CLI Subprocess Crash

**Current experience:** The singleton client detects dead subprocesses via ping-based health checks. The next request triggers a restart. From the user's perspective: one request fails with a vague error, then subsequent requests work.

**Problem:** The first failure is unexplained. The user doesn't know the CLI crashed and was restarted. A log message should say: "CLI subprocess was unresponsive. Restarting... (this may add 1-2 seconds to the current request)."

**Grade: C** — Self-healing works but is invisible.

### 6.7 Failure Mode Summary

| Failure Mode | Detection | Error Quality | Recovery Guidance | Grade |
|---|---|---|---|---|
| Auth fails | Good (multi-source check) | Poor (no source detail) | None | D |
| CLI not found | Good (multi-platform search) | Poor (wrong error type) | None | D |
| Model not found | Adequate (string matching) | Adequate (clear message) | Poor (no alternatives) | C |
| Rate limited | Good (pattern extraction) | Good (retry-after) | Good (automatic retry) | B+ |
| SDK loop | Good (circuit breaker) | Poor (internal jargon) | Poor (says "not retryable") | C- |
| CLI crash | Good (health check + restart) | Poor (unexplained failure) | Adequate (auto-recovery) | C |
| Content filter | **Missing** (error defined, never raised) | N/A | N/A | F |

---

## 7. Overall Developer Experience Assessment

### 7.1 Composite Grade: C

| Dimension | Grade | Weight | Weighted |
|-----------|-------|--------|----------|
| Configuration UX | C+ | 20% | 0.46 |
| Error Experience | B- | 25% | 0.68 |
| Observability UX | C | 15% | 0.30 |
| Performance Perception | C+ | 15% | 0.35 |
| Documentation UX | D+ | 10% | 0.13 |
| Failure Modes | C | 15% | 0.30 |
| **Composite** | **C** | 100% | **2.22/4.0** |

### 7.2 The Core Problem

The provider is **engineered for the machine, not the human.** Internally, it's well-structured: clean exception hierarchy, smart retry logic, elegant circuit breaker pattern, tiered caching. But all this sophistication is invisible to the developer using it. The user-facing surface — error messages, logging, documentation, configuration — is an afterthought.

This is the classic "brilliant backend, neglected frontend" pattern. The fix isn't a redesign — it's a **presentation layer** for the existing excellent internals.

### 7.3 Top 5 Highest-Impact Improvements

1. **Add mount-time validation + startup summary log** — Catch configuration errors early, confirm auth works, show resolved config. One change that improves configuration UX, observability, and failure modes simultaneously.

2. **Add request-level summary logging at INFO level** — Model, tokens, time, tools, finish reason. One log line that answers 80% of debugging questions without enabling debug mode.

3. **Wire up `CopilotContentFilterError` and add `suggested_action` to all errors** — The content filter gap is a real bug. Adding recovery suggestions to errors is the single highest-ROI change for error experience.

4. **Create a minimal getting-started guide with troubleshooting FAQ** — Cover auth setup, CLI installation, model selection, and the top 5 error scenarios. This doesn't need to be comprehensive — just enough to unblock the first-time user.

5. **Add "thinking in progress" and "slow request" log messages** — Users waiting 60+ seconds with no feedback assume something is broken. A periodic heartbeat log ("Request in progress: 45s elapsed, model is reasoning...") eliminates an entire category of support questions.

---

*The provider's internal architecture is excellent. Its developer experience should match.*
