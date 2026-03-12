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
