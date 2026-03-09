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


def create_deny_hook() -> Callable[[Any], dict[str, str]]:
    """Create a preToolUse hook that denies all tool execution.

    Contract: deny-destroy.md
    - MUST return DENY for all tool requests
    - MUST include reason referencing Amplifier orchestrator

    Returns:
        A function that returns a denial response for any tool request.
    """

    def deny_all_tools(tool_request: Any) -> dict[str, str]:
        """Deny all tool execution requests.

        The SDK never executes tools - Amplifier's orchestrator handles them.
        This prevents the "Two Orchestrators" problem.
        """
        return {
            "action": "DENY",
            "reason": "Amplifier orchestrator handles tools - SDK tool execution denied",
        }

    return deny_all_tools


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
        deny_all_tools = True

    # Create session via SDK
    if sdk_create_fn is None:
        # Use real SDK adapter (to be implemented in future feature)
        from .sdk_adapter.driver import create_session as sdk_create

        session = await sdk_create(config, deny_hook=create_deny_hook())
    else:
        # Use injected mock for testing
        session = await sdk_create_fn(config)
        # Register hook on mock session
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
