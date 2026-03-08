# Wave 3, Agent 26: Integration Architecture Analysis

**Agent Role**: Integration Architecture Expert  
**Date**: 2026-03-08  
**Subject**: How the GitHub Copilot Provider integrates with the Amplifier ecosystem, SDK, MCP, multi-provider scenarios, external services, and testing infrastructure

---

## Executive Summary

The GitHub Copilot Provider is an **integration membrane** — it exists solely to bridge two orchestration worlds (Amplifier and the Copilot SDK) without allowing either to leak into the other. This analysis examines every integration surface: the Amplifier kernel protocols the provider must satisfy, the SDK session lifecycle it must tame, the MCP capabilities it must NOT absorb, the multi-provider scenarios it must support, the external service dependencies it must manage, and the testing infrastructure required to verify all of the above.

The central finding: **the provider's integration complexity is concentrated at exactly two boundaries** — the Amplifier Provider Protocol (upward) and the Copilot SDK session API (downward). Every other integration concern (MCP, multi-provider, authentication, rate limiting) is derived from these two boundaries. Get these two right, and the rest follows. Get either wrong, and no amount of downstream engineering can compensate.

---

## 1. Amplifier Integration

### 1.1 Provider Protocol Compliance

The provider implements a 5-method `Protocol` defined in `amplifier_core/interfaces.py`:

```
Provider Protocol Surface:
  name          → str                          # Identity
  get_info()    → ProviderInfo                 # Metadata + capabilities
  list_models() → list[ModelInfo]              # Available models
  complete()    → ChatResponse                 # Core LLM translation
  parse_tool_calls() → list[ToolCall]          # Tool extraction
```

**Compliance requirements the provider MUST satisfy:**

| Requirement | Integration Point | Verification Method |
|-------------|------------------|---------------------|
| `@runtime_checkable` Protocol | `isinstance(provider, Provider)` at mount time | Unit test with `TestCoordinator` |
| `ProviderInfo.defaults` includes `context_window`, `max_output_tokens` | ContextManager reads these for FIC compaction budget | Integration test: verify compaction uses provider values |
| `ModelInfo.capabilities` uses canonical constants | Orchestrator capability-gates features (e.g., thinking, vision) | Unit test: verify `THINKING` not `REASONING` |
| `ChatResponse` preserves all content block types | Multi-turn conversations require `ThinkingBlock.signature` | Round-trip test: send thinking response, verify signature survives |
| `Usage` reporting is complete | Cost tracking, budget enforcement | Contract test: every response has non-zero `total_tokens` |
| `parse_tool_calls()` produces `ToolCall` from `amplifier_core.message_models` | Orchestrator executes tools based on these | Unit test: parse known tool call formats |

**Critical integration gotcha — ThinkingBlock.signature:**

The Amplifier kernel requires `ThinkingBlock.signature` for multi-turn extended thinking. If the provider strips or fails to capture this field from the SDK response, subsequent turns with thinking-enabled models will fail silently (the model receives thinking content without the cryptographic signature proving it generated it, and may refuse to continue). This is the most fragile integration point in the entire provider.

```
SIGNATURE FLOW:
  Turn 1: LLM generates thinking → SDK returns signature
  Provider MUST: capture signature from SDK event/response
  Provider MUST: include signature in ThinkingBlock
  Amplifier: stores ThinkingBlock with signature in context
  Turn 2: Amplifier sends ThinkingBlock (with signature) back to provider
  Provider MUST: translate ThinkingBlock back to SDK format with signature intact
  SDK: validates signature, continues thinking
```

### 1.2 Hook Integration Patterns

The provider integrates with Amplifier's hook system in three ways:

**1. Passive recipient of orchestrator-emitted events:**

The orchestrator emits `provider:request`, `provider:response`, `provider:error` around every `complete()` call. The provider does NOT emit these — it just needs to return clean `ChatResponse` objects that the orchestrator can pass to hooks.

**2. Active emitter of provider-specific events:**

The provider emits its own events through `coordinator.hooks.emit()`:

