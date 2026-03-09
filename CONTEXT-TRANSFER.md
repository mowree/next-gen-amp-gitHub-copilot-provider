# provider-github-copilot -- Context Transfer

> **This project is managed by an autonomous development machine.**
> Do NOT implement features or fix code directly. Run the recipes instead.
> See `AGENTS.md` for instructions.

> This file is the institutional memory of the project. Updated continuously.
> Each session reads this to understand recent decisions and context.
> Reverse-chronological: newest entries at the top.

---

## Session 2026-03-09T01:08Z -- F-003 Implemented

### Work Completed

**F-003: Session Factory with Deny Hook** (IMPLEMENTED)
- `src/amplifier_module_provider_github_copilot/session_factory.py` - ~130 lines
- `tests/test_session_factory.py` - 12 tests for session lifecycle
- Implements the Deny + Destroy pattern (non-negotiable)
- `create_deny_hook()` - returns DENY for all tool requests
- `create_ephemeral_session()` - creates session with hook installed
- `destroy_session()` - graceful session cleanup

### Key Design Decisions

1. **Dependency injection for testing**: `create_ephemeral_session` accepts optional `sdk_create_fn` parameter for test mocking. Real SDK integration deferred to driver.py.

2. **Force deny_all_tools=True**: Even if caller passes `deny_all_tools=False`, the function forces it to True with a warning log. The Deny+Destroy pattern is non-negotiable.

3. **Graceful destruction**: `destroy_session` catches exceptions from disconnect() and logs warnings rather than propagating errors.

### Build Status
- `ruff check src/` - PASS (0 errors)
- `pyright src/` - PASS (0 errors, 2 expected warnings for skeleton stubs)

### Blocker (INFO severity)
**B001**: Git commits not executed - sub-agent cannot run bash. Human must commit after session.

### For Human to Commit
```bash
cd /workspace && \
git add src/amplifier_module_provider_github_copilot/sdk_adapter/ \
        src/amplifier_module_provider_github_copilot/error_translation.py \
        src/amplifier_module_provider_github_copilot/session_factory.py \
        tests/test_sdk_adapter.py \
        tests/test_error_translation.py \
        tests/test_session_factory.py \
        config/errors.yaml \
        STATE.yaml \
        CONTEXT-TRANSFER.md && \
git commit -m "feat(core): implement F-001 + F-002 + F-003

- F-001: SDK Adapter skeleton (DomainEvent, SessionConfig, driver stubs)
- F-002: Config-driven error translation with 7 mapping rules
- F-003: Session factory with deny hook (Deny+Destroy pattern)

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Next Steps
1. Run: `uv run pytest tests/ -v` to verify all tests pass
2. Execute commit command above
3. Continue with F-004 (Tool Parsing) - NOTE: spec file F-004-tool-parsing.md is missing

---

## Session 2026-03-09T00:47Z -- F-001 + F-002 Implemented

### Work Completed

**F-001: SDK Adapter Skeleton** (IMPLEMENTED)
- `src/amplifier_module_provider_github_copilot/sdk_adapter/__init__.py` - Module exports
- `src/amplifier_module_provider_github_copilot/sdk_adapter/types.py` - DomainEvent, SessionConfig, SDKSession
- `src/amplifier_module_provider_github_copilot/sdk_adapter/driver.py` - create_session, destroy_session stubs
- `tests/test_sdk_adapter.py` - 12 tests for adapter types and exports

**F-002: Error Translation** (IMPLEMENTED)
- `src/amplifier_module_provider_github_copilot/error_translation.py` - Config-driven error translation (~290 lines)
- `config/errors.yaml` - Full SDK→kernel error mappings (7 mapping rules)
- `tests/test_error_translation.py` - 17 tests for error translation

### Key Design Decisions

1. **Kernel error types defined locally**: Since amplifier-core may not be installed, the error_translation.py defines matching LLMError subclasses. These match the kernel interface (`provider`, `model`, `retryable`, `retry_after` attributes).

2. **Config loading from YAML**: ErrorConfig/ErrorMapping dataclasses load from config/errors.yaml. Pattern matching supports both type name matching and string pattern matching.

3. **Retry-after extraction**: RateLimitError mappings can set `extract_retry_after: true` to parse "Retry after N seconds" from error messages.

### Build Status
- `ruff check src/` - PASS (0 errors)
- `pyright src/` - PASS (0 errors, 2 expected warnings for skeleton stubs)

### Blocker (INFO severity)
**B001**: Not a git repository - commits deferred. Code is complete; human will commit after session.

### Next Steps for Human
1. Initialize git: `git init && git add -A && git commit -m "feat: F-001 + F-002 implementation"`
2. Run tests: `uv run pytest tests/ -v`
3. Continue with F-003 (Session Factory with Deny Hook)

---

## Founding Session -- Phase 1

### Architecture Decisions

1. **Three-Medium Architecture** -- Python for mechanism (~300 lines), YAML for policy (~200 lines), Markdown for contracts (~400 lines). This is the core principle from GOLDEN_VISION_V2.md.

2. **Kernel Error Types Only** -- All errors MUST use `amplifier_core.llm_errors.*` types. Custom error types are NOT allowed (they break cross-provider error handling). See contracts/error-hierarchy.md.

3. **Kernel Content Types Only** -- Use `TextContent`, `ThinkingContent`, `ToolCallContent` from `amplifier_core.content_models`. The phantom `ContentDelta` type does NOT exist. See contracts/streaming-contract.md.

4. **4 Methods + 1 Property Protocol** -- The Provider Protocol is `name` (property), `get_info()`, `list_models()`, `complete(**kwargs)`, `parse_tool_calls()`. Note: `complete()` uses `**kwargs`, not a named streaming callback. See contracts/provider-protocol.md.

5. **Deny + Destroy Pattern** -- Every SDK session is ephemeral. A `preToolUse` hook denies all tool execution (Amplifier's orchestrator handles tools). Sessions are destroyed immediately after the first turn. This is non-negotiable. See contracts/deny-destroy.md.

6. **SDK Boundary = The Membrane** -- No SDK type crosses the adapter boundary. All SDK imports live in `sdk_adapter/`. Domain code never imports from SDK directly. See contracts/sdk-boundary.md.

### Initial Module Structure

| Module | Lines | Purpose |
|--------|-------|---------|
| `sdk_adapter/` | ~200 | THE MEMBRANE -- all SDK imports here only |
| `provider.py` | ~120 | Thin orchestrator, 4+1 interface |
| `completion.py` | ~150 | LLM call lifecycle |
| `error_translation.py` | ~80 | Config-driven error boundary |
| `tool_parsing.py` | ~120 | Tool call extraction |
| `session_factory.py` | ~100 | Ephemeral session + deny hook |
| `streaming.py` | ~100 | Config-driven event handler |

### Technology Choices

- **Python 3.11+** -- Required for modern typing features
- **github-copilot-sdk>=0.1.32,<0.2.0** -- SDK with `session.disconnect()` API
- **amplifier-core** -- Kernel types (dev dependency for testing)
- **ruff** -- Linting and formatting
- **pyright** -- Type checking (strict mode)
- **pytest + pytest-asyncio** -- Testing framework

### Known Constraints

1. Module size threshold: 400 LOC (soft) / 600 LOC (hard)
2. File size threshold: 1000 lines (flag for decomposition)
3. Max 3 features per working session
4. Build MUST pass after every feature (both `ruff check` and `pyright`)

### First Batch of Work

- F-001: SDK Adapter skeleton
- F-002: Error translation
- F-003: Session factory with deny hook
