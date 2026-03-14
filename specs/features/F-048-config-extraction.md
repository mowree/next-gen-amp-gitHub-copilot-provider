# F-048: Config Extraction — Policy Out of Python

**Status**: ready
**Priority**: high
**Type**: refactor / architecture
**Estimated Effort**: medium (no new behavior; pure restructuring)

---

## Problem Statement

Three source files are 2-4x their target size because policy data lives inside Python code.
The mechanism (how to apply policy) and policy (what the policy says) are entangled.

| File | Current | Target | Excess |
|------|---------|--------|--------|
| `provider.py` | 467 lines | ~120 lines | ~347 lines |
| `error_translation.py` | 382 lines | ~80 lines | ~302 lines |
| `streaming.py` | 273 lines | ~100 lines | ~173 lines |

**Rule**: Python contains mechanism. YAML contains policy. YAML loaders are mechanism.

---

## Part 1: Mechanism vs Policy Analysis

### 1.1 `provider.py` — Policy Found

**Lines 311–330: Hardcoded provider identity (POLICY)**
```python
# provider.py lines 311-330 — ALL VALUES ARE POLICY
return ProviderInfo(
    id="github-copilot",
    display_name="GitHub Copilot SDK",
    credential_env_vars=[
        "COPILOT_GITHUB_TOKEN",
        "GH_TOKEN",
        "GITHUB_TOKEN",
    ],
    capabilities=["streaming", "tool_use"],
    defaults={
        "model": "gpt-4o",
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout": 60,
        "context_window": 200000,
        "max_output_tokens": 32000,
    },
    config_fields=[],
)
```
This is ~20 lines of pure data. It belongs in `config/models.yaml`.

**Lines 339–356: Hardcoded model catalog (POLICY)**
```python
# provider.py lines 339-356 — ALL VALUES ARE POLICY
return [
    ModelInfo(
        id="gpt-4",
        display_name="GPT-4",
        context_window=128000,
        max_output_tokens=4096,
        capabilities=["streaming", "tool_use"],
        defaults={},
    ),
    ModelInfo(
        id="gpt-4o",
        display_name="GPT-4o",
        context_window=128000,
        max_output_tokens=4096,
        capabilities=["streaming", "tool_use"],
        defaults={},
    ),
]
```
This is ~18 lines of pure data. It belongs in `config/models.yaml`.

**Line 173: Hardcoded default model fallback (POLICY)**
```python
# provider.py line 173
session_config = config.session_config or SessionConfig(model=request.model or "gpt-4")
```
The string `"gpt-4"` is policy. It should come from `models.yaml`.

**Line 221 in `sdk_adapter/client.py`: Hardcoded session mode (POLICY + BUG)**
```python
# client.py line 221 — WRONG VALUE (F-044 bug) AND IT IS POLICY
session_config["system_message"] = {"mode": "append", "content": system_message}
```
The `"append"` mode is policy. The correct value per F-044 is `"replace"`. This belongs in config.

**Lines 125 in `sdk_adapter/client.py`: Token priority order (POLICY)**
```python
# client.py lines 125-129
for var in ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
```
The token variable priority list is policy. It belongs in `config/models.yaml`.

**Mechanism (STAYS in `provider.py`):**
- Lines 53–89: `extract_response_content()` — runtime dispatch logic
- Lines 92–128: `CompletionRequest`, `CompletionConfig` dataclasses — structural types
- Lines 130–225: `complete()` — async generator, session lifecycle protocol
- Lines 227–257: `complete_and_collect()` — accumulation convenience
- Lines 260–302: `GitHubCopilotProvider.__init__()`, `.name` property
- Lines 304–330: `get_info()` — FUNCTION SHELL stays, VALUES move out
- Lines 332–356: `list_models()` — FUNCTION SHELL stays, VALUES move out
- Lines 358–450: `complete()`, `_complete_internal()` — request conversion + dispatch
- Lines 452–467: `close()`, `parse_tool_calls()` — lifecycle + delegation

### 1.2 `error_translation.py` — Policy Found

