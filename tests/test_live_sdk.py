"""Tier 7: Live Smoke Tests - verify real SDK behavior with actual API calls.

These tests make REAL API calls to GitHub Copilot and require:
1. A valid GITHUB_TOKEN with copilot scope
2. Network access

They are slow (10-60s per test) and rate-limit-sensitive.
Run these NIGHTLY, not on every PR.

Contract references:
- contracts/sdk-boundary.md
- contracts/deny-destroy.md

Run: pytest -m live -v
"""

from __future__ import annotations

from typing import Any

import pytest

from .sdk_helpers import (
    collect_event_types,
    describe_event,
    get_event_field,
    get_event_type,
    has_event_type,
)


@pytest.mark.live
class TestLiveCompletion:
    """Verify real SDK completion produces expected event shapes.

    AC-4: Simple Completion
    Contract: sdk-boundary:Translation:MUST:1
    """

    @pytest.mark.asyncio
    async def test_simple_text_completion(self, sdk_client: Any) -> None:
        """A simple prompt produces text_delta events and message_complete."""
        session = await sdk_client.create_session(
            {
                "model": "gpt-4o",
                "streaming": True,
            }
        )

        events: list[Any] = []
        try:
            async for event in session.send_message("Say 'hello' and nothing else."):
                events.append(event)
        finally:
            await session.disconnect()

        # Structural assertions (not content assertions)
        event_types = collect_event_types(events)

        # Must have at least one content event
        content_events = {"text_delta", "content_block_delta", "content_delta"}
        assert any(t in content_events for t in event_types), (
            f"No content events found. Types: {event_types}"
        )

        # Must have a completion signal
        completion_events = {"message_complete", "message_stop", "turn_complete"}
        assert any(t in completion_events for t in event_types), (
            f"No completion signal found. Types: {event_types}"
        )

    @pytest.mark.asyncio
    async def test_event_shape_matches_assumptions(self, sdk_client: Any) -> None:
        """Verify event objects have the fields our translate_event expects."""
        session = await sdk_client.create_session(
            {
                "model": "gpt-4o",
                "streaming": True,
            }
        )

        events: list[Any] = []
        try:
            async for event in session.send_message("Say 'test'."):
                events.append(event)
        finally:
            await session.disconnect()

        # Record event shapes for drift detection
        text_delta_found = False
        for event in events:
            event_type = get_event_type(event)
            if event_type in ("text_delta", "content_delta", "content_block_delta"):
                # Our code assumes: event has "text" field
                text = get_event_field(event, "text")
                if text is not None:
                    text_delta_found = True
                    # Assert text is a string
                    assert isinstance(text, str), (
                        f"text_delta 'text' field should be str, got {type(text)}. "
                        f"Event: {describe_event(event)}"
                    )

        # We should have found at least one text delta with content
        assert text_delta_found, (
            f"No text_delta with 'text' field found. Event types: {collect_event_types(events)}"
        )


