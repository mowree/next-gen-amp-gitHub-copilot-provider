# WAVE 3, AGENT 28: Anthropic/OpenAI Provider Comparison Expert

**Agent Role**: Provider Comparison & Cross-Pollination Analyst  
**Date**: 2026-03-08  
**Scope**: How Anthropic and OpenAI providers work in Amplifier, shared patterns, Copilot uniqueness, borrowable best practices, anti-patterns to avoid, contract evolution lessons, and unified provider abstractions

---

## Executive Summary

The Amplifier ecosystem hosts multiple LLM providers that all implement the same 5-method Provider Protocol (`name`, `get_info()`, `list_models()`, `complete()`, `parse_tool_calls()`). Despite sharing this contract, the three major providers — **Anthropic**, **OpenAI**, and **GitHub Copilot** — differ dramatically in their integration architecture. Anthropic and OpenAI providers are "thin translators" that talk directly to HTTP APIs with well-documented, stable SDKs. The Copilot provider is an "agentic SDK tamer" that must suppress an opinionated CLI subprocess's internal orchestration loop. This fundamental difference means **not all patterns from Anthropic/OpenAI apply to Copilot**, and blindly copying them would create fragile abstractions. This analysis identifies what CAN be borrowed, what MUST NOT be borrowed, and what unified patterns ALL providers should adopt.

---

## 1. Provider Comparison

### 1.1 How the Anthropic Provider Works in Amplifier

The Anthropic provider is the **gold standard** of simplicity in Amplifier's provider ecosystem. Its architecture:

```
┌─────────────────────────────────────────────────────────────┐
│  ANTHROPIC PROVIDER (thin HTTP translator)                   │
│                                                              │
│  ChatRequest                                                 │
│    │                                                         │
│    ▼                                                         │
│  Message Conversion (Amplifier → Anthropic Messages API)     │
│    │  - Role mapping (system → system block)                 │
│    │  - Content blocks (text, image, tool_use, tool_result)  │
│    │  - Tool definitions (JSON Schema format)                │
│    │                                                         │
│    ▼                                                         │
│  anthropic.AsyncAnthropic.messages.create()                  │
│    │  - Direct HTTP POST to api.anthropic.com                │
│    │  - API key in Authorization header                      │
│    │  - Streaming via SSE (server-sent events)               │
│    │                                                         │
│    ▼                                                         │
│  Response Conversion (Anthropic → ChatResponse)              │
│    │  - ContentBlock mapping (text, thinking, tool_use)      │
│    │  - Usage extraction (input_tokens, output_tokens)       │
│    │  - Stop reason mapping (end_turn → stop, tool_use)      │
│    │                                                         │
│    ▼                                                         │
│  ChatResponse (returned to orchestrator)                     │
└─────────────────────────────────────────────────────────────┘
```

**Key characteristics:**

1. **Stateless HTTP calls**: Each `complete()` is a single HTTP POST. No subprocess, no persistent connection, no session management.
2. **Native tool support**: Anthropic's API natively returns structured `tool_use` content blocks with JSON arguments. No XML parsing, no fake tool call detection needed.
3. **Native streaming**: SSE stream yields typed events (`content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`). Each event has a well-defined schema.
4. **Native extended thinking**: Claude models support `thinking` content blocks natively via `thinking` parameter. The API returns `thinking` blocks with `signature` field directly — no heuristic detection needed.
5. **Direct error types**: `anthropic.AuthenticationError`, `anthropic.RateLimitError`, `anthropic.APIError` map cleanly to Amplifier's kernel error hierarchy.
6. **No agent loop suppression**: The Anthropic SDK has no internal agent loop. It sends a request and returns a response. Period.

**Provider complexity**: ~800-1200 lines total. The vast majority is format conversion.

### 1.2 How the OpenAI Provider Works in Amplifier

The OpenAI provider is structurally similar to Anthropic but handles a wider model surface area:

