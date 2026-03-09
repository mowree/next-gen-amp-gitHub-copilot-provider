# Feature: F-008 Provider Orchestrator

## Overview
Implement the 4 methods + 1 property Provider Protocol as a thin orchestrator that delegates to specialized modules.

## Contract Reference
- **Primary**: contracts/provider-protocol.md
- **Related**: contracts/deny-destroy.md, contracts/error-hierarchy.md

## Dependencies
- F-007: Completion Lifecycle (complete(), complete_and_collect())
- F-004: Tool Parsing (parse_tool_calls())

## Interface

```python
class GitHubCopilotProvider:
    """Thin orchestrator implementing Provider Protocol."""
    
    @property
    def name(self) -> str:
        """MUST return 'github-copilot'"""
    
    def get_info(self) -> ProviderInfo:
        """Return provider metadata with context_window."""
    
    async def list_models(self) -> list[ModelInfo]:
        """Query available models from SDK."""
    
    async def complete(
        self,
        request: ChatRequest,
        **kwargs,
    ) -> ChatResponse:
        """Execute completion via completion module."""
    
    def parse_tool_calls(self, response: ChatResponse) -> list[ToolCall]:
        """Delegate to tool_parsing module."""
```

## Data Types

### ProviderInfo
```python
@dataclass
class ProviderInfo:
    name: str
    version: str
    defaults: ProviderDefaults

@dataclass
class ProviderDefaults:
    model: str
    context_window: int
    max_output_tokens: int
```

### ModelInfo
```python
@dataclass
class ModelInfo:
    id: str
    name: str
    context_window: int
    max_output_tokens: int
```

### ChatRequest
```python
@dataclass
class ChatRequest:
    messages: list[dict[str, Any]]
    model: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    max_tokens: int | None = None
    temperature: float | None = None
```

### ChatResponse
```python
@dataclass
class ChatResponse:
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: dict[str, int] | None = None
    finish_reason: str | None = None
```

## Behavioral Requirements

### P1: name property
- MUST return `"github-copilot"` exactly
- MUST NOT vary based on configuration

### P2: get_info()
- MUST return valid ProviderInfo
- MUST include defaults.context_window (default: 128000)
- MUST include defaults.max_output_tokens (default: 4096)

### P3: list_models()
- MUST return list of ModelInfo
- SHOULD cache results (stub implementation returns hardcoded list)
- MUST translate SDK model info to ModelInfo domain type

### P4: complete()
- MUST accept `**kwargs` (not named callback)
- MUST delegate to completion.complete_and_collect()
- MUST convert CompletionRequest to ChatRequest format
- MUST return ChatResponse with content and tool_calls

### P5: parse_tool_calls()
- MUST delegate to tool_parsing.parse_tool_calls()
- MUST return list[ToolCall] (not ToolCallBlock)

## Test Anchors

| Anchor | Test |
|--------|------|
| `provider-protocol:name:MUST:1` | test_name_returns_github_copilot |
| `provider-protocol:get_info:MUST:1` | test_get_info_returns_provider_info |
| `provider-protocol:get_info:MUST:2` | test_get_info_includes_context_window |
| `provider-protocol:list_models:MUST:1` | test_list_models_returns_list |
| `provider-protocol:complete:MUST:1` | test_complete_accepts_kwargs |
| `provider-protocol:complete:MUST:2` | test_complete_returns_chat_response |
| `provider-protocol:parse_tool_calls:MUST:1` | test_parse_tool_calls_extracts_tools |
| `provider-protocol:parse_tool_calls:MUST:2` | test_parse_tool_calls_empty_when_none |

## Acceptance Criteria

1. All test anchors pass
2. Provider class < 120 lines
3. ruff check passes
4. pyright passes
5. No SDK imports in provider.py (delegation only)

## Implementation Notes

- Provider is thin orchestrator - all logic lives in delegated modules
- ChatRequest/ChatResponse are domain types that mirror kernel interface
- SDK session management is handled by completion module
- Error translation is handled by completion module
