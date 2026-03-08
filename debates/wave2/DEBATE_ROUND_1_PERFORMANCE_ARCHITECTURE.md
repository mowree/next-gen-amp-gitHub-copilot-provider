# Wave 2, Agent 16: Performance & Efficiency Architecture

**Agent Role**: Performance & Efficiency Expert  
**Date**: 2026-03-08  
**Subject**: Latency budgets, connection management, caching, async patterns, resource efficiency, and performance testing for the next-generation GitHub Copilot provider

---

## Executive Summary

The current provider pays a **per-request tax** of ~200–800ms in overhead that is entirely avoidable. The three dominant costs are: (1) CLI subprocess health-check ping on every `complete()` call, (2) ephemeral SDK session creation/teardown per request, and (3) synchronous event handling blocking the streaming pipeline. A redesigned performance architecture targets **<50ms provider overhead** (time spent outside the LLM itself) through client warmup, session lifecycle optimization, strategic caching, and fully async event dispatch. Every optimization is measured against a latency budget, and every cache has an explicit invalidation contract.

---

## 1. Latency Budget

### 1.1 Current Latency Breakdown (Estimated)

A single `complete()` call currently traverses this critical path:

```
complete() called
 ├─ Health check ping (client.py:196)         ~30–100ms  (JSON-RPC round-trip to CLI subprocess)
 ├─ Session creation (client.py:580)          ~50–200ms  (SDK allocates session, configures tools)
 │   ├─ Tool registration (27 built-in exclusions + user tools)  ~10–50ms
 │   └─ Permission handler setup              ~5–10ms
 ├─ Message conversion (converters.py)        ~1–5ms     (CPU-bound, proportional to message count)
 ├─ send_and_wait / send (SDK)                ~500–60000ms (LLM latency — NOT our problem)
 ├─ Event handling (sdk_driver.py)            ~5–20ms    (per event, synchronous dispatch)
 ├─ Fake tool call detection (provider.py)    ~1–5ms     (regex over response text)
 ├─ Response conversion                       ~1–5ms     (CPU-bound)
 ├─ Session disconnect (client.py:600)        ~20–80ms   (SDK session teardown)
 └─ Error translation                         ~<1ms      (exception mapping)

Total provider overhead: ~120–475ms per request (excluding LLM time)
Worst case with retries: ~800ms+ overhead
```

### 1.2 Target Latency Budget

| Operation | Current | Target | Strategy |
|-----------|---------|--------|----------|
| Client health check | 30–100ms | 0ms (amortized) | Background heartbeat, not per-request |
| Session creation | 50–200ms | 0–10ms | Session pooling or warm creation |
| Tool registration | 10–50ms | 0ms | Pre-built tool set caching |
| Message conversion | 1–5ms | 1–3ms | Minor; optimize only if >100 messages |
| Event dispatch | 5–20ms/event | <1ms/event | Fully async, non-blocking |
| Session disconnect | 20–80ms | 0ms (background) | Fire-and-forget cleanup |
| Fake tool call check | 1–5ms | 1–3ms | Compiled regex (already done) |
| Response conversion | 1–5ms | 1–3ms | Minor optimization |
| **Total overhead** | **120–475ms** | **<50ms** | **4–10x improvement** |

### 1.3 Latency Categories

**P0 — User-perceived latency** (time-to-first-token):
- Target: <100ms provider overhead before first streaming token
- This is the metric users feel. Everything before the first `ASSISTANT_MESSAGE_DELTA` event counts.

**P1 — Request overhead** (total non-LLM time per complete()):
- Target: <50ms total provider overhead
- Includes setup, teardown, conversion, event handling

**P2 — Background overhead** (amortized across requests):
- Health checks, cache warming, session pool maintenance
- Target: zero impact on request latency

---

## 2. Connection Management

### 2.1 Current Architecture: Singleton CLI Client

