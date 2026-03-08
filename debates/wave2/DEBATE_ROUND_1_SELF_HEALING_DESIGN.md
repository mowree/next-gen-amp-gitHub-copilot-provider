# Self-Healing System Design for Copilot SDK Evolution

> **Wave 2, Agent 12** — Self-Healing System Designer
> **Date**: 2026-03-08
> **Status**: Design Proposal

---

## Executive Summary

The Copilot SDK **will** change. This is not a risk to mitigate — it's a certainty to design for. This document specifies a self-healing architecture that detects SDK changes, attempts automated adaptation, rolls back safely when adaptation fails, and escalates to humans only when machine intelligence is insufficient.

The core principle: **the system should survive SDK minor and patch upgrades without human intervention, and gracefully degrade on major upgrades while clearly signaling what needs human attention.**

---

## 1. SDK Change Detection

### 1.1 Detection Layers

We employ three detection layers, ordered from cheapest to most expensive:

```
┌─────────────────────────────────────────────────┐
│  Layer 1: STATIC DETECTION (pre-install)        │
│  • Package version diff                         │
│  • Changelog parsing                            │
│  • TypeScript type signature diff               │
│  Cost: Near-zero. Runs in CI before deployment. │
├─────────────────────────────────────────────────┤
│  Layer 2: CANARY TESTS (post-install)           │
│  • SDK assumption tests                         │
│  • Contract verification suite                  │
│  • Behavioral snapshot comparison               │
│  Cost: Low. Runs in staging.                    │
├─────────────────────────────────────────────────┤
│  Layer 3: RUNTIME MONITORING (production)       │
│  • Error rate anomaly detection                 │
│  • Response shape validation                    │
│  • Latency deviation alerts                     │
│  Cost: Continuous. Always-on.                   │
└─────────────────────────────────────────────────┘
```

### 1.2 Static Detection: Version Diffing

When a dependency update is proposed (via Dependabot, Renovate, or manual):

```
SDK_UPGRADE_DETECTED
  │
  ├─ Parse semver delta
  │   ├─ PATCH (0.0.x): Low risk → auto-proceed to canary
  │   ├─ MINOR (0.x.0): Medium risk → canary + extended validation
  │   └─ MAJOR (x.0.0): High risk → canary + human review gate
  │
  ├─ Fetch changelog / release notes
  │   ├─ Extract BREAKING CHANGES section
  │   ├─ Identify deprecated APIs we use
  │   └─ Flag new APIs that match our patterns
  │
  └─ TypeScript type diff (if applicable)
      ├─ Compare exported type signatures
      ├─ Detect removed/renamed exports
      └─ Detect changed function signatures
```

**Implementation**: A CI job triggered on dependency update PRs. It runs `npm diff` or equivalent, parses the output, and annotates the PR with a risk assessment.

### 1.3 SDK Assumption Tests (Canaries)

These are the heart of the detection system. For every assumption our provider makes about the SDK, we write a corresponding **assumption test**.

Assumption tests are NOT unit tests of our code. They are **tests of the SDK's behavior that we depend on**.

```typescript
// assumption-tests/event-types.test.ts
describe('SDK Assumption: Event Types', () => {
  test('CopilotRequestPayload has messages array', () => {
    // We assume the payload shape includes messages
    const schema = getTypeSchema(CopilotRequestPayload);
    expect(schema).toHaveProperty('messages');
    expect(schema.messages).toBeArrayOf('CopilotMessage');
  });

  test('CopilotMessage has role and content fields', () => {
    const schema = getTypeSchema(CopilotMessage);
    expect(schema).toHaveProperty('role');
    expect(schema).toHaveProperty('content');
  });

  test('Verification callback accepts expected signature', () => {
    // We assume verification works with token + payload
    expect(typeof verifyPayload).toBe('function');
    expect(verifyPayload.length).toBeGreaterThanOrEqual(2);
  });
});

// assumption-tests/behavioral.test.ts
describe('SDK Assumption: Behavioral Contracts', () => {
  test('SSE streaming sends data in expected format', async () => {
    const stream = createMockStream();
    const chunks = await collectChunks(stream);
    // We assume each chunk is a valid SSE event
    for (const chunk of chunks) {
      expect(chunk).toMatch(/^data: .+\n\n$/);
    }
  });

  test('Error responses use expected HTTP status codes', async () => {
    const result = await triggerKnownError();
    expect([400, 401, 403, 404, 500]).toContain(result.status);
  });
});
```

