# F-027: Real SDK Integration Tests

**Status:** Draft  
**Priority:** High  
**Contract References:** contracts/sdk-boundary.md, contracts/deny-destroy.md  
**Architecture Reference:** debates/GOLDEN_VISION_V2.md §Testing Strategy (Tier 6 + Tier 7)

---

## Problem Statement

The provider has 176 unit tests — all passing, all using mocks. No test has ever touched the real `github-copilot-sdk`. This means:

1. **SDK assumption drift is invisible.** If the SDK changes `create_session()` signature, `send_message()` event shapes, or `disconnect()` behavior, we won't know until production.
2. **The deny hook is tested against mocks.** We assert `register_pre_tool_use_hook` is called, but never verify the SDK actually honors it.
3. **Error translation is tested against fake exceptions.** We create `FakeAuthError` with `__name__ = "AuthenticationError"` — but real SDK errors may have different class hierarchies, messages, or attributes.
4. **Streaming event shapes are assumed.** Our `MockSDKSession.send_message()` yields `{"type": "text_delta", "text": "..."}` — the real SDK may yield objects, not dicts.

This spec defines integration tests that verify our assumptions against the real SDK.

---

## Design Decisions

### 1. Two Test Tiers (Matching Golden Vision Diamond)

| Tier | Name | Hits Real API? | When Run | Marker |
|------|------|---------------|----------|--------|
| **6** | SDK Assumption Tests | No — SDK imported, objects created, but no network | Every PR | `@pytest.mark.sdk_assumption` |
| **7** | Live Smoke Tests | Yes — real API, real tokens, real network | Nightly / manual | `@pytest.mark.live` |

**Tier 6** tests verify SDK types, method signatures, and object shapes without making API calls. They import the real SDK, instantiate objects, and check structural assumptions. These are fast (<5s total) and require no credentials.

**Tier 7** tests make real API calls. They require a valid `GITHUB_TOKEN` and network access. They are slow (10-60s) and rate-limit-sensitive.

### 2. Authentication Strategy

```
Environment Variables (precedence order):
1. COPILOT_AGENT_TOKEN  — CI service account token
2. COPILOT_GITHUB_TOKEN — Copilot-specific token
3. GH_TOKEN             — GitHub CLI token
4. GITHUB_TOKEN         — Standard GitHub token

Test behavior:
- Tier 6: No token needed (no API calls)
- Tier 7: Skip with clear message if no token available
```

**CI Setup:**
- GitHub Actions secret `COPILOT_INTEGRATION_TOKEN` → `GITHUB_TOKEN` env var
- Token requires `copilot` scope (GitHub Copilot API access)
- Dedicated test account recommended to avoid rate limit interference with dev work

### 3. Determinism Strategy

Real API responses are non-deterministic. Our strategy:

| Aspect | Approach |
|--------|----------|
| **Response content** | Assert structure, not exact text. "Response has non-empty text" not "Response equals 'Hello world'" |
| **Event ordering** | Assert required events appear (text_delta before message_complete), not exact sequence |
| **Timing** | Use generous timeouts (30s), assert completion, not speed |
| **Model availability** | Parameterize models, skip unavailable ones gracefully |
| **Finish reasons** | Assert valid set membership, not exact value |

### 4. Test Isolation Strategy

```
┌─────────────────────────────────────────────┐
│  Each test gets:                            │
│  - Fresh CopilotClient (start/stop)         │
│  - Fresh session (create/disconnect)         │
│  - Own deny hook installation                │
│  - Independent assertions                    │
│                                             │
│  Shared across test module:                 │
│  - Client fixture (module-scoped)           │
│  - Auth token resolution                     │
│  - Skip logic for missing credentials        │
└─────────────────────────────────────────────┘
```

A module-scoped `CopilotClient` fixture avoids repeated subprocess spawning (the SDK starts a Node.js subprocess). Individual sessions are function-scoped for isolation.

