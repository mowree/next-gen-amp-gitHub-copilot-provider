# Documentation Architecture for AI-Maintained Systems

> **Wave 2, Agent 17 — Documentation Architecture Expert**
>
> *"Documentation is not a complement to AI-maintained code — it IS the institutional memory. Without it, every AI session starts from zero."*

---

## 1. Core Premise: Why Documentation Architecture Matters for AI

Human developers carry institutional knowledge in their heads. They remember why a decision was made, what was tried and failed, and which module is fragile. AI agents have **none of this**. Every session begins with a blank slate, and the only bridge between sessions is written artifacts.

This means documentation in an AI-maintained system serves a fundamentally different purpose than in human-maintained systems:

| Human-Maintained | AI-Maintained |
|------------------|---------------|
| Docs supplement memory | Docs ARE memory |
| Tribal knowledge fills gaps | Gaps cause repeated mistakes |
| Docs can be "good enough" | Docs must be precise and complete |
| Narrative style preferred | Structured format preferred |
| Updated when someone remembers | Must be updated atomically with code |

**Design Principle:** Every piece of knowledge that would live in a human developer's head must have a canonical written location. If it's not written down, it doesn't exist.

---

## 2. Documentation Types

### 2.1 Architecture Decision Records (ADRs)

**Purpose:** Capture the *why* behind architectural choices. AI agents need to understand not just what the code does, but why it was built this way — otherwise they'll "improve" things back to approaches that were already tried and rejected.

**When to create:** Any decision that constrains future implementation choices.

**Template:**

```markdown
# ADR-{NNN}: {Title}

## Status
{Proposed | Accepted | Deprecated | Superseded by ADR-XXX}

## Context
{What is the problem or situation that requires a decision?
 Include concrete constraints, not just abstract concerns.}

## Decision
{What is the decision? State it directly.}

## Consequences
### Positive
- {Benefit 1}

### Negative
- {Trade-off 1}

### Neutral
- {Side effect that is neither good nor bad}

## Alternatives Considered
### {Alternative 1}
- **Why rejected:** {Specific reason}

### {Alternative 2}
- **Why rejected:** {Specific reason}

## Validation
- {How can we verify this decision is still correct?}
- {What conditions would trigger revisiting this decision?}
```

### 2.2 API Reference

**Purpose:** Define the contract surface of every module. AI agents use this to understand what they can call, what guarantees exist, and what constraints apply.

**Rule:** API docs live adjacent to the code they describe. Never in a separate `/docs/api/` tree that drifts out of sync.

**Template (per module):**

```markdown
# Module: {name}

## Purpose
{One sentence. If you need two, the module is doing too much.}

## Public Interface

### `function_name(param: Type, param: Type) -> ReturnType`
**Description:** {What it does}
**Params:**
- `param` — {description, constraints, defaults}
**Returns:** {description of return value}
**Raises:** {error conditions}
**Example:**
```python
result = function_name("input", option=True)
# result: ExpectedOutput(...)
```
**Counterexample (what NOT to do):**
```python
# DON'T: passing unvalidated input
result = function_name(raw_user_input)  # Will raise ValidationError
```

## Internal Details (AI Context)
{Implementation notes that help AI understand non-obvious behavior.
 NOT implementation details that change frequently — those belong in code comments.}

## Dependencies
- {module_a}: Used for {purpose}
- {external_lib}: Version constraints: {why}
```

### 2.3 Behavioral Specifications

**Purpose:** Define what the system DOES, not how it's built. These are the source of truth for correctness. Tests validate these specs; code implements them.

**Template:**

```markdown
# Behavior: {Feature/Capability Name}

## Summary
{What does this behavior accomplish from the user's perspective?}

## Preconditions
- {What must be true before this behavior triggers?}

## Rules
1. WHEN {condition} THEN {outcome}
2. WHEN {condition} AND {condition} THEN {outcome}
3. NEVER {prohibited behavior} BECAUSE {reason}

## Edge Cases
| Scenario | Expected Behavior | Rationale |
|----------|-------------------|-----------|
| {edge case 1} | {what happens} | {why} |
| {edge case 2} | {what happens} | {why} |

## Invariants
- {Thing that must ALWAYS be true, regardless of state}
- {Another invariant}

## Validated By
- Test: `tests/test_{feature}.py::test_{scenario}`
- Integration: `tests/integration/test_{feature}_flow.py`
```

### 2.4 SDK Assumption Documentation

**Purpose:** Document assumptions about external dependencies — SDKs, APIs, libraries — that AI agents might not know about or might have outdated training data for.

**This is critical.** AI models have training cutoffs. SDK behavior changes. Without explicit assumption docs, AI will write code against stale mental models.

**Template:**

