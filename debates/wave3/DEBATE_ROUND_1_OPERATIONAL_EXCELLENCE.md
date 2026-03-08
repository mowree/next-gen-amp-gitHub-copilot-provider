# Wave 3, Agent 27: Operational Excellence for GitHub Copilot Provider

**Agent Role**: Operational Excellence Expert  
**Date**: 2026-03-08  
**Subject**: Deployment, monitoring, incident response, capacity planning, reliability engineering, and operations automation for `amplifier-module-provider-github-copilot` v1.0.4

---

## Executive Summary

This provider is not a typical web service. It is a **Python module** loaded into an Amplifier session that manages a **CLI subprocess** (~500MB RSS) communicating over **JSON-RPC**. Operational excellence here means: keeping the subprocess alive, detecting when it silently degrades, managing the ~120–475ms per-request overhead, and ensuring the "Deny + Destroy" pattern doesn't spiral into the documented 305-turn loop bug. Every operational practice in this guide is informed by the specific failure modes of this architecture — subprocess death, SDK event ordering changes, rate limit cascades, and model cache staleness.

---

## 1. Deployment Patterns

### 1.1 How This Provider Is Deployed

The provider is a Python package installed via pip and loaded by the Amplifier kernel at session initialization time:

```
pip install amplifier-module-provider-github-copilot
```

The kernel's Mount Plan specifies the provider, which triggers `mount()` in `__init__.py`. This function:
1. Acquires a process-level singleton lock
2. Spawns (or reuses) the Copilot CLI subprocess
3. Performs a health check ping
4. Registers the provider at the `"providers"` mount point
5. Returns a cleanup callable

**Deployment is not "deploy a server" — it's "ensure this package is installed and the CLI binary is discoverable."**

### 1.2 Container Considerations

| Concern | Requirement | Rationale |
|---------|------------|-----------|
| Base image | Python 3.10+ with Node.js runtime | CLI subprocess requires Node.js |
| Binary discovery | CLI binary at known path or on `$PATH` | `_platform.py` searches `shutil.which()` then platform-specific paths |
| File permissions | `_permissions.py` calls `ensure_executable()` | CLI binary must be executable; container may strip execute bits |
| Writable cache dir | `~/.amplifier/cache/` must be writable | `model_cache.py` uses atomic writes (`tempfile.mkstemp` + `os.fsync` + `Path.replace`) |
| Memory budget | **Minimum 1GB per provider instance** | CLI subprocess alone is ~500MB; Python runtime + model cache + conversation buffers add ~200–400MB |
| Tmpdir | `/tmp` must be writable and on same filesystem as cache dir | Atomic file replace requires same-filesystem move |
| PID namespace | Standard (not shared) | Singleton pattern uses process-level lock; shared PID namespaces could cause lock contention across containers |

