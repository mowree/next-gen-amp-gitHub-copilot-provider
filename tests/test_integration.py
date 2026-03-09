"""
Integration tests for provider-github-copilot.

End-to-end tests verifying all modules work together with mock SDK.

Contract: All feature contracts (F-001 through F-008)
Feature: F-009
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest

from amplifier_module_provider_github_copilot.completion import (
    CompletionConfig,
    CompletionRequest,
    complete_and_collect,
)
from amplifier_module_provider_github_copilot.error_translation import (
    AuthenticationError,
    ErrorConfig,
    ErrorMapping,
    RateLimitError,
)
from amplifier_module_provider_github_copilot.provider import (
    ChatRequest,
    GitHubCopilotProvider,
)
from amplifier_module_provider_github_copilot.sdk_adapter.types import (
    SDKSession,
    SessionConfig,
)
from amplifier_module_provider_github_copilot.streaming import (
    EventConfig,
    DomainEventType,
    load_event_config,
)


# ============================================================================
# Mock SDK Session
# ============================================================================


@dataclass
class MockToolCall:
    """Mock tool call object."""

    id: str
    name: str
    arguments: dict[str, Any]


class MockSDKSession:
    """
    Mock SDK session for integration testing.

    Simulates SDK session behavior without real SDK dependencies.
    """

    def __init__(
        self,
        events: list[dict[str, Any]],
        *,
        raise_on_send: Exception | None = None,
    ) -> None:
        """Initialize mock session.

        Args:
            events: List of SDK events to yield.
            raise_on_send: Exception to raise during send_message.
        """
        self.events = events
        self.raise_on_send = raise_on_send
        self.destroyed = False
        self.deny_hook_installed = False
        self._hooks: list[Any] = []

    def register_pre_tool_use_hook(self, hook: Any) -> None:
        """Register a pre-tool-use hook."""
        self._hooks.append(hook)
        self.deny_hook_installed = True

    async def send_message(
        self,
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield mock SDK events."""
        if self.raise_on_send:
            raise self.raise_on_send

        for event in self.events:
            yield event

    async def disconnect(self) -> None:
        """Mark session as destroyed."""
        self.destroyed = True


