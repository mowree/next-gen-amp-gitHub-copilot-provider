# F-064: PyPI Publishing Readiness

**Status:** ready
**Priority:** P2
**Source:** deep-review/foundation-expert.md
**Defect ID:** N/A

## Problem Statement
The package cannot be correctly installed from PyPI due to:
1. `config/` directory is outside the Python package — not included in wheels
2. `pyproject.toml` is missing `authors`, `keywords`, `classifiers`, `[project.urls]`
3. `bundle.md` uses `source: ./` (local path only)
4. Config loading via `Path(__file__).parent.parent / "config"` breaks when installed from wheel

## Success Criteria
- [ ] `config/` directory moved inside `amplifier_module_provider_github_copilot/`
- [ ] Config loading updated to use package-relative paths
- [ ] `pyproject.toml` has all required PyPI metadata fields
- [ ] `bundle.md` updated with distribution-ready source URL
- [ ] `pip install .` in clean venv works and provider mounts correctly
- [ ] Config loading works from installed wheel

## Implementation Approach
1. Move `config/` to `amplifier_module_provider_github_copilot/config/`
2. Update all config loading paths (use `importlib.resources` or `Path(__file__).parent / "config"`)
3. Add missing pyproject.toml metadata
4. Update bundle.md source reference

## Files to Modify
- Move: `config/` → `amplifier_module_provider_github_copilot/config/`
- `amplifier_module_provider_github_copilot/provider.py` (config path references)
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py` (config path references)
- `pyproject.toml` (add metadata)
- `bundle.md` (update source)

## Tests Required
- `tests/test_config_loading.py` (new) or additions to existing config tests:
  - Test: config loads from package-relative path
  - Smoke test: `pip install .` in clean venv

## Not In Scope
- Actual PyPI publishing
- Moving `contracts/` into the package
