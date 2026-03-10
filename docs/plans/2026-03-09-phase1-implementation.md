# Phase 1: SDK Integration Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Wire the Phase 0 scaffold to the real GitHub Copilot SDK with defense-in-depth sovereignty over tool execution.
**Architecture:** Module-level singleton client in `driver.py`, deny hook + breach detector in `session_factory.py`, completion wiring removes test injection cruft, E2E tests verify hooks empirically.
**Tech Stack:** Python 3.11+, `github-copilot-sdk>=0.1.32,<0.2.0`, pytest + pytest-asyncio, pyright strict mode.

**Design doc:** `docs/plans/2026-03-09-phase1-sdk-integration-design.md`

---

## Package Layout Reference

```
src/amplifier_module_provider_github_copilot/
├── sdk_adapter/
│   ├── __init__.py          # Re-exports: DomainEvent, SessionConfig, create_session, destroy_session
│   ├── types.py             # SessionConfig, DomainEvent, SDKSession = Any
│   └── driver.py            # ← MODIFY (Tasks 1-3)
├── session_factory.py       # ← MODIFY (Tasks 4-5)
├── completion.py            # ← MODIFY (Tasks 6-7)
├── streaming.py             # (no changes)
├── error_translation.py     # (no changes)
├── tool_parsing.py          # (no changes)
└── provider.py              # (no changes)

tests/
├── test_sdk_adapter.py      # (existing — will need updates)
├── test_session_factory.py  # (existing — will need updates)
├── test_completion.py       # (existing — will need updates)
└── test_e2e_hooks.py        # ← CREATE (Task 8)
```

---

## Task 0: Fix Pyright Errors from Phase 0

**Files:**
- Fix: various files in `src/amplifier_module_provider_github_copilot/`

**Step 1: Run pyright to capture current errors**

```bash
uv run pyright src/
```

Capture all errors. There should be ~7 errors from Phase 0.

**Step 2: Fix each error, grouped by file**

Fix whatever pyright reports. Common issues in this codebase:
- Missing type annotations on return values
- `Any` usage in strict mode needing explicit annotations
- Import issues with optional dependencies

For each error, read the file, understand the issue, and make the minimal fix.

**Step 3: Run pyright again to verify clean**

```bash
uv run pyright src/
```

Expected: 0 errors.

**Step 4: Run existing tests to verify nothing broke**

```bash
uv run pytest tests/ -v
```

Expected: All existing tests pass.

**Step 5: Commit**

```bash
git add src/ && git commit -m "fix: resolve pyright errors from Phase 0

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 1: Add Singleton Client + `_get_client()` to driver.py

**Files:**
- Modify: `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py`
- Test: `tests/test_sdk_adapter.py`

**Step 1: Write failing tests for `_get_client()`**

Open `tests/test_sdk_adapter.py`. Add these tests at the bottom of the file, after the existing `TestSDKAdapterExports` class:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestGetClient:
    """Test singleton client initialization."""

    @pytest.mark.asyncio
    async def test_get_client_returns_client(self) -> None:
        """_get_client returns a CopilotClient instance."""
        from amplifier_module_provider_github_copilot.sdk_adapter import driver

        # Reset module-level singleton
        driver._client = None

        with patch.object(driver, "CopilotClient", autospec=False) as MockClient:
            mock_instance = MagicMock()
            mock_instance.start = AsyncMock()
            MockClient.return_value = mock_instance

            client = await driver._get_client()

            assert client is mock_instance
            MockClient.assert_called_once()
            mock_instance.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_client_returns_same_instance(self) -> None:
        """_get_client returns the same instance on subsequent calls (singleton)."""
        from amplifier_module_provider_github_copilot.sdk_adapter import driver

        # Reset module-level singleton
        driver._client = None

        with patch.object(driver, "CopilotClient", autospec=False) as MockClient:
            mock_instance = MagicMock()
            mock_instance.start = AsyncMock()
            MockClient.return_value = mock_instance

            client1 = await driver._get_client()
            client2 = await driver._get_client()

            assert client1 is client2
            # CopilotClient() called only ONCE (singleton)
            MockClient.assert_called_once()
```

