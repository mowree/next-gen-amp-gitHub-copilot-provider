# F-046: SDK Integration Testing Architecture

**Status**: ready
**Priority**: critical
**Type**: architecture / testing infrastructure
**Estimated Effort**: medium (new test files + contract updates)

---

## Problem Statement

Critical bugs F-044 (system prompt mode) and F-045 (SDK built-in tools) survived 42 feature implementations because our TDD approach tested internal wiring with forgiving mocks, not the actual SDK boundary contract.

**Root cause**: `MagicMock()` and `AsyncMock()` accept any input without validation. Our tests verified "did we call a function?" but never "did we send the right configuration to the SDK?"

**Evidence from current tests** (`test_sdk_boundary.py` line 125):
```python
# This test PASSES with mode="append" — it doesn't enforce "replace"
assert config["system_message"] == {"mode": "append", "content": "Be helpful"}
```

No test ever verified:
- `available_tools` is set to `[]`
- `system_message.mode` is `"replace"` (not `"append"`)
- All required session config fields are present

---

## Architecture: The Configuration Capture Pattern

### Core Principle

Instead of mocking the SDK and hoping mocks match reality, **capture the actual configuration dict** passed to `client.create_session()` and assert on it.

### The Pattern

```python
class ConfigCapturingMock:
    """Mock SDK client that captures the exact config sent to create_session."""
    
    def __init__(self):
        self.captured_configs: list[dict] = []
        self._mock_session = AsyncMock()
        self._mock_session.disconnect = AsyncMock()
    
    async def create_session(self, config: dict) -> Any:
        self.captured_configs.append(copy.deepcopy(config))
        return self._mock_session
```

This is NOT a MagicMock. It's a purpose-built capture fixture that:
1. Records the exact dict passed to `create_session()`
2. Returns a minimal session mock
3. Enables assertions on what was SENT, not what was received

---

## Test Categories

### Category 1: Boundary Contract Tests (NEW)

**File**: `tests/test_sdk_boundary_contract.py`

**Purpose**: Verify the exact configuration dict that `CopilotClientWrapper.session()` sends to `client.create_session()`.

**These tests would have caught F-044 and F-045 on day one.**

#### Required Tests

```python
class TestSessionConfigContract:
    """Verify the session_config dict sent to SDK matches our contract."""

    @pytest.mark.asyncio
    async def test_available_tools_always_empty_list(self):
        """F-045: SDK built-in tools MUST be disabled.
        
        Contract: deny-destroy:NoExecution:MUST:3
        SDK ref: copilot/types.py SessionConfig.available_tools
        SDK ref: copilot/client.py lines 527-529 (available_tools is not None check)
        """
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="gpt-4o"):
            pass
        
        config = mock_client.captured_configs[0]
        assert "available_tools" in config, "available_tools MUST be set"
        assert config["available_tools"] == [], "available_tools MUST be empty list"

    @pytest.mark.asyncio
    async def test_system_message_uses_replace_mode(self):
        """F-044: System message MUST use replace mode.
        
        SDK ref: copilot/types.py SystemMessageConfig
        SDK ref: copilot/client.py line 522-524 (system_message handling)
        """
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(
            model="gpt-4o",
            system_message="You are the Amplifier assistant."
        ):
            pass
        
        config = mock_client.captured_configs[0]
        assert config["system_message"]["mode"] == "replace"
        assert config["system_message"]["content"] == "You are the Amplifier assistant."

    @pytest.mark.asyncio
    async def test_system_message_absent_when_not_provided(self):
        """No system_message key when caller doesn't provide one."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="gpt-4o"):
            pass
        
        config = mock_client.captured_configs[0]
        assert "system_message" not in config

    @pytest.mark.asyncio
    async def test_permission_handler_always_set(self):
        """F-033: Permission handler MUST be set on every session.
        
        Contract: deny-destroy:DenyHook:MUST:1
        """
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="gpt-4o"):
            pass
        
        config = mock_client.captured_configs[0]
        assert "on_permission_request" in config
        assert callable(config["on_permission_request"])

    @pytest.mark.asyncio
    async def test_streaming_always_enabled(self):
        """Streaming MUST be enabled for event-based tool capture."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="gpt-4o"):
            pass
        
        config = mock_client.captured_configs[0]
        assert config["streaming"] is True

    @pytest.mark.asyncio
    async def test_model_passed_through(self):
        """Model parameter forwarded to SDK session config."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="claude-sonnet-4"):
            pass
        
        config = mock_client.captured_configs[0]
        assert config["model"] == "claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_deny_hook_registered_on_session(self):
        """Deny hook MUST be registered after session creation.
        
        Contract: deny-destroy:DenyHook:MUST:1
        """
        mock_client = ConfigCapturingMock()
        # Ensure mock session has the registration method
        mock_client._mock_session.register_pre_tool_use_hook = MagicMock()
        
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="gpt-4o"):
            pass
        
        mock_client._mock_session.register_pre_tool_use_hook.assert_called_once()
```

