# WAVE 2, AGENT 20: Modular Architecture for GitHub Copilot Provider

**Date**: 2026-03-08
**Scope**: Decomposition of 1799-line `provider.py` + 5286-line package into AI-maintainable modules
**Philosophy**: Occam's Razor — as simple as possible, but no simpler

---

## Executive Summary

The current `provider.py` at 1799 lines is an AI-hostile monolith. An AI agent editing any function must hold the entire file in context, risking unintended mutations to unrelated code. The existing package already has good decomposition for supporting concerns (client, converters, sdk_driver, etc.), but the core provider remains a god-class with 7+ distinct responsibilities tangled into one file.

The decomposition strategy is **surgical, not revolutionary**: we split `provider.py` into focused modules while preserving the existing well-structured modules (`client.py`, `converters.py`, `sdk_driver.py`, etc.) that are already right-sized. The goal is every module under 400 lines, every responsibility in exactly one place.

---

## 1. Module Inventory

### 1.1 Current State (13 modules, 5286 lines)

| Module | Lines | Status |
|--------|-------|--------|
| `provider.py` | 1799 | **DECOMPOSE** — god-class |
| `client.py` | 820 | **KEEP** — already focused (session lifecycle) |
| `sdk_driver.py` | 620 | **KEEP** — already focused (loop control) |
| `converters.py` | 426 | **KEEP** — already focused (format conversion) |
| `model_cache.py` | 415 | **KEEP** — already focused (disk cache) |
| `model_naming.py` | 359 | **KEEP** — already focused (naming conventions) |
| `exceptions.py` | 322 | **KEEP** — already focused (error hierarchy) |
| `_constants.py` | 312 | **KEEP** — already focused (configuration values) |
| `models.py` | 292 | **KEEP** — already focused (model mapping) |
| `_platform.py` | 280 | **KEEP** — already focused (binary location) |
| `tool_capture.py` | 218 | **KEEP** — already focused (deny + capture) |
| `__init__.py` | 371 | **SIMPLIFY** — singleton + mount logic |
| `_permissions.py` | 52 | **KEEP** — already minimal |

### 1.2 Target State (17 modules, ~5400 lines)

The decomposition extracts 5 new modules from `provider.py` and slims `__init__.py`:

| Module | Lines (target) | Responsibility | Extracted From |
|--------|---------------|----------------|----------------|
| **`provider.py`** | **~300** | Thin orchestrator: 5-method protocol, dependency wiring | Current provider.py (skeleton) |
| **`completion.py`** | **~350** | `_complete_non_streaming()`, `_complete_streaming()`, response assembly | provider.py lines 1140-1400 |
| **`error_translation.py`** | **~200** | SDK→Kernel error mapping, rate-limit detection, content-filter detection | provider.py lines 976-1049, exceptions.py detection helpers |
| **`tool_parsing.py`** | **~250** | `parse_tool_calls()`, fake tool call detection, retry logic, missing tool result repair | provider.py lines 1076-1138, 1596-1783 |
| **`session_factory.py`** | **~250** | Session configuration building, tool registration, system message extraction | provider.py lines 800-975 |
| **`streaming.py`** | **~200** | Streaming event handler, content emission, delta assembly | provider.py lines 1200-1350 |
| `client.py` | 820 | *Unchanged* — SDK client lifecycle | — |
| `sdk_driver.py` | 620 | *Unchanged* — loop control, circuit breaker | — |
| `converters.py` | 426 | *Unchanged* — message format conversion | — |
| `model_cache.py` | 415 | *Unchanged* — disk-persistent cache | — |
| `model_naming.py` | 359 | *Unchanged* — naming conventions | — |
| `exceptions.py` | 322 | *Unchanged* — exception hierarchy | — |
| `_constants.py` | 312 | *Unchanged* — constants | — |
| `models.py` | 292 | *Unchanged* — model info mapping | — |
| `_platform.py` | 280 | *Unchanged* — platform detection | — |
| `tool_capture.py` | 218 | *Unchanged* — deny hook + capture | — |
| `__init__.py` | ~300 | Simplified mount + singleton | — |
| `_permissions.py` | 52 | *Unchanged* — file permissions | — |