```
Provider-emitted events (must register via contribution channels):
  github-copilot:rate_limit      — SDK reported rate limiting
  github-copilot:retry           — Provider retried an operation
  github-copilot:token_refresh   — Authentication token refreshed
  github-copilot:auto_continue   — Response truncation detected, continuing
  sdk_driver:turn                — SDK internal loop turn completed
  sdk_driver:abort               — Circuit breaker triggered
  llm:content_block              — Streaming text content delta
  llm:thinking_block             — Streaming reasoning content delta
```

**3. Fire-and-forget emission pattern:**

Streaming events MUST NOT introduce backpressure. The established pattern:

```python
def _make_emit_callback(self) -> Callable:
    hooks = self._coordinator.hooks
    def emit(event_name: str, data: dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(hooks.emit(event_name, data))
            task.add_done_callback(_handle_emit_error)
        except RuntimeError:
            pass  # No event loop — swallow silently
    return emit
```

This is correct. Hooks that need to observe streaming content (UI rendering, logging) receive events asynchronously. Hooks MUST NOT block the streaming pipeline.

### 1.3 Error Handling Expectations

The kernel expects providers to follow the **Non-Interference Principle**:

```
KERNEL ERROR CONTRACT:
  1. mount() → return None for graceful degradation (missing credentials)
  2. mount() → raise only for truly unrecoverable config errors
  3. complete() → raise well-known exceptions (RateLimitError, AuthenticationError)
  4. complete() → NEVER raise bare Exception — always wrap in domain type
  5. complete() → NEVER corrupt kernel state on failure
  6. complete() → ALWAYS emit observability events before raising
  7. cleanup() → NEVER raise — best-effort resource release
```

**Error translation integration:**

The provider translates SDK exceptions into Amplifier-compatible exceptions. This mapping is the authoritative bridge between SDK error semantics and kernel error semantics:

```
SDK Exception              → Provider Exception        → Kernel Behavior
CopilotAuthError           → AuthenticationError       → Provider skipped, fallback
CopilotRateLimitError      → RateLimitError           → Orchestrator retries with backoff
CopilotTimeoutError        → TimeoutError             → Orchestrator retries
CopilotNetworkError        → ConnectionError          → Orchestrator retries
CopilotContentFilterError  → ContentFilterError       → Return to user with explanation
CopilotModelNotFoundError  → ModelNotFoundError       → Provider skipped for this model
Unknown SDK exception      → RuntimeError(wrapped)    → Logged, provider may be skipped
```

### 1.4 Mount Lifecycle Integration

The provider's mount function is the entry point for Amplifier integration:

```python
async def mount(coordinator: ModuleCoordinator, config: dict) -> Callable | None:
    # Phase 1: Configuration validation
    api_key = config.get("api_key") or os.environ.get("GITHUB_COPILOT_API_KEY")
    if not api_key:
        return None  # Graceful degradation

    # Phase 2: Provider construction
    provider = GitHubCopilotProvider(config=config, coordinator=coordinator)

    # Phase 3: Registration
    await coordinator.mount("providers", provider, name="github-copilot")

    # Phase 4: Contribution channel registration
    coordinator.register_contributor(
        "observability.events", "github-copilot",
        lambda: ["github-copilot:rate_limit", "github-copilot:retry", ...]
    )

    # Phase 5: Cleanup function
    async def cleanup():
        await provider.close()
    return cleanup
```

**Integration invariants:**
- `mount()` is called exactly once per session
- The cleanup callable is invoked on session teardown
- The provider MUST release all resources in cleanup (HTTP clients, subprocess handles)
- The provider MUST be mountable in multiple sessions simultaneously (shared HTTP client)

---

## 2. SDK Integration

### 2.1 Session Management Patterns

The Copilot SDK manages sessions through `CopilotClient` → `CopilotSession`. The provider's integration with the SDK session lifecycle is the most complex part of the entire system:

```
SDK SESSION LIFECYCLE (per complete() call):

  1. CREATE:  session = await client.create_session(config)
  2. HOOK:    session.on(event_handler) → unsubscribe callable
  3. DENY:    Install preToolUse deny hook
  4. SEND:    await session.send(prompt_options)
  5. WAIT:    await event_handler.wait_for_completion()
  6. CAPTURE: Extract tool calls from event handler
  7. BUILD:   Construct ChatResponse from accumulated state
  8. DESTROY: unsubscribe(); session.abort(); session.disconnect()
```

