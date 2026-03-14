# F-047: Testing Course Correction — Comprehensive TDD Enforcement

**Status**: ready
**Priority**: critical
**Type**: process / testing infrastructure / governance
**Estimated Effort**: large (multiple test files + contract updates + process changes)

---

## Executive Summary

F-044 and F-045 were fundamental SDK integration bugs that survived 42 feature implementations. This document synthesizes findings from five expert agents (zen-architect, bug-hunter, integration-specialist, explorer, amplifier-expert) into a comprehensive course correction.

**The Core Failure**: We practiced TDD on our adapter code, not on the SDK boundary contract. MagicMock accepted anything without validation. Tests verified "did we call a function?" not "did we send the correct configuration?"

---

## Part 1: What Went Wrong (Post-Mortem)

### The Evidence

| Bug | Root Cause | How It Survived |
|-----|------------|-----------------|
| **F-044**: System prompt uses `mode: "append"` | Test at line 125 of `test_sdk_boundary.py` asserted `"append"` — it **codified the bug** | Test passed ✓ (wrong assertion) |
| **F-045**: SDK tools not disabled (`available_tools` not set) | No test ever checked for `available_tools` key | Test didn't exist |

### The Testing Gaps

| Gap | Severity | Impact |
|-----|----------|--------|
| **Mock forgiveness** | 🔴 CRITICAL | `MagicMock()` accepts any input without validation |
| **No config capture** | 🔴 CRITICAL | Never verified what was sent to SDK |
| **Shadow tests too shallow** | 🟡 HIGH | Verified loading, not identity/tool routing |
| **Live tests gated** | 🟡 HIGH | Required credentials unavailable in CI |
| **Contracts too high-level** | 🟡 HIGH | Said "what" not "how" |
| **No SDK assumption tests** | 🟠 MEDIUM | Didn't verify SDK types we depend on |

### The Mock Problem (Detailed)

From bug-hunter's analysis:

```python
# What we did (WRONG):
mock_client.create_session = AsyncMock(return_value=mock_session)
# This accepts ANY dict silently. No validation.

# What should have existed:
async def validated_create_session(config: dict) -> Any:
    assert config["system_message"]["mode"] == "replace"  # F-044 catch
    assert "available_tools" in config                     # F-045 catch
    assert config["available_tools"] == []                 # F-045 catch
    return mock_session
```

**The test that codified the bug:**
```python
# test_sdk_boundary.py line 125 — THE BUG FROZEN AS A SPEC:
assert config["system_message"] == {"mode": "append", "content": "Be helpful"}
```

When this test was written, whoever wrote it wrote down the **observed behavior**, not the **required behavior**. The test became a specification that locked in the wrong value.

---

## Part 2: The Corrected Testing Architecture

### Test Pyramid for SDK Integration

```
                    ┌──────────────────┐
                    │   Live Smoke     │  Tier 7: Real API (nightly)
                    │    5 tests       │  - Identity verification
                    │                  │  - Tool sovereignty check
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │   SDK Assumptions       │  Tier 6: Real SDK, no API
                │     12 tests            │  - SessionConfig fields exist
                │                         │  - SystemMessageConfig structure
                │                         │  - available_tools semantics
                └────────────┬────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         │  Boundary Contract Tests (NEW)        │  Tier 5: Config capture
         │    7 tests                            │  - Exact config assertions
         │                                       │  - No MagicMock forgiveness
         └───────────────────┬───────────────────┘
                             │
    ┌────────────────────────┴────────────────────────┐
    │  Configuration Invariant Tests (NEW)           │  Tier 4: Parameterized
    │    6+ tests (parameterized)                     │  - Invariants across inputs
    │                                                 │  - Unknown key detection
    └────────────────────────┬────────────────────────┘
                             │
    ┌────────────────────────┴────────────────────────┐
    │  Existing Unit/Integration Tests               │  Tiers 1-3: Current suite
    │    100+ tests                                   │  - Domain logic
    │                                                 │  - Error translation
    │                                                 │  - Streaming accumulation
    └─────────────────────────────────────────────────┘
```

### Test Categories

| Category | File | Purpose | Catches |
|----------|------|---------|---------|
| **Boundary Contract** | `test_sdk_boundary_contract.py` | Verify exact config dict sent to SDK | F-044, F-045 class bugs |
| **Config Invariants** | `test_session_config_invariants.py` | Verify invariants hold across inputs | Missing keys, wrong values |
| **SDK Assumptions** | `test_sdk_assumptions.py` | Verify SDK types we depend on | SDK drift |
| **Live Smoke** | `test_live_sdk.py` | End-to-end with real API | Integration bugs |

