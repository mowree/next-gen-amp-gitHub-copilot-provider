# GitHub Copilot Provider — Phase 1 Design

## Goal

Wire the existing provider scaffold (Phase 0) to the real GitHub Copilot SDK with defense-in-depth sovereignty over tool execution. Target: ~200 lines of new Python code.

## Background

### The Critical Discovery

The expert panel discovered that SDK-registered tools (`SessionConfig.tools`) bypass hooks entirely. This means:

1. We MUST never register tools via SDK
2. We MUST test empirically that hooks fire
3. The `on_post_tool_use` hook is CRITICAL, not just defensive

### Phase 0 (Complete)

9 features implemented. 7 pyright errors pending fix.

## Approach: Three-Medium Architecture Alignment

- **Python:** ~200 lines of mechanism code
- **YAML:** Keep `config/errors.yaml`, `config/events.yaml`, `config/retry.yaml` (existing)
- **Markdown:** Contracts drive tests and AI implementation

## Architecture

### Defense-in-Depth Layers

| Layer | Mechanism | What It Stops |
|-------|-----------|---------------|
| 1 | Empty `tools=[]`, `mcp_servers=[]` | SDK-registered tools (bypass hooks) |
| 2 | `on_pre_tool_use` → deny | All tool execution requests |
| 3 | `on_post_tool_use` → canary | Catches hook bypass / SDK bugs |
| 4 | Session abort + disconnect | Kills server-side loop on breach |

### Phase Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 0 | Foundation (9 features) | ✅ Complete |
| Phase 1 | SDK Wiring + Sovereignty (~200 lines) | **This design** |
| Phase 2 | Sovereignty Verification + Hooks Ecosystem | Future |
| Phase 3 | SDK Evolution Resilience | Future |

## Components

### F-010: SDK Integration (~95 lines)

**Files to Modify:**

| File | Action | Lines |
|------|--------|-------|
| `sdk_adapter/driver.py` | Modify | ~80 (replace `NotImplementedError` stubs + singleton) |
| `session_factory.py` | Modify | ~15 (add hooks) |

**Module-level singleton in driver.py:**

```python
_client: CopilotClient | None = None
_client_lock = asyncio.Lock()

async def _get_client() -> CopilotClient:
    global _client
    async with _client_lock:
        if _client is None:
            _client = CopilotClient()
            await _client.start()
        return _client
```

**Deny hook + breach detector in session_factory.py:**

```python
DENY_ALL = {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Amplifier sovereignty",
}

def _create_deny_hook():
    async def deny(input_data, invocation):
        try:
            return DENY_ALL
        except Exception:
            return DENY_ALL  # NEVER return None
    return deny

def _create_breach_detector(on_breach):
    async def detect(input_data, invocation):
        on_breach(input_data["toolName"])
        return {"modifiedResult": "REDACTED", "suppressOutput": True}
    return detect
```

**Session creation:**

```python
session = await client.create_session({
    "model": config.model,
    "hooks": {
        "on_pre_tool_use": _create_deny_hook(),
        "on_post_tool_use": _create_breach_detector(_handle_breach),
    },
    "tools": [],  # NEVER register SDK tools — they bypass hooks
})
```

**Auth:** Uses `GITHUB_TOKEN` (or `GH_TOKEN`, `COPILOT_GITHUB_TOKEN`).

**Eliminated (not needed):**

- ~~LoopController class~~ — SDK loop is server-side
- ~~ToolCaptureStrategy class~~ — 5 lines in deny hook
- ~~EventRouter class~~ — already have `translate_event()`
- ~~sdk_adapter/client.py~~ — singleton lives in driver.py

---

### F-015: Completion Wiring (~50 lines changed)

**Files to Modify:**

| File | Action | Lines Changed |
|------|--------|---------------|
| `completion.py` | Modify | ~40 (remove `sdk_create_fn` injection, wire to driver.py) |
| `session_factory.py` | Modify | ~10 (use hooks in `create_ephemeral_session`) |

