# F-068: Event Classification Overlap Validation

**Status:** ready
**Priority:** P2
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-011

## Problem Statement
`classify_event()` in `streaming.py:231-240` checks BRIDGE before CONSUME/DROP. If the same event type appears in both bridge mappings and consume patterns (YAML config error), BRIDGE wins silently. No validation in `load_event_config()` detects duplicate registrations across classification categories.

## Success Criteria
- [ ] `load_event_config()` validates no overlap between BRIDGE, CONSUME, and DROP categories
- [ ] Overlap raises `ConfigurationError` with details of the conflicting entry
- [ ] Test covers overlapping config detection

## Implementation Approach
1. After loading all categories, check for intersection between bridge keys, consume patterns, and drop patterns
2. Raise `ConfigurationError` if any event type appears in multiple categories

## Files to Modify
- `amplifier_module_provider_github_copilot/streaming.py` (`load_event_config()`)

## Tests Required
- Test: overlapping event type in bridge + consume → `ConfigurationError`
- Test: clean config loads without error (regression)

## Not In Scope
- Changing classification priority logic
- Adding new event types
