"""
Tests for Error Translation (F-002).

Contract: contracts/error-hierarchy.md
Feature: specs/features/F-002-error-translation.md

Acceptance Criteria:
- AC-1: Translates known SDK errors to kernel types
- AC-2: Uses config/errors.yaml for mappings
- AC-3: Unknown errors become ProviderUnavailableError
- AC-4: All errors have provider="github-copilot"
- AC-5: Original exception chained via __cause__
- AC-6: RateLimitError extracts retry_after when present
"""

from dataclasses import dataclass

import pytest


# Mock kernel error types for testing (since amplifier-core may not be installed)
# In real usage, these come from amplifier_core.llm_errors
@dataclass
class MockLLMError(Exception):
    """Mock base LLM error for testing."""

    message: str
    provider: str | None = None
    model: str | None = None
    retryable: bool = False
    retry_after: float | None = None


class MockAuthenticationError(MockLLMError):
    """Mock authentication error."""

    retryable: bool = False


class MockRateLimitError(MockLLMError):
    """Mock rate limit error."""

    retryable: bool = True


class MockLLMTimeoutError(MockLLMError):
    """Mock timeout error."""

    retryable: bool = True


class MockContentFilterError(MockLLMError):
    """Mock content filter error."""

    retryable: bool = False


class MockProviderUnavailableError(MockLLMError):
    """Mock provider unavailable error."""

    retryable: bool = True


class MockNetworkError(MockLLMError):
    """Mock network error."""

    retryable: bool = True


class MockNotFoundError(MockLLMError):
    """Mock not found error."""

    retryable: bool = False


# Test fixtures
@pytest.fixture
def error_config():
    """Load error config from YAML."""
    from amplifier_module_provider_github_copilot.error_translation import load_error_config

    return load_error_config("config/errors.yaml")


@pytest.fixture
def translate_fn():
    """Get translate function."""
    from amplifier_module_provider_github_copilot.error_translation import translate_sdk_error

    return translate_sdk_error


class TestErrorTranslationBasic:
    """Test basic error translation functionality."""

    def test_translate_sdk_error_exists(self) -> None:
        """translate_sdk_error function exists."""
        from amplifier_module_provider_github_copilot.error_translation import translate_sdk_error

        assert callable(translate_sdk_error)

    def test_load_error_config_exists(self) -> None:
        """load_error_config function exists."""
        from amplifier_module_provider_github_copilot.error_translation import load_error_config

        assert callable(load_error_config)

    def test_error_config_dataclass_exists(self) -> None:
        """ErrorConfig dataclass exists."""
        from amplifier_module_provider_github_copilot.error_translation import ErrorConfig

        assert ErrorConfig is not None

    def test_error_mapping_dataclass_exists(self) -> None:
        """ErrorMapping dataclass exists."""
        from amplifier_module_provider_github_copilot.error_translation import ErrorMapping

        assert ErrorMapping is not None


class TestErrorConfigLoading:
    """Test error config loading from YAML."""

    def test_load_config_from_yaml(self) -> None:
        """AC-2: Can load config from errors.yaml."""
        from amplifier_module_provider_github_copilot.error_translation import load_error_config

        config = load_error_config("config/errors.yaml")
        assert config is not None
        assert hasattr(config, "mappings")
        assert hasattr(config, "default_error")

    def test_config_has_default_error(self) -> None:
        """Config specifies default error type."""
        from amplifier_module_provider_github_copilot.error_translation import load_error_config

        config = load_error_config("config/errors.yaml")
        assert config.default_error == "ProviderUnavailableError"

    def test_config_has_default_retryable(self) -> None:
        """Config specifies default retryable flag."""
        from amplifier_module_provider_github_copilot.error_translation import load_error_config

        config = load_error_config("config/errors.yaml")
        assert config.default_retryable is True


