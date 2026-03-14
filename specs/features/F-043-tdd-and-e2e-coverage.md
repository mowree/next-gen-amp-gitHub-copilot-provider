# F-043: TDD Discipline and E2E Coverage Gaps

## Context

During shadow testing, a critical bug was discovered: the provider returns raw `Data` dataclass objects instead of extracting `.content`. This bug survived 42 feature implementations because:

1. **No E2E tests with real SDK responses** — All tests use MagicMock() that return simple strings
2. **Specs didn't specify response extraction** — Contract says "return ChatResponse" but not HOW to extract from SDK response
3. **TDD was not enforced** — Tests were written to pass, not to verify behavior

## Root Cause Analysis

### Bug Location
```python
# provider.py line ~380
response_data = getattr(sdk_response, "data", sdk_response)
if isinstance(response_data, dict):
    content = response_data.get("content", "")
else:
    content = str(response_data) if response_data else ""  # <-- BUG: str(Data(...))
```

The SDK returns a `Data` dataclass with `.content` attribute, not a dict. The code falls through to `str()` which produces the repr dump.

### Why Tests Didn't Catch This
- `MagicMock()` returns strings, not `Data` objects
- No integration test with actual SDK response shapes
- Specs don't define SDK response structure

## Acceptance Criteria

### AC-1: Fix SDK Response Extraction
- [ ] Add `hasattr(response_data, 'content')` check before dict check
- [ ] Extract `response_data.content` for Data objects
- [ ] Add test with realistic SDK response shape

### AC-2: Add E2E Test with Real SDK Response Shapes
- [ ] Create test fixture matching actual `copilot.generated.session_events.Data` structure
- [ ] Test complete flow: `complete()` → accumulate → `ChatResponse`
- [ ] Verify content is plain text, not repr dump

### AC-3: Update Specs with SDK Response Contract
- [ ] Add `contracts/sdk-response.md` documenting expected SDK response shapes
- [ ] Update `streaming-contract.md` with extraction requirements
- [ ] Add MUST constraint: "MUST extract .content from Data objects"

### AC-4: Strengthen Test Fixtures
- [ ] Replace `MagicMock()` returns with realistic data structures
- [ ] Add `tests/fixtures/sdk_responses.py` with typed fixtures
- [ ] Document fixture shapes match SDK version 0.1.32+

### AC-5: Add TDD Enforcement Checklist to Working Session Protocol
- [ ] Update `.dev-machine/working-session-instructions.md`
- [ ] Add pre-implementation checklist: "Does test use realistic data shapes?"
- [ ] Add RED phase requirement: "Test must fail for the RIGHT reason"

## Implementation Order

1. **Fix the bug first** (AC-1) — unblocks shadow testing
2. **Add E2E test** (AC-2) — proves fix works
3. **Document in contracts** (AC-3) — prevents recurrence
4. **Improve fixtures** (AC-4) — systematic hardening
5. **Update protocol** (AC-5) — process improvement

## Files to Modify

| File | Change |
|------|--------|
| `amplifier_module_provider_github_copilot/provider.py` | Fix response extraction |
| `tests/test_completion.py` | Add E2E test with real shapes |
| `tests/fixtures/sdk_responses.py` | New file: typed fixtures |
| `contracts/sdk-response.md` | New file: SDK response contract |
| `contracts/streaming-contract.md` | Add extraction requirements |
| `.dev-machine/working-session-instructions.md` | Add TDD checklist |

## Success Criteria

- Shadow test completes with actual text response (not repr dump)
- All tests pass with realistic fixtures
- New contract documents SDK response shapes
- Protocol updated to prevent similar gaps
