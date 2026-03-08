# Deep Analysis: Amplifier Ecosystem Perspective on Next-Generation GitHub Copilot Provider

**Author**: Amplifier Ecosystem Expert (Agent 2, Wave 1)  
**Date**: 2026-03-08  
**Scope**: Kernel contracts, module protocols, hook system, orchestration boundaries, and future-proofing

---

## Executive Summary

The GitHub Copilot Provider sits at the most architecturally sensitive junction in Amplifier: the boundary between Amplifier's "mechanism, not policy" kernel and an external SDK that embodies its own set of policies. The current Pattern A (Stateless Provider / Deny + Destroy) is a correct first-generation design that successfully preserves Amplifier's non-negotiables. However, as the Copilot SDK evolves with 58+ event types, BYOK support, MCP integration, and agentic capabilities, the provider must evolve from a "dumb pipe" into an "intelligent membrane" — one that selectively bridges two orchestration worlds without surrendering Amplifier's sovereignty.

This analysis establishes the authoritative Amplifier ecosystem perspective on what MUST be preserved, what CAN evolve, and where the precise boundaries lie.

---

## 1. Amplifier's Non-Negotiables

These are the features that define Amplifier's value proposition. Losing ANY of them reduces Amplifier to a thin wrapper with no justification for existence.

### 1.1 FIC Context Compaction

**What it is**: Amplifier's Context Manager applies Focused In-Context (FIC) compaction BEFORE the provider ever sees messages. This is the mechanism that keeps conversations productive over hundreds of turns.

**Why it's essential**: The Context Manager reads `context_window` and `max_output_tokens` from `provider.get_info()` to calculate the token budget. It then compacts the conversation history — summarizing old messages, pruning irrelevant context, maintaining critical tool results — so the LLM always gets the most relevant context within its window.

```
┌──────────────────────────────────────────────────────────────┐
│  AMPLIFIER ORCHESTRATOR LOOP                                  │
│                                                                │
│  1. User message arrives                                       │
│  2. Context Manager: Calculate budget from provider.get_info() │
│  3. Context Manager: Apply FIC compaction if over budget       │
│  4. Orchestrator: Inject tool definitions                      │
│  5. Orchestrator: Build ChatRequest with FULL context          │
│  6. ──► Provider.complete(request) ──►                        │
│  7. Provider returns ChatResponse                              │
│  8. Orchestrator: Parse tool calls                             │
│  9. Orchestrator: Execute tools                                │
│  10. Context Manager: Store response                           │
│  11. Loop if tools were called                                 │
└──────────────────────────────────────────────────────────────┘
```

**Non-negotiable because**: If the SDK manages its own context (as it does in normal operation), Amplifier's compaction is bypassed. The SDK has NO awareness of Amplifier's compaction strategy, tool result importance, or agent delegation history. Two systems cannot independently compact the same conversation without catastrophic context loss.

**Current provider correctly preserves this**: Each `complete()` call receives the FULL compacted context from Amplifier and creates an ephemeral SDK session. The SDK never accumulates history because sessions are destroyed after each call.

### 1.2 Session Persistence

**What it is**: Amplifier's hook system manages session persistence — saving and restoring conversation state across process restarts. This is handled by hooks like `context-persistent` that serialize the full conversation to disk.

**Why it's essential**: Session persistence is a MODULE concern in Amplifier (not kernel), allowing different persistence strategies:
- Simple in-memory (default)
- File-based persistence (context-persistent)
- Database-backed (enterprise scenarios)
- Custom persistence (user-defined hooks)

The SDK also has session persistence (`session-persistence.md` in SDK docs shows `source: "startup" | "resume" | "new"`), but it's internal to the SDK process. If Amplifier delegates persistence to the SDK, it loses the ability to:
- Persist across different LLM providers (switch from Copilot to Anthropic mid-session)
- Apply custom serialization (redaction, compression)
- Integrate with external storage systems

**Non-negotiable because**: Session persistence is a POLICY decision. Per Amplifier's design philosophy: "Could two teams want different behavior? → Module, not kernel." Different deployments absolutely want different persistence — this MUST remain in Amplifier's module layer.

### 1.3 Agent Delegation

