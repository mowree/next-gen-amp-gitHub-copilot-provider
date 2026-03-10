"""
Tests for create_session() in driver.py (F-010, Task 2).

Acceptance Criteria:
- create_session() calls _get_client() to get the SDK client
- Passes model from config to client.create_session()
- Passes deny_hook as on_pre_tool_use when provided
- Passes empty tools list (NEVER registers SDK tools)
- Returns the session from client.create_session()
- Works without deny_hook (hooks dict is empty)
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCreateSession:
    """F-010: create_session() integrates with SDK via _get_client()."""

    @pytest.mark.asyncio
    async def test_create_session_calls_get_client(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """create_session() must call _get_client() to retrieve the SDK client."""
        import amplifier_module_provider_github_copilot.sdk_adapter.driver as driver_mod
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)
        mock_get_client = AsyncMock(return_value=mock_client)

        monkeypatch.setattr(driver_mod, "_get_client", mock_get_client)

        config = SessionConfig(model="gpt-4o")
        await driver_mod.create_session(config)

        mock_get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_passes_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """create_session() must pass config.model to client.create_session()."""
        import amplifier_module_provider_github_copilot.sdk_adapter.driver as driver_mod
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        monkeypatch.setattr(driver_mod, "_get_client", AsyncMock(return_value=mock_client))

        config = SessionConfig(model="claude-3-5-sonnet")
        await driver_mod.create_session(config)

        call_args = mock_client.create_session.call_args[0][0]
        assert call_args["model"] == "claude-3-5-sonnet"

    @pytest.mark.asyncio
    async def test_create_session_passes_empty_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """create_session() must pass empty tools list - NEVER register SDK tools."""
        import amplifier_module_provider_github_copilot.sdk_adapter.driver as driver_mod
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        monkeypatch.setattr(driver_mod, "_get_client", AsyncMock(return_value=mock_client))

        config = SessionConfig(model="gpt-4o")
        await driver_mod.create_session(config)

        call_args = mock_client.create_session.call_args[0][0]
        assert call_args["tools"] == []

    @pytest.mark.asyncio
    async def test_create_session_with_deny_hook(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """create_session() must set deny_hook as on_pre_tool_use when provided."""
        import amplifier_module_provider_github_copilot.sdk_adapter.driver as driver_mod
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        monkeypatch.setattr(driver_mod, "_get_client", AsyncMock(return_value=mock_client))

        deny_hook: Callable[..., Any] = MagicMock()
        config = SessionConfig(model="gpt-4o")
        await driver_mod.create_session(config, deny_hook=deny_hook)

        call_args = mock_client.create_session.call_args[0][0]
        assert call_args["hooks"]["on_pre_tool_use"] is deny_hook

    @pytest.mark.asyncio
    async def test_create_session_without_deny_hook_has_empty_hooks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_session() without deny_hook must pass empty hooks dict."""
        import amplifier_module_provider_github_copilot.sdk_adapter.driver as driver_mod
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        monkeypatch.setattr(driver_mod, "_get_client", AsyncMock(return_value=mock_client))

        config = SessionConfig(model="gpt-4o")
        await driver_mod.create_session(config)

        call_args = mock_client.create_session.call_args[0][0]
        assert call_args["hooks"] == {}

    @pytest.mark.asyncio
    async def test_create_session_returns_sdk_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """create_session() must return the session from client.create_session()."""
        import amplifier_module_provider_github_copilot.sdk_adapter.driver as driver_mod
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        monkeypatch.setattr(driver_mod, "_get_client", AsyncMock(return_value=mock_client))

        config = SessionConfig(model="gpt-4o")
        result = await driver_mod.create_session(config)

        assert result is mock_session
