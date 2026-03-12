"""
Provider Orchestrator Module.

Thin orchestrator implementing Provider Protocol.
Delegates to specialized modules for all logic.

Contract: provider-protocol.md
Feature: F-008, F-020

MUST constraints:
- MUST implement Provider Protocol (4 methods + 1 property)
- MUST delegate tool parsing to tool_parsing module
- MUST NOT contain SDK imports (delegation only)
- MUST implement mount(), get_info(), list_models(), complete(), parse_tool_calls()
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


def _empty_str_list() -> list[str]:
    """Factory for empty string list."""
    return []


@dataclass
class ProviderInfo:
    """Provider metadata returned by get_info().

    Contract: provider-protocol.md
    Feature: F-020 AC-2
    """

    name: str
    version: str
    description: str
    capabilities: list[str] = field(default_factory=_empty_str_list)


@dataclass
class ModelInfo:
    """Model metadata returned by list_models().

    Contract: provider-protocol.md
    Feature: F-020 AC-3
    """

    id: str
    display_name: str
    context_window: int
    max_output_tokens: int


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
            # AC-2 (F-021): Replace assert with proper error (asserts stripped by -O)
            if session is None:
                from .error_translation import ProviderUnavailableError

                raise ProviderUnavailableError(
                    "SDK session factory returned None",
                    provider="github-copilot",
                )
            if hasattr(session, "register_pre_tool_use_hook"):
                session.register_pre_tool_use_hook(create_deny_hook())
        else:
            from .error_translation import ProviderUnavailableError

            raise ProviderUnavailableError(
                "Real SDK path requires CopilotClientWrapper.session() context manager.",
                provider="github-copilot",
            )

        # Stream events from session (session guaranteed non-None here)
        async for sdk_event in session.send_message(request.prompt, request.tools):
            domain_event = translate_event(sdk_event, event_config)
            if domain_event is not None:
                yield domain_event

    except Exception as e:
        # F-019 AC-3: Don't double-wrap already-translated LLMError
        from .error_translation import LLMError

        if isinstance(e, LLMError):
            raise  # Already translated, don't wrap again
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


class GitHubCopilotProvider:
    """
    Provider Protocol implementation for GitHub Copilot.

    Contract: provider-protocol.md
    Feature: F-008, F-020

    This is a thin orchestrator that delegates to:
    - completion logic (now inlined) for LLM calls
    - tool_parsing module for tool extraction

    Implements 4 methods + 1 property Provider Protocol:
    - name (property)
    - get_info()
    - list_models()
    - complete()
    - parse_tool_calls()
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        coordinator: Any | None = None,
    ) -> None:
        """Initialize provider.

        Args:
            config: Optional provider configuration.
            coordinator: Optional Amplifier kernel coordinator.
        """
        self.config = config or {}
        self.coordinator = coordinator
        self._complete_fn: SDKCreateFn | None = None

    @property
    def name(self) -> str:
        """Return provider name.

        Contract: provider-protocol:name:MUST:1
        """
        return "github-copilot"

    def get_info(self) -> ProviderInfo:
        """Return provider metadata.

        Contract: provider-protocol:get_info:MUST:1
        Feature: F-020 AC-2
        """
        return ProviderInfo(
            name="github-copilot",
            version="0.1.0",
            description="GitHub Copilot provider for Amplifier",
            capabilities=["streaming", "tool_use"],
        )

    async def list_models(self) -> list[ModelInfo]:
        """Return available models from GitHub Copilot.

        Contract: provider-protocol:list_models:MUST:1
        Feature: F-020 AC-3
        """
        return [
            ModelInfo(
                id="gpt-4",
                display_name="GPT-4",
                context_window=128000,
                max_output_tokens=4096,
            ),
            ModelInfo(
                id="gpt-4o",
                display_name="GPT-4o",
                context_window=128000,
                max_output_tokens=4096,
            ),
        ]

    async def complete(
        self,
        request: CompletionRequest,
        **kwargs: Any,
    ) -> AsyncIterator[DomainEvent]:
        """Execute completion lifecycle, yielding domain events.

        Contract: provider-protocol:complete:MUST:1
        Feature: F-020 AC-4

        This is a thin wrapper around the module-level complete() function.
        """
        # Delegate to module-level complete() function
        async for event in complete(
            request,
            config=kwargs.get("config"),
            sdk_create_fn=kwargs.get("sdk_create_fn") or self._complete_fn,
        ):
            yield event

    async def close(self) -> None:
        """Clean up provider resources.

        Feature: F-020 AC-1
        """
        # Currently no resources to clean up
        pass

    def parse_tool_calls(self, response: Any) -> list[ToolCall]:
        """Extract tool calls from response.

        Contract: provider-protocol:parse_tool_calls:MUST:1 through MUST:4

        Delegates to tool_parsing module.
        """
        return parse_tool_calls(response)