The provider uses a process-level singleton `CopilotClient` that manages a single CLI subprocess. This is correct — spawning multiple CLI processes (~500MB each) would be catastrophic. However, the current lifecycle has inefficiencies:

```
Current: Per-Request Session Pattern
─────────────────────────────────────
Request 1: [health-check] → [create-session] → [LLM] → [disconnect-session]
Request 2: [health-check] → [create-session] → [LLM] → [disconnect-session]
Request 3: [health-check] → [create-session] → [LLM] → [disconnect-session]
```

### 2.2 Optimized Client Lifecycle

#### Strategy A: Background Heartbeat (Recommended)

Replace per-request health checks with a background heartbeat task:

```python
class ClientHealthMonitor:
    """Background health monitor for the shared CLI client."""
    
    def __init__(self, client: CopilotClient, interval: float = 15.0):
        self._client = client
        self._interval = interval
        self._healthy = True
        self._last_check: float = 0.0
        self._task: asyncio.Task | None = None
    
    async def start(self) -> None:
        self._task = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self) -> None:
        while True:
            try:
                await self._client.ping()
                self._healthy = True
                self._last_check = time.monotonic()
            except Exception:
                self._healthy = False
            await asyncio.sleep(self._interval)
    
    @property
    def is_healthy(self) -> bool:
        """Non-blocking health check. Falls back to stale-OK within grace period."""
        if self._healthy:
            return True
        # If last successful check was within 2x interval, still consider healthy
        return (time.monotonic() - self._last_check) < (self._interval * 2)
```

**Impact**: Eliminates 30–100ms health check from every request. Background task runs every 15s regardless of request volume.

#### Strategy B: Lazy Health Check with Exponential Backoff

If background tasks are undesirable (e.g., resource-constrained environments):

```python
class LazyHealthChecker:
    """Check health only after failures or long idle periods."""
    
    IDLE_THRESHOLD = 60.0  # seconds
    
    def __init__(self):
        self._last_successful_request: float = 0.0
        self._consecutive_failures: int = 0
    
    def needs_check(self) -> bool:
        if self._consecutive_failures > 0:
            return True
        idle_time = time.monotonic() - self._last_successful_request
        return idle_time > self.IDLE_THRESHOLD
    
    def record_success(self) -> None:
        self._last_successful_request = time.monotonic()
        self._consecutive_failures = 0
    
    def record_failure(self) -> None:
        self._consecutive_failures += 1
```

**Impact**: Skip health check for most requests. Only check after errors or 60s idle.

### 2.3 Session Lifecycle Optimization

The "Deny + Destroy" pattern requires ephemeral sessions — we cannot reuse SDK sessions because each `complete()` call needs fresh tool registration and system message configuration. However, we can optimize the session lifecycle:

#### Optimization 1: Parallel Session Creation

Start session creation concurrently with message conversion:

```python
async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
    # Start session creation and message conversion in parallel
    session_config = self._build_session_config(request)
    
    session_coro = self._client.create_session(session_config)
    convert_coro = asyncio.to_thread(self._convert_messages, request.messages)
    
    session, converted_messages = await asyncio.gather(session_coro, convert_coro)
    
    try:
        response = await self._execute_session(session, converted_messages)
    finally:
        # Fire-and-forget disconnect
        asyncio.create_task(self._safe_disconnect(session))
    
    return response
```

**Impact**: Overlaps ~50–200ms session creation with ~1–5ms message conversion. Net savings: up to 5ms (message conversion time hidden behind session creation).

#### Optimization 2: Fire-and-Forget Session Disconnect

Session disconnect is a teardown operation that doesn't affect the response. It should not block the return path:

```python
async def _safe_disconnect(self, session) -> None:
    """Disconnect session without blocking the caller."""
    try:
        await asyncio.wait_for(session.disconnect(), timeout=5.0)
    except Exception:
        pass  # Best-effort cleanup; CLI will GC the session anyway
```

**Impact**: Removes 20–80ms from the critical path. Session cleanup happens after the response is returned.

