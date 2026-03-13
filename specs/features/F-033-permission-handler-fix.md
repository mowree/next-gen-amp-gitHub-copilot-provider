# F-033: Add on_permission_request Handler to Production Code

## Summary
Add `on_permission_request` handler to `CopilotClientWrapper` initialization to comply with SDK v0.1.33+ requirements.

## Status
- **Priority**: Critical (production will crash without this)
- **Layer**: Python mechanism
- **Status**: ✅ APPROVED - Deny-by-default approach

## Background
SDK v0.1.28+ REQUIRES `on_permission_request` handler in `create_session()`. The next-gen provider is missing this.

## Approved Design: Deny-by-Default

**Rationale (from expert panel + human review):**
1. Tool capture happens via **streaming events** (ASSISTANT_MESSAGE), not hooks
2. Hooks are for **blocking**, not learning — we already have tool info when hooks fire
3. Denying at permission layer is semantically correct + future-proofs against new SDK operations
4. Defense-in-depth: deny at permission layer + deny at preToolUse + session destroy

## Implementation

### 1. Add deny_permission_request function to client.py

```python
from copilot.types import PermissionRequest, PermissionRequestResult

def deny_permission_request(
    request: PermissionRequest, 
    invocation: dict[str, str]
) -> PermissionRequestResult:
    """
    Deny all permission requests at source.
    
    The SDK asks: "May I do X?"
    Amplifier's answer: "No. Return the request to Amplifier's orchestrator."
    
    Tool capture happens via streaming events (ASSISTANT_MESSAGE), not hooks.
    This is the FIRST line of defense. preToolUse deny hook is the second.
    """
    return PermissionRequestResult(
        kind="denied-by-rules",
        message="Amplifier orchestrator controls all operations"
    )
```

### 2. Add to CopilotClient options (with backward compatibility)

```python
# In client.py, when building options dict:
try:
    from copilot.types import PermissionRequest, PermissionRequestResult
    options["on_permission_request"] = deny_permission_request
    logger.debug("[CLIENT] Permission handler set to deny_permission_request")
except (ImportError, AttributeError):
    # SDK < 0.1.28 doesn't require this
    logger.debug("[CLIENT] PermissionHandler not available; using SDK default")
```

### 3. Update contracts/deny-destroy.md

Add new MUST clause:
```markdown
## Permission Requests

MUST: Register `on_permission_request` handler that denies all requests
MUST: Return `PermissionRequestResult(kind="denied-by-rules")` for all permission requests
MUST NOT: Use `PermissionHandler.approve_all` or any approval-returning handler
RATIONALE: Permission requests are the SDK asking "may I execute?" — the answer is always "no, Amplifier decides."
```

## Acceptance Criteria

- [ ] `on_permission_request` handler added to `client.py` auto-init path
- [ ] Handler denies all permission requests (per Deny+Destroy)
- [ ] Backward compatible with SDK <0.1.28 (try/except)
- [ ] `contracts/deny-destroy.md` updated if needed
- [ ] F-032 tests pass

## References
- security-guardian: "PermissionHandler.approve_all is NOT compatible with Deny+Destroy"
- amplifier-expert: "Permission requests MUST be captured as events and returned to orchestrator"
- integration-specialist: "Use try/except for backward compatibility"
