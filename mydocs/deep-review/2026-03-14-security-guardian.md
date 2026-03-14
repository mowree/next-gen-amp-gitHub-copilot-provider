# Security Audit Report: next-get-provider-github-copilot

**Date:** 2026-03-14
**Auditor:** security-guardian
**Scope:**
- `mydocs/debates/GOLDEN_VISION_V2.md`
- `contracts/deny-destroy.md`
- `contracts/sdk-boundary.md`
- `amplifier_module_provider_github_copilot/**/*.py`
- Security-relevant tests covering auth, permission handling, SDK boundary, and live SDK assumptions

---

## Executive Summary

**Security Posture:** Adequate but contract-critical controls are only partially enforced.

**Critical Issues:** 0
**High Severity:** 2
**Medium Severity:** 4
**Low Severity:** 1

**Risk Level:** High

The codebase has good defensive intent: no hardcoded credentials, environment-based token resolution, `available_tools=[]`, `on_permission_request` denial, and a registered pre-tool hook. The main risk is not obvious secret leakage or classic injection, but a gap between the Deny+Destroy contract and the real SDK path: end-to-end sovereignty is not currently proven against the live SDK, timeouts are not enforced on the blocking real path, and cleanup/error handling are best-effort in ways that can weaken ephemerality and confidentiality.

---

## Quick Answers to Requested Audit Questions

### 1. Deny hook implementation - does it actually prevent tool execution by SDK?
**Answer:** Not proven on the current SDK; partially enforced by defense-in-depth, but contract assurance is incomplete.

**Evidence:**
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:216-242` sets `available_tools=[]`, `on_permission_request`, and registers `create_deny_hook()`.
- `amplifier_module_provider_github_copilot/provider.py:478-483` uses `send_and_wait()` and does **not** pass `internal_request.tools` into the real SDK path.
- `tests/test_live_sdk.py:37-41,134-150,319-367` marks live deny-hook verification as `xfail` due SDK API drift.

**Assessment:** The implementation currently reduces tool-execution surface, but the repo does not provide a passing live proof that the SDK still honors the deny hook as the contract requires.

### 2. Session destruction - are sessions properly ephemeral?
**Answer:** Mostly, but not fully.

**Evidence:**
- Session disconnect is attempted in `finally` blocks: `sdk_adapter/client.py:248-256` and `provider.py:286-293`.
- However, disconnect failures are only logged and suppressed.
- The provider cleanup path is incomplete: `amplifier_module_provider_github_copilot/__init__.py:81-84` calls `provider.close()`, but `amplifier_module_provider_github_copilot/provider.py:517-523` is a no-op and does not call `self._client.close()`.

**Assessment:** Per-request sessions are intended to be ephemeral, but cleanup is best-effort and the owned SDK client can outlive provider cleanup.

### 3. Credential exposure - any tokens/keys logged or exposed?
**Answer:** No hardcoded secrets found, but raw exception logging creates leakage risk.

**Evidence:**
- Tokens are resolved from environment only: `sdk_adapter/client.py:116-129`.
- No token values are explicitly logged in normal flow.
- `amplifier_module_provider_github_copilot/__init__.py:85-91` logs raw exception strings and full traceback.
- `amplifier_module_provider_github_copilot/error_translation.py:317-351,364-372` propagates raw SDK exception text into kernel errors.

**Assessment:** Secret handling is better than average, but error paths could expose sensitive operational data if the SDK includes tokens, headers, or prompt fragments in exceptions.

### 4. Input validation - are SDK responses validated?
**Answer:** Weakly.

**Evidence:**
- `provider.py:121-157` uses permissive `hasattr()`-based extraction and recursive `.data` unwrapping with no cycle guard.
- `streaming.py:248-273` trusts SDK event dictionaries with minimal normalization.
- `tool_parsing.py:53-89` parses JSON if needed but does not validate tool-call schema beyond basic shape.

**Assessment:** This is acceptable for trusted SDK input, but fragile under SDK drift or malformed objects.

### 5. Error message leakage - do errors expose sensitive info?
**Answer:** Yes, potentially.

**Evidence:**
- Full traceback logging at mount failure: `__init__.py:85-91`.
- Raw exception text preserved in translated errors: `error_translation.py:317-351,364-372`.

### 6. Injection vectors - any string interpolation in prompts?
**Answer:** No dangerous shell/SQL interpolation found, but there is prompt-boundary collapse.

**Evidence:**
- `provider.py:442-455` flattens all message content into one raw prompt string, losing role boundaries.

### 7. Rate limiting - any denial-of-service vectors?
**Answer:** Yes.

**Evidence:**
- Real path uses blocking `send_and_wait()` with no timeout wrapper: `provider.py:478-488`.
- Configured timeout exists in policy but is unused: `config/models.yaml:21-27`.
- No request-level concurrency limiter or local backpressure is present.

### 8. OWASP Top 10 relevance
**Most relevant:**
- **A01 Broken Access Control** - Deny-hook assurance gap on live SDK
- **A03 Injection** - Prompt-boundary confusion via message flattening
- **A04 Insecure Design** - Security contract not fully enforced/verified on real path
- **A05 Security Misconfiguration** - Missing timeout enforcement, best-effort cleanup only
- **A07 Identification and Authentication Failures** - Raw auth/provider errors may leak detail
- **A09 Security Logging and Monitoring Failures** - Sensitive traceback logging

---

## Findings

### 1. Deny+Destroy sovereignty is not end-to-end proven on the current SDK
**Severity:** HIGH

**Location:**
- `amplifier_module_provider_github_copilot/provider.py:478-483`
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:216-242`
- `tests/test_live_sdk.py:37-41,134-150,319-367`