**Net result**: `provider.py` drops from 1799 → ~300 lines. Five new modules average ~250 lines each. Total package grows by ~100 lines (module docstrings, imports) but every file is under 400 lines.

---

## 2. Dependency Graph

### 2.1 Full Module Dependency Diagram

```
                          ┌──────────────┐
                          │  __init__.py  │
                          │  (mount/     │
                          │   singleton)  │
                          └──────┬───────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │             │
                    ▼            ▼             ▼
            ┌──────────┐  ┌──────────┐  ┌──────────────┐
            │ client.py │  │provider.py│  │ models.py    │
            │ (SDK      │  │(orchestr.)│  │ (model info) │
            │  lifecycle)│  └─────┬────┘  └──────────────┘
            └─────┬────┘        │
                  │        ┌────┼────────┬──────────┬──────────┐
                  │        │    │        │          │          │
                  │        ▼    ▼        ▼          ▼          ▼
                  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
                  │  │session_ │ │completion│ │  tool_   │ │streaming │
                  │  │factory  │ │  .py     │ │ parsing  │ │  .py     │
                  │  │  .py    │ │          │ │  .py     │ │          │
                  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
                  │       │          │           │           │
                  │       │          ▼           │           │
                  │       │   ┌──────────────┐   │           │
                  │       │   │   error_     │   │           │
                  │       │   │ translation  │   │           │
                  │       │   │    .py       │   │           │
                  │       │   └──────┬───────┘   │           │
                  │       │          │           │           │
                  ▼       ▼          ▼           ▼           ▼
            ┌─────────────────────────────────────────────────────┐
            │                   LEAF MODULES                      │
            │  ┌────────────┐ ┌───────────┐ ┌──────────────────┐ │
            │  │ converters │ │exceptions │ │  _constants.py   │ │
            │  │   .py      │ │   .py     │ │                  │ │
            │  └────────────┘ └───────────┘ └──────────────────┘ │
            │  ┌────────────┐ ┌───────────┐ ┌──────────────────┐ │
            │  │tool_capture│ │sdk_driver │ │  model_naming    │ │
            │  │   .py      │ │   .py     │ │     .py          │ │
            │  └────────────┘ └───────────┘ └──────────────────┘ │
            │  ┌────────────┐ ┌───────────┐ ┌──────────────────┐ │
            │  │model_cache │ │ _platform │ │  _permissions    │ │
            │  │   .py      │ │   .py     │ │     .py          │ │
            │  └────────────┘ └───────────┘ └──────────────────┘ │
            └─────────────────────────────────────────────────────┘
```

### 2.2 Layering Rules

**Layer 0 — Leaf modules** (no internal imports):
- `_constants.py` — imports only `enum`
- `exceptions.py` — imports only stdlib
- `_permissions.py` — imports only `os`, `stat`
- `_platform.py` — imports only `sys`, `shutil`, `pathlib`
- `model_naming.py` — pure Python

**Layer 1 — Foundation modules** (import only Layer 0):
- `converters.py` → `_constants`, `amplifier_core`
- `tool_capture.py` → `_constants`, `copilot.types`
- `sdk_driver.py` → `_constants`, `exceptions`
- `model_cache.py` → `_constants`

**Layer 2 — Domain modules** (import Layers 0-1):
- `models.py` → `_constants`, `client.py`, `amplifier_core`
- `error_translation.py` → `exceptions`, `_constants`
- `tool_parsing.py` → `converters`, `exceptions`, `_constants`
- `session_factory.py` → `tool_capture`, `converters`, `_constants`, `model_naming`
- `streaming.py` → `sdk_driver`, `_constants`

**Layer 3 — Orchestration modules** (import Layers 0-2):
- `completion.py` → `session_factory`, `streaming`, `error_translation`, `sdk_driver`, `client`
- `provider.py` → `completion`, `tool_parsing`, `models`, `model_cache`, `error_translation`

**Layer 4 — Entry point** (imports Layer 3):
- `__init__.py` → `provider`, `client`

### 2.3 Circular Dependency Prevention Rules

