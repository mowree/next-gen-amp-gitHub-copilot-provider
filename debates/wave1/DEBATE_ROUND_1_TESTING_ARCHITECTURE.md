# DEBATE ROUND 1: Testing Architecture for AI-Written Code

**Agent**: Wave 1, Agent 8 — Testing Architecture Expert
**Date**: 2026-03-08
**Scope**: `next-get-provider-github-copilot` — a provider written and maintained by AI

---

## 1. Test Pyramid for AI-Written Code

### The Standard Pyramid Doesn't Apply

When humans write code, the traditional test pyramid (many unit tests, fewer integration, fewest e2e) works because humans understand *intent* implicitly. When AI writes code, the pyramid must be inverted at certain layers because **the most dangerous failure mode is "code that runs but misunderstands the requirement."**

A human developer who writes `fetchModels()` understands what "models" means in the Copilot API context. An AI might produce syntactically correct code that fetches the wrong endpoint, parses the wrong field, or silently drops data. Unit tests alone cannot catch this.

### The AI-Code Test Diamond

```
         ╱╲
        ╱  ╲        Live Integration (smoke-level, <60s)
       ╱    ╲       — Does the real API still behave as expected?
      ╱──────╲
     ╱        ╲     SDK Assumption Tests (<100ms)
    ╱          ╲    — Do our expectations about SDK behavior hold?
   ╱────────────╲
  ╱              ╲   Behavioral Contract Tests (<10ms)
 ╱                ╲  — Does the code fulfill the documented contract?
╱──────────────────╲
╲                  ╱  Pure Function Unit Tests (<10ms)
 ╲                ╱   — Do transformations, parsing, mapping work?
  ╲──────────────╱
   ╲            ╱     Property-Based Tests (<100ms)
    ╲          ╱      — Do invariants hold across random inputs?
     ╲────────╱
      ╲      ╱       Evidence Capture Tests (all tiers)
       ╲    ╱        — Structured proof that behavior matches spec
        ╲  ╱
         ╲╱
```

The key difference: **SDK Assumption Tests and Behavioral Contract Tests** form a thick middle layer that doesn't exist in typical projects. This is the "AI trust layer" — it proves the AI understood what it was building.

### Recommended Distribution

| Tier | Percentage | Purpose |
|------|-----------|---------|
| Pure function unit tests | 30% | Validate transformations and logic |
| Property-based tests | 10% | Validate invariants hold universally |
| Behavioral contract tests | 25% | Prove the code matches the spec |
| SDK assumption tests | 20% | Validate our understanding of the SDK |
| Local integration tests | 10% | Component wiring works end-to-end |
| Live integration tests | 5% | Real API still behaves as expected |

### Property-Based Testing Applicability

Property-based testing is **exceptionally valuable** for AI-written code because AI tends to handle the "happy path" well but miss edge cases. Properties document invariants that must hold regardless of input.

```python
from hypothesis import given, strategies as st

# Property: model list normalization never loses models
@given(st.lists(st.dictionaries(
    keys=st.text(min_size=1),
    values=st.text(),
    min_size=1
)))
def test_normalize_models_preserves_count(raw_models):
    """Normalization never drops models from the list."""
    normalized = normalize_model_list(raw_models)
    assert len(normalized) == len(raw_models)

# Property: token counting is monotonically non-decreasing with input length
@given(st.text(), st.text())
def test_token_count_monotonic(text_a, text_b):
    """Longer text never produces fewer tokens."""
    if len(text_a) <= len(text_b):
        assert count_tokens(text_a) <= count_tokens(text_b) + 1  # +1 for encoding variance

# Property: serialized requests are always valid JSON
@given(st.builds(CompletionRequest,
    model=st.text(min_size=1, max_size=50),
    messages=st.lists(st.builds(Message, role=st.sampled_from(["user", "assistant", "system"]), content=st.text()), min_size=1),
    temperature=st.floats(min_value=0.0, max_value=2.0)
))
def test_request_serialization_always_valid_json(request):
    """Every possible request serializes to valid JSON."""
    import json
    serialized = request.to_api_payload()
    parsed = json.loads(json.dumps(serialized))  # roundtrip
    assert parsed["model"] == request.model
    assert len(parsed["messages"]) == len(request.messages)
```