#### Optimization 3: Pre-Built Tool Set

Tool registration is repeated identically for every request with the same tool set. Cache the built tool objects:

```python
class ToolSetCache:
    """Cache built Tool objects for reuse across sessions."""
    
    def __init__(self):
        self._cache: dict[frozenset[str], list[Tool]] = {}
    
    def get_or_build(
        self,
        tool_names: frozenset[str],
        builder: Callable[[frozenset[str]], list[Tool]],
    ) -> list[Tool]:
        if tool_names not in self._cache:
            self._cache[tool_names] = builder(tool_names)
        return self._cache[tool_names]
```

**Impact**: Saves 10–50ms on tool object construction for repeat requests with the same tools.

### 2.4 Warm-Up Strategy

At mount time, the provider should warm critical resources:

```python
async def mount(coordinator, config: dict) -> Callable | None:
    provider = GitHubCopilotProvider(config=config, coordinator=coordinator)
    
    # Warm-up sequence (parallel where possible)
    await asyncio.gather(
        provider.warm_client(),       # Ensure CLI subprocess is alive
        provider.warm_model_cache(),  # Pre-populate model metadata
    )
    
    await coordinator.mount("providers", provider, name="github-copilot")
    return provider.cleanup
```

```python
async def warm_client(self) -> None:
    """Ensure CLI client is started and responsive."""
    await self._client.ensure_client()
    await self._client.ping()  # Verify responsiveness
    self._health_monitor.record_success()

async def warm_model_cache(self) -> None:
    """Pre-populate model cache to avoid first-request penalty."""
    try:
        models = await self._client.list_models()
        self._model_cache.update(models)
    except Exception:
        pass  # Fall through to disk cache or bundled defaults
```

**Impact**: First `complete()` call avoids cold-start penalties. Mount time increases by ~200ms but this happens once per session.

---

## 3. Caching Strategy

### 3.1 What to Cache

| Data | Cache Location | TTL | Invalidation | Justification |
|------|---------------|-----|-------------|---------------|
| Model list + capabilities | Memory + Disk | 30 days (disk), session (memory) | Manual or on SDK error | Rarely changes; avoids API call per session |
| Model supports-reasoning flag | Memory | Session lifetime | Never (immutable per model) | Called per `complete()` via double-checked lock |
| Built Tool objects | Memory | Until tool set changes | On tool set hash change | Avoids re-constructing Tool objects |
| Compiled regexes | Module-level | Process lifetime | Never | Already done; verify with `re.compile()` |
| Session config templates | Memory | Until config changes | On config change | Avoid rebuilding SessionConfig each request |
| Converted built-in exclusion list | Memory | Process lifetime | Never | `sorted(COPILOT_BUILTIN_TOOL_NAMES)` is static |

### 3.2 What NOT to Cache

| Data | Reason |
|------|--------|
| SDK sessions | "Deny + Destroy" requires fresh sessions |
| Auth tokens | Managed by SDK/CLI internally |
| Conversation history | Owned by ContextManager, not provider |
| LLM responses | Provider is stateless; orchestrator owns response history |
| Health check results | Stale health data is dangerous — use background heartbeat instead |

### 3.3 Model Cache Simplification

The current 4-tier cache (memory → disk → bundled → defaults) is over-engineered. The performance-optimal design:

**Tier 1: Memory (hot path)**
```python
class ModelCapabilityCache:
    """In-memory cache for model capabilities. Populated at warm-up."""
    
    def __init__(self):
        self._models: dict[str, ModelInfo] = {}
        self._populated = False
    
    def get(self, model_id: str) -> ModelInfo | None:
        return self._models.get(model_id)
    
    def populate(self, models: list[ModelInfo]) -> None:
        self._models = {m.id: m for m in models}
        self._populated = True
    
    @property
    def is_populated(self) -> bool:
        return self._populated
```