**Container Health Check:**

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "from amplifier_module_provider_github_copilot.client import CopilotClientWrapper; print('ok')" || exit 1
```

This validates the import chain but NOT the CLI subprocess. A deeper health check requires the Amplifier session to be running.

### 1.3 CLI Subprocess Management

The CLI subprocess is the single most critical operational dependency. It is:

- **Singleton**: One subprocess per Python process, shared across all mounted providers (`__init__.py:125-210`)
- **Reference-counted**: `_shared_client_refcount` tracks active users; subprocess is stopped when refcount hits zero
- **Health-checked per request**: `client.py:182-207` pings before returning cached client (30–100ms overhead)
- **Auto-restartable**: If health check fails, client is recreated

**Operational Risk**: If the CLI subprocess dies silently (segfault, OOM kill), the health check ping will timeout after `CLIENT_HEALTH_CHECK_TIMEOUT = 5.0s`, triggering a restart. During this window, all `complete()` calls block waiting for the lock.

**Mitigation**: Background heartbeat monitoring (proposed in Wave 2 Performance Architecture) replaces per-request pings with a continuous 15-second health check loop, reducing detection latency from "next request" to "≤15 seconds."

### 1.4 Environment Variable Precedence

Operators must understand the token resolution order:

```
1. config["github_token"]     ← Mount Plan config
2. COPILOT_GITHUB_TOKEN       ← Provider-specific env var
3. GH_TOKEN                   ← GitHub CLI standard
4. GITHUB_TOKEN               ← GitHub Actions standard
5. SDK stored OAuth creds     ← Persisted from `gh auth login`
```

**Operational Practice**: In production containers, always set `COPILOT_GITHUB_TOKEN` explicitly. Do not rely on fallback resolution — it makes debugging authentication failures unnecessarily complex.

---

## 2. Monitoring Strategy

### 2.1 What to Monitor in Production

Monitoring this provider requires understanding its three layers: the Python module, the CLI subprocess, and the remote Copilot API.

#### Layer 1: Python Module Health

| Metric | Type | Source | Why It Matters |
|--------|------|--------|---------------|
| `copilot.provider.mount_status` | Gauge (0/1) | `mount()` return value | Provider failed to initialize |
| `copilot.provider.complete_duration_ms` | Histogram | `provider.py:complete()` | Total request time including overhead |
| `copilot.provider.overhead_ms` | Histogram | Computed: total - LLM time | Provider-specific overhead (target: <50ms) |
| `copilot.provider.error_rate` | Counter | Error translation layer | Errors per error type |
| `copilot.provider.fake_tool_call_detections` | Counter | `provider.py:1076-1138` | Prompt format causing model to emit text tool calls |
| `copilot.provider.missing_tool_result_repairs` | Counter | `provider.py:1596-1657` | Conversation history corruption frequency |
| `copilot.provider.repaired_tool_ids_size` | Gauge | `OrderedDict` length | Approaching MAX_REPAIRED_TOOL_IDS (1000) = memory pressure |

#### Layer 2: CLI Subprocess Health

| Metric | Type | Source | Why It Matters |
|--------|------|--------|---------------|
| `copilot.cli.process_alive` | Gauge (0/1) | `client.py` health check | Subprocess died |
| `copilot.cli.health_check_duration_ms` | Histogram | `client.py:196-197` | Ping latency trend |
| `copilot.cli.restart_count` | Counter | Client recreation events | Frequent restarts = unstable subprocess |
| `copilot.cli.memory_rss_bytes` | Gauge | `/proc/{pid}/status` | Memory leak detection (baseline: ~500MB) |
| `copilot.cli.session_create_duration_ms` | Histogram | `client.py:580` | SDK session creation latency |
| `copilot.cli.session_disconnect_duration_ms` | Histogram | `client.py:600` | Session teardown latency |
| `copilot.cli.active_sessions` | Gauge | `client.list_sessions()` | Session leak detection (should be 0 or 1) |

#### Layer 3: Copilot API Health

| Metric | Type | Source | Why It Matters |
|--------|------|--------|---------------|
| `copilot.api.rate_limit_hits` | Counter | `CopilotRateLimitError` | Approaching API limits |
| `copilot.api.rate_limit_retry_after_seconds` | Histogram | `retry_after` extraction | How long we're being throttled |
| `copilot.api.auth_failures` | Counter | `CopilotAuthenticationError` | Token expired/invalid |
| `copilot.api.model_not_found` | Counter | `CopilotModelNotFoundError` | Model deprecation/removal |
| `copilot.api.ttfb_ms` | Histogram | First streaming event timestamp | API responsiveness |
| `copilot.api.content_filter_blocks` | Counter | Content filter detection | Content policy violations |

### 2.2 Alerting Thresholds

| Alert | Condition | Severity | Response |
|-------|-----------|----------|----------|
| **CLI Process Dead** | `cli.process_alive == 0` for > 30s | P1 Critical | Auto-restart; page if restart fails |
| **CLI Restart Storm** | `cli.restart_count` > 3 in 5min | P1 Critical | Investigate OOM/crash; consider scaling |
| **High Error Rate** | `error_rate` > 10% over 5min window | P2 High | Check API status; verify auth tokens |
| **Rate Limit Cascade** | `rate_limit_hits` > 10 in 1min | P2 High | Reduce concurrency; check account limits |
| **Auth Failure** | Any `auth_failures` > 0 | P2 High | Token refresh; check OAuth status |
| **High Overhead** | p99 `overhead_ms` > 200ms | P3 Medium | Profile session creation; check health check latency |
| **Session Leak** | `active_sessions` > 5 for > 2min | P3 Medium | Disconnect/destroy stale sessions |
| **Memory Growth** | `cli.memory_rss_bytes` > 1GB | P3 Medium | Potential memory leak in CLI subprocess |
| **Fake Tool Call Spike** | `fake_tool_call_detections` > 20% of requests | P4 Low | Model behavior change; review prompt format |
| **Model Cache Stale** | Cache age > `CACHE_STALE_DAYS` (30) | P4 Low | Trigger `list_models()` refresh |
| **Circuit Breaker Trips** | `SDK_MAX_TURNS` exceeded | P3 Medium | Possible 305-turn loop regression |

### 2.3 Dashboard Design

**Dashboard 1: Provider Overview (default view)**

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Copilot Provider - Operational Status               │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ CLI Status   │ Error Rate   │ Avg Overhead │ Active Sessions│
│ 🟢 HEALTHY   │ 0.3%         │ 47ms         │ 1              │
├──────────────┴──────────────┴──────────────┴────────────────┤
│                                                             │
│  Request Duration (p50/p95/p99)     [time-series graph]     │
│  Provider Overhead (p50/p95/p99)    [time-series graph]     │
│  Error Rate by Type                 [stacked area chart]    │
│  Rate Limit Events                  [event markers]         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  CLI Subprocess                                             │
│  ┌─────────────┬──────────────┬─────────────┐              │
│  │ RSS Memory  │ Restart Cnt  │ Health Ping  │              │
│  │ 487MB       │ 0 (24h)      │ 12ms avg     │              │
│  └─────────────┴──────────────┴─────────────┘              │
│  Memory Trend [gauge + 24h sparkline]                       │
│  Health Check Latency [time-series]                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  SDK Driver                                                 │
│  Circuit Breaker Trips: 0 (24h)                             │
│  Avg Turns per Request: 1.2                                 │
│  Tool Capture Success Rate: 99.8%                           │
│  Fake Tool Call Detection Rate: 0.4%                        │
└─────────────────────────────────────────────────────────────┘
```

