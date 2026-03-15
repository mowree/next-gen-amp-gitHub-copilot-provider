# LINUX KERNEL LESSONS: Mechanism in Code, Policy in Config

*Final Round — The council cargo-culted "mechanism vs policy" but didn't actually APPLY it.*

---

## The Numbers That Should Embarrass Us

| System | Total Lines | Core/Kernel | Ratio |
|--------|-------------|-------------|-------|
| Linux | ~30,000,000 | ~300,000 | 1:100 |
| Amplifier | ~15,000 | ~2,600 | 1:6 |
| This Provider | 5,200 | ??? | ??? |

Linux maintains a 1:100 ratio between kernel mechanism and everything else (drivers, modules, configs, build scripts). Amplifier maintains roughly 1:6. This provider? It's ALL kernel. 5,200 lines of mechanism and policy fused together, inseparable, hardcoded.

The Linux kernel doesn't contain retry counts. It doesn't hardcode timeout values. It doesn't embed device-specific quirks in the scheduler. Those are POLICY decisions made by drivers, modules, and userspace config. The kernel provides the *mechanism* — the ability to retry, the ability to timeout, the ability to schedule — and lets external actors decide *when* and *how much*.

We said "mechanism vs policy" in the council debates. We nodded along. We didn't do anything about it.

This document fixes that.

---

## 1. What Is MECHANISM in a Provider?

Mechanism is the irreducible machinery. It's what you CANNOT externalize because it IS the translation layer between two systems. In Linux kernel terms, mechanism is the interrupt handler, the memory allocator, the syscall dispatch table. Not the policies governing them — the raw capability.

For a Copilot provider, mechanism consists of exactly three things:

### 1.1 SDK Session Lifecycle

The provider must manage the connection to the Copilot API. This is pure mechanism — there is no policy decision about *whether* to authenticate or *whether* to maintain a session. You either have a connection or you don't.

```python
class CopilotSession:
    """Pure mechanism: manages SDK connection lifecycle."""

    async def initialize(self, token: str) -> None:
        """Establish authenticated session with Copilot API."""
        self._client = await CopilotClient.connect(token)

    async def close(self) -> None:
        """Clean shutdown of SDK connection."""
        if self._client:
            await self._client.disconnect()
            self._client = None

    @property
    def is_active(self) -> bool:
        return self._client is not None and self._client.connected
```

That's it. No retry logic, no reconnection strategy, no timeout handling. Those are policy. The session either connects or raises. What happens after a failure is someone else's decision.

### 1.2 Event Stream Reading

The provider must read events from the Copilot API's streaming response. This is mechanical translation — bytes come in, typed events come out. The kernel analog is reading from a device file descriptor. The kernel provides `read()`. It doesn't decide what to do when the device is slow.

```python
class EventStreamReader:
    """Pure mechanism: reads and yields typed events from stream."""

    async def read_events(self, stream: AsyncIterator[bytes]) -> AsyncIterator[Event]:
        """Translate raw stream bytes into typed event objects."""
        async for chunk in stream:
            event = self._parse_event(chunk)
            if event is not None:
                yield event

    def _parse_event(self, raw: bytes) -> Event | None:
        """Mechanical parsing. No interpretation, no filtering."""
        # Parse SSE format, return typed Event or None for keep-alives
        ...
```

No filtering. No "should I skip this event type?" decisions. No buffering strategy. Those are policies that belong elsewhere. The stream reader yields what the API sends, period.

### 1.3 Type Conversion

The provider bridges two type systems: Amplifier's internal model and Copilot's API model. This is the most kernel-like function — it's a device driver translating between the bus protocol and the kernel's internal representation.

```python
class TypeConverter:
    """Pure mechanism: bidirectional type translation."""

    def to_copilot_request(self, request: AmplifierRequest) -> CopilotAPIRequest:
        """Translate Amplifier request format to Copilot API format."""
        ...

    def from_copilot_event(self, event: CopilotEvent) -> AmplifierEvent:
        """Translate Copilot API event to Amplifier event format."""
        ...
```

