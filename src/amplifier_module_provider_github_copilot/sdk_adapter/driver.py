"""
SDK driver functions for session lifecycle.

These functions manage SDK session creation and destruction.
All SDK imports MUST be contained within this module.

Contract: contracts/sdk-boundary.md
Feature: F-001

Note: This is a skeleton implementation. Full SDK integration
comes in later features (F-003 session factory).
"""

import asyncio
from collections.abc import Callable
from typing import Any

from copilot import CopilotClient  # type: ignore[import-untyped]

from .types import SDKSession, SessionConfig

_client: Any = None
_client_lock = asyncio.Lock()


async def _get_client() -> Any:  # pyright: ignore[reportUnusedFunction]
    """Get or create singleton CopilotClient."""
    global _client
    async with _client_lock:
        if _client is None:
            new_client: Any = CopilotClient()  # type: ignore[misc]
            await new_client.start()  # type: ignore[misc]
            _client = new_client  # type: ignore[assignment]
        return _client  # type: ignore[return-value]


async def create_session(
    config: SessionConfig,
    deny_hook: Callable[..., Any] | None = None,
) -> SDKSession:
    """Create a new SDK session with hooks configured.

    Args:
        config: Session configuration.
        deny_hook: Hook to deny tool execution (required for sovereignty).

    Returns:
        Opaque session handle.
    """
    client = await _get_client()

    # Build hooks dict - deny_hook is the pre-tool-use hook
    hooks: dict[str, Any] = {}
    if deny_hook is not None:
        hooks["on_pre_tool_use"] = deny_hook

    # Create session with hooks, NEVER register SDK tools
    session = await client.create_session(  # type: ignore[union-attr]
        {
            "model": config.model,
            "hooks": hooks,
            "tools": [],  # NEVER register SDK tools - they bypass hooks
        }
    )

    return session  # type: ignore[return-value]


async def destroy_session(session: SDKSession) -> None:
    """Destroy an SDK session.

    Sessions MUST be destroyed after use. This is non-negotiable.
    The Deny + Destroy pattern ensures Amplifier maintains sovereignty.

    Args:
        session: The session to destroy.

    Raises:
        NotImplementedError: Skeleton - full implementation in F-003.
    """
    # Skeleton implementation - raises until F-003 implements real logic
    raise NotImplementedError(
        "SDK session destruction not yet implemented. See F-003 session factory."
    )
