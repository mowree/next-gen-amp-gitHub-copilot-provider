# Security Audit Report: next-get-provider-github-copilot

**Date:** 2026-03-14
**Auditor:** security-guardian
**Scope:**
- `mydocs/debates/GOLDEN_VISION_V2.md`
- `contracts/deny-destroy.md`
- `contracts/sdk-boundary.md`
- `amplifier_module_provider_github_copilot/**/*.py`
- Security-relevant tests covering permission handling, SDK boundary behavior, provider lifecycle, and live SDK assumptions

---

## Executive Summary

**Security Posture:** Adequate, with several evidence-backed hardening gaps.

**Critical Issues:** 0
**High Severity:** 1
**Medium Severity:** 5
**Low Severity:** 1

**Risk Level:** Medium

The prior draft overstated the Deny+Destroy result. The actual code does implement the core controls in `sdk_adapter/client.py`: it installs `deny_permission_request`, sets `available_tools=[]` on every session, registers a pre-tool deny hook when supported, and disconnects sessions in `finally` blocks. The evidence-backed gaps are narrower: live verification is degraded by SDK API drift, the real blocking path has no enforced timeout, and provider-level cleanup does not stop the owned SDK client.

---

## Quick Answers to Requested Audit Questions

### 1. Deny hook implementation - does code actually install it?
**Answer:** Yes.

**Evidence:**
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:43-69` defines `deny_permission_request()` and returns `denied-by-rules`.
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:195-197` installs `deny_permission_request` when creating the owned SDK client.
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:230-231` installs `deny_permission_request` again in every session config.
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:240-243` registers `create_deny_hook()` on sessions that expose `register_pre_tool_use_hook()`.

**Assessment:** The hook is implemented and wired in code. What is missing is current live proof that the SDK still honors the pre-tool hook path under API drift.

### 2. Session creation - is `available_tools=[]` actually enforced?
**Answer:** Yes.

**Evidence:**
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:216-220` unconditionally sets `session_config["available_tools"] = []`.
- `tests/test_sdk_boundary_contract.py:25-40` asserts `available_tools` is present and equals `[]`.
- `tests/test_sdk_boundary_contract.py:134-165` and `188-189` verify the invariant across model/system-message variations.

**Assessment:** This control is implemented and covered by boundary-contract tests.

### 3. Session destruction - are sessions actually destroyed?
**Answer:** Per-session cleanup is implemented, but provider-wide cleanup is incomplete.

**Evidence:**
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:248-256` disconnects each session in a `finally` block.
- `amplifier_module_provider_github_copilot/provider.py:286-292` also disconnects test/injected sessions in a `finally` block.
- `amplifier_module_provider_github_copilot/provider.py:517-523` leaves `GitHubCopilotProvider.close()` as a no-op.
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:258-268` contains real client shutdown logic, but it is not called by `provider.close()`.
- `amplifier_module_provider_github_copilot/__init__.py:81-82` mount cleanup only calls `provider.close()`.

**Assessment:** Session destruction exists for request-scoped sessions, but provider cleanup does not destroy the owned SDK client process.

---

## VERIFICATION

### Verification of the prior finding: "HIGH risk: Deny+Destroy not fully enforced"

**Result:** **REVISED**. The prior wording was too strong for the code that is actually present.

#### What is implemented in code

**1. Permission denial exists and is wired twice**
```python
# amplifier_module_provider_github_copilot/sdk_adapter/client.py:43-69
def deny_permission_request(request: Any, invocation: dict[str, str]) -> Any:
    try:
        from copilot.types import PermissionRequestResult
        return PermissionRequestResult(
            kind="denied-by-rules",
            message="Amplifier orchestrator controls all operations",
        )
    except ImportError:
        return {
            "kind": "denied-by-rules",
            "message": "Amplifier orchestrator controls all operations",
        }
