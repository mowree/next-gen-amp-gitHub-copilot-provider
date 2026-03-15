# F-078: Add context_window to Fallback Config

**Status:** ready
**Priority:** P1
**Source:** deep-review/core-expert.md

## Problem Statement
The provider-protocol.md contract specifies `defaults.context_window` as a **MUST** requirement for budget calculation. However, the fallback config at `provider.py` line 112 is missing `context_window`:
```python
defaults={"model": "gpt-4o", "max_tokens": 4096}  # MISSING context_window
```
If `models.yaml` fails to load, budget calculation fails because `context_window` is undefined.

Evidence:
- `provider.py` line 112: fallback config missing `context_window`
- `provider-protocol.md` requires `context_window` for budget calculation

## Success Criteria
- [ ] Fallback `ProviderInfo.defaults` includes `context_window: 128000`
- [ ] `models.yaml` has `context_window` defined for every model entry
- [ ] Budget calculation succeeds even when `models.yaml` fails to load
- [ ] Existing tests pass with the updated fallback defaults
- [ ] No new dependencies introduced

## Implementation Approach
1. Add `"context_window": 128000` to the fallback `defaults` dict in `provider.py`
2. Audit `models.yaml` to confirm every model entry includes `context_window`
3. Add any missing `context_window` values to `models.yaml` model entries

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (add `context_window` to fallback defaults)
- `config/models.yaml` (verify/add `context_window` for all models)

## TDD Anchor
- Red: Load fallback config (simulate `models.yaml` failure), access `defaults["context_window"]` → KeyError
- Green: Add `context_window: 128000` to fallback defaults → key exists with correct value
- Refactor: Ensure fallback defaults mirror all required keys from `provider-protocol.md`

## Contract Traceability
- `contracts/provider-protocol.md` — "MUST include `defaults.context_window` for budget calculation"

## Not In Scope
- Changing the fallback model name or `max_tokens` value
- Refactoring config loading logic (see F-051, F-053)
- Moving config into the wheel (see F-074)
