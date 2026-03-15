# F-070: Clean Up Deferred Imports

**Status:** ready
**Priority:** P2
**Source:** deep-review/code-intel.md

## Problem Statement

`ProviderUnavailableError` and `LLMError` are imported inside functions at provider.py lines 250, 259, and 274 rather than at the top of the module. Code-intel analysis confirms there is no circular import risk — error_translation.py has NO imports from provider.py. These deferred imports add unnecessary indirection and deviate from Python conventions.

## Success Criteria

- [ ] `ProviderUnavailableError` and `LLMError` moved to top-level imports in provider.py
- [ ] All deferred (in-function) imports of these errors removed
- [ ] No circular import errors introduced
- [ ] Existing tests pass without modification

## Implementation Approach

1. Add top-level imports for `ProviderUnavailableError` and `LLMError` from error_translation module
2. Remove the in-function import statements at lines 250, 259, 274
3. Verify no circular import by running the module

## Files to Modify

- amplifier_module_provider_github_copilot/provider.py

## Tests Required

- Verify existing test suite passes after change
- Verify module imports cleanly (`python -c "import amplifier_module_provider_github_copilot.provider"`)

## Contract Traceability
- N/A — code quality cleanup, no contract implications

## Not In Scope

- Refactoring error_translation.py
- Changing error class hierarchy
- Other import cleanup beyond the identified deferred imports