**Key properties to test in this provider:**
- Token counts are bounded and non-negative
- Model IDs survive normalization roundtrips
- Error responses always contain structured error info
- Authentication headers are always present when token exists
- Streaming chunks reassemble to match non-streaming output

---

## 2. SDK Assumption Tests

### Why This Pattern Is Critical

The `tests/sdk_assumptions/` pattern exists because **AI-written code encodes assumptions about external APIs that can silently become wrong.** A human developer might notice an SDK update in a changelog. An AI maintaining code needs explicit tests that scream when assumptions break.

### Assumption Categories

#### Category 1: API Shape Assumptions

These test that the Copilot/GitHub API returns data in the shape we expect.

```python
# tests/sdk_assumptions/test_api_shape.py

"""
SDK Assumption: API Response Shape

These tests validate that the GitHub Copilot API returns responses
in the format our code expects. If any of these fail, our parsing
logic needs updating.

Last verified: 2026-03-08
API version: 2024-12-15
"""

import pytest

class TestCompletionResponseShape:
    """Assumptions about chat completion response structure."""

    def test_response_has_choices_array(self, completion_response):
        """ASSUMPTION: Response always contains 'choices' as a list."""
        assert "choices" in completion_response
        assert isinstance(completion_response["choices"], list)

    def test_choice_has_message_with_content(self, completion_response):
        """ASSUMPTION: Each choice has message.content as string or None."""
        for choice in completion_response["choices"]:
            assert "message" in choice
            assert "content" in choice["message"]
            assert isinstance(choice["message"]["content"], (str, type(None)))

    def test_choice_has_finish_reason(self, completion_response):
        """ASSUMPTION: Each choice has a finish_reason field."""
        for choice in completion_response["choices"]:
            assert "finish_reason" in choice
            assert choice["finish_reason"] in ("stop", "length", "content_filter", "tool_calls", None)

    def test_usage_field_structure(self, completion_response):
        """ASSUMPTION: usage contains prompt_tokens, completion_tokens, total_tokens."""
        if "usage" in completion_response:
            usage = completion_response["usage"]
            assert "prompt_tokens" in usage
            assert "completion_tokens" in usage
            assert "total_tokens" in usage
            assert all(isinstance(v, int) for v in usage.values())


class TestStreamingChunkShape:
    """Assumptions about streaming SSE chunk structure."""

    def test_chunk_has_delta_not_message(self, streaming_chunk):
        """ASSUMPTION: Streaming chunks use 'delta', not 'message'."""
        for choice in streaming_chunk.get("choices", []):
            assert "delta" in choice
            assert "message" not in choice

    def test_first_chunk_has_role(self, first_streaming_chunk):
        """ASSUMPTION: First chunk's delta contains role field."""
        delta = first_streaming_chunk["choices"][0]["delta"]
        assert "role" in delta
        assert delta["role"] == "assistant"

    def test_final_chunk_is_data_done(self, raw_sse_stream):
        """ASSUMPTION: Stream terminates with 'data: [DONE]' line."""
        lines = raw_sse_stream.strip().split("\n")
        assert lines[-1].strip() == "data: [DONE]"
```

#### Category 2: Authentication Assumptions

```python
# tests/sdk_assumptions/test_auth_assumptions.py

"""
SDK Assumption: Authentication Flow

These tests validate our understanding of how GitHub Copilot
authentication works — token format, expiry behavior, refresh flow.
"""

class TestTokenAssumptions:
    """Assumptions about Copilot token structure and lifecycle."""

    def test_token_is_jwt_format(self, copilot_token):
        """ASSUMPTION: Copilot token is a JWT with 3 dot-separated parts."""
        parts = copilot_token.split(".")
        assert len(parts) == 3, f"Expected JWT format, got {len(parts)} parts"

    def test_token_contains_exp_claim(self, decoded_token):
        """ASSUMPTION: Token payload contains 'exp' (expiration) claim."""
        assert "exp" in decoded_token
        assert isinstance(decoded_token["exp"], (int, float))

    def test_expired_token_returns_401(self, api_client, expired_token):
        """ASSUMPTION: Expired token gets HTTP 401, not 403 or other."""
        response = api_client.complete(token=expired_token, messages=[{"role": "user", "content": "test"}])
        assert response.status_code == 401

    def test_token_refresh_endpoint_exists(self, github_token):
        """ASSUMPTION: Token refresh uses the Copilot token endpoint."""
        # This verifies the endpoint URL hasn't changed
        import requests
        resp = requests.get(
            "https://api.github.com/copilot_internal/v2/token",
            headers={"Authorization": f"token {github_token}"}
        )
        assert resp.status_code in (200, 401)  # 401 = bad token, but endpoint exists
```

