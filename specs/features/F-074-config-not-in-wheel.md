# F-074: Config Not Included in Wheel

**Status:** ready
**Priority:** P0
**Source:** deep-review/code-quality-reviewer.md

## Problem Statement
`pyproject.toml` packages only `amplifier_module_provider_github_copilot`. The `config/` directory with errors.yaml, events.yaml, models.yaml is NOT included in wheel builds. When installed from wheel, `_load_error_config_once()` fails to find config, silently falls back to defaults, and ALL SDK errors pass through untranslated.

Evidence:
- pyproject.toml line 36: `packages = ["amplifier_module_provider_github_copilot"]`
- config/ is at repo root, not inside the package
- `resources.files("config")` fails in wheel context

Contract violated: `contracts/error-hierarchy.md` — errors MUST be translated

## Success Criteria
- [ ] `config/` directory lives inside `amplifier_module_provider_github_copilot/config/`
- [ ] Wheel builds include all config YAML files (errors.yaml, events.yaml, models.yaml)
- [ ] All `importlib.resources` references updated to `amplifier_module_provider_github_copilot.config`
- [ ] All `Path(__file__).parent.parent / "config"` references updated
- [ ] `pip install` from wheel correctly loads error config and translates errors
- [ ] Existing tests pass with new config location

## Implementation Approach
1. Move `config/` into `amplifier_module_provider_github_copilot/config/`
2. Add `__init__.py` to the new config directory (required for `importlib.resources`)
3. Update all path references in source code to use `importlib.resources.files("amplifier_module_provider_github_copilot.config")`
4. Update any `Path`-based config loading to use the new location
5. Verify pyproject.toml package discovery includes the nested config

## Files to Modify
- `config/` → move to `amplifier_module_provider_github_copilot/config/`
- `amplifier_module_provider_github_copilot/config/__init__.py` (new, empty or minimal)
- `amplifier_module_provider_github_copilot/error_translation.py` (update config path references)
- `amplifier_module_provider_github_copilot/events.py` (update config path references if applicable)
- `amplifier_module_provider_github_copilot/provider.py` (update any config path references)
- `pyproject.toml` (verify package-data or include directives if needed)
- Any test files referencing `config/` paths

## TDD Anchor
- Red: Install package from wheel, call `load_error_config()` → fails to find config
- Green: Move config inside package, update references → config loads correctly
- Refactor: Consolidate any duplicated config-loading paths

## Contract Traceability
- `contracts/error-hierarchy.md` — "The provider MUST translate SDK errors into kernel error types"

## Not In Scope
- Changing config file contents or format
- Adding new config files
- Retry config wiring (see F-075)
