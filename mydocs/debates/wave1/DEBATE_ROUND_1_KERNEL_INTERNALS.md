# Wave 1, Agent 3: Amplifier Kernel Internals — Deep Analysis

**Agent Role**: Amplifier Core/Kernel Expert  
**Date**: 2026-03-08  
**Subject**: Provider Protocol Compliance, Module Boundaries, Event System, Error Handling, Coordinator Integration, and Session Lifecycle for a Next-Generation GitHub Copilot Provider

---

## Executive Summary

The Amplifier kernel (`amplifier-core`) is an ultra-thin Rust+PyO3 layer (~6,600 lines) that provides **mechanisms only** — stable contracts, module loading, event dispatch, session lifecycle, and coordinator infrastructure. A GitHub Copilot provider is a **module** (specifically a Provider) that must implement the Provider protocol, emit canonical events, interact with the ModuleCoordinator, and respect session lifecycle boundaries. This analysis provides the exact interfaces, contracts, event schemas, error handling expectations, and integration patterns the provider must follow. The current 1700+ line monolithic implementation likely violates multiple kernel boundaries by embedding policies (retry logic, model selection, response formatting) that should live in modules or application-layer configuration.

---

## 1. Provider Protocol Compliance

### 1.1 The Exact Interface

The Provider protocol is defined in `amplifier_core/interfaces.py` (lines 54–119) and is a `@runtime_checkable` Protocol:

```python
@runtime_checkable
class Provider(Protocol):
    @property
    def name(self) -> str: ...

    def get_info(self) -> ProviderInfo: ...

    async def list_models(self) -> list[ModelInfo]: ...

    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...

    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...
```

**Five methods. No more, no less.** The provider MUST implement exactly these five methods. The kernel validates protocol compliance at mount time using `isinstance(provider, Provider)` thanks to `@runtime_checkable`.

### 1.2 Method-by-Method Requirements

#### `name` (property)
- Returns a stable string identifier (e.g., `"github-copilot"`)
- Used as the key in `providers: dict[str, Provider]` passed to orchestrators
- Must be unique within a session
- Convention: lowercase, hyphenated

#### `get_info() -> ProviderInfo`
- Returns metadata model from `amplifier_core/models.py`
- Must include `config_fields` for interactive setup (e.g., API key, base URL)
- `ProviderInfo.defaults` should contain `context_window` and `max_output_tokens` — these are used by ContextManagers to calculate dynamic token budgets
- ConfigField supports `field_type="secret"` for credentials, `env_var` for environment variable resolution, `show_when` and `requires_model` for conditional fields

#### `list_models() -> list[ModelInfo]`
- Returns available models with required fields: `id`, `display_name`, `context_window`, `max_output_tokens`
- **SHOULD** populate `cost_per_input_token`, `cost_per_output_token` for cost-aware routing
- **SHOULD** set `metadata["cost_tier"]` to one of: `free`, `low`, `medium`, `high`, `extreme`
- **SHOULD** populate `capabilities` using well-known constants from `amplifier_core.capabilities`: `TOOLS`, `STREAMING`, `THINKING`, `VISION`, `JSON_MODE`, `FAST`, `CODE_EXECUTION`, `WEB_SEARCH`, etc.
- **Critical naming decision**: Extended reasoning capability is canonically `"thinking"`, not `"reasoning"`. The Copilot provider must map any vendor terminology to `"thinking"`.

#### `complete(request: ChatRequest, **kwargs) -> ChatResponse`
- The core translation method. Receives Amplifier's unified `ChatRequest` (from `amplifier_core/message_models.py`), translates to vendor API, translates response back to `ChatResponse`
- **Content block preservation is critical**: All block types must round-trip without loss
  - `ThinkingBlock`: MUST preserve `signature` field (required for multi-turn)
  - `ReasoningBlock`: MUST preserve `content` and `summary` arrays
  - `ToolCallBlock`: MUST preserve `id` for result correlation
- Must report `Usage` (input_tokens, output_tokens, total_tokens)
- Must handle role conversion (see §1.3)
- Must validate tool call/result sequences
- Auto-continuation for truncated responses should be handled transparently

