"""Pytest configuration and shared fixtures for SDK integration tests.

Provides fixtures for Tier 6 (SDK assumption tests) and Tier 7 (live smoke tests).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    pass


# -- Skip controls --


def _has_github_token() -> bool:
    """Check if any valid GitHub token is available for live tests."""
    for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(var):
            return True
    return False


def _get_github_token() -> str | None:
    """Get the first available GitHub token."""
    for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(var)
        if token:
            return token
    return None


def _sdk_installed() -> bool:
    """Check if github-copilot-sdk is installed."""
    try:
        import copilot  # noqa: F401

        return True
    except ImportError:
        return False


# Skip markers
skip_no_sdk = pytest.mark.skipif(not _sdk_installed(), reason="github-copilot-sdk not installed")

skip_no_token = pytest.mark.skipif(
    not _has_github_token(), reason="No GITHUB_TOKEN available for live SDK tests"
)


# -- Fixtures --


async def _default_permission_handler(permission: Any) -> dict[str, str]:
    """Default permission handler that denies all permission requests.

    SDK ASSUMPTION: The SDK requires on_permission_request handler when creating
    sessions. Without it, create_session() raises ValueError.

    Discovered during F-027 implementation.
    """
    return {"permissionDecision": "deny", "permissionDecisionReason": "test environment"}


@pytest.fixture(scope="module")
async def sdk_client() -> AsyncIterator[Any]:
    """Module-scoped real SDK client for live tests.

    Skips if SDK not installed or no token available.
    Starts client once per test module, stops on cleanup.

    SDK ASSUMPTION: CopilotClient requires on_permission_request handler
    to be set before create_session() can be called.
    """
    copilot = pytest.importorskip("copilot", reason="github-copilot-sdk not installed")

    token = _get_github_token()
    if not token:
        pytest.skip("No GitHub token available for live SDK tests")

    client = copilot.CopilotClient(
        {"github_token": token, "on_permission_request": _default_permission_handler}
    )
    await client.start()
    yield client
    await client.stop()


@pytest.fixture(scope="module")
def sdk_module() -> Any:
    """Import the copilot module, skip if not available.

    Use this for Tier 6 tests that need SDK types but not a running client.
    """
    return pytest.importorskip("copilot", reason="github-copilot-sdk not installed")


@pytest.fixture
def mock_sdk_event_dict() -> dict[str, Any]:
    """Sample SDK event as dict for testing helpers."""
    return {"type": "text_delta", "text": "hello"}


@pytest.fixture
def mock_sdk_event_object() -> Any:
    """Sample SDK event as object for testing helpers."""

    class MockEvent:
        type = "text_delta"
        text = "hello"

    return MockEvent()
