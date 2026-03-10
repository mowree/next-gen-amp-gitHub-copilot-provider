# F-016: End-to-End Integration Tests

## 1. Overview

**Module:** tests/
**Priority:** P0
**Depends on:** F-015-completion-wiring

Full end-to-end tests against real Copilot SDK with auth token.

## 2. Requirements

### Test Structure

```python
# tests/test_e2e_integration.py
import pytest
import os

# Skip all tests if no token
pytestmark = pytest.mark.skipif(
    not os.environ.get("COPILOT_AGENT_TOKEN"),
    reason="COPILOT_AGENT_TOKEN required for E2E tests"
)

class TestE2EIntegration:
    """End-to-end tests against real Copilot SDK."""
    
    @pytest.mark.asyncio
    async def test_simple_completion(self):
        """Test basic text completion without tools."""
        ...
    
    @pytest.mark.asyncio
    async def test_completion_with_tools(self):
        """Test completion that returns tool calls."""
        ...
    
    @pytest.mark.asyncio
    async def test_deny_hook_prevents_execution(self):
        """Verify deny hook blocks tool execution."""
        ...
    
    @pytest.mark.asyncio
    async def test_session_destroyed_after_completion(self):
        """Verify session is destroyed after use."""
        ...
    
    @pytest.mark.asyncio
    async def test_error_translation(self):
        """Test SDK errors become kernel errors."""
        ...
```

### Test Scenarios

| Scenario | What It Tests |
|----------|---------------|
| Simple completion | Basic flow works end-to-end |
| Tool call capture | Tools returned correctly |
| Deny hook | No SDK tool execution happens |
| Session cleanup | No resource leaks |
| Auth error | Proper error when no/bad token |

### Environment

- Requires `COPILOT_AGENT_TOKEN` environment variable
- Tests skipped automatically if not set
- Use `pytest -m e2e` to run E2E tests specifically

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | Tests skip gracefully without token | Run without token |
| AC-2 | Simple completion returns text | Run with token |
| AC-3 | Tool calls captured correctly | Run with token |
| AC-4 | No SDK tool execution (deny works) | Run with token |
| AC-5 | All kernel error types tested | Unit + E2E |

## 4. Test Fixtures

```python
@pytest.fixture
async def provider():
    """Get configured provider instance."""
    from amplifier_module_provider_github_copilot import GitHubCopilotProvider
    return GitHubCopilotProvider()

@pytest.fixture
def simple_request():
    """Simple completion request."""
    from amplifier_module_provider_github_copilot.provider import ChatRequest
    return ChatRequest(
        messages=[{"role": "user", "content": "Say hello"}],
        model="gpt-4",
    )
```

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `tests/test_e2e_integration.py` | Create | E2E test suite |
| `tests/conftest.py` | Modify | Add E2E fixtures |
| `pyproject.toml` | Modify | Add `e2e` pytest marker |

## 6. Running E2E Tests

```bash
# Set token
export COPILOT_AGENT_TOKEN="your_token_here"

# Run all tests including E2E
uv run pytest tests/ -v

# Run only E2E tests
uv run pytest tests/ -v -m e2e
```
