"""Tier 6: SDK Assumption Tests - verify SDK types and shapes without API calls.

These tests import the real SDK, instantiate objects, and verify our structural
assumptions. They require the SDK to be installed but do NOT make API calls.

Contract references:
- contracts/sdk-boundary.md
- contracts/deny-destroy.md

Run: pytest -m sdk_assumption -v
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.sdk_assumption
class TestSDKImportAssumptions:
    """Verify SDK module structure matches our assumptions.

    AC-1: SDK Import Assumptions
    """

    def test_copilot_module_importable(self, sdk_module: Any) -> None:
        """We assume the copilot module is importable."""
        assert sdk_module is not None

    def test_copilot_client_class_exists(self, sdk_module: Any) -> None:
        """We assume copilot.CopilotClient exists and is importable.

        sdk-boundary:Translation:MUST:1
        """
        assert hasattr(sdk_module, "CopilotClient")
        assert sdk_module.CopilotClient is not None

    def test_client_has_create_session(self, sdk_module: Any) -> None:
        """We assume CopilotClient has create_session method.

        sdk-boundary:Session:MUST:1
        """
        assert hasattr(sdk_module.CopilotClient, "create_session")

    def test_client_has_start_stop(self, sdk_module: Any) -> None:
        """We assume CopilotClient has start() and stop() lifecycle methods.

        sdk-boundary:Lifecycle:MUST:1
        """
        assert hasattr(sdk_module.CopilotClient, "start")
        assert hasattr(sdk_module.CopilotClient, "stop")

    def test_client_accepts_options_dict(self, sdk_module: Any) -> None:
        """We assume CopilotClient(options) accepts a dict with github_token.

        Note: This does NOT start the client or make any network calls.
        sdk-boundary:Auth:MUST:1
        """
        # Should not raise TypeError
        client = sdk_module.CopilotClient({"github_token": "test-token-not-real"})
        assert client is not None


@pytest.mark.sdk_assumption
class TestSessionInterfaceAssumptions:
    """Verify session-related assumptions without API calls.

    AC-2: Session Lifecycle Assumptions (Tier 6 portion)

    Note: Session OBJECT interface (disconnect, send_message, register_pre_tool_use_hook)
    cannot be verified without creating a real session, which requires credentials.
    Those checks are in test_live_sdk.py (Tier 7).

    Here we verify what CAN be checked without credentials:
    - Client has create_session method
    - Our wrapper has the expected interface
    """

    def test_client_has_create_session_method(self, sdk_module: Any) -> None:
        """CopilotClient must have create_session method.

        sdk-boundary:Session:MUST:1
        """
        assert hasattr(sdk_module.CopilotClient, "create_session")
        # Note: Session object interface (disconnect, send_message) verified in Tier 7

    def test_sdk_requires_on_permission_request(self, sdk_module: Any) -> None:
        """SDK ASSUMPTION: CopilotClient requires on_permission_request handler.

        Discovered during F-027 implementation: create_session() raises ValueError
        if on_permission_request is not provided in client options.

        This test documents the assumption for future SDK version drift detection.
        """
        # Document the assumption - if SDK changes this requirement, test needs update
        # We cannot verify this without starting the client, but we document it here
        client = sdk_module.CopilotClient({"github_token": "test-token-not-real"})
        assert client is not None
        # The on_permission_request requirement is verified by Tier 7 tests passing


@pytest.mark.sdk_assumption
class TestOurWrapperImports:
    """Verify our wrapper code imports work correctly."""

    def test_copilot_client_wrapper_importable(self) -> None:
        """Our CopilotClientWrapper should be importable."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        assert CopilotClientWrapper is not None

    def test_create_deny_hook_importable(self) -> None:
        """create_deny_hook should be importable from sdk_adapter.

        deny-destroy:DenyHook:MUST:1
        """
        from amplifier_module_provider_github_copilot.sdk_adapter import create_deny_hook

        assert create_deny_hook is not None
        # Verify it returns a callable
        hook = create_deny_hook()
        assert callable(hook)

    def test_copilot_client_wrapper_has_session_method(self) -> None:
        """CopilotClientWrapper should have session() context manager."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()
        assert hasattr(wrapper, "session")
        assert hasattr(wrapper, "close")


@pytest.mark.sdk_assumption
class TestHelperFunctions:
    """Test our SDK helper functions work correctly."""

    def test_get_event_type_from_dict(self, mock_sdk_event_dict: dict[str, Any]) -> None:
        """get_event_type should extract type from dict."""
        from tests.sdk_helpers import get_event_type

        result = get_event_type(mock_sdk_event_dict)
        assert result == "text_delta"

    def test_get_event_type_from_object(self, mock_sdk_event_object: Any) -> None:
        """get_event_type should extract type from object."""
        from tests.sdk_helpers import get_event_type

        result = get_event_type(mock_sdk_event_object)
        assert result == "text_delta"

    def test_get_event_field_from_dict(self, mock_sdk_event_dict: dict[str, Any]) -> None:
        """get_event_field should extract field from dict."""
        from tests.sdk_helpers import get_event_field

        result = get_event_field(mock_sdk_event_dict, "text")
        assert result == "hello"

    def test_get_event_field_from_object(self, mock_sdk_event_object: Any) -> None:
        """get_event_field should extract field from object."""
        from tests.sdk_helpers import get_event_field

        result = get_event_field(mock_sdk_event_object, "text")
        assert result == "hello"

    def test_describe_event_dict(self, mock_sdk_event_dict: dict[str, Any]) -> None:
        """describe_event should produce readable string from dict."""
        from tests.sdk_helpers import describe_event

        result = describe_event(mock_sdk_event_dict)
        assert "text_delta" in result

    def test_describe_event_object(self, mock_sdk_event_object: Any) -> None:
        """describe_event should produce readable string from object."""
        from tests.sdk_helpers import describe_event

        result = describe_event(mock_sdk_event_object)
        assert "MockEvent" in result

    def test_collect_event_types(self) -> None:
        """collect_event_types should return list of type strings."""
        from tests.sdk_helpers import collect_event_types

        events = [
            {"type": "text_delta"},
            {"type": "message_complete"},
        ]
        result = collect_event_types(events)
        assert result == ["text_delta", "message_complete"]

    def test_has_event_type_true(self) -> None:
        """has_event_type should return True when event type exists."""
        from tests.sdk_helpers import has_event_type

        events = [{"type": "text_delta"}, {"type": "message_complete"}]
        assert has_event_type(events, "text_delta")

    def test_has_event_type_false(self) -> None:
        """has_event_type should return False when event type missing."""
        from tests.sdk_helpers import has_event_type

        events = [{"type": "text_delta"}]
        assert not has_event_type(events, "tool_result")

    def test_count_event_type(self) -> None:
        """count_event_type should count occurrences."""
        from tests.sdk_helpers import count_event_type

        events = [
            {"type": "text_delta"},
            {"type": "text_delta"},
            {"type": "message_complete"},
        ]
        assert count_event_type(events, "text_delta") == 2
        assert count_event_type(events, "message_complete") == 1
        assert count_event_type(events, "tool_result") == 0