**What it is**: Amplifier's orchestrator supports multi-agent patterns where a primary agent can delegate to specialized sub-agents. Each agent has its own system prompt, tool set, and context. The orchestrator manages agent switching, context transfer, and result propagation.

**Why it's essential**: The SDK has `customAgents` (seen in `getting-started.md`), but these are SDK-internal agents that the SDK orchestrates. Amplifier's agent delegation is fundamentally different:
- Agents are defined as mount plan overlays (partial configurations)
- Agent switching is controlled by the orchestrator module
- Each agent can have different providers, tools, and hooks
- The `task` tool enables recursive agent delegation

If the SDK's internal agent loop is allowed to run, it will conflict with Amplifier's agent delegation:

```
CONFLICT SCENARIO:
  Amplifier Orchestrator wants to delegate to "code-review" agent
  SDK's internal loop is running its own agent loop
  WHO decides the delegation? WHO manages context transfer?
  Answer: Amplifier MUST decide. SDK must be a passive executor.
```

**Non-negotiable because**: Agent delegation is the foundation of Amplifier's extensibility. It's what allows bundles to define specialized agents, skills, and workflows. The SDK cannot replicate this because it has no concept of mount plans, module protocols, or bundle composition.

### 1.4 Hook System (Observability and Control)

**What it is**: Amplifier's hook system provides 5 capabilities through `HookResult`:
1. **Observe** — logging, metrics, audit trails
2. **Block** — security gates, validation (`action: "deny"`)
3. **Modify** — data transformation (`action: "modify"`)
4. **Inject Context** — automated feedback loops (`action: "inject_context"`)
5. **Request Approval** — user permission gates (`action: "ask_user"`)

**Why it's essential**: The hook system is Amplifier's "signals/netlink" equivalent. It's how the kernel provides MECHANISM for policies to be enforced. Every observable action emits a canonical event. Hooks can:

- Block tool execution (`tool:pre` → `deny`)
- Inject linter feedback after file writes (`tool:post` → `inject_context`)
- Require user approval for dangerous operations (`tool:pre` → `ask_user`)
- Suppress verbose output (`suppress_output: true`)
- Control context injection with ephemeral messages

**Non-negotiable because**: Without hooks, Amplifier becomes unobservable and uncontrollable. The SDK has its own hooks (`onPreToolUse`, `onPostToolUse`, `onSessionStart`, etc.), but they serve the SDK's internal policies. Amplifier's hooks serve Amplifier's users and their custom policies.

**The current provider correctly preserves this**: The provider emits events through `self._emit_event()` which flows through `self._coordinator.hooks.emit()`. Events like `llm:request`, `llm:response`, `provider:retry`, `provider:fake_tool_retry`, `sdk_driver:*` are all visible to Amplifier hooks.

### 1.5 Tool Execution Sovereignty

**What it is**: Amplifier's orchestrator executes tools, not the provider. The provider only PARSES tool call requests from the LLM response. The orchestrator then:
1. Calls `parse_tool_calls()` to extract tool calls
2. Executes each tool through the tool module protocol
3. Emits `tool:pre` and `tool:post` hook events
4. Adds tool results to conversation context
5. Calls `complete()` again with the updated context

**Why it's essential**: Tool execution is where ALL of Amplifier's safety guarantees are enforced:
- `tool:pre` hooks can deny dangerous operations
- `tool:post` hooks can inject corrective feedback
- Approval gates can require user permission
- Tool results are stored in Amplifier's context (not the SDK's)
- Custom tool modules can override behavior

The SDK's `preToolUse` hook with `deny` is the mechanism that PREVENTS the SDK from executing tools internally. This is the "Deny + Destroy" pattern — deny all tool execution in the SDK, capture the tool call requests, and let Amplifier's orchestrator handle them.