async def mock_create_session(config: SessionConfig) -> MockSDKSession:
    """Factory that creates MockSDKSession - used as sdk_create_fn."""
    # Default events for simple completion
    return MockSDKSession(
        events=[
            {"type": "text_delta", "text": "Hello "},
            {"type": "text_delta", "text": "world!"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
    )


# ============================================================================
# AC-1: Full Completion Lifecycle
# ============================================================================


class TestFullCompletionLifecycle:
    """AC-1: Provider can complete a request end-to-end with mock SDK."""

    @pytest.mark.asyncio
    async def test_complete_simple_request(self) -> None:
        """Full completion lifecycle with text response."""
        events = [
            {"type": "text_delta", "text": "Hello "},
            {"type": "text_delta", "text": "world!"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="Say hello")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        result = await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert result.text_content == "Hello world!"
        assert result.finish_reason == "stop"
        assert result.is_complete
        assert session.destroyed  # Session cleanup

    @pytest.mark.asyncio
    async def test_provider_complete_method(self) -> None:
        """Provider.complete() returns ChatResponse."""
        events = [
            {"type": "text_delta", "text": "Test response"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        # Create provider with injected completion function
        provider = GitHubCopilotProvider()

        async def mock_complete(req: CompletionRequest) -> Any:
            event_config = load_event_config()
            config = CompletionConfig(event_config=event_config)
            return await complete_and_collect(req, config=config, sdk_create_fn=create_session)

        provider._complete_fn = mock_complete

        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        response = await provider.complete(request)

        assert response.content == "Test response"
        assert response.finish_reason == "stop"


# ============================================================================
# AC-2: Tool Call Integration
# ============================================================================


class TestToolCallIntegration:
    """AC-2: Provider correctly parses tool calls from completion response."""

    @pytest.mark.asyncio
    async def test_complete_with_tool_calls(self) -> None:
        """Tool calls are extracted from completion response."""
        events = [
            {"type": "text_delta", "text": "I'll help you with that."},
            {
                "type": "tool_use_complete",
                "id": "call_123",
                "name": "get_weather",
                "arguments": {"location": "Seattle"},
            },
            {"type": "message_complete", "finish_reason": "tool_use"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="What's the weather?")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        result = await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert result.text_content == "I'll help you with that."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "get_weather"
        assert result.tool_calls[0]["arguments"] == {"location": "Seattle"}
        assert result.finish_reason == "tool_use"

    def test_parse_tool_calls_from_response(self) -> None:
        """parse_tool_calls returns ToolCall objects with correct structure."""
        provider = GitHubCopilotProvider()

        @dataclass
        class MockResponse:
            tool_calls: list[MockToolCall]

        response = MockResponse(
            tool_calls=[
                MockToolCall(
                    id="call_456",
                    name="search",
                    arguments={"query": "python"},
                ),
            ]
        )

        tool_calls = provider.parse_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0].id == "call_456"
        assert tool_calls[0].name == "search"
        assert tool_calls[0].arguments == {"query": "python"}


# ============================================================================
# AC-3: Error Translation Integration
# ============================================================================


class TestErrorTranslationIntegration:
    """AC-3: SDK errors are translated to domain error types."""

    @pytest.mark.asyncio
    async def test_auth_error_translation(self) -> None:
        """Authentication errors are translated correctly."""

        class SDKAuthError(Exception):
            """Mock SDK authentication error."""

            pass

        session = MockSDKSession(events=[], raise_on_send=SDKAuthError("Invalid token"))

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        # Create error config that maps SDKAuthError
        error_config = ErrorConfig(
            mappings=[
                ErrorMapping(
                    sdk_patterns=["SDKAuthError"],
                    kernel_error="AuthenticationError",
                    retryable=False,
                ),
            ]
        )

        request = CompletionRequest(prompt="Test")
        config = CompletionConfig(error_config=error_config)

        with pytest.raises(AuthenticationError) as exc_info:
            await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert exc_info.value.retryable is False
        assert exc_info.value.provider == "github-copilot"
        assert session.destroyed  # Session still cleaned up

    @pytest.mark.asyncio
    async def test_rate_limit_error_with_retry_after(self) -> None:
        """Rate limit errors have retry_after populated."""

        class SDKRateLimitError(Exception):
            """Mock SDK rate limit error."""

            pass

        session = MockSDKSession(
            events=[],
            raise_on_send=SDKRateLimitError("Rate limited. Retry after 30 seconds"),
        )

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        error_config = ErrorConfig(
            mappings=[
                ErrorMapping(
                    sdk_patterns=["RateLimitError"],
                    kernel_error="RateLimitError",
                    retryable=True,
                    extract_retry_after=True,
                ),
            ]
        )

        request = CompletionRequest(prompt="Test")
        config = CompletionConfig(error_config=error_config)

        with pytest.raises(RateLimitError) as exc_info:
            await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert exc_info.value.retryable is True
        assert exc_info.value.retry_after == 30.0


# ============================================================================
# AC-4: Streaming Event Flow
# ============================================================================


class TestStreamingEventFlow:
    """AC-4: Events flow from SDK → streaming → accumulator → response."""

    @pytest.mark.asyncio
    async def test_content_delta_accumulation(self) -> None:
        """CONTENT_DELTA events accumulate correctly."""
        events = [
            {"type": "text_delta", "text": "Part 1. "},
            {"type": "text_delta", "text": "Part 2. "},
            {"type": "text_delta", "text": "Part 3."},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="Test")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        result = await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert result.text_content == "Part 1. Part 2. Part 3."

    @pytest.mark.asyncio
    async def test_thinking_content_separate(self) -> None:
        """Thinking content is accumulated separately from text."""
        events = [
            {"type": "thinking_delta", "text": "Let me think..."},
            {"type": "text_delta", "text": "Here's my answer."},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="Test")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        result = await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert result.text_content == "Here's my answer."
        assert result.thinking_content == "Let me think..."

    @pytest.mark.asyncio
    async def test_turn_complete_signals_finish(self) -> None:
        """TURN_COMPLETE signals completion with finish_reason."""
        events = [
            {"type": "text_delta", "text": "Done"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="Test")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        result = await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert result.is_complete
        assert result.finish_reason == "stop"


# ============================================================================
# AC-5: Session Factory Integration
# ============================================================================


class TestSessionFactoryIntegration:
    """AC-5: Session lifecycle is correctly managed."""

    @pytest.mark.asyncio
    async def test_deny_hook_installed(self) -> None:
        """Deny hook is installed on all sessions."""
        events = [
            {"type": "text_delta", "text": "Response"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="Test")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert session.deny_hook_installed

    @pytest.mark.asyncio
    async def test_session_destroyed_on_success(self) -> None:
        """Sessions are destroyed after successful completion."""
        events = [
            {"type": "text_delta", "text": "Response"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="Test")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert session.destroyed

    @pytest.mark.asyncio
    async def test_session_destroyed_on_error(self) -> None:
        """Sessions are destroyed even on error (try/finally)."""

        class SDKError(Exception):
            pass

        session = MockSDKSession(events=[], raise_on_send=SDKError("Boom"))

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        request = CompletionRequest(prompt="Test")
        event_config = load_event_config()
        config = CompletionConfig(event_config=event_config)

        with pytest.raises(Exception):
            await complete_and_collect(request, config=config, sdk_create_fn=create_session)

        assert session.destroyed


# ============================================================================
# AC-6: Provider Protocol Compliance
# ============================================================================


class TestProviderProtocolCompliance:
    """AC-6: Provider implements the full protocol."""

    def test_provider_name_property(self) -> None:
        """Provider has name property."""
        provider = GitHubCopilotProvider()
        assert provider.name == "github-copilot"

    def test_get_info_returns_provider_info(self) -> None:
        """get_info() returns ProviderInfo."""
        provider = GitHubCopilotProvider()
        info = provider.get_info()

        assert info.name == "github-copilot"
        assert info.version == "0.1.0"
        assert info.defaults is not None
        assert info.defaults.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_list_models_returns_model_list(self) -> None:
        """list_models() returns list of ModelInfo."""
        provider = GitHubCopilotProvider()
        models = await provider.list_models()

        assert len(models) >= 1
        assert all(hasattr(m, "id") for m in models)
        assert all(hasattr(m, "name") for m in models)
        assert all(hasattr(m, "context_window") for m in models)

    @pytest.mark.asyncio
    async def test_complete_returns_chat_response(self) -> None:
        """complete() returns ChatResponse."""
        events = [
            {"type": "text_delta", "text": "Response"},
            {"type": "message_complete", "finish_reason": "stop"},
        ]
        session = MockSDKSession(events)

        async def create_session(_: SessionConfig) -> MockSDKSession:
            return session

        provider = GitHubCopilotProvider()

        async def mock_complete(req: CompletionRequest) -> Any:
            event_config = load_event_config()
            config = CompletionConfig(event_config=event_config)
            return await complete_and_collect(req, config=config, sdk_create_fn=create_session)

        provider._complete_fn = mock_complete

        request = ChatRequest(messages=[{"role": "user", "content": "Hello"}])
        response = await provider.complete(request)

        assert hasattr(response, "content")
        assert hasattr(response, "tool_calls")
        assert hasattr(response, "finish_reason")

    def test_parse_tool_calls_returns_tool_call_list(self) -> None:
        """parse_tool_calls() returns list[ToolCall]."""
        provider = GitHubCopilotProvider()

        @dataclass
        class EmptyResponse:
            tool_calls: None = None

        result = provider.parse_tool_calls(EmptyResponse())
        assert result == []