**Tier 2: Bundled defaults (cold path)**
```python
BUNDLED_MODEL_LIMITS: dict[str, ModelLimits] = {
    "claude-opus-4.5": ModelLimits(context=200000, max_output=32000),
    "gpt-4o": ModelLimits(context=128000, max_output=16384),
    # ... 21 models
}
```

**Remove Tier 3 (disk cache)**: The disk cache adds ~5ms read latency, atomic write complexity, and file permission edge cases on Windows. The bundled defaults cover all known models. If `list_models()` succeeds at warm-up, memory cache is populated. If it fails, bundled defaults are sufficient. The 30-day disk cache is solving a problem that doesn't meaningfully exist.

### 3.4 Cache Warming Sequence

```
Mount time:
  1. Load bundled defaults into memory cache (instant, 0ms)
  2. Attempt list_models() API call (background, ~100-500ms)
  3. If successful, overlay API results onto memory cache
  4. If failed, memory cache still has bundled defaults

First complete() call:
  - Memory cache hit: 0ms overhead
  - Memory cache miss (unknown model): use bundled defaults, log warning
```

### 3.5 Cache Invalidation Contract

| Cache | Invalidation Trigger | Behavior |
|-------|---------------------|----------|
| Model capabilities (memory) | `list_models()` called | Full replacement |
| Model capabilities (memory) | Model-not-found error from SDK | Remove single entry, trigger background refresh |
| Tool set cache | Tool names change between requests | Hash-based eviction |
| Session config template | Provider config changes | Full rebuild |

**Rule**: No time-based invalidation for in-memory caches. Memory caches are invalidated by events, not timers. This eliminates TTL-check overhead from the hot path.

---

## 4. Async Excellence

### 4.1 Concurrent Operation Opportunities

The current codebase has several places where sequential operations could be concurrent:

#### Mount-Time Parallelism
```python
# Current: sequential
await client.start()
models = await client.list_models()
auth = await client.get_auth_status()

# Optimized: parallel
await client.start()
models, auth = await asyncio.gather(
    client.list_models(),
    client.get_auth_status(),
    return_exceptions=True,
)
```

#### Request-Time Parallelism
```python
# Current: sequential in complete()
session = await client.create_session(config)
# ... then send

# Optimized: overlap session creation with message preparation
async def complete(self, request, **kwargs):
    # These don't depend on each other
    session_task = asyncio.create_task(
        self._client.create_session(self._build_config(request))
    )
    messages = self._convert_messages(request.messages)
    tools = self._tool_cache.get_or_build(request.tool_names, self._build_tools)
    
    session = await session_task
    # Now use session with pre-built messages and tools
```

### 4.2 Event Dispatch: Fully Async, Non-Blocking

The SDK event handler (`SdkEventHandler`) currently processes events synchronously within the SDK's event loop. This creates backpressure on the streaming pipeline.

**Current pattern** (problematic):
```python
def on_event(self, event):
    # This blocks the SDK's event dispatch thread
    self._process_event(event)  # synchronous
    self._emit_to_amplifier(event)  # synchronous, may involve I/O
```

**Target pattern** (non-blocking):
```python
class AsyncEventDispatcher:
    """Non-blocking event dispatcher for SDK events."""
    
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=256)
        self._handlers: list[Callable] = []
    
    def enqueue(self, event: Event) -> None:
        """Called from SDK callback — MUST be non-blocking."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop oldest event under pressure
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(event)
            except asyncio.QueueEmpty:
                pass
    
    async def dispatch_loop(self) -> None:
        """Process events from queue. Runs as background task."""
        while True:
            event = await self._queue.get()
            for handler in self._handlers:
                try:
                    await handler(event)
                except Exception:
                    pass  # Event handlers must not crash the dispatch loop
```

**Impact**: SDK event callbacks return in <1μs (just a queue put). Actual event processing happens asynchronously without blocking the streaming pipeline.

### 4.3 Streaming Pipeline Optimization

The streaming path is the most latency-sensitive code in the provider. Current flow:

```
SDK event → SdkEventHandler → tool capture check → emit to Amplifier → yield to caller
```

Optimized flow with pipelining:

```python
class StreamPipeline:
    """Zero-copy streaming pipeline from SDK to Amplifier."""
    
    def __init__(self):
        self._buffer: asyncio.Queue[StreamChunk | None] = asyncio.Queue()
        self._tool_requests: list[ToolRequest] = []
        self._first_token_time: float | None = None
    
    async def feed(self, event: SessionEvent) -> None:
        """Called by event dispatcher. Processes and enqueues chunks."""
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            chunk = self._to_stream_chunk(event.data)
            if self._first_token_time is None:
                self._first_token_time = time.monotonic()
            await self._buffer.put(chunk)
        elif event.type == SessionEventType.ASSISTANT_MESSAGE:
            # Capture tool requests from complete message
            if hasattr(event.data, 'tool_requests') and event.data.tool_requests:
                self._tool_requests.extend(event.data.tool_requests)
    
    async def chunks(self) -> AsyncIterator[StreamChunk]:
        """Yields chunks as they arrive. Non-blocking consumption."""
        while True:
            chunk = await self._buffer.get()
            if chunk is None:  # Sentinel for end-of-stream
                return
            yield chunk
```

### 4.4 Backpressure Handling

Backpressure occurs when the consumer (Amplifier orchestrator) processes chunks slower than the SDK produces them. Strategy:

1. **Bounded queue** (256 items): Prevents unbounded memory growth
2. **Drop-oldest on overflow**: For streaming deltas, old chunks are less valuable than new ones
3. **Monitoring**: Track queue depth as a performance metric
4. **No flow control to SDK**: The CLI subprocess streams at its own pace; we buffer, not throttle

```python
class BackpressureMonitor:
    """Track streaming backpressure for observability."""
    
    def __init__(self, queue: asyncio.Queue, high_watermark: int = 200):
        self._queue = queue
        self._high_watermark = high_watermark
        self._drops: int = 0
        self._peak_depth: int = 0
    
    def check(self) -> dict[str, int]:
        depth = self._queue.qsize()
        self._peak_depth = max(self._peak_depth, depth)
        return {
            "queue_depth": depth,
            "peak_depth": self._peak_depth,
            "drops": self._drops,
            "at_high_watermark": depth >= self._high_watermark,
        }
```

### 4.5 Task Management Discipline

Every background task must be tracked and cleaned up:

```python
class TaskTracker:
    """Tracks background tasks for clean shutdown."""
    
    def __init__(self):
        self._tasks: set[asyncio.Task] = set()
    
    def spawn(self, coro: Coroutine, *, name: str | None = None) -> asyncio.Task:
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task
    
    async def cancel_all(self, timeout: float = 5.0) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=timeout)
```

---

## 5. Resource Efficiency

### 5.1 Memory Usage Patterns

| Resource | Current Usage | Concern | Optimization |
|----------|--------------|---------|-------------|
| CLI subprocess | ~500MB | Shared singleton — correct | No change needed |
| Repaired tool ID tracking | OrderedDict, max 1000 | LRU is appropriate | No change needed |
| Model cache (disk) | Small JSON file | Disk I/O on cold start | Eliminate disk cache |
| Compiled regexes | Module-level | One-time cost | Already optimized |
| Event handler closures | Per-session | GC'd on disconnect | Ensure no reference cycles |
| Message conversion buffers | Per-request | Proportional to conversation | Use generators for large conversations |

#### Large Conversation Optimization

For conversations with 100+ messages, conversion creates a full copy of all messages. Use lazy conversion:

```python
def convert_messages_lazy(
    messages: Iterable[Message],
) -> Iterator[str]:
    """Lazily convert messages to SDK format. Avoids holding both formats in memory."""
    for msg in messages:
        yield _convert_single_message(msg)
```

**Impact**: Halves peak memory for large conversations (~100KB savings per 100 messages). Marginal for small conversations.