```

```python
# client.py:195-197
options["on_permission_request"] = deny_permission_request
```

```python
# client.py:230-231
session_config["on_permission_request"] = deny_permission_request
```

**2. SDK built-in tools are explicitly suppressed**
```python
# client.py:216-220
session_config: dict[str, Any] = {}
session_config["available_tools"] = []
```

**3. Pre-tool deny hook is registered when the SDK exposes the hook API**
```python
# client.py:240-243
if hasattr(sdk_session, "register_pre_tool_use_hook"):
    sdk_session.register_pre_tool_use_hook(create_deny_hook())
```

**4. Sessions are disconnected on exit**
```python
# client.py:248-256
try:
    yield sdk_session
finally:
    if sdk_session is not None:
        try:
            await sdk_session.disconnect()
        except Exception as disconnect_err:
            logger.warning(f"[CLIENT] Error disconnecting session: {disconnect_err}")
```

#### What remains unproven or incomplete

**1. Live SDK verification is degraded by API drift**
- `tests/test_live_sdk.py:37-41` documents current SDK drift.
- `tests/test_live_sdk.py:134-185`, `203-221`, and `319-369` mark deny-hook and related live checks `xfail`.

**2. The real provider path does not currently exercise Amplifier tool passing**
```python
# amplifier_module_provider_github_copilot/provider.py:481-483
async with self._client.session(model=model) as sdk_session:
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```
The real path does not pass `internal_request.tools` into `send_and_wait()`, so the runtime path currently reduces tool-execution surface rather than proving full tool-capture behavior.

**3. Provider shutdown does not stop the owned client**
```python
# provider.py:517-523
async def close(self) -> None:
    # Currently no resources to clean up
    pass
```

**Corrected judgment:** The codebase does **not** support the prior claim that Deny+Destroy is missing from implementation. It **does** support a narrower claim: Deny+Destroy core controls are implemented, but live verification is incomplete and provider-level destruction is not fully wired. Severity revised from **HIGH** to **MEDIUM**.

---

## Findings

### 1. Live verification of Deny+Destroy is incomplete under current SDK API drift
**Severity:** MEDIUM

**Location:**
- `tests/test_live_sdk.py:37-41`
- `tests/test_live_sdk.py:134-185`
- `tests/test_live_sdk.py:203-221`
- `tests/test_live_sdk.py:319-369`
- `amplifier_module_provider_github_copilot/provider.py:481-483`

**Issue:** The prior audit incorrectly implied the controls were absent. They are present in implementation, but the live tests that would prove current SDK behavior are `xfail`, and the real `send_and_wait()` path does not pass tool definitions.

**Exploit Scenario:** If a future SDK release changes hook semantics, the repository may not detect that regression quickly because the strongest live verification for deny-hook behavior is not currently passing.

**Impact:**
- Confidentiality: Low
- Integrity: Medium
- Availability: Low

**Fix:**
- Restore passing live verification for deny-hook behavior against the current SDK API.
- Add a real-path test that verifies the exact wrapper behavior used by `GitHubCopilotProvider.complete()`.
- Reconcile contract language with the current `send_and_wait()` integration if tool passing remains intentionally disabled.

**Explanation:** This is an assurance gap, not evidence that the deny controls are missing.

---

### 2. Real SDK requests have no enforced timeout or circuit breaker
**Severity:** HIGH

**Location:**
- `amplifier_module_provider_github_copilot/provider.py:481-483`
- `config/models.yaml:21-27`

**Evidence:**
```python
async with self._client.session(model=model) as sdk_session:
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```

```yaml
defaults:
  timeout: 60