**Canary Categories**:

| Category | What It Tests | Example |
|----------|--------------|---------|
| **Type Shape** | SDK exports the types we import | `CopilotRequestPayload` exists and has `messages` |
| **Function Signature** | Functions accept the args we pass | `createAckEvent()` takes no args |
| **Behavioral Contract** | SDK behaves as we expect | Streaming sends valid SSE events |
| **Error Contract** | Errors look like we expect | Auth failures return 401 |
| **Integration Point** | Our glue code works with SDK | Our handler receives parsed payload |

### 1.4 Behavioral Snapshot Comparison

Beyond explicit tests, we maintain **behavioral snapshots** — recorded outputs from known inputs.

```
Input: Fixed test payload → SDK processing → Output snapshot
```

After SDK upgrade, we replay the same inputs and diff the outputs. Any deviation is flagged. This catches subtle behavioral changes that explicit tests might miss (e.g., field ordering changes, whitespace differences in SSE output, timing changes).

---

## 2. Automated Adaptation

### 2.1 The Adaptation State Machine

When a canary test fails after an SDK upgrade, the system enters the adaptation pipeline:

```
                    ┌──────────────┐
                    │  TEST FAILS  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   CLASSIFY   │
                    │   FAILURE    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼────────┐ ┌─▼──────────┐
       │ TYPE_CHANGE │ │ BEHAVIOR  │ │ REMOVAL /  │
       │ (shape diff)│ │ CHANGE    │ │ BREAKING   │
       └──────┬──────┘ └──┬────────┘ └─┬──────────┘
              │            │            │
       ┌──────▼──────┐ ┌──▼────────┐ ┌─▼──────────┐
       │ AUTO-ADAPT  │ │ ANALYZE   │ │ ESCALATE   │
       │ via mapping │ │ & ATTEMPT │ │ TO HUMAN   │
       └──────┬──────┘ └──┬────────┘ └────────────┘
              │            │
       ┌──────▼──────┐ ┌──▼────────┐
       │  VALIDATE   │ │  VALIDATE │
       │  FIX        │ │  FIX      │
       └──────┬──────┘ └──┬────────┘
              │            │
         ┌────▼────┐  ┌───▼────┐
         │ PASS?   │  │ PASS?  │
         └────┬────┘  └───┬────┘
          Y/  │  \N    Y/  │  \N
         /    │    \  /    │    \
     DEPLOY  RETRY  DEPLOY ESCALATE
              (max 3)
```

### 2.2 Failure Classification

The classifier examines the test failure and categorizes it:

**Type 1 — Shape Change** (automatable):
- A field was renamed: `message.text` → `message.content`
- A field was moved: `payload.auth` → `payload.verification.auth`
- A type was renamed: `CopilotEvent` → `CopilotStreamEvent`

Detection: Compare old and new TypeScript declarations. If a field disappeared and a new one appeared with a similar type, it's likely a rename.

**Type 2 — Behavioral Change** (partially automatable):
- Response format changed (e.g., JSON structure of SSE events)
- Timing/ordering changed
- Default values changed

Detection: Behavioral snapshot diffs. The system attempts to update our code to match the new behavior.

**Type 3 — Breaking/Removal** (requires escalation):
- An entire API was removed
- A fundamental paradigm shifted (e.g., callbacks → promises)
- Security model changed

Detection: Import failures, type errors that can't be mapped, test failures with no clear adaptation path.

### 2.3 Automated Fix Generation

For Type 1 (Shape Changes), the system uses a **mapping engine**:

```typescript
// The system maintains a migration map
interface MigrationMap {
  typeRenames: Record<string, string>;      // OldType → NewType
  fieldRenames: Record<string, string>;     // old.path → new.path
  signatureChanges: Record<string, SignatureTransform>;
}

// Auto-generated from type diffs
const migration: MigrationMap = {
  typeRenames: {
    'CopilotEvent': 'CopilotStreamEvent',
  },
  fieldRenames: {
    'payload.copilot_token': 'payload.auth.token',
  },
  signatureChanges: {
    'createAckEvent': {
      oldArgs: [],
      newArgs: [{ name: 'options', type: 'AckOptions', optional: true }],
      transform: 'add-optional-arg',
    },
  },
};
```

The system then applies AST-level transformations using the migration map:
1. Find all usages of renamed types → replace with new names
2. Find all accesses to renamed fields → update access paths
3. Find all calls to changed functions → adapt call sites
4. Run the full test suite to validate

For Type 2 (Behavioral Changes), the system:
1. Captures the new behavior via snapshot
2. Updates our behavioral expectations (snapshot files)
3. Checks if our **consumer code** handles the new behavior
4. If not, attempts to generate an adapter layer

### 2.4 The Adapter Layer Pattern

When direct adaptation is too invasive, the system can generate a **shim**:

```typescript
// auto-generated: sdk-adapter.ts
// This adapter normalizes SDK v3.2.0 behavior to match our v3.1.0 expectations.
// Generated by self-healing system on 2026-03-08.
// TODO: Remove when codebase is updated to use v3.2.0 natively.

export function normalizePayload(raw: SDKPayloadV320): NormalizedPayload {
  return {
    messages: raw.messages,                    // unchanged
    auth: raw.verification?.auth ?? raw.auth,  // field moved in 3.2.0
    metadata: raw.meta ?? raw.metadata,        // field renamed in 3.2.0
  };
}
```

This adapter is:
- Auto-generated with a clear deprecation comment
- Tested against both old and new SDK behavior
- Tracked as technical debt with an expiry date
- Flagged for human review within N days

---

## 3. Rollback Strategy

### 3.1 Rollback Decision Tree

```
ADAPTATION ATTEMPTED
  │
  ├─ All tests pass? ──YES──→ DEPLOY with monitoring
  │                            │
  │                     30min health check
  │                            │
  │                     Error rate normal? ──YES──→ COMPLETE
  │                            │
  │                           NO
  │                            │
  ├─────────────────────── ROLLBACK ◄──────────┘
  │
  NO (adaptation failed)
  │
  ├─ Retry count < 3? ──YES──→ RETRY with different strategy
  │
  NO
  │
  └─ ROLLBACK + ESCALATE
```

### 3.2 Rollback Mechanism

Rollback is **version pinning** — we revert to the last known-good SDK version.

```json
// package.json — version pinning strategy
{
  "dependencies": {
    "@anthropic-ai/sdk": "3.1.0",  // Pinned, not ranged
  },
  "selfHealing": {
    "lastKnownGood": "3.1.0",
    "attemptedUpgrade": "3.2.0",
    "rollbackReason": "behavioral-change-in-sse-format",
    "rollbackDate": "2026-03-08T10:00:00Z",
    "nextRetryDate": "2026-03-15T10:00:00Z"
  }
}
```

**Rollback Steps**:
1. Revert `package.json` to pinned last-known-good version
2. Revert any auto-generated adapter code
3. Run full test suite to confirm clean state
4. Deploy the rollback
5. Log the failure for learning (see Section 6)
6. Schedule retry with human review

### 3.3 Compatibility Matrix

The system maintains a compatibility matrix — a living document of which SDK versions work with which provider versions:

```
┌──────────────────┬─────────┬─────────┬─────────┐
│ Provider Version │ SDK 3.0 │ SDK 3.1 │ SDK 3.2 │
├──────────────────┼─────────┼─────────┼─────────┤
│ v1.0.0           │   ✅    │   ✅    │   ❌    │
│ v1.1.0           │   ✅    │   ✅    │   ✅    │
│ v1.2.0           │   ❌    │   ✅    │   ✅    │
└──────────────────┴─────────┴─────────┴─────────┘
```

This matrix is auto-updated by CI. Every SDK version is tested against the current provider code. Every provider release is tested against supported SDK versions.