**Dashboard 2: Rate Limit & API Health**

- Rate limit events over time by model
- `retry_after` distribution
- Auth token refresh events
- API TTFB trends per model
- Error type breakdown (network vs auth vs rate limit vs model)

**Dashboard 3: Session Lifecycle**

- Session creation/teardown waterfall (per request)
- Session duration histogram
- Orphaned session count over time
- Tool registration count per session
- Event count per session

---

## 3. Incident Response

### 3.1 When Things Break

The most likely incidents, ordered by frequency based on the architecture:

| Incident | Probability | Impact | Detection Time |
|----------|------------|--------|---------------|
| Rate limiting | High | Degraded (slower responses) | Immediate (error type) |
| CLI subprocess crash | Medium | Full outage until restart (~5s) | ≤5s (health check timeout) |
| Auth token expiration | Medium | Full outage until refresh | Immediate (error type) |
| SDK behavioral change | Low | Unpredictable (tool capture failure, loops) | Minutes to hours |
| 305-turn loop regression | Low | Resource exhaustion, high cost | Circuit breaker trips |
| Model deprecation | Low | Specific model unavailable | `ModelNotFoundError` |

### 3.2 Runbook: CLI Subprocess Crash

```
TRIGGER: copilot.cli.process_alive == 0 AND auto-restart failed

1. ASSESS
   - Check system OOM killer: `dmesg | grep -i oom | tail -20`
   - Check CLI process exit code: logged by client.py on failure
   - Check available memory: `free -h`
   - Check disk space (for cache writes): `df -h /tmp ~/.amplifier`

2. MITIGATE
   - If OOM: Increase container memory limit to 2GB minimum
   - If disk full: Clear model cache: `rm ~/.amplifier/cache/github-copilot-models.json`
   - If repeated crash: Check CLI binary integrity: `sha256sum $(which copilot-cli)`
   - Manual restart: The next `complete()` call will auto-recreate the client

3. VERIFY
   - Monitor copilot.cli.process_alive returns to 1
   - Monitor copilot.cli.health_check_duration_ms is normal (<30ms)
   - Send test completion request

4. POSTMORTEM
   - Collect: CLI stderr output, system logs, memory profile
   - Check: Was SDK recently upgraded? New built-in tools added?
   - Update: If new failure mode, add to this runbook
```

