# WAVE 1, AGENT 10: Comprehensive Codebase Exploration Report

**Date**: 2026-03-08
**Scope**: amplifier-module-provider-github-copilot v1.0.4 + copilot-sdk (Python)
**Total Source Lines Read**: ~6,500+ (provider) + SDK docs

---

## 1. CODE MAP: Full Module Inventory

### Provider Package: `amplifier_module_provider_github_copilot/`

| Module | Lines | Responsibility | Key Dependencies |
|--------|-------|---------------|-----------------|
| `__init__.py` | 371 | Entry point, `mount()` function, process-level singleton client management | All modules, `amplifier_core` |
| `provider.py` | 1799 | **Core**: `CopilotSdkProvider` class implementing 5-method Amplifier Provider protocol | `client`, `converters`, `exceptions`, `model_cache`, `model_naming`, `tool_capture`, `sdk_driver`, `amplifier_core` |
| `client.py` | 820 | `CopilotClientWrapper` - lifecycle management, session creation, health checks | `copilot` SDK, `_constants`, `exceptions` |
| `converters.py` | 426 | Message format conversion (Amplifier ↔ Copilot SDK prompt format) | `amplifier_core` |
| `sdk_driver.py` | 620 | SDK Driver pattern - `SdkEventHandler`, `LoopController`, `ToolCaptureStrategy`, `CircuitBreaker` | `_constants`, `exceptions` |
| `tool_capture.py` | 218 | Tool bridge for Deny + Destroy pattern - converts tools, creates deny hooks | `copilot.types.Tool`, `_constants` |
| `models.py` | 292 | Model mapping - `CopilotModelInfo`, `fetch_and_map_models()`, `to_amplifier_model_info()` | `amplifier_core.ModelInfo`, `client` |
| `model_cache.py` | 415 | Disk-persistent model metadata cache with atomic writes | `_constants` |
| `model_naming.py` | 359 | Model ID naming conventions, pattern parsing, thinking model detection | Pure Python |
| `exceptions.py` | 322 | Exception hierarchy (8 exception classes) + rate-limit/content-filter detection | Pure Python |
| `_constants.py` | 312 | All constants: timeouts, built-in tool names, SDK behavior constants | `enum` |
| `_permissions.py` | 52 | File permission utilities (ensure_executable with least-privilege) | `os`, `stat` |
| `_platform.py` | 280 | Cross-platform CLI binary location (Windows/Unix/macOS) | `sys`, `shutil`, `pathlib` |

**Total provider source**: ~5,286 lines across 13 modules.

### SDK Package: `copilot-sdk/python/copilot/`

| Module | Responsibility |
|--------|---------------|
| `client.py` | `CopilotClient` - manages CLI subprocess, JSON-RPC communication |
| `session.py` | `CopilotSession` - session management, event subscription, send/wait |
| `types.py` | Type definitions: `SessionConfig`, `Tool`, `PermissionHandler`, `CopilotClientOptions` |
| `tools.py` | Tool definition utilities (`define_tool` decorator) |
| `jsonrpc.py` | JSON-RPC protocol implementation |
| `generated/` | Auto-generated event types (`SessionEventType` enum) |

---

## 2. TECHNICAL DEBT

### Explicit TODOs/FIXMEs Found

1. **`client.py:537-555`** - **TECH DEBT (Security Enhancement)**: Permission handler uses `approve_all`. Comment explicitly says future versions should implement granular permission handler with rate limiting and audit logging. Risk: MEDIUM.

2. **`_constants.py:182-190`** - **BUILTIN_TO_AMPLIFIER_CAPABILITY mapping comment**: States "Excluding ALL built-ins at once hangs the CLI" but the current code in `provider.py:877` does `excluded_builtins = sorted(COPILOT_BUILTIN_TOOL_NAMES)` which excludes ALL known built-ins. **Potential contradiction** between comment and implementation.

3. **`provider.py:416-428`** - Comments mention "BUG 3 FIX" and "BUG 5 FIX" (`provider.py:1503`) indicating past bugs that were fixed but the fix comments are scattered.

4. **`model_cache.py:69-71`** - Gemini model has a NOTE: "SDK returns max_output=0 for gemini - likely SDK bug. Using 65536 as max_output_tokens to keep budget positive." This is a hardcoded workaround.