### 5.2 Connection Limits

The provider operates through a single CLI subprocess. There is no HTTP connection pooling to manage directly — the SDK handles that internally. However:

**Concurrent Session Limit**: The CLI subprocess may have internal limits on concurrent sessions. The provider should enforce its own limit:

```python
class SessionSemaphore:
    """Limits concurrent SDK sessions to prevent CLI overload."""
    
    def __init__(self, max_concurrent: int = 10):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active: int = 0
    
    async def acquire(self) -> None:
        await self._semaphore.acquire()
        self._active += 1
    
    def release(self) -> None:
        self._active -= 1
        self._semaphore.release()
    
    @property
    def active_sessions(self) -> int:
        return self._active
```

**Recommendation**: Default limit of 10 concurrent sessions per CLI subprocess. This prevents resource exhaustion while allowing parallel sub-agent requests.

### 5.3 Subprocess Management

The CLI subprocess is the most expensive resource. Management rules:

1. **Never spawn more than one**: Singleton pattern (already implemented)
2. **Detect zombie processes**: Background heartbeat detects dead subprocesses
3. **Restart with backoff**: If subprocess dies, restart with exponential backoff (1s, 2s, 4s, max 30s)
4. **Clean shutdown**: On provider cleanup, send `stop()` with timeout, then SIGTERM, then SIGKILL

```python
class SubprocessLifecycle:
    """Manages CLI subprocess with restart and clean shutdown."""
    
    RESTART_DELAYS = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
    
    async def ensure_alive(self) -> None:
        if self._process_healthy:
            return
        
        attempt = min(self._restart_count, len(self.RESTART_DELAYS) - 1)
        delay = self.RESTART_DELAYS[attempt]
        
        await asyncio.sleep(delay)
        await self._start_subprocess()
        self._restart_count += 1
    
    async def shutdown(self, timeout: float = 10.0) -> None:
        try:
            await asyncio.wait_for(self._client.stop(), timeout=timeout)
        except asyncio.TimeoutError:
            self._process.terminate()
            await asyncio.sleep(1.0)
            if self._process.returncode is None:
                self._process.kill()
```

---

## 6. Performance Testing

### 6.1 Benchmark Suite Design

Three tiers of performance tests:

#### Tier 1: Micro-Benchmarks (Unit Level)

Test individual operations in isolation with mocked SDK:

```python
# tests/benchmarks/test_conversion_perf.py

import pytest
from pytest_benchmark import fixture

def test_message_conversion_100_messages(benchmark):
    """Benchmark: convert 100 messages to SDK format."""
    messages = [make_test_message() for _ in range(100)]
    result = benchmark(convert_messages, messages)
    assert len(result) == 100

def test_tool_registration_50_tools(benchmark):
    """Benchmark: register 50 tools with exclusions."""
    tools = [make_test_tool(f"tool_{i}") for i in range(50)]
    result = benchmark(build_tool_set, tools, COPILOT_BUILTIN_TOOL_NAMES)
    assert len(result) == 50

def test_fake_tool_call_detection(benchmark):
    """Benchmark: regex-based fake tool call detection on large response."""
    response_text = "A" * 10000 + "<tool_used>" + "B" * 1000
    result = benchmark(detect_fake_tool_calls, response_text)
```

**Target thresholds**:
| Operation | Max p50 | Max p99 |
|-----------|---------|---------|
| Convert 100 messages | 2ms | 5ms |
| Build 50 tools | 5ms | 10ms |
| Fake tool call regex (10KB) | 0.5ms | 2ms |
| Model cache lookup | 0.01ms | 0.05ms |

#### Tier 2: Integration Benchmarks (Component Level)

Test the full `complete()` path with a mock SDK that returns instantly:

