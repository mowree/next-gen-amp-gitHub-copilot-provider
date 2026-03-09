"""
Tests for completion lifecycle module.

Contract: streaming-contract.md, deny-destroy.md
Feature: F-007

Test categories:
- Session lifecycle (create/destroy)
- Event streaming and accumulation
- Error handling and translation
- Response construction
"""

from __future__ import annotations

import pytest
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from amplifier_module_provider_github_copilot.completion import (
    CompletionConfig,
    CompletionRequest,
    complete,
    complete_and_collect,
)
from amplifier_module_provider_github_copilot.streaming import (
    AccumulatedResponse,
    DomainEvent,
    DomainEventType,
    EventConfig,
)
from amplifier_module_provider_github_copilot.error_translation import (
    ErrorConfig,
    LLMError,
    NetworkError,
)
from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig


# === Mock SDK Session ===


class MockSDKSession:
    """Mock SDK session for testing."""

    def __init__(self, events: list[dict[str, Any]] | None = None):
        self.events = events or []
        self.deny_hook = None
        self.disconnected = False

    def register_pre_tool_use_hook(self, hook):
        self.deny_hook = hook

    async def disconnect(self):
        self.disconnected = True

    async def send_message(self, prompt: str, tools: list | None = None) -> AsyncIterator[dict[str, Any]]:
        """Yield mock SDK events."""
        for event in self.events:
            yield event


class MockSDKSessionWithError(MockSDKSession):
    """Mock SDK session that raises error during streaming."""

    def __init__(self, error: Exception, events_before_error: int = 0):
        super().__init__()
        self.error = error
        self.events_before_error = events_before_error
        self._count = 0

    async def send_message(self, prompt: str, tools: list | None = None) -> AsyncIterator[dict[str, Any]]:
        for i in range(self.events_before_error):
            yield {"type": "text_delta", "text": f"chunk{i}"}
            self._count += 1
        raise self.error


# === Fixtures ===


@pytest.fixture
def event_config() -> EventConfig:
    """Minimal event config for testing."""
    from amplifier_module_provider_github_copilot.streaming import EventConfig, DomainEventType
    return EventConfig(
        bridge_mappings={
            "text_delta": (DomainEventType.CONTENT_DELTA, "TEXT"),
            "thinking_delta": (DomainEventType.CONTENT_DELTA, "THINKING"),
            "tool_use_complete": (DomainEventType.TOOL_CALL, None),
            "message_complete": (DomainEventType.TURN_COMPLETE, None),
            "usage_update": (DomainEventType.USAGE_UPDATE, None),
            "error": (DomainEventType.ERROR, None),
        },
        consume_patterns=["tool_use_start", "tool_use_delta"],
        drop_patterns=["heartbeat", "debug_*"],
    )


@pytest.fixture
def error_config() -> ErrorConfig:
    """Minimal error config for testing."""
    from amplifier_module_provider_github_copilot.error_translation import ErrorConfig, ErrorMapping
    return ErrorConfig(
        mappings=[
            ErrorMapping(
                sdk_patterns=["ConnectionError"],
                kernel_error="NetworkError",
                retryable=True,
            ),
        ],
        default_error="ProviderUnavailableError",
        default_retryable=True,
    )


@pytest.fixture
def completion_config(event_config, error_config) -> CompletionConfig:
    """Complete config for testing."""
    return CompletionConfig(
        session_config=SessionConfig(model="gpt-4"),
        event_config=event_config,
        error_config=error_config,
    )


# === Session Lifecycle Tests ===


