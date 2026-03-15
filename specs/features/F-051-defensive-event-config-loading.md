# F-051: Defensive Event Config Loading

**Status:** ready
**Priority:** P0
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-002

## Problem Statement
`load_event_config()` in `streaming.py:211-212` uses unguarded dict access (`mapping["sdk_type"]`) and unguarded enum lookup (`DomainEventType[mapping["domain_type"]]`) for bridge mapping entries. A malformed `events.yaml` with a missing key or unrecognized domain type causes `KeyError` at startup — with a cryptic traceback, not a descriptive error. This contrasts with `load_error_config()` which uses `.get()` with defaults throughout.

## Success Criteria
- [ ] Bridge mapping entries with missing `sdk_type` produce a clear `ConfigurationError` (not `KeyError`)
- [ ] Bridge mapping entries with unrecognized `domain_type` produce a clear `ConfigurationError`
- [ ] Valid configurations continue to work identically
- [ ] Error messages include the offending entry for debugging
- [ ] Tests cover both malformed-key and unknown-enum-value cases

## Implementation Approach
1. Wrap bridge mapping parsing in try/except with descriptive error messages
2. Use `.get()` for key access with validation
3. Catch `KeyError` on `DomainEventType[...]` lookup and raise `ConfigurationError` with context
4. Follow the defensive pattern already established in `load_error_config()`

## Files to Modify
- `amplifier_module_provider_github_copilot/streaming.py` (lines 211-212)

## Tests Required
- `tests/test_event_config_loading.py` (new) or additions to `tests/test_streaming.py`:
  - Test: bridge entry missing `sdk_type` → `ConfigurationError` with message
  - Test: bridge entry with unknown `domain_type` → `ConfigurationError` with message
  - Test: valid config loads correctly (regression guard)

## Contract Traceability
- `contracts/event-vocabulary.md` — event config loading must produce valid domain event types

## Not In Scope
- Refactoring `load_event_config()` beyond defensive loading
- YAML schema validation
