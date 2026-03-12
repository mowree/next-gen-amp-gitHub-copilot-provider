# F-026: Contract Compliance Tests

**Priority**: ESSENTIAL
**Source**: test-coverage, zen-architect, core:core-expert
**Estimated Lines**: ~400 test code

## Objective

Create tests that verify every MUST clause in the 7 contract files. This proves correctness, not just "tests pass."

## Acceptance Criteria

### AC-1: test_contract_protocol.py

Maps to `contracts/provider-protocol.md`:

```python
"""
Contract: provider-protocol.md
Tests every MUST clause via anchor IDs.
"""

class TestProtocolNameProperty:
    """provider-protocol:name:MUST:1,2"""
    
    def test_returns_github_copilot_string(self, provider):
        assert provider.name == "github-copilot"
    
    def test_is_a_property_not_method(self, provider):
        assert isinstance(type(provider).name, property)


class TestProtocolComplete:
    """provider-protocol:complete:MUST:1-4"""
    
    async def test_creates_ephemeral_session_per_call(self, provider, mock_sdk):
        # Verify different session IDs on consecutive calls
        ...
    
    async def test_destroys_session_after_turn(self, provider, mock_sdk):
        # Verify session.disconnect called
        ...
    
    async def test_no_state_between_calls(self, provider, mock_sdk):
        # Verify fresh accumulator each time
        ...
    
    async def test_captures_not_executes_tools(self, provider, mock_sdk):
        # Verify tool_calls in response, not executed
        ...


class TestProtocolParseToolCalls:
    """provider-protocol:parse_tool_calls:MUST:1-4"""
    
    def test_uses_arguments_field_not_input(self, provider):
        ...
    
    def test_preserves_tool_call_ids(self, provider):
        ...
```

### AC-2: test_contract_deny_destroy.py

Maps to `contracts/deny-destroy.md`:

```python
"""
Contract: deny-destroy.md
Tests sovereignty guarantee.
"""

class TestDenyHookInstalled:
    """deny-destroy:DenyHook:MUST:1"""
    
    async def test_hook_installed_on_every_session(self, provider, mock_sdk):
        ...


class TestDenyHookNotConfigurable:
    """deny-destroy:DenyHook:MUST:3 — ARCHITECTURE FITNESS"""
    
    def test_no_yaml_key_can_disable_deny_hook(self):
        # Scan config files for any deny-related keys
        ...
    
    def test_deny_hook_always_returns_deny(self, deny_hook):
        ...


class TestArchitectureFitness:
    """deny-destroy:NoExecution:MUST:3 — SDK imports outside sdk_adapter/ are prohibited"""
    
    def test_no_sdk_imports_outside_adapter(self):
        """Scan all .py files outside sdk_adapter/ for copilot imports."""
        import ast
        from pathlib import Path
        
        root = Path("src/amplifier_module_provider_github_copilot")
        for f in root.glob("*.py"):
            tree = ast.parse(f.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    for name in names:
                        assert not (name or "").startswith("copilot"), \
                            f"{f}: SDK import '{name}' found outside sdk_adapter/"
```

### AC-3: test_contract_errors.py

Maps to `contracts/error-hierarchy.md`:

```python
"""
Contract: error-hierarchy.md
Tests error mapping compliance.
"""

class TestErrorConfigCompliance:
    """Verify config/errors.yaml satisfies contracts/error-hierarchy.md."""
    
    def test_auth_errors_not_retryable(self, error_config):
        """Contract: AuthenticationError MUST have retryable=False."""
        auth = [m for m in error_config.mappings if m.kernel_error == "AuthenticationError"]
        assert len(auth) >= 1
        assert all(not m.retryable for m in auth)
    
    def test_quota_exceeded_not_retryable(self, error_config):
        """Contract: QuotaExceededError MUST have retryable=False."""
        quota = [m for m in error_config.mappings if m.kernel_error == "QuotaExceededError"]
        assert all(not m.retryable for m in quota)
    
    def test_rate_limit_retryable(self, error_config):
        """Contract: RateLimitError MUST have retryable=True."""
        rate = [m for m in error_config.mappings if m.kernel_error == "RateLimitError"]
        assert len(rate) >= 1
        assert all(m.retryable for m in rate)
    
    def test_all_mappings_reference_valid_kernel_errors(self, error_config):
        """Contract: Only kernel types from amplifier_core.llm_errors allowed."""
        VALID_KERNEL_ERRORS = {
            "AuthenticationError", "RateLimitError", "LLMTimeoutError",
            "ContentFilterError", "ProviderUnavailableError", "NetworkError",
            "NotFoundError", "QuotaExceededError"
        }
        for mapping in error_config.mappings:
            assert mapping.kernel_error in VALID_KERNEL_ERRORS, \
                f"Invalid kernel error: {mapping.kernel_error}"
```

