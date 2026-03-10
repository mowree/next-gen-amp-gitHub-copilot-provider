"""
SDK Client Wrapper with lifecycle management.

Wraps copilot.CopilotClient for Amplifier integration. This is the ONLY file
that may import from the Copilot SDK.

Contract: contracts/sdk-boundary.md
Feature: F-010
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..error_translation import load_error_config, translate_sdk_error

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "errors.yaml"


def _load_error_config_once() -> Any:
    try:
        return load_error_config(_CONFIG_PATH)
    except Exception:
        from ..error_translation import ErrorConfig

        return ErrorConfig()


@dataclass(frozen=True)
class AuthStatus:
    """Authentication status from Copilot SDK.

    Attributes:
        is_authenticated: True if authenticated, False if not, None if unknown (error during check)
        github_user: GitHub username if authenticated
        auth_type: Auth method (e.g. "oauth", "token")
        error: Error message if status check failed
    """

    is_authenticated: bool | None
    github_user: str | None
    auth_type: str | None = None
    error: str | None = None


class CopilotSessionWrapper:
    """Opaque wrapper around a Copilot SDK session.

    Domain code must not access SDK session internals directly.
    Use this wrapper to pass session handles around.
    """

    __slots__ = ("_sdk_session",)

    def __init__(self, sdk_session: Any) -> None:
        self._sdk_session = sdk_session

    @property
    def session_id(self) -> str:
        return str(self._sdk_session.session_id)  # type: ignore[no-any-return]

    def get_sdk_session(self) -> Any:
        """Return inner SDK session. Use sparingly - SDK boundary concerns."""
        return self._sdk_session


def _resolve_token() -> str | None:
    """Resolve auth token from environment (highest precedence to lowest)."""
    for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(var)
        if token:
            return token
    return None


class CopilotClientWrapper:
    """Wrapper around copilot.CopilotClient with lifecycle management.

    Supports two modes:
    - Injected: pass sdk_client directly (for testing, owned=False)
    - Auto-init: no sdk_client, wrapper creates one lazily (owned=True)

    Only the auto-initialized client is owned and stopped on close().
    """

    def __init__(self, *, sdk_client: Any = None) -> None:
        self._sdk_client: Any = sdk_client
        self._owned_client: Any = None  # Only set when we created the client ourselves
        self._error_config: Any = None

    def _get_error_config(self) -> Any:
        if self._error_config is None:
            self._error_config = _load_error_config_once()
        return self._error_config

    def _get_client(self) -> Any | None:
        """Return the active SDK client (injected or owned)."""
        return self._sdk_client or self._owned_client

    async def get_auth_status(self) -> AuthStatus:
        """Check authentication status without creating session.

        Returns:
            AuthStatus with authentication details.
            - is_authenticated=False + error if no token and no client configured
            - is_authenticated=None + error if SDK call fails
            - is_authenticated=True/False with user details on success
        """
        client = self._get_client()
        if client is None:
            token = _resolve_token()
            if not token:
                logger.debug("[CLIENT] No auth token found in environment")
                return AuthStatus(
                    is_authenticated=False,
                    github_user=None,
                    error="No auth token found. Set COPILOT_GITHUB_TOKEN or GH_TOKEN.",
                )
            # No client yet; can't check without initializing - return unknown
            logger.debug("[CLIENT] Token present but client not initialized yet")
            return AuthStatus(
                is_authenticated=None,
                github_user=None,
                error="Client not initialized. Call session() first.",
            )

        try:
            logger.debug("[CLIENT] Getting auth status from SDK...")
            sdk_auth = await client.get_auth_status()
            result = AuthStatus(
                is_authenticated=sdk_auth.isAuthenticated,
                github_user=sdk_auth.login,
                auth_type=getattr(sdk_auth, "authType", None),
                error=None,
            )
            logger.debug(
                f"[CLIENT] Auth status: authenticated={result.is_authenticated}, "
                f"user={result.github_user}"
            )
            return result
        except Exception as e:
            logger.warning(f"[CLIENT] Failed to get auth status: {e}")
            return AuthStatus(
                is_authenticated=None,
                github_user=None,
                error=str(e),
            )

    @asynccontextmanager
    async def session(
        self,
        model: str | None = None,
        *,
        system_message: str | None = None,
        streaming: bool = True,
    ) -> AsyncIterator[CopilotSessionWrapper]:
        """Create an ephemeral session with proper cleanup.

        Sessions are always destroyed on exit (success or error).

        Args:
            model: Model ID to use
            system_message: Optional system message
            streaming: Enable streaming events (default: True)

        Yields:
            CopilotSessionWrapper - opaque session handle

        Raises:
            Domain errors (from error_translation) on creation failure
        """
        client = self._get_client()
        if client is None:
            # Attempt lazy import of real SDK
            try:
                from copilot import CopilotClient  # type: ignore[import-untyped]

                token = _resolve_token()
                options: dict[str, Any] = {}
                if token:
                    options["github_token"] = token

                self._owned_client = CopilotClient(options)  # type: ignore[arg-type]
                await self._owned_client.start()  # type: ignore[union-attr]
                client = self._owned_client  # type: ignore[assignment]
                logger.info("[CLIENT] Copilot client initialized")
            except ImportError as e:
                from ..error_translation import ProviderUnavailableError

                err = ProviderUnavailableError(
                    f"Copilot SDK not installed: {e}",
                    provider="github-copilot",
                )
                err.__cause__ = e
                raise err from e
            except Exception as e:
                error_config = self._get_error_config()
                raise translate_sdk_error(e, error_config) from e

        session_config: dict[str, Any] = {}
        if model:
            session_config["model"] = model
        if system_message:
            session_config["system_message"] = {"mode": "append", "content": system_message}
        session_config["streaming"] = streaming

        sdk_session = None
        try:
            logger.debug(f"[CLIENT] Creating session with model={model!r}")
            sdk_session = await client.create_session(session_config)  # type: ignore[union-attr]
            logger.debug(  # type: ignore[union-attr]
                f"[CLIENT] Session created: {getattr(sdk_session, 'session_id', '?')}"  # type: ignore[arg-type]
            )
        except Exception as e:
            error_config = self._get_error_config()
            raise translate_sdk_error(e, error_config) from e

        try:
            yield CopilotSessionWrapper(sdk_session)
        finally:
            if sdk_session is not None:
                try:
                    await sdk_session.disconnect()  # type: ignore[union-attr]
                    logger.debug("[CLIENT] Session disconnected")
                except Exception as disconnect_err:
                    logger.warning(f"[CLIENT] Error disconnecting session: {disconnect_err}")

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models from SDK.

        Returns:
            List of model dicts with at least 'id' key.
        """
        client = self._get_client()
        if client is None:
            logger.debug("[CLIENT] No client available for list_models")
            return []

        try:
            sdk_models = await client.list_models()
            return [
                {
                    "id": getattr(m, "id", None),
                    "name": getattr(m, "name", None),
                    "family": getattr(m, "family", None),
                }
                for m in sdk_models
            ]
        except Exception as e:
            logger.warning(f"[CLIENT] Failed to list models: {e}")
            return []

    async def close(self) -> None:
        """Clean up owned client resources. Safe to call multiple times."""
        if self._owned_client is not None:
            try:
                logger.info("[CLIENT] Stopping owned Copilot client...")
                await self._owned_client.stop()
                logger.info("[CLIENT] Copilot client stopped")
            except Exception as e:
                logger.warning(f"[CLIENT] Error stopping client: {e}")
            finally:
                self._owned_client = None
