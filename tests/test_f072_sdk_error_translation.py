"""Tests for F-072: Real SDK Path Error Translation.

Feature: F-072, F-073
Contract: contracts/error-hierarchy.md - "The provider MUST translate SDK errors into kernel error types"

These tests verify that exceptions raised during the real SDK path are properly
translated to kernel error types via translate_sdk_error().
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from amplifier_module_provider_github_copilot.error_translation import (
    AuthenticationError,
    LLMError,
    LLMTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from amplifier_module_provider_github_copilot.provider import (
    CompletionRequest,
    GitHubCopilotProvider,
)


@pytest.fixture
def provider_with_mock_client():
    """Create provider with a mocked _client attribute."""
    provider = GitHubCopilotProvider()
    mock_client = MagicMock()
    provider._client = mock_client
    return provider, mock_client


def create_mock_session_ctx(send_and_wait_side_effect=None, send_and_wait_return=None):
    """Create an async context manager that yields a mock session."""

    @asynccontextmanager
    async def session_ctx(model: str):
        mock_session = MagicMock()
        if send_and_wait_side_effect:
            mock_session.send_and_wait = AsyncMock(side_effect=send_and_wait_side_effect)
        else:
            mock_session.send_and_wait = AsyncMock(return_value=send_and_wait_return)
        yield mock_session

    return session_ctx


class TestRealSDKPathErrorTranslation:
    """Tests for F-072: Real SDK path error translation."""

    @pytest.mark.asyncio
    async def test_timeout_error_translated(self, provider_with_mock_client):
        """TimeoutError from SDK is translated to LLMTimeoutError.

        Contract: error-hierarchy.md - TimeoutError -> LLMTimeoutError
        """
        provider, mock_client = provider_with_mock_client
        mock_client.session = create_mock_session_ctx(
            send_and_wait_side_effect=TimeoutError("SDK timeout")
        )

        request = CompletionRequest(prompt="test", model="gpt-4o")

        with pytest.raises(LLMTimeoutError):
            await provider.complete(request)

    @pytest.mark.asyncio
    async def test_auth_like_error_translated(self, provider_with_mock_client):
        """Auth-like errors from SDK are translated to AuthenticationError.

        Contract: error-hierarchy.md - PermissionError, 401/403 -> AuthenticationError
        """
        provider, mock_client = provider_with_mock_client
        mock_client.session = create_mock_session_ctx(
            send_and_wait_side_effect=PermissionError("401 Unauthorized")
        )

        request = CompletionRequest(prompt="test", model="gpt-4o")

        with pytest.raises(AuthenticationError):
            await provider.complete(request)

    @pytest.mark.asyncio
    async def test_generic_error_translated_to_provider_unavailable(
        self, provider_with_mock_client
    ):
        """Generic RuntimeError is translated to ProviderUnavailableError (fallback).

        Contract: error-hierarchy.md - Unknown errors -> ProviderUnavailableError
        """
        provider, mock_client = provider_with_mock_client
        mock_client.session = create_mock_session_ctx(
            send_and_wait_side_effect=RuntimeError("Some SDK failure")
        )

        request = CompletionRequest(prompt="test", model="gpt-4o")

        with pytest.raises(ProviderUnavailableError):
            await provider.complete(request)

    @pytest.mark.asyncio
    async def test_llm_error_passes_through_unchanged(self, provider_with_mock_client):
        """Already-translated LLMError subclasses pass through without double-wrapping.

        Contract: F-072 - LLMError subclasses must not be double-wrapped
        """
        provider, mock_client = provider_with_mock_client
        # Create an already-translated error
        original_error = RateLimitError(
            "Rate limited", provider="github-copilot", retry_after=30.0
        )
        mock_client.session = create_mock_session_ctx(
            send_and_wait_side_effect=original_error
        )

        request = CompletionRequest(prompt="test", model="gpt-4o")

        with pytest.raises(RateLimitError) as exc_info:
            await provider.complete(request)

        # Verify it's the exact same error, not a wrapped one
        assert exc_info.value is original_error
        assert exc_info.value.retry_after == 30.0

    @pytest.mark.asyncio
    async def test_connection_error_translated(self, provider_with_mock_client):
        """ConnectionError from SDK is translated appropriately.

        Contract: error-hierarchy.md - Connection errors -> appropriate mapping
        """
        provider, mock_client = provider_with_mock_client
        mock_client.session = create_mock_session_ctx(
            send_and_wait_side_effect=ConnectionError("Connection refused")
        )

        request = CompletionRequest(prompt="test", model="gpt-4o")

        # Should translate to some LLMError subclass (likely ProviderUnavailableError)
        with pytest.raises(LLMError):
            await provider.complete(request)


class TestF078ContextWindowFallback:
    """Tests for F-078: context_window in fallback config."""

    def test_fallback_config_has_context_window(self):
        """Fallback config must include context_window for budget calculation.

        Contract: provider-protocol.md - "MUST include defaults.context_window"
        Feature: F-078
        """
        from amplifier_module_provider_github_copilot.provider import (
            _default_provider_config,
        )

        fallback = _default_provider_config()

        # Key assertion: context_window must exist
        assert "context_window" in fallback.defaults
        # Should be a reasonable default (128000 per spec)
        assert fallback.defaults["context_window"] == 128000

    def test_fallback_config_budget_calculation_succeeds(self):
        """Budget calculation should work with fallback config.

        Feature: F-078 - Budget calculation must succeed when models.yaml fails to load
        """
        from amplifier_module_provider_github_copilot.provider import (
            _default_provider_config,
        )

        fallback = _default_provider_config()

        # Simulate budget calculation (would fail without context_window)
        context_window = fallback.defaults.get("context_window")
        max_tokens = fallback.defaults.get("max_tokens", 4096)

        # This should not raise
        remaining_budget = context_window - max_tokens
        assert remaining_budget > 0
