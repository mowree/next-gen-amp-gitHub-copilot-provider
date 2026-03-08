# Feature Spec: F-002 Provider Protocol Contract

**Feature ID:** F-002
**Module:** `contracts/`
**Contract:** `contracts/provider-protocol.md`
**Priority:** P0 (Foundation)
**Estimated Size:** ~150 lines (markdown)

---

## Summary

Document the 5-method Provider Protocol as a markdown contract. This contract defines what our provider MUST implement to integrate with Amplifier.

---

## Acceptance Criteria

1. **Contract file created:** `contracts/provider-protocol.md`

2. **All 5 methods documented:**
   - `name` (property) — Provider identifier
   - `get_info()` — Provider metadata
   - `list_models()` — Available models
   - `complete()` — LLM completion
   - `parse_tool_calls()` — Tool extraction

3. **Each method has:**
   - Signature (with types)
   - Behavioral requirements (MUST/SHOULD/MAY)
   - Preconditions and postconditions
   - Test anchors

4. **Contract follows RFC 2119 style** (MUST/SHOULD/MAY keywords)

---

## Contract Structure

```markdown
# Contract: Provider Protocol

## Version
- **Current:** 1.0
- **Module Reference:** modules/provider-core/provider.py
- **Amplifier Contract:** amplifier-core PROVIDER_CONTRACT.md

---

## The Five Methods

### 1. name (property)
- **Signature:** `@property def name(self) -> str`
- **MUST:** Return "github-copilot" (exact string)
- **MUST:** Be a property, not a method call

### 2. get_info()
- **Signature:** `def get_info(self) -> ProviderInfo`
- **MUST:** Return ProviderInfo with accurate context_window
- **MUST:** Include defaults.context_window for budget calculation
- **SHOULD:** Cache model info to avoid repeated API calls

### 3. list_models()
- **Signature:** `async def list_models(self) -> list[ModelInfo]`
- **MUST:** Return all available models from SDK
- **MUST:** Include context_window and max_output_tokens per model
- **SHOULD:** Cache results for session lifetime

### 4. complete()
- **Signature:** `async def complete(request: ChatRequest, **kwargs) -> ChatResponse`
- **MUST:** Create ephemeral session per call (deny-destroy.md)
- **MUST:** Capture tool calls, not execute them
- **MUST:** Support streaming via on_content callback
- **MUST NOT:** Maintain state between calls

### 5. parse_tool_calls()
- **Signature:** `def parse_tool_calls(response: ChatResponse) -> list[ToolCall]`
- **MUST:** Extract tool calls from response
- **MUST:** Return empty list if no tool calls
- **MUST NOT:** Execute tools (orchestrator responsibility)

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `provider-protocol:name:MUST:1` | Returns "github-copilot" |
| `provider-protocol:get_info:MUST:1` | Returns valid ProviderInfo |
| `provider-protocol:list_models:MUST:1` | Returns model list |
| `provider-protocol:complete:MUST:1` | Creates ephemeral session |
| `provider-protocol:complete:MUST:2` | Captures tool calls |
| `provider-protocol:parse_tool_calls:MUST:1` | Extracts tool calls |
```

---

## Reference Sources

1. **Amplifier Core Contract:** `reference-only/amplifier-core/docs/contracts/PROVIDER_CONTRACT.md`
2. **Reference Implementation:** `reference-only/amplifier-module-provider-anthropic/`
3. **Existing Provider:** `reference-only/amplifier-module-provider-github-copilot/provider.py`

---

## Implementation Notes

- Read the Amplifier PROVIDER_CONTRACT.md first
- Adapt to our Three-Medium Architecture (contracts drive tests AND implementation)
- Use the contract format from `debates/research/MARKDOWN_CONTRACTS_IN_OUR_PROJECT.md`

---

## Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `contracts/provider-protocol.md` | Create | ~150 |

---

## Contract References

This IS a contract creation task. It establishes test anchors for:
- F-011 (Provider implementation)
- Integration tests