```python
# tests/benchmarks/test_provider_overhead.py

@pytest.mark.asyncio
async def test_complete_overhead(benchmark):
    """Measure total provider overhead excluding LLM time."""
    provider = create_provider_with_instant_mock_sdk()
    request = make_test_request(message_count=10, tool_count=5)
    
    async def run():
        return await provider.complete(request)
    
    result = benchmark.pedantic(run, rounds=50, warmup_rounds=5)
    
    # Provider overhead should be <50ms when SDK returns instantly
    assert benchmark.stats.stats.mean < 0.050  # 50ms

@pytest.mark.asyncio
async def test_streaming_overhead_per_chunk():
    """Measure per-chunk overhead in the streaming pipeline."""
    provider = create_provider_with_mock_stream(chunk_count=100)
    
    start = time.monotonic()
    chunks = []
    async for chunk in provider.stream_complete(make_test_request()):
        chunks.append(chunk)
    elapsed = time.monotonic() - start
    
    # 100 chunks should take <10ms of provider overhead
    assert elapsed < 0.010
    assert len(chunks) == 100
```

**Target thresholds**:
| Operation | Max p50 | Max p99 |
|-----------|---------|---------|
| complete() overhead (mock SDK) | 30ms | 50ms |
| stream chunk processing (100 chunks) | 5ms | 15ms |
| Time-to-first-token overhead | 20ms | 40ms |
| Session create + disconnect (mock) | 10ms | 30ms |

#### Tier 3: Load Tests (System Level)

Test concurrent request handling with a mock or real SDK:

```python
# tests/benchmarks/test_concurrent_load.py

@pytest.mark.asyncio
async def test_concurrent_requests_10():
    """10 concurrent complete() calls should not degrade individual latency."""
    provider = create_provider_with_slow_mock_sdk(delay=0.1)  # 100ms mock LLM
    
    requests = [make_test_request() for _ in range(10)]
    
    start = time.monotonic()
    results = await asyncio.gather(
        *[provider.complete(r) for r in requests]
    )
    elapsed = time.monotonic() - start
    
    # All 10 should complete in ~100ms (parallelized), not 1000ms (serialized)
    assert elapsed < 0.300  # 300ms with overhead
    assert all(r is not None for r in results)

@pytest.mark.asyncio
async def test_session_semaphore_prevents_overload():
    """More than max_concurrent requests should queue, not fail."""
    provider = create_provider_with_session_limit(max_concurrent=5)
    
    # Launch 20 requests
    tasks = [asyncio.create_task(provider.complete(make_test_request())) for _ in range(20)]
    
    # All should eventually complete
    results = await asyncio.gather(*tasks)
    assert len(results) == 20
```

### 6.2 Performance Regression Detection

#### Automated CI Integration

```yaml
# .github/workflows/perf.yml (conceptual)
perf-benchmarks:
  runs-on: ubuntu-latest
  steps:
    - run: pytest tests/benchmarks/ --benchmark-json=benchmark.json
    - run: python scripts/check_perf_regression.py benchmark.json --threshold 20%
```

**Regression detection script logic:**
1. Compare current benchmark results against baseline (stored in repo)
2. Flag if any p50 regresses by >20% or any p99 regresses by >50%
3. Baseline is updated manually after intentional changes

#### Key Metrics to Track

```python
PERF_METRICS = {
    "provider_overhead_p50_ms": 30,     # Target: <30ms p50
    "provider_overhead_p99_ms": 50,     # Target: <50ms p99
    "ttft_overhead_p50_ms": 20,         # Time-to-first-token overhead
    "message_convert_per_100_ms": 2,    # Message conversion rate
    "stream_chunk_overhead_us": 50,     # Per-chunk overhead in microseconds
    "memory_peak_mb": 50,              # Peak memory during load test
    "concurrent_10_total_ms": 300,     # 10 concurrent requests total time
}
```

### 6.3 Observability Integration

Performance metrics should be emittable as provider-specific events:

```python
# Events to register for performance observability
PERF_EVENTS = [
    "github-copilot:perf:ttft",           # Time-to-first-token
    "github-copilot:perf:overhead",       # Total provider overhead
    "github-copilot:perf:session_create", # Session creation time
    "github-copilot:perf:queue_depth",    # Streaming queue depth
]
```

