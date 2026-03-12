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

```yaml
providers:
  - module: provider-github-copilot
    source: git+https://github.com/your-org/provider-github-copilot
```

## Configuration

Environment variables:
- `GITHUB_TOKEN` or `COPILOT_AGENT_TOKEN` — authentication

## Contracts

- `contracts/deny-destroy.md` — sovereignty guarantee
- `contracts/provider-protocol.md` — protocol compliance
