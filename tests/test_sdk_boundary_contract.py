"""Boundary contract tests for SDK session configuration.

These tests verify the exact configuration dict that CopilotClientWrapper.session()
sends to client.create_session(). They use ConfigCapturingMock instead of MagicMock
to ensure we test what is SENT, not just that something was called.

Contract: contracts/sdk-boundary.md
Feature: F-046 (testing architecture), F-044 (system_message replace), F-045 (disable SDK tools)
"""

from __future__ import annotations

import pytest

from amplifier_module_provider_github_copilot.sdk_adapter.client import (
    CopilotClientWrapper,
)
from tests.fixtures.config_capture import ConfigCapturingMock


class TestSessionConfigContract:
    """Verify the session_config dict sent to SDK matches our contract."""

    @pytest.mark.asyncio
    async def test_available_tools_always_empty_list(self) -> None:
        """F-045: SDK built-in tools MUST be disabled.

        Contract: deny-destroy:NoExecution:MUST:3
        SDK ref: copilot/types.py SessionConfig.available_tools
        SDK ref: copilot/client.py lines 527-529 (available_tools is not None check)
        """
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="gpt-4o"):
            pass

        config = mock_client.last_config
        assert "available_tools" in config, "available_tools MUST be set"
        assert config["available_tools"] == [], "available_tools MUST be empty list"

    @pytest.mark.asyncio
    async def test_system_message_uses_replace_mode(self) -> None:
        """F-044: System message MUST use replace mode.

        SDK ref: copilot/types.py SystemMessageConfig
        SDK ref: copilot/client.py line 522-524 (system_message handling)
        """
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(
            model="gpt-4o",
            system_message="You are the Amplifier assistant."
        ):
            pass

        config = mock_client.last_config
        assert config["system_message"]["mode"] == "replace"
        assert config["system_message"]["content"] == "You are the Amplifier assistant."

    @pytest.mark.asyncio
    async def test_system_message_absent_when_not_provided(self) -> None:
        """No system_message key when caller doesn't provide one."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="gpt-4o"):
            pass

        config = mock_client.last_config
        assert "system_message" not in config

    @pytest.mark.asyncio
    async def test_permission_handler_always_set(self) -> None:
        """F-033: Permission handler MUST be set on every session.

        Contract: deny-destroy:DenyHook:MUST:1
        """
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="gpt-4o"):
            pass

        config = mock_client.last_config
        assert "on_permission_request" in config
        assert callable(config["on_permission_request"])

    @pytest.mark.asyncio
    async def test_streaming_always_enabled(self) -> None:
        """Streaming MUST be enabled for event-based tool capture."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="gpt-4o"):
            pass

        config = mock_client.last_config
        assert config["streaming"] is True

    @pytest.mark.asyncio
    async def test_model_passed_through(self) -> None:
        """Model parameter forwarded to SDK session config."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="claude-sonnet-4"):
            pass

        config = mock_client.last_config
        assert config["model"] == "claude-sonnet-4"

    @pytest.mark.asyncio
    async def test_deny_hook_registered_on_session(self) -> None:
        """Deny hook MUST be registered after session creation.

        Contract: deny-destroy:DenyHook:MUST:1
        """
        mock_client = ConfigCapturingMock()

        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="gpt-4o"):
            pass

        # The strict stub records hook registrations via _hook_mock
        mock_client._mock_session._hook_mock.assert_called_once()


class TestConfigInvariants:
    """Configuration invariants that must ALWAYS hold."""

    INVARIANTS: dict[str, object] = {
        "available_tools": [],           # F-045: No SDK tools
        "streaming": True,               # Required for event capture
    }

    CALLABLE_INVARIANTS = [
        "on_permission_request",         # F-033: Always set
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("model", ["gpt-4", "gpt-4o", "claude-sonnet-4", None])
    async def test_invariants_hold_for_any_model(self, model: str | None) -> None:
        """Config invariants hold regardless of model selection."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        kwargs: dict[str, object] = {}
        if model:
            kwargs["model"] = model

        async with wrapper.session(**kwargs):  # type: ignore[arg-type]
            pass

        config = mock_client.last_config
        for key, expected in self.INVARIANTS.items():
            assert config.get(key) == expected, (
                f"Invariant violated: {key} should be {expected!r}, got {config.get(key)!r}"
            )
        for key in self.CALLABLE_INVARIANTS:
            assert key in config and callable(config[key]), (
                f"Callable invariant violated: {key} must be present and callable"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("system_message", [
        "You are helpful",
        "Custom persona",
        None,
    ])
    async def test_invariants_hold_with_system_message_variations(
        self, system_message: str | None
    ) -> None:
        """Config invariants hold regardless of system message."""
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        kwargs: dict[str, object] = {"model": "gpt-4o"}
        if system_message:
            kwargs["system_message"] = system_message

        async with wrapper.session(**kwargs):  # type: ignore[arg-type]
            pass

        config = mock_client.last_config
        assert config.get("available_tools") == []
        assert config.get("streaming") is True

    @pytest.mark.asyncio
    async def test_no_unexpected_keys_in_config(self) -> None:
        """Session config should only contain known SDK keys.

        Guards against typos or wrong key names that SDK silently ignores.
        SDK ref: copilot/types.py SessionConfig fields
        """
        KNOWN_SDK_KEYS = {
            "session_id", "client_name", "model", "reasoning_effort",
            "tools", "system_message", "available_tools", "excluded_tools",
            "on_permission_request", "on_user_input_request", "hooks",
            "working_directory", "provider", "streaming", "mcp_servers",
            "custom_agents", "agent", "config_dir", "skill_directories",
            "disabled_skills", "infinite_sessions", "on_event",
        }

        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="gpt-4o", system_message="test"):
            pass

        config = mock_client.last_config
        unknown_keys = set(config.keys()) - KNOWN_SDK_KEYS
        assert unknown_keys == set(), (
            f"Unknown keys in session config: {unknown_keys}. "
            f"These may be typos that the SDK silently ignores."
        )