**Lines 60–76: KERNEL_ERROR_MAP string→class registry (MECHANISM, not policy)**
```python
# error_translation.py lines 60-76
KERNEL_ERROR_MAP: dict[str, type[LLMError]] = {
    "AuthenticationError": AuthenticationError,
    "RateLimitError": RateLimitError,
    # ... 13 entries
}
```
This looks like policy but is actually mechanism: it's how config string names resolve to
Python classes at runtime. It MUST stay in Python. It cannot live in YAML because YAML
cannot reference Python classes.

**Lines 84–96: `ContextExtraction` dataclass (SCHEMA DESCRIPTION = MECHANISM)**
This describes the shape of YAML data. It stays in Python as a structural type.

**Lines 104–122: `ErrorMapping` dataclass (SCHEMA DESCRIPTION = MECHANISM)**
Same — structural type for YAML data. Stays in Python.

**Lines 130–142: `ErrorConfig` dataclass (SCHEMA DESCRIPTION = MECHANISM)**
Same — structural type for YAML data. Stays in Python.

**Lines 79–81, 99–101, 125–127: Factory functions `_str_list`, `_context_list`, `_mapping_list`**
```python
def _str_list() -> list[str]:
    return []
```
These exist only to satisfy `dataclass field(default_factory=...)` typing.
They are 9 lines of boilerplate that can be collapsed to inline lambdas or removed
by restructuring to use `field(default_factory=list)` with type annotation.

**Lines 207–210: Retry-after regex patterns (BORDERLINE POLICY)**
```python
patterns = [
    r"[Rr]etry[- ]?after[:\s]+(\d+(?:\.\d+)?)",
]
```
These patterns are currently correct and rarely change. Leave in Python for now.
Mark as a future extraction candidate.

**Lines 195–382: All functions are MECHANISM** — they apply the policy loaded from YAML.
The error config is already externalized to `config/errors.yaml`. The Python is the engine
that applies it. The main bloat is docstrings (each function has 10–15 line docstrings)
and the factory boilerplate.

**Real bloat in `error_translation.py`:**
- Factory function boilerplate: ~9 lines
- Overly long docstrings: ~60 lines (each function has 8-15 lines of docstring)
- `translate_sdk_error()` has two near-identical code paths (matched + default): ~40 lines
  that could be extracted into a helper

### 1.3 `streaming.py` — Policy Found

**Lines 25–33: `DomainEventType` enum (MECHANISM)**
```python
class DomainEventType(Enum):
    CONTENT_DELTA = "CONTENT_DELTA"
    TOOL_CALL = "TOOL_CALL"
    USAGE_UPDATE = "USAGE_UPDATE"
    TURN_COMPLETE = "TURN_COMPLETE"
    SESSION_IDLE = "SESSION_IDLE"
    ERROR = "ERROR"
```
These strings ARE used in `config/events.yaml` as `domain_type` values. The enum must
stay in Python because Python code uses `DomainEventType.CONTENT_DELTA`. The VALUES
are already aligned with the YAML config.

**Lines 53–63: `AccumulatedResponse` vs Lines 66–107: `StreamingAccumulator` (DUPLICATION)**
```python
@dataclass
class AccumulatedResponse:   # 10 fields
    text_content: str = ""
    thinking_content: str = ""
    tool_calls: list[...] = ...
    usage: ... = None
    finish_reason: ... = None
    error: ... = None
    is_complete: bool = False

@dataclass
class StreamingAccumulator:  # SAME 7 fields + 4 methods
    text_content: str = ""
    thinking_content: str = ""
    ...
```
`StreamingAccumulator` has the same 7 fields as `AccumulatedResponse` plus methods.
The `get_result()` method (lines 97-107) just copies all fields into an
`AccumulatedResponse`. This is 30+ lines of duplication. The accumulator can simply
BE the result; eliminate the separate `AccumulatedResponse` dataclass or have
`StreamingAccumulator` extend it.