```
DENY + DESTROY PATTERN:
  ┌─────────────────────────────────────────────────────┐
  │  SDK SESSION (ephemeral)                             │
  │                                                       │
  │  1. LLM returns tool_request for "read_file"         │
  │  2. SDK's preToolUse hook → DENY (our deny hook)     │
  │  3. Tool request captured from ASSISTANT_MESSAGE event│
  │  4. Session DESTROYED (context manager exit)          │
  │                                                       │
  │  SDK never executes the tool.                        │
  │  SDK never retries after denial.                     │
  │  SDK session state is discarded.                     │
  └─────────────────────────────────────────────────────┘
        │
        ▼
  ┌─────────────────────────────────────────────────────┐
  │  AMPLIFIER ORCHESTRATOR                              │
  │                                                       │
  │  5. parse_tool_calls() extracts ToolCall objects     │
  │  6. Emit tool:pre hook event                         │
  │  7. Hook returns allow/deny/ask_user                 │
  │  8. If allowed: Execute tool via tool module          │
  │  9. Emit tool:post hook event                        │
  │  10. Store result in context                         │
  │  11. Call complete() again with tool results          │
  └─────────────────────────────────────────────────────┘
```

**Non-negotiable because**: Surrendering tool execution to the SDK means surrendering Amplifier's entire safety and extensibility model. No hooks, no approval gates, no custom tool modules, no context injection.

---

## 2. Provider Contract Evolution

### 2.1 The Current 5-Method Contract

The current provider protocol is:

```python
class Provider(Protocol):
    @property
    def name(self) -> str: ...           # 1. Provider identifier
    def get_info(self) -> ProviderInfo: ...  # 2. Metadata + capabilities
    async def list_models(self) -> list: ... # 3. Available models
    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...  # 4. Core LLM call
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...  # 5. Extract tool calls
```

**Assessment**: This contract is SUFFICIENT for the current design but has gaps for the next generation.

### 2.2 What's Missing

**Capability Negotiation**: The current contract reports capabilities statically via `get_info()`. But the Copilot SDK's capabilities are model-dependent and can change at runtime:
- `reasoning_effort` is only available on some models
- `vision` support varies by model
- `streaming` behavior differs across models
- MCP server availability is session-dependent

**Proposal**: Add an optional `get_model_capabilities(model_id: str) -> ModelCapabilities` method:

```python
class ModelCapabilities:
    supports_tools: bool
    supports_vision: bool
    supports_streaming: bool
    supports_extended_thinking: bool
    supports_mcp: bool
    context_window: int
    max_output_tokens: int
    reasoning_efforts: list[str] | None  # ["low", "medium", "high"]
```

The current provider already has `_model_supports_reasoning()` and `get_model_info()` — these are proto-capabilities that should be formalized.

**Streaming Content Protocol**: The current contract returns a complete `ChatResponse`. But the provider already emits streaming content via `_emit_streaming_content()` and `llm:content_block` events. This should be formalized:

```python
# Option A: Streaming as separate method
async def stream_complete(self, request: ChatRequest, **kwargs) -> AsyncIterator[ContentDelta]: ...

# Option B: Streaming via callback (current pattern, formalized)
async def complete(self, request: ChatRequest, *, on_content: ContentCallback | None = None, **kwargs) -> ChatResponse: ...
```

**Provider Lifecycle**: The current contract has `close()` but no formal lifecycle protocol. For providers that manage subprocesses (like the Copilot SDK), lifecycle matters:

```python
async def initialize(self) -> None: ...  # Optional: Warm up resources
async def health_check(self) -> HealthStatus: ...  # Optional: Is the provider healthy?
async def close(self) -> None: ...  # Cleanup
```

### 2.3 What Should NOT Change

The 5-method contract should NOT be expanded aggressively. Per Amplifier's design philosophy:

> "Start minimal, grow as needed (avoid future-proofing)"
> "Need from ≥2 independent modules before adding to kernel"

The `get_model_capabilities` addition is justified because BOTH the Copilot provider and the Anthropic provider need per-model capability reporting. The streaming protocol is justified because BOTH providers implement streaming differently.

But adding methods like `create_session()`, `manage_context()`, or `delegate_agent()` would be anti-patterns — those are orchestrator concerns, not provider concerns.

---

## 3. Event Bridge Architecture

### 3.1 The SDK's Event System

The Copilot SDK emits events through `session.on(handler)`. From the docs and source code, the event types include:

**Session lifecycle**: `session.idle`, `session.start`, `session.end`  
**Message events**: `assistant.message`, `assistant.message_delta`, `assistant.reasoning_delta`  
**Tool events**: `tool.call`, `tool.result`, `tool.error`  
**Error events**: Various error types  
**MCP events**: MCP server connection, tool discovery  
**Permission events**: Permission requests and responses

### 3.2 How Events Should Map to Amplifier Hooks

The ideal architecture is a **selective event bridge** — NOT a blind passthrough:

```
┌───────────────────────────────────────────────────────────────┐
│  SDK EVENT STREAM                                              │
│                                                                 │
│  session.idle ──────────► [CONSUMED] Control flow signal       │
│  assistant.message_delta ► [BRIDGED] llm:content_block         │
│  assistant.reasoning_delta► [BRIDGED] llm:thinking_block       │
│  assistant.message ──────► [BRIDGED] llm:response              │
│  tool.call ──────────────► [CONSUMED] Captured by SdkDriver   │
│  tool.result ────────────► [DROPPED] SDK tools are denied      │
│  session.start ──────────► [BRIDGED] sdk:session_created       │
│  session.end ────────────► [BRIDGED] sdk:session_destroyed     │
│  error.* ────────────────► [BRIDGED] sdk:error                 │
│  usage.* ────────────────► [BRIDGED] llm:usage                 │
│                                                                 │
│  Legend:                                                        │
│  [CONSUMED] = Used internally by provider, not forwarded       │
│  [BRIDGED]  = Translated to Amplifier event and emitted        │
│  [DROPPED]  = Not applicable in Deny+Destroy pattern           │
└───────────────────────────────────────────────────────────────┘
```

### 3.3 Event Translation Layer

The key insight is that SDK events and Amplifier events serve DIFFERENT purposes:

| SDK Event | Purpose in SDK | Amplifier Translation | Purpose in Amplifier |
|-----------|---------------|----------------------|---------------------|
| `assistant.message_delta` | UI streaming | `llm:content_block` | Hook-driven streaming UI |
| `assistant.message` | Complete response | Part of `llm:response` | Response observability |
| `tool.call` | Internal tool dispatch | Captured by SdkDriver | Tool call extraction |
| `session.idle` | Session ready signal | Internal control flow | Wait loop termination |
| Error events | SDK error handling | `provider:error` | Error observability |

**Architecture principle**: The event bridge should be implemented in the `SdkEventHandler` (already exists as `sdk_driver.py`), NOT in the provider's `complete()` method. The handler already has the `emit_event` callback pattern:

```python
handler = SdkEventHandler(
    max_turns=max_turns,
    first_turn_only=True,
    deduplicate=True,
    emit_event=self._make_emit_callback(),  # ← This is the bridge
)
```

### 3.4 What Amplifier Hooks Should NOT Do

Amplifier hooks should NOT try to:
1. **Control SDK-internal behavior** — The SDK's hooks (`onPreToolUse`, etc.) are set by the provider. Amplifier hooks should not try to influence SDK hooks directly.
2. **Duplicate SDK events** — Don't create 1:1 mappings for all 58 event types. Only bridge events that have meaningful Amplifier equivalents.
3. **Break the abstraction** — Hooks should receive Amplifier-native event data, not raw SDK event objects. The translation layer should convert SDK events to Amplifier's canonical event taxonomy.

---

## 4. The Orchestration Boundary

### 4.1 The Core Tension

Both Amplifier and the Copilot SDK want to be the orchestrator:

```
AMPLIFIER'S VIEW:                    SDK'S VIEW:
┌─────────────────┐                 ┌─────────────────┐
│  Orchestrator    │                 │  Session         │
│  (loop-basic/   │                 │  (internal agent │
│   loop-streaming)│                 │   loop)          │
│                  │                 │                  │
│  Controls:       │                 │  Controls:       │
│  - Tool execution│                 │  - Tool execution│
│  - Agent switch  │                 │  - Multi-turn    │
│  - Context mgmt  │                 │  - Context mgmt  │
│  - Compaction    │                 │  - Conversation  │
│  - Hook dispatch │                 │  - Built-in tools│
└─────────────────┘                 └─────────────────┘
```

