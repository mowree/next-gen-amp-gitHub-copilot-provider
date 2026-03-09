"""
Tests for tool parsing module.

Contract: provider-protocol.md (parse_tool_calls method)
"""

from dataclasses import dataclass
from typing import Any

import pytest


# Mock types for testing (before implementation exists)
@dataclass
class MockToolCall:
    """Mock tool call from SDK response."""

    id: str
    name: str
    arguments: dict[str, Any] | str


@dataclass
class MockChatResponse:
    """Mock ChatResponse for testing."""

    content: list[Any]
    tool_calls: list[MockToolCall] | None = None


class TestParseToolCalls:
    """Tests for parse_tool_calls function."""

    def test_empty_tool_calls_returns_empty_list(self):
        """No tool_calls in response → empty list."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(content=[], tool_calls=None)
        result = parse_tool_calls(response)
        assert result == []

    def test_empty_list_tool_calls_returns_empty_list(self):
        """Empty tool_calls list → empty list."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(content=[], tool_calls=[])
        result = parse_tool_calls(response)
        assert result == []

    def test_single_tool_call_parsed(self):
        """Single tool call extracted correctly."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(
            content=[],
            tool_calls=[MockToolCall(id="tc1", name="read_file", arguments={"path": "test.py"})],
        )
        result = parse_tool_calls(response)
        assert len(result) == 1
        assert result[0].id == "tc1"
        assert result[0].name == "read_file"
        assert result[0].arguments == {"path": "test.py"}

    def test_multiple_tool_calls_parsed(self):
        """Multiple tool calls all extracted."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(
            content=[],
            tool_calls=[
                MockToolCall(id="tc1", name="read_file", arguments={"path": "a.py"}),
                MockToolCall(
                    id="tc2", name="write_file", arguments={"path": "b.py", "content": "hello"}
                ),
                MockToolCall(id="tc3", name="bash", arguments={"command": "ls"}),
            ],
        )
        result = parse_tool_calls(response)
        assert len(result) == 3
        assert result[0].name == "read_file"
        assert result[1].name == "write_file"
        assert result[2].name == "bash"

    def test_string_arguments_parsed_as_json(self):
        """String arguments are JSON-parsed."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(
            content=[],
            tool_calls=[MockToolCall(id="tc1", name="bash", arguments='{"command": "ls -la"}')],
        )
        result = parse_tool_calls(response)
        assert result[0].arguments == {"command": "ls -la"}

    def test_invalid_json_raises_value_error(self):
        """Invalid JSON arguments raise ValueError."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(
            content=[],
            tool_calls=[MockToolCall(id="tc1", name="bash", arguments="{invalid json}")],
        )
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_tool_calls(response)


class TestToolCallType:
    """Tests for ToolCall dataclass."""

    def test_tool_call_has_arguments_not_input(self):
        """ToolCall uses 'arguments' field per kernel contract (E3)."""
        from amplifier_module_provider_github_copilot.tool_parsing import ToolCall

        tc = ToolCall(id="1", name="test", arguments={"key": "value"})
        assert hasattr(tc, "arguments")
        assert not hasattr(tc, "input")

    def test_tool_call_fields(self):
        """ToolCall has required fields: id, name, arguments."""
        from amplifier_module_provider_github_copilot.tool_parsing import ToolCall

        tc = ToolCall(id="tc-123", name="read_file", arguments={"path": "/etc/hosts"})
        assert tc.id == "tc-123"
        assert tc.name == "read_file"
        assert tc.arguments == {"path": "/etc/hosts"}

    def test_tool_call_empty_arguments(self):
        """ToolCall can have empty arguments dict."""
        from amplifier_module_provider_github_copilot.tool_parsing import ToolCall

        tc = ToolCall(id="1", name="get_time", arguments={})
        assert tc.arguments == {}


class TestEdgeCases:
    """Edge case tests for tool parsing."""

    def test_nested_arguments(self):
        """Nested dict arguments are preserved."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        nested = {"config": {"nested": {"deep": "value"}}, "list": [1, 2, 3]}
        response = MockChatResponse(
            content=[],
            tool_calls=[MockToolCall(id="tc1", name="complex", arguments=nested)],
        )
        result = parse_tool_calls(response)
        assert result[0].arguments == nested

    def test_unicode_in_arguments(self):
        """Unicode characters in arguments are preserved."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(
            content=[],
            tool_calls=[MockToolCall(id="tc1", name="write", arguments={"text": "Hello 世界 🌍"})],
        )
        result = parse_tool_calls(response)
        assert result[0].arguments["text"] == "Hello 世界 🌍"

    def test_special_characters_in_tool_name(self):
        """Tool names with special characters are preserved."""
        from amplifier_module_provider_github_copilot.tool_parsing import parse_tool_calls

        response = MockChatResponse(
            content=[],
            tool_calls=[MockToolCall(id="tc1", name="mcp_server:read_file", arguments={})],
        )
        result = parse_tool_calls(response)
        assert result[0].name == "mcp_server:read_file"
