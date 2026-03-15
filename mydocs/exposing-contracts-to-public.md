# Exposing Contracts to Public Community

**Date:** 2026-03-15  
**Status:** Recommendation  
**Author:** Principal Engineer Review  
**References:**
- `mydocs/debates/research/MARKDOWN_AS_CONTRACTS_EXAMPLES.md`
- `mydocs/debates/research/MARKDOWN_CONTRACTS_IN_OUR_PROJECT.md`

---

## Executive Summary

**Recommendation: Selective exposure, not wholesale.**

The `specs/features/` folder contains 90 files that are a **mix of concerns**:
- Some are **behavioral contracts** (F-002-provider-protocol-contract.md) — yes, expose
- Most are **implementation work orders** (F-049-fix-architecture-test-paths.md) — no, keep private

---

## The Core Insight from Research

The projects cited in the research that do specification-first development well have a **clear separation**:

| Project | Public | Private |
|---------|--------|---------|
| **Kubernetes** | KEPs (enhancement proposals) | Implementation PRs |
| **Rust** | RFCs (design documents) | rustc source details |
| **W3C** | Specifications | Working group internals |
| **Gauge** | `.spec` files (what to test) | Implementation details |

**Key distinction:** They publish **"what must be true"**, not **"how we're building it"**.

---

## Analysis of `specs/features/` Directory

Looking at the 90 files:

| Pattern | Example | Count | Nature | Public? |
|---------|---------|-------|--------|---------|
| **Contracts** | `F-002-provider-protocol-contract.md` | ~6 | "MUST/SHOULD" behavioral requirements | ✅ Yes |
| **Architecture** | `specs/architecture.md` | 1 | System design | ✅ Yes |
| **Bug fixes** | `F-049-fix-architecture-test-paths.md` | ~20 | Internal cleanup tasks | ❌ No |
| **Implementation tasks** | `F-052-real-sdk-streaming-pipeline.md` | ~40 | Development work orders | ❌ No |
| **Debt cleanup** | `F-017-technical-debt-cleanup.md` | ~10 | Internal maintenance | ❌ No |
| **Test improvements** | `F-067-test-quality-improvements.md` | ~10 | CI/quality work | ❌ No |

**The problem:** Feature specs evolved into **"Jira tickets in markdown"** — excellent for autonomous dev-machine execution, but **not what public contributors need**.

---

## What Public Contributors Actually Need

Based on OSS maintenance experience, contributors need:

1. **What are the rules?** → Contracts with MUST/SHOULD/MAY
2. **What's the architecture?** → High-level design
3. **How do I contribute?** → Clear workflow
4. **What's the specification format?** → Template to follow

**They do NOT need:**
- 90 internal feature specs with priorities and blockers
- Deep-review forensic analysis
- Dev-machine protocols and STATE.yaml
- Implementation status tracking

---

## Recommended Structure

### PUBLIC Repository

```
provider-github-copilot/
├── contracts/                       # ✅ THE GOLD — expose this
│   ├── provider-protocol.md         # 4 methods + 1 property interface
│   ├── deny-destroy.md              # Sovereignty guarantee
│   ├── error-hierarchy.md           # Domain exception taxonomy
│   ├── event-vocabulary.md          # 6 stable event types
│   ├── sdk-boundary.md              # What crosses the membrane
│   ├── streaming-contract.md        # Delta accumulation
│   └── behaviors.md                 # Cross-cutting requirements
│
├── docs/
│   ├── architecture.md              # ← MOVE from specs/architecture.md
│   ├── specification-format.md      # ← NEW: How to write specs (for contributors)
│   ├── contract-testing.md          # ← NEW: How contracts drive tests
│   └── getting-started.md           # Developer onboarding
│
├── CONTRIBUTING.md                   # ← NEW: Required for OSS
├── LICENSE                           # ← NEW: Required for OSS (MIT)
├── CODE_OF_CONDUCT.md                # ← NEW: Standard for OSS
└── README.md
```

