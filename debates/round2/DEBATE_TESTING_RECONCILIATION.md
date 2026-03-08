# DEBATE ROUND 2: Testing Philosophy Reconciliation

**Agent**: Zen Architect — Testing Strategy Reconciliation
**Date**: 2026-03-08
**Inputs**: Wave 1 Testing Architecture (Agent 8), Wave 2 Contract Architecture (Agent 13)
**Scope**: Unified testing strategy for `next-get-provider-github-copilot`

---

## 1. The Reconciled Shape: The Contract-Anchored Diamond

Five proposals were on the table: the AI-Code Test Diamond (thick middle layer for SDK assumptions and behavioral contracts), contract-first testing (every MUST clause becomes a test), evidence-based testing (structured proof artifacts), property-based testing (invariants via Hypothesis), and SDK assumption testing (canary tests for external API drift). These are not competing philosophies — they are complementary layers that, when unified, form something stronger than any individual proposal.

The reconciled shape is a **Contract-Anchored Diamond**. It preserves the diamond's thick middle (the "AI trust layer") from Wave 1, but anchors every test to a contract artifact from Wave 2. The key insight: *contracts define WHAT to test, the diamond defines HOW MUCH of each kind, evidence captures WHAT HAPPENED, and properties guard WHAT MUST ALWAYS HOLD.*

```
                    ╱╲
                   ╱  ╲         TIER 5: Live Smoke (nightly)
                  ╱    ╲        Real API, real tokens, real network
                 ╱──────╲
                ╱        ╲      TIER 4: SDK Assumption Tests (every PR)
               ╱          ╲     Recorded responses, shape validation, drift detection
              ╱────────────╲
             ╱              ╲   TIER 3: Contract Compliance Tests (every PR)
            ╱                ╲  One test per MUST clause, behavioral proof
           ╱──────────────────╲
          ╱                    ╲ TIER 2: Integration Tests (every commit)
         ╱                      ╲ Component wiring with stubs, full flows
        ╱────────────────────────╲
       ╱                          ╲ TIER 1: Unit + Property Tests (every commit)
      ╱                            ╲ Pure functions, invariants, transformations
     ╱──────────────────────────────╲
      ╲                            ╱
       ╲  CROSS-CUTTING: Evidence ╱  All tiers emit structured evidence
        ╲────────────────────────╱
```

The diamond is widest at Tiers 2–3. This is deliberate. In AI-maintained code, the most dangerous failure is "code that runs but violates the contract" — not missing edge cases in pure functions (caught by properties) and not API drift (caught by SDK assumptions). The thick middle catches the failure mode unique to AI: *syntactically correct code that misunderstands the requirement.*

---

## 2. Test Categories with Percentage Allocations

| Tier | Category | % of Total Tests | Anchored To | Speed Limit |
|------|----------|----------------:|-------------|-------------|
| 1a | Pure Function Unit Tests | 20% | Input/output contracts | <10ms |
| 1b | Property-Based Tests | 10% | Contract invariants (MUST/ALWAYS clauses) | <100ms |
| 2 | Integration Tests (stubbed) | 20% | Component wiring contracts | <500ms |
| 3 | Contract Compliance Tests | 25% | Provider Protocol MUST clauses | <100ms |
| 4 | SDK Assumption Tests | 15% | SDK Dependency Manifest | <200ms (stubbed), <5s (live) |
| 5 | Live Smoke Tests | 5% | API behavioral contracts | <60s |
| ∞ | Evidence capture | 100% (cross-cutting) | All contracts | Zero overhead target |
| — | Platform contract tests | 5% | Cross-platform behavioral contracts | <100ms |

### Why These Numbers

**20% pure unit + 10% property = 30% bottom layer.** Lower than the traditional pyramid's ~60% because many "unit test" concerns are better expressed as properties (invariants) or contract compliance tests (behavioral proof). We don't need 50 example-based unit tests when 3 property tests cover the entire input space.