---

## 4. Human Escalation

### 4.1 Escalation Triggers

Not everything can be auto-healed. The system escalates when:

| Trigger | Why It Can't Auto-Heal | Urgency |
|---------|----------------------|---------|
| Major version bump | Paradigm shift likely | Medium — pin old version |
| API removal with no replacement | Requires architectural decision | High |
| Security model change | Risk of getting security wrong | Critical |
| >3 failed adaptation attempts | Machine is stuck | High |
| Adapter layer count > 5 | Technical debt spiral | Medium |
| Performance regression >50% | May need architectural change | High |
| New required auth flow | Security-critical path | Critical |

### 4.2 Detecting "Outside AI Capability"

The system recognizes its limits through these signals:

1. **Cycle detection**: If the same fix is attempted and reverted more than twice, the problem is beyond pattern matching.
2. **Blast radius**: If the required changes touch more than 30% of the codebase, it's likely an architectural shift.
3. **Semantic gap**: If the type diff shows concepts that don't map to anything in our codebase (entirely new abstractions), a human needs to make design decisions.
4. **Test oracle problem**: If the system can't determine what "correct" looks like for the new behavior, it can't validate any fix.

```
CAN_AUTO_HEAL(failure) → boolean:
  IF failure.type == REMOVAL → false
  IF failure.blastRadius > 0.3 → false
  IF failure.hasMappableReplacement == false → false
  IF failure.isSecurityRelated → false
  IF failure.retryCount >= 3 → false
  IF failure.requiresNewAbstraction → false
  ELSE → true
```

### 4.3 Escalation Notifications

When escalation is needed:

```
ESCALATION PAYLOAD:
{
  "severity": "high",
  "sdk_version": { "from": "3.1.0", "to": "3.2.0" },
  "failed_tests": ["event-types.test.ts#L42", "behavioral.test.ts#L18"],
  "diagnosis": "SSE event format changed from single-line to multi-line. No clear adapter path.",
  "attempted_fixes": [
    { "strategy": "field-remap", "result": "3/12 tests still failing" },
    { "strategy": "adapter-shim", "result": "adapter generated but behavioral test fails" }
  ],
  "recommended_action": "Review new SSE format and update stream parser",
  "rollback_status": "active — running on SDK 3.1.0",
  "time_pressure": "SDK 3.1.0 EOL in 60 days"
}
```

Delivered via:
- GitHub Issue (auto-created with full context)
- Slack/Teams notification (summary + link to issue)
- Dashboard status change (provider health: DEGRADED)

---

## 5. Continuous Validation

### 5.1 Scheduled Assumption Verification

Canary tests run on a schedule, not just on upgrades:

```
┌─────────────────────────────────────────────┐
│           VALIDATION SCHEDULE               │
├─────────────────────────────────────────────┤
│ Every commit:     Unit tests + lint         │
│ Every PR:         Full canary suite         │
│ Daily (nightly):  SDK assumption tests      │
│                   + behavioral snapshots    │
│ Weekly:           Full compatibility matrix  │
│                   + dependency audit        │
│ Monthly:          SDK pre-release testing   │
│                   (test against next/beta)  │
└─────────────────────────────────────────────┘
```

### 5.2 Behavioral Regression Detection

Beyond explicit tests, we monitor production behavior:

```typescript
// Health check: compare current behavior against baseline
interface HealthMetrics {
  errorRate: number;           // Should stay below threshold
  avgResponseTime: number;     // Should stay within 2σ of baseline
  sseChunkFormat: string;      // Should match expected pattern
  authSuccessRate: number;     // Should stay above 99.5%
  eventTypeDistribution: Map<string, number>;  // Should match expected ratios
}

function detectAnomaly(current: HealthMetrics, baseline: HealthMetrics): Anomaly[] {
  const anomalies: Anomaly[] = [];

  if (current.errorRate > baseline.errorRate * 2) {
    anomalies.push({ type: 'error_spike', severity: 'high' });
  }

  if (current.avgResponseTime > baseline.avgResponseTime + 2 * baseline.stdDev) {
    anomalies.push({ type: 'latency_regression', severity: 'medium' });
  }

  // Check for new/missing event types
  for (const [type, count] of current.eventTypeDistribution) {
    if (!baseline.eventTypeDistribution.has(type)) {
      anomalies.push({ type: 'new_event_type', severity: 'low', detail: type });
    }
  }

  return anomalies;
}
```

