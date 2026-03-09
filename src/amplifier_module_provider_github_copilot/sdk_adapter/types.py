"""
Domain types for SDK adapter.

These types are the ONLY types that cross the SDK boundary.
SDK types MUST NOT leak outside this module.

Contract: contracts/sdk-boundary.md
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SessionConfig:
    """Configuration for creating an SDK session.

    Attributes:
        model: The model identifier (e.g., "gpt-4", "claude-3").
        system_prompt: Optional system prompt for the session.
        max_tokens: Optional maximum tokens for responses.
    """

    model: str
    system_prompt: str | None = None
    max_tokens: int | None = None


@dataclass
class DomainEvent:
    """Event from SDK translated to domain representation.

    Attributes:
        type: Event type (e.g., "text_delta", "tool_call", "thinking").
        data: Event payload as dictionary.
    """

    type: str
    data: dict[str, Any]


# SDKSession is intentionally an opaque type alias.
# Domain code should not access SDK session internals.
# In the skeleton, we use Any; real implementation will wrap SDK session.
SDKSession = Any