Type conversion is mechanical. Message A in format X becomes message B in format Y. There's no decision about *whether* to convert — if you get an event, you convert it. The mapping is deterministic.

### The Mechanism Audit

Everything else currently in the provider is NOT mechanism. If you can imagine it being configured differently for different deployments, users, or conditions — it's policy.

**True mechanism (keep in code):**
- SDK authentication handshake
- SSE event parsing
- Type mapping between Amplifier ↔ Copilot models
- Event yield/dispatch plumbing

**NOT mechanism (extract to config):**
- How many times to retry
- How long to wait
- Which errors are retryable
- What counts as a "fake tool"
- How to cache models
- Which headers to send
- Rate limit thresholds

The true mechanism of this provider is approximately **300 lines**. The other 4,900 lines are policy masquerading as mechanism.

---

## 2. What Is POLICY That Should Be EXTERNAL?

Policy is every decision that *could reasonably be different* in another deployment, another context, another user's setup. Linux gets this right: the kernel provides `sched_setscheduler()` (mechanism), but the actual scheduling parameters come from userspace config and process attributes (policy).

Here are the policies currently hardcoded in our provider:

### 2.1 Retry Counts and Timing

Currently buried somewhere in the code: magic numbers like `max_retries=3`, `delay=1.0`, exponential backoff multipliers. These are not properties of the Copilot API. They're operational decisions that should change based on:

- Network conditions (corporate proxy vs direct)
- Use case (interactive chat vs batch processing)
- SLA requirements (fast-fail vs resilient)
- Cost sensitivity (each retry costs tokens)

**Policy, not mechanism.** Extract it.

### 2.2 Timeout Selection

How long to wait for a response? For a streaming chunk? For authentication? These are deployment-specific decisions. A user on a fast connection wants tight timeouts (fail fast, retry elsewhere). A user behind a corporate VPN needs generous timeouts. The mechanism is "wait for response with a deadline." The deadline itself is policy.

### 2.3 Error Classification Rules

Which HTTP status codes are retryable? Is a 429 always a rate limit, or could it be a quota exhaustion that won't recover? Is a 503 transient or is the service down for maintenance? These classifications are heuristics — educated guesses that should be tunable. The mechanism is "check if error is retryable." The classification table is policy.

### 2.4 Fake Tool Detection

The provider currently contains logic to detect and handle "fake" tool calls from the model. This is entirely a policy decision: what patterns constitute a fake tool call? What do we do when we detect one? Suppress it? Log it? Pass it through with a warning? The detection heuristics and response strategy are policy. The ability to intercept and filter events is mechanism.

### 2.5 Model Caching Strategy

How long to cache the model list? When to invalidate? What's the fallback if the cache is stale? These are operational decisions that depend on how frequently the model list actually changes (which varies by deployment type — enterprise vs individual, stable vs preview).

### The Policy Test

For any line of code, ask: "Would a different reasonable operator make a different choice here?" If yes, it's policy. Ship it as config.

---

## 3. The Config Contract

Linux uses Kconfig, devicetree, and sysfs for policy configuration. We'll use YAML because it's human-readable, well-tooled, and already used by Amplifier for bundle configuration. Here are the schemas:

### 3.1 Retry Policy

```yaml
# policies/retry.yaml
retry:
  max_attempts: 3
  initial_delay_ms: 1000
  max_delay_ms: 60000
  backoff_multiplier: 2.0
  jitter: true
  jitter_range_ms: 500
  retryable_errors:
    - rate_limit
    - timeout
    - transient
    - connection_reset
  non_retryable_errors:
    - authentication_failed
    - invalid_request
    - quota_exhausted
```

### 3.2 Timeout Policy

```yaml
# policies/timeouts.yaml
timeouts:
  connection_ms: 10000
  request_ms: 30000
  streaming_chunk_ms: 5000
  authentication_ms: 15000
  model_list_ms: 10000
  # Per-operation overrides
  overrides:
    chat_completion:
      request_ms: 120000
      streaming_chunk_ms: 10000
    embedding:
      request_ms: 60000
```