### 5.3 Integration Health Dashboard

A single dashboard shows the health of every integration point:

```
PROVIDER HEALTH STATUS
━━━━━━━━━━━━━━━━━━━━━
SDK Version:        3.1.0 (pinned)
Latest Available:   3.2.0
Canary Status:      ✅ All passing (last run: 2h ago)
Behavioral Drift:   0.0% (no detected changes)
Adapter Count:      1 (expiry: 2026-04-08)
Next Compat Check:  2026-03-09 02:00 UTC

INTEGRATION POINTS:
  ├─ Payload Parsing:     ✅ Healthy
  ├─ Auth Verification:   ✅ Healthy
  ├─ SSE Streaming:       ✅ Healthy
  ├─ Token Refresh:       ⚠️  Adapter active (v3.0 compat)
  └─ Error Handling:      ✅ Healthy
```

---

## 6. Learning from Fixes

### 6.1 Fix Knowledge Capture

Every adaptation — successful or failed — is recorded in a structured knowledge base:

```typescript
interface AdaptationRecord {
  id: string;
  timestamp: Date;
  sdkVersionFrom: string;
  sdkVersionTo: string;
  failureType: 'type_change' | 'behavioral_change' | 'removal' | 'breaking';
  failedTests: string[];
  diagnosis: string;
  fixStrategy: string;
  fixSucceeded: boolean;
  filesChanged: string[];
  linesChanged: number;
  timeToFix: number;           // minutes
  humanIntervention: boolean;
  patterns: string[];          // e.g., ['field-rename', 'type-rename']
}
```

### 6.2 Pattern Recognition

Over time, the knowledge base reveals patterns:

```
PATTERN ANALYSIS (from 47 recorded adaptations):

Most common change type:
  1. Field rename (38%)  → Always auto-healed
  2. Type rename (22%)   → Always auto-healed
  3. New required field (18%) → 60% auto-healed
  4. Behavioral change (15%) → 30% auto-healed
  5. API removal (7%)    → Never auto-healed

SDK areas most likely to change:
  1. Event payload shapes (52% of changes)
  2. Authentication flow (23% of changes)
  3. Streaming format (15% of changes)
  4. Error codes (10% of changes)

Average time to auto-heal: 4.2 minutes
Average time for human fix: 2.3 hours
Auto-heal success rate: 71%
```

### 6.3 Improving Future Adaptation

The pattern data feeds back into the system:

1. **Prediction**: If event payload shapes change most often, write MORE canary tests for payload shapes and FEWER for stable areas. Allocate testing budget proportionally to change frequency.

2. **Pre-computation**: If field renames are the most common change, pre-compute a mapping table of all our field accesses so renames can be applied instantly.

3. **Proactive hardening**: If authentication flow changes 23% of the time, abstract our auth integration behind an adapter from day one — don't wait for it to break.

4. **Fix templates**: Catalog successful fixes as templates:

```typescript
// Fix template: field-rename
// Trigger: canary test fails with "property X not found"
// Detection: old property missing, new property with same type exists
// Fix: AST rename across codebase
// Validation: re-run canary suite
// Success rate: 98%

const FIELD_RENAME_TEMPLATE = {
  detect: (failure) => failure.message.includes('property') && failure.message.includes('not found'),
  diagnose: (oldTypes, newTypes) => findRenamedFields(oldTypes, newTypes),
  fix: (renames) => applyASTRenames(renames),
  validate: () => runCanarySuite(),
};
```

### 6.4 The Learning Loop

