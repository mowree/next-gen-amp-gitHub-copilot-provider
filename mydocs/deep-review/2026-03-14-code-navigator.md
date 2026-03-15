# Code Navigation Analysis
**Date:** 2026-03-14  
**Project:** next-get-provider-github-copilot  
**Method:** Source inspection + LSP (LSP server unavailable — filesystem state issue)

---

## Overview

The codebase is organized as a thin orchestration layer (`provider.py`) over three specialized modules:

| Module | Role |
|--------|------|
| `sdk_adapter/client.py` | Only file allowed to import from `copilot` SDK |
| `sdk_adapter/types.py` | Opaque boundary types (`SessionConfig`, `SDKSession = Any`) |
| `streaming.py` | Event translation, accumulation, → `ChatResponse` |
| `error_translation.py` | Config-driven SDK error → kernel `LLMError` |
| `tool_parsing.py` | Extract `ToolCall` objects from response |

---

## Flow 1: Session Creation

### Entry Points

```
GitHubCopilotProvider.__init__()          provider.py:347
  └─ CopilotClientWrapper()               client.py:142
       └─ self._sdk_client = None         (lazy init)
       └─ self._client_lock = Lock()      (race-condition guard)
```

### Lazy Initialization Path (first `complete()` call)

```
GitHubCopilotProvider.complete()          provider.py:423
  └─ self._client.session(model=...)      client.py:157
       └─ CopilotClientWrapper.session()  [asynccontextmanager]
            └─ _get_client() → None
            └─ acquire self._client_lock
            └─ double-check → still None
            └─ from copilot import CopilotClient   [ONLY SDK import site]
            └─ _resolve_token()           client.py:116
                 └─ os.environ.get(...)   (COPILOT_AGENT_TOKEN → ... → GITHUB_TOKEN)
            └─ options["on_permission_request"] = deny_permission_request
            └─ self._owned_client = CopilotClient(options)
            └─ await self._owned_client.start()
            └─ client.create_session(session_config)
                 session_config = {
                   "available_tools": [],   # F-045: disable SDK tools
                   "model": model,
                   "streaming": True,       # F-046: always streaming
                   "on_permission_request": deny_permission_request,
                 }
            └─ session.register_pre_tool_use_hook(create_deny_hook())
            └─ yield sdk_session
       └─ [finally] sdk_session.disconnect()
```

### Deny Hooks (Two Lines of Defense)

```
deny_permission_request()               client.py:43   ← SDK asks "may I do X?"
  └─ returns PermissionRequestResult(kind="denied-by-rules")

create_deny_hook()                      client.py:34   ← pre_tool_use callback
  └─ returns async deny() → {"permissionDecision": "deny"}
```

### Test Path (sdk_create_fn injection)

```
GitHubCopilotProvider.complete()
  └─ sdk_create_fn = kwargs["sdk_create_fn"] or self._complete_fn
  └─ self._complete_internal(request, sdk_create_fn=sdk_create_fn)
       └─ complete() [module-level]      provider.py:198
            └─ sdk_create_fn(session_config)  ← calls injected factory
            └─ session.register_pre_tool_use_hook(create_deny_hook())
```

---

## Flow 2: Completion (User Message → SDK → Response)

### Real SDK Path

```
caller
  └─ GitHubCopilotProvider.complete(request)       provider.py:423
       └─ [message extraction]
            request.messages → [msg.content] → prompt_parts
            → CompletionRequest(prompt="\n".join(parts), model=..., tools=...)
       └─ StreamingAccumulator()                    streaming.py:67
       └─ self._client.session(model=model)
            └─ [session creation — see Flow 1]
            └─ sdk_session.send_and_wait({"prompt": ...})    ← SDK call
            └─ extract_response_content(sdk_response)        provider.py:121
                 handles: response.data → response.content → dict["content"]
            └─ DomainEvent(type=CONTENT_DELTA, data={"text": content})
            └─ accumulator.add(event)
       └─ accumulator.to_chat_response()            streaming.py:109
            └─ TextBlock(text=...) / ThinkingBlock(thinking=...)
            └─ ToolCall(id=..., name=..., arguments=...)
            └─ Usage(input_tokens=..., output_tokens=..., total_tokens=...)
            └─ ChatResponse(content=..., tool_calls=..., usage=..., finish_reason=...)
       └─ returns ChatResponse                      ← kernel type
```

