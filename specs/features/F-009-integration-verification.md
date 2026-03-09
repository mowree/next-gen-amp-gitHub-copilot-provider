# F-009: Integration Verification

**Status**: Ready  
**Module**: tests  
**Depends On**: F-008 (Provider Orchestrator)

## Overview

End-to-end integration tests that verify the full provider lifecycle works correctly with mock SDK. This feature validates that all modules (F-001 through F-008) work together as a coherent system.

## Acceptance Criteria

### AC-1: Full Completion Lifecycle
- Provider can complete a request end-to-end with mock SDK
- Session is created, completion streams, session is destroyed
- Response contains accumulated text content

### AC-2: Tool Call Integration
- Provider correctly parses tool calls from completion response
- `parse_tool_calls()` returns `ToolCall` objects with correct structure
- Tool calls have `id`, `name`, and `arguments` (dict)

### AC-3: Error Translation Integration
- SDK errors are translated to domain error types
- Provider raises appropriate error types (AuthenticationError, RateLimitError, etc.)
- Error attributes (`retryable`, `retry_after`) are correctly populated

### AC-4: Streaming Event Flow
- Events flow from SDK → streaming → accumulator → response
- CONTENT_DELTA events accumulate correctly
- TURN_COMPLETE signals completion with finish_reason

### AC-5: Session Factory Integration
- Deny hook is installed on all sessions
- Sessions are ephemeral (create, use once, destroy)
- Session destruction happens even on error (try/finally)

### AC-6: Provider Protocol Compliance
- Provider has `name` property
- `get_info()` returns ProviderInfo
- `list_models()` returns list of ModelInfo
- `complete()` returns ChatResponse
- `parse_tool_calls()` returns list[ToolCall]

## Test Structure

```python
# tests/test_integration.py

class TestProviderIntegration:
    """End-to-end integration tests with mock SDK."""

    async def test_complete_simple_request(self):
        """AC-1: Full completion lifecycle."""
        
    async def test_complete_with_tool_calls(self):
        """AC-2: Tool call extraction works end-to-end."""
        
    async def test_error_translation_auth_error(self):
        """AC-3: Authentication errors are translated."""
        
    async def test_error_translation_rate_limit(self):
        """AC-3: Rate limit errors have retry_after."""
        
    async def test_streaming_event_accumulation(self):
        """AC-4: Events accumulate correctly."""
        
    async def test_session_lifecycle(self):
        """AC-5: Session created and destroyed."""
        
    async def test_session_destroyed_on_error(self):
        """AC-5: Session destroyed even on error."""
        
    async def test_provider_protocol_compliance(self):
        """AC-6: All protocol methods work."""
```

## Mock SDK Design

The mock SDK simulates the real SDK without actual network calls:

```python
class MockSDKSession:
    """Mock SDK session for integration testing."""
    
    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.destroyed = False
        self.deny_hook_installed = False
    
    async def send_message(self, prompt: str) -> AsyncIterator[dict]:
        """Yield mock SDK events."""
        for event in self.responses:
            yield event
    
    async def disconnect(self):
        """Mark session as destroyed."""
        self.destroyed = True
```

## Dependencies

- All modules from F-001 through F-008 must be implemented
- Config files: `config/errors.yaml`, `config/events.yaml`
- No actual SDK required (fully mocked)

## Non-Goals

- Live API testing (that's for nightly smoke tests)
- Performance benchmarking
- Concurrency stress testing
