# F-059: ChatRequest Multi-Turn Context Preservation

**Status:** ready
**Priority:** P1
**Source:** deep-review/bug-hunter.md
**Defect ID:** DEF-008

## Problem Statement
`provider.py:443-458` extracts only `text` blocks from ChatRequest messages. `ThinkingContent`, `ToolCallContent`, tool result blocks, and non-text content are silently dropped. All messages are joined with `"\n".join()` — role information (user/assistant) is discarded. The SDK receives an undifferentiated blob of text, losing critical context in multi-turn conversations.

## Success Criteria
- [ ] Role information is preserved (user/assistant/system labels or structure)
- [ ] Tool call content blocks are represented in the prompt
- [ ] Tool result blocks are represented in the prompt
- [ ] Multi-turn conversations maintain context fidelity
- [ ] Test covers mixed content types in a multi-turn request

## Implementation Approach
1. Preserve role labels when flattening messages (prefix with role markers if SDK doesn't support structured messages)
2. Extract text from ThinkingContent and ToolCallContent blocks
3. Represent tool results as formatted text blocks
4. If SDK supports structured message API, use it instead of flattening

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (lines 443-458)

## Tests Required
- Test: multi-turn request with user + assistant + tool_result messages
- Test: ThinkingContent blocks are included
- Test: ToolCallContent blocks are included
- Test: role boundaries are preserved

## Not In Scope
- Structured SDK message passing (depends on F-052 streaming pipeline)
- Token counting or context window management