1. **Imports flow DOWN layers only.** Layer 2 never imports from Layer 3. Layer 1 never imports from Layer 2.
2. **No sibling imports within the same layer** unless explicitly documented (e.g., `completion.py` may import `streaming.py` since streaming is a subroutine of completion).
3. **`from __future__ import annotations`** in every file — breaks runtime circular import from type hints.
4. **Shared state lives in `_constants.py`** (Layer 0), not passed between peers.
5. **Coordinator reference flows down via constructor**, not via module-level import. `provider.py` receives `coordinator` and passes it to `completion.py`, which passes it to `streaming.py`.

---

## 3. Interface Design

### 3.1 New Module: `provider.py` (Thin Orchestrator)

```python
"""
GitHub Copilot provider — thin orchestrator implementing the 5-method Amplifier protocol.

Responsibilities:
- Wire together completion, tool_parsing, models, and error_translation
- Implement Provider protocol (name, get_info, list_models, complete, parse_tool_calls)
- Manage provider configuration and coordinator reference

NOT responsible for:
- Session creation (see session_factory.py)
- Streaming logic (see streaming.py)
- Error classification (see error_translation.py)
- Tool call parsing details (see tool_parsing.py)
"""

class CopilotSdkProvider:
    """Amplifier Provider protocol implementation."""

    # --- Protocol methods ---
    @property
    def name(self) -> str: ...

    def get_info(self) -> ProviderInfo: ...

    async def list_models(self) -> list[ModelInfo]: ...

    async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse: ...

    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]: ...

    # --- Internal wiring ---
    def __init__(self, config: dict, coordinator: ModuleCoordinator,
                 client: CopilotClientWrapper): ...
```

**Public API**: `CopilotSdkProvider` class only.
**Size target**: ~300 lines.

### 3.2 New Module: `completion.py` (Completion Engine)

```python
"""
Completion engine — handles the actual LLM call lifecycle.

Responsibilities:
- Non-streaming completion flow (send_and_wait)
- Streaming completion flow (send + event collection)
- Response assembly from SDK events into ChatResponse
- Timeout management with SDK timeout buffer

NOT responsible for:
- Session creation/configuration (see session_factory.py)
- Error classification (see error_translation.py)
- Tool call parsing (see tool_parsing.py)
"""

async def complete_non_streaming(
    client: CopilotClientWrapper,
    session_config: SessionConfig,
    prompt: str,
    timeout: float,
    *,
    emit_event: EventCallback | None = None,
) -> CompletionResult: ...

async def complete_streaming(
    client: CopilotClientWrapper,
    session_config: SessionConfig,
    prompt: str,
    timeout: float,
    *,
    emit_event: EventCallback | None = None,
    streaming_handler: StreamingHandler | None = None,
) -> CompletionResult: ...

@dataclass(frozen=True)
class CompletionResult:
    """Intermediate result before ChatResponse assembly."""
    content: str
    tool_calls: list[dict]
    usage: Usage | None
    finish_reason: str
    raw_response: dict | None  # For debug/raw mode
```

**Public API**: `complete_non_streaming()`, `complete_streaming()`, `CompletionResult`.
**Size target**: ~350 lines.

### 3.3 New Module: `error_translation.py` (Error Boundary)

```python
"""
Error translation layer — maps SDK/Copilot errors to Amplifier kernel errors.

Responsibilities:
- Translate CopilotProviderError hierarchy to KernelLLMError hierarchy
- Detect rate-limit errors from unstructured error messages
- Detect content-filter errors from unstructured error messages
- Determine retryability of each error type

NOT responsible for:
- Defining the exception classes (see exceptions.py)
- Retry logic (handled by amplifier_core.utils.retry)
"""

def translate_error(error: Exception) -> KernelLLMError:
    """Translate a Copilot SDK error into a Kernel LLM error."""
    ...

def is_retryable(error: KernelLLMError) -> bool:
    """Determine if an error should be retried by the orchestrator."""
    ...

def detect_rate_limit(error: Exception) -> CopilotRateLimitError | None:
    """Detect rate-limit condition from unstructured error messages."""
    ...

def detect_content_filter(error: Exception) -> CopilotContentFilterError | None:
    """Detect content-filter condition from unstructured error messages."""
    ...
```

**Public API**: `translate_error()`, `is_retryable()`, `detect_rate_limit()`, `detect_content_filter()`.
**Size target**: ~200 lines.

### 3.4 New Module: `tool_parsing.py` (Tool Call Processing)

