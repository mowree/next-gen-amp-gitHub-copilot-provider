# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- F-029: Documentation update (README.md, DEVELOPMENT.md)
- F-030: CHANGELOG.md

## [0.1.0] - 2026-03-13

### Added

#### Phase 0: Core Infrastructure (F-001 to F-009)
- **F-001**: SDK Adapter skeleton with DomainEvent, SessionConfig types
- **F-002**: Config-driven error translation with 7 mapping rules
- **F-003**: Session factory with deny hook (Deny+Destroy pattern)
- **F-004**: Tool parsing module with ToolCall dataclass
- **F-005**: Event translation with BRIDGE/CONSUME/DROP classification
- **F-006**: Streaming handler with AccumulatedResponse
- **F-007**: Completion lifecycle with async generator pattern
- **F-008**: Provider orchestrator (4 methods + 1 property)
- **F-009**: Integration verification tests (16 tests)

#### Phase 1: SDK Integration (F-010 to F-018)
- **F-010**: SDK client wrapper with auth status, session management
- **F-011**: Loop controller with circuit breaker (hard limit: 10 turns)
- **F-017**: Technical debt cleanup (removed dead code paths)
- **F-018**: Aggressive simplification (module consolidation)

#### Phase 2: Expert Review Remediation (F-019 to F-024)
- **F-019**: Critical security fixes
  - Deny hook on real SDK path
  - Race condition fix with asyncio.Lock
  - Double exception translation guard
- **F-020**: Provider protocol compliance
  - mount() entry point
  - get_info() and list_models() methods
  - complete() as class method
- **F-021**: Bug fixes from expert review
  - load_event_config crash fix
  - Dead assert statement removal
  - retry_after regex fix
  - finish_reason_map loading
- **F-022**: Foundation integration
  - bundle.md for Amplifier ecosystem
  - Extension guidance skill
- **F-023**: Critical test coverage (12 new tests)
  - Token resolution precedence
  - SDK boundary behavior
  - Concurrent session handling
- **F-024**: Code quality improvements
  - create_deny_hook export
  - Config loading with importlib.resources

#### Phase 3: Production Readiness (F-025 to F-028)
- **F-025**: CI pipeline
  - GitHub Actions workflow
  - ruff, pyright, pytest integration
  - 90-second timeout enforcement
- **F-026**: Contract compliance tests (46 tests)
  - provider-protocol.md compliance
  - deny-destroy.md compliance
  - error-hierarchy.md compliance
  - event-vocabulary.md compliance
  - streaming-contract.md compliance
- **F-027**: Real SDK integration tests
  - Tier 6: 19 SDK assumption tests
  - Tier 7: 11 live smoke tests
- **F-028**: Entry point registration (7 tests)

### Architecture

This release implements the Three-Medium Architecture:

| Medium | Purpose | Lines |
|--------|---------|-------|
| Python | Mechanism: control flow, protocol translation | ~700 |
| YAML | Policy: error mappings, event routing | ~200 |
| Markdown | Contracts: behavioral specifications | ~400 |

### Testing

- **256 total tests**
- 246 tests pass without credentials
- 10 live SDK tests require GITHUB_TOKEN (designed for nightly CI)

### Security

- Deny+Destroy pattern enforced on all SDK sessions
- preToolUse hook denies all tool execution
- Sessions are ephemeral (create, use once, destroy)

[Unreleased]: https://github.com/microsoft/amplifier-module-provider-github-copilot/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/microsoft/amplifier-module-provider-github-copilot/releases/tag/v0.1.0