### 3.3 Runbook: 305-Turn Loop Regression

```
TRIGGER: copilot.sdk_driver.circuit_breaker_trips > 0

1. ASSESS
   - This means the SDK's denial retry loop was triggered again
   - Check SDK version: was it upgraded past 0.2.0?
   - Check SDK assumption tests: do they still pass?
   - Check SDK_MAX_TURNS_DEFAULT (currently 3) and SDK_MAX_TURNS_HARD_LIMIT (10)

2. MITIGATE
   - Circuit breaker already stopped the loop (this is the designed safety net)
   - If frequent: Lower SDK_MAX_TURNS_DEFAULT to 1 (first-turn-only capture)
   - If SDK was upgraded: Roll back to last known-good version
   - If all models affected: Check tool_capture.py deny hook behavior

3. VERIFY
   - Run sdk_assumptions/test_deny_hook.py
   - Run sdk_assumptions/test_event_ordering.py
   - Confirm circuit breaker trips return to 0

4. ROOT CAUSE
   - Most likely: SDK changed denial_behavior from RETRY
   - Check: Does SDK now offer official capture-only mode? (mentioned in tool_capture.py:33-36)
   - If so: Migrate away from Deny + Destroy pattern entirely
```

### 3.4 Runbook: Rate Limit Cascade

```
TRIGGER: copilot.api.rate_limit_hits > 10 in 1 minute

1. ASSESS
   - Check which model(s) are being rate-limited
   - Check retry_after values — are they increasing? (exponential = account-level)
   - Check if multiple Amplifier sessions are competing for the same token

2. MITIGATE
   - If retry_after > 60s: This is account-level limiting, not transient
     → Reduce concurrent requests (lower parallelism in orchestrator)
     → Switch to a different model temporarily
   - If retry_after < 10s: Transient burst
     → Existing retry_with_backoff handles this (max_retries=3, max_delay=60s)
   - If fail-fast triggered (retry_after > max_delay):
     → Request is marked non-retryable
     → User gets immediate error — this is correct behavior

3. VERIFY
   - Monitor rate_limit_hits trending downward
   - Monitor successful requests resuming
   - Check: Did we hit GitHub Copilot's API quota? Contact GitHub support if persistent.

4. PREVENTION
   - Implement request queuing at orchestrator level
   - Add rate limit awareness to provider selection (prefer non-limited providers)
   - Monitor daily token consumption trends
```

### 3.5 On-Call Considerations for AI-Maintained Systems

This provider is designed to be maintained by AI agents. On-call has unique characteristics:

