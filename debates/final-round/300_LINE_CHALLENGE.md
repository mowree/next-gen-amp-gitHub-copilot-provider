
# THE 300-LINE PROVIDER: Ruthless Simplicity

**Version**: 1.0  
**Date**: 2026-03-08  
**Authority**: Zen Architect, after forensic analysis of 5,286 lines across 13 Python files  
**Provocation**: Elon Musk — "If limited to 300 lines, everything else is policy that shouldn't be in the provider."  
**Counter**: Steve Jobs — "That's not simplicity. That's moving furniture around in a crowded room."

---

## Executive Summary

The current GitHub Copilot provider is **5,286 lines of Python** across 13 files. The Golden Vision proposed decomposing the 1,799-line `provider.py` into 17 modules of ~100 lines each — but that's still 1,700+ lines, with the supporting cast pushing the total past 5,000.

**The question is not "how do we decompose 5,286 lines?" The question is: "what are the 300 lines that actually translate between Amplifier and the SDK?"**

Everything else is one of three things:
1. **Policy** that belongs in YAML configuration
2. **Documentation** that belongs in Markdown contracts
3. **Code that shouldn't exist at all** because the SDK already handles it

This document proves it's possible. Not by moving furniture — by realizing most of the furniture was never needed.

---

## The Autopsy: Where Do 5,286 Lines Come From?

| File | Lines | Actual Purpose |
|------|------:|----------------|
| `provider.py` | 1,799 | Provider protocol + everything else |
| `client.py` | 820 | SDK client wrapper with lifecycle |
| `sdk_driver.py` | 620 | Loop control, circuit breaker, event handler |
| `converters.py` | 426 | Message format conversion |
| `model_cache.py` | 415 | Disk-based model metadata cache |
| `model_naming.py` | 359 | Model ID parsing and pattern matching |
| `exceptions.py` | 322 | 9 exception classes + detection helpers |
| `_constants.py` | 312 | Constants, enums, built-in tool names |
| `models.py` | 292 | Model conversion SDK → Amplifier |
| `_platform.py` | 280 | Cross-platform binary discovery |
| `tool_capture.py` | 218 | Tool bridge: convert + deny hook |
| `__init__.py` | 371 | Module mounting, singleton management |
| `_permissions.py` | 52 | File permission utility |
| **Total** | **5,286** | |

### The Damning Ratio

Of 5,286 lines, how many are the **actual translation mechanism** — converting Amplifier requests to SDK sessions and SDK responses to Amplifier responses?

**Answer: approximately 200 lines.**

The remaining ~5,000 lines are:
- **~1,200 lines**: Error handling, retry logic, timeout selection (policy)
- **~800 lines**: Model metadata caching, naming conventions, capability detection (the SDK knows this)
- **~700 lines**: SDK binary discovery, platform detection, permissions (the SDK handles this)
- **~600 lines**: Observability events, metrics tracking, debug logging (cross-cutting concerns)
- **~500 lines**: Docstrings, comments, section headers (documentation embedded in code)
- **~400 lines**: Fake tool call detection, missing tool result repair (edge case defense)
- **~300 lines**: Module boilerplate, imports, __init__.py (structural overhead)
- **~500 lines**: Constants, enums, mapping tables (configuration embedded in code)

---

## What Stays in Python (The 300 Lines)

### Principle: The provider is a **translator**. It converts between two protocols. That's it.

The 300 lines contain exactly **five responsibilities**:

#### 1. Provider Protocol Implementation (~40 lines)

```python
class CopilotProvider:
    """Amplifier Provider Protocol: translate requests to Copilot SDK."""
    
    api_label = "GitHub Copilot"
    
    def __init__(self, config, coordinator, client=None):
        self._config = config or {}
        self._coordinator = coordinator
        self._client = client or CopilotClientWrapper(config=self._config)
        self._model = config.get("model", "claude-opus-4.5")
    
    @property
    def name(self) -> str:
        return "github-copilot"
    
    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            id=self.name,
            display_name="GitHub Copilot SDK",
            credential_env_vars=["GITHUB_TOKEN", "GH_TOKEN"],
            capabilities=["streaming", "tools", "vision"],
            defaults={"model": self._model, "max_tokens": 4096},
        )
    
    async def list_models(self) -> list[ModelInfo]:
        raw = await self._client.list_models()
        return [_to_model_info(m) for m in raw]
    
    def parse_tool_calls(self, response):
        return response.tool_calls or []
```

That's the protocol. Four of the five methods are trivial. The fifth — `complete()` — is the reason the provider exists.

#### 2. The Complete Method: Session Lifecycle (~80 lines)