---

## Part 3: The ConfigCapturingMock Pattern

### Why It's Different from MagicMock

| Aspect | MagicMock | ConfigCapturingMock |
|--------|-----------|---------------------|
| Accepts any call | ✓ Yes | ✗ Only `create_session(dict)` |
| Validates input | ✗ No | ✓ Type-checked |
| Records what was sent | ✗ No | ✓ Deep copies config |
| Enables assertions | ✗ No | ✓ On exact values |

### Implementation

```python
# tests/fixtures/config_capture.py

class ConfigCapturingMock:
    """Mock SDK client that captures session configuration.
    
    Unlike MagicMock, this fixture:
    1. Records the exact dict passed to create_session()
    2. Validates it's a dict (not arbitrary args)
    3. Returns a minimal but functional mock session
    4. Does NOT accept arbitrary method calls
    """

    def __init__(self) -> None:
        self.captured_configs: list[dict[str, Any]] = []
        self._mock_session = self._create_mock_session()

    def _create_mock_session(self) -> Any:
        session = MagicMock()
        session.session_id = "mock-session-001"
        session.disconnect = AsyncMock()
        session.register_pre_tool_use_hook = MagicMock()
        return session

    async def create_session(self, config: dict[str, Any]) -> Any:
        if not isinstance(config, dict):
            raise TypeError(
                f"create_session expects dict, got {type(config).__name__}. "
                f"This mock enforces the SDK contract."
            )
        self.captured_configs.append(copy.deepcopy(config))
        return self._mock_session

    @property
    def last_config(self) -> dict[str, Any]:
        if not self.captured_configs:
            raise AssertionError("No configs captured. Was create_session called?")
        return self.captured_configs[-1]
```

### Usage

```python
@pytest.mark.asyncio
async def test_available_tools_always_empty_list():
    """F-045: SDK built-in tools MUST be disabled."""
    mock_client = ConfigCapturingMock()
    wrapper = CopilotClientWrapper(sdk_client=mock_client)
    
    async with wrapper.session(model="gpt-4o"):
        pass
    
    config = mock_client.last_config
    assert "available_tools" in config, "available_tools MUST be set"
    assert config["available_tools"] == [], "available_tools MUST be empty list"
```

---

## Part 4: Contract Updates

### `contracts/sdk-boundary.md` — New Section

```markdown
## Session Configuration Contract

### MUST Constraints

1. **MUST** set `available_tools: []` to disable SDK built-in tools (F-045)
2. **MUST** use `system_message.mode: "replace"` when system_message is provided (F-044)
3. **MUST** set `on_permission_request` handler on every session (F-033)
4. **MUST** set `streaming: true` for event-based tool capture
5. **MUST** register `preToolUse` deny hook after session creation
6. **MUST NOT** include keys that are not in SDK's SessionConfig TypedDict

### Test Anchors

| Anchor | Clause |
|--------|--------|
| `sdk-boundary:Config:MUST:1` | available_tools is empty list |
| `sdk-boundary:Config:MUST:2` | system_message mode is replace |
| `sdk-boundary:Config:MUST:3` | on_permission_request always set |
| `sdk-boundary:Config:MUST:4` | streaming is true |
| `sdk-boundary:Config:MUST:5` | deny hook registered post-creation |
| `sdk-boundary:Config:MUST:6` | no unknown keys in config |
```

### `contracts/deny-destroy.md` — New Section

```markdown
### 4. SDK Built-in Tool Suppression (deny-destroy:ToolSuppression:MUST:1)

The SDK exposes built-in tools (bash, view, edit, etc.) to the LLM by default.
These tools crash the Copilot CLI when called because they are handled by
Node.js runtime code that expects a different calling convention.

**MUST:** Set `available_tools: []` in every session config.
**MUST NOT:** Allow any SDK built-in tools to be visible to the LLM.

This is the THIRD line of defense in the Deny+Destroy pattern:
1. on_permission_request → deny all permission requests
2. preToolUse hook → deny all tool execution
3. available_tools=[] → prevent SDK tools from being offered to LLM at all

### Test Anchors

| Anchor | Clause |
|--------|--------|
| `deny-destroy:ToolSuppression:MUST:1` | available_tools=[] on every session |
| `deny-destroy:ToolSuppression:MUST:2` | SDK built-in tools never visible to LLM |
```