---

### Category 2: Configuration Invariant Tests (NEW)

**File**: `tests/test_session_config_invariants.py`

**Purpose**: Verify configuration invariants that MUST hold regardless of input parameters.

#### Required Tests

```python
class TestConfigInvariants:
    """Configuration invariants that must ALWAYS hold."""

    INVARIANTS = {
        "available_tools": [],           # F-045: No SDK tools
        "streaming": True,               # Required for event capture
    }
    
    CALLABLE_INVARIANTS = [
        "on_permission_request",         # F-033: Always set
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", ["gpt-4", "gpt-4o", "claude-sonnet-4", None])
    async def test_invariants_hold_for_any_model(self, model):
        """Config invariants hold regardless of model selection."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        kwargs = {}
        if model:
            kwargs["model"] = model
        
        async with wrapper.session(**kwargs):
            pass
        
        config = mock_client.captured_configs[0]
        for key, expected in self.INVARIANTS.items():
            assert config.get(key) == expected, (
                f"Invariant violated: {key} should be {expected!r}, got {config.get(key)!r}"
            )
        for key in self.CALLABLE_INVARIANTS:
            assert key in config and callable(config[key]), (
                f"Callable invariant violated: {key} must be present and callable"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("system_message", [
        "You are helpful",
        "Custom persona",
        None,
    ])
    async def test_invariants_hold_with_system_message_variations(self, system_message):
        """Config invariants hold regardless of system message."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        kwargs = {"model": "gpt-4o"}
        if system_message:
            kwargs["system_message"] = system_message
        
        async with wrapper.session(**kwargs):
            pass
        
        config = mock_client.captured_configs[0]
        assert config.get("available_tools") == []
        assert config.get("streaming") is True

    @pytest.mark.asyncio
    async def test_no_unexpected_keys_in_config(self):
        """Session config should only contain known SDK keys.
        
        Guards against typos or wrong key names that SDK silently ignores.
        SDK ref: copilot/types.py SessionConfig fields
        """
        KNOWN_SDK_KEYS = {
            "session_id", "client_name", "model", "reasoning_effort",
            "tools", "system_message", "available_tools", "excluded_tools",
            "on_permission_request", "on_user_input_request", "hooks",
            "working_directory", "provider", "streaming", "mcp_servers",
            "custom_agents", "agent", "config_dir", "skill_directories",
            "disabled_skills", "infinite_sessions", "on_event",
        }
        
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="gpt-4o", system_message="test"):
            pass
        
        config = mock_client.captured_configs[0]
        unknown_keys = set(config.keys()) - KNOWN_SDK_KEYS
        assert unknown_keys == set(), (
            f"Unknown keys in session config: {unknown_keys}. "
            f"These may be typos that the SDK silently ignores."
        )
```

---

### Category 3: SDK Assumption Drift Tests (ENHANCED)

**File**: `tests/test_sdk_assumptions.py` (enhance existing)

**Purpose**: Verify our assumptions about SDK types and behavior. These tests import the REAL SDK and check structure — no mocks, no API calls.

#### New Tests to Add

