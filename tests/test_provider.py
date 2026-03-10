"""
Tests for Provider Orchestrator (F-008).

Contract: provider-protocol.md
"""

from dataclasses import dataclass, field
from typing import Any

from amplifier_module_provider_github_copilot.provider import (
    GitHubCopilotProvider,
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
        assert isinstance(GitHubCopilotProvider.name, property), "name should be a property"


class TestParseToolCalls:
    """Test provider-protocol:parse_tool_calls:MUST clauses."""

    def test_parse_tool_calls_extracts_tools(self) -> None:
        """provider-protocol:parse_tool_calls:MUST:1 - Extracts tool calls."""
        provider = GitHubCopilotProvider()

        @dataclass
        class MockResponse:
            content: str = ""
            tool_calls: list[Any] = field(default_factory=lambda: [])

        @dataclass
        class MockToolCall:
            id: str
            name: str
            arguments: dict[str, Any]

        response = MockResponse(
            tool_calls=[MockToolCall(id="tc1", name="search", arguments={"q": "test"})]
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
