# Contract-First Architecture for next-get-provider-github-copilot

**Wave 2, Agent 13 — Contract-First Design Expert**
**Date**: 2026-03-08

---

## Premise: Why Contracts Are the Only Truth

This provider will be maintained by AI agents with zero institutional memory. No tribal knowledge. No "ask Sarah, she knows how that works." The ONLY reliable truth is what is written down, machine-verifiable, and self-describing. Contracts are not documentation — they are the system. Everything else is derived.

A contract-first architecture inverts the usual relationship between code and specification. Instead of writing code and then documenting it, we write contracts and then generate/validate code against them. The contract is the source of truth. The implementation is a consequence.

---

## 1. Contract Inventory

### 1.1 Provider Protocol Contract (5 Methods)

The provider protocol defines the surface area that the hosting system (`next-get`) calls into. These five methods are the entire public interface.

```python
# contracts/provider_protocol.py
"""
Provider Protocol Contract v1.0

This is the AUTHORITATIVE definition of the provider interface.
All implementations MUST satisfy this protocol.
All tests MUST verify against this protocol.
"""
from typing import Protocol, AsyncIterator, runtime_checkable
from dataclasses import dataclass


@runtime_checkable
class CopilotProvider(Protocol):
    """The five methods that define a complete Copilot provider."""

    async def initialize(self, config: "ProviderConfig") -> "InitResult":
        """
        Contract:
        - MUST be called exactly once before any other method
        - MUST validate config and raise ConfigError if invalid
        - MUST return InitResult with capabilities list
        - MUST be idempotent (second call returns same result, no side effects)
        - MUST complete within 10 seconds or raise TimeoutError
        """
        ...

    async def complete(self, request: "CompletionRequest") -> "CompletionResponse":
        """
        Contract:
        - MUST raise NotInitializedError if initialize() not called
        - MUST validate request fields before calling SDK
        - MUST return CompletionResponse (never None)
        - MUST map all SDK exceptions to provider error hierarchy
        - MUST include usage metadata in response
        """
        ...

    async def stream(self, request: "CompletionRequest") -> AsyncIterator["StreamChunk"]:
        """
        Contract:
        - MUST yield StreamChunk objects (never raw strings)
        - MUST yield a final chunk with is_final=True
        - MUST handle cancellation gracefully (no leaked resources)
        - MUST emit at least one chunk or raise EmptyResponseError
        """
        ...

    async def check_health(self) -> "HealthStatus":
        """
        Contract:
        - MUST complete within 5 seconds
        - MUST NOT raise exceptions (returns HealthStatus with error info)
        - MUST check actual SDK connectivity, not cached state
        """
        ...

    async def shutdown(self) -> None:
        """
        Contract:
        - MUST release all resources (connections, file handles)
        - MUST be safe to call multiple times
        - MUST complete within 5 seconds
        - MUST NOT raise exceptions
        """
        ...
```

**Key design decision**: The protocol uses Python's `typing.Protocol` with `@runtime_checkable`. This means the contract is simultaneously:
- A type-checking contract (pyright/mypy verify at build time)
- A runtime contract (`isinstance()` checks at initialization)
- A human-readable specification (docstrings are the spec)

### 1.2 SDK API Contract (What We Depend On)

We do not control the GitHub Copilot SDK. We must document the surface area we depend on so that SDK upgrades can be assessed mechanically.