class TestSessionLifecycle:
    """Test session create/destroy lifecycle."""

    @pytest.mark.asyncio
    async def test_session_created_and_destroyed_on_success(self, completion_config):
        """AC-001: Session destroyed after successful completion."""
        events = [
            {"type": "text_delta", "text": "Hello"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        result = await complete_and_collect(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        )

        assert session.disconnected is True
        assert result.is_complete is True

    @pytest.mark.asyncio
    async def test_session_destroyed_on_error(self, completion_config):
        """AC-001: Session destroyed even when error occurs."""
        error = ConnectionError("Network failed")
        session = MockSDKSessionWithError(error)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        with pytest.raises(LLMError):
            await complete_and_collect(
                request,
                config=completion_config,
                sdk_create_fn=mock_create,
            )

        assert session.disconnected is True

    @pytest.mark.asyncio
    async def test_deny_hook_installed(self, completion_config):
        """AC-001: Deny hook installed on session."""
        events = [{"type": "message_complete", "finish_reason": "stop"}]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        await complete_and_collect(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        )

        assert session.deny_hook is not None


# === Streaming Integration Tests ===


class TestStreamingIntegration:
    """Test event streaming and accumulation."""

    @pytest.mark.asyncio
    async def test_events_yielded_during_streaming(self, completion_config):
        """AC-002: Domain events yielded during streaming."""
        events = [
            {"type": "text_delta", "text": "Hello "},
            {"type": "text_delta", "text": "World"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        yielded_events = []
        async for event in complete(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        ):
            yielded_events.append(event)

        assert len(yielded_events) == 3
        assert yielded_events[0].type == DomainEventType.CONTENT_DELTA
        assert yielded_events[1].type == DomainEventType.CONTENT_DELTA
        assert yielded_events[2].type == DomainEventType.TURN_COMPLETE

    @pytest.mark.asyncio
    async def test_consume_events_not_yielded(self, completion_config):
        """AC-002: Consume events processed internally, not yielded."""
        events = [
            {"type": "tool_use_start", "tool_id": "t1"},  # consume
            {"type": "text_delta", "text": "Hello"},      # bridge
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        yielded_events = []
        async for event in complete(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        ):
            yielded_events.append(event)

        # Only bridge events yielded
        assert len(yielded_events) == 2

    @pytest.mark.asyncio
    async def test_drop_events_not_yielded(self, completion_config):
        """AC-002: Drop events ignored, not yielded."""
        events = [
            {"type": "heartbeat"},  # drop
            {"type": "text_delta", "text": "Hello"},
            {"type": "debug_info", "data": "x"},  # drop via pattern
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        yielded_events = []
        async for event in complete(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        ):
            yielded_events.append(event)

        assert len(yielded_events) == 2


# === Error Handling Tests ===


class TestErrorHandling:
    """Test error translation and propagation."""

    @pytest.mark.asyncio
    async def test_sdk_error_translated(self, completion_config):
        """AC-003: SDK errors translated to kernel types."""
        error = ConnectionError("Connection refused")
        session = MockSDKSessionWithError(error)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        with pytest.raises(NetworkError) as exc_info:
            await complete_and_collect(
                request,
                config=completion_config,
                sdk_create_fn=mock_create,
            )

        assert exc_info.value.provider == "github-copilot"
        assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_error_preserves_original(self, completion_config):
        """AC-003: Original exception chained via __cause__."""
        original = ConnectionError("Original error")
        session = MockSDKSessionWithError(original)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        with pytest.raises(LLMError) as exc_info:
            await complete_and_collect(
                request,
                config=completion_config,
                sdk_create_fn=mock_create,
            )

        assert exc_info.value.__cause__ is original


# === Response Construction Tests ===


class TestResponseConstruction:
    """Test final response construction."""

    @pytest.mark.asyncio
    async def test_text_content_accumulated(self, completion_config):
        """AC-004: Text content accumulated correctly."""
        events = [
            {"type": "text_delta", "text": "Hello "},
            {"type": "text_delta", "text": "World"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        result = await complete_and_collect(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        )

        assert result.text_content == "Hello World"
        assert result.finish_reason == "stop"
        assert result.is_complete is True

    @pytest.mark.asyncio
    async def test_thinking_content_separated(self, completion_config):
        """AC-004: Thinking content accumulated separately."""
        events = [
            {"type": "thinking_delta", "text": "Let me think..."},
            {"type": "text_delta", "text": "The answer is 42"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        result = await complete_and_collect(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        )

        assert result.thinking_content == "Let me think..."
        assert result.text_content == "The answer is 42"

    @pytest.mark.asyncio
    async def test_tool_calls_accumulated(self, completion_config):
        """AC-004: Tool calls accumulated correctly."""
        events = [
            {"type": "tool_use_complete", "tool_id": "t1", "name": "read_file", "arguments": {"path": "/test"}},
            {"type": "tool_use_complete", "tool_id": "t2", "name": "write_file", "arguments": {"path": "/out"}},
            {"type": "message_complete", "finish_reason": "tool_use"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        result = await complete_and_collect(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        )

        assert len(result.tool_calls) == 2
        assert result.tool_calls[0]["name"] == "read_file"
        assert result.tool_calls[1]["name"] == "write_file"
        assert result.finish_reason == "tool_use"

    @pytest.mark.asyncio
    async def test_usage_captured(self, completion_config):
        """AC-004: Usage data captured."""
        events = [
            {"type": "text_delta", "text": "Hello"},
            {"type": "usage_update", "input_tokens": 10, "output_tokens": 5},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        result = await complete_and_collect(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        )

        assert result.usage is not None
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 5

    @pytest.mark.asyncio
    async def test_empty_response_handled(self, completion_config):
        """AC-004: Empty response handled gracefully."""
        events = [
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def mock_create(config):
            return session

        request = CompletionRequest(prompt="test")
        result = await complete_and_collect(
            request,
            config=completion_config,
            sdk_create_fn=mock_create,
        )

        assert result.text_content == ""
        assert result.is_complete is True
