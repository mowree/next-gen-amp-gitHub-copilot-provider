# Python Code Quality Review — 2026-03-14

**Project:** `amplifier-module-provider-github-copilot`  
**Scope:** `amplifier_module_provider_github_copilot/` + `tests/`  
**Reviewer:** python-dev agent  
**Tools:** ruff (format + lint), pyright (strict), stub-check

---

## Executive Summary

The **production code is clean**: all 8 source files pass ruff and pyright strict mode with zero issues. The architecture is sound, well-structured, and adheres to its own contracts.

The **test code has 221 pyright errors and 3 warnings** across 49 files. These are almost entirely in the test suite — not in the production module. The errors fall into predictable patterns: missing type annotations on pytest fixtures, tests reaching into private symbols, and a few genuine logic issues. One real logic bug was found in production code (a redundant lazy import).

---

## Tool Output Summary

### Production code only (`amplifier_module_provider_github_copilot/`)

```
ruff check:   0 errors, 0 warnings
pyright:      0 errors, 0 warnings
ruff format:  clean
stub-check:   clean
8 files checked — ALL CLEAN
```

### Full scope (production + tests)

```
ruff check:   3 errors (tests only), 3 warnings (tests only)
pyright:      218 errors (tests only), 0 production errors
ruff format:  1 file would be reformatted (tests/test_sdk_boundary_contract.py)
49 files checked — 221 errors total
```

---

## Production Code Analysis

### 1. Type Hints — ✅ Complete and Correct

All public APIs are annotated. The use of `Any` is intentional and well-documented: it isolates the opaque SDK boundary (`SDKSession = Any` in `sdk_adapter/types.py`) and handles the untyped kernel coordinator interface. Type ignores (`# type: ignore[...]`) are all targeted (not blanket), which is good practice.

One minor issue: `provider.py` has a redundant lazy `Path` import inside a function body (line 233) when `Path` is already imported at the top of the file (line 27):

```python
# provider.py line 27 — already imported here
from pathlib import Path

# ...inside complete() function at line 233 — redundant
from pathlib import Path
```

### 2. Async Patterns — ✅ Correct

`async def`, `async for`, `asynccontextmanager`, and `AsyncIterator` are all used correctly. The `complete()` function in `provider.py` is an `async def` that both yields (via `_complete_internal`) and returns — this dual-mode approach is intentional and works correctly. The double-checked locking in `CopilotClientWrapper._client_lock` (provider.py/client.py) correctly prevents race conditions.

Minor note: `_complete_internal()` is declared as returning `AsyncIterator[DomainEvent]` but is an async generator function (uses `yield`). Technically it returns `AsyncGenerator[DomainEvent, None]`, which is a subtype of `AsyncIterator`, so it's functionally correct but the annotation could be more precise.

### 3. Error Handling — ✅ Proper Exception Hierarchy

Error translation is config-driven and thorough. The pattern of catching `Exception`, checking `isinstance(e, LLMError)` to avoid double-wrapping, and then translating via `translate_sdk_error()` is correct. The `translate_sdk_error()` function is documented as "MUST NOT raise" and correctly always returns.

One minor style note: `kernel_error.__cause__ = exc` (lines 351, 372 in `error_translation.py`) manually sets `__cause__` after construction rather than using `raise X from exc`. This pattern is used when returning (not raising) errors, which is the correct approach here — just slightly unusual.

### 4. Import Structure — ✅ No Circular Dependencies

Import graph:
```
__init__  → provider → streaming, error_translation, tool_parsing, sdk_adapter.client
sdk_adapter.client → error_translation
sdk_adapter.types  (standalone)
```

No circular imports. The `from __future__ import annotations` is used in all production modules, which is good for forward reference support. SDK imports are correctly isolated to `sdk_adapter/client.py` only.

One observation: `error_translation.py` imports from `amplifier_core.llm_errors` at module level, and `streaming.py` uses `TYPE_CHECKING` guard for `ChatResponse` but then imports it lazily inside `to_chat_response()`. This inconsistency is intentional (the `TYPE_CHECKING` pattern avoids circular imports at load time) but could be documented.

### 5. Naming Conventions — ✅ PEP 8 Compliant

All classes use `PascalCase`, functions/methods use `snake_case`, private functions use `_` prefix, constants use `ALL_CAPS`. The `_os`, `_PkgNotFoundError`, `_pkg_version` aliases in `__init__.py` are a thoughtful pattern to avoid polluting the module namespace.

