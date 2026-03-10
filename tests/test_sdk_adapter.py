"""
Tests for SDK Adapter skeleton (F-001) and client exports (F-017).

Contract: contracts/sdk-boundary.md
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


class TestSDKAdapterExports:
    """Test sdk_adapter module exports."""

    def test_exports_session_config(self) -> None:
        """sdk_adapter exports SessionConfig."""
        from amplifier_module_provider_github_copilot.sdk_adapter import SessionConfig

        assert SessionConfig is not None

    def test_exports_copilot_client_wrapper(self) -> None:
        """sdk_adapter exports CopilotClientWrapper."""
        from amplifier_module_provider_github_copilot.sdk_adapter import CopilotClientWrapper

        assert CopilotClientWrapper is not None

    def test_exports_copilot_session_wrapper(self) -> None:
        """sdk_adapter exports CopilotSessionWrapper."""
        from amplifier_module_provider_github_copilot.sdk_adapter import CopilotSessionWrapper

        assert CopilotSessionWrapper is not None
