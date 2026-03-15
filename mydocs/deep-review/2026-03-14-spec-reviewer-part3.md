## Spec Compliance Review

### Scope
Limited to `mydocs/debates/GOLDEN_VISION_V2.md` (YAML config requirements section), `config/errors.yaml`, `config/events.yaml`, and `config/models.yaml`.

### Spec Requirements Checklist
- [ ] YAML target met: The reviewed files total **185 lines**, so this chunk is in the vision's rough `~160-200` YAML range, but the **per-file target is missed**: `config/errors.yaml` is **93 lines**, above the vision's `~40` target and the stated `50-line` config cap.
- [ ] Error mappings complete per spec: The file correctly uses **kernel error types** (matching v2.1 errata), but it is **not complete** against the vision. Missing/unclear items include explicit **AbortError** coverage, explicit **SessionCreateError/SessionDestroyError -> ProviderUnavailableError** mapping, and **ModelUnavailableError** coverage. The fallback policy also diverges: unknown errors default to **`ProviderUnavailableError` + `retryable: true`**, while the vision's example/default is conservative/non-retryable.
- [ ] Event classifications per spec: Core BRIDGE / CONSUME / DROP classifications match the vision example, but `events.yaml` adds **`system_notification`** under `consume`, which is **not present in the Golden Vision target**.
- [x] Model capabilities defined per spec: `models.yaml` does define **provider defaults**, **model IDs/display names**, **context/output limits**, and **per-model capabilities** in YAML.
- [ ] Config-driven behavior missing: Within reviewed config, the main missing behavior is **explicit abort/session-error policy** plus the vision's **safer unknown-error fallback behavior**.

### Extra Changes Found
- `config/errors.yaml` adds mappings not named in the Golden Vision example: `QuotaExceededError`, `ContextLengthError`, `StreamError`, `InvalidToolCallError`, and `ConfigurationError`.
- `config/events.yaml` adds `system_notification` consume behavior beyond the Golden Vision example.
- `config/models.yaml` includes credential env-var policy, which is not explicitly called out in the YAML target section.

### Verdict: NEEDS CHANGES

### Issues
1. **Missing**: No explicit abort mapping and no explicit session lifecycle error mapping in `config/errors.yaml`.
2. **Different**: Unknown-error fallback is retryable/provider-unavailable instead of the vision's conservative non-retryable default.
3. **Different**: `config/events.yaml` includes `system_notification`, which is outside the Golden Vision target.
4. **Target miss**: `config/errors.yaml` exceeds the vision's config-size target/cap.

### Required Actions
- Add explicit abort and session lifecycle mappings, and clarify whether `ModelUnavailableError` needs a dedicated mapping.
- Revisit fallback retryability for unmapped errors.
- Either document `system_notification` as an intentional spec update or remove it.
- Split/simplify `config/errors.yaml` if the `<=50 line` config-file goal is still being enforced.

### PRINCIPAL REVIEW AND AMENDMENTS
- **Document rating:** 5/10 — Made factual errors about what the spec requires.
- **RETRACT:** The prior claim that the unknown-error fallback diverges from spec is incorrect. `contracts/error-hierarchy.md` explicitly requires unknown errors to fall through to `ProviderUnavailableError` with `retryable: true`, and `config/errors.yaml` matches that contract.
- **RETRACT:** The prior claim about missing `AbortError` / `SessionCreateError` / `SessionDestroyError` was not contract-grounded as written. `SessionCreateError` and `SessionDestroyError` are not defined in `contracts/error-hierarchy.md`, so they should not have been treated as required config entries. The review methodology error was relying on non-authoritative design intent instead of the contract; any `AbortError` concern must be evaluated strictly against the contract text actually present.
- **KEEP:** The `system_notification` finding remains valid, but only as a minor/P3 observation because `config/events.yaml` documents it inline as `SDK v0.1.33` behavior.
- **ADD:** Missed observation — the config is not consumed on the real SDK path. In `amplifier_module_provider_github_copilot/provider.py`, the real path calls `sdk_session.send_and_wait({"prompt": internal_request.prompt})` without local `try/except` or `translate_sdk_error(...)`, so the configured error-mapping policy is bypassed there. This aligns with **F-072**.
- **Methodology issue:** Future spec reviews must compare implementation against the authoritative contract files first and treat aspirational design documents as secondary context, not as the contract of record.
