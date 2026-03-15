# F-091: Add Ephemeral Session Invariant Tests

**Status:** ready
**Priority:** P1 (HIGH)
**Source:** manual-review

## Problem Statement

The deny-destroy.md contract requires sessions to be ephemeral and distinct, but no tests verify this behavioral invariant.

## Evidence

- deny-destroy.md: "Each session MUST be ephemeral — no session reuse"
- Current tests verify structure (session_id is UUID, owns_client flag)
- No tests create 2 sessions and verify they're distinct entities

## Success Criteria

- [ ] `test_ephemeral_sessions.py` exists with session isolation tests
- [ ] Test verifies two sessions have distinct IDs
- [ ] Test verifies session state is not shared between sessions
- [ ] Test verifies no session reuse occurs
- [ ] All existing tests continue to pass
- [ ] Type checker (pyright) passes without new errors

## Implementation Approach

Create `tests/test_ephemeral_sessions.py`:

```python
@pytest.mark.asyncio
async def test_sessions_are_distinct():
    """Verify deny-destroy.md ephemeral invariant."""
    async with provider.session(...) as session1:
        id1 = session1.session_id
    async with provider.session(...) as session2:
        id2 = session2.session_id
    
    assert id1 != id2, "Sessions must have distinct IDs"
    # Also verify internal state is not shared

@pytest.mark.asyncio  
async def test_session_state_isolated():
    """Verify session 2 doesn't see session 1's state."""
    # Set state in session 1
    # Verify session 2 doesn't see it
    pass
```

## Files to Modify

- `tests/test_ephemeral_sessions.py` (create)

## Contract Traceability

- **deny-destroy.md** — "Each session MUST be ephemeral — no session reuse"

## Tests Required

- Two sessions produce distinct session IDs
- Session internal state is isolated (no cross-session leakage)
- Session resources are not reused across sessions

## Not In Scope

- Implementing session isolation logic (that's a separate feature if missing)
- Concurrent session stress testing
- Session persistence or serialization

## 7. Test Strategy (TDD)

Write tests BEFORE implementation:

| Test | Type | What it verifies | Contract Anchor |
|------|------|------------------|-----------------|
| `test_happy_path` | Unit | Primary behavior | `<contract>:<Section>:MUST:N` |
| `test_error_case` | Unit | Error handling | `<contract>:<Section>:MUST:N` |
| `test_edge_case` | Unit | Boundary conditions | `<contract>:<Section>:SHOULD:N` |

**Test file:** `tests/test_<module_name>.py`

Tests MUST:
- Reference contract clause in docstring
- Use `ConfigCapturingMock` for SDK boundary tests
- Fail before implementation (Red phase)
