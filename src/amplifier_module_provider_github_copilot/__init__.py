"""
GitHub Copilot Provider for Amplifier.

Three-Medium Architecture:
- Python for mechanism (~300 lines)
- YAML for policy (~200 lines)
- Markdown for contracts (~400 lines)

Contract: contracts/provider-protocol.md
Feature: F-020
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .provider import GitHubCopilotProvider, ModelInfo, ProviderInfo

__version__ = "0.1.0"

# Amplifier module metadata
__amplifier_module_type__ = "provider"

# Type alias for cleanup function
CleanupFn = Callable[[], Awaitable[None]]


async def mount(
    coordinator: Any,
    config: dict[str, Any] | None = None,
) -> CleanupFn | None:
    """Mount the GitHub Copilot provider.

    Contract: provider-protocol.md
    Feature: F-020 AC-1

    Args:
        coordinator: Amplifier kernel coordinator.
        config: Optional provider configuration.

    Returns:
        Cleanup callable, or None.
    """
    provider = GitHubCopilotProvider(config, coordinator)
    await coordinator.mount("providers", provider, name="github-copilot")

    async def cleanup() -> None:
        await provider.close()

    return cleanup


__all__ = ["mount", "GitHubCopilotProvider", "ProviderInfo", "ModelInfo"]
