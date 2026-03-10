"""
Tests for deny hook wiring into create_ephemeral_session() (F-010/F-017).

Verifies that deny hook is registered when sdk_create_fn is provided,
and that no-sdk_create_fn path raises ProviderUnavailableError.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestEphemeralSessionDenyHookWiring:
    """Verify deny hook is wired into create_ephemeral_session() via sdk_create_fn."""

    @pytest.mark.asyncio
    async def test_deny_hook_passed_to_sdk_create_fn(self) -> None:
        """create_ephemeral_session() with sdk_create_fn must register deny hook."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig
        from amplifier_module_provider_github_copilot.session_factory import (
            create_ephemeral_session,
        )

        mock_session = MagicMock()
        mock_session.register_pre_tool_use_hook = MagicMock()
        mock_create = AsyncMock(return_value=mock_session)

        config = SessionConfig(model="gpt-4o")
        await create_ephemeral_session(config, sdk_create_fn=mock_create)

        # Verify deny hook was registered
        mock_session.register_pre_tool_use_hook.assert_called_once()
        hook = mock_session.register_pre_tool_use_hook.call_args[0][0]
        assert callable(hook)

    @pytest.mark.asyncio
    async def test_no_sdk_create_fn_raises_provider_unavailable(self) -> None:
        """create_ephemeral_session() without sdk_create_fn raises ProviderUnavailableError."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ProviderUnavailableError,
        )
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig
        from amplifier_module_provider_github_copilot.session_factory import (
            create_ephemeral_session,
        )

        config = SessionConfig(model="gpt-4o")
        with pytest.raises(ProviderUnavailableError):
            await create_ephemeral_session(config)
