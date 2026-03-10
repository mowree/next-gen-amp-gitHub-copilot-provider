"""
Session Factory with Deny Hook.

Creates ephemeral SDK sessions with preToolUse deny hook installed.
This is the provider's defining commitment to Amplifier's sovereignty.

Contract: contracts/deny-destroy.md
Feature: F-003

NON-NEGOTIABLE CONSTRAINTS:
- preToolUse deny hook MUST be installed on every session
- Sessions MUST be ephemeral (create, use once, destroy)
- No tool execution MUST occur inside the SDK
- Deny + Destroy is NEVER configurable
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from .sdk_adapter.types import SDKSession, SessionConfig

logger = logging.getLogger(__name__)

# Module-level constant for deny response
DENY_ALL: dict[str, str] = {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Amplifier sovereignty",
}


def create_deny_hook() -> Callable[..., Awaitable[dict[str, str]]]:
    """Create a preToolUse hook that denies ALL tool execution.

    NEVER returns None - that would allow the tool to proceed.
    Exception handling ensures we always return DENY_ALL.
    """

    async def deny(input_data: Any, invocation: Any) -> dict[str, str]:
        try:
            return DENY_ALL
        except Exception:
            return DENY_ALL  # NEVER return None

    return deny


def _create_breach_detector(  # pyright: ignore[reportUnusedFunction]
    on_breach: Callable[[str], None],
) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Create a postToolUse hook that detects sovereignty breaches.

    If this hook fires, a tool executed despite our deny hook.
    This is CRITICAL - it's our canary for detecting hook bypass.
    """

    async def detect(input_data: Any, invocation: Any) -> dict[str, Any]:
        tool_name = input_data.get("toolName", "unknown")
        on_breach(tool_name)  # Signal the breach
        return {
            "modifiedResult": "REDACTED - unauthorized execution",
            "suppressOutput": True,
        }

    return detect


class SDKSessionProtocol(Protocol):
    """Protocol for SDK session with hook registration."""

    def register_pre_tool_use_hook(self, hook: Callable[..., Any]) -> None:
        """Register a preToolUse hook."""
        ...

    async def disconnect(self) -> None:
        """Disconnect the session."""
        ...


# Type alias for SDK session creation function
SDKCreateFn = Callable[[SessionConfig], Awaitable[SDKSession]]


async def create_ephemeral_session(
    config: SessionConfig,
    *,
    sdk_create_fn: SDKCreateFn | None = None,
    deny_all_tools: bool = True,
) -> SDKSession:
    """Create an ephemeral SDK session with deny hook.

    Contract: deny-destroy.md
    - MUST register preToolUse hook that denies all tools
    - Session is ephemeral - caller MUST destroy after use

    Args:
        config: Session configuration.
        sdk_create_fn: SDK session creation function (for testing injection).
        deny_all_tools: Whether to install deny hook (ALWAYS True, not configurable).

    Returns:
        Opaque session handle with deny hook installed.

    Raises:
        NetworkError: If SDK session creation fails.
    """
    # Note: deny_all_tools parameter exists for API completeness but MUST always be True
    # The Deny + Destroy pattern is non-negotiable
    if not deny_all_tools:
        logger.warning(
            "Attempted to create session without deny hook - forcing deny_all_tools=True"
        )

    # Build the breach detector (Phase 2 will wire this to the SDK)
    breaches: list[str] = []
    _breach_detector = _create_breach_detector(breaches.append)

    # Create session via SDK
    if sdk_create_fn is None:
        # Use CopilotClientWrapper for real SDK path
        # Note: CopilotClientWrapper.session() handles deny internally
        # For now, fallback to raising - full wiring comes in F-015
        from .error_translation import ProviderUnavailableError

        raise ProviderUnavailableError(
            "Real SDK path requires CopilotClientWrapper. Use sdk_create_fn for testing.",
            provider="github-copilot",
        )
    else:
        # Use injected function for testing
        session = await sdk_create_fn(config)
        if hasattr(session, "register_pre_tool_use_hook"):
            session.register_pre_tool_use_hook(create_deny_hook())

    return session


async def destroy_session(session: SDKSession) -> None:
    """Destroy an ephemeral session.

    Contract: deny-destroy.md
    - MUST call session.disconnect() (not destroy())
    - MUST handle already-destroyed sessions gracefully

    Args:
        session: The session to destroy.
    """
    try:
        if hasattr(session, "disconnect"):
            await session.disconnect()
        else:
            logger.warning("Session does not have disconnect method")
    except Exception as e:
        # Log but don't propagate - session destruction should not fail
        logger.warning(f"Error destroying session: {e}")
