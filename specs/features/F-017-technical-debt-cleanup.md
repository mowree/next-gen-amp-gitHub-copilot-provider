# F-017: Technical Debt Cleanup

## Overview

Remove ~335 lines of dead code, duplication, and drift from Phase 1 implementation.
Four targeted changes, each independent. Run `uv run pytest tests/ -v --tb=short`
and `python_check` after EACH change to ensure nothing breaks.

**IMPORTANT**: Complete changes in the exact order listed. Each builds on the previous.

---

## Change 1: Delete `driver.py` and rewire `session_factory.py`

### Problem

`driver.py` (80 lines) is superseded by `client.py` (271 lines).
`session_factory.py` calls `driver.create_session` via `_driver_create_session()`.
After rewiring, `driver.py` becomes truly dead code.

### Files to Modify

#### 1a. `src/amplifier_module_provider_github_copilot/session_factory.py`

**Remove** the import on line 23:
```python
from .sdk_adapter.types import SDKSession, SessionConfig
```
**Replace with**:
```python
from .sdk_adapter.client import CopilotClientWrapper
from .sdk_adapter.types import SDKSession, SessionConfig
```

**Remove** the entire `_driver_create_session` function (lines 86-93):
```python
async def _driver_create_session(  # pyright: ignore[reportUnusedFunction]
    config: SessionConfig,
    deny_hook: Callable[..., Awaitable[dict[str, str]]] | None = None,
) -> SDKSession:
    """Thin wrapper around driver.create_session for testability."""
    from .sdk_adapter.driver import create_session as sdk_create

    return await sdk_create(config, deny_hook=deny_hook)
```

**Modify** `create_ephemeral_session()` — replace the `if sdk_create_fn is None:` branch (lines 156-159):
```python
# OLD:
    if sdk_create_fn is None:
        # Use async deny hook for real driver path
        deny_hook = _create_deny_hook()
        session = await _driver_create_session(config, deny_hook=deny_hook)
```
```python
# NEW:
    if sdk_create_fn is None:
        # Use CopilotClientWrapper for real SDK path
        # Note: CopilotClientWrapper.session() handles deny internally
        # For now, fallback to raising - full wiring comes in F-015
        from .error_translation import ProviderUnavailableError
        raise ProviderUnavailableError(
            "Real SDK path requires CopilotClientWrapper. Use sdk_create_fn for testing.",
            provider="github-copilot",
        )
```

> **Rationale**: The `_driver_create_session → driver.create_session` path is never
> used in production (all tests inject `sdk_create_fn`). The real SDK path will be
> wired through `CopilotClientWrapper.session()` in F-015 (completion wiring).
> This makes driver.py truly dead and deletable.

#### 1b. Delete `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py`

Delete the entire file (80 lines removed).

#### 1c. `src/amplifier_module_provider_github_copilot/sdk_adapter/__init__.py`

**Replace entire file** with:
```python
"""
SDK Adapter Layer - The Membrane.

All SDK imports live here and only here.
Domain code MUST NOT import from SDK directly.

Contract: contracts/sdk-boundary.md

Exports:
- SessionConfig: Configuration for SDK session creation
- CopilotClientWrapper: SDK client with lifecycle management
- CopilotSessionWrapper: Opaque session handle
"""

from .client import CopilotClientWrapper, CopilotSessionWrapper
from .types import SessionConfig

__all__ = [
    "CopilotClientWrapper",
    "CopilotSessionWrapper",
    "SessionConfig",
]
```

#### 1d. Delete test files that test driver.py directly

- Delete `tests/test_driver_singleton.py` (49 lines)
- Delete `tests/test_create_session.py` (133 lines)
- Delete `tests/test_destroy_session.py` (40 lines)

#### 1e. Update `tests/test_sdk_adapter.py`

**Remove** `TestSDKAdapterDriver` class (lines 80-93) — tests driver functions that no longer exist.

**Update** `TestSDKAdapterExports` class — remove `test_exports_create_session` and
`test_exports_destroy_session` methods. **Add** tests for new exports:

