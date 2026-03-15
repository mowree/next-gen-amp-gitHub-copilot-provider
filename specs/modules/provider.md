# Module Spec: Provider

**Module:** `amplifier_module_provider_github_copilot/provider.py`
**Contract:** `contracts/provider-protocol.md`
**Target Size:** ~400 lines

---

## Purpose

The thin orchestrator implementing the 5-method Amplifier Provider Protocol. Coordinates other modules but contains minimal logic itself.

---

## Public API (Provider Protocol)

```python
# Kernel types from amplifier_core
from amplifier_core import ChatRequest, ChatResponse, ModelInfo, ProviderInfo, ToolCall

class CopilotProvider(Protocol):
    @property
    def name(self) -> str:
        """Provider identifier: 'github-copilot'"""
    
    def get_info(self) -> ProviderInfo:
        """Provider metadata for display and configuration."""
    
    async def list_models(self) -> list[ModelInfo]:
        """Available models from Copilot SDK."""
    
    async def complete(
        self,
        request: ChatRequest,
        **kwargs,
    ) -> ChatResponse:
        """
        Execute LLM completion.
        
        Creates ephemeral session → sends request → captures response → destroys session.
        Tool calls are captured and returned, NOT executed.
        """
    
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]:
        """Extract tool calls from response for orchestrator."""
```

---

## Module Interactions

```
                     ┌─────────────────┐
                     │   provider.py   │
                     │ (orchestrator)  │
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  sdk_adapter/ │    │   streaming   │    │ tool_parsing  │
│   client.py   │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
        │
        ▼
┌───────────────┐
│error_translation│
│               │
└───────────────┘
```

---

## Complete Method Flow

```python
async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
    # 1. Create SDK session via CopilotClientWrapper
    # 2. Install deny hooks (create_deny_hook, deny_permission_request)
    # 3. Send request and accumulate streaming response
    accumulator = StreamingAccumulator()
    async for event in session.events():
        domain_event = translate_event(event, config)
        accumulator.add(domain_event)
    
    # 4. Convert accumulated response to kernel ChatResponse
    return accumulator.to_chat_response()
```

---

## Invariants

1. **MUST:** Implement all 5 Provider Protocol methods
2. **MUST:** Create new session per complete() call (via CopilotClientWrapper)
3. **MUST:** Return tool calls to orchestrator (NOT execute them)
4. **MUST:** Delegate complex logic to streaming, error_translation, tool_parsing
5. **MUST NOT:** Import SDK types directly (use sdk_adapter only)

---

## Dependencies

```
provider.py
├── imports: error_translation, sdk_adapter.client, sdk_adapter.types, streaming, tool_parsing
├── uses: CopilotClientWrapper (from sdk_adapter/client.py)
├── types: ProviderInfo, ModelInfo, ChatResponse, ToolCall (from amplifier_core)
├── implements: Provider Protocol
└── enforces: provider-protocol.md contract
```

---

## Test Strategy

| Tier | Tests |
|------|-------|
| Unit | Each method has correct signature |
| Integration | Complete flow with stubbed SDK |
| Contract | All provider-protocol.md MUST clauses tested |
| Behavioral | Matches reference implementation on test cases |