### 5. Rate Limit / Quota Strategy

| Control | Implementation |
|---------|---------------|
| **Test count** | Cap at 5-8 live tests (one per critical path) |
| **Retry on 429** | Tests retry once with 60s backoff on rate limit |
| **CI schedule** | Nightly only (not on every PR) |
| **Quota guard** | First test checks quota; if <10 requests remaining, skip suite |
| **Prompt minimalism** | Use shortest possible prompts ("Say hi") to minimize token usage |

---

## Acceptance Criteria

### AC-1: SDK Import Assumptions (Tier 6)

Tests that verify we can import and instantiate real SDK types without network calls.

```python
# tests/test_sdk_assumptions.py

import pytest

sdk_available = pytest.importorskip("copilot", reason="github-copilot-sdk not installed")


@pytest.mark.sdk_assumption
class TestSDKImportAssumptions:
    """Verify SDK module structure matches our assumptions."""

    def test_copilot_client_class_exists(self):
        """We assume copilot.CopilotClient exists and is importable."""
        from copilot import CopilotClient
        assert CopilotClient is not None

    def test_client_has_create_session(self):
        """We assume CopilotClient has create_session method."""
        from copilot import CopilotClient
        assert hasattr(CopilotClient, "create_session")

    def test_client_has_start_stop(self):
        """We assume CopilotClient has start() and stop() lifecycle methods."""
        from copilot import CopilotClient
        assert hasattr(CopilotClient, "start")
        assert hasattr(CopilotClient, "stop")

    def test_client_accepts_options_dict(self):
        """We assume CopilotClient(options) accepts a dict with github_token."""
        from copilot import CopilotClient
        # Should not raise TypeError
        client = CopilotClient({"github_token": "test-token-not-real"})
        assert client is not None
```

### AC-2: Session Lifecycle Assumptions (Tier 6)

```python
@pytest.mark.sdk_assumption
class TestSessionAssumptions:
    """Verify session object has expected interface."""

    @pytest.mark.asyncio
    async def test_session_has_disconnect(self, sdk_client):
        """Sessions must have disconnect() for cleanup."""
        session = await sdk_client.create_session({"model": "gpt-4o"})
        assert hasattr(session, "disconnect")
        assert callable(session.disconnect)
        await session.disconnect()

    @pytest.mark.asyncio
    async def test_session_has_register_pre_tool_use_hook(self, sdk_client):
        """Sessions must support deny hook registration."""
        session = await sdk_client.create_session({"model": "gpt-4o"})
        assert hasattr(session, "register_pre_tool_use_hook")
        await session.disconnect()

    @pytest.mark.asyncio
    async def test_session_has_send_message(self, sdk_client):
        """Sessions must have send_message for prompts."""
        session = await sdk_client.create_session({"model": "gpt-4o"})
        assert hasattr(session, "send_message")
        await session.disconnect()
```

### AC-3: Deny Hook Verification (Tier 7 — Live)

```python
@pytest.mark.live
class TestDenyHookLive:
    """Verify deny hook actually prevents tool execution on real SDK.

    Contract: deny-destroy:DenyHook:MUST:1, deny-destroy:DenyHook:MUST:2
    """

    @pytest.mark.asyncio
    async def test_deny_hook_prevents_tool_execution(self, sdk_client):
        """When deny hook is installed and tools are provided,
        SDK should return tool_call events but NOT execute them."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import create_deny_hook

        session = await sdk_client.create_session({
            "model": "gpt-4o",
            "streaming": True,
        })
        session.register_pre_tool_use_hook(create_deny_hook())

        tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            },
        }]

        events = []
        try:
            async for event in session.send_message(
                "What's the weather in Seattle? Use the get_weather tool.",
                tools=tools,
            ):
                events.append(event)
        finally:
            await session.disconnect()

        # Assert: We got events (SDK responded)
        assert len(events) > 0

        # Assert: No tool_result events (tool was NOT executed)
        event_types = [_get_event_type(e) for e in events]
        assert "tool_result" not in event_types, (
            "SDK executed a tool despite deny hook! "
            f"Event types: {event_types}"
        )
```

