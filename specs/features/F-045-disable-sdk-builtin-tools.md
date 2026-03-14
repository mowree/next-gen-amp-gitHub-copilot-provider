# F-045: Disable SDK Built-in Tools

**Status**: ready
**Priority**: critical
**Type**: bugfix
**Estimated Effort**: small (1 line change + tests)

---

## Problem Statement

All tools fail with `TypeError: Cannot read properties of undefined (reading 'map')` — a JavaScript error occurring in the Copilot CLI (Node.js), not Python.

**User experience:**
```
> what is in this directory.. list them

Amplifier:
It seems my tools are currently experiencing errors and I'm unable to execute 
any commands or list files. This appears to be a session/runtime issue...
```

**Copilot CLI logs show:**
```json
{
  "tool_name": "bash",
  "tool_call_id": "tooluse_CmonBRrvCYekOvepeawB8U",
  "result_type": "FAILURE",
  "duration_ms": 9,
  "is_mcp_tool": "false"
}
```

The 9ms duration confirms the CLI crashes before executing the tool.

---

## Root Cause Analysis

**Expert panel investigation (amplifier-expert, bug-hunter, integration-specialist, explorer):**

### Architecture Diagram
```
┌─────────────────┐
│   LLM (Claude)  │  ← Sees SDK's built-in tools: bash, view, edit, etc.
└────────┬────────┘
         │ calls "bash" tool (SDK's, not Amplifier's)
         ▼
┌─────────────────────────────┐
│  Copilot SDK (Python)       │
│  - Creates session          │
│  - Forwards tool call       │
└────────┬────────────────────┘
         │ RPC
         ▼
┌─────────────────────────────┐
│  Copilot CLI (Node.js)      │  ← JavaScript runtime
│  - server mode              │
│  - Executes bash tool       │  ← CRASHES HERE with JS error
│  - Returns error to SDK     │
└────────┬────────────────────┘
         │
         ▼
   "TypeError: Cannot read properties
    of undefined (reading 'map')"
```

### Why Current Deny Hooks Don't Help

| Hook | What It Does | Why It Doesn't Help |
|------|--------------|---------------------|
| `deny_permission_request` | Blocks permission REQUESTS | SDK tools don't need separate permission |
| `pre_tool_use_hook` | Runs BEFORE execution | JS error happens DURING execution inside CLI |

### The Real Problem

The provider does NOT disable SDK built-in tools. From `sdk_adapter/client.py`:
```python
session_config: dict[str, Any] = {}
if model:
    session_config["model"] = model
if system_message:
    session_config["system_message"] = {"mode": "append", "content": system_message}
session_config["streaming"] = streaming
# NO available_tools setting here!
```

---

## Solution

The SDK supports tool control via `SessionConfig` (from `copilot/types.py` lines 492-495):
```python
class SessionConfig(TypedDict, total=False):
    # List of tool names to allow (takes precedence over excluded_tools)
    available_tools: list[str]
    # List of tool names to disable (ignored if available_tools is set)
    excluded_tools: list[str]
```

### Files to Modify

**`amplifier_module_provider_github_copilot/sdk_adapter/client.py`** (line ~217):

```python
# BEFORE
session_config: dict[str, Any] = {}
if model:
    session_config["model"] = model

# AFTER
session_config: dict[str, Any] = {}
# F-045: Disable ALL SDK/CLI built-in tools.
# The LLM should only see Amplifier tools passed in completion request.
# Without this, SDK exposes bash/view/edit/etc. which crash in CLI.
session_config["available_tools"] = []
if model:
    session_config["model"] = model
```

---

## Why This Works

1. **`available_tools: []`** tells CLI "no built-in tools available"
2. The check in SDK (`client.py` lines 527-532) is `is not None`:
   ```python
   available_tools = cfg.get("available_tools")
   if available_tools is not None:
       payload["availableTools"] = available_tools
   ```
3. Empty list sends `availableTools: []` to CLI
4. CLI won't expose bash/view/edit/etc. to the LLM
5. LLM only sees Amplifier tools → Amplifier orchestrator handles them

---

## Safety Analysis

| Concern | Status | Rationale |
|---------|--------|-----------|
| Tool sovereignty | ✅ Restored | Only Amplifier tools visible to LLM |
| Deny hooks | ✅ Still active | Defense in depth at permission layer |
| Session lifecycle | ✅ Unchanged | Ephemeral pattern preserved |
| Existing tests | ✅ Should pass | Tests use mocks, not real CLI |

---

## Acceptance Criteria

1. **Tool error gone**: After fix, tools work without JS errors
2. **Amplifier tools work**: bash, read_file, write_file function correctly
3. **SDK tools invisible**: LLM cannot call SDK's built-in bash/view/edit
4. **Existing tests pass**: No regressions in test suite
5. **Integration test**: Live test with real SDK confirms fix

---

## Test Cases

### New Test: SDK Tool Visibility

```python
# tests/test_f045_sdk_tool_config.py

import pytest
from amplifier_module_provider_github_copilot.sdk_adapter.client import CopilotClientWrapper

@pytest.mark.asyncio
async def test_session_config_disables_builtin_tools():
    """F-045: Session config should set available_tools to empty list."""
    captured_config = None
    
    # Mock the SDK to capture session config
    original_create = CopilotClientWrapper._create_session
    
    async def capture_create(self, config):
        nonlocal captured_config
        captured_config = config
        return await original_create(self, config)
    
    CopilotClientWrapper._create_session = capture_create
    
    try:
        wrapper = CopilotClientWrapper()
        async with wrapper.session(model="gpt-4o") as session:
            pass
        
        assert captured_config is not None
        assert "available_tools" in captured_config
        assert captured_config["available_tools"] == []
    finally:
        CopilotClientWrapper._create_session = original_create


@pytest.mark.asyncio
async def test_amplifier_tools_still_work():
    """F-045: Amplifier tools should work after disabling SDK tools."""
    # This test verifies that disabling SDK tools doesn't break Amplifier tools
    # Mock SDK session to return success
    pass  # Implementation depends on test infrastructure
```

---

## Implementation Steps

1. **RED**: Write failing test `test_session_config_disables_builtin_tools`
2. **GREEN**: Add `session_config["available_tools"] = []` to client.py
3. **REFACTOR**: Add explanatory comment
4. **VERIFY**: Run full test suite
5. **INTEGRATION**: Test with real SDK in WSL environment

---

## Not In Scope

- Configurable tool whitelist (always use empty list)
- MCP server tool configuration
- Custom tool registration via SDK

---

## References

- Expert investigation: amplifier-expert, bug-hunter, integration-specialist, explorer
- SDK source: `copilot/types.py` lines 492-495, `client.py` lines 527-532
- Copilot CLI logs: `~/.copilot/logs/`
- Current deny hooks: F-033 in `client.py`
- Provider protocol: `contracts/provider-protocol.md`

---

## Relationship to Other Features

| Feature | Relationship |
|---------|--------------|
| F-033 (Deny Hooks) | Complementary - F-045 prevents exposure, F-033 denies permission |
| F-044 (System Prompt) | Independent - both improve SDK integration |
| F-043 (SDK Response) | Independent - different SDK aspects |

---

*Created: 2026-03-14*
*Author: Expert panel synthesis (amplifier-expert, bug-hunter, integration-specialist, explorer)*