```python
@pytest.mark.sdk_assumption
class TestSessionConfigTypeAssumptions:
    """Verify SessionConfig TypedDict has the fields we depend on."""

    def test_session_config_has_available_tools(self, sdk_module):
        """SDK SessionConfig MUST have available_tools field.
        
        If this fails, the SDK changed and F-045 fix needs review.
        """
        from copilot.types import SessionConfig
        annotations = SessionConfig.__annotations__
        assert "available_tools" in annotations

    def test_session_config_has_system_message(self, sdk_module):
        """SDK SessionConfig MUST have system_message field."""
        from copilot.types import SessionConfig
        annotations = SessionConfig.__annotations__
        assert "system_message" in annotations

    def test_session_config_has_excluded_tools(self, sdk_module):
        """SDK SessionConfig has excluded_tools (lower priority than available_tools)."""
        from copilot.types import SessionConfig
        annotations = SessionConfig.__annotations__
        assert "excluded_tools" in annotations

    def test_available_tools_takes_precedence_over_excluded(self, sdk_module):
        """Document: available_tools takes precedence per SDK docs.
        
        SDK ref: copilot/types.py line 493-495 comment
        """
        # This is a documentation test — verifies the comment still exists
        import inspect
        from copilot.types import SessionConfig
        source = inspect.getsource(SessionConfig)
        assert "takes precedence" in source.lower()


@pytest.mark.sdk_assumption
class TestSystemMessageConfigAssumptions:
    """Verify SystemMessageConfig supports replace mode."""

    def test_system_message_config_exists(self, sdk_module):
        """SDK has SystemMessageConfig type."""
        from copilot.types import SystemMessageConfig
        assert SystemMessageConfig is not None

    def test_system_message_config_has_mode(self, sdk_module):
        """SystemMessageConfig has mode field."""
        from copilot.types import SystemMessageConfig
        annotations = SystemMessageConfig.__annotations__
        assert "mode" in annotations

    def test_system_message_config_has_content(self, sdk_module):
        """SystemMessageConfig has content field."""
        from copilot.types import SystemMessageConfig
        annotations = SystemMessageConfig.__annotations__
        assert "content" in annotations


@pytest.mark.sdk_assumption
class TestCopilotClientCreateSessionAssumptions:
    """Verify create_session handles available_tools correctly."""

    def test_client_create_session_accepts_dict(self, sdk_module):
        """create_session accepts a dict (TypedDict is dict at runtime)."""
        import inspect
        sig = inspect.signature(sdk_module.CopilotClient.create_session)
        # Should accept at least one positional arg (the config)
        params = list(sig.parameters.values())
        # First param is self, second is config
        assert len(params) >= 2

    def test_available_tools_none_vs_empty_list(self):
        """Document the critical distinction:
        - None/absent: SDK exposes all built-in tools (DEFAULT)
        - []: SDK exposes NO built-in tools (what we want)
        
        SDK ref: copilot/client.py lines 527-529:
            available_tools = cfg.get("available_tools")
            if available_tools is not None:  # <-- None check, not truthiness!
                payload["availableTools"] = available_tools
        """
        # Simulate the SDK's logic
        cfg_without = {}
        cfg_with_none = {"available_tools": None}
        cfg_with_empty = {"available_tools": []}
        
        # SDK logic: `if available_tools is not None`
        assert cfg_without.get("available_tools") is None  # Won't send
        assert cfg_with_none.get("available_tools") is None  # Won't send
        assert cfg_with_empty.get("available_tools") is not None  # WILL send []
```

---

### Category 4: Live Integration Smoke Tests (ENHANCED)

**File**: `tests/test_live_sdk.py` (enhance existing)

**Purpose**: With real SDK + real API, verify end-to-end behavior.

#### New Tests to Add

```python
@pytest.mark.live
class TestLiveToolSovereignty:
    """Verify Amplifier tools work and SDK tools don't appear."""

    @pytest.mark.asyncio
    async def test_sdk_builtin_tools_not_visible(self):
        """F-045 live verification: SDK built-in tools should not be available.
        
        Creates a session with available_tools=[] and verifies that
        asking for tool use doesn't trigger SDK's bash/edit/view.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()
        try:
            async with wrapper.session(
                model="gpt-4o",
                system_message="You have no tools available. Say 'NO TOOLS' if asked to use tools."
            ) as session:
                response = await session.send_and_wait(
                    {"prompt": "Use the bash tool to run 'echo hello'"}
                )
                # Should NOT crash with JS error
                # Should respond with text (no tool execution)
                assert response is not None
        finally:
            await wrapper.close()

    @pytest.mark.asyncio
    async def test_system_prompt_identity(self):
        """F-044 live verification: Model should follow replace-mode persona.
        
        The model should NOT identify as 'GitHub Copilot CLI'.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()
        try:
            async with wrapper.session(
                model="gpt-4o",
                system_message="You are TestBot. When asked who you are, say 'I am TestBot'."
            ) as session:
                response = await session.send_and_wait(
                    {"prompt": "Who are you? Answer in one sentence."}
                )
                assert response is not None
                content = getattr(getattr(response, 'data', None), 'content', str(response))
                content_lower = content.lower()
                # Should NOT contain default SDK identity
                assert "github copilot cli" not in content_lower, (
                    f"System message replace mode failed. Got: {content}"
                )
        finally:
            await wrapper.close()
```