**Lines 109–166: `to_chat_response()` (MECHANISM — but can be trimmed)**
This 58-line method converts internal types to kernel types. It stays in Python but
can be condensed (currently has 10+ lines of comments for ~15 lines of actual logic).

**Lines 186–223: `load_event_config()` (MECHANISM — YAML loader)**
This loads `config/events.yaml`. It is correctly placed.

**Real bloat in `streaming.py`:**
- `AccumulatedResponse` + `StreamingAccumulator` field duplication: ~30 lines
- Overly long docstrings: ~25 lines
- `_empty_str_to_str_dict` factory function (lines 169-171): trivial boilerplate

### 1.4 `sdk_adapter/client.py` — Duplicate Policy Found

**Lines 72–113: `_load_error_config_once()` (DUPLICATION)**
```python
def _load_error_config_once() -> ErrorConfig:
    # tries importlib.resources then falls back to file path
    # manually parses YAML into ErrorMapping/ErrorConfig objects
    # lines 87-103: DUPLICATES error_translation.load_error_config()!
```
This function manually constructs `ErrorMapping` and `ErrorConfig` objects from raw
YAML — the same work that `error_translation.load_error_config()` already does.
This is 42 lines of duplicate code that should call `load_error_config()` directly.

---

## Part 2: YAML Schema Designs

### 2.1 `config/models.yaml` — NEW FILE

This config does not yet exist. It should hold all provider and model policy.

```yaml
# config/models.yaml
# Provider identity and model catalog policy
# Contract: contracts/provider-protocol.md
# Feature: F-048

version: "1.0"

provider:
  id: github-copilot
  display_name: "GitHub Copilot SDK"
  # Auth token env vars in priority order (first non-empty wins)
  # Priority: Copilot agent mode > recommended > CLI compat > Actions compat
  credential_env_vars:
    - COPILOT_AGENT_TOKEN    # Copilot agent mode
    - COPILOT_GITHUB_TOKEN   # Official recommended
    - GH_TOKEN               # GitHub CLI compatible
    - GITHUB_TOKEN           # GitHub Actions compatible
  capabilities:
    - streaming
    - tool_use
  defaults:
    model: gpt-4o
    max_tokens: 4096
    temperature: 0.7
    timeout: 60
    context_window: 200000
    max_output_tokens: 32000

models:
  - id: gpt-4
    display_name: "GPT-4"
    context_window: 128000
    max_output_tokens: 4096
    capabilities:
      - streaming
      - tool_use
    defaults: {}

  - id: gpt-4o
    display_name: "GPT-4o"
    context_window: 128000
    max_output_tokens: 4096
    capabilities:
      - streaming
      - tool_use
    defaults: {}
```

### 2.2 `config/errors.yaml` — ALREADY EXISTS, NO CHANGES NEEDED

The existing `config/errors.yaml` is correct and complete. F-048 does not modify it.

### 2.3 `config/events.yaml` — ALREADY EXISTS, NO CHANGES NEEDED

The existing `config/events.yaml` is correct and complete. F-048 does not modify it.

### 2.4 `config/retry.yaml` — ALREADY EXISTS, NO CHANGES NEEDED

The existing `config/retry.yaml` is correct and complete. F-048 does not modify it.

### 2.5 `config/circuit-breaker.yaml` — NOT NEEDED (already in `retry.yaml`)

The `circuit_breaker:` section of `retry.yaml` covers this. No separate file needed.

---

## Part 3: Python Loader Design

### 3.1 `config/models.yaml` loader

Add to a new thin module `amplifier_module_provider_github_copilot/config_loader.py`
OR add a `load_models_config()` function directly in `provider.py` (preferred — no new file).

