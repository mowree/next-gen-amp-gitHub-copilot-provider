# DEBATE ROUND 3: Definitive Implementation Roadmap

**Author**: The Zen Architect  
**Date**: 2026-03-08  
**Status**: Round 3 — Crystallized from 31 documents across Waves 1-3, Round 2 mediations, Golden Vision Draft  
**Mandate**: No more debates until Phase 1 ships. This is the build order.

---

## Preamble: What This Document Is

This is not a vision. It is a construction schedule. Every task answers four questions: what failure mode does it prevent, what is the minimum viable version, what tests prove completion, and who approves it. Tasks that cannot answer all four questions have been removed.

The Skeptic's challenge — "Will the machine ever actually run?" — is the organizing principle. Week 1 makes the machine run. Week 2 makes it observable. Weeks 3-4 make it resilient. In that order, with explicit stop-work criteria at every boundary.

---

## Week 1: Foundation (Days 1-5)

**Goal**: A decomposed, testable, CI-gated provider that passes all existing tests with no behavioral change.

### Day 1: Project Scaffolding + Module Boundary Planning

**Deliverables**:
- `pyproject.toml` with exact SDK version pin, dev dependencies (pytest, pytest-asyncio, ruff, pyright, hypothesis)
- Directory structure created (flat package, no nested subpackages — per Round 2 consensus)
- `conftest.py` with speed tier enforcement (pure <10ms, stubbed <500ms, local <5s, live <60s)
- `from __future__ import annotations` in every existing file
- Dependency DAG documented as a comment block in `__init__.py`

**Failure mode prevented**: Without scaffolding, every subsequent task makes ad-hoc structural decisions that conflict. The 305-turn loop bug originated from structural confusion in the monolith.

**Minimum viable version**: Directory structure exists. `pip install -e ".[dev]"` succeeds. `pytest --collect-only` runs without import errors. `ruff check .` and `pyright .` run clean on the existing codebase (or with a documented baseline of pre-existing issues).

**Tests that prove completion**:
- `pip install -e ".[dev]" && python -c "import provider_github_copilot"` exits 0
- `ruff check . --statistics` produces output (no crash)
- `pyright .` produces output (no crash)
- `pytest --collect-only` discovers existing tests

**Approval**: Tier 1 (fully autonomous) — no behavioral change, deterministic validation, reversible.

**Blockers**: None. This is the root task.

---

### Day 2: Extract Error Translation Module

**Deliverables**:
- `error_translation.py` (~200 lines) extracted from `provider.py`
- Domain exception hierarchy: `CopilotProviderError` base with 8 subclasses (Auth, RateLimit, Timeout, ContentFilter, Session, ModelNotFound, Subprocess, CircuitBreaker)
- Each exception carries `retryable: bool` and optional `retry_after: float`
- `translate_sdk_error()` function as the sole error boundary
- Regex-based `retry_after` extraction from unstructured error messages
- All existing error handling tests pass with only import path changes

**Failure mode prevented**: Error handling is currently scattered across `provider.py` with inconsistent classification. SDK errors surface as generic exceptions, making retry decisions impossible. The Error Handling analysis (Wave 2) identified 7 error categories currently conflated into generic exception catching.

**Minimum viable version**: The `translate_sdk_error()` function accepts any `Exception` and returns a typed domain exception with correct `retryable` flag. The 6 most common SDK error types (auth, rate limit, timeout, content filter, session, connection) are mapped. Unknown exceptions map to `CopilotProviderError(retryable=False)`.

**Tests that prove completion**:
- Unit tests for each SDK exception type → domain exception mapping (6 tests minimum)
- Test that unknown exceptions produce non-retryable `CopilotProviderError`
- Test that `retry_after` is extracted from both structured fields and error message strings
- All pre-existing tests pass (`pytest` green)
- `ruff check error_translation.py` clean
- `pyright error_translation.py` clean
- Module is ≤250 lines (`wc -l`)

**Approval**: Tier 2 (AI writes, human approves PR) — behavioral code extracted, import paths change.

**Blockers**: Day 1 scaffolding complete.

---

### Day 3: Extract Tool Parsing Module

**Deliverables**:
- `tool_parsing.py` (~250 lines) extracted from `provider.py`
- `parse_tool_calls()` function: extracts tool call blocks from SDK response
- Fake tool detection: identifies and filters SDK-injected built-in tool calls
- Missing result repair: generates placeholder results for tool calls that lack them
- Tool call ID generation for calls missing IDs

**Failure mode prevented**: Tool parsing is the most security-sensitive code path. The preToolUse deny hook (Deny + Destroy pattern) depends on correct tool identification. Fake tools from the SDK's 27 built-in tools must never reach Amplifier's orchestrator. Currently embedded in the monolith where it cannot be tested independently.