**Evidence:**
```python
# provider.py
async with self._client.session(model=model) as sdk_session:
    sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```

```python
# client.py
session_config["available_tools"] = []
session_config["on_permission_request"] = deny_permission_request
...
sdk_session.register_pre_tool_use_hook(create_deny_hook())
```

```python
# test_live_sdk.py
_SDK_API_DRIFT_REASON = (
    "SDK API drift: CopilotSession no longer has send_message/register_pre_tool_use_hook. "
)
```

**Issue:** The code intends three layers of tool suppression, but the real path currently bypasses the event-driven tool-capture design and the live verification of deny-hook behavior is explicitly xfailed. The implementation is safer than a permissive one, but the central security guarantee is no longer continuously verified against the live SDK.

**Exploit Scenario:** If a future SDK version changes how tools are exposed or how `register_pre_tool_use_hook()` is honored, the repo may not detect loss of sovereignty quickly because the live safety tests already acknowledge API drift and do not enforce passing behavior.

**Impact:**
- Confidentiality: Medium
- Integrity: High
- Availability: Medium

**Fix:**
- Restore a real SDK path that passes tool definitions intentionally and captures tool-call events.
- Make live deny-hook verification a required nightly gate instead of `xfail`.
- Assert that tool denial produces no SDK-side `tool_result_*` execution events.

**Explanation:** This is an insecure-design problem more than a coding mistake: the system relies on a safety boundary it no longer proves in production-like execution.

---

### 2. Real SDK requests have no enforced timeout or circuit breaker
**Severity:** HIGH

**Location:**
- `amplifier_module_provider_github_copilot/provider.py:478-488`
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

**Issue:** The blocking real SDK path does not use `asyncio.timeout`, a circuit breaker, or a semaphore. Configured timeout policy exists but is not enforced.

**Exploit Scenario:** An attacker can issue prompts that cause the SDK or upstream model call to hang for long periods, tying up provider workers and exhausting available sessions/process slots.

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
Also add request concurrency limiting and wire timeout values from config.

**Explanation:** This is a classic availability weakness. The contract discusses resilience, but the active real path does not implement it.

---

### 3. Provider cleanup leaves the owned authenticated SDK client alive
**Severity:** MEDIUM

**Location:**
- `amplifier_module_provider_github_copilot/__init__.py:81-84`
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
    # Currently no resources to clean up
    pass