### 4.2 The Precise Boundary

**Amplifier owns**: Everything above the LLM call
**SDK provides**: The LLM call itself (authentication, model routing, API access)

```
═══════════════════════════════════════════════════════════════
 AMPLIFIER'S DOMAIN (above the line)
═══════════════════════════════════════════════════════════════

 User Input
    │
    ▼
 Orchestrator Module
    ├── Agent selection (which agent handles this?)
    ├── Context assembly (system prompt + history + tools)
    ├── FIC compaction (is context too large?)
    ├── Hook dispatch (tool:pre, tool:post, etc.)
    └── Tool execution (via tool modules)
    │
    ▼
 ChatRequest (messages[], tools[], config{})
    │
════╪═══════════════════════════════════════════════════════════
    │  THE BOUNDARY: Provider.complete(request) → ChatResponse
════╪═══════════════════════════════════════════════════════════
    │
    ▼
═══════════════════════════════════════════════════════════════
 PROVIDER'S DOMAIN (at the line)
═══════════════════════════════════════════════════════════════

 CopilotSdkProvider.complete()
    ├── Message format conversion (Amplifier → SDK prompt)
    ├── System message extraction
    ├── Tool registration with SDK (for LLM visibility)
    ├── Deny hook installation (prevent SDK tool execution)
    ├── Ephemeral session creation
    ├── Prompt sending + response collection
    ├── Event bridging (SDK events → Amplifier events)
    ├── Response conversion (SDK → ChatResponse)
    └── Session destruction
    │
    ▼
═══════════════════════════════════════════════════════════════
 SDK'S DOMAIN (below the line)
═══════════════════════════════════════════════════════════════

 CopilotClient + CopilotSession
    ├── GitHub authentication (OAuth, token management)
    ├── Model routing (which backend serves this model?)
    ├── API communication (HTTP/gRPC to GitHub's infrastructure)
    ├── Rate limiting (token bucket, retry headers)
    ├── Streaming transport (SSE/WebSocket)
    └── Response parsing (raw API → structured events)
```

### 4.3 Why This Boundary Is Correct

**The SDK should NOT orchestrate** because:
1. It has no concept of Amplifier's module system
2. It cannot emit events through Amplifier's hook registry
3. It cannot consult Amplifier's approval gates
4. It cannot delegate to Amplifier's agent system
5. It cannot apply Amplifier's compaction strategy

**Amplifier should NOT handle authentication** because:
1. GitHub OAuth is Copilot-specific (not a general mechanism)
2. Token management requires GitHub's infrastructure
3. Model routing is GitHub's business logic
4. Rate limiting signals come from GitHub's API

**The provider is the membrane** — it translates between two worlds without allowing either to leak into the other.

### 4.4 The SDK's Internal Loop Must Be Suppressed

The SDK's `sendAndWait()` method runs an internal agent loop:
1. Send prompt
2. Receive response
3. If tool calls: execute tools → send results → goto 2
4. If no tool calls: return response

The current provider suppresses this via:
- **Deny hooks**: Prevent SDK tool execution
- **First-turn capture**: SdkEventHandler captures tools from first turn only
- **Session abort**: After capturing tools, abort the session
- **Session destroy**: Context manager destroys the session on exit
- **Max turns**: Circuit breaker prevents runaway loops

This is the correct architecture. The SDK's loop MUST be suppressed because it conflicts with Amplifier's orchestrator loop. Allowing both to run would result in:
- Double tool execution
- Conflicting context management
- Uncontrolled event emission
- Bypassed safety hooks

---

## 5. Future-Proofing

### 5.1 The Agentic Provider Problem

LLM providers are adding increasingly agentic capabilities:
- **Tool use**: Already handled (Deny + Destroy)
- **Planning**: Models that break tasks into steps internally
- **Sub-agents**: Models that spawn sub-tasks
- **Computer use**: Models that interact with UIs directly
- **MCP integration**: Models that connect to external tool servers

### 5.2 How Amplifier's Provider Contract Should Evolve

**Principle**: The provider contract should evolve ADDITIVELY using optional capabilities, never by restructuring the core contract.

