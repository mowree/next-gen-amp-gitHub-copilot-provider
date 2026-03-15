# F-081: Fix context_extraction Missing in client.py Error Loading

**Status:** ready
**Priority:** P0
**Source:** manual investigation

## Problem Statement
`client.py`'s `_load_error_config_once()` constructs `ErrorMapping` objects WITHOUT the `context_extraction` field that F-036 added. The parallel loader in `error_translation.py` correctly parses `context_extraction` from config, but the `client.py` loader omits it entirely.

Evidence:
- `client.py` lines 88-96: `ErrorMapping(sdk_patterns=..., string_patterns=..., kernel_error=..., retryable=..., extract_retry_after=...)` — no `context_extraction`
- `error_translation.py` lines 171-182: correctly parses `context_extraction` list and passes to `ErrorMapping(..., context_extraction=context_extraction)`

When installed from wheel (where `importlib.resources` succeeds and uses the `client.py` code path), F-036 context extraction is silently lost. Error messages won't include extracted context like rate limit retry-after values.

Contract violated: F-036 feature spec — config-driven context extraction should work regardless of which code path loads the config.

Root cause: Duplicate config loading code. When F-036 added `context_extraction` to `error_translation.py`, it wasn't added to the duplicate loader in `client.py`.

## Success Criteria
- [ ] `client.py`'s `_load_error_config_once()` parses `context_extraction` from config YAML
- [ ] `ErrorMapping` objects created in `client.py` include `context_extraction` field
- [ ] Parsing logic matches `error_translation.py` implementation (creates `ContextExtraction` objects)
- [ ] Existing tests pass
- [ ] Both code paths produce identical `ErrorMapping` objects for the same config input

## Implementation Approach
1. Add `context_extraction` parsing to `client.py`'s error config loading loop, matching the pattern in `error_translation.py`
2. Import `ContextExtraction` in `client.py` if not already imported
3. Parse `mapping_data.get("context_extraction", [])` and construct `ContextExtraction` objects
4. Pass `context_extraction=context_extraction` to `ErrorMapping()` constructor

## Files to Modify
- `amplifier_module_provider_github_copilot/client.py` (add context_extraction parsing to `_load_error_config_once()`)

## TDD Anchor
- Red: Load error config via `client.py` path, assert `context_extraction` is populated → fails (empty list)
- Green: Add `context_extraction` parsing to `client.py` → passes
- Refactor: Consider unifying the two loaders (see F-053)

## Contract Traceability
- F-036 spec — context extraction must work regardless of loading path
- `contracts/error-hierarchy.md` — error translation must be complete

## Relationship to Other Features
- **F-053** (Unify Error Config Loading): F-081 is the immediate P0 fix; F-053 is the structural fix that eliminates the duplication root cause
- **F-036** (Error Context Enhancement): F-081 restores F-036 functionality on the client.py code path
- **F-074** (Config Not in Wheel): F-074 fixes config availability; F-081 fixes config parsing completeness

## Not In Scope
- Unifying the two config loaders (that's F-053)
- Changing config file format or content
- Adding new context extraction rules
