"""
Provider Orchestrator Module.

Thin orchestrator implementing Provider Protocol.
Delegates to specialized modules for all logic.

Contract: provider-protocol.md
Feature: F-008, F-020, F-038

MUST constraints:
- MUST implement Provider Protocol (4 methods + 1 property)
- MUST delegate tool parsing to tool_parsing module
- MUST NOT contain SDK imports (delegation only)
- MUST implement mount(), get_info(), list_models(), complete(), parse_tool_calls()

F-038: Kernel Type Migration
- Now imports ProviderInfo and ModelInfo from amplifier_core.models
- Now imports ToolCall from amplifier_core.message_models
- Removed local dataclass definitions for these types
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

# F-038: Import kernel types
from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall

from .error_translation import (
    ErrorConfig,
    load_error_config,
    translate_sdk_error,
)
from .sdk_adapter.client import CopilotClientWrapper, create_deny_hook
from .sdk_adapter.types import SDKSession, SessionConfig
from .streaming import (
    AccumulatedResponse,
    DomainEvent,
    DomainEventType,
    EventConfig,
    StreamingAccumulator,
    load_event_config,
    translate_event,
)
from .tool_parsing import parse_tool_calls

logger = logging.getLogger(__name__)


# ============================================================================
# F-048: Config Loading
# ============================================================================


@dataclass
class ProviderConfig:
    """Policy data loaded from config/models.yaml.

    Feature: F-048
    """

    provider_id: str
    display_name: str
    credential_env_vars: list[str]
    capabilities: list[str]
    defaults: dict[str, Any]
    models: list[dict[str, Any]]


def _load_models_config() -> ProviderConfig:
    """Load provider and model policy from config/models.yaml.

    Feature: F-048, F-074

    Falls back to minimal hardcoded defaults if file is missing.
    (Graceful degradation — same pattern as load_event_config.)

    F-074: Config now lives inside wheel at amplifier_module_provider_github_copilot/config/
    """
    # F-074: Config moved inside package
    config_path = Path(__file__).parent / "config" / "models.yaml"
    if not config_path.exists():
        return _default_provider_config()

    try:
        with config_path.open() as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("Failed to load models.yaml: %s", e)
        return _default_provider_config()

    if not data:
        return _default_provider_config()

    p = data.get("provider", {})
    return ProviderConfig(
        provider_id=p.get("id", "github-copilot"),
        display_name=p.get("display_name", "GitHub Copilot SDK"),
        credential_env_vars=p.get("credential_env_vars", []),
        capabilities=p.get("capabilities", []),
        defaults=p.get("defaults", {}),
        models=data.get("models", []),
    )


def _default_provider_config() -> ProviderConfig:
    """Minimal fallback config for environments without config files."""
    return ProviderConfig(
        provider_id="github-copilot",
        display_name="GitHub Copilot SDK",
        credential_env_vars=["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
        capabilities=["streaming", "tool_use"],
        defaults={"model": "gpt-4o", "max_tokens": 4096},
        models=[],
    )


def extract_response_content(response: Any) -> str:
    """Extract text content from SDK response.

    Contract: sdk-response.md
    Feature: F-043 AC-1

    The SDK returns Data dataclass objects with .content attribute.
    This function handles all response shapes:
    1. Data object with .content attribute
    2. Dict with 'content' key
    3. Response wrapper with .data attribute (recurses)
    4. None (returns empty string)

    Args:
        response: SDK response (Data object, dict, wrapper, or None)

    Returns:
        Extracted text content as string.
    """
    if response is None:
        return ""

    # Check for .data wrapper first (response.data -> Data object)
    if hasattr(response, "data"):
        return extract_response_content(response.data)

    # Check for Data object with .content attribute (the bug fix!)
    if hasattr(response, "content"):
        content = response.content  # type: ignore[union-attr]
        return str(content) if content is not None else ""

    # Handle dict response
    if isinstance(response, dict):
        return str(cast(dict[str, Any], response).get("content", ""))

    # Fallback for unknown types (shouldn't reach here normally)
    return ""


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
        # F-074: Config moved inside package at amplifier_module_provider_github_copilot/config/
        error_config = load_error_config(Path(__file__).parent / "config" / "errors.yaml")

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
            # F-050: Deny hook installation is MANDATORY (deny-destroy:DenyHook:MUST:1)
            if not hasattr(session, "register_pre_tool_use_hook"):
                from .error_translation import ProviderUnavailableError

                raise ProviderUnavailableError(
                    "SDK session lacks register_pre_tool_use_hook method - "
                    "deny hook cannot be installed. Deny+Destroy pattern requires "
                    "hook registration on every session.",
                    provider="github-copilot",
                )
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
        # F-039: Create SDK client wrapper for real SDK path
        self._client = CopilotClientWrapper()
        # F-048: Load provider config from YAML
        self._provider_config = _load_models_config()

    @property
    def name(self) -> str:
        """Return provider name.

        Contract: provider-protocol:name:MUST:1
        """
        return "github-copilot"

    def get_info(self) -> ProviderInfo:
        """Return provider metadata.

        Contract: provider-protocol:get_info:MUST:1
        Feature: F-020 AC-2, F-038, F-048
        """
        # F-048: Use config from YAML instead of hardcoded values
        cfg = self._provider_config
        return ProviderInfo(
            id=cfg.provider_id,
            display_name=cfg.display_name,
            credential_env_vars=cfg.credential_env_vars,
            capabilities=cfg.capabilities,
            defaults=cfg.defaults,
            config_fields=[],
        )

    async def list_models(self) -> list[ModelInfo]:
        """Return available models from GitHub Copilot.

        Contract: provider-protocol:list_models:MUST:1
        Feature: F-020 AC-3, F-038, F-048
        """
        # F-048: Use config from YAML instead of hardcoded values
        cfg = self._provider_config
        if not cfg.models:
            # Fallback if no models in config
            return [
                ModelInfo(
                    id="gpt-4o",
                    display_name="GPT-4o",
                    context_window=128000,
                    max_output_tokens=4096,
                    capabilities=["streaming", "tool_use"],
                    defaults={},
                ),
            ]
        return [
            ModelInfo(
                id=m["id"],
                display_name=m["display_name"],
                context_window=m["context_window"],
                max_output_tokens=m["max_output_tokens"],
                capabilities=m.get("capabilities", []),
                defaults=m.get("defaults", {}),
            )
            for m in cfg.models
        ]

    async def complete(
        self,
        request: Any,
        **kwargs: Any,
    ) -> ChatResponse:
        """Execute completion lifecycle, returning ChatResponse.

        Contract: provider-protocol:complete:MUST:1
        Feature: F-020 AC-4, F-038, F-039

        F-038: Now returns ChatResponse instead of AsyncIterator[DomainEvent].
        F-039: Uses CopilotClientWrapper.session() for real SDK path.
        """

        # Convert request to internal CompletionRequest if needed
        internal_request: CompletionRequest
        if isinstance(request, CompletionRequest):
            internal_request = request
        else:
            # Handle kernel ChatRequest - extract prompt from messages
            messages: list[Any] = getattr(request, "messages", [])
            prompt_parts: list[str] = []
            for msg in messages:
                content: Any = getattr(msg, "content", "")
                if isinstance(content, str):
                    prompt_parts.append(content)
                elif isinstance(content, list):
                    for block in content:  # type: ignore[union-attr]
                        text: str | None = getattr(block, "text", None)  # type: ignore[arg-type]
                        if text is not None:
                            prompt_parts.append(text)
            internal_request = CompletionRequest(
                prompt="\n".join(prompt_parts),
                model=getattr(request, "model", None),
                tools=getattr(request, "tools", []) or [],
            )

        # F-039: Use the SDK client wrapper for real SDK path
        # The client.session() context manager handles:
        # - Lazy SDK initialization
        # - Session creation with deny hook
        # - Proper cleanup on exit
        accumulator = StreamingAccumulator()

        # Check for test injection first
        sdk_create_fn = kwargs.get("sdk_create_fn") or self._complete_fn
        if sdk_create_fn is not None:
            # Test path: use injected SDK factory
            async for event in self._complete_internal(
                internal_request,
                config=kwargs.get("config"),
                sdk_create_fn=sdk_create_fn,
            ):
                accumulator.add(event)
        else:
            # Real SDK path: use client wrapper
            # F-040: Fixed SDK API - use send_and_wait(), not send_message()
            model = internal_request.model or "gpt-4o"
            async with self._client.session(model=model) as sdk_session:
                # SDK uses send_and_wait() for blocking call
                sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})

                # Extract response content and convert to domain event
                # F-043: Use extract_response_content() to handle Data objects
                if sdk_response is not None:
                    content = extract_response_content(sdk_response)

                    # Create CONTENT_DELTA event with correct DomainEvent signature
                    text_event = DomainEvent(
                        type=DomainEventType.CONTENT_DELTA,
                        data={"text": content},
                    )
                    accumulator.add(text_event)

        # Convert at boundary to kernel ChatResponse
        return accumulator.to_chat_response()

    async def _complete_internal(
        self,
        request: CompletionRequest,
        **kwargs: Any,
    ) -> AsyncIterator[DomainEvent]:
        """Internal: Execute completion lifecycle, yielding domain events.

        This is the preserved streaming implementation, now private.
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