| Traditional On-Call | AI-Maintained On-Call |
|--------------------|----------------------|
| Human reads alerts at 3am | AI agent processes structured alert payload |
| Human reads logs, forms hypothesis | AI reads structured events, traces span trees |
| Human writes hotfix, tests manually | AI generates fix, runs full test suite |
| Human decides to rollback | AI follows rollback decision tree (see Self-Healing Design) |
| Human writes postmortem | AI generates structured adaptation record |

**When AI On-Call Escalates to Humans:**
- Security-related failures (auth model changes)
- Repeated fix-revert cycles (>2 attempts)
- Blast radius > 30% of codebase
- New abstractions required (no mappable replacement)
- Performance regression > 50% with no clear cause

---

## 4. Capacity Planning

### 4.1 Resource Requirements

**Per-Instance Resource Profile:**

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| Memory | 1 GB | 2 GB | CLI subprocess: ~500MB; Python: ~200MB; headroom for spikes |
| CPU | 0.5 vCPU | 1 vCPU | Mostly I/O-bound; CPU for message conversion + regex |
| Disk | 100 MB | 500 MB | CLI binary + model cache + temp files for atomic writes |
| Network | Stable outbound HTTPS | Low-latency outbound | Copilot API is the bottleneck, not bandwidth |
| File descriptors | 256 | 1024 | CLI subprocess + JSON-RPC pipe + event listeners |

**Memory Breakdown:**

```
CLI subprocess (Node.js)          ~500 MB (measured baseline)
Python interpreter + modules       ~80 MB
Provider module loaded             ~20 MB
Model cache (in-memory)            ~5 MB
Conversation buffer (per request)  ~1-50 MB (proportional to context window)
Event handling buffers             ~10 MB
LRU tracking (OrderedDict)        ~1 MB (max 1000 entries)
────────────────────────────────────────
Total baseline                     ~620 MB
Peak (large conversation)          ~900 MB
```

### 4.2 Scaling Considerations

**This provider does NOT scale horizontally within a single process.** The singleton pattern (`__init__.py:125-210`) ensures exactly one CLI subprocess per Python process. Multiple concurrent `complete()` calls share this subprocess via SDK sessions.

**Scaling Strategy:**

| Dimension | Approach | Limit |
|-----------|----------|-------|
| Concurrent requests | SDK session multiplexing (ephemeral per request) | CLI subprocess throughput (~10-50 concurrent sessions) |
| Multiple users | Multiple Amplifier processes, each with own CLI singleton | Memory: ~1GB per process |
| Multiple models | Same CLI subprocess, different model per session | No additional overhead |
| Geographic distribution | Deploy closer to GitHub API endpoints | Latency-sensitive; API is US-centric |

**Scaling Bottleneck**: The CLI subprocess is the chokepoint. If you need more than ~50 concurrent completions, you need multiple Python processes (each spawning its own CLI). This is inherently memory-expensive.

**Cost Scaling:**

```
1 concurrent user:     ~1 GB memory, ~0.5 vCPU
5 concurrent users:    ~1.5 GB memory, ~1 vCPU (shared CLI)
10 concurrent users:   ~2 GB memory, ~1.5 vCPU (shared CLI, contention starts)
50 concurrent users:   Multiple processes needed → ~5 GB memory minimum
```

### 4.3 Connection Pooling

There is no HTTP connection pooling in the traditional sense. The communication path is:

```
Provider → JSON-RPC over stdio → CLI subprocess → HTTPS → Copilot API
```

The CLI subprocess manages its own HTTPS connections to the Copilot API. The provider has no control over this. What the provider CAN pool:

- **CLI client instance**: Already pooled (singleton pattern)
- **SDK sessions**: Currently ephemeral (create per request, destroy after). Session pooling is proposed in Wave 2 Performance Architecture but adds complexity around state isolation.
- **Model metadata**: Cached across requests (4-tier fallback: memory → disk → bundled → defaults)

**Operational Practice**: Do NOT attempt to pool SDK sessions unless you can guarantee state isolation. The "Deny + Destroy" pattern relies on each session being fresh. A leaked session state could cause tool capture failures.