### PRIVATE Repository (development infrastructure)

```
provider-github-copilot/
├── [all public structure above]
│
├── specs/
│   ├── features/                    # 90 implementation work orders
│   │   ├── F-001-sdk-adapter-skeleton.md
│   │   ├── ...
│   │   └── F-091-ephemeral-session-invariant-tests.md
│   └── modules/
│       └── completion.md
│
├── mydocs/                          # Analysis documents
│   └── deep-review/
│       └── AMPLIFIER-DIRECTIVE-*.md
│
├── .tool/                           # Forensic tools
├── .dev-machine/                    # Recipes
├── STATE.yaml                       # Dev-machine state
├── CONTEXT-TRANSFER.md              # Session handoff
├── SCRATCH.md                       # Working memory
├── AGENTS.md                        # Operator protocol
└── FEATURE-ARCHIVE.yaml             # Completed features
```

---

## The Key Transformation

**Transform feature specs INTO contracts:**

F-002-provider-protocol-contract.md is already a contract. But most F-* files are tasks.

For public consumption, **distill** them:

```
BEFORE (private feature spec):
┌─────────────────────────────────────────────┐
│ F-052-real-sdk-streaming-pipeline.md        │
│ Status: ready                               │
│ Priority: P0                                │
│ Source: deep-review/integration-specialist  │
│ Blocked By: SDK verification                │
│                                             │
│ ## Problem                                  │
│ The real SDK path doesn't stream events...  │
│                                             │
│ ## Implementation                           │
│ Add queue-based event collection...         │
└─────────────────────────────────────────────┘

AFTER (public contract clause):
┌─────────────────────────────────────────────┐
│ contracts/streaming-contract.md             │
│                                             │
│ ### Real SDK Path Requirements              │
│ - MUST: Use on() handler + asyncio.Queue    │
│ - MUST: Yield CONTENT_DELTA for message_delta│
│ - MUST: Yield CONTENT_COMPLETE for message  │
│ - MUST: Break loop on SESSION_IDLE          │
└─────────────────────────────────────────────┘
```

---

## The Contributor Experience

**For external contributors (public):**

1. Read `contracts/streaming-contract.md`
2. See MUST clauses
3. Look at tests tagged `@pytest.mark.contract("streaming:RealSDK:MUST:1")`
4. Understand what their code must satisfy
5. Submit PR that passes contract compliance tests

**For internal dev-machine (private):**

1. Read `specs/features/F-052-real-sdk-streaming-pipeline.md`
2. See priority, status, blockers, implementation approach
3. Execute with visibility to STATE.yaml
4. Track completion in FEATURE-ARCHIVE.yaml

---

## What to Expose vs Keep Private

| Artifact | Public? | Rationale |
|----------|---------|-----------|
| `contracts/*.md` | ✅ **Yes** | This IS the public API contract |
| `specs/architecture.md` | ✅ **Yes** | System understanding |
| `ENFORCEMENT-FRAMEWORK.md` | ⚠️ **Maybe** | Meta-process (could be useful for contributors) |
| `specs/features/F-*.md` | ❌ **No** | Implementation work orders, status tracking |
| `specs/modules/*.md` | ❌ **No** | Internal decomposition planning |
| `mydocs/**` | ❌ **No** | Internal analysis |
| `.dev-machine/**` | ❌ **No** | Autonomous machine infra |
| `STATE.yaml` | ❌ **No** | Machine state |
| `AGENTS.md` | ❌ **No** | Operator protocol |

---

## Creating the Public Specification Guide

New file: `docs/specification-format.md`

This teaches contributors the methodology without exposing internal machinery:

