# WAVE 3 — Technical Debt Analyst (Agent 25)

## Scope note (what I could and could not inspect)

In this workspace, the only material present is the `debates/` directory with `wave1/` and `wave2/`. There is **no provider implementation code** (no `src/`, no package manifest, no tests, no configs) to directly analyze.

That absence is itself a form of technical debt: it prevents grounded assessment of real coupling, correctness, security posture, and maintenance cost. So below I:

1) Call out **likely debt in a typical “provider”** (e.g., an integration/provider package that talks to GitHub Copilot APIs, handles auth, request shaping, streaming, retries, telemetry).
2) Emphasize **AI-maintained codebase failure modes**, detection, and architecture choices that prevent debt from accumulating.
3) Provide **operational debt management**: budgets, metrics, dashboards, and refactoring guardrails.

If you later add the provider code into this repo, the same framework can be applied with concrete file-level findings and a prioritized refactor backlog.

---

# 1) Current Technical Debt

### 1.1 What debt exists in the current provider?

Because the provider code is missing from the repository snapshot, the most immediate, concrete debts are **repository-level debts** that will propagate into implementation debt:

- **Observability gap debt**: without code, tests, and runbooks, there is no way to establish current behavior or regressions. AI agents (and humans) will guess.
- **Traceability debt**: no artifact links code → decisions → requirements → tests. This encourages “fix by patching” rather than “fix by understanding.”
- **Reproducibility debt**: missing build/run instructions, lockfiles, CI config, and deterministic dependencies makes any future change riskier.

For a typical “provider” integration, the most common *actual* code-level debts (what you should expect to find once code exists) include:

1) **Boundary ambiguity**
   - Provider code blending transport, auth, caching, and business logic.
   - No clear contract for inputs/outputs (e.g., “prompt request” object), leading to ad-hoc shapes and drift.

2) **Error-handling debt**
   - Exceptions are swallowed or over-generalized.
   - Retrying everything (including 4xx) or retrying nothing.
   - No classification: transient vs permanent vs caller-error.

3) **Configuration sprawl**
   - Environment variables accessed throughout the code.
   - Undocumented flags; defaults scattered.
   - No validation layer.

4) **Security/credentials debt**
   - Token handling and redaction inconsistent.
   - Logs accidentally include auth headers, prompts, or PII.
   - Unclear separation between “client credential” and “user credential.”

5) **Test debt**
   - Unit tests absent or brittle.
   - No golden-file tests for request formatting.
   - No determinism for time-based or streaming behavior.

6) **Dependency and protocol drift debt**
   - Provider tied to specific API quirks without isolation.
   - Lack of compatibility tests; assumptions about payload fields.

### 1.2 Debt categorization (deliberate vs accidental)

**Deliberate debt** is the debt you *knowingly* take to ship faster with an explicit plan to pay it down. In providers, deliberate debt often appears as:

- “We’ll ship with a simple synchronous flow first; streaming comes later.”
- “We won’t implement multi-tenant auth initially; single token only.”
- “We’ll use a generic retry strategy now; later we’ll add error taxonomy.”

Deliberate debt is acceptable only if it has:

- A **bounded scope** (what exactly is missing).
- A **trigger** (when it must be revisited: traffic level, new customer, security review).
- A **rollback plan** (how to disable the risky part).

**Accidental debt** arises from unclear requirements, rushed patches, or AI-generated “looks right” code. Common accidental debt in providers:

- Inconsistent request/response shapes across codepaths.
- Incomplete handling for rate limits, timeouts, partial streams.
- Duplicate logic for headers, signing, base URLs.
- Non-obvious side effects (mutating inputs, global state).

### 1.3 Debt prioritization

Prioritize technical debt by **risk × frequency × cost of failure** rather than “code ugliness.” For providers, a pragmatic priority stack:

