"""F-043: TDD Discipline and E2E Coverage Tests.

Tests for SDK response extraction bug fix.
Contract: streaming-contract.md, sdk-response.md

The bug: SDK returns Data(content="actual text") but code does str(Data(...))
which produces repr dump instead of extracting .content attribute.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import realistic fixtures from the fixtures module
from tests.fixtures.sdk_responses import (
    MockData,
    MockSDKResponse,
)


class TestSDKResponseExtraction:
    """AC-1: Fix SDK response extraction to handle Data.content attribute."""

    def test_extracts_content_from_data_object(self) -> None:
        """MUST extract .content from Data objects, not str() them.

        Contract: sdk-response.md

        This is the critical bug: provider was doing str(Data(...)) which
        produces "Data(content='hello', role='assistant', ...)" instead of "hello".
        """
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        data = MockData(content="Hello, world!")
        result = extract_response_content(data)

        # MUST be plain text, NOT repr dump
        assert result == "Hello, world!"
        assert "Data(" not in result  # No dataclass repr
        assert "content=" not in result  # No field name in output

    def test_extracts_content_from_response_wrapper(self) -> None:
        """MUST handle response.data -> Data.content path."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        response = MockSDKResponse(data=MockData(content="Nested content"))
        result = extract_response_content(response)

        assert result == "Nested content"

    def test_handles_dict_response(self) -> None:
        """MUST still handle dict responses (backward compat)."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        response: dict[str, Any] = {"content": "Dict content"}
        result = extract_response_content(response)

        assert result == "Dict content"

    def test_handles_nested_dict_in_data(self) -> None:
        """MUST handle response.data as dict."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        response = MockSDKResponse(data={"content": "Nested dict content"})
        result = extract_response_content(response)

        assert result == "Nested dict content"

    def test_handles_empty_content(self) -> None:
        """MUST handle empty content gracefully."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        data = MockData(content="")
        result = extract_response_content(data)

        assert result == ""

    def test_handles_none_response(self) -> None:
        """MUST handle None response gracefully."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        result = extract_response_content(None)

        assert result == ""

    def test_handles_data_none(self) -> None:
        """MUST handle response.data = None gracefully."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        response = MockSDKResponse(data=None)
        result = extract_response_content(response)

        assert result == ""

    def test_handles_content_none(self) -> None:
        """MUST handle .content = None gracefully."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        # Create mock with content=None but NO .data attribute
        # MagicMock auto-creates attributes, causing infinite recursion
        # Use spec to restrict available attributes
        mock_data = MagicMock(spec=["content"])
        mock_data.content = None
        result = extract_response_content(mock_data)

        assert result == ""

    def test_object_with_both_data_and_content_prefers_data(self) -> None:
        """MUST prefer .data over .content when both present (unwrap first)."""
        from amplifier_module_provider_github_copilot.provider import (
            extract_response_content,
        )

        # Object with both .data and .content
        mock_response = MagicMock()
        mock_response.data = MockData(content="from data")
        mock_response.content = "from content"

        result = extract_response_content(mock_response)

        # Should get content from .data path, not direct .content
        assert result == "from data"


class TestE2ECompletionWithRealisticData:
    """AC-2: E2E test with realistic SDK response shapes."""

    @pytest.mark.asyncio
    async def test_complete_returns_text_not_repr(self) -> None:
        """complete() MUST return plain text content, not Data repr.

        This is the E2E test that would have caught the original bug.
        """
        from amplifier_module_provider_github_copilot.provider import (
            CompletionRequest,
            GitHubCopilotProvider,
        )

        # Create realistic SDK response using fixtures
        sdk_response = MagicMock()
        sdk_response.data = MockData(content="This is the actual response text.")

        # Create mock session that returns realistic response
        mock_session = AsyncMock()
        mock_session.send_and_wait = AsyncMock(return_value=sdk_response)

        # Create provider with mock client
        provider = GitHubCopilotProvider()
        # Override client for testing (accessing protected member in test is acceptable)
        provider._client = MagicMock()  # type: ignore[assignment]
        provider._client.session = MagicMock()  # type: ignore[union-attr]

        # Mock context manager
        async_cm = AsyncMock()
        async_cm.__aenter__ = AsyncMock(return_value=mock_session)
        async_cm.__aexit__ = AsyncMock(return_value=None)
        provider._client.session.return_value = async_cm  # type: ignore[union-attr]

        # Execute completion
        request = CompletionRequest(prompt="Hello")
        response = await provider.complete(request)

        # MUST contain plain text, not repr dump
        content_text = ""
        for block in response.content:
            text = getattr(block, "text", None)
            if text is not None:
                content_text += str(text)

        assert content_text == "This is the actual response text."
        assert "Data(" not in content_text
        assert "content=" not in content_text