```python
class TestSDKAdapterExports:
    """Test sdk_adapter module exports."""

    def test_exports_session_config(self) -> None:
        """sdk_adapter exports SessionConfig."""
        from amplifier_module_provider_github_copilot.sdk_adapter import SessionConfig

        assert SessionConfig is not None

    def test_exports_copilot_client_wrapper(self) -> None:
        """sdk_adapter exports CopilotClientWrapper."""
        from amplifier_module_provider_github_copilot.sdk_adapter import CopilotClientWrapper

        assert CopilotClientWrapper is not None

    def test_exports_copilot_session_wrapper(self) -> None:
        """sdk_adapter exports CopilotSessionWrapper."""
        from amplifier_module_provider_github_copilot.sdk_adapter import CopilotSessionWrapper

        assert CopilotSessionWrapper is not None
```

#### 1f. Update `tests/test_ephemeral_session_wiring.py`

The test `test_deny_hook_passed_to_driver_uses_async_deny_all` monkeypatches
`_driver_create_session` which no longer exists. **Replace** this test:

```python
@pytest.mark.asyncio
async def test_deny_hook_passed_to_sdk_create_fn(self) -> None:
    """create_ephemeral_session() with sdk_create_fn must register deny hook."""
    from amplifier_module_provider_github_copilot.session_factory import (
        create_ephemeral_session,
    )
    from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

    mock_session = MagicMock()
    mock_session.register_pre_tool_use_hook = MagicMock()
    mock_create = AsyncMock(return_value=mock_session)

    config = SessionConfig(model="gpt-4o")
    await create_ephemeral_session(config, sdk_create_fn=mock_create)

    # Verify deny hook was registered
    mock_session.register_pre_tool_use_hook.assert_called_once()
    hook = mock_session.register_pre_tool_use_hook.call_args[0][0]
    assert callable(hook)
```

The test `test_deny_hook_not_none_when_passed_to_driver` — same issue, **replace**:

```python
@pytest.mark.asyncio
async def test_deny_hook_always_registered(self, monkeypatch: pytest.MonkeyPatch) -> None:
    """create_ephemeral_session() must always register a deny hook."""
    from amplifier_module_provider_github_copilot.session_factory import (
        create_ephemeral_session,
    )
    from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

    mock_session = MagicMock()
    mock_session.register_pre_tool_use_hook = MagicMock()
    mock_create = AsyncMock(return_value=mock_session)

    config = SessionConfig(model="gpt-4o")
    await create_ephemeral_session(config, sdk_create_fn=mock_create)

    mock_session.register_pre_tool_use_hook.assert_called_once()
```

The test `test_breach_detector_created_during_session_creation` — monkeypatches
`_driver_create_session`. **Update** to use `sdk_create_fn` instead:

```python
@pytest.mark.asyncio
async def test_breach_detector_created_during_session_creation(
    self, monkeypatch: pytest.MonkeyPatch
) -> None:
    """create_ephemeral_session() must create a breach detector (for future Phase 2)."""
    import amplifier_module_provider_github_copilot.session_factory as sf_mod
    from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

    mock_session = MagicMock()
    mock_session.register_pre_tool_use_hook = MagicMock()
    mock_create = AsyncMock(return_value=mock_session)

    # Patch _create_breach_detector to verify it's called
    breach_detector_calls: list[Any] = []
    original_create_breach = sf_mod._create_breach_detector  # type: ignore[attr-defined]

    def spy_create_breach(on_breach: Any) -> Any:
        breach_detector_calls.append(on_breach)
        return original_create_breach(on_breach)

    monkeypatch.setattr(sf_mod, "_create_breach_detector", spy_create_breach)

    config = SessionConfig(model="gpt-4o")
    await sf_mod.create_ephemeral_session(config, sdk_create_fn=mock_create)

    assert len(breach_detector_calls) == 1
```

### Verification

```bash
uv run pytest tests/ -v --tb=short
```

Expected: All tests pass. driver.py tests deleted, remaining tests updated.

---

## Change 2: Unify deny hooks (remove sync duplicate)

### Problem

`session_factory.py` has TWO deny hook factories:
- `_create_deny_hook()` (line 34) — **async**, returns `DENY_ALL` with `permissionDecision` key
- `create_deny_hook()` (line 96) — **sync**, returns dict with `action: DENY` key

The sync version uses a DIFFERENT response format than what the SDK expects.
Only the async version (`permissionDecision`) is correct per SDK API.

### Files to Modify

#### 2a. `src/amplifier_module_provider_github_copilot/session_factory.py`

**Remove** the sync `create_deny_hook()` function (lines 96-118):
```python
def create_deny_hook() -> Callable[[Any], dict[str, str]]:
    ...
    def deny_all_tools(tool_request: Any) -> dict[str, str]:
        ...
    return deny_all_tools
```

