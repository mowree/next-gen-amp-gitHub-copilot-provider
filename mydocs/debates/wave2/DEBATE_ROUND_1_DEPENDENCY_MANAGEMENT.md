# Dependency Management Strategy: GitHub Copilot SDK

**Agent 14 — Dependency Management Expert**
**Wave 2, Round 1**

---

## Executive Summary

The GitHub Copilot SDK is a single, volatile external dependency that connects our provider to GitHub's infrastructure. It evolves rapidly, ships multiple releases per month, and is our primary vector for breaking changes. This strategy treats the SDK as **radioactive material**: essential, powerful, but requiring strict containment. Every design decision here optimizes for one outcome — **the SDK can change without our users noticing**.

---

## 1. Version Pinning Strategy

### Decision: Exact Pinning with Automated Upgrade Proposals

**We pin to exact versions. No ranges. No carets. No tildes.**

```
# Correct
"@github/copilot-sdk": "3.2.1"

# Never
"@github/copilot-sdk": "^3.2.1"
"@github/copilot-sdk": "~3.2.1"
"@github/copilot-sdk": ">=3.0.0"
```

**Rationale:**

A range-pinned dependency on a rapidly evolving SDK is a time bomb. With multiple releases per month, a `^` range means any `npm install` or `pnpm install` on a different day could pull a different SDK version. This makes builds non-reproducible and debugging nightmarish. Exact pinning guarantees that every developer, CI run, and production deployment uses the identical SDK binary.

### When to Upgrade

Upgrades are triggered by one of three events:

1. **Security advisory**: Immediate upgrade, bypass normal cadence. Security patches in the SDK (or its transitive dependencies) are treated as P0.
2. **Feature need**: We require a new SDK capability for a planned feature. Upgrade is bundled with the feature work.
3. **Scheduled cadence**: Every two weeks, an automated process proposes the latest stable SDK version. This prevents drift — if we ignore the SDK for months, the eventual upgrade becomes a migration project.

### How to Test Upgrades

Every SDK upgrade — regardless of trigger — passes through the same gate:

1. **Type check**: Does the new SDK version compile against our wrapper layer without type errors?
2. **Unit tests**: All existing unit tests pass with mocked SDK boundaries unchanged.
3. **Integration tests**: A dedicated integration test suite exercises real SDK calls against a test environment (or recorded fixtures).
4. **Behavioral snapshot**: A small set of "golden path" tests that capture exact request/response shapes. If the shape changes, the test fails loudly and forces a human to acknowledge the change.

If any gate fails, the upgrade PR is flagged for manual review rather than auto-merged.

---

## 2. SDK Isolation Architecture

### The Adapter Layer Pattern

The SDK never touches application code directly. All SDK interaction passes through a single **adapter module** — a thin translation layer that owns the import and exposes a stable internal API.

```
┌─────────────────────────────────────────┐
│           Application Code              │
│  (provider logic, handlers, routing)    │
├─────────────────────────────────────────┤
│          SDK Adapter Layer              │  ← We own this contract
│  (copilot-adapter.ts / sdk-client.ts)  │
├─────────────────────────────────────────┤
│        @github/copilot-sdk              │  ← They own this contract
└─────────────────────────────────────────┘
```

**Rules for the adapter layer:**

1. **Single point of import**: The SDK package is imported in exactly one module (or a small cluster of files within one directory). No other file in the codebase may `import` from `@github/copilot-sdk` directly. This is enforced via an ESLint rule or similar static check.

2. **Stable internal types**: The adapter defines its own TypeScript interfaces for everything it exposes. These interfaces are *our* types, not re-exports of SDK types. When the SDK changes a type shape, we update the adapter's mapping — application code remains untouched.

3. **Error normalization**: The adapter catches SDK-specific errors and translates them into our own error hierarchy. Application code never handles `CopilotSDKAuthError` — it handles `ProviderAuthError`.

4. **No SDK types in public signatures**: Functions, hooks, or components that other modules consume must not accept or return SDK types. The adapter converts at the boundary.

### Mock/Stub Strategy for Testing

Because the adapter defines a stable internal interface, testing becomes straightforward:

- **Unit tests**: Mock the adapter interface, not the SDK. Tests import `CopilotAdapter` (our interface) and provide a mock implementation. They never need to know what `@github/copilot-sdk` looks like.
- **Integration tests**: Use a thin test double that implements the adapter interface but records/replays HTTP interactions (via fixtures or a lightweight recording proxy).
- **Adapter-specific tests**: A small, focused test suite validates that the real adapter correctly translates between SDK and internal types. These are the only tests that import the SDK.

This structure means ~95% of our test suite is completely immune to SDK changes. Only the adapter tests need updating when the SDK evolves.

---

## 3. Breaking Change Detection

### Three Layers of Defense

#### Layer 1: Static Type Checking

TypeScript's compiler is our first line of defense. Because the adapter imports the SDK and maps to internal types, any SDK type change that breaks the mapping produces a compile error *in the adapter module only*.