**The Ephemeral Session Pattern:**

Every `complete()` call creates a NEW SDK session. Sessions are NEVER reused across calls. This is the "Deny + Destroy" pattern — the provider denies all SDK tool execution, captures tool calls from events, aborts the session, and destroys it. The session is ephemeral because:

1. Amplifier owns context management (not the SDK)
2. Amplifier owns tool execution (not the SDK)
3. The SDK's internal agent loop conflicts with Amplifier's orchestrator
4. Session state would drift from Amplifier's compacted context

**Session configuration integration:**

```python
session_config = {
    "model": model_id,                          # From ChatRequest
    "system_prompt": extracted_system_message,   # From ChatRequest.messages
    "reasoning_effort": effort_mapping.get(request.reasoning_effort),
    "max_output_tokens": request.max_output_tokens or model_default,
    "tools": translated_tool_definitions,        # From ChatRequest.tools
}
```

The provider translates Amplifier's `ChatRequest` into SDK session configuration. Key translation points:
- System messages extracted from message array → SDK `system_prompt` parameter
- Amplifier tool definitions → SDK tool format (name, description, parameters schema)
- Amplifier reasoning_effort → SDK reasoning_effort (direct mapping for compatible values)

### 2.2 Event Handling Integration

The SDK emits events through `session.on(handler)`. The provider's `SdkEventHandler` bridges SDK events to Amplifier events:

```
SDK EVENT → HANDLER ACTION → AMPLIFIER EVENT

ASSISTANT_MESSAGE_DELTA    → accumulate text     → emit llm:content_block
ASSISTANT_REASONING_DELTA  → accumulate thinking → emit llm:thinking_block
ASSISTANT_MESSAGE          → capture tools,      → (internal: build response)
                             finalize blocks
SESSION_IDLE               → check circuit       → emit sdk_driver:turn
                             breaker, abort
                             if tools captured
ERROR                      → translate error     → emit provider:error
preToolUse (hook)          → return DENY         → (internal: prevent execution)
```

**Event handler state machine:**

```
IDLE → RECEIVING_DELTAS → BLOCK_COMPLETE → [IDLE | TOOLS_CAPTURED | ABORTED]
  │                                              │
  └──────────── TIMEOUT/ERROR ──────────────────→ ERROR_STATE
```

The handler transitions are driven entirely by SDK events. The provider awaits completion via `asyncio.Event`, with a timeout that fires BEFORE the SDK's internal timeout (5-second buffer) to ensure the provider controls error handling.

### 2.3 Tool Registration Integration

Tools are registered with the SDK session so the LLM can "see" them, but the provider's deny hook prevents the SDK from executing them:

```
TOOL REGISTRATION FLOW:
  1. Amplifier provides tool definitions in ChatRequest.tools
  2. Provider translates to SDK tool format:
     {name, description, parameters: JSON Schema}
  3. Tools registered in session config
  4. LLM generates tool_request in response
  5. SDK's preToolUse hook fires → Provider returns DENY
  6. Tool request captured from ASSISTANT_MESSAGE event
  7. Provider returns tool calls in ChatResponse
  8. Amplifier orchestrator executes tools via its own tool modules
  9. Tool results added to context for next complete() call
```

**Why this indirection matters:**
- Amplifier's `tool:pre` hooks can deny dangerous tool calls
- Amplifier's `tool:post` hooks can inject corrective feedback
- Approval gates can require user permission
- Custom tool modules can override behavior
- Tool results are stored in Amplifier's context (not SDK's)

---

## 3. MCP Integration

### 3.1 Can the Provider Expose MCP Capabilities?

**Short answer: No, and it SHOULD NOT.**

The Copilot SDK supports MCP (Model Context Protocol) servers natively — it can connect to MCP servers and expose their tools to the LLM. However, delegating MCP to the SDK would bypass all of Amplifier's safety guarantees:

```
WRONG (SDK-managed MCP):
  Amplifier → Provider → SDK → MCP Server → SDK → Provider → Amplifier
  
  Problems:
  - Amplifier hooks never see MCP tool calls
  - Approval gates are bypassed
  - Context injection doesn't work for MCP results
  - MCP tools only work with Copilot provider (not portable)

RIGHT (Amplifier-managed MCP):
  Amplifier → MCP Tool Module → MCP Server → MCP Tool Module → Amplifier
  
  Benefits:
  - All Amplifier hooks see MCP tool calls
  - Approval gates work for MCP tools
  - Context injection works for MCP results
  - MCP tools work across ALL providers
```

### 3.2 Tool Bridging Patterns

If MCP tools need to be available through the Copilot provider, they should be bridged at the Amplifier level:

```
MCP TOOL BRIDGING:

  1. Amplifier MCP module discovers tools from MCP server
  2. MCP tools registered as Amplifier tool modules
  3. Tool definitions included in ChatRequest.tools
  4. Provider registers them with SDK session (LLM visibility)
  5. LLM requests MCP tool → Provider captures via Deny+Destroy
  6. Amplifier orchestrator executes MCP tool via MCP tool module
  7. Result added to context, next complete() call includes result
```

This bridging is transparent to the provider — MCP tools look identical to any other Amplifier tool. The provider never knows (or needs to know) whether a tool is MCP-backed, filesystem-backed, or custom.

### 3.3 Protocol Translation

The provider should explicitly DISABLE the SDK's MCP integration to prevent conflicts:

```python
session_config = {
    # ... other config ...
    "mcp_servers": [],  # Explicitly disable SDK-managed MCP
}
```

If the SDK auto-discovers MCP servers, the provider should suppress this. Any MCP capability should flow through Amplifier's MCP modules, not through the SDK.

**Future consideration:** If Amplifier adds a dedicated MCP module protocol, the provider could optionally report SDK-discovered MCP servers as available tool sources (metadata only), allowing Amplifier to decide whether to connect to them through its own MCP infrastructure.

---

## 4. Multi-Provider Scenarios

### 4.1 Working Alongside Other Providers

Amplifier supports mounting multiple providers simultaneously. The Copilot provider must behave as a good citizen in multi-provider configurations:

```
MULTI-PROVIDER MOUNT PLAN:
  providers:
    - github-copilot  (priority: 100, models: claude-*, gpt-*, o-*)
    - anthropic        (priority: 200, models: claude-*)
    - openai           (priority: 300, models: gpt-*, o-*)

  Orchestrator selects based on:
    1. Requested model availability
    2. Provider priority (lower = preferred)
    3. Provider health status
    4. Fallback chain on error
```

**Integration requirements for multi-provider:**

| Requirement | Why It Matters | Implementation |
|-------------|---------------|----------------|
| Accurate `list_models()` | Orchestrator routes by model availability | Query SDK for current model list, cache with TTL |
| Correct error types | Orchestrator uses error type for fallback decisions | `AuthenticationError` → skip provider, `RateLimitError` → retry with backoff |
| Stateless `complete()` | Provider switching mid-conversation must work | No conversation state in provider; all context in ChatRequest |
| Fast `get_info()` | Called during provider selection | Return cached ProviderInfo, no API calls |
| Health reporting | Orchestrator needs to know if provider is functional | `check_health()` pings SDK subprocess |

### 4.2 Provider Selection Criteria

The orchestrator selects providers based on capabilities reported through `get_info()` and `list_models()`. The Copilot provider must accurately report:

```python
# ModelInfo for each available model
ModelInfo(
    id="claude-sonnet-4-20250514",
    display_name="Claude Sonnet 4",
    context_window=200000,
    max_output_tokens=16384,
    capabilities=[TOOLS, STREAMING, THINKING, VISION],
    cost_per_input_token=0.003,
    cost_per_output_token=0.015,
    metadata={"cost_tier": "medium", "provider": "github-copilot"},
)
```

**Capability accuracy is critical for selection:** If the Copilot provider reports `THINKING` capability for a model that doesn't support it through the SDK, the orchestrator may route thinking-enabled requests to a provider that can't fulfill them. This causes silent degradation (response without thinking) rather than a clean fallback to a provider that genuinely supports thinking.