```python
# contracts/sdk_dependency.py
"""
SDK Dependency Contract v1.0

Documents the EXACT SDK surface area we use.
Any SDK method NOT listed here is NOT relied upon.
SDK upgrades are safe if all listed methods still exist with compatible signatures.
"""

SDK_DEPENDENCY_MANIFEST = {
    "package": "github-copilot-sdk",
    "min_version": "1.0.0",
    "max_version": "2.0.0",  # exclusive — major bump = review required

    "used_classes": {
        "CopilotClient": {
            "constructor": {"params": ["api_key: str", "base_url: str | None"]},
            "methods_used": {
                "create_completion": {
                    "params": ["model: str", "messages: list[Message]", "**kwargs"],
                    "returns": "CompletionResult",
                    "raises": ["AuthError", "RateLimitError", "APIError"],
                },
                "create_completion_stream": {
                    "params": ["model: str", "messages: list[Message]", "**kwargs"],
                    "returns": "AsyncIterator[StreamDelta]",
                    "raises": ["AuthError", "RateLimitError", "APIError"],
                },
            },
        },
        "Message": {
            "fields_used": ["role: str", "content: str"],
        },
        "CompletionResult": {
            "fields_used": ["choices: list[Choice]", "usage: Usage"],
        },
    },

    "used_exceptions": [
        "AuthError",
        "RateLimitError",
        "APIError",
        "ConnectionError",
    ],
}
```

**Why this matters for AI agents**: When an SDK upgrade occurs, an AI agent can diff the new SDK's public API against this manifest and determine *mechanically* whether anything we depend on changed. No institutional memory needed.

### 1.3 Event Contract (58 Events)

Events are the provider's observability surface. Every significant state transition emits an event. The contract defines the complete event catalog.

```python
# contracts/events.py
"""
Event Contract v1.0

ALL events the provider can emit. Events not in this catalog MUST NOT be emitted.
Each event has a fixed schema. Adding fields is backward-compatible; removing is not.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Any


class EventCategory(Enum):
    LIFECYCLE = "lifecycle"       # 8 events: init, shutdown, health, etc.
    REQUEST = "request"           # 12 events: request start/end/error, validation, etc.
    STREAM = "stream"             # 10 events: chunk, backpressure, cancel, etc.
    SDK = "sdk"                   # 14 events: call, response, retry, rate_limit, etc.
    AUTH = "auth"                 # 6 events: token refresh, expiry, rotation, etc.
    CONFIG = "config"             # 4 events: load, change, validation, etc.
    ERROR = "error"               # 4 events: unhandled, recovery, circuit_break, etc.
    # Total: 58 events


@dataclass(frozen=True)
class EventSchema:
    """Defines the shape of one event type."""
    name: str
    category: EventCategory
    description: str
    fields: dict[str, str]  # field_name -> type annotation
    required_fields: list[str]
    since_version: str
    deprecated: bool = False
    replacement: str | None = None


# Example entries from the catalog:
EVENT_CATALOG: dict[str, EventSchema] = {
    "lifecycle.initialized": EventSchema(
        name="lifecycle.initialized",
        category=EventCategory.LIFECYCLE,
        description="Provider completed initialization successfully",
        fields={
            "capabilities": "list[str]",
            "sdk_version": "str",
            "duration_ms": "float",
        },
        required_fields=["capabilities", "sdk_version", "duration_ms"],
        since_version="1.0.0",
    ),
    "request.started": EventSchema(
        name="request.started",
        category=EventCategory.REQUEST,
        description="A completion request has begun processing",
        fields={
            "request_id": "str",
            "model": "str",
            "message_count": "int",
            "stream": "bool",
        },
        required_fields=["request_id", "model", "stream"],
        since_version="1.0.0",
    ),
    # ... 56 more entries
}
```

The event catalog is both the documentation AND the validation schema. At runtime, event emission checks the catalog — emitting an unlisted event or missing a required field raises a `ContractViolationError` in development mode.

### 1.4 Error Contract (Exception Hierarchy)