### 6. Docstrings — ✅ Complete and Accurate

All public functions have docstrings with Args/Returns/Raises sections where relevant. Contract references (`Contract: provider-protocol.md`) and feature references (`Feature: F-038`) are consistently present. The docstrings accurately reflect the current implementation.

### 7. Code Duplication — ⚠️ Minor DRY Violations

**Issue 1: `AccumulatedResponse` vs `StreamingAccumulator` (`streaming.py`)**

Both dataclasses share identical field definitions:
```python
# AccumulatedResponse (lines 53-63) and StreamingAccumulator (lines 66-76)
# share: text_content, thinking_content, tool_calls, usage, finish_reason, error, is_complete
```
`StreamingAccumulator.get_result()` creates an `AccumulatedResponse` by copying all fields. These two classes could be unified by making `StreamingAccumulator` a subclass of `AccumulatedResponse` or by using composition. However, the separation between "accumulator (mutable)" and "result (immutable snapshot)" is an intentional design pattern — the duplication is the cost of that design and is acceptable.

**Issue 2: `_load_error_config_once()` in `client.py` duplicates YAML parsing**

`client.py:_load_error_config_once()` (lines 72-113) re-implements most of the YAML parsing logic from `error_translation.py:load_error_config()`. The `importlib.resources` path exists only in `client.py` while the file-path path exists in `error_translation.py`. This is a genuine DRY violation — the two code paths can diverge. The `context_extraction` field in `ErrorMapping` is not populated in `client.py`'s parser (it always gets an empty list), which is a behavioral inconsistency.

### 8. Performance — ✅ No Issues

No obvious performance issues. The lazy client initialization is correct. Config loading is done once at startup (not per-request). The `fnmatch` pattern matching in `streaming.py` is linear in the number of patterns, which is fine for config-sized lists.

### 9. Python Idioms — ✅ Pythonic

The code uses modern Python idioms throughout:
- `from __future__ import annotations` for deferred type evaluation
- `collections.abc` for abstract types (not `typing.`)
- `field(default_factory=...)` for mutable dataclass defaults
- `asynccontextmanager` for context manager lifecycle
- `getattr(obj, "attr", default)` for duck-typing SDK objects
- f-strings for logging (though `%s` format is mixed in — both are acceptable)

---

## Test Code Issues

The 221 errors are concentrated in a few categories. The production module itself is not affected.

### Category 1: Missing Type Annotations on Pytest Fixtures (HIGH VOLUME)

**Files affected:** `test_completion.py` (~90 errors), `test_f035_error_types.py` (~40 errors), `test_streaming.py`, `test_f036_error_context.py`

**Pattern:** Pytest fixture parameters lack type annotations, causing pyright to infer `Unknown`:
```python
# test_completion.py — missing types on fixture args
async def test_something(completion_config, config):  # completion_config: Unknown
```
**Fix:** Annotate fixture parameters with their actual types (e.g., `completion_config: CompletionConfig`).

### Category 2: Tests Accessing Private Symbols (POLICY ISSUE)

**Files:** `test_bug_fixes.py`, `test_config_loading.py`, `test_foundation_integration.py`, `test_security_fixes.py`, `test_sdk_boundary_contract.py`

```
reportPrivateUsage: "_extract_retry_after" is private (test_bug_fixes.py:94)
reportPrivateUsage: "_load_models_config" is private (test_config_loading.py:23)
reportPrivateUsage: "_load_error_config_once" is private (test_foundation_integration.py:102)
reportPrivateUsage: "_owned_client" is protected (test_security_fixes.py:106)
reportPrivateUsage: "_client_lock" is protected (test_security_fixes.py:153)
reportPrivateUsage: "_mock_session" is protected (test_sdk_boundary_contract.py:128)
```
These tests are white-box testing internal implementation details. This is sometimes necessary for security/invariant testing, but each test should carry a comment explaining why private access is justified.

### Category 3: Logic Issue — Wrong Type Passed to DomainEvent (`test_contract_events.py:98`)

**Severity: REAL BUG IN TEST**

```
reportArgumentType: Argument of type "Literal['CONTENT_DELTA']" cannot be assigned
to parameter "type" of type "DomainEventType"
```
A string literal `'CONTENT_DELTA'` is being passed where a `DomainEventType` enum value is required. This test is passing a wrong type, which means it tests incorrect behavior. Fix:
```python
# Wrong:
DomainEvent(type='CONTENT_DELTA', ...)
# Correct:
DomainEvent(type=DomainEventType.CONTENT_DELTA, ...)
```

