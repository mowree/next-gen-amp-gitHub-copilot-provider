"""
SDK Adapter Layer - The Membrane.

All SDK imports live here and only here.
Domain code MUST NOT import from SDK directly.

Contract: contracts/sdk-boundary.md
Feature: F-001

Exports:
- DomainEvent: Event from SDK translated to domain types
- SessionConfig: Configuration for SDK session creation
- create_session: Create a new SDK session
- destroy_session: Destroy an SDK session
"""

from .driver import create_session, destroy_session
from .types import DomainEvent, SessionConfig

__all__ = [
    "DomainEvent",
    "SessionConfig",
    "create_session",
    "destroy_session",
]