**Priority 0 (stop-the-line)**
- Secret leakage in logs; insecure token storage.
- Incorrect auth boundaries (user token used as app token, etc.).
- Unbounded retries causing request storms.
- Data corruption or cross-tenant data exposure.

**Priority 1 (production correctness & operability)**
- Missing error taxonomy; callers can’t handle failures.
- No timeouts/circuit breaker; provider hangs.
- Lack of observability: no correlation IDs, no metrics.
- Rate limit handling absent.

**Priority 2 (velocity and maintainability)**
- Config sprawl and duplicated plumbing.
- No clear module boundaries.
- Test brittleness; no deterministic fixtures.

**Priority 3 (style and micro-optimizations)**
- Formatting, minor refactors, local improvements.

A useful decision tool is a debt register with fields:

- **User impact** (S0–S3)
- **Likelihood** (1–5)
- **Detectability** (1–5; low detectability = higher priority)
- **Blast radius** (single request vs entire system)
- **Paydown cost** (S/M/L)

---

# 2) AI-Generated Debt Patterns

### 2.1 What debt patterns does AI-written code tend to have?

AI-generated code has distinct “debt signatures”:

1) **Over-abstraction early**
   - Introduces factories, interfaces, and layers before requirements justify them.
   - Increases coupling and cognitive load; hides the actual data flow.

2) **Shallow correctness**
   - Handles the “happy path” perfectly, but misses edge cases: retries, partial failures, streaming truncation, timeouts, cancellation.

3) **Inconsistent semantics**
   - Similar functions differ subtly in naming, return types, or error conventions.
   - Multiple “almost identical” helpers for headers/auth.

4) **Copy-paste divergence**
   - Repeats a pattern across files; later edits fix one copy but not the others.

5) **Config and constants leakage**
   - Magic strings for endpoints/headers; environment variables read everywhere.

6) **Logging debt**
   - Too verbose (noise, cost) or too sparse (no diagnosis).
   - Logs sensitive data due to generic “log request” helpers.

7) **Test illusion**
   - Tests that mock everything, assert nothing meaningful, or are snapshot-heavy with unstable output.

### 2.2 How to detect AI-introduced debt

Detection should be mostly mechanical and behavior-based rather than trying to “spot AI style.” Practical signals:

- **Duplication metrics**: identical blocks across files; repeated header construction.
- **Dependency graph anomalies**: “core” depends on “transport” and “transport” depends on “core.”
- **Error taxonomy absence**: everything throws `Error` with strings; no typed/structured errors.
- **Mismatch between code paths**: e.g., sync request sets headers A/B/C, streaming sets A/B only.
- **Inconsistent logging fields**: missing correlation ID on some paths.
- **Dead feature toggles**: flags referenced but never set; code branches never executed.

AI debt often shows up as “many features exist but none are complete.” A key heuristic: **count the number of partial implementations** (e.g., TODOs, empty handlers, stubbed functions) and treat it as a risk multiplier.

### 2.3 Prevention strategies

Prevention is mostly about constraining the solution space:

- **Narrow contracts first**: define request/response types and error types before implementation.
- **Single place for policy**: retries, timeouts, and backoff live in one module.
- **Single place for config**: parse/validate once, pass a typed config object.
- **Golden tests for protocol**: snapshot *normalized* request payloads/headers (with secrets redacted) to catch drift.
- **Explicit invariants**: “All outbound requests must include `X-Request-ID` and `User-Agent`” enforced by a shared request builder.
- **“No new abstraction” rule**: new patterns must pay for themselves by removing code or enabling tests.

---

# 3) Debt Prevention Architecture

### 3.1 How does architecture prevent debt?

Architecture prevents debt by making the “wrong” change hard and the “right” change easy.

For a provider, the simplest debt-resistant architecture is typically:

- **Domain layer**: pure functions/types; knows nothing about HTTP.
- **Client/transport layer**: handles HTTP, auth injection, retries, timeouts.
- **Adapter layer**: converts domain requests into API-specific payloads.

