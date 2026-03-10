"""
Provider Orchestrator Module.

Thin orchestrator implementing 4 methods + 1 property Provider Protocol.
Delegates to specialized modules for all logic.

Contract: provider-protocol.md
Feature: F-008

MUST constraints:
- MUST implement Provider Protocol (4 methods + 1 property)
- MUST delegate tool parsing to tool_parsing module
- MUST NOT contain SDK imports (delegation only)
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .error_translation import (
    ErrorConfig,
    load_error_config,
    translate_sdk_error,
)
from .sdk_adapter.client import create_deny_hook
from .sdk_adapter.types import SDKSession, SessionConfig
from .streaming import (
    AccumulatedResponse,
    DomainEvent,
    EventConfig,
    StreamingAccumulator,
    load_event_config,
    translate_event,
)
from .tool_parsing import ToolCall, parse_tool_calls

logger = logging.getLogger(__name__)


# Type alias for SDK session creation function
SDKCreateFn = Callable[[SessionConfig], Awaitable[SDKSession]]


@dataclass
class CompletionRequest:
    """Request for LLM completion.

    Attributes:
        prompt: The prompt text to send.
        model: Optional model override.
        tools: Tool definitions for the completion.
        max_tokens: Maximum tokens in response.
        temperature: Sampling temperature.
    """

    prompt: str
    model: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=lambda: [])
    max_tokens: int | None = None
    temperature: float | None = None


@dataclass
class CompletionConfig:
    """Configuration for completion lifecycle.

    Attributes:
        session_config: SDK session configuration.
        event_config: Event translation configuration.
        error_config: Error translation configuration.
    """

    session_config: SessionConfig | None = None
    event_config: EventConfig | None = None
    error_config: ErrorConfig | None = None


async def complete(
    request: CompletionRequest,
    *,
    config: CompletionConfig | None = None,
    sdk_create_fn: SDKCreateFn | None = None,
) -> AsyncIterator[DomainEvent]:
    """Execute completion lifecycle, yielding domain events.

    Contract: streaming-contract.md, deny-destroy.md

    - MUST create ephemeral session with deny hook
    - MUST yield translated domain events
    - MUST destroy session in finally block
    - MUST translate SDK errors to kernel types

    Args:
        request: Completion request with prompt and options.
        config: Optional configuration overrides.
        sdk_create_fn: Optional SDK session factory (for testing).

    Yields:
        DomainEvent for each bridged SDK event.

    Raises:
        LLMError: Translated from SDK errors.
    """
    config = config or CompletionConfig()

    # Load configs if not provided
    event_config = config.event_config
    if event_config is None:
        event_config = load_event_config()

    error_config = config.error_config
    if error_config is None:
        from pathlib import Path

        package_root = Path(__file__).parent.parent.parent
        error_config = load_error_config(package_root / "config" / "errors.yaml")

    # Create session config
    session_config = config.session_config or SessionConfig(model=request.model or "gpt-4")

    # Create session
    session: SDKSession | None = None
    try:
        if sdk_create_fn is not None:
            session = await sdk_create_fn(session_config)
            assert session is not None
            if hasattr(session, "register_pre_tool_use_hook"):
                session.register_pre_tool_use_hook(create_deny_hook())
        else:
            from .error_translation import ProviderUnavailableError

            raise ProviderUnavailableError(
                "Real SDK path requires CopilotClientWrapper.session() context manager.",
                provider="github-copilot",
            )

        # Stream events from session
        assert session is not None
        async for sdk_event in session.send_message(request.prompt, request.tools):
            domain_event = translate_event(sdk_event, event_config)
            if domain_event is not None:
                yield domain_event

    except Exception as e:
        kernel_error = translate_sdk_error(
            e,
            error_config,
            provider="github-copilot",
            model=request.model,
        )
        raise kernel_error from e

    finally:
        if session is not None:
            try:
                if hasattr(session, "disconnect"):
                    await session.disconnect()
            except Exception as disconnect_err:
                logger.warning(f"Error destroying session: {disconnect_err}")


async def complete_and_collect(
    request: CompletionRequest,
    *,
    config: CompletionConfig | None = None,
    sdk_create_fn: SDKCreateFn | None = None,
) -> AccumulatedResponse:
    """Execute completion lifecycle and collect final response.

    Convenience wrapper that accumulates all events into AccumulatedResponse.

    Args:
        request: Completion request with prompt and options.
        config: Optional configuration overrides.
        sdk_create_fn: Optional SDK session factory (for testing).

    Returns:
        AccumulatedResponse with text, tool calls, usage, etc.

    Raises:
        LLMError: Translated from SDK errors.
    """
    accumulator = StreamingAccumulator()

    async for event in complete(
        request,
        config=config,
        sdk_create_fn=sdk_create_fn,
    ):
        accumulator.add(event)

    return accumulator.get_result()


@dataclass
class ProviderDefaults:
    """Default values for provider behavior."""

    model: str = "gpt-4"
    context_window: int = 128000
    max_output_tokens: int = 4096


@dataclass
class ProviderInfo:
    """Provider metadata."""

    name: str
    version: str
    defaults: ProviderDefaults


@dataclass
class ModelInfo:
    """Model metadata."""

    id: str
    name: str
    context_window: int
    max_output_tokens: int


@dataclass
class ChatRequest:
    """Request for chat completion."""

    messages: list[dict[str, Any]]
    model: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=lambda: [])
    max_tokens: int | None = None
    temperature: float | None = None


@dataclass
class ChatResponse:
    """Response from chat completion."""

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: dict[str, int] | None = None
    finish_reason: str | None = None


# Type for injectable completion function (testing)
CompleteFn = Callable[[CompletionRequest], Awaitable[AccumulatedResponse]]


class GitHubCopilotProvider:
    """
    Provider Protocol implementation for GitHub Copilot.

    Contract: provider-protocol.md

    This is a thin orchestrator that delegates to:
    - completion logic (now inlined) for LLM calls
    - tool_parsing module for tool extraction
    """

    def __init__(self) -> None:
        self._complete_fn: CompleteFn | None = None

    @property
    def name(self) -> str:
        """Return provider name.

        Contract: provider-protocol:name:MUST:1
        """
        return "github-copilot"

    def get_info(self) -> ProviderInfo:
        """Return provider metadata.

        Contract: provider-protocol:get_info:MUST:1, MUST:2
        """
        return ProviderInfo(
            name="github-copilot",
            version="0.1.0",
            defaults=ProviderDefaults(),
        )

    async def list_models(self) -> list[ModelInfo]:
        """Return available models.

        Contract: provider-protocol:list_models:MUST:1, MUST:2

        NOTE: Stub implementation returns hardcoded list.
        Real implementation would query SDK.
        """
        return [
            ModelInfo(
                id="gpt-4",
                name="GPT-4",
                context_window=128000,
                max_output_tokens=4096,
            ),
            ModelInfo(
                id="gpt-4o",
                name="GPT-4o",
                context_window=128000,
                max_output_tokens=4096,
            ),
            ModelInfo(
                id="claude-3.5-sonnet",
                name="Claude 3.5 Sonnet",
                context_window=200000,
                max_output_tokens=8192,
            ),
        ]

    async def complete(
        self,
        request: ChatRequest,
        **kwargs: Any,
    ) -> ChatResponse:
        """Execute completion via completion logic.

        Contract: provider-protocol:complete:MUST:1 through MUST:4

        Args:
            request: Chat request with messages and options.
            **kwargs: Provider-specific options (ignored by default).

        Returns:
            ChatResponse with content and tool_calls.
        """
        # Build prompt from messages
        prompt = self._build_prompt(request.messages)

        # Create completion request
        completion_request = CompletionRequest(
            prompt=prompt,
            model=request.model,
            tools=request.tools,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        # Execute completion (injectable for testing)
        if self._complete_fn is not None:
            accumulated = await self._complete_fn(completion_request)
        else:
            accumulated = await complete_and_collect(completion_request)

        # Convert accumulated response to ChatResponse
        return self._to_chat_response(accumulated)

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Extract tool calls from response.

        Contract: provider-protocol:parse_tool_calls:MUST:1 through MUST:4

        Delegates to tool_parsing module.
        """
        return parse_tool_calls(response)

    def _build_prompt(self, messages: list[dict[str, Any]]) -> str:
        """Build prompt string from message list."""
        parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[System]: {content}")
            elif role == "assistant":
                parts.append(f"[Assistant]: {content}")
            else:
                parts.append(f"[User]: {content}")
        return "\n\n".join(parts)

    def _to_chat_response(self, accumulated: AccumulatedResponse) -> ChatResponse:
        """Convert AccumulatedResponse to ChatResponse."""
        return ChatResponse(
            content=accumulated.text_content,
            tool_calls=accumulated.tool_calls if accumulated.tool_calls else None,
            usage=accumulated.usage,
            finish_reason=accumulated.finish_reason,
        )