### Test/Streaming Path (sdk_create_fn)

```
GitHubCopilotProvider.complete(request, sdk_create_fn=fn)
  └─ GitHubCopilotProvider._complete_internal()    provider.py:500
       └─ complete() [module-level]                provider.py:198
            └─ load_event_config()                 streaming.py:186
            └─ load_error_config(errors.yaml)      error_translation.py:145
            └─ SessionConfig(model=...)
            └─ sdk_create_fn(session_config) → SDKSession
            └─ session.register_pre_tool_use_hook(create_deny_hook())
            └─ async for sdk_event in session.send_message(prompt, tools):
                 └─ translate_event(sdk_event, event_config)   streaming.py:248
                      └─ classify_event(event_type, config)    streaming.py:231
                           BRIDGE → DomainEvent(domain_type, data, block_type)
                           CONSUME/DROP → None
                 └─ yield DomainEvent
       └─ accumulator.add(event)  [for each event]
  └─ accumulator.to_chat_response()
```

### Event Translation Detail

```
translate_event(sdk_event, config)        streaming.py:248
  └─ event_type = sdk_event["type"]
  └─ classify_event(event_type, config)
       └─ event_type in config.bridge_mappings  → BRIDGE
       └─ fnmatch(event_type, consume_patterns) → CONSUME
       └─ fnmatch(event_type, drop_patterns)    → DROP
       └─ else: WARNING + DROP
  └─ if BRIDGE:
       domain_type, block_type = config.bridge_mappings[event_type]
       data = {k:v for k,v in sdk_event.items() if k != "type"}
       if TURN_COMPLETE: apply finish_reason_map
       return DomainEvent(type=domain_type, data=data, block_type=block_type)
  └─ else: return None
```

### StreamingAccumulator.add() Dispatch

```
CONTENT_DELTA  → if block_type == "THINKING": thinking_content += text
                 else: text_content += text
TOOL_CALL      → tool_calls.append(event.data)
USAGE_UPDATE   → usage = event.data
TURN_COMPLETE  → finish_reason = data["finish_reason"]; is_complete = True
ERROR          → error = event.data; is_complete = True
```

---

## Flow 3: Error Translation (SDK Error → Domain Error)

### Trigger Sites

Two sites where SDK exceptions are caught and translated:

```
[Site A] CopilotClientWrapper.session()     client.py:212,244,246
  └─ ImportError (SDK not installed)
       → ProviderUnavailableError("Copilot SDK not installed")
  └─ Exception during client.start()
       → translate_sdk_error(e, error_config)
  └─ Exception during client.create_session()
       → translate_sdk_error(e, error_config)

[Site B] complete() [module-level]          provider.py:272-284
  └─ catches all Exception
  └─ if isinstance(e, LLMError): raise  (no double-wrap)
  └─ else: translate_sdk_error(e, error_config, provider=..., model=...)
           raise kernel_error from e
```

### translate_sdk_error() Call Graph

```
translate_sdk_error(exc, config, provider, model)     error_translation.py:288
  └─ for mapping in config.mappings:
       └─ _matches_mapping(exc, mapping)              error_translation.py:221
            └─ type(exc).__name__ in sdk_patterns     (type name match)
            └─ pattern.lower() in str(exc).lower()    (message match)
       └─ if matched:
            └─ KERNEL_ERROR_MAP[mapping.kernel_error] → error_class
            └─ if mapping.extract_retry_after:
                 _extract_retry_after(message)        error_translation.py:195
                   └─ re.search("Retry-after: N")
            └─ _extract_context(message, context_extraction)  error_translation.py:247
                 └─ re.search(pattern) for each extraction
            └─ if error_class is InvalidToolCallError:
                 error_class(msg, provider, model, retryable)
               else:
                 error_class(msg, provider, model, retryable, retry_after)
            └─ kernel_error.__cause__ = exc
            └─ logger.debug("[ERROR_TRANSLATION] ...")
            └─ return kernel_error
  └─ no match: default_class(msg, provider, model, retryable)
```

### Kernel Error Class Hierarchy (from amplifier_core.llm_errors)