#### `parse_tool_calls(response: ChatResponse) -> list[ToolCall]`
- Extracts `ToolCall` objects from `ChatResponse`
- `ToolCall` is from `amplifier_core.message_models`
- Must correctly parse the vendor-specific tool call format into Amplifier's unified `ToolCall` shape

### 1.3 Role Conversion Table

```
Amplifier Role    → Copilot API Mapping
────────────────────────────────────────
system            → system / instructions parameter
developer         → user (XML-wrapped for context separation)
user              → user
assistant         → assistant
tool              → user (with tool_result blocks)
```

### 1.4 What's Likely Over-Implemented in Current 1700+ Lines

Based on the kernel philosophy ("mechanism not policy"), a Provider module should NOT contain:

- **Retry logic** — This is policy. A retry hook or orchestrator-level retry should handle this.
- **Model selection logic** — Policy. The orchestrator or app layer selects the model via config.
- **Response formatting** — Policy. The orchestrator decides how to present responses.
- **Rate limiting strategy** — Policy. A hook can observe `provider:response` events and inject delays.
- **Conversation management** — Mechanism owned by ContextManager, not Provider.
- **Session persistence** — App layer responsibility.
- **Logging to stdout/files** — Use event emission; hooks decide where to log.
- **Hardcoded defaults** — Should come from Mount Plan `config` dict.

### 1.5 What's Likely Missing

- Proper `mount()` function entry point pattern
- `pyproject.toml` entry point registration
- Content block preservation (especially `ThinkingBlock.signature`)
- `ModelInfo` with capabilities, cost tiers, and cost-per-token fields
- Contribution channel registration for observability events
- Cleanup function for HTTP client resource management
- Graceful degradation (return `None` from `mount()` on missing credentials)

---

## 2. Module Boundaries

### 2.1 The Provider Is a Module — What That Means

The kernel treats providers as loadable drivers (Linux kernel analogy). The provider module:

- **Implements the Provider protocol** — nothing more
- **Receives configuration** via `config: dict` parameter in `mount()`
- **Accesses kernel services** only through `ModuleCoordinator`
- **Never imports kernel internals** — use protocols and public APIs only
- **Never crashes the kernel** — all failures must be caught and reported gracefully
- **Emits events** for any observable action
- **Is independently testable** — works in isolation with `TestCoordinator`

### 2.2 Exact Boundaries

| Responsibility | Owner | NOT Provider's Job |
|---|---|---|
| API translation | Provider | — |
| Content block mapping | Provider | — |
| Token counting | Provider (for Usage) | Budget calculation (ContextManager) |
| Tool call parsing | Provider | Tool execution (Orchestrator) |
| Model metadata | Provider (list_models) | Model selection (App layer) |
| HTTP client lifecycle | Provider | — |
| Retry policy | Hook/Orchestrator | NOT Provider |
| Rate limit strategy | Hook | NOT Provider |
| Response formatting | Orchestrator | NOT Provider |
| Conversation state | ContextManager | NOT Provider |
| Execution loop | Orchestrator | NOT Provider |
| Logging destination | Hook | NOT Provider |
| Provider selection | App layer | NOT Provider |

### 2.3 Kernel Capabilities the Provider SHOULD Use

1. **ModuleCoordinator.mount()** — Register itself at the `"providers"` mount point
2. **ModuleCoordinator.register_contributor()** — Declare observability events
3. **coordinator.hooks** — Access HookRegistry for event emission (if needed for provider-specific events)
4. **Configuration from `config` dict** — All tunable parameters
5. **amplifier_core.message_models** — Request/response types
6. **amplifier_core.content_models** — Event content types for streaming
7. **amplifier_core.models** — ProviderInfo, ModelInfo, ConfigField
8. **amplifier_core.capabilities** — Well-known capability constants
9. **amplifier_core.testing** — TestCoordinator, create_test_coordinator for tests

---

## 3. Event System Integration

### 3.1 Event Architecture

The kernel provides a hook-based event system. Events are emitted via `HookRegistry.emit()` and consumed by registered hook handlers. The provider participates in this system in two ways:

1. **Standard events emitted by the orchestrator** (not by the provider) around provider calls:
   - `provider:request` — Before LLM call
   - `provider:response` — After LLM call
   - `provider:error` — On LLM call failure

2. **Provider-specific events** emitted by the provider itself for internal observability:
   - Must be registered via contribution channels
   - Must follow naming convention: `{module-name}:{event}`