### 4.3 Fallback Patterns

When the Copilot provider fails, the orchestrator needs clean error signals for fallback:

```
FALLBACK DECISION TREE:

  complete() raises AuthenticationError
    → Orchestrator: Skip github-copilot for remainder of session
    → Try next provider (anthropic) with same ChatRequest
    → ChatRequest is provider-agnostic (no Copilot-specific data)

  complete() raises RateLimitError(retry_after=30)
    → Orchestrator: Backoff github-copilot for 30 seconds
    → Try next provider immediately
    → When backoff expires, github-copilot rejoins selection pool

  complete() raises ModelNotFoundError
    → Orchestrator: Remove model from github-copilot's available list
    → Route to alternative provider for this model
    → Other models on github-copilot remain available

  complete() raises TimeoutError
    → Orchestrator: Retry once on github-copilot
    → If retry fails: try next provider
    → Mark github-copilot as degraded (health check before next use)
```

**Key integration property:** The `ChatRequest` is fully self-contained and provider-agnostic. It contains all messages, tools, and configuration needed for any provider to fulfill the request. This enables seamless fallback — the orchestrator simply passes the same `ChatRequest` to the next provider.

### 4.4 Provider Interchangeability Invariant

The provider MUST maintain this invariant: **A session can switch from Copilot to any other provider mid-conversation without losing context.**

This is only possible if:
1. Context is managed by Amplifier's ContextManager (not the SDK) ✓
2. Tool execution is managed by Amplifier's orchestrator (not the SDK) ✓
3. The provider is a stateless translation layer ✓
4. Content blocks round-trip correctly through all providers ✓ (if `ThinkingBlock.signature` is preserved)

---

## 5. External Services

### 5.1 GitHub API Integration

The provider depends on GitHub's infrastructure through the Copilot SDK:

```
EXTERNAL SERVICE DEPENDENCY CHAIN:

  Provider → SDK Client → CLI Subprocess → GitHub API
                                              │
                                     ┌────────┴────────┐
                                     │  Authentication  │
                                     │  (OAuth/PAT)     │
                                     ├─────────────────┤
                                     │  Model Routing   │
                                     │  (which backend) │
                                     ├─────────────────┤
                                     │  LLM Inference   │
                                     │  (actual model)  │
                                     ├─────────────────┤
                                     │  Rate Limiting   │
                                     │  (token bucket)  │
                                     └─────────────────┘
```

The provider NEVER communicates with GitHub's API directly — all communication flows through the SDK's CLI subprocess. This is an important integration boundary:

- **Provider responsibility:** Manage the SDK client lifecycle (start/stop subprocess)
- **SDK responsibility:** Manage HTTP connections, authentication headers, API versioning
- **Provider does NOT:** Make direct HTTP calls to GitHub, manage OAuth tokens, handle API pagination

### 5.2 Authentication Flows

Authentication is managed entirely by the SDK. The provider's integration with authentication:

```
AUTHENTICATION INTEGRATION:

  Mount time:
    1. Config provides API key or OAuth token
    2. Provider passes to SDK client constructor
    3. SDK validates token and establishes session
    4. If auth fails: mount() returns None (graceful degradation)

  Runtime:
    1. SDK handles token refresh transparently
    2. If token expires during complete(): SDK raises AuthError
    3. Provider translates to AuthenticationError
    4. Orchestrator may retry (if token refresh succeeded) or fallback

  Provider events:
    - github-copilot:token_refresh — emitted when SDK refreshes token
    - github-copilot:auth_failure  — emitted when auth fails permanently
```

**BYOK (Bring Your Own Key) integration:**

The SDK supports BYOK through Azure AI Foundry. The provider should pass BYOK configuration through to the SDK without interpretation:

```python
# BYOK config flows through transparently
session_config = {
    "model": model_id,
    # BYOK fields passed directly to SDK
    "azure_endpoint": config.get("azure_endpoint"),
    "azure_api_key": config.get("azure_api_key"),
    "azure_deployment": config.get("azure_deployment"),
}
```