```python
# In provider.py — add near top, after imports

from pathlib import Path
import yaml

@dataclass
class ProviderConfig:
    """Policy data loaded from config/models.yaml."""
    provider_id: str
    display_name: str
    credential_env_vars: list[str]
    capabilities: list[str]
    defaults: dict[str, Any]
    models: list[dict[str, Any]]

def _load_models_config() -> ProviderConfig:
    """Load provider and model policy from config/models.yaml.

    Falls back to minimal hardcoded defaults if file is missing.
    (Graceful degradation — same pattern as load_event_config.)
    """
    config_path = Path(__file__).parent.parent / "config" / "models.yaml"
    if not config_path.exists():
        # Minimal fallback so unit tests can run without the file
        return _default_provider_config()

    with config_path.open() as f:
        data = yaml.safe_load(f)

    if not data:
        return _default_provider_config()

    p = data.get("provider", {})
    return ProviderConfig(
        provider_id=p.get("id", "github-copilot"),
        display_name=p.get("display_name", "GitHub Copilot SDK"),
        credential_env_vars=p.get("credential_env_vars", []),
        capabilities=p.get("capabilities", []),
        defaults=p.get("defaults", {}),
        models=data.get("models", []),
    )

def _default_provider_config() -> ProviderConfig:
    """Minimal fallback config for environments without config files."""
    return ProviderConfig(
        provider_id="github-copilot",
        display_name="GitHub Copilot SDK",
        credential_env_vars=["COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
        capabilities=["streaming", "tool_use"],
        defaults={"model": "gpt-4o", "max_tokens": 4096},
        models=[],
    )
```

**Startup loading**: `_load_models_config()` is called once at class instantiation in
`GitHubCopilotProvider.__init__()` and cached as `self._provider_config`.

### 3.2 Fixing duplicate error config loading in `client.py`

Replace the 42-line `_load_error_config_once()` (lines 72–113 of `client.py`) with:

```python
def _load_error_config_once() -> ErrorConfig:
    """Load error config from canonical location."""
    from pathlib import Path
    from ..error_translation import load_error_config

    config_path = Path(__file__).parent.parent.parent / "config" / "errors.yaml"
    return load_error_config(config_path)
```

This is 6 lines instead of 42. The full YAML loading logic lives in `load_error_config()`.

### 3.3 Collapsing `StreamingAccumulator` + `AccumulatedResponse` duplication

Replace two separate dataclasses (30+ lines of duplicate fields) with a single class:

```python
@dataclass
class StreamingAccumulator:
    """Accumulates streaming domain events into final response."""
    text_content: str = ""
    thinking_content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    error: dict[str, Any] | None = None
    is_complete: bool = False

    def add(self, event: DomainEvent) -> None: ...
    def to_chat_response(self) -> "ChatResponse": ...
    # Remove get_result() — callers use accumulator directly or to_chat_response()
```

`AccumulatedResponse` is removed. Any caller using `accumulator.get_result()` is updated
to use the accumulator directly or call `to_chat_response()`.

### 3.4 Removing factory function boilerplate in `error_translation.py`

Replace:
```python
def _str_list() -> list[str]:
    return []

def _context_list() -> list[ContextExtraction]:
    return []

def _mapping_list() -> list[ErrorMapping]:
    return []
```

With inline `field(default_factory=list)`:
```python
@dataclass
class ErrorMapping:
    sdk_patterns: list[str] = field(default_factory=list)
    string_patterns: list[str] = field(default_factory=list)
    ...
    context_extraction: list[ContextExtraction] = field(default_factory=list)
```

Saves 9 lines, improves readability.

### 3.5 Validation approach

**No JSON Schema or Pydantic validation required for V1.**
- YAML files are small and human-maintained
- Missing keys use `.get()` with sensible defaults (existing pattern)
- Missing config file falls back gracefully (existing pattern from `load_event_config`)
- Config loading is tested via `test_config_loading.py` (new test file per F-048)

Future: Add jsonschema validation in a separate feature if YAML files grow complex enough
to require it.

---

## Part 4: Acceptance Criteria

### AC-1: Line Count Targets

After F-048 is complete, the following file sizes MUST be verified:

| File | Pre-F048 | Target | Tolerance |
|------|----------|--------|-----------|
| `provider.py` | 467 | ≤ 200 | ±10 lines |
| `error_translation.py` | 382 | ≤ 160 | ±10 lines |
| `streaming.py` | 273 | ≤ 160 | ±10 lines |
| `sdk_adapter/client.py` | 261 | ≤ 220 | ±10 lines |
| `config/models.yaml` | 0 | ~55 lines | ±10 lines |

> Note: Targets are more conservative than the task brief's ~120/~80/~100 goals.
> The brief's numbers assume elimination of all dataclass schemas, which would require
> Pydantic or similar. F-048 uses a more conservative approach: extract policy to YAML
> and remove duplication, preserving structural dataclasses.

### AC-2: Config Loading Tests

A new test file `tests/test_config_loading.py` MUST cover:

- `test_load_models_config_from_yaml` — loads `config/models.yaml`, asserts provider id,
  display_name, credential_env_vars, capabilities, defaults, and models list
- `test_load_models_config_missing_file` — returns fallback config without raising
- `test_load_models_config_empty_file` — returns fallback config without raising
- `test_load_models_config_partial_data` — missing optional fields use defaults
- `test_provider_config_fields_round_trip` — load → build ProviderInfo → check fields

### AC-3: Provider Method Tests

- `test_get_info_uses_yaml_config` — `get_info()` returns values from `models.yaml`,
  NOT hardcoded Python strings
- `test_list_models_uses_yaml_config` — `list_models()` returns models from `models.yaml`
- `test_get_info_graceful_without_yaml` — `get_info()` returns valid `ProviderInfo`
  even if `models.yaml` doesn't exist

### AC-4: No Regression

All existing tests MUST continue to pass. Specifically:
- `tests/test_contract_protocol.py` — provider protocol compliance
- `tests/test_f038_kernel_integration.py` — kernel type migration
- `tests/test_error_translation.py` — error translation logic
- `tests/test_streaming.py` — streaming accumulation
- Full suite: `pytest tests/ -v --ignore=tests/test_live_sdk.py`

### AC-5: Duplicate Code Eliminated

- `sdk_adapter/client.py::_load_error_config_once()` MUST NOT duplicate YAML parsing
  logic that already exists in `error_translation.load_error_config()`
- `StreamingAccumulator` fields MUST NOT duplicate `AccumulatedResponse` fields
  (merge or eliminate `AccumulatedResponse`)

### AC-6: Config Compliance Tests

A new test `test_config_loading.py::test_models_yaml_schema_compliance` MUST:
- Load `config/models.yaml` using the production loader
- Assert the YAML version field is present
- Assert `provider.id` equals `"github-copilot"`
- Assert `models` is a non-empty list
- Assert each model has `id`, `display_name`, `context_window`, `max_output_tokens`

---

## Part 5: Implementation Steps (TDD Sequence)

### Order of Operations

1. `config/models.yaml` — create YAML file (no Python change yet)
2. `tests/test_config_loading.py` — write RED tests for the loader
3. `provider.py::_load_models_config()` — write GREEN loader
4. `provider.py::get_info()` + `list_models()` — REFACTOR to use loaded config
5. `streaming.py` — merge `AccumulatedResponse` into `StreamingAccumulator`
6. `error_translation.py` — remove factory boilerplate + trim docstrings
7. `sdk_adapter/client.py` — fix duplicate `_load_error_config_once()`
8. Verify: run full test suite, check line counts

### Step 1: Create `config/models.yaml`

Write the YAML file as specified in Part 2.1. No Python changes.

Verify: file parses with `python -c "import yaml; yaml.safe_load(open('config/models.yaml'))"`.

### Step 2: RED Tests — `tests/test_config_loading.py`

Write failing tests BEFORE writing the loader:

```python
# tests/test_config_loading.py

def test_load_models_config_returns_provider_id():
    """Models config loader returns correct provider id from YAML."""
    config = _load_models_config()
    assert config.provider_id == "github-copilot"

def test_load_models_config_returns_models_list():
    """Models config loader returns non-empty models list."""
    config = _load_models_config()
    assert len(config.models) >= 2  # gpt-4 and gpt-4o

def test_load_models_config_missing_file_returns_fallback():
    """Missing models.yaml returns fallback without raising."""
    from unittest.mock import patch
    with patch("pathlib.Path.exists", return_value=False):
        config = _load_models_config()
    assert config.provider_id == "github-copilot"  # fallback default

def test_get_info_sourced_from_yaml():
    """Provider.get_info() values come from YAML, not hardcoded strings."""
    provider = GitHubCopilotProvider()
    info = provider.get_info()
    # If this test fails when models.yaml changes, we know it's working correctly
    assert info.id == "github-copilot"
    assert "gpt-4o" in str(info.defaults.get("model", ""))

def test_list_models_sourced_from_yaml():
    """Provider.list_models() comes from YAML, not hardcoded list."""
    import asyncio
    provider = GitHubCopilotProvider()
    models = asyncio.run(provider.list_models())
    model_ids = [m.id for m in models]
    assert "gpt-4o" in model_ids
    assert "gpt-4" in model_ids
```

These tests FAIL until Step 3 is complete. That's the RED phase.

### Step 3: GREEN — Write `_load_models_config()` in `provider.py`

Add the `ProviderConfig` dataclass and `_load_models_config()` function as designed in
Part 3.1. Update `GitHubCopilotProvider.__init__()` to call `_load_models_config()`.

Run: `pytest tests/test_config_loading.py -v` — all tests should now pass.

### Step 4: REFACTOR — `get_info()` and `list_models()` use loaded config

Replace hardcoded values in `get_info()` (lines 311–330) and `list_models()` (lines 339–356)
with values from `self._provider_config`.

```python
def get_info(self) -> ProviderInfo:
    """Return provider metadata. Contract: provider-protocol:get_info:MUST:1"""
    cfg = self._provider_config
    return ProviderInfo(
        id=cfg.provider_id,
        display_name=cfg.display_name,
        credential_env_vars=cfg.credential_env_vars,
        capabilities=cfg.capabilities,
        defaults=cfg.defaults,
        config_fields=[],
    )

async def list_models(self) -> list[ModelInfo]:
    """Return available models. Contract: provider-protocol:list_models:MUST:1"""
    return [
        ModelInfo(
            id=m["id"],
            display_name=m["display_name"],
            context_window=m["context_window"],
            max_output_tokens=m["max_output_tokens"],
            capabilities=m.get("capabilities", []),
            defaults=m.get("defaults", {}),
        )
        for m in self._provider_config.models
    ]
```

Run: `pytest tests/ -v --ignore=tests/test_live_sdk.py` — all tests must pass.

### Step 5: REFACTOR — Merge `AccumulatedResponse` into `StreamingAccumulator` in `streaming.py`

1. Remove `AccumulatedResponse` dataclass (lines 53–63)
2. Remove `get_result()` method from `StreamingAccumulator` (lines 97–107)
3. Update any caller of `get_result()` — currently only `complete_and_collect()` in
   `provider.py` (lines 248–257)
4. Update `complete_and_collect()` to use `accumulator.to_chat_response()` or return
   the accumulator directly

Check: `grep -rn "AccumulatedResponse\|get_result()" amplifier_module_provider_github_copilot/`
should return no hits after refactor.

Run: `pytest tests/test_streaming.py tests/test_completion.py -v`

### Step 6: REFACTOR — `error_translation.py` cleanup

Remove factory boilerplate (9 lines), replace with `field(default_factory=list)`.
Trim docstrings to 3-line maximum (contract reference + one-liner description + return).
Extract the matched/default branches of `translate_sdk_error()` into a helper:

```python
def _build_kernel_error(
    error_class: type[LLMError],
    message: str,
    provider: str,
    model: str | None,
    retryable: bool,
    retry_after: float | None,
) -> LLMError:
    """Build kernel error, handling InvalidToolCallError's signature difference."""
    if error_class is InvalidToolCallError:
        return error_class(message, provider=provider, model=model, retryable=retryable)
    return error_class(
        message, provider=provider, model=model, retryable=retryable, retry_after=retry_after
    )
```

