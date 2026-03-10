"""
Tests for deny hook (formerly session_factory, now in sdk_adapter/client.py).

Contract: contracts/deny-destroy.md
Feature: specs/features/F-003-session-factory.md

Acceptance Criteria:
- AC-1: Deny hook is created with correct response
- AC-2: Deny hook returns denial for all tool calls
- AC-3: DENY_ALL constant has required keys

Note: create_ephemeral_session() and destroy_session() removed in F-018 Change 3.
Session lifecycle now handled by CopilotClientWrapper.session() context manager.
"""

import pytest


class TestCreateDenyHook:
    """Test deny hook creation (now in sdk_adapter/client.py)."""

    def test_create_deny_hook_exists(self) -> None:
        """create_deny_hook function exists in client.py."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            create_deny_hook,
        )

        assert callable(create_deny_hook)

    def test_deny_hook_returns_callable(self) -> None:
        """Deny hook returns a callable."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            create_deny_hook,
        )

        hook = create_deny_hook()
        assert callable(hook)

    @pytest.mark.asyncio
    async def test_deny_hook_returns_deny_response(self) -> None:
        """Deny hook returns DENY_ALL with permissionDecision key."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            DENY_ALL,
            create_deny_hook,
        )

        hook = create_deny_hook()
        result = await hook(None, None)

        assert result is not None
        assert result == DENY_ALL
        assert result["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_deny_hook_includes_reason(self) -> None:
        """Deny hook includes Amplifier sovereignty reason."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            create_deny_hook,
        )

        hook = create_deny_hook()
        result = await hook(None, None)

        assert "permissionDecisionReason" in result
        assert "Amplifier" in result["permissionDecisionReason"]


class TestDenyAllConstant:
    """Test DENY_ALL constant (now in sdk_adapter/client.py)."""

    def test_deny_all_exists(self) -> None:
        """DENY_ALL constant exists in client.py."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import DENY_ALL

        assert DENY_ALL is not None

    def test_deny_all_has_required_keys(self) -> None:
        """DENY_ALL constant has permissionDecision and permissionDecisionReason."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import DENY_ALL

        assert DENY_ALL["permissionDecision"] == "deny"
        assert "Amplifier" in DENY_ALL["permissionDecisionReason"]