Key idea: *protocol and auth are infrastructure*, not domain.

Concrete “debt stoppers”:

- **Typed boundary objects** (even in JS/TS, use zod/io-ts or strict TS types):
  - `ProviderRequest` (input)
  - `ProviderResponse` (output)
  - `ProviderError` (structured errors)

- **One-way dependencies**:
  - domain → adapter → transport
  - never transport → domain

- **Policy injection**:
  - `RetryPolicy`, `TimeoutPolicy`, `RateLimitPolicy` are values/config, not scattered code.

### 3.2 Automated debt detection

Automate checks that correlate strongly with long-term maintenance pain:

- **Lint rules**: forbid direct access to `process.env` except in config module.
- **Secret scanning**: ensure logs redact tokens/prompt text.
- **Dependency freshness**: alert when critical dependencies are >N minor versions behind.
- **API contract tests**: compare generated request payloads to expected canonical form.
- **Complexity thresholds**: functions exceeding size/complexity require refactor.

The goal is not “zero warnings,” but **early detection of drift**.

### 3.3 Debt budgets

A debt budget is a deliberate allowance of imperfection with explicit limits. Examples:

- **Complexity budget**: no function > 40 cyclomatic complexity; no file > 400 LOC.
- **Duplication budget**: duplication < 3% (or no duplicated header/auth logic).
- **Error budget (operational)**: provider 5xx rate < 0.5%; timeouts < 0.2%.
- **Test budget**: minimum coverage for critical modules (auth, request builder, retry policy).

Budgets must be enforced by CI gates and reviewed periodically. A good budget is “tight enough to prevent rot, loose enough to ship.”

---

# 4) Refactoring Strategy

### 4.1 When should AI refactor?

AI should refactor when:

- **There is a stable contract** (types, tests, or golden outputs) to prevent behavior change.
- **The refactor reduces duplication or clarifies a boundary**.
- **There is clear evidence of repeated bugs** in the same area (e.g., auth headers diverge).

AI should *not* refactor when:

- Requirements are unclear.
- The code is untested and lacks a baseline.
- The refactor is “architectural” but speculative.

A pragmatic trigger policy:

- If a module has been modified **3+ times in 30 days** (churn), require either tests or refactor to stabilize.
- If a bug repeats in the same subsystem twice, prioritize a structural fix.

### 4.2 Safe refactoring patterns

Refactors that are low-risk and high-payoff in provider code:

1) **Extract request builder**
   - One function builds the canonical outbound request.
   - All call sites use it.

2) **Introduce structured errors**
   - Wrap raw errors into `ProviderError { kind, status?, retryable, cause }`.

3) **Isolate configuration**
   - Replace scattered env reads with `loadConfig()` once.

4) **Normalize logging**
   - A single `logger.withContext({ requestId, userIdHash })` pattern.

5) **Add timeouts and cancellation**
   - Ensure every call has a deadline.

These patterns reduce future bug surface and make tests easier.

### 4.3 Refactoring validation

Validation must be multi-layered:

- **Golden tests**: request payload/header snapshots (redacted).
- **Property tests** (where possible): e.g., “redaction never outputs token-like strings.”
- **Integration tests**: mock server for rate limits, timeouts, 500s.
- **Diff-based review**: ensure no behavior drift in HTTP semantics (methods, paths, headers).

Additionally, require “refactor PR” discipline:

- One refactor per PR.
- No unrelated behavior changes.
- Before/after metrics: duplication reduced, complexity reduced.

---

# 5) Code Rot Prevention

### 5.1 How does code rot without human maintenance?

In AI-maintained codebases, rot accelerates because:

- **Local optimization**: AI fixes the immediate bug; it doesn’t feel long-term pain.
- **Context loss**: future agents don’t know why a workaround exists.
- **Dependency churn**: upstream APIs and libraries change.
- **Silent failure modes**: provider keeps “working” but performance and correctness degrade.

