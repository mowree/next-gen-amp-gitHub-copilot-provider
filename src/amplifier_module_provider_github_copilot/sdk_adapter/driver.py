"""
SDK driver functions for session lifecycle.

These functions manage SDK session creation and destruction.
All SDK imports MUST be contained within this module.

Contract: contracts/sdk-boundary.md
Feature: F-001

Note: This is a skeleton implementation. Full SDK integration
comes in later features (F-003 session factory).
"""

from collections.abc import Callable
from typing import Any

from .types import SDKSession, SessionConfig


async def create_session(
    config: SessionConfig,
    deny_hook: Callable[..., Any] | None = None,
) -> SDKSession:
    """Create a new SDK session.

    Args:
        config: Session configuration.
        deny_hook: Hook to deny tool execution (required for sovereignty).

    Returns:
        Opaque session handle.

    Raises:
        NotImplementedError: Skeleton - full implementation in F-003.
    """
    # Skeleton implementation - raises until F-003 implements real logic
    raise NotImplementedError(
        "SDK session creation not yet implemented. See F-003 session factory."
    )


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