```python
    async def complete(self, request, **kwargs):
        model = kwargs.get("model", self._model)
        messages = _extract_messages(request)
        system_msg = _extract_system(messages)
        prompt = _to_prompt(messages)
        tools, hooks = _prepare_tools(request)
        
        async with self._client.create_session(
            model=model,
            system_message=system_msg,
            streaming=True,
            tools=tools,
            hooks=hooks,
            reasoning_effort=_resolve_reasoning(kwargs, model),
        ) as session:
            handler = EventHandler()
            unsub = session.on(handler.on_event)
            try:
                await session.send({"prompt": prompt})
                await handler.wait(timeout=self._config.get("timeout", 3600))
                
                if handler.should_abort and tools:
                    await _try_abort(session)
                
                return _build_response(handler, model)
            finally:
                unsub()
```

No retry logic (that's kernel policy via `retry_with_backoff`). No error translation inline (that's a mapping table). No fake tool call detection (that's a prompt engineering concern, not a provider concern). No metrics (that's observability middleware). No model capability caching (the SDK knows).

#### 3. Event Handler: SDK Events → Domain Data (~80 lines)

```python
class EventHandler:
    """Collect SDK streaming events into response data."""
    
    def __init__(self):
        self.text = []
        self.thinking = []
        self.tools = []
        self.usage = {}
        self._done = asyncio.Event()
        self._turn = 0
        self._captured = False
    
    def on_event(self, event):
        t = event.type
        d = event.data
        
        if t == EventType.ASSISTANT_TURN_START:
            self._turn += 1
            if self._turn > MAX_TURNS:
                self._done.set()
                
        elif t == EventType.ASSISTANT_MESSAGE_DELTA:
            self.text.append(getattr(d, "delta_content", "") or "")
            
        elif t == EventType.ASSISTANT_REASONING_DELTA:
            self.thinking.append(getattr(d, "delta_content", "") or "")
            
        elif t == EventType.ASSISTANT_USAGE:
            self.usage = {"input": getattr(d, "input_tokens", 0),
                          "output": getattr(d, "output_tokens", 0)}
            
        elif t == EventType.ASSISTANT_MESSAGE:
            if not self._captured and getattr(d, "tool_requests", None):
                self.tools = _parse_tool_requests(d.tool_requests, self._turn)
                self._captured = True
                self._done.set()
            elif not self.text and getattr(d, "content", None):
                self.text.append(d.content)
                
        elif t in (EventType.SESSION_IDLE, EventType.SESSION_ERROR):
            self._done.set()
    
    async def wait(self, timeout):
        await asyncio.wait_for(self._done.wait(), timeout=timeout)
    
    @property
    def should_abort(self):
        return self._captured or self._turn > MAX_TURNS
```

This is the **entire** SDK Driver, LoopController, ToolCaptureStrategy, and CircuitBreaker — collapsed from 620 lines to ~50. The three separate classes were an abstraction for a single event callback. One class, one method, one event loop.

#### 4. Conversion Functions (~60 lines)

```python
def _to_prompt(messages):
    """Serialize Amplifier messages to SDK prompt format."""
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = _text(msg)
        if role == "system": continue
        elif role == "user": parts.append(f"Human: {content}")
        elif role == "assistant": parts.append(f"Assistant: {_with_tools(msg, content)}")
        elif role == "tool": parts.append(f'<tool_result name="{msg.get("name", "tool")}">{content}</tool_result>')
    return "\n\n".join(parts)

def _extract_system(messages):
    parts = [_text(m) for m in messages if m.get("role") == "system"]
    return "\n\n".join(parts) or None

def _text(msg):
    c = msg.get("content", "")
    if isinstance(c, str): return c
    if isinstance(c, list): return "\n".join(
        b.get("text", "") for b in c 
        if isinstance(b, dict) and b.get("type") not in ("tool_call", "tool_use", "thinking")
    )
    return str(c) if c else ""

def _build_response(handler, model):
    blocks = []
    if handler.thinking:
        blocks.append(ThinkingBlock(thinking="".join(handler.thinking)))
    if handler.text:
        blocks.append(TextBlock(type="text", text="".join(handler.text)))
    
    tool_calls = None
    if handler.tools:
        tool_calls = [ToolCall(id=t["id"], name=t["name"], arguments=t["args"]) for t in handler.tools]
        blocks.extend(ToolCallBlock(type="tool_call", id=t["id"], name=t["name"], input=t["args"]) for t in handler.tools)
    
    u = handler.usage
    return ChatResponse(
        content=blocks, tool_calls=tool_calls,
        usage=Usage(input_tokens=u.get("input", 0), output_tokens=u.get("output", 0),
                    total_tokens=u.get("input", 0) + u.get("output", 0)),
        finish_reason="tool_use" if tool_calls else "end_turn",
    )

def _to_model_info(raw):
    """SDK ModelInfo → Amplifier ModelInfo. Trust the SDK."""
    caps = getattr(raw, "capabilities", None)
    limits = getattr(caps, "limits", None) if caps else None
    supports = getattr(caps, "supports", None) if caps else None
    ctx = getattr(limits, "max_context_window_tokens", 128000) or 128000
    prompt = getattr(limits, "max_prompt_tokens", None)
    out = (ctx - prompt) if prompt and prompt < ctx else 8192
    
    abilities = ["streaming", "tools"]
    if getattr(supports, "vision", False): abilities.append("vision")
    if getattr(supports, "reasoning_effort", False): abilities.append("thinking")
    
    return ModelInfo(id=raw.id, display_name=raw.name, context_window=ctx,
                     max_output_tokens=out, capabilities=abilities)
```