---

## 5. Reliability Engineering

### 5.1 SLO/SLI Definitions

**SLI 1: Availability**
- **Definition**: Percentage of `complete()` calls that return a valid `ChatResponse` (not an error)
- **Measurement**: `1 - (error_count / total_requests)` over 5-minute windows
- **Excludes**: Rate limit errors with `retry_after` (these are expected throttling, not failures)
- **Target SLO**: 99.5% availability

**SLI 2: Latency (Provider Overhead)**
- **Definition**: p99 of time spent in provider code (excluding LLM inference time)
- **Measurement**: `complete_duration - llm_inference_duration`
- **Target SLO**: p99 < 200ms (current); p99 < 50ms (target after optimization)

**SLI 3: Correctness**
- **Definition**: Percentage of responses where tool calls are correctly captured and returned
- **Measurement**: `1 - (fake_tool_call_detections + missing_tool_result_repairs) / total_requests`
- **Target SLO**: 99.9% correct tool capture

**SLI 4: CLI Subprocess Uptime**
- **Definition**: Percentage of time the CLI subprocess is alive and responding to pings
- **Measurement**: Background heartbeat success rate
- **Target SLO**: 99.9% uptime (allows ~8.6 seconds downtime per day for restarts)

### 5.2 Error Budgets

| SLO | Target | Error Budget (per 30 days) | Burn Rate Alert |
|-----|--------|---------------------------|----------------|
| Availability 99.5% | 0.5% error budget | ~2.16 hours of errors | Alert at 2x burn rate (1% errors over 1 hour) |
| Latency p99 < 200ms | 1% of requests can exceed | ~14,400 requests per 1M | Alert at 3x burn rate |
| Correctness 99.9% | 0.1% tool capture failures | ~1,440 per 1M requests | Alert at any sustained failures |
| CLI Uptime 99.9% | 0.1% downtime | ~43 minutes per month | Alert at 2x burn rate |

**Error Budget Policy:**
- If error budget is < 25% remaining: Freeze non-critical changes; focus on reliability
- If error budget is exhausted: Roll back last change; conduct incident review
- Rate limit errors do NOT consume availability error budget (they are external)
- Circuit breaker trips DO consume correctness error budget

### 5.3 Reliability Testing

**Chaos Engineering Scenarios:**

| Scenario | How to Simulate | What It Tests |
|----------|----------------|---------------|
| CLI subprocess crash | `kill -9 $(pgrep copilot-cli)` | Auto-restart, lock release, request queuing |
| CLI subprocess hang | `kill -STOP $(pgrep copilot-cli)` | Health check timeout detection |
| Network partition | `iptables -A OUTPUT -d api.github.com -j DROP` | Connection timeout → error translation → retry |
| Rate limit burst | Mock SDK to return 429 for 30 seconds | Retry backoff, fail-fast for long retry_after |
| Model deprecation | Mock SDK to return "model not found" | Error translation, fallback model selection |
| Slow API response | Add 30s delay to mock SDK | Timeout handling, circuit breaker |
| OOM pressure | `stress --vm 1 --vm-bytes 1G` | CLI process survival, graceful degradation |
| SDK event order change | Mock different event ordering | Tool capture resilience |
| Cache corruption | Corrupt `github-copilot-models.json` | Cache fallback to bundled → defaults |
| Concurrent mount stress | 10 simultaneous `mount()` calls | Singleton lock, reference counting |

**Regression Testing:**
- The SDK assumption tests (`tests/sdk_assumptions/`) are the primary reliability regression suite
- Must pass before any SDK upgrade (pinned at `>=0.1.32,<0.2.0`)
- Four categories: deny hook behavior, event ordering, session lifecycle, tool registration

---

## 6. Operations Automation

### 6.1 Automatable Operations