```python
# contracts/errors.py
"""
Error Contract v1.0

Complete exception hierarchy. No other exceptions may escape the provider boundary.
All SDK exceptions MUST be caught and mapped to this hierarchy.
"""

class ProviderError(Exception):
    """Base. All provider exceptions inherit from this."""
    def __init__(self, message: str, *, code: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


# -- Configuration errors (not retryable) --
class ConfigError(ProviderError):
    """Invalid or missing configuration."""
    pass

class NotInitializedError(ProviderError):
    """Method called before initialize()."""
    pass


# -- SDK/Network errors (may be retryable) --
class SDKError(ProviderError):
    """Wraps any SDK exception."""
    pass

class AuthenticationError(SDKError):
    """Token invalid, expired, or missing. Retryable after token refresh."""
    pass

class RateLimitError(SDKError):
    """Rate limit hit. Always retryable with backoff."""
    def __init__(self, message: str, *, retry_after: float | None = None):
        super().__init__(message, code="RATE_LIMITED", retryable=True)
        self.retry_after = retry_after

class ConnectionError(SDKError):
    """Network connectivity failure. Retryable."""
    pass


# -- Response errors --
class EmptyResponseError(ProviderError):
    """SDK returned no content."""
    pass

class MalformedResponseError(ProviderError):
    """SDK response didn't match expected schema."""
    pass


# Mapping table: SDK exceptions -> Provider exceptions
SDK_ERROR_MAP: dict[str, type[ProviderError]] = {
    "AuthError": AuthenticationError,
    "RateLimitError": RateLimitError,
    "APIError": SDKError,
    "ConnectionError": ConnectionError,
}
```

**Contract rule**: No exception outside this hierarchy may cross the provider boundary. The `SDK_ERROR_MAP` is the authoritative mapping. An AI agent implementing error handling needs only this file.

### 1.5 Configuration Contract

```python
# contracts/config.py
"""
Configuration Contract v1.0

Every configuration field, its type, default, and validation rule.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConfigField:
    name: str
    type: str
    required: bool
    default: object
    description: str
    env_var: str | None  # Environment variable override
    validation: str      # Human-readable validation rule


CONFIG_SCHEMA: list[ConfigField] = [
    ConfigField(
        name="api_key",
        type="str",
        required=True,
        default=None,
        description="GitHub Copilot API key",
        env_var="COPILOT_API_KEY",
        validation="Non-empty string, starts with 'ghu_' or 'ghp_'",
    ),
    ConfigField(
        name="model",
        type="str",
        required=False,
        default="copilot-gpt-4",
        description="Model identifier for completions",
        env_var="COPILOT_MODEL",
        validation="One of SUPPORTED_MODELS list",
    ),
    ConfigField(
        name="timeout_seconds",
        type="float",
        required=False,
        default=30.0,
        description="Request timeout in seconds",
        env_var="COPILOT_TIMEOUT",
        validation="Positive number, max 120",
    ),
    ConfigField(
        name="max_retries",
        type="int",
        required=False,
        default=3,
        description="Maximum retry attempts for retryable errors",
        env_var="COPILOT_MAX_RETRIES",
        validation="Integer 0-10",
    ),
    ConfigField(
        name="base_url",
        type="str | None",
        required=False,
        default=None,
        description="Override SDK base URL (testing/enterprise)",
        env_var="COPILOT_BASE_URL",
        validation="Valid URL or None",
    ),
]
```

---

## 2. Contract Formats

### 2.1 Dual-Format: Code IS the Contract

We reject the pattern of "contracts in YAML/JSON, code generated from them." Instead, **Python code IS the contract**. This is a deliberate choice:

| Approach | Pros | Cons |
|----------|------|------|
| YAML/JSON schemas → code gen | Machine-readable, language-agnostic | Extra build step, drift risk, two sources of truth |
| Python code with dataclasses | Single source, directly executable, type-checkable | Python-specific |
| Separate docs + code | Rich documentation | Guaranteed drift |

**Decision**: Python dataclasses and Protocols ARE the contracts. They are simultaneously:

- **Machine-readable**: Type checkers (pyright) can verify implementations against Protocol definitions. Dataclass schemas can be introspected at runtime.
- **Human-readable**: Docstrings and clear naming serve as documentation. No separate doc needed.
- **Executable**: Contracts run as part of the test suite. They aren't passive documents.

### 2.2 Contract Versioning

Each contract file declares its version in the module docstring (`v1.0`, `v1.1`, etc.) following these rules:

- **Patch version** (1.0.x): Docstring or description changes only. No behavioral change.
- **Minor version** (1.x.0): Additive changes. New optional fields, new events, new optional methods. All existing consumers continue to work unchanged.
- **Major version** (x.0.0): Breaking changes. Removed fields, changed types, removed events. Requires migration.

