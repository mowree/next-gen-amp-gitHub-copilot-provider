# Module Spec: Provider

**Module:** `src/provider_github_copilot/provider.py`
**Contract:** `contracts/provider-protocol.md`
**Target Size:** ~120 lines

---

## Purpose

The thin orchestrator implementing the 5-method Amplifier Provider Protocol. Coordinates other modules but contains minimal logic itself.

---

## Public API (Provider Protocol)

```python
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
        *,
        on_content: Callable[[ContentDelta], None] | None = None,
    ) -> ChatResponse:
        """
        Execute LLM completion.
        
        Creates ephemeral session → sends request → captures response → destroys session.
        Tool calls are captured and returned, NOT executed.
        """
    
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCallBlock]:
        """Extract tool calls from response for orchestrator."""
```

---

## Module Interactions

```
                     ┌─────────────────┐
                     │   provider.py   │
                     │ (thin orchestrator)
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│session_factory│    │  completion   │    │ tool_parsing  │
│               │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │
        ▼                     ▼
┌───────────────┐    ┌───────────────┐
│  sdk_adapter  │    │   streaming   │
│ (THE MEMBRANE)│    │               │
└───────────────┘    └───────────────┘
```

---

## Complete Method Flow

```python
async def complete(self, request: ChatRequest, **kwargs) -> ChatResponse:
    # 1. Create ephemeral session (with deny hook)
    async with create_ephemeral_session(self.client, config) as session:
        # 2. Delegate to completion lifecycle
        response = await execute_completion(session, request, streaming=True)
    
    # 3. Session destroyed on context exit
    # 4. Return response (tool calls captured, not executed)
    return response
```

---

## Invariants

1. **MUST:** Implement all 5 Provider Protocol methods
2. **MUST:** Create new session per complete() call (via session_factory)
3. **MUST:** Return tool calls to orchestrator (NOT execute them)
4. **MUST:** Be a thin orchestrator (~120 lines, no complex logic)
5. **MUST NOT:** Import SDK types (use sdk_adapter only)

---

## Dependencies

```
provider.py
├── imports: session_factory, completion, tool_parsing
├── uses: CopilotClient (injected)
├── implements: Provider Protocol (from amplifier-core)
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