#### 5. Tool Bridge + Deny Hook (~40 lines)

```python
def _prepare_tools(request):
    """Convert request tools to SDK format + deny hook."""
    req_tools = getattr(request, "tools", None)
    if not req_tools: return None, None
    
    from copilot.types import Tool
    sdk_tools = []
    seen = set()
    for spec in sorted(req_tools, key=lambda t: getattr(t, "name", "")):
        name = getattr(spec, "name", "")
        if not name or name in seen: continue
        seen.add(name)
        sdk_tools.append(Tool(
            name=name,
            description=getattr(spec, "description", ""),
            handler=lambda _: {"textResultForLlm": "denied"},
            parameters=getattr(spec, "parameters", None),
            overrides_built_in_tool=name in EXCLUDED_BUILTINS,
        ))
    
    hooks = {"on_pre_tool_use": lambda inp, ctx: {
        "permissionDecision": "deny",
        "permissionDecisionReason": "Processing",
        "suppressOutput": True,
    }}
    return sdk_tools, hooks

def _parse_tool_requests(reqs, turn):
    tools = []
    for tr in reqs:
        args = getattr(tr, "arguments", {}) or {}
        if isinstance(args, str):
            try: args = json.loads(args)
            except: args = {"raw": args}
        tools.append({"id": getattr(tr, "tool_call_id", ""), "name": getattr(tr, "name", ""), "args": args})
    return tools
```

### Total: ~300 lines. Everything the provider needs to translate between Amplifier and the Copilot SDK.

---

## What Moves to YAML Configuration

### `provider-config.yaml` — All Policy Decisions

```yaml
# GitHub Copilot Provider Configuration
# Everything here is POLICY, not MECHANISM

provider:
  name: github-copilot
  display_name: GitHub Copilot SDK
  api_label: GitHub Copilot

defaults:
  model: claude-opus-4.5
  max_tokens: 4096
  temperature: 0.7
  timeout: 3600          # 1 hour for all models
  thinking_timeout: 3600  # Same — override if needed

credentials:
  env_vars:
    - GITHUB_TOKEN
    - GH_TOKEN
    - COPILOT_GITHUB_TOKEN

retry:
  max_retries: 3
  initial_delay: 1.0
  max_delay: 60.0
  jitter: true

circuit_breaker:
  max_turns: 3           # Evidence: 305-turn incident
  hard_limit: 10         # Absolute ceiling
  capture_first_turn_only: true
  deduplicate_tools: true

# SDK built-in tools to exclude when user tools are present
# Evidence: Session 497bbab7, 2a1fe04a
excluded_builtins:
  - view
  - edit
  - str_replace_editor
  - grep
  - glob
  - bash
  - read_bash
  - write_bash
  - list_bash
  - stop_bash
  - powershell
  - read_powershell
  - write_powershell
  - web_fetch
  - web_search
  - ask_user
  - report_intent
  - task
  - create
  - create_file
  - shell
  - report_progress
  - update_todo
  - skill
  - fetch_copilot_cli_documentation
  - search_code_subagent
  - github-mcp-server-web_search
  - task_complete
```

### `error-mapping.yaml` — Error Translation Table