### 3.2 Event Naming Contract

```
Standard events (emitted by orchestrator):
  provider:request    — {provider, messages, model}
  provider:response   — {provider, response, usage}
  provider:error      — {provider, error}

Provider-specific events (emitted by provider, must register):
  github-copilot:rate_limit     — {retry_after, endpoint}
  github-copilot:retry          — {attempt, max_attempts, error}
  github-copilot:token_refresh  — {success, error?}
  github-copilot:auto_continue  — {iteration, accumulated_tokens}
```

### 3.3 Contribution Channel Registration

The provider MUST register its custom events during `mount()`:

```python
async def mount(coordinator: ModuleCoordinator, config: dict) -> Provider | Callable | None:
    # ... provider setup ...

    coordinator.register_contributor(
        "observability.events",
        "github-copilot",
        lambda: [
            "github-copilot:rate_limit",
            "github-copilot:retry",
            "github-copilot:token_refresh",
            "github-copilot:auto_continue",
        ],
    )

    await coordinator.mount("providers", provider, name="github-copilot")
    # ...
```

### 3.4 Event Data Shape Contract

Events carry `dict[str, Any]` data. The kernel does NOT enforce schemas — consumers interpret the data. However, following conventions is critical for interoperability:

```python
# provider:request data shape (emitted by orchestrator)
{
    "provider": "github-copilot",
    "messages": [...],       # list[dict] — messages being sent
    "model": "gpt-4o",      # str — model identifier
    "request_id": "...",     # str — correlation ID (if available)
}

# provider:response data shape (emitted by orchestrator)
{
    "provider": "github-copilot",
    "response": ChatResponse,  # The full response object
    "usage": {
        "input_tokens": int,
        "output_tokens": int,
        "total_tokens": int,
    },
    "model": "gpt-4o",
    "latency_ms": float,      # Optional but recommended
}
```

### 3.5 Debug Levels

The provider should support tiered debug logging via config flags:

| Flag | Events | Content |
|------|--------|---------|
| (default) | `llm:request`, `llm:response` | Summary only |
| `debug: true` | `llm:request:debug`, `llm:response:debug` | Truncated payloads |
| `debug: true, raw_debug: true` | `llm:request:raw`, `llm:response:raw` | Complete API I/O |

These are emitted by the provider internally using `coordinator.hooks.emit()` when configured. They're provider-specific events and must be registered via contribution channels.

### 3.6 Correlation IDs

The kernel passes `session_id` through the coordinator. The provider should:
- Include `session_id` in all event data it emits
- Generate a `request_id` per `complete()` call for tracing
- Forward any `request_id` from `**kwargs` if provided by the orchestrator

---

## 4. Error Handling Contract

### 4.1 The Kernel's Expectation

From the kernel philosophy: **"Your failures shouldn't crash the kernel."**

The kernel expects:
1. Providers catch their own exceptions
2. Providers return meaningful error information in `ChatResponse` or raise well-known exceptions
3. Provider failures are non-interfering — they don't corrupt kernel state
4. Module-level failures result in the module being skipped, not the session crashing

### 4.2 Mount-Time Error Handling

```python
async def mount(coordinator: ModuleCoordinator, config: dict) -> Provider | Callable | None:
    """
    Return None for graceful degradation.
    Raise only for truly unrecoverable configuration errors.
    """
    api_key = config.get("api_key") or os.environ.get("GITHUB_COPILOT_API_KEY")
    if not api_key:
        logger.warning("No GitHub Copilot API key - provider not mounted")
        return None  # Graceful degradation, not an error

    try:
        provider = GitHubCopilotProvider(api_key=api_key, config=config)
        await coordinator.mount("providers", provider, name="github-copilot")
    except Exception as e:
        logger.error(f"Failed to initialize GitHub Copilot provider: {e}")
        return None  # Graceful degradation

    async def cleanup():
        await provider.close()

    return cleanup
```

### 4.3 Runtime Error Translation

SDK/API errors must be translated into kernel-compatible responses:

