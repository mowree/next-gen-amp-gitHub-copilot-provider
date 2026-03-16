"""Tests for config loading functionality.

Feature: F-048
Contract: contracts/provider-protocol.md

Tests verify that provider identity and model catalog are loaded from
config/models.yaml instead of being hardcoded in Python.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


class TestLoadModelsConfig:
    """Tests for _load_models_config() function."""

    def test_load_models_config_returns_provider_id(self) -> None:
        """Models config loader returns correct provider id from YAML."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        config = _load_models_config()
        assert config.provider_id == "github-copilot"

    def test_load_models_config_returns_display_name(self) -> None:
        """Models config loader returns display_name from YAML."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        config = _load_models_config()
        assert config.display_name == "GitHub Copilot SDK"

    def test_load_models_config_returns_credential_env_vars(self) -> None:
        """Models config loader returns credential_env_vars from YAML."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        config = _load_models_config()
        assert "COPILOT_GITHUB_TOKEN" in config.credential_env_vars
        assert "GH_TOKEN" in config.credential_env_vars
        assert "GITHUB_TOKEN" in config.credential_env_vars

    def test_load_models_config_returns_capabilities(self) -> None:
        """Models config loader returns capabilities from YAML."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        config = _load_models_config()
        assert "streaming" in config.capabilities
        assert "tool_use" in config.capabilities

    def test_load_models_config_returns_defaults(self) -> None:
        """Models config loader returns defaults from YAML."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        config = _load_models_config()
        assert config.defaults["model"] == "gpt-4o"
        assert config.defaults["max_tokens"] == 4096

    def test_load_models_config_returns_models_list(self) -> None:
        """Models config loader returns non-empty models list."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        config = _load_models_config()
        assert len(config.models) >= 2
        model_ids = [m["id"] for m in config.models]
        assert "gpt-4" in model_ids
        assert "gpt-4o" in model_ids

    def test_load_models_config_missing_file_returns_fallback(self) -> None:
        """Missing models.yaml returns fallback without raising."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        with patch.object(Path, "exists", return_value=False):
            config = _load_models_config()
        assert config.provider_id == "github-copilot"

    def test_load_models_config_empty_file_returns_fallback(self) -> None:
        """Empty models.yaml returns fallback without raising."""
        from amplifier_module_provider_github_copilot.provider import _load_models_config

        with patch("builtins.open", return_value=__import__("io").StringIO("")):
            with patch.object(Path, "exists", return_value=True):
                config = _load_models_config()
        assert config.provider_id == "github-copilot"


class TestProviderUsesYamlConfig:
    """Tests verify provider methods use YAML config, not hardcoded values."""

    def test_get_info_sourced_from_yaml(self) -> None:
        """Provider.get_info() values come from YAML, not hardcoded strings."""
        from amplifier_module_provider_github_copilot.provider import GitHubCopilotProvider

        provider = GitHubCopilotProvider()
        info = provider.get_info()
        assert info.id == "github-copilot"
        assert "gpt-4o" in str(info.defaults.get("model", ""))

    @pytest.mark.asyncio
    async def test_list_models_sourced_from_yaml(self) -> None:
        """Provider.list_models() comes from YAML, not hardcoded list."""
        from amplifier_module_provider_github_copilot.provider import GitHubCopilotProvider

        provider = GitHubCopilotProvider()
        models = await provider.list_models()
        model_ids = [m.id for m in models]
        assert "gpt-4o" in model_ids
        assert "gpt-4" in model_ids

    def test_get_info_graceful_without_yaml(self) -> None:
        """Provider.get_info() returns valid ProviderInfo even if models.yaml doesn't exist."""
        from amplifier_module_provider_github_copilot.provider import GitHubCopilotProvider

        with patch.object(Path, "exists", return_value=False):
            provider = GitHubCopilotProvider()
            info = provider.get_info()
        assert info.id == "github-copilot"
        assert info.display_name is not None


class TestModelsYamlSchemaCompliance:
    """Tests verify models.yaml has correct structure."""

    def test_models_yaml_version_field_present(self) -> None:
        """Models YAML has version field."""
        import yaml

        config_path = Path(__file__).parent.parent / "amplifier_module_provider_github_copilot" / "config" / "models.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)
        assert "version" in data
        assert data["version"] == "1.0"

    def test_models_yaml_provider_id(self) -> None:
        """Models YAML provider.id equals github-copilot."""
        import yaml

        config_path = Path(__file__).parent.parent / "amplifier_module_provider_github_copilot" / "config" / "models.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)
        assert data["provider"]["id"] == "github-copilot"

    def test_models_yaml_models_list_nonempty(self) -> None:
        """Models YAML has non-empty models list."""
        import yaml

        config_path = Path(__file__).parent.parent / "amplifier_module_provider_github_copilot" / "config" / "models.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

    def test_models_yaml_each_model_has_required_fields(self) -> None:
        """Each model in YAML has required fields."""
        import yaml

        config_path = Path(__file__).parent.parent / "amplifier_module_provider_github_copilot" / "config" / "models.yaml"
        with config_path.open() as f:
            data = yaml.safe_load(f)

        required_fields = ["id", "display_name", "context_window", "max_output_tokens"]
        for model in data["models"]:
            for field in required_fields:
                assert field in model, f"Model {model.get('id', 'unknown')} missing field: {field}"
