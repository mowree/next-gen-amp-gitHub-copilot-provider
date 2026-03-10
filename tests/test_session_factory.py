"""
Tests for Session Factory (F-003).

Contract: contracts/deny-destroy.md
Feature: specs/features/F-003-session-factory.md

Acceptance Criteria:
- AC-1: Session created with deny hook registered
- AC-2: Deny hook returns denial for all tool calls
- AC-3: destroy_session calls disconnect()
- AC-4: destroy_session handles already-destroyed gracefully
- AC-5: No tool execution occurs (tools are captured, not executed)
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# Mock SDK types for testing
@dataclass
class MockToolRequest:
    """Mock SDK tool request."""

    name: str
    arguments: dict[str, Any]


class MockSDKSession:
    """Mock SDK session for testing."""

    def __init__(self) -> None:
        self.connected = True
        self.pre_tool_use_hook: Callable[..., Any] | None = None
        self.disconnect_called = False

    def register_pre_tool_use_hook(self, hook: Callable[..., Any]) -> None:
        """Register a preToolUse hook."""
        self.pre_tool_use_hook = hook

    async def disconnect(self) -> None:
        """Disconnect the session."""
        if not self.connected:
            raise RuntimeError("Session already disconnected")
        self.connected = False
        self.disconnect_called = True


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


class TestCreateEphemeralSession:
    """Test ephemeral session creation."""

    def test_create_ephemeral_session_exists(self) -> None:
        """create_ephemeral_session function exists."""
        from amplifier_module_provider_github_copilot.session_factory import (
            create_ephemeral_session,
        )

        assert callable(create_ephemeral_session)

    @pytest.mark.asyncio
    async def test_session_created_with_deny_hook(self) -> None:
        """AC-1: Session created with deny hook registered."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import (
            SessionConfig,
        )
        from amplifier_module_provider_github_copilot.session_factory import (
            create_ephemeral_session,
        )

        config = SessionConfig(model="gpt-4")

        # Create mock SDK driver
        mock_sdk_session = MockSDKSession()
        mock_create = AsyncMock(return_value=mock_sdk_session)

        _session = await create_ephemeral_session(config, sdk_create_fn=mock_create)

        # Verify hook was registered (session itself is opaque)
        assert mock_sdk_session.pre_tool_use_hook is not None
        assert callable(mock_sdk_session.pre_tool_use_hook)

    @pytest.mark.asyncio
    async def test_deny_hook_is_always_installed(self) -> None:
        """AC-1: Deny hook MUST be installed on every session."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import (
            SessionConfig,
        )
        from amplifier_module_provider_github_copilot.session_factory import (
            create_ephemeral_session,
        )

        config = SessionConfig(model="gpt-4")
        mock_sdk_session = MockSDKSession()
        mock_create = AsyncMock(return_value=mock_sdk_session)

        # Even with deny_all_tools=True (default), hook must be installed
        await create_ephemeral_session(config, sdk_create_fn=mock_create)
        assert mock_sdk_session.pre_tool_use_hook is not None


class TestDestroySession:
    """Test session destruction."""

    def test_destroy_session_exists(self) -> None:
        """destroy_session function exists."""
        from amplifier_module_provider_github_copilot.session_factory import (
            destroy_session,
        )

        assert callable(destroy_session)

    @pytest.mark.asyncio
    async def test_destroy_session_calls_disconnect(self) -> None:
        """AC-3: destroy_session calls disconnect()."""
        from amplifier_module_provider_github_copilot.session_factory import (
            destroy_session,
        )

        mock_session = MockSDKSession()
        await destroy_session(mock_session)

        assert mock_session.disconnect_called

    @pytest.mark.asyncio
    async def test_destroy_handles_already_destroyed(self) -> None:
        """AC-4: destroy_session handles already-destroyed gracefully."""
        from amplifier_module_provider_github_copilot.session_factory import (
            destroy_session,
        )

        mock_session = MockSDKSession()
        mock_session.connected = False

        # Should not raise, even if already disconnected
        await destroy_session(mock_session)
        # No assertion needed - test passes if no exception

    @pytest.mark.asyncio
    async def test_destroy_logs_on_error(self) -> None:
        """Edge case: Disconnect raises - should log, not propagate."""
        from amplifier_module_provider_github_copilot.session_factory import (
            destroy_session,
        )

        mock_session = MagicMock()
        mock_session.disconnect = AsyncMock(side_effect=RuntimeError("SDK error"))

        # Should not raise
        await destroy_session(mock_session)


class TestSessionLifecycle:
    """Test full session lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Contract: Session lifecycle is create -> use -> destroy."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import (
            SessionConfig,
        )
        from amplifier_module_provider_github_copilot.session_factory import (
            create_ephemeral_session,
            destroy_session,
        )

        config = SessionConfig(model="gpt-4")
        mock_sdk_session = MockSDKSession()
        mock_create = AsyncMock(return_value=mock_sdk_session)

        # Create
        session = await create_ephemeral_session(config, sdk_create_fn=mock_create)
        assert session is not None
        assert mock_sdk_session.pre_tool_use_hook is not None

        # Use (verify hook denies) - hook is async
        result = await mock_sdk_session.pre_tool_use_hook(None, None)
        assert result["permissionDecision"] == "deny"

        # Destroy
        await destroy_session(session)
        assert mock_sdk_session.disconnect_called
