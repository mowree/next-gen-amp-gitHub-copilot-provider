"""
Tests for SDK Adapter skeleton (F-001).

Contract: contracts/sdk-boundary.md
Feature: specs/features/F-001-sdk-adapter-skeleton.md

Acceptance Criteria:
- AC-1: sdk_adapter/ directory exists with __init__.py, types.py, driver.py
- AC-2: No SDK imports outside of sdk_adapter/
- AC-3: DomainEvent dataclass defined with type and data fields
- AC-4: SessionConfig dataclass defined with model, system_prompt, max_tokens
- AC-5: create_session and destroy_session stubs exist
"""

from dataclasses import fields


class TestSDKAdapterTypes:
    """Test domain types exposed by sdk_adapter."""

    def test_domain_event_has_type_field(self) -> None:
        """AC-3: DomainEvent has type field."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import DomainEvent

        event = DomainEvent(type="text_delta", data={"content": "hello"})
        assert event.type == "text_delta"

    def test_domain_event_has_data_field(self) -> None:
        """AC-3: DomainEvent has data field."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import DomainEvent

        event = DomainEvent(type="tool_call", data={"name": "read_file", "args": {}})
        assert event.data == {"name": "read_file", "args": {}}

    def test_domain_event_is_dataclass(self) -> None:
        """AC-3: DomainEvent is a dataclass."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import DomainEvent

        field_names = {f.name for f in fields(DomainEvent)}
        assert "type" in field_names
        assert "data" in field_names

    def test_session_config_has_model(self) -> None:
        """AC-4: SessionConfig has model field."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        config = SessionConfig(model="gpt-4")
        assert config.model == "gpt-4"

    def test_session_config_has_system_prompt(self) -> None:
        """AC-4: SessionConfig has system_prompt field with None default."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        config = SessionConfig(model="gpt-4")
        assert config.system_prompt is None

        config_with_prompt = SessionConfig(model="gpt-4", system_prompt="You are helpful.")
        assert config_with_prompt.system_prompt == "You are helpful."

    def test_session_config_has_max_tokens(self) -> None:
        """AC-4: SessionConfig has max_tokens field with None default."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        config = SessionConfig(model="gpt-4")
        assert config.max_tokens is None

        config_with_tokens = SessionConfig(model="gpt-4", max_tokens=1000)
        assert config_with_tokens.max_tokens == 1000

    def test_session_config_is_dataclass(self) -> None:
        """AC-4: SessionConfig is a dataclass."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        field_names = {f.name for f in fields(SessionConfig)}
        assert "model" in field_names
        assert "system_prompt" in field_names
        assert "max_tokens" in field_names


class TestSDKAdapterDriver:
    """Test driver functions exposed by sdk_adapter."""

    def test_create_session_exists(self) -> None:
        """AC-5: create_session function exists."""
        from amplifier_module_provider_github_copilot.sdk_adapter.driver import create_session

        assert callable(create_session)

    def test_destroy_session_exists(self) -> None:
        """AC-5: destroy_session function exists."""
        from amplifier_module_provider_github_copilot.sdk_adapter.driver import destroy_session

        assert callable(destroy_session)


class TestSDKAdapterExports:
    """Test sdk_adapter module exports."""

    def test_exports_domain_event(self) -> None:
        """sdk_adapter exports DomainEvent."""
        from amplifier_module_provider_github_copilot.sdk_adapter import DomainEvent

        assert DomainEvent is not None

    def test_exports_session_config(self) -> None:
        """sdk_adapter exports SessionConfig."""
        from amplifier_module_provider_github_copilot.sdk_adapter import SessionConfig

        assert SessionConfig is not None

    def test_exports_create_session(self) -> None:
        """sdk_adapter exports create_session."""
        from amplifier_module_provider_github_copilot.sdk_adapter import create_session

        assert callable(create_session)

    def test_exports_destroy_session(self) -> None:
        """sdk_adapter exports destroy_session."""
        from amplifier_module_provider_github_copilot.sdk_adapter import destroy_session

        assert callable(destroy_session)
