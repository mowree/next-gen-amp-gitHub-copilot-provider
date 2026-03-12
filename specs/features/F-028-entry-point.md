# F-028: Entry Point Registration

**Priority**: ESSENTIAL
**Source**: zen-architect, amplifier-expert
**Estimated Lines**: ~20

## Objective

Register the provider as an Amplifier module so the kernel can discover it.

## Acceptance Criteria

### AC-1: Add Entry Point to pyproject.toml

Add to `pyproject.toml`:

```toml
[project.entry-points."amplifier.modules"]
github-copilot = "amplifier_module_provider_github_copilot:mount"
```

### AC-2: Verify mount() Function Exists

Confirm `src/amplifier_module_provider_github_copilot/__init__.py` exports:

```python
from .provider import GitHubCopilotProvider

async def mount(coordinator, config=None):
    """Mount the GitHub Copilot provider."""
    provider = GitHubCopilotProvider(config, coordinator)
    await coordinator.mount("providers", provider, name="github-copilot")
    
    async def cleanup():
        await provider.close()
    
    return cleanup

__all__ = ["mount", "GitHubCopilotProvider"]
__amplifier_module_type__ = "provider"
```

### AC-3: Test Kernel Discovery

Create test to verify kernel can discover the provider:

```python
def test_entry_point_registered():
    """Kernel can discover provider via entry point."""
    from importlib.metadata import entry_points
    
    eps = entry_points(group="amplifier.modules")
    names = [ep.name for ep in eps]
    assert "github-copilot" in names


def test_entry_point_loads():
    """Entry point loads mount function."""
    from importlib.metadata import entry_points
    
    eps = entry_points(group="amplifier.modules")
    ep = next(ep for ep in eps if ep.name == "github-copilot")
    mount_fn = ep.load()
    
    assert callable(mount_fn)
    assert mount_fn.__name__ == "mount"
```

## Files to Modify

- `pyproject.toml` (add entry-points section)
- `src/amplifier_module_provider_github_copilot/__init__.py` (verify exports)

## Files to Create

- `tests/test_entry_point.py`

## Success Criteria

- `amplifier` CLI can discover the provider
- Entry point test passes
- Provider appears in `amplifier bundles list` output

## NOT IN SCOPE

- Advanced coordinator hooks
- Multi-provider registration
