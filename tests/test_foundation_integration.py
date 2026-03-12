"""
Tests for F-022: Foundation Integration.

Verifies bundle.md, exports, and config loading.
"""

from __future__ import annotations

import inspect
from pathlib import Path


class TestBundleFile:
    """AC-1: bundle.md exists and has required structure."""

    def test_bundle_file_exists(self) -> None:
        """bundle.md exists at project root."""
        bundle_path = Path(__file__).parent.parent / "bundle.md"
        assert bundle_path.exists(), "bundle.md should exist at project root"

    def test_bundle_has_frontmatter(self) -> None:
        """bundle.md contains YAML frontmatter."""
        bundle_path = Path(__file__).parent.parent / "bundle.md"
        content = bundle_path.read_text()
        assert content.startswith("---"), "bundle.md should start with YAML frontmatter"
        assert "bundle:" in content, "bundle.md should have bundle section"
        assert "providers:" in content, "bundle.md should have providers section"


class TestModuleExports:
    """AC-2: Module exports are correct."""

    def test_all_exports_defined(self) -> None:
        """__all__ is defined with required exports."""
        import amplifier_module_provider_github_copilot as mod

        assert hasattr(mod, "__all__")
        assert "mount" in mod.__all__
        assert "GitHubCopilotProvider" in mod.__all__

    def test_amplifier_module_type(self) -> None:
        """__amplifier_module_type__ is set to 'provider'."""
        import amplifier_module_provider_github_copilot as mod

        assert hasattr(mod, "__amplifier_module_type__")
        assert mod.__amplifier_module_type__ == "provider"

    def test_mount_is_async(self) -> None:
        """mount() is an async function."""
        import asyncio
        import amplifier_module_provider_github_copilot as mod

        assert asyncio.iscoroutinefunction(mod.mount)


class TestSkillFile:
    """AC-3: Skill file exists."""

    def test_skill_file_exists(self) -> None:
        """three-medium-extension skill exists."""
        skill_path = (
            Path(__file__).parent.parent
            / ".amplifier"
            / "skills"
            / "three-medium-extension"
            / "skill.md"
        )
        assert skill_path.exists(), "skill.md should exist"

    def test_skill_has_frontmatter(self) -> None:
        """Skill file has YAML frontmatter."""
        skill_path = (
            Path(__file__).parent.parent
            / ".amplifier"
            / "skills"
            / "three-medium-extension"
            / "skill.md"
        )
        content = skill_path.read_text()
        assert content.startswith("---"), "skill.md should start with YAML frontmatter"
        assert "skill:" in content, "skill.md should have skill section"


class TestConfigPackage:
    """AC-4: Config path uses importlib.resources."""

    def test_config_init_exists(self) -> None:
        """config/__init__.py exists (makes it a package)."""
        config_init = Path(__file__).parent.parent / "config" / "__init__.py"
        assert config_init.exists(), "config/__init__.py should exist"

    def test_create_deny_hook_exported(self) -> None:
        """create_deny_hook is exported from sdk_adapter."""
        from amplifier_module_provider_github_copilot.sdk_adapter import create_deny_hook

        assert callable(create_deny_hook)

    def test_error_config_loads_with_fallback(self) -> None:
        """Error config loading falls back gracefully."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            _load_error_config_once,
        )
        from amplifier_module_provider_github_copilot.error_translation import ErrorConfig

        # Should return ErrorConfig (either loaded or default)
        config = _load_error_config_once()
        assert isinstance(config, ErrorConfig)