```
┌─────────────────────────────────────────────────────────────┐
│  OPENAI PROVIDER (thin HTTP translator + model routing)      │
│                                                              │
│  ChatRequest                                                 │
│    │                                                         │
│    ▼                                                         │
│  Message Conversion (Amplifier → OpenAI Chat Completions)    │
│    │  - Role mapping (system, user, assistant, tool)         │
│    │  - Tool calls as function_call / tool_calls array       │
│    │  - Content: string or array of content parts            │
│    │                                                         │
│    ▼                                                         │
│  Model Routing:                                              │
│    │  - GPT-4/4o → chat/completions endpoint                 │
│    │  - o1/o3/o4 → chat/completions with reasoning_effort    │
│    │  - Responses API (newer models)                         │
│    │                                                         │
│    ▼                                                         │
│  openai.AsyncOpenAI.chat.completions.create()                │
│    │  - HTTP POST to api.openai.com                          │
│    │  - Streaming via SSE                                    │
│    │                                                         │
│    ▼                                                         │
│  Response Conversion (OpenAI → ChatResponse)                 │
│    │  - choices[0].message.content → TextBlock               │
│    │  - choices[0].message.tool_calls → ToolCallBlocks       │
│    │  - usage.prompt_tokens / completion_tokens               │
│    │  - finish_reason mapping (stop, tool_calls, length)     │
│    │                                                         │
│    ▼                                                         │
│  ChatResponse                                                │
└─────────────────────────────────────────────────────────────┘
```

**Key characteristics:**

1. **Stateless HTTP calls**: Same as Anthropic. Pure request-response.
2. **Structured tool calls**: OpenAI returns `tool_calls` as a structured array with `function.name` and `function.arguments` (JSON string). No XML, no parsing ambiguity.
3. **Model-dependent behavior**: o-series models (o1, o3, o4) have different parameter support (no `temperature`, uses `reasoning_effort`). The provider must route parameters per model family.
4. **Two API surfaces**: Chat Completions API (legacy) and Responses API (newer). Provider must handle both.
5. **Streaming differences**: SSE stream for Chat Completions yields `delta` objects. Tool call streaming yields incremental `function.arguments` chunks that must be concatenated.
6. **Rate limiting**: OpenAI returns `Retry-After` header and `x-ratelimit-*` headers. The SDK surfaces these as `RateLimitError` with retry timing.

**Provider complexity**: ~1000-1500 lines. Format conversion + model routing logic.

### 1.3 Shared Patterns Across Anthropic and OpenAI Providers

| Pattern | Anthropic | OpenAI | Shared? |
|---------|-----------|--------|---------|
| Stateless HTTP per `complete()` | ✅ | ✅ | ✅ Universal |
| Direct API key auth | ✅ | ✅ | ✅ Universal |
| Native structured tool calls | ✅ (content blocks) | ✅ (tool_calls array) | ✅ Universal |
| SSE streaming | ✅ | ✅ | ✅ Universal |
| SDK handles retries | ✅ (configurable) | ✅ (configurable) | ✅ Universal |
| SDK raises typed exceptions | ✅ | ✅ | ✅ Universal |
| No internal agent loop | ✅ | ✅ | ✅ Universal |
| No subprocess management | ✅ | ✅ | ✅ Universal |
| Model capability detection | Via API metadata | Via model ID patterns | ⚠️ Partial |
| Extended thinking support | ✅ Native | ✅ (o-series reasoning) | ⚠️ Different APIs |
| Content filter handling | Via stop_reason | Via finish_reason | ⚠️ Different signals |

**The critical shared pattern**: Both Anthropic and OpenAI providers are **pure translators**. They convert Amplifier's `ChatRequest` into provider-native format, make an HTTP call, and convert the response back. There is no state, no subprocess, no loop suppression, no session management.

---

## 2. Copilot Uniqueness

### 2.1 What Makes Copilot SDK Fundamentally Different

The Copilot SDK is **not an HTTP API client**. It is an **agentic runtime** that manages its own orchestration loop via a CLI subprocess:

```
ANTHROPIC/OPENAI:                     COPILOT:
┌──────────────┐                      ┌──────────────────────────┐
│ HTTP Client   │                      │ CLI Subprocess (~500MB)   │
│              │                      │   ├── JSON-RPC transport  │
│ request() ──►│──HTTP──► API         │   ├── Internal agent loop │
│              │                      │   ├── Built-in tools (27) │
│ ◄── response │◄─HTTP──              │   ├── Session management  │
│              │                      │   ├── Permission system   │
└──────────────┘                      │   ├── MCP integration     │
                                      │   └── Context management  │
  Simple.                             └──────────────────────────┘
  One call.                             Complex.
  One response.                         Must be TAMED.
```

**Fundamental differences that no pattern from Anthropic/OpenAI can address:**