A `CONTRACTS_CHANGELOG.md` tracks every version bump with the exact diff, rationale, and migration guide. This file is the first thing an AI agent reads when investigating a breaking change.

---

## 3. Contract Validation

### 3.1 Runtime Contract Validation (Development Mode)

In development mode, a contract validation layer wraps the provider:

```python
# validation/runtime_validator.py
class ContractEnforcingWrapper:
    """Wraps a provider and validates every call against contracts."""

    def __init__(self, provider: CopilotProvider):
        self._provider = provider
        self._initialized = False

    async def complete(self, request):
        # Pre-condition: must be initialized
        if not self._initialized:
            raise ContractViolation("complete() called before initialize()")

        # Pre-condition: request validation
        self._validate_request(request)

        # Call real implementation
        response = await self._provider.complete(request)

        # Post-condition: response must not be None
        if response is None:
            raise ContractViolation("complete() returned None")

        # Post-condition: usage metadata must be present
        if not hasattr(response, 'usage') or response.usage is None:
            raise ContractViolation("complete() response missing usage metadata")

        return response
```

This wrapper is **zero-cost in production** — it's only active when `PROVIDER_ENV=development`. In production, calls go directly to the implementation.

### 3.2 Test-Time Contract Verification

Every contract generates a test suite:

```python
# tests/contract_tests/test_provider_protocol.py
"""
Auto-verifiable tests derived from the Provider Protocol Contract.
Each docstring clause becomes a test case.
"""

class TestInitializeContract:
    async def test_must_return_init_result(self, provider):
        result = await provider.initialize(valid_config())
        assert isinstance(result, InitResult)

    async def test_must_be_idempotent(self, provider):
        result1 = await provider.initialize(valid_config())
        result2 = await provider.initialize(valid_config())
        assert result1 == result2

    async def test_must_raise_config_error_on_invalid_config(self, provider):
        with pytest.raises(ConfigError):
            await provider.initialize(invalid_config())

    async def test_must_complete_within_10_seconds(self, provider):
        with timeout(10):
            await provider.initialize(valid_config())


class TestShutdownContract:
    async def test_must_be_safe_to_call_multiple_times(self, provider):
        await provider.initialize(valid_config())
        await provider.shutdown()
        await provider.shutdown()  # Must not raise

    async def test_must_not_raise(self, provider):
        await provider.initialize(valid_config())
        # Even with corrupted state, shutdown must not raise
        provider._client = None  # Simulate corruption
        await provider.shutdown()  # Must not raise
```

**Mapping rule**: Every MUST/MUST NOT clause in a contract docstring maps to exactly one test. If a contract has 5 MUST clauses, there are 5 tests. No more, no fewer. This is auditable.

### 3.3 Build-Time Contract Checking

Pyright (or mypy) verifies structural compatibility at build time:

```python
# This fails pyright if CopilotProviderImpl doesn't match CopilotProvider Protocol
def _type_check() -> None:
    provider: CopilotProvider = CopilotProviderImpl()  # type: ignore[assignment] if broken
```

Additionally, a CI script validates contract completeness:

```python
# scripts/validate_contracts.py
def validate_event_coverage():
    """Every event in EVENT_CATALOG must have at least one test."""
    tested_events = extract_tested_events_from_test_suite()
    all_events = set(EVENT_CATALOG.keys())
    untested = all_events - tested_events
    if untested:
        fail(f"Events without tests: {untested}")

def validate_error_mapping_coverage():
    """Every SDK exception in SDK_ERROR_MAP must have a test."""
    ...

def validate_config_field_coverage():
    """Every config field must have validation test."""
    ...
```

---

## 4. Contract Evolution

### 4.1 Safe Change Rules