This removes the duplicated 8-line error construction blocks in `translate_sdk_error()`.

Run: `pytest tests/test_error_translation.py tests/test_f035_error_types.py tests/test_f036_error_context.py -v`

### Step 7: FIX — `sdk_adapter/client.py` duplicate loader

Replace `_load_error_config_once()` lines 72–113 (42 lines) with 6-line version:

```python
def _load_error_config_once() -> ErrorConfig:
    """Load error config from canonical location."""
    from pathlib import Path
    from ..error_translation import load_error_config

    config_path = Path(__file__).parent.parent.parent / "config" / "errors.yaml"
    return load_error_config(config_path)
```

Also fix the F-044 bug at line 221:
```python
# BEFORE (buggy):
session_config["system_message"] = {"mode": "append", "content": system_message}
# AFTER (correct):
session_config["system_message"] = {"mode": "replace", "content": system_message}
```

Run: `pytest tests/test_sdk_client.py tests/test_sdk_boundary.py -v`

### Step 8: Verify

```bash
# Line count check
wc -l amplifier_module_provider_github_copilot/provider.py
wc -l amplifier_module_provider_github_copilot/error_translation.py
wc -l amplifier_module_provider_github_copilot/streaming.py
wc -l amplifier_module_provider_github_copilot/sdk_adapter/client.py

# Full test suite (no live tests)
pytest tests/ -v --ignore=tests/test_live_sdk.py

# Type check
pyright amplifier_module_provider_github_copilot/

# Lint
ruff check amplifier_module_provider_github_copilot/
```

---

## Part 6: What Does NOT Move to YAML

These are mechanisms that MUST remain in Python:

| Item | Why it stays in Python |
|------|----------------------|
| `KERNEL_ERROR_MAP` dict | Maps string names → Python classes; YAML cannot reference classes |
| `DomainEventType` enum | Python code uses `DomainEventType.CONTENT_DELTA`; not just data |
| `EventClassification` enum | Python code uses `EventClassification.BRIDGE` |
| All `@dataclass` schema types | Structural types for type-safe YAML deserialization |
| `extract_response_content()` | Runtime dispatch with attribute inspection |
| `complete()` async generator | Session lifecycle protocol |
| `translate_sdk_error()` | Pattern matching engine |
| `translate_event()` | Event dispatch engine |
| `StreamingAccumulator.add()` | Event routing logic |
| `to_chat_response()` | Kernel type conversion |

---

## Part 7: Scope Boundaries

**IN SCOPE:**
- Create `config/models.yaml`
- Add `_load_models_config()` + `ProviderConfig` dataclass to `provider.py`
- Refactor `get_info()` and `list_models()` to use loaded config
- Merge `AccumulatedResponse` into `StreamingAccumulator`
- Remove factory function boilerplate in `error_translation.py`
- Fix duplicate loader in `sdk_adapter/client.py`
- Fix F-044 mode bug in `sdk_adapter/client.py` line 221 (append → replace)
- Write `tests/test_config_loading.py`

**OUT OF SCOPE:**
- Pydantic schema validation for YAML files (future feature)
- Extracting retry-after patterns to YAML
- Any changes to existing YAML files (errors.yaml, events.yaml, retry.yaml)
- Any new behavior changes
- New SDK integration tests (covered by F-046/F-047)
- The `config/circuit-breaker.yaml` separate file (already in retry.yaml)

---

## References

- `config/errors.yaml` — already-extracted error policy (pattern to follow)
- `config/events.yaml` — already-extracted event policy (pattern to follow)
- `config/retry.yaml` — already-extracted retry policy (pattern to follow)
- `specs/F-047-testing-course-correction.md` — F-044 bug context (mode: append→replace)
- `contracts/provider-protocol.md` — provider contract
- `contracts/error-hierarchy.md` — error contract

---

*Created: 2026-03-14*
*Author: foundation:integration-specialist*
*Purpose: Establish textbook-perfect policy-extraction standards for F-048 implementation*