```python
"""
Tool call processing — parsing, validation, fake detection, and repair.

Responsibilities:
- Parse tool calls from ChatResponse content
- Detect fake tool calls (LLM writing tool XML as text)
- Generate correction messages for fake tool call retry
- Repair missing tool results in conversation history
- Track repaired tool IDs with LRU eviction

NOT responsible for:
- Tool registration with SDK (see tool_capture.py)
- Tool execution (handled by Amplifier orchestrator)
- Session management (see session_factory.py)
"""

def parse_tool_calls_from_response(
    response: ChatResponse,
    converters: module,
) -> list[ToolCall]: ...

def detect_fake_tool_calls(content: str) -> list[FakeToolCall]: ...

def build_correction_message(fake_calls: list[FakeToolCall]) -> str: ...

class ToolResultRepairer:
    """Tracks and repairs missing tool results in conversation history."""

    def __init__(self, max_tracked: int = MAX_REPAIRED_TOOL_IDS): ...

    def repair_missing_results(
        self, messages: list[Message]
    ) -> list[Message]: ...
```

**Public API**: `parse_tool_calls_from_response()`, `detect_fake_tool_calls()`, `build_correction_message()`, `ToolResultRepairer`.
**Size target**: ~250 lines.

### 3.5 New Module: `session_factory.py` (Session Configuration)

```python
"""
Session factory — builds SDK session configuration from Amplifier requests.

Responsibilities:
- Build SessionConfig dict from ChatRequest and provider config
- Extract and format system messages
- Register tools with SDK (user tools + deny hooks)
- Configure excluded built-in tools
- Set reasoning effort and streaming parameters

NOT responsible for:
- Actually creating the SDK session (see client.py)
- Message format conversion (see converters.py)
- Tool capture logic (see tool_capture.py)
"""

def build_session_config(
    request: ChatRequest,
    provider_config: ProviderConfig,
    model_id: str,
    *,
    use_streaming: bool = True,
    reasoning_effort: str | None = None,
) -> SessionConfig: ...

def extract_system_message(messages: list[Message]) -> str | None: ...

def build_tool_list(
    request_tools: list[ToolDef],
    builtin_exclusions: set[str],
) -> tuple[list[Tool], list[str]]: ...

@dataclass(frozen=True)
class ProviderConfig:
    """Resolved provider configuration for session building."""
    timeout: float
    thinking_timeout: float
    sdk_max_turns: int
    debug: bool
    raw: bool
```

**Public API**: `build_session_config()`, `extract_system_message()`, `build_tool_list()`, `ProviderConfig`.
**Size target**: ~250 lines.

### 3.6 New Module: `streaming.py` (Streaming Handler)

```python
"""
Streaming event handler — processes SDK streaming events into Amplifier content.

Responsibilities:
- Subscribe to SDK session events
- Emit streaming content deltas via Amplifier hook system
- Assemble final content from streaming deltas
- Handle reasoning/thinking deltas separately from content deltas

NOT responsible for:
- SDK event loop control (see sdk_driver.py)
- Session lifecycle (see client.py)
- Response assembly into ChatResponse (see completion.py)
"""

class StreamingHandler:
    """Handles SDK streaming events and emits Amplifier content events."""

    def __init__(
        self,
        emit_event: EventCallback,
        *,
        debug: bool = False,
        raw: bool = False,
    ): ...

    def make_event_handler(self) -> Callable: ...

    def get_accumulated_content(self) -> str: ...

    def get_accumulated_thinking(self) -> str | None: ...

    def get_usage(self) -> Usage | None: ...
```

**Public API**: `StreamingHandler` class.
**Size target**: ~200 lines.

### 3.7 Protocol Classes (Cross-Module Contracts)

```python
# Defined in the module that CONSUMES the protocol, not the one that implements it.

# In completion.py — what it needs from the event system
class EventCallback(Protocol):
    async def __call__(self, event_name: str, data: dict[str, Any]) -> None: ...

# In session_factory.py — what it needs from tool definitions
class ToolDef(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def parameters(self) -> dict: ...
```

---

## 4. Package Structure

### 4.1 Directory Layout