### 3.3 Error Classification

```yaml
# policies/errors.yaml
error_classification:
  http_status:
    429: rate_limit
    500: transient
    502: transient
    503: transient
    504: timeout
    401: authentication_failed
    403: authentication_failed
    400: invalid_request
    404: invalid_request
  # Pattern-based classification for error messages
  message_patterns:
    - pattern: "quota exceeded"
      classification: quota_exhausted
    - pattern: "model not found"
      classification: invalid_request
    - pattern: "context length exceeded"
      classification: invalid_request
  # Default for unclassified errors
  default: unknown
```

### 3.4 Fake Tool Detection

```yaml
# policies/tool_filtering.yaml
tool_filtering:
  enabled: true
  fake_tool_patterns:
    - name_regex: "^(search|browse|fetch)_web$"
      action: suppress
    - name_regex: "^python_exec$"
      action: suppress
    - name_regex: "^file_(read|write)$"
      action: pass_through
  unknown_tool_action: log_and_pass
  log_suppressed: true
```

### 3.5 Model Cache Policy

```yaml
# policies/cache.yaml
cache:
  model_list:
    ttl_seconds: 3600
    stale_while_revalidate: true
    max_stale_seconds: 86400
    fallback_on_error: true
  # Future: response caching, embedding caching, etc.
```

### 3.6 The Meta-Config: Policy Manifest

```yaml
# policies/manifest.yaml
# Which policy files to load and in what order
# Later files override earlier ones (like Linux's config overlay)
policies:
  - retry.yaml
  - timeouts.yaml
  - errors.yaml
  - tool_filtering.yaml
  - cache.yaml

# Environment-specific overrides
# Analogous to Linux's devicetree overlays
overrides:
  production:
    - overrides/production.yaml
  development:
    - overrides/development.yaml
  ci:
    - overrides/ci.yaml
```

### Why YAML and Not Code?

The same reason Linux uses devicetree instead of compiled-in board support: **you shouldn't need to recompile the kernel to change a timer value.** YAML files can be:

- Edited by operators who aren't Python developers
- Overridden per-environment without code changes
- Validated against schemas before deployment
- Diffed and audited as configuration changes
- Loaded at startup or hot-reloaded at runtime

---

## 4. The Provider as Kernel Module

A Linux device driver follows a strict pattern: register capabilities, implement a small interface, read configuration from external sources. The driver for an Intel NIC doesn't contain TCP/IP — it implements `ndo_start_xmit()` and `ndo_open()` and lets the kernel's networking stack handle everything above the wire.

Our provider should follow the same pattern.

### 4.1 The 300-Line Provider

```python
"""
Copilot Provider — A kernel module for Amplifier.

Implements ONLY the translation mechanism between
Amplifier's provider interface and GitHub Copilot's API.
All policy is read from external configuration.
"""

from amplifier.provider import Provider, ProviderCapabilities
from amplifier.types import Request, Event

from .session import CopilotSession
from .stream import EventStreamReader
from .types import TypeConverter
from .policy import PolicyEngine


class CopilotProvider(Provider):
    """
    Analogous to a Linux device driver:
    - Registers what it can do (capabilities)
    - Reads config from external files (policies)
    - Implements only the translation (mechanism)
    """

    # --- Registration (like module_init / module_exit) ---

    @staticmethod
    def capabilities() -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            tool_calls=True,
            vision=False,
            embeddings=False,
        )

    # --- Lifecycle (like probe / remove) ---

    async def initialize(self, config: dict) -> None:
        self._policy = PolicyEngine.from_config_dir(config["policy_dir"])
        self._session = CopilotSession()
        self._stream = EventStreamReader()
        self._types = TypeConverter()
        await self._session.initialize(config["token"])

    async def shutdown(self) -> None:
        await self._session.close()

    # --- The Interface (like ndo_start_xmit / ndo_open) ---

    async def complete(self, request: Request) -> AsyncIterator[Event]:
        """The ONLY interesting method. Everything else is plumbing."""
        api_request = self._types.to_copilot_request(request)

        raw_stream = await self._session.send(
            api_request,
            timeout=self._policy.timeout_for("chat_completion"),
        )

        async for raw_event in self._stream.read_events(raw_stream):
            event = self._types.from_copilot_event(raw_event)

            if self._policy.should_filter(event):
                continue

            yield event

    async def list_models(self) -> list[Model]:
        """Model listing with policy-driven caching."""
        cached = self._policy.get_cached("model_list")
        if cached is not None:
            return cached

        models = await self._session.list_models(
            timeout=self._policy.timeout_for("model_list"),
        )

        self._policy.set_cached("model_list", models)
        return models
```