1. **Subprocess lifecycle management**: The CLI subprocess must be started, health-checked, restarted on crash, and shared across multiple provider instances via a process-level singleton with reference counting. Anthropic/OpenAI have nothing analogous — `httpx` manages connections transparently.

2. **Agent loop suppression (Deny + Destroy)**: The SDK's core value proposition IS its agent loop. It wants to receive tool calls, execute them, send results back, and iterate. The Copilot provider must **subvert this entire paradigm** by denying all tool execution and destroying sessions after capturing tool requests. This pattern has zero parallel in Anthropic/OpenAI.

3. **Session-per-request**: Each `complete()` creates an ephemeral `CopilotSession`, registers tools, installs deny hooks, sends the prompt, captures the response, and destroys the session. Anthropic/OpenAI create no sessions — they make stateless HTTP calls.

4. **Event-based response collection**: Instead of receiving a structured HTTP response, the Copilot provider subscribes to an event stream (`session.on(handler)`) and accumulates state from delta events, complete message events, and idle signals. The `SdkEventHandler` is a mini state machine that has no equivalent in HTTP-based providers.

5. **Circuit breaker for runaway loops**: The SDK's retry-after-denial behavior can cause 305-turn, 607-tool accumulation loops. The `SdkDriver` with `LoopController`, `ToolCaptureStrategy`, and `CircuitBreaker` exists solely to prevent this. HTTP providers never experience runaway loops because they make exactly one call.

6. **Prompt format conversion**: Anthropic/OpenAI accept structured message arrays natively. The Copilot SDK takes a single prompt string (serialized `Human:/Assistant:` format) plus session config. The `converters.py` module exists to bridge this gap.

7. **27 built-in tools to exclude**: The SDK has 27 built-in tools that must be excluded to prevent interference with Amplifier's tool system. The `COPILOT_BUILTIN_TOOL_NAMES` set is manually maintained. No other provider has this concern.

### 2.2 Patterns That DON'T Apply from Other Providers

| Pattern from Anthropic/OpenAI | Why It Doesn't Apply to Copilot |
|-------------------------------|--------------------------------|
| Direct HTTP error parsing | Errors come as SDK exceptions from JSON-RPC, not HTTP status codes |
| `Retry-After` header extraction | Rate limit info is embedded in error message strings, requiring regex extraction |
| SDK-level automatic retries | Cannot use — SDK retries happen inside the agent loop which we suppress |
| Simple streaming via SSE | Streaming is via JSON-RPC notifications from subprocess, not SSE |
| Stateless connection pooling | Must manage a persistent subprocess with health checks |
| API version in URL/header | SDK version is the CLI binary version, discovered at runtime |
| Direct model parameter passthrough | Session config vs. per-message config; `reasoning_effort` is session-level |
| Native content filter detection | Content filters detected via string matching in error messages |

### 2.3 Unique Challenges Only Copilot Faces

1. **Binary dependency management**: The provider depends on a platform-specific CLI binary (`_platform.py` handles Windows/Unix/macOS detection). Anthropic/OpenAI depend only on Python packages.

2. **Permission handler configuration**: The SDK has a permission system (`PermissionHandler.approve_all`) that's irrelevant in Deny+Destroy mode but must be configured. No parallel in other providers.

3. **Fake tool call detection**: Because the prompt format uses `<tool_used>` XML tags, models sometimes write tool calls as plain text instead of structured calls. The provider has regex-based detection with retry logic. This is a prompt format problem unique to the Copilot integration.

4. **Missing tool result repair**: The provider must detect and repair missing tool results in conversation history (`_repair_missing_tool_results()`). This compensates for the ephemeral session pattern where tool results may be lost between sessions. HTTP providers don't have this issue because they send complete message arrays.

5. **Model cache with 4-tier fallback**: Memory → disk → bundled → defaults. The Copilot SDK's `list_models()` API has different latency/reliability characteristics than Anthropic/OpenAI's model endpoints, necessitating aggressive caching.

---

## 3. Best Practices to Borrow

### 3.1 From the Anthropic Provider

**1. Native content block model**

Anthropic's API returns structured content blocks (`text`, `thinking`, `tool_use`) that map directly to Amplifier's `ContentBlock` types. The Copilot provider should aspire to the same clean mapping, even though it builds blocks from events rather than receiving them from an API:

