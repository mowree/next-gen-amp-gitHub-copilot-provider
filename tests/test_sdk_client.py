"""
Tests for SDK Client Wrapper (F-010).

Contract: contracts/sdk-boundary.md
Feature: specs/features/F-010-sdk-client-wrapper.md

Acceptance Criteria:
- AC-1: CopilotClientWrapper class exists
- AC-3: session() context manager destroys on exit, yields raw session
- AC-4: SDK import isolated to sdk_adapter/client.py
- AC-5: Proper error translation for auth failures
"""

from unittest.mock import AsyncMock

import pytest


class TestCopilotClientWrapperClass:
    """AC-1: CopilotClientWrapper class has required methods."""

    def test_class_exists(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert CopilotClientWrapper is not None

    def test_has_session(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert hasattr(CopilotClientWrapper, "session")

    def test_has_close(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert hasattr(CopilotClientWrapper, "close")
        assert callable(CopilotClientWrapper.close)


class TestSessionYieldsRawSession:
    """session() yields the raw SDK session, not a wrapper."""

    @pytest.mark.asyncio
    async def test_session_yields_raw_sdk_session(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        mock_sdk_session = AsyncMock()
        mock_sdk_session.session_id = "sess-raw"
        mock_sdk_session.disconnect = AsyncMock()

        mock_sdk_client = AsyncMock()
        mock_sdk_client.create_session = AsyncMock(return_value=mock_sdk_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)

        async with wrapper.session(model="gpt-4") as session:
            assert session is mock_sdk_session


class TestSessionContextManager:
    """AC-3: session() context manager destroys session on exit."""

    @pytest.mark.asyncio
    async def test_session_destroys_on_normal_exit(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        mock_sdk_session = AsyncMock()
        mock_sdk_session.session_id = "sess-001"
        mock_sdk_session.disconnect = AsyncMock()

        mock_sdk_client = AsyncMock()
        mock_sdk_client.create_session = AsyncMock(return_value=mock_sdk_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)
        async with wrapper.session(model="gpt-4"):
            pass

        mock_sdk_session.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_destroys_on_exception(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        mock_sdk_session = AsyncMock()
        mock_sdk_session.session_id = "sess-002"
        mock_sdk_session.disconnect = AsyncMock()

        mock_sdk_client = AsyncMock()
        mock_sdk_client.create_session = AsyncMock(return_value=mock_sdk_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)

        with pytest.raises(ValueError):
            async with wrapper.session(model="gpt-4"):
                raise ValueError("user error")

        mock_sdk_session.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_creation_error_translated(self) -> None:
        """AC-5: Session creation errors translate to domain errors."""
        from amplifier_module_provider_github_copilot.error_translation import AuthenticationError
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        class FakeAuthError(Exception):
            pass

        FakeAuthError.__name__ = "AuthenticationError"

        mock_sdk_client = AsyncMock()
        mock_sdk_client.create_session = AsyncMock(side_effect=FakeAuthError("token invalid"))

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)

        with pytest.raises(AuthenticationError):
            async with wrapper.session(model="gpt-4"):
                pass  # pragma: no cover


class TestClose:
    """close() cleans up owned client resources."""

    @pytest.mark.asyncio
    async def test_close_owned_client(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        wrapper = CopilotClientWrapper()
        mock_owned = AsyncMock()
        mock_owned.stop = AsyncMock()
        wrapper._owned_client = mock_owned  # type: ignore[attr-defined]

        await wrapper.close()

        mock_owned.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_injected_client_does_not_stop(self) -> None:
        """Injected clients are not owned; close() must not stop them."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        mock_sdk_client = AsyncMock()
        mock_sdk_client.stop = AsyncMock()

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)
        await wrapper.close()

        mock_sdk_client.stop.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        wrapper = CopilotClientWrapper()
        await wrapper.close()  # no owned client - should not raise
        await wrapper.close()  # second call - still no error


class TestDenyHookInClient:
    """create_deny_hook() and DENY_ALL exported from client.py."""

    def test_create_deny_hook_exists_in_client(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import create_deny_hook

        assert callable(create_deny_hook)

    def test_deny_all_constant_exists_in_client(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import DENY_ALL

        assert DENY_ALL["permissionDecision"] == "deny"
        assert "Amplifier" in DENY_ALL["permissionDecisionReason"]

    @pytest.mark.asyncio
    async def test_deny_hook_returns_deny_all(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            DENY_ALL,
            create_deny_hook,
        )

        hook = create_deny_hook()
        result = await hook(None, None)
        assert result == DENY_ALL
        assert result["permissionDecision"] == "deny"


class TestSDKIsolation:
    """AC-4: SDK imports are isolated to sdk_adapter/ only."""

    def test_no_copilot_imports_in_domain_modules(self) -> None:
        """Non-adapter Python modules must not import from 'copilot'."""
        from pathlib import Path

        src_root = Path("amplifier_module_provider_github_copilot")
        violations = []
        files_scanned = 0
        for py_file in src_root.glob("*.py"):
            files_scanned += 1
            source = py_file.read_text()
            lines = [
                ln
                for ln in source.splitlines()
                if ("import copilot" in ln or "from copilot" in ln)
                and not ln.strip().startswith("#")
                and "TYPE_CHECKING" not in ln
            ]
            if lines:
                violations.append(py_file.name)

        assert files_scanned > 0, "No files found — check path"
        assert violations == [], f"SDK imports found outside sdk_adapter/: {violations}"
