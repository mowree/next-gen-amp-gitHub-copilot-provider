# Bundle & Pattern Compliance Review

**Date:** 2026-03-14
**Reviewer:** Foundation Expert
**Project:** next-get-provider-github-copilot (provider-github-copilot)

---

## 1. Bundle Structure

### Current: `bundle.md`

```yaml
bundle:
  name: provider-github-copilot
  version: 0.1.0
  description: GitHub Copilot provider for Amplifier

providers:
  - module: provider-github-copilot
    source: ./
    config: {}

context:
  include:
    - contracts/provider-protocol.md
    - contracts/deny-destroy.md
```

### Verdict: PASS (with recommendations)

**Correct:**
- Frontmatter format is valid (YAML between `---` fences)
- `bundle.name` and `bundle.version` present
- Provider module declared with entry point name matching `pyproject.toml`
- Context includes are relative paths to local files
- Markdown body provides usage documentation

**Issues:**

| # | Severity | Issue | Recommendation |
|---|----------|-------|----------------|
| 1 | **Medium** | `source: ./` is a local path — works for development but won't resolve when consumed by other bundles via `includes:` | Change to `source: pypi:amplifier-module-provider-github-copilot` after PyPI publish, or `source: git+https://github.com/...` for git-based distribution |
| 2 | **Low** | Usage example in markdown body shows `source: git+https://github.com/your-org/...` (placeholder) | Update to actual repo URL once published |
| 3 | **Low** | No `bundle.description` line break — minor style preference | Fine as-is |

---

## 2. Module Source Declaration (`pyproject.toml`)

### Current State

```toml
[project]
name = "amplifier-module-provider-github-copilot"
version = "0.1.0"

[project.entry-points."amplifier.modules"]
provider-github-copilot = "amplifier_module_provider_github_copilot:mount"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["amplifier_module_provider_github_copilot"]
```

### Verdict: MOSTLY CORRECT — needs PyPI readiness fixes

**Correct:**
- Entry point name `provider-github-copilot` matches bundle's `module:` field
- Entry point target `amplifier_module_provider_github_copilot:mount` is the correct pattern
- Hatchling build system matches all reference providers
- `packages` wheel target correctly scoped

**Comparison with reference (production) provider:**

| Field | Your Project | Reference (production) | Status |
|-------|-------------|----------------------|--------|
| `name` | `amplifier-module-provider-github-copilot` | `amplifier-module-provider-github-copilot` | MATCH |
| `version` | `0.1.0` | `1.0.4` | OK (dev) |
| `entry-points` | `provider-github-copilot` | `provider-github-copilot` | MATCH |
| `authors` | **Missing** | `Microsoft MADE:Explorations Team` | **ADD** |
| `keywords` | **Missing** | `["amplifier", "copilot", ...]` | **ADD** |
| `classifiers` | **Missing** | Present | **ADD** |
| `[project.urls]` | **Missing** | Homepage, Repository, Issues | **ADD** |
| `[tool.uv]` | **Missing** | Not in reference either | OK |
| `license` | `{text = "MIT"}` | `{text = "MIT"}` | MATCH |
| `requires-python` | `>=3.11` | `>=3.11` | MATCH |
| `amplifier-core` in deps | dev-only (correct) | dev-only (correct) | MATCH |

**PyPI Publishing Blockers:**

1. **Missing `authors`** — PyPI requires this
2. **Missing `[project.urls]`** — Not strictly required but expected for discoverability
3. **Missing `keywords`** — Helps PyPI search
4. **Missing `classifiers`** — Helps PyPI categorization
5. **`amplifier-core>=1.0.7` in dev deps** — Reference uses `git+` reference; verify `1.0.7` exists on PyPI before publishing

---

## 3. Thin Bundle Pattern

### Verdict: PASS — correctly minimal

This is a **provider-only bundle**, not a full application bundle. It correctly:

- **Does NOT include foundation** — Provider bundles should not declare tools, session config, or agents. The consuming application (e.g., foundation bundle) composes the provider.
- **Does NOT redeclare tools or session** — No `tools:`, no `session:` block
- **Only declares what it uniquely provides** — One provider module + two contract context files
- **Separates policy from mechanism:**
  - **Mechanism (Python):** `amplifier_module_provider_github_copilot/` — SDK adapter, streaming, error translation
  - **Policy (YAML):** `config/models.yaml`, `config/errors.yaml`, `config/events.yaml`, `config/retry.yaml`
  - **Contracts (Markdown):** `contracts/` — behavioral specifications

This is exemplary Three-Medium Architecture. The separation is cleaner than the production reference provider (which puts everything in Python).

---

## 4. Agent Definitions

### Verdict: N/A — No agents (correct)

Provider bundles should not define agents. Agents are orchestrator/application concerns. This bundle correctly has zero agent definitions.

---

## 5. Behavior Composition

### Verdict: N/A — Not a behavior bundle (correct)

This is a standalone provider module, not a behavior. It is consumed via:

```yaml
providers:
  - module: provider-github-copilot
    source: <pypi-or-git-url>
```

Not via `includes:` behavior composition. This is the correct pattern for providers.

**If you wanted to make it composable as a behavior** (optional, not recommended for providers):
- You would create `behaviors/github-copilot-provider.yaml` that wraps the provider declaration
- This is unnecessary — providers are mounted directly, not composed via behaviors

---

## 6. Namespace Usage

### Verdict: PASS (with one note)

**Correct:**
- Context includes use relative paths (`contracts/provider-protocol.md`) — correct for files within the same bundle
- No `@namespace:` references needed since all files are local
- No cross-bundle references attempted