```yaml
# Maps provider exceptions to kernel exceptions
# This is POLICY: which errors are retryable and how they map

error_mapping:
  CopilotAuthenticationError:
    kernel_type: AuthenticationError
    retryable: false
    
  CopilotRateLimitError:
    kernel_type: RateLimitError
    retryable: true
    retryable_override: "retry_after > max_delay → false"
    
  CopilotTimeoutError:
    kernel_type: LLMTimeoutError
    retryable: true
    
  CopilotConnectionError:
    kernel_type: NetworkError
    retryable: true
    
  CopilotModelNotFoundError:
    kernel_type: NotFoundError
    retryable: false
    
  CopilotSdkLoopError:
    kernel_type: ProviderUnavailableError
    retryable: false
    
  CopilotSessionError:
    kernel_type: ProviderUnavailableError
    retryable: true
    
  CopilotAbortError:
    kernel_type: AbortError
    retryable: false

# Rate limit detection patterns
rate_limit_patterns:
  text:
    - "rate limit"
    - "rate_limit"
    - "ratelimit"
    - "too many requests"
    - "quota exceeded"
    - "throttl"
  status_codes:
    - 429
```

### `model-limits.yaml` — Bundled Fallback Limits

```yaml
# Hardcoded fallback when SDK is unavailable
# Source: Live SDK data as of 2026-02-16
# Updated by: `amplifier init` → disk cache

bundled_limits:
  claude-haiku-4.5:     { context: 144000, output: 16000 }
  claude-opus-4.5:      { context: 200000, output: 32000 }
  claude-opus-4.6:      { context: 200000, output: 32000 }
  claude-opus-4.6-1m:   { context: 1000000, output: 64000 }
  claude-sonnet-4:      { context: 216000, output: 88000 }
  claude-sonnet-4.5:    { context: 200000, output: 32000 }
  claude-sonnet-4.6:    { context: 200000, output: 72000 }
  gemini-3-pro-preview: { context: 128000, output: 65536 }
  gpt-4.1:              { context: 128000, output: 64000 }
  gpt-5:                { context: 400000, output: 272000 }
  gpt-5-mini:           { context: 264000, output: 136000 }
  gpt-5.1:              { context: 264000, output: 136000 }
  gpt-5.1-codex:        { context: 400000, output: 272000 }
```

---

## What Moves to Markdown

### `SDK_CONTRACT.md` — SDK Behavior Documentation

The 93-line docstring in `model_naming.py` explaining naming conventions? That's documentation, not code. The 37-line architecture note in `tool_capture.py`? Documentation. The evidence notes scattered through `_constants.py`? Documentation.

All of these move to `SDK_CONTRACT.md`:

```markdown
# SDK Behavior Contract

## Deny + Destroy Pattern
- preToolUse deny prevents CLI tool execution
- Session disconnect prevents retry loops  
- Evidence: Session a1a0af17 (305 turns), Session 497bbab7 (bypass)

## Event Model
- ASSISTANT_TURN_START fires before each turn
- ASSISTANT_MESSAGE contains tool_requests
- ASSISTANT_MESSAGE_DELTA contains text deltas
- SESSION_IDLE signals completion
- SESSION_ERROR signals failure

## Model Naming Convention
- Periods for versions: claude-opus-4.5 (not 4-5)
- Dashes for separators: gpt-5.1-codex
- SDK is authoritative for capabilities

## Known Built-in Tools
[List moved from _constants.py with evidence links]
```

### `ERROR_CONTRACTS.md` — Error Handling Rules

```markdown
# Error Handling Contracts

## Rate Limit Detection
- Patterns: "rate limit", "429", "too many requests"
- Extract retry_after from response headers/message
- Mark non-retryable if retry_after > max_delay

## Content Filter Detection  
- Patterns: "content filtered", "blocked by policy"
- Never retryable — user must modify request

## Auth Error Detection
- Heuristic: "auth", "token", "login" in error message
- SDK doesn't expose typed auth exceptions
```

---

## What DELETES Entirely

This is where Steve Jobs was wrong. We're not moving furniture. We're **burning furniture that was never sat in**.

### 1. `model_cache.py` — 415 lines → **DELETED**

**Why it existed**: Cache model metadata to disk so `get_info()` returns accurate context_window without an API call.

**Why it deletes**: The SDK already knows model limits. `list_models()` is called during `amplifier init`. Amplifier's kernel can cache the result in memory. A 415-line disk caching system with atomic writes, staleness detection, format versioning, and cross-platform path handling exists because we built our own cache instead of asking "does Amplifier already have a caching mechanism?"

If Amplifier needs persistent model metadata, that's a **kernel feature**, not a provider responsibility. The provider's job is to call `list_models()` and return the result.

**Lines saved**: 415

### 2. `model_naming.py` — 359 lines → **DELETED**

**Why it existed**: Parse model IDs to detect thinking models for timeout selection. Fallback for when SDK capability check fails.