**Key changes:**

- Remove `sdk_create_fn` injection parameter (testing cruft)
- Wire directly to `create_ephemeral_session()`
- Tests mock at `driver.py` level (the SDK boundary), not `completion.py`

**Reused without changes:**

- `streaming.py` — `translate_event()` already exists
- `error_translation.py` — config-driven error mapping
- `config/events.yaml` — event classification

---

### F-016: E2E Verification (~50 lines)

**Files to Create:**

| File | Action | Lines |
|------|--------|-------|
| `tests/test_e2e_hooks.py` | Create | ~50 |

**Test cases:**

1. **`test_simple_completion`** (~10 lines)
   - Happy path — validates SDK wiring works
   - Catches auth/connection issues early
   - Runs first to gate other tests

2. **`test_deny_hook_fires`** (~20 lines)
   - Empirically verify `on_pre_tool_use` is called
   - Probabilistic: if LLM doesn't request a tool, test skips via `pytest.skip()` (not fails)
   - 30-second timeout (generous for API latency)
   - Passes if hook fired, even if completion doesn't finish

3. **`test_deny_blocks_execution`** (~20 lines)
   - Canary: `on_post_tool_use` should NEVER fire if deny works
   - If it fires, sovereignty breach detected

**CI safeguard:**

- Run E2E tests 5 times per CI job
- If ALL 5 runs skip, fail with warning: "Unable to verify hooks — no tool calls triggered in 5 runs"
- Catches the case where prompts stop triggering tools or SDK behavior changes

## Data Flow

```
User Request
  → completion.py (remove sdk_create_fn, call create_ephemeral_session)
    → session_factory.py (hooks: deny + breach detector, tools=[])
      → driver.py (_get_client singleton → CopilotClient)
        → SDK (server-side loop)
          ← SDK events
        ← translate_event() (streaming.py, existing)
      ← DomainEvent stream
    ← error_translation.py (config-driven)
  ← Response to user
```

## Error Handling

| Error | Translation | Source |
|-------|-------------|--------|
| No `GITHUB_TOKEN` | Clear error message with instructions | driver.py |
| Invalid token | `AuthenticationError(provider="github-copilot")` | driver.py |
| `ProcessExitedError` | `NetworkError` | error_translation.py |
| Timeout | `LLMTimeoutError` | error_translation.py |
| Rate limit | `RateLimitError` (with `retry_after`) | error_translation.py |

All errors translated via `config/errors.yaml`.

## Testing Strategy

**Unit tests (existing):**

- Mock at `driver.py` level (SDK boundary)
- Test error translation paths
- Test event translation paths

**E2E tests (F-016, new):**

- Real SDK calls with `GITHUB_TOKEN`
- Verify hooks fire empirically
- Tests skip gracefully without token
- Runtime `pytest.skip()` for probabilistic tool triggering

**CI safeguard:**

- Multiple runs to catch 100% skip rate
- Fail CI if hooks can never be verified

## Open Questions (Deferred to Later Phases)

1. **SDK hooks wiring:** Explorer found `session.py:_execute_tool_and_respond()` doesn't call hooks. Need empirical verification (F-016).

2. **Tool discovery:** 28 known tools, more may exist. Deferred to Phase 2 (F-017).

3. **Event vocabulary:** `events.yaml` uses `text_delta` but SDK uses `assistant.message_delta`. Reconciliation deferred to Phase 2.

## Line Count Summary

| Feature | New Lines | Changed Lines |
|---------|-----------|---------------|
| F-010 | ~95 | — |
| F-015 | — | ~50 |
| F-016 | ~50 | — |
| **Total** | **~145 new** | **~50 changed** |

Target: ~200 lines. Actual: ~195 lines. ✅

## Blockers Before Phase 1

1. Fix 7 pyright errors from Phase 0
2. Verify `GITHUB_TOKEN` available for E2E tests
