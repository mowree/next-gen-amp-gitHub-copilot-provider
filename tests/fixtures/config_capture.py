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
        """Create a minimal mock session with required methods only."""
        session = MagicMock()
        session.session_id = "mock-session-001"
        session.disconnect = AsyncMock()
        session.register_pre_tool_use_hook = MagicMock()
        return session

    async def create_session(self, config: dict[str, Any]) -> Any:
        """Capture config and return mock session."""
        if not isinstance(config, dict):
            raise TypeError(
                f"create_session expects dict, got {type(config).__name__}. "
                f"This mock enforces the SDK contract."
            )
        self.captured_configs.append(copy.deepcopy(config))
        return self._mock_session

    @property
    def last_config(self) -> dict[str, Any]:
        """Most recent captured config."""
        if not self.captured_configs:
            raise AssertionError("No configs captured. Was create_session called?")
        return self.captured_configs[-1]
