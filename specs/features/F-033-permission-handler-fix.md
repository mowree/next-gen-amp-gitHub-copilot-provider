# F-033: Add on_permission_request Handler to Production Code

## Summary
Add `on_permission_request` handler to `CopilotClientWrapper` initialization to comply with SDK v0.1.33+ requirements.

## Status
- **Priority**: Critical (production will crash without this)
- **Layer**: Python mechanism
- **Status**: ⚠️ BLOCKED - Awaiting design discussion on handler approach

## Background
SDK v0.1.28+ REQUIRES `on_permission_request` handler in `create_session()`. The next-gen provider is missing this.

## Design Discussion Required

Three approaches identified by expert panel:

### Option A: Use `PermissionHandler.approve_all` (upstream pattern)
```python
from copilot.types import PermissionHandler
session_config["on_permission_request"] = PermissionHandler.approve_all
```
- ✅ Matches upstream implementation
- ❌ security-guardian: "HIGH RISK — violates Deny+Destroy"
- ❌ amplifier-expert: "Permission requests must be events, not executed"

### Option B: Use `create_deny_hook()` (deny-by-default)
```python
session_config["on_permission_request"] = create_deny_hook()
```
- ✅ Aligns with Deny+Destroy pattern
- ✅ zen-architect: "Handler must be fixed deny-all like preToolUse hook"
- ⚠️ Need to verify `create_deny_hook()` signature is compatible

### Option C: Create new deny permission handler
```python
async def deny_permission_request(request: Any) -> dict:
    return {"permissionDecision": "deny", "permissionDecisionReason": "Amplifier sovereignty"}

session_config["on_permission_request"] = deny_permission_request
```
- ✅ Explicit deny semantics
- ✅ Clear sovereignty assertion
- ⚠️ More code to maintain

## Questions for Discussion

1. **Compatibility**: Does `create_deny_hook()` have the same signature as `on_permission_request` expects?
2. **Semantics**: Should permission requests be logged as events before denial?
3. **Contract**: Should `contracts/deny-destroy.md` be updated to cover permission requests?

## Acceptance Criteria (once approach decided)

- [ ] `on_permission_request` handler added to `client.py` auto-init path
- [ ] Handler denies all permission requests (per Deny+Destroy)
- [ ] Backward compatible with SDK <0.1.28 (try/except)
- [ ] `contracts/deny-destroy.md` updated if needed
- [ ] F-032 tests pass

## References
- security-guardian: "PermissionHandler.approve_all is NOT compatible with Deny+Destroy"
- amplifier-expert: "Permission requests MUST be captured as events and returned to orchestrator"
- integration-specialist: "Use try/except for backward compatibility"
