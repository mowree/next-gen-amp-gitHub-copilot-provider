# F-031: Add system.notification Event Classification

## Summary
Add `system.notification` event type to `config/events.yaml` to prevent "Unknown SDK event type" warnings.

## Status
- **Priority**: Medium
- **Layer**: YAML only (config-healable)
- **Expert Consensus**: 5/6 agents agree

## Background
SDK v0.1.33-preview.0 introduced `system.notification` events. Currently, these trigger warnings in streaming.py because they're not classified.

## Changes Required

### 1. Update config/events.yaml

Add to the `consume` section (per security-guardian: treat as sensitive-by-default):

```yaml
consume:
  - tool_use_start
  - tool_use_delta
  - session_created
  - session_destroyed
  - usage
  - system_notification  # NEW: SDK v0.1.33 - log internally, don't forward
```

### 2. No Code Changes Required

The `classify_event()` function in `streaming.py` already handles `consume` classification correctly.

## Acceptance Criteria

- [ ] `system.notification` is in `config/events.yaml` under `consume:`
- [ ] No "Unknown SDK event type: system.notification" warning in logs
- [ ] Test verifies `system.notification` is classified as CONSUME

## Test Anchor
`event-vocabulary:classification:system_notification:MUST:1`

## References
- SDK v0.1.33 release: https://github.com/github/copilot-sdk/releases/tag/v0.1.33-preview.0
- zen-architect assessment: "Pure Config (Tier 1)"