The provider does NOT validate BYOK credentials — that's the SDK's responsibility. The provider only needs to pass the configuration through and translate any resulting auth errors.

### 5.3 Rate Limiting Coordination

Rate limiting is a shared concern between the SDK, the provider, and Amplifier's orchestrator:

```
RATE LIMIT COORDINATION:

  Layer 1: SDK (detection)
    - SDK receives 429 response from GitHub API
    - SDK raises RateLimitError with retry_after header
    - SDK may retry internally (depends on SDK config)

  Layer 2: Provider (translation + emission)
    - Catches SDK RateLimitError
    - Emits github-copilot:rate_limit event with retry_after
    - Raises Amplifier-compatible RateLimitError
    - Does NOT retry internally (that's orchestrator policy)

  Layer 3: Orchestrator (policy)
    - Receives RateLimitError from provider
    - Applies retry policy (exponential backoff, jitter)
    - May fall back to alternative provider
    - May inform user of delay

  Layer 4: Hooks (observation)
    - github-copilot:rate_limit event visible to all hooks
    - Logging hook records rate limit events
    - Metrics hook tracks rate limit frequency
    - Alert hook may notify user of persistent rate limiting
```

**Critical integration principle:** The provider MUST NOT implement retry logic for rate limits. Retry is a POLICY decision owned by the orchestrator or hooks. The provider's job is to detect, translate, emit, and propagate. This separation ensures:
- Different deployments can have different retry strategies
- Rate limiting across multiple providers is coordinated at the orchestrator level
- Hooks can implement custom rate limit responses (e.g., switch to cheaper model)

---

## 6. Testing Integration

### 6.1 Test Environment Setup

The provider's integration tests require a layered test infrastructure:

```
TEST ENVIRONMENT LAYERS:

  Layer 1: Unit Tests (no external dependencies)
    - TestCoordinator from amplifier_core.testing
    - Mock SDK client
    - Verify: Protocol compliance, message translation, error mapping
    - Run: Every commit, < 5 seconds

  Layer 2: Integration Tests (mock SDK, real Amplifier)
    - Real ModuleCoordinator with test hooks
    - Mock SDK client that returns scripted responses
    - Verify: Mount lifecycle, event emission, hook interaction
    - Run: Every commit, < 30 seconds

  Layer 3: SDK Integration Tests (real SDK, mock API)
    - Real SDK client with mock HTTP backend
    - Verify: Session lifecycle, event handling, streaming
    - Run: CI pipeline, < 2 minutes

  Layer 4: End-to-End Tests (real SDK, real API)
    - Real SDK client, real GitHub API
    - Verify: Authentication, model availability, actual completions
    - Run: Nightly/manual, < 10 minutes, requires API credentials
```

### 6.2 Mock Service Integration

**TestCoordinator mock:**

```python
from amplifier_core.testing import create_test_coordinator

async def test_provider_mounts_correctly():
    coordinator = create_test_coordinator()
    cleanup = await mount(coordinator, {"api_key": "test-key-ghu_xxx"})
    
    # Verify provider is mounted
    providers = coordinator.get_mounted("providers")
    assert "github-copilot" in providers
    
    # Verify provider satisfies Protocol
    provider = providers["github-copilot"]
    assert isinstance(provider, Provider)
    
    # Verify contribution channels registered
    events = coordinator.get_contributions("observability.events", "github-copilot")
    assert "github-copilot:rate_limit" in events
    
    # Cleanup
    if cleanup:
        await cleanup()
```

**Mock SDK client for streaming tests:**

```python
class MockSdkSession:
    """Simulates SDK session with scripted event sequences."""
    
    def __init__(self, events: list[tuple[str, dict]]):
        self._events = events
        self._handlers = []
    
    def on(self, handler):
        self._handlers.append(handler)
        return lambda: self._handlers.remove(handler)
    
    async def send(self, options):
        for event_type, data in self._events:
            for handler in self._handlers:
                await handler(event_type, data)
    
    async def abort(self): pass
    async def disconnect(self): pass

# Usage in tests:
mock_session = MockSdkSession([
    ("ASSISTANT_MESSAGE_DELTA", {"content": "Hello"}),
    ("ASSISTANT_MESSAGE_DELTA", {"content": " world"}),
    ("ASSISTANT_MESSAGE", {"content": "Hello world", "tool_requests": []}),
    ("SESSION_IDLE", {}),
])
```

