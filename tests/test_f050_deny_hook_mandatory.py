"""
Tests for F-050: Mandatory Deny Hook Installation.

Contract: deny-destroy:DenyHook:MUST:1
Feature: F-050

The deny hook installation MUST be mandatory. If the SDK session lacks
register_pre_tool_use_hook method, a ProviderUnavailableError MUST be raised.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from amplifier_module_provider_github_copilot.error_translation import ProviderUnavailableError
from amplifier_module_provider_github_copilot.provider import (
    CompletionConfig,
    CompletionRequest,
    complete,
)
from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper


class TestDenyHookMandatoryProvider:
    """Tests for mandatory deny hook in provider.py complete() path."""

    @pytest.mark.asyncio
    async def test_raises_when_session_lacks_hook_method(self) -> None:
        """deny-destroy:DenyHook:MUST:1 - raises when hook method absent.

        When SDK session doesn't have register_pre_tool_use_hook method,
        complete() MUST raise ProviderUnavailableError.
        """
        # Create mock session WITHOUT register_pre_tool_use_hook
        mock_session = MagicMock(spec=["send_message", "disconnect"])
        mock_session.send_message = AsyncMock(return_value=iter([]))

        async def sdk_create_fn(config: MagicMock) -> MagicMock:
            return mock_session

        request = CompletionRequest(prompt="test")

        with pytest.raises(ProviderUnavailableError) as exc_info:
            async for _ in complete(request, sdk_create_fn=sdk_create_fn):
                pass

        assert "register_pre_tool_use_hook" in str(exc_info.value)
        assert "deny hook cannot be installed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_registers_hook_when_method_present(self) -> None:
        """deny-destroy:DenyHook:MUST:1 - hook registered when method present.

        When SDK session has register_pre_tool_use_hook, it MUST be called.
        """
        # Create mock session WITH register_pre_tool_use_hook
        mock_session = MagicMock(spec=["send_message", "disconnect", "register_pre_tool_use_hook"])
        mock_session.send_message = AsyncMock(return_value=iter([]))
        mock_session.disconnect = AsyncMock()
        mock_session.register_pre_tool_use_hook = MagicMock()

        async def sdk_create_fn(config: MagicMock) -> MagicMock:
            return mock_session

        request = CompletionRequest(prompt="test")

        # Should not raise
        async for _ in complete(request, sdk_create_fn=sdk_create_fn):
            pass

        # Verify hook was registered
        mock_session.register_pre_tool_use_hook.assert_called_once()


class TestDenyHookMandatoryClient:
    """Tests for mandatory deny hook in client.py session() path."""

    @pytest.mark.asyncio
    async def test_raises_when_sdk_session_lacks_hook_method(self) -> None:
        """deny-destroy:DenyHook:MUST:1 - client raises when hook method absent.

        When SDK session created by client.create_session() doesn't have
        register_pre_tool_use_hook, session() MUST raise ProviderUnavailableError.
        """
        # Create mock client that returns session WITHOUT hook method
        mock_sdk_client = MagicMock()
        mock_session = MagicMock(spec=["disconnect", "send_and_wait", "session_id"])
        mock_session.session_id = "test-session-123"
        mock_session.disconnect = AsyncMock()
        mock_sdk_client.create_session = AsyncMock(return_value=mock_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)

        with pytest.raises(ProviderUnavailableError) as exc_info:
            async with wrapper.session(model="gpt-4"):
                pass

        assert "register_pre_tool_use_hook" in str(exc_info.value)
        assert "deny hook cannot be installed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_registers_hook_when_sdk_session_has_method(self) -> None:
        """deny-destroy:DenyHook:MUST:1 - client registers hook when present.

        When SDK session has register_pre_tool_use_hook, it MUST be called.
        """
        # Create mock client that returns session WITH hook method
        mock_sdk_client = MagicMock()
        mock_session = MagicMock(
            spec=["disconnect", "send_and_wait", "session_id", "register_pre_tool_use_hook"]
        )
        mock_session.session_id = "test-session-123"
        mock_session.disconnect = AsyncMock()
        mock_session.register_pre_tool_use_hook = MagicMock()
        mock_sdk_client.create_session = AsyncMock(return_value=mock_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)

        # Should not raise
        async with wrapper.session(model="gpt-4"):
            pass

        # Verify hook was registered
        mock_session.register_pre_tool_use_hook.assert_called_once()