Count the lines. **Under 80 lines** for the provider itself. The rest lives in four focused modules:

| Module | Lines (est.) | Responsibility |
|--------|-------------|----------------|
| `session.py` | ~60 | SDK connection lifecycle |
| `stream.py` | ~50 | SSE event parsing |
| `types.py` | ~120 | Type conversion (this is the bulk — mapping is verbose) |
| `policy.py` | ~70 | Config loading and policy queries |
| **Total** | **~380** | **Complete provider** |

380 lines of code. Down from 5,200. That's a **92% reduction**. And the 380 lines are ALL mechanism — no policy decisions baked in.

### 4.2 What Disappeared?

The 4,800 lines that vanished didn't contain value. They contained:

- **Retry logic with hardcoded parameters** → Replaced by `PolicyEngine` reading `retry.yaml`
- **Timeout constants** → Replaced by `timeouts.yaml`
- **Error classification switch statements** → Replaced by `errors.yaml`
- **Fake tool detection heuristics** → Replaced by `tool_filtering.yaml`
- **Cache management code** → Replaced by `cache.yaml` + a generic cache utility
- **Defensive code for edge cases that may never occur** → Removed. If they occur, add them to config.

### 4.3 The Analogy Made Precise

| Linux Kernel | Provider |
|-------------|----------|
| `module_init()` / `module_exit()` | `initialize()` / `shutdown()` |
| `struct file_operations` | `Provider` base class interface |
| Device Tree / Kconfig | `policies/*.yaml` |
| `probe()` — detect hardware | `initialize()` — connect to API |
| `read()` / `write()` — data transfer | `complete()` — request/response |
| `ioctl()` — control operations | `list_models()` — metadata queries |
| Driver reads DT for config | Provider reads YAML for policy |
| Kernel provides retry infra | Amplifier provides retry utilities |
| Driver says "retry 3 times" via DT | Provider says "retry 3 times" via YAML |

---

## 5. Dynamic Policy Loading

The most powerful consequence of separating mechanism from policy: **policy changes without code changes.**

### 5.1 How Linux Does It

Linux has multiple mechanisms for runtime policy changes:

- **sysctl**: Change kernel parameters at runtime (`/proc/sys/net/ipv4/tcp_retries2`)
- **sysfs**: Per-device attribute files (`/sys/class/net/eth0/mtu`)
- **modprobe options**: Load-time parameters (`modprobe iwlwifi power_save=1`)
- **cgroups**: Per-process resource policies

None of these require recompilation. None require restarting the kernel. The mechanism stays running; only the policy parameters change.

### 5.2 How the Provider Should Do It