```markdown
# Specification-Driven Development

This project uses **contracts as the source of truth**.

## The Pattern

1. **Contract defines behavior** (MUST/SHOULD/MAY)
2. **Tests verify contract** (@pytest.mark.contract)
3. **Code implements contract**
4. **Config drives variation** (errors.yaml, events.yaml)

## Writing a Contract Clause

Use RFC 2119 keywords:

- **MUST:** Absolute requirement
- **MUST NOT:** Absolute prohibition  
- **SHOULD:** Recommended
- **MAY:** Optional

Example:
```
### Error Translation Function
- **MUST:** Never raise; always return a domain exception
- **MUST:** Preserve original exception in `.original` attribute
- **SHOULD:** Log the translation for debugging
```

## Test Anchor Format

`{contract}:{section}:{keyword}:{number}`

Example: `error-hierarchy:Translation:MUST:1`

## References

- [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt) — Keyword definitions
- [W3C WPT](https://web-platform-tests.org/) — Spec-driven test pattern
- [Gauge](https://gauge.org/) — Markdown as executable spec
```

---

## Action Plan

| Action | Priority | Phase |
|--------|----------|-------|
| Create `CONTRIBUTING.md` | P0 | Phase 1 (pre-OSS) |
| Create `LICENSE` (MIT) | P0 | Phase 1 |
| Move `specs/architecture.md` → `docs/architecture.md` | P1 | Phase 1 |
| Create `docs/specification-format.md` | P1 | Phase 1 |
| Create `docs/contract-testing.md` | P2 | Phase 2 |
| Add `CODE_OF_CONDUCT.md` | P2 | Phase 2 |
| Keep `specs/features/` in .gitignore for public | P1 | At fork time |

---

## Summary Decision Matrix

| Question | Answer |
|----------|--------|
| Expose `contracts/`? | ✅ **Yes** — this is the gold |
| Expose `specs/features/`? | ❌ **No** — these are work orders |
| Teach the methodology? | ✅ **Yes** — via `docs/specification-format.md` |
| Require spec-first PRs? | ✅ **Yes** — via `CONTRIBUTING.md` |
| Move to `docs/`? | Only `architecture.md` |

---

## Research References

### MARKDOWN_AS_CONTRACTS_EXAMPLES.md

Key projects analyzed:

- **Gauge** (ThoughtWorks) — Purest example of "markdown as contracts"
- **Cucumber** — Gherkin-in-Markdown evolution
- **W3C WPT** — Largest example of "specs drive tests"
- **Kubernetes KEPs** — Structured enhancement proposals
- **Rust RFCs** — Contract-first language design
- **RFC 2119** — MUST/SHOULD/MAY keywords

### MARKDOWN_CONTRACTS_IN_OUR_PROJECT.md

Patterns borrowed:

- **Gauge** — Markdown headings as spec names, bullets as steps
- **W3C WPT** — Test anchors referencing spec sections
- **RFC 2119** — Precise requirement keywords
- **Kubernetes KEPs** — Version tracking, structured sections

The Contract-Config-Code Triangle:

```
                    CONTRACT (Markdown)
                         /\
                        /  \
                       /    \
                      /      \
                     / DRIVES \
                    /   BOTH   \
                   /            \
                  /              \
                 /                \
                /                  \
               /                    \
              ▼                      ▼
    CONFIG (YAML)  ◄────────────►  CODE (Python)
                    CONSUMES
```

---

## External References

- [Gauge](https://gauge.org/) — Markdown-as-spec pattern
- [W3C Web Platform Tests](https://web-platform-tests.org/) — Spec-driven test organization
- [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt) — MUST/SHOULD/MAY keywords
- [Kubernetes KEPs](https://github.com/kubernetes/enhancements) — Structured specification markdown
- [Rust RFCs](https://github.com/rust-lang/rfcs) — Contract-first language design
- [h2spec](https://github.com/summerwind/h2spec) — RFC-derived conformance tests
- [Tom Preston-Werner RDD](https://tom.preston-werner.com/2010/08/23/readme-driven-development.html) — Readme Driven Development
