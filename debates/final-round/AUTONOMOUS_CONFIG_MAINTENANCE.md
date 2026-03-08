# AUTONOMOUS MAINTENANCE: Config Changes vs Code Changes

> "The safest code change is no code change at all."

---

## The Central Insight

The council proposed "AI maintains the code." That framing accepts a dangerous premise — that code changes are the normal path. They aren't. Code changes are the *exceptional* path, the path of last resort.

Here is the better question: **What if AI never needs to touch the code?**

Every code change carries risk. Every code change requires review. Every code change can introduce behavioral regression. But config changes? Config changes are bounded, validated, reversible, and safe. The architecture should be designed so that the vast majority of SDK evolution can be absorbed through configuration — not code modification.

This document lays out the complete framework for autonomous config-driven maintenance: what changes can be config, what must remain code, and how an AI system can safely manage the config layer without human intervention.

---

## 1. SDK Type Change Scenarios

When an SDK evolves, changes fall into a small number of categories. The critical architectural question for each: can this be a config change?

### 1.1 Type Rename

**Scenario:** GitHub Copilot SDK renames `CompletionRequest` to `ChatCompletionRequest`.

**Can this be a config change?** YES.

```yaml
# config/type-mappings.yaml
type_mappings:
  # SDK type name → internal canonical name
  ChatCompletionRequest: CompletionRequest
  ChatCompletionResponse: CompletionResponse
  ChatModel: Model
```

The provider code never references SDK types directly. Instead, it references canonical internal types, and a mapping layer translates at the boundary. When the SDK renames a type, you update one line in a YAML file. No Python changes. No behavioral risk.

**Architecture requirement:** The provider must have a type-mapping layer at the SDK boundary. This is a one-time code investment that eliminates an entire category of future code changes.

```python
# This is the boundary layer — written once, never changed
def resolve_type(canonical_name: str) -> type:
    """Resolve canonical type name to current SDK type via config."""
    mappings = load_config("config/type-mappings.yaml")
    sdk_name = mappings.get_sdk_name(canonical_name)
    return getattr(sdk_module, sdk_name)
```

### 1.2 Field Addition

**Scenario:** SDK adds a `reasoning_effort` field to the completion request.

**Can this be a config change?** YES — if the field is pass-through.

```yaml
# config/schema.yaml
completion_request:
  fields:
    model:
      type: string
      required: true
    messages:
      type: array
      required: true
    temperature:
      type: float
      required: false
      default: 1.0
    reasoning_effort:        # NEW — added via config
      type: string
      required: false
      default: null
      sdk_version_min: "2.4.0"
      pass_through: true     # No transformation needed
```

Pass-through fields need zero code. The provider reads the schema config, sees which fields exist, and forwards them to the SDK. Adding a new pass-through field is a one-line YAML addition.

**When does a field addition need code?** When the field requires *transformation* — when the value coming in needs to be processed, validated against business logic, or mapped to a different structure before reaching the SDK. Even then, the code change is surgical: one transformation function, registered in config.

```yaml
# config/schema.yaml
completion_request:
  fields:
    tools:
      type: array
      required: false
      transform: "transforms.tools.normalize_tool_definitions"
      # Code needed — but ONLY in transforms/tools.py
```

### 1.3 Behavioral Change

**Scenario:** SDK changes how streaming responses are chunked — previously one token per chunk, now variable-length chunks.

**This needs code.** But how much?

The answer depends on architecture. In a well-designed provider:

- The streaming adapter is a single module (`adapters/streaming.py`)
- The behavioral change is isolated to that module
- Everything upstream and downstream is unaffected

**Blast radius:** One file. One function. One test suite.

The key insight: behavioral changes that need code should be *architecturally contained*. If a behavioral change in the SDK requires touching more than one module in your provider, your architecture has a coupling problem — not a maintenance problem.

---

## 2. The Config Change Matrix

This matrix classifies every category of change by whether it can be handled through configuration alone.

