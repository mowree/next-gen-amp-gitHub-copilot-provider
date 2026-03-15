# TDD Compliance Audit — Feature Specs & Test Files

**Date:** 2026-03-15  
**Authority:** Principal Reviewer  
**Purpose:** Actionable work order for Amplifier to retrofit TDD compliance across all feature specs and test files.

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total feature specs audited | 90 |
| Specs with TDD Section 7 | 0 |
| Specs with contract anchors | ~35% |
| Test files with naming issues | 12 |
| ConfigCapturingMock usage | 1/35 files |

**Verdict:** All 41 pending features will fail Gate 0 (spec contract anchor check) without retrofit.

---

## Part A: Feature Spec TDD Compliance

### Section 1: Specs Requiring Full TDD Retrofit (Priority: P0)

These specs are in `ready` status and will be executed by dev-machine. Each MUST have Section 7 added.

| Spec ID | File | Current Test Section | Required Action |
|---------|------|---------------------|-----------------|
| F-049 | F-049-fix-architecture-test-paths.md | "Tests Required" (prose) | Add Section 7 TDD table |
| F-050 | F-050-mandatory-deny-hook-installation.md | "Tests Required" (prose) | Add Section 7 TDD table |
| F-051 | F-051-defensive-event-config-loading.md | Has test cases | Add contract anchors |
| F-052 | F-052-real-sdk-streaming-pipeline.md | Has test mentions | Add Section 7 TDD table |
| F-053 | F-053-unify-error-config-loading.md | Has test mentions | Add Section 7 TDD table |
| F-054 | F-054-response-extraction-recursion-guard.md | Has test mentions | Add Section 7 TDD table |
| F-055 | F-055-streaming-accumulator-completion-guard.md | Has test mentions | Add Section 7 TDD table |
| F-056 | F-056-sdk-client-failed-start-cleanup.md | Vague | Add Section 7 TDD table |
| F-059 | F-059-chatrequest-multi-turn-context.md | Vague | Add Section 7 TDD table |
| F-060 | F-060-config-driven-retry.md | Vague | Add Section 7 TDD table |
| F-061 | F-061-error-config-missing-mappings.md | Vague | Add Section 7 TDD table |
| F-062 | F-062-architecture-test-hardening.md | Implicit | Add Section 7 TDD table |
| F-063 | F-063-sdk-boundary-structure.md | Missing | Add Section 7 TDD table |
| F-064 | F-064-pypi-publishing-readiness.md | Missing | Add smoke test anchor |
| F-065 | F-065-provider-decomposition.md | Missing | Add Section 7 TDD table |
| F-066 | F-066-error-translation-safety.md | Vague | Add Section 7 TDD table |
| F-067 | F-067-test-quality-improvements.md | N/A (meta) | Mark as non-TDD |
| F-068 | F-068-event-classification-validation.md | Vague | Add Section 7 TDD table |
| F-069 | F-069-remove-complete-fn-dead-code.md | N/A (cleanup) | Mark as non-TDD |
| F-070 | F-070-cleanup-deferred-imports.md | N/A (cleanup) | Mark as non-TDD |
| F-072 | F-072-real-sdk-path-error-translation.md | Has TDD anchor | Compliant ✓ |
| F-073 | F-073-real-sdk-path-error-test.md | Has TDD anchor | Compliant ✓ |
| F-074 | F-074-config-not-in-wheel.md | Has TDD anchor | Compliant ✓ |
| F-075 | F-075-retry-yaml-dead-config.md | Has TDD anchor | Compliant ✓ |
| F-076 | F-076-fix-async-mock-warning.md | Has TDD anchor | Compliant ✓ |
| F-077 | F-077-delete-tombstone-test-files.md | Has TDD anchor | Compliant ✓ |
| F-078 | F-078-add-context-window-to-fallback-config.md | Has TDD anchor | Compliant ✓ |
| F-079 | F-079-add-py-typed-marker.md | Has TDD anchor | Compliant ✓ |
| F-080 | F-080-add-missing-pypi-metadata.md | Has TDD anchor | Compliant ✓ |
| F-081 | F-081-fix-context-extraction-in-client-error-loading.md | Has TDD anchor | Compliant ✓ |
| F-082 | F-082-wire-provider-close-to-client-close.md | Contract ref only | Add Section 7 TDD table |
| F-083 | F-083-fix-test-contract-events-enum-type.md | N/A (type fix) | Mark as non-TDD |
| F-084 | F-084-remove-redundant-path-import.md | N/A (cleanup) | Mark as non-TDD |
| F-085 | F-085-add-timeout-enforcement-real-sdk-path.md | Vague | Add Section 7 TDD table |
| F-086 | F-086-handle-session-disconnect-failures.md | Vague | Add Section 7 TDD table |
| F-087 | F-087-strengthen-complete-parameter-type.md | Type check only | Mark as non-TDD |
| F-088 | F-088-create-imports-py-sdk-quarantine.md | Structural only | Mark as non-TDD |
| F-089 | F-089-align-sessionconfig-shape-with-contract.md | Docstring only | Mark as non-TDD |
| F-090 | F-090-behavioral-tests-for-behaviors-contract.md | Aspirational | Add Section 7 TDD table |
| F-091 | F-091-ephemeral-session-invariant-tests.md | Aspirational | Add Section 7 TDD table |

