# F-092: Update Default Model to claude-opus-4.5

## 1. Overview

**Module:** provider
**Priority:** P1
**Depends on:** F-078-add-context-window-to-fallback-config

Update the fallback provider configuration to use `claude-opus-4.5` as the default model,
with context window and token limits matching the real SDK model catalog. This ensures
the provider uses a modern, capable model by default and has correct budget calculations.

## 2. Requirements

### Interfaces

```python
# No new interfaces. Modifies existing fallback defaults in provider.py
def _default_provider_config() -> ProviderConfig:
    return ProviderConfig(
        provider_id="github-copilot",
        display_name="GitHub Copilot SDK",
        credential_env_vars=["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
        capabilities=["streaming", "tool_use"],
        defaults={
            "model": "claude-opus-4.5",        # CHANGED from gpt-4o
            "max_tokens": 168000,              # CHANGED from 4096
            "context_window": 200000,          # ADDED (F-078 requirement)
        },
        models=[],
    )
```

### Behavior

- Fallback config MUST use `claude-opus-4.5` as default model
- Fallback config MUST set `max_tokens: 168000` (SDK: max_prompt_tokens)
- Fallback config MUST set `context_window: 200000` (SDK: max_context_window_tokens)
- config/models.yaml MUST include `claude-opus-4.5` with matching values
- Budget calculation MUST work with fallback config (per provider-protocol.md)

## 3. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC-1 | `_default_provider_config().defaults["model"]` returns `"claude-opus-4.5"` | Unit test |
| AC-2 | `_default_provider_config().defaults["max_tokens"]` returns `168000` | Unit test |
| AC-3 | `_default_provider_config().defaults["context_window"]` returns `200000` | Unit test |
| AC-4 | models.yaml contains claude-opus-4.5 with context_window: 200000 | Unit test |
| AC-5 | All existing tests pass with new defaults | pytest |

## 4. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| models.yaml fails to load | Fallback defaults provide correct claude-opus-4.5 values |
| Session created without explicit model | Uses claude-opus-4.5 |
| Budget calculation with fallback | Works (context_window present) |

## 5. Files to Create/Modify

| File | Action | Contents |
|------|--------|----------|
| `amplifier_module_provider_github_copilot/provider.py` | Modify | Update `_default_provider_config()` defaults dict |
| `config/models.yaml` | Modify | Add claude-opus-4.5 model entry if missing |
| `amplifier_module_provider_github_copilot/config/models.yaml` | Modify | Add claude-opus-4.5 model entry if missing |
| `tests/test_config_loading.py` | Modify | Update expected default model assertions |

## 6. Dependencies

- No new dependencies

## 7. Test Strategy (TDD)

Write these tests BEFORE implementation:

| Test | Type | What it verifies | Contract Anchor |
|------|------|------------------|-----------------|
| `test_default_model_is_claude_opus_45` | Unit | defaults["model"] == "claude-opus-4.5" | `provider-protocol:get_info:MUST:1` |
| `test_default_max_tokens_matches_sdk` | Unit | defaults["max_tokens"] == 168000 | `provider-protocol:get_info:MUST:1` |
| `test_default_context_window_matches_sdk` | Unit | defaults["context_window"] == 200000 | `provider-protocol:get_info:MUST:2` |
| `test_fallback_config_budget_calculation` | Unit | Budget calc works with fallback | `provider-protocol:get_info:MUST:2` |

**Contract anchor format:** `provider-protocol:get_info:MUST:2`

Tests MUST:
- Reference a contract clause in docstring (prevents F-044 regression)
- Use realistic fixtures from `tests/fixtures/`
- Verify SDK-documented values (200000 context, 168000 max_tokens)

## 8. Notes

**SDK Source (2026-03-15):**
```
claude-opus-4.5:
  context_window: 200,000
  max_output_tokens: 168,000
  billing_multiplier: 3.0
  vision: Yes
  policy: enabled
```

This feature supersedes the legacy `gpt-4o` default which does not exist in the SDK.
See `mydocs/Py-sdk-list-models.md` for the full SDK model catalog baseline.
