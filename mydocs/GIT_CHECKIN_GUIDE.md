# Git Check-in Guide for amplifier-module-provider-github-copilot

## What Goes Into Git (Check These In)

| Path | Purpose |
|------|---------|
| `README.md` | Project documentation |
| `pyproject.toml` | Package definition, dependencies, build config |
| `uv.lock` | Lockfile for reproducible builds |
| `src/amplifier_module_provider_github_copilot/` | ALL Python source code |
| `config/` | YAML policy files (errors.yaml, events.yaml, retry.yaml, etc.) |
| `contracts/` | Markdown specifications (provider-protocol.md, deny-destroy.md, etc.) |
| `specs/` | Feature and module specs for dev-machine |
| `tests/` | All test files |
| `mydocs/debates/` | Decision records (GOLDEN_VISION_V2.md, etc.) — valuable architectural context |
| `.gitignore` | Git ignore rules |

## What Does NOT Go Into Git (Exclude These)

| Path | Reason |
|------|--------|
| `.venv/` | Local Python virtual environment |
| `__pycache__/` | Python bytecode cache |
| `*.pyc` | Compiled Python files |
| `.pytest_cache/` | Pytest cache |
| `.ruff_cache/` | Ruff linter cache |
| `reference-only/` | External reference repos — contributors clone these separately |
| `mydocs/` | Personal notes and working documents |
| `.dev-machine/` | Generated dev-machine artifacts (optional — could commit if you want recipes in repo) |
| `*.egg-info/` | Build artifacts |
| `dist/` | Distribution files |
| `build/` | Build output |

## .gitignore Template

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
*.egg

# Virtual environments
.venv/
venv/
ENV/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# Linting
.ruff_cache/
.mypy_cache/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Project-specific
reference-only/
mydocs/
.dev-machine/
```

## Why These Decisions?

### Why check in `config/`, `contracts/`, `specs/`?
These are part of the Three-Medium Architecture:
- **config/** = YAML policy files that define behavior
- **contracts/** = Markdown specifications that define requirements
- **specs/** = Feature specs for autonomous development

Contributors need all of these to understand and extend the project.

### Why check in `mydocs/debates/`?
The GOLDEN_VISION_V2.md and debate documents are architectural decision records. They explain WHY the architecture is designed this way. Future contributors (human or AI) need this context.

### Why exclude `reference-only/`?
These are clones of other Amplifier repos (amplifier-core, amplifier-foundation, etc.) used as reference material. Contributors should clone these separately if needed. They're large and change frequently.

### Why exclude `mydocs/`?
Personal working notes. Not relevant to other contributors.

---

*Document created: 2026-03-08*
*For project: amplifier-module-provider-github-copilot*
