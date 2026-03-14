"""Fixture for capturing SDK session configuration.

Unlike MagicMock, this fixture:
1. Records the exact dict passed to create_session()
2. Validates it's a dict (not arbitrary args)
3. Returns a minimal but functional mock session
4. Does NOT accept arbitrary method calls

Contract: contracts/sdk-boundary.md
Feature: F-046
"""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock


class ConfigCapturingMock:
    """Mock SDK client that captures session configuration.

    Usage:
        mock_client = ConfigCapturingMock()
        wrapper = CopilotClientWrapper(sdk_client=mock_client)

        async with wrapper.session(model="gpt-4o"):
            pass

        config = mock_client.captured_configs[0]
        assert config["available_tools"] == []
    """

    def __init__(self) -> None:
        self.captured_configs: list[dict[str, Any]] = []
        self._mock_session = self._create_mock_session()

    def _create_mock_session(self) -> Any:
        """Create a strict mock session with only the required methods.

        Unlike MagicMock, this stub only exposes the methods our code actually needs.
        Accessing undefined attributes will raise AttributeError.
        """

        class StrictSessionStub:
            """Strict stub that only exposes known SDK session methods."""

            def __init__(self) -> None:
                self.session_id = "mock-session-001"
                self._disconnect_mock = AsyncMock()
                self._hook_mock = MagicMock()

            async def disconnect(self) -> None:
                """Disconnect the session."""
                await self._disconnect_mock()

            def register_pre_tool_use_hook(self, hook: Any) -> None:
                """Register a pre-tool-use hook."""
                self._hook_mock(hook)

        return StrictSessionStub()

    async def create_session(self, config: dict[str, Any]) -> Any:
        """Capture config and return mock session."""
        # Deep copy to capture the exact state at call time
        self.captured_configs.append(copy.deepcopy(config))
        return self._mock_session

    @property
    def last_config(self) -> dict[str, Any]:
        """Most recent captured config."""
        if not self.captured_configs:
            raise AssertionError("No configs captured. Was create_session called?")
        return self.captured_configs[-1]

    def assert_hook_registered(self) -> None:
        """Assert that register_pre_tool_use_hook was called exactly once."""
        self._mock_session._hook_mock.assert_called_once()