```
LLMError (base)
  ├─ AuthenticationError
  ├─ RateLimitError
  ├─ QuotaExceededError
  ├─ LLMTimeoutError
  ├─ ContentFilterError
  ├─ NetworkError
  ├─ NotFoundError
  ├─ ProviderUnavailableError  ← default fallback
  ├─ ContextLengthError
  ├─ InvalidRequestError
  ├─ StreamError
  ├─ InvalidToolCallError      ← no retry_after param
  ├─ ConfigurationError
  ├─ AccessDeniedError
  └─ AbortError
```

### Error Config Loading

```
[At client init]
_load_error_config_once()               client.py:72
  └─ importlib.resources.files("config").joinpath("errors.yaml")  [prod path]
  └─ fallback: Path(__file__).parent.parent.parent.parent / "config/errors.yaml"

[At complete() call]
load_error_config(package_root / "config" / "errors.yaml")  error_translation.py:145
  └─ yaml.safe_load() → ErrorConfig(mappings=[...], default_error=..., default_retryable=...)
```

---

## Flow 4: Tool Call (SDK Event → Parser → Amplifier ToolCall)

### Capture Path (streaming)

```
[During streaming in test/internal path]
session.send_message(prompt, tools)     → async SDK event stream
  └─ sdk_event with type == "ASSISTANT_MESSAGE" (or similar bridge type)
  └─ translate_event() → DomainEvent(type=TOOL_CALL, data={...})
  └─ StreamingAccumulator.add(event)
       └─ self.tool_calls.append(event.data)

[During accumulator → ChatResponse]
StreamingAccumulator.to_chat_response()    streaming.py:109
  └─ for tc in self.tool_calls:
       ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"])
  └─ ChatResponse(tool_calls=[ToolCall(...), ...])
```

### Parse Path (explicit caller)

```
GitHubCopilotProvider.parse_tool_calls(response)    provider.py:525
  └─ parse_tool_calls(response)                     tool_parsing.py:34
       └─ tool_calls = getattr(response, "tool_calls", None)
       └─ if not tool_calls: return []
       └─ for tc in tool_calls:
            args = getattr(tc, "arguments", {})
            if args is None: args = {}
            elif isinstance(args, str): args = json.loads(args)    [JSON parse]
            if args == {} and not args_was_none:
              logger.warning("[TOOL_PARSING] Empty arguments ...")  [F-037]
            ToolCall(id=..., name=..., arguments=args)
       └─ return [ToolCall, ...]
```

### Deny Hook Integration (prevents SDK from executing tools)

```
[Hook registration — session creation]
session.register_pre_tool_use_hook(create_deny_hook())
  └─ create_deny_hook() → async deny(input_data, invocation) → DENY_ALL

[Hook registration — permission handler]
options["on_permission_request"] = deny_permission_request
session_config["on_permission_request"] = deny_permission_request
  └─ deny_permission_request() → PermissionRequestResult(kind="denied-by-rules")

[Effect]
SDK tool execution is blocked at two layers.
Tool calls are captured as streaming events by Amplifier instead.
```

---

## Module Dependency Graph

```
provider.py
  ├─── sdk_adapter/client.py      [session management, SDK import isolation]
  │         └─── sdk_adapter/types.py   [SessionConfig, SDKSession]
  │         └─── error_translation.py   [translate_sdk_error at client boundary]
  ├─── sdk_adapter/types.py       [SessionConfig, SDKSession type alias]
  ├─── streaming.py               [DomainEvent, StreamingAccumulator, translate_event]
  ├─── error_translation.py       [translate_sdk_error, load_error_config]
  └─── tool_parsing.py            [parse_tool_calls]

External kernel types (amplifier_core):
  provider.py     → ChatResponse, ModelInfo, ProviderInfo, ToolCall
  streaming.py    → ChatResponse, TextBlock, ThinkingBlock, ToolCall, Usage
  error_translation.py → LLMError and all subclasses (from amplifier_core.llm_errors)
  tool_parsing.py → ToolCall
```

---

## Key Design Invariants

| Invariant | Where Enforced |
|-----------|---------------|
| SDK import isolation | Only `sdk_adapter/client.py` imports `copilot.*` |
| Session always destroyed | `client.py` `finally: sdk_session.disconnect()` |
| Tools always denied at SDK | Two hooks: `pre_tool_use` + `on_permission_request` |
| SDK errors never leak | Caught at `complete()` module-level + `client.session()` |
| No double-wrap of LLMError | `isinstance(e, LLMError)` check before translate |
| Config-driven mappings | `errors.yaml` + `events.yaml` — no hardcoded patterns |
| Kernel types at boundary | `to_chat_response()` converts internal → `ChatResponse` |