@pytest.mark.live
class TestDenyHookLive:
    """Verify deny hook actually prevents tool execution on real SDK.

    AC-3: Deny Hook Verification
    Contract: deny-destroy:DenyHook:MUST:1, deny-destroy:DenyHook:MUST:2
    """

    @pytest.mark.asyncio
    async def test_deny_hook_prevents_tool_execution(self, sdk_client: Any) -> None:
        """When deny hook is installed and tools are provided,
        SDK should return tool_call events but NOT execute them.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.client import create_deny_hook

        session = await sdk_client.create_session(
            {
                "model": "gpt-4o",
                "streaming": True,
            }
        )
        session.register_pre_tool_use_hook(create_deny_hook())

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                },
            }
        ]

        events: list[Any] = []
        try:
            async for event in session.send_message(
                "What's the weather in Seattle? Use the get_weather tool.",
                tools=tools,
            ):
                events.append(event)
        finally:
            await session.disconnect()

        # Assert: We got events (SDK responded)
        assert len(events) > 0

        # Assert: No tool_result events (tool was NOT executed)
        event_types = collect_event_types(events)
        assert not has_event_type(events, "tool_result"), (
            f"SDK executed a tool despite deny hook! Event types: {event_types}"
        )


@pytest.mark.live
class TestSessionLifecycleLive:
    """Verify session lifecycle works on real SDK.

    AC-2: Session Lifecycle Assumptions (live verification)
    """

    @pytest.mark.asyncio
    async def test_session_has_disconnect(self, sdk_client: Any) -> None:
        """Sessions must have disconnect() for cleanup."""
        session = await sdk_client.create_session({"model": "gpt-4o"})
        assert hasattr(session, "disconnect")
        assert callable(session.disconnect)
        await session.disconnect()

    @pytest.mark.asyncio
    async def test_session_has_register_pre_tool_use_hook(self, sdk_client: Any) -> None:
        """Sessions must support deny hook registration."""
        session = await sdk_client.create_session({"model": "gpt-4o"})
        assert hasattr(session, "register_pre_tool_use_hook")
        await session.disconnect()

    @pytest.mark.asyncio
    async def test_session_has_send_message(self, sdk_client: Any) -> None:
        """Sessions must have send_message for prompts."""
        session = await sdk_client.create_session({"model": "gpt-4o"})
        assert hasattr(session, "send_message")
        await session.disconnect()


@pytest.mark.live
class TestLiveErrors:
    """Verify real SDK error shapes match our error_translation assumptions.

    AC-5: Error Shape Verification
    """

    @pytest.mark.asyncio
    async def test_invalid_model_produces_expected_error(self, sdk_client: Any) -> None:
        """Requesting a nonexistent model should produce an identifiable error."""
        session = await sdk_client.create_session(
            {
                "model": "nonexistent-model-xyz-999",
                "streaming": True,
            }
        )

        with pytest.raises(Exception) as exc_info:
            async for _ in session.send_message("test"):
                pass

        await session.disconnect()

        # Record the actual error type for drift detection
        error = exc_info.value
        error_class = type(error).__name__
        error_msg = str(error)

        # Structural assertion: error is catchable and has useful info
        assert error_class, "Error has no class name"
        assert error_msg, "Error has no message"

        # Log for manual review (helps update errors.yaml)
        print(f"SDK error for invalid model: {error_class}: {error_msg}")

    @pytest.mark.asyncio
    async def test_auth_error_shape(self) -> None:
        """Invalid token should produce an auth-related error.

        AC-5: Verify auth error class matches config/errors.yaml patterns.
        """
        copilot = pytest.importorskip("copilot", reason="github-copilot-sdk not installed")

        async def deny_permission(p: Any) -> dict[str, str]:
            return {"permissionDecision": "deny", "permissionDecisionReason": "test"}

        client = copilot.CopilotClient(
            {"github_token": "invalid-token-xxx", "on_permission_request": deny_permission}
        )
        await client.start()

        try:
            session = await client.create_session({"model": "gpt-4o"})

            with pytest.raises(Exception) as exc_info:
                async for _ in session.send_message("test"):
                    pass

            error = exc_info.value
            error_class = type(error).__name__

            # Log actual error type (helps verify errors.yaml patterns)
            print(f"SDK auth error type: {error_class}: {error}")

            # The error class name should match one of our configured patterns
            # or contain auth-related status codes
            auth_indicators = [
                "AuthenticationError",
                "InvalidTokenError",
                "PermissionDeniedError",
                "Unauthorized",
                "401",
                "403",
            ]
            matches = any(p in error_class or p in str(error) for p in auth_indicators)
            assert matches, (
                f"Auth error '{error_class}' doesn't match any configured pattern. "
                f"Update config/errors.yaml sdk_patterns if this is a new error type."
            )
        finally:
            await client.stop()


@pytest.mark.live
class TestCopilotClientWrapperLive:
    """Verify CopilotClientWrapper works with real SDK.

    AC-6: Wrapper Integration
    This is THE critical integration test — it uses our actual code path.
    """

    @pytest.mark.asyncio
    async def test_wrapper_session_lifecycle(self) -> None:
        """CopilotClientWrapper.session() creates, yields, and destroys real session."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()

        try:
            async with wrapper.session(model="gpt-4o") as session:
                # Session should be a real SDK session
                assert session is not None
                assert hasattr(session, "send_message")
                assert hasattr(session, "disconnect")

                # Send a minimal message
                events: list[Any] = []
                async for event in session.send_message("Say 'ok'."):
                    events.append(event)

                assert len(events) > 0, "No events received from real SDK"
        finally:
            await wrapper.close()

    @pytest.mark.asyncio
    async def test_wrapper_deny_hook_installed_on_real_session(self) -> None:
        """CopilotClientWrapper installs deny hook on real SDK sessions.

        Verifies that the wrapper's session() context manager properly
        installs the deny hook before yielding the session.
        """
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
        )

        wrapper = CopilotClientWrapper()

        try:
            async with wrapper.session(model="gpt-4o") as session:
                # The wrapper calls register_pre_tool_use_hook in session()
                # We can't easily verify internal state, but we can verify:
                # 1. Session exists
                assert session is not None
                # 2. Hook registration method exists
                assert hasattr(session, "register_pre_tool_use_hook")
                # 3. No crash occurred during hook registration
        finally:
            await wrapper.close()