| Operation | Automation Level | Trigger | Implementation |
|-----------|-----------------|---------|----------------|
| CLI subprocess restart | Fully automated | Health check failure | Already implemented in `client.py` |
| Model cache refresh | Fully automated | Cache age > 30 days | Trigger `list_models()` on stale check |
| Auth token refresh | Fully automated | `TokenExpiredError` | SDK handles OAuth refresh flow |
| SDK version monitoring | Fully automated | Nightly cron | Check PyPI for new `github-copilot-sdk` versions |
| SDK assumption test run | Fully automated | On dependency update PR | CI pipeline (see CI/CD Architecture) |
| Rate limit backoff | Fully automated | 429 response | `retry_with_backoff()` already implemented |
| Session leak cleanup | Semi-automated | `active_sessions > 5` alert | Call `client.list_sessions()` → disconnect stale |
| SDK upgrade (patch) | Semi-automated | New patch version detected | Auto-PR → canary tests → merge if green |
| SDK upgrade (minor) | Human-gated | New minor version detected | Auto-PR → extended validation → human review |
| Incident postmortem | AI-assisted | After any P1/P2 incident | AI generates structured record from telemetry |

### 6.2 Self-Healing Operations

The provider already implements several self-healing patterns:

**Pattern 1: Dead Subprocess Recovery**
```
CLI subprocess dies → health check ping fails → 
  singleton lock acquired → new CopilotClient created → 
  client.start() → health check passes → requests resume
```
Recovery time: ~3-8 seconds

**Pattern 2: Circuit Breaker (SDK Driver)**
```
SDK denial loop starts → turn count exceeds SDK_MAX_TURNS_DEFAULT (3) → 
  CircuitBreaker trips → session aborted → 
  captured tools returned (if any) → error raised
```
Prevents: Runaway token consumption, 305-turn loop

**Pattern 3: Missing Tool Result Repair**
```
Conversation history has tool_call without matching tool_result → 
  repair detected during message conversion → 
  synthetic error result injected → 
  tool_call ID tracked in LRU (max 1000) to prevent infinite loops
```
Prevents: SDK/model confusion from orphaned tool calls

**Pattern 4: Tiered Model Metadata Fallback**
```
In-memory cache miss → disk cache miss → 
  bundled hardcoded limits (21 models) → 
  universal defaults (200000/32000)
```
Prevents: Model metadata unavailability from blocking requests

### 6.3 Proposed Self-Healing Additions

**Addition 1: Proactive Session Garbage Collection**
```python
# Run every 60 seconds in background
async def gc_stale_sessions():
    sessions = await client.list_sessions()
    for session in sessions:
        if session.age > SESSION_MAX_AGE:
            await session.disconnect()
            emit("copilot:session.gc", {"session_id": session.id})
```

**Addition 2: Memory Pressure Response**
```python
# Monitor CLI process RSS; restart if exceeding threshold
async def memory_watchdog(pid: int, threshold_mb: int = 900):
    rss = get_process_rss(pid)
    if rss > threshold_mb * 1024 * 1024:
        logger.warning(f"CLI RSS {rss}MB exceeds {threshold_mb}MB, restarting")
        await restart_cli_client()
        emit("copilot:cli.memory_restart", {"rss_mb": rss})
```

**Addition 3: Token Proactive Refresh**
```python
# Refresh token before it expires, not after
async def proactive_token_refresh():
    auth_status = await client.get_auth_status()
    if auth_status.expires_in < TOKEN_REFRESH_BUFFER:
        await client.refresh_auth()
        emit("copilot:auth.proactive_refresh", {})
```

### 6.4 Maintenance Windows

This provider does not require traditional maintenance windows because:
1. The CLI subprocess can be restarted transparently between requests
2. Model cache is updated atomically (no read-during-write corruption)
3. SDK upgrades are tested via canary before deployment