```python
async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
    try:
        raw_response = await self._client.chat(...)
        return self._translate_response(raw_response)
    except RateLimitError as e:
        # Emit provider-specific event for observability
        await self._hooks.emit("github-copilot:rate_limit", {
            "retry_after": e.retry_after,
            "provider": self.name,
        })
        # Re-raise as a known error type — orchestrator handles retry policy
        raise
    except AuthenticationError as e:
        # Fatal for this provider — let it propagate
        raise
    except APIError as e:
        # Transient API error — raise for orchestrator to decide
        raise
    except Exception as e:
        # Unknown error — wrap and raise
        raise RuntimeError(f"GitHub Copilot provider error: {e}") from e
```

### 4.4 Error Categories

| SDK Error | Provider Behavior | Who Handles Recovery |
|---|---|---|
| Missing credentials | Return `None` from `mount()` | Kernel (skips module) |
| Rate limit | Emit event, raise exception | Orchestrator/Hook (retry policy) |
| Auth failure | Raise exception | App layer (credential refresh) |
| Network timeout | Raise exception | Orchestrator (retry policy) |
| Malformed response | Log warning, raise or return partial | Orchestrator |
| Token limit exceeded | Return truncated response with `finish_reason` | Orchestrator (auto-continue) |
| Invalid tool call format | Log warning, return best-effort parse | Provider (`parse_tool_calls`) |

### 4.5 The Non-Interference Principle

The provider MUST NOT:
- Mutate shared state on error
- Hold locks that could deadlock the kernel
- Swallow exceptions silently (always emit events or log)
- Retry internally without emitting observability events
- Block the event loop with synchronous error handling

---

## 5. Coordinator Integration

### 5.1 What the ModuleCoordinator Provides

The `ModuleCoordinator` (from `amplifier_core/coordinator.py`) is the infrastructure context carrying:
- `session_id` — Current session identifier
- `hooks` — Reference to `HookRegistry`
- Mount points — For registering the provider
- Capability checks — For feature negotiation
- Contribution channels — For observability registration

### 5.2 Provider's Interaction with Coordinator

The provider interacts with the coordinator at three lifecycle points:

#### Mount Time (in `mount()` function)
```python
async def mount(coordinator: ModuleCoordinator, config: dict):
    provider = GitHubCopilotProvider(config=config, coordinator=coordinator)

    # 1. Mount at providers mount point
    await coordinator.mount("providers", provider, name="github-copilot")

    # 2. Register observability events
    coordinator.register_contributor(
        "observability.events",
        "github-copilot",
        lambda: [
            "github-copilot:rate_limit",
            "github-copilot:retry",
            "github-copilot:token_refresh",
        ],
    )

    # 3. Return cleanup callable
    async def cleanup():
        await provider.close()
    return cleanup
```

#### Runtime (during `complete()` calls)
```python
class GitHubCopilotProvider:
    def __init__(self, config, coordinator):
        self._coordinator = coordinator
        self._hooks = coordinator.hooks
        self._session_id = coordinator.session_id

    async def complete(self, request, **kwargs):
        # Provider can emit its own events through coordinator.hooks
        # (Standard provider:request/response are emitted by orchestrator)
        if self._debug:
            await self._hooks.emit("github-copilot:debug:request", {
                "session_id": self._session_id,
                "model": self._model,
                "message_count": len(request.messages),
            })
        # ...
```

#### Cleanup Time (via returned cleanup callable)
```python
async def cleanup():
    # Close HTTP connections, flush buffers, etc.
    await provider._client.aclose()
```

### 5.3 Hooks the Provider Should Be Aware Of