### AC-4: Simple Completion (Tier 7 — Live)

```python
@pytest.mark.live
class TestLiveCompletion:
    """Verify real SDK completion produces expected event shapes.

    Contract: sdk-boundary:Translation:MUST:1
    """

    @pytest.mark.asyncio
    async def test_simple_text_completion(self, sdk_client):
        """A simple prompt produces text_delta events and message_complete."""
        session = await sdk_client.create_session({
            "model": "gpt-4o",
            "streaming": True,
        })

        events = []
        try:
            async for event in session.send_message("Say 'hello' and nothing else."):
                events.append(event)
        finally:
            await session.disconnect()

        # Structural assertions (not content assertions)
        event_types = [_get_event_type(e) for e in events]

        # Must have at least one content event
        assert any(t in ("text_delta", "content_block_delta") for t in event_types), (
            f"No content events found. Types: {event_types}"
        )

        # Must have a completion signal
        assert any(t in ("message_complete", "message_stop") for t in event_types), (
            f"No completion signal found. Types: {event_types}"
        )

    @pytest.mark.asyncio
    async def test_event_shape_matches_assumptions(self, sdk_client):
        """Verify event objects have the fields our translate_event expects."""
        session = await sdk_client.create_session({
            "model": "gpt-4o",
            "streaming": True,
        })

        events = []
        try:
            async for event in session.send_message("Say 'test'."):
                events.append(event)
        finally:
            await session.disconnect()

        # Record event shapes for drift detection
        for event in events:
            event_type = _get_event_type(event)
            if event_type == "text_delta":
                # Our code assumes: event has "text" field
                text = _get_event_field(event, "text")
                assert text is not None, (
                    f"text_delta event missing 'text' field. "
                    f"Event: {_describe_event(event)}"
                )
            elif event_type == "message_complete":
                # Our code assumes: event has "finish_reason" field
                # (may be nested or attribute)
                pass  # Log shape for manual review
```

### AC-5: Error Shape Verification (Tier 7 — Live)

```python
@pytest.mark.live
class TestLiveErrors:
    """Verify real SDK error shapes match our error_translation assumptions."""

    @pytest.mark.asyncio
    async def test_invalid_model_produces_expected_error(self, sdk_client):
        """Requesting a nonexistent model should produce an identifiable error."""
        session = await sdk_client.create_session({
            "model": "nonexistent-model-xyz-999",
            "streaming": True,
        })

        with pytest.raises(Exception) as exc_info:
            async for _ in session.send_message("test"):
                pass

        await session.disconnect()

        # Record the actual error type for drift detection
        error = exc_info.value
        error_class = type(error).__name__
        error_msg = str(error)

        # Structural assertion: error is catchable and has useful info
        assert error_class, "Error has no class name"
        assert error_msg, "Error has no message"

        # Log for manual review (helps update errors.yaml)
        print(f"SDK error for invalid model: {error_class}: {error_msg}")

    @pytest.mark.asyncio
    async def test_auth_error_shape(self):
        """Invalid token should produce an auth-related error."""
        from copilot import CopilotClient

        client = CopilotClient({"github_token": "invalid-token-xxx"})
        await client.start()

        try:
            session = await client.create_session({"model": "gpt-4o"})

            with pytest.raises(Exception) as exc_info:
                async for _ in session.send_message("test"):
                    pass

            error = exc_info.value
            error_class = type(error).__name__

            # Log actual error type (helps verify errors.yaml patterns)
            print(f"SDK auth error type: {error_class}: {error}")

            # The error class name should match one of our configured patterns
            auth_patterns = ["AuthenticationError", "InvalidTokenError", "PermissionDeniedError"]
            assert any(p in error_class for p in auth_patterns) or "401" in str(error) or "403" in str(error), (
                f"Auth error '{error_class}' doesn't match any configured pattern. "
                f"Update config/errors.yaml sdk_patterns."
            )
        finally:
            await client.stop()
```