```
amplifier_module_provider_github_copilot/
├── __init__.py              # mount(), unmount(), singleton management
├── provider.py              # CopilotSdkProvider (thin orchestrator, ~300 lines)
├── completion.py            # complete_non_streaming(), complete_streaming() (~350 lines)
├── session_factory.py       # build_session_config(), tool/system extraction (~250 lines)
├── streaming.py             # StreamingHandler (~200 lines)
├── error_translation.py     # translate_error(), detection helpers (~200 lines)
├── tool_parsing.py          # parse_tool_calls, fake detection, repair (~250 lines)
├── client.py                # CopilotClientWrapper (UNCHANGED, 820 lines)
├── sdk_driver.py            # SdkEventHandler, LoopController (UNCHANGED, 620 lines)
├── converters.py            # Message format conversion (UNCHANGED, 426 lines)
├── models.py                # CopilotModelInfo, fetch_and_map (UNCHANGED, 292 lines)
├── model_cache.py           # Disk cache with atomic writes (UNCHANGED, 415 lines)
├── model_naming.py          # ID conventions, thinking detection (UNCHANGED, 359 lines)
├── tool_capture.py          # Deny hook, tool bridge (UNCHANGED, 218 lines)
├── exceptions.py            # Exception hierarchy (UNCHANGED, 322 lines)
├── _constants.py            # All constants (UNCHANGED, 312 lines)
├── _platform.py             # Cross-platform binary location (UNCHANGED, 280 lines)
└── _permissions.py          # File permission utilities (UNCHANGED, 52 lines)
```

### 4.2 Why Flat, Not Nested

The Wave 1 Python Architecture report proposed nested subpackages (`auth/`, `client/`, `models/`, `streaming/`, `tools/`, `config/`, `errors/`). **I reject this for this codebase.** Here's why:

1. **The existing codebase is flat.** 13 modules at the same level. Introducing subpackages would require touching every import in every test file — a massive, risky refactor with no functional benefit.

2. **The module count is manageable.** 17 files is not 50. A flat layout with clear naming is navigable. Subpackages add indirection (`from .auth.token_manager import TokenManager` vs. `from .client import CopilotClientWrapper`).

3. **AI agents work better with flat structures.** An AI can `ls` the package and see all modules. Nested packages require recursive exploration.

4. **The existing modules are already well-named.** `client.py`, `converters.py`, `sdk_driver.py` — these names are self-documenting. The new modules follow the same convention: `completion.py`, `session_factory.py`, `streaming.py`, `error_translation.py`, `tool_parsing.py`.

5. **The Kernel Philosophy demands it.** From the kernel internals analysis: "The provider should be thin." A flat package reflects a thin, focused concern. Subpackages imply a framework-scale complexity that doesn't exist here.

### 4.3 `__init__.py` Exports

```python
# amplifier_module_provider_github_copilot/__init__.py

__all__ = [
    "mount",          # Entry point for Amplifier module loading
    "CopilotSdkProvider",  # For type hints and testing
]

# The mount() function is the ONLY public API.
# CopilotSdkProvider is exported for type hints in tests.
# Everything else is internal.
```

### 4.4 Internal Module Visibility

| Module | Visibility | Rationale |
|--------|-----------|-----------|
| `provider.py` | **Semi-public** — exported via `__init__.py` for testing | Protocol implementation |
| `completion.py` | **Internal** — used only by `provider.py` | Implementation detail |
| `session_factory.py` | **Internal** — used only by `completion.py` | Implementation detail |
| `streaming.py` | **Internal** — used only by `completion.py` | Implementation detail |
| `error_translation.py` | **Internal** — used by `provider.py` and `completion.py` | Shared utility |
| `tool_parsing.py` | **Internal** — used only by `provider.py` | Implementation detail |
| `client.py` | **Internal** — used by `__init__.py` and `provider.py` | SDK lifecycle |
| All others | **Internal** | Supporting infrastructure |

---

## 5. Module Boundaries

### 5.1 What Crosses Module Boundaries

**Data objects that flow between modules:**