```

```python
# client.py
async def close(self) -> None:
    if self._owned_client is not None:
        await self._owned_client.stop()
```

**Issue:** The provider has an owned `CopilotClientWrapper`, but `provider.close()` never delegates to `self._client.close()`. That means unmount/cleanup does not stop the owned SDK client subprocess.

**Exploit Scenario:** A long-lived authenticated subprocess remains alive after provider cleanup, increasing token exposure window and resource leakage across lifecycle boundaries.

**Impact:**
- Confidentiality: Medium
- Integrity: Low
- Availability: Medium

**Fix:**
```python
async def close(self) -> None:
    await self._client.close()
```

**Explanation:** Sessions are mostly ephemeral, but the client process is not. This weakens the “destroy” half of Deny+Destroy.

---

### 4. Session destruction is best-effort only; disconnect failures are swallowed
**Severity:** MEDIUM

**Location:**
- `amplifier_module_provider_github_copilot/sdk_adapter/client.py:250-256`
- `amplifier_module_provider_github_copilot/provider.py:286-293`

**Evidence:**
```python
try:
    await sdk_session.disconnect()
except Exception as disconnect_err:
    logger.warning(f"[CLIENT] Error disconnecting session: {disconnect_err}")
```

**Issue:** Cleanup failures are logged and suppressed rather than surfaced or retried. If disconnect fails, session ephemerality becomes aspirational rather than guaranteed.

**Exploit Scenario:** Repeated disconnect failures can accumulate stale sessions or zombie SDK resources, eventually degrading availability and potentially leaving residual authenticated state alive longer than intended.

**Impact:**
- Confidentiality: Low
- Integrity: Low
- Availability: Medium

**Fix:**
- Emit metrics/alerts on disconnect failure.
- Consider fallback hard cleanup of the owned client when session disconnect fails.
- Treat repeated disconnect failures as `ProviderUnavailableError`.

**Explanation:** Silent or soft-failed cleanup is a security-relevant lifecycle bug in systems that rely on ephemerality as a protection boundary.

---

### 5. Error handling may leak sensitive operational data
**Severity:** MEDIUM

**Location:**
- `amplifier_module_provider_github_copilot/__init__.py:85-91`
- `amplifier_module_provider_github_copilot/error_translation.py:317-351,364-372`

**Evidence:**
```python
logger.error(f"[MOUNT] Failed to mount GitHubCopilotProvider: {type(e).__name__}: {e}")
logger.error(f"[MOUNT] Traceback:\n{traceback.format_exc()}")
```

```python
original_message = str(exc)
...
kernel_error = error_class(message, provider=provider, model=model, ...)
```

**Issue:** Raw exception messages and full tracebacks are logged and propagated. If SDK/auth/network exceptions contain token fragments, headers, filesystem paths, working directories, or prompt content, they will leak into logs or user-facing error surfaces.

**Exploit Scenario:** A bad upstream response or auth failure includes sensitive metadata in the exception string; the provider preserves and logs it verbatim, creating a disclosure path.

**Impact:**
- Confidentiality: Medium
- Integrity: None
- Availability: Low

**Fix:**
- Redact common secret patterns before logging or returning errors.
- Avoid full traceback logging for expected operational failures.
- Prefer stable, sanitized error envelopes for caller-facing paths.

**Explanation:** The code does not directly log tokens, but it trusts external exception text too much.

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

**Issue:** The provider trusts SDK object shape with permissive `Any`, `hasattr()`, and dict access. There is no recursion guard, schema validation, or strict normalization layer.

**Exploit Scenario:** A compromised or drifted SDK object with cyclical `.data` references or malformed event shapes can trigger recursion errors, memory growth, or incorrect tool/event interpretation.

**Impact:**
- Confidentiality: Low
- Integrity: Medium
- Availability: Medium

**Fix:**
- Add explicit normalization with depth limits.
- Validate event and response shapes before translation.
- Reject malformed tool-call structures instead of silently normalizing them.

**Explanation:** This is primarily an SDK-boundary hardening issue.

---

### 7. Prompt construction collapses role boundaries, increasing prompt-injection risk
**Severity:** LOW

**Location:** `amplifier_module_provider_github_copilot/provider.py:442-455`

**Evidence:**
```python
messages: list[Any] = getattr(request, "messages", [])
prompt_parts: list[str] = []
for msg in messages:
    ...