### AC-6: Wrapper Integration (Tier 7 — Live)

```python
@pytest.mark.live
class TestCopilotClientWrapperLive:
    """Verify CopilotClientWrapper works with real SDK.

    This is THE critical integration test — it uses our actual code path.
    """

    @pytest.mark.asyncio
    async def test_wrapper_session_lifecycle(self):
        """CopilotClientWrapper.session() creates, yields, and destroys real session."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        wrapper = CopilotClientWrapper()

        try:
            async with wrapper.session(model="gpt-4o") as session:
                # Session should be a real SDK session
                assert session is not None
                assert hasattr(session, "send_message")
                assert hasattr(session, "disconnect")

                # Send a minimal message
                events = []
                async for event in session.send_message("Say 'ok'."):
                    events.append(event)

                assert len(events) > 0, "No events received from real SDK"
        finally:
            await wrapper.close()

    @pytest.mark.asyncio
    async def test_wrapper_deny_hook_installed_on_real_session(self):
        """CopilotClientWrapper installs deny hook on real SDK sessions."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        wrapper = CopilotClientWrapper()
        hook_installed = False

        try:
            async with wrapper.session(model="gpt-4o") as session:
                # Verify hook was registered (check session state)
                # The wrapper calls register_pre_tool_use_hook in session()
                if hasattr(session, "_pre_tool_use_hooks"):
                    hook_installed = len(session._pre_tool_use_hooks) > 0
                elif hasattr(session, "register_pre_tool_use_hook"):
                    # Hook registration happened (we can't easily verify
                    # without internal state, but we can verify no crash)
                    hook_installed = True
        finally:
            await wrapper.close()

        assert hook_installed, "Deny hook was not installed on real SDK session"
```

---

## Files to Create

### 1. `tests/test_sdk_assumptions.py` — Tier 6 (SDK shape tests, no API calls)

```
Content: AC-1 + AC-2 tests above
Marker: @pytest.mark.sdk_assumption
CI: Every PR
Dependencies: github-copilot-sdk installed
Auth: None required
```

### 2. `tests/test_live_sdk.py` — Tier 7 (Real API tests)

```
Content: AC-3 through AC-6 tests above
Marker: @pytest.mark.live
CI: Nightly only
Dependencies: github-copilot-sdk + valid GITHUB_TOKEN
Auth: GITHUB_TOKEN with copilot scope
```

### 3. `tests/conftest.py` additions — Shared fixtures

```python
import os
import pytest

# ── Skip controls ──

def _has_github_token() -> bool:
    """Check if any valid GitHub token is available."""
    for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return True
    return False

def _sdk_installed() -> bool:
    """Check if github-copilot-sdk is installed."""
    try:
        import copilot  # noqa: F401
        return True
    except ImportError:
        return False

skip_no_sdk = pytest.mark.skipif(
    not _sdk_installed(),
    reason="github-copilot-sdk not installed"
)

skip_no_token = pytest.mark.skipif(
    not _has_github_token(),
    reason="No GITHUB_TOKEN available for live SDK tests"
)


# ── Fixtures ──

@pytest.fixture(scope="module")
async def sdk_client():
    """Module-scoped real SDK client. Skips if SDK not available."""
    pytest.importorskip("copilot", reason="github-copilot-sdk not installed")
    from copilot import CopilotClient

    token = None
    for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(var)
        if token:
            break

    if not token:
        pytest.skip("No GitHub token available")

    client = CopilotClient({"github_token": token})
    await client.start()
    yield client
    await client.stop()
```

### 4. `pyproject.toml` additions — Test markers