---

## Part 5: Tests That Would Have Caught F-044 and F-045

### F-044: The Red Test

```python
@pytest.mark.asyncio
async def test_system_message_mode_is_replace_not_append(self) -> None:
    """sdk-boundary:SessionConfig:MUST:2
    
    System message MUST use replace mode so Amplifier bundle persona
    takes precedence over SDK's default 'GitHub Copilot CLI' identity.
    """
    mock_client = ConfigCapturingMock()
    wrapper = CopilotClientWrapper(sdk_client=mock_client)
    
    async with wrapper.session(system_message="You are the Amplifier assistant."):
        pass
    
    config = mock_client.last_config
    assert config["system_message"]["mode"] == "replace", (
        "system_message mode MUST be 'replace', not 'append'. "
        "With 'append', the SDK injects 'You are GitHub Copilot CLI...' first."
    )
```

### F-045: The Red Test

```python
@pytest.mark.asyncio
async def test_session_config_always_sets_available_tools_to_empty_list(self) -> None:
    """deny-destroy:ToolSuppression:MUST:1
    
    available_tools MUST be [] on every session.
    Without this, SDK exposes bash/view/edit to LLM, which crash the CLI.
    """
    mock_client = ConfigCapturingMock()
    wrapper = CopilotClientWrapper(sdk_client=mock_client)
    
    async with wrapper.session():
        pass
    
    config = mock_client.last_config
    assert "available_tools" in config, "available_tools MUST be present"
    assert config["available_tools"] == [], "available_tools MUST be []"
```

---

## Part 6: Shadow Test Enhancements

### Current Gap

Shadow test at `run_shadow_test.sh` only verifies the entry point loads. It doesn't verify:
- Model identity (F-044 regression)
- Tool execution works (F-045 regression)

### Required Additions

```bash
# F-044 Regression Check: Identity Verification
echo "=== Verifying bundle persona (F-044) ==="
RESPONSE=$(amplifier run --bundle /workspace/shadow-test-bundle.md \
  --no-interactive \
  --prompt "In one sentence, what is your name and purpose?" \
  2>&1)

if echo "$RESPONSE" | grep -qi "github copilot cli"; then
  echo "FAIL: Model identifies as 'GitHub Copilot CLI'"
  exit 1
fi
echo "PASS: Model does not identify as GitHub Copilot CLI"

# F-045 Regression Check: Tool Execution
echo "=== Tool execution smoke test (F-045) ==="
RESPONSE=$(amplifier run --bundle /workspace/shadow-test-bundle.md \
  --no-interactive \
  --prompt "Run: echo hello_from_shadow_test" \
  --timeout 60 \
  2>&1)

if echo "$RESPONSE" | grep -qi "cannot read properties\|TypeError"; then
  echo "FAIL: JavaScript error detected — SDK built-in tools exposed"
  exit 1
fi

if ! echo "$RESPONSE" | grep -q "hello_from_shadow_test"; then
  echo "FAIL: Tool did not execute successfully"
  exit 1
fi
echo "PASS: Tool executed without JS error"
```

---

## Part 7: Dev Machine Governance Rules

### Before Marking ANY SDK-Touching Feature "Done"

The dev machine MUST verify:

1. **Boundary contract tests pass**:
   ```bash
   pytest tests/test_sdk_boundary_contract.py -v
   ```

2. **Invariant tests pass**:
   ```bash
   pytest tests/test_session_config_invariants.py -v
   ```

3. **SDK assumption tests pass**:
   ```bash
   pytest -m sdk_assumption -v
   ```

4. **No unknown config keys**: The unknown-key test catches typos

5. **Full suite green**:
   ```bash
   pytest tests/ -v --ignore=tests/test_live_sdk.py
   ```