**Rename** `_create_deny_hook` to `create_deny_hook` (remove leading underscore).
Update the pyright ignore comment since it's now public. Update the call in
`create_ephemeral_session` accordingly.

#### 2b. `src/amplifier_module_provider_github_copilot/completion.py`

**Remove** the import of `create_deny_hook` on line 30:
```python
from .session_factory import create_deny_hook, destroy_session
```
**Replace with**:
```python
from .session_factory import destroy_session
```

**Remove** the deny hook registration in the `complete()` function (lines 131-132):
```python
            if hasattr(session, "register_pre_tool_use_hook"):
                session.register_pre_tool_use_hook(create_deny_hook())
```

> **Rationale**: `create_ephemeral_session` already installs the deny hook.
> Installing it AGAIN in `complete()` is redundant. The sdk_create_fn test
> path in session_factory already handles hook registration.

#### 2c. Update `tests/test_session_factory.py`

The `TestCreateDenyHook` class tests the sync deny hook. **Update** to test the
async version instead:

```python
class TestCreateDenyHook:
    """Test deny hook creation."""

    def test_create_deny_hook_exists(self) -> None:
        """create_deny_hook function exists."""
        from amplifier_module_provider_github_copilot.session_factory import (
            create_deny_hook,
        )

        assert callable(create_deny_hook)

    def test_deny_hook_returns_callable(self) -> None:
        """Deny hook returns a callable."""
        from amplifier_module_provider_github_copilot.session_factory import (
            create_deny_hook,
        )

        hook = create_deny_hook()
        assert callable(hook)

    @pytest.mark.asyncio
    async def test_deny_hook_returns_deny_response(self) -> None:
        """Deny hook returns DENY_ALL with permissionDecision key."""
        from amplifier_module_provider_github_copilot.session_factory import (
            DENY_ALL,
            create_deny_hook,
        )

        hook = create_deny_hook()
        result = await hook(None, None)

        assert result is not None
        assert result == DENY_ALL
        assert result["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_deny_hook_includes_reason(self) -> None:
        """Deny hook includes Amplifier sovereignty reason."""
        from amplifier_module_provider_github_copilot.session_factory import (
            create_deny_hook,
        )

        hook = create_deny_hook()
        result = await hook(None, None)

        assert "permissionDecisionReason" in result
        assert "Amplifier" in result["permissionDecisionReason"]
```

Also update `TestSessionLifecycle.test_full_lifecycle` — the deny hook is now
async, so the test needs updating. The mock session's `register_pre_tool_use_hook`
stores the async hook. Calling it requires `await`:

```python
    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Contract: Session lifecycle is create -> use -> destroy."""
        from amplifier_module_provider_github_copilot.session_factory import (
            create_ephemeral_session,
            destroy_session,
        )

        from amplifier_module_provider_github_copilot.sdk_adapter.types import (
            SessionConfig,
        )

        config = SessionConfig(model="gpt-4")
        mock_sdk_session = MockSDKSession()
        mock_create = AsyncMock(return_value=mock_sdk_session)

        # Create
        session = await create_ephemeral_session(config, sdk_create_fn=mock_create)
        assert session is not None
        assert mock_sdk_session.pre_tool_use_hook is not None

        # Use (verify hook denies) - hook is now sync (register_pre_tool_use_hook path)
        result = mock_sdk_session.pre_tool_use_hook(MockToolRequest(name="test", arguments={}))
        assert result["action"] == "DENY"

        # Destroy
        await destroy_session(session)
        assert mock_sdk_session.disconnect_called
```

Wait — after Change 2a removes sync `create_deny_hook`, the `sdk_create_fn` path
in `create_ephemeral_session` still calls `session.register_pre_tool_use_hook(create_deny_hook())`.
Since we're renaming `_create_deny_hook` to `create_deny_hook` (which is async),
this call will register an async hook via `register_pre_tool_use_hook`.

The `MockSDKSession.register_pre_tool_use_hook` in tests just stores whatever
callable it gets. The test needs to `await` the hook to get the result.

**Update** `TestSessionLifecycle.test_full_lifecycle`:
```python
        # Use (verify hook denies) - hook is async
        result = await mock_sdk_session.pre_tool_use_hook(None, None)
        assert result["permissionDecision"] == "deny"
```

