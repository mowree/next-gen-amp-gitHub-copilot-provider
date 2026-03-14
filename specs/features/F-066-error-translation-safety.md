# F-066: Error Translation Safety Improvements

**Status:** ready
**Priority:** P2
**Source:** deep-review/bug-hunter.md, deep-review/security-guardian.md
**Defect ID:** DEF-010, DEF-014

## Problem Statement
Two error translation issues:
1. **DEF-010**: `_matches_mapping()` uses substring matching (`pattern in exc_type_name`). Pattern `"Error"` matches every exception. Pattern `"TimeoutError"` matches `"LLMTimeoutError"`. Future SDK exceptions could cause incorrect broad matching.
2. **DEF-014**: Only `InvalidToolCallError` is special-cased for constructor signature. Other kernel error classes that don't accept `retry_after` (e.g., `AbortError`) would cause `TypeError` at runtime.

Additionally, raw exception messages are logged without sanitization (security-guardian Finding #5), risking token/path leakage in logs.

## Success Criteria
- [ ] Pattern matching uses exact type name match (or documented prefix/suffix strategy)
- [ ] Negative matching tests added (e.g., `AuthenticationError` doesn't match `NetworkAuthenticationError`)
- [ ] Kernel error construction handles varying constructor signatures safely
- [ ] Exception messages are sanitized before logging

## Implementation Approach
1. Change `pattern in exc_type_name` to exact match or ends-with match
2. Add try/except around kernel error construction to handle `TypeError` from unexpected signatures
3. Add log sanitization for exception messages (strip potential token patterns)

## Files to Modify
- `amplifier_module_provider_github_copilot/error_translation.py` (lines 235-237, 336-350)
- `amplifier_module_provider_github_copilot/__init__.py` (log sanitization)

## Tests Required
- Test: exact type matching (no false positives)
- Test: kernel error with non-standard constructor doesn't crash
- Test: negative matching assertions

## Not In Scope
- Adding new error mappings (see F-061)
- Changing error translation algorithm
