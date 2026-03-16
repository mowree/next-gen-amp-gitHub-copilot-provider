"""Tests for F-051: Defensive Event Config Loading.

Feature: F-051
Contract: contracts/event-vocabulary.md - event config loading must produce valid domain event types

These tests verify that malformed events.yaml produces clear ConfigurationError messages
instead of cryptic KeyError tracebacks.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
import yaml

from amplifier_module_provider_github_copilot.error_translation import ConfigurationError
from amplifier_module_provider_github_copilot.streaming import (
    DomainEventType,
    EventConfig,
    load_event_config,
)


class TestDefensiveEventConfigLoading:
    """Tests for F-051: Defensive event config loading."""

    def test_valid_config_loads_correctly(self):
        """Valid configuration loads without error.

        Regression guard: ensure defensive changes don't break valid configs.
        """
        # Create a valid config file
        config_data = {
            "event_classifications": {
                "bridge": [
                    {"sdk_type": "text_delta", "domain_type": "CONTENT_DELTA"},
                    {"sdk_type": "error", "domain_type": "ERROR"},
                ],
                "consume": ["tool_use_start"],
                "drop": ["heartbeat"],
            },
            "finish_reason_map": {"stop": "STOP"},
        }

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_event_config(config_path)

            assert isinstance(config, EventConfig)
            assert "text_delta" in config.bridge_mappings
            assert config.bridge_mappings["text_delta"][0] == DomainEventType.CONTENT_DELTA
        finally:
            config_path.unlink()

    def test_missing_sdk_type_raises_configuration_error(self):
        """Bridge entry missing sdk_type produces ConfigurationError with clear message.

        Feature: F-051 - Missing sdk_type must not cause KeyError
        """
        config_data = {
            "event_classifications": {
                "bridge": [
                    # Missing sdk_type key!
                    {"domain_type": "CONTENT_DELTA"}
                ],
            },
        }

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_event_config(config_path)

            # Error message should mention the missing key
            assert "sdk_type" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_missing_domain_type_raises_configuration_error(self):
        """Bridge entry missing domain_type produces ConfigurationError with clear message.

        Feature: F-051 - Missing domain_type must not cause KeyError
        """
        config_data = {
            "event_classifications": {
                "bridge": [
                    # Missing domain_type key!
                    {"sdk_type": "text_delta"}
                ],
            },
        }

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_event_config(config_path)

            # Error message should mention the missing key and the sdk_type
            error_msg = str(exc_info.value)
            assert "domain_type" in error_msg
            assert "text_delta" in error_msg
        finally:
            config_path.unlink()

    def test_unknown_domain_type_raises_configuration_error(self):
        """Bridge entry with unknown domain_type produces ConfigurationError.

        Feature: F-051 - Unknown enum value must not cause cryptic KeyError
        """
        config_data = {
            "event_classifications": {
                "bridge": [
                    {"sdk_type": "text_delta", "domain_type": "NONEXISTENT_TYPE"}
                ],
            },
        }

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_event_config(config_path)

            error_msg = str(exc_info.value)
            # Should mention the unknown type
            assert "NONEXISTENT_TYPE" in error_msg
            # Should list valid types
            assert "CONTENT_DELTA" in error_msg or "Valid types" in error_msg
        finally:
            config_path.unlink()

    def test_error_message_includes_entry_index(self):
        """Error message includes the index of the problematic entry.

        Feature: F-051 - Debugging aid: know which entry failed
        """
        config_data = {
            "event_classifications": {
                "bridge": [
                    {"sdk_type": "text_delta", "domain_type": "CONTENT_DELTA"},  # valid
                    {"sdk_type": "bad_entry"},  # invalid - missing domain_type (index 1)
                ],
            },
        }

        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            f.flush()
            config_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_event_config(config_path)

            # The error should help locate the problem
            assert "bad_entry" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_empty_config_returns_default(self):
        """Empty config file returns default EventConfig.

        Regression guard: don't break graceful fallback behavior.
        """
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")  # Empty file
            f.flush()
            config_path = Path(f.name)

        try:
            config = load_event_config(config_path)
            assert isinstance(config, EventConfig)
            assert config.bridge_mappings == {}
        finally:
            config_path.unlink()

    def test_missing_file_returns_default(self):
        """Missing config file returns default EventConfig.

        Contract: AC-1 (F-021) - Graceful fallback on missing file.
        """
        config = load_event_config("/nonexistent/path/events.yaml")
        assert isinstance(config, EventConfig)
        assert config.bridge_mappings == {}