```
    ┌──────────┐
    │  DETECT  │ ← SDK change detected
    └────┬─────┘
         │
    ┌────▼─────┐
    │ CLASSIFY │ ← Use pattern DB to classify faster
    └────┬─────┘
         │
    ┌────▼─────┐
    │   FIX    │ ← Use fix templates from similar past fixes
    └────┬─────┘
         │
    ┌────▼─────┐
    │ VALIDATE │ ← Run full suite
    └────┬─────┘
         │
    ┌────▼─────┐
    │  RECORD  │ ← Store adaptation record
    └────┬─────┘
         │
    ┌────▼─────┐
    │  LEARN   │ ← Update patterns, templates, predictions
    └──────────┘
         │
         └──→ feeds back into CLASSIFY and FIX
```

---

## 7. Architecture Summary

### 7.1 Complete System State Machine

```
                         ┌─────────────┐
                         │   STABLE    │ ← Normal operation
                         └──────┬──────┘
                                │
                         SDK upgrade detected
                                │
                         ┌──────▼──────┐
                         │  ANALYZING  │ ← Static detection + canary tests
                         └──────┬──────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
             All tests pass  Some fail  Critical fail
                    │           │           │
             ┌──────▼──────┐ ┌─▼────────┐ ┌▼───────────┐
             │  UPGRADING  │ │ ADAPTING │ │ ESCALATING │
             └──────┬──────┘ └─┬────────┘ └┬───────────┘
                    │          │            │
                    │    ┌─────▼─────┐      │
                    │    │ VALIDATING│      │
                    │    └─────┬─────┘      │
                    │     Pass │ │ Fail     │
                    │          │ │          │
                    │          │ ┌▼────────┐│
                    │          │ │ROLLBACK ││
                    │          │ └─┬───────┘│
                    │          │   │        │
                    ▼          ▼   ▼        ▼
                 ┌─────────────────────────────┐
                 │          STABLE             │
                 │  (new version or rolled     │
                 │   back to known-good)       │
                 └─────────────────────────────┘
```

### 7.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Version pinning | Exact versions, not ranges | Upgrades must be explicit and tested |
| Adapter vs. direct fix | Prefer direct fix; adapter as fallback | Adapters accumulate debt |
| Retry limit | 3 attempts max | Diminishing returns; escalate early |
| Canary scope | Every SDK assumption = one test | Granular failure detection |
| Rollback speed | Automated, <5 minutes | Production stability > new features |
| Knowledge format | Structured records, not prose | Machine-parseable for pattern recognition |

### 7.3 What This Does NOT Do

Honesty about limitations:

- **Does not handle complete SDK rewrites**. If the SDK is replaced with something fundamentally different, humans must redesign.
- **Does not guarantee zero downtime during adaptation**. There may be a brief window during validation.
- **Does not replace integration tests**. This system augments, not replaces, standard testing.
- **Does not work without canary tests**. The system is only as good as its assumption coverage. Writing and maintaining canaries is a human responsibility.

---

## 8. Implementation Priority

Applying the 80/20 rule — what gives us the most resilience for the least effort:

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| **P0** | SDK assumption tests (canaries) | Medium | Critical — without these, nothing else works |
| **P1** | Version pinning + rollback | Low | High — guaranteed safe fallback |
| **P2** | Static detection in CI | Low | Medium — early warning before deployment |
| **P3** | Type-change auto-adaptation | Medium | High — handles 60% of changes automatically |
| **P4** | Behavioral snapshot comparison | Medium | Medium — catches subtle changes |
| **P5** | Knowledge capture + learning | Low | Medium — compounds over time |
| **P6** | Full adapter generation | High | Medium — handles remaining 30% |
| **P7** | Production anomaly detection | High | Low — most issues caught earlier |

**Start with P0-P2. This alone handles 80% of the problem.**

---

## 9. Conclusion

Self-healing is not magic. It's **canary tests + automated type mapping + rollback + honest escalation**. The system works because it:

1. **Knows what it assumes** (canary tests document every SDK dependency)
2. **Detects when assumptions break** (automated testing on every upgrade)
3. **Fixes what it can** (type renames, field moves, adapter shims)
4. **Admits what it can't** (escalation with full diagnostic context)
5. **Learns from experience** (pattern recognition improves over time)

The most important insight: **the canary test suite IS the self-healing system**. Everything else is automation around the fundamental act of knowing what you depend on and checking if it still holds true.
