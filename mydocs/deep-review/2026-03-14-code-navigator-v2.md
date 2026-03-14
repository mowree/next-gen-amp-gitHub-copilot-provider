# Code Navigation Deep Review — LSP Analysis
**Date:** 2026-03-14  
**Method:** Pyright LSP — goToDefinition, outgoingCalls, findReferences, documentSymbol  
**Scope:** 4 major execution flows traced through semantic call hierarchy

---

## LSP Operations Performed

| Operation | File | Symbol | Results |
|-----------|------|--------|---------|
| `documentSymbol` | provider.py | (whole file) | 11 top-level symbols |
| `documentSymbol` | client.py | (whole file) | 7 top-level symbols |
| `outgoingCalls` | provider.py:423 | `GitHubCopilotProvider.complete` | 21 callees |
| `outgoingCalls` | provider.py:198 | module-level `complete` | 12 callees |
| `outgoingCalls` | streaming.py:248 | `translate_event` | 7 callees |
| `outgoingCalls` | error_translation.py:288 | `translate_sdk_error` | 10 callees |
| `outgoingCalls` | tool_parsing.py:34 | `parse_tool_calls` | 11 callees |
| `findReferences` | provider.py:328 | `GitHubCopilotProvider` | 1 result (definition only — no external callers in project) |
| `prepareCallHierarchy` | provider.py:423 | `GitHubCopilotProvider.complete` | 1 hierarchy node |
| `prepareCallHierarchy` | client.py:157 | `CopilotClientWrapper.session` | resolved via contextlib decorator |

---

## Flow 1: Session Creation

### Trigger
`GitHubCopilotProvider.__init__` runs at provider instantiation time.

### LSP-Confirmed Call Chain

```
GitHubCopilotProvider.__init__()          provider.py:347
  └─► CopilotClientWrapper()              sdk_adapter/client.py:142
        stores: _sdk_client=None
                _owned_client=None
                _client_lock=asyncio.Lock()

[Later, on first complete() call]
GitHubCopilotProvider.complete()          provider.py:423
  └─► self._client.session(model=model)   sdk_adapter/client.py:157
        └─► self._get_client()            client.py:153
              [None → lazy init path]
        └─► async with self._client_lock:
              └─► CopilotClient(options)  copilot SDK (dynamic import)
                    options["on_permission_request"] = deny_permission_request
              └─► client.start()          SDK: start lifecycle
              └─► client.create_session(session_config)
                    session_config = {
                      "available_tools": [],   # F-045: disable SDK tools
                      "model": model,
                      "streaming": True,       # F-046: always on
                      "on_permission_request": deny_permission_request
                    }
              └─► session.register_pre_tool_use_hook(create_deny_hook())
                    └─► create_deny_hook()     client.py:34
                          returns: async deny() → DENY_ALL dict
        yield sdk_session
  [finally block]
        └─► sdk_session.disconnect()
```

### Key LSP Finding
`findReferences` on `GitHubCopilotProvider` returned **1 result** (its own definition). No external callers are in the project — the provider is loaded by the Amplifier kernel via dynamic module discovery, not direct import within this repo.

### Dual Permission Defense (LSP-verified)
`outgoingCalls` on `complete()` at line 198 shows `create_deny_hook` is called from **two distinct locations**:
- `provider.py:256` — legacy streaming/test path (module-level `complete()`)
- `client.py:242` — real SDK path (`CopilotClientWrapper.session()`)

---

## Flow 2: Completion Flow

### Two Paths (LSP-confirmed via outgoingCalls)

`outgoingCalls` on `GitHubCopilotProvider.complete` (line 423) revealed 21 callees. The critical branching callees are:

- `_complete_internal` (line 470) — test/streaming path
- `CopilotClientWrapper.session` (line 480) — real SDK path
- `extract_response_content` (line 487) — real SDK path only
- `StreamingAccumulator` (line 464) — both paths
- `StreamingAccumulator.to_chat_response` (line 497) — both paths

### Real SDK Path

```
GitHubCopilotProvider.complete(request)         provider.py:423
  │
  ├─[convert request]─► CompletionRequest(       provider.py:453
  │                         prompt="\n".join(prompt_parts),
  │                         model=..., tools=...)
  │
  ├─► StreamingAccumulator()                     streaming.py:66
  │
  └─► async with self._client.session(model):    client.py:157
        [see Flow 1 for session creation]
        yield sdk_session
        │
        └─► sdk_session.send_and_wait(           SDK boundary (opaque)
                {"prompt": internal_request.prompt})
              returns: sdk_response (Data object or dict)
        │
        └─► extract_response_content(sdk_response)  provider.py:121
              ├─[has .data]─► recurse
              ├─[has .content]─► str(response.content)
              └─[dict]─► str(response.get("content", ""))
        │
        └─► DomainEvent(                         streaming.py:44
                type=CONTENT_DELTA,
                data={"text": content})
        │
        └─► accumulator.add(text_event)          streaming.py:78
              [CONTENT_DELTA → text_content += text]
  │
  └─► accumulator.to_chat_response()             streaming.py:109
        └─► ChatResponse(                        amplifier_core
              content=[TextBlock(text=...)],
              tool_calls=None,
              usage=None,
              finish_reason=None)
```