**Note:** When published, consuming bundles will reference this as:
```yaml
providers:
  - module: provider-github-copilot
    source: pypi:amplifier-module-provider-github-copilot
```
The module name in the entry point (`provider-github-copilot`) becomes the namespace for any bundle-level references.

---

## 7. Code Pattern Compliance

### mount() Function

| Check | Status | Notes |
|-------|--------|-------|
| Signature `mount(coordinator, config)` | PASS | Matches all reference providers |
| Returns cleanup callable or None | PASS | Returns `async def cleanup()` or `None` on error |
| Graceful degradation on failure | PASS | Catches exceptions, logs, returns `None` |
| `__amplifier_module_type__ = "provider"` | PASS | Module metadata present |
| Entry point registered | PASS | `pyproject.toml` entry-points correct |

### Provider Protocol (4 Methods + 1 Property)

| Method | Status | Notes |
|--------|--------|-------|
| `name` (property) | PASS | Returns `"github-copilot"` |
| `get_info()` → `ProviderInfo` | PASS | Uses kernel type from `amplifier_core` |
| `list_models()` → `list[ModelInfo]` | PASS | Uses kernel type from `amplifier_core` |
| `complete(request, **kwargs)` → `ChatResponse` | PASS | Kernel type, ephemeral sessions |
| `parse_tool_calls(response)` → `list[ToolCall]` | PASS | Kernel type, delegates to module |

### Deny+Destroy Pattern

| Check | Status |
|-------|--------|
| Deny hook installed on sessions | PASS |
| Session ephemerality | PASS |
| `available_tools=[]` suppression | Verify in `sdk_adapter/client.py` |

---

## 8. Differences from Production Reference

| Aspect | Your Project | Production Reference |
|--------|-------------|---------------------|
| Architecture | Three-Medium (Python/YAML/Markdown) | Single-Medium (all Python) |
| Config | YAML files in `config/` | Hardcoded in Python |
| Error handling | YAML-driven error translation | Python exception hierarchy |
| SDK adapter | Separate `sdk_adapter/` package | Flat module structure |
| Contracts | Formal markdown contracts | Inline docstrings |
| Process singleton | Not implemented | `_shared_client` pattern with refcount |
| CLI binary discovery | Not implemented | `_platform.py` + `_permissions.py` |
| Model naming | Not implemented | `model_naming.py` with pattern matching |

**Your architecture is arguably better-structured** for maintainability (separation of concerns), but the production reference has more features (process singleton, model naming, CLI discovery).

---

## 9. PyPI Publishing Recommendations

### Required Changes

1. **Add missing `pyproject.toml` fields:**

```toml
[project]
name = "amplifier-module-provider-github-copilot"
version = "0.1.0"
description = "GitHub Copilot provider for Amplifier - Three-Medium Architecture"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    { name = "Your Name or Org" },
]
keywords = ["amplifier", "copilot", "github", "llm", "ai", "provider"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]

[project.urls]
Homepage = "https://github.com/your-org/provider-github-copilot"
Repository = "https://github.com/your-org/provider-github-copilot"
```

2. **Update `bundle.md` source for distribution:**

```yaml
providers:
  - module: provider-github-copilot
    source: pypi:amplifier-module-provider-github-copilot
```

3. **Include `config/` directory in wheel:**

Currently `config/` is a sibling to the Python package, not inside it. The `provider.py` loads configs via `Path(__file__).parent.parent / "config"`. This works in development but **will NOT work from an installed wheel** because:
- Wheels only include files listed in `[tool.hatch.build.targets.wheel].packages`
- `config/` is not inside `amplifier_module_provider_github_copilot/`

**Fix options:**
- **(A) Move `config/` inside the Python package:** `amplifier_module_provider_github_copilot/config/` — simplest, recommended
- **(B) Add `config/` to wheel includes** via `[tool.hatch.build.targets.wheel].artifacts`
- **(C) Use `importlib.resources`** to load config files as package data

**Option A is strongly recommended** — it matches how Python packages work and requires no build system changes.

4. **Include `contracts/` in distribution** (if context includes should resolve):

Same issue as `config/` — `contracts/` is outside the Python package. If the bundle's `context.include` paths need to resolve from an installed package, they need to be inside the wheel.

**For bundle distribution**, contracts would typically be referenced via `@provider-github-copilot:contracts/...` which requires the bundle loader to know the bundle root. This works for git-based sources but needs verification for PyPI sources.

### Pre-Publish Checklist

- [ ] Move `config/` inside Python package (or configure as package data)
- [ ] Add `authors`, `keywords`, `classifiers`, `[project.urls]` to `pyproject.toml`
- [ ] Update `bundle.md` source to PyPI or git URL
- [ ] Verify `amplifier-core>=1.0.7` exists on PyPI (or remove version pin)
- [ ] Add `py.typed` marker file for type-checking consumers
- [ ] Test `pip install .` in clean venv and verify `mount()` works
- [ ] Test config loading from installed wheel (not just development tree)
- [ ] Build wheel: `python -m build` and inspect contents

---

## Summary

| Category | Grade | Notes |
|----------|-------|-------|
| Bundle format | A | Valid, minimal, correct |
| Thin bundle pattern | A+ | Exemplary — only declares what it provides |
| Policy/mechanism separation | A+ | Three-Medium Architecture well-applied |
| Module entry point | A | Matches all reference providers |
| Provider protocol | A | All 4+1 implemented with kernel types |
| PyPI readiness | C | Missing metadata, config packaging issue |
| Agent definitions | N/A | Correctly absent |
| Behavior composition | N/A | Correctly not a behavior |

**Bottom line:** The bundle structure and pattern compliance are excellent. The main gap is PyPI packaging — specifically the `config/` directory location and missing project metadata. Fix those and this is ready to publish.