---

### Category 5: Existing Test Updates (MODIFY)

**File**: `tests/test_sdk_boundary.py`

**Required change**: Update `TestSystemMessageStructure.test_session_system_message_structure` to assert `"replace"` not `"append"`.

```python
# BEFORE (line 125):
assert config["system_message"] == {"mode": "append", "content": "Be helpful"}

# AFTER:
assert config["system_message"] == {"mode": "replace", "content": "Be helpful"}
```

---

## Test Infrastructure: ConfigCapturingMock

**File**: `tests/fixtures/config_capture.py`

```python
"""Fixture for capturing SDK session configuration.

Unlike MagicMock, this fixture:
1. Records the exact dict passed to create_session()
2. Validates it's a dict (not arbitrary args)
3. Returns a minimal but functional mock session
4. Does NOT accept arbitrary method calls
"""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock


class ConfigCapturingMock:
    """Mock SDK client that captures session configuration.
    
    Usage:
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        
        async with wrapper.session(model="gpt-4o"):
            pass
        
        config = mock_client.captured_configs[0]
        assert config["available_tools"] == []
    """

    def __init__(self) -> None:
        self.captured_configs: list[dict[str, Any]] = []
        self._mock_session = self._create_mock_session()

    def _create_mock_session(self) -> Any:
        """Create a minimal mock session with required methods only."""
        session = MagicMock()
        session.session_id = "mock-session-001"
        session.disconnect = AsyncMock()
        session.register_pre_tool_use_hook = MagicMock()
        return session

    async def create_session(self, config: dict[str, Any]) -> Any:
        """Capture config and return mock session."""
        if not isinstance(config, dict):
            raise TypeError(
                f"create_session expects dict, got {type(config).__name__}. "
                f"This mock enforces the SDK contract."
            )
        self.captured_configs.append(copy.deepcopy(config))
        return self._mock_session

    @property
    def last_config(self) -> dict[str, Any]:
        """Most recent captured config."""
        if not self.captured_configs:
            raise AssertionError("No configs captured. Was create_session called?")
        return self.captured_configs[-1]
```

---

## Contract Updates

### `contracts/sdk-boundary.md` — Add Section

```markdown
## Session Configuration Contract

### MUST Constraints

1. **MUST** set `available_tools: []` to disable SDK built-in tools (F-045)
2. **MUST** use `system_message.mode: "replace"` when system_message is provided (F-044)
3. **MUST** set `on_permission_request` handler on every session (F-033)
4. **MUST** set `streaming: true` for event-based tool capture
5. **MUST** register `preToolUse` deny hook after session creation
6. **MUST NOT** include keys that are not in SDK's SessionConfig TypedDict

### Test Anchors

| Anchor | Clause |
|--------|--------|
| `sdk-boundary:Config:MUST:1` | available_tools is empty list |
| `sdk-boundary:Config:MUST:2` | system_message mode is replace |
| `sdk-boundary:Config:MUST:3` | on_permission_request always set |
| `sdk-boundary:Config:MUST:4` | streaming is true |
| `sdk-boundary:Config:MUST:5` | deny hook registered post-creation |
| `sdk-boundary:Config:MUST:6` | no unknown keys in config |
```

---

## Test Pyramid

