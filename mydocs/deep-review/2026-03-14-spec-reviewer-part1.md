## Spec Compliance Review

Scope: file-only review of `mydocs/debates/GOLDEN_VISION_V2.md` (Section 3/4 intent as stated there), `amplifier_module_provider_github_copilot/provider.py`, and `amplifier_module_provider_github_copilot/__init__.py`.

### Spec Requirements Checklist
- [ ] **Line count targets:** `provider.py` is **532 lines** (target: **~120**). The Golden Vision also expects the provider core to be split across `provider.py` (~120) and `completion.py` (~150); instead, `provider.py` still contains completion lifecycle, config loading, response extraction, helper dataclasses, and session handling.
- [~] **Provider Protocol methods:** Present overall: `name`, `get_info()`, `list_models()`, `complete()`, `parse_tool_calls()`, plus `mount()` in `__init__.py`. However, `complete()` is declared as `request: Any` rather than `ChatRequest`, so the protocol shape is only partially aligned with the spec's contract-first signature.
- [ ] **Session configuration:** Not compliant with the stated session setup. In `provider.py`, `SessionConfig` is created as `SessionConfig(model=request.model or "gpt-4")` with no visible `available_tools=[]` and no `mode="replace"`; the real SDK path bypasses `SessionConfig` entirely.
- [ ] **Core provider architecture:** Not compliant with the Three-Medium Architecture membrane. `provider.py` directly handles SDK-session-shaped objects (`SDKSession`, `register_pre_tool_use_hook`, `send_message`, `send_and_wait`, `disconnect`) instead of staying a thin orchestrator over a strict adapter boundary.

### Extra Changes Found
- `provider.py` includes substantial mechanism that Golden Vision expects to live elsewhere (`completion.py`, adapter/session factory layers), so the core provider currently does more than the spec assigns to it.

### Verdict: NEEDS CHANGES

### Issues
1. **Missing target decomposition**: `provider.py` is far above the Golden Vision target and still owns logic that should be extracted.
2. **Session config mismatch**: required `available_tools=[]` / `mode=replace` configuration is not present in the reviewed core code.
3. **Boundary violation**: SDK session concepts leak into `provider.py`, contrary to the contract-first membrane.
4. **Protocol looseness**: methods exist, but `complete(request: Any, **kwargs)` is weaker than the spec's `ChatRequest` contract.

### Required Actions
- Shrink `provider.py` to a thin orchestrator by moving completion/session mechanics out to the intended modules.
- Ensure session creation explicitly uses the spec-required configuration (`available_tools=[]`, `mode="replace"`).
- Remove SDK-session handling from `provider.py`; keep that inside the adapter/session layer.
- Tighten `complete()` to the Provider Protocol contract type (`ChatRequest`).