| Change Type | Backward Compatible? | Process |
|-------------|---------------------|---------|
| Add optional field to response | ✅ Yes | Minor version bump |
| Add new event to catalog | ✅ Yes | Minor version bump |
| Add optional config field | ✅ Yes | Minor version bump |
| Add new error subclass | ✅ Yes | Minor version bump |
| Remove a field | ❌ No | Major version bump + migration guide |
| Change field type | ❌ No | Major version bump + migration guide |
| Remove an event | ❌ No | Deprecate first, remove in next major |
| Change method signature | ❌ No | Major version bump |
| Add required field | ❌ No | Major version bump |

### 4.2 Deprecation Pattern

```python
# Step 1: Mark deprecated in contract (minor version bump)
EventSchema(
    name="sdk.call_complete",
    # ...
    deprecated=True,
    replacement="sdk.response_received",
    since_version="1.0.0",
)

# Step 2: Runtime warning in development mode
def emit_event(name: str, data: dict):
    schema = EVENT_CATALOG[name]
    if schema.deprecated:
        warnings.warn(
            f"Event '{name}' is deprecated. Use '{schema.replacement}' instead.",
            DeprecationWarning,
            stacklevel=2,
        )

# Step 3: Remove in next major version
# Delete from EVENT_CATALOG, bump major version
```

### 4.3 Contract Change Workflow

1. **Propose**: Create a contract diff showing the change
2. **Assess impact**: Run `scripts/contract_impact.py` which uses `findReferences`-style analysis to list all code touching the changed contract element
3. **Update tests first**: Modify contract tests to reflect the new contract (TDD)
4. **Update implementation**: Make the code satisfy the new contract
5. **Update changelog**: Document the change in `CONTRACTS_CHANGELOG.md`
6. **Verify**: CI confirms all contract validations pass

---

## 5. Contract-Driven Testing

### 5.1 Tests Generated from Contracts

The contract IS the test specification. A generator script produces test skeletons:

```python
# scripts/generate_contract_tests.py
def generate_tests_for_protocol():
    """Parse Protocol class docstrings, extract MUST clauses, generate test stubs."""
    for method in get_protocol_methods(CopilotProvider):
        must_clauses = extract_must_clauses(method.__doc__)
        for clause in must_clauses:
            yield TestCase(
                name=f"test_{method.__name__}_{slugify(clause)}",
                docstring=f"Verifies: {clause}",
                method_under_test=method.__name__,
            )
```

This is not a replacement for hand-written tests — it's a scaffolding and coverage verification tool. If a new MUST clause is added to a contract, the CI detects that no matching test exists and fails.

### 5.2 Contract Coverage Metrics

```
Contract Coverage Report
========================
Provider Protocol:  23/23 clauses tested (100%)
Event Catalog:      58/58 events tested  (100%)
Error Hierarchy:     9/9  exceptions tested (100%)
Config Schema:       5/5  fields tested   (100%)
SDK Dependency:      4/6  methods tested  (66%) ⚠️

Overall: 99/101 (98%) — PASS (threshold: 95%)
```

### 5.3 Property-Based Testing from Contracts

Contracts define invariants that hold for ALL valid inputs, not just specific examples:

```python
from hypothesis import given, strategies as st

@given(
    model=st.sampled_from(SUPPORTED_MODELS),
    message_count=st.integers(min_value=1, max_value=100),
)
async def test_complete_always_returns_usage(model, message_count):
    """Contract: complete() MUST include usage metadata in response."""
    request = build_request(model=model, messages=random_messages(message_count))
    response = await provider.complete(request)
    assert response.usage is not None
    assert response.usage.total_tokens > 0


@given(config_field=st.sampled_from(CONFIG_SCHEMA))
def test_config_fields_have_env_var_or_default(config_field):
    """Contract: every non-required field MUST have a default."""
    if not config_field.required:
        assert config_field.default is not None
```

Property-based tests are the highest-fidelity contract verification. They explore the input space automatically and find edge cases that example-based tests miss.

---

## 6. AI and Contracts

### 6.1 How AI Uses Contracts to Understand the System

An AI agent arriving at this codebase for the first time follows this reading order:

