# Architecture Specification

**Primary Spec:** [mydocs/debates/GOLDEN_VISION_V2.md](../mydocs/debates/GOLDEN_VISION_V2.md)

This document serves as an index to the architecture specification.

---

## Quick Reference

### The Three-Medium Architecture

| Medium | Purpose | Target Size |
|--------|---------|-------------|
| **Python** | Mechanism — control flow, state machines, protocol translation | ~300 lines |
| **YAML** | Policy — error mappings, event routing, retry config | ~200 lines |
| **Markdown** | Contracts — behavioral requirements, invariants | ~400 lines |

### The Litmus Tests

| Question | Answer |
|----------|--------|
| Does it require control flow, state, or type-safe transformation? | **Python** |
| Could two teams want different values? Is it a mapping or threshold? | **YAML** |
| Is it a requirement that implementations must satisfy? | **Markdown** |

### Non-Negotiable Constraints

1. No SDK type crosses the adapter boundary
2. preToolUse deny hook on every session
3. Sessions are ephemeral (create, use once, destroy)
4. Security changes always require human review
5. Tests must trace to contracts
6. Deny + Destroy is NEVER configurable
7. Every YAML config file has a schema
8. Effective config must be explainable

---

## Full Specification

See [mydocs/debates/GOLDEN_VISION_V2.md](../mydocs/debates/GOLDEN_VISION_V2.md) for:

- Executive Summary (The Six Innovations)
- Core Philosophy (The Six Principles)
- Architecture (Directory Structure, SDK Boundary, Key Interfaces)
- Autonomous Development Machine (Four-Tier Autonomy Model)
- Testing Strategy (Contract-Anchored Diamond)
- Implementation Roadmap (Phase 0-2)
- Risks and Mitigations