**When maintenance IS needed:**
- **Major SDK upgrades** (0.x.0 → 0.y.0): Deploy during low-traffic period; monitor for 30 minutes
- **CLI binary updates**: Replace binary, kill old subprocess, let auto-restart pick up new version
- **Cache schema changes**: Delete old cache file; fallback tiers handle the gap automatically

---

## 7. Operational Checklist

### Pre-Deployment
- [ ] CLI binary is discoverable at expected path
- [ ] `COPILOT_GITHUB_TOKEN` is set and valid
- [ ] Cache directory (`~/.amplifier/cache/`) is writable
- [ ] Container has ≥1GB memory allocated
- [ ] SDK version is within pinned range (`>=0.1.32,<0.2.0`)
- [ ] SDK assumption tests pass
- [ ] Health check endpoint responds

### Post-Deployment (First 30 minutes)
- [ ] `copilot.cli.process_alive == 1`
- [ ] `copilot.provider.mount_status == 1`
- [ ] First `complete()` call succeeds
- [ ] Error rate < 1%
- [ ] Provider overhead p99 < 200ms
- [ ] No circuit breaker trips
- [ ] Model cache populated (either from API or disk)

### Weekly Operations
- [ ] Review CLI subprocess restart count (should be 0-2)
- [ ] Review rate limit event frequency and trends
- [ ] Check for new SDK versions (automated)
- [ ] Verify model cache freshness (< 30 days)
- [ ] Review fake tool call detection rate trends
- [ ] Run full SDK assumption test suite

### Monthly Operations
- [ ] Test against SDK pre-release/beta versions
- [ ] Full compatibility matrix verification
- [ ] Review error budget consumption
- [ ] Update BUNDLED_MODEL_LIMITS if new models discovered
- [ ] Review and update alerting thresholds based on trends
- [ ] Capacity planning review: memory trends, request volume trends

---

## 8. Key Operational Insights

### The Singleton Is Both Savior and Risk

The process-level singleton for the CLI client prevents catastrophic memory usage (N subprocess × 500MB) but creates a single point of failure. If the singleton lock deadlocks (`asyncio.Lock` is event-loop-bound), ALL providers in the process are blocked. The `CLIENT_INIT_LOCK_TIMEOUT = 30.0` is the safety valve — if lock acquisition fails, the request errors out rather than hanging forever.

**Operational Practice**: Monitor lock acquisition times. If they trend upward, it indicates contention from concurrent requests, not a deadlock.

### The "Deny + Destroy" Pattern Is Operationally Fragile

The entire tool capture mechanism depends on undocumented SDK behavior: event ordering (ASSISTANT_MESSAGE before preToolUse), denial causing retry, and session disconnect stopping the retry loop. Any SDK update that changes these behaviors will silently break tool capture.

**Operational Practice**: The SDK assumption tests are NOT optional. They are the only early warning system for this fragility. Run them nightly, not just on upgrades.

### Rate Limits Are External But Your Problem

The provider's retry logic (`max_retries=3`, `initial_delay=1.0s`, `max_delay=60.0s`) handles transient rate limits well. But account-level rate limits (indicated by long `retry_after` values) require operational response: reduce concurrency, switch models, or contact GitHub. The fail-fast behavior (`retry_after > max_delay → non_retryable`) is correct — don't waste time retrying what won't succeed.

### Model Cache Is Your Resilience Buffer

The 4-tier fallback (memory → disk → bundled → defaults) means the provider can operate for 30+ days without a successful `list_models()` API call. The bundled limits cover 21 models. The operational risk is model addition: new Copilot models not in `BUNDLED_MODEL_LIMITS` will get default values (200000/32000), which may be incorrect but functional.

**Operational Practice**: After GitHub announces new models, update `BUNDLED_MODEL_LIMITS` proactively rather than relying on the API cache.

---

*The best operations are invisible. When this provider runs well, nobody notices it's there — they just see fast, reliable LLM responses. Operational excellence means keeping it invisible.*