```python
# Current contract (preserved)
class Provider(Protocol):
    name: str
    def get_info(self) -> ProviderInfo: ...
    async def list_models(self) -> list: ...
    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...

# Future additions (optional, capability-negotiated)
class StreamingProvider(Provider, Protocol):
    async def stream_complete(self, request: ChatRequest, **kwargs) -> AsyncIterator[ContentDelta]: ...

class CapabilityAwareProvider(Provider, Protocol):
    def get_model_capabilities(self, model_id: str) -> ModelCapabilities: ...

class LifecycleProvider(Provider, Protocol):
    async def initialize(self) -> None: ...
    async def health_check(self) -> HealthStatus: ...
```

**The Two-Implementation Rule**: Before adding ANY of these to the kernel protocol, they must be needed by ≥2 independent provider implementations.

### 5.3 MCP Integration Strategy

The SDK supports MCP servers natively. Amplifier should NOT delegate MCP to the SDK. Instead:

```
WRONG: Amplifier → Provider → SDK → MCP Server → SDK → Provider → Amplifier
RIGHT: Amplifier → MCP Tool Module → MCP Server → MCP Tool Module → Amplifier
```

MCP tools should be registered as Amplifier tool modules, not as SDK-internal MCP connections. This ensures:
- Amplifier hooks see all MCP tool calls
- Approval gates work for MCP tools
- Context injection works for MCP results
- MCP tools work across providers (not just Copilot)

### 5.4 Extended Thinking and Reasoning

The current provider already handles this well:
- `reasoning_effort` parameter is capability-gated
- `ThinkingBlock` content is captured and forwarded
- `assistant.reasoning_delta` events are bridged for streaming

Future evolution: As models add more thinking capabilities (chain-of-thought, scratchpad, planning), the `ChatResponse` content blocks should remain the integration point. Each new content type becomes a new block type (like `ThinkingBlock` was added). No contract change needed — just new content block types.

---

## 6. BYOK and Multi-Provider

### 6.1 BYOK (Bring Your Own Key) Impact

The Copilot SDK supports BYOK through Azure AI Foundry and other providers. This creates an interesting scenario:

```
BYOK SCENARIO:
  User has Azure OpenAI API key
  User wants to use it through Copilot's infrastructure
  SDK handles the key routing

  BUT:
  Amplifier already has an Azure OpenAI provider module
  Should the user use Amplifier's Azure provider or SDK's BYOK?
```

**Resolution**: These are DIFFERENT use cases:
- **SDK BYOK**: Uses GitHub's infrastructure with user's API key. Benefits from Copilot's model routing, token management, and rate limiting.
- **Amplifier Azure provider**: Direct connection to Azure. Benefits from Amplifier's full module ecosystem without GitHub's intermediation.

The provider design should NOT try to unify these. They are separate providers:
- `github-copilot` provider (with optional BYOK through SDK)
- `azure-openai` provider (direct connection)

### 6.2 Multi-Provider Configuration

Amplifier supports mounting multiple providers simultaneously. The provider design affects this in several ways:

**Provider Selection**: The orchestrator selects providers based on mount plan configuration. The Copilot provider's `priority` attribute (default 100) determines selection order. This is already correct.

**Provider Fallback**: If the Copilot SDK is unavailable (authentication expired, rate limited, network error), the orchestrator should fall back to other providers. The current error translation (Copilot exceptions → Kernel LLM errors) enables this:

```python
except CopilotRateLimitError as e:
    raise KernelRateLimitError(...)  # Orchestrator can fall back

except CopilotAuthenticationError as e:
    raise KernelAuthenticationError(...)  # Orchestrator can switch providers
```

**Model Routing**: Different models might be served by different providers. The Copilot provider should accurately report its available models via `list_models()` so the orchestrator can route `claude-opus-4.5` to Copilot and `gemini-2.5-pro` to Google's provider.

