"""
SDK Adapter Layer - The Membrane.

All SDK imports live here and only here.
Domain code MUST NOT import from SDK directly.

Contract: contracts/sdk-boundary.md

Exports:
- SessionConfig: Configuration for SDK session creation
- CopilotClientWrapper: SDK client with lifecycle management
"""

from .client import CopilotClientWrapper
from .types import SessionConfig

__all__ = [
    "CopilotClientWrapper",
    "SessionConfig",
]
