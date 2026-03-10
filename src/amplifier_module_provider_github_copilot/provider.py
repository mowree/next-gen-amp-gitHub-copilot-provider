"""
Provider Orchestrator Module.

Thin orchestrator implementing 4 methods + 1 property Provider Protocol.
Delegates to specialized modules for all logic.

Contract: provider-protocol.md
Feature: F-008

MUST constraints:
- MUST implement Provider Protocol (4 methods + 1 property)
- MUST delegate completion to completion module
- MUST delegate tool parsing to tool_parsing module
- MUST NOT contain SDK imports (delegation only)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .completion import (
    AccumulatedResponse,
    CompletionRequest,
    complete_and_collect,
)
from .tool_parsing import ToolCall, parse_tool_calls


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
    - completion module for LLM calls
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
        """Execute completion via completion module.

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
