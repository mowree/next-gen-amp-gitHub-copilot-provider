# Observability Architecture — Next-Gen GitHub Copilot Provider

**Agent**: Wave 2, Agent 11 — Observability Architecture Expert  
**Date**: 2026-03-08  
**Status**: Design Proposal (Round 1)

---

## 1. Design Philosophy

Observability is not logging. Logging tells you what happened. Observability tells you **why** it happened, **how long** it took, and **what else** was affected. For an AI provider that bridges the Copilot SDK (58 event types) to Amplifier's hook system, observability is the nervous system — without it, debugging is archaeology.

**Core Principles:**

1. **Every event flows** — all 58 SDK events are forwarded; none are silently dropped
2. **Structured over unstructured** — every observation is machine-parseable
3. **Trace context is sacred** — every operation carries a trace ID from entry to exit
4. **Evidence-based testing** — tests produce the same telemetry as production
5. **Zero-cost when off** — observability infrastructure adds no overhead when disabled

---

## 2. Event Bridge Design

### 2.1 Architecture Overview

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Copilot SDK    │────▶│   Event Bridge    │────▶│  Amplifier Hooks │
│  (58 event types)│     │                  │     │                  │
│                  │     │  ┌────────────┐  │     │  hook.emit(name, │
│  on(event, cb)   │     │  │ Transform  │  │     │    payload)      │
│                  │     │  │ + Enrich   │  │     │                  │
│                  │     │  │ + Classify │  │     │                  │
│                  │     │  └────────────┘  │     │                  │
│                  │     │  ┌────────────┐  │     │                  │
│                  │     │  │ OTEL Span  │  │     │                  │
│                  │     │  │ Emitter    │  │     │                  │
│                  │     │  └────────────┘  │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

The Event Bridge is a single module (`event-bridge.ts`) that:
1. Subscribes to ALL SDK events
2. Transforms each into the Amplifier hook schema
3. Emits an OTEL span or event alongside each hook
4. Classifies each event by criticality

### 2.2 Naming Convention

SDK events follow dot-notation (`session.created`, `tool.execution_start`). Amplifier hooks follow the same convention with a provider prefix:

```
SDK Event:        session.created
Amplifier Hook:   copilot:session.created
OTEL Span/Event:  copilot.session.created
```

**Rules:**
- Amplifier hooks: `copilot:{sdk_event_name}` — colon separator for namespace
- OTEL spans/events: `copilot.{sdk_event_name}` — dot separator per OTEL convention
- No renaming, no aliasing — the SDK name IS the canonical name
- Underscore-separated suffixes are preserved: `tool.execution_start` stays as-is

### 2.3 Complete Event Mapping Table

Events are classified into four criticality tiers:

| Tier | Meaning | Action on Failure | Example |
|------|---------|-------------------|---------|
| **CRITICAL** | Must succeed or session fails | Throw, retry, alert | `session.created` |
| **IMPORTANT** | Affects correctness | Log error, continue | `assistant.response` |
| **STANDARD** | Normal telemetry | Log warning, continue | `tool.execution_end` |
| **INFORMATIONAL** | Nice to have | Silently continue | `session.heartbeat` |

#### Session Lifecycle Events (8 events)

| SDK Event | Amplifier Hook | Tier | OTEL Type | Transform Notes |
|-----------|---------------|------|-----------|-----------------|
| `session.created` | `copilot:session.created` | CRITICAL | Span start | Root span; sets trace context |
| `session.ended` | `copilot:session.ended` | CRITICAL | Span end | Closes root span |
| `session.resumed` | `copilot:session.resumed` | IMPORTANT | Span link | Links to previous trace |
| `session.paused` | `copilot:session.paused` | STANDARD | Event | Timestamp + reason |
| `session.compaction_start` | `copilot:session.compaction_start` | STANDARD | Span start | Child of session span |
| `session.compaction_end` | `copilot:session.compaction_end` | STANDARD | Span end | Duration + token delta |
| `session.compaction_error` | `copilot:session.compaction_error` | IMPORTANT | Span error | Error details + context size |
| `session.warning` | `copilot:session.warning` | STANDARD | Event | Warning code + message |

#### Conversation Events (10 events)

