## Spec Compliance Review

Scope: reviewed only `contracts/sdk-boundary.md`, `contracts/deny-destroy.md`, `sdk_adapter/client.py`, and `sdk_adapter/types.py`.

### Spec Requirements Checklist
- [x] Session config sets `available_tools: []` on every session (`client.py:216-220`).
- [x] Session config uses `system_message.mode: "replace"` when a system message is provided (`client.py:223-227`).
- [x] Session config sets `on_permission_request` (`client.py:195-199`, `230-231`).
- [x] Session config forces `streaming = True` (`client.py:228-229`).
- [x] Deny hook returns a deny decision for tool requests (`client.py:27-40`).
- [ ] SDK import quarantine: violated. SDK imports occur inside `client.py` (`client.py:57`, `188`) instead of a single `_imports.py` file required by contract.
- [ ] Eager dependency check: violated. Missing SDK is detected only when functions run, not at module import time (`client.py:56-69`, `186-211`).
- [ ] No SDK types cross the membrane: violated. `session()` yields the raw SDK session as `Any` (`client.py:157-175`, `248-249`), and `types.py` exposes `SDKSession = Any` (`types.py:29-32`).
- [ ] Domain types required by the contract are missing/incomplete. `SessionHandle` and `DomainEvent` are absent; `SessionConfig` does not match the contract shape (`types.py:14-32`).
- [ ] `SessionConfig` contract mismatch: implementation uses `system_prompt` and `max_tokens`, but contract requires `system_message`, `tools`, and `reasoning_effort` primitives (`types.py:14-27`).
- [ ] preToolUse hook installation is not unconditional. It is skipped if `register_pre_tool_use_hook` is absent, which violates "install on every session" / "no code path skips hook installation" (`client.py:240-243`).
- [ ] Deny+Destroy is only partial here. Session cleanup exists (`client.py:250-256`), but these files do not implement or evidence the required tool-request capture/return path from SDK events.

### Extra Changes Found
- `types.py` defines `max_tokens`, which is not part of the contract-defined `SessionConfig`.
- `types.py` exports `SDKSession = Any`, which is contrary to the membrane model rather than required supporting code.

### Verdict: NEEDS CHANGES

### Issues
1. **Missing/Incorrect boundary enforcement**: SDK imports are not isolated to `_imports.py`, and missing-SDK failure is lazy instead of import-time.
2. **Membrane breach**: raw SDK sessions cross the adapter boundary, and required domain types are not implemented as specified.
3. **Deny hook guarantee not met**: hook registration is conditional, so there is a skip path.
4. **Session type/config contract mismatch**: `SessionConfig` shape does not match the contract.
5. **Deny+Destroy incomplete in reviewed files**: tool capture/return behavior is not present here.

### Required Actions
- Move all SDK imports into a single `_imports.py` and make SDK availability fail fast at module import.
- Replace raw SDK session exposure with contract-defined domain types/opaque handles.
- Make preToolUse deny-hook registration mandatory, not conditional.
- Align `sdk_adapter/types.py` with the contract-defined `SessionConfig` and add the missing domain types.
- Implement or surface the required tool-capture/return path without letting SDK types cross the boundary.

### PRINCIPAL REVIEW AND AMENDMENTS
- **Document rating:** 7/10 — Strong contract-based review.
- **Verified correct findings:** The principal review confirmed the key boundary findings in this document are correct: missing `_imports.py` quarantine, `SDKSession = Any` breaching the membrane, `SessionConfig` shape drift from contract requirements, conditional `preToolUse` hook installation, the deny-destroy contract violation caused by that skip path, and the missing eager dependency check.
- **Pragmatic hook-registration nuance:** The `if hasattr(..., "register_pre_tool_use_hook")` branch is still a contract violation as written, but the principal review correctly notes it may have been added for SDK-version compatibility. Pragmatic resolution should be one of two explicit choices: either relax the contract to acknowledge SDK variability, or treat a missing hook API as an incompatible SDK and fail fast rather than silently skipping installation.
- **Missed P0 amendment:** This review missed the dominant production-path failure already tracked as `F-072-real-sdk-path-error-translation`. In `amplifier_module_provider_github_copilot/provider.py:481-495`, the real SDK path calls `sdk_session.send_and_wait(...)` and `extract_response_content(...)` with no local `try/except` and no `translate_sdk_error(...)` call, so raw SDK exceptions can escape the provider boundary untranslated.
- **New specs to reference:** `F-088-create-imports-py-sdk-quarantine` tracks the `_imports.py` quarantine requirement, and `F-089-align-sessionconfig-shape-with-contract` tracks the `SessionConfig` contract-shape mismatch.