```markdown
# SDK Assumptions: {Library/Service Name}

## Version
{Exact version pinned and why}

## Key Assumptions
1. **{Assumption}**: {Detail}
   - Verified: {date or "by test X"}
   - Risk if wrong: {impact}

## Known Gotchas
- {Gotcha 1}: {What happens and how to avoid it}
- {Gotcha 2}: {What happens and how to avoid it}

## Behavioral Quirks
- {Undocumented behavior we depend on}
- {Default that differs from what you'd expect}

## Migration Notes
- {What to watch for when upgrading}
- {Breaking changes in recent versions}

## Validation
- Smoke test: `tests/sdk/test_{library}_assumptions.py`
```

### 2.5 Decision Records (Lightweight)

**Purpose:** For decisions smaller than ADRs but still important enough to record. These prevent AI agents from re-debating settled questions.

**Format:** Inline in the relevant file or module README.

```markdown
<!-- DECISION: {topic}
     Date: {date}
     Choice: {what we chose}
     Why: {one sentence}
     Alternatives rejected: {list}
-->
```

---

## 3. Documentation Location Strategy

### 3.1 The Proximity Principle

**Rule: Documentation lives as close to its subject as possible.**

Distance from code correlates directly with staleness. The further docs are from code, the faster they rot.

```
project/
├── src/
│   ├── auth/
│   │   ├── README.md          ← Module-level docs
│   │   ├── __init__.py        ← Public interface + docstrings
│   │   ├── auth_service.py    ← Inline comments for non-obvious logic
│   │   └── ASSUMPTIONS.md     ← SDK/external dependency assumptions
│   └── ...
├── docs/
│   ├── architecture/
│   │   ├── ADR-001-auth.md    ← Cross-cutting architectural decisions
│   │   └── ADR-002-db.md
│   ├── behaviors/
│   │   ├── login-flow.md      ← Behavioral specifications
│   │   └── token-refresh.md
│   └── onboarding/
│       └── AI_CONTEXT.md      ← Entry point for AI agents
├── CLAUDE.md                   ← Top-level AI context file
└── README.md                   ← Human-facing project overview
```

### 3.2 Location Rules

| Doc Type | Location | Rationale |
|----------|----------|-----------|
| Function/method docs | Docstrings in code | Zero distance, auto-extracted |
| Module purpose | `README.md` in module dir | First thing AI reads when entering module |
| SDK assumptions | `ASSUMPTIONS.md` in module dir | Relevant to that module's dependencies |
| Architecture decisions | `docs/architecture/ADR-NNN.md` | Cross-cutting, not module-specific |
| Behavioral specs | `docs/behaviors/{feature}.md` | Feature-scoped, not module-scoped |
| AI onboarding | `CLAUDE.md` or `AI_CONTEXT.md` at root | Entry point, always loaded first |
| API reference | Generated from docstrings | Single source of truth |

### 3.3 README Structure (Per Module)

Every module directory gets a README with this structure:

```markdown
# {Module Name}

## Purpose
{One sentence}

## Responsibilities
- {Thing 1 this module owns}
- {Thing 2 this module owns}

## NOT Responsible For
- {Common misconception about scope}

## Public API
- `function_a()` — {brief}
- `function_b()` — {brief}

## Key Decisions
- {Decision}: {Why} (see ADR-NNN if applicable)

## Dependencies
- Depends on: {list}
- Depended on by: {list}

## Current State
- Status: {stable | active development | needs refactoring}
- Known issues: {list or "none"}
- Last significant change: {date and description}
```

---

## 4. Documentation Format: Optimizing for AI Consumption

### 4.1 Structured Over Narrative

AI agents parse structured formats more reliably than prose. Every doc should be **scannable** — an AI should be able to extract the information it needs without reading the entire document.

**Prefer:**
- Headers with clear hierarchy
- Tables for comparisons and mappings
- Bullet lists for enumeration
- Code blocks for examples
- Key-value patterns for metadata

**Avoid:**
- Long narrative paragraphs
- Ambiguous language ("sometimes", "usually", "it depends")
- Implicit context ("as we discussed", "the usual approach")
- Forward references without links

### 4.2 The FACT Pattern

Every documentation statement should follow the FACT pattern:

- **F**ixed: States something concrete, not vague
- **A**ctionable: AI can use this to make a decision or write code
- **C**omplete: Doesn't require external context to understand
- **T**estable: Can be verified programmatically or by inspection

**Bad:** "The auth module handles authentication."
**Good:** "The auth module validates JWT tokens from the `/auth/token` endpoint. It rejects tokens older than 1 hour. It uses the `RS256` algorithm with keys from `config.AUTH_PUBLIC_KEY`."

### 4.3 Examples and Counterexamples

Every non-trivial interface should include:

1. **A working example** — the happy path
2. **A counterexample** — a common mistake and why it fails
3. **An edge case example** — behavior at boundaries

AI agents learn patterns from examples faster than from descriptions. Counterexamples prevent the AI from generating code that looks right but fails at runtime.

### 4.4 Markdown as Standard

Use Markdown everywhere. It's:
- Readable by humans and AI alike
- Renderable in most tools
- Diffable in version control
- Lightweight enough to not discourage writing

Use YAML frontmatter for machine-parseable metadata:

```yaml
---
type: adr
status: accepted
created: 2026-03-08
last_validated: 2026-03-08
related: [ADR-001, ADR-003]
modules: [auth, session]
---
```

---

## 5. Living Documentation

### 5.1 Docs Generated from Code

**Principle:** If information exists in code, don't duplicate it in docs — generate it.

| Source | Generated Doc | Method |
|--------|--------------|--------|
| Docstrings | API reference | Sphinx/pdoc/typedoc |
| Type hints | Interface contracts | Type extractor script |
| Test names | Behavior coverage | Test-to-spec mapper |
| Config schemas | Configuration reference | Schema-to-doc generator |
| OpenAPI spec | REST API docs | Swagger/Redoc |

### 5.2 Docs Validated by Tests

**Critical practice:** Documentation that can be wrong will be wrong. Validate it.

```python
# tests/test_docs.py

def test_readme_lists_all_public_functions():
    """Verify module README documents all public API functions."""
    readme_functions = parse_readme_api_section("src/auth/README.md")
    actual_functions = get_public_functions("src/auth/__init__.py")
    assert set(readme_functions) == set(actual_functions), (
        f"README is stale. Missing: {actual_functions - readme_functions}, "
        f"Extra: {readme_functions - actual_functions}"
    )

def test_adr_references_exist():
    """Verify ADRs reference modules that actually exist."""
    for adr in glob("docs/architecture/ADR-*.md"):
        modules = parse_adr_modules(adr)
        for module in modules:
            assert Path(f"src/{module}").exists(), (
                f"{adr} references non-existent module: {module}"
            )

def test_sdk_assumptions_have_validation_tests():
    """Every SDK assumption file must have a corresponding test."""
    for assumption_file in glob("src/**/ASSUMPTIONS.md"):
        module = assumption_file.parent.name
        test_file = f"tests/sdk/test_{module}_assumptions.py"
        assert Path(test_file).exists(), (
            f"No validation test for {assumption_file}"
        )
```

### 5.3 Auto-Updated Documentation

Certain docs should update automatically as part of the development workflow:

1. **Dependency graphs** — regenerated on every build
2. **API reference** — generated from docstrings on commit
3. **Test coverage maps** — updated after test runs
4. **Module dependency lists** — extracted from imports

**Implementation:** A `docs:refresh` task that runs in CI:

```yaml
# In CI pipeline
docs-refresh:
  steps:
    - generate-api-docs
    - update-dependency-graph
    - validate-doc-freshness
    - fail-if-stale
```

---

## 6. Onboarding Documentation: The AI Context Loading Sequence

### 6.1 What an AI Agent Needs to Know

When an AI agent starts a session on this codebase, it needs context loaded in a specific order — from broad to narrow, from stable to volatile.

### 6.2 Context Loading Sequence

```
Phase 1: ORIENTATION (always loaded)
├── CLAUDE.md                    → Project identity, tech stack, conventions
├── docs/onboarding/AI_CONTEXT.md → AI-specific working instructions
└── README.md                    → Project purpose and structure

Phase 2: ARCHITECTURE (loaded for structural work)
├── docs/architecture/ADR-*.md   → Key architectural decisions
├── docs/behaviors/index.md      → Behavioral specification index
└── src/*/README.md              → Module purposes and boundaries

Phase 3: TASK-SPECIFIC (loaded per task)
├── src/{module}/README.md       → Target module details
├── src/{module}/ASSUMPTIONS.md  → SDK/dependency assumptions
├── Related ADRs                 → Decisions affecting this area
└── Related behavioral specs     → Expected behaviors to preserve
```

### 6.3 AI_CONTEXT.md Template (Root-Level Onboarding Doc)

```markdown
# AI Working Context

## Project Identity
- Name: {project}
- Purpose: {one sentence}
- Tech stack: {language, framework, key libraries}
- Architecture style: {monolith, microservice, modular monolith, etc.}

## Critical Rules
1. {Non-negotiable rule 1 — e.g., "Never modify migration files"}
2. {Non-negotiable rule 2 — e.g., "All public functions require docstrings"}
3. {Non-negotiable rule 3}

## Module Map
| Module | Purpose | Owner/Status |
|--------|---------|-------------|
| src/auth | JWT authentication | Stable |
| src/api | REST endpoints | Active development |

## Common Tasks
### Adding a new endpoint
1. {Step 1}
2. {Step 2}

### Modifying a behavior
1. Update behavioral spec in `docs/behaviors/`
2. Update tests to match
3. Implement change
4. Verify spec, tests, and code are aligned

## Things That Will Bite You
- {Gotcha 1}: {explanation}
- {Gotcha 2}: {explanation}

## Essential Reading (Priority Order)
1. This file
2. `README.md` — project overview
3. `docs/architecture/ADR-001.md` — foundational architecture decision
4. Module README for your target area
```