```
ANTHROPIC (ideal):    API returns ContentBlock[] → map to Amplifier ContentBlock[]
COPILOT (current):    Events accumulate → manually construct blocks
COPILOT (improved):   StreamAccumulator builds ContentBlock[] with same structure
```

**Recommendation**: The `StreamAccumulator` should produce content blocks identical in structure to what the Anthropic provider returns. Same `TextBlock`, `ThinkingBlock`, `ToolCallBlock` types. This enables the orchestrator to treat all providers uniformly.

**2. Thinking signature preservation**

Anthropic's API returns `thinking.signature` in the response, which is required for multi-turn conversations with extended thinking. The Copilot provider must extract this from SDK events. The Anthropic provider's pattern of preserving the signature through the `ThinkingBlock` dataclass should be adopted exactly.

**3. Error hierarchy with `retryable` flag**

Anthropic's exception classes carry a `retryable` attribute that the retry logic reads directly. The Copilot provider already does this (`CopilotProviderError` base has retry semantics), which is correct. This pattern should be maintained and potentially strengthened with explicit retry-after timing.

**4. Usage metadata structure**

Anthropic's API returns detailed usage: `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`. The Copilot provider should aim to return usage metadata with the same granularity. Currently, the SDK may not provide all fields, but the `ChatResponse.usage` structure should be consistent across providers.

### 3.2 From the OpenAI Provider

**1. Model family routing**

OpenAI's provider routes parameters differently based on model family (GPT-4 vs. o-series). The Copilot provider already does this with `_model_supports_reasoning()`, but should formalize it:

```python
# Pattern from OpenAI provider (worth adopting)
class ModelFamily(Enum):
    STANDARD = "standard"        # GPT-4, Claude non-thinking
    REASONING = "reasoning"      # o1, o3, Claude Opus thinking
    VISION = "vision"            # Models with image support

def get_model_family(model_id: str) -> ModelFamily:
    """Determine model family from ID. Used for parameter routing."""
    ...
```

**2. Streaming tool call concatenation**

OpenAI's streaming yields incremental tool call argument chunks that must be concatenated before JSON parsing. The Copilot provider faces a similar but different challenge — it captures complete tool calls from events but must handle the SDK's retry behavior. The principle of "accumulate before parsing" is the same.

**3. Finish reason normalization**

OpenAI normalizes diverse finish reasons (`stop`, `tool_calls`, `length`, `content_filter`) into a standard enum. The Copilot provider should adopt the same normalized set rather than inventing provider-specific finish reasons:

```python
class FinishReason(Enum):
    STOP = "stop"                # Natural completion
    TOOL_USE = "tool_use"        # Tool calls requested
    LENGTH = "length"            # Token limit reached
    CONTENT_FILTER = "filter"    # Content policy triggered
    ERROR = "error"              # Provider error
```

### 3.3 Common Patterns to Adopt

**1. Unified configuration validation**

All providers should validate configuration at initialization time, not at first `complete()` call. Both Anthropic and OpenAI providers validate API keys and model availability eagerly. The Copilot provider currently validates lazily (first health check). Recommendation: validate CLI binary existence, auth status, and model availability during `mount()`.

**2. Structured logging with redaction**

All providers should use `amplifier_core.utils.redact_secrets()` for logging. The Copilot provider already does this, which is correct. This should be a shared utility, not reimplemented per provider.

**3. Provider info reporting**

All providers return `ProviderInfo` with `context_window`, `max_output_tokens`, and capabilities. The structure should be identical across providers so the orchestrator can make uniform decisions.

---

## 4. Anti-Patterns to Avoid

### 4.1 Mistakes from Other Providers (and Their Own History)

**Anti-Pattern 1: Leaking SDK types across the provider boundary**

Early versions of providers allowed SDK-specific types (`anthropic.Message`, `openai.ChatCompletion`) to leak into the `ChatResponse`. This made the orchestrator SDK-dependent. The Copilot provider must NEVER return `copilot.types.*` objects to the orchestrator — everything must be converted to Amplifier-native types.

**Status**: The current Copilot provider correctly converts all SDK types. Maintain this discipline.

**Anti-Pattern 2: Retrying inside the provider when the kernel should retry**

Some providers implemented internal retry loops for transient errors, duplicating the kernel's `retry_with_backoff()` logic. This creates confusion about which layer owns retry policy and can cause retry amplification (provider retries × kernel retries).