```python
class PolicyEngine:
    """Loads and serves policy from external YAML files."""

    def __init__(self, policies: dict):
        self._policies = policies
        self._load_time = time.monotonic()

    @classmethod
    def from_config_dir(cls, path: Path) -> "PolicyEngine":
        """Load all policy files from directory."""
        manifest = yaml.safe_load((path / "manifest.yaml").read_text())
        policies = {}
        for policy_file in manifest["policies"]:
            data = yaml.safe_load((path / policy_file).read_text())
            policies = deep_merge(policies, data)

        # Apply environment overrides
        env = os.environ.get("AMPLIFIER_ENV", "production")
        if env in manifest.get("overrides", {}):
            for override_file in manifest["overrides"][env]:
                data = yaml.safe_load((path / override_file).read_text())
                policies = deep_merge(policies, data)

        return cls(policies)

    def timeout_for(self, operation: str) -> float:
        """Get timeout in seconds for a specific operation."""
        timeouts = self._policies["timeouts"]
        override = timeouts.get("overrides", {}).get(operation, {})
        ms = override.get("request_ms", timeouts["request_ms"])
        return ms / 1000.0

    def should_filter(self, event: Event) -> bool:
        """Apply tool filtering policy to an event."""
        if not self._policies["tool_filtering"]["enabled"]:
            return False
        if not isinstance(event, ToolCallEvent):
            return False
        for pattern in self._policies["tool_filtering"]["fake_tool_patterns"]:
            if re.match(pattern["name_regex"], event.tool_name):
                return pattern["action"] == "suppress"
        return False

    def retry_policy(self) -> RetryPolicy:
        """Return retry configuration as a typed object."""
        cfg = self._policies["retry"]
        return RetryPolicy(
            max_attempts=cfg["max_attempts"],
            initial_delay=cfg["initial_delay_ms"] / 1000.0,
            max_delay=cfg["max_delay_ms"] / 1000.0,
            backoff_multiplier=cfg["backoff_multiplier"],
            jitter=cfg["jitter"],
        )
```

### 5.3 The Three Levels of Policy Change

**Level 1: Restart-time (like modprobe options)**
Edit YAML, restart the provider. Simplest, safest. Good enough for 90% of cases.

```bash
# Change retry count
sed -i 's/max_attempts: 3/max_attempts: 5/' policies/retry.yaml
# Restart provider
amplifier restart provider copilot
```

**Level 2: Signal-based reload (like SIGHUP)**
Send a signal, provider reloads config without dropping connections.

```python
# In provider initialization
signal.signal(signal.SIGHUP, lambda *_: self._policy.reload())
```

**Level 3: Watch-based hot reload (like inotify + sysfs)**
Provider watches config directory, reloads automatically on change.

```python
# Optional: filesystem watcher for zero-touch updates
async def _watch_policies(self):
    async for change in watchfiles.awatch(self._policy_dir):
        self._policy = PolicyEngine.from_config_dir(self._policy_dir)
        log.info("Policy reloaded", changes=change)
```

### 5.4 What This Enables

Without touching provider code, an operator can:

1. **Increase retry attempts** during known flaky periods
2. **Tighten timeouts** for latency-sensitive deployments
3. **Add new fake tool patterns** as models evolve
4. **Reclassify errors** when API behavior changes
5. **Extend cache TTL** for stable enterprise deployments
6. **Override everything** per-environment (dev gets loose timeouts, prod gets tight ones)

This is the power Linux gives sysadmins. No recompilation. No PR review for a timeout change. No deployment pipeline for a retry count bump. **Mechanism in code, policy in config.**

---

## The Verdict

The council said "mechanism vs policy" and felt sophisticated. Linux has been *living* it for 30 years.

A provider is a device driver. It translates between two systems. It registers its capabilities. It reads its configuration from external files. It implements the minimum viable interface. Everything else — every retry count, every timeout, every heuristic — is policy that belongs in config files, editable by operators, overridable per environment, changeable without code changes.

**5,200 lines → 380 lines of mechanism + YAML policy files.**

That's not a refactoring suggestion. That's what "mechanism vs policy" actually means when you stop cargo-culting the phrase and start applying it.

The kernel doesn't care how many times you retry. It just gives you the ability to retry. Be the kernel.

---

*"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."*
— Antoine de Saint-Exupéry

*"UNIX is simple. It just takes a genius to understand its simplicity."*
— Dennis Ritchie