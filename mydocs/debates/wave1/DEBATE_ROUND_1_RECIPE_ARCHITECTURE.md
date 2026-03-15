# Recipe Architecture: Autonomous GitHub Copilot Provider Development

**Wave 1, Agent 7 — Recipe & Workflow Expert**
**Date:** 2026-03-08

---

## 1. Executive Summary

Building a GitHub Copilot provider for the Amplifier SDK is a multi-phase engineering effort that benefits enormously from recipe-driven orchestration. Recipes give us **reproducibility** (every run follows the same disciplined flow), **observability** (each step's output is captured and inspectable), and **human-in-the-loop control** (approval gates at critical junctures). This document defines the complete recipe architecture: the core recipes needed, how they compose, where approval gates belong, how context accumulates, how errors are handled, and how convergence loops drive iterative quality improvement.

The architecture is built around five core recipes that compose into a master orchestration recipe. Each recipe is self-contained and independently testable, following the DRY principle through recipe composition (`type: "recipe"`). The design prioritizes **test-driven development**, **SDK contract fidelity**, and **safe iteration** — meaning the system can autonomously loop on test failures but must pause for human review before publishing or making architectural decisions.

---

## 2. Core Recipes Needed

### 2.1 Provider Implementation Recipe (TDD Flow)

This is the heart of the system. It follows a strict red-green-refactor cycle, driven by the SDK's provider interface contract.

**Purpose:** Implement the GitHub Copilot provider from interface contract to passing tests.

**Key Design Decisions:**
- Tests are written FIRST, derived from the SDK's provider interface
- Implementation is driven by test failures
- A convergence loop runs until all tests pass or a maximum iteration count is hit
- Refactoring happens only after green tests

```yaml
name: "copilot-provider-tdd"
description: "TDD implementation of GitHub Copilot provider against SDK interface"
version: "1.0.0"
tags: ["tdd", "implementation", "copilot-provider"]

context:
  sdk_interface_path: ""      # Path to SDK provider interface definition
  provider_output_dir: ""     # Where to write the provider source
  test_output_dir: ""         # Where to write test files
  max_tdd_iterations: "10"    # Safety cap on red-green loops

steps:
  - id: "analyze-sdk-interface"
    agent: "foundation:zen-architect"
    mode: "ANALYZE"
    prompt: |
      Analyze the SDK provider interface at {{sdk_interface_path}}.
      Extract every method signature, type constraint, required behavior,
      lifecycle hook, and error contract. Produce a structured catalog of
      everything the provider must implement.
    output: "interface_catalog"
    timeout: 300

  - id: "generate-test-suite"
    agent: "foundation:test-coverage"
    prompt: |
      Using this interface catalog:
      {{interface_catalog}}

      Generate a comprehensive test suite for a GitHub Copilot provider.
      Cover: construction, configuration, authentication flow, chat completion
      (streaming and non-streaming), model listing, error handling, edge cases.
      Write tests to {{test_output_dir}}. All tests MUST fail initially (red phase).
    output: "test_suite_report"
    timeout: 600

  - id: "scaffold-provider"
    agent: "foundation:zen-architect"
    mode: "ARCHITECT"
    prompt: |
      Based on the interface catalog:
      {{interface_catalog}}

      Generate the initial provider scaffold at {{provider_output_dir}}.
      Implement method stubs that throw "not implemented" errors.
      Ensure the scaffold compiles but all tests fail.
    output: "scaffold_report"
    timeout: 300

  - id: "implement-provider"
    agent: "copilot-provider-implementer"
    prompt: |
      Implement the GitHub Copilot provider to pass all tests.

      Interface catalog: {{interface_catalog}}
      Test suite: {{test_suite_report}}
      Current scaffold: {{scaffold_report}}

      Work method by method. Run tests after each method implementation.
      Focus on correctness first, then clean code.
    output: "implementation_report"
    timeout: 1800
    on_error: continue

  - id: "convergence-test-loop"
    type: "recipe"
    recipe: "tdd-convergence-loop.yaml"
    context:
      test_dir: "{{test_output_dir}}"
      source_dir: "{{provider_output_dir}}"
      max_iterations: "{{max_tdd_iterations}}"
      implementation_context: "{{implementation_report}}"
    output: "convergence_result"

  - id: "refactor-pass"
    agent: "foundation:zen-architect"
    mode: "REVIEW"
    prompt: |
      All tests are passing. Now refactor for quality:
      {{convergence_result}}

      Apply: extract methods, reduce duplication, improve naming,
      add JSDoc/docstrings, ensure consistent error handling patterns.
      DO NOT change behavior — tests must still pass after refactoring.
    output: "refactor_report"
    timeout: 600
    condition: "convergence_result.success == true"
```

### 2.2 SDK Assumption Validation Recipe

**Purpose:** Validate that our assumptions about the SDK's behavior match reality. This catches "interface says X but runtime does Y" problems early.

```yaml
name: "sdk-assumption-validator"
description: "Validate assumptions about SDK behavior against actual runtime"
version: "1.0.0"
tags: ["sdk", "validation", "assumptions"]

context:
  sdk_package: ""             # SDK package name/path
  assumptions_doc: ""         # Path to documented assumptions
  provider_source: ""         # Current provider implementation

steps:
  - id: "extract-assumptions"
    agent: "foundation:zen-architect"
    mode: "ANALYZE"
    prompt: |
      Analyze the provider source at {{provider_source}} and any
      documented assumptions at {{assumptions_doc}}.

      Extract every implicit and explicit assumption about:
      - SDK method signatures and return types
      - Lifecycle ordering (init before use, cleanup after)
      - Error propagation behavior
      - Configuration merging/override semantics
      - Streaming protocol details
      - Authentication flow expectations

      Produce a numbered list of testable assumptions.
    output: "assumption_list"
    timeout: 300

  - id: "generate-validation-tests"
    agent: "foundation:test-coverage"
    prompt: |
      For each assumption in:
      {{assumption_list}}

      Generate a focused validation test that exercises the SDK directly
      (not through our provider) to confirm or deny the assumption.
      Each test should be independent and produce a clear PASS/FAIL.
    output: "validation_tests"
    timeout: 600

  - id: "run-validations"
    agent: "foundation:integration-specialist"
    prompt: |
      Execute the assumption validation tests:
      {{validation_tests}}

      Report: which assumptions hold, which are violated, and the
      actual behavior observed for each violation.
    output: "validation_results"
    timeout: 900

  - id: "impact-analysis"
    agent: "foundation:zen-architect"
    mode: "ANALYZE"
    prompt: |
      Given these validation results:
      {{validation_results}}

      For each violated assumption, analyze:
      1. What code in our provider depends on this assumption?
      2. What is the severity (crash, wrong behavior, cosmetic)?
      3. What is the recommended fix?
      
      Prioritize by severity. Produce actionable fix plan.
    output: "impact_report"
    timeout: 300
```

### 2.3 Integration Test Recipe

**Purpose:** End-to-end testing against GitHub Copilot's actual API (or a realistic mock). This validates the provider works in the real Amplifier runtime.

```yaml
name: "integration-test-suite"
description: "End-to-end integration testing of Copilot provider"
version: "1.0.0"
tags: ["integration", "e2e", "testing"]

context:
  provider_path: ""
  copilot_token: ""           # GitHub Copilot auth token (secret)
  test_scenarios_path: ""
  mock_mode: "true"           # Use mock API by default for safety

stages:
  - name: "setup-and-smoke"
    steps:
      - id: "setup-test-env"
        agent: "foundation:integration-specialist"
        prompt: |
          Set up integration test environment for {{provider_path}}.
          Mock mode: {{mock_mode}}.
          Install dependencies, configure test fixtures, verify environment.
        output: "env_setup"
        timeout: 300

      - id: "smoke-test"
        agent: "foundation:integration-specialist"
        prompt: |
          Run smoke tests: provider loads, authenticates, lists models,
          completes a simple chat request. Environment: {{env_setup}}
        output: "smoke_results"
        timeout: 300

    approval:
      message: |
        Smoke test results:
        {{smoke_results}}
        
        Approve to proceed to full integration suite.

  - name: "full-integration"
    steps:
      - id: "streaming-tests"
        agent: "foundation:integration-specialist"
        prompt: |
          Test streaming chat completions: token-by-token delivery,
          cancellation mid-stream, error during stream, empty stream.
          Provider: {{provider_path}}
        output: "streaming_results"
        timeout: 600

      - id: "error-handling-tests"
        agent: "foundation:integration-specialist"
        prompt: |
          Test error scenarios: invalid token, rate limiting, network timeout,
          malformed response, server 500. Verify graceful degradation.
        output: "error_results"
        timeout: 600

      - id: "concurrency-tests"
        agent: "foundation:integration-specialist"
        prompt: |
          Test concurrent usage: multiple simultaneous requests,
          request queuing, resource cleanup under load.
        output: "concurrency_results"
        timeout: 600

      - id: "integration-report"
        agent: "foundation:zen-architect"
        mode: "ANALYZE"
        prompt: |
          Synthesize integration test results:
          Streaming: {{streaming_results}}
          Errors: {{error_results}}
          Concurrency: {{concurrency_results}}
          
          Produce a pass/fail report with severity classification.
        output: "integration_report"

    approval:
      message: |
        Full integration results:
        {{integration_report}}
        
        Approve to proceed to release validation.
```

### 2.4 Release Validation Recipe

**Purpose:** Final quality gate before publishing. Checks everything: tests, types, lint, docs, security, package integrity.

```yaml
name: "release-validation"
description: "Pre-release validation checklist"
version: "1.0.0"
tags: ["release", "validation", "quality"]

context:
  package_path: ""
  target_version: ""

stages:
  - name: "automated-checks"
    steps:
      - id: "type-check"
        agent: "foundation:integration-specialist"
        prompt: "Run type checker on {{package_path}}. Report all errors."
        output: "type_results"
        timeout: 300

      - id: "lint-check"
        agent: "foundation:integration-specialist"
        prompt: "Run linter on {{package_path}}. Report violations."
        output: "lint_results"
        timeout: 300

      - id: "test-check"
        agent: "foundation:integration-specialist"
        prompt: "Run full test suite for {{package_path}}. Report results."
        output: "test_results"
        timeout: 600

      - id: "security-scan"
        agent: "foundation:security-guardian"
        prompt: |
          Security audit of {{package_path}}:
          - Dependency vulnerabilities
          - Credential handling (no hardcoded secrets)
          - Input validation
          - Token/auth safety
        output: "security_results"
        timeout: 600

      - id: "package-integrity"
        agent: "foundation:integration-specialist"
        prompt: |
          Validate package.json/pyproject.toml at {{package_path}}:
          - Version matches {{target_version}}
          - All dependencies pinned appropriately
          - Entry points correct
          - README present and accurate
          - License present
        output: "package_results"
        timeout: 300

  - name: "human-review"
    approval:
      message: |
        ## Release Validation Report for v{{target_version}}
        
        | Check | Result |
        |-------|--------|
        | Types | {{type_results}} |
        | Lint | {{lint_results}} |
        | Tests | {{test_results}} |
        | Security | {{security_results}} |
        | Package | {{package_results}} |
        
        Approve to publish, or deny with feedback.
```

### 2.5 SDK Upgrade Detection and Adaptation Recipe

**Purpose:** Detect when the upstream SDK changes, analyze the delta, and adapt the provider.

```yaml
name: "sdk-upgrade-adaptation"
description: "Detect SDK changes and adapt provider implementation"
version: "1.0.0"
tags: ["sdk", "upgrade", "adaptation"]

context:
  sdk_package: ""
  current_sdk_version: ""
  provider_path: ""

steps:
  - id: "check-sdk-updates"
    agent: "foundation:integration-specialist"
    prompt: |
      Check for new versions of {{sdk_package}} beyond {{current_sdk_version}}.
      If no update available, output {"update_available": false}.
      If available, output the new version and changelog.
    output: "update_check"
    parse_json: true
    timeout: 120

  - id: "diff-analysis"
    agent: "foundation:zen-architect"
    mode: "ANALYZE"
    condition: "update_check.update_available == true"
    prompt: |
      Analyze the SDK diff between {{current_sdk_version}} and the new version.
      Update info: {{update_check}}
      
      Classify changes as:
      - BREAKING: Signature changes, removed methods, type changes
      - ADDITIVE: New methods, new optional parameters
      - INTERNAL: Bug fixes, performance improvements (no API change)
      
      For each BREAKING change, map to affected code in {{provider_path}}.
    output: "diff_report"
    timeout: 600

  - id: "adaptation-plan"
    agent: "foundation:zen-architect"
    mode: "ARCHITECT"
    condition: "update_check.update_available == true"
    prompt: |
      Based on the diff report:
      {{diff_report}}

      Create a step-by-step adaptation plan. For each breaking change:
      1. What code must change?
      2. What tests must be updated?
      3. Are new tests needed?
      4. Risk assessment (low/medium/high)
    output: "adaptation_plan"
    timeout: 300

  - id: "apply-adaptations"
    type: "recipe"
    recipe: "copilot-provider-tdd.yaml"
    condition: "update_check.update_available == true"
    context:
      sdk_interface_path: "{{sdk_package}}"
      provider_output_dir: "{{provider_path}}"
      test_output_dir: "{{provider_path}}/tests"
      max_tdd_iterations: "5"
    output: "adaptation_result"
```

---

## 3. Approval Gates: Human Checkpoints vs Full Autonomy

The principle is: **automate the mechanical, gate the consequential.**

| Activity | Autonomy Level | Rationale |
|----------|---------------|-----------|
| Test generation | **Full autonomy** | Low risk — tests don't ship to users |
| Implementation iteration (red→green) | **Full autonomy** | Bounded by convergence loop caps |
| Refactoring | **Full autonomy** | Tests guard against regression |
| SDK assumption extraction | **Full autonomy** | Analysis only, no mutations |
| Assumption validation execution | **Full autonomy** | Read-only against SDK |
| Integration smoke tests | **Approval gate** | Catches environment issues early |
| Full integration suite | **Approval gate** | May hit real APIs, costs money |
| Release publish | **Approval gate** | Irreversible — must be human-approved |
| SDK breaking change adaptation | **Approval gate** | Architectural decisions may be needed |
| Security scan results | **Approval gate** | Security findings need human judgment |

**Design pattern used:** Staged recipes (`stages:` with `approval:` blocks) for gated workflows. Flat recipes (`steps:`) for fully autonomous workflows.

---

## 4. Recipe Composition

The recipes compose hierarchically through a master orchestration recipe:

```yaml
name: "copilot-provider-master"
description: "Full lifecycle orchestration for GitHub Copilot provider"
version: "1.0.0"

recursion:
  max_depth: 3
  max_total_steps: 200

context:
  sdk_package: "@anthropic/amplifier-sdk"
  sdk_interface_path: "node_modules/@anthropic/amplifier-sdk/types/provider.d.ts"
  provider_output_dir: "src/providers/copilot"
  test_output_dir: "tests/providers/copilot"
  target_version: "0.1.0"

stages:
  - name: "validate-sdk"
    steps:
      - id: "sdk-validation"
        type: "recipe"
        recipe: "sdk-assumption-validator.yaml"
        context:
          sdk_package: "{{sdk_package}}"
          assumptions_doc: "docs/sdk-assumptions.md"
          provider_source: "{{provider_output_dir}}"
        output: "sdk_validation"
    approval:
      message: "SDK assumptions validated: {{sdk_validation}}. Proceed to implementation?"

  - name: "implement"
    steps:
      - id: "tdd-implementation"
        type: "recipe"
        recipe: "copilot-provider-tdd.yaml"
        context:
          sdk_interface_path: "{{sdk_interface_path}}"
          provider_output_dir: "{{provider_output_dir}}"
          test_output_dir: "{{test_output_dir}}"
          max_tdd_iterations: "10"
        output: "implementation"
    approval:
      message: "Implementation complete: {{implementation}}. Proceed to integration tests?"

  - name: "integrate"
    steps:
      - id: "integration-testing"
        type: "recipe"
        recipe: "integration-test-suite.yaml"
        context:
          provider_path: "{{provider_output_dir}}"
          mock_mode: "true"
        output: "integration"
    approval:
      message: "Integration tests complete: {{integration}}. Proceed to release validation?"

  - name: "release"
    steps:
      - id: "release-checks"
        type: "recipe"
        recipe: "release-validation.yaml"
        context:
          package_path: "."
          target_version: "{{target_version}}"
        output: "release_validation"
    approval:
      message: "Release validation: {{release_validation}}. Approve v{{target_version}} for publish?"
```

**Composition principles:**

1. **Context isolation:** Each sub-recipe receives only the context it needs. The TDD recipe doesn't see the release version. The integration recipe doesn't see the SDK assumptions doc.

2. **Output aggregation:** Each sub-recipe's output feeds into the approval gate message, giving the human reviewer a complete picture.

3. **Independent testability:** Every sub-recipe can be executed standalone. You can run `sdk-assumption-validator.yaml` without running the full master recipe.

4. **Fail-fast with gates:** If SDK validation reveals critical issues, the human can deny the gate and redirect work before expensive implementation begins.

---

## 5. Context Accumulation

Context flows through three mechanisms:

### 5.1 Step-to-Step Output Variables
Each step's `output` field captures its result and makes it available as `{{variable_name}}` to subsequent steps. This is the primary flow mechanism.

```
analyze-sdk-interface → {{interface_catalog}}
    ↓
generate-test-suite → {{test_suite_report}}
    ↓
scaffold-provider → {{scaffold_report}}
    ↓
implement-provider → {{implementation_report}}
```

### 5.2 Cross-Recipe Context Passing
When recipes compose, context is explicitly passed. The parent recipe maps its variables into the child's namespace:

```yaml
- id: "tdd-implementation"
  type: "recipe"
  recipe: "copilot-provider-tdd.yaml"
  context:
    sdk_interface_path: "{{sdk_interface_path}}"  # parent → child mapping
```

### 5.3 Accumulated Context in Convergence Loops
Inside convergence loops, context accumulates across iterations. Each iteration appends to a running context that includes:
- Previous test failure details
- Previous fix attempts
- Narrowing scope of remaining failures

This prevents the loop from retrying the same failed approach.

---

## 6. Error Handling Strategy

### 6.1 Step-Level Error Handling

| Step Type | `on_error` | Rationale |
|-----------|------------|-----------|
| Analysis steps | `fail` | Bad analysis poisons all downstream work |
| Test generation | `fail` | Can't do TDD without tests |
| Implementation | `continue` | Partial progress is useful; convergence loop can fix gaps |
| Integration tests | `continue` | Capture partial results, some tests may pass |
| Security scan | `continue` | Don't block release review on scanner issues |
| Refactoring | `continue` | Original code still works if refactor fails |

### 6.2 Recovery Strategies

**Strategy 1: Convergence Loop Recovery**
When the TDD implementation step fails, the convergence loop picks up where it left off. The loop's accumulated context includes the failure, so the next iteration can try a different approach.

**Strategy 2: Approval Gate Redirection**
When a gated step fails, the human can:
- **Retry:** Re-run the stage with modified context
- **Skip:** Mark as acceptable and continue
- **Redirect:** Deny the gate with instructions, causing the recipe to halt for correction

**Strategy 3: Fallback Recipes**
For non-critical steps, configure a fallback:

```yaml
- id: "security-scan"
  agent: "foundation:security-guardian"
  prompt: "..."
  on_error: continue
  # If security-guardian fails, the step outputs an error marker
  # The release gate shows this to the human for manual security review
```

### 6.3 Circuit Breaker Pattern
Convergence loops include a maximum iteration cap. If hit, the loop exits with a failure report rather than looping forever. The failure report includes all attempts and their results, giving the human reviewer maximum context.

---

## 7. Convergence Loops

### 7.1 TDD Convergence Loop

This is the most critical loop — it drives the red→green cycle:

```yaml
name: "tdd-convergence-loop"
description: "Iterative test-fix loop until all tests pass"
version: "1.0.0"
tags: ["tdd", "convergence"]

context:
  test_dir: ""
  source_dir: ""
  max_iterations: "10"
  implementation_context: ""

steps:
  - id: "run-tests"
    agent: "foundation:integration-specialist"
    prompt: |
      Run the test suite at {{test_dir}} against source at {{source_dir}}.
      Output structured results: total, passed, failed, error details.
    output: "test_run"
    parse_json: true
    timeout: 300

  - id: "check-convergence"
    agent: "foundation:zen-architect"
    mode: "ANALYZE"
    prompt: |
      Test results: {{test_run}}
      Iteration context: {{implementation_context}}
      Max iterations: {{max_iterations}}

      If all tests pass, output: {"converged": true, "success": true}
      If max iterations reached, output: {"converged": true, "success": false, "remaining_failures": [...]}
      Otherwise, output: {"converged": false, "failures_to_fix": [...], "strategy": "..."}
    output: "convergence_check"
    parse_json: true

  - id: "fix-failures"
    condition: "convergence_check.converged == false"
    agent: "copilot-provider-implementer"
    prompt: |
      Fix these test failures:
      {{convergence_check.failures_to_fix}}

      Strategy: {{convergence_check.strategy}}
      
      Previous context (avoid repeating failed approaches):
      {{implementation_context}}

      Make minimal, targeted fixes. Run tests after each fix.
    output: "fix_report"
    timeout: 900

  # Loop back: the orchestrator re-executes this recipe
  # with updated implementation_context including fix_report
```

**Loop mechanics:** The parent recipe invokes this as a sub-recipe. On non-convergence, the parent re-invokes with accumulated context. The `max_iterations` field in context acts as the decrementing counter. Each iteration appends its fix_report to the accumulating implementation_context, preventing repeated failed approaches.

### 7.2 Code Quality Convergence Loop

For post-implementation quality improvement:

```yaml
name: "quality-convergence-loop"
description: "Iterative quality improvement until standards met"
version: "1.0.0"

context:
  source_dir: ""
  quality_threshold: "B"    # Minimum grade: A, B, C
  max_iterations: "5"

steps:
  - id: "quality-scan"
    agent: "foundation:zen-architect"
    mode: "REVIEW"
    prompt: |
      Review code quality at {{source_dir}}.
      Grade on: complexity, duplication, naming, error handling, documentation.
      Output grade (A-F) and specific issues to fix.
    output: "quality_report"
    timeout: 300

  - id: "check-threshold"
    agent: "foundation:zen-architect"
    mode: "ANALYZE"
    prompt: |
      Quality report: {{quality_report}}
      Threshold: {{quality_threshold}}
      
      Does the code meet the threshold?
      Output: {"meets_threshold": true/false, "current_grade": "...", "top_issues": [...]}
    output: "threshold_check"
    parse_json: true

  - id: "improve-quality"
    condition: "threshold_check.meets_threshold == false"
    agent: "foundation:zen-architect"
    mode: "ARCHITECT"
    prompt: |
      Improve code quality at {{source_dir}}.
      Focus on top issues: {{threshold_check.top_issues}}
      
      Make targeted improvements. Run tests after changes to ensure no regressions.
    output: "improvement_report"
    timeout: 600
```

---

## 8. Model Selection Strategy

Different steps have different complexity profiles. Match models to task difficulty:

| Task | Recommended Model | Rationale |
|------|------------------|-----------|
| SDK interface analysis | `claude-opus-*` | Deep architectural reasoning |
| Test generation | `claude-sonnet-*` | Solid code generation |
| Implementation | `claude-sonnet-*` | Core coding task |
| Convergence check | `claude-haiku-*` | Simple classification |
| Security audit | `claude-opus-*` | Requires deep security reasoning |
| Package validation | `claude-haiku-*` | Mechanical checklist |
| Diff analysis | `claude-sonnet-*` | Code understanding |

Example step with model selection:

```yaml
- id: "check-convergence"
  agent: "foundation:zen-architect"
  provider: "anthropic"
  model: "claude-haiku-*"     # Fast model for simple classification
  prompt: "..."
```

---

## 9. Recipe File Layout

```
recipes/
├── copilot-provider-master.yaml          # Master orchestration (staged)
├── copilot-provider-tdd.yaml             # TDD implementation flow
├── sdk-assumption-validator.yaml         # SDK assumption checking
├── integration-test-suite.yaml           # Integration testing (staged)
├── release-validation.yaml               # Release quality gate (staged)
├── sdk-upgrade-adaptation.yaml           # SDK change detection
├── loops/
│   ├── tdd-convergence-loop.yaml         # Red-green convergence
│   └── quality-convergence-loop.yaml     # Quality improvement
└── README.md                             # Recipe catalog documentation
```

---

## 10. Key Design Principles

1. **Tests before code, always.** The TDD recipe enforces this structurally — test generation is a prerequisite step for implementation.

2. **Bounded iteration.** Every convergence loop has a `max_iterations` cap. Unbounded loops are a recipe for runaway costs and no progress.

3. **Context isolation prevents contamination.** Sub-recipes only see what they're explicitly given. A security scan can't accidentally modify implementation context.

4. **Human gates at irreversible boundaries.** Autonomy is maximized within each stage, but stage transitions require human approval when the action has external consequences (API calls, publishing, architectural decisions).

5. **Accumulated failure context prevents loops.** Each convergence iteration carries forward its failure history, preventing the agent from retrying identical failed approaches.

6. **Independent testability.** Every recipe is executable standalone. You don't need to run the master recipe to validate that the TDD loop works correctly.

7. **Model-task matching.** Use powerful models for reasoning-heavy steps, fast models for mechanical checks. This controls cost without sacrificing quality where it matters.

---

## 11. Open Questions for Debate

1. **Should the TDD convergence loop be a native recipe primitive (while/until) or a recursive sub-recipe call?** The current design uses composition, which is supported today but adds invocation overhead.

2. **How do we handle flaky integration tests?** The current design uses approval gates, but could add automatic retry with jitter for network-related failures.

3. **Should SDK upgrade detection run on a schedule or be triggered manually?** A scheduled recipe (cron-like) would catch upgrades proactively, but the recipe system may not support scheduling natively.

4. **What's the right `max_iterations` for TDD convergence?** Too low and we abandon viable implementations. Too high and we waste cycles on fundamentally wrong approaches. 10 is a starting heuristic.

5. **Should the security scan block release or just inform it?** Current design makes it an approval gate input rather than a hard blocker, giving humans flexibility. Is this the right tradeoff?
