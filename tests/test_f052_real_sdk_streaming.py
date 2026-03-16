"""Tests for F-052: Real SDK Streaming Pipeline.

Contract: streaming-contract.md, event-vocabulary.md
Feature: F-052

These tests verify that the real SDK path uses streaming iteration
instead of send_and_wait, routing events through the translation pipeline.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from amplifier_module_provider_github_copilot.provider import (
    CompletionRequest,
    GitHubCopilotProvider,
)
from amplifier_module_provider_github_copilot.streaming import (
    DomainEvent,
    DomainEventType,
)


class MockSDKEvent:
    """Mock SDK event with type attribute."""

    def __init__(self, event_type: str, **kwargs):
        self.type = event_type
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getitem__(self, key: str):
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)


def create_streaming_session_mock(events: list[dict]) -> MagicMock:
    """Create a mock SDK session that yields streaming events.

    The session should:
    1. Have an async iterator for streaming events (on() or iterate pattern)
    2. NOT use send_and_wait (that's the blocking path we're replacing)
    """
    session = MagicMock()
    session.session_id = "test-session-123"

    # Mock the disconnect method
    session.disconnect = AsyncMock()

    # Mock register_pre_tool_use_hook (required for deny hook)
    session.register_pre_tool_use_hook = MagicMock()

    # Create async iterator for streaming events
    async def stream_events(prompt_or_config, tools=None):
        """Yield SDK events as async iterator."""
        for event_data in events:
            # Convert dict to object-like mock that matches SDK event structure
            event = MagicMock()
            for key, value in event_data.items():
                setattr(event, key, value)
            # Make the mock look like a dict to get() calls
            event.get = lambda k, d=None, e=event_data: e.get(k, d)
            # Make vars() work for dict conversion in provider
            event.__dict__.update(event_data)
            yield event

    # Use AsyncMock that wraps the generator to enable call tracking
    mock_send_message = AsyncMock(side_effect=stream_events)
    session.send_message = mock_send_message
    # Store reference to check calls
    session._send_message_mock = mock_send_message

    return session


class TestF052RealSDKStreamingPipeline:
    """Test that real SDK path uses streaming pipeline.

    Contract: streaming-contract.md:Accumulation:MUST:1
    """

    @pytest.mark.asyncio
    async def test_real_sdk_path_uses_streaming_not_send_and_wait(self):
        """Real SDK path should iterate over streaming events, not use send_and_wait.

        Contract: streaming-contract.md - streaming pipeline must emit correct event sequence
        """
        # Arrange: Create mock SDK session that streams events
        events = [
            {"type": "text_delta", "text": "Hello "},
            {"type": "text_delta", "text": "World!"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        mock_session = create_streaming_session_mock(events)

        # Mock client wrapper
        provider = GitHubCopilotProvider()

        # Patch the client.session() context manager
        with patch.object(provider._client, "session") as mock_cm:
            mock_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            request = CompletionRequest(prompt="Hello")
            response = await provider.complete(request)

            # Assert: Response should contain accumulated text from streaming
            # If send_and_wait was used, this would be a single synthetic event
            # With streaming, we get proper event translation
            assert response.content is not None
            assert len(response.content) > 0

            # Verify send_message (streaming) was called, NOT send_and_wait
            mock_session._send_message_mock.assert_called()

    @pytest.mark.asyncio
    async def test_tool_calls_captured_from_streaming_events(self):
        """Tool calls should be captured from TOOL_CALL streaming events.

        Contract: streaming-contract.md:ToolCapture:MUST:1
        """
        # Arrange: Stream includes tool_use_complete event
        events = [
            {"type": "text_delta", "text": "Let me check that."},
            {
                "type": "tool_use_complete",
                "id": "tool-123",
                "name": "read_file",
                "arguments": {"path": "/tmp/test.txt"},
            },
            {"type": "message_complete", "finish_reason": "tool_use"},
        ]
        mock_session = create_streaming_session_mock(events)

        provider = GitHubCopilotProvider()

        with patch.object(provider._client, "session") as mock_cm:
            mock_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            request = CompletionRequest(prompt="Read a file")
            response = await provider.complete(request)

            # Assert: Tool calls should be in response
            assert response.tool_calls is not None
            assert len(response.tool_calls) >= 1
            assert response.tool_calls[0].name == "read_file"
            assert response.tool_calls[0].id == "tool-123"

    @pytest.mark.asyncio
    async def test_usage_update_captured_from_streaming(self):
        """Usage updates should be captured from USAGE_UPDATE streaming events.

        Contract: streaming-contract.md - streaming events translated through pipeline
        """
        # Arrange: Stream includes usage_update event
        events = [
            {"type": "text_delta", "text": "Response text"},
            {
                "type": "usage_update",
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        mock_session = create_streaming_session_mock(events)

        provider = GitHubCopilotProvider()

        with patch.object(provider._client, "session") as mock_cm:
            mock_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act
            request = CompletionRequest(prompt="Test usage")
            response = await provider.complete(request)

            # Assert: Usage should be captured from streaming event
            assert response.usage is not None
            assert response.usage.input_tokens == 10
            assert response.usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_finish_reason_from_turn_complete_event(self):
        """Finish reason should come from TURN_COMPLETE streaming event.

        Contract: streaming-contract.md - finish_reason from streaming events
        """
        events = [
            {"type": "text_delta", "text": "Done"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        mock_session = create_streaming_session_mock(events)

        provider = GitHubCopilotProvider()

        with patch.object(provider._client, "session") as mock_cm:
            mock_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            request = CompletionRequest(prompt="Test")
            response = await provider.complete(request)

            # Assert: finish_reason should come from message_complete event
            # With send_and_wait, there's no finish_reason (synthetic event)
            assert response.finish_reason is not None
            # After finish_reason_map translation: stop -> STOP
            assert response.finish_reason in ("stop", "STOP")

    @pytest.mark.asyncio
    async def test_events_routed_through_translate_event(self):
        """SDK events should be routed through translate_event function.

        Contract: event-vocabulary.md - events must use defined domain event types
        """
        events = [
            {"type": "text_delta", "text": "Hello"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        mock_session = create_streaming_session_mock(events)

        provider = GitHubCopilotProvider()

        with patch.object(provider._client, "session") as mock_cm:
            mock_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Patch translate_event to verify it's called
            with patch(
                "amplifier_module_provider_github_copilot.provider.translate_event"
            ) as mock_translate:
                # Make translate_event return domain events
                def translate_side_effect(event, config):
                    event_type = event.get("type", "")
                    if event_type == "text_delta":
                        return DomainEvent(
                            type=DomainEventType.CONTENT_DELTA,
                            data={"text": event.get("text", "")},
                        )
                    elif event_type == "message_complete":
                        return DomainEvent(
                            type=DomainEventType.TURN_COMPLETE,
                            data={"finish_reason": event.get("finish_reason", "stop")},
                        )
                    return None

                mock_translate.side_effect = translate_side_effect

                request = CompletionRequest(prompt="Test")
                await provider.complete(request)

                # Assert: translate_event should have been called for each event
                assert mock_translate.call_count >= 2

    @pytest.mark.asyncio
    async def test_tool_definitions_passed_to_sdk_session(self):
        """Tool definitions from request should be passed to SDK streaming call.

        Contract: streaming-contract.md - tools must be available to SDK
        """
        events = [
            {"type": "text_delta", "text": "I'll use the tool."},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        mock_session = create_streaming_session_mock(events)

        provider = GitHubCopilotProvider()

        with patch.object(provider._client, "session") as mock_cm:
            mock_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Act: Pass tools in request
            tools = [
                {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {"path": {"type": "string"}},
                }
            ]
            request = CompletionRequest(prompt="Read /tmp/test.txt", tools=tools)
            await provider.complete(request)

            # Assert: Tools should be passed to send_message
            # The call should include the tools parameter
            call_args = mock_session._send_message_mock.call_args
            assert call_args is not None
            # Check if tools were passed (either as positional or keyword arg)
            args, kwargs = call_args
            passed_tools = kwargs.get("tools") or (args[1] if len(args) > 1 else None)
            assert passed_tools == tools


class TestF052EventConfigExercised:
    """Test that config/events.yaml is exercised in real SDK path."""

    @pytest.mark.asyncio
    async def test_event_config_loaded_for_real_path(self):
        """Event config should be loaded and used for real SDK path.

        Contract: event-vocabulary.md - events classified per config
        """
        events = [
            {"type": "text_delta", "text": "Test"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        mock_session = create_streaming_session_mock(events)

        provider = GitHubCopilotProvider()

        with patch.object(provider._client, "session") as mock_cm:
            mock_cm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.return_value.__aexit__ = AsyncMock(return_value=None)

            # Patch load_event_config to verify it's called
            with patch(
                "amplifier_module_provider_github_copilot.provider.load_event_config"
            ) as mock_load_config:
                from amplifier_module_provider_github_copilot.streaming import EventConfig

                mock_load_config.return_value = EventConfig(
                    bridge_mappings={
                        "text_delta": (DomainEventType.CONTENT_DELTA, None),
                        "message_complete": (DomainEventType.TURN_COMPLETE, None),
                    }
                )

                request = CompletionRequest(prompt="Test")
                await provider.complete(request)

                # Assert: Event config should have been loaded
                mock_load_config.assert_called()
