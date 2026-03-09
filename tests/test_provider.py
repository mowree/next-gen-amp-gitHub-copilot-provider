"""
Tests for Provider Orchestrator (F-008).

Contract: provider-protocol.md
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass, field
from typing import Any


# Import the module under test (will fail until implemented)
from amplifier_module_provider_github_copilot.provider import (
    GitHubCopilotProvider,
    ProviderInfo,
    ProviderDefaults,
    ModelInfo,
    ChatRequest,
    ChatResponse,
)
from amplifier_module_provider_github_copilot.tool_parsing import ToolCall


class TestNameProperty:
    """Test provider-protocol:name:MUST clauses."""

    def test_name_returns_github_copilot(self) -> None:
        """provider-protocol:name:MUST:1 - Returns 'github-copilot'."""
        provider = GitHubCopilotProvider()
        assert provider.name == "github-copilot"

    def test_name_is_property(self) -> None:
        """provider-protocol:name:MUST:2 - Is a property, not method."""
        assert isinstance(
            GitHubCopilotProvider.name, property
        ), "name should be a property"


class TestGetInfo:
    """Test provider-protocol:get_info:MUST clauses."""

    def test_get_info_returns_provider_info(self) -> None:
        """provider-protocol:get_info:MUST:1 - Returns valid ProviderInfo."""
        provider = GitHubCopilotProvider()
        info = provider.get_info()
        assert isinstance(info, ProviderInfo)
        assert info.name == "github-copilot"

    def test_get_info_includes_context_window(self) -> None:
        """provider-protocol:get_info:MUST:2 - Includes context_window."""
        provider = GitHubCopilotProvider()
        info = provider.get_info()
        assert hasattr(info, "defaults")
        assert hasattr(info.defaults, "context_window")
        assert info.defaults.context_window > 0


class TestListModels:
    """Test provider-protocol:list_models:MUST clauses."""

    @pytest.mark.asyncio
    async def test_list_models_returns_list(self) -> None:
        """provider-protocol:list_models:MUST:1 - Returns model list."""
        provider = GitHubCopilotProvider()
        models = await provider.list_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert all(isinstance(m, ModelInfo) for m in models)

    @pytest.mark.asyncio
    async def test_list_models_includes_context_window(self) -> None:
        """provider-protocol:list_models:MUST:2 - Includes context_window."""
        provider = GitHubCopilotProvider()
        models = await provider.list_models()
        for model in models:
            assert hasattr(model, "context_window")
            assert model.context_window > 0


class TestComplete:
    """Test provider-protocol:complete:MUST clauses."""

    @pytest.mark.asyncio
    async def test_complete_accepts_kwargs(self) -> None:
        """provider-protocol:complete:MUST:1 - Accepts **kwargs."""
        provider = GitHubCopilotProvider()
        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        
        # Should not raise TypeError for extra kwargs
        # We'll use a mock completion function
        mock_response = ChatResponse(content="Hi there!")
        provider._complete_fn = AsyncMock(return_value=mock_response)
        
        response = await provider.complete(request, extra_param="value")
        assert isinstance(response, ChatResponse)

    @pytest.mark.asyncio
    async def test_complete_returns_chat_response(self) -> None:
        """provider-protocol:complete:MUST:2 - Returns ChatResponse."""
        provider = GitHubCopilotProvider()
        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        
        mock_response = ChatResponse(content="Hello!")
        provider._complete_fn = AsyncMock(return_value=mock_response)
        
        response = await provider.complete(request)
        assert isinstance(response, ChatResponse)
        assert response.content == "Hello!"

    @pytest.mark.asyncio
    async def test_complete_includes_tool_calls(self) -> None:
        """provider-protocol:complete:MUST:2 - ChatResponse includes tool_calls."""
        provider = GitHubCopilotProvider()
        request = ChatRequest(
            messages=[{"role": "user", "content": "Search for X"}],
            tools=[{"name": "search", "description": "Search"}],
        )
        
        mock_response = ChatResponse(
            content="",
            tool_calls=[{"id": "tc1", "name": "search", "arguments": {"q": "X"}}],
        )
        provider._complete_fn = AsyncMock(return_value=mock_response)
        
        response = await provider.complete(request)
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1


class TestParseToolCalls:
    """Test provider-protocol:parse_tool_calls:MUST clauses."""

    def test_parse_tool_calls_extracts_tools(self) -> None:
        """provider-protocol:parse_tool_calls:MUST:1 - Extracts tool calls."""
        provider = GitHubCopilotProvider()
        
        # Create response with tool_calls attribute
        @dataclass
        class MockResponse:
            content: str = ""
            tool_calls: list[Any] = field(default_factory=list)
        
        @dataclass
        class MockToolCall:
            id: str
            name: str
            arguments: dict[str, Any]
        
        response = MockResponse(
            tool_calls=[
                MockToolCall(id="tc1", name="search", arguments={"q": "test"})
            ]
        )
        
        tool_calls = provider.parse_tool_calls(response)
        assert len(tool_calls) == 1
        assert isinstance(tool_calls[0], ToolCall)
        assert tool_calls[0].id == "tc1"
        assert tool_calls[0].name == "search"
        assert tool_calls[0].arguments == {"q": "test"}

    def test_parse_tool_calls_empty_when_none(self) -> None:
        """provider-protocol:parse_tool_calls:MUST:2 - Returns empty list when none."""
        provider = GitHubCopilotProvider()
        
        @dataclass
        class MockResponse:
            content: str = "Just text"
            tool_calls: list[Any] | None = None
        
        response = MockResponse()
        tool_calls = provider.parse_tool_calls(response)
        assert tool_calls == []

    def test_parse_tool_calls_preserves_ids(self) -> None:
        """provider-protocol:parse_tool_calls:MUST:3 - Preserves tool call IDs."""
        provider = GitHubCopilotProvider()
        
        @dataclass
        class MockToolCall:
            id: str
            name: str
            arguments: dict[str, Any]
        
        @dataclass
        class MockResponse:
            tool_calls: list[Any]
        
        response = MockResponse(
            tool_calls=[
                MockToolCall(id="unique-id-123", name="tool", arguments={}),
                MockToolCall(id="unique-id-456", name="tool2", arguments={}),
            ]
        )
        
        tool_calls = provider.parse_tool_calls(response)
        assert tool_calls[0].id == "unique-id-123"
        assert tool_calls[1].id == "unique-id-456"

    def test_parse_tool_calls_uses_arguments_not_input(self) -> None:
        """provider-protocol:parse_tool_calls:MUST:4 - Uses arguments, not input."""
        provider = GitHubCopilotProvider()
        
        @dataclass
        class MockToolCall:
            id: str
            name: str
            arguments: dict[str, Any]
        
        @dataclass
        class MockResponse:
            tool_calls: list[Any]
        
        response = MockResponse(
            tool_calls=[MockToolCall(id="tc1", name="tool", arguments={"key": "value"})]
        )
        
        tool_calls = provider.parse_tool_calls(response)
        assert hasattr(tool_calls[0], "arguments")
        assert tool_calls[0].arguments == {"key": "value"}
