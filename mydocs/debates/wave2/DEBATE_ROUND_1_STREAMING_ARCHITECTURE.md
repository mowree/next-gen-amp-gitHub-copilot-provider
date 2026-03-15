# WAVE 2, AGENT 19: Streaming & Real-Time Architecture

**Agent Role**: Streaming & Real-Time Expert  
**Date**: 2026-03-08  
**Subject**: Event Flow Design, Streaming Response Handling, Tool Call Streaming, Real-Time Observability, Error Recovery, and Performance Optimization for the Next-Generation GitHub Copilot Provider

---

## Executive Summary

The GitHub Copilot Provider's streaming architecture must bridge two fundamentally different event systems: the Copilot SDK's internal event stream (driven by a CLI subprocess communicating via JSON-RPC) and Amplifier's hook-based event emission system. The current implementation in `sdk_driver.py` (~620 lines) already solves the hardest problems — loop control, first-turn tool capture, and circuit breaking. This architecture document formalizes and extends that foundation, addressing event ordering guarantees, backpressure, memory efficiency, error recovery, and observability.

The core design principle: **The streaming layer is a stateful event transformer** — it receives a continuous stream of SDK events, accumulates state (tokens, content blocks, thinking blocks, tool calls), emits Amplifier-native events in real-time, and produces a final `ChatResponse` when the stream terminates. It must handle partial failures, stream interruptions, and resource cleanup without leaking state or blocking the event loop.

---

## 1. Event Flow Design

### 1.1 End-to-End Event Pipeline