**Minimum viable version**: `parse_tool_calls(response) → list[ToolCallBlock]` correctly extracts tool calls, filters fakes, and repairs missing data. The function is pure (no I/O, no side effects) and testable in isolation.

**Tests that prove completion**:
- Test: valid tool calls are extracted with correct IDs, names, and arguments
- Test: SDK built-in tools (e.g., `editFile`, `runCommand`) are filtered out
- Test: tool calls with missing IDs get generated UUIDs
- Test: malformed JSON arguments are handled gracefully (empty dict, not crash)
- Test: empty response produces empty list (not None, not crash)
- All pre-existing tests pass
- Module ≤300 lines

**Approval**: Tier 2 — security-adjacent code path, requires human review of fake tool detection logic.

**Blockers**: Day 1 scaffolding.

---

### Day 4: Extract Session Factory + Streaming Handler

**Deliverables**:
- `session_factory.py` (~250 lines): builds SDK session configuration from Amplifier's ChatRequest
  - Model resolution (requested model → SDK model ID)
  - System prompt injection
  - Tool definition translation (Amplifier format → SDK format)
  - Ephemeral session enforcement (no state accumulation)
  - preToolUse deny hook registration
- `streaming.py` (~200 lines): streaming event handler
  - Text delta accumulation
  - Thinking delta accumulation (extended thinking models)
  - Usage metadata extraction
  - Session idle detection (completion signal)

**Failure mode prevented**: Session configuration and streaming are the two largest concerns interleaved in the monolith. Session misconfiguration can break sovereignty (if ephemeral sessions aren't enforced or deny hooks aren't registered). Streaming bugs can cause data loss (missed deltas) or infinite loops (missed completion signals).

**Minimum viable version**: Session factory produces a valid SDK session config from any well-formed ChatRequest. Streaming handler accumulates deltas and detects completion. Both are independently testable.

**Tests that prove completion**:
- Session factory: test that ephemeral mode is always set (sovereignty preservation)
- Session factory: test that preToolUse deny hook is always registered
- Session factory: test that system prompt is injected correctly
- Streaming: test that text deltas accumulate in order
- Streaming: test that thinking deltas are separated from text deltas
- Streaming: test that session_idle triggers completion
- Streaming: test that usage metadata is captured
- All pre-existing tests pass
- Each module ≤300 lines

**Approval**: Tier 2 — sovereignty-critical code (deny hook registration), requires human verification.

**Blockers**: Day 1 scaffolding, Day 2 error module (streaming imports error types).

---

### Day 5: Extract Completion Orchestrator + Integration Verification

**Deliverables**:
- `completion.py` (~350 lines): the LLM call lifecycle orchestrator
  - Creates ephemeral session via session factory
  - Sends prompt via SDK driver
  - Processes streaming events via streaming handler
  - Captures tool calls (first-turn-only) via tool parsing
  - Translates errors via error translation
  - Circuit breaker logic (3-turn soft limit, 10-turn hard limit)
  - Returns ChatResponse with accumulated content, tool calls, and usage
- Slimmed `provider.py` (~300 lines): thin delegation layer implementing the 5-method Provider Protocol
  - `name` → static property
  - `get_info()` → delegates to model cache
  - `list_models()` → delegates to model cache
  - `complete()` → delegates to completion orchestrator
  - `parse_tool_calls()` → delegates to tool parsing
- **Full integration verification**: all existing tests pass against the decomposed structure

**Failure mode prevented**: The completion orchestrator is where all extracted modules compose. If the wiring is wrong, the provider silently produces incorrect results. Day 5 is explicitly allocated for integration verification, not just extraction.

**Minimum viable version**: `provider.py` is ≤350 lines. `completion.py` orchestrates the full call lifecycle. All 5 Provider Protocol methods work identically to the pre-decomposition version.

**Tests that prove completion**:
- Full test suite passes (`pytest` — 100% green, zero regressions)
- `provider.py` ≤350 lines (`wc -l`)
- No module exceeds 400 lines (soft cap)
- `ruff check .` clean
- `pyright .` clean (or no new errors beyond baseline)
- Zero circular imports (validated by import test or `importlib` check)
- Every module has `from __future__ import annotations`
- **Behavioral equivalence**: for 5 representative requests, the decomposed provider produces byte-identical responses to the monolith (snapshot comparison)

**Approval**: Tier 2 — this is the integration point where all Week 1 work composes. Human must verify that the decomposition preserved behavior.

**Blockers**: Days 2-4 complete.

---

### Week 1 Success Criteria (Gate for Week 2)

All of the following must be true before Week 2 begins:

| Criterion | Measurement | Pass/Fail |
|-----------|-------------|-----------|
| All existing tests pass | `pytest` exit code 0 | Binary |
| No module exceeds 400 lines | `wc -l` on each `.py` file | Binary |
| Zero circular imports | Import validation test | Binary |
| `provider.py` ≤350 lines | `wc -l provider.py` | Binary |
| Ruff clean | `ruff check .` exit code 0 | Binary |
| Pyright clean (or baselined) | `pyright .` no new errors | Binary |
| Behavioral equivalence | Snapshot comparison on 5 representative requests | Binary |

**Stop-work criterion**: If behavioral equivalence cannot be demonstrated (snapshot comparison fails and the cause cannot be identified within 4 hours), STOP. Revert all changes. The monolith's behavior is the source of truth. Revisit the extraction strategy before proceeding.

**Decision point requiring human input**: If any module exceeds 400 lines after extraction, a human must decide whether to (a) allow the exception with justification, (b) further decompose, or (c) adjust the module boundary. This is a Tier 3 decision (architectural).

---

## Week 2: Core (Days 6-10)

**Goal**: The provider has SDK canary tests, a basic CI pipeline, and lightweight observability. It can detect when the SDK changes.

**Prerequisite**: Week 1 gate criteria met.

### Day 6: SDK Canary Test Suite (Type Shape + Function Signature)

**Deliverables**:
- `tests/sdk_assumptions/` directory with ~12 type shape and function signature tests
- Type shape tests: verify that every SDK type we import still exists with expected fields
  - `CopilotClient` exists and has `create_session` method
  - `Session` has `send`, `abort`, `destroy` methods
  - `SessionConfig` accepts `model`, `system_prompt`, `max_tokens` parameters
  - Event types we handle exist in `SessionEventType` enum
- Function signature tests: verify that SDK functions accept the arguments we pass
  - `create_session()` accepts our config shape
  - `send()` accepts prompt string and tool definitions
  - Hook registration accepts our callback signature
- Each test tagged with `sdk_version`, `risk_if_violated`, `auto_healable`

**Failure mode prevented**: SDK changes silently break the provider. This is the #1 risk identified across all debate documents. The SDK is pre-1.0 and actively evolving. Without canary tests, the first sign of breakage is a production error.

**Minimum viable version**: 12 tests covering the 12 SDK import paths identified in the Dependency Management analysis (Wave 2). Tests run against the pinned SDK version and pass. Tests are fast (<200ms each, stubbed mode).

**Tests that prove completion**:
- `pytest tests/sdk_assumptions/ -v` passes with 12+ tests
- Each test has a docstring citing the specific SDK assumption
- Each test has `sdk_version` metadata tag
- Tests run in <5 seconds total

**Approval**: Tier 2 — tests are specifications (new contracts), human should review what we're asserting about the SDK.

**Blockers**: Week 1 complete.

---

### Day 7: SDK Canary Tests (Behavioral + Error Contract)

**Deliverables**:
- ~8 additional canary tests covering behavioral expectations and error contracts
- Behavioral tests (using recorded/stubbed responses):
  - Streaming sends delta events before complete message
  - Session idle event signals completion
  - preToolUse hook receives tool call data in expected format
  - Abort stops the session within expected timeframe
- Error contract tests:
  - Auth failures produce recognizable error type/message pattern
  - Rate limits include retry-after information (structured or in message)
  - Timeout errors are distinguishable from other errors
  - Content filter violations produce identifiable error pattern
- Recorded response fixtures in `tests/fixtures/sdk_responses/`

**Failure mode prevented**: Type shape tests (Day 6) catch structural changes. Behavioral tests catch semantic changes — the SDK returns the right types but with different meaning, ordering, or timing. The Self-Healing Design analysis documented that 30% of SDK changes are behavioral, not structural.

**Minimum viable version**: 8 behavioral/error tests using recorded SDK responses. Tests validate event ordering, error classification, and hook data format. Total canary suite is now ~20 tests.

**Tests that prove completion**:
- `pytest tests/sdk_assumptions/ -v` passes with 20+ tests
- Each behavioral test uses a recorded response fixture (not live API)
- Recorded fixtures are committed to the repo with the SDK version they were captured from
- Total canary suite runs in <10 seconds

**Approval**: Tier 2 — behavioral contracts being asserted, human reviews the assertions.

**Blockers**: Day 6 complete (type tests provide the structural foundation for behavioral tests).

---

### Day 8: Basic CI Pipeline

**Deliverables**:
- `.github/workflows/ci.yml` with three gates:
  1. **Lint** (ruff check + ruff format --check): <10 seconds
  2. **Type check** (pyright): <30 seconds
  3. **Test** (pytest -m "pure or stubbed"): <90 seconds