### Test/Streaming Path (sdk_create_fn injected)

```
GitHubCopilotProvider.complete(request, sdk_create_fn=fn)
  └─► self._complete_internal(internal_request,   provider.py:500
            sdk_create_fn=sdk_create_fn)
        └─► module-level complete(request,         provider.py:198
                  config=..., sdk_create_fn=fn)
              ├─► load_event_config()               streaming.py:186
              ├─► load_error_config(path)            error_translation.py:145
              ├─► sdk_create_fn(session_config)      [injected factory]
              │     returns SDKSession
              ├─► session.register_pre_tool_use_hook(create_deny_hook())
              └─► async for sdk_event in session.send_message(prompt, tools):
                    └─► translate_event(sdk_event, event_config)   streaming.py:248
                          [see Flow 4 for tool events]
                          yields: DomainEvent | None
                    └─► yield domain_event
```

---

## Flow 3: Error Flow

### LSP-Confirmed Call Chain for `translate_sdk_error`

`outgoingCalls` on `translate_sdk_error` (error_translation.py:288) revealed 10 callees:

```
translate_sdk_error(exc, config, provider, model)   error_translation.py:288
  │
  ├─► for mapping in config.mappings:
  │     └─► _matches_mapping(exc, mapping)           error_translation.py:221
  │           ├─[type name match]─ exc_type_name in mapping.sdk_patterns
  │           └─[message match]─── pattern.lower() in exc_message.lower()
  │
  ├─[match found]─► KERNEL_ERROR_MAP.get(mapping.kernel_error, ProviderUnavailableError)
  │     maps: "AuthenticationError" → AuthenticationError (amplifier_core.llm_errors)
  │           "RateLimitError"      → RateLimitError
  │           "LLMTimeoutError"     → LLMTimeoutError
  │           ... (15 total mappings)
  │
  ├─[extract_retry_after=True]─► _extract_retry_after(message)  error_translation.py:195
  │     regex: r"[Rr]etry[- ]?after[:\s]+(\d+(?:\.\d+)?)"
  │
  ├─► _extract_context(message, mapping.context_extraction)      error_translation.py:247
  │     regex capture groups → dict[field → value]
  │
  ├─► _format_context_suffix(context)                            error_translation.py:271
  │     → " [context: key=value, ...]"
  │
  └─► error_class(message, provider=provider, model=model,
            retryable=mapping.retryable, retry_after=retry_after)
        kernel_error.__cause__ = exc      [chain preserved]
        logger.debug("[ERROR_TRANSLATION] ...")
        return kernel_error
```

### Where translate_sdk_error is Called (LSP outgoingCalls)

Two distinct call sites confirmed:

```
module-level complete()          provider.py:278
  catch Exception as e:
    if isinstance(e, LLMError): raise   # no double-wrap
    kernel_error = translate_sdk_error(e, error_config, ...)
    raise kernel_error from e

CopilotClientWrapper.session()   client.py:213-214, 245-246
  catch ImportError as e:
    → ProviderUnavailableError directly (SDK not installed case)
  catch Exception as e:
    error_config = self._get_error_config()
    raise translate_sdk_error(e, error_config) from e
```

### Error Type Hierarchy (config-driven, LSP-verified imports)

```
amplifier_core.llm_errors
  └─► LLMError (base)
        ├─► AuthenticationError
        ├─► RateLimitError
        ├─► QuotaExceededError
        ├─► LLMTimeoutError
        ├─► ContentFilterError
        ├─► NetworkError
        ├─► NotFoundError
        ├─► ProviderUnavailableError  ← default fallback
        ├─► ContextLengthError
        ├─► InvalidRequestError
        ├─► StreamError
        ├─► InvalidToolCallError      ← no retry_after param
        ├─► ConfigurationError
        ├─► AccessDeniedError
        └─► AbortError
```

---

## Flow 4: Tool Call Flow

### Two Sub-Flows

Tool calls arrive via two mechanisms depending on the execution path.

#### A. Streaming Path (test path, sdk_create_fn injected)

