# F-038: Kernel Type Migration

> **Priority**: CRITICAL — Provider cannot be loaded by Amplifier without this
> **Estimated Effort**: Medium (150-200 lines changed across 5-6 files)
> **Dependencies**: None
> **Contract**: contracts/provider-protocol.md

## 1. Overview

### Problem Statement

The next-gen provider defines local Python dataclasses for all types (`ProviderInfo`, `ModelInfo`, `ToolCall`, `LLMError` hierarchy). The Amplifier kernel expects Pydantic models from `amplifier_core`. When the kernel's `ProviderValidator` calls `isinstance(info, ProviderInfo)`, it fails because the workspace returns a different type.

**Current State:**
- 0 imports from `amplifier_core`
- 5 local type definitions (ProviderInfo, ModelInfo, CompletionRequest, ToolCall, LLMError)
- `complete()` returns `AsyncIterator[DomainEvent]` instead of `ChatResponse`

**Target State:**
- Import all required types from `amplifier_core`
- Provider class methods return kernel types
- YAML-driven error translation produces kernel error types
- Internal streaming machinery preserved (only boundary conversion added)
- Three-Medium Architecture preserved (YAML policy, Markdown contracts)

### Evidence

| Source | Finding |
|--------|---------|
| `reference-only/amplifier-core/python/amplifier_core/interfaces.py:67-131` | Provider Protocol requires kernel types |
| `reference-only/amplifier-core/python/amplifier_core/models.py:358-384` | `ProviderInfo` is Pydantic with `id`, `display_name`, `credential_env_vars`, `capabilities`, `defaults`, `config_fields` |
| `reference-only/amplifier-core/python/amplifier_core/message_models.py:257-271` | `ChatResponse` is Pydantic with `content`, `tool_calls`, `usage`, `finish_reason` |
| `reference-only/amplifier-core/python/amplifier_core/__init__.py:9` | Kernel version is `1.0.7` |
| `reference-only/amplifier-module-provider-github-copilot/provider.py:40-72` | Production imports all types from `amplifier_core` |
| `src/amplifier_module_provider_github_copilot/provider.py:49-75` | Workspace defines local dataclasses |

---

## 2. Expert Panel Blockers (MUST Address)

| Blocker | Source | Resolution |
|---------|--------|------------|
| Version `>=1.2.0` doesn't exist | Integration Specialist | Change to `>=1.0.7` |
| `to_chat_response()` uses wrong types | Bug Hunter, Integration Specialist | Use `TextBlock`/`ThinkingBlock` (Pydantic from `message_models`), NOT `TextContent`/`ThinkingContent` (dataclass from `content_models`) |
| `parse_tool_calls()` must be method | Integration Specialist | Move to provider class method per Protocol |
| Test calls `mount()` without `await` | Bug Hunter | Make test async, use `await mount(...)` |
| Capability vocabulary mismatch | Zen Architect | Use `tool_use` (current tests expect this) |
| Missing `AccessDeniedError` | Integration Specialist | Add to imports |
| Delete internal types unnecessarily | Zen Architect | KEEP `CompletionRequest`, `CompletionConfig`, internal streaming. Only add boundary conversion at `complete()` method |

---

## 3. Type Migration Map

### 3.1 Types to Import from `amplifier_core`

```python
# From amplifier_core (top-level exports)
from amplifier_core import (
    # Protocol types (for ChatResponse construction)
    ChatResponse,
    Usage,
    
    # Content blocks for ChatResponse.content (PYDANTIC, not dataclass!)
    TextBlock,
    ThinkingBlock,
    ToolCallBlock,
    
    # Provider metadata
    ProviderInfo,
    ModelInfo,
    
    # Tool calls
    ToolCall,
)

# From amplifier_core.llm_errors (ALL 15 types)
from amplifier_core.llm_errors import (
    LLMError,
    AuthenticationError,
    RateLimitError,
    QuotaExceededError,
    LLMTimeoutError,
    ContentFilterError,
    NetworkError,
    NotFoundError,
    ContextLengthError,
    StreamError,
    InvalidToolCallError,
    ConfigurationError,
    ProviderUnavailableError,
    InvalidRequestError,
    AbortError,
    AccessDeniedError,  # <-- Was missing in original spec
)
```