5. **`converters.py:136`** - Tool call serialization uses `<tool_used>` XML tags which the model can mimic, leading to the fake tool call detection logic in `provider.py:1076-1138`. This is a workaround for a fundamental format issue.

### Commented-Out Code

- **`client.py:350`**: `# logger.exception()` comment explaining why `logger.exception()` is used (not commented code, but notable).
- No significant commented-out code blocks found. The codebase is clean in this regard.

### Workarounds

1. **Fake Tool Call Detection** (`provider.py:122-208`): Module-level regex + code-block-aware detection to catch when the LLM writes tool calls as plain text instead of structured calls. Up to 2 retry attempts with correction messages.

2. **Missing Tool Result Repair** (`provider.py:1596-1657`): Safety net that detects missing tool results in conversation history and injects synthetic error results. Uses LRU-bounded tracking (`OrderedDict`, max 1000) to prevent infinite loops.

3. **SDK Timeout Buffer** (`_constants.py:78`): `SDK_TIMEOUT_BUFFER_SECONDS = 5.0` added to SDK-level timeout so the provider's `asyncio.timeout` wins the race.

4. **Health Check on Cached Client** (`client.py:182-207`): Ping-based health check before returning cached client to detect dead subprocesses.

---

## 3. PATTERN INVENTORY

### Design Patterns Currently Used

1. **Stateless Provider (Pattern A: Deny + Destroy)**
   - Each `complete()` creates an ephemeral Copilot session
   - Sessions are disconnected after use
   - Amplifier maintains all conversation state externally
   - **Location**: `provider.py:7-17`, `client.py:425-607`

2. **Process-Level Singleton** (for shared CLI subprocess)
   - `_shared_client` + `_shared_client_refcount` + `_shared_client_lock`
   - Reference counting with lazy lock initialization
   - Prevents N sub-agents from spawning N CLI processes (~500MB each)
   - **Location**: `__init__.py:125-210`