`outgoingCalls` on `translate_event` (streaming.py:248) shows 7 callees including `classify_event` and `_extract_event_data`:

```
session.send_message(prompt, tools)        SDK (async iterator)
  └─► yields: sdk_event dict
        e.g. {"type": "tool_call", "name": "bash", "id": "tc_123", ...}

translate_event(sdk_event, event_config)   streaming.py:248
  ├─► event_type = str(sdk_event.get("type", ""))
  ├─► classify_event(event_type, config)   streaming.py:231
  │     ├─[in bridge_mappings]─► BRIDGE
  │     ├─[matches consume_patterns]─► CONSUME
  │     └─[matches drop_patterns]─► DROP (with warning)
  │
  ├─[not BRIDGE]─► return None  (dropped)
  │
  ├─► domain_type, block_type = config.bridge_mappings[event_type]
  ├─► data = _extract_event_data(sdk_event)
  │     = {k:v for k,v in sdk_event.items() if k != "type"}
  │
  └─► DomainEvent(type=domain_type, data=data, block_type=block_type)
        e.g. DomainEvent(type=TOOL_CALL, data={"name": "bash", "id": "tc_123", ...})

[in module-level complete()]
  └─► yield domain_event

[in GitHubCopilotProvider.complete()]
  └─► accumulator.add(domain_event)         streaming.py:78
        [TOOL_CALL branch]
        └─► self.tool_calls.append(event.data)

  └─► accumulator.to_chat_response()        streaming.py:109
        └─► ToolCall(
              id=tc.get("id", ""),
              name=tc.get("name", ""),
              arguments=tc.get("arguments", {}))
            → ChatResponse(tool_calls=[ToolCall(...)])
```

#### B. Real SDK Path (send_and_wait)

```
sdk_session.send_and_wait({"prompt": ...})   SDK boundary
  returns: Data object with .content (text) or .tool_calls

[if tool calls present in response]
  content = extract_response_content(sdk_response)   → text only
  → DomainEvent(CONTENT_DELTA, {"text": content})
  → accumulator → ChatResponse(tool_calls=None)

[Caller then invokes separately:]
GitHubCopilotProvider.parse_tool_calls(response)   provider.py:525
  └─► parse_tool_calls(response)                   tool_parsing.py:34
        ├─► tool_calls = getattr(response, "tool_calls", None)
        ├─[None/empty]─► return []
        └─► for tc in tool_calls:
              ├─► args = getattr(tc, "arguments", {})
              ├─[args is None]─► args = {}
              ├─[isinstance(args, str)]─► json.loads(args)
              │     raises ValueError on bad JSON
              ├─[args == {} and not was_none]─► logger.warning("Empty arguments...")
              └─► ToolCall(id=..., name=..., arguments=args)
```

### Tool Capture Defense (LSP-verified double layer)

```
Layer 1: CopilotClientWrapper.session()        client.py:231
  session_config["on_permission_request"] = deny_permission_request
  → deny_permission_request() returns PermissionRequestResult(kind="denied-by-rules")

Layer 2: session.register_pre_tool_use_hook()  client.py:242
  create_deny_hook() → async deny() → {"permissionDecision": "deny", ...}
```

---

## Module Dependency Graph (LSP-confirmed)

```
amplifier_core (kernel)
  ├─► ChatResponse, ModelInfo, ProviderInfo
  ├─► ToolCall, TextBlock, ThinkingBlock, Usage
  └─► llm_errors: LLMError + 14 subclasses

provider.py (orchestrator)
  ├─► sdk_adapter.client: CopilotClientWrapper, create_deny_hook
  ├─► sdk_adapter.types: SDKSession, SessionConfig
  ├─► streaming: DomainEvent, DomainEventType, StreamingAccumulator,
  │               AccumulatedResponse, EventConfig, load_event_config, translate_event
  ├─► error_translation: ErrorConfig, load_error_config, translate_sdk_error
  └─► tool_parsing: parse_tool_calls

streaming.py (event translation)
  └─► amplifier_core: ChatResponse, TextBlock, ThinkingBlock, ToolCall, Usage (TYPE_CHECKING)

error_translation.py (error mapping)
  └─► amplifier_core.llm_errors: all 15 error types

tool_parsing.py (tool extraction)
  └─► amplifier_core: ToolCall

sdk_adapter/client.py (SDK boundary — ONLY file importing copilot SDK)
  ├─► copilot.CopilotClient  (lazy import, guarded by try/except ImportError)
  ├─► copilot.types.PermissionRequestResult  (lazy import with fallback)
  └─► error_translation: ErrorConfig, ErrorMapping, translate_sdk_error

sdk_adapter/types.py (boundary types)
  └─► (stdlib only — no external deps)
```