**20% integration.** Component wiring is where AI-generated code most often breaks silently — the function works in isolation but the adapter passes the wrong field, the event emitter uses the wrong name, the error mapper catches the wrong exception class. Integration tests with stubs catch this at near-unit-test speed.

**25% contract compliance.** This is the heart of the diamond. Every MUST clause in the Provider Protocol, Error Contract, Event Contract, and Config Contract maps to exactly one test. The contract says "complete() MUST include usage metadata" → one test verifies it. This is the AI trust layer: proof that the implementation satisfies the specification.

**15% SDK assumption.** Higher than typical projects because we depend on an external API we don't control, maintained by a team that doesn't know we exist. SDK assumptions are our early-warning system. They run in dual mode (stubbed daily, live nightly) to catch both our regressions and GitHub's breaking changes.

**5% live smoke.** Expensive, slow, requires secrets — but irreplaceable. The only way to know the real API still works is to call it.

**5% platform contracts.** Line endings, file paths, environment variables. Small but critical for a provider that runs on Windows, WSL, and Linux.

---

## 3. Example Tests for Each Category

### Tier 1a: Pure Function Unit Tests

```python
@pytest.mark.pure
class TestErrorMapping:
    """Pure mapping from HTTP status codes to domain errors."""

    def test_401_maps_to_authentication_error(self):
        error = map_http_error(401, {})
        assert isinstance(error, AuthenticationError)
        assert error.retryable is False

    def test_429_maps_to_rate_limit_with_retry_after(self):
        error = map_http_error(429, {"Retry-After": "30"})
        assert isinstance(error, RateLimitError)
        assert error.retry_after == 30

    def test_unknown_status_maps_to_sdk_error(self):
        error = map_http_error(502, {})
        assert isinstance(error, SDKError)
```

### Tier 1b: Property-Based Tests

```python
@pytest.mark.pure
class TestModelNormalizationProperties:
    """Invariants that must hold for ALL valid model inputs."""

    @given(st.text(min_size=1, max_size=100))
    def test_normalization_is_idempotent(self, model_id):
        """Normalizing twice gives the same result as normalizing once."""
        once = normalize_model_id(model_id)
        twice = normalize_model_id(once)
        assert once == twice

    @given(st.lists(st.dictionaries(
        keys=st.text(min_size=1), values=st.text(), min_size=1
    )))
    def test_normalize_list_preserves_count(self, raw_models):
        """Normalization never drops or duplicates models."""
        normalized = normalize_model_list(raw_models)
        assert len(normalized) == len(raw_models)

    @given(st.builds(CompletionRequest,
        model=st.text(min_size=1, max_size=50),
        messages=st.lists(st.builds(Message,
            role=st.sampled_from(["user", "assistant", "system"]),
            content=st.text()), min_size=1),
        temperature=st.floats(min_value=0.0, max_value=2.0)
    ))
    def test_request_serialization_roundtrips(self, request):
        """Every valid request survives JSON roundtrip."""
        import json
        payload = request.to_api_payload()
        roundtripped = json.loads(json.dumps(payload))
        assert roundtripped["model"] == request.model
        assert len(roundtripped["messages"]) == len(request.messages)
```

### Tier 2: Integration Tests (Stubbed)

```python
@pytest.mark.stubbed
class TestCompletionFlow:
    """Full completion flow with stubbed HTTP and token ports."""

    async def test_complete_wires_token_into_auth_header(self, stub_http, stub_token):
        stub_token.set_token("tok_abc123")
        stub_http.enqueue(200, VALID_COMPLETION_RESPONSE)

        provider = CopilotProvider(http=stub_http, token=stub_token)
        await provider.complete(basic_request())

        assert stub_http.requests_made[0]["headers"]["Authorization"] == "Bearer tok_abc123"

    async def test_401_triggers_token_refresh_and_retry(self, stub_http, stub_token):
        stub_token.set_token("expired")
        stub_http.enqueue(401, {"error": "token expired"})
        stub_token.set_refresh_token("fresh_token")
        stub_http.enqueue(200, VALID_COMPLETION_RESPONSE)

        provider = CopilotProvider(http=stub_http, token=stub_token)
        result = await provider.complete(basic_request())

        assert result.content is not None
        assert len(stub_http.requests_made) == 2
```

