# F-020: Provider Protocol Compliance

**Priority**: CRITICAL
**Source**: amplifier-expert, core-expert, spec-reviewer
**Estimated Lines**: ~150

## Objective

Implement the full Amplifier Provider Protocol so this module can be mounted by the kernel.

## Acceptance Criteria

### AC-1: Implement mount() Entry Point (CRITICAL)

**Problem**: `pyproject.toml` declares entry point but `mount()` doesn't exist.

**Fix**: Add to `__init__.py`:

```python
from amplifier_core.coordinator import ModuleCoordinator

async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None) -> Callable | None:
    """Mount the GitHub Copilot provider.
    
    Args:
        coordinator: Amplifier kernel coordinator
        config: Optional provider configuration
        
    Returns:
        Cleanup callable, or None
    """
    provider = GitHubCopilotProvider(config, coordinator)
    await coordinator.mount("providers", provider, name="github-copilot")
    
    async def cleanup():
        await provider.close()
    
    return cleanup

__all__ = ["mount", "GitHubCopilotProvider"]
```

### AC-2: Implement get_info() Method (CRITICAL)

**Problem**: Missing required protocol method.

**Fix**: Add to `GitHubCopilotProvider`:

```python
async def get_info(self) -> ProviderInfo:
    """Return provider metadata."""
    return ProviderInfo(
        name="github-copilot",
        version="0.1.0",
        description="GitHub Copilot provider for Amplifier",
        capabilities=["streaming", "tool_use"],
    )
```

### AC-3: Implement list_models() Method (CRITICAL)

**Problem**: Missing required protocol method.

**Fix**: Add to `GitHubCopilotProvider`:

```python
async def list_models(self) -> list[ModelInfo]:
    """Return available models from GitHub Copilot."""
    return [
        ModelInfo(
            id="gpt-4",
            display_name="GPT-4",
            context_window=128000,
            max_output_tokens=4096,
        ),
        ModelInfo(
            id="gpt-4o",
            display_name="GPT-4o",
            context_window=128000,
            max_output_tokens=4096,
        ),
    ]
```

### AC-4: Refactor complete() as Class Method (CRITICAL)

**Problem**: `complete()` is a standalone function, not a class method.

**Fix**: Move `complete()` function logic into `GitHubCopilotProvider.complete()` method.

The method signature must match the kernel's `Provider` protocol:
```python
async def complete(
    self,
    request: ChatRequest,
    **kwargs
) -> AsyncIterator[ChatResponse]:
    """Stream completion response."""
    ...
```

### AC-5: Import Kernel Error Types (HIGH)

**Problem**: Using custom fallback error classes instead of `amplifier_core.llm_errors`.

**Fix**: Replace the fallback definitions in `error_translation.py`:

```python
# Remove: class LLMError, _make_error_class, etc.
# Add:
from amplifier_core.llm_errors import (
    LLMError,
    AuthenticationError,
    RateLimitError,
    QuotaExceededError,
    LLMTimeoutError,
    ContentFilterError,
    NetworkError,
    NotFoundError,
    ProviderUnavailableError,
)
```

## Files to Modify

- `src/amplifier_module_provider_github_copilot/__init__.py`
- `src/amplifier_module_provider_github_copilot/provider.py`
- `src/amplifier_module_provider_github_copilot/error_translation.py`
- `tests/test_protocol_compliance.py` (create)

## Contract References

- `reference-only/amplifier-core/docs/contracts/PROVIDER_CONTRACT.md`
- `reference-only/amplifier-module-provider-anthropic/` — reference implementation

## NOT IN SCOPE

- Event emission via coordinator hooks (Phase 2)
- Advanced model capabilities (Phase 2)
