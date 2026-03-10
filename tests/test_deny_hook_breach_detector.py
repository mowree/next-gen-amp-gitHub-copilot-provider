"""
Tests for create_deny_hook() and _create_breach_detector() (F-010).

Task 4: Defense-in-depth hooks for session_factory.py
"""

import pytest


class TestPrivateDenyHook:
    """Test create_deny_hook() - async deny hook factory."""

    @pytest.mark.asyncio
    async def test_private_deny_hook_returns_deny_all(self) -> None:
        """create_deny_hook() returns async callable that returns DENY_ALL."""
        from amplifier_module_provider_github_copilot.session_factory import (
            DENY_ALL,
            create_deny_hook,
        )

        hook = create_deny_hook()
        result = await hook(None, None)
        assert result == DENY_ALL

    @pytest.mark.asyncio
    async def test_private_deny_hook_never_returns_none(self) -> None:
        """create_deny_hook() never returns None - always DENY_ALL."""
        from amplifier_module_provider_github_copilot.session_factory import (
            DENY_ALL,
            create_deny_hook,
        )

        hook = create_deny_hook()
        result = await hook(None, None)
        assert result is not None
        assert result == DENY_ALL

    def test_deny_all_constant_has_expected_keys(self) -> None:
        """DENY_ALL constant has permissionDecision and permissionDecisionReason."""
        from amplifier_module_provider_github_copilot.session_factory import DENY_ALL

        assert DENY_ALL["permissionDecision"] == "deny"
        assert "Amplifier" in DENY_ALL["permissionDecisionReason"]


class TestBreachDetector:
    """Test _create_breach_detector() - postToolUse hook factory."""

    @pytest.mark.asyncio
    async def test_breach_detector_calls_on_breach_with_tool_name(self) -> None:
        """_create_breach_detector() calls on_breach with the tool name."""
        from amplifier_module_provider_github_copilot.session_factory import (  # pyright: ignore[reportPrivateUsage]
            _create_breach_detector,
        )

        breaches: list[str] = []
        detector = _create_breach_detector(breaches.append)

        input_data = {"toolName": "read_file"}
        await detector(input_data, None)

        assert breaches == ["read_file"]

    @pytest.mark.asyncio
    async def test_breach_detector_uses_unknown_for_missing_tool_name(self) -> None:
        """_create_breach_detector() uses 'unknown' when toolName missing."""
        from amplifier_module_provider_github_copilot.session_factory import (  # pyright: ignore[reportPrivateUsage]
            _create_breach_detector,
        )

        breaches: list[str] = []
        detector = _create_breach_detector(breaches.append)

        await detector({}, None)

        assert breaches == ["unknown"]

    @pytest.mark.asyncio
    async def test_breach_detector_returns_redacted_result(self) -> None:
        """_create_breach_detector() returns suppressed/redacted response."""
        from amplifier_module_provider_github_copilot.session_factory import (  # pyright: ignore[reportPrivateUsage]
            _create_breach_detector,
        )

        detector = _create_breach_detector(lambda _: None)
        result = await detector({"toolName": "evil_tool"}, None)

        assert result["suppressOutput"] is True
        assert "REDACTED" in result["modifiedResult"]
