"""
Config-driven error translation using kernel types.

All SDK errors are translated to kernel LLMError types from amplifier_core.llm_errors.
Mappings are driven by config/errors.yaml - no hardcoded error mappings.

Contract: contracts/error-hierarchy.md
Feature: F-002, F-036

MUST constraints (from contract):
- MUST use kernel error types from amplifier_core.llm_errors
- MUST NOT create custom error classes
- MUST set provider="github-copilot" on all errors
- MUST preserve original exception via chaining
- MUST use config-driven pattern matching
- MUST fall through to ProviderUnavailableError(retryable=True) for unknown errors

F-036 additions:
- Optional context extraction from error messages
- DEBUG logging for translation decisions
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

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

# F-035: New error types for actionable error messages
ContextLengthError = _make_error_class("ContextLengthError", False)
InvalidRequestError = _make_error_class("InvalidRequestError", False)
StreamError = _make_error_class("StreamError", True)  # Retryable
InvalidToolCallError = _make_error_class("InvalidToolCallError", False)
ConfigurationError = _make_error_class("ConfigurationError", False)


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
    # F-035: New error types
    "ContextLengthError": ContextLengthError,
    "InvalidRequestError": InvalidRequestError,
    "StreamError": StreamError,
    "InvalidToolCallError": InvalidToolCallError,
    "ConfigurationError": ConfigurationError,
}


def _str_list() -> list[str]:
    """Factory for empty string list (typed)."""
    return []


@dataclass
class ContextExtraction:
    """A context extraction pattern for enhanced error messages.

    F-036: Extracts structured context from error messages.

    Attributes:
        pattern: Regex pattern with a capture group.
        field: Name of the field to extract (e.g., "tool_name").
    """

    pattern: str
    field: str


def _context_list() -> list[ContextExtraction]:
    """Factory for empty ContextExtraction list (typed)."""
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
        context_extraction: Optional list of context extraction patterns (F-036).
    """

    sdk_patterns: list[str] = field(default_factory=_str_list)
    string_patterns: list[str] = field(default_factory=_str_list)
    kernel_error: str = "ProviderUnavailableError"
    retryable: bool = True
    extract_retry_after: bool = False
    context_extraction: list[ContextExtraction] = field(default_factory=_context_list)


def _mapping_list() -> list[ErrorMapping]:
    """Factory for empty ErrorMapping list (typed)."""
    return []


@dataclass
class ErrorConfig:
    """Error translation configuration.

    Attributes:
        mappings: List of error mappings to try in order.
        default_error: Default kernel error type for unmatched errors.
        default_retryable: Default retryable flag for unmatched errors.
    """

    mappings: list[ErrorMapping] = field(default_factory=_mapping_list)
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
        # F-036: Load context extraction patterns
        context_extraction: list[ContextExtraction] = []
        for ce_data in mapping_data.get("context_extraction", []):
            context_extraction.append(
                ContextExtraction(
                    pattern=ce_data.get("pattern", ""),
                    field=ce_data.get("field", ""),
                )
            )

        mappings.append(
            ErrorMapping(
                sdk_patterns=mapping_data.get("sdk_patterns", []),
                string_patterns=mapping_data.get("string_patterns", []),
                kernel_error=mapping_data.get("kernel_error", "ProviderUnavailableError"),
                retryable=mapping_data.get("retryable", True),
                extract_retry_after=mapping_data.get("extract_retry_after", False),
                context_extraction=context_extraction,
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
    # AC-3 (F-021): Only match retry-specific patterns, not generic "N seconds"
    patterns = [
        r"[Rr]etry[- ]?after[:\s]+(\d+(?:\.\d+)?)",
        # Removed overly broad r"(\d+(?:\.\d+)?)\s*seconds?" pattern
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


def _extract_context(message: str, extractions: list[ContextExtraction]) -> dict[str, str]:
    """Extract context fields from error message using regex patterns.

    F-036: Context extraction for enhanced error messages.

    Args:
        message: The error message to extract from.
        extractions: List of context extraction patterns.

    Returns:
        Dictionary of field_name -> extracted_value.
    """
    context: dict[str, str] = {}
    for extraction in extractions:
        try:
            match = re.search(extraction.pattern, message)
            if match:
                context[extraction.field] = match.group(1)
        except (re.error, IndexError):
            # Invalid regex or no capture group - silently skip
            pass
    return context


def _format_context_suffix(context: dict[str, str]) -> str:
    """Format extracted context as a message suffix.

    F-036: Appends context in [context: key=value, ...] format.

    Args:
        context: Dictionary of field_name -> value.

    Returns:
        Formatted suffix string, or empty string if no context.
    """
    if not context:
        return ""
    parts = [f"{k}={v}" for k, v in context.items()]
    return f" [context: {', '.join(parts)}]"


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

    F-036 additions:
    - Extracts context from error messages when configured
    - Logs DEBUG message with translation details

    Args:
        exc: The SDK exception to translate.
        config: Error translation configuration.
        provider: Provider name to set on error.
        model: Model name to set on error.

    Returns:
        Kernel LLMError with original exception chained.
    """
    original_message = str(exc)
    retry_after: float | None = None

    # Try each mapping in order
    for mapping in config.mappings:
        if _matches_mapping(exc, mapping):
            # Get the kernel error class
            error_class = KERNEL_ERROR_MAP.get(mapping.kernel_error, ProviderUnavailableError)

            # Extract retry_after if configured
            if mapping.extract_retry_after:
                retry_after = _extract_retry_after(original_message)

            # F-036: Extract context from message
            context = _extract_context(original_message, mapping.context_extraction)
            message = original_message + _format_context_suffix(context)

            # Create the kernel error
            kernel_error = error_class(
                message,
                provider=provider,
                model=model,
                retryable=mapping.retryable,
                retry_after=retry_after,
            )
            kernel_error.__cause__ = exc

            # F-036: Log translation with context
            logger.debug(
                "[ERROR_TRANSLATION] %s -> %s (retryable=%s, context=%s)",
                type(exc).__name__,
                kernel_error.__class__.__name__,
                kernel_error.retryable,
                context if context else "none",
            )

            return kernel_error

    # No mapping matched - use default
    default_class = KERNEL_ERROR_MAP.get(config.default_error, ProviderUnavailableError)
    kernel_error = default_class(
        original_message,
        provider=provider,
        model=model,
        retryable=config.default_retryable,
    )
    kernel_error.__cause__ = exc

    # F-036: Log default translation
    logger.debug(
        "[ERROR_TRANSLATION] %s -> %s (retryable=%s, default)",
        type(exc).__name__,
        kernel_error.__class__.__name__,
        kernel_error.retryable,
    )

    return kernel_error