| SDK Event | Amplifier Hook | Tier | OTEL Type | Transform Notes |
|-----------|---------------|------|-----------|-----------------|
| `conversation.created` | `copilot:conversation.created` | IMPORTANT | Span start | Child of session |
| `conversation.turn_start` | `copilot:conversation.turn_start` | IMPORTANT | Span start | Child of conversation |
| `conversation.turn_end` | `copilot:conversation.turn_end` | IMPORTANT | Span end | Duration + turn index |
| `conversation.message_added` | `copilot:conversation.message_added` | STANDARD | Event | Role + token count |
| `conversation.context_added` | `copilot:conversation.context_added` | STANDARD | Event | Context type + size |
| `conversation.context_removed` | `copilot:conversation.context_removed` | INFORMATIONAL | Event | Context ID |
| `conversation.truncated` | `copilot:conversation.truncated` | STANDARD | Event | Before/after token counts |
| `conversation.branched` | `copilot:conversation.branched` | STANDARD | Span link | Parent conversation ID |
| `conversation.merged` | `copilot:conversation.merged` | STANDARD | Event | Source conversation IDs |
| `conversation.deleted` | `copilot:conversation.deleted` | INFORMATIONAL | Event | Conversation ID |

#### Assistant Events (12 events)

| SDK Event | Amplifier Hook | Tier | OTEL Type | Transform Notes |
|-----------|---------------|------|-----------|-----------------|
| `assistant.request_start` | `copilot:assistant.request_start` | IMPORTANT | Span start | GenAI span; model + params |
| `assistant.request_end` | `copilot:assistant.request_end` | IMPORTANT | Span end | Response metadata |
| `assistant.response` | `copilot:assistant.response` | IMPORTANT | Event | Content type + length |
| `assistant.response_chunk` | `copilot:assistant.response_chunk` | INFORMATIONAL | Event | Chunk index + size (sampled) |
| `assistant.error` | `copilot:assistant.error` | CRITICAL | Span error | Error code + retry info |
| `assistant.usage` | `copilot:assistant.usage` | IMPORTANT | Event | Token counts (prompt/completion/total) |
| `assistant.tool_call` | `copilot:assistant.tool_call` | STANDARD | Event | Tool name + args summary |
| `assistant.tool_result` | `copilot:assistant.tool_result` | STANDARD | Event | Tool name + result summary |
| `assistant.thinking_start` | `copilot:assistant.thinking_start` | INFORMATIONAL | Span start | Thinking mode indicator |
| `assistant.thinking_end` | `copilot:assistant.thinking_end` | INFORMATIONAL | Span end | Duration |
| `assistant.citation` | `copilot:assistant.citation` | INFORMATIONAL | Event | Source reference |
| `assistant.feedback` | `copilot:assistant.feedback` | STANDARD | Event | Rating + context |

#### Tool Events (10 events)

| SDK Event | Amplifier Hook | Tier | OTEL Type | Transform Notes |
|-----------|---------------|------|-----------|-----------------|
| `tool.registered` | `copilot:tool.registered` | STANDARD | Event | Tool name + schema hash |
| `tool.unregistered` | `copilot:tool.unregistered` | INFORMATIONAL | Event | Tool name |
| `tool.execution_start` | `copilot:tool.execution_start` | STANDARD | Span start | Tool name + input summary |
| `tool.execution_end` | `copilot:tool.execution_end` | STANDARD | Span end | Duration + output summary |
| `tool.execution_error` | `copilot:tool.execution_error` | IMPORTANT | Span error | Error type + tool name |
| `tool.execution_timeout` | `copilot:tool.execution_timeout` | IMPORTANT | Span error | Timeout duration + tool |
| `tool.validation_error` | `copilot:tool.validation_error` | STANDARD | Event | Schema violation details |
| `tool.permission_denied` | `copilot:tool.permission_denied` | IMPORTANT | Event | Tool + permission context |
| `tool.rate_limited` | `copilot:tool.rate_limited` | STANDARD | Event | Tool + retry-after |
| `tool.cache_hit` | `copilot:tool.cache_hit` | INFORMATIONAL | Event | Tool + cache key summary |

#### SubAgent Events (8 events)