### AC-4: test_contract_events.py

Maps to `contracts/event-vocabulary.md`:

```python
"""
Contract: event-vocabulary.md
Tests event classification compliance.
"""

class TestEventConfigCompliance:
    """Verify config/events.yaml satisfies contracts/event-vocabulary.md."""
    
    def test_six_bridge_event_types_defined(self, event_config):
        bridge_events = [e for e, c in event_config.event_classifications.items() if c == "BRIDGE"]
        assert len(bridge_events) >= 6
    
    def test_all_bridge_events_have_domain_type(self, event_config, event_translator):
        for event_type in ["text_delta", "thinking_delta", "tool_use_start", 
                           "tool_use_complete", "message_complete", "usage_update"]:
            domain = event_translator.translate({"type": event_type})
            assert domain is not None
```

### AC-5: test_contract_streaming.py

Maps to `contracts/streaming-contract.md`:

```python
"""
Contract: streaming-contract.md
Tests streaming behavior compliance.
"""

class TestStreamingAccumulator:
    """streaming-contract:Accumulator:MUST:1-3"""
    
    def test_preserves_event_order(self, accumulator):
        ...
    
    def test_produces_complete_response_on_message_complete(self, accumulator):
        ...
```

### AC-6: Pytest Markers

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "contract: marks tests as contract compliance (run with -m contract)",
    "pure: marks tests as pure/no-IO (run with -m pure)",
    "canary: marks tests as SDK canary (run with -m canary)",
    "live: marks tests as requiring real credentials (run with -m live)",
]
```

### AC-7: Contract Coverage Report

Create `scripts/check_contract_coverage.py`:

```python
#!/usr/bin/env python3
"""
Check that every MUST clause in contracts/*.md has a corresponding test.
"""
import re
from pathlib import Path

def extract_must_clauses(contract_file: Path) -> list[str]:
    """Extract MUST clause anchors from a contract file."""
    text = contract_file.read_text()
    # Pattern: anchor IDs like error-hierarchy:AuthenticationError:MUST:1
    anchors = re.findall(r'(\w+(?:-\w+)*:\w+:MUST:\d+)', text)
    return anchors

def extract_test_anchors(test_file: Path) -> list[str]:
    """Extract anchor references from test docstrings."""
    text = test_file.read_text()
    anchors = re.findall(r'""".*?(\w+(?:-\w+)*:\w+:MUST:\d+(?:-\d+)?)', text, re.DOTALL)
    return anchors

# ... coverage calculation logic
```

## Files to Create

- `tests/test_contract_protocol.py`
- `tests/test_contract_deny_destroy.py`
- `tests/test_contract_errors.py`
- `tests/test_contract_events.py`
- `tests/test_contract_streaming.py`
- `scripts/check_contract_coverage.py`

## Files to Modify

- `pyproject.toml` (add pytest markers)

## Dependencies

- None (uses existing modules)

## Success Criteria

- Every MUST clause in contracts/*.md has a corresponding test
- `pytest -m contract` passes
- Architecture fitness test prevents SDK imports outside sdk_adapter/

## NOT IN SCOPE

- Config compliance tests for missing behaviors (retry, circuit breaker)
- Property-based testing