internal_request = CompletionRequest(
    prompt="\n".join(prompt_parts),
)
```

**Issue:** Structured message roles are flattened into a single prompt string. This removes the distinction between system, user, and assistant content and makes instruction-confusion easier.

**Exploit Scenario:** A malicious user message can embed text that imitates higher-priority instructions because the provider discards original role boundaries before handing content to the SDK.

**Impact:**
- Confidentiality: Low
- Integrity: Medium
- Availability: None

**Fix:**
- Preserve structured roles if the SDK supports them.
- If flattening is unavoidable, prefix each block with explicit role labels and delimiters.

**Explanation:** This is not shell/SQL injection, but it is still relevant under OWASP A03/A04 for LLM-integrated systems.

---

## Positive Findings

- ✅ **No hardcoded secrets found** in reviewed Python/config files.
- ✅ **Credential resolution uses environment variables only**: `sdk_adapter/client.py:116-129`.
- ✅ **Defense in depth is present by design**: `available_tools=[]`, `on_permission_request`, and `pre_tool_use` denial in `sdk_adapter/client.py:216-242`.
- ✅ **YAML loading uses `yaml.safe_load()`**, avoiding unsafe deserialization.
- ✅ **Tool parsing avoids code execution** by using JSON parsing rather than `eval`-style behavior.

---

## Prioritized Remediation Plan

### High Priority
1. **Re-establish live Deny+Destroy verification against the current SDK**
   - Remove `xfail` posture for deny-hook verification once the SDK contract is updated.
   - Verify no SDK-side tool execution occurs when tools are present.
2. **Add enforced timeout/circuit-breaker behavior to the real `send_and_wait()` path**
   - Use `asyncio.timeout`.
   - Add concurrency limiting and failure accounting.

### Medium Priority
3. **Fix provider cleanup to stop the owned SDK client**
   - Implement `GitHubCopilotProvider.close()` properly.
4. **Harden cleanup failures**
   - Escalate repeated disconnect failures.
   - Add metrics/alerts.
5. **Sanitize exception text before logging or surfacing**
   - Redact token-like substrings and headers.
6. **Add strict SDK response normalization**
   - Validate response/event shape, including recursion limits.

### Low Priority
7. **Preserve role boundaries in prompt construction**
   - Reduce prompt-boundary ambiguity.

---

## OWASP Top 10 Mapping

| OWASP Area | Relevance | Notes |
|---|---|---|
| A01 Broken Access Control | High | Deny-hook enforcement is contract-critical but not currently proven end-to-end on live SDK |
| A02 Cryptographic Failures | Low | No custom crypto present; credential storage is environment-based |
| A03 Injection | Medium | Prompt-boundary collapse increases prompt injection/confusion risk |
| A04 Insecure Design | High | Real path diverges from contract assumptions; no active timeout/circuit breaker |
| A05 Security Misconfiguration | Medium | Best-effort cleanup, unused timeout policy, live security checks xfailed |
| A06 Vulnerable Components | Unknown | Dependency CVE scan not performed in this review |
| A07 Identification/Auth Failures | Medium | Raw auth/provider errors can leak detail |
| A08 Software and Data Integrity Failures | Low | No unsafe deserialization found; config integrity relies on repository controls |
| A09 Security Logging and Monitoring Failures | Medium | Traceback logging may expose too much; cleanup failures only warn |
| A10 SSRF | Not Evidenced | No outbound URL construction from user input found |

---

## Final Verdict

The repository shows deliberate security architecture and several strong controls, but the **Deny+Destroy guarantee is stronger in documentation than in currently verified runtime behavior**. The most important security work is to re-prove sovereignty on the live SDK and add timeout/circuit-breaker enforcement to the real path; until then, the design is defensively intended but not fully security-assured.