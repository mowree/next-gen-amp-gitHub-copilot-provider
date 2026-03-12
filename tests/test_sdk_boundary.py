"""
Tests for F-023 AC-2, AC-3, AC-5, AC-6: SDK Boundary Tests.

Contract: contracts/sdk-boundary.md, contracts/deny-destroy.md
Feature: specs/features/F-023-test-coverage.md
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplifier_module_provider_github_copilot.error_translation import (
    AuthenticationError,
    LLMError,
)
from amplifier_module_provider_github_copilot.sdk_adapter.client import (
    CopilotClientWrapper,
)


class TestSDKImportError:
    """AC-2: SDK ImportError raises ProviderUnavailableError."""

    @pytest.mark.asyncio
    async def test_sdk_import_error_raises_provider_unavailable(self) -> None:
        """Missing SDK raises ProviderUnavailableError or other LLMError."""
        # Remove copilot from sys.modules if present to force ImportError
        copilot_module = sys.modules.pop("copilot", None)
        try:
            # Patch sys.modules to make import fail
            with patch.dict(sys.modules, {"copilot": None}):
                wrapper = CopilotClientWrapper()

                # Should raise some form of LLMError (ImportError -> ProviderUnavailableError)
                with pytest.raises(LLMError):
                    async with wrapper.session():
                        pass  # pragma: no cover
        finally:
            # Restore copilot module if it was present
            if copilot_module is not None:
                sys.modules["copilot"] = copilot_module


class TestDenyHookOnWrapper:
    """AC-3: Deny hook registered on CopilotClientWrapper.session() path."""

    @pytest.mark.asyncio
    async def test_deny_hook_registered_on_wrapper_session(self) -> None:
        """CopilotClientWrapper.session() registers deny hook."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        mock_session = MagicMock()
        mock_session.register_pre_tool_use_hook = MagicMock()
        mock_session.disconnect = AsyncMock()

        mock_client = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        async with wrapper.session():
            pass

        # Verify deny hook was registered
        mock_session.register_pre_tool_use_hook.assert_called_once()


class TestDoubleTranslationGuard:
    """AC-5: LLMError not double-wrapped."""

    @pytest.mark.asyncio
    async def test_llm_error_not_double_wrapped(self) -> None:
        """LLMError raised inside complete() is not re-translated."""
        from amplifier_module_provider_github_copilot.provider import (
            CompletionRequest,
            complete,
        )

        # Create a mock session factory that raises AuthenticationError
        async def failing_sdk_fn(config: object) -> AsyncMock:
            raise AuthenticationError("Already translated", provider="test")

        request = CompletionRequest(prompt="Hello", model="gpt-4")

        caught_error: AuthenticationError | None = None
        try:
            async for _ in complete(request, sdk_create_fn=failing_sdk_fn):
                pass  # pragma: no cover
        except AuthenticationError as e:
            caught_error = e

        # Should have caught the error
        assert caught_error is not None
        # Should NOT be wrapped in another error
        assert caught_error.__cause__ is None
        assert caught_error.provider == "test"


class TestSystemMessageStructure:
    """AC-6: system_message parameter structure."""

    @pytest.mark.asyncio
    async def test_session_system_message_structure(self) -> None:
        """system_message is passed with correct structure."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        mock_session = MagicMock()
        mock_session.disconnect = AsyncMock()

        mock_client = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        async with wrapper.session(system_message="Be helpful"):
            pass

        call_args = mock_client.create_session.call_args
        config = call_args[0][0]  # First positional arg is the config dict
        assert config["system_message"] == {"mode": "append", "content": "Be helpful"}

    @pytest.mark.asyncio
    async def test_session_without_system_message(self) -> None:
        """Session config omits system_message when not provided."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        mock_session = MagicMock()
        mock_session.disconnect = AsyncMock()

        mock_client = AsyncMock()
        mock_client.create_session = AsyncMock(return_value=mock_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_client)
        async with wrapper.session(model="gpt-4"):
            pass

        call_args = mock_client.create_session.call_args
        config = call_args[0][0]
        assert "system_message" not in config
        assert config["model"] == "gpt-4"