**Why it deletes**: The function `is_thinking_model()` is a fallback for a fallback. The primary path queries SDK capabilities. If that fails (network error), we fall back to pattern matching. But **the timeout is already 3600 seconds for all models**. The entire 359-line module exists to select between two timeouts that are currently identical.

Even if timeouts differed: using a longer timeout for a non-thinking model wastes a few minutes. Using a shorter timeout for a thinking model causes failures. **The safe default is always the longer timeout.** No pattern matching needed.

**Lines saved**: 359

### 3. `_platform.py` — 280 lines → **DELETED**

**Why it existed**: Cross-platform CLI binary discovery with strategy pattern, factory function, platform detection.

**Why it deletes**: The Copilot SDK bundles its own binary. The SDK's `CopilotClient()` finds it automatically. We wrote 280 lines to locate a binary that the SDK already locates for itself. The `_build_client_options()` method in `client.py` doesn't even pass a CLI path to the SDK constructor.

**Lines saved**: 280

### 4. `_permissions.py` — 52 lines → **DELETED**

**Why it existed**: Ensure SDK binary has execute permissions (uv strips them).

**Why it deletes**: This is a workaround for a packaging tool bug. If the SDK binary isn't executable, the SDK fails to start. That's an SDK/packaging concern. If it needs fixing, fix it in the SDK's `__init__.py` or the `pyproject.toml` post-install script. Not in the provider.

**Lines saved**: 52

### 5. Fake Tool Call Detection — ~120 lines in `provider.py` → **DELETED**

**Why it existed**: When the LLM writes tool calls as text instead of structured calls, retry with a correction message.

**Why it deletes**: This is a prompt engineering concern. The LLM writing fake tool calls is caused by poor system prompts or conversation history formatting. The fix belongs in the system message ("Always use structured tool calls") or in Amplifier's prompt engineering, not in a provider-level regex scanner with markdown code block awareness.

If the LLM keeps faking tool calls, the orchestrator will see no tool_calls in the response and treat it as text. The user sees the text. This is an acceptable degradation, not a provider error.

**Lines saved**: 120

### 6. Missing Tool Result Repair — ~150 lines in `provider.py` → **DELETED**

**Why it existed**: Detect and inject synthetic error results for missing tool results in conversation history.

**Why it deletes**: The provider's docstring says it: "This indicates a bug in context management." If tool results are missing, the bug is in the orchestrator or context manager. A backup safety net in the provider **masks the bug** instead of exposing it. Delete the net, fix the actual bug when it surfaces.

**Lines saved**: 150

### 7. Session Metrics — ~50 lines in `provider.py` → **DELETED**

**Why it existed**: Track request count, session count, error count, response time.

**Why it deletes**: This is observability middleware. Amplifier's hooks system already emits `llm:request` and `llm:response` events. An external observer can compute these metrics from events. The provider shouldn't track its own metrics.

**Lines saved**: 50

### 8. Raw Payload Logging — ~40 lines in `provider.py` → **DELETED**

**Why it existed**: Debug logging of full request/response payloads when `raw=True`.

**Why it deletes**: This is a debug tool, not a provider feature. Use Amplifier's hook system to attach a debug observer that captures payloads. Don't embed debug logging in the hot path.

**Lines saved**: 40

### Total Lines Deleted: ~1,466

---

## The Accounting

| Category | Current Lines | 300-Line Provider |
|----------|-------------:|------------------:|
| Provider protocol | ~1,799 | ~40 |
| Complete method + streaming | (in provider) | ~80 |
| Event handler | ~620 | ~50 (inline) |
| Message conversion | ~426 | ~60 |
| Tool bridge + deny hook | ~218 | ~40 |
| Model conversion | ~292 | ~30 (inline) |
| Client wrapper | ~820 | ~0 (use SDK directly) |
| Error mapping | ~322 | ~0 (YAML table) |
| Constants | ~312 | ~0 (YAML config) |
| Model cache | ~415 | ~0 (deleted) |
| Model naming | ~359 | ~0 (deleted) |
| Platform detection | ~280 | ~0 (deleted) |
| Permissions | ~52 | ~0 (deleted) |
| Module init | ~371 | ~0 (simplified) |
| **Total** | **~5,286** | **~300** |

---

## The Client Wrapper Question

The biggest remaining question is `client.py` (820 lines). The 300-line provider above assumes we use the SDK's `CopilotClient` directly. Is this safe?

**What `client.py` actually does:**
1. Lazy initialization with double-checked locking (~80 lines)
2. Health check ping for cached clients (~30 lines)
3. Session creation with config translation (~100 lines)
4. `send_and_wait` with timeout wrapping (~70 lines)
5. Error translation for client-level errors (~100 lines)
6. Auth verification (~30 lines)
7. Client options building (~40 lines)
8. Cleanup/close (~30 lines)
9. Auth status, session listing utilities (~100 lines)
10. Docstrings and comments (~240 lines)