### New Pytest Markers

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "sdk_assumption: tests that verify SDK type/behavior assumptions",
    "sdk_boundary: tests that verify SDK boundary contract",
    "live: tests that require real API credentials",
    "contract: tests linked to contract clauses",
]
```

---

## Part 8: Implementation Checklist

### Phase 1: Test Infrastructure (F-046)

- [ ] Create `tests/fixtures/config_capture.py` with ConfigCapturingMock
- [ ] Add fixtures to `tests/conftest.py`
- [ ] Add pytest markers to `pyproject.toml`

### Phase 2: Boundary Contract Tests (F-046)

- [ ] Create `tests/test_sdk_boundary_contract.py`:
  - [ ] `test_available_tools_always_empty_list`
  - [ ] `test_system_message_uses_replace_mode`
  - [ ] `test_system_message_absent_when_not_provided`
  - [ ] `test_permission_handler_always_set`
  - [ ] `test_streaming_always_enabled`
  - [ ] `test_model_passed_through`
  - [ ] `test_deny_hook_registered_on_session`

### Phase 3: Configuration Invariant Tests (F-046)

- [ ] Create `tests/test_session_config_invariants.py`:
  - [ ] `test_invariants_hold_for_any_model` (parameterized)
  - [ ] `test_invariants_hold_with_system_message_variations`
  - [ ] `test_no_unexpected_keys_in_config`

### Phase 4: SDK Assumption Tests (F-046)

- [ ] Enhance `tests/test_sdk_assumptions.py`:
  - [ ] `TestSessionConfigTypeAssumptions`
  - [ ] `TestSystemMessageConfigAssumptions`
  - [ ] `TestCopilotClientCreateSessionAssumptions`

### Phase 5: Implement Fixes

- [ ] F-044: Change `"append"` → `"replace"` in `client.py` line 221
- [ ] F-045: Add `session_config["available_tools"] = []` in `client.py` line ~217
- [ ] Update `test_sdk_boundary.py` line 125: `"append"` → `"replace"`

### Phase 6: Contract Updates

- [ ] Add Session Configuration Contract to `contracts/sdk-boundary.md`
- [ ] Add Tool Suppression section to `contracts/deny-destroy.md`

### Phase 7: Shadow Test Enhancement

- [ ] Add identity verification to shadow test
- [ ] Add tool execution verification to shadow test

### Phase 8: Live Smoke Tests

- [ ] Add `TestLiveToolSovereignty` to `test_live_sdk.py`:
  - [ ] `test_sdk_builtin_tools_not_visible`
  - [ ] `test_system_prompt_identity`

---

## Part 9: Prevention Matrix

| Bug Pattern | Prevention Layer | How It Catches |
|-------------|------------------|----------------|
| Wrong config value | Boundary contract test | Exact value assertion |
| Missing config key | Invariant test | Key presence check |
| Typo in config key | Unknown key test | Non-SDK key detection |
| SDK removes field | SDK assumption test | Type annotation check |
| SDK behavior change | Live smoke test | End-to-end verification |
| Mock forgiveness | ConfigCapturingMock | Type-checked, deep copy |
| Test codifies bug | Contract-first TDD | Write contract, then test, then code |

---

## Part 10: Amplifier Pattern Alignment

From amplifier-expert's validation:

### Test Inheritance Pattern

```python
# Reference providers (Anthropic, OpenAI) use:
from amplifier_core.validation.behavioral import ProviderBehaviorTests

class TestGitHubCopilotProviderBehavior(ProviderBehaviorTests):
    """Run standard provider behavioral tests."""
    pass  # Kernel provides the tests
```

### Mechanism vs Policy in Testing

| Aspect | Mechanism (Kernel) | Policy (Module) |
|--------|-------------------|-----------------|
| **Test Contracts** | Kernel provides ProviderBehaviorTests | Module adds feature-specific |
| **Error Types** | Kernel defines LLMError subclasses | Module translates SDK → kernel |
| **Retry Logic** | Kernel provides error.retryable flag | Module implements strategy |

---

## References

- Expert reports: zen-architect, bug-hunter, integration-specialist, explorer, amplifier-expert
- F-044 spec: `specs/features/F-044-system-prompt-replace-mode.md`
- F-045 spec: `specs/features/F-045-disable-sdk-builtin-tools.md`
- F-046 spec: `specs/features/F-046-sdk-integration-testing-architecture.md`
- SDK source: `reference-only/copilot-sdk/python/copilot/types.py`
- SDK source: `reference-only/copilot-sdk/python/copilot/client.py`

---

*Created: 2026-03-14*
*Author: Expert panel synthesis (zen-architect, bug-hunter, integration-specialist, explorer, amplifier-expert)*
*Purpose: Prevent F-044/F-045 class bugs from ever recurring*