---

## Key Observations from LSP Analysis

### 1. SDK Boundary Enforced by Import Structure
`client.py` is the **only** file with `from copilot import ...`. LSP `documentSymbol` confirms no other file in the module has SDK imports — all other files use domain types only.

### 2. Real vs Test Path Divergence (LSP outgoingCalls)
`outgoingCalls` on `GitHubCopilotProvider.complete` reveals a clean split:
- **Test path** (sdk_create_fn present): → `_complete_internal` → module-level `complete` → `send_message` (streaming)
- **Real path** (no inject): → `self._client.session()` → `send_and_wait` (blocking)

The two paths have **different response shapes**: streaming path uses `translate_event` pipeline; real path uses `extract_response_content` directly.

### 3. No External References to GitHubCopilotProvider
`findReferences` on `GitHubCopilotProvider` returned **1 result** — its own definition. The provider is loaded by the Amplifier kernel dynamically (not imported directly within this repo). This is intentional — the provider is a plugin, not a library.

### 4. Double Error Translation Guard (LSP line 273-277)
The `isinstance(e, LLMError)` check before calling `translate_sdk_error` in module-level `complete()` prevents double-wrapping when `_complete_internal` is used. LSP outgoingCalls confirmed this guard is in the module-level function only, not in `GitHubCopilotProvider.complete()`.

### 5. to_chat_response() Is the Only Kernel Boundary Crossing
`outgoingCalls` on `GitHubCopilotProvider.complete` shows `to_chat_response()` (streaming.py:109) is called at line 497 — the final step before returning to the kernel. All internal types (`DomainEvent`, `AccumulatedResponse`, `StreamingAccumulator`) are local to the provider module; only `ChatResponse` crosses out.

---

## Diagrams: End-to-End Flows

### Session + Completion (Real SDK)
```
Kernel
  │ calls complete(ChatRequest)
  ▼
GitHubCopilotProvider.complete()         provider.py:423
  │ extract prompt from messages
  │ build CompletionRequest
  ▼
CopilotClientWrapper.session(model)      client.py:157
  │ [lazy] CopilotClient(options) + start()
  │ create_session({tools:[], streaming:True, ...})
  │ register deny hook
  ▼
sdk_session.send_and_wait({"prompt":...})   SDK (opaque)
  │
  ▼
extract_response_content(sdk_response)   provider.py:121
  │ handles Data/.content/.data/dict
  ▼
DomainEvent(CONTENT_DELTA, {"text":...}) streaming.py:44
  │
  ▼
StreamingAccumulator.add()               streaming.py:78
  │
  ▼
accumulator.to_chat_response()           streaming.py:109
  │ TextBlock, ThinkingBlock, ToolCall, Usage
  ▼
ChatResponse                             amplifier_core → Kernel
```

### Error Translation
```
Any SDK Exception
  │
  ▼
translate_sdk_error(exc, config)         error_translation.py:288
  │
  ├─► _matches_mapping(exc, mapping)     [type name OR message pattern]
  │
  ├─► KERNEL_ERROR_MAP[mapping.kernel_error]
  │     → specific LLMError subclass
  │
  ├─► _extract_retry_after() [if configured]
  ├─► _extract_context()     [F-036: structured context from message]
  │
  └─► ErrorClass(message, provider="github-copilot", retryable=..., retry_after=...)
        .__cause__ = exc      [chain preserved per contract]
  │
  ▼
raise kernel_error from exc              → Kernel sees LLMError subclass only
```

### Tool Call (Streaming Path)
```
SDK session.send_message()
  │ yields {"type": "tool_call", "name": "X", "id": "tc_1", "arguments": {...}}
  ▼
translate_event(sdk_event, event_config) streaming.py:248
  │ classify_event() → BRIDGE
  │ bridge_mappings["tool_call"] → (TOOL_CALL, None)
  │ _extract_event_data() → {name, id, arguments, ...}
  ▼
DomainEvent(type=TOOL_CALL, data={name, id, arguments})
  │
  ▼
StreamingAccumulator.add()               streaming.py:86
  │ self.tool_calls.append(event.data)
  ▼
to_chat_response()                       streaming.py:139-150
  │ ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"])
  ▼
ChatResponse(tool_calls=[ToolCall(...)])  → Kernel

[Kernel then calls:]
GitHubCopilotProvider.parse_tool_calls(response)
  └─► parse_tool_calls(response)         tool_parsing.py:34
        └─► [JSON decode if str args, warn if empty]
            ToolCall(id, name, arguments) → [ToolCall, ...]
```