- Single Python version (3.12), single OS (ubuntu-latest), single SDK version (pinned)
- Pipeline runs on push and pull_request
- Pipeline blocks merge on failure

**Failure mode prevented**: Broken code reaches the main branch. Regressions go undetected between local development sessions. Without CI, the canary tests only run when someone remembers to run them.

**Minimum viable version**: Three sequential gates. If lint fails, type check doesn't run. If type check fails, tests don't run. Total pipeline time <3 minutes. No matrix builds, no caching optimization, no nightly schedules.

**Tests that prove completion**:
- Push a commit; CI runs and passes
- Introduce a deliberate lint error; CI fails at gate 1
- Introduce a deliberate type error; CI fails at gate 2
- Introduce a deliberate test failure; CI fails at gate 3
- All three gates pass on the clean codebase

**Approval**: Tier 1 (fully autonomous) — infrastructure setup, deterministic validation, no behavioral change.

**Blockers**: Days 6-7 complete (canary tests must exist for the test gate to be meaningful).

---

### Day 9: Lightweight Streaming Metrics + Architecture Fitness Test

**Deliverables**:
- Streaming metrics added to `streaming.py` (4 counters/timestamps, no framework):
  - `ttft_ms`: time from session send to first text delta
  - `total_stream_ms`: time from first delta to completion signal
  - `delta_count`: total delta events received (0 with content = error)
  - `max_gap_ms`: maximum inter-event gap (detects stalls)
- Metrics logged via structured logging (not emitted to any external system)
- Architecture fitness test in `tests/architecture/`:
  - `test_no_sdk_imports_outside_boundary.py`: scans all `.py` files, fails if SDK imports exist outside the adapter boundary modules
  - `test_no_circular_imports.py`: validates the dependency DAG
  - `test_module_size_limits.py`: fails if any module exceeds 500 lines

**Failure mode prevented**: Streaming breaks silently (metrics). SDK types leak beyond the boundary over time (fitness test). Modules grow back into monoliths (size test). Circular imports create fragile coupling (import test). These are structural invariants that must be enforced continuously, not just at decomposition time.

**Minimum viable version**: Metrics are 4 timestamp variables in the streaming handler, logged at debug level on completion. Architecture tests are 3 small test files that run in <1 second total.

**Tests that prove completion**:
- Streaming test: verify that `ttft_ms > 0` after a stubbed streaming completion
- Streaming test: verify that `delta_count` matches expected fixture delta count
- Architecture test: intentionally add an SDK import outside boundary, verify test fails, then remove it
- Architecture test: verify all modules pass the 500-line limit
- All tests pass

**Approval**: Tier 2 for streaming metrics (behavioral addition), Tier 1 for architecture tests (read-only validation).

**Blockers**: Week 1 decomposition complete (architecture tests validate the decomposed structure).

---

### Day 10: Integration Verification + Week 2 Gate

**Deliverables**:
- Full integration test run against the complete decomposed + tested codebase
- Documentation: `SDK_ASSUMPTIONS.md` auto-generated from canary test docstrings (listing every assumption, SDK version, risk level)
- Version pin verification: `pyproject.toml` has exact SDK pin, no version ranges
- Rollback procedure documented in `CONTRIBUTING.md`: "To rollback SDK version: change pin in pyproject.toml, run tests, deploy"

