# F-025: CI Pipeline Stage 1

**Priority**: ESSENTIAL
**Source**: zen-architect, test-coverage
**Estimated Lines**: ~100 (GitHub Actions workflow)

## Objective

Create a fast-feedback CI pipeline that gates all merges. Target: <90 seconds.

## Acceptance Criteria

### AC-1: GitHub Actions Workflow

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  fast-feedback:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Install dependencies
        run: |
          uv venv
          uv pip install -e ".[dev]"
      
      - name: Lint (ruff)
        run: uv run ruff check src/ tests/
      
      - name: Format check (ruff)
        run: uv run ruff format --check src/ tests/
      
      - name: Type check (pyright)
        run: uv run pyright src/
      
      - name: YAML schema validation
        run: |
          uv pip install yamale pyyaml
          python -c "
          import yaml
          from pathlib import Path
          for f in Path('config').glob('*.yaml'):
              yaml.safe_load(f.read_text())
              print(f'✓ {f}')
          "
      
      - name: Unit tests
        run: uv run pytest tests/ -v --timeout=30 -x
```

### AC-2: Branch Protection

Document required branch protection settings:
- Require status checks to pass
- Require branches to be up to date
- Required checks: `fast-feedback`

### AC-3: Badge in README

Add CI status badge to README.md:

```markdown
[![CI](https://github.com/YOUR_ORG/provider-github-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/provider-github-copilot/actions/workflows/ci.yml)
```

## Files to Create

- `.github/workflows/ci.yml`

## Files to Modify

- `README.md` (add badge)

## Success Criteria

- Pipeline runs on every push to main and every PR
- Total runtime < 90 seconds
- All checks pass on current codebase

## NOT IN SCOPE

- Multi-platform matrix (Phase 4)
- Nightly live smoke tests (Phase 4)
- Auto-deployment (Phase 4)