### Section 2: TDD Section 7 Template

Insert this section into each spec requiring retrofit:

```markdown
## 7. Test Strategy (TDD)

Write tests BEFORE implementation:

| Test | Type | What it verifies | Contract Anchor |
|------|------|------------------|-----------------|
| `test_<name>_happy_path` | Unit | [primary behavior] | `<contract>:<Section>:MUST:N` |
| `test_<name>_error_case` | Unit | [error handling] | `<contract>:<Section>:MUST:N` |
| `test_<name>_edge_case` | Unit | [boundary] | `<contract>:<Section>:SHOULD:N` |

**Test file:** `tests/test_<module_name>.py`

Tests MUST:
- Reference contract clause in docstring
- Use `ConfigCapturingMock` for SDK boundary tests (not bare MagicMock)
- Fail before implementation (Red phase)
```

### Section 3: Contract Anchor Reference

Available contracts for anchoring:

| Contract | File | Key Sections |
|----------|------|--------------|
| provider-protocol | contracts/provider-protocol.md | EP (entry point), Complete, Close |
| sdk-boundary | contracts/sdk-boundary.md | Config, Types, Errors |
| deny-destroy | contracts/deny-destroy.md | DenyHook, Sovereignty |
| streaming-contract | contracts/streaming-contract.md | Accumulation, Types |
| error-hierarchy | contracts/error-hierarchy.md | Types, Translation |
| event-vocabulary | contracts/event-vocabulary.md | Classification, Events |
| behaviors | contracts/behaviors.md | Retry, Session |

**Anchor format:** `<contract>:<Section>:<MUST|SHOULD|MAY>:<N>`

Example: `deny-destroy:DenyHook:MUST:1`

---

## Part B: Test File Audit

### Section 1: Files Requiring Rename

| Current Name | Issue | Proposed Name | Action |
|--------------|-------|---------------|--------|
| test_bug_fixes.py | Generic catch-all | Split into feature files | Split by AC |
| test_placeholder.py | Dead placeholder | (delete) | Delete |
| test_integration.py | Non-descriptive | test_provider_integration.py | Rename |
| test_f035_error_types.py | F-XXX prefix | test_error_types.py | Rename |
| test_f036_error_context.py | F-XXX prefix | test_error_context.py | Rename |
| test_f037_observability.py | F-XXX prefix | test_observability.py | Rename |
| test_f038_kernel_integration.py | F-XXX prefix | test_kernel_types.py | Rename |
| test_f043_sdk_response.py | F-XXX prefix | test_sdk_response_extraction.py | Rename |
| test_security_fixes.py | F-XXX mixed | test_security.py | Rename |
| test_deny_hook_breach_detector.py | Tombstone | (delete) | Delete |

### Section 2: Files Requiring ConfigCapturingMock Migration

Only `test_sdk_boundary_contract.py` currently uses ConfigCapturingMock. The following SDK boundary tests should migrate:

| File | Current Mock | Required Change |
|------|--------------|-----------------|
| test_sdk_client.py | MagicMock | Use ConfigCapturingMock |
| test_sdk_adapter.py | MagicMock | Use ConfigCapturingMock |
| test_sdk_boundary.py | MagicMock | Merge into test_sdk_boundary_contract.py |
| test_provider.py | MagicMock | Use ConfigCapturingMock for SDK calls |
| test_session_factory.py | MagicMock | Use ConfigCapturingMock |

### Section 3: Files Requiring Contract Anchor Addition

These test files lack contract anchors in docstrings:

| File | Missing Anchors | Contract to Reference |
|------|-----------------|----------------------|
| test_live_sdk.py | sdk-boundary:* | sdk-boundary:Config:MUST:* |
| test_foundation_integration.py | provider-protocol:* | provider-protocol:EP:MUST:* |
| test_concurrent_sessions.py | behaviors:* | behaviors:Session:MUST:* |

### Section 4: Test-to-Feature Mapping

This mapping should be added to STATE.yaml under a `test_coverage` key:

```yaml
test_coverage:
  # Module tests (stable)
  test_provider.py: [provider.py]
  test_streaming.py: [streaming.py]
  test_error_translation.py: [error_translation.py]
  test_tool_parsing.py: [tool_parsing.py]
  test_sdk_adapter.py: [sdk_adapter/client.py, sdk_adapter/types.py]
  test_session_factory.py: [sdk_adapter/client.py]
  
  # Contract tests (stable)
  test_contract_protocol.py: [contracts/provider-protocol.md]
  test_contract_deny_destroy.py: [contracts/deny-destroy.md]
  test_contract_errors.py: [contracts/error-hierarchy.md]
  test_contract_events.py: [contracts/event-vocabulary.md]
  test_contract_streaming.py: [contracts/streaming-contract.md]
  
  # Feature tests (to be consolidated)
  test_error_types.py: [F-035]  # Renamed from test_f035_*
  test_error_context.py: [F-036]  # Renamed from test_f036_*
  test_observability.py: [F-037]  # Renamed from test_f037_*
```

---

## Part C: Completed Specs (F-001 to F-048) — Historical Record

These specs are completed. No action required unless drift is detected during implementation.

### Duplicates Detected:

| Spec ID | Duplicate Of | Action |
|---------|--------------|--------|
| F-002-error-translation.md | F-002-provider-protocol-contract.md | Keep both (different scope) |
| F-003-error-hierarchy-contract.md | F-003-session-factory.md | Keep both (different scope) |
| F-004-tool-parsing.md | F-004-session-factory.md | Keep both (different scope) |
| F-005-basic-completion.md | F-005-event-translation.md | Keep both (different scope) |

### Missing Test File Specifications (Historical):

| Spec ID | Test File Missing | Inferred File |
|---------|-------------------|---------------|
| F-005 | Yes | test_completion.py |
| F-006 | Yes | test_streaming.py |
| F-007 | Yes | test_completion.py |
| F-008 | Yes | test_provider.py |

---

## Part D: Execution Order for Amplifier

### Phase 1: Delete Dead Files (5 min)
```bash
rm tests/test_placeholder.py
rm tests/test_deny_hook_breach_detector.py
```

### Phase 2: Rename Test Files (10 min)
```bash
git mv tests/test_f035_error_types.py tests/test_error_types.py
git mv tests/test_f036_error_context.py tests/test_error_context.py
git mv tests/test_f037_observability.py tests/test_observability.py
git mv tests/test_f038_kernel_integration.py tests/test_kernel_types.py
git mv tests/test_f043_sdk_response.py tests/test_sdk_response_extraction.py
git mv tests/test_integration.py tests/test_provider_integration.py
```

### Phase 3: Add TDD Section 7 to Pending Specs (60 min)

For each spec in the "Requiring Full TDD Retrofit" table:
1. Open `specs/features/<spec>.md`
2. Insert Section 7 template before "Notes" or at end
3. Fill in test table from existing "Tests Required" prose
4. Add contract anchors from contract reference table
5. Specify exact test file name

### Phase 4: Split test_bug_fixes.py (30 min)

Extract ACs into feature-specific tests:
- AC-1 → test_session_cleanup.py
- AC-2 → test_error_propagation.py
- AC-3 → test_config_fallback.py
- AC-5 → test_stream_completion.py
- AC-6 → test_sdk_disconnect.py

Delete test_bug_fixes.py after extraction.

### Phase 5: Migrate to ConfigCapturingMock (45 min)

For each file in Section B.2:
1. Import ConfigCapturingMock from tests/fixtures/config_capture.py
2. Replace bare MagicMock() for SDK client/session with ConfigCapturingMock
3. Add assertions for captured config values

### Phase 6: Add Contract Anchors to Test Docstrings (30 min)

For each test function in SDK boundary tests, add:
```python
def test_example():
    """
    Contract: sdk-boundary:Config:MUST:1
    
    Verifies that SDK session config includes required fields.
    """
```

---

## Part E: Drift Detection (Add to working-session-instructions.md)

Add this check to Step 9 Drift Report:

```bash
# TDD Compliance Check
for spec in specs/features/F-*.md; do
  if ! grep -q "## 7. Test Strategy" "$spec"; then
    echo "⚠️ $spec: Missing TDD Section 7"
  fi
  if ! grep -qE '\w+-\w+:\w+:(MUST|SHOULD|MAY):\d+' "$spec"; then
    echo "⚠️ $spec: No contract anchors found"
  fi
done
```

---

## Appendix: Non-TDD Specs

These specs do not require TDD because they are cleanup/refactor/docs:

- F-017 Technical Debt Cleanup
- F-018 Aggressive Simplification
- F-022 Foundation Integration (config only)
- F-024 Code Quality (tooling)
- F-025 CI Pipeline (infra)
- F-029 Documentation Update
- F-030 Changelog
- F-067 Test Quality Improvements (meta)
- F-069 Remove Dead Code
- F-070 Cleanup Imports
- F-083 Fix Enum Type
- F-084 Remove Redundant Import
- F-087 Strengthen Type (pyright)
- F-088 SDK Quarantine (structural)
- F-089 SessionConfig Docstring

Mark these with `## 7. Test Strategy: N/A (cleanup/refactor)` to pass Gate 0.