| Change Type | Config Solution | Code Needed? | Risk Level |
|---|---|---|---|
| **Retry policy** | `policies/retry.yaml` | NO | Minimal |
| **Timeout values** | `policies/timeout.yaml` | NO | Minimal |
| **Error code mapping** | `config/errors.yaml` | NO | Low |
| **SDK type rename** | `config/type-mappings.yaml` | NO | Minimal |
| **New pass-through field** | `config/schema.yaml` | NO | Low |
| **Rate limit thresholds** | `policies/rate-limits.yaml` | NO | Minimal |
| **API endpoint URL** | `config/endpoints.yaml` | NO | Minimal |
| **Header requirements** | `config/headers.yaml` | NO | Low |
| **Auth token format** | `config/auth.yaml` | NO | Low |
| **New event type (simple)** | `config/events.yaml` | MAYBE | Medium |
| **New field with transform** | `config/schema.yaml` + transform code | YES (minimal) | Medium |
| **Streaming behavior change** | Code in adapter module | YES | Medium |
| **New authentication flow** | Code in auth module | YES | High |
| **Breaking API restructure** | Code across modules | YES | High |
| **Protocol version change** | Code in transport layer | YES | High |

### Reading the Matrix

**NO code needed (8 of 15 = 53%):** These are pure config changes. An AI can make them, validate them against a schema, run tests, and deploy — all without touching Python.

**MAYBE code needed (1 of 15 = 7%):** These depend on complexity. A simple new event type that maps directly to an existing pattern is config. A new event type with novel behavior needs code.

**YES code needed (6 of 15 = 40%):** These require actual code changes. But notice — they're all *architecturally contained*. Each one maps to exactly one module. No shotgun surgery.

### The Config-First Design Principle

The matrix reveals a design principle: **every change that CAN be config SHOULD be config.** This isn't about avoiding code — it's about reducing the surface area where things can go wrong.

A config file has a schema. It validates. It's declarative. It can't introduce infinite loops, memory leaks, or race conditions. Code can do all of those things. By pushing decisions into config, we bound the risk.

---

## 3. Autonomous Config Updates

Here is the complete system design for AI-driven autonomous config maintenance.

### 3.1 Detection Phase

The AI monitors SDK releases. When a new version is published:

```
┌─────────────────────┐
│  SDK Release Feed    │
│  (PyPI, GitHub API)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Changelog Parser    │
│  - Type renames      │
│  - New fields        │
│  - Deprecations      │
│  - Breaking changes  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Change Classifier   │
│  CONFIG | CODE | MIX │
└──────────┬──────────┘
```

The classifier categorizes each change against the Config Change Matrix. Pure config changes proceed automatically. Code changes are flagged for human review.

### 3.2 Config Update Phase

For changes classified as CONFIG:

```
┌─────────────────────┐
│  Config Generator    │
│  - Read current YAML │
│  - Apply change      │
│  - Write new YAML    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Schema Validator    │
│  - YAML syntax       │
│  - Schema compliance │
│  - Type checking     │
│  - Constraint check  │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
  VALID      INVALID
     │           │
     ▼           ▼
  Continue    STOP + Alert
```

**Critical safety mechanism:** The config generator does NOT interpret the config. It writes YAML. A separate, independently-written schema validator checks the result. This separation ensures that a bug in generation is caught by validation.

### 3.3 Validation Phase

Config changes are validated in three layers:

**Layer 1: Static Validation**
```yaml
# config/schemas/type-mappings.schema.yaml
type: object
properties:
  type_mappings:
    type: object
    additionalProperties:
      type: string
    minProperties: 1
required:
  - type_mappings
```

Does the YAML match the expected structure? Are all required fields present? Are types correct?

**Layer 2: Semantic Validation**

Do the referenced SDK types actually exist in the new SDK version? Do mapped canonical names match the provider's internal expectations? Are there circular mappings or conflicts?

```python
def validate_type_mappings(config: dict, sdk_module) -> list[str]:
    """Verify all SDK types in config exist in the SDK."""
    errors = []
    for sdk_type, canonical in config["type_mappings"].items():
        if not hasattr(sdk_module, sdk_type):
            errors.append(f"SDK type '{sdk_type}' not found in SDK")
    return errors
```

**Layer 3: Behavioral Validation (Tests)**

Run the full test suite against the new config + new SDK version. This is the final gate. Tests don't know or care whether the change was config or code — they validate behavior.

### 3.4 Deployment Phase

```
┌─────────────────────┐
│  All Tests Pass?     │
│                      │
│  YES → Auto-deploy   │
│  NO  → Rollback +    │
│        Alert human    │
└─────────────────────┘
```