3. **SDK Driver Pattern** (for taming SDK's internal agent loop)
   - `LoopController` - turn tracking and abort signaling
   - `ToolCaptureStrategy` - first-turn-only capture with deduplication
   - `CircuitBreaker` - trip on turn count or timeout exceeded
   - `SdkEventHandler` - unified coordinator
   - **Location**: `sdk_driver.py` (entire module)

4. **Strategy Pattern** (for platform detection)
   - `PlatformInfo` dataclass with `get_platform_info()` factory
   - Single source of truth for binary naming
   - **Location**: `_platform.py:54-111`

5. **Double-Checked Locking** (for thread-safe initialization)
   - Used in `client.py:ensure_client()` and `provider.py:_model_supports_reasoning()`
   - Fast path without lock, slow path with lock re-check

6. **Error Translation Layer**
   - Domain exceptions (`CopilotProviderError` hierarchy) → Kernel exceptions (`KernelLLMError` hierarchy)
   - **Location**: `provider.py:976-1049`

7. **LRU Eviction** (for repaired tool ID tracking)
   - `OrderedDict` with `move_to_end()` and `popitem(last=False)`
   - **Location**: `provider.py:1762-1783`

8. **Atomic File Write** (for cache persistence)
   - `tempfile.mkstemp()` + `os.fsync()` + `Path.replace()`
   - **Location**: `model_cache.py:329-359`

9. **Tiered Fallback** (for model limits)
   - Tier 1: In-memory cache (populated by `list_models()`)
   - Tier 2: Disk cache (`~/.amplifier/cache/github-copilot-models.json`)
   - Tier 3: Bundled hardcoded limits (`BUNDLED_MODEL_LIMITS`)
   - Tier 4: Default values (200000/32000)
   - **Location**: `provider.py:456-505`, `model_cache.py:44-107`

---

## 4. SDK INTEGRATION POINTS

Every place the provider calls SDK code:

| Call Site | SDK API Used | Location |
|-----------|-------------|----------|
| Client initialization | `CopilotClient(options)`, `client.start()` | `client.py:272-296` |
| Health check | `client.ping()` | `client.py:196-197` |
| Authentication | `client.get_auth_status()` | `client.py:413` |
| Session creation | `client.create_session(config)` | `client.py:580` |
| Session disconnect | `session.disconnect()` | `client.py:600` |
| Send & wait | `session.send_and_wait(options, timeout)` | `client.py:645-648` |
| Send (streaming) | `session.send(options)` | `provider.py:1235` |
| Event subscription | `session.on(handler)` | `provider.py:1231` |
| Session abort | `session.abort()` | `provider.py:1270`, `client.py:655` |
| List models | `client.list_models()` | `client.py:694` |
| List sessions | `client.list_sessions()` | `client.py:784` |
| Client stop | `client.stop()` | `client.py:712` |
| Tool creation | `Tool(name, description, handler, parameters, overrides_built_in_tool)` | `tool_capture.py:153-161` |
| Permission handler | `PermissionHandler.approve_all` | `client.py:561` |
| Event types | `SessionEventType.*` | `sdk_driver.py:412` |
| SDK types | `CopilotClientOptions`, `SessionConfig`, `ModelInfo` | `client.py:293-295, 578-580` |

**Critical SDK Dependencies**:
- `copilot.CopilotClient` - core client class
- `copilot.types.Tool` - tool definition (requires `handler`, `overrides_built_in_tool`)
- `copilot.types.PermissionHandler` - session permission handling
- `copilot.types.SessionConfig` - TypedDict for session configuration
- `copilot.generated.session_events.SessionEventType` - event type enum

---

## 5. ERROR PATHS

### Exception Hierarchy

```
CopilotProviderError (base)
├── CopilotAuthenticationError → KernelAuthenticationError (not retryable)
├── CopilotConnectionError → KernelNetworkError (retryable)
├── CopilotRateLimitError → KernelRateLimitError (conditionally retryable)
├── CopilotModelNotFoundError → KernelNotFoundError (not retryable)
├── CopilotSessionError → KernelProviderUnavailableError (retryable)
├── CopilotSdkLoopError → KernelProviderUnavailableError (not retryable)
├── CopilotAbortError → KernelAbortError (not retryable)
├── CopilotTimeoutError → KernelLLMTimeoutError (retryable)
└── CopilotContentFilterError (defined but NOT used in provider.py error translation)
```

### Error Detection Heuristics

1. **Rate limit detection** (`exceptions.py:229-273`): Pattern matching on error messages for "rate limit", "429", "too many requests", etc. Extracts `retry_after` value via regex.

2. **Content filter detection** (`exceptions.py:280-322`): Pattern matching for "content filtered", "blocked by policy", etc. **NOTE: `CopilotContentFilterError` is defined but never raised in `provider.py`'s error translation block.** This is a gap.

3. **Model not found heuristic** (`client.py:584-586`): Checks for "model" AND ("not found" OR "invalid") in error message.

4. **Auth error heuristic** (`client.py:354`): Checks for "auth", "token", or "login" in error message.

### Retry Configuration

- `max_retries`: 3 (default)
- `initial_delay`: 1.0s
- `max_delay`: 60.0s
- `jitter`: True
- Rate limit fail-fast: If `retry_after > max_delay`, marked non-retryable
- Uses `amplifier_core.utils.retry.retry_with_backoff`

---

## 6. CONFIGURATION SURFACE

### Provider Config (passed to `mount()` / `CopilotSdkProvider.__init__`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model` / `default_model` | `"claude-opus-4.5"` | Default model ID |
| `timeout` | `3600.0` (1 hour) | Regular request timeout |
| `thinking_timeout` | `3600.0` (1 hour) | Extended thinking timeout |
| `debug` | `False` | Debug logging |
| `debug_truncate_length` | `180` | Max debug output length |
| `use_streaming` | `True` | Enable streaming mode |
| `raw` | `False` | Include raw payloads in events |
| `priority` | `100` | Orchestrator provider selection priority |
| `max_retries` | `3` | Retry count |
| `retry_min_delay` | `1.0` | Initial retry delay (seconds) |
| `retry_max_delay` | `60.0` | Maximum retry delay |
| `retry_jitter` | `True` | Add jitter to retry delays |
| `sdk_max_turns` | `3` | SDK driver max turns |
| `cli_path` | Auto-discovered | Path to Copilot CLI binary |

### Client Config (passed to `CopilotClientWrapper`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `log_level` | None | CLI log level |
| `auto_restart` | None | Auto-restart CLI on crash |
| `cwd` | None | Working directory for CLI |
| `github_token` | Env vars | GitHub auth token |

### Environment Variables (Token Precedence)

1. `config["github_token"]`
2. `COPILOT_GITHUB_TOKEN`
3. `GH_TOKEN`
4. `GITHUB_TOKEN`
5. SDK stored OAuth creds

### Constants (`_constants.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `DEFAULT_MODEL` | `"claude-opus-4.5"` | Default model |
| `DEFAULT_TIMEOUT` | `3600.0` | 1 hour timeout |
| `SDK_MAX_TURNS_DEFAULT` | `3` | Circuit breaker threshold |
| `SDK_MAX_TURNS_HARD_LIMIT` | `10` | Absolute maximum turns |
| `CLIENT_HEALTH_CHECK_TIMEOUT` | `5.0` | Health check timeout |
| `CLIENT_INIT_LOCK_TIMEOUT` | `30.0` | Lock acquisition timeout |
| `SDK_TIMEOUT_BUFFER_SECONDS` | `5.0` | Buffer for SDK timeout |
| `CACHE_STALE_DAYS` | `30` | Cache staleness threshold |
| `MAX_REPAIRED_TOOL_IDS` | `1000` | LRU eviction limit |
| `COPILOT_BUILTIN_TOOL_NAMES` | 27 tools | Built-in tool exclusion set |

---

## 7. TEST COVERAGE MAP

### Unit Tests (tests/)

| Test File | Module Tested | Coverage Focus |
|-----------|--------------|----------------|
| `test_provider.py` | `provider.py` | 5-method protocol, complete(), streaming, error handling |
| `test_client.py` | `client.py` | Session lifecycle, health checks, auth, error translation |
| `test_client_error_recovery.py` | `client.py` | Error recovery paths, dead subprocess detection |
| `test_converters.py` | `converters.py` | Message format conversion, tool call serialization |
| `test_models.py` | `models.py` | Model mapping, capability detection |
| `test_model_cache.py` | `model_cache.py` | Cache read/write, staleness, atomic writes |
| `test_model_cache_integration.py` | `model_cache.py` | Integration with provider initialization |
| `test_model_naming.py` | `model_naming.py` | ID parsing, thinking detection, validation |
| `test_sdk_driver.py` | `sdk_driver.py` | Loop control, tool capture, circuit breaker |
| `test_tool_capture.py` | `tool_capture.py` | Tool conversion, deny hook, deduplication |
| `test_exceptions.py` | `exceptions.py` | Exception hierarchy, rate-limit detection |
| `test_permissions.py` | `_permissions.py` | Execute permission handling |
| `test_platform.py` | `_platform.py` | Cross-platform binary location |
| `test_mount.py` | `__init__.py` | Mount/unmount, graceful degradation |
| `test_mount_coverage.py` | `__init__.py` | Additional mount edge cases |
| `test_streaming.py` | `provider.py` | Streaming-specific tests |
| `test_provider_streaming_edge.py` | `provider.py` | Streaming edge cases |
| `test_type_safety.py` | All | Type correctness assertions |
| `test_coverage_gaps.py` | Various | Coverage gap hunters |
| `test_user_facing_strings.py` | `_constants.py` | User-visible string validation |
| `test_verbosity_collapse.py` | Various | Log verbosity checks |

### SDK Assumption Tests (tests/sdk_assumptions/)

| Test File | What It Validates |
|-----------|-------------------|
| `test_deny_hook.py` | preToolUse deny hook behavior |
| `test_event_ordering.py` | Event fire order assumptions |
| `test_session_lifecycle.py` | Session create/disconnect lifecycle |
| `test_tool_registration.py` | Tool registration with SDK |

These are **boundary tests** that validate assumptions about SDK behavior. Must be run before upgrading past SDK 0.2.0.

### Integration Tests (tests/integration/)

| Test File | Scope |
|-----------|-------|
| `test_live_copilot.py` | Live SDK interaction |
| `test_live_sdk_driver.py` | Live SDK driver behavior |
| `test_regression_305_loop.py` | Regression: 305-turn loop bug |
| `test_forensic_regression.py` | Historical incident regression |
| `test_multi_model_saturation.py` | Multi-model concurrent load |
| `forensic_runner.py` | Test runner utility |

### What's NOT Tested (Gaps)

1. **`CopilotContentFilterError`** - Defined in `exceptions.py:293` but never raised in `provider.py`'s error translation. No test verifies it's actually used.

2. **`provider.py:_make_emit_callback()`** - Fire-and-forget event emission has no direct unit test for the `RuntimeError` path (no running loop).

3. **`model_cache.py` Windows path handling** - Atomic write uses `Path.replace()` which has different semantics on Windows, but no Windows-specific test.

4. **Concurrent singleton access** - `__init__.py` singleton uses `asyncio.Lock` but no test exercises concurrent `mount()` calls from multiple coroutines.

5. **`provider.py:_complete_streaming()` timeout with captured tools** - The path where timeout occurs but tools were already captured (lines 1244-1252) has a warning log but unclear if tested.

---

## 8. HIDDEN ASSUMPTIONS

### SDK Behavior Assumptions

1. **Event ordering**: `ASSISTANT_MESSAGE` events fire BEFORE `preToolUse` hook. If SDK changes this ordering, tool capture breaks. (`tool_capture.py:26-30`)

2. **Denial causes retry**: SDK's `denial_behavior = RETRY` causes the 305-turn loop issue. The entire SDK Driver exists because of this assumption. (`_constants.py:223`)

3. **`session.disconnect()` exists in SDK ≥0.1.32**: The code uses `disconnect()` instead of deprecated `destroy()`. (`client.py:600`)

4. **`overrides_built_in_tool` field exists**: Tool registration requires this field. (`tool_capture.py:159`)

5. **SDK returns `tool_requests` on `ASSISTANT_MESSAGE` data**: Tool capture depends on `data.tool_requests` attribute. (`sdk_driver.py:499`)

6. **`PermissionHandler.approve_all` exists in SDK ≥0.1.28**: Falls back gracefully if not available. (`client.py:559-568`)

### Amplifier Core Assumptions

1. **Provider protocol is 5 methods**: `name`, `get_info()`, `list_models()`, `complete()`, `parse_tool_calls()`.

2. **`ChatResponse` accepts `content`, `tool_calls`, `usage`, `finish_reason`**.

3. **`coordinator.hooks.emit()` is async and safe to call fire-and-forget**.

4. **`coordinator.mount("providers", provider, name=...)` is the registration API**.

5. **`retry_with_backoff()` catches `LLMError` subtypes and checks `retryable` flag**.

### Architecture Assumptions

1. **One Python process = one CLI subprocess**: The singleton pattern assumes all providers share one process. If Amplifier ever runs providers in separate processes, the singleton is useless.

2. **All sub-agents share the same event loop**: The singleton lock uses `asyncio.Lock` which is event-loop-bound. (`__init__.py:131`)

3. **Prompt serialization preserves context**: Converting messages to `Human:/Assistant:` format assumes the LLM can reconstruct multi-turn conversation from this format. No round-trip fidelity guarantee.

4. **System message is separate from prompt**: Copilot SDK handles system messages via session config `append` mode, not inline in the prompt. (`client.py:491-495`)

5. **Tool names are globally unique**: The SDK rejects duplicate names with a 400 error. (`tool_capture.py:142-146`)

6. **27 known built-in tools is complete**: `COPILOT_BUILTIN_TOOL_NAMES` is manually maintained. If SDK adds new built-ins, they won't be excluded. (`_constants.py:127-171`)

### Data Format Assumptions

1. **Model IDs use periods for versions**: `claude-opus-4.5`, not `claude-opus-4-5`. (`model_naming.py`)

2. **Thinking models contain "opus", "gpt-5", "o1", "o3", "o4", "-thinking", or "-reasoning" in ID**: Used as fallback when SDK capability check fails. (`model_naming.py:129-139`)

3. **`max_output_tokens = context_window - max_prompt_tokens`**: Derived from SDK limits. If SDK changes this formula, budget calculation breaks. (`models.py:96`)

---

## 9. DEPENDENCY ANALYSIS

### External Dependencies

```
github-copilot-sdk>=0.1.32,<0.2.0  (pinned range)
amplifier-core                       (provided by runtime)
```

### Internal Dependency Graph (imports)

```
__init__.py
  └── client.py
  │     └── _constants.py
  │     └── _platform.py
  │     └── _permissions.py
  │     └── exceptions.py
  └── provider.py
  │     └── client.py
  │     └── converters.py
  │     │     └── amplifier_core
  │     └── exceptions.py
  │     └── model_cache.py
  │     │     └── _constants.py
  │     └── model_naming.py
  │     └── models.py
  │     │     └── _constants.py
  │     │     └── client.py
  │     │     └── amplifier_core.ModelInfo
  │     └── tool_capture.py
  │     │     └── _constants.py
  │     │     └── copilot.types.Tool
  │     └── sdk_driver.py
  │     │     └── _constants.py
  │     │     └── exceptions.py
  │     └── amplifier_core (ChatResponse, ProviderInfo, etc.)
  │     └── amplifier_core.llm_errors (Kernel error types)
  │     └── amplifier_core.utils (redact_secrets, retry_with_backoff)
```

---

## 10. KEY ARCHITECTURAL INSIGHTS

### The "Deny + Destroy" Pattern Is Central

The entire architecture revolves around using the Copilot SDK in a way it wasn't designed for. The SDK is built for **agentic workflows** where tools execute inside the CLI process. This provider **subverts** that by:

1. Registering tools with no-op handlers
2. Denying all tool execution via `preToolUse` hook
3. Capturing tool requests from streaming events
4. Destroying the session to stop the CLI's retry loop
5. Returning captured tool calls to Amplifier's orchestrator

This is fragile because it depends on undocumented SDK internals (event ordering, denial behavior). The SDK assumption tests exist specifically to catch breakage.

### The SDK Driver Solves a Real Problem

The 305-turn, 607-tool accumulation bug (Session a1a0af17) is well-documented. The SDK Driver with first-turn-only capture + circuit breaker is an elegant solution to an agentic SDK's retry behavior. However, the `SDK_MAX_TURNS_DEFAULT = 3` means ANY legitimate multi-turn SDK behavior would trip the breaker.

### Model Cache Is Over-Engineered for Its Purpose

Four tiers of fallback (memory → disk → bundled → defaults) with atomic writes, staleness detection, and format versioning for what is essentially a small JSON file of model limits. The `BUNDLED_MODEL_LIMITS` dict already handles 21 models. The disk cache adds complexity for marginal benefit (avoiding one `list_models()` API call per session).

### Error Translation Is Comprehensive but Has Gaps

The error translation in `provider.py:976-1049` maps 8 domain exceptions to kernel exceptions, with a catch-all that also detects rate limits. However:
- `CopilotContentFilterError` is defined but never raised in the translation layer
- The catch-all `detect_rate_limit_error()` on line 1028 could mask other errors

### The Fake Tool Call Detection Is a Symptom

The fact that fake tool call detection with retry exists (lines 1076-1138) suggests the prompt format (`<tool_used>` XML tags) teaches the model to write tool calls as text. This is a format design issue, not just a detection problem.

---

## 11. OPPORTUNITIES FOR IMPROVEMENT

1. **Use SDK's official capture-only mode when available** (mentioned in `tool_capture.py:33-36`)
2. **Wire up `CopilotContentFilterError`** in the error translation layer
3. **Simplify model cache** - the bundled limits are sufficient for most cases
4. **Add Windows CI** for atomic write and platform detection tests
5. **Test concurrent singleton access** with multiple coroutines
6. **Consider structured prompt format** instead of `Human:/Assistant:` text serialization
7. **Monitor SDK version for `denial_behavior` changes** that could eliminate the need for SDK Driver
8. **Add telemetry for fake tool call frequency** to quantify the format issue

---

## 12. SDK DOCUMENTATION KEY INSIGHTS

From the Copilot SDK docs:

- **`session.on(handler)`** returns an unsubscribe function (used correctly in `provider.py:1231,1347`)
- **`streaming: True`** enables delta events (`ASSISTANT_MESSAGE_DELTA`, `ASSISTANT_REASONING_DELTA`)
- **`reasoning_effort`** is a session config option, not a per-message option
- **`excluded_tools`** is IGNORED if `available_tools` is set (noted in `client.py:514-517`)
- **`infinite_sessions: {enabled: False}`** disables SDK's session persistence (used in `client.py:506`)
- **`system_message: {mode: "append", content: ...}`** appends to default system message
- **`cli_url`** option allows connecting to external CLI server (not currently used by provider)

---

*End of Exploration Report*
