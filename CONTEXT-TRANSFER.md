# provider-github-copilot -- Context Transfer

> **This project is managed by an autonomous development machine.**
> Do NOT implement features or fix code directly. Run the recipes instead.
> See `AGENTS.md` for instructions.

> This file is the institutional memory of the project. Updated continuously.
> Each session reads this to understand recent decisions and context.
> Reverse-chronological: newest entries at the top.

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
