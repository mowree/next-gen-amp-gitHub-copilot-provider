 # F-035 Error Type Expansion Implementation Plan

 > **For execution:** Use `/execute-plan` mode or the subagent-driven-development recipe.

 **Goal:** Add 5 missing kernel error types and fix circuit breaker false positive to make error messages actionable.

 **Architecture:** Config-driven error translation with pattern matching. Circuit breaker pattern must come BEFORE timeout pattern
 to prevent false positive retries. New error classes use existing `_make_error_class()` factory.

 **Tech Stack:** Python 3.11+, pytest, YAML config

 ---

 ## Prerequisites

 - Baseline tests pass: `uv run python -m pytest tests/test_error_translation.py -v`
 - Contract validated: `uv run python -m pytest tests/test_contract_errors.py -v`

 ---

 ## Task 1: Create Test File Structure

 **Files:**
 - Create: `tests/test_f035_error_types.py`

 **Step 1: Write test file skeleton**

 ```python
 """
 Tests for F-035: Error Type Expansion.

 Contract: contracts/error-hierarchy.md
 Feature: F-035

 Acceptance Criteria:
 - P0: Circuit breaker errors MUST NOT match LLMTimeoutError
 - P1: Token/context errors MUST map to ContextLengthError
 - P2: Stream interruption errors MUST map to StreamError
 - P3: Tool errors MUST map to InvalidToolCallError
 - P4: Config errors MUST map to ConfigurationError
 """

 import pytest
 from amplifier_module_provider_github_copilot.error_translation import (
     ErrorConfig,
     load_error_config,
     translate_sdk_error,
 )


 @pytest.fixture
 def error_config() -> ErrorConfig:
     """Load error config from YAML."""
     return load_error_config()


 @pytest.fixture
 def translate_fn():
     """Get translate function."""
     return translate_sdk_error


 # Test classes will be added in subsequent tasks


Step 2: Verify file creates without syntax errors

Run: uv run python -c "import tests.test_f035_error_types" Expected: No output (success)

Step 3: Commit skeleton


 git add tests/test_f035_error_types.py
 git commit -m "test: add F-035 test file skeleton"


-------------------------------------------------------------------------------------------------------------------------------------


Task 2: Write Error Class Existence Tests (FAILING)

Files:

 • Modify: tests/test_f035_error_types.py

Step 1: Add class existence tests

Add after the fixtures in tests/test_f035_error_types.py:


 class TestF035ErrorClassesExist:
     """F-035: New error classes must exist in error_translation module."""

     @pytest.mark.parametrize("class_name", [
         "ContextLengthError",
         "InvalidRequestError",
         "StreamError",
         "InvalidToolCallError",
         "ConfigurationError",
     ])
     def test_error_class_exists(self, class_name: str) -> None:
         """F-035:Classes - {class_name} must be importable."""
         import amplifier_module_provider_github_copilot.error_translation as et
         assert hasattr(et, class_name), f"{class_name} not found in error_translation"


 class TestF035KernelErrorMap:
     """F-035: KERNEL_ERROR_MAP must include new types."""

     def test_kernel_error_map_has_new_types(self) -> None:
         """F-035:Map - All new error types must be in KERNEL_ERROR_MAP."""
         from amplifier_module_provider_github_copilot.error_translation import KERNEL_ERROR_MAP

         required_types = [
             "ContextLengthError",
             "InvalidRequestError",
             "StreamError",
             "InvalidToolCallError",
             "ConfigurationError",
         ]

         for error_type in required_types:
             assert error_type in KERNEL_ERROR_MAP, f"{error_type} missing from KERNEL_ERROR_MAP"


Step 2: Run tests to verify they FAIL

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035ErrorClassesExist -v Expected: FAIL with "AttributeError" or
"AssertionError" (classes don't exist yet)

Step 3: Commit failing tests


 git add tests/test_f035_error_types.py
 git commit -m "test: add F-035 error class existence tests (RED)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 3: Add Error Classes to error_translation.py

Files:

 • Modify: src/amplifier_module_provider_github_copilot/error_translation.py:83-96

Step 1: Add 5 new error classes

After line 83 (after ProviderUnavailableError = _make_error_class(...)), add:


 # F-035: New error types for actionable error messages
 ContextLengthError = _make_error_class("ContextLengthError", False)
 InvalidRequestError = _make_error_class("InvalidRequestError", False)
 StreamError = _make_error_class("StreamError", True)  # Retryable
 InvalidToolCallError = _make_error_class("InvalidToolCallError", False)
 ConfigurationError = _make_error_class("ConfigurationError", False)


Step 2: Update KERNEL_ERROR_MAP

Modify the KERNEL_ERROR_MAP dict (around line 87-96) to include new types:


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


Step 3: Run type checker

Run: uv run pyright src/amplifier_module_provider_github_copilot/error_translation.py Expected: No errors

Step 4: Run class existence tests

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035ErrorClassesExist -v Expected: PASS (all 5 classes exist)

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035KernelErrorMap -v Expected: PASS (all in map)

Step 5: Commit


 git add src/amplifier_module_provider_github_copilot/error_translation.py
 git commit -m "feat(F-035): add 5 new kernel error types"


-------------------------------------------------------------------------------------------------------------------------------------


Task 4: Write P0 Circuit Breaker Tests (FAILING)

Files:

 • Modify: tests/test_f035_error_types.py

Step 1: Add circuit breaker tests

Add to tests/test_f035_error_types.py:


 class TestF035P0CircuitBreaker:
     """P0: Circuit breaker false positive fix (CRITICAL)."""

     def test_circuit_breaker_pattern_exists(self, error_config: ErrorConfig) -> None:
         """F-035:P0:Exists - Circuit breaker pattern must exist in config."""
         circuit_patterns = [
             m for m in error_config.mappings
             if any("circuit breaker" in p.lower() for p in m.string_patterns)
         ]
         assert len(circuit_patterns) >= 1, "Must have circuit breaker pattern"
         assert circuit_patterns[0].retryable is False, "Circuit breaker must NOT be retryable"

     def test_circuit_breaker_before_timeout(self, error_config: ErrorConfig) -> None:
         """F-035:P0:Order - Circuit breaker MUST come before timeout pattern."""
         circuit_idx = None
         timeout_idx = None

         for i, m in enumerate(error_config.mappings):
             if any("circuit breaker" in p.lower() for p in m.string_patterns):
                 circuit_idx = i
             if m.kernel_error == "LLMTimeoutError":
                 timeout_idx = i

         assert circuit_idx is not None, "Circuit breaker pattern not found"
         assert timeout_idx is not None, "Timeout pattern not found"
         assert circuit_idx < timeout_idx, (
             f"Circuit breaker (idx={circuit_idx}) must come before timeout (idx={timeout_idx})"
         )

     def test_circuit_breaker_not_retryable(
         self, error_config: ErrorConfig, translate_fn
     ) -> None:
         """F-035:P0:Retryable - Circuit breaker MUST NOT be retryable."""
         exc = Exception("Circuit breaker TRIPPED: timeout=3720.0s > max=60.0s")
         result = translate_fn(exc, error_config)

         assert result.__class__.__name__ == "ProviderUnavailableError"
         assert result.retryable is False

     def test_circuit_breaker_not_timeout_error(
         self, error_config: ErrorConfig, translate_fn
     ) -> None:
         """F-035:P0:FalsePositive - Circuit breaker MUST NOT match LLMTimeoutError."""
         exc = Exception("Circuit breaker TRIPPED: timeout=3720.0s > max=60.0s")
         result = translate_fn(exc, error_config)

         assert result.__class__.__name__ != "LLMTimeoutError", (
             "Circuit breaker matched LLMTimeoutError - this causes infinite retry loops!"
         )


Step 2: Run tests to verify they FAIL

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P0CircuitBreaker -v Expected: FAIL (circuit breaker pattern
doesn't exist yet)

Step 3: Commit failing tests


 git add tests/test_f035_error_types.py
 git commit -m "test: add P0 circuit breaker tests (RED)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 5: Add Circuit Breaker Pattern to errors.yaml

Files:

 • Modify: config/errors.yaml

Step 1: Add circuit breaker pattern BEFORE timeout

In config/errors.yaml, add this as the FIRST entry in error_mappings: (before line 12):


 error_mappings:
   # P0: Circuit breaker - MUST be FIRST (before timeout pattern)
   # Prevents false positive match on "timeout" substring
   - sdk_patterns: ["CircuitBreakerError"]
     string_patterns: ["circuit breaker", "> max=", "Circuit breaker TRIPPED"]
     kernel_error: ProviderUnavailableError
     retryable: false

   # Existing patterns below...
   - sdk_patterns: ["AuthenticationError", "InvalidTokenError", "PermissionDeniedError"]


Step 2: Run P0 tests

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P0CircuitBreaker -v Expected: PASS (all 4 tests)

Step 3: Run regression tests

Run: uv run python -m pytest tests/test_error_translation.py -v Expected: PASS (no regressions)

Step 4: Commit


 git add config/errors.yaml
 git commit -m "fix(F-035): add circuit breaker pattern before timeout (P0)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 6: Write P1 ContextLengthError Tests (FAILING)

Files:

 • Modify: tests/test_f035_error_types.py

Step 1: Add context length tests


 class TestF035P1ContextLength:
     """P1: ContextLengthError mappings."""

     @pytest.mark.parametrize("message", [
         "CAPIError: 400 prompt token count of 140535 exceeds the limit of 128000",
         "CAPIError: 413 Request Entity Too Large",
         "context length exceeded",
         "token count 50000 exceeds limit",
     ])
     def test_context_length_patterns(
         self, error_config: ErrorConfig, translate_fn, message: str
     ) -> None:
         """F-035:P1 - Token/context errors MUST map to ContextLengthError."""
         result = translate_fn(Exception(message), error_config)

         assert result.__class__.__name__ == "ContextLengthError", (
             f"Expected ContextLengthError for '{message[:50]}...', got {result.__class__.__name__}"
         )
         assert result.retryable is False

     def test_400_without_token_not_context_error(
         self, error_config: ErrorConfig, translate_fn
     ) -> None:
         """F-035:P1:Negative - Generic 400 should NOT match ContextLengthError."""
         exc = Exception("HTTP 400 Bad Request: invalid JSON syntax")
         result = translate_fn(exc, error_config)

         assert result.__class__.__name__ != "ContextLengthError", (
             "Generic 400 error should not match ContextLengthError"
         )


Step 2: Run tests to verify they FAIL

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P1ContextLength -v Expected: FAIL (pattern doesn't exist yet)

Step 3: Commit


 git add tests/test_f035_error_types.py
 git commit -m "test: add P1 ContextLengthError tests (RED)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 7: Add ContextLengthError Pattern to errors.yaml

Files:

 • Modify: config/errors.yaml

Step 1: Add context length pattern

Add after the existing NotFoundError pattern:


   # P1: Context/token limit errors
   - sdk_patterns: ["ContextLengthError"]
     string_patterns: ["413", "token count", "exceeds the limit", "context length", "too many tokens"]
     kernel_error: ContextLengthError
     retryable: false


Step 2: Run P1 tests

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P1ContextLength -v Expected: PASS

Step 3: Commit


 git add config/errors.yaml
 git commit -m "feat(F-035): add ContextLengthError pattern (P1)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 8: Write P2 StreamError Tests (FAILING)

Files:

 • Modify: tests/test_f035_error_types.py

Step 1: Add stream error tests


 class TestF035P2StreamError:
     """P2: StreamError mappings."""

     @pytest.mark.parametrize("message", [
         "HTTP/2 GOAWAY: NO_ERROR (server gracefully closing connection)",
         "[Errno 32] Broken pipe",
         "Connection reset by peer",
         "stream terminated unexpectedly",
     ])
     def test_stream_error_patterns(
         self, error_config: ErrorConfig, translate_fn, message: str
     ) -> None:
         """F-035:P2 - Stream errors MUST map to StreamError."""
         result = translate_fn(Exception(message), error_config)

         assert result.__class__.__name__ == "StreamError", (
             f"Expected StreamError for '{message[:50]}...', got {result.__class__.__name__}"
         )
         assert result.retryable is True  # Streams are retryable


Step 2: Run tests to verify they FAIL

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P2StreamError -v Expected: FAIL

Step 3: Commit


 git add tests/test_f035_error_types.py
 git commit -m "test: add P2 StreamError tests (RED)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 9: Add StreamError Pattern to errors.yaml

Files:

 • Modify: config/errors.yaml

Step 1: Add stream error pattern


   # P2: Stream interruption errors
   - sdk_patterns: ["StreamError"]
     string_patterns: ["GOAWAY", "broken pipe", "connection reset", "stream terminated"]
     kernel_error: StreamError
     retryable: true


Step 2: Run P2 tests

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P2StreamError -v Expected: PASS

Step 3: Commit


 git add config/errors.yaml
 git commit -m "feat(F-035): add StreamError pattern (P2)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 10: Write P3 InvalidToolCallError Tests (FAILING)

Files:

 • Modify: tests/test_f035_error_types.py

Step 1: Add tool error tests


 class TestF035P3InvalidToolCall:
     """P3: InvalidToolCallError mappings."""

     @pytest.mark.parametrize("message", [
         'External tool "apply_patch" conflicts with a built-in tool',
         "Detected fake tool call text in response",
         "Detected 3 missing tool result(s)",
         "tool conflict detected",
     ])
     def test_tool_error_patterns(
         self, error_config: ErrorConfig, translate_fn, message: str
     ) -> None:
         """F-035:P3 - Tool errors MUST map to InvalidToolCallError."""
         result = translate_fn(Exception(message), error_config)

         assert result.__class__.__name__ == "InvalidToolCallError", (
             f"Expected InvalidToolCallError for '{message[:50]}...', got {result.__class__.__name__}"
         )
         assert result.retryable is False


Step 2: Run tests to verify they FAIL

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P3InvalidToolCall -v Expected: FAIL

Step 3: Commit


 git add tests/test_f035_error_types.py
 git commit -m "test: add P3 InvalidToolCallError tests (RED)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 11: Add InvalidToolCallError Pattern to errors.yaml

Files:

 • Modify: config/errors.yaml

Step 1: Add tool error pattern


   # P3: Tool-related errors
   - sdk_patterns: ["InvalidToolCallError"]
     string_patterns: ["tool conflict", "fake tool", "missing tool result", "conflicts with a built-in"]
     kernel_error: InvalidToolCallError
     retryable: false


Step 2: Run P3 tests

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P3InvalidToolCall -v Expected: PASS

Step 3: Commit


 git add config/errors.yaml
 git commit -m "feat(F-035): add InvalidToolCallError pattern (P3)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 12: Write P4 ConfigurationError Tests (FAILING)

Files:

 • Modify: tests/test_f035_error_types.py

Step 1: Add config error tests


 class TestF035P4ConfigurationError:
     """P4: ConfigurationError mappings."""

     @pytest.mark.parametrize("message", [
         "gpt-3.5-turbo does not support reasoning effort configuration",
         "Model configuration error: invalid parameter",
         "does not support extended thinking",
     ])
     def test_config_error_patterns(
         self, error_config: ErrorConfig, translate_fn, message: str
     ) -> None:
         """F-035:P4 - Config errors MUST map to ConfigurationError."""
         result = translate_fn(Exception(message), error_config)

         assert result.__class__.__name__ == "ConfigurationError", (
             f"Expected ConfigurationError for '{message[:50]}...', got {result.__class__.__name__}"
         )
         assert result.retryable is False


Step 2: Run tests to verify they FAIL

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P4ConfigurationError -v Expected: FAIL

Step 3: Commit


 git add tests/test_f035_error_types.py
 git commit -m "test: add P4 ConfigurationError tests (RED)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 13: Add ConfigurationError Pattern to errors.yaml

Files:

 • Modify: config/errors.yaml

Step 1: Add config error pattern


   # P4: Model/provider configuration errors
   - sdk_patterns: ["ConfigurationError"]
     string_patterns: ["does not support", "configuration error", "not configured"]
     kernel_error: ConfigurationError
     retryable: false


Step 2: Run P4 tests

Run: uv run python -m pytest tests/test_f035_error_types.py::TestF035P4ConfigurationError -v Expected: PASS

Step 3: Commit


 git add config/errors.yaml
 git commit -m "feat(F-035): add ConfigurationError pattern (P4)"


-------------------------------------------------------------------------------------------------------------------------------------


Task 14: Add Logger to error_translation.py

Files:

 • Modify: src/amplifier_module_provider_github_copilot/error_translation.py

Step 1: Add logger import

At the top of the file (after other imports, around line 24):


 import logging

 logger = logging.getLogger(__name__)


Step 2: Add debug logging to translate_sdk_error

In the translate_sdk_error function, after pattern matching (around line 265-270), add:


     # Log translation decision for debugging
     if matched_mapping:
         logger.debug(
             "[ERROR_TRANSLATION] %s -> %s (retryable=%s)",
             type(exc).__name__,
             matched_mapping.kernel_error,
             matched_mapping.retryable,
         )
     else:
         logger.info(
             "[ERROR_TRANSLATION] No pattern matched for %s: %s (using default)",
             type(exc).__name__,
             str(exc)[:200],
         )


Step 3: Run type checker

Run: uv run pyright src/amplifier_module_provider_github_copilot/error_translation.py Expected: No errors

Step 4: Run linter

Run: uv run ruff check src/amplifier_module_provider_github_copilot/error_translation.py Expected: No errors

Step 5: Commit


 git add src/amplifier_module_provider_github_copilot/error_translation.py
 git commit -m "feat(F-035): add debug logging to error translation"


-------------------------------------------------------------------------------------------------------------------------------------


Task 15: Full Regression Test

Step 1: Run all F-035 tests

Run: uv run python -m pytest tests/test_f035_error_types.py -v Expected: All PASS (should be ~15-20 tests)

Step 2: Run all error translation tests

Run: uv run python -m pytest tests/test_error_translation.py tests/test_contract_errors.py -v Expected: All PASS (no regressions)

Step 3: Run full test suite

Run: uv run python -m pytest tests/ -v --tb=short Expected: All PASS

-------------------------------------------------------------------------------------------------------------------------------------


Task 16: Update STATE.yaml

Files:

 • Modify: STATE.yaml

Step 1: Add F-035 to completed features

Add to completed_features: list:


 completed_features:
   # ... existing ...
   - F-035-error-type-expansion


Step 2: Update next_action


 next_action: "F-035 complete - error handling now provides actionable messages"


Step 3: Commit


 git add STATE.yaml
 git commit -m "docs: mark F-035 error type expansion complete"


-------------------------------------------------------------------------------------------------------------------------------------


Task 17: Final Summary Commit

Step 1: Push all commits


 git push origin main


-------------------------------------------------------------------------------------------------------------------------------------


Verification Checklist

After all tasks complete, verify:

 • [ ] Circuit breaker message → ProviderUnavailableError (retryable=false)
 • [ ] Token limit 400/413 → ContextLengthError
 • [ ] GOAWAY/broken pipe → StreamError (retryable=true)
 • [ ] Tool conflicts → InvalidToolCallError
 • [ ] Model config errors → ConfigurationError
 • [ ] All tests pass: uv run python -m pytest tests/ -v
 • [ ] No type errors: uv run pyright src/
 • [ ] No lint errors: uv run ruff check src/