| SDK Event | Amplifier Hook | Tier | OTEL Type | Transform Notes |
|-----------|---------------|------|-----------|-----------------|
| `subagent.spawned` | `copilot:subagent.spawned` | IMPORTANT | Span start | Agent type + parent context |
| `subagent.completed` | `copilot:subagent.completed` | IMPORTANT | Span end | Duration + result summary |
| `subagent.failed` | `copilot:subagent.failed` | IMPORTANT | Span error | Error + agent context |
| `subagent.cancelled` | `copilot:subagent.cancelled` | STANDARD | Span end (cancelled) | Reason + partial results |
| `subagent.message` | `copilot:subagent.message` | INFORMATIONAL | Event | Message type + direction |
| `subagent.progress` | `copilot:subagent.progress` | INFORMATIONAL | Event | Progress percentage |
| `subagent.tool_delegated` | `copilot:subagent.tool_delegated` | STANDARD | Event | Tool + target agent |
| `subagent.context_shared` | `copilot:subagent.context_shared` | STANDARD | Event | Context type + size |

#### System Events (10 events)

| SDK Event | Amplifier Hook | Tier | OTEL Type | Transform Notes |
|-----------|---------------|------|-----------|-----------------|
| `system.initialized` | `copilot:system.initialized` | CRITICAL | Span start | Provider version + config |
| `system.shutdown` | `copilot:system.shutdown` | CRITICAL | Span end | Graceful vs forced |
| `system.error` | `copilot:system.error` | CRITICAL | Event | Unhandled error details |
| `system.config_changed` | `copilot:system.config_changed` | STANDARD | Event | Changed keys (no values) |
| `system.health_check` | `copilot:system.health_check` | INFORMATIONAL | Event | Component statuses |
| `system.rate_limit_warning` | `copilot:system.rate_limit_warning` | STANDARD | Event | Limit + current usage |
| `system.auth_refresh` | `copilot:system.auth_refresh` | STANDARD | Span | Duration + success |
| `system.connection_status` | `copilot:system.connection_status` | STANDARD | Event | Connected/disconnected |
| `system.memory_warning` | `copilot:system.memory_warning` | STANDARD | Event | Usage percentage |
| `system.version_mismatch` | `copilot:system.version_mismatch` | IMPORTANT | Event | Expected vs actual |

**Total: 58 events mapped.**

### 2.4 Data Transformation Rules

Each SDK event payload is transformed before emission:

```typescript
interface BridgeTransform {
  // 1. Enrich with trace context
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  
  // 2. Add provider metadata
  provider: 'github-copilot';
  providerVersion: string;
  timestamp: number;  // Unix ms, always provider-side
  
  // 3. Normalize the SDK payload
  event: string;      // Original SDK event name
  tier: EventTier;    // CRITICAL | IMPORTANT | STANDARD | INFORMATIONAL
  payload: Record<string, unknown>;  // SDK payload, redacted
  
  // 4. Redaction
  // - No raw user content in telemetry
  // - Tool arguments: summary only (type + length)
  // - Token counts: always included
  // - Error messages: included (no stack traces in production)
}
```

**Redaction Rules:**
- User messages: replaced with `{content_length: N, role: "user"}`
- Assistant responses: replaced with `{content_length: N, chunk_count: M}`
- Tool arguments: replaced with `{arg_count: N, schema_hash: "abc123"}`
- Tool results: replaced with `{result_type: "string", result_length: N}`
- Exception: Debug mode disables redaction for local development

---

## 3. OpenTelemetry Integration

### 3.1 Span Structure

The provider creates a hierarchical span tree that maps to the natural lifecycle:

```
copilot.session (root span)
├── copilot.conversation
│   ├── copilot.conversation.turn
│   │   ├── copilot.assistant.request       ← GenAI span
│   │   │   ├── copilot.assistant.thinking  (optional)
│   │   │   └── copilot.tool.execution      (0..N)
│   │   └── copilot.subagent.execution      (0..N)
│   │       ├── copilot.assistant.request    ← nested GenAI span
│   │       └── copilot.tool.execution      (0..N)
│   └── copilot.session.compaction          (if triggered)
└── copilot.system.auth_refresh             (if triggered)
```

### 3.2 GenAI Semantic Convention Mapping (v1.34.0)