### Tier 3: Contract Compliance Tests

```python
@pytest.mark.stubbed
class TestProviderProtocolCompliance:
    """One test per MUST clause in contracts/provider_protocol.py."""

    async def test_complete_must_raise_not_initialized_if_not_initialized(self, provider):
        """Contract: complete() MUST raise NotInitializedError if initialize() not called."""
        with pytest.raises(NotInitializedError):
            await provider.complete(basic_request())

    async def test_complete_must_never_return_none(self, initialized_provider, stub_http):
        """Contract: complete() MUST return CompletionResponse (never None)."""
        stub_http.enqueue(200, VALID_COMPLETION_RESPONSE)
        result = await initialized_provider.complete(basic_request())
        assert result is not None
        assert isinstance(result, CompletionResponse)

    async def test_complete_must_include_usage_metadata(self, initialized_provider, stub_http):
        """Contract: complete() MUST include usage metadata in response."""
        stub_http.enqueue(200, VALID_COMPLETION_RESPONSE)
        result = await initialized_provider.complete(basic_request())
        assert result.usage is not None
        assert result.usage.total_tokens > 0

    async def test_shutdown_must_be_idempotent(self, initialized_provider):
        """Contract: shutdown() MUST be safe to call multiple times."""
        await initialized_provider.shutdown()
        await initialized_provider.shutdown()  # Must not raise

    async def test_shutdown_must_not_raise_on_corrupted_state(self, initialized_provider):
        """Contract: shutdown() MUST NOT raise exceptions."""
        initialized_provider._client = None  # Simulate corruption
        await initialized_provider.shutdown()  # Must not raise
```

### Tier 4: SDK Assumption Tests

```python
@pytest.mark.stubbed  # Runs against recorded responses by default
class TestCompletionResponseShape:
    """ASSUMPTION: Copilot API completion responses have this structure."""

    def test_response_has_choices_array(self, completion_response):
        assert "choices" in completion_response
        assert isinstance(completion_response["choices"], list)

    def test_each_choice_has_message_with_content(self, completion_response):
        for choice in completion_response["choices"]:
            assert "message" in choice
            assert "content" in choice["message"]

    def test_usage_contains_token_counts(self, completion_response):
        if "usage" in completion_response:
            usage = completion_response["usage"]
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                assert field in usage
                assert isinstance(usage[field], int)


@pytest.mark.stubbed
class TestStreamingChunkShape:
    """ASSUMPTION: Streaming chunks use 'delta' not 'message'."""

    def test_chunk_uses_delta_field(self, streaming_chunk):
        for choice in streaming_chunk.get("choices", []):
            assert "delta" in choice
            assert "message" not in choice

    def test_stream_terminates_with_done_sentinel(self, raw_sse_stream):
        lines = raw_sse_stream.strip().split("\n")
        assert lines[-1].strip() == "data: [DONE]"
```

### Tier 5: Live Smoke Tests

```python
@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("COPILOT_TOKEN"), reason="No live token")
class TestLiveSmoke:
    """Nightly verification that the real API still behaves as expected."""

    async def test_live_completion_returns_content(self, live_provider):
        result = await live_provider.complete(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Respond with exactly: SMOKE_OK"}]
        )
        assert result.content is not None
        assert len(result.content) > 0

    async def test_live_model_list_includes_known_model(self, live_provider):
        models = await live_provider.list_models()
        assert len(models) > 0
        model_ids = [m.id.lower() for m in models]
        assert any("gpt" in mid for mid in model_ids)
```

