# provider-github-copilot

[![CI](https://github.com/microsoft/amplifier-module-provider-github-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/microsoft/amplifier-module-provider-github-copilot/actions/workflows/ci.yml)

GitHub Copilot provider for Amplifier implementing the Three-Medium Architecture.

## Architecture

- **Python** (~300 lines) - Mechanism: control flow, state machines, protocol translation
- **YAML** (~200 lines) - Policy: error mappings, event routing, retry config
- **Markdown** (~400 lines) - Contracts: behavioral requirements, invariants

## Development

```bash
uv venv
uv pip install -e ".[dev]"
uv run ruff check src/
uv run pyright src/
uv run pytest tests/ -v
```

## Status

Scaffold phase - implementing from GOLDEN_VISION_V2.md specification.