The provider does NOT register hook handlers (that's for hook modules). But it should be aware that the orchestrator emits these events around provider calls:

| Event | When | Data |
|---|---|---|
| `provider:request` | Before `complete()` is called | provider, messages, model |
| `provider:response` | After `complete()` returns | provider, response, usage |
| `provider:error` | If `complete()` raises | provider, error |

Hooks can intercept these events to:
- **Modify** the request before it reaches the provider (`action="modify"`)
- **Block** the request entirely (`action="deny"`)
- **Inject context** based on the response (`action="inject_context"`)
- **Log** the request/response for debugging (`action="continue"`)

The provider should be designed to work correctly regardless of what hooks do to the request/response pipeline.

---

## 6. Session vs Request Lifecycle

### 6.1 Kernel Session Lifecycle

The kernel manages sessions via `AmplifierSession`:

```
create_session(mount_plan)
    → session.initialize()       # Loads modules, mounts providers
        → mount() called for each module
        → Providers registered at "providers" mount point
    → session.execute(prompt)    # Runs orchestrator loop
        → orchestrator.execute(prompt, context, providers, tools, hooks)
            → provider.complete(request)  ← THIS IS WHERE THE PROVIDER RUNS
    → session.cleanup()          # Unmounts modules
        → cleanup() callables invoked
```

### 6.2 The Copilot SDK Session Problem

The Copilot SDK likely has its own session/conversation concept. These are DIFFERENT from kernel sessions:

| Concept | Kernel Session | SDK Session |
|---|---|---|
| Lifecycle | `create_session` → `execute` → `cleanup` | SDK-managed conversation state |
| Identity | `session_id` from coordinator | SDK conversation/thread ID |
| State | Managed by ContextManager module | Managed by SDK internally |
| Scope | One user interaction or multi-turn conversation | May span multiple API calls |

### 6.3 How They Should Interact

**The provider MUST NOT manage conversation state.** This is the ContextManager's job. The interaction pattern:

```
Kernel Session
├── ContextManager (owns conversation state)
├── Orchestrator (owns execution loop)
│   └── For each turn:
│       ├── context.get_messages_for_request()  → messages
│       ├── Build ChatRequest from messages
│       ├── provider.complete(request)          → ChatResponse
│       ├── context.add_message(response)       → update state
│       └── If tool_calls: execute tools, add results to context
└── Provider (STATELESS translation layer)
    └── complete(request) → translate → API call → translate → response
```

**Critical design principle**: The provider should be **stateless per-request**. It receives a `ChatRequest` with all necessary context (messages, tools, config) and returns a `ChatResponse`. It does NOT:
- Maintain conversation history
- Track which messages have been sent
- Remember previous responses
- Manage a conversation thread

### 6.4 SDK Session Mapping

If the Copilot SDK requires a session/thread ID:

```python
class GitHubCopilotProvider:
    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
        # Map kernel session_id to SDK session concept if needed
        # But DON'T use SDK's conversation management
        thread_id = kwargs.get("thread_id") or self._session_id

        # Send ALL messages from request (ContextManager already compacted)
        # Don't try to diff against previous calls
        sdk_messages = self._translate_messages(request.messages)

        raw = await self._client.chat.completions.create(
            model=self._model,
            messages=sdk_messages,
            tools=self._translate_tools(request.tools),
            # ... other params from request
        )

        return self._translate_response(raw)
```

### 6.5 Multi-Session Considerations

The kernel supports parent/child sessions (via `agents` in Mount Plan). The provider should:
- Be mountable in multiple sessions simultaneously
- Share HTTP client resources across sessions (connection pooling)
- Not assume single-session usage
- Use `coordinator.session_id` to correlate events, not internal state

---

## 7. Complete Provider Skeleton

Based on all the contracts above, here's the exact structure the GitHub Copilot provider module must follow:

```python
# github_copilot_provider/__init__.py

import os
import logging
from typing import Any, Callable

from amplifier_core.models import ProviderInfo, ModelInfo, ConfigField, HookResult
from amplifier_core.message_models import ChatRequest, ChatResponse, ToolCall
from amplifier_core.capabilities import TOOLS, STREAMING, THINKING, VISION, JSON_MODE

logger = logging.getLogger(__name__)


class GitHubCopilotProvider:
    """Amplifier Provider module for GitHub Copilot API."""

    @property
    def name(self) -> str:
        return "github-copilot"

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            name="github-copilot",
            display_name="GitHub Copilot",
            description="GitHub Copilot LLM provider",
            config_fields=[
                ConfigField(
                    id="api_key",
                    field_type="secret",
                    env_var="GITHUB_COPILOT_API_KEY",
                    prompt="Enter GitHub Copilot API key",
                ),
            ],
        )

    async def list_models(self) -> list[ModelInfo]:
        # Fetch from API or return known models
        # MUST include capabilities and cost information
        ...

    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
        # 1. Translate ChatRequest → SDK format
        # 2. Call Copilot API
        # 3. Translate response → ChatResponse
        # 4. Preserve ALL content blocks
        # 5. Report Usage
        ...

    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]:
        # Extract ToolCall objects from response
        ...


async def mount(coordinator, config: dict) -> Callable | None:
    """Entry point for Amplifier module loading."""
    api_key = config.get("api_key") or os.environ.get("GITHUB_COPILOT_API_KEY")
    if not api_key:
        logger.warning("No GitHub Copilot API key - provider not mounted")
        return None

    provider = GitHubCopilotProvider(api_key=api_key, config=config, coordinator=coordinator)
    await coordinator.mount("providers", provider, name="github-copilot")

    coordinator.register_contributor(
        "observability.events",
        "github-copilot",
        lambda: [
            "github-copilot:rate_limit",
            "github-copilot:token_refresh",
        ],
    )

    async def cleanup():
        await provider.close()

    return cleanup
```

```toml
# pyproject.toml (entry point)
[project.entry-points."amplifier.modules"]
github-copilot = "github_copilot_provider:mount"
```

---

## 8. Key Architectural Recommendations

### 8.1 Separate Mechanism from Policy

The current 1700+ line provider should be decomposed:

| Current (likely) | Should Be |
|---|---|
| Retry logic in provider | Retry hook or orchestrator policy |
| Model selection in provider | App layer config / Mount Plan |
| Logging in provider | Event emission → hook handles logging |
| Conversation tracking | ContextManager module |
| Rate limit handling | Provider emits event; hook decides strategy |
| Response formatting | Orchestrator decides presentation |
| Token budget management | ContextManager via `get_messages_for_request()` |

### 8.2 The Provider Should Be Thin

A well-designed Amplifier provider is approximately 200–400 lines:
- ~50 lines: `mount()` + entry point + cleanup
- ~30 lines: `get_info()` + `list_models()`
- ~100 lines: `complete()` (translate in, API call, translate out)
- ~30 lines: `parse_tool_calls()`
- ~100 lines: Message translation helpers
- ~50 lines: Content block mapping

Everything beyond this is likely policy that belongs elsewhere.

### 8.3 Testing Strategy

Use kernel test utilities:

```python
from amplifier_core.testing import TestCoordinator, create_test_coordinator

@pytest.mark.asyncio
async def test_provider_mount():
    coordinator = create_test_coordinator()
    cleanup = await mount(coordinator, {"api_key": "test-key"})
    assert "github-copilot" in coordinator.get_mounted("providers")
    if cleanup:
        await cleanup()

@pytest.mark.asyncio
async def test_provider_graceful_degradation():
    coordinator = create_test_coordinator()
    result = await mount(coordinator, {})  # No API key
    assert result is None
```

---

## 9. Summary of Kernel Contracts the Provider Must Respect

| Contract | Requirement | Reference |
|---|---|---|
| Provider Protocol | Implement 5 methods exactly | `PROVIDER_CONTRACT.md` |
| Entry Point | `mount()` function + pyproject.toml entry | `PROVIDER_CONTRACT.md` §Entry Point |
| Content Preservation | Round-trip all block types, preserve signatures | `PROVIDER_SPECIFICATION.md` §Content |
| Usage Reporting | Return input/output/total tokens | `PROVIDER_SPECIFICATION.md` §Required |
| Graceful Degradation | Return `None` from `mount()` on missing config | `PROVIDER_CONTRACT.md` §Recommended |
| Event Registration | Register custom events via contribution channels | `CONTRIBUTION_CHANNELS.md` |
| Resource Cleanup | Return cleanup callable from `mount()` | `PROVIDER_CONTRACT.md` §Entry Point |
| Capabilities | Populate `ModelInfo.capabilities` with well-known constants | `PROVIDER_SPECIFICATION.md` §Capabilities |
| Cost Information | Populate cost_per_token and cost_tier on ModelInfo | `PROVIDER_CONTRACT.md` §ModelInfo |
| Non-Interference | Never crash the kernel; handle own failures | `DESIGN_PHILOSOPHY.md` §Anti-Patterns |
| Stateless Translation | No conversation state; per-request translation only | Kernel architecture |
| Debug Levels | Support debug/raw_debug config flags | `PROVIDER_SPECIFICATION.md` §Debug |

---

**The center stays still so the edges can move fast.** The GitHub Copilot provider is an edge module. It translates. It emits events. It respects contracts. It does not make policy decisions. Keep it thin, keep it compliant, keep it boring.