#### Category 3: Behavioral Assumptions

```python
# tests/sdk_assumptions/test_behavioral_assumptions.py

"""
SDK Assumption: API Behavioral Contracts

These tests validate behavioral contracts we depend on — things like
"the API is idempotent" or "rate limits use standard headers."
"""

class TestRateLimitAssumptions:
    """Assumptions about rate limiting behavior."""

    def test_rate_limit_uses_standard_headers(self, rate_limited_response):
        """ASSUMPTION: Rate limit info in X-RateLimit-* headers."""
        headers = rate_limited_response.headers
        assert "X-RateLimit-Limit" in headers or "x-ratelimit-limit" in headers
        assert "X-RateLimit-Remaining" in headers or "x-ratelimit-remaining" in headers

    def test_rate_limit_returns_429(self, rate_limited_response):
        """ASSUMPTION: Rate limiting returns HTTP 429, not 503."""
        assert rate_limited_response.status_code == 429

    def test_retry_after_header_present_on_429(self, rate_limited_response):
        """ASSUMPTION: 429 responses include Retry-After header."""
        assert "Retry-After" in rate_limited_response.headers


class TestModelListAssumptions:
    """Assumptions about model listing behavior."""

    def test_model_list_returns_array(self, model_list_response):
        """ASSUMPTION: Model list endpoint returns array of model objects."""
        data = model_list_response.json()
        assert isinstance(data.get("data", data), list)

    def test_model_object_has_id_field(self, model_list_response):
        """ASSUMPTION: Each model object has an 'id' string field."""
        models = model_list_response.json().get("data", model_list_response.json())
        for model in models:
            assert "id" in model
            assert isinstance(model["id"], str)
```

### Catching SDK Breaking Changes Early

**Strategy 1: Snapshot Testing of API Responses**

```python
# tests/sdk_assumptions/conftest.py

import json
from pathlib import Path

SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"

def save_snapshot(name: str, data: dict):
    """Save API response as a snapshot for drift detection."""
    path = SNAPSHOTS_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, sort_keys=True))

def load_snapshot(name: str) -> dict:
    """Load a previously saved snapshot."""
    path = SNAPSHOTS_DIR / f"{name}.json"
    return json.loads(path.read_text())

def compare_shape(actual: dict, snapshot: dict, path: str = "") -> list[str]:
    """Compare structure (keys and types), not values."""
    diffs = []
    for key in snapshot:
        full_path = f"{path}.{key}" if path else key
        if key not in actual:
            diffs.append(f"MISSING KEY: {full_path}")
        elif type(actual[key]) != type(snapshot[key]):
            diffs.append(f"TYPE CHANGED: {full_path}: {type(snapshot[key]).__name__} -> {type(actual[key]).__name__}")
        elif isinstance(snapshot[key], dict):
            diffs.extend(compare_shape(actual[key], snapshot[key], full_path))
    for key in actual:
        full_path = f"{path}.{key}" if path else key
        if key not in snapshot:
            diffs.append(f"NEW KEY: {full_path}")
    return diffs
```

**Strategy 2: CI Nightly Runs Against Live API**

SDK assumption tests should run in two modes:
- **Stubbed (every commit)**: Fast, validates our code against recorded responses
- **Live (nightly)**: Slow, validates recorded responses still match reality

```python
# Marker-based dual-mode execution
import pytest
import os

LIVE_MODE = os.environ.get("TEST_LIVE_API", "0") == "1"

@pytest.fixture
def completion_response(recorded_response, live_api_client):
    if LIVE_MODE:
        return live_api_client.complete(model="gpt-4o", messages=[{"role": "user", "content": "Say hello"}])
    return recorded_response("completion_basic")
```

**Strategy 3: Version Pinning with Assertion**