**Recommendation**: The Copilot provider should NOT retry SDK calls internally. Instead, it should raise retryable exceptions (`retryable=True`) and let the kernel's retry mechanism handle backoff. The only exception: the SDK driver's tool capture retry (re-sending after fake tool call detection) is provider-internal logic that the kernel cannot replicate.

**Anti-Pattern 3: Over-abstracting the provider interface**

Attempts to create a "universal provider interface" that captures every possible LLM capability (streaming, batching, fine-tuning, embeddings, image generation, speech) result in bloated interfaces that no single provider fully implements. Amplifier's 5-method contract is correct in its minimalism.

**Recommendation**: Resist the urge to add methods like `batch_complete()`, `create_embedding()`, or `generate_image()` to the provider protocol. These should be separate module protocols if needed.

**Anti-Pattern 4: Caching model responses at the provider level**

Some providers cached LLM responses to avoid redundant calls. This is WRONG at the provider layer because the kernel/orchestrator manages caching policy. Provider-level caching can serve stale results, bypass context compaction, and violate the stateless provider contract.

**Recommendation**: The Copilot provider's model METADATA cache (`model_cache.py`) is appropriate — it caches model capabilities, not LLM responses. This distinction must be maintained.

**Anti-Pattern 5: Blocking the event loop during initialization**

Providers that perform synchronous operations (file I/O, network calls) during `__init__` block the event loop. The Copilot provider's CLI binary discovery (`_platform.py`) is currently synchronous.

**Recommendation**: Move all blocking operations (binary discovery, CLI startup, health check) to `async` initialization. The `mount()` function should handle async setup.

**Anti-Pattern 6: Swallowing errors silently**

The worst anti-pattern: catching exceptions and returning empty/default responses instead of propagating errors. This makes debugging impossible. Every exception should either be translated to a domain-specific error or re-raised.

**Status**: The Copilot provider's error translation layer (`provider.py:976-1049`) is comprehensive. However, the unused `CopilotContentFilterError` (defined but never raised) suggests a gap. Wire it up or remove it.

### 4.2 What We Should NOT Do

1. **Do NOT try to make Copilot "look like" Anthropic/OpenAI** by hiding the subprocess architecture behind an HTTP-like abstraction. The subprocess is fundamental — pretending it's not there creates leaky abstractions.

2. **Do NOT disable the Deny+Destroy pattern** in favor of letting the SDK execute tools. This would surrender Amplifier's tool execution sovereignty.

3. **Do NOT attempt to use the SDK's MCP integration** as a shortcut for Amplifier's tool system. MCP tools should be registered as Amplifier tool modules.

4. **Do NOT duplicate the kernel's retry logic** inside the provider. Raise retryable exceptions and let the kernel handle it.

5. **Do NOT cache `complete()` responses** at the provider level. Model metadata caching is fine; response caching is not.

---

## 5. Provider Contract Evolution

### 5.1 How Anthropic Provider Has Evolved

**Phase 1: Basic completion** (v0.x)
- Simple `messages.create()` call
- Text-only responses
- No streaming

**Phase 2: Tool use** (v1.x)
- Added tool definitions and `tool_use` content blocks
- `parse_tool_calls()` method added to provider protocol
- Required `tool_result` messages in conversation history

**Phase 3: Extended thinking** (v2.x)
- Added `thinking` parameter and `ThinkingBlock` content type
- Required `thinking.signature` preservation across turns
- Added `thinking_budget_tokens` parameter
- Changed token counting (thinking tokens separate from output)

**Phase 4: Streaming formalization** (v2.x)
- Streaming events formalized with typed deltas
- `content_block_start`, `content_block_delta`, `content_block_stop` event model
- Server-sent events with structured JSON payloads

**Contract changes needed at each phase:**
- Phase 1→2: `parse_tool_calls()` added to protocol (breaking)
- Phase 2→3: `ThinkingBlock` added to content block types (additive)
- Phase 3→4: Streaming callback pattern added (optional, additive)

### 5.2 How OpenAI Provider Has Evolved

**Phase 1: Chat Completions** (v0.x)
- `chat.completions.create()` with message array
- `function_call` parameter (deprecated)

**Phase 2: Tool calls** (v1.x)
- Migrated from `function_call` to `tools` parameter
- `tool_calls` array in response (structured)
- `tool` role for tool results