**What stays**: Session creation (~30 lines factored into provider's `complete()`), error wrapping (YAML mapping), auth verification (keep as a pre-flight check).

**What deletes**: Health check (SDK handles reconnection), lazy initialization (initialize in `mount()`), session listing (not used by provider protocol), send_and_wait (provider uses streaming only).

The SDK's `CopilotClient` is already a high-level wrapper. Our `CopilotClientWrapper` is a wrapper around a wrapper. The 300-line provider calls the SDK directly:

```python
from copilot import CopilotClient

client = CopilotClient(options)
await client.start()
session = await client.create_session(config)
```

No wrapper needed.

---

## The Error Translation Architecture

Instead of 322 lines of exception classes and a 50-line error translation block in `complete()`, use a **declarative error mapping** loaded from YAML:

```python
# ~20 lines in provider.py
ERROR_MAP = _load_yaml("error-mapping.yaml")

def _translate_error(e, provider_name):
    """Map SDK/provider exceptions to kernel exceptions."""
    for cls_name, mapping in ERROR_MAP.items():
        if type(e).__name__ == cls_name:
            kernel_cls = getattr(llm_errors, mapping["kernel_type"])
            return kernel_cls(str(e), provider=provider_name, 
                            retryable=mapping.get("retryable", True))
    return KernelLLMError(str(e), provider=provider_name, retryable=True)
```

The exception class hierarchy still exists in Python (8 simple classes, ~40 lines total without docstrings), but the **mapping logic** is YAML, not code.

---

## Why This Is Not "Moving Furniture"

Steve Jobs' objection was valid against the **decomposition** approach. Taking 1,700 lines and splitting them into 17 files of 100 lines each is furniture rearrangement. The total complexity is unchanged.

The 300-line approach is different because it **eliminates complexity**:

| Eliminated | Mechanism | Why |
|-----------|-----------|-----|
| Model cache | SDK already knows | Provider shouldn't cache what the SDK reports |
| Model naming | SDK capabilities are authoritative | Pattern matching is a fallback for a fallback |
| Platform detection | SDK finds its own binary | We locate what the SDK already locates |
| Fake tool call detection | Prompt engineering concern | Provider shouldn't parse LLM output for patterns |
| Missing tool result repair | Context manager's responsibility | Provider masks orchestrator bugs |
| Session metrics | Observability concern | Hook system provides this |
| Error mapping code | Policy, not mechanism | YAML table, not code |
| Client wrapper | Wrapper around a wrapper | Use SDK directly |

This isn't 5,286 lines distributed differently. This is **4,986 lines that don't need to exist**.

---

## The Proof: `provider.py` at ~200 Lines

```python
"""GitHub Copilot provider for Amplifier. Translation layer, nothing more."""
from __future__ import annotations
import asyncio, json, logging
from typing import Any
from amplifier_core import (ChatResponse, ModelInfo, ProviderInfo, 
    TextBlock, ThinkingBlock, ToolCall, ToolCallBlock, Usage)
from amplifier_core.llm_errors import LLMError as KernelLLMError

logger = logging.getLogger(__name__)

# Loaded from YAML at import time
_CONFIG = {}  # provider-config.yaml
_ERRORS = {}  # error-mapping.yaml  
_BUILTINS = frozenset()  # from config

MAX_TURNS = 3

class CopilotProvider:
    api_label = "GitHub Copilot"

    def __init__(self, config=None, coordinator=None, client=None):
        self._config = config or {}
        self._coordinator = coordinator
        self._client = client
        self._model = self._config.get("model", "claude-opus-4.5")
        self.config = self._config
        self.default_model = self._model

    @property
    def name(self): return "github-copilot"

    def get_info(self):
        return ProviderInfo(id=self.name, display_name="GitHub Copilot SDK",
            credential_env_vars=["GITHUB_TOKEN", "GH_TOKEN"],
            capabilities=["streaming", "tools", "vision"],
            defaults={"model": self._model, "max_tokens": 4096, "timeout": 3600})

    async def list_models(self):
        raw = await self._client.list_models()
        return [_to_model_info(m) for m in raw]

    def parse_tool_calls(self, response): return response.tool_calls or []

    async def complete(self, request, **kwargs):
        model = kwargs.get("model", self._model)
        messages = _extract_messages(request)
        prompt = _to_prompt(messages)
        system = _extract_system(messages)
        tools, hooks, excluded = _prepare_tools(request)
        effort = kwargs.get("reasoning_effort") if kwargs.get("extended_thinking") else None
        timeout = float(kwargs.get("timeout", self._config.get("timeout", 3600)))

        try:
            async with self._client.create_session(
                model=model, system_message=system, streaming=True,
                reasoning_effort=effort, tools=tools,
                excluded_tools=excluded, hooks=hooks,
            ) as session:
                h = _EventHandler()
                unsub = session.on(h.on_event)
                try:
                    await session.send({"prompt": prompt})
                    await h.wait(timeout)
                    if h.should_abort and tools:
                        try: await session.abort()
                        except: pass
                    return _build_response(h, bool(kwargs.get("extended_thinking")))
                finally:
                    unsub()
        except KernelLLMError: raise
        except Exception as e:
            raise _translate_error(e, self.name) from e

    async def close(self):
        if self._client: await self._client.close()


class _EventHandler:
    def __init__(self):
        self.text, self.thinking, self.tools, self.usage = [], [], [], {}
        self._done = asyncio.Event()
        self._turn = 0
        self._captured = False

    def on_event(self, event):
        from copilot.generated.session_events import SessionEventType as E
        t, d = event.type, event.data
        if t == E.ASSISTANT_TURN_START:
            self._turn += 1
            if self._turn > MAX_TURNS: self._done.set()
        elif t == E.ASSISTANT_MESSAGE_DELTA:
            self.text.append(getattr(d, "delta_content", "") or "")
        elif t == E.ASSISTANT_REASONING_DELTA:
            self.thinking.append(getattr(d, "delta_content", "") or "")
        elif t == E.ASSISTANT_USAGE:
            self.usage = {"in": getattr(d, "input_tokens", 0) or 0,
                          "out": getattr(d, "output_tokens", 0) or 0}
        elif t == E.ASSISTANT_MESSAGE:
            if not self._captured and getattr(d, "tool_requests", None):
                self.tools = _parse_tools(d.tool_requests)
                self._captured = True
                self._done.set()
            elif not self.text and getattr(d, "content", None):
                self.text.append(d.content)
        elif t in (E.SESSION_IDLE, E.SESSION_ERROR):
            self._done.set()

    async def wait(self, timeout):
        await asyncio.wait_for(self._done.wait(), timeout=timeout)

    @property
    def should_abort(self): return self._captured or self._turn > MAX_TURNS


# === Conversion helpers ===

def _extract_messages(req):
    if isinstance(req, dict): return req.get("messages", [])
    msgs = getattr(req, "messages", [])
    return [m.model_dump() if hasattr(m, "model_dump") else m for m in msgs]

def _extract_system(msgs):
    parts = [_text(m) for m in msgs if m.get("role") == "system"]
    return "\n\n".join(parts) or None

def _to_prompt(msgs):
    parts = []
    for m in msgs:
        r, c = m.get("role", "user"), _text(m)
        if r == "system": continue
        elif r == "user": parts.append(f"Human: {c}")
        elif r == "assistant": parts.append(f"Assistant: {c}")
        elif r == "tool": parts.append(f'<tool_result name="{m.get("name","tool")}">{c}</tool_result>')
    return "\n\n".join(parts)

def _text(msg):
    c = msg.get("content", "")
    if isinstance(c, str): return c
    if isinstance(c, list):
        return "\n".join(b.get("text","") for b in c
            if isinstance(b, dict) and b.get("type") not in ("tool_call","tool_use","thinking"))
    return str(c) if c else ""

def _prepare_tools(request):
    req_tools = getattr(request, "tools", None) if not isinstance(request, dict) else (request.get("tools") if isinstance(request, dict) else None)
    if not req_tools: return None, None, None
    from copilot.types import Tool
    sdk_tools, seen = [], set()
    for spec in sorted(req_tools, key=lambda t: getattr(t, "name", "")):
        name = getattr(spec, "name", "")
        if not name or name in seen: continue
        seen.add(name)
        sdk_tools.append(Tool(name=name, description=getattr(spec, "description", ""),
            handler=lambda _: {"textResultForLlm": "denied"},
            parameters=getattr(spec, "parameters", None),
            overrides_built_in_tool=name in _BUILTINS))
    hooks = {"on_pre_tool_use": lambda i, c: {"permissionDecision": "deny",
        "permissionDecisionReason": "Processing", "suppressOutput": True}}
    return sdk_tools, hooks, sorted(_BUILTINS)

def _parse_tools(reqs):
    result = []
    for tr in reqs:
        args = getattr(tr, "arguments", {}) or {}
        if isinstance(args, str):
            try: args = json.loads(args)
            except: args = {"raw": args}
        result.append({"id": getattr(tr, "tool_call_id", ""),
                       "name": getattr(tr, "name", ""), "args": args})
    return result

def _build_response(h, thinking_enabled):
    blocks = []
    if h.thinking and thinking_enabled:
        blocks.append(ThinkingBlock(thinking="".join(h.thinking), visibility="internal"))
    if h.text:
        blocks.append(TextBlock(type="text", text="".join(h.text)))
    tc = None
    if h.tools:
        tc = [ToolCall(id=t["id"], name=t["name"], arguments=t["args"]) for t in h.tools]
        blocks.extend(ToolCallBlock(type="tool_call", id=t["id"], name=t["name"], input=t["args"]) for t in h.tools)
    inp, out = h.usage.get("in", 0), h.usage.get("out", 0)
    return ChatResponse(content=blocks, tool_calls=tc,
        usage=Usage(input_tokens=inp, output_tokens=out, total_tokens=inp+out),
        finish_reason="tool_use" if tc else "end_turn")

def _to_model_info(raw):
    caps = getattr(raw, "capabilities", None)
    lim = getattr(caps, "limits", None) if caps else None
    sup = getattr(caps, "supports", None) if caps else None
    ctx = getattr(lim, "max_context_window_tokens", 128000) or 128000
    pt = getattr(lim, "max_prompt_tokens", None)
    out = max((ctx - pt), 8192) if pt and pt < ctx else 8192
    ab = ["streaming", "tools"]
    if getattr(sup, "vision", False): ab.append("vision")
    if getattr(sup, "reasoning_effort", False): ab.append("thinking")
    return ModelInfo(id=raw.id, display_name=getattr(raw, "name", raw.id),
        context_window=ctx, max_output_tokens=out, capabilities=ab)

def _translate_error(e, name):
    from amplifier_core import llm_errors
    type_name = type(e).__name__
    mapping = _ERRORS.get(type_name)
    if mapping:
        cls = getattr(llm_errors, mapping["kernel_type"], KernelLLMError)
        return cls(str(e), provider=name, retryable=mapping.get("retryable", True))
    return KernelLLMError(f"Unexpected: {e}", provider=name, retryable=True)
```

**Line count: ~195 lines.** Under 200. With room to spare for the mount function and YAML loading.

---

## The Philosophical Resolution

The Council of Elders debated decomposition vs. monolith. They were arguing about the wrong axis.

The axis isn't **structure** (one file vs. many files). The axis is **necessity** (does this code need to exist at all?).

| Principle | Application |
|-----------|------------|
| **Translation, not framework** | Provider translates. It doesn't cache, detect patterns, repair contexts, or track metrics. |
| **Mechanism with sensible defaults** | Retry policy, error mapping, timeout selection — all policy. YAML. |
| **Design for SDK evolution** | Don't build 359 lines of model naming logic. The SDK's capability field evolves with the SDK. |
| **Occam's Razor** | The simplest provider that translates correctly is the correct provider. |

The 300-line provider doesn't compromise on the Golden Vision's principles. It **fulfills** them more purely than the 17-module decomposition ever could. Because the Golden Vision said "Translation, Not Framework" — and then proposed a framework.

---

## Migration Path

1. **Day 1**: Create `provider-config.yaml`, `error-mapping.yaml`, `model-limits.yaml` from existing constants and code
2. **Day 2**: Write the 200-line `provider.py` with inline event handler
3. **Day 3**: Write the simplified `__init__.py` mount function (~50 lines)
4. **Day 4**: Write the exception classes (8 classes, ~50 lines, no detection helpers)
5. **Day 5**: Delete everything else. Run the test suite. Fix what breaks.

The test suite is the safety net. If the 200-line provider passes all existing tests, the other 5,086 lines were **provably unnecessary**.

If some tests fail, those tests reveal the **actual essential complexity** that the 300-line constraint forces us to identify and justify.

---

## Closing

> *"Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away."* — Antoine de Saint-Exupéry

The 1,799-line provider works. The 17-module decomposition would also work. But neither asks the question that matters: **why do these lines exist?**

300 lines is not a constraint imposed from outside. It's what remains when you remove everything that isn't translation. The SDK knows its models. The kernel handles retries. The orchestrator manages context. The hook system provides observability.

The provider? The provider translates. In 300 lines.

---

**Document Control**

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-08 | Initial provocation — The 300-Line Challenge |

*This document is a challenge to the Golden Vision, not a replacement. It asks: "What if the Vision's own principle — Translation, Not Framework — were applied ruthlessly?"*