### Cross-Cutting: Platform Contract Tests

```python
@pytest.mark.pure
class TestSSELineEndingContracts:
    """SSE parser must handle all line ending styles identically."""

    @pytest.mark.parametrize("line_ending", ["\n", "\r\n", "\r"])
    def test_parser_handles_all_endings(self, line_ending):
        raw = f'data: {{"test": true}}{line_ending}{line_ending}'
        events = list(parse_sse(raw.encode()))
        assert len(events) == 1
        assert events[0]["test"] is True
```

---

## 4. What Makes a Test "AI-Friendly"

A test is AI-friendly when an AI agent can understand it, maintain it, and trust its results without institutional knowledge. Five properties define AI-friendly tests:

### 4.1 Contract-Anchored

Every test traces to a contract clause. The test docstring cites the exact contract and MUST clause it verifies. An AI agent reading the test knows immediately *why* it exists and *what specification* it enforces.

```python
# AI-UNFRIENDLY: Why does this test exist? What requirement does it check?
def test_complete_returns_usage():
    result = await provider.complete(request)
    assert result.usage is not None

# AI-FRIENDLY: Clear lineage to contract
def test_complete_must_include_usage_metadata():
    """Contract: provider_protocol.py:55 — MUST include usage metadata in response."""
    result = await provider.complete(request)
    assert result.usage is not None
```

### 4.2 Evidence-Producing

Tests emit structured evidence — not just pass/fail but what was tested, what was observed, and how it compared to expectations. An AI agent reviewing test results gets machine-parseable data, not log scraping.

```python
# Evidence is captured automatically via the EvidenceCollector fixture
# Output: {"test_id": "PROTO-005", "inputs": {...}, "expected": {...}, "actual": {...}, "passed": true}
```

### 4.3 Self-Diagnosing

When a test fails, the failure message tells the AI agent exactly what contract was violated, what was expected, what was observed, and where to look for the fix. No investigation needed.

```python
# AI-UNFRIENDLY: "AssertionError: False is not True"
assert result.usage is not None

# AI-FRIENDLY: Full diagnostic context
assert result.usage is not None, (
    f"Contract violation: complete() MUST include usage metadata.\n"
    f"Contract: contracts/provider_protocol.py:55\n"
    f"Response had {len(result.choices)} choices but usage=None.\n"
    f"Fix: Ensure SDK response.usage is mapped, provide default if None."
)
```

### 4.4 Deterministic and Isolated

Tests use stubbed I/O ports (hexagonal architecture), deterministic clocks, and no shared mutable state. An AI agent can run any test in any order and get the same result. No "works on my machine" or "fails when run after test_X."

### 4.5 Speed-Tier Declared

Every test declares its speed tier via a pytest marker. An AI agent knows immediately whether a test is safe to run in a tight loop during development (`@pytest.mark.pure`, <10ms) or requires special setup (`@pytest.mark.live`, <60s, needs secrets).

---

## 5. Speed Tiers and Enforcement

### Tier Definitions

| Tier | Marker | Time Limit | Network | Secrets | When Run |
|------|--------|-----------|---------|---------|----------|
| Pure | `@pytest.mark.pure` | 10ms | No | No | Every commit |
| Stubbed | `@pytest.mark.stubbed` | 500ms | No (stubs) | No | Every commit |
| Local | `@pytest.mark.local` | 5s | Localhost only | No | Every PR |
| Live | `@pytest.mark.live` | 60s | Yes | Yes | Nightly |

### Enforcement Mechanism

Speed tiers are enforced at runtime, not by convention. A test that exceeds its declared tier **fails the build**.