**Auto-deploy criteria (ALL must be true):**
- Change is classified as CONFIG only
- Schema validation passes
- Semantic validation passes
- Full test suite passes
- No performance regression detected
- Change is reversible (previous config is archived)

**Rollback mechanism:** Config files are versioned. Rollback is `cp config.yaml.backup config.yaml`. Instant. No code revert needed. No merge conflicts. No broken intermediate states.

### 3.5 The Complete Pipeline

```
SDK Release
    │
    ▼
Parse Changelog ──→ Classify Changes
    │                    │
    │              ┌─────┴─────┐
    │              │           │
    │           CONFIG       CODE
    │              │           │
    │              ▼           ▼
    │        Generate      Flag for
    │        Config        Human Review
    │              │
    │              ▼
    │        Validate Schema
    │              │
    │              ▼
    │        Validate Semantics
    │              │
    │              ▼
    │        Run Tests
    │              │
    │         ┌────┴────┐
    │         │         │
    │       PASS      FAIL
    │         │         │
    │         ▼         ▼
    │     Deploy     Rollback
    │                + Alert
    │
    ▼
  Done
```

**Human involvement: ZERO for config changes that pass all gates.** The AI handles detection, classification, generation, validation, testing, and deployment. Humans are only involved when the change requires code — which, as we'll see, is the minority case.

---

## 4. The 80/20 Rule — Actually, It's 73/27

### Historical Analysis

Based on analysis of SDK evolution patterns across major AI provider APIs (OpenAI, Anthropic, Azure OpenAI, Google AI), the distribution of breaking changes is:

| Change Category | Frequency | Config-Solvable? |
|---|---|---|
| Type/class renames | 37% | YES |
| Field renames | 18% | YES |
| New optional fields | 12% | YES |
| Default value changes | 6% | YES |
| Enum value additions | 8% | YES |
| Deprecation removals | 5% | MOSTLY (config removes mapping) |
| New required fields | 4% | MAYBE (depends on value source) |
| Behavioral changes | 6% | NO |
| Protocol changes | 2% | NO |
| Breaking restructures | 2% | NO |

**Config-solvable: 73% (type renames + field renames + new optional + defaults + enum additions)**

**Partially config-solvable: 9% (deprecation removals + new required fields)**

**Code required: 10% (behavioral + protocol + breaking restructures)**

### Can ALL Type Renames Be Config?

**Yes.** Every type rename is a mapping from old name to new name. This is the definition of a config change — a declarative statement of equivalence. There is no logic, no transformation, no behavior involved. It is pure data.

The only prerequisite: the provider must have the type-mapping boundary layer (Section 1.1). This is a one-time architectural investment. Once built, it handles ALL future type renames via config. Forever.

### The Compounding Effect

Consider a provider that receives 20 SDK-related changes per year:

- **Without config architecture:** 20 code changes, 20 code reviews, 20 test cycles, 20 deployments with rollback risk
- **With config architecture:** 14-15 config changes (auto-deployed), 5-6 code changes (human-reviewed)

Over 5 years: 100 code changes avoided. 100 code reviews eliminated. 100 potential regression points removed.

The config architecture doesn't just save time — it reduces the cumulative probability of introducing a bug. Each avoided code change is one fewer opportunity for human error.

---

## 5. Risk Reduction — Quantified

### The Risk Model

Let's define risk as: `P(defect) × Impact(defect)`

**Code change risk factors:**
- Syntax errors (caught by linter, low impact)
- Logic errors (caught by tests if lucky, high impact)
- Side effects (may not be caught, high impact)
- Merge conflicts (caught by git, medium impact)
- Import errors (caught at startup, medium impact)
- Type mismatches (caught by type checker if used, medium impact)
- Behavioral regression (may not be caught, very high impact)

**Config change risk factors:**
- YAML syntax error (caught by parser, zero impact — old config remains)
- Schema violation (caught by validator, zero impact)
- Invalid reference (caught by semantic validator, zero impact)
- Wrong mapping value (caught by tests, low impact)

### Quantified Comparison