---

## LSP Server Status

The Pyright LSP server failed to start during this session due to a filesystem state issue (`/home/mowrim/.amplifier/lsp-servers/` directory missing). Analysis above is based on direct source inspection of all five modules. All symbol references, call sites, and data flows were manually traced from the actual source code.

---

## PRINCIPAL REVIEW AND AMENDMENTS

**Reviewed:** 2026-03-15  
**Verdict:** One invariant in the Key Design Invariants table is **FALSE**. All other findings confirmed correct.

---

### FALSE INVARIANT: "SDK errors never leak"

The document claimed:

> | SDK errors never leak | Caught at `complete()` module-level + `client.session()` |

**This is incorrect.** The real SDK execution path has no error translation coverage.

#### Code Evidence

**`provider.py` lines 477–495 — Real SDK path has NO try/except:**

```python
else:
    # Real SDK path: use client wrapper
    model = internal_request.model or "gpt-4o"
    async with self._client.session(model=model) as sdk_session:
        # NO try/except here
        sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
        if sdk_response is not None:
            content = extract_response_content(sdk_response)
            text_event = DomainEvent(...)
            accumulator.add(text_event)
```

**`client.py` lines 248–256 — `yield` block has only `finally`, no `except`:**

```python
try:
    yield sdk_session          # <-- exceptions from send_and_wait() bubble from here
finally:
    if sdk_session is not None:
        try:
            await sdk_session.disconnect()
        except Exception as disconnect_err:
            logger.warning(...)
```

If `sdk_session.send_and_wait()` raises, the exception propagates uncaught through the `yield`, through `provider.py`, and up to the kernel as a raw SDK exception.

#### What IS caught (corrected scope)

| Site | What is caught | What is NOT covered |
|------|---------------|---------------------|
| `client.py:212,244,246` — `except Exception` before `yield` | `ImportError` (SDK missing), errors during `client.start()`, errors during `client.create_session()` | Errors during `send_and_wait()` after session is established |
| `provider.py:272-284` — `complete()` module-level `except Exception` | All exceptions in the **test/`_complete_internal` path** | The real SDK `else` branch — this block is not reached from `GitHubCopilotProvider.complete()` directly |

#### Corrected Invariants Table

| Invariant | Where Enforced | Status |
|-----------|---------------|--------|
| SDK import isolation | Only `sdk_adapter/client.py` imports `copilot.*` | ✅ Correct |
| Session always destroyed | `client.py` `finally: sdk_session.disconnect()` | ✅ Correct |
| Tools always denied at SDK | Two hooks: `pre_tool_use` + `on_permission_request` | ✅ Correct |
| SDK errors never leak | **FALSE** — real SDK path (`send_and_wait`) has no error translation | ❌ **BUG** |
| No double-wrap of LLMError | `isinstance(e, LLMError)` check before translate | ✅ Correct (test path only) |
| Config-driven mappings | `errors.yaml` + `events.yaml` — no hardcoded patterns | ✅ Correct |
| Kernel types at boundary | `to_chat_response()` converts internal → `ChatResponse` | ✅ Correct |

---

### Root Cause Analysis

The F-039/F-040 refactoring split `complete()` into two parallel paths:

1. **Test path** (`sdk_create_fn` injected) → calls `_complete_internal()` → calls module-level `complete()` → **has** `except Exception` at lines 272-284 → errors translated ✅
2. **Real SDK path** (`else` branch) → inline `async with self._client.session()` + `send_and_wait()` → **no** `except Exception` → errors bubble raw ❌

The error handling was only implemented in the test path. The real SDK path was left unprotected, violating the contract in `error-hierarchy.md`:

> "The provider MUST translate SDK errors into kernel error types"

This is the same systemic gap identified in the `code-navigator-v2.md` review, confirming it is a structural issue introduced by the parallel-path refactoring, not an isolated oversight.

---

### Remediation

**Spec F-072** covers the fix. The real SDK path in `GitHubCopilotProvider.complete()` (lines 477-495) requires a `try/except Exception` block wrapping the `send_and_wait()` call, with `translate_sdk_error()` applied before re-raising — matching the pattern already present in the test path at `provider.py:272-284`.