The complete event flow from SDK to Amplifier hooks traverses four layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 1: SDK TRANSPORT (JSON-RPC over stdio)                       │
│                                                                     │
│  CLI Subprocess ──stdio──▶ CopilotClient ──JSON-RPC──▶ CopilotSession│
│                                                                     │
│  Events arrive as JSON-RPC notifications:                           │
│    {"jsonrpc":"2.0","method":"session/event","params":{...}}        │
│                                                                     │
│  Rate: 10-200 events/second during active generation                │
│  Ordering: FIFO within the stdio pipe (guaranteed by OS)            │
│  Backpressure: None — if consumer is slow, pipe buffer fills        │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 2: SDK EVENT DISPATCH (session.on() handler)                 │
│                                                                     │
│  CopilotSession dispatches events to registered handlers:           │
│    session.on(handler) → unsubscribe callable                       │
│                                                                     │
│  Event types (from SessionEventType enum):                          │
│    ASSISTANT_MESSAGE_DELTA  — token-by-token text content           │
│    ASSISTANT_REASONING_DELTA — token-by-token thinking content      │
│    ASSISTANT_MESSAGE        — complete message (with tool_requests) │
│    SESSION_IDLE             — SDK loop iteration complete            │
│    ERROR                    — SDK-level error                       │
│                                                                     │
│  Ordering: Events arrive in SDK's internal order                    │
│  Contract: Deltas BEFORE complete message (SDK assumption #1)       │
│  Contract: ASSISTANT_MESSAGE fires BEFORE preToolUse hook           │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 3: PROVIDER EVENT TRANSFORMER (SdkEventHandler)              │
│                                                                     │
│  This is the core of the streaming architecture.                    │
│  Responsibilities:                                                  │
│    1. Accumulate tokens into content blocks                         │
│    2. Track thinking blocks separately                              │
│    3. Capture tool calls (first-turn-only)                          │
│    4. Enforce circuit breaker (max turns, timeout)                  │
│    5. Translate SDK events → Amplifier-native events                │
│    6. Emit events via coordinator.hooks.emit()                      │
│    7. Signal stream completion via asyncio.Event                    │
│                                                                     │
│  State machine:                                                     │
│    IDLE → RECEIVING_DELTAS → BLOCK_COMPLETE → [IDLE | TOOLS_CAPTURED]│
│                                                                     │
│  Ordering guarantee: Amplifier events emitted in SDK event order    │
│  Backpressure: Fire-and-forget emission (no await on hooks)         │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LAYER 4: AMPLIFIER HOOK DISPATCH (coordinator.hooks.emit())        │
│                                                                     │
│  Events emitted:                                                    │
│    llm:content_block   — streaming text content                     │
│    llm:thinking_block  — streaming reasoning content                │
│    llm:response        — final complete response                    │
│    sdk_driver:turn     — SDK loop turn tracking                     │
│    sdk_driver:abort    — circuit breaker triggered                  │
│                                                                     │
│  Hook handlers receive events and can:                              │
│    - Observe (logging, metrics, UI streaming)                       │
│    - React (but NOT block the stream — fire-and-forget)             │
│                                                                     │
│  Critical: Streaming events are fire-and-forget.                    │
│  Hooks MUST NOT introduce backpressure on the streaming pipeline.   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Backpressure Strategy

The streaming pipeline has **no backpressure** by design. This is a deliberate architectural choice:

**Why no backpressure:**
1. The SDK's CLI subprocess writes to stdout continuously — there's no mechanism to tell the LLM to "slow down"
2. The JSON-RPC transport has no flow control beyond OS pipe buffers (typically 64KB on Linux, 4KB on macOS)
3. If the consumer (our event handler) blocks, the pipe buffer fills, the CLI process blocks on write, and we risk timeout
4. Hook handlers may be slow (e.g., writing to disk, sending to remote telemetry) — they must not stall token delivery

**The fire-and-forget pattern:**

```python
def _make_emit_callback(self) -> Callable:
    """Create a fire-and-forget event emission callback.
    
    Events are scheduled on the event loop but NOT awaited.
    If hooks are slow, events queue in the event loop — they don't
    block the SDK event handler.
    
    Trade-off: Event ordering is preserved (same event loop),
    but slow hooks may see events after the stream has completed.
    """
    hooks = self._coordinator.hooks
    
    def emit(event_name: str, data: dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(hooks.emit(event_name, data))
        except RuntimeError:
            # No running event loop — swallow silently
            # This can happen during cleanup/shutdown
            pass
    
    return emit
```

**Buffer overflow protection:**

The OS pipe buffer is the only backpressure mechanism. If it fills (extremely unlikely under normal operation — would require the event handler to block for >100ms while tokens stream at maximum rate), the CLI process blocks on stdout write. The SDK timeout then fires, and we get a timeout error. This is acceptable because:
- Normal event processing takes <1ms per event
- The pipe buffer holds ~64KB of JSON-RPC messages (~100+ events)
- The only scenario where this matters is if the Python process is completely stalled (e.g., GC pause, CPU starvation)

### 1.3 Event Ordering Guarantees

**Guaranteed orderings (enforced by SDK and transport):**

| Guarantee | Mechanism | Assumption Level |
|-----------|-----------|-----------------|
| Deltas arrive before complete message | SDK internal ordering | SDK Assumption #1 (tested) |
| `ASSISTANT_MESSAGE` before `preToolUse` | SDK internal ordering | SDK Assumption #1 (tested) |
| Events within a turn are ordered | Single-threaded SDK dispatch | Transport guarantee |
| Amplifier events emitted in SDK order | Same event loop, sequential handler | Architecture guarantee |

**NOT guaranteed (and we must handle):**

| Non-guarantee | Impact | Mitigation |
|--------------|--------|------------|
| Delta event count | May get 0 deltas for very short responses | Accumulate from complete message if no deltas received |
| Reasoning delta before text delta | Model may interleave thinking and text | Track block type transitions |
| Tool request count per message | May get 0 or N tool requests | Handle both cases |
| `SESSION_IDLE` timing after abort | May arrive late or not at all | Use timeout as secondary completion signal |

### 1.4 Event Classification Table

Every SDK event falls into exactly one category:

```
┌─────────────────────────────┬──────────┬────────────────────────────┐
│ SDK Event                   │ Category │ Amplifier Action           │
├─────────────────────────────┼──────────┼────────────────────────────┤
│ ASSISTANT_MESSAGE_DELTA     │ BRIDGE   │ Emit llm:content_block     │
│ ASSISTANT_REASONING_DELTA   │ BRIDGE   │ Emit llm:thinking_block    │
│ ASSISTANT_MESSAGE           │ CONSUME  │ Extract tools, accumulate  │
│ SESSION_IDLE                │ CONSUME  │ Signal turn/stream complete │
│ ERROR                       │ BRIDGE   │ Emit provider:error        │
│ USAGE                       │ CONSUME  │ Accumulate usage counters  │
│ preToolUse (hook)           │ CONSUME  │ Return DENY (always)       │
│ postToolUse (hook)          │ DROP     │ Never fires (tools denied) │
│ SESSION_START               │ BRIDGE   │ Emit sdk:session_start     │
│ SESSION_END                 │ CONSUME  │ Cleanup signal             │
│ All other events            │ DROP     │ Ignored (logged at debug)  │
└─────────────────────────────┴──────────┴────────────────────────────┘
```

---

## 2. Streaming Response Handling

### 2.1 Token Accumulation Architecture

The streaming handler maintains an **accumulator** — a mutable structure that builds up the final `ChatResponse` incrementally as events arrive:

```
┌──────────────────────────────────────────────────────────────────┐
│  STREAM ACCUMULATOR (per-request, lives for duration of stream)  │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ text_buffer: str     │  ← Accumulated from ASSISTANT_MESSAGE_ │
│  │                      │     DELTA events (token by token)      │
│  └─────────────────────┘                                         │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ thinking_buffer: str │  ← Accumulated from ASSISTANT_REASONING│
│  │                      │     _DELTA events                      │
│  └─────────────────────┘                                         │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ content_blocks: list │  ← Completed blocks (text, thinking,   │
│  │                      │     tool_use)                           │
│  └─────────────────────┘                                         │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ tool_requests: list  │  ← Captured from ASSISTANT_MESSAGE     │
│  │                      │     data.tool_requests (first turn)    │
│  └─────────────────────┘                                         │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ usage: Usage         │  ← input_tokens, output_tokens,        │
│  │                      │     thinking_tokens (if applicable)    │
│  └─────────────────────┘                                         │
│                                                                  │
│  ┌─────────────────────┐                                         │
│  │ turn_count: int      │  ← Circuit breaker counter             │
│  │ first_token_at: float│  ← TTFT (time to first token) metric   │
│  │ stream_start: float  │  ← Stream start timestamp              │
│  │ is_complete: Event   │  ← asyncio.Event for completion signal │
│  └─────────────────────┘                                         │
└──────────────────────────────────────────────────────────────────┘
```

**Accumulator lifecycle:**

```
CREATE (at session.send() call)
  │
  ├── DELTA events → append to text_buffer/thinking_buffer
  │     └── Emit llm:content_block / llm:thinking_block per delta
  │
  ├── ASSISTANT_MESSAGE → flush buffers, extract tool_requests, record usage
  │     └── If tool_requests: capture tools (first turn only)
  │
  ├── SESSION_IDLE → increment turn_count, check circuit breaker
  │     └── If first turn with tools: signal abort
  │     └── If max turns exceeded: trip circuit breaker
  │
  └── COMPLETE (SESSION_IDLE with no tools OR abort OR timeout OR error)
        └── Build ChatResponse from accumulated state
        └── Set is_complete event
        └── Accumulator becomes immutable (consumed)
```

### 2.2 Content Block Construction

Content blocks are constructed from the stream in a specific order. The provider must handle block type transitions correctly:

```
SDK Event Sequence              →  Content Blocks Built
─────────────────────────────     ──────────────────────
REASONING_DELTA("Let me")       →  thinking_buffer = "Let me"
REASONING_DELTA(" think...")    →  thinking_buffer = "Let me think..."
MESSAGE_DELTA("Here is")        →  [flush thinking → ThinkingBlock]
                                   text_buffer = "Here is"
MESSAGE_DELTA(" the answer")    →  text_buffer = "Here is the answer"
ASSISTANT_MESSAGE(complete)     →  [flush text → TextBlock]
                                   Final: [ThinkingBlock, TextBlock]
```

**Block flush rules:**

1. **Thinking → Text transition**: When the first `MESSAGE_DELTA` arrives after `REASONING_DELTA` events, flush the thinking buffer into a `ThinkingBlock` and start the text buffer
2. **Text → Tool transition**: When `ASSISTANT_MESSAGE` arrives with `tool_requests`, flush the text buffer into a `TextBlock` and create `ToolCallBlock` entries
3. **End of stream**: Flush any remaining buffer content into the appropriate block type
4. **Empty buffers**: Don't create blocks for empty buffers (short responses may have no deltas)

**Critical: ThinkingBlock.signature preservation**

The Amplifier kernel requires `ThinkingBlock.signature` for multi-turn conversations with extended thinking. The SDK may provide this in the `ASSISTANT_MESSAGE` complete event or as metadata on reasoning delta events. The accumulator MUST capture and preserve this field:

```python
class StreamAccumulator:
    def on_assistant_message(self, data):
        # Extract thinking signature from complete message
        if hasattr(data, 'thinking_signature'):
            self._thinking_signature = data.thinking_signature
    
    def build_thinking_block(self) -> ThinkingBlock:
        return ThinkingBlock(
            content=self._thinking_buffer,
            signature=self._thinking_signature,  # MUST preserve
        )
```

### 2.3 Thinking Block Handling

Extended thinking (reasoning) requires special streaming treatment:

**Thinking-capable models** (detected via `model_naming.py` heuristics or SDK capability check):
- `claude-opus-*`, `gpt-5*`, `o1*`, `o3*`, `o4*`, models with `-thinking` or `-reasoning` suffix

**Streaming behavior differences with thinking:**

| Aspect | Without Thinking | With Thinking |
|--------|-----------------|---------------|
| First event type | `MESSAGE_DELTA` | `REASONING_DELTA` |
| Timeout | `config.timeout` | `config.thinking_timeout` |
| Content blocks | `[TextBlock]` | `[ThinkingBlock, TextBlock]` |
| Token counting | `output_tokens` | `output_tokens + thinking_tokens` |
| Budget calculation | Standard | Extended (thinking tokens don't count against max_output) |
| Streaming emission | `llm:content_block` only | `llm:thinking_block` + `llm:content_block` |

**Thinking block streaming flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│  THINKING-ENABLED STREAM                                         │
│                                                                  │
│  Phase 1: Reasoning (may last 10-60+ seconds)                   │
│  ┌─────────────────────────────────────────────┐                │
│  │ REASONING_DELTA → emit llm:thinking_block   │                │
│  │ REASONING_DELTA → emit llm:thinking_block   │  ← Real-time  │
│  │ REASONING_DELTA → emit llm:thinking_block   │     thinking   │
│  │ ...                                          │     visible   │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  Phase 2: Response (after thinking completes)                    │
│  ┌─────────────────────────────────────────────┐                │
│  │ MESSAGE_DELTA → emit llm:content_block      │                │
│  │ MESSAGE_DELTA → emit llm:content_block      │  ← Normal     │
│  │ ...                                          │     streaming  │
│  └─────────────────────────────────────────────┘                │
│                                                                  │
│  Phase 3: Completion                                             │
│  ┌─────────────────────────────────────────────┐                │
│  │ ASSISTANT_MESSAGE → finalize all blocks      │                │
│  │ SESSION_IDLE → signal stream complete        │                │
│  └─────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

**reasoning_effort mapping:**

The provider maps Amplifier's reasoning effort to SDK session config:

```python
EFFORT_MAP = {
    "low": "low",        # Minimal thinking, fast response
    "medium": "medium",  # Balanced thinking
    "high": "high",      # Deep reasoning, slower response
}

# Applied at session creation time, NOT per-message
session_config = {
    "reasoning_effort": EFFORT_MAP.get(request.reasoning_effort, "medium"),
}
```

---

## 3. Tool Call Streaming

### 3.1 Event-Based Tool Capture

Tool calls are captured from the streaming event pipeline, NOT from the SDK's tool execution system. This is the foundation of the Deny + Destroy pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│  TOOL CAPTURE PIPELINE                                           │
│                                                                  │
│  SDK generates tool request                                      │
│      │                                                           │
│      ▼                                                           │
│  ASSISTANT_MESSAGE event fires (contains tool_requests[])        │
│      │                                                           │
│      ├──▶ SdkEventHandler captures tool_requests                │
│      │    └── ToolCaptureStrategy: first_turn_only + deduplicate │
│      │                                                           │
│      ▼                                                           │
│  preToolUse hook fires (SDK attempts to execute tool)            │
│      │                                                           │
│      └──▶ Deny hook returns DENY                                │
│           └── SDK receives denial, enters retry loop             │
│                                                                  │
│  SESSION_IDLE fires (SDK retry turn complete)                    │
│      │                                                           │
│      └──▶ LoopController: Tools captured on turn 1              │
│           └── Signal session.abort()                             │
│           └── Stream accumulator marks complete                  │
│                                                                  │
│  Result: Tools captured WITHOUT SDK executing them               │
│  Result: Session aborted to prevent 305-turn retry loop          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 First-Turn-Only Strategy

The `ToolCaptureStrategy` implements a critical invariant: **only capture tool calls from the first SDK turn**. This prevents the 305-turn, 607-tool accumulation bug:

```
Turn 1: LLM says "Call read_file('/src/main.py')"
  → CAPTURE: [{name: "read_file", args: {path: "/src/main.py"}}]
  → DENY tool execution
  → Signal abort

Turn 2+: SDK retries with "tool was denied" context
  → IGNORE all tool requests (duplicates from retry)
  → Circuit breaker monitors turn count
  → If turn > SDK_MAX_TURNS_DEFAULT (3): trip breaker
```

**Deduplication logic:**

Tool calls from retry turns may differ from the original (the LLM may reformulate after denial). The strategy captures ONLY from turn 1 and ignores everything else. This is simpler and more predictable than attempting to deduplicate across turns:

```python
class ToolCaptureStrategy:
    def __init__(self, first_turn_only: bool = True, deduplicate: bool = True):
        self._captured_turn: int | None = None
        self._captured_tools: list[ToolRequest] = []
        self._seen_ids: set[str] = set()
    
    def should_capture(self, turn: int) -> bool:
        if self._first_turn_only and self._captured_turn is not None:
            return False  # Already captured from a turn
        return True
    
    def capture(self, turn: int, tool_requests: list) -> list:
        if not self.should_capture(turn):
            return []  # Ignore subsequent turns
        
        captured = []
        for req in tool_requests:
            if self._deduplicate and req.id in self._seen_ids:
                continue
            self._seen_ids.add(req.id)
            captured.append(req)
        
        if captured:
            self._captured_turn = turn
            self._captured_tools.extend(captured)
        
        return captured
```

### 3.3 Abort Mechanisms

Three abort mechanisms protect against runaway SDK loops:

**1. Graceful abort (first-turn tools captured):**
```
Trigger: Tools captured on turn 1, SESSION_IDLE fires
Action: session.abort() — tells SDK to stop loop
Result: SDK stops, stream completes with captured tools
Latency: ~0ms (immediate after SESSION_IDLE)
```

**2. Circuit breaker abort (too many turns):**
```
Trigger: turn_count > SDK_MAX_TURNS_DEFAULT (3)
Action: session.abort() + raise CopilotSdkLoopError
Result: Stream terminates with error
Latency: Depends on how many turns elapsed (~seconds per turn)
Hard limit: SDK_MAX_TURNS_HARD_LIMIT (10) — absolute safety net
```

**3. Timeout abort (time exceeded):**
```
Trigger: asyncio.timeout(config.timeout + SDK_TIMEOUT_BUFFER_SECONDS)
Action: session.abort() via timeout handler
Result: Stream terminates with CopilotTimeoutError
Design: Provider timeout fires BEFORE SDK timeout (5s buffer)
         This ensures the provider controls the error, not the SDK
```

**Abort priority (highest to lowest):**
1. Timeout — always wins, non-negotiable safety mechanism
2. Circuit breaker — prevents infinite loops
3. Graceful abort — normal tool capture completion

```
┌─────────────────────────────────────────────────────────────────┐
│  ABORT DECISION TREE                                             │
│                                                                  │
│  On SESSION_IDLE:                                                │
│    ├── Timeout exceeded? → ABORT + TimeoutError                 │
│    ├── Turn > hard limit? → ABORT + SdkLoopError                │
│    ├── Turn > soft limit? → ABORT + SdkLoopError (with warning) │
│    ├── Tools captured on turn 1? → ABORT (graceful, with tools) │
│    └── No tools, turn 1? → CONTINUE (response-only stream)     │
│                                                                  │
│  On ASSISTANT_MESSAGE:                                           │
│    ├── Has tool_requests AND turn == 1? → CAPTURE tools         │
│    ├── Has tool_requests AND turn > 1? → IGNORE (retry noise)   │
│    └── No tool_requests? → ACCUMULATE text/thinking content     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Real-Time Observability

### 4.1 Streaming Metrics

The provider should emit structured metrics at key streaming lifecycle points:

```
┌─────────────────────────────────────────────────────────────────┐
│  STREAMING METRICS (per-request)                                 │
│                                                                  │
│  Timing Metrics:                                                 │
│  ┌──────────────────┬──────────────────────────────────────┐    │
│  │ stream_start_at  │ Timestamp when session.send() called  │    │
│  │ first_token_at   │ Timestamp of first DELTA event        │    │
│  │ first_text_at    │ Timestamp of first MESSAGE_DELTA      │    │
│  │ stream_end_at    │ Timestamp when stream completes       │    │
│  │ ttft_ms          │ first_token_at - stream_start_at      │    │
│  │ ttft_text_ms     │ first_text_at - stream_start_at       │    │
│  │ total_stream_ms  │ stream_end_at - stream_start_at       │    │
│  │ thinking_ms      │ first_text_at - first_token_at        │    │
│  └──────────────────┴──────────────────────────────────────┘    │
│                                                                  │
│  Volume Metrics:                                                 │
│  ┌──────────────────┬──────────────────────────────────────┐    │
│  │ delta_count      │ Total DELTA events received           │    │
│  │ reasoning_deltas │ Count of REASONING_DELTA events       │    │
│  │ text_deltas      │ Count of MESSAGE_DELTA events         │    │
│  │ tokens_per_sec   │ output_tokens / total_stream_seconds  │    │
│  │ event_count      │ Total SDK events received             │    │
│  │ turns_used       │ SDK turns before completion           │    │
│  └──────────────────┴──────────────────────────────────────┘    │
│                                                                  │
│  Outcome Metrics:                                                │
│  ┌──────────────────┬──────────────────────────────────────┐    │
│  │ finish_reason    │ stop | tool_use | timeout | error     │    │
│  │ tools_captured   │ Count of captured tool calls          │    │
│  │ circuit_tripped  │ Boolean — did circuit breaker fire?   │    │
│  │ aborted          │ Boolean — was session aborted?        │    │
│  └──────────────────┴──────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Event Latency Tracking

Each event can carry a latency measurement for pipeline health monitoring:

```python
class StreamMetrics:
    def __init__(self):
        self._stream_start = time.monotonic()
        self._first_token: float | None = None
        self._last_event: float = self._stream_start
        self._event_count: int = 0
        self._delta_count: int = 0
        self._max_inter_event_gap: float = 0.0
    
    def record_event(self, event_type: str) -> dict:
        now = time.monotonic()
        gap = now - self._last_event
        self._max_inter_event_gap = max(self._max_inter_event_gap, gap)
        self._last_event = now
        self._event_count += 1
        
        if event_type in ("ASSISTANT_MESSAGE_DELTA", "ASSISTANT_REASONING_DELTA"):
            self._delta_count += 1
            if self._first_token is None:
                self._first_token = now
        
        return {
            "event_type": event_type,
            "elapsed_ms": (now - self._stream_start) * 1000,
            "inter_event_gap_ms": gap * 1000,
            "event_index": self._event_count,
        }
    
    def summary(self) -> dict:
        end = time.monotonic()
        return {
            "ttft_ms": ((self._first_token - self._stream_start) * 1000) if self._first_token else None,
            "total_ms": (end - self._stream_start) * 1000,
            "event_count": self._event_count,
            "delta_count": self._delta_count,
            "max_gap_ms": self._max_inter_event_gap * 1000,
            "events_per_sec": self._event_count / max(end - self._stream_start, 0.001),
        }
```

### 4.3 Buffer Monitoring

The accumulator's buffers should be monitorable for debugging large responses:

```
Metrics emitted at stream completion:
  text_buffer_peak_bytes: Maximum size of text accumulation buffer
  thinking_buffer_peak_bytes: Maximum size of thinking buffer
  content_blocks_count: Number of finalized content blocks
  tool_requests_count: Number of captured tool requests
```

**When to alert (debug mode):**

| Metric | Warning Threshold | Error Threshold |
|--------|------------------|-----------------|
| `text_buffer_peak_bytes` | >100KB | >1MB |
| `thinking_buffer_peak_bytes` | >500KB | >5MB |
| `delta_count` with 0 content | >0 | — (should never happen) |
| `max_gap_ms` | >5000ms | >30000ms |
| `turns_used` | >1 (unexpected) | >3 (circuit breaker) |

---

## 5. Error in Streams

### 5.1 Partial Response Handling

When a stream is interrupted after some content has been received, the provider must decide what to return:

```
┌─────────────────────────────────────────────────────────────────┐
│  PARTIAL RESPONSE DECISION MATRIX                                │
│                                                                  │
│  Received    │ Error Type      │ Action                          │
│  ────────────┼─────────────────┼─────────────────────────────── │
│  No content  │ Any error       │ Raise error (no partial data)  │
│  Some text   │ Timeout         │ Return partial + finish=length │
│  Some text   │ Network error   │ Raise error (data unreliable)  │
│  Some text   │ Content filter  │ Return partial + finish=filter │
│  Text+Tools  │ Abort (normal)  │ Return full + finish=tool_use  │
│  Text+Tools  │ Circuit breaker │ Return tools + finish=tool_use │
│  Thinking    │ Timeout         │ Return partial + finish=length │
│  Thinking    │ Any other error │ Raise error (thinking invalid) │
└─────────────────────────────────────────────────────────────────┘
```

**Key principle:** If we have captured tool calls, we ALWAYS return them regardless of subsequent errors. The tool calls are the valuable output — the orchestrator needs them to continue the loop.

```python
async def _complete_streaming(self, request, session, ...):
    accumulator = StreamAccumulator()
    try:
        async with asyncio.timeout(effective_timeout):
            await accumulator.wait_for_completion()
    except TimeoutError:
        if accumulator.has_captured_tools():
            # Tools captured before timeout — return them
            logger.warning("Timeout after tool capture — returning captured tools")
            return accumulator.build_response(finish_reason="tool_use")
        elif accumulator.has_content():
            # Partial content — return what we have
            logger.warning("Timeout with partial content — returning partial response")
            return accumulator.build_response(finish_reason="length")
        else:
            # No content at all — raise timeout
            raise CopilotTimeoutError("Stream timed out with no content")
    except Exception as e:
        if accumulator.has_captured_tools():
            # Prioritize tool delivery even on error
            logger.warning(f"Error after tool capture: {e} — returning captured tools")
            return accumulator.build_response(finish_reason="tool_use")
        raise  # Re-raise if no tools captured
```

### 5.2 Stream Interruption Recovery

The provider handles four categories of stream interruption:

**Category 1: Clean completion (no recovery needed)**
```
DELTA... DELTA... ASSISTANT_MESSAGE → SESSION_IDLE → Complete
```

**Category 2: Timeout during generation**
```
DELTA... DELTA... [timeout fires]
→ session.abort()
→ Build partial response from accumulated state
→ Set finish_reason = "length"
```

**Category 3: SDK error event**
```
DELTA... DELTA... ERROR(message)
→ Translate SDK error to domain exception
→ If content accumulated: return partial response
→ If no content: raise translated exception
```

**Category 4: Transport failure (CLI process crash)**
```
DELTA... [CLI process dies]
→ session.on() handler stops receiving events
→ asyncio.timeout fires (no SESSION_IDLE received)
→ Handle as Category 2 (timeout)
→ Additionally: mark client as unhealthy for health check
```

### 5.3 Cleanup on Error

The streaming pipeline has three resources that MUST be cleaned up regardless of how the stream terminates:

```python
async def _complete_streaming(self, request, ...):
    session = None
    unsubscribe = None
    
    try:
        session = await self._client.create_session(config)
        
        handler = SdkEventHandler(...)
        unsubscribe = session.on(handler)  # Returns unsubscribe callable
        
        await session.send(options)
        await handler.wait_for_completion()
        
        return handler.build_response()
    
    finally:
        # CLEANUP ORDER MATTERS:
        # 1. Unsubscribe event handler (stop receiving events)
        if unsubscribe:
            unsubscribe()
        
        # 2. Abort session (stop SDK's internal loop)
        if session:
            try:
                await session.abort()
            except Exception:
                pass  # Best-effort abort
        
        # 3. Disconnect session (release session resources)
        if session:
            try:
                await session.disconnect()
            except Exception:
                pass  # Best-effort disconnect
```

**Why this order:**
1. **Unsubscribe first**: Prevents the handler from processing events after we've started cleanup. Without this, a late-arriving event could mutate the accumulator while we're reading from it.
2. **Abort second**: Tells the SDK to stop its loop. If we disconnect without aborting, the SDK may continue processing in the background.
3. **Disconnect last**: Releases the session's resources in the SDK. This is the "Destroy" in "Deny + Destroy."

---

## 6. Performance Optimization

### 6.1 Memory Efficiency in Streaming

**String concatenation optimization:**

The accumulator appends tokens to buffers. Naive string concatenation (`buffer += token`) is O(n²) over the stream. For long responses (>10K tokens), this matters:

```python
class StreamAccumulator:
    def __init__(self):
        # Use list of chunks + single join at flush time
        self._text_chunks: list[str] = []
        self._thinking_chunks: list[str] = []
    
    def on_text_delta(self, text: str):
        self._text_chunks.append(text)
        # DON'T: self._text_buffer += text  (O(n²))
    
    def flush_text_buffer(self) -> str:
        result = "".join(self._text_chunks)  # O(n) single join
        self._text_chunks.clear()
        return result
```

**Content block memory:**

Content blocks are immutable once created. The accumulator creates them at flush points (block transitions), not at every delta. This means at most 2-3 content blocks per response (thinking + text + possibly another text block), keeping memory allocation minimal.

**Tool request memory:**

Tool requests are typically small (< 1KB each). The `ToolCaptureStrategy.captured_tools` list is bounded by the number of tools the LLM can request in a single turn (practically < 20). No memory optimization needed here.

### 6.2 Event Batching Opportunities

**Current state: No batching (correct for this use case).**

Event batching would introduce latency in the streaming pipeline. Since the primary consumers of streaming events are:
1. **UI rendering** (needs real-time token display)
2. **Logging hooks** (fire-and-forget, latency doesn't matter)
3. **Metrics hooks** (periodic aggregation, not per-event)

Batching would hurt the #1 use case (UI responsiveness) while only marginally improving #2 and #3. The recommendation is:

**DO NOT batch streaming events.** Each delta event should be emitted immediately.

**WHERE batching IS appropriate:**

The final `llm:response` event (emitted once at stream completion) should batch all metrics and accumulated data into a single event payload. This prevents hooks from needing to reconstruct the full response from individual events:

```python
# Single comprehensive event at stream end
await self._emit("llm:response", {
    "provider": self.name,
    "model": model_id,
    "response": chat_response,            # Complete ChatResponse
    "usage": usage_dict,                   # Token counts
    "metrics": stream_metrics.summary(),   # All timing/volume metrics
    "tools_captured": len(tool_requests),  # Tool capture summary
    "thinking_used": bool(thinking_blocks),# Was thinking enabled?
})
```

### 6.3 Async Event Emission

The fire-and-forget pattern using `loop.create_task()` is the correct approach for streaming events. However, there are two failure modes to handle:

**Failure mode 1: No running event loop**

This can happen during interpreter shutdown or in test environments:

```python
def emit(event_name: str, data: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(hooks.emit(event_name, data))
    except RuntimeError:
        pass  # No event loop — silently drop the event
```

**Failure mode 2: Event loop overloaded**

If hundreds of tasks queue up (e.g., very fast token generation + slow hook), the event loop task queue grows. This is bounded by the stream length (typically < 10K events) and each task is lightweight (dict allocation + hook dispatch). No mitigation needed for normal operation.

**Failure mode 3: Hook raises exception**

If a hook handler raises an exception during event processing, it should NOT crash the streaming pipeline. The `create_task` isolation already provides this — unhandled exceptions in tasks are logged by asyncio but don't propagate to the caller. However, we should add a task exception handler:

```python
def _make_emit_callback(self) -> Callable:
    hooks = self._coordinator.hooks

    def emit(event_name: str, data: dict) -> None:
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(hooks.emit(event_name, data))
            task.add_done_callback(_handle_emit_error)
        except RuntimeError:
            pass

    def _handle_emit_error(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.debug(f"Hook emission error (non-fatal): {exc}")

    return emit
```

### 6.4 Connection Reuse

The Copilot SDK manages a single CLI subprocess that handles multiple sessions. The provider's process-level singleton (`_shared_client`) ensures connection reuse:

```
Process A (Amplifier)
  └── _shared_client (CopilotClientWrapper, singleton)
        └── CLI subprocess (one per process, ~500MB)
              └── Session 1 (ephemeral, per complete() call)
              └── Session 2 (ephemeral, concurrent if needed)
              └── ...
```

**Streaming doesn't require additional connection optimization** because:
- Each `complete()` call creates one ephemeral session
- Sessions are short-lived (destroyed after response)
- The CLI subprocess is reused across sessions
- No persistent WebSocket/SSE connections to manage

---

## 7. Complete Streaming Sequence Diagram

### 7.1 Happy Path (Text-Only Response)

```
Provider         SDK Session      CLI Process      LLM API
   │                 │                │               │
   │  send(prompt)   │                │               │
   │────────────────▶│  JSON-RPC      │               │
   │                 │───────────────▶│  HTTP POST    │
   │                 │                │──────────────▶│
   │                 │                │               │
   │                 │                │  SSE stream   │
   │                 │                │◀──────────────│
   │  REASONING_DELTA│  JSON-RPC      │               │
   │◀────────────────│◀───────────────│               │
   │  emit(thinking) │                │               │
   │                 │                │               │
   │  REASONING_DELTA│                │               │
   │◀────────────────│◀───────────────│               │
   │  emit(thinking) │                │               │
   │                 │                │               │
   │  MESSAGE_DELTA  │                │               │
   │◀────────────────│◀───────────────│               │
   │  emit(content)  │                │               │
   │                 │                │               │
   │  MESSAGE_DELTA  │                │ ...           │
   │◀────────────────│◀───────────────│               │
   │  emit(content)  │                │               │
   │                 │                │               │
   │  ASST_MESSAGE   │                │  (stream end) │
   │◀────────────────│◀───────────────│◀──────────────│
   │  accumulate()   │                │               │
   │                 │                │               │
   │  SESSION_IDLE   │                │               │
   │◀────────────────│                │               │
   │  complete!      │                │               │
   │                 │                │               │
   │  disconnect()   │                │               │
   │────────────────▶│                │               │
   │                 │                │               │
   │  ChatResponse   │                │               │
   │ (return)        │                │               │
```

### 7.2 Tool Capture Path

```
Provider         SDK Session      SdkEventHandler    ToolCaptureStrategy
   │                 │                  │                    │
   │  send(prompt)   │                  │                    │
   │────────────────▶│                  │                    │
   │                 │                  │                    │
   │  MESSAGE_DELTA  │                  │                    │
   │◀────────────────│                  │                    │
   │  ──────────────▶│ on_delta()       │                    │
   │                 │  emit(content)   │                    │
   │                 │                  │                    │
   │  ASST_MESSAGE   │                  │                    │
   │  (tool_requests)│                  │                    │
   │◀────────────────│                  │                    │
   │  ──────────────▶│ on_message()     │                    │
   │                 │  ───────────────▶│ capture(turn=1)    │
   │                 │                  │  tools captured!   │
   │                 │                  │◀───────────────────│
   │                 │                  │                    │
   │  preToolUse     │                  │                    │
   │  (SDK attempts) │                  │                    │
   │◀────────────────│                  │                    │
   │  return DENY    │                  │                    │
   │────────────────▶│                  │                    │
   │                 │                  │                    │
   │  SESSION_IDLE   │                  │                    │
   │◀────────────────│                  │                    │
   │  ──────────────▶│ on_idle()        │                    │
   │                 │  tools captured  │                    │
   │                 │  → abort!        │                    │
   │                 │                  │                    │
   │  abort()        │                  │                    │
   │────────────────▶│                  │                    │
   │                 │                  │                    │
   │  disconnect()   │                  │                    │
   │────────────────▶│                  │                    │
   │                 │                  │                    │
   │  ChatResponse   │                  │                    │
   │ (with tools)    │                  │                    │
```

---

## 8. Design Decisions and Trade-offs

### 8.1 Decision: Fire-and-Forget over Awaited Emission

**Chose**: `loop.create_task()` without await  
**Over**: `await hooks.emit()` in handler  
**Because**: Awaiting emission would create backpressure from hooks to SDK transport. A slow hook (e.g., writing to a remote metrics service) would delay token delivery to the UI.  
**Trade-off**: Late-arriving hook events may process after the stream has completed. Hooks must be designed to handle this (e.g., don't assume `llm:content_block` events always arrive before `llm:response`).

### 8.2 Decision: First-Turn-Only Capture over Multi-Turn Deduplication

**Chose**: Capture tools from turn 1 only, ignore subsequent turns  
**Over**: Deduplicate tool calls across turns (comparing name+args)  
**Because**: The SDK's retry behavior after denial may produce different tool calls on subsequent turns (the LLM reformulates). Multi-turn deduplication adds complexity for zero benefit — the first turn's tools are always the "real" ones.  
**Trade-off**: If the SDK ever changes to provide better tool calls on turn 2 (e.g., with self-correction), we'd miss them. This is acceptable because Amplifier's orchestrator handles tool errors and retries at a higher level.

### 8.3 Decision: Single Accumulator over Event Sourcing

**Chose**: Mutable accumulator that builds state incrementally  
**Over**: Immutable event log with reconstruction at completion  
**Because**: Event sourcing adds memory overhead (storing every event) and CPU overhead (reconstructing state from events). The accumulator pattern is O(n) in tokens with O(1) state queries.  
**Trade-off**: We lose the ability to replay the stream. If replay is needed (e.g., for debugging), it should be implemented as a separate debug hook that logs events, not in the core accumulator.

### 8.4 Decision: Provider Timeout Before SDK Timeout

**Chose**: Provider timeout = configured timeout, SDK timeout = configured timeout + 5s buffer  
**Over**: Letting SDK timeout fire first  
**Because**: If the SDK times out, it returns a generic error that loses context (how many tokens were accumulated, were tools captured, etc.). By having the provider timeout fire first, we control the error handling and can return partial responses.  
**Trade-off**: The 5-second buffer is a magic number. If the provider timeout fires very close to the actual operation completion, we might miss a response that would have completed in those 5 seconds. Acceptable because the configured timeout is typically 3600s.

---

## 9. Recommendations for Next Generation

### 9.1 Formalize the StreamAccumulator

The current implementation splits accumulation logic between `SdkEventHandler` and `provider.py`'s `_complete_streaming()`. In the next generation:

- **Extract `StreamAccumulator` as a standalone class** with clear state machine semantics
- **Make it testable in isolation** — inject events, assert state transitions
- **Define the state machine formally**: `IDLE → THINKING → GENERATING → TOOLS_CAPTURED → COMPLETE`

### 9.2 Add Streaming Protocol to Provider Contract

The current `complete()` method returns a complete `ChatResponse`. For first-class streaming support:

```python
class StreamingProvider(Provider, Protocol):
    async def complete(
        self, 
        request: ChatRequest, 
        *,
        on_content: Callable[[ContentDelta], None] | None = None,
        **kwargs,
    ) -> ChatResponse:
        """If on_content is provided, call it for each content delta.
        Always return the complete ChatResponse at the end."""
        ...
```

This keeps backward compatibility (on_content is optional) while formalizing the streaming callback pattern that already exists in the current implementation.

### 9.3 Structured Streaming Events

Replace free-form `dict` event data with typed dataclasses:

```python
@dataclass(frozen=True)
class ContentDelta:
    block_type: Literal["text", "thinking"]
    content: str
    block_index: int
    is_first: bool
    is_last: bool

@dataclass(frozen=True)
class StreamComplete:
    response: ChatResponse
    metrics: StreamMetrics
    tools_captured: int
    finish_reason: str
```

### 9.4 Health-Based Connection Management

If the CLI subprocess crashes during streaming, the client should be marked unhealthy. The next `complete()` call should trigger a health check before creating a new session:

```
complete() → health_check() → [unhealthy] → restart_client() → create_session()
complete() → health_check() → [healthy] → create_session()
```

This is already partially implemented in `client.py` with the ping-based health check. The streaming layer should feed back into this system when transport failures are detected.

---

*End of Streaming Architecture Document*
