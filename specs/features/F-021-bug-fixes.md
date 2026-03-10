# F-021: Bug Fixes from Expert Review

**Priority**: HIGH
**Source**: bug-hunter, python-dev, code-intel
**Estimated Lines**: ~80 changes

## Objective

Fix all HIGH and MEDIUM severity bugs identified by the expert panel.

## Acceptance Criteria

### AC-1: Fix load_event_config Crash (HIGH)

**Problem**: `load_event_config()` in `streaming.py` crashes on missing file (no fallback like `load_error_config`).

**Fix**:
```python
def load_event_config(config_path: str | Path) -> EventConfig:
    path = Path(config_path)
    if not path.exists():
        return EventConfig()  # Graceful fallback
    # ... rest of function
```

**Test**: Verify `load_event_config` with non-existent path returns default config.

### AC-2: Remove Dead Assert Statements (MEDIUM)

**Problem**: `assert session is not None` at lines 129, 141 in `provider.py` — stripped by `-O` flag.

**Fix**: 
- Line 129: Replace with `if session is None: raise ProviderUnavailableError(...)`
- Line 141: Remove entirely (unreachable dead code)

### AC-3: Fix retry_after Regex (MEDIUM)

**Problem**: Second regex pattern `r"(\d+(?:\.\d+)?)\s*seconds?"` matches unrelated "N seconds" strings.

**Fix**: Remove the overly broad fallback pattern:
```python
patterns = [
    r"[Rr]etry[- ]?after[:\s]+(\d+(?:\.\d+)?)",
    # Remove: r"(\d+(?:\.\d+)?)\s*seconds?"
]
```

### AC-4: Fix _make_error_class Super Call (MEDIUM)

**Problem**: `super(Exception, self).__init__` bypasses `LLMError.__init__`.

**Note**: This is fixed by AC-5 in F-020 (importing kernel types). Mark as dependent.

### AC-5: Load finish_reason_map from events.yaml (LOW)

**Problem**: `finish_reason_map` in events.yaml is never loaded or used.

**Fix**: Add to `EventConfig` and apply in `StreamingAccumulator.add()`:
```python
@dataclass
class EventConfig:
    event_classifications: dict[str, str]
    finish_reason_map: dict[str, str]  # Add this field
```

### AC-6: Delete Tombstone Files

**Problem**: `completion.py` and `session_factory.py` are 3-line placeholders.

**Fix**: 
```bash
git rm src/amplifier_module_provider_github_copilot/completion.py
git rm src/amplifier_module_provider_github_copilot/session_factory.py
```

Update any imports that reference these files.

## Files to Modify

- `src/amplifier_module_provider_github_copilot/streaming.py`
- `src/amplifier_module_provider_github_copilot/provider.py`
- `src/amplifier_module_provider_github_copilot/error_translation.py`
- `src/amplifier_module_provider_github_copilot/completion.py` (delete)
- `src/amplifier_module_provider_github_copilot/session_factory.py` (delete)
- `config/events.yaml`
- `tests/test_bug_fixes.py` (create)

## Dependencies

- F-020 (AC-4 depends on kernel error type imports)

## NOT IN SCOPE

- Adding new functionality
- Performance optimizations