**Mock for tool capture testing:**

```python
mock_tool_session = MockSdkSession([
    ("ASSISTANT_MESSAGE_DELTA", {"content": "Let me read that file"}),
    ("ASSISTANT_MESSAGE", {
        "content": "Let me read that file",
        "tool_requests": [
            {"id": "call_1", "name": "read_file", "args": {"path": "/src/main.py"}}
        ],
    }),
    ("SESSION_IDLE", {}),
    # preToolUse hook fires → DENY
    # SDK retries → SESSION_IDLE fires again
    ("SESSION_IDLE", {}),
])
```

### 6.3 CI/CD Integration

**CI pipeline stages:**

```
STAGE 1: Static Analysis (< 30s)
  - pyright type checking (verifies Protocol compliance)
  - ruff linting and formatting
  - Contract coverage check (every MUST clause has a test)

STAGE 2: Unit Tests (< 30s)
  - Protocol compliance tests
  - Message translation tests
  - Error mapping tests
  - Tool parsing tests
  - No network, no SDK, no subprocess

STAGE 3: Integration Tests (< 2m)
  - Mount lifecycle with TestCoordinator
  - Event emission verification
  - Streaming accumulation tests
  - Circuit breaker tests
  - Mock SDK, no network

STAGE 4: SDK Integration Tests (< 5m, optional)
  - Real SDK client, mock HTTP backend
  - Session lifecycle verification
  - Event handling verification
  - Only runs if SDK is available in CI environment

STAGE 5: E2E Smoke Tests (nightly, requires credentials)
  - Real API call with minimal prompt
  - Verify authentication works
  - Verify model list is non-empty
  - Verify basic completion returns content
```

**Contract verification in CI:**

```python
# scripts/verify_contracts.py
def verify_protocol_compliance():
    """Every MUST clause in Provider Protocol has a test."""
    must_clauses = extract_must_clauses(Provider)
    tested_clauses = find_tests_for_clauses("tests/contract_tests/")
    untested = must_clauses - tested_clauses
    if untested:
        fail(f"Untested contract clauses: {untested}")

def verify_error_mapping_completeness():
    """Every SDK exception in SDK_ERROR_MAP has a test."""
    mapped_errors = set(SDK_ERROR_MAP.keys())
    tested_errors = find_error_tests("tests/test_error_translation.py")
    untested = mapped_errors - tested_errors
    if untested:
        fail(f"Untested error mappings: {untested}")

def verify_event_emission():
    """Every registered event has at least one emission test."""
    registered_events = get_registered_events()
    tested_events = find_event_tests("tests/")
    untested = registered_events - tested_events
    if untested:
        fail(f"Untested events: {untested}")
```

### 6.4 Test Fixtures for Multi-Provider Scenarios

```python
@pytest.fixture
async def multi_provider_coordinator():
    """Sets up a coordinator with multiple providers for fallback testing."""
    coordinator = create_test_coordinator()
    
    # Mount Copilot provider (priority 100)
    copilot = MockCopilotProvider(priority=100)
    await coordinator.mount("providers", copilot, name="github-copilot")
    
    # Mount fallback provider (priority 200)
    fallback = MockFallbackProvider(priority=200)
    await coordinator.mount("providers", fallback, name="fallback")
    
    return coordinator, copilot, fallback

async def test_fallback_on_rate_limit(multi_provider_coordinator):
    coordinator, copilot, fallback = multi_provider_coordinator
    copilot.set_behavior(raise_error=RateLimitError("Rate limited", retry_after=30))
    
    # Orchestrator should fall back to fallback provider
    response = await orchestrator.execute(request, coordinator)
    assert response.provider_used == "fallback"
```

---

## 7. Integration Patterns Summary

### 7.1 Pattern Catalog

