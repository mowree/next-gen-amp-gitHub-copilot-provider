# PROVIDER AS BUNDLE: A Config-First Architecture

**Version**: 1.0  
**Date**: 2026-03-08  
**Authority**: Foundation Bundle Expert — grounded in amplifier-foundation bundle composition patterns  
**Status**: Architectural Counter-Proposal

---

## Executive Summary

The previous council proposed 17 flat Python modules, policies embedded in code, and tests as the only specification. This is the exact anti-pattern that the Amplifier bundle system was designed to eliminate. The bundle architecture provides a fundamentally different organizing principle: **configuration declares intent, code implements only the mechanical minimum, and composition replaces inheritance.**

A provider is not a Python application. A provider is a **bundle** — a composable unit of configuration that declares what it translates, how it handles errors, and what policies govern its behavior. The Python code that remains after extracting configuration into YAML and contracts into markdown should be shockingly small: under 300 lines of pure mechanical translation.

This document redesigns the GitHub Copilot provider using bundle patterns: thin bundles, behavior composition, context injection, and config-driven policies. The result is a system where 80% of maintenance is configuration changes (safe for AI), 15% is contract updates (reviewable as markdown), and only 5% requires touching Python code (the dangerous part).

---

## Part 1: The Bundle Structure

### The Full Layout

```
provider-github-copilot/
├── bundle.md                       # Root bundle — THIN (< 20 lines YAML)
├── behaviors/
│   ├── sdk-translation.yaml        # Core translation behavior
│   ├── error-handling.yaml         # Error policies as composable config
│   └── streaming.yaml              # Streaming behavior
├── agents/
│   └── provider-diagnostics.md     # Expert agent for debugging provider issues
├── context/
│   ├── sdk-contracts.md            # SDK assumptions declared as prose
│   ├── error-mapping.md            # Error translation rules (readable!)
│   ├── deny-destroy-contract.md    # The sovereignty pattern, documented
│   └── policies.md                 # Configurable policy descriptions
├── modules/
│   └── provider-copilot/           # The THIN Python code
│       ├── pyproject.toml          # Module package config
│       └── provider_copilot/
│           ├── __init__.py
│           ├── adapter.py          # SDK ↔ Domain translation (~150 lines)
│           ├── driver.py           # Raw SDK session management (~100 lines)
│           └── events.py           # Event type mapping (~50 lines)
├── config/
│   ├── retry-policy.yaml           # Retry behavior: counts, backoff, jitter
│   ├── timeout-policy.yaml         # Timeout thresholds per operation
│   ├── sdk-assumptions.yaml        # SDK version expectations, type mappings
│   └── error-classification.yaml   # Which errors are transient vs fatal
├── docs/
│   ├── ARCHITECTURE.md             # This document's implementation notes
│   └── SDK_EVOLUTION.md            # How to handle SDK changes
└── providers/
    └── copilot.yaml                # Provider bundle for composition
```

### Why This Structure Matters

Every directory follows the bundle convention from `amplifier-foundation`:

| Directory | Convention | What Lives Here |
|-----------|-----------|-----------------|
| `bundle.md` | Root bundle | Thin entry point, includes foundation + behaviors |
| `behaviors/` | Behavior bundles | Composable capability packages |
| `agents/` | Agent files | Expert agents for debugging/diagnostics |
| `context/` | Context files | Contracts, policies, mappings as markdown |
| `modules/` | Local modules | The minimal Python implementation |
| `config/` | Configuration | YAML-driven policies and assumptions |
| `providers/` | Provider bundles | Provider config for composition by apps |

**Key insight from the Bundle Guide**: "Bundles are configuration, not Python packages. A bundle repo does not need a root `pyproject.toml`." The root of this repository is a bundle. The Python code lives inside `modules/provider-copilot/` — a local module with its own `pyproject.toml`, referenced by the behavior.

---

## Part 2: The Root Bundle — Radical Thinness

```markdown
---
bundle:
  name: provider-copilot
  version: 1.0.0
  description: GitHub Copilot SDK provider for Amplifier — translation layer

includes:
  - bundle: provider-copilot:behaviors/sdk-translation
  - bundle: provider-copilot:behaviors/error-handling
  - bundle: provider-copilot:behaviors/streaming
---

# GitHub Copilot Provider

@provider-copilot:context/sdk-contracts.md

@provider-copilot:context/deny-destroy-contract.md
```