**Phase 3: o-series models** (v2.x)
- Added `reasoning_effort` parameter
- Removed `temperature` support for o-series
- Model-family-dependent parameter routing

**Phase 4: Responses API** (v3.x)
- New API surface (`responses.create()`) alongside Chat Completions
- Different response structure
- Provider must support both APIs

**Contract changes needed at each phase:**
- Phase 1→2: Tool call format changed (migration, not additive)
- Phase 2→3: Model capability detection needed (additive)
- Phase 3→4: Dual API support (internal complexity, no contract change)

### 5.3 Migration Lessons

**Lesson 1: Additive changes are cheap; breaking changes are expensive.**

Both Anthropic and OpenAI evolved through additive changes (new content block types, new parameters) far more often than breaking changes. The Copilot provider should follow this pattern — when the SDK adds new capabilities, expose them as new optional features, not as changes to existing behavior.

**Lesson 2: Model capability detection always starts as heuristics, then becomes API-driven.**

Both providers initially detected model capabilities via name patterns (`if "gpt-4" in model_id`). Over time, the APIs added capability metadata. The Copilot provider's `model_naming.py` heuristics are the Phase 1 version of this. Plan for the SDK to eventually provide capability metadata directly.

**Lesson 3: SDK version pinning prevents surprises.**

The Copilot provider correctly pins `github-copilot-sdk>=0.1.32,<0.2.0`. Both Anthropic and OpenAI providers learned (the hard way) that unpinned SDK dependencies cause production breakage when minor versions change behavior. The SDK assumption tests (`tests/sdk_assumptions/`) are the safety net — run them before any SDK upgrade.

**Lesson 4: Error translation is never "done."**

Every SDK version adds new error conditions. The error translation layer must be reviewed with every SDK upgrade. The current gap (unused `CopilotContentFilterError`) suggests the translation layer needs a review pass.

**Lesson 5: Streaming implementations are 3-5x more complex than non-streaming.**

Both Anthropic and OpenAI providers saw their streaming code grow to 3-5x the size of their non-streaming code. The Copilot provider's streaming path (`_complete_streaming()` + `SdkEventHandler` + `StreamAccumulator`) is already the most complex part of the provider. Budget accordingly.

---

## 6. Unified Provider Patterns

### 6.1 Patterns ALL Providers Should Follow

**Pattern 1: The Provider Protocol (non-negotiable)**

```python
class Provider(Protocol):
    @property
    def name(self) -> str: ...
    def get_info(self) -> ProviderInfo: ...
    async def list_models(self) -> list[ModelInfo]: ...
    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...
```

This is the immutable core. All three providers implement it. It should not change.

**Pattern 2: Error Translation Layer**

Every provider must translate SDK exceptions to the kernel's error hierarchy:

```
Provider SDK Exception → Domain Exception → Kernel Exception
  anthropic.RateLimitError → AnthropicRateLimitError → KernelRateLimitError
  openai.RateLimitError   → OpenAIRateLimitError    → KernelRateLimitError
  CopilotRateLimitError   → CopilotRateLimitError   → KernelRateLimitError
```

The domain exception layer is optional but useful for provider-specific error metadata (e.g., `retry_after` from rate limit headers). The kernel exception layer is mandatory — it's what the orchestrator sees.

**Pattern 3: ProviderInfo with Model Capabilities**

All providers should report per-model capabilities in a standardized format:

```python
@dataclass
class ModelCapabilities:
    supports_tools: bool
    supports_vision: bool
    supports_streaming: bool
    supports_extended_thinking: bool
    context_window: int
    max_output_tokens: int
    reasoning_efforts: list[str] | None  # ["low", "medium", "high"] or None
```

This is already needed by at least two providers (Anthropic and Copilot), meeting Amplifier's "two-implementation rule" for kernel additions.

**Pattern 4: Streaming Content Callback**

All providers that support streaming should use the same callback pattern:

```python
async def complete(
    self, 
    request: ChatRequest, 
    *, 
    on_content: Callable[[ContentDelta], None] | None = None,
    **kwargs,
) -> ChatResponse:
```

This is a non-breaking additive change to the protocol (optional keyword argument).

**Pattern 5: Configuration Validation at Mount Time**

All providers should validate their configuration (API keys, model availability, connectivity) during `mount()`, not during the first `complete()` call. Fail fast with clear error messages.

**Pattern 6: Usage Metadata Reporting**