```python
def test_api_version_unchanged():
    """GUARD: Alert if GitHub changes the API version we target."""
    # This value must be manually updated when we intentionally upgrade
    EXPECTED_API_VERSION = "2024-12-15"
    assert get_current_api_version() == EXPECTED_API_VERSION, (
        f"API version changed from {EXPECTED_API_VERSION} to {get_current_api_version()}. "
        "Review changelog and update SDK assumption tests."
    )
```

---

## 3. Evidence-Based Testing

### Core Principle

Every test should produce **structured evidence** — not just pass/fail, but a record of what was tested, what was observed, and how it compared to expectations. This is essential for AI-maintained code because:

1. **Audit trail**: When AI modifies code, evidence shows what changed in behavior
2. **Regression detection**: Structured evidence enables automated comparison across versions
3. **Spec compliance**: Evidence maps directly to specification requirements

### Event Capture Pattern

```python
# tests/evidence/capture.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import json

@dataclass
class TestEvidence:
    """Structured evidence from a single test execution."""
    test_id: str
    test_name: str
    category: str  # "unit", "sdk_assumption", "integration", "contract"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    inputs: dict[str, Any] = field(default_factory=dict)
    expected: dict[str, Any] = field(default_factory=dict)
    actual: dict[str, Any] = field(default_factory=dict)
    assertions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    passed: bool = False

    def record_assertion(self, name: str, expected: Any, actual: Any, passed: bool):
        self.assertions.append({
            "name": name,
            "expected": repr(expected),
            "actual": repr(actual),
            "passed": passed,
        })
        if not passed:
            self.passed = False

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "category": self.category,
            "timestamp": self.timestamp,
            "inputs": self.inputs,
            "expected": self.expected,
            "actual": self.actual,
            "assertions": self.assertions,
            "metadata": self.metadata,
            "passed": self.passed,
        }


@dataclass
class EvidenceCollector:
    """Collects evidence across a test session."""
    session_id: str
    evidence: list[TestEvidence] = field(default_factory=list)

    def capture(self, test_id: str, test_name: str, category: str) -> TestEvidence:
        ev = TestEvidence(test_id=test_id, test_name=test_name, category=category)
        self.evidence.append(ev)
        return ev

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({
                "session_id": self.session_id,
                "total": len(self.evidence),
                "passed": sum(1 for e in self.evidence if e.passed),
                "failed": sum(1 for e in self.evidence if not e.passed),
                "evidence": [e.to_dict() for e in self.evidence],
            }, f, indent=2)
```

### Evidence-Producing Test Example

```python
# tests/test_model_normalization.py

import pytest
from tests.evidence.capture import EvidenceCollector, TestEvidence

@pytest.fixture(scope="session")
def evidence(tmp_path_factory):
    collector = EvidenceCollector(session_id="model-normalization")
    yield collector
    path = tmp_path_factory.getbasetemp() / "evidence_model_normalization.json"
    collector.save(str(path))

def test_normalize_model_id_strips_prefix(evidence):
    """Model IDs with vendor prefixes are normalized to bare IDs."""
    ev = evidence.capture(
        test_id="NORM-001",
        test_name="normalize_model_id_strips_prefix",
        category="unit"
    )
    ev.inputs = {"raw_id": "copilot/gpt-4o"}
    ev.expected = {"normalized_id": "gpt-4o"}

    result = normalize_model_id("copilot/gpt-4o")

    ev.actual = {"normalized_id": result}
    ev.record_assertion("id_value", "gpt-4o", result, result == "gpt-4o")
    ev.passed = result == "gpt-4o"
    assert result == "gpt-4o"
```

### Evidence Storage Structure

```
tests/
├── evidence/
│   ├── capture.py           # Evidence capture framework
│   ├── baselines/           # Known-good evidence snapshots
│   │   ├── model_normalization.json
│   │   ├── auth_flow.json
│   │   └── streaming.json
│   └── compare.py           # Baseline comparison tool
```

### Baseline Comparison