```
                    ┌──────────────┐
                    │  Live Smoke  │  Tier 7: Real API (nightly)
                    │   5 tests    │  - Identity test
                    │              │  - Tool sovereignty test
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                │  SDK Assumptions    │  Tier 6: Real SDK, no API
                │    12 tests         │  - SessionConfig fields
                │                     │  - SystemMessageConfig
                │                     │  - available_tools semantics
                └──────────┬──────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │  Boundary Contract Tests          │  Tier 5: Config capture
         │    7 tests                         │  - Exact config assertions
         │                                    │  - No MagicMock forgiveness
         └─────────────────┬─────────────────┘
                           │
    ┌──────────────────────┴──────────────────────┐
    │  Configuration Invariant Tests              │  Tier 4: Parameterized
    │    6+ tests (parameterized)                  │  - Invariants across inputs
    │                                              │  - Unknown key detection
    └──────────────────────┬──────────────────────┘
                           │
    ┌──────────────────────┴──────────────────────┐
    │  Existing Unit/Integration Tests            │  Tiers 1-3: Current suite
    │    100+ tests                                │  - Domain logic
    │                                              │  - Error translation
    │                                              │  - Streaming accumulation
    └─────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Create ConfigCapturingMock fixture
- File: `tests/fixtures/config_capture.py`
- No production code changes

### Step 2: Create boundary contract tests (RED)
- File: `tests/test_sdk_boundary_contract.py`
- These tests WILL FAIL until F-044 and F-045 are implemented
- This is intentional — TDD discipline

### Step 3: Create configuration invariant tests (RED)  
- File: `tests/test_session_config_invariants.py`
- These tests WILL FAIL until F-045 is implemented

### Step 4: Implement F-044 (GREEN)
- Change `"append"` to `"replace"` in `client.py` line 221
- Boundary contract test passes

### Step 5: Implement F-045 (GREEN)
- Add `session_config["available_tools"] = []` in `client.py` line ~217
- Boundary contract + invariant tests pass

### Step 6: Update existing test
- Fix `test_sdk_boundary.py` line 125: `"append"` → `"replace"`

### Step 7: Enhance SDK assumption tests
- Add `TestSessionConfigTypeAssumptions` to `test_sdk_assumptions.py`
- Add `TestSystemMessageConfigAssumptions`
- Add `TestCopilotClientCreateSessionAssumptions`

### Step 8: Add live smoke tests
- Add `TestLiveToolSovereignty` to `test_live_sdk.py`
- These only run with `pytest -m live`

### Step 9: Update contract
- Add "Session Configuration Contract" section to `contracts/sdk-boundary.md`

---

## Dev Machine Checklist: Before Marking Any Feature "Done"

The dev machine MUST verify these before marking any SDK-touching feature complete:

1. **Boundary contract tests pass**: `pytest tests/test_sdk_boundary_contract.py -v`
2. **Invariant tests pass**: `pytest tests/test_session_config_invariants.py -v`
3. **No unknown config keys**: The unknown-key test catches typos
4. **SDK assumption tests pass**: `pytest -m sdk_assumption -v`
5. **Full suite green**: `pytest tests/ -v --ignore=tests/test_live_sdk.py`

---

## Why This Architecture Prevents Future F-044/F-045 Bugs

| Bug Pattern | How It's Caught |
|-------------|-----------------|
| Wrong config value (e.g., mode="append") | Boundary contract test: exact value assertion |
| Missing config key (e.g., no available_tools) | Invariant test: key presence check |
| Typo in config key (e.g., "avaliable_tools") | Unknown key test: catches non-SDK keys |
| SDK removes a field we depend on | SDK assumption test: checks type annotations |
| SDK changes behavior of a field | Live smoke test: end-to-end verification |
| Mock forgiveness hides bug | ConfigCapturingMock: type-checked, not MagicMock |

---

## Not In Scope

- Replacing ALL existing MagicMock usage (that's a separate cleanup)
- Testing SDK internals (we test our boundary, not SDK code)
- Performance testing
- Load testing

---

## References

- SDK source: `reference-only/copilot-sdk/python/copilot/types.py` (SessionConfig lines 478-533)
- SDK source: `reference-only/copilot-sdk/python/copilot/client.py` (create_session lines 510-560)
- SDK source: `reference-only/copilot-sdk/python/copilot/session.py` (CopilotSession)
- F-044 spec: `specs/features/F-044-system-prompt-replace-mode.md`
- F-045 spec: `specs/features/F-045-disable-sdk-builtin-tools.md`
- Existing contract: `contracts/sdk-boundary.md`
- Existing contract: `contracts/deny-destroy.md`

---

*Created: 2026-03-14*
*Author: zen-architect (via deep analysis of SDK boundary, test gaps, and root cause investigation)*