We run `tsc --noEmit` in CI on every commit. If the SDK upgrade PR introduces type errors, they surface immediately and are localized to the adapter.

**Enhancement**: We maintain a `sdk-surface.d.ts` file that declares the *subset* of SDK types we actually use. This acts as a contract snapshot. When upgrading the SDK, we diff the relevant SDK type declarations against our snapshot. Any delta is a signal — not necessarily a problem, but something a human must review.

#### Layer 2: Runtime Behavior Verification

Type compatibility doesn't guarantee behavioral compatibility. A function can keep the same signature but change its return value semantics, timing, or side effects.

We maintain a **behavioral test suite** that validates:

- Authentication flow produces a valid token with expected fields
- Model listing returns objects with expected structure
- Completion requests produce responses with expected shape
- Error responses have expected status codes and message formats
- Rate limiting headers are present and parseable

These tests run against recorded fixtures (for speed in CI) and periodically against live endpoints (for accuracy in a nightly job).

#### Layer 3: API Surface Monitoring

An automated job runs weekly that:

1. Installs the latest SDK version in an isolated environment
2. Extracts the public API surface (exported types, functions, classes)
3. Diffs against the previous week's snapshot
4. If changes are detected, creates an informational issue or notification

This gives us early warning about SDK evolution *before* we attempt an upgrade. We can plan for breaking changes rather than discovering them mid-upgrade.

---

## 4. Upgrade Process

### Automated Upgrade Pipeline

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐     ┌────────────┐
│  Dependabot  │────▶│  Type Check   │────▶│  Test Suite  │────▶│  Human     │
│  or Renovate │     │  (tsc)        │     │  (all gates) │     │  Review    │
│  opens PR    │     │               │     │              │     │            │
└──────────────┘     └───────────────┘     └──────────────┘     └────────────┘
       │                    │                     │                    │
       │              Pass? ▼               Pass? ▼              Approve?
       │              ┌─────────┐          ┌─────────┐          ┌─────────┐
       │              │ ❌ Flag │          │ ❌ Flag │          │ ✅ Merge│
       │              │ for     │          │ for     │          │         │
       │              │ review  │          │ review  │          └─────────┘
       │              └─────────┘          └─────────┘
```

**Step 1 — PR Generation**: Renovate (preferred over Dependabot for its richer configuration) creates a PR every two weeks bumping the SDK to the latest release. The PR description includes the SDK changelog diff.

**Step 2 — Automated Validation**: CI runs the full gate sequence: type check → unit tests → integration tests → behavioral snapshots. If all pass, the PR is labeled `auto-upgradeable`.

**Step 3 — Human Review**: Even auto-upgradeable PRs require one human approval. The reviewer checks the SDK changelog for semantic changes that tests might not catch (deprecation warnings, new required configuration, behavioral shifts documented in release notes).

**Step 4 — Merge Window**: SDK upgrades merge only on designated days (e.g., Tuesday/Wednesday) to ensure the team is available if issues surface. No Friday SDK upgrades.

### Rollback Procedure

If an SDK upgrade causes issues in production:

1. **Immediate**: Revert the version bump commit. Because we exact-pin, reverting one line in `package.json` and the lockfile restores the previous state.
2. **Verify**: Run the full test suite against the reverted version to confirm stability.
3. **Investigate**: Create an issue documenting what broke, why tests didn't catch it, and what test should be added to prevent recurrence.
4. **Re-attempt**: Fix the adapter or add workarounds, then re-attempt the upgrade with the new test coverage in place.

Rollback should take under 5 minutes from decision to deployment.

---

## 5. Minimal Surface Area

### SDK Features We Actually Need

Based on the provider's scope, our SDK usage reduces to a surprisingly small surface:

| SDK Feature | Status | Justification |
|---|---|---|
| Authentication / Token Exchange | **Required** | Core functionality — cannot operate without it |
| Model Listing | **Required** | Provider must enumerate available models |
| Chat Completions (streaming) | **Required** | Primary use case for the provider |
| Chat Completions (non-streaming) | **Required** | Fallback and simpler use cases |
| Embeddings | **Conditional** | Only if next-get core supports embedding providers |
| Token Counting | **Optional** | Nice-to-have, can estimate client-side |
| Fine-tuning APIs | **Excluded** | Not in scope for a provider |
| Assistants / Agents API | **Excluded** | Not in scope |
| Image Generation | **Excluded** | Not in scope |
| Audio APIs | **Excluded** | Not in scope |

**Principle**: Import only the functions and types needed for Required and Conditional features. Do not import utilities, helpers, or convenience wrappers from the SDK that we can trivially implement ourselves.

### Reducing Dependency Surface

The adapter layer should import at most:

- 1 authentication function/class
- 1 client/request function for completions
- 1 model listing function
- Type definitions for request/response shapes

If the SDK bundles all features in a single entry point, we still only reference the specific exports we need. Tree-shaking handles the bundle size, but more importantly, our `sdk-surface.d.ts` snapshot only tracks the types we consume.

### Feature Flags for Optional SDK Features

Optional SDK features (like embeddings or token counting) are gated behind configuration:

```typescript
// Provider configuration
interface CopilotProviderConfig {
  // Core — always active
  auth: AuthConfig;