The `assistant.request_start` / `assistant.request_end` pair creates a GenAI span following the [OpenTelemetry GenAI Semantic Conventions v1.34.0](https://opentelemetry.io/docs/specs/semconv/gen-ai/):

| OTEL GenAI Attribute | Source | Example |
|---------------------|--------|---------|
| `gen_ai.system` | Hardcoded | `"github.copilot"` |
| `gen_ai.request.model` | SDK event payload | `"gpt-4o"` |
| `gen_ai.request.max_tokens` | SDK event payload | `4096` |
| `gen_ai.request.temperature` | SDK event payload | `0.1` |
| `gen_ai.request.top_p` | SDK event payload | `1.0` |
| `gen_ai.request.stop_sequences` | SDK event payload | `["```"]` |
| `gen_ai.response.id` | SDK event payload | `"chatcmpl-abc123"` |
| `gen_ai.response.model` | SDK event payload | `"gpt-4o-2025-01"` |
| `gen_ai.response.finish_reasons` | SDK event payload | `["stop"]` |
| `gen_ai.usage.input_tokens` | `assistant.usage` event | `1523` |
| `gen_ai.usage.output_tokens` | `assistant.usage` event | `847` |
| `gen_ai.usage.total_tokens` | Computed | `2370` |
| `gen_ai.prompt` | Redacted | `{role: "user", length: 423}` |
| `gen_ai.completion` | Redacted | `{length: 847, chunks: 12}` |

**Tool-call attributes (per GenAI tool convention):**

| OTEL Attribute | Source | Example |
|---------------|--------|---------|
| `gen_ai.tool.name` | `assistant.tool_call` | `"read_file"` |
| `gen_ai.tool.call_id` | SDK payload | `"call_abc123"` |
| `gen_ai.tool.type` | Inferred | `"function"` |

### 3.3 Trace Context Propagation

```
┌─────────────┐    W3C TraceContext    ┌─────────────┐
│  Amplifier   │◄─────────────────────▶│  Provider    │
│  (parent)    │   traceparent header  │             │
└─────────────┘                        └──────┬──────┘
                                              │
                                    Inject into SDK
                                              │
                                       ┌──────▼──────┐
                                       │ Copilot API  │
                                       │ (if supported)│
                                       └─────────────┘
```

**Propagation Rules:**
1. Amplifier passes `traceparent` and `tracestate` headers to the provider
2. Provider creates child spans under the Amplifier trace
3. If Copilot API supports trace headers, provider injects them
4. If not, provider creates a span link to mark the boundary
5. SubAgent spans are children of the spawning turn span

**Context Storage:**
```typescript
// Per-session context stored in AsyncLocalStorage
interface SessionTraceContext {
  traceId: string;
  sessionSpanId: string;
  conversationSpanId?: string;
  turnSpanId?: string;
  baggage: Map<string, string>;  // session metadata
}
```

### 3.4 Exporter Configuration

```typescript
interface OTELConfig {
  // Where to send traces
  exporter: 'otlp-grpc' | 'otlp-http' | 'console' | 'none';
  endpoint?: string;  // Default: http://localhost:4317
  
  // Sampling
  sampler: 'always_on' | 'always_off' | 'trace_id_ratio' | 'parent_based';
  sampleRate?: number;  // For ratio sampler, default 1.0
  
  // Resource attributes
  serviceName: 'amplifier-copilot-provider';
  serviceVersion: string;  // From package.json
  
  // Batching
  batchSize: 512;
  exportTimeout: 30_000;  // ms
  scheduleDelay: 5_000;   // ms
}
```

---

## 4. Test Evidence System

### 4.1 Philosophy

Every test is a mini-observability session. Tests don't just assert outcomes — they produce **structured evidence** that can be compared across runs, analyzed for regressions, and used to validate the observability pipeline itself.

### 4.2 Evidence Emission

```typescript
// Every test emits evidence through the same Event Bridge
interface TestEvidence {
  testId: string;           // Unique test identifier
  testSuite: string;        // Suite name
  timestamp: number;
  
  // The events captured during this test
  events: CapturedEvent[];
  
  // Assertions made and their results
  assertions: AssertionRecord[];
  
  // Performance measurements
  timings: {
    totalMs: number;
    setupMs: number;
    executionMs: number;
    teardownMs: number;
  };
  
  // Resource usage
  resources: {
    tokensUsed?: number;
    apiCallsMade: number;
    toolExecutions: number;
  };
}

interface CapturedEvent {
  event: string;          // SDK event name
  timestamp: number;
  payload: unknown;       // Full payload (not redacted in tests)
  spanContext?: {
    traceId: string;
    spanId: string;
  };
}
```

### 4.3 Evidence Storage Structure

```
test-evidence/
├── baselines/                    # Approved baseline evidence
│   ├── session-lifecycle.json
│   ├── tool-execution.json
│   └── error-handling.json
├── current/                      # Latest test run evidence
│   ├── session-lifecycle.json
│   ├── tool-execution.json
│   └── error-handling.json
├── snapshots/                    # Historical snapshots
│   ├── 2026-03-08T10:00:00Z/
│   └── 2026-03-07T15:30:00Z/
└── regressions/                  # Detected regressions
    └── 2026-03-08T10:36:00Z.json
```

### 4.4 Baseline Comparison for Regression Detection

```typescript
interface BaselineComparison {
  // Event sequence must match (order + event names)
  eventSequence: 'exact' | 'subset' | 'superset';
  
  // Timing thresholds (percentage deviation allowed)
  timingTolerance: {
    total: 0.20;     // 20% slower is a warning
    perEvent: 0.50;  // 50% slower per-event is a warning
  };
  
  // Token usage deviation
  tokenTolerance: {
    prompt: 0.10;      // 10% more prompt tokens is notable
    completion: 0.15;  // 15% more completion tokens is notable
  };
  
  // New events not in baseline
  newEventsPolicy: 'warn' | 'fail';
  
  // Missing events from baseline
  missingEventsPolicy: 'fail';  // Always fail on missing events
}
```

**Comparison Algorithm:**
1. Load baseline evidence for the test
2. Run test, capture current evidence
3. Compare event sequences (name + order)
4. Compare timing distributions (flag outliers)
5. Compare token usage (flag significant increases)
6. Report: PASS / WARN / REGRESSION

---

## 5. Metrics Strategy

### 5.1 Core Metrics

Metrics are exposed via OTEL Metrics SDK and optionally via a Prometheus-compatible endpoint.

#### Token Metrics

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `copilot.tokens.input` | Counter | `model`, `session_id` | Total input tokens consumed |
| `copilot.tokens.output` | Counter | `model`, `session_id` | Total output tokens consumed |
| `copilot.tokens.total` | Counter | `model` | Total tokens (input + output) |
| `copilot.tokens.compaction_saved` | Counter | `session_id` | Tokens saved by compaction |
| `copilot.tokens.context_window_usage` | Gauge | `model`, `session_id` | % of context window used |

#### Latency Metrics

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `copilot.request.duration_ms` | Histogram | `model`, `status` | LLM request duration |
| `copilot.request.ttfb_ms` | Histogram | `model` | Time to first byte (streaming) |
| `copilot.tool.duration_ms` | Histogram | `tool_name`, `status` | Tool execution duration |
| `copilot.turn.duration_ms` | Histogram | `session_id` | Full turn duration |
| `copilot.subagent.duration_ms` | Histogram | `agent_type`, `status` | SubAgent execution duration |

#### Error Metrics

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `copilot.errors.total` | Counter | `error_type`, `component` | Total errors by type |
| `copilot.errors.retries` | Counter | `error_type` | Number of retries attempted |
| `copilot.errors.rate_limits` | Counter | `model` | Rate limit hits |
| `copilot.tool.errors` | Counter | `tool_name`, `error_type` | Tool-specific errors |

#### Session Metrics

| Metric Name | Type | Labels | Description |
|------------|------|--------|-------------|
| `copilot.sessions.active` | Gauge | — | Currently active sessions |
| `copilot.sessions.total` | Counter | `status` | Sessions created (by outcome) |
| `copilot.sessions.duration_ms` | Histogram | — | Session duration |
| `copilot.turns.per_session` | Histogram | — | Turns per session |
| `copilot.compactions.total` | Counter | `trigger_reason` | Compactions performed |

### 5.2 Metric Exposure

```typescript
interface MetricsConfig {
  // OTEL Metrics exporter
  exporter: 'otlp' | 'prometheus' | 'console' | 'none';
  
  // Prometheus endpoint (if exporter is 'prometheus')
  prometheusPort?: number;  // Default: 9464
  prometheusPath?: string;  // Default: /metrics
  
  // Collection interval
  collectInterval: 15_000;  // ms
  
  // Histogram buckets for latency
  latencyBuckets: [10, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000];
}
```

### 5.3 Derived Metrics (Computed, Not Collected)

These are calculated from raw metrics, not directly collected:

- **Token Efficiency**: `output_tokens / input_tokens` — measures how concise responses are
- **Tool Success Rate**: `tool_successes / tool_executions` — per tool name
- **Error Rate**: `errors / requests` — over sliding window
- **Compaction Frequency**: `compactions / session_duration` — indicates context pressure
- **SubAgent Overhead**: `subagent_time / total_turn_time` — delegation cost

---

## 6. Debug Observability

### 6.1 When Things Go Wrong

Debugging an AI provider is uniquely challenging because:
- The LLM is non-deterministic — same input can produce different outputs
- Tool chains can be long — one bad tool result cascades
- Context windows are invisible — you can't see what the model "sees"
- SubAgents add nesting depth — errors can be deeply buried

**Critical Debug Signals:**

| Signal | Why It Matters | How We Capture It |
|--------|---------------|-------------------|
| Context window contents | What the model saw when it failed | Snapshot on error (debug mode only) |
| Tool execution chain | Which tools ran before the error | Span tree with tool spans |
| Token usage trajectory | Context growing too fast? | Per-turn token gauge |
| Error correlation | Is this error related to others? | Trace ID linking |
| Timing anomalies | Unusually slow? Timeout? | Latency histograms + alerts |
| SubAgent state | What was the subagent doing? | Nested spans + events |

### 6.2 Session Replay

Session replay allows developers to reconstruct exactly what happened in a session:

```typescript
interface SessionReplay {
  sessionId: string;
  
  // Complete event timeline
  timeline: Array<{
    timestamp: number;
    event: string;
    direction: 'inbound' | 'outbound' | 'internal';
    payload: unknown;  // Redacted in prod, full in debug
    spanContext: SpanContext;
  }>;
  
  // Conversation state at each turn boundary
  turnSnapshots: Array<{
    turnIndex: number;
    messageCount: number;
    tokenUsage: { input: number; output: number; total: number };
    toolCallsSoFar: number;
    contextWindowPercent: number;
  }>;
  
  // Error events with full context
  errors: Array<{
    timestamp: number;
    error: Error;
    precedingEvents: string[];  // Last 5 events before error
    spanContext: SpanContext;
  }>;
}
```

**Replay Storage:**
- Debug mode: Full replay stored in memory, dumped to file on error or session end
- Production mode: Only error-adjacent events stored (5 events before + after each error)
- Storage: Local filesystem or configurable sink (S3, GCS, etc.)

### 6.3 Error Correlation

Errors are correlated across three dimensions:

1. **Temporal**: Events within ±5 seconds of an error
2. **Causal**: Events in the same span tree branch
3. **Categorical**: Errors with the same error code across sessions

```typescript
interface ErrorCorrelation {
  errorId: string;
  traceId: string;
  
  // Temporal neighbors
  temporalContext: CapturedEvent[];
  
  // Span ancestors
  spanAncestors: Array<{
    spanName: string;
    spanId: string;
    status: 'ok' | 'error';
  }>;
  
  // Similar errors in recent sessions
  relatedErrors: Array<{
    sessionId: string;
    errorCode: string;
    similarity: number;  // 0-1
  }>;
}
```

---

## 7. AI Agent Observability

### 7.1 When AI Writes This Code

AI agents maintaining this codebase need observability signals that are different from human developers:

| Human Need | AI Agent Need | How We Serve Both |
|-----------|--------------|-------------------|
| "What broke?" | "What changed and broke?" | Git-aware error context |
| "Show me the logs" | "Structured event stream" | JSON-structured events |
| "Which test failed?" | "Which assertion in which test with which input?" | Rich test evidence |
| "Is this a regression?" | "Baseline comparison with diff" | Automated baseline diffing |
| "What's the architecture?" | "Module dependency graph" | OTEL span tree = architecture |

### 7.2 AI Development Process Observability

When an AI agent is developing or maintaining this provider, we observe:

```typescript
interface AIDevelopmentEvent {
  type: 'code_change' | 'test_run' | 'lint_result' | 'build_result';
  
  // What the AI was trying to do
  intent: string;
  
  // What actually happened
  outcome: 'success' | 'failure' | 'partial';
  
  // Evidence
  evidence: {
    filesChanged: string[];
    testsRun: number;
    testsPassed: number;
    testsFailed: number;
    lintErrors: number;
    typeErrors: number;
  };
  
  // Regression check
  baselineComparison?: {
    newEvents: string[];       // Events not in baseline
    missingEvents: string[];   // Events missing from baseline
    timingDrift: number;       // % change in total timing
    tokenDrift: number;        // % change in token usage
  };
}
```

### 7.3 Self-Healing Observability

The observability system should help AI agents fix themselves:

1. **Test Evidence as Feedback**: When a test fails, the captured events + assertions provide the AI with exactly what went wrong, not just "test failed"
2. **Baseline Diffs as Guides**: When a regression is detected, the diff shows the AI exactly which events changed and how
3. **Span Trees as Architecture Maps**: The OTEL span tree IS the module dependency graph — AI agents can read it to understand how components interact
4. **Error Correlation as Root Cause**: Correlated errors point the AI directly to the root cause instead of surface symptoms

---

## 8. Implementation Module Specification

### 8.1 Module: `event-bridge`

```
src/observability/
├── event-bridge.ts        # Core bridge: SDK events → Amplifier hooks + OTEL
├── event-catalog.ts       # Static catalog of all 58 events + metadata
├── transforms.ts          # Payload transformation + redaction
├── otel-spans.ts          # Span lifecycle management
├── otel-metrics.ts        # Metric instruments
├── test-evidence.ts       # Test evidence capture + comparison
├── session-replay.ts      # Debug session replay
├── types.ts               # Shared types
└── index.ts               # Public API
```

### 8.2 Public API Surface

```typescript
// index.ts — the ONLY public interface
export { EventBridge } from './event-bridge';
export { TestEvidenceCollector } from './test-evidence';
export { SessionReplay } from './session-replay';
export type { 
  BridgeConfig, 
  EventTier, 
  TestEvidence, 
  BaselineComparison 
} from './types';
```

### 8.3 Integration Points

```typescript
// In the provider's main initialization:
const bridge = new EventBridge({
  sdk: copilotSdk,
  hooks: amplifierHooks,
  otel: otelConfig,
  redaction: isProduction ? 'full' : 'none',
});

// Bridge subscribes to ALL 58 events automatically
bridge.start();

// In tests:
const evidence = new TestEvidenceCollector(bridge);
evidence.startCapture('test-session-lifecycle');
// ... run test ...
const result = evidence.stopCapture();
const comparison = evidence.compareToBaseline(result, 'session-lifecycle');
```

---

## 9. Configuration & Feature Flags

```typescript
interface ObservabilityConfig {
  // Master switch
  enabled: boolean;  // Default: true
  
  // Event bridge
  eventBridge: {
    enabled: boolean;         // Default: true
    tierFilter: EventTier[];  // Default: all tiers
    samplingRate: number;     // Default: 1.0 (for INFORMATIONAL events)
  };
  
  // OTEL
  otel: {
    traces: OTELConfig;
    metrics: MetricsConfig;
  };
  
  // Debug
  debug: {
    sessionReplay: boolean;   // Default: false in prod
    fullPayloads: boolean;    // Default: false in prod
    consoleEvents: boolean;   // Default: false
  };
  
  // Test evidence
  testEvidence: {
    enabled: boolean;         // Default: true in test env
    baselinePath: string;     // Default: './test-evidence/baselines'
    autoBaseline: boolean;    // Default: false (manual approval)
  };
}
```

---

## 10. Summary & Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Event naming | `copilot:{sdk_name}` for hooks, `copilot.{sdk_name}` for OTEL | Direct mapping, no confusion |
| Redaction default | Full redaction in prod | Security first |
| Span structure | Hierarchical session→conversation→turn→request | Matches natural lifecycle |
| GenAI convention | v1.34.0 strict compliance | Future-proof, standard |
| Test evidence | Structured JSON with baseline comparison | AI-friendly, regression-detecting |
| Metrics exposure | OTEL metrics + optional Prometheus | Standard, flexible |
| Session replay | Debug-only full replay, prod error-adjacent only | Performance vs debuggability |
| AI observability | Same system, richer test evidence | One system to maintain |

**The observability system is the immune system of the provider.** It detects problems (metrics + alerts), explains them (traces + events), proves fixes work (test evidence), and helps AI agents self-heal (structured feedback). Build it first, build it right, and every other component benefits.