```python
# tests/evidence/compare.py

import json
from pathlib import Path

def compare_to_baseline(current_evidence_path: str, baseline_path: str) -> dict:
    """Compare current test evidence against a known-good baseline."""
    current = json.loads(Path(current_evidence_path).read_text())
    baseline = json.loads(Path(baseline_path).read_text())

    current_by_id = {e["test_id"]: e for e in current["evidence"]}
    baseline_by_id = {e["test_id"]: e for e in baseline["evidence"]}

    report = {
        "new_tests": [],
        "removed_tests": [],
        "behavior_changes": [],
        "stable": [],
    }

    for tid, bev in baseline_by_id.items():
        if tid not in current_by_id:
            report["removed_tests"].append(tid)
            continue
        cev = current_by_id[tid]
        if cev["actual"] != bev["actual"]:
            report["behavior_changes"].append({
                "test_id": tid,
                "baseline_actual": bev["actual"],
                "current_actual": cev["actual"],
            })
        else:
            report["stable"].append(tid)

    for tid in current_by_id:
        if tid not in baseline_by_id:
            report["new_tests"].append(tid)

    return report
```

---

## 4. Hexagonal Testing Pattern

### Architecture Overview

The hexagonal (ports and adapters) pattern is **the single most important architectural choice for testability** in this provider. It separates "what the code does" from "how it talks to the outside world."

```
                    ┌─────────────────────────┐
   Tests ──────────►│     PORTS (Interfaces)  │
                    │                         │
   Real Client ───►│  ┌───────────────────┐  │
                    │  │   CORE DOMAIN     │  │
                    │  │                   │  │
                    │  │  - Model listing  │  │
                    │  │  - Completion     │  │
                    │  │  - Streaming      │  │
                    │  │  - Token mgmt     │  │
                    │  └───────────────────┘  │
                    │                         │
   Stubs ──────────►│   ADAPTERS (Impls)      │
                    └─────────────────────────┘
```

### Port Definitions

```python
# src/ports.py

from abc import ABC, abstractmethod
from typing import AsyncIterator

class HttpPort(ABC):
    """Port for all HTTP communication."""

    @abstractmethod
    async def request(self, method: str, url: str, headers: dict, body: dict | None = None) -> "HttpResponse":
        ...

    @abstractmethod
    async def stream(self, method: str, url: str, headers: dict, body: dict | None = None) -> AsyncIterator[bytes]:
        ...


class TokenPort(ABC):
    """Port for token acquisition and refresh."""

    @abstractmethod
    async def get_token(self) -> str:
        ...

    @abstractmethod
    async def refresh_token(self) -> str:
        ...

    @abstractmethod
    def is_expired(self, token: str) -> bool:
        ...


class ClockPort(ABC):
    """Port for time operations (critical for token expiry testing)."""

    @abstractmethod
    def now_utc(self) -> float:
        ...


class FileSystemPort(ABC):
    """Port for config file access."""

    @abstractmethod
    def read_config(self, path: str) -> str:
        ...

    @abstractmethod
    def config_exists(self, path: str) -> bool:
        ...
```

### What Should Be Stubbed vs. Real

| Component | In Unit Tests | In Integration Tests | Rationale |
|-----------|--------------|---------------------|-----------|
| **HTTP client** | STUB always | STUB (recorded) or REAL (live) | Network calls are slow and flaky |
| **Token provider** | STUB always | STUB or REAL | Token refresh hits real API |
| **Clock** | STUB always | REAL | Must test expiry logic deterministically |
| **JSON parsing** | REAL always | REAL always | Pure function, no reason to stub |
| **SSE parser** | REAL always | REAL always | Core logic, must test real implementation |
| **Model normalization** | REAL always | REAL always | Pure function |
| **File system** | STUB always | REAL (temp dirs) | Avoid polluting real filesystem |
| **Error mapping** | REAL always | REAL always | Critical path, pure transformation |
| **Rate limiter** | REAL with stub clock | REAL with stub clock | Needs deterministic time |

**Rule of thumb**: Stub I/O boundaries. Keep domain logic real. Never stub what you're testing.

### Test Adapter Implementations

