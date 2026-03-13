"""
SDK Client Wrapper with lifecycle management.

Wraps copilot.CopilotClient for Amplifier integration. This is the ONLY file
that may import from the Copilot SDK.

Contract: contracts/sdk-boundary.md
Feature: F-010
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from importlib import resources
from typing import Any

import yaml

from ..error_translation import ErrorConfig, ErrorMapping, translate_sdk_error

logger = logging.getLogger(__name__)

# Deny hook constant
DENY_ALL: dict[str, str] = {
    "permissionDecision": "deny",
    "permissionDecisionReason": "Amplifier sovereignty - tools executed by kernel only",
}


def create_deny_hook() -> Callable[[Any, Any], Awaitable[dict[str, str]]]:
    """Create async deny hook for SDK pre_tool_use callback."""

    async def deny(input_data: Any, invocation: Any) -> dict[str, str]:
        return DENY_ALL

    return deny


def deny_permission_request(request: Any, invocation: dict[str, str]) -> Any:
    """Deny all permission requests at source.

    F-033: SDK v0.1.33 requires on_permission_request handler.

    The SDK asks: "May I do X?"
    Amplifier's answer: "No. Return the request to Amplifier's orchestrator."

    Tool capture happens via streaming events (ASSISTANT_MESSAGE), not hooks.
    This is the FIRST line of defense. preToolUse deny hook is the second.

    Contract: contracts/deny-destroy.md
    """
    try:
        from copilot.types import PermissionRequestResult  # type: ignore[import-untyped]

        return PermissionRequestResult(  # type: ignore[return-value]
            kind="denied-by-rules",
            message="Amplifier orchestrator controls all operations",
        )
    except ImportError:
        # SDK < 0.1.28 doesn't have PermissionRequestResult
        # Return dict fallback
        return {
            "kind": "denied-by-rules",
            "message": "Amplifier orchestrator controls all operations",
        }


def _load_error_config_once() -> ErrorConfig:
    """Load error config with fallback path resolution.

    F-022 AC-4: Fix config path fragility.
    Tries importlib.resources first, then falls back to file path.
    """
    from pathlib import Path

    from ..error_translation import load_error_config

    # Try importlib.resources first
    try:
        config_text = resources.read_text("config", "errors.yaml")
        data = yaml.safe_load(config_text)
        if data:
            mappings: list[ErrorMapping] = []
            for mapping_data in data.get("error_mappings", []):
                mappings.append(
                    ErrorMapping(
                        sdk_patterns=mapping_data.get("sdk_patterns", []),
                        string_patterns=mapping_data.get("string_patterns", []),
                        kernel_error=mapping_data.get("kernel_error", "ProviderUnavailableError"),
                        retryable=mapping_data.get("retryable", True),
                        extract_retry_after=mapping_data.get("extract_retry_after", False),
                    )
                )
            default = data.get("default", {})
            return ErrorConfig(
                mappings=mappings,
                default_error=default.get("kernel_error", "ProviderUnavailableError"),
                default_retryable=default.get("retryable", True),
            )
    except Exception as e:
        logger.debug("importlib.resources failed, trying file path: %s", e)

    # Fall back to file path (works in dev/test)
    try:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "errors.yaml"
        return load_error_config(config_path)
    except Exception as e:
        logger.warning("Failed to load error config: %s", e)
        return ErrorConfig()


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
        self._client_lock: asyncio.Lock = asyncio.Lock()  # F-019 AC-2: Race condition fix

    def _get_error_config(self) -> Any:
        if self._error_config is None:
            self._error_config = _load_error_config_once()
        return self._error_config

    def _get_client(self) -> Any | None:
        """Return the active SDK client (injected or owned)."""
        return self._sdk_client or self._owned_client

    @asynccontextmanager
    async def session(
        self,
        model: str | None = None,
        *,
        system_message: str | None = None,
        streaming: bool = True,
    ) -> AsyncIterator[Any]:
        """Create an ephemeral session with proper cleanup.

        Sessions are always destroyed on exit (success or error).

        Args:
            model: Model ID to use
            system_message: Optional system message
            streaming: Enable streaming events (default: True)

        Yields:
            Raw SDK session (opaque Any)

        Raises:
            Domain errors (from error_translation) on creation failure
        """
        client = self._get_client()
        if client is None:
            # F-019 AC-2: Protect lazy init with lock to prevent race conditions
            async with self._client_lock:
                # Double-check after acquiring lock (another task may have initialized)
                client = self._get_client()
                if client is None:
                    # Attempt lazy import of real SDK
                    try:
                        from copilot import CopilotClient  # type: ignore[import-untyped]

                        token = _resolve_token()
                        options: dict[str, Any] = {}
                        if token:
                            options["github_token"] = token

                        # F-033: SDK v0.1.33 requires on_permission_request handler
                        options["on_permission_request"] = deny_permission_request
                        logger.debug("[CLIENT] Permission handler set to deny_permission_request")

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
        # F-033: SDK v0.1.33 requires on_permission_request at session level too
        session_config["on_permission_request"] = deny_permission_request

        sdk_session = None
        try:
            logger.debug(f"[CLIENT] Creating session with model={model!r}")
            sdk_session = await client.create_session(session_config)  # type: ignore[union-attr]
            logger.debug(  # type: ignore[union-attr]
                f"[CLIENT] Session created: {getattr(sdk_session, 'session_id', '?')}"  # type: ignore[arg-type]
            )
            # F-019 AC-1: MUST register deny hook on real SDK path
            if hasattr(sdk_session, "register_pre_tool_use_hook"):
                sdk_session.register_pre_tool_use_hook(create_deny_hook())
                logger.debug("[CLIENT] Deny hook registered on session")
        except Exception as e:
            error_config = self._get_error_config()
            raise translate_sdk_error(e, error_config) from e

        try:
            yield sdk_session
        finally:
            if sdk_session is not None:
                try:
                    await sdk_session.disconnect()  # type: ignore[union-attr]
                    logger.debug("[CLIENT] Session disconnected")
                except Exception as disconnect_err:
                    logger.warning(f"[CLIENT] Error disconnecting session: {disconnect_err}")

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