These events allow hooks to collect performance data without modifying the provider:

```python
# Example: emit timing at end of complete()
await self._hooks.emit("github-copilot:perf:overhead", {
    "session_id": self._session_id,
    "overhead_ms": (time.monotonic() - start) * 1000,
    "model": model_id,
    "message_count": len(request.messages),
})
```

---

## 7. Optimization Roadmap

### Phase 1: Quick Wins (0–2 days)

| Optimization | Estimated Impact | Effort |
|-------------|-----------------|--------|
| Fire-and-forget session disconnect | -20–80ms per request | Low |
| Pre-build tool set cache | -10–50ms per request | Low |
| Cache sorted built-in exclusion list | -1ms per request | Trivial |
| Pre-compile all regexes at module level | Already done | N/A |

### Phase 2: Architecture Changes (3–5 days)

| Optimization | Estimated Impact | Effort |
|-------------|-----------------|--------|
| Background heartbeat (replace per-request health check) | -30–100ms per request | Medium |
| Async event dispatch queue | -5–20ms per event | Medium |
| Eliminate disk cache tier | -5ms cold start, reduce complexity | Medium |
| Session semaphore for concurrency control | Prevents degradation under load | Low |

### Phase 3: Advanced Optimizations (5–10 days)

| Optimization | Estimated Impact | Effort |
|-------------|-----------------|--------|
| Streaming pipeline with zero-copy chunks | -1–2ms per chunk | High |
| Lazy message conversion for large conversations | -50% peak memory for 100+ messages | Medium |
| Full benchmark suite with CI regression detection | Prevents future regressions | High |
| Performance event emission for observability | Enables production monitoring | Medium |

### Phase 4: Measurement & Validation

| Activity | Purpose |
|----------|---------|
| Run Tier 1 benchmarks against current code | Establish baseline |
| Implement Phase 1 optimizations | Quick wins |
| Re-run benchmarks, compare | Validate improvement |
| Implement Phase 2 optimizations | Architecture changes |
| Run Tier 2 + Tier 3 benchmarks | Validate under load |
| Establish CI baseline | Prevent regressions |

---

## 8. Anti-Patterns to Avoid

1. **Session pooling**: The "Deny + Destroy" pattern makes session reuse impossible. Don't try to pool sessions — it will break tool capture.

2. **Speculative session pre-creation**: Creating sessions before `complete()` is called wastes resources for requests that may never come.

3. **Response caching**: LLM responses are non-deterministic. Caching them is semantically incorrect.

4. **Connection multiplexing**: The CLI subprocess handles one JSON-RPC stream. Don't try to multiplex requests on a single session.

5. **Synchronous fallbacks**: Never use `asyncio.run_in_executor()` for operations that should be async. The entire provider should be async-native.

6. **Premature optimization of message conversion**: At <5ms for typical conversations, message conversion is not the bottleneck. Optimize session lifecycle and event dispatch first.

---

## 9. Summary

The performance architecture targets a **4–10x reduction** in provider overhead (from ~200–475ms to <50ms) through four key strategies:

1. **Eliminate per-request health checks** → Background heartbeat (-30–100ms)
2. **Fire-and-forget session cleanup** → Async disconnect (-20–80ms)
3. **Cache immutable data** → Tool sets, model capabilities, config templates (-10–50ms)
4. **Async event pipeline** → Non-blocking event dispatch (-5–20ms/event)

The optimization roadmap is phased: quick wins first (Phase 1, 0–2 days), architecture changes second (Phase 2, 3–5 days), advanced optimizations third (Phase 3, 5–10 days). Every optimization is validated against the benchmark suite, and regressions are caught in CI.

**The fastest code is code that doesn't run.** Every eliminated health check, every cached tool set, every fire-and-forget disconnect removes code from the critical path. The provider's job is translation — everything else is overhead to minimize.