1. **`contracts/provider_protocol.py`** — "What does this system do?" (5 methods, clear docstrings)
2. **`contracts/errors.py`** — "What can go wrong?" (exception hierarchy + SDK mapping)
3. **`contracts/config.py`** — "How is it configured?" (every field, type, default, env var)
4. **`contracts/events.py`** — "What can I observe?" (58 events with schemas)
5. **`contracts/sdk_dependency.py`** — "What external surface do we depend on?"

After reading these 5 files, an AI agent understands the ENTIRE system boundary. It knows every input, output, error, event, and dependency. It can implement, test, debug, or refactor any part of the system without reading a single line of implementation code first.

**This is the core value proposition of contract-first design for AI maintainability.**

### 6.2 Contracts as Specification for AI Implementation

When an AI agent needs to implement a method, the contract provides:

```
Task: Implement provider.complete()

Contract says:
- Input: CompletionRequest (defined in contracts)
- Output: CompletionResponse (defined in contracts)
- Must raise NotInitializedError if not initialized
- Must validate request fields
- Must map SDK exceptions via SDK_ERROR_MAP
- Must include usage metadata
- Must emit request.started and request.completed events

SDK surface:
- Call CopilotClient.create_completion(model, messages, **kwargs)
- Returns CompletionResult with .choices and .usage
- May raise AuthError, RateLimitError, APIError, ConnectionError

Error mapping:
- AuthError → AuthenticationError
- RateLimitError → RateLimitError (with retry_after)
- APIError → SDKError
- ConnectionError → ConnectionError
```

This is a COMPLETE specification. An AI agent can implement `complete()` without asking a single clarifying question. Every decision is pre-made by the contract.

### 6.3 Contract Violations as Learning Signals

When something fails, contracts provide immediate, precise diagnosis:

```
ContractViolation: complete() returned response without usage metadata
  Contract: contracts/provider_protocol.py:45
  Clause: "MUST include usage metadata in response"
  Actual: response.usage = None
  
Fix guidance:
  The SDK's CompletionResult.usage field may be None for certain models.
  Implementation must provide a default Usage(prompt_tokens=0, ...) when SDK returns None.
```

This error message tells an AI agent:
1. WHAT contract was violated (exact file and line)
2. WHAT the contract requires (the MUST clause)
3. WHAT actually happened (the runtime value)
4. HOW to fix it (guidance derived from the contract)

No investigation needed. No "let me search the codebase." The contract violation IS the debugging session.

### 6.4 Contract-Driven Code Generation Pattern

For AI agents generating code, contracts enable a reliable pattern:

```
1. Read contract → Extract all MUST clauses
2. For each MUST clause → Generate one guard/check in implementation
3. For each error in error contract → Generate one except clause
4. For each event in event catalog → Generate one emit() call
5. Run contract tests → Verify all clauses satisfied
6. Run type checker → Verify structural compatibility
```

This is mechanical. It doesn't require creativity or judgment. It's a translation from specification to implementation, which is exactly what AI agents are good at.

---

## Summary: The Contract Stack

```
┌─────────────────────────────────────────┐
│           Build-Time Checking            │
│  pyright verifies Protocol compliance    │
│  CI verifies contract coverage           │
├─────────────────────────────────────────┤
│           Test-Time Verification         │
│  1 test per MUST clause                  │
│  Property-based tests for invariants     │
│  Contract coverage metrics               │
├─────────────────────────────────────────┤
│           Runtime Validation             │
│  ContractEnforcingWrapper (dev mode)     │
│  Event catalog validation                │
│  Error boundary enforcement              │
├─────────────────────────────────────────┤
│           Contracts (Source of Truth)     │
│  provider_protocol.py  — 5 methods       │
│  sdk_dependency.py     — SDK surface     │
│  events.py             — 58 events       │
│  errors.py             — exception tree  │
│  config.py             — all config      │
└─────────────────────────────────────────┘
```

**The principle is simple**: An AI agent reads 5 contract files and knows everything. It implements against the contracts. It tests against the contracts. It debugs using contract violations. The contracts are the system. Everything else is derived.