| Data Type | Origin | Consumers | Notes |
|-----------|--------|-----------|-------|
| `ChatRequest` | Amplifier kernel | `provider.py` → `session_factory.py`, `converters.py` | Immutable, never modified |
| `ChatResponse` | `completion.py` | `provider.py` → Amplifier kernel | Constructed once, returned |
| `CompletionResult` | `completion.py` | `provider.py` | Intermediate before ChatResponse |
| `SessionConfig` | `session_factory.py` | `completion.py` → `client.py` | Dict, passed through |
| `ProviderConfig` | `provider.py` | `session_factory.py`, `completion.py` | Frozen dataclass |
| `list[ToolCall]` | `tool_parsing.py` | `provider.py` → Amplifier kernel | Parsed tool calls |
| `KernelLLMError` | `error_translation.py` | `provider.py` → Amplifier kernel | Raised as exception |
| `list[ModelInfo]` | `models.py` | `provider.py` → Amplifier kernel | Model metadata |

**Principle**: Data crosses boundaries as **immutable value objects** (frozen dataclasses, TypedDicts, or plain dicts). No mutable shared state crosses boundaries.

### 5.2 Data Flow Diagram: `complete()` Call

```
provider.py                     completion.py                    session_factory.py
    │                               │                                 │
    │  complete(request, **kwargs)  │                                 │
    │─────────────────────────────►│                                 │
    │                               │  build_session_config(request) │
    │                               │────────────────────────────────►│
    │                               │◄────────────────────────────────│
    │                               │  SessionConfig                  │
    │                               │                                 │
    │                               │         streaming.py
    │                               │             │
    │                               │  StreamingHandler()
    │                               │────────────►│
    │                               │             │
    │                               │         client.py
    │                               │             │
    │                               │  create_session(config)
    │                               │────────────►│
    │                               │  send/wait  │
    │                               │────────────►│
    │                               │             │
    │                               │  (events flow through StreamingHandler)
    │                               │             │
    │                               │  disconnect │
    │                               │────────────►│
    │                               │             │
    │  CompletionResult             │
    │◄─────────────────────────────│
    │                               │
    │  tool_parsing.py              │
    │       │                       │
    │  parse_tool_calls()           │
    │──────►│                       │
    │◄──────│                       │
    │  list[ToolCall]               │
    │                               │
    │  → assemble ChatResponse      │
    │  → return to kernel           │
```

### 5.3 Data Flow Diagram: Error Path

```
completion.py                error_translation.py              provider.py
    │                               │                              │
    │  (SDK raises exception)       │                              │
    │  CopilotSessionError          │                              │
    │──────────────────────────────►│                              │
    │                               │  translate_error()           │
    │                               │  → KernelProviderUnavailable │
    │◄──────────────────────────────│                              │
    │                               │                              │
    │  raise translated error       │                              │
    │─────────────────────────────────────────────────────────────►│
    │                               │                              │
    │                               │     (provider re-raises to kernel)
```

### 5.4 Event Flow Between Modules

```
streaming.py ──emit_event()──► coordinator.hooks ──► Amplifier hook system
    │
    │  Events emitted:
    │  - llm:content_block (streaming content deltas)
    │  - llm:thinking_block (reasoning deltas)
    │  - llm:response (complete response, debug mode)
    │  - llm:request (request details, debug mode)

completion.py ──emit_event()──► coordinator.hooks ──► Amplifier hook system
    │
    │  Events emitted:
    │  - sdk_driver:turn (turn tracking)
    │  - sdk_driver:abort (session abort)
    │  - provider:timeout (timeout occurred)

provider.py ──emit_event()──► coordinator.hooks ──► Amplifier hook system
    │
    │  Events emitted:
    │  - provider:fake_tool_retry (fake tool call detected)
    │  - provider:tool_repair (missing tool result repaired)
```

**Rule**: Each module emits its OWN events. `streaming.py` does not emit on behalf of `completion.py`. The `emit_event` callback is passed down through constructors, but each module decides WHEN and WHAT to emit.

---

## 6. AI Maintainability

### 6.1 Module Size for AI Context