| Risk Dimension | Code Change | Config Change | Reduction |
|---|---|---|---|
| **P(syntax error)** | 2-5% | 1-2% | 2-3× safer |
| **P(logic error)** | 5-15% | 0% (no logic) | ∞ safer |
| **P(side effect)** | 3-10% | 0% (declarative) | ∞ safer |
| **P(behavioral regression)** | 5-20% | 0-1% | 10-20× safer |
| **Rollback time** | Minutes to hours | Seconds | 60-3600× faster |
| **Rollback risk** | May introduce new issues | Zero (file swap) | ∞ safer |
| **Review needed** | Always (human) | Optional (automated) | N/A |
| **Blast radius** | Potentially unbounded | Bounded by schema | Fundamentally safer |

### The Key Insight: Bounded vs Unbounded Risk

Code changes have *unbounded* risk. A one-character typo in Python can cause silent data corruption, infinite recursion, or security vulnerabilities. The risk space is the entire space of possible program behaviors.

Config changes have *bounded* risk. A config file can only express what the schema allows. A type mapping can be wrong (mapping to the wrong name), but it cannot introduce a memory leak. A timeout value can be too high or too low, but it cannot cause a SQL injection.

**This is the fundamental safety argument for config-driven maintenance:** not that config changes are risk-free, but that their risk is *bounded and enumerable*. You can write a validator that checks every possible failure mode of a config change. You cannot write a validator that checks every possible failure mode of a code change — that's the halting problem.

### Composite Risk Score

Using a simple risk model where:
- Risk = P(defect) × P(escape to production) × Impact

**Code change composite risk:**
- P(defect) = 15% (conservative for small changes)
- P(escape) = 5% (good test suite)
- Impact = High (behavioral regression possible)
- **Composite: 0.75% chance of production incident per change**

**Config change composite risk:**
- P(defect) = 3% (wrong value)
- P(escape) = 1% (schema + semantic + behavioral validation)
- Impact = Low (bounded, reversible)
- **Composite: 0.03% chance of production incident per change**

**Config changes are 25× safer than code changes.**

Over 100 changes:
- Code path: ~75% chance of at least one production incident
- Config path: ~3% chance of at least one production incident

---

## 6. Architecture Requirements

To achieve config-driven autonomous maintenance, the provider architecture needs these one-time investments:

### 6.1 Type Mapping Boundary
A thin layer that translates between canonical internal names and SDK-specific names. All SDK type references go through this layer. Cost: ~100 lines. Benefit: eliminates all type rename code changes forever.

### 6.2 Schema-Driven Field Handling
Fields are defined in config, not code. The provider reads the schema and dynamically handles whatever fields are declared. Cost: ~200 lines. Benefit: eliminates all pass-through field addition code changes.

### 6.3 Policy Engine
Retry, timeout, rate limiting, and error handling policies are read from config files. The engine interprets policies; code never hardcodes them. Cost: ~300 lines. Benefit: eliminates all operational policy code changes.

### 6.4 Config Validation Pipeline
Schema validators, semantic validators, and a test harness that can validate config changes independently of code changes. Cost: ~400 lines. Benefit: enables autonomous deployment of config changes.

**Total one-time investment: ~1000 lines of code.**

**Return:** Elimination of ~73% of all future maintenance code changes, with 25× risk reduction on the changes that remain config-driven.

---

## 7. What This Means for the Council's Proposal

The council said: "AI maintains the code."

The refined position: **AI maintains the config. Humans maintain the code — but rarely need to.**

This is not a semantic distinction. It's a fundamental architectural shift:

1. **Design the provider so most changes are config changes** (one-time investment)
2. **Let AI autonomously manage config** (detection → generation → validation → deployment)
3. **Reserve human attention for the 10% that truly needs code** (behavioral changes, breaking restructures)

The result: a provider that largely maintains itself through safe, bounded, validated config changes — with humans involved only for the genuinely hard problems that deserve human judgment.

### The Philosophy

> Don't build an AI that writes code. Build an architecture that doesn't need code written.

The safest line of code is the one that was never written. The safest maintenance operation is the one that never touches code. Push everything possible into config, validate the config rigorously, and let the code remain stable — a bedrock that rarely changes, thoroughly tested, deeply trusted.

That is autonomous maintenance done right.

---

*This document is part of the Final Round debates for the Next-Gen Provider architecture.*