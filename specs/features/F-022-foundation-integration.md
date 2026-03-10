# F-022: Foundation Integration

**Priority**: HIGH
**Source**: foundation-expert, amplifier-expert
**Estimated Lines**: ~100

## Objective

Make this provider a proper Foundation-composable module with bundle.md and skills.

## Acceptance Criteria

### AC-1: Create bundle.md

**Problem**: Missing bundle definition for composition.

**Fix**: Create `bundle.md` at project root:

```markdown
---
bundle:
  name: provider-github-copilot
  version: 0.1.0
  description: GitHub Copilot provider for Amplifier

providers:
  - module: provider-github-copilot
    source: ./
    config:
      # Optional provider config
      
context:
  - contracts/provider-protocol.md
  - contracts/deny-destroy.md
---

# GitHub Copilot Provider

A provider module implementing the Three-Medium Architecture for GitHub Copilot SDK integration.

## Usage

Include in your bundle:

\`\`\`yaml
providers:
  - module: provider-github-copilot
    source: git+https://github.com/your-org/provider-github-copilot
\`\`\`

## Configuration

Environment variables:
- `GITHUB_TOKEN` or `COPILOT_AGENT_TOKEN` — authentication

## Contracts

- `contracts/deny-destroy.md` — sovereignty guarantee
- `contracts/provider-protocol.md` — protocol compliance
```

### AC-2: Export __all__ in __init__.py

**Problem**: No explicit exports.

**Fix**:
```python
__all__ = ["mount", "GitHubCopilotProvider"]
__amplifier_module_type__ = "provider"
```

### AC-3: Create three-medium-extension Skill

**Problem**: No guidance for extending this provider.

**Fix**: Create `.amplifier/skills/three-medium-extension/skill.md`:

```markdown
---
skill:
  name: three-medium-extension
  version: 1.0.0
  description: How to extend the provider respecting Three-Medium Architecture
---

# Extending provider-github-copilot

## The Three Mediums

1. **Python (Mechanism)**: ~300 lines of orchestration
   - Lives in: `src/amplifier_module_provider_github_copilot/`
   - Only translation logic, no policy

2. **YAML (Policy)**: ~200 lines of configuration
   - Lives in: `config/`
   - Error mappings, event classifications, retry configs

3. **Markdown (Contracts)**: ~400 lines of specification
   - Lives in: `contracts/`
   - What MUST happen, what MUST NOT happen

## Adding New Features

1. **First**: Write the contract in `contracts/`
2. **Second**: Add policy to `config/` if needed
3. **Third**: Implement mechanism in `src/`
4. **Always**: Tests trace back to contracts

## Anti-Patterns

- ❌ Hardcoding policy in Python
- ❌ Skipping contract documentation
- ❌ Adding classes when functions suffice
```

### AC-4: Fix Config Path Fragility

**Problem**: `Path(__file__).parent.parent.parent` is fragile.

**Fix**: Use `importlib.resources`:

```python
from importlib import resources

def load_error_config() -> ErrorConfig:
    try:
        config_text = resources.read_text(
            'amplifier_module_provider_github_copilot.config',
            'errors.yaml'
        )
        data = yaml.safe_load(config_text)
        # ... parse
    except (FileNotFoundError, ImportError):
        return ErrorConfig()
```

Create `config/__init__.py` to make it a package.

## Files to Create

- `bundle.md`
- `config/__init__.py`
- `.amplifier/skills/three-medium-extension/skill.md`

## Files to Modify

- `src/amplifier_module_provider_github_copilot/__init__.py`
- `src/amplifier_module_provider_github_copilot/error_translation.py`
- `src/amplifier_module_provider_github_copilot/sdk_adapter/client.py`

## Dependencies

- F-020 (must have mount() first)

## NOT IN SCOPE

- Coordinator event emission (Phase 2)