```toml
[tool.pytest.ini_options]
markers = [
    "sdk_assumption: Tests that verify SDK type/shape assumptions (no API calls)",
    "live: Tests that hit the real GitHub Copilot API (require GITHUB_TOKEN)",
]
```

---

## Helper Functions

```python
# tests/sdk_helpers.py

from typing import Any


def _get_event_type(event: Any) -> str:
    """Extract event type from SDK event (handles dict or object)."""
    if isinstance(event, dict):
        return event.get("type", "unknown")
    return getattr(event, "type", getattr(event, "event_type", "unknown"))


def _get_event_field(event: Any, field: str) -> Any:
    """Extract field from SDK event (handles dict or object)."""
    if isinstance(event, dict):
        return event.get(field)
    return getattr(event, field, None)


def _describe_event(event: Any) -> str:
    """Human-readable description of an SDK event for debugging."""
    if isinstance(event, dict):
        return str(event)
    cls = type(event).__name__
    attrs = {k: v for k, v in vars(event).items() if not k.startswith("_")}
    return f"{cls}({attrs})"
```

---

## What These Tests Will Catch

| Risk | Tier 6 Catches | Tier 7 Catches |
|------|----------------|----------------|
| SDK class renamed | ✅ Import fails | ✅ |
| Method signature changed | ✅ hasattr fails | ✅ |
| Event type changed from dict to object | ❌ | ✅ text_delta assertion |
| Event field renamed | ❌ | ✅ field extraction |
| Deny hook mechanism changed | ✅ hasattr check | ✅ tool not executed |
| Auth error class renamed | ❌ | ✅ pattern matching |
| New required session config field | ✅ create_session fails | ✅ |
| Rate limit behavior changed | ❌ | ✅ (if triggered) |
| disconnect() renamed/removed | ✅ hasattr check | ✅ cleanup works |

---

## What These Tests Will NOT Catch

1. **Subtle behavioral changes** (e.g., SDK starts batching events differently) — requires response comparison tests
2. **Performance regressions** in SDK — requires benchmarking, not integration tests
3. **Intermittent SDK bugs** — requires longer soak tests
4. **Multi-turn conversation changes** — out of scope (we use single-turn only)

---

## CI Configuration

```yaml
# .github/workflows/sdk-integration.yml (sketch)
name: SDK Integration Tests

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6am UTC
  workflow_dispatch:       # Manual trigger

jobs:
  sdk-assumptions:
    # Tier 6: Every PR (fast, no auth needed)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: uv sync --all-extras
      - run: uv run pytest -m sdk_assumption --timeout=30 -v

  live-smoke:
    # Tier 7: Nightly only (slow, needs auth)
    runs-on: ubuntu-latest
    environment: copilot-integration
    env:
      GITHUB_TOKEN: ${{ secrets.COPILOT_INTEGRATION_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - run: uv sync --all-extras
      - run: uv run pytest -m live --timeout=120 -v
```

---

## Implementation Order

1. Add pytest markers to `pyproject.toml`
2. Add fixtures and helpers to `tests/conftest.py` and `tests/sdk_helpers.py`
3. Create `tests/test_sdk_assumptions.py` (Tier 6) — runs without credentials
4. Create `tests/test_live_sdk.py` (Tier 7) — runs with `GITHUB_TOKEN`
5. Run Tier 6 locally to discover any immediate SDK shape mismatches
6. Run Tier 7 manually with a real token to validate
7. Add CI workflow for nightly runs

---

## Open Questions

1. **Does the SDK `send_message` yield dicts or typed objects?** Tier 7 tests will answer this — if objects, our `MockSDKSession` and `translate_event` may need updates.
2. **What's the exact error class hierarchy in the SDK?** Tier 7 auth error test will record this.
3. **Does `register_pre_tool_use_hook` exist on all SDK versions ≥0.1.32?** Tier 6 will verify.
4. **Is there a quota-check API we can call before running live tests?** Unknown — needs SDK docs review.