```

**Issue:** The blocking real SDK path does not enforce timeout policy even though timeout policy is configured.

**Exploit Scenario:** A long-running or hung SDK call can hold provider resources indefinitely and degrade service availability.

**Impact:**
- Confidentiality: None
- Integrity: Low
- Availability: High

**Fix:**
```python
async with self._client.session(model=model) as sdk_session:
    async with asyncio.timeout(timeout_s):
        sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```
Also wire timeout values from config and consider concurrency limiting.

**Explanation:** This is the strongest evidence-backed risk in the current code.

---

### 3. Provider cleanup leaves the owned authenticated SDK client alive
**Severity:** MEDIUM

**Location:**
- `amplifier_module_provider_github_copilot/__init__.py:81-82`
- `amplifier_module_provider_github_copilot/provider.py:517-523`
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:258-268`

**Evidence:**
```python
# __init__.py
async def cleanup() -> None:
    await provider.close()
```

```python
# provider.py
async def close(self) -> None:
    pass
```

```python
# client.py
async def close(self) -> None:
    if self._owned_client is not None:
        await self._owned_client.stop()
```

**Issue:** Mount cleanup calls `provider.close()`, but `provider.close()` does not delegate to `self._client.close()`.

**Exploit Scenario:** An authenticated SDK client process may remain alive after provider cleanup, extending token exposure window and consuming resources longer than intended.

**Impact:**
- Confidentiality: Medium
- Integrity: Low
- Availability: Medium

**Fix:**
```python
async def close(self) -> None:
    await self._client.close()
```

**Explanation:** Per-session ephemerality exists, but provider-level destruction is incomplete.

---

### 4. Session destruction is best-effort only; disconnect failures are swallowed
**Severity:** MEDIUM

**Location:**
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:252-256`
- `amplifier_module_provider_github_copilot/provider.py:287-292`

**Evidence:**
```python
try:
    await sdk_session.disconnect()
except Exception as disconnect_err:
    logger.warning(f"[CLIENT] Error disconnecting session: {disconnect_err}")
```

**Issue:** Cleanup failures are logged but not surfaced, retried, or counted.

**Exploit Scenario:** Repeated disconnect failures can leave stale resources or zombie sessions alive without causing any stronger operational response.

**Impact:**
- Confidentiality: Low
- Integrity: Low
- Availability: Medium

**Fix:**
- Emit metrics/alerts for disconnect failures.
- Consider fallback client shutdown if session disconnect fails.
- Escalate repeated failures into provider-health errors.

**Explanation:** The session cleanup code exists, but its failure mode is soft.

---

### 5. Error handling may leak sensitive operational data
**Severity:** MEDIUM

**Location:**
- `amplifier_module_provider_github_copilot/__init__.py:85-91`
- `amplifier_module_provider_github_copilot/error_translation.py:317-372`

**Evidence:**
```python
logger.error(f"[MOUNT] Failed to mount GitHubCopilotProvider: {type(e).__name__}: {e}")
logger.error(f"[MOUNT] Traceback:\n{traceback.format_exc()}")
```

```python
original_message = str(exc)
...
kernel_error = default_class(
    original_message,
    provider=provider,
    model=model,
    retryable=config.default_retryable,
)
```

**Issue:** Raw exception messages and tracebacks are logged and propagated without sanitization.

**Exploit Scenario:** If upstream exceptions contain token fragments, prompt content, headers, filesystem paths, or environment details, those values may leak into logs or caller-visible errors.

**Impact:**
- Confidentiality: Medium
- Integrity: None
- Availability: Low

**Fix:**
- Sanitize exception strings before logging or surfacing.
- Avoid full traceback logging for expected operational failures.
- Prefer stable error envelopes over raw SDK text.

**Explanation:** No direct secret logging was found, but exception text is trusted too broadly.

---

### 6. SDK response and event validation are weak
**Severity:** MEDIUM

**Location:**
- `amplifier_module_provider_github_copilot/provider.py:121-157`
- `amplifier_module_provider_github_copilot/streaming.py:248-273`
- `amplifier_module_provider_github_copilot/tool_parsing.py:53-89`

**Evidence:**
```python
if hasattr(response, "data"):
    return extract_response_content(response.data)