  // Optional — enabled via config
  features?: {
    embeddings?: boolean;    // Default: false
    tokenCounting?: boolean; // Default: false
  };
}
```

When a feature flag is off, the corresponding SDK imports are never called. This means a breaking change in the SDK's embeddings API doesn't affect users who haven't opted into embeddings. It also simplifies testing — the default configuration exercises the smallest possible SDK surface.

---

## 6. Vendoring Considerations

### Decision: Do Not Vendor

**We do not vendor the Copilot SDK.** Here's the full analysis:

#### Arguments For Vendoring

- **Stability**: A vendored copy can't change unexpectedly. We control exactly what code runs.
- **Offline development**: No need to fetch from a registry.
- **Forking ability**: We could patch SDK bugs without waiting for an upstream fix.

#### Arguments Against Vendoring (Decisive)

- **Authentication coupling**: The SDK handles token exchange with GitHub's infrastructure. If GitHub changes their auth protocol (which they can do server-side at any time), a vendored copy becomes instantly broken. Unlike a library that processes local data, the SDK is a *client* for a *live service*. Vendoring a client while the server evolves freely is a losing proposition.

- **Security updates**: When the SDK patches a vulnerability, we need to pick it up immediately. A vendored copy requires manual patching — a process that's slower and more error-prone than running `npm update`.

- **Maintenance burden**: The SDK is complex enough that understanding its internals for patching purposes would consume significant engineering time. We're a provider, not an SDK maintainer.

- **License compliance**: Vendoring creates ambiguity about which version is in use, complicates license auditing, and may conflict with the SDK's distribution terms.

- **Divergence risk**: Once vendored, the temptation to "just fix this one thing" leads to a fork that diverges from upstream. Merging future updates becomes progressively harder.

#### Alternative to Vendoring: Adapter Isolation

The adapter layer gives us most of vendoring's benefits without the costs:

| Vendoring Benefit | How Adapter Achieves It |
|---|---|
| Stability | Adapter provides stable internal API regardless of SDK changes |
| Bug workarounds | Adapter can work around SDK bugs in the translation layer |
| Controlled surface | Adapter imports only what we need |
| Predictable behavior | Adapter tests verify exact behavior we depend on |

The one thing vendoring provides that the adapter cannot is protection against SDK *removal* from the registry. This is an acceptable risk — if GitHub removes the SDK, we have much bigger problems than dependency resolution.

### Exception: Type Snapshots

While we don't vendor the SDK code, we do maintain a **type snapshot** (`sdk-surface.d.ts`) that captures the SDK types we depend on. This is not vendoring — it's a contract test artifact. It serves as documentation and as a breaking-change detection mechanism, but it never runs in production.

---

## Summary of Key Decisions

| Decision | Choice | Confidence |
|---|---|---|
| Version pinning | Exact pin, no ranges | High |
| Upgrade cadence | Biweekly automated proposals | Medium-High |
| SDK isolation | Single adapter module, no direct imports elsewhere | High |
| Testing strategy | Mock adapter interface, not SDK | High |
| Breaking change detection | Type check + behavioral tests + surface monitoring | High |
| Upgrade automation | Renovate + full CI gates + human approval | High |
| Rollback | Revert version pin (single line change) | High |
| SDK surface area | 4 core imports, feature-flagged optionals | High |
| Vendoring | Do not vendor; use adapter isolation instead | High |
| Type snapshots | Maintain `sdk-surface.d.ts` for contract testing | Medium-High |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SDK introduces silent behavioral change | Medium | High | Behavioral test suite, golden-path snapshots |
| SDK deprecates API we depend on | Medium | Medium | Surface monitoring alerts, adapter absorbs change |
| SDK authentication protocol changes | Low | Critical | Integration tests against live endpoints (nightly) |
| SDK removed from registry | Very Low | Critical | Lockfile + npm cache preserves current version |
| Adapter layer becomes too complex | Low | Medium | Keep adapter thin; complexity signals we're using too much SDK surface |

---

## Architecture Fitness Function

To verify this strategy remains healthy over time, we track:

1. **Adapter line count**: If the adapter exceeds ~300 lines, we're likely absorbing too much SDK complexity. Investigate.
2. **SDK import count**: Number of distinct SDK exports we import. Target: ≤8. Alert at >12.
3. **Upgrade lag**: Days between latest SDK release and our adopted version. Target: ≤21 days. Alert at >45 days.
4. **Test isolation ratio**: Percentage of tests that don't transitively depend on SDK types. Target: >90%.
5. **Upgrade success rate**: Percentage of automated upgrade PRs that pass all gates without manual intervention. Target: >70%.

These metrics are cheap to collect and provide early warning if the dependency relationship is becoming unhealthy.