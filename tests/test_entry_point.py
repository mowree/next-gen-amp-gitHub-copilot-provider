"""
Entry Point Registration Tests.

Contract: provider-protocol.md (AC-1: mount entry point)
Feature: F-028

Tests that the provider is discoverable by the Amplifier kernel via entry points.
"""

from __future__ import annotations

import pytest


class TestEntryPointRegistration:
    """F-028: Entry point registration tests."""

    def test_entry_point_registered(self) -> None:
        """F-028 AC-3: Kernel can discover provider via entry point."""
        from importlib.metadata import entry_points

        eps = entry_points(group="amplifier.modules")
        names = [ep.name for ep in eps]
        assert "provider-github-copilot" in names, (
            f"Entry point 'provider-github-copilot' not found in amplifier.modules. Found: {names}"
        )

    def test_entry_point_loads_mount_function(self) -> None:
        """F-028 AC-3: Entry point loads mount function."""
        from importlib.metadata import entry_points

        eps = entry_points(group="amplifier.modules")
        ep = next((ep for ep in eps if ep.name == "provider-github-copilot"), None)
        assert ep is not None, "Entry point not found"

        mount_fn = ep.load()
        assert callable(mount_fn), "mount should be callable"
        assert mount_fn.__name__ == "mount", f"Expected 'mount', got '{mount_fn.__name__}'"

    def test_mount_function_signature(self) -> None:
        """F-028 AC-2: mount() has correct signature."""
        import inspect

        from amplifier_module_provider_github_copilot import mount

        sig = inspect.signature(mount)
        params = list(sig.parameters.keys())

        assert "coordinator" in params, "mount() must accept coordinator parameter"
        assert "config" in params, "mount() must accept config parameter"

    def test_module_type_metadata(self) -> None:
        """F-028 AC-2: Module declares type as 'provider'."""
        import amplifier_module_provider_github_copilot as module

        assert hasattr(module, "__amplifier_module_type__"), (
            "Module must declare __amplifier_module_type__"
        )
        assert module.__amplifier_module_type__ == "provider"

    def test_module_exports(self) -> None:
        """F-028 AC-2: Module exports required symbols."""
        import amplifier_module_provider_github_copilot as module

        assert hasattr(module, "mount"), "Module must export mount"
        assert hasattr(module, "GitHubCopilotProvider"), "Module must export GitHubCopilotProvider"
        assert "mount" in module.__all__
        assert "GitHubCopilotProvider" in module.__all__


class TestMountFunction:
    """Tests for mount() behavior."""

    @pytest.mark.asyncio
    async def test_mount_creates_provider(self) -> None:
        """mount() creates and registers provider with coordinator."""
        from unittest.mock import AsyncMock, MagicMock

        from amplifier_module_provider_github_copilot import mount

        coordinator = MagicMock()
        coordinator.mount = AsyncMock()

        cleanup = await mount(coordinator)

        coordinator.mount.assert_called_once()
        call_args = coordinator.mount.call_args
        assert call_args[0][0] == "providers"
        assert call_args[1]["name"] == "github-copilot"
        assert cleanup is not None
        assert callable(cleanup)

    @pytest.mark.asyncio
    async def test_mount_returns_cleanup_function(self) -> None:
        """mount() returns async cleanup callable."""
        import inspect
        from unittest.mock import AsyncMock, MagicMock

        from amplifier_module_provider_github_copilot import mount

        coordinator = MagicMock()
        coordinator.mount = AsyncMock()

        cleanup = await mount(coordinator)

        assert cleanup is not None
        assert callable(cleanup)
        assert inspect.iscoroutinefunction(cleanup)
