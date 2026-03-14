# Contract: Deny + Destroy Pattern

## Version
- **Current:** 1.0
- **Module Reference:** modules/provider-core/session_factory.py
- **Status:** Non-Negotiable Constraint

---

## Overview

The Deny + Destroy pattern is the provider's defining commitment to Amplifier's sovereignty. It ensures that the Copilot SDK never executes tools — only Amplifier's orchestrator does.

This prevents the "Two Orchestrators" problem: the SDK has its own agent loop, Amplifier has its own orchestrator. If the provider allows the SDK to execute tools, it creates a hidden second brain that conflicts with Amplifier's control.

---

## Non-Negotiable Constraints

These constraints are extracted from GOLDEN_VISION_V2.md and are **NEVER configurable**:

### 1. preToolUse Deny Hook
- **MUST:** Install a `preToolUse` deny hook on every SDK session
- **MUST:** The hook returns `DENY` for all tool execution requests
- **MUST NOT:** Allow any configuration to disable this hook
- **MUST NOT:** Have any code path that skips hook installation

### 2. Session Ephemerality
- **MUST:** Create a new session for each `complete()` call
- **MUST:** Destroy the session immediately after the first turn completes
- **MUST NOT:** Reuse sessions across `complete()` calls
- **MUST NOT:** Accumulate state in sessions

### 3. No SDK Tool Execution
- **MUST:** Capture tool requests from SDK events (ASSISTANT_MESSAGE)
- **MUST:** Return tool requests to Amplifier's orchestrator
- **MUST NOT:** Allow the SDK's internal agent loop to execute tools
- **MUST NOT:** Allow the SDK to retry after tool denial

### 4. SDK Built-in Tool Suppression (F-045)

The SDK exposes built-in tools (bash, view, edit, etc.) to the LLM by default.
These tools crash the Copilot CLI when called because they are handled by
Node.js runtime code that expects a different calling convention.

- **MUST:** Set `available_tools: []` in every session config
- **MUST NOT:** Allow any SDK built-in tools to be visible to the LLM

This is the THIRD line of defense in the Deny+Destroy pattern:
1. **on_permission_request** → deny all permission requests (first barrier)
2. **preToolUse hook** → deny all tool execution (second barrier)
3. **available_tools=[]** → prevent SDK tools from being offered to LLM at all (prevention)

---

## Architectural Rationale

From GOLDEN_VISION_V2.md:

> The provider's job is translation — converting between the Amplifier protocol and the Copilot SDK. Every design decision must answer: "Does this add translation capability or framework complexity?" If the latter, remove it.
>
> The provider does not manage retry logic (kernel policy), context windows (orchestrator concern), tool execution (always denied), or model selection preferences (consumer policy). It translates requests into SDK sessions, SDK events into domain events, and SDK errors into domain exceptions.

---

## Behavioral Requirements

### Session Creation
- **Precondition:** `complete()` called with ChatRequest
- **Postcondition:** Fresh SDK session created with deny hook installed
- **Invariant:** No session exists before `complete()` or after it returns

### Tool Denial
- **Precondition:** SDK emits tool execution request
- **Postcondition:** Request is denied, tool calls captured for return
- **Invariant:** No tool ever executes inside the SDK

### Session Destruction
- **Precondition:** First turn complete (text or tool calls received)
- **Postcondition:** Session destroyed, resources released
- **Invariant:** Session lifetime is bounded to a single `complete()` call

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `deny-destroy:DenyHook:MUST:1` | preToolUse hook installed on every session |
| `deny-destroy:DenyHook:MUST:2` | Hook returns DENY for all tool requests |
| `deny-destroy:DenyHook:MUST:3` | No configuration disables the hook |
| `deny-destroy:Ephemeral:MUST:1` | New session per complete() call |
| `deny-destroy:Ephemeral:MUST:2` | Session destroyed after first turn |
| `deny-destroy:Ephemeral:MUST:3` | No session reuse |
| `deny-destroy:NoExecution:MUST:1` | Tool requests captured from events |
| `deny-destroy:NoExecution:MUST:2` | Tool requests returned to orchestrator |
| `deny-destroy:NoExecution:MUST:3` | SDK never executes tools |
| `deny-destroy:ToolSuppression:MUST:1` | available_tools=[] on every session |
| `deny-destroy:ToolSuppression:MUST:2` | SDK built-in tools never visible to LLM |

---

## Why This Is Never Configurable

From GOLDEN_VISION_V2.md Non-Negotiable Constraints:

> 6. **Deny + Destroy is NEVER configurable.** This is mechanism, not policy. No YAML knob. *(From Config-First Skeptic's warning about knob-creep)*

The pattern exists to preserve Amplifier's sovereignty over:
- Tool execution decisions
- Context management
- Session persistence
- Agent delegation

Any configuration that would allow the SDK to execute tools would break Amplifier's core value proposition.

---

## Implementation Notes

The deny hook must be installed using the SDK's `preToolUse` mechanism:

```python
# Pseudocode - actual implementation in session_factory.py
def make_deny_hook():
    def deny_all_tools(tool_request):
        return {"action": "DENY", "reason": "Amplifier orchestrator handles tools"}
    return deny_all_tools
```

Session destruction must use the SDK's proper cleanup mechanism to avoid resource leaks.

---

## References

- GOLDEN_VISION_V2.md § "The Deny + Destroy Pattern"
- GOLDEN_VISION_V2.md § "Non-Negotiable Constraints"
- contracts/provider-protocol.md (to be created)
- reference-only/amplifier-module-provider-github-copilot/tool_capture.py