```python
# tests/adapters/stub_http.py

from src.ports import HttpPort

class StubHttpAdapter(HttpPort):
    """Deterministic HTTP adapter for testing."""

    def __init__(self):
        self.responses: list[tuple[int, dict, dict]] = []  # (status, headers, body)
        self.requests_made: list[dict] = []

    def enqueue(self, status: int, body: dict, headers: dict | None = None):
        """Queue a response to be returned on next request."""
        self.responses.append((status, headers or {}, body))

    async def request(self, method, url, headers, body=None):
        self.requests_made.append({"method": method, "url": url, "headers": headers, "body": body})
        if not self.responses:
            raise RuntimeError("StubHttpAdapter: no responses queued")
        status, resp_headers, resp_body = self.responses.pop(0)
        return StubHttpResponse(status=status, headers=resp_headers, body=resp_body)

    async def stream(self, method, url, headers, body=None):
        self.requests_made.append({"method": method, "url": url, "headers": headers, "body": body})
        if not self.responses:
            raise RuntimeError("StubHttpAdapter: no responses queued")
        _, _, body_data = self.responses.pop(0)
        for chunk in body_data.get("chunks", []):
            yield chunk.encode() if isinstance(chunk, str) else chunk


class StubClockAdapter:
    """Deterministic clock for testing time-dependent logic."""

    def __init__(self, initial_time: float = 1700000000.0):
        self._time = initial_time

    def now_utc(self) -> float:
        return self._time

    def advance(self, seconds: float):
        self._time += seconds
```

---

## 5. Test Speed Tiers

### Tier Architecture

Speed tiers are enforced via pytest markers and CI pipeline stages. The key insight: **every test must declare its tier, and tier violations fail the build.**

```python
# conftest.py

import pytest
import time

TIER_LIMITS = {
    "pure": 0.010,       # 10ms
    "stubbed": 0.100,    # 100ms
    "local": 5.0,        # 5s
    "live": 60.0,        # 60s
}

@pytest.fixture(autouse=True)
def enforce_tier_speed(request):
    """Fail tests that exceed their declared speed tier."""
    marker = None
    for tier_name in TIER_LIMITS:
        if request.node.get_closest_marker(tier_name):
            marker = tier_name
            break

    if marker is None:
        pytest.fail(f"Test {request.node.name} has no speed tier marker. Add @pytest.mark.<tier>.")

    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start

    if elapsed > TIER_LIMITS[marker]:
        pytest.fail(
            f"Test {request.node.name} exceeded {marker} tier limit: "
            f"{elapsed:.3f}s > {TIER_LIMITS[marker]}s"
        )
```

### Tier 1: Pure Functions (<10ms)

```python
@pytest.mark.pure
class TestModelIdNormalization:
    """Pure transformations on model identifiers."""

    def test_strip_vendor_prefix(self):
        assert normalize("copilot/gpt-4o") == "gpt-4o"

    def test_lowercase_normalization(self):
        assert normalize("GPT-4O") == "gpt-4o"

    def test_passthrough_already_normalized(self):
        assert normalize("gpt-4o") == "gpt-4o"


@pytest.mark.pure
class TestErrorMapping:
    """Pure mapping from HTTP status to domain errors."""

    def test_401_maps_to_auth_error(self):
        assert map_error(401, {}) == AuthenticationError("Token expired or invalid")

    def test_429_maps_to_rate_limit(self):
        assert map_error(429, {"Retry-After": "30"}) == RateLimitError(retry_after=30)

    def test_500_maps_to_server_error(self):
        assert map_error(500, {}) == ServerError("Internal server error")
```

### Tier 2: Stubbed SDK (<100ms)

```python
@pytest.mark.stubbed
class TestCompletionWithStubs:
    """Completion flow with stubbed HTTP and token providers."""

    async def test_basic_completion(self, stub_http, stub_token):
        stub_token.set_token("valid-token-123")
        stub_http.enqueue(200, {
            "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
        })

        provider = CopilotProvider(http=stub_http, token=stub_token)
        result = await provider.complete(model="gpt-4o", messages=[{"role": "user", "content": "Hi"}])

        assert result.content == "Hello!"
        assert result.usage.total_tokens == 7
        assert stub_http.requests_made[0]["headers"]["Authorization"] == "Bearer valid-token-123"

    async def test_auto_refresh_on_401(self, stub_http, stub_token, stub_clock):
        stub_token.set_token("expired-token")
        stub_http.enqueue(401, {"error": "token expired"})
        stub_token.set_refresh_token("fresh-token")
        stub_http.enqueue(200, {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}]})

        provider = CopilotProvider(http=stub_http, token=stub_token, clock=stub_clock)
        result = await provider.complete(model="gpt-4o", messages=[{"role": "user", "content": "test"}])

        assert result.content == "OK"
        assert len(stub_http.requests_made) == 2  # first attempt + retry
```

