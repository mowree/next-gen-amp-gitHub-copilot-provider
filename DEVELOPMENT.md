# Development Guide

This guide covers local development setup and contributing to provider-github-copilot.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Git

## Setup

```bash
# Clone the repository
git clone https://github.com/microsoft/amplifier-module-provider-github-copilot.git
cd amplifier-module-provider-github-copilot

# Create virtual environment and install dependencies
uv venv
uv pip install -e ".[dev]"
```

## Code Quality

Run before committing:

```bash
# Linting and formatting
uv run ruff check src/
uv run ruff format --check src/

# Type checking
uv run pyright src/

# All checks (CI equivalent)
uv run ruff check src/ && uv run pyright src/ && uv run pytest tests/ -m "not live" -v
```

## Testing

### Test Tiers

| Tier | Type | Speed | When Run |
|------|------|-------|----------|
| 1 | Pure function unit tests | <10ms | Every commit |
| 2 | Integration tests (stubbed) | <500ms | Every commit |
| 3 | Config compliance tests | <100ms | Every commit |
| 4 | Contract compliance tests | <100ms | Every PR |
| 5 | Property-based tests | <100ms | Every PR |
| 6 | SDK assumption tests | <200ms | Every PR |
| 7 | Live smoke tests | <60s | Nightly |

### Running Tests

```bash
# Run all tests except live SDK tests (no credentials needed)
uv run pytest tests/ -m "not live" -v

# Run specific test tiers
uv run pytest tests/ -m "pure" -v        # Tier 1: Pure functions
uv run pytest tests/ -m "contract" -v    # Tier 4: Contract compliance
uv run pytest tests/ -m "sdk_assumption" -v  # Tier 6: SDK assumptions

# Run live SDK tests (requires GITHUB_TOKEN)
export GITHUB_TOKEN="your-token"
uv run pytest tests/ -m "live" -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.pure` | Pure function tests, no I/O |
| `@pytest.mark.contract` | Contract compliance tests |
| `@pytest.mark.canary` | SDK canary tests |
| `@pytest.mark.live` | Live SDK tests (require credentials) |
| `@pytest.mark.sdk_assumption` | SDK shape verification |

## Project Structure

```
provider-github-copilot/
├── src/amplifier_module_provider_github_copilot/
│   ├── __init__.py           # mount() entry point
│   ├── provider.py           # Provider orchestrator
│   ├── streaming.py          # Event translation
│   ├── error_translation.py  # Error mapping
│   ├── tool_parsing.py       # Tool call extraction
│   └── sdk_adapter/          # SDK boundary (all SDK imports here)
│       ├── client.py         # SDK client wrapper
│       ├── types.py          # Domain types
│       └── loop_control.py   # Circuit breaker
├── config/                   # YAML policies
│   ├── errors.yaml           # Error mappings
│   └── events.yaml           # Event routing
├── contracts/                # Behavioral specifications
│   ├── provider-protocol.md
│   ├── deny-destroy.md
│   └── ...
└── tests/                    # Test suite (256 tests)
```

## Contributing

### Workflow

1. Read the relevant contract in `contracts/`
2. Write failing tests first (TDD)
3. Implement minimal code to pass tests
4. Run full quality checks
5. Submit PR

### SDK Boundary Rules

- **All SDK imports must be in `sdk_adapter/`**
- Domain code never imports from the SDK
- Use domain types (`DomainEvent`, `SessionConfig`) not SDK types

### Code Style

- Max module size: 400 lines (soft), 600 lines (hard)
- Use type hints everywhere
- Follow ruff/pyright strict settings

## Contracts

The `contracts/` directory contains behavioral specifications:

| Contract | Purpose |
|----------|---------|
| `provider-protocol.md` | 4 methods + 1 property interface |
| `deny-destroy.md` | Ephemeral session pattern |
| `error-hierarchy.md` | Error classification |
| `event-vocabulary.md` | 6 stable event types |
| `streaming-contract.md` | Delta accumulation |

Every test should trace to a contract clause.

## Troubleshooting

### "No GITHUB_TOKEN" skips

Live tests require credentials. For local development, use:
```bash
uv run pytest tests/ -m "not live" -v
```

### Pyright warnings

Two warnings in `sdk_adapter/client.py` are expected (SDK partial types). Do not suppress them.

### Test failures after SDK update

1. Run SDK assumption tests: `uv run pytest tests/ -m "sdk_assumption" -v`
2. If shapes changed, update `config/events.yaml` or `config/errors.yaml`
3. Re-run contract tests to verify compliance
