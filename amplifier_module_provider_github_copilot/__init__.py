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

# Eager dependency check: ensure github-copilot-sdk is installed.
# All SDK imports in this module are lazy (inside function bodies) so the module
# would otherwise import successfully without the SDK. That tricks Amplifier's
# provider discovery into thinking the module is fully functional, which prevents
# the automatic dependency-installation fallback from ever running.
# Using importlib.metadata avoids importing the SDK itself at module load time.
# Contract: sdk-boundary.md MUST:5
#
# TESTING: Set SKIP_SDK_CHECK=1 to allow test imports without SDK installed.
# Tests use pytest.importorskip() and skip markers to handle SDK availability.
import os as _os
from importlib.metadata import PackageNotFoundError as _PkgNotFoundError
from importlib.metadata import version as _pkg_version

if not _os.environ.get("SKIP_SDK_CHECK"):
    try:
        _pkg_version("github-copilot-sdk")
    except _PkgNotFoundError as _e:
        raise ImportError(
            "Required dependency 'github-copilot-sdk' is not installed. "
            "Install with:  pip install 'github-copilot-sdk>=0.1.32,<0.2.0'"
        ) from _e

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