**Failure mode prevented**: Day 10 is a consolidation day, not a feature day. It prevents the failure mode of "each piece works alone but they don't compose." Also prevents the failure mode of undocumented rollback procedures (the Skeptic's valid concern about operational controls requiring human judgment).

**Minimum viable version**: All tests pass. SDK assumptions are documented. Rollback procedure is a 3-step process anyone can follow.

**Tests that prove completion**:
- `pytest` (full suite) passes
- `pytest tests/sdk_assumptions/ -v` shows 20+ passing canary tests
- `pytest tests/architecture/ -v` shows 3+ passing fitness tests
- CI pipeline passes end-to-end
- `SDK_ASSUMPTIONS.md` exists and lists all assumptions

**Approval**: Tier 2 — documentation and consolidation, human reviews the complete Week 2 deliverable.

**Blockers**: Days 6-9 complete.

---

### Week 2 Success Criteria (Gate for Weeks 3-4)

| Criterion | Measurement | Pass/Fail |
|-----------|-------------|-----------|
| 20+ SDK canary tests passing | `pytest tests/sdk_assumptions/ --count` | Binary |
| 3+ architecture fitness tests passing | `pytest tests/architecture/ --count` | Binary |
| CI pipeline runs on every push | GitHub Actions run history | Binary |
| CI blocks merge on failure | Protected branch rule active | Binary |
| Streaming metrics logged | Debug log contains `ttft_ms` on completion | Binary |
| SDK version pinned (exact) | `grep` pyproject.toml for `==` pin | Binary |
| Rollback procedure documented | `CONTRIBUTING.md` contains rollback steps | Binary |
| All Week 1 criteria still hold | Re-run Week 1 verification | Binary |

**Stop-work criterion**: If the canary test suite cannot be written because the SDK's API surface is undocumented or inaccessible for testing, STOP. This means the SDK boundary design assumed more testability than exists. Reassess whether canary tests should target the CLI subprocess interface instead of the Python SDK types.

**Decision point requiring human input**: If fewer than 15 canary tests can be written (because the SDK surface is smaller than the 12 import paths suggested), a human must decide whether the coverage is sufficient or if additional behavioral tests should compensate.

---

## Weeks 3-4: Autonomy Foundations (Days 11-20)

**Goal**: The provider can detect SDK changes automatically and surface them to humans with full diagnostic context. Semi-automated adaptation for the simplest change category (type renames).

**Prerequisite**: Week 2 gate criteria met. The Skeptic Rebuttal (Round 2) explicitly gated Phase 3 autonomy on Phase 1-2 proving value. Weeks 3-4 are the MINIMUM VIABLE autonomous loop — not the full vision.

### Contingency: What's Contingent on Week 1-2 Success?

Everything in Weeks 3-4 is contingent. If Week 1-2 success criteria are not met:

| If this failed... | Then Weeks 3-4 become... |
|-------------------|--------------------------|
| Decomposition didn't preserve behavior | Fix decomposition. No new features. |
| Canary tests couldn't be written | Research SDK testability. Write integration tests against CLI subprocess instead. |
| CI pipeline unreliable | Stabilize CI. No autonomy without reliable gates. |
| Module boundaries unclear | Revisit architecture. Hold architectural review (Tier 3). |

### Days 11-12: SDK Event Audit + Selective Event Bridge

**Deliverables**:
- **Audit script** that hooks into a real SDK session and logs every event type, payload shape, and ordering
- **Event catalog**: actual SDK events documented (replacing the speculative 58-event list from Wave 1)
- **Selective event bridge** (~200 lines): translates only Critical + Important events
  - Events classified as BRIDGE (translate to domain events), CONSUME (use internally), or DROP (debug log)
  - Expected ~10-15 bridged events based on the SDK Boundary Design (Round 2)
  - `EventTranslator` class with stateful tool call accumulation

**Failure mode prevented**: Building observability for events that don't exist (the Synthesis agent flagged the 58-event catalog as speculative). The audit-first approach ensures we bridge reality, not imagination.

**Minimum viable version**: Event catalog with actual event types. Bridge handles text deltas, thinking deltas, tool calls, usage, errors, and session idle. All other events are DROPped with debug logging. No OTEL, no metrics framework — just translation.

**Tests that prove completion**:
- Unit tests for each BRIDGE translation (text → ContentDelta, thinking → ContentDelta, etc.)
- Test that DROPped events are logged at debug level, not silently swallowed
- Test that tool call accumulation works across start/delta/complete events
- Integration test: recorded SDK event stream produces correct domain events in correct order

**Approval**: Tier 2 — new module creation aspect makes this borderline Tier 3, but the event bridge design was pre-approved in Round 2. Human reviews the event catalog and BRIDGE/CONSUME/DROP classifications.

**Blockers**: Week 2 complete. Real SDK session access for audit.

---

### Days 13-14: Weekly SDK Change Detection (CI Job)

**Deliverables**:
- GitHub Actions workflow: `sdk-check.yml` running on weekly schedule
  - Checks if a new SDK version is available (pip index check)
  - If new version found: creates a temporary branch, updates pin, runs canary suite
  - Reports results as a GitHub Issue with structured body:
    - SDK version delta (old → new)
    - Canary test results (pass/fail per test)
    - Changelog summary (if available)
    - Risk assessment (patch/minor/major)
    - Recommended action (auto-update / human review / block)
- **No auto-fix. No auto-deploy. No adaptation engine.** Detection only.

**Failure mode prevented**: SDK update available and nobody knows until production breaks. The Phased Approach (Round 2) explicitly scoped Phase 1 detection as "a weekly CI job that checks, runs canaries, and reports. A human reads the issue and decides."

**Minimum viable version**: Weekly cron job. Creates GitHub Issue on new SDK version. Issue body includes canary test pass/fail counts. Human decides all next steps.

**Tests that prove completion**:
- Manually trigger the workflow; verify it creates an issue
- Simulate a canary failure (mock a test to fail); verify issue body includes failure details
- Verify the workflow doesn't modify the main branch (temporary branch only)

**Approval**: Tier 1 — read-only detection, no code changes to main branch.

**Blockers**: Day 8 CI pipeline exists. Days 6-7 canary tests exist.

---

### Days 15-16: Property-Based Tests for Pure Functions

**Deliverables**:
- Hypothesis-based property tests for all pure functions in extracted modules:
  - `error_translation.py`: error mapping is total (every exception type produces a domain error, never crashes)
  - `tool_parsing.py`: tool list normalization preserves count; malformed input never crashes
  - `streaming.py`: delta accumulation is monotonically non-decreasing; empty deltas don't corrupt state
  - Model naming: normalization is idempotent (normalizing twice = normalizing once)
  - Serialization: request roundtrips through JSON without data loss
- Tests tagged `@pytest.mark.pure` with <100ms per test execution

**Failure mode prevented**: Edge cases in pure functions that example-based tests miss. The Testing Reconciliation (Round 2) identified properties as ideal for converters and parsers — functions where the input space is large and AI-generated example tests tend to cover only happy paths.

**Minimum viable version**: 8-10 property tests covering the 5 extracted modules' pure functions. Each property test runs 100 examples (Hypothesis default). Focus on "never crashes" and "preserves invariants" properties.

**Tests that prove completion**:
- `pytest -m pure -k property` passes with 8+ property tests
- Each property test runs without Hypothesis health check warnings
- No property test takes >100ms

**Approval**: Tier 2 — new test contracts, human reviews what invariants we're asserting.

**Blockers**: Week 1 decomposition (pure functions must be extracted to test them).

---

### Days 17-18: Semi-Automated Type Change Adaptation (Prototype)

**Deliverables**:
- Prototype script: `scripts/adapt_type_change.py`
  - Input: canary test failure report + SDK version diff
  - Detection: identifies field renames and type renames from canary failures
  - Proposal: generates a diff showing proposed code changes
  - Output: creates a PR branch with the proposed changes + runs test suite
  - **Does NOT auto-merge.** Creates a PR for human review with structured evidence block:
    - Trigger (which canary test failed)
    - Confidence score (computed from test coverage of changed lines + blast radius)
    - Proposed changes (diff)
    - Test results (pass/fail)
    - Rollback instruction (`git revert`)
- Scope limited to Type 1 changes only (field renames, type renames — the 60% category from Self-Healing Design)

**Failure mode prevented**: Manual adaptation of mechanical type changes wastes human time on work that is fully deterministic. The Skeptic demanded: "Pick 10 real historical changes. Attempt AI-only fixes. Measure." This prototype enables that validation.

**Minimum viable version**: Script handles a single field rename (e.g., `message.text → message.content`). It reads the canary failure, identifies the renamed field from the SDK diff, finds all references in our codebase, generates a sed-like replacement, and creates a PR. One change type. One PR. Human reviews.

**Tests that prove completion**:
- Simulate a field rename in a test fixture; verify the script detects it
- Verify the script generates a syntactically valid diff
- Verify the script creates a PR branch (does not push to main)
- Verify the PR body contains the structured evidence block

**Approval**: Tier 3 — new tool creation, architectural decision about adaptation scope. Human must approve the approach before it's used on real SDK changes.

**Blockers**: Days 6-7 canary tests (the adaptation script reads canary failures). Days 13-14 SDK change detection (provides the trigger).

---

### Days 19-20: Consolidation, Documentation, and Adversarial Validation

**Deliverables**:
- **Adversarial validation**: Run the adaptation prototype against 3-5 historical SDK changes (if available from changelog) or simulated changes. Document results:
  - How many changes were correctly detected?
  - How many proposed fixes were correct?
  - How many required human intervention?
  - What was the false positive rate?
- **Updated SDK_ASSUMPTIONS.md** with all canary tests + behavioral tests
- **Architecture Decision Record** summarizing all decisions made during implementation:
  - Module boundaries chosen and why
  - Events bridged vs. dropped and why
  - Policies extracted vs. kept and why
- **Phase 2 gate evaluation**: formal assessment of whether Weeks 3-4 deliverables met success criteria

**Failure mode prevented**: Day 20 is the adversarial benchmark the Skeptic demanded. If the adaptation prototype fails on historical cases, we know before investing further in autonomy. Also prevents documentation drift — the ADR captures decisions while they're fresh.

**Minimum viable version**: 3 simulated SDK changes tested against the adaptation prototype. Results documented honestly (including failures). ADR captures the top 10 architectural decisions.

**Tests that prove completion**:
- Adversarial validation report exists with ≥3 test cases
- ADR exists with ≥10 documented decisions
- All existing tests still pass
- CI pipeline still green

**Approval**: Tier 2 — documentation and validation, human reviews the adversarial results and ADR.

**Blockers**: Days 17-18 adaptation prototype exists.

---

### Weeks 3-4 Approval Gates

| Gate | Decision | Who Decides | Trigger |
|------|----------|-------------|---------|
| Event bridge classifications | Which events are BRIDGE vs. CONSUME vs. DROP | Human (Tier 3) | Day 12 event catalog complete |
| Adaptation prototype scope | Which change types the script handles | Human (Tier 3) | Day 17 prototype design |
| Adversarial validation results | Whether to continue autonomy investment | Human (Tier 3) | Day 20 validation report |
| SDK change detection cadence | Weekly vs. daily vs. on-demand | Human (Tier 2) | Day 14 CI job working |

---

## Risk Register

| # | Risk | Probability | Impact | Mitigation | Detection | Owner |
|---|------|-------------|--------|------------|-----------|-------|
| R1 | SDK breaking change during implementation | MEDIUM | HIGH — blocks all work | Exact version pin in pyproject.toml. Do not upgrade during Weeks 1-2. | CI canary tests (Week 2+) | Autonomous (Tier 1 rollback) |
| R2 | Decomposition introduces subtle behavioral change | HIGH | HIGH — provider silently wrong | Snapshot comparison on Day 5 (5 representative requests). Full test suite as safety net. | Behavioral equivalence test | Human reviews Day 5 PR |
| R3 | Canary tests can't be written (SDK not testable) | LOW | HIGH — entire Week 2 strategy fails | Fallback: test against CLI subprocess output instead of Python SDK types. | Day 6 attempt to write first canary test | Human decides fallback approach (Tier 3) |
| R4 | Module boundaries wrong (too many or too few modules) | MEDIUM | MEDIUM — rework needed | Start with the 5 extraction targets from Phased Approach (Round 2). Adjust based on actual complexity. | Architecture fitness tests, module size checks | Human reviews if any module >400 lines |
| R5 | CI pipeline flaky (non-deterministic test failures) | MEDIUM | MEDIUM — erodes trust in gates | Speed tier enforcement prevents slow/flaky tests. All tests use stubs, not live APIs. No shared state. | CI failure rate tracking | Human investigates if failure rate >5% |
| R6 | Adaptation prototype gives false confidence | MEDIUM | HIGH — over-invest in autonomy | Adversarial validation on Day 20 with honest reporting. The Skeptic's benchmark is the gate. | Adversarial validation results | Human decides based on results (Tier 3) |
| R7 | Scope creep — adding features not in this roadmap | HIGH | MEDIUM — delays foundation work | This document is the scope. If it's not listed here, it's not in scope. Weekly scope check. | Human awareness | Human enforces scope |
| R8 | "Two Orchestrators" conflict resurfaces | LOW | CRITICAL — provider causes kernel instability | Deny + Destroy pattern preserved in session_factory.py. Architecture fitness test validates deny hook registration. | Integration tests, architecture fitness tests | Automated + human review |

---

## Decision Points Requiring Human Input

| Day | Decision | Options | Information Available | Deadline |
|-----|----------|---------|----------------------|----------|
| 5 | Module boundary approval | (a) Accept as-is, (b) Adjust boundaries, (c) Further decompose | Module sizes, test results, behavioral equivalence | End of Day 5 |
| 7 | Canary test coverage sufficiency | (a) 20 tests sufficient, (b) Need more behavioral tests, (c) Need different approach | Canary test list, SDK surface audit | End of Day 7 |
| 12 | Event bridge classifications | (a) Approve BRIDGE/CONSUME/DROP list, (b) Reclassify specific events | Event catalog from audit, domain event type list | End of Day 12 |
| 17 | Adaptation prototype scope | (a) Field renames only, (b) Include type renames, (c) Don't build prototype yet | Canary test data, SDK changelog analysis | End of Day 17 |
| 20 | Continue autonomy investment? | (a) Continue to Phase 2, (b) Pause and stabilize, (c) Adopt Skeptic's "targeted improvements" path | Adversarial validation results, all gate criteria | End of Day 20 |

---

## "Stop Work" Criteria

These are conditions under which ALL implementation work halts and the team reassesses the approach:

### Immediate Stop (Halt within 1 hour)

1. **Behavioral regression detected**: Any existing test that passed before decomposition now fails, and the cause cannot be identified within 2 hours. The monolith's behavior is the source of truth. Revert and reassess.

2. **Security boundary breach**: The Deny + Destroy pattern is broken — SDK executes a tool call, accumulates conversation state, or bypasses the deny hook. This is a Tier 4 (never autonomous) issue. Human must investigate immediately.

3. **Kernel compatibility break**: The decomposed provider fails to mount in the Amplifier kernel. This means the Provider Protocol contract is violated. Revert and investigate.

### Planned Stop (Reassess at next gate)

4. **Module count exceeds 25**: The decomposition has created more modules than the target (~17). Each additional module adds integration surface. If module count exceeds 25, reassess whether boundaries are correct.

5. **Test suite time exceeds 5 minutes**: The fast test suite (pure + stubbed) should complete in <90 seconds. If it exceeds 5 minutes, test architecture needs optimization before adding more tests.

6. **Canary test suite has <10 tests after Day 7**: If the SDK surface doesn't support 10+ canary tests, the self-healing strategy needs fundamental revision (test against CLI output, not SDK types).

7. **Adversarial validation success rate <50% on Day 20**: If the adaptation prototype can't correctly handle half of simulated changes, autonomy investment is premature. Adopt the Skeptic's "targeted improvements" path.

---

## What We Are Explicitly NOT Building (Kill List)

Carried forward from the Phased Approach (Round 2) and Skeptic Rebuttal:

| Item | Status | Reason |
|------|--------|--------|
| AI auto-merge without human review | **KILLED** | The Skeptic's argument is decisive. No confidence score substitutes for human judgment on security and correctness. |
| Adapter shim generation engine | **KILLED** | Shims are auto-generated technical debt. Direct fixes with human review instead. |
| Custom production APM | **KILLED** | Use existing monitoring tools (Datadog, Grafana). Don't build bespoke anomaly detection for one provider. |
| Runtime event catalog validation | **KILLED** | Testing concern, not runtime concern. Validate at build time via lint/test. |
| Multi-version SDK compatibility matrix | **KILLED** | We pin one version. No partial deployments across SDK versions. |
| Nested subpackage structure | **KILLED** | Flat package with clear naming. Decisively rejected in Round 2. |
| ABCs for internal interfaces | **KILLED** | Single-implementation interfaces are premature abstraction. Protocol only where structural typing helps testing. |
| Full OTEL stack | **DEFERRED** | No OTEL collector deployed. Build when there's a consumer. Structured logging covers current needs. |
| 5 recipe pipelines | **DEFERRED** | Start with 0 recipes in Weeks 1-2. Consider 1 recipe (SDK upgrade) after Weeks 3-4 validation. |
| Knowledge capture system | **DEFERRED** | Needs 10+ adaptation records to be useful. We'll have 3-5 at most by Day 20. |
| Full self-healing engine | **DEFERRED** | Contingent on adversarial validation results (Day 20 gate). |
| Session replay debugging | **DEFERRED** | Build when debugging a production issue that can't be reproduced. |
| Test evidence JSON storage | **DEFERRED** | pytest output is the evidence. Structured JSON adds maintenance burden for marginal benefit in Weeks 1-4. |
| Performance baselines + regression gates | **DEFERRED** | Requires usage data that doesn't exist yet. Build after 2+ weeks of production use. |

---

## Summary: The 20-Day Build Order

```
WEEK 1: FOUNDATION (Make it work)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day  1: Scaffolding + dependency setup
Day  2: Extract error_translation.py
Day  3: Extract tool_parsing.py
Day  4: Extract session_factory.py + streaming.py
Day  5: Extract completion.py + FULL INTEGRATION VERIFICATION
         ↓ GATE: All tests pass, no module >400 lines, behavioral equivalence ↓

WEEK 2: CORE (Make it detectable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day  6: SDK canary tests (type shape + function signature)
Day  7: SDK canary tests (behavioral + error contract)
Day  8: CI pipeline (lint → typecheck → test)
Day  9: Streaming metrics + architecture fitness tests
Day 10: Integration verification + documentation
         ↓ GATE: 20+ canary tests, CI blocks merge, metrics logged ↓

WEEKS 3-4: AUTONOMY FOUNDATIONS (Make it resilient)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Day 11-12: SDK event audit + selective event bridge
Day 13-14: Weekly SDK change detection (CI job)
Day 15-16: Property-based tests for pure functions
Day 17-18: Semi-automated type change adaptation (prototype)
Day 19-20: Adversarial validation + ADR + Phase 2 gate
            ↓ GATE: Adversarial results determine autonomy investment ↓
```

**The golden rule**: If a gate fails, fix the foundation before building higher. Autonomy without correctness is automated self-harm. The Skeptic was right: make the machine run first. Then make it observable. Then make it resilient. In that order.

---

*This document is the construction schedule. It replaces all previous roadmaps. No feature not listed here is in scope for the next 20 days. When Day 20 is complete, the adversarial validation results determine whether we proceed with deeper autonomy or adopt the Skeptic's "targeted improvements" path. Either outcome is a success — one means the autonomous vision is validated, the other means we saved months of misguided investment. Both require the same foundation: a decomposed, tested, observable provider that works correctly.*