| Pattern | Where Used | Why |
|---------|-----------|-----|
| **Deny + Destroy** | SDK tool execution | Prevent SDK from running tools; let Amplifier handle them |
| **Fire-and-Forget** | Streaming event emission | Prevent hook backpressure on streaming pipeline |
| **Ephemeral Session** | Every complete() call | Prevent SDK state from diverging from Amplifier context |
| **Error Translation** | SDK → Amplifier boundary | Clean error semantics for orchestrator fallback decisions |
| **Capability Reporting** | get_info(), list_models() | Enable orchestrator model routing and feature gating |
| **Contribution Channels** | mount() registration | Enable hook system to discover provider-specific events |
| **Transparent Passthrough** | BYOK config, MCP disable | Let SDK handle what it owns; don't interpret or modify |
| **Circuit Breaker** | SDK loop control | Prevent 305-turn runaway loops from exhausting resources |

### 7.2 Integration Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Correct Approach |
|-------------|---------------|------------------|
| Provider manages conversation state | Conflicts with ContextManager | Stateless per-request translation |
| Provider retries internally | Retry is policy, not mechanism | Raise error; let orchestrator decide |
| Provider connects to MCP servers | Bypasses Amplifier hooks and approval gates | MCP tools as Amplifier tool modules |
| Provider manages its own context window | Conflicts with FIC compaction | Report context_window in get_info(); let ContextManager budget |
| Provider executes tools | Bypasses tool:pre/tool:post hooks | Deny+Destroy; return tool calls for orchestrator |
| Provider logs directly to stdout | Bypasses hook-based logging | Emit events; hooks decide logging destination |
| Provider negotiates with other providers | Provider has no awareness of other providers | Orchestrator handles multi-provider coordination |

### 7.3 Integration Health Checklist

Before any release, verify these integration properties:

```
□ Protocol compliance: isinstance(provider, Provider) passes
□ Mount lifecycle: mount() → complete() → cleanup() works
□ Graceful degradation: mount() returns None with missing credentials
□ Content preservation: ThinkingBlock.signature round-trips correctly
□ Error translation: All SDK errors map to domain exceptions
□ Event emission: All registered events are emitted in correct scenarios
□ Streaming: Fire-and-forget emission doesn't block pipeline
□ Tool capture: Deny+Destroy captures tools without SDK execution
□ Circuit breaker: Runaway SDK loops are terminated
□ Multi-provider: ChatRequest is provider-agnostic (no Copilot-specific data)
□ Fallback: Error types enable orchestrator fallback decisions
□ MCP disabled: SDK MCP servers are not connected
□ Cleanup: All resources released on session teardown
□ Health check: Provider reports accurate health status
```

---

## 8. Recommendations

### 8.1 Immediate (Next-Gen Provider)

1. **Formalize ThinkingBlock.signature preservation** — This is the most fragile integration point. Add explicit round-trip tests for every content block type.
2. **Disable SDK MCP explicitly** — Pass empty MCP server list in session config.
3. **Emit events before raising** — Every error path must emit an observability event before raising the translated exception.
4. **Test multi-provider fallback** — Add integration tests that verify the orchestrator can fall back from Copilot to another provider on each error type.

### 8.2 Medium-Term

1. **Health check integration** — Feed streaming transport failures into the health check system so the orchestrator can proactively avoid unhealthy providers.
2. **Capability negotiation per model** — Add `get_model_capabilities(model_id)` for dynamic capability reporting.
3. **Event schema validation** — In development mode, validate all emitted events against the registered event catalog.

### 8.3 Long-Term

1. **Provider remains a pipe** — As LLMs become more agentic, resist the temptation to add agentic capabilities to the provider. Agent delegation, planning, sub-tasks — all should be orchestrator concerns.
2. **MCP as first-class Amplifier modules** — When Amplifier adds dedicated MCP infrastructure, the provider should report SDK-discovered MCP servers as metadata (not connect to them).
3. **Cross-provider content block standardization** — Ensure all providers (Copilot, Anthropic, OpenAI) produce identical content block types so mid-conversation provider switching is truly seamless.

---

*The provider is the thinnest possible membrane between two orchestration worlds. Its integration surface is deliberately minimal — five methods up, one session lifecycle down. Everything else is a consequence of keeping that membrane thin, transparent, and reliable.*