| Module | Lines | Context % (8K window) | AI Can Hold Full Module? |
|--------|-------|-----------------------|--------------------------|
| `provider.py` | ~300 | 3.75% | ✅ Yes, with room for tests |
| `completion.py` | ~350 | 4.4% | ✅ Yes, with room for tests |
| `session_factory.py` | ~250 | 3.1% | ✅ Yes, with room for related modules |
| `streaming.py` | ~200 | 2.5% | ✅ Yes, with room for sdk_driver context |
| `error_translation.py` | ~200 | 2.5% | ✅ Yes, trivially |
| `tool_parsing.py` | ~250 | 3.1% | ✅ Yes, with room for converters context |
| `client.py` | 820 | 10.25% | ⚠️ Tight but OK — consider future split |
| `sdk_driver.py` | 620 | 7.75% | ✅ Yes |

**Target**: Every module should be readable by an AI agent with enough remaining context for the module's direct dependencies. The 400-line soft limit ensures this.

### 6.2 Self-Contained Module Pattern

Each module follows the **Self-Contained Module** pattern:

```python
"""
Module docstring answering three questions:
1. What it does
2. What it does NOT do
3. What its dependencies are
"""
from __future__ import annotations

# stdlib imports
# third-party imports
# internal imports (from this package only)

# Module-level constants with explanatory comments

# Protocol classes (if this module defines contracts for its inputs)

# Main classes/functions

# Private helpers (prefixed with _)
```

### 6.3 Module Contract Documentation

Every module's docstring serves as its contract. An AI agent reading ONLY the module docstring should know:

1. **What functions/classes to call** (the public API)
2. **What data types flow in and out** (input/output contracts)
3. **What errors can be raised** (failure modes)
4. **What other modules to read** if deeper understanding is needed

Example:
```python
"""
Session factory — builds SDK session configuration from Amplifier requests.

Public API:
    build_session_config(request, config, model_id) -> SessionConfig
    extract_system_message(messages) -> str | None
    build_tool_list(tools, exclusions) -> tuple[list[Tool], list[str]]

Input types:
    ChatRequest (from amplifier_core.message_models)
    ProviderConfig (from this module)

Output types:
    SessionConfig (dict — see copilot.types.SessionConfig)

Errors:
    ValueError — if model_id is empty or invalid

Dependencies:
    tool_capture.py — for Tool creation with deny hooks
    converters.py — for message format conversion
    _constants.py — for built-in tool names and defaults
    model_naming.py — for thinking model detection
"""
```

### 6.4 AI-Friendly Change Patterns

Common changes and which modules an AI agent needs to read:

| Change | Modules to Read | Modules to Modify |
|--------|----------------|-------------------|
| Add new model support | `models.py`, `model_naming.py` | `models.py`, `model_naming.py` |
| Fix streaming bug | `streaming.py`, `sdk_driver.py` | `streaming.py` |
| Change error handling | `error_translation.py`, `exceptions.py` | `error_translation.py` |
| Add new tool call format | `tool_parsing.py`, `converters.py` | `tool_parsing.py` |
| Fix session config bug | `session_factory.py`, `_constants.py` | `session_factory.py` |
| Change completion flow | `completion.py`, `client.py` | `completion.py` |
| Add new event emission | `streaming.py` or `completion.py` | One of those |
| Fix fake tool detection | `tool_parsing.py` only | `tool_parsing.py` |
| Fix missing tool repair | `tool_parsing.py` only | `tool_parsing.py` |
| Change SDK timeout | `_constants.py` | `_constants.py` |

**Key insight**: Every common change touches at most 2-3 modules, and the AI only needs to read 2-3 modules to understand the full context. This is the metric that matters for AI maintainability.

---

## 7. Migration Strategy

### 7.1 Phased Extraction (from provider.py)

The decomposition should happen in phases, each independently testable:

**Phase 1: Extract `error_translation.py`** (~200 lines)
- Move error mapping from `provider.py:976-1049` 
- Move rate-limit detection helpers
- Zero behavior change — just relocation
- Tests: existing `test_provider.py` error tests should pass with import change

**Phase 2: Extract `tool_parsing.py`** (~250 lines)
- Move `parse_tool_calls()` implementation
- Move fake tool call detection (regex + code-block-aware detection)
- Move `ToolResultRepairer` class (missing tool result repair + LRU tracking)
- Tests: existing tool parsing tests should pass with import change

**Phase 3: Extract `session_factory.py`** (~250 lines)
- Move session configuration building
- Move system message extraction
- Move tool list building
- Tests: new unit tests for session config building