Rot symptoms:

- Flags accumulate; nobody deletes them.
- Compatibility code for old API versions remains.
- Unused helpers remain and mislead future changes.

### 5.2 Dead code detection

Dead code is a prime rot vector because it multiplies ambiguity.

Automated approaches:

- **Static reachability** (TS/JS): unused exports, unused files, unused dependencies.
- **Runtime tracing**: in staging, record which code paths execute.
- **Feature-flag expiry**: flags must have an expiration date; expired flags fail CI.

Process approach:

- Monthly “dead code sweep”: remove unused exports and dependencies.
- “Delete over deprecate” bias: fewer branches = fewer bugs.

### 5.3 Dependency rot

Dependency rot is inevitable. The goal is to make it **predictable and low-cost**:

- Pin versions with lockfiles.
- Automate dependency updates (renovate/dependabot).
- Maintain a small dependency surface area.
- Add contract tests that catch behavioral changes.

Special note for providers: API dependencies (remote service behavior) rot too. Mitigation:

- Keep protocol mapping isolated.
- Add “compatibility harness” tests for expected headers/payload.
- Monitor response schema changes and unknown fields.

---

# 6) Debt Metrics

### 6.1 How do we measure debt?

Debt is best measured as a combination of:

**A) Code health metrics (leading indicators)**
- Cyclomatic complexity distribution.
- File size distribution.
- Duplication percentage.
- Dependency count and depth.
- Test coverage *of critical modules* (auth, request builder, retry).
- Churn vs coverage (high churn + low coverage is a debt hotspot).

**B) Operational metrics (lagging indicators)**
- Error rates by category (timeouts, rate limits, 4xx, 5xx).
- Retry rates and retry success.
- Latency p50/p95/p99.
- “Unknown error” rate (should be near-zero if taxonomy is good).
- Incidents tied to provider changes.

**C) Process metrics (organizational debt)**
- Time to diagnose incidents.
- Mean time to restore.
- PR size and review time.
- Number of hotfixes.

A good rule: if you can’t measure it, you can’t manage it—so start with a small, stable set.

### 6.2 Debt dashboards

Dashboards should answer:

1) “Is the provider stable?”
2) “Is debt increasing?”
3) “Where is it concentrated?”

Minimum dashboard panels:

- Requests/min, error rate, timeout rate.
- Latency p95/p99.
- Rate-limit events.
- Retry volume and backoff.
- Top error kinds.
- Code churn heatmap by module.
- Complexity and duplication trends.

Add an explicit “Debt Budget” widget:

- Complexity budget consumed.
- Duplication budget consumed.
- % critical modules covered by tests.

### 6.3 Alerting on debt growth

Alert on **trends** and **threshold violations**:

- Sudden increases in timeouts or retries.
- Growth in “unknown error” classification.
- Dependency age thresholds (e.g., critical deps lagging > 90 days).
- Churn spikes in low-tested modules.

Avoid noisy alerts. Tie alerts to actions:

- “Unknown error rate > 0.1% for 30m” → investigate error taxonomy gaps.
- “Timeout rate doubled week-over-week” → review timeouts, circuit breaker, upstream health.

---

# Practical playbook (condensed)

If you want AI to maintain a provider long-term with low debt growth:

1) **Lock the contracts** (request/response/errors) and test them.
2) **Centralize policy** (auth, retries, timeouts, rate limits).
3) **Make drift visible** (dashboards + alerts + CI gates).
4) **Enforce deletion** (dead code sweeps, flag expirations).
5) **Refactor only with a baseline** (golden tests + integration harness).

---

## Immediate next steps for this repo

Right now, the biggest debt is that wave3 artifacts don’t exist in the workspace and the provider code is absent. If the provider implementation is intended to be in this repo, add it (or link it) so future waves can produce grounded, file-specific debt findings and concrete remediation PRs.