```python
# conftest.py — Tier enforcement is automatic and mandatory

TIER_LIMITS = {
    "pure": 0.010,      # 10ms
    "stubbed": 0.500,   # 500ms
    "local": 5.0,       # 5s
    "live": 60.0,       # 60s
}

@pytest.fixture(autouse=True)
def enforce_tier_speed(request):
    """Every test MUST declare a speed tier. Exceeding the tier fails the test."""
    tier = None
    for tier_name in TIER_LIMITS:
        if request.node.get_closest_marker(tier_name):
            tier = tier_name
            break

    if tier is None:
        pytest.fail(
            f"Test {request.node.name} has no speed tier marker. "
            "Add @pytest.mark.pure, @pytest.mark.stubbed, @pytest.mark.local, or @pytest.mark.live."
        )

    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start

    if elapsed > TIER_LIMITS[tier]:
        pytest.fail(
            f"SPEED VIOLATION: {request.node.name} [{tier}] took {elapsed:.3f}s "
            f"(limit: {TIER_LIMITS[tier]}s). Move to a slower tier or optimize."
        )
```

### No Unmarked Tests

A test without a tier marker is a build failure. This prevents "I'll add the marker later" drift. The autouse fixture enforces this at the conftest level.

---

## 6. CI Integration Strategy

### Pipeline Stages

```yaml
# .github/workflows/test.yml

name: Test Pipeline
on: [push, pull_request]

jobs:
  # ──────────────────────────────────────────────
  # STAGE 1: Fast feedback (every commit, <90s)
  # ──────────────────────────────────────────────
  fast-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"

      # Type checking — contract structural compliance
      - name: Type Check (pyright)
        run: pyright src/ contracts/

      # Pure + stubbed tests — the fast diamond layers
      - name: Unit + Property + Contract Tests
        run: pytest -m "pure or stubbed" --timeout=90 --evidence-dir=evidence/

      # Contract coverage — every MUST clause has a test
      - name: Contract Coverage Check
        run: python scripts/validate_contracts.py

  # ──────────────────────────────────────────────
  # STAGE 2: Integration (every PR, <5min)
  # ──────────────────────────────────────────────
  integration-tests:
    needs: fast-tests
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: ${{ matrix.python }} }
      - run: pip install -e ".[dev]"

      # Local integration + platform contract tests
      - name: Integration Tests
        run: pytest -m "local" --timeout=300

      # SDK assumption tests (stubbed mode — against recorded responses)
      - name: SDK Assumption Tests (stubbed)
        run: pytest tests/sdk_assumptions/ -m "stubbed" --timeout=120

  # ──────────────────────────────────────────────
  # STAGE 3: Evidence baseline (every PR merge)
  # ──────────────────────────────────────────────
  evidence-baseline:
    needs: integration-tests
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - name: Generate Evidence
        run: pytest -m "pure or stubbed or local" --evidence-dir=evidence/current/
      - name: Compare to Baseline
        run: python tests/evidence/compare.py evidence/current/ tests/evidence/baselines/
      - name: Upload Evidence
        uses: actions/upload-artifact@v4
        with:
          name: test-evidence-${{ github.sha }}
          path: evidence/current/

  # ──────────────────────────────────────────────
  # STAGE 4: Live smoke (nightly, <10min)
  # ──────────────────────────────────────────────
  live-smoke:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"

      # Live API tests — validates SDK assumptions against real API
      - name: Live API Smoke Tests
        env:
          COPILOT_TOKEN: ${{ secrets.COPILOT_TOKEN }}
          TEST_LIVE_API: "1"
        run: pytest -m "live" --timeout=600

      # SDK assumption tests (live mode — against real API)
      - name: SDK Assumptions (live)
        env:
          COPILOT_TOKEN: ${{ secrets.COPILOT_TOKEN }}
          TEST_LIVE_API: "1"
        run: pytest tests/sdk_assumptions/ --timeout=300

      # Update snapshots if API shape changed (creates PR)
      - name: Update Snapshots (if changed)
        run: python scripts/update_snapshots.py --auto-pr
```

### Pipeline Decision Rules

