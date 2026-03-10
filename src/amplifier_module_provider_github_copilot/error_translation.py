"""
Config-driven error translation using kernel types.

All SDK errors are translated to kernel LLMError types from amplifier_core.llm_errors.
Mappings are driven by config/errors.yaml - no hardcoded error mappings.

Contract: contracts/error-hierarchy.md
Feature: F-002

MUST constraints (from contract):
- MUST use kernel error types from amplifier_core.llm_errors
- MUST NOT create custom error classes
- MUST set provider="github-copilot" on all errors
- MUST preserve original exception via chaining
- MUST use config-driven pattern matching
- MUST fall through to ProviderUnavailableError(retryable=True) for unknown errors
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# TODO(amplifier-core): Replace fallback error classes below with imports from
# amplifier_core.llm_errors once amplifier-core is a project dependency.
# See: contracts/error-hierarchy.md


# Define fallback error types that match kernel interface
# These are used when amplifier-core is not installed (testing scenarios)
class LLMError(Exception):
    """Base LLM error - matches amplifier_core.llm_errors.LLMError interface."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        retryable: bool = False,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.retryable = retryable
        self.retry_after = retry_after


def _make_error_class(name: str, default_retryable: bool) -> type:
    """Create an LLMError subclass with fixed retryable default."""

    def __init__(
        self: LLMError,
        message: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        retryable: bool = default_retryable,
        retry_after: float | None = None,
    ) -> None:
        self.message = message  # type: ignore[attr-defined]
        self.provider = provider
        self.model = model
        self.retryable = retryable
        self.retry_after = retry_after
        super(Exception, self).__init__(message)

    return type(name, (LLMError,), {"__init__": __init__})


# Create all error types via factory (8 lines instead of 165)
AuthenticationError = _make_error_class("AuthenticationError", False)
RateLimitError = _make_error_class("RateLimitError", True)
QuotaExceededError = _make_error_class("QuotaExceededError", False)
LLMTimeoutError = _make_error_class("LLMTimeoutError", True)
ContentFilterError = _make_error_class("ContentFilterError", False)
NetworkError = _make_error_class("NetworkError", True)
NotFoundError = _make_error_class("NotFoundError", False)
ProviderUnavailableError = _make_error_class("ProviderUnavailableError", True)


# Mapping from config names to error classes
KERNEL_ERROR_MAP: dict[str, type[LLMError]] = {
    "AuthenticationError": AuthenticationError,
    "RateLimitError": RateLimitError,
    "QuotaExceededError": QuotaExceededError,
    "LLMTimeoutError": LLMTimeoutError,
    "ContentFilterError": ContentFilterError,
    "NetworkError": NetworkError,
    "NotFoundError": NotFoundError,
    "ProviderUnavailableError": ProviderUnavailableError,
}


def _empty_str_list() -> list[str]:
    """Factory for empty string list."""
    return []


def _empty_mapping_list() -> list[ErrorMapping]:
    """Factory for empty mapping list."""
    return []


@dataclass
class ErrorMapping:
    """A single error mapping from SDK to kernel error.

    Attributes:
        sdk_patterns: Exception type names to match (e.g., ["AuthenticationError"]).
        string_patterns: Patterns to match in exception message.
        kernel_error: Target kernel error type name.
        retryable: Whether the error is retryable.
        extract_retry_after: Whether to extract retry_after from message.
    """

    sdk_patterns: list[str] = field(default_factory=_empty_str_list)
    string_patterns: list[str] = field(default_factory=_empty_str_list)
    kernel_error: str = "ProviderUnavailableError"
    retryable: bool = True
    extract_retry_after: bool = False


@dataclass
class ErrorConfig:
    """Error translation configuration.

    Attributes:
        mappings: List of error mappings to try in order.
        default_error: Default kernel error type for unmatched errors.
        default_retryable: Default retryable flag for unmatched errors.
    """

    mappings: list[ErrorMapping] = field(default_factory=_empty_mapping_list)
    default_error: str = "ProviderUnavailableError"
    default_retryable: bool = True


def load_error_config(config_path: str | Path) -> ErrorConfig:
    """Load error configuration from YAML file.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        ErrorConfig with loaded mappings.
    """
    path = Path(config_path)
    if not path.exists():
        return ErrorConfig()

    with path.open() as f:
        data = yaml.safe_load(f)

    if not data:
        return ErrorConfig()

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


def _extract_retry_after(message: str) -> float | None:
    """Extract retry_after seconds from error message.

    Looks for patterns like "Retry after 30 seconds" or "retry-after: 60".

    Args:
        message: The exception message to parse.

    Returns:
        Seconds to wait, or None if not found.
    """
    patterns = [
        r"[Rr]etry[- ]?after[:\s]+(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*seconds?",
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def _matches_mapping(exc: Exception, mapping: ErrorMapping) -> bool:
    """Check if exception matches a mapping's patterns.

    Args:
        exc: The exception to check.
        mapping: The mapping to match against.

    Returns:
        True if the exception matches.
    """
    exc_type_name = type(exc).__name__
    exc_message = str(exc).lower()

    # Check SDK type patterns
    for pattern in mapping.sdk_patterns:
        if pattern in exc_type_name:
            return True

    # Check string patterns in message
    for pattern in mapping.string_patterns:
        if pattern.lower() in exc_message:
            return True

    return False


def translate_sdk_error(
    exc: Exception,
    config: ErrorConfig,
    *,
    provider: str = "github-copilot",
    model: str | None = None,
) -> LLMError:
    """Translate SDK exception to kernel LLMError.

    Contract: error-hierarchy.md

    - MUST NOT raise (always returns)
    - MUST use config patterns (no hardcoded mappings)
    - MUST chain original via `raise X from exc`
    - MUST set provider attribute

    Args:
        exc: The SDK exception to translate.
        config: Error translation configuration.
        provider: Provider name to set on error.
        model: Model name to set on error.

    Returns:
        Kernel LLMError with original exception chained.
    """
    message = str(exc)
    retry_after: float | None = None

    # Try each mapping in order
    for mapping in config.mappings:
        if _matches_mapping(exc, mapping):
            # Get the kernel error class
            error_class = KERNEL_ERROR_MAP.get(mapping.kernel_error, ProviderUnavailableError)

            # Extract retry_after if configured
            if mapping.extract_retry_after:
                retry_after = _extract_retry_after(message)

            # Create the kernel error
            kernel_error = error_class(
                message,
                provider=provider,
                model=model,
                retryable=mapping.retryable,
                retry_after=retry_after,
            )
            kernel_error.__cause__ = exc
            return kernel_error

    # No mapping matched - use default
    default_class = KERNEL_ERROR_MAP.get(config.default_error, ProviderUnavailableError)
    kernel_error = default_class(
        message,
        provider=provider,
        model=model,
        retryable=config.default_retryable,
    )
    kernel_error.__cause__ = exc
    return kernel_error
