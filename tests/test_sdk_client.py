"""
Tests for SDK Client Wrapper (F-010).

Contract: contracts/sdk-boundary.md
Feature: specs/features/F-010-sdk-client-wrapper.md

Acceptance Criteria:
- AC-1: CopilotClientWrapper class exists
- AC-2: get_auth_status() returns AuthStatus
- AC-3: session() context manager destroys on exit
- AC-4: SDK import isolated to sdk_adapter/client.py
- AC-5: Proper error translation for auth failures
"""

from dataclasses import fields
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestAuthStatusDataclass:
    """AC-1 / AC-2: AuthStatus dataclass exists with correct fields."""

    def test_auth_status_class_exists(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import AuthStatus

        assert AuthStatus is not None

    def test_auth_status_has_required_fields(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import AuthStatus

        field_names = {f.name for f in fields(AuthStatus)}
        assert "is_authenticated" in field_names
        assert "github_user" in field_names
        assert "auth_type" in field_names
        assert "error" in field_names

    def test_auth_status_is_frozen(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import AuthStatus

        status = AuthStatus(is_authenticated=True, github_user="testuser")
        with pytest.raises((AttributeError, TypeError)):
            status.is_authenticated = False  # type: ignore[misc]

    def test_auth_status_defaults(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import AuthStatus

        status = AuthStatus(is_authenticated=True, github_user="user")
        assert status.auth_type is None
        assert status.error is None


class TestCopilotClientWrapperClass:
    """AC-1: CopilotClientWrapper class has required methods."""

    def test_class_exists(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert CopilotClientWrapper is not None

    def test_has_get_auth_status(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert hasattr(CopilotClientWrapper, "get_auth_status")
        assert callable(CopilotClientWrapper.get_auth_status)

    def test_has_session(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert hasattr(CopilotClientWrapper, "session")

    def test_has_list_models(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert hasattr(CopilotClientWrapper, "list_models")
        assert callable(CopilotClientWrapper.list_models)

    def test_has_close(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        assert hasattr(CopilotClientWrapper, "close")
        assert callable(CopilotClientWrapper.close)


class TestCopilotSessionWrapper:
    """CopilotSessionWrapper wraps SDK session opaquely."""

    def test_class_exists(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotSessionWrapper,
        )

        assert CopilotSessionWrapper is not None

    def test_wraps_sdk_session(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotSessionWrapper,
        )

        mock_session = MagicMock()
        mock_session.session_id = "abc-123"

        wrapper = CopilotSessionWrapper(mock_session)
        assert wrapper.session_id == "abc-123"

    def test_get_sdk_session_returns_inner(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotSessionWrapper,
        )

        mock_session = MagicMock()
        wrapper = CopilotSessionWrapper(mock_session)
        assert wrapper.get_sdk_session() is mock_session


class TestGetAuthStatus:
    """AC-2: get_auth_status() returns AuthStatus."""

    @pytest.mark.asyncio
    async def test_returns_auth_status_type(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            AuthStatus,
            CopilotClientWrapper,
        )

        mock_sdk_auth = MagicMock()
        mock_sdk_auth.isAuthenticated = True
        mock_sdk_auth.login = "testuser"
        mock_sdk_auth.authType = "token"

        mock_sdk_client = AsyncMock()
        mock_sdk_client.get_auth_status = AsyncMock(return_value=mock_sdk_auth)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)
        status = await wrapper.get_auth_status()

        assert isinstance(status, AuthStatus)

    @pytest.mark.asyncio
    async def test_authenticated_user_fields(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        mock_sdk_auth = MagicMock()
        mock_sdk_auth.isAuthenticated = True
        mock_sdk_auth.login = "octocat"
        mock_sdk_auth.authType = "oauth"

        mock_sdk_client = AsyncMock()
        mock_sdk_client.get_auth_status = AsyncMock(return_value=mock_sdk_auth)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)
        status = await wrapper.get_auth_status()

        assert status.is_authenticated is True
        assert status.github_user == "octocat"
        assert status.error is None

    @pytest.mark.asyncio
    async def test_no_token_returns_unauthenticated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Edge case: No COPILOT_AGENT_TOKEN -> is_authenticated=False."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
            monkeypatch.delenv(var, raising=False)

        wrapper = CopilotClientWrapper()  # no sdk_client, no env token
        status = await wrapper.get_auth_status()

        assert status.is_authenticated is False
        assert status.error is not None

    @pytest.mark.asyncio
    async def test_sdk_error_returns_unknown_status(self) -> None:
        """SDK error -> is_authenticated=None with error message."""
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            AuthStatus,
            CopilotClientWrapper,
        )

        mock_sdk_client = AsyncMock()
        mock_sdk_client.get_auth_status = AsyncMock(side_effect=RuntimeError("connection failed"))

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)
        status = await wrapper.get_auth_status()

        assert isinstance(status, AuthStatus)
        assert status.is_authenticated is None
        assert status.error is not None
        assert "connection failed" in status.error


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
    async def test_session_yields_copilot_session_wrapper(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import (
            CopilotClientWrapper,
            CopilotSessionWrapper,
        )

        mock_sdk_session = AsyncMock()
        mock_sdk_session.session_id = "sess-003"
        mock_sdk_session.disconnect = AsyncMock()

        mock_sdk_client = AsyncMock()
        mock_sdk_client.create_session = AsyncMock(return_value=mock_sdk_session)

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)

        async with wrapper.session(model="gpt-4") as session:
            assert isinstance(session, CopilotSessionWrapper)

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


class TestListModels:
    """list_models() returns list[dict[str, Any]]."""

    @pytest.mark.asyncio
    async def test_returns_list(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        mock_model: Any = MagicMock()
        mock_model.id = "gpt-4"
        mock_model.name = "GPT-4"

        mock_sdk_client = AsyncMock()
        mock_sdk_client.list_models = AsyncMock(return_value=[mock_model])

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)
        models = await wrapper.list_models()

        assert isinstance(models, list)
        assert len(models) == 1
        assert models[0]["id"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_empty_list(self) -> None:
        from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

        mock_sdk_client = AsyncMock()
        mock_sdk_client.list_models = AsyncMock(return_value=[])

        wrapper = CopilotClientWrapper(sdk_client=mock_sdk_client)
        models = await wrapper.list_models()

        assert models == []


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


class TestSDKIsolation:
    """AC-4: SDK imports are isolated to sdk_adapter/ only."""

    def test_no_copilot_imports_in_domain_modules(self) -> None:
        """Non-adapter Python modules must not import from 'copilot'."""
        from pathlib import Path

        src_root = Path("src/amplifier_module_provider_github_copilot")
        violations = []
        for py_file in src_root.glob("*.py"):
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

        assert violations == [], f"SDK imports found outside sdk_adapter/: {violations}"
