# F-087: Strengthen complete() Parameter Type from Any to ChatRequest

**Status:** ready
**Priority:** P2 (MEDIUM)
**Source:** manual-review

## Problem Statement

The `complete()` method in `provider.py` accepts `request: Any` instead of the contract-specified `ChatRequest` type, weakening type safety at the provider boundary.

## Evidence

Contract `provider-protocol.md` specifies:

```
complete(request: ChatRequest) -> ChatResponse
```

Actual code in `provider.py`:

```python
async def complete(self, request: Any, **kwargs) -> ChatResponse:
```

## Success Criteria

- [ ] `complete()` signature uses `ChatRequest` instead of `Any`
- [ ] `ChatRequest` is properly imported (from amplifier_core or local TypedDict/Protocol)
- [ ] All existing tests pass
- [ ] Type checker (pyright) passes without new errors

## Implementation Approach

Change the signature from:

```python
async def complete(self, request: Any, **kwargs) -> ChatResponse:
```

to:

```python
async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
```

This may require importing `ChatRequest` from `amplifier_core` or defining a local TypedDict/Protocol if the kernel type is not directly available.

## Files to Modify

- `amplifier_module_provider_github_copilot/provider.py` (change parameter type, add import)

## Contract Traceability

- **provider-protocol.md** — "complete MUST accept ChatRequest and return ChatResponse"

## Tests Required

- Verify existing tests pass with the stronger type annotation
- Verify pyright accepts the new signature without errors

## Not In Scope

- Runtime type validation or enforcement beyond the annotation
- Changes to callers of `complete()`
- Refactoring internal request handling logic

## 7. Test Strategy

N/A — cleanup/refactor feature, no behavioral tests required.