| Signal | Action |
|--------|--------|
| Fast tests fail | Block merge. Fix immediately. |
| Integration tests fail on one OS only | Block merge. Platform contract violated. |
| Evidence baseline differs | Warn in PR comment. Require human review of behavioral change. |
| Contract coverage < 95% | Block merge. Missing MUST clause test. |
| Live smoke fails | Create issue, notify on-call. Do NOT block merges (API may be down). |
| SDK assumption fails (live) | Create issue with "sdk-drift" label. Snapshot update PR auto-created. |

### Evidence as CI Artifact

Every CI run produces structured evidence JSON. This enables:
- **Behavioral diff in PRs**: "This PR changed the actual output of 3 tests" — surfaced in PR comments
- **Historical analysis**: Track how test outputs evolve over time
- **Regression forensics**: When did behavior X change? Check the evidence artifacts.

---

## 7. Reconciliation Decisions

These are the design conflicts between the input proposals and how they were resolved:

| Conflict | Wave 1 Position | Wave 2 Position | Resolution |
|----------|----------------|----------------|------------|
| Test organization | By speed tier (unit/, property/, integration/, live/) | By contract (contract_tests/, sdk_assumptions/) | **Hybrid**: Directories by *purpose*, markers by *speed*. Tests live in `unit/`, `contract/`, `sdk_assumptions/`, `integration/`, `live/`, `platform/`, `property/`. Speed is a marker, not a directory. |
| Evidence capture | Separate evidence framework with explicit capture calls | Contract violations are the evidence | **Both**: Evidence collector runs as a pytest plugin (auto-capture), contract violations produce rich diagnostic evidence. No manual `ev.record_assertion()` calls in normal tests — the plugin captures inputs/outputs automatically. Manual evidence only for complex multi-step tests. |
| Property test scope | 10% allocation, separate tier | Used to verify contract invariants | **Merged**: Properties ARE contract compliance tests for universal invariants. A MUST ALWAYS clause becomes a property test. A MUST [specific condition] clause becomes an example test. Properties count toward the contract compliance allocation. The 10% standalone is for invariants not tied to a specific contract clause (e.g., serialization roundtrips). |
| SDK assumption test frequency | Dual-mode (stubbed daily, live nightly) | Not specifically addressed | **Adopted from Wave 1**: Dual-mode is the right call. Stubbed on every PR (fast), live nightly (real). |
| Hexagonal ports | Defined 4 ports (Http, Token, Clock, FileSystem) | Contracts define the same boundaries implicitly | **Wave 1 ports adopted**: Explicit port interfaces enable the stub/real switching that makes the diamond work. Contracts define WHAT the ports must do; ports define HOW to swap implementations. |

---

## 8. Summary: The Unified Testing Strategy

**Shape**: Contract-Anchored Diamond — thick middle of contract compliance and SDK assumption tests, thin top (live smoke) and bottom (pure units are partially replaced by properties).

**Anchor**: Every test traces to a contract clause. No orphan tests. No "test this because it seems important."

**Evidence**: Every test run produces structured evidence artifacts. Evidence enables behavioral diffing in PRs and historical regression analysis.

**Speed**: Four enforced tiers (pure <10ms, stubbed <500ms, local <5s, live <60s). No unmarked tests. Violations fail the build.

**AI-Friendliness**: Tests are contract-anchored, evidence-producing, self-diagnosing, deterministic, and speed-declared. An AI agent can understand, maintain, and trust every test without institutional knowledge.

**CI**: Four-stage pipeline — fast feedback on every commit, cross-platform integration on every PR, evidence baselining on merge, live smoke nightly. SDK assumption drift auto-creates PRs.

**Principle**: Contracts define WHAT to test. The diamond defines HOW MUCH. Evidence captures WHAT HAPPENED. Properties guard WHAT MUST ALWAYS HOLD. Speed tiers enforce WHEN tests run. Together they form a testing strategy where an AI agent can maintain the provider with confidence that every behavioral requirement is verified, every SDK assumption is guarded, and every test result is auditable.