**That's it.** The root bundle is 14 lines of YAML frontmatter and 2 context references. This follows the thin bundle pattern exactly: declare what you uniquely provide, compose everything else through behaviors.

Notice what is NOT here:
- No `session:` block (the provider doesn't own session config)
- No `tools:` block (the provider doesn't provide tools)
- No inline instructions (extracted to `context/` files)
- No Python imports, no class hierarchies, no framework

The root bundle does NOT include foundation — because this is a **provider bundle**, not an application bundle. Provider bundles are composed INTO application bundles by the consuming app. The app's bundle includes foundation; the provider just provides the provider.

---

## Part 3: What Lives in YAML vs Python

This is the critical design decision. The previous council put everything in Python. The bundle architecture inverts this: **YAML declares, Python executes.**

### YAML: Policies, Configuration, Assumptions

#### `config/retry-policy.yaml`
```yaml
retry:
  max_attempts: 3
  backoff:
    strategy: exponential
    base_seconds: 1.0
    max_seconds: 30.0
    jitter: true
  retryable_errors:
    - rate_limited        # 429
    - server_error        # 5xx
    - connection_timeout  # Network
  non_retryable_errors:
    - authentication      # 401 — retrying won't help
    - forbidden           # 403 — permission issue
    - not_found           # 404 — resource doesn't exist
    - invalid_request     # 400 — our bug, not transient
```

#### `config/timeout-policy.yaml`
```yaml
timeouts:
  session_create: 10.0      # seconds to establish SDK session
  completion_request: 120.0  # seconds for a completion (streaming start)
  stream_idle: 30.0          # seconds between stream chunks before timeout
  session_destroy: 5.0       # seconds to clean up session
  
  # Circuit breaker: if N consecutive timeouts, stop trying
  circuit_breaker:
    threshold: 5
    reset_after_seconds: 60
```

#### `config/error-classification.yaml`
```yaml
# Maps SDK error types to domain error classifications
# This is the SINGLE SOURCE OF TRUTH for error translation
error_mapping:
  # SDK Exception Class → Domain Classification
  CopilotAuthError: authentication
  CopilotRateLimitError: rate_limited
  CopilotServerError: server_error
  CopilotNetworkError: connection_timeout
  CopilotModelNotFoundError: not_found
  CopilotInvalidRequestError: invalid_request
  CopilotContentFilterError: content_filtered
  
  # Fallback for unknown SDK errors
  default: unknown_provider_error

# Maps HTTP status codes (when SDK throws raw HTTP errors)
http_status_mapping:
  401: authentication
  403: forbidden
  404: not_found
  429: rate_limited
  500: server_error
  502: server_error
  503: server_error
```

#### `config/sdk-assumptions.yaml`
```yaml
# Explicit assumptions about SDK behavior
# When these change, the config changes — not the code
sdk:
  version_constraint: ">=0.1.0,<1.0.0"  # Pre-1.0, expect breakage
  
  # Session behavior assumptions
  session:
    supports_streaming: true
    requires_auth_before_create: true
    session_is_ephemeral: true          # We create, use once, destroy
    
  # Event type mapping: SDK event name → our domain event name
  event_mapping:
    textDelta: content_delta
    toolCall: tool_request          # We deny these, but must recognize them
    toolResult: tool_result         # Should never occur (we deny tool calls)
    turnComplete: turn_complete
    error: provider_error
    usage: usage_report
    
  # Fields we extract from SDK responses
  response_extraction:
    model_field: "response.model"
    usage_field: "response.usage"
    content_field: "response.choices[0].message.content"
    finish_reason_field: "response.choices[0].finish_reason"
```

### Python: ONLY Mechanical Translation (~300 lines total)

The Python code that remains does exactly three things:

1. **`adapter.py` (~150 lines)**: Reads the YAML configs at startup. Translates domain requests into SDK calls. Translates SDK responses into domain events. Uses the error classification YAML to map exceptions. This is the adapter layer — the membrane.

2. **`driver.py` (~100 lines)**: Manages the raw SDK session lifecycle. Creates sessions with the deny hook. Destroys sessions after use. Handles the streaming connection. This is pure mechanics — no policy decisions.

3. **`events.py` (~50 lines)**: Domain event types. Dataclasses that represent what the provider emits. No SDK types — these are the domain vocabulary.

**What is NOT in Python:**
- Retry logic → reads `retry-policy.yaml`, delegates to a generic retry mechanism
- Timeout values → reads `timeout-policy.yaml`
- Error classification → reads `error-classification.yaml`
- SDK assumptions → reads `sdk-assumptions.yaml`
- Event mapping → reads from `sdk-assumptions.yaml`'s `event_mapping`
- The deny+destroy contract → documented in `context/deny-destroy-contract.md`, enforced by 5 lines in `driver.py`

**The Python code has no policy in it.** It reads YAML, translates mechanically, and emits domain events. When the SDK changes an event name, you change one line in `sdk-assumptions.yaml`. When you want different retry behavior, you edit `retry-policy.yaml`. When a new error type appears, you add it to `error-classification.yaml`. None of these require touching Python.

---

## Part 4: How Behaviors Compose

The three behaviors compose onto the root bundle following the standard behavior pattern from amplifier-foundation.

### `behaviors/sdk-translation.yaml` — The Core
```yaml
bundle:
  name: sdk-translation-behavior
  version: 1.0.0
  description: Core SDK translation — the provider's primary capability

# The provider module itself
providers:
  - module: provider-copilot
    source: provider-copilot:modules/provider-copilot
    config:
      sdk_assumptions: provider-copilot:config/sdk-assumptions.yaml
      
# Context that any composing bundle gets
context:
  include:
    - provider-copilot:context/sdk-contracts.md
    - provider-copilot:context/deny-destroy-contract.md
```

This behavior does one thing: it provides the Copilot provider module and injects awareness of the SDK contracts into the composing bundle's context. Any bundle that includes this behavior gets the provider AND understands its contracts.

### `behaviors/error-handling.yaml` — Error Policies
```yaml
bundle:
  name: error-handling-behavior
  version: 1.0.0
  description: Error classification and retry policies for the Copilot provider

# No module — this behavior is pure configuration
# It composes config onto the provider module
providers:
  - module: provider-copilot
    config:
      error_classification: provider-copilot:config/error-classification.yaml
      retry_policy: provider-copilot:config/retry-policy.yaml
      timeout_policy: provider-copilot:config/timeout-policy.yaml

context:
  include:
    - provider-copilot:context/error-mapping.md
```

**This is where bundle composition shines.** The error-handling behavior has NO Python code. It is pure YAML configuration that composes onto the provider module via config deep-merge. When the root bundle includes both `sdk-translation` and `error-handling`, the provider module receives the merged config from both behaviors.

From the Bundle Guide: "configs for same module are deep-merged." This means the `sdk-translation` behavior provides the base provider config, and the `error-handling` behavior layers error-specific config on top. No Python inheritance. No class hierarchies. Just YAML deep-merge.

**Want different error handling?** Don't include this behavior. Write your own `behaviors/custom-error-handling.yaml` with different retry counts or different error classifications. The Python code doesn't change — it reads whatever config it receives.

### `behaviors/streaming.yaml` — Streaming Behavior
```yaml
bundle:
  name: streaming-behavior
  version: 1.0.0
  description: Streaming configuration for the Copilot provider

providers:
  - module: provider-copilot
    config:
      streaming:
        enabled: true
        chunk_buffer_size: 4096
        idle_timeout: provider-copilot:config/timeout-policy.yaml#stream_idle
        backpressure_strategy: drop_oldest

context:
  include:
    - provider-copilot:context/policies.md
```

Again: no Python code. Pure configuration that merges onto the provider module. The streaming behavior declares how streaming should work. The Python `driver.py` reads this config and implements the mechanical streaming loop accordingly.

### Composition in Action

When the root bundle includes all three behaviors:

```yaml
includes:
  - bundle: provider-copilot:behaviors/sdk-translation    # Base provider
  - bundle: provider-copilot:behaviors/error-handling      # + error policies
  - bundle: provider-copilot:behaviors/streaming           # + streaming config
```

The composition engine deep-merges all three configs onto the `provider-copilot` module:

```yaml
# Effective merged config for provider-copilot module:
config:
  sdk_assumptions: provider-copilot:config/sdk-assumptions.yaml
  error_classification: provider-copilot:config/error-classification.yaml
  retry_policy: provider-copilot:config/retry-policy.yaml
  timeout_policy: provider-copilot:config/timeout-policy.yaml
  streaming:
    enabled: true
    chunk_buffer_size: 4096
    idle_timeout: ...
    backpressure_strategy: drop_oldest
```

**The Python module receives this as a flat config dict at mount time.** It doesn't know or care which behavior contributed which config key. It reads the values and translates mechanically.

### Selective Composition

An app that doesn't want streaming? Don't include the streaming behavior:

```yaml
includes:
  - bundle: provider-copilot:behaviors/sdk-translation
  - bundle: provider-copilot:behaviors/error-handling
  # No streaming behavior — provider works without it
```

An app that wants custom retry logic?

```yaml
includes:
  - bundle: provider-copilot:behaviors/sdk-translation
  - bundle: provider-copilot:behaviors/streaming
  # No error-handling behavior — app provides its own:

providers:
  - module: provider-copilot
    config:
      retry_policy:
        max_attempts: 1    # Fail fast, app handles retries
```

This is **mechanism not policy** made concrete through bundle composition. The provider provides mechanisms. Behaviors provide sensible default policies. Apps override policies through composition.

---

## Part 5: Where SDK Contracts Go

The previous council proposed contracts embedded in Python docstrings and enforced only through tests. The bundle architecture puts contracts in **markdown** — human-readable, AI-readable, versionable, diffable prose.

### `context/sdk-contracts.md`

```markdown
# SDK Contracts: GitHub Copilot Provider

## Authentication Contract

The provider MUST authenticate with the Copilot SDK before creating sessions.
Authentication uses OAuth token exchange. The token is provided by the Amplifier
kernel via the provider config's `auth_token` field.

**Assumption**: The SDK's `CopilotClient.authenticate()` method is synchronous 
and returns a session token. If this changes to async, `driver.py` must be updated.

## Session Lifecycle Contract

1. Create session with deny hook → SDK session is live
2. Send exactly ONE completion request → SDK processes
3. Consume streaming response OR collect full response
4. Destroy session → SDK session is terminated

**INVARIANT**: No session survives past a single turn. This is the Deny+Destroy
pattern. Violation of this invariant creates the Two Orchestrators problem.

## Event Translation Contract

The provider translates SDK events to domain events per `sdk-assumptions.yaml`.
Unknown event types are logged and dropped — never propagated.

| SDK Event | Domain Event | Notes |
|-----------|-------------|-------|
| textDelta | content_delta | The primary content stream |
| toolCall | tool_request | Always denied by preToolUse hook |
| turnComplete | turn_complete | Signals end of response |
| error | provider_error | Classified per error-classification.yaml |
| usage | usage_report | Token counts for billing/limits |

## What We Expect to Break

Based on 18 months of SDK changelog analysis:
- **Event type renames** (73% of changes): Fix in sdk-assumptions.yaml
- **New required fields** (21% of changes): Fix in adapter.py extraction
- **Removed APIs** (6% of changes): Requires human architectural review
```

### `context/deny-destroy-contract.md`

```markdown
# The Deny + Destroy Contract

## Why This Exists

The Copilot SDK has its own agent loop. Amplifier has its own orchestrator.
If both try to execute tools, you get the Two Orchestrators problem: 
conflicting decisions, duplicated state, undefined behavior.

## The Mechanism

1. Every SDK session is created with a `preToolUse` hook that returns DENY
2. The SDK sees the denial and includes tool requests in its response
3. Amplifier's orchestrator handles tool execution
4. The session is destroyed after ONE turn — no state accumulates

## Non-Negotiable

This contract is NOT configurable. There is no YAML policy for it.
The deny hook is hardcoded in `driver.py`. The destroy-after-turn is 
hardcoded in `driver.py`. These are architectural invariants, not policies.

## How to Verify

Any test that creates a provider session MUST verify:
- preToolUse hook is registered
- Session is destroyed after response completes
- No tool execution occurs through the SDK
```

### `context/error-mapping.md`

```markdown
# Error Mapping Rules

Error translation follows a three-tier strategy:

1. **SDK Exception Match**: If the SDK throws a typed exception, classify 
   per `config/error-classification.yaml`
2. **HTTP Status Fallback**: If the SDK throws a raw HTTP error, classify
   per `config/error-classification.yaml` http_status_mapping
3. **Unknown Default**: Any unrecognized error becomes `unknown_provider_error`

## Retry vs Escalate

Retryable errors (rate_limited, server_error, connection_timeout) are retried
per `config/retry-policy.yaml`. Non-retryable errors are immediately converted
to domain exceptions and propagated to the kernel.

## Adding New Error Types

When the SDK introduces a new exception class:
1. Add it to `config/error-classification.yaml`
2. Verify the classification with a test
3. No Python code changes needed
```

### Why Markdown Contracts Matter

Contracts in markdown are:

1. **Readable by AI agents**: An agent spawned to diagnose a provider issue loads `@provider-copilot:context/sdk-contracts.md` and immediately understands the provider's assumptions, invariants, and expected failure modes. No need to reverse-engineer Python code.

2. **Diffable as prose**: When a contract changes, the diff is English: "Changed session timeout from 120s to 180s" or "Added new SDK event type `reasoning`." Reviewers read words, not code paths.

3. **Single source of truth via context injection**: The behavior's `context.include` injects these contracts into any bundle that composes the provider. The composing bundle's AI agent knows the contracts without the provider author doing anything special.

4. **Versionable independently from code**: A contract can change (new assumption documented) without any code changing. A code change can happen (refactoring adapter.py) without any contract changing. They evolve at different rates, as they should.

---

## Part 6: Enabling Autonomous Maintenance

This is where the bundle architecture decisively outperforms the 17-module Python approach. The question is: **what kind of change is safest for an AI agent to make?**

### The Safety Hierarchy

| Change Type | Risk Level | Example | Where It Lives |
|------------|-----------|---------|---------------|
| YAML config edit | **Lowest** | Change retry count from 3 to 5 | `config/retry-policy.yaml` |
| YAML mapping addition | **Low** | Add new SDK error type | `config/error-classification.yaml` |
| Markdown contract update | **Low-Medium** | Document new SDK event | `context/sdk-contracts.md` |
| YAML event mapping | **Low** | SDK renames `textDelta` to `text_delta` | `config/sdk-assumptions.yaml` |
| Python extraction fix | **Medium** | SDK moves `usage` to different field | `adapter.py` (1-2 lines) |
| Python driver change | **High** | SDK changes session lifecycle | `driver.py` |
| Contract violation | **Highest** | Deny+Destroy invariant needs rethinking | Architecture review |

**The bundle architecture puts 80% of expected maintenance into the lowest-risk categories.** An AI agent editing a YAML file with clear structure, explicit field names, and immediate testability is vastly safer than an AI agent editing a 400-line Python module with implicit control flow and cross-cutting concerns.

### Config Changes: AI-Safe by Design

When the SDK introduces a new error type, the AI agent:

1. Reads `context/error-mapping.md` — understands the error classification strategy
2. Reads `config/error-classification.yaml` — sees the current mappings
3. Adds one line: `CopilotNewError: appropriate_classification`
4. Runs existing tests — they validate the classification works
5. Done. No Python touched. No risk of breaking translation logic.

Compare with the 17-module approach: the AI agent must understand the `error_translator.py` module's class hierarchy, find the right method to modify, ensure the new exception class is imported correctly, verify it doesn't break the inheritance chain, and hope the change doesn't have side effects in 3 other modules that catch exceptions.

### Contract Changes: Reviewable as English

When the SDK adds a new event type, the AI agent:

1. Updates `config/sdk-assumptions.yaml` — adds the event mapping
2. Updates `context/sdk-contracts.md` — documents the new event's semantics
3. The PR diff shows: YAML mapping + English description
4. A human reviewer reads English, not code. Approval is fast.

### The 73/21/6 Rule Applied to Bundles

The Golden Vision identified that 73% of SDK changes are type renames, 21% are behavioral changes, and 6% are breaking removals. Here's how each maps to the bundle architecture:

**73% — Type Renames**: Change one line in `config/sdk-assumptions.yaml` or `config/error-classification.yaml`. Zero Python changes. Full AI autonomy.

**21% — Behavioral Changes**: Update `context/sdk-contracts.md` to document the new behavior. May require a small change in `adapter.py` or `driver.py`. AI writes the change, human reviews the contract diff.

**6% — Breaking Removals**: Update contracts, possibly restructure behaviors. Human architects review. But even here, the blast radius is contained — you're changing one behavior's YAML, not refactoring 17 Python modules.

### The Context Sink Pattern for Diagnostics

The `agents/provider-diagnostics.md` agent is a context sink — it `@mentions` the full contracts, configs, and architecture docs. When something goes wrong with the provider, you delegate to this agent. It loads all the heavy context in its own session (not yours) and diagnoses the issue.

```markdown
---
meta:
  name: provider-diagnostics
  description: |
    Expert agent for diagnosing GitHub Copilot provider issues.
    
    ALWAYS delegate to this agent when:
    - Provider returns unexpected errors
    - SDK behavior doesn't match contracts
    - Streaming failures or timeout issues
    - Need to understand provider architecture
    
    <example>
    <context>Provider is returning 'unknown_provider_error' for a new SDK exception</context>
    <user>The provider is failing with an unclassified error from the Copilot SDK</user>
    <assistant>I'll delegate to provider-diagnostics to analyze the error classification</assistant>
    </example>
---

You are the expert on the GitHub Copilot provider architecture.

@provider-copilot:context/sdk-contracts.md
@provider-copilot:context/deny-destroy-contract.md
@provider-copilot:context/error-mapping.md
@provider-copilot:context/policies.md
@provider-copilot:docs/ARCHITECTURE.md
```

This agent carries ~5,000 tokens of context. That context loads ONLY when the agent is spawned. The root session pays zero tokens for this diagnostic capability until it's needed. This is the context sink pattern from the Bundle Guide applied to provider maintenance.

---

## Part 7: What the Previous Council Got Wrong

### Wrong: 17 Python Modules

The council proposed `adapter.py`, `driver.py`, `event_translator.py`, `error_translator.py`, `stream_handler.py`, `session_lifecycle.py`, `config_loader.py`, `auth_handler.py`, `retry_handler.py`, `timeout_handler.py`, `circuit_breaker.py`, `pagination_handler.py`, `token_redactor.py`, `deny_hook.py`, `destroy_handler.py`, `health_checker.py`, and `metrics_emitter.py`.

**The bundle rebuttal**: `retry_handler.py`, `timeout_handler.py`, `circuit_breaker.py`, and `config_loader.py` are YAML config files, not Python modules. `error_translator.py` is a YAML mapping. `deny_hook.py` and `destroy_handler.py` are 5 lines each inside `driver.py`. `health_checker.py` and `metrics_emitter.py` are hooks, not provider code. `pagination_handler.py` and `auth_handler.py` are SDK mechanics that belong in `driver.py`.

After extraction to config: **3 Python files, ~300 lines total.** Not 17 modules.

### Wrong: Tests as Specification

Tests verify behavior. They do not communicate intent. A test that asserts `retry_count == 3` tells you what the system does, not why, not what the tradeoff was, not when to change it.

**The bundle rebuttal**: Markdown contracts communicate intent. YAML configs communicate current policy. Tests verify that the config produces the expected behavior. All three exist, but they serve different purposes. The contract says "retry transient errors." The config says "3 times with exponential backoff." The test verifies that 3 retries actually happen with exponential backoff. Change the config, the test still passes (it reads the config). Change the contract, and you know to update both config and tests.

### Wrong: Policies Embedded in Code

A retry policy in Python is a policy hidden in implementation. Changing it requires understanding the code, the control flow, the exception handling, and the test suite. It is inherently unsafe for autonomous modification.

**The bundle rebuttal**: A retry policy in YAML is a policy stated in plain structure. Changing it requires understanding the YAML schema (self-documenting) and running tests. An AI agent can safely change `max_attempts: 3` to `max_attempts: 5` in YAML. The same agent changing retry logic in a Python class with inheritance, exception handling, and async context managers is playing with fire.

---

## Conclusion: The Provider is a Bundle, Not an Application

The Amplifier ecosystem was designed around a principle: **configuration declares intent, code implements mechanism.** The bundle architecture is this principle made concrete through YAML frontmatter, behavior composition, context injection, and config-driven policies.

A provider that follows this architecture is:

- **Thin**: ~300 lines of Python, not 1,799
- **Composable**: Behaviors mix and match error handling, streaming, and translation
- **Declarative**: Policies live in YAML, contracts live in markdown
- **AI-maintainable**: 80% of changes are config edits, the safest possible change type
- **Diagnosable**: Expert agents carry full context, spawned on demand
- **Evolvable**: SDK changes hit config first, code last

The previous council designed a Python application. This document designs a **bundle** — a composable, config-first, AI-maintainable translation layer that follows every pattern the Amplifier foundation provides.

Build applications with the simplest configuration that meets your needs. Foundation handles the complexity; you add the value.

---

*Grounded in: amplifier-foundation Bundle Guide, Patterns, Context Architecture, Behavior Pattern, Thin Bundle Pattern, Context Sink Pattern, and Mechanism-not-Policy philosophy.*