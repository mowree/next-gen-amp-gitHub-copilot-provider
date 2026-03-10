# F-023: Critical Test Coverage

**Priority**: HIGH
**Source**: test-coverage, security-guardian
**Estimated Lines**: ~200 test code

## Objective

Add tests for critical gaps identified by the expert panel.

## Acceptance Criteria

### AC-1: Test _resolve_token() Precedence (CRITICAL)

**Problem**: Zero tests for auth token resolution.

**Tests**:
```python
def test_resolve_token_precedence():
    """COPILOT_AGENT_TOKEN takes precedence over GITHUB_TOKEN."""
    with patch.dict(os.environ, {
        "COPILOT_AGENT_TOKEN": "agent-token",
        "GITHUB_TOKEN": "gh-token",
    }):
        assert _resolve_token() == "agent-token"

def test_resolve_token_fallback():
    """Falls back through the chain."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": "gh-token"}, clear=True):
        assert _resolve_token() == "gh-token"

def test_resolve_token_missing():
    """Returns None when no token set."""
    with patch.dict(os.environ, {}, clear=True):
        assert _resolve_token() is None
```

### AC-2: Test SDK ImportError Path (CRITICAL)

**Problem**: ImportError fallback untested.

**Test**:
```python
def test_sdk_import_error_raises_provider_unavailable():
    """Missing SDK raises ProviderUnavailableError."""
    with patch.dict(sys.modules, {"copilot": None}):
        wrapper = CopilotClientWrapper()
        with pytest.raises(ProviderUnavailableError) as exc_info:
            async with wrapper.session():
                pass
        assert "SDK not installed" in str(exc_info.value)
```

### AC-3: Test Deny Hook on CopilotClientWrapper Path

**Problem**: No test verifies deny hook fires on real SDK path.

**Test**:
```python
async def test_deny_hook_registered_on_wrapper_session():
    """CopilotClientWrapper.session() registers deny hook."""
    mock_session = MagicMock()
    mock_session.register_pre_tool_use_hook = MagicMock()
    
    wrapper = CopilotClientWrapper(injected_client=mock_client)
    async with wrapper.session():
        pass
    
    mock_session.register_pre_tool_use_hook.assert_called_once()
```

### AC-4: Test Concurrent Session Race Condition

**Problem**: No test for concurrent session() calls.

**Test**:
```python
async def test_concurrent_sessions_no_race():
    """Concurrent session() calls don't race on client init."""
    wrapper = CopilotClientWrapper()
    
    # Launch 5 concurrent session requests
    async def get_session():
        async with wrapper.session() as s:
            return s
    
    sessions = await asyncio.gather(*[get_session() for _ in range(5)])
    
    # All should succeed without error
    assert len(sessions) == 5
    # Client should have been initialized exactly once
    assert wrapper._owned_client is not None
```

### AC-5: Test Double Translation Guard

**Problem**: No test for LLMError re-wrap prevention.

**Test**:
```python
async def test_llm_error_not_double_wrapped():
    """LLMError raised inside complete() is not re-translated."""
    async def failing_sdk_fn(config):
        raise AuthenticationError("Already translated", provider="test")
    
    with pytest.raises(AuthenticationError) as exc_info:
        async for _ in complete(request, sdk_create_fn=failing_sdk_fn):
            pass
    
    # Should NOT be wrapped in another error
    assert exc_info.value.__cause__ is None
```

### AC-6: Test system_message Parameter

**Problem**: `system_message` never verified in session config.

**Test**:
```python
async def test_session_system_message_structure():
    """system_message is passed with correct structure."""
    mock_client = MagicMock()
    mock_client.create_session = AsyncMock()
    
    wrapper = CopilotClientWrapper(injected_client=mock_client)
    async with wrapper.session(system_message="Be helpful"):
        pass
    
    call_args = mock_client.create_session.call_args
    config = call_args[0][0]
    assert config["system_message"] == {
        "mode": "append",
        "content": "Be helpful"
    }
```

## Files to Create

- `tests/test_auth_token.py`
- `tests/test_sdk_boundary.py`
- `tests/test_concurrent_sessions.py`

## Files to Modify

- `tests/test_sdk_client.py` (add deny hook test)
- `tests/test_completion.py` (add double-translation test)

## Dependencies

- F-019 (security fixes must exist to test)
- F-020 (protocol must exist to test)

## NOT IN SCOPE

- E2E tests requiring real SDK (Phase 2)
- Performance benchmarks