### Category 4: Deprecated API Usage (`test_foundation_integration.py:53`)

```
reportDeprecated: "iscoroutinefunction" is deprecated
  Deprecated since Python 3.14. Use `inspect.iscoroutinefunction()` instead.
```
Replace `asyncio.iscoroutinefunction` with `inspect.iscoroutinefunction`.

### Category 5: Unused Imports

```
F401: `pathlib.Path` imported but unused (test_f036_error_context.py:14)
reportUnusedImport: Import "copilot" is not accessed (conftest.py:44)
reportUnusedImport: Import "Path" is not accessed (test_f036_error_context.py:14)
```
`conftest.py:44` uses `import copilot  # noqa: F401` — the `noqa` suppresses ruff but pyright still flags it. The import exists only to check SDK presence; a `try/except ImportError` around `import copilot` would be cleaner. `test_f036_error_context.py:14` should remove the unused `from pathlib import Path` import.

### Category 6: Ruff Issues

```
test_entry_point.py:26  — I001: Unsorted imports
test_entry_point.py:40  — E501: Line too long (103 > 100)
test_f038_kernel_integration.py:140  — E501: Line too long (102 > 100)
test_f036_error_context.py:14  — F401: Unused import
test_integration.py:429  — B017: Do not assert blind exception (pytest.raises(Exception))
test_sdk_boundary_contract.py  — FORMAT: File would be reformatted
```

The `B017` issue in `test_integration.py:429` is meaningful: `pytest.raises(Exception)` asserts that *some* exception is raised, but doesn't verify the *type* or *message*. This can mask incorrect behavior. Use a specific exception type.

---

## Summary Table

| Area | Production | Tests |
|------|-----------|-------|
| Type hints | ✅ Complete | ⚠️ Many missing in fixtures |
| Async patterns | ✅ Correct | ✅ Correct |
| Error handling | ✅ Proper | ⚠️ B017 blind assertion |
| Imports | ✅ Clean (1 redundant) | ⚠️ Unused imports |
| Naming | ✅ PEP 8 | ✅ PEP 8 |
| Docstrings | ✅ Complete | ✅ Adequate |
| DRY | ⚠️ Minor violations | N/A |
| Performance | ✅ Fine | N/A |
| Idioms | ✅ Pythonic | ✅ Pythonic |

---

## Prioritized Recommendations

### P1 — Fix (Correctness)
1. **`test_contract_events.py:98`** — Replace string `'CONTENT_DELTA'` with `DomainEventType.CONTENT_DELTA`. This test is passing invalid data.
2. **`provider.py:233`** — Remove the redundant `from pathlib import Path` import inside the `complete()` function body. `Path` is already imported at module level (line 27).

### P2 — Fix (Quality)
3. **`test_f036_error_context.py:14`** — Remove unused `from pathlib import Path`.
4. **`test_integration.py:429`** — Replace `pytest.raises(Exception)` with a specific exception type.
5. **`test_foundation_integration.py:53`** — Replace `asyncio.iscoroutinefunction` with `inspect.iscoroutinefunction`.
6. **`test_entry_point.py`** — Fix import sort order and line length.
7. **`test_sdk_boundary_contract.py`** — Run `ruff format` to fix formatting.

### P3 — Improve (Type Safety)
8. **`test_completion.py`** — Add type annotations to fixture parameters. The pervasive `Unknown` types come from unannotated pytest fixture args.
9. **`test_f035_error_types.py`** — Add type annotations to `translate_fn` fixture parameter (use `Callable[[Exception, ErrorConfig], LLMError]`).
10. **`client.py:_load_error_config_once()`** — Consider delegating to `load_error_config()` and adding a separate `importlib.resources` fallback at the `load_error_config` level, eliminating the duplicate YAML parsing logic.

### P4 — Consider (Design)
11. **Private symbol access in tests** — Each test that accesses `_private` symbols should have a comment explaining why white-box access is necessary, or the symbols should be made accessible via a narrow testing interface.
12. **`_complete_internal()` return type** — Change `AsyncIterator[DomainEvent]` to `AsyncGenerator[DomainEvent, None]` for accuracy, or leave as-is (functionally correct).