```

```python
event_type: str = str(sdk_event.get("type", ""))
```

```python
args = getattr(tc, "arguments", {})
if isinstance(args, str):
    args = json.loads(args)
```

**Issue:** The provider trusts SDK object shapes with permissive `Any`, `hasattr()`, and dict access; there is no recursion guard or strict schema validation.

**Exploit Scenario:** A malformed or drifted SDK object may trigger recursion problems, misclassification, or incorrect tool/event translation.

**Impact:**
- Confidentiality: Low
- Integrity: Medium
- Availability: Medium

**Fix:**
- Add explicit normalization with depth limits.
- Validate event and response shapes before translation.
- Reject malformed tool-call structures earlier.

**Explanation:** This is a hardening issue at the SDK membrane.

---

### 7. Prompt construction collapses role boundaries, increasing prompt-injection risk
**Severity:** LOW

**Location:** `amplifier_module_provider_github_copilot/provider.py:442-458`

**Evidence:**
```python
messages: list[Any] = getattr(request, "messages", [])
prompt_parts: list[str] = []
for msg in messages:
    ...
internal_request = CompletionRequest(
    prompt="\n".join(prompt_parts),
    model=getattr(request, "model", None),
    tools=getattr(request, "tools", []) or [],
)
```

**Issue:** Structured message roles are flattened into one prompt string before calling the SDK.

**Exploit Scenario:** A malicious user message can imitate higher-priority instructions more easily when original role boundaries are discarded.

**Impact:**
- Confidentiality: Low
- Integrity: Medium
- Availability: None

**Fix:**
- Preserve structured roles if the SDK supports them.
- If flattening remains necessary, prefix each block with explicit role labels and delimiters.

**Explanation:** This is an LLM-specific injection-hardening issue rather than a shell/SQL injection issue.

---

## Positive Findings

- ✅ **No hardcoded secrets found** in reviewed Python/config files.
- ✅ **Credential resolution uses environment variables only**: `sdk_adapter/client.py:116-129`.
- ✅ **Permission denial is implemented in code**: `sdk_adapter/client.py:43-69`, `195-197`, `230-231`.
- ✅ **SDK built-in tool suppression is implemented and tested**: `sdk_adapter/client.py:216-220`, `tests/test_sdk_boundary_contract.py:25-40`.
- ✅ **Per-session cleanup exists in `finally` blocks**: `sdk_adapter/client.py:248-256`, `provider.py:286-292`.
- ✅ **YAML loading uses `yaml.safe_load()`**, avoiding unsafe deserialization.
- ✅ **Tool parsing uses JSON parsing rather than code execution primitives**.

---

## Prioritized Remediation Plan

### High Priority
1. **Enforce timeout policy on the real `send_and_wait()` path**
   - Apply `asyncio.timeout`.
   - Wire timeout values from `config/models.yaml`.
   - Consider concurrency limiting for availability protection.

### Medium Priority
2. **Fix provider cleanup to stop the owned SDK client**
   - Implement `GitHubCopilotProvider.close()` by delegating to `self._client.close()`.
3. **Re-establish live Deny+Destroy verification against the current SDK**
   - Replace `xfail` deny-hook coverage with passing verification once SDK drift is resolved.
   - Add a live or canary test for the exact real wrapper path.
4. **Harden disconnect-failure handling**
   - Emit metrics/alerts and escalate repeated failures.
5. **Sanitize exception text before logging or surfacing**
   - Redact token-like substrings and reduce raw traceback exposure.
6. **Add stricter SDK response normalization**
   - Enforce depth limits and schema checks.

### Low Priority
7. **Preserve role boundaries in prompt construction**
   - Reduce prompt-boundary ambiguity.

---

## OWASP Top 10 Mapping

| OWASP Area | Relevance | Notes |
|---|---|---|
| A01 Broken Access Control | Medium | Core deny controls are implemented, but live proof is degraded by SDK drift |
| A02 Cryptographic Failures | Low | No custom crypto present; credential storage is environment-based |
| A03 Injection | Medium | Prompt-boundary collapse increases prompt-injection/confusion risk |
| A04 Insecure Design | Medium | Provider cleanup and live verification do not fully match the contract story |
| A05 Security Misconfiguration | Medium | Timeout policy exists but is not enforced; cleanup failures are soft |
| A06 Vulnerable Components | Unknown | Dependency CVE scan not performed in this review |
| A07 Identification/Auth Failures | Medium | Raw auth/provider errors can leak detail |
| A08 Software and Data Integrity Failures | Low | No unsafe deserialization found; config integrity relies on repository controls |
| A09 Security Logging and Monitoring Failures | Medium | Traceback logging may expose too much; disconnect failures only warn |
| A10 SSRF | Not Evidenced | No outbound URL construction from user input found |

---

## Final Verdict

The corrected evidence does **not** support the prior claim that Deny+Destroy is simply "not fully enforced" at high severity. The code does implement the main controls: permission denial, built-in tool suppression, pre-tool hook registration when supported, and per-session disconnect. The strongest remaining risks are timeout enforcement, incomplete provider-level client shutdown, and degraded live verification under SDK API drift.

---

## PRINCIPAL REVIEW AND AMENDMENTS

**Reviewed by:** Principal-Level Developer  
**Date:** 2026-03-15  
**Document Rating:** 8/10 — Second-best in the review set

### Verified Correct ✅

Excellent self-correcting methodology. The following findings are verified accurate:

1. **`deny_permission_request()` implemented at client.py:43-69** — VERIFIED
2. **`available_tools=[]` enforced at client.py:216-220** — VERIFIED
3. **`provider.close()` is no-op at provider.py:517-523** — VERIFIED
4. **`client.close()` exists at client.py:258-268** — VERIFIED
5. **Real SDK path has no timeout enforcement** — VERIFIED (zero matches for timeout)
6. **Session disconnect failure swallowed at client.py:252-256** — VERIFIED
7. **Self-correcting approach** — Excellent ("prior draft overstated...")

### Critical Addition: Finding #0 (P0) 🚨

**This review missed the dominant P0 bug that 4+ other reviews caught.**

**Finding #0: Real SDK Path Propagates Raw Exceptions**

**Location:** `provider.py:479-495`

**Issue:** The `send_and_wait()` call has no try/except block:
```python
async with self._client.session(model=model) as sdk_session:
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```

If `send_and_wait()` raises ANY exception:
- No `translate_sdk_error()` call
- Raw SDK exception propagates to kernel
- Contract provider-protocol.md violation

**Security Impact:**
- Information disclosure (raw SDK internals exposed in errors)
- Contract violation (provider-protocol.md requires wrapped errors)
- Integration failure (kernel may not handle SDK-specific exceptions)

**Remediation:** F-072 spec covers this fix.

### Root Cause Connection

Finding #5 ("Error may leak sensitive data") was ON THE RIGHT TRACK but didn't connect to root cause. The root cause is Finding #0: **no try/except on the real SDK path**. Finding #5 should reference Finding #0.

### Valuable New Findings (Unique to This Review)

| Finding | Severity | Status |
|---------|----------|--------|
| No timeout on send_and_wait (Finding #2) | HIGH | **F-085 spec created** |
| Disconnect failures swallowed (Finding #4) | MEDIUM | **F-086 spec created** |

These are important availability and observability concerns that other reviews missed.

### Summary of Specs from This Review

- **F-072** (P0): Real SDK path error translation (referenced, already exists)
- **F-085** (P1): Add timeout enforcement to real SDK path (NEW)
- **F-086** (P2): Handle session disconnect failures properly (NEW)

---

*End of principal amendments. Original findings retained — excellent security methodology.*