**Phase 4: Extract `streaming.py`** (~200 lines)
- Move streaming event handler
- Move content emission logic
- Tests: existing streaming tests should pass with import change

**Phase 5: Extract `completion.py`** (~350 lines)
- Move `_complete_non_streaming()` and `_complete_streaming()` 
- Wire up session_factory, streaming, error_translation
- Tests: existing completion tests should pass

**Phase 6: Slim `provider.py`** (~300 lines)
- Replace extracted code with delegation calls
- Verify all existing tests pass
- Run integration tests

### 7.2 Test Strategy

Each extraction phase should:
1. **Keep existing tests passing** with minimal import changes
2. **Add module-specific unit tests** for the extracted module
3. **Verify integration tests** still pass end-to-end

The existing test suite (20+ test files) is the safety net. No test should need logic changes — only import path updates.

---

## 8. What We Deliberately Do NOT Do

### 8.1 No Subpackages

As argued in §4.2, nested packages add complexity without benefit for 17 files.

### 8.2 No Abstract Base Classes

The Wave 1 Python Architecture report suggested `Protocol` classes extensively. While Protocols are useful for cross-module contracts, we DON'T add ABCs for:
- Internal module interactions (direct imports are clearer)
- Single-implementation interfaces (premature abstraction)
- Test isolation (mock the function, not the interface)

We use `Protocol` only where structural typing genuinely simplifies testing (e.g., `EventCallback`).

### 8.3 No New Configuration System

The existing `_constants.py` + mount config dict pattern works. We don't introduce frozen dataclass hierarchies for configuration. The `ProviderConfig` in `session_factory.py` is the ONE new config type, and it's a thin extraction of values already computed in `provider.py.__init__()`.

### 8.4 No Dependency Injection Framework

The provider wires dependencies in `__init__()`. That's sufficient. No DI containers, no service locators, no registry patterns.

### 8.5 No Event Bus Abstraction

Events flow through `coordinator.hooks.emit()`. We don't abstract this into an internal event bus. The `emit_event` callback passed through constructors is intentionally a raw callable, not a typed interface.

---

## 9. Success Criteria

The decomposition is successful when:

1. **No file exceeds 400 lines** (soft limit) or 600 lines (hard limit, only `client.py` and `sdk_driver.py` may approach this)
2. **Every common change touches ≤3 modules** (measured by the table in §6.4)
3. **All existing tests pass** with only import path changes
4. **No circular dependencies** (verified by import analysis)
5. **An AI agent can read any module + its direct dependencies** within a single context window
6. **The dependency graph has no upward arrows** (verified by the layering rules in §2.2)

---

## 10. Summary: The Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROVIDER PACKAGE (17 modules)                 │
│                                                                  │
│  ┌──────────────┐                                               │
│  │ __init__.py   │  Entry point: mount(), singleton             │
│  └──────┬───────┘                                               │
│         │                                                        │
│  ┌──────▼───────┐                                               │
│  │  provider.py  │  Orchestrator: 5-method protocol (~300 LOC)  │
│  └──┬──┬──┬──┬──┘                                               │
│     │  │  │  │                                                   │
│     │  │  │  └────► tool_parsing.py     Parse + repair (~250)   │
│     │  │  └───────► error_translation   SDK→Kernel errors (~200)│
│     │  └──────────► models.py           Model metadata (292)    │
│     │                                                            │
│     └─────────────► completion.py       LLM call engine (~350)  │
│                         │  │                                     │
│                         │  └──► streaming.py    Deltas (~200)   │
│                         └─────► session_factory Config (~250)   │
│                                                                  │
│  ═══════════════════════════════════════════════════════════════ │
│  EXISTING MODULES (unchanged):                                   │
│  client.py(820) sdk_driver.py(620) converters.py(426)           │
│  model_cache.py(415) model_naming.py(359) exceptions.py(322)   │
│  _constants.py(312) _platform.py(280) tool_capture.py(218)     │
│  _permissions.py(52)                                             │
└─────────────────────────────────────────────────────────────────┘
```

**The center stays still so the edges can move fast.** The existing 10 well-structured modules are the stable center. The 5 new modules extracted from `provider.py` are the edges that enable faster, safer AI-driven development.

---

*End of Modular Architecture Design*