### Tier 3: Local Integration (<5s)

```python
@pytest.mark.local
class TestFullProviderWiring:
    """Tests that all components wire together correctly."""

    async def test_provider_initialization_from_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"github_token": "ghp_test123"}')

        provider = CopilotProvider.from_config(str(config_file))
        assert provider is not None
        assert provider._token_manager is not None

    async def test_streaming_reassembly(self, stub_http, stub_token):
        """Full streaming flow: chunks arrive, get parsed, reassemble."""
        chunks = [
            'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n',
            'data: [DONE]\n\n',
        ]
        stub_http.enqueue(200, {"chunks": chunks})
        stub_token.set_token("valid")

        provider = CopilotProvider(http=stub_http, token=stub_token)
        collected = []
        async for chunk in provider.stream(model="gpt-4o", messages=[{"role": "user", "content": "Hi"}]):
            collected.append(chunk)

        full_text = "".join(c.content for c in collected if c.content)
        assert full_text == "Hello world"
```

### Tier 4: Live Integration (<60s)

```python
@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("COPILOT_TOKEN"), reason="No live token available")
class TestLiveAPI:
    """Tests against the real GitHub Copilot API. Run nightly only."""

    async def test_live_completion(self, live_provider):
        result = await live_provider.complete(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Respond with exactly: LIVE_TEST_OK"}]
        )
        assert result.content is not None
        assert len(result.content) > 0

    async def test_live_model_list(self, live_provider):
        models = await live_provider.list_models()
        assert len(models) > 0
        assert any("gpt" in m.id.lower() for m in models)

    async def test_live_streaming(self, live_provider):
        chunks = []
        async for chunk in live_provider.stream(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Count from 1 to 3"}]
        ):
            chunks.append(chunk)
        assert len(chunks) > 1  # Must actually stream, not batch
```

### CI Pipeline Configuration

```yaml
# .github/workflows/test.yml (conceptual)
stages:
  - name: "Fast Tests (every commit)"
    markers: "pure or stubbed"
    timeout: 60s

  - name: "Local Integration (every PR)"
    markers: "local"
    timeout: 120s

  - name: "Live Integration (nightly)"
    markers: "live"
    timeout: 300s
    secrets: [COPILOT_TOKEN]
```

---

## 6. Cross-Platform Strategy

### The Problem

This provider runs on Windows, WSL, and Linux. Key differences that affect behavior:

1. **File paths**: Config file location differs (`%APPDATA%` vs `~/.config`)
2. **Line endings**: SSE parsing must handle `\r\n` and `\n`
3. **Environment variables**: Case sensitivity differs
4. **Process model**: Token refresh subprocess behavior differs

### Platform Behavioral Contracts

```python
# tests/platform/test_cross_platform_contracts.py

"""
Cross-Platform Behavioral Contracts

These tests define behavior that MUST be identical across platforms.
If a test here fails on any platform, it's a bug.
"""

import pytest
import sys

class TestConfigDiscovery:
    """Config file discovery must work identically on all platforms."""

    @pytest.mark.pure
    def test_config_path_resolution(self, platform_adapter, tmp_path):
        """Config resolves to a valid path on every platform."""
        path = platform_adapter.resolve_config_path()
        assert path is not None
        assert isinstance(path, str)
        assert len(path) > 0

    @pytest.mark.pure
    def test_config_path_uses_native_separators(self, platform_adapter):
        """Paths use OS-native separators."""
        path = platform_adapter.resolve_config_path()
        if sys.platform == "win32":
            assert "\\" in path or "/" in path  # Windows accepts both
        else:
            assert "\\" not in path  # Unix must not have backslashes


class TestSSEParsing:
    """SSE parsing must handle all line ending styles."""

    @pytest.mark.pure
    @pytest.mark.parametrize("line_ending", ["\n", "\r\n", "\r"])
    def test_sse_parser_handles_all_line_endings(self, line_ending):
        """SSE parser correctly splits on any line ending style."""
        raw = f"data: {{\"test\": true}}{line_ending}{line_ending}"
        events = list(parse_sse(raw.encode()))
        assert len(events) == 1
        assert events[0]["test"] is True

    @pytest.mark.pure
    def test_sse_parser_handles_mixed_line_endings(self):
        """Real-world streams may mix line endings (e.g., WSL proxy)."""
        raw = 'data: {"a": 1}\r\n\r\ndata: {"b": 2}\n\n'
        events = list(parse_sse(raw.encode()))
        assert len(events) == 2


class TestEnvironmentVariables:
    """Environment variable access must be case-insensitive on Windows, case-sensitive on Unix."""

    @pytest.mark.pure
    def test_env_lookup_respects_platform_case_rules(self, platform_adapter):
        """Token lookup from env respects platform case conventions."""
        import os
        os.environ["GITHUB_COPILOT_TOKEN"] = "test-value"
        try:
            token = platform_adapter.get_env_token()
            assert token == "test-value"
        finally:
            del os.environ["GITHUB_COPILOT_TOKEN"]
```