### 3.2 Field Mapping: ProviderInfo

| Workspace (DELETE) | Kernel (USE) | Notes |
|--------------------|--------------|-------|
| `name: str` | `id: str` | Same value: `"github-copilot"` |
| `version: str` | (not a field) | Remove — kernel doesn't have version |
| `description: str` | `display_name: str` | Value: `"GitHub Copilot SDK"` |
| `capabilities: list[str]` | `capabilities: list[str]` | Keep: `["streaming", "tool_use"]` ← NOTE: `tool_use` not `tools` |
| (missing) | `credential_env_vars: list[str]` | Add: `["GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN"]` |
| (missing) | `defaults: dict[str, Any]` | Add: `{"model": "gpt-4o", "timeout": 60, ...}` |
| (missing) | `config_fields: list[ConfigField]` | Add: `[]` (empty for now) |

**Kernel ProviderInfo signature:**
```python
ProviderInfo(
    id="github-copilot",
    display_name="GitHub Copilot SDK",
    credential_env_vars=["GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN"],
    capabilities=["streaming", "tool_use"],  # tool_use, not tools!
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

### 3.3 Field Mapping: ModelInfo

| Workspace (DELETE) | Kernel (USE) | Notes |
|--------------------|--------------|-------|
| `id: str` | `id: str` | Same |
| `display_name: str` | `display_name: str` | Same |
| `context_window: int` | `context_window: int` | Same |
| `max_output_tokens: int` | `max_output_tokens: int` | Same |
| (missing) | `capabilities: list[str]` | Add: `["streaming", "tool_use"]` |
| (missing) | `defaults: dict[str, Any]` | Add: `{}` |

### 3.4 ChatResponse Content Blocks (CRITICAL)

**WRONG (from original spec):**
```python
# DO NOT USE - These are DATACLASSES from content_models.py
from amplifier_core import TextContent, ThinkingContent  # WRONG!
```

**CORRECT:**
```python
# USE THESE - These are PYDANTIC MODELS from message_models.py
from amplifier_core import TextBlock, ThinkingBlock, ToolCallBlock  # CORRECT!
```

`ChatResponse.content` is `list[ContentBlockUnion]` where `ContentBlockUnion` is a discriminated union requiring `type` field:
- `TextBlock(type="text", text="...")`
- `ThinkingBlock(type="thinking", thinking="...")`
- `ToolCallBlock(type="tool_call", id="...", name="...", input={...})`

### 3.5 Method Changes (Boundary Only)

**KEEP internal types** (`CompletionRequest`, `CompletionConfig`, `DomainEvent`, `AccumulatedResponse`).

**ADD boundary conversion** only at provider class methods:

| Method | Input | Output | Change |
|--------|-------|--------|--------|
| `get_info()` | — | `ProviderInfo` | Return kernel type directly |
| `list_models()` | — | `list[ModelInfo]` | Return kernel type directly |
| `complete(request, **kwargs)` | `Any` (ChatRequest) | `ChatResponse` | Extract messages, use internal machinery, convert result |
| `parse_tool_calls(response)` | `ChatResponse` | `list[ToolCall]` | **NEW: Must be method on provider class** |

---

## 4. Files to Modify

| File | Action | Changes |
|------|--------|---------|
| `src/.../provider.py` | HEAVY | Delete local `ProviderInfo`/`ModelInfo`, import kernel types, add `complete()` wrapper, move `parse_tool_calls()` to method |
| `src/.../error_translation.py` | MEDIUM | Delete local error classes, import from kernel, update `KERNEL_ERROR_MAP` |
| `src/.../tool_parsing.py` | LIGHT | Import `ToolCall` from kernel, update return type |
| `src/.../streaming.py` | MEDIUM | Add `to_chat_response()` using correct `TextBlock`/`ThinkingBlock` types |
| `src/.../__init__.py` | LIGHT | Update exports (remove local types from `__all__`) |
| `pyproject.toml` | LIGHT | Change dev dep to `amplifier-core>=1.0.7` |
| `tests/*.py` | MEDIUM | Update imports, fix async mount, use kernel types for isinstance |

---

## 5. Implementation Steps (TDD)

### Step 0: Fix Dependencies

Update `pyproject.toml`:
```diff
- "amplifier-core>=1.2.0",
+ "amplifier-core>=1.0.7",
```

### Step 1: Write Failing Integration Tests (RED)

Create `tests/test_f038_kernel_integration.py`:

```python
"""
F-038: Kernel Type Integration Tests

These tests verify the provider returns kernel types that pass isinstance() checks.
They MUST fail before migration and PASS after.

NOTE: Tests use pytest.importorskip() to gracefully skip if amplifier_core unavailable.
"""
import pytest

# Skip entire module if amplifier_core not installed
pytest.importorskip("amplifier_core")


class TestKernelTypeCompliance:
    """Tests that provider returns actual kernel types."""

    @pytest.mark.asyncio
    async def test_provider_info_is_kernel_type(self) -> None:
        """F-038:AC-1 - get_info() returns amplifier_core.ProviderInfo."""
        from amplifier_core import ProviderInfo as KernelProviderInfo
        from amplifier_module_provider_github_copilot import mount
        from unittest.mock import AsyncMock, MagicMock
        
        # Create mock coordinator with async mount
        coordinator = MagicMock()
        coordinator.mount = AsyncMock()
        
        # Mount is async!
        await mount(coordinator, config=None)
        
        # Get the mounted provider
        provider = coordinator.mount.call_args[0][1]
        info = provider.get_info()
        
        # This is THE critical check that fails today
        assert isinstance(info, KernelProviderInfo), (
            f"get_info() returned {type(info).__name__}, expected ProviderInfo from amplifier_core"
        )
        
        # Verify required fields exist
        assert hasattr(info, "id")
        assert hasattr(info, "display_name")
        assert hasattr(info, "credential_env_vars")
        assert hasattr(info, "defaults")

    def test_error_translation_produces_kernel_errors(self) -> None:
        """F-038:AC-2 - translate_sdk_error() returns amplifier_core.llm_errors types."""
        from amplifier_core.llm_errors import AuthenticationError as KernelAuthError
        from amplifier_module_provider_github_copilot.error_translation import (
            translate_sdk_error,
            load_error_config,
        )
        from pathlib import Path
        
        # Must provide config path explicitly
        config_path = Path(__file__).parent.parent / "config" / "errors.yaml"
        config = load_error_config(config_path)
        
        # Create an auth error
        class SDKAuthError(Exception):
            pass
        
        exc = SDKAuthError("401 Unauthorized")
        result = translate_sdk_error(exc, config)
        
        # Must be actual kernel type
        assert isinstance(result, KernelAuthError), (
            f"Expected amplifier_core AuthenticationError, got {type(result).__name__}"
        )

    def test_tool_call_is_kernel_type(self) -> None:
        """F-038:AC-3 - parse_tool_calls() returns amplifier_core.ToolCall."""
        from amplifier_core import ToolCall as KernelToolCall
        from amplifier_module_provider_github_copilot import GitHubCopilotProvider
        
        provider = GitHubCopilotProvider()
        
        # Mock response with tool calls
        class MockToolCall:
            id = "tc_1"
            name = "test_tool"
            arguments = {"arg1": "value1"}
        
        class MockResponse:
            tool_calls = [MockToolCall()]
        
        # parse_tool_calls must be a METHOD on provider (per Protocol)
        assert hasattr(provider, "parse_tool_calls"), (
            "parse_tool_calls must be a method on provider class"
        )
        
        result = provider.parse_tool_calls(MockResponse())
        
        assert len(result) == 1
        assert isinstance(result[0], KernelToolCall), (
            f"Expected amplifier_core ToolCall, got {type(result[0]).__name__}"
        )

    @pytest.mark.asyncio
    async def test_complete_returns_chat_response(self) -> None:
        """F-038:AC-4 - complete() returns ChatResponse (not iterator)."""
        from amplifier_core import ChatResponse
        from amplifier_module_provider_github_copilot import GitHubCopilotProvider
        from unittest.mock import AsyncMock, MagicMock, patch
        
        provider = GitHubCopilotProvider()
        
        # Mock the internal SDK call
        with patch.object(provider, '_complete_internal', new_callable=AsyncMock) as mock:
            # Simulate accumulated response
            mock.return_value = MagicMock(
                text_content="Hello",
                thinking_content="",
                tool_calls=[],
                usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                finish_reason="stop",
            )
            
            # Create minimal request
            request = MagicMock()
            request.messages = []
            request.tools = []
            
            response = await provider.complete(request)
            
            assert isinstance(response, ChatResponse), (
                f"complete() returned {type(response).__name__}, expected ChatResponse"
            )


class TestChatResponseContentTypes:
    """Tests that ChatResponse.content uses correct Pydantic block types."""

    def test_text_block_is_pydantic(self) -> None:
        """ChatResponse.content must use TextBlock (Pydantic), not TextContent (dataclass)."""
        from amplifier_core import TextBlock
        from pydantic import BaseModel
        
        # TextBlock must be Pydantic
        assert issubclass(TextBlock, BaseModel), "TextBlock must be Pydantic BaseModel"
        
        # Must have type discriminator
        block = TextBlock(text="hello")
        assert block.type == "text"

    def test_thinking_block_is_pydantic(self) -> None:
        """ChatResponse.content must use ThinkingBlock (Pydantic), not ThinkingContent (dataclass)."""
        from amplifier_core import ThinkingBlock
        from pydantic import BaseModel
        
        # ThinkingBlock must be Pydantic
        assert issubclass(ThinkingBlock, BaseModel), "ThinkingBlock must be Pydantic BaseModel"
        
        # Must have type discriminator
        block = ThinkingBlock(thinking="reasoning here")
        assert block.type == "thinking"


class TestUsageRequiredFields:
    """Tests that Usage has all required fields."""

    def test_usage_requires_three_fields(self) -> None:
        """Usage must have input_tokens, output_tokens, total_tokens."""
        from amplifier_core import Usage
        
        # All three are required (no defaults)
        usage = Usage(input_tokens=10, output_tokens=5, total_tokens=15)
        
        assert usage.input_tokens == 10
        assert usage.output_tokens == 5
        assert usage.total_tokens == 15
```

**Run to verify failure:**
```bash
pytest tests/test_f038_kernel_integration.py -v
# Expected: Multiple FAILED (isinstance checks fail, parse_tool_calls not method, etc.)
```

### Step 2: Migrate error_translation.py (GREEN partial)

1. Delete lines 41-97 (local error class definitions via `_make_error_class()`)
2. Add kernel imports at top:
   ```python
   from amplifier_core.llm_errors import (
       LLMError,
       AuthenticationError,
       RateLimitError,
       # ... all 15 types including AccessDeniedError
   )
   ```
3. Update `KERNEL_ERROR_MAP` to reference kernel classes directly:
   ```python
   KERNEL_ERROR_MAP: dict[str, type[LLMError]] = {
       "AuthenticationError": AuthenticationError,
       "RateLimitError": RateLimitError,
       # ... etc
   }
   ```
4. Keep all YAML-driven translation logic unchanged

### Step 3: Migrate tool_parsing.py (GREEN partial)

1. Replace local `ToolCall` dataclass with kernel import:
   ```python
   from amplifier_core import ToolCall
   ```
2. Delete local `ToolCall` dataclass definition
3. Update `parse_tool_calls()` to construct kernel `ToolCall`:
   ```python
   def parse_tool_calls(response: Any) -> list[ToolCall]:
       # ... existing logic ...
       return [
           ToolCall(
               id=tc.id,
               name=tc.name,
               arguments=tc.arguments if isinstance(tc.arguments, dict) else {},
           )
           for tc in tool_calls
       ]
   ```
4. Add validation for malformed arguments (None, list, invalid JSON) → raise `ValueError`

### Step 4: Add ChatResponse conversion in streaming.py

Add method to `StreamingAccumulator` using **correct Pydantic types**:

```python
def to_chat_response(self) -> "ChatResponse":
    """Convert accumulated response to kernel ChatResponse.
    
    Feature: F-038
    
    IMPORTANT: Uses TextBlock/ThinkingBlock (Pydantic from message_models),
    NOT TextContent/ThinkingContent (dataclass from content_models).
    """
    from amplifier_core import (
        ChatResponse,
        TextBlock,      # Pydantic, has type="text"
        ThinkingBlock,  # Pydantic, has type="thinking"
        ToolCall,
        Usage,
    )
    
    content = []
    
    # Add text content using Pydantic TextBlock
    if self.text_content:
        content.append(TextBlock(text=self.text_content))
    
    # Add thinking content using Pydantic ThinkingBlock
    if self.thinking_content:
        content.append(ThinkingBlock(thinking=self.thinking_content))
    
    # Convert tool calls to kernel ToolCall
    tool_calls = None
    if self.tool_calls:
        tool_calls = [
            ToolCall(
                id=tc.get("id", ""),
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}) if isinstance(tc.get("arguments"), dict) else {},
            )
            for tc in self.tool_calls
        ]
    
    # Convert usage - all three fields REQUIRED
    usage = None
    if self.usage:
        usage = Usage(
            input_tokens=self.usage.get("input_tokens", 0),
            output_tokens=self.usage.get("output_tokens", 0),
            total_tokens=self.usage.get("total_tokens", 0),
        )
    
    return ChatResponse(
        content=content,
        tool_calls=tool_calls,
        usage=usage,
        finish_reason=self.finish_reason,
    )
```

### Step 5: Migrate provider.py (GREEN complete)

**KEEP internal types** (`CompletionRequest`, `CompletionConfig`). Only change boundary methods.

1. Delete local `ProviderInfo`, `ModelInfo` dataclasses
2. Import kernel types
3. Update `get_info()` to return kernel `ProviderInfo`:
   ```python
   def get_info(self) -> ProviderInfo:
       return ProviderInfo(
           id="github-copilot",
           display_name="GitHub Copilot SDK",
           credential_env_vars=["GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN"],
           capabilities=["streaming", "tool_use"],
           defaults={...},
           config_fields=[],
       )
   ```
4. Update `list_models()` to return kernel `ModelInfo`:
   ```python
   async def list_models(self) -> list[ModelInfo]:
       return [
           ModelInfo(
               id="gpt-4o",
               display_name="GPT-4o",
               context_window=128000,
               max_output_tokens=16384,
               capabilities=["streaming", "tool_use"],
               defaults={},
           ),
           # ... etc
       ]
   ```
5. Add `complete()` wrapper that uses internal machinery and converts at boundary:
   ```python
   async def complete(self, request: Any, **kwargs: Any) -> ChatResponse:
       """Provider Protocol: complete() returns ChatResponse."""
       # Use internal streaming machinery (preserved)
       accumulator = StreamingAccumulator()
       async for event in self._complete_internal(request, **kwargs):
           accumulator.add(event)
       
       # Convert at boundary
       return accumulator.to_chat_response()
   
   async def _complete_internal(self, request: Any, **kwargs: Any) -> AsyncIterator[DomainEvent]:
       """Internal: preserved streaming implementation."""
       # ... existing implementation moved here ...
   ```
6. **Move `parse_tool_calls()` to provider class** as method:
   ```python
   def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]:
       """Provider Protocol: parse tool calls from response."""
       from .tool_parsing import parse_tool_calls as _parse
       return _parse(response)
   ```

### Step 6: Update __init__.py

```python
# Remove local types from exports
from .provider import GitHubCopilotProvider

# Re-export from kernel for convenience (optional)
try:
    from amplifier_core import ProviderInfo, ModelInfo
except ImportError:
    pass  # Kernel provides at runtime

__all__ = ["mount", "GitHubCopilotProvider"]
```

### Step 7: Update Existing Tests

Update tests that import local types:
- `tests/test_protocol_compliance.py` → import from kernel or use duck typing
- `tests/test_tool_parsing.py` → import `ToolCall` from kernel
- `tests/test_provider.py` → update `ProviderInfo` field checks

### Step 8: Run All Tests (GREEN)

```bash
pytest tests/test_f038_kernel_integration.py -v
# Expected: All PASS

pytest tests/ -v
# Expected: All PASS

ruff check src/ && pyright src/
# Expected: Exit 0
```

---

## 6. Acceptance Criteria

| # | Criterion | Verification Command | Expected |
|---|-----------|---------------------|----------|
| AC-1 | `get_info()` returns `amplifier_core.ProviderInfo` | `pytest tests/test_f038_kernel_integration.py::TestKernelTypeCompliance::test_provider_info_is_kernel_type -v` | PASS |
| AC-2 | `translate_sdk_error()` returns kernel error types | `pytest tests/test_f038_kernel_integration.py::TestKernelTypeCompliance::test_error_translation_produces_kernel_errors -v` | PASS |
| AC-3 | `parse_tool_calls()` is method returning `amplifier_core.ToolCall` | `pytest tests/test_f038_kernel_integration.py::TestKernelTypeCompliance::test_tool_call_is_kernel_type -v` | PASS |
| AC-4 | `complete()` returns `ChatResponse` | `pytest tests/test_f038_kernel_integration.py::TestKernelTypeCompliance::test_complete_returns_chat_response -v` | PASS |
| AC-5 | `ChatResponse.content` uses `TextBlock`/`ThinkingBlock` | `pytest tests/test_f038_kernel_integration.py::TestChatResponseContentTypes -v` | PASS |
| AC-6 | All existing tests pass | `pytest tests/ -v` | All PASS |
| AC-7 | Build passes | `ruff check src/ && pyright src/` | Exit 0 |
| AC-8 | YAML error translation preserved | `pytest tests/test_error_translation.py -v` | All PASS |

---

## 7. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| `amplifier_core` not installed at test time | Tests skip with `pytest.importorskip()` |
| ChatRequest has empty messages | Return ChatResponse with empty content |
| SDK returns no tool calls | `tool_calls=None` in ChatResponse |
| Error during streaming | Translate to kernel error type, raise |
| Unknown SDK error | Fall through to `ProviderUnavailableError(retryable=True)` |
| `tool_call.arguments` is None | Normalize to `{}` |
| `tool_call.arguments` is list/scalar | Raise `ValueError` (invalid) |
| Usage missing fields | Zero-fill: `input_tokens=0, output_tokens=0, total_tokens=0` |

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing tests | HIGH | Update tests atomically with code changes |
| `amplifier_core` version mismatch | MEDIUM | Pin to `>=1.0.7` (confirmed exists) |
| Pydantic validation failures | MEDIUM | Match field types exactly to kernel |
| `complete()` signature change breaks internal callers | LOW | Keep internal `_complete_internal()`, only change public method |
| Import-time failures | MEDIUM | Use submodule imports, add import smoke test |

---

## 9. Out of Scope

- Changing YAML config structure (errors.yaml, events.yaml)
- Adding new error types beyond kernel types
- Production hardening (circuit breaker, process singleton)
- Model caching improvements
- Internal type restructuring (keep `CompletionRequest`, `CompletionConfig`, `DomainEvent`)

---

## 10. Notes

### Why This Wasn't Caught Earlier

1. **Scaffolding became permanent**: Code comments say "TODO: Replace with amplifier_core.llm_errors" but it was never done
2. **Tests use mocks**: `MagicMock()` coordinators don't validate types
3. **No integration test against real kernel**: Tests never ran `isinstance()` checks
4. **38 features built on diverged types**: Each feature added more local type usage

### Three-Medium Architecture Preserved

This migration changes MECHANISM (which classes to use), not POLICY (how error translation works). The YAML-driven error translation, config-first design, and Markdown contracts all survive intact.

```
Before: errors.yaml → local AuthenticationError
After:  errors.yaml → amplifier_core.AuthenticationError
```

### Internal Architecture Preserved

Per Zen Architect guidance, internal types are KEPT:
- `CompletionRequest` — internal request format
- `CompletionConfig` — internal config
- `DomainEvent` — internal streaming events
- `AccumulatedResponse` — internal accumulator

Only the PUBLIC boundary is changed (provider methods return kernel types).