---

## 7. Documentation Maintenance: Keeping Docs Alive

### 7.1 Atomic Doc Updates

**Rule: When AI changes code, docs update in the same commit.**

This is non-negotiable. Docs that update "later" never update. The practice:

1. AI reads relevant docs before making changes
2. AI identifies which docs are affected by the change
3. Code change AND doc update are committed together
4. CI validates doc consistency

### 7.2 Doc Freshness Validation

Every doc file includes metadata for freshness tracking:

```yaml
---
last_validated: 2026-03-08
validates_against: src/auth/**/*.py
staleness_threshold_days: 30
---
```

A CI job checks:

```python
def check_doc_freshness():
    for doc in all_docs_with_metadata():
        source_files = glob(doc.validates_against)
        latest_source_change = max(git_last_modified(f) for f in source_files)
        if latest_source_change > doc.last_validated:
            if (today - doc.last_validated).days > doc.staleness_threshold_days:
                fail(f"{doc.path} is stale: source changed {latest_source_change}, "
                     f"doc last validated {doc.last_validated}")
```

### 7.3 Stale Doc Detection Strategies

| Strategy | Implementation | Catches |
|----------|---------------|---------|
| Metadata freshness | YAML frontmatter + CI check | Time-based staleness |
| Reference validation | Test that referenced files/functions exist | Broken references |
| Content hashing | Hash code sections, compare on CI | Code changed but docs didn't |
| Coverage tracking | Map docs to code, flag undocumented areas | Missing documentation |
| AI pre-flight check | AI reads docs before coding, flags inconsistencies | Semantic staleness |

### 7.4 The Documentation Contract

For every code change, the AI agent must answer:

1. **Which docs did I read?** (Listed in commit message or PR)
2. **Which docs are affected by this change?** (Must be updated)
3. **Are there new concepts that need documentation?** (Must be created)
4. **Did I introduce any new assumptions?** (Must be recorded)

If any answer is "I don't know," the change is not ready to commit.

---

## 8. Anti-Patterns to Avoid

### 8.1 The Documentation Graveyard
A `/docs` folder full of files nobody reads because they're disconnected from code. **Fix:** Proximity principle — docs live next to code.

### 8.2 The Aspirational Doc
Documentation that describes what the system *should* do, not what it *does*. **Fix:** Behavioral specs validated by tests.

### 8.3 The Duplicate Truth
The same information in docstrings, README, and API docs — all slightly different. **Fix:** Single source of truth, generated copies.

### 8.4 The Implicit Context
Docs that assume the reader knows things that aren't written down. **Fix:** FACT pattern — every statement is complete and self-contained.

### 8.5 The Stale ADR
Architecture decisions that were made for a codebase that no longer exists. **Fix:** Validation conditions in every ADR, periodic review.

---

## 9. Success Metrics

How do you know your documentation architecture is working?

| Metric | Target | Measurement |
|--------|--------|-------------|
| AI task success rate | >90% on first attempt | Track AI session outcomes |
| Doc freshness | <5% stale docs | CI staleness check |
| Context load time | <30s to understand a module | Measure AI onboarding reads |
| Repeated mistakes | Zero recurring issues | Track identical failures |
| Doc coverage | 100% of public APIs | Automated coverage check |
| Doc-test alignment | 100% behavioral specs have tests | CI validation |

---

## 10. Summary: The Documentation Stack

```
Layer 4: ONBOARDING          AI_CONTEXT.md, CLAUDE.md
         ↓ loads
Layer 3: ARCHITECTURE         ADRs, behavioral specs, module map
         ↓ constrains
Layer 2: MODULE DOCS          README.md, ASSUMPTIONS.md per module
         ↓ details
Layer 1: CODE DOCS            Docstrings, type hints, inline comments
         ↓ validated by
Layer 0: TESTS                Doc validation tests, assumption tests
```

Each layer serves a different purpose, lives at a different proximity to code, and updates at a different frequency. Together, they form a complete knowledge base that gives AI agents everything they need to maintain the system correctly.

**The fundamental insight:** In an AI-maintained system, documentation is not a nice-to-have. It is the system's memory. Treat it with the same rigor as code — tested, versioned, reviewed, and never allowed to rot.