### Platform Abstraction Layer

```python
# src/platform.py

import sys
from src.ports import FileSystemPort

class PlatformAdapter:
    """Abstracts platform-specific behavior for testability."""

    @staticmethod
    def resolve_config_path() -> str:
        if sys.platform == "win32":
            import os
            return os.path.join(os.environ.get("APPDATA", ""), "github-copilot", "config.json")
        return os.path.expanduser("~/.config/github-copilot/config.json")

    @staticmethod
    def normalize_line_endings(data: bytes) -> bytes:
        """Normalize all line endings to \n for consistent SSE parsing."""
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
```

### CI Matrix

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
    python: ["3.11", "3.12"]
    include:
      - os: ubuntu-latest
        name: "Linux"
      - os: windows-latest
        name: "Windows"
```

---

## 7. Test Directory Structure

```
tests/
├── conftest.py                    # Shared fixtures, tier enforcement
├── evidence/
│   ├── capture.py                 # Evidence capture framework
│   ├── compare.py                 # Baseline comparison
│   └── baselines/                 # Known-good evidence snapshots
│       ├── completion.json
│       ├── streaming.json
│       └── auth_flow.json
├── adapters/
│   ├── stub_http.py               # Stubbed HTTP port
│   ├── stub_token.py              # Stubbed token port
│   ├── stub_clock.py              # Deterministic clock
│   └── recorded_responses/        # Recorded API responses
│       ├── completion_basic.json
│       ├── completion_streaming.json
│       ├── model_list.json
│       └── error_401.json
├── sdk_assumptions/
│   ├── test_api_shape.py          # API response shape validation
│   ├── test_auth_assumptions.py   # Auth flow assumptions
│   ├── test_behavioral.py         # Behavioral contract assumptions
│   └── snapshots/                 # API response shape snapshots
├── unit/
│   ├── test_model_normalization.py
│   ├── test_error_mapping.py
│   ├── test_token_parsing.py
│   ├── test_sse_parser.py
│   └── test_request_builder.py
├── property/
│   ├── test_invariants.py         # Hypothesis property-based tests
│   └── test_roundtrips.py         # Serialization roundtrip properties
├── integration/
│   ├── test_completion_flow.py    # Full completion with stubs
│   ├── test_streaming_flow.py     # Full streaming with stubs
│   └── test_auth_flow.py          # Token refresh with stubs
├── live/
│   ├── test_live_completion.py    # Real API tests
│   ├── test_live_models.py
│   └── test_live_streaming.py
└── platform/
    ├── test_cross_platform.py     # Platform behavioral contracts
    └── test_path_resolution.py    # Config path tests
```

---

## 8. Summary: Key Principles

1. **AI code needs more behavioral contract tests** than human-written code — the "did the AI understand?" layer
2. **SDK assumptions must be explicit, tested, and dated** — they are the canary for breaking changes
3. **Every test produces evidence** — structured records that enable automated regression analysis
4. **Hexagonal architecture is non-negotiable** — ports and adapters make every component independently testable
5. **Speed tiers are enforced, not suggested** — tests that exceed their tier fail the build
6. **Cross-platform contracts document behavioral expectations** — line endings, paths, and env vars are tested explicitly
7. **Property-based tests guard invariants** — AI is good at happy paths, properties catch everything else
8. **Dual-mode execution** (stubbed daily, live nightly) catches both code regressions and API drift

---

*This architecture ensures that when AI modifies provider code, every change is verified against explicit behavioral contracts, SDK assumptions are validated, and structured evidence provides an auditable trail of what was tested and what was observed.*