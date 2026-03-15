## Spec Compliance Review

Scope: amended review of `mydocs/debates/GOLDEN_VISION_V2.md` (Section 3/4 intent as stated there), `amplifier_module_provider_github_copilot/provider.py`, `amplifier_module_provider_github_copilot/__init__.py`, and `amplifier_module_provider_github_copilot/sdk_adapter/client.py` for SDK-boundary session configuration verification.

### Spec Requirements Checklist
- [ ] **Line count targets:** `provider.py` should be treated here as **432 lines** (not the previously claimed **532**) against a target of **~120**. The Golden Vision also expects the provider core to be split across `provider.py` (~120) and `completion.py` (~150); even with the corrected count, `provider.py` still contains completion lifecycle, config loading, response extraction, helper dataclasses, and session handling.
- [~] **Provider Protocol methods:** Present overall: `name`, `get_info()`, `list_models()`, `complete()`, `parse_tool_calls()`, plus `mount()` in `__init__.py`. However, `complete()` is declared as `request: Any` rather than `ChatRequest`, so the protocol shape is only partially aligned with the spec's contract-first signature.
- [x] **Session configuration at SDK boundary:** Prior noncompliance finding retracted. Verified in `amplifier_module_provider_github_copilot/sdk_adapter/client.py:216-229` that the actual SDK session configuration sets `available_tools = []` and `system_message = {"mode": "replace", "content": system_message}`. The earlier review incorrectly stopped at the domain-layer `SessionConfig` view and did not trace into the SDK boundary implementation.
- [ ] **Real SDK path error translation:** Not compliant. In `amplifier_module_provider_github_copilot/provider.py:481-488`, the real SDK path calls `sdk_session.send_and_wait(...)` with no local `try/except` and no `translate_sdk_error(...)` call, so raw SDK exceptions can escape the provider boundary.
- [ ] **Core provider architecture:** Still not compliant with the Three-Medium Architecture membrane. `provider.py` directly handles SDK-session-shaped objects and methods (`send_and_wait`, lifecycle coordination, direct response extraction) instead of staying a thin orchestrator over a strict adapter boundary.

### Extra Changes Found
- `provider.py` includes substantial mechanism that Golden Vision expects to live elsewhere (`completion.py`, adapter/session factory layers), so the core provider currently does more than the spec assigns to it.

### Verdict: NEEDS CHANGES

### Issues
1. **Missing target decomposition:** `provider.py` remains far above the Golden Vision target and still owns logic that should be extracted.
2. **Missing real-path error translation:** the production `send_and_wait(...)` path in `provider.py:481-488` can leak raw SDK exceptions instead of translating them at the provider boundary.
3. **Boundary violation:** SDK session concepts still leak into `provider.py`, contrary to the contract-first membrane.
4. **Protocol looseness:** methods exist, but `complete(request: Any, **kwargs)` is weaker than the spec's `ChatRequest` contract.

### Required Actions
- Shrink `provider.py` to a thin orchestrator by moving completion/session mechanics out to the intended modules.
- Add provider-boundary error translation for the real SDK path around `sdk_session.send_and_wait(...)`, consistent with the translated test/injected path.
- Remove SDK-session handling from `provider.py`; keep that inside the adapter/session layer.
- Tighten `complete()` to the Provider Protocol contract type (`ChatRequest`).

### PRINCIPAL REVIEW AND AMENDMENTS
- **Rating:** 4/10. Two major factual errors were present, and the original review scope was too narrow.
- **Corrected line count:** `provider.py` should be recorded here as **432 lines, not 532**.
- **Retraction:** The prior `available_tools=[]` and `mode="replace"` findings were false positives. Those requirements are implemented in the correct architectural layer at `amplifier_module_provider_github_copilot/sdk_adapter/client.py:216-229`.
- **Retained valid finding:** `complete(request: Any, **kwargs)` is still weaker than the Provider Protocol contract expecting `ChatRequest`. This remains a valid P2 concern and maps to `F-087-strengthen-complete-parameter-type`.
- **Added missed P0:** The real SDK path at `amplifier_module_provider_github_copilot/provider.py:481-488` has no local error translation around `sdk_session.send_and_wait(...)`. This is the dominant production-facing gap and aligns with `F-072-real-sdk-path-error-translation`.
- **Methodology acknowledgment:** The original file-isolated scope prevented an accurate assessment. Failing to trace `SessionConfig` usage into `sdk_adapter/client.py` led to incorrect conclusions about session configuration compliance.