#### 2d. Update `tests/test_deny_hook_breach_detector.py`

The `TestPrivateDenyHook` class references `_create_deny_hook`. After rename:

**Replace** all `_create_deny_hook` with `create_deny_hook` in this file.
**Update** the import lines accordingly (remove `pyright: ignore` comments).

### Verification

```bash
uv run pytest tests/ -v --tb=short
```

---

## Change 3: Remove duplicate `DomainEvent` from `types.py`

### Problem

`DomainEvent` is defined in two places:
- `sdk_adapter/types.py` line 30: `DomainEvent(type: str, data: dict)` — simple, used by old tests
- `streaming.py` line 41: `DomainEvent(type: DomainEventType, data: dict, block_type: str | None)` — rich, used by completion pipeline

The streaming.py version is the real one used in production code.

### Files to Modify

#### 3a. `src/amplifier_module_provider_github_copilot/sdk_adapter/types.py`

**Remove** the `DomainEvent` dataclass (lines 29-39):
```python
@dataclass
class DomainEvent:
    """Event from SDK translated to domain representation.
    ...
    """
    type: str
    data: dict[str, Any]
```

The file should only contain `SessionConfig` and `SDKSession`.

#### 3b. `sdk_adapter/__init__.py`

Already updated in Change 1c — `DomainEvent` is no longer exported.
No further changes needed.

#### 3c. `tests/test_sdk_adapter.py`

**Remove** the entire `TestSDKAdapterTypes` class (lines 18-78) — it tests
the old `DomainEvent` from types.py. The streaming.py `DomainEvent` is tested
in `test_streaming.py`.

**Keep** `TestSDKAdapterExports` (already updated in Change 1e).

### Verification

```bash
uv run pytest tests/ -v --tb=short
```

---

## Change 4: Clean up error class boilerplate (OPTIONAL — mark for later)

### Assessment

The 8 error classes in `error_translation.py` (lines 30-183, ~153 lines) are
**fallback implementations** matching the `amplifier_core.llm_errors` interface.
They exist because `amplifier-core` is not yet installed as a dependency.

**Decision: DO NOT DELETE.** These are legitimate code, not drift. They will be
replaced when `amplifier-core` becomes a real dependency. Add a TODO comment:

#### 4a. `src/amplifier_module_provider_github_copilot/error_translation.py`

**Add** a comment after the imports (after line 25):
```python
# TODO(amplifier-core): Replace fallback error classes below with imports from
# amplifier_core.llm_errors once amplifier-core is a project dependency.
# See: contracts/error-hierarchy.md
```

### Verification

```bash
uv run pytest tests/ -v --tb=short
```

---

## Acceptance Criteria

After all changes:

1. **pyright passes**: `uv run pyright src/` — 0 errors
2. **ruff passes**: `uv run ruff check src/ tests/` — 0 errors
3. **All tests pass**: `uv run pytest tests/ -v --tb=short`
4. **driver.py deleted**: File no longer exists
5. **Line count reduced**: ~335 lines removed (80 driver + 23 sync deny hook + 10 DomainEvent + 222 deleted tests)
6. **No import of driver.py**: `grep -r "from.*driver import" src/` returns empty
7. **Single DomainEvent**: Only in `streaming.py`
8. **Single deny hook factory**: Only `create_deny_hook()` in `session_factory.py` (async)

## Files Summary

| Action | File | Lines Δ |
|--------|------|---------|
| DELETE | `sdk_adapter/driver.py` | -80 |
| DELETE | `tests/test_driver_singleton.py` | -49 |
| DELETE | `tests/test_create_session.py` | -133 |
| DELETE | `tests/test_destroy_session.py` | -40 |
| MODIFY | `sdk_adapter/__init__.py` | ~-5 |
| MODIFY | `sdk_adapter/types.py` | -10 |
| MODIFY | `session_factory.py` | ~-30 |
| MODIFY | `completion.py` | ~-3 |
| MODIFY | `error_translation.py` | +3 |
| MODIFY | `tests/test_sdk_adapter.py` | ~-40 |
| MODIFY | `tests/test_session_factory.py` | ~+5 |
| MODIFY | `tests/test_ephemeral_session_wiring.py` | ~-10 |
| MODIFY | `tests/test_deny_hook_breach_detector.py` | ~-3 |
| **NET** | | **~-335** |