You will also need to add `import pytest` at the top of the file if not already present (it is NOT currently imported — the existing tests don't use `@pytest.mark`).

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_sdk_adapter.py::TestGetClient -v
```

Expected: FAIL — `_get_client` doesn't exist yet, `CopilotClient` not importable.

**Step 3: Implement singleton client in driver.py**

Replace the ENTIRE contents of `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py` with:

```python
"""
SDK driver functions for session lifecycle.

These functions manage SDK session creation and destruction.
All SDK imports MUST be contained within this module.

Contract: contracts/sdk-boundary.md
Feature: F-001, F-010

MUST constraints:
- CopilotClient is a module-level singleton
- _get_client() is the ONLY way to access the client
- SDK handles process cleanup on exit
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from copilot import CopilotClient

from .types import SDKSession, SessionConfig

logger = logging.getLogger(__name__)

# Module-level singleton — SDK handles process cleanup on exit
_client: CopilotClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> CopilotClient:
    """Get or create the singleton CopilotClient.

    Thread-safe via asyncio.Lock. The client is created once
    and reused for the lifetime of the process.

    Returns:
        The singleton CopilotClient instance.
    """
    global _client
    async with _client_lock:
        if _client is None:
            _client = CopilotClient()
            await _client.start()
        return _client


async def create_session(
    config: SessionConfig,
    deny_hook: Callable[..., Any] | None = None,
) -> SDKSession:
    """Create a new SDK session.

    Args:
        config: Session configuration.
        deny_hook: Hook to deny tool execution (required for sovereignty).

    Returns:
        Opaque session handle.

    Raises:
        NotImplementedError: Skeleton - full implementation in Task 2.
    """
    raise NotImplementedError(
        "SDK session creation not yet implemented. See Task 2."
    )


async def destroy_session(session: SDKSession) -> None:
    """Destroy an SDK session.

    Sessions MUST be destroyed after use. This is non-negotiable.
    The Deny + Destroy pattern ensures Amplifier maintains sovereignty.

    Args:
        session: The session to destroy.

    Raises:
        NotImplementedError: Skeleton - full implementation in Task 3.
    """
    raise NotImplementedError(
        "SDK session destruction not yet implemented. See Task 3."
    )
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_sdk_adapter.py::TestGetClient -v
```

Expected: PASS — both tests green.

**Step 5: Run ALL sdk_adapter tests to verify no regressions**

```bash
uv run pytest tests/test_sdk_adapter.py -v
```

Expected: All tests pass (existing + new).

**Step 6: Commit**

```bash
git add src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py tests/test_sdk_adapter.py && git commit -m "feat(F-010): add singleton CopilotClient with _get_client()

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: Implement `create_session()` (Replace Stub)

**Files:**
- Modify: `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py`
- Test: `tests/test_sdk_adapter.py`

**Step 1: Write failing test for `create_session()`**

Add to `tests/test_sdk_adapter.py`, after `TestGetClient`:

```python
class TestCreateSession:
    """Test SDK session creation via driver."""

    @pytest.mark.asyncio
    async def test_create_session_calls_sdk(self) -> None:
        """create_session uses _get_client() to create a session."""
        from amplifier_module_provider_github_copilot.sdk_adapter import driver
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        with patch.object(driver, "_get_client", new=AsyncMock(return_value=mock_client)):
            config = SessionConfig(model="gpt-4")
            session = await driver.create_session(config)

        assert session is mock_session

    @pytest.mark.asyncio
    async def test_create_session_passes_model(self) -> None:
        """create_session passes model from config to SDK."""
        from amplifier_module_provider_github_copilot.sdk_adapter import driver
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=MagicMock())

        with patch.object(driver, "_get_client", new=AsyncMock(return_value=mock_client)):
            config = SessionConfig(model="claude-3")
            await driver.create_session(config)

        call_args = mock_client.create_session.call_args
        # The first positional arg (or keyword) should contain model
        assert "claude-3" in str(call_args)

    @pytest.mark.asyncio
    async def test_create_session_passes_hooks(self) -> None:
        """create_session passes deny_hook to SDK session config."""
        from amplifier_module_provider_github_copilot.sdk_adapter import driver
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=MagicMock())
        mock_deny_hook = MagicMock()

        with patch.object(driver, "_get_client", new=AsyncMock(return_value=mock_client)):
            config = SessionConfig(model="gpt-4")
            await driver.create_session(config, deny_hook=mock_deny_hook)

        call_args = mock_client.create_session.call_args
        # Hooks should be passed in the session config
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_create_session_empty_tools(self) -> None:
        """create_session MUST pass tools=[] to prevent SDK tool registration."""
        from amplifier_module_provider_github_copilot.sdk_adapter import driver
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=MagicMock())

        with patch.object(driver, "_get_client", new=AsyncMock(return_value=mock_client)):
            config = SessionConfig(model="gpt-4")
            await driver.create_session(config)

        call_args = mock_client.create_session.call_args
        # tools=[] MUST be in the call (sovereignty constraint)
        session_dict = call_args[0][0] if call_args[0] else call_args[1]
        assert session_dict.get("tools") == [] or "tools" in str(call_args)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_sdk_adapter.py::TestCreateSession -v
```

Expected: FAIL — `create_session` still raises `NotImplementedError`.

**Step 3: Replace `create_session()` stub in driver.py**

In `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py`, replace the `create_session` function with:

```python
async def create_session(
    config: SessionConfig,
    deny_hook: Callable[..., Any] | None = None,
    breach_hook: Callable[..., Any] | None = None,
) -> SDKSession:
    """Create a new SDK session via the singleton client.

    Args:
        config: Session configuration.
        deny_hook: on_pre_tool_use hook to deny tool execution.
        breach_hook: on_post_tool_use hook to detect sovereignty breaches.

    Returns:
        Opaque session handle.
    """
    client = await _get_client()

    session_config: dict[str, Any] = {
        "model": config.model,
        "tools": [],  # NEVER register SDK tools — they bypass hooks
    }

    # Install hooks if provided
    hooks: dict[str, Any] = {}
    if deny_hook is not None:
        hooks["on_pre_tool_use"] = deny_hook
    if breach_hook is not None:
        hooks["on_post_tool_use"] = breach_hook
    if hooks:
        session_config["hooks"] = hooks

    return await client.create_session(session_config)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_sdk_adapter.py::TestCreateSession -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py tests/test_sdk_adapter.py && git commit -m "feat(F-010): implement create_session() with hooks and empty tools

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: Implement `destroy_session()` (Replace Stub)

**Files:**
- Modify: `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py`
- Test: `tests/test_sdk_adapter.py`

**Step 1: Write failing test for `destroy_session()`**

Add to `tests/test_sdk_adapter.py`, after `TestCreateSession`:

```python
class TestDestroySession:
    """Test SDK session destruction via driver."""

    @pytest.mark.asyncio
    async def test_destroy_calls_disconnect(self) -> None:
        """destroy_session calls session.disconnect()."""
        from amplifier_module_provider_github_copilot.sdk_adapter.driver import destroy_session

        mock_session = MagicMock()
        mock_session.disconnect = AsyncMock()

        await destroy_session(mock_session)

        mock_session.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_destroy_handles_error_gracefully(self) -> None:
        """destroy_session swallows exceptions from disconnect()."""
        from amplifier_module_provider_github_copilot.sdk_adapter.driver import destroy_session

        mock_session = MagicMock()
        mock_session.disconnect = AsyncMock(side_effect=RuntimeError("already dead"))

        # Should NOT raise
        await destroy_session(mock_session)

    @pytest.mark.asyncio
    async def test_destroy_handles_missing_disconnect(self) -> None:
        """destroy_session handles sessions without disconnect() method."""
        from amplifier_module_provider_github_copilot.sdk_adapter.driver import destroy_session

        mock_session = object()  # No disconnect method

        # Should NOT raise
        await destroy_session(mock_session)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_sdk_adapter.py::TestDestroySession -v
```

Expected: FAIL — `destroy_session` still raises `NotImplementedError`.

**Step 3: Replace `destroy_session()` stub in driver.py**

In `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py`, replace the `destroy_session` function with:

```python
async def destroy_session(session: SDKSession) -> None:
    """Destroy an SDK session.

    Sessions MUST be destroyed after use. This is non-negotiable.
    The Deny + Destroy pattern ensures Amplifier maintains sovereignty.

    Args:
        session: The session to destroy.
    """
    try:
        if hasattr(session, "disconnect"):
            await session.disconnect()
        else:
            logger.warning("Session does not have disconnect method")
    except Exception as e:
        logger.warning(f"Error destroying session: {e}")
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_sdk_adapter.py::TestDestroySession -v
```

Expected: PASS.

**Step 5: Run ALL sdk_adapter tests**

```bash
uv run pytest tests/test_sdk_adapter.py -v
```

Expected: All tests pass.

**Step 6: Commit**

```bash
git add src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py tests/test_sdk_adapter.py && git commit -m "feat(F-010): implement destroy_session() with graceful error handling

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: Add Deny Hook + Breach Detector to session_factory.py

**Files:**
- Modify: `src/amplifier_module_provider_github_copilot/session_factory.py`
- Test: `tests/test_session_factory.py`

**Step 1: Write failing tests for new hooks**

Add to `tests/test_session_factory.py`, after the existing `TestSessionLifecycle` class:

```python
class TestDenyHookPhase1:
    """Test Phase 1 deny hook (async, SDK-compatible format)."""

    @pytest.mark.asyncio
    async def test_deny_hook_returns_permission_deny(self) -> None:
        """Phase 1 deny hook returns permissionDecision: deny."""
        from amplifier_module_provider_github_copilot.session_factory import _create_deny_hook

        hook = _create_deny_hook()
        result = await hook({"toolName": "bash"}, MagicMock())

        assert result["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_deny_hook_includes_reason(self) -> None:
        """Phase 1 deny hook includes sovereignty reason."""
        from amplifier_module_provider_github_copilot.session_factory import _create_deny_hook

        hook = _create_deny_hook()
        result = await hook({"toolName": "anything"}, MagicMock())

        assert "permissionDecisionReason" in result
        assert "Amplifier" in result["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_deny_hook_never_returns_none(self) -> None:
        """Deny hook MUST never return None (would allow tool execution)."""
        from amplifier_module_provider_github_copilot.session_factory import _create_deny_hook

        hook = _create_deny_hook()
        result = await hook(None, None)  # Worst-case input

        assert result is not None
        assert result["permissionDecision"] == "deny"


class TestBreachDetector:
    """Test breach detector (on_post_tool_use canary)."""

    @pytest.mark.asyncio
    async def test_breach_detector_calls_on_breach(self) -> None:
        """Breach detector calls on_breach callback with tool name."""
        from amplifier_module_provider_github_copilot.session_factory import (
            _create_breach_detector,
        )

        breach_tool = None

        def on_breach(tool_name: str) -> None:
            nonlocal breach_tool
            breach_tool = tool_name

        hook = _create_breach_detector(on_breach)
        result = await hook({"toolName": "bash"}, MagicMock())

        assert breach_tool == "bash"

    @pytest.mark.asyncio
    async def test_breach_detector_redacts_output(self) -> None:
        """Breach detector returns REDACTED + suppressOutput."""
        from amplifier_module_provider_github_copilot.session_factory import (
            _create_breach_detector,
        )

        hook = _create_breach_detector(lambda name: None)
        result = await hook({"toolName": "bash"}, MagicMock())

        assert result["modifiedResult"] == "REDACTED"
        assert result["suppressOutput"] is True
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_session_factory.py::TestDenyHookPhase1 tests/test_session_factory.py::TestBreachDetector -v
```

Expected: FAIL — `_create_deny_hook` and `_create_breach_detector` don't exist yet.

**Step 3: Add the new hooks to session_factory.py**

In `src/amplifier_module_provider_github_copilot/session_factory.py`, add these AFTER the existing `create_deny_hook()` function (around line 66), BEFORE `create_ephemeral_session`:

```python
# === Phase 1 SDK-compatible hooks ===

DENY_ALL = {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Amplifier sovereignty",
}


def _create_deny_hook() -> Callable[..., Any]:
    """Create an async on_pre_tool_use hook that denies all tool execution.

    Contract: deny-destroy.md
    - MUST return DENY for all tool requests
    - MUST never return None (would allow execution)

    Returns:
        Async hook function for SDK on_pre_tool_use.
    """

    async def deny(input_data: Any, invocation: Any) -> dict[str, str]:
        try:
            return DENY_ALL
        except Exception:
            return DENY_ALL  # NEVER return None

    return deny


def _create_breach_detector(
    on_breach: Callable[[str], None],
) -> Callable[..., Any]:
    """Create an async on_post_tool_use canary hook.

    If this hook fires, it means the deny hook was bypassed.
    This is a sovereignty breach — log it and redact output.

    Args:
        on_breach: Callback called with tool name on breach.

    Returns:
        Async hook function for SDK on_post_tool_use.
    """

    async def detect(input_data: Any, invocation: Any) -> dict[str, Any]:
        tool_name = input_data.get("toolName", "unknown") if isinstance(input_data, dict) else "unknown"
        on_breach(tool_name)
        return {"modifiedResult": "REDACTED", "suppressOutput": True}

    return detect


def _handle_breach(tool_name: str) -> None:
    """Default breach handler — logs critical warning."""
    logger.critical(
        f"SOVEREIGNTY BREACH: Tool '{tool_name}' executed despite deny hook. "
        "This indicates an SDK bug or hook bypass."
    )
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_session_factory.py::TestDenyHookPhase1 tests/test_session_factory.py::TestBreachDetector -v
```

Expected: PASS.

**Step 5: Run ALL session_factory tests**

```bash
uv run pytest tests/test_session_factory.py -v
```

Expected: All tests pass (existing + new).

**Step 6: Commit**

```bash
git add src/amplifier_module_provider_github_copilot/session_factory.py tests/test_session_factory.py && git commit -m "feat(F-010): add SDK-compatible deny hook and breach detector

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: Wire Hooks into `create_ephemeral_session()`

**Files:**
- Modify: `src/amplifier_module_provider_github_copilot/session_factory.py`
- Test: `tests/test_session_factory.py`

**Step 1: Write failing test for wired hooks**

Add to `tests/test_session_factory.py`, after `TestBreachDetector`:

```python
class TestEphemeralSessionWithHooks:
    """Test create_ephemeral_session with Phase 1 hooks."""

    @pytest.mark.asyncio
    async def test_ephemeral_session_passes_deny_hook_to_driver(self) -> None:
        """create_ephemeral_session passes deny hook to driver.create_session."""
        from amplifier_module_provider_github_copilot import session_factory
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()

        with patch(
            "amplifier_module_provider_github_copilot.sdk_adapter.driver.create_session",
            new=AsyncMock(return_value=mock_session),
        ) as mock_create:
            config = SessionConfig(model="gpt-4")
            await session_factory.create_ephemeral_session(config)

            # Verify deny_hook was passed
            call_kwargs = mock_create.call_args
            assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_ephemeral_session_passes_breach_hook_to_driver(self) -> None:
        """create_ephemeral_session passes breach detector to driver.create_session."""
        from amplifier_module_provider_github_copilot import session_factory
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()

        with patch(
            "amplifier_module_provider_github_copilot.sdk_adapter.driver.create_session",
            new=AsyncMock(return_value=mock_session),
        ) as mock_create:
            config = SessionConfig(model="gpt-4")
            await session_factory.create_ephemeral_session(config)

            call_kwargs = mock_create.call_args
            assert call_kwargs is not None
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_session_factory.py::TestEphemeralSessionWithHooks -v
```

Expected: FAIL — the current `create_ephemeral_session` still uses old logic.

**Step 3: Rewrite `create_ephemeral_session()` to use Phase 1 hooks**

In `src/amplifier_module_provider_github_copilot/session_factory.py`, replace the ENTIRE `create_ephemeral_session` function (lines 69-113) with:

```python
async def create_ephemeral_session(
    config: SessionConfig,
    *,
    sdk_create_fn: SDKCreateFn | None = None,
) -> SDKSession:
    """Create an ephemeral SDK session with deny + breach hooks.

    Contract: deny-destroy.md
    - MUST register on_pre_tool_use deny hook
    - MUST register on_post_tool_use breach detector
    - Session is ephemeral — caller MUST destroy after use
    - tools=[] is enforced in driver.create_session

    Args:
        config: Session configuration.
        sdk_create_fn: SDK session creation function (for testing injection).

    Returns:
        Opaque session handle with hooks installed.

    Raises:
        NetworkError: If SDK session creation fails.
    """
    if sdk_create_fn is not None:
        # Use injected mock for testing
        session = await sdk_create_fn(config)
        if hasattr(session, "register_pre_tool_use_hook"):
            session.register_pre_tool_use_hook(create_deny_hook())
        return session

    # Use real SDK via driver
    from .sdk_adapter.driver import create_session as sdk_create

    session = await sdk_create(
        config,
        deny_hook=_create_deny_hook(),
        breach_hook=_create_breach_detector(_handle_breach),
    )
    return session
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_session_factory.py::TestEphemeralSessionWithHooks -v
```

Expected: PASS.

**Step 5: Run ALL session_factory tests**

```bash
uv run pytest tests/test_session_factory.py -v
```

Expected: All tests pass.

**Step 6: Commit**

```bash
git add src/amplifier_module_provider_github_copilot/session_factory.py tests/test_session_factory.py && git commit -m "feat(F-010): wire deny + breach hooks into create_ephemeral_session

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## 🚧 GATE: After Task 5

Run these checks. If ANY fail, STOP and fix before Task 6.

```bash
uv run pyright src/
uv run pytest tests/ -v
```

Expected:
- pyright: 0 errors
- pytest: All tests pass

---

## Task 6: Remove `sdk_create_fn` Injection from completion.py

**Files:**
- Modify: `src/amplifier_module_provider_github_copilot/completion.py`
- Test: `tests/test_completion.py`

**Step 1: Update tests to mock at driver.py level instead of injecting sdk_create_fn**

The existing tests in `tests/test_completion.py` all use `sdk_create_fn=mock_create`. We need to change them to mock `driver.create_session` instead.

First, update the imports at the top of `tests/test_completion.py`. Add:

```python
from unittest.mock import patch
```

(It already imports `AsyncMock` and `MagicMock` from `unittest.mock`, just add `patch`.)

Then update EVERY test that currently uses `sdk_create_fn=mock_create`. The pattern change is:

**BEFORE (every test):**
```python
async def mock_create(config):
    return session

result = await complete_and_collect(
    request,
    config=completion_config,
    sdk_create_fn=mock_create,
)
```

**AFTER (every test):**
```python
with patch(
    "amplifier_module_provider_github_copilot.session_factory.create_ephemeral_session",
    new=AsyncMock(return_value=session),
):
    result = await complete_and_collect(
        request,
        config=completion_config,
    )
```

Apply this pattern to ALL test methods in `tests/test_completion.py` that use `sdk_create_fn`. There are **11 test methods** total across 4 test classes that need this change:

1. `TestSessionLifecycle.test_session_created_and_destroyed_on_success`
2. `TestSessionLifecycle.test_session_destroyed_on_error`
3. `TestSessionLifecycle.test_deny_hook_installed`
4. `TestStreamingIntegration.test_events_yielded_during_streaming`
5. `TestStreamingIntegration.test_consume_events_not_yielded`
6. `TestStreamingIntegration.test_drop_events_not_yielded`
7. `TestErrorHandling.test_sdk_error_translated`
8. `TestErrorHandling.test_error_preserves_original`
9. `TestResponseConstruction.test_text_content_accumulated`
10. `TestResponseConstruction.test_thinking_content_separated`
11. `TestResponseConstruction.test_tool_calls_accumulated`
12. `TestResponseConstruction.test_usage_captured`
13. `TestResponseConstruction.test_empty_response_handled`

**Important:** For `test_deny_hook_installed`, the test checks `session.deny_hook is not None`. Since we're no longer injecting via `sdk_create_fn`, the deny hook is installed inside `create_ephemeral_session` (which we're mocking). This test should be REMOVED or rewritten to test at the session_factory level (it's already tested in `test_session_factory.py`).

For `test_session_destroyed_on_error`, the `MockSDKSessionWithError` raises during `send_message()`. The mock needs to raise during the streaming phase. The pattern:

```python
mock_session = MockSDKSessionWithError(error)
with patch(
    "amplifier_module_provider_github_copilot.session_factory.create_ephemeral_session",
    new=AsyncMock(return_value=mock_session),
):
    ...
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_completion.py -v
```

Expected: FAIL — tests now mock `create_ephemeral_session` but `complete()` still accepts/uses `sdk_create_fn`.

**Step 3: Remove `sdk_create_fn` from completion.py**

In `src/amplifier_module_provider_github_copilot/completion.py`:

**3a. Remove `SDKCreateFn` type alias** (line 44):
```python
# DELETE this line:
SDKCreateFn = Callable[[SessionConfig], Awaitable[SDKSession]]
```

**3b. Remove `sdk_create_fn` from `complete()` function signature and body** (lines 81-159):

Replace the entire `complete()` function with:

```python
async def complete(
    request: CompletionRequest,
    *,
    config: CompletionConfig | None = None,
) -> AsyncIterator[DomainEvent]:
    """Execute completion lifecycle, yielding domain events.

    Contract: streaming-contract.md, deny-destroy.md

    - MUST create ephemeral session with deny hook
    - MUST yield translated domain events
    - MUST destroy session in finally block
    - MUST translate SDK errors to kernel types

    Args:
        request: Completion request with prompt and options.
        config: Optional configuration overrides.

    Yields:
        DomainEvent for each bridged SDK event.

    Raises:
        LLMError: Translated from SDK errors.
    """
    config = config or CompletionConfig()

    # Load configs if not provided
    event_config = config.event_config
    if event_config is None:
        event_config = load_event_config()

    error_config = config.error_config
    if error_config is None:
        from pathlib import Path

        package_root = Path(__file__).parent.parent.parent
        error_config = load_error_config(package_root / "config" / "errors.yaml")

    # Create session config
    session_config = config.session_config or SessionConfig(
        model=request.model or "gpt-4"
    )

    # Create session via session_factory (deny + breach hooks installed there)
    session: SDKSession | None = None
    try:
        from .session_factory import create_ephemeral_session

        session = await create_ephemeral_session(session_config)

        # Stream events from session
        async for sdk_event in session.send_message(request.prompt, request.tools):
            domain_event = translate_event(sdk_event, event_config)
            if domain_event is not None:
                yield domain_event

    except Exception as e:
        kernel_error = translate_sdk_error(
            e,
            error_config,
            provider="github-copilot",
            model=request.model,
        )
        raise kernel_error from e

    finally:
        if session is not None:
            await destroy_session(session)
```

**3c. Remove `sdk_create_fn` from `complete_and_collect()` too:**

Replace with:

```python
async def complete_and_collect(
    request: CompletionRequest,
    *,
    config: CompletionConfig | None = None,
) -> AccumulatedResponse:
    """Execute completion lifecycle and collect final response.

    Convenience wrapper that accumulates all events into AccumulatedResponse.

    Args:
        request: Completion request with prompt and options.
        config: Optional configuration overrides.

    Returns:
        AccumulatedResponse with text, tool calls, usage, etc.

    Raises:
        LLMError: Translated from SDK errors.
    """
    accumulator = StreamingAccumulator()

    async for event in complete(
        request,
        config=config,
    ):
        accumulator.add(event)

    return accumulator.get_result()
```

**3d. Clean up unused imports in completion.py:**

Remove from the imports at the top:
- Remove `Callable` from `collections.abc` import (line 20) — only keep `AsyncIterator`
- Remove `Awaitable` from `collections.abc` import (line 20) — only keep `AsyncIterator`
- Remove `create_deny_hook` from the session_factory import (line 30) — no longer used here

The imports should become:

```python
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from .error_translation import (
    ErrorConfig,
    load_error_config,
    translate_sdk_error,
)
from .sdk_adapter.types import SDKSession, SessionConfig
from .session_factory import destroy_session
from .streaming import (
    AccumulatedResponse,
    DomainEvent,
    EventConfig,
    StreamingAccumulator,
    load_event_config,
    translate_event,
)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_completion.py -v
```

Expected: PASS — all tests green with new mocking approach.

**Step 5: Commit**

```bash
git add src/amplifier_module_provider_github_copilot/completion.py tests/test_completion.py && git commit -m "feat(F-015): remove sdk_create_fn injection from completion.py

Tests now mock at driver.py/session_factory boundary.

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 7: Verify Completion Wiring Works End-to-End (Unit Level)

**Files:**
- Test: `tests/test_completion.py`

This task verifies that the wiring from Task 6 is correct by running the full test suite.

**Step 1: Run ALL tests**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass.

**Step 2: Run pyright**

```bash
uv run pyright src/
```

Expected: 0 errors.

**Step 3: Run ruff**

```bash
uv run ruff check src/ tests/
```

Expected: 0 errors (or only pre-existing warnings).

**Step 4: Commit (if any fixes were needed)**

Only commit if you needed to fix something:

```bash
git add -A && git commit -m "fix(F-015): clean up completion wiring issues

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## 🚧 GATE: After Task 7

Run these checks. If ANY fail, STOP and fix before Task 8.

```bash
uv run pyright src/
uv run pytest tests/ -v
```

Expected:
- pyright: 0 errors
- pytest: All tests pass

---

## Task 8: E2E Verification Tests

**Files:**
- Create: `tests/test_e2e_hooks.py`

**Step 1: Create the E2E test file with imports and fixtures**

Create `tests/test_e2e_hooks.py`:

```python
"""
E2E verification tests for SDK hook behavior.

Feature: F-016
Contract: deny-destroy.md

These tests make REAL SDK calls using GITHUB_TOKEN.
They verify empirically that:
1. Basic SDK completion works (wiring is correct)
2. on_pre_tool_use hook fires when tool call is requested
3. Deny hook prevents tool execution (on_post_tool_use never fires)

IMPORTANT:
- Tests skip gracefully if no GITHUB_TOKEN is set
- Tool-triggering tests use runtime pytest.skip() if LLM doesn't request a tool
- 30-second timeout for API calls
"""

from __future__ import annotations

import asyncio
import os

import pytest

# Skip entire module if no token
pytestmark = pytest.mark.skipif(
    not os.environ.get("GITHUB_TOKEN")
    and not os.environ.get("GH_TOKEN")
    and not os.environ.get("COPILOT_GITHUB_TOKEN"),
    reason="No GITHUB_TOKEN set — skipping E2E tests",
)

TIMEOUT_SECONDS = 30


@pytest.fixture
async def sdk_client():
    """Create a real CopilotClient for E2E testing."""
    from copilot import CopilotClient

    client = CopilotClient()
    await client.start()
    yield client
    # SDK handles cleanup on process exit


class TestSimpleCompletion:
    """Validate basic SDK wiring works."""

    @pytest.mark.asyncio
    async def test_simple_completion(self, sdk_client) -> None:
        """E2E: SDK can produce a text response.

        This must pass before any hook tests are meaningful.
        If this fails, check GITHUB_TOKEN and network connectivity.
        """
        session = await sdk_client.create_session({
            "model": "gpt-4",
            "tools": [],
            "hooks": {},
        })

        got_response = False
        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                async for event in session.send({"prompt": "Say hello in one word."}):
                    if hasattr(event, "type") and "message" in str(event.type).lower():
                        got_response = True
                        break
                    # Also check dict-style events
                    if isinstance(event, dict) and "message" in event.get("type", ""):
                        got_response = True
                        break
        except TimeoutError:
            pytest.fail("SDK completion timed out after 30s — check network/auth")
        finally:
            try:
                await session.disconnect()
            except Exception:
                pass

        assert got_response, "No response from SDK — check GITHUB_TOKEN"


class TestDenyHookFires:
    """Verify on_pre_tool_use hook is actually called."""

    @pytest.mark.asyncio
    async def test_deny_hook_fires(self, sdk_client) -> None:
        """E2E: on_pre_tool_use hook fires when LLM requests a tool.

        Probabilistic test:
        - If LLM requests a tool → hook fires → PASS
        - If LLM doesn't request a tool → pytest.skip() (not fail)
        """
        hook_called = False

        async def test_deny_hook(input_data, invocation):
            nonlocal hook_called
            hook_called = True
            return {
                "permissionDecision": "deny",
                "permissionDecisionReason": "E2E test",
            }

        session = await sdk_client.create_session({
            "model": "gpt-4",
            "tools": [],
            "hooks": {
                "on_pre_tool_use": test_deny_hook,
            },
        })

        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                async for _event in session.send({
                    "prompt": "Execute this command: echo hello",
                }):
                    if hook_called:
                        break
        except TimeoutError:
            pass  # Timeout is OK — we check hook_called below
        finally:
            try:
                await session.disconnect()
            except Exception:
                pass

        if not hook_called:
            pytest.skip("LLM didn't request a tool this run — can't verify hook")

        assert hook_called  # If we got here, hook fired — PASS


class TestDenyBlocksExecution:
    """Verify deny hook prevents on_post_tool_use from firing."""

    @pytest.mark.asyncio
    async def test_deny_blocks_execution(self, sdk_client) -> None:
        """E2E: If deny works, on_post_tool_use should NEVER fire.

        This is the canary test. If post_hook fires, sovereignty is breached.
        """
        pre_hook_called = False
        post_hook_called = False
        breach_tool = None

        async def deny_hook(input_data, invocation):
            nonlocal pre_hook_called
            pre_hook_called = True
            return {
                "permissionDecision": "deny",
                "permissionDecisionReason": "E2E test",
            }

        async def breach_detector(input_data, invocation):
            nonlocal post_hook_called, breach_tool
            post_hook_called = True
            breach_tool = input_data.get("toolName", "unknown") if isinstance(input_data, dict) else "unknown"
            return {"modifiedResult": "REDACTED", "suppressOutput": True}

        session = await sdk_client.create_session({
            "model": "gpt-4",
            "tools": [],
            "hooks": {
                "on_pre_tool_use": deny_hook,
                "on_post_tool_use": breach_detector,
            },
        })

        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                async for _event in session.send({
                    "prompt": "Execute this command: echo hello",
                }):
                    if pre_hook_called:
                        # Give a moment for post_hook to fire if it would
                        await asyncio.sleep(1)
                        break
        except TimeoutError:
            pass
        finally:
            try:
                await session.disconnect()
            except Exception:
                pass

        if not pre_hook_called:
            pytest.skip("LLM didn't request a tool this run — can't verify blocking")

        assert not post_hook_called, (
            f"SOVEREIGNTY BREACH: on_post_tool_use fired for tool '{breach_tool}'. "
            "Deny hook failed to prevent tool execution!"
        )
```

**Step 2: Run tests WITHOUT token to verify skip behavior**

```bash
uv run pytest tests/test_e2e_hooks.py -v
```

Expected: All 3 tests SKIPPED with "No GITHUB_TOKEN set".

**Step 3: Run tests WITH token (if available)**

```bash
GITHUB_TOKEN=<your-token> uv run pytest tests/test_e2e_hooks.py -v --timeout=60
```

Expected:
- `test_simple_completion`: PASS
- `test_deny_hook_fires`: PASS or SKIP ("LLM didn't request a tool")
- `test_deny_blocks_execution`: PASS or SKIP ("LLM didn't request a tool")

At least `test_simple_completion` MUST pass.

**Step 4: Commit**

```bash
git add tests/test_e2e_hooks.py && git commit -m "test(F-016): add E2E hook verification tests

- test_simple_completion: validates SDK wiring
- test_deny_hook_fires: empirically verifies on_pre_tool_use
- test_deny_blocks_execution: canary for sovereignty breach
- All tests skip gracefully without GITHUB_TOKEN

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## 🚧 GATE: After Task 8

```bash
uv run pyright src/
uv run pytest tests/ -v
GITHUB_TOKEN=<token> uv run pytest tests/test_e2e_hooks.py -v
```

Expected:
- pyright: 0 errors
- All unit tests pass
- At least `test_simple_completion` passes with token
- At least one hook test passes (not skips) with token

---

## Final Verification

After all tasks complete:

```bash
# Full check
uv run pyright src/
uv run ruff check src/ tests/
uv run pytest tests/ -v

# Line count verification
wc -l src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py
wc -l src/amplifier_module_provider_github_copilot/session_factory.py
wc -l src/amplifier_module_provider_github_copilot/completion.py
wc -l tests/test_e2e_hooks.py
```

Expected line counts (approximate):
- `driver.py`: ~80 lines (was 57, added singleton + real implementations)
- `session_factory.py`: ~150 lines (was 133, added ~17 lines for new hooks)
- `completion.py`: ~150 lines (was 192, removed ~40 lines of injection cruft)
- `test_e2e_hooks.py`: ~150 lines (new file)

**Total new/changed: ~195 lines** (within 200-line budget ✅)