All providers should return usage metadata in a consistent format:

```python
@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    thinking_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
```

Fields that the SDK doesn't provide should be `None`, not fabricated.

### 6.2 Provider Abstraction Opportunities

**Opportunity 1: Shared base utilities module**

Create `amplifier_core.providers.utils` with:
- `redact_for_logging(data: dict) -> dict` — redact API keys, tokens
- `normalize_finish_reason(reason: str) -> FinishReason` — standardize finish reasons
- `build_usage(input: int, output: int, **kwargs) -> Usage` — consistent usage construction
- `validate_model_id(model_id: str, supported: list[str]) -> str` — model validation

**Opportunity 2: Shared error mapping infrastructure**

Create `amplifier_core.providers.errors` with:
- `ErrorMapper` class that translates SDK exceptions to kernel exceptions
- Configurable mapping table (SDK exception type → kernel exception type)
- Built-in rate limit retry-after extraction
- Content filter detection patterns

**Opportunity 3: Shared streaming event protocol**

Create `amplifier_core.providers.streaming` with:
- `ContentDelta` dataclass (block_type, content, block_index)
- `StreamMetrics` dataclass (ttft, total_time, token_count)
- `StreamCallback` protocol for typed streaming callbacks

**What should NOT be abstracted:**

- **SDK-specific client management** — Each SDK has fundamentally different lifecycle needs (HTTP client vs. subprocess). Abstracting this would be a leaky abstraction.
- **Message format conversion** — Each API has different message formats. A "universal converter" would be a maintenance nightmare.
- **Provider-specific workarounds** — The Copilot fake tool call detection, missing tool result repair, and SDK driver are Copilot-specific. Don't generalize them.

### 6.3 The Abstraction Spectrum

```
DO ABSTRACT (shared across all providers):
├── Error translation pattern (ErrorMapper)
├── Usage metadata structure (Usage)
├── Model capabilities reporting (ModelCapabilities)
├── Streaming event types (ContentDelta)
├── Finish reason normalization (FinishReason)
├── Configuration validation pattern
└── Logging/redaction utilities

DO NOT ABSTRACT (provider-specific):
├── SDK client lifecycle (HTTP vs. subprocess)
├── Message format conversion
├── Authentication mechanism
├── Session management (Copilot-only)
├── Agent loop suppression (Copilot-only)
├── Tool capture strategy (Copilot-only)
├── Built-in tool exclusion (Copilot-only)
└── Prompt serialization format
```

---

## 7. Comparative Architecture Summary

### Provider Complexity Spectrum

```
SIMPLICITY ◄─────────────────────────────────────────────► COMPLEXITY

Anthropic         OpenAI              Copilot
  │                 │                    │
  │ ~1000 lines     │ ~1300 lines        │ ~5300 lines
  │ HTTP only       │ HTTP only          │ Subprocess + JSON-RPC
  │ No sessions     │ No sessions        │ Ephemeral sessions
  │ No agent loop   │ No agent loop      │ Agent loop suppression
  │ Native tools    │ Native tools       │ Deny + Destroy
  │ Native thinking │ Reasoning effort   │ SDK driver pattern
  │ Simple errors   │ Simple errors      │ Heuristic error detection
  │                 │                    │
  │ "Thin pipe"     │ "Thin pipe +       │ "Intelligent membrane"
  │                 │  model routing"    │
```

### Key Takeaway

The Copilot provider is fundamentally different from Anthropic/OpenAI providers. It is **5x more complex** because it must tame an agentic SDK that wants to orchestrate, while Amplifier must remain the orchestrator. The patterns that make Anthropic/OpenAI providers simple (stateless HTTP, native tool support, direct streaming) are exactly the patterns that are ABSENT in the Copilot SDK.

The next-generation Copilot provider should:
1. **Adopt unified patterns** where they apply (error translation, usage reporting, content blocks, finish reasons)
2. **Reject false unification** where the architectures diverge (client lifecycle, session management, agent loop suppression)
3. **Aspire to the simplicity** of Anthropic/OpenAI patterns in the areas it can control (clean content block construction, typed events, validated configuration)
4. **Accept the complexity** of Deny+Destroy as the necessary cost of maintaining Amplifier's orchestration sovereignty

The Copilot provider is not a thin pipe — it is a membrane. Design it as one.

---

*End of Provider Comparison Analysis*