### 6.3 Multi-Provider Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  AMPLIFIER SESSION                                           │
│                                                               │
│  Mount Plan:                                                  │
│    providers:                                                 │
│      - github-copilot (priority: 100, models: claude-*, gpt-*)│
│      - anthropic       (priority: 200, models: claude-*)     │
│      - openai          (priority: 300, models: gpt-*, o-*)   │
│                                                               │
│  Orchestrator selects provider per-request based on:          │
│    1. Model requested                                        │
│    2. Provider priority                                      │
│    3. Provider health/availability                            │
│    4. Fallback chain on error                                │
│                                                               │
│  ALL providers share the same:                                │
│    - Context Manager (FIC compaction)                        │
│    - Hook system (observability)                             │
│    - Tool modules (execution)                                │
│    - Agent system (delegation)                               │
└─────────────────────────────────────────────────────────────┘
```

**Key insight**: The provider design MUST maintain the property that providers are INTERCHANGEABLE. A session should be able to switch from Copilot to Anthropic mid-conversation without losing context. This is only possible if:
1. Context is managed by Amplifier (not the SDK)
2. Tool execution is managed by Amplifier (not the SDK)
3. The provider only does: format conversion + LLM call + response parsing

---

## 7. Architectural Recommendations

### 7.1 Short-Term (Next Generation Provider)

1. **Keep Pattern A as the foundation** — Deny + Destroy is correct. Don't compromise it.
2. **Formalize the event bridge** — Define a clear SDK event → Amplifier event mapping in the SdkEventHandler.
3. **Add `get_model_capabilities()`** — Per-model capability reporting is needed now.
4. **Improve streaming protocol** — The `_emit_streaming_content()` pattern should be formalized.
5. **Expose session metrics** — `get_session_metrics()` is already implemented; consider making it part of the provider protocol.

### 7.2 Medium-Term (Provider Contract v2)

1. **Optional protocol extensions** — Use Python Protocol composition for optional capabilities.
2. **Content block extensibility** — New content types (planning blocks, citation blocks) should be additive.
3. **Health check protocol** — For multi-provider fallback, providers should report health status.

### 7.3 Long-Term (Agentic Future)

1. **Provider remains a pipe** — Even as LLMs become more agentic, the provider should remain a translation layer. Agentic capabilities should be exposed as CONTENT in the response, not as BEHAVIOR in the provider.
2. **MCP as Amplifier modules** — MCP tools should be first-class Amplifier tool modules, not SDK-internal connections.
3. **Sub-agent requests as tool calls** — If an LLM requests sub-agent delegation, it should come back as a special tool call that the orchestrator interprets, not as SDK-internal agent spawning.

---

## 8. Philosophy Alignment Scorecard

| Principle | Current Provider | Score |
|-----------|-----------------|-------|
| Mechanism, Not Policy | Provider is pure mechanism (translation) | ✅ 10/10 |
| Ruthless Simplicity | Pattern A is minimal and correct | ✅ 9/10 |
| Small, Stable, Boring Kernel | Provider doesn't modify kernel | ✅ 10/10 |
| Bricks & Studs | Clear interface, independently testable | ✅ 9/10 |
| Event-First Observability | Emits llm:*, provider:*, sdk_driver:* events | ✅ 8/10 |
| Text-First, Inspectable | JSONL logging, redacted secrets | ✅ 9/10 |
| Don't Break Modules | Backward compatible 5-method contract | ✅ 10/10 |

**Overall**: The current provider is well-aligned with Amplifier's philosophy. The next generation should preserve this alignment while adding capabilities ADDITIVELY.

---

## 9. Conclusion

The next-generation GitHub Copilot Provider should be an evolution, not a revolution. The foundational architecture is sound:

1. **Pattern A (Deny + Destroy) is correct** — it preserves ALL of Amplifier's non-negotiables
2. **The 5-method contract is sufficient** — extend with optional capabilities, don't restructure
3. **The event bridge should be formalized** — selective translation, not blind passthrough
4. **The orchestration boundary is clear** — Amplifier above, SDK below, provider at the membrane
5. **Multi-provider interchangeability is essential** — providers must remain stateless translation layers

**The center stays still so the edges can move fast.**

The Copilot SDK will continue evolving with new capabilities. Amplifier's provider design should accommodate this evolution through:
- Additive content block types
- Capability negotiation per model
- Event bridge extensibility
- Protocol composition for optional features

The provider is not where innovation happens — it's where STABILITY enables innovation elsewhere in the stack.
