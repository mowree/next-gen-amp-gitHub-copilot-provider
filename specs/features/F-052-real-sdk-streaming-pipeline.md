# F-052: Real SDK Streaming Pipeline

**Status:** ready
**Priority:** P0
**Source:** deep-review/integration-specialist.md
**Defect ID:** N/A (structural correctness failure)

## Problem Statement
The real SDK path in `GitHubCopilotProvider.complete()` (provider.py:479-498) uses `send_and_wait()` for blocking calls, generating a single synthetic `CONTENT_DELTA` event. This bypasses the entire event translation pipeline: no `TOOL_CALL` events (tool use broken), no `USAGE_UPDATE` events (usage tracking broken), no `TURN_COMPLETE` events (finish_reason absent), and `translate_event()`/`config/events.yaml` are never used. The test path correctly uses streaming, but the production path does not.

## Success Criteria
- [ ] Real SDK path uses streaming iteration over SDK events
- [ ] SDK events are routed through `translate_event()` and `classify_event()`
- [ ] `TOOL_CALL` events are generated for tool use
- [ ] `USAGE_UPDATE` events are generated for usage tracking
- [ ] `TURN_COMPLETE` events are generated with correct `finish_reason`
- [ ] `config/events.yaml` is exercised in the real path
- [ ] Existing test path continues to work
- [ ] Integration test verifies streaming pipeline end-to-end

## Implementation Approach
1. Replace `send_and_wait()` with streaming message send + event iteration
2. Route events through `translate_event()` → `classify_event()` → accumulator
3. Follow the pattern already established in the test path (`sdk_create_fn`)
4. Ensure tool definitions from `internal_request.tools` are passed to the SDK
5. Add integration test that verifies the full pipeline

## Files to Modify
- `amplifier_module_provider_github_copilot/provider.py` (lines 479-498, `GitHubCopilotProvider.complete()`)

## Tests Required
- `tests/test_real_sdk_streaming.py` (new):
  - Integration test: real SDK path produces correct event sequence
  - Test: tool definitions are passed to SDK session
  - Test: streaming events are translated through the pipeline

## Contract Traceability
- `contracts/streaming-contract.md` — streaming pipeline must emit correct event sequence
- `contracts/event-vocabulary.md` — events must use defined domain event types

## Not In Scope
- Changing the event translation logic itself
- Modifying `config/events.yaml`
- Retry logic (see F-060)
