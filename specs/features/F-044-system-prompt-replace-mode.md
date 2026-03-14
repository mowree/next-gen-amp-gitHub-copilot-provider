# F-044: System Prompt Replace Mode

**Status**: ready
**Priority**: high
**Type**: bugfix
**Estimated Effort**: small (1 file change + tests)

---

## Problem Statement

When users start an Amplifier session with the GitHub Copilot provider, the model identifies itself as "GitHub Copilot CLI" instead of following the Amplifier bundle persona.

**User report:**
```
> who are you?

Amplifier:
I'm GitHub Copilot CLI, a terminal assistant built by GitHub...
```

**Expected behavior:**
The model should identify according to the Amplifier bundle's instructions, not the SDK's default persona.

---

## Root Cause Analysis

**Expert panel investigation (amplifier-expert, integration-specialist, foundation:explorer):**

1. The GitHub Copilot SDK server injects its own system message ("You are GitHub Copilot CLI...")
2. Current provider uses `mode: "append"` in `sdk_adapter/client.py` line 221:
   ```python
   session_config["system_message"] = {"mode": "append", "content": system_message}
   ```
3. This appends Amplifier's instructions AFTER the SDK's default prompt
4. The model prioritizes the first (server) prompt for identity

**SDK supports two modes:**
| Mode | Behavior |
|------|----------|
| `append` | Adds content after SDK default; agent retains "GitHub Copilot CLI" identity |
| `replace` | Full override; Amplifier controls agent identity |

---

## Solution

Change from `append` to `replace` mode.

### Files to Modify

**`amplifier_module_provider_github_copilot/sdk_adapter/client.py`** (line ~221):

```python
# BEFORE
if system_message:
    session_config["system_message"] = {"mode": "append", "content": system_message}

# AFTER
if system_message:
    # F-044: Use replace mode to ensure Amplifier bundle persona takes precedence
    # The SDK's default "GitHub Copilot CLI" prompt interferes with bundle instructions.
    # Replace mode gives full control over agent identity.
    # Security: Deny hooks (F-033) remain active at client & session level.
    session_config["system_message"] = {"mode": "replace", "content": system_message}
```

---

## Safety Analysis

| Concern | Status | Rationale |
|---------|--------|-----------|
| Tool execution control | ✅ Safe | Deny hooks (F-033) are independent of system_message mode |
| Session ephemerality | ✅ Safe | Unchanged by this fix |
| Security boundary | ⚠️ Shifts | Moves to Amplifier bundle instructions (expected) |

**Key insight:** The `deny_permission_request` hooks operate at client and session level, not at system_message level. Tool execution control is preserved regardless of system_message mode.

---

## Acceptance Criteria

1. **Identity test**: After fix, `amplifier run` + "who are you?" returns bundle identity, NOT "GitHub Copilot CLI"
2. **Deny hooks still work**: Tool execution requests are still blocked/approved per deny hooks
3. **Existing tests pass**: No regressions in test suite
4. **Documentation updated**: Comment in code explains the mode choice

---

## Test Cases

### New Test: System Prompt Mode

```python
# tests/test_system_prompt_mode.py

import pytest
from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

@pytest.mark.asyncio
async def test_system_message_uses_replace_mode():
    """F-044: System message should use replace mode, not append."""
    # Capture the session config that would be sent to SDK
    captured_config = None
    
    async def mock_create_session(config):
        nonlocal captured_config
        captured_config = config
        # Return mock session
        return MockSession()
    
    client = CopilotClientWrapper()
    # ... setup mock SDK ...
    
    async with client.session(
        model="gpt-4o",
        system_message="You are the Amplifier assistant."
    ) as session:
        pass
    
    assert captured_config is not None
    assert captured_config["system_message"]["mode"] == "replace"
    assert captured_config["system_message"]["content"] == "You are the Amplifier assistant."


@pytest.mark.asyncio
async def test_deny_hooks_still_active_with_replace_mode():
    """F-044: Deny hooks should remain active regardless of system_message mode."""
    # Verify deny_permission_request is still configured
    # This test ensures F-033 compatibility
    pass
```

---

## Implementation Steps

1. **RED**: Write failing test `test_system_message_uses_replace_mode`
2. **GREEN**: Change line 221 in `client.py` from `"append"` to `"replace"`
3. **REFACTOR**: Add explanatory comment
4. **VERIFY**: Run full test suite
5. **DOCUMENT**: Update contract or add to release notes

---

## Not In Scope

- Configurable mode selection (always use replace)
- Custom agents feature integration
- Renaming `system_prompt` to `system_message` in domain types

---

## References

- Expert investigation: Session with amplifier-expert, integration-specialist, foundation:explorer
- SDK documentation: `reference-only/copilot-sdk/test/scenarios/prompts/system-message/README.md`
- Deny hooks implementation: F-033 in `client.py`
- Provider protocol: `contracts/provider-protocol.md`

---

*Created: 2026-03-14*
*Author: Copilot (via expert panel investigation)*
