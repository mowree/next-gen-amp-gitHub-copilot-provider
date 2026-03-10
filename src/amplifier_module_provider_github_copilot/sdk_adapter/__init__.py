"""
SDK Adapter Layer - The Membrane.

All SDK imports live here and only here.
Domain code MUST NOT import from SDK directly.

Contract: contracts/sdk-boundary.md

Exports:
- SessionConfig: Configuration for SDK session creation
- CopilotClientWrapper: SDK client with lifecycle management
- CopilotSessionWrapper: Opaque session handle
"""

from .client import CopilotClientWrapper, CopilotSessionWrapper
from .types import SessionConfig

__all__ = [
    "CopilotClientWrapper",
    "CopilotSessionWrapper",
    "SessionConfig",
]