class TestErrorTranslationMappings:
    """Test error translation using config mappings."""

    def test_unknown_error_becomes_provider_unavailable(self) -> None:
        """AC-3: Unknown errors become ProviderUnavailableError."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            translate_sdk_error,
        )

        config = ErrorConfig(
            mappings=[], default_error="ProviderUnavailableError", default_retryable=True
        )

        class UnknownSDKError(Exception):
            pass

        result = translate_sdk_error(UnknownSDKError("something went wrong"), config)
        assert result.__class__.__name__ == "ProviderUnavailableError"

    def test_error_has_provider_attribute(self) -> None:
        """AC-4: All errors have provider='github-copilot'."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            translate_sdk_error,
        )

        config = ErrorConfig(
            mappings=[], default_error="ProviderUnavailableError", default_retryable=True
        )

        class SomeError(Exception):
            pass

        result = translate_sdk_error(SomeError("test"), config)
        assert result.provider == "github-copilot"

    def test_original_exception_chained(self) -> None:
        """AC-5: Original exception chained via __cause__."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            translate_sdk_error,
        )

        config = ErrorConfig(
            mappings=[], default_error="ProviderUnavailableError", default_retryable=True
        )

        class OriginalError(Exception):
            pass

        original = OriginalError("original message")
        result = translate_sdk_error(original, config)
        assert result.__cause__ is original

    def test_translate_never_raises(self) -> None:
        """Contract: translate_sdk_error MUST NOT raise."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            translate_sdk_error,
        )

        config = ErrorConfig(
            mappings=[], default_error="ProviderUnavailableError", default_retryable=True
        )

        # Even with weird inputs, should not raise
        result = translate_sdk_error(Exception("test"), config)
        assert result is not None


class TestErrorMappingPatterns:
    """Test pattern matching for error translation."""

    def test_match_by_type_name(self) -> None:
        """AC-1: Match SDK error by type name."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            ErrorMapping,
            translate_sdk_error,
        )

        mapping = ErrorMapping(
            sdk_patterns=["AuthenticationError"],
            string_patterns=[],
            kernel_error="AuthenticationError",
            retryable=False,
        )
        config = ErrorConfig(
            mappings=[mapping],
            default_error="ProviderUnavailableError",
            default_retryable=True,
        )

        class AuthenticationError(Exception):
            pass

        result = translate_sdk_error(AuthenticationError("invalid token"), config)
        assert result.__class__.__name__ == "AuthenticationError"
        assert result.retryable is False

    def test_match_by_string_pattern(self) -> None:
        """AC-1: Match SDK error by string pattern in message."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            ErrorMapping,
            translate_sdk_error,
        )

        mapping = ErrorMapping(
            sdk_patterns=[],
            string_patterns=["429", "rate limit"],
            kernel_error="RateLimitError",
            retryable=True,
        )
        config = ErrorConfig(
            mappings=[mapping],
            default_error="ProviderUnavailableError",
            default_retryable=True,
        )

        class GenericError(Exception):
            pass

        result = translate_sdk_error(GenericError("HTTP 429 rate limit exceeded"), config)
        assert result.__class__.__name__ == "RateLimitError"
        assert result.retryable is True

    def test_first_match_wins(self) -> None:
        """Edge case: First matching pattern wins."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            ErrorMapping,
            translate_sdk_error,
        )

        mapping1 = ErrorMapping(
            sdk_patterns=["TestError"],
            string_patterns=[],
            kernel_error="AuthenticationError",
            retryable=False,
        )
        mapping2 = ErrorMapping(
            sdk_patterns=["TestError"],
            string_patterns=[],
            kernel_error="RateLimitError",
            retryable=True,
        )
        config = ErrorConfig(
            mappings=[mapping1, mapping2],
            default_error="ProviderUnavailableError",
            default_retryable=True,
        )

        class TestError(Exception):
            pass

        result = translate_sdk_error(TestError("test"), config)
        # First mapping should win
        assert result.__class__.__name__ == "AuthenticationError"


class TestRateLimitRetryAfter:
    """Test retry_after extraction for rate limit errors."""

    def test_extract_retry_after_from_message(self) -> None:
        """AC-6: RateLimitError extracts retry_after when present."""
        from amplifier_module_provider_github_copilot.error_translation import (
            ErrorConfig,
            ErrorMapping,
            translate_sdk_error,
        )

        mapping = ErrorMapping(
            sdk_patterns=["RateLimitError"],
            string_patterns=[],
            kernel_error="RateLimitError",
            retryable=True,
            extract_retry_after=True,
        )
        config = ErrorConfig(
            mappings=[mapping],
            default_error="ProviderUnavailableError",
            default_retryable=True,
        )

        class RateLimitError(Exception):
            pass

        # Error message contains retry_after hint
        result = translate_sdk_error(
            RateLimitError("Rate limit exceeded. Retry after 30 seconds."),
            config,
        )
        assert result.__class__.__name__ == "RateLimitError"
        # Should have extracted retry_after
        assert result.retry_after is not None
        assert result.retry_after == 30.0
