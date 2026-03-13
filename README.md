# provider-github-copilot

[![CI](https://github.com/microsoft/amplifier-module-provider-github-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/microsoft/amplifier-module-provider-github-copilot/actions/workflows/ci.yml)

GitHub Copilot provider for Amplifier implementing the Three-Medium Architecture.

**Status:** Production Ready (Phase 3 Complete)

## Quick Start

```bash
# Install
uv pip install amplifier-module-provider-github-copilot

# Configure token
export GITHUB_TOKEN="your-github-copilot-token"

# Verify installation
uv run pytest tests/ -m "not live" -v
```

## Architecture

| Medium | Purpose | Size |
|--------|---------|------|
| **Python** | Mechanism: control flow, state machines, protocol translation | ~700 lines |
| **YAML** | Policy: error mappings, event routing, retry config | ~200 lines |
| **Markdown** | Contracts: behavioral requirements, invariants | ~400 lines |

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes | GitHub Copilot API token |
| `COPILOT_MODEL` | No | Model to use (default: gpt-4) |

## Running Tests

```bash
# All tests except live SDK tests (no token required)
uv run pytest tests/ -m "not live" -v

# Contract compliance tests only
uv run pytest tests/ -m "contract" -v

# Full suite including live tests (requires GITHUB_TOKEN)
uv run pytest tests/ -v
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.contract` | Contract compliance tests |
| `@pytest.mark.pure` | Pure function unit tests |
| `@pytest.mark.live` | Live SDK tests (require credentials) |
| `@pytest.mark.sdk_assumption` | SDK shape verification tests |

## Troubleshooting

**Live tests skip with "No GITHUB_TOKEN"**
- Set `GITHUB_TOKEN` environment variable with valid credentials
- Live tests are designed for nightly CI, not local development

**Pyright warnings about SDK types**
- Expected: SDK is pre-1.0 with partial type coverage
- 2 warnings in `sdk_adapter/client.py` are acceptable

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for local development setup and contributing guidelines.

## Contracts

Behavioral specifications are in `contracts/`:
- [Provider Protocol](contracts/provider-protocol.md)
- [Deny + Destroy](contracts/deny-destroy.md)
- [Error Hierarchy](contracts/error-hierarchy.md)
- [Event Vocabulary](contracts/event-vocabulary.md)
- [Streaming Contract](contracts/streaming-contract.md)

## License

MIT
