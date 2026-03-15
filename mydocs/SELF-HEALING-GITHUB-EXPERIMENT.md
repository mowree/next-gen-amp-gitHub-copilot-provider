# Self-Healing Software Experiment on GitHub.com

> **Status**: Vision document — Pre-meticulous-attention phase
> **Date**: 2026-03-15
> **Context**: Exploring GitHub.com as the platform for autonomous self-healing software

---

## The Vision

Open source community files a bug → Autonomous orchestration begins → Self-healing software attempts fix → Human reviews → Merge or learn.

**Why GitHub.com?**
- Already has AI integration (Copilot coding agent)
- Already has automation (Actions)
- Already has community (Issues, PRs, Discussions)
- Already has security gates (branch protection, code scanning)
- **Precedent exists**: Dependabot does autonomous PRs, Copilot Autofix does security fixes

---

## What GitHub.com Has TODAY (March 2026)

### ✅ Available and Ready

| Capability | How It Works | Self-Healing Role |
|------------|--------------|-------------------|
| **Copilot Coding Agent** | Assign issue to `@copilot` → Agent creates PR | The "fix engine" |
| **Copilot Code Review** | Add Copilot as reviewer → AI reviews PR | Quality gate |
| **Copilot Autofix** | CodeQL finds vuln → Auto-generates fix | Security self-healing |
| **GitHub Actions** | Event triggers → Run workflows | Orchestration layer |
| **Issue Labels/Automation** | Label-based routing | Triage system |
| **Branch Protection** | Required reviews, status checks | Human review gate |
| **Custom Instructions** | `.github/copilot-instructions.md` | Guide agent behavior |

### 🔄 In Preview (Usable Now)

| Capability | Status | Self-Healing Role |
|------------|--------|-------------------|
| **Copilot Memory** | Public preview | Remembers repo patterns |
| **Custom Agents** | Public preview | Specialized fix agents |
| **Agent Hooks** | Available | Custom shell commands |
| **MCP Servers** | Available | Extend Copilot capabilities |

### ❌ Gaps Requiring Workarounds

| Gap | Impact | Workaround |
|-----|--------|------------|
| No direct Copilot API | Can't invoke Copilot from code | Use `gh issue edit --add-assignee @copilot` via Actions |
| Single-repo scope | Agent can't span repos | External orchestrator or multiple sessions |
| Workflow chain limit (3) | Complex pipelines break | Use `repository_dispatch` for external orchestration |
| No real-time streaming | Can't interact live | Poll status, use webhooks |

---

## Architecture: Self-Healing on GitHub.com

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         COMMUNITY / EXTERNAL                              │
│  Bug report │ Test failure │ Security alert │ Dependency update │ Monitor│
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼ issue created / alert triggered
┌──────────────────────────────────────────────────────────────────────────┐
│  TRIAGE WORKFLOW (GitHub Actions)                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  1. Classify: config change? code change? unknown?                  │  │
│  │  2. Apply labels: `self-heal/config`, `self-heal/code`, `human`     │  │
│  │  3. Route: Copilot-eligible? → assign @copilot                      │  │
│  │           Human-required? → notify maintainers                      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼ label: self-heal/*
┌──────────────────────────────────────────────────────────────────────────┐
│  COPILOT CODING AGENT                                                     │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  - Reads issue + repo context                                       │  │
│  │  - Follows .github/copilot-instructions.md                          │  │
│  │  - Creates fix on copilot/* branch                                  │  │
│  │  - Runs local validation (tests, lint)                              │  │
│  │  - Opens draft PR                                                   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼ PR opened
┌──────────────────────────────────────────────────────────────────────────┐
│  VALIDATION PIPELINE (GitHub Actions)                                     │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  - Full CI/CD test suite                                            │  │
│  │  - CodeQL security scan                                             │  │
│  │  - Copilot Code Review (as second reviewer)                         │  │
│  │  - Contract/spec compliance checks                                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                   ┌───────────────┴───────────────┐
                   │                               │
                   ▼ all checks pass               ▼ checks fail
┌──────────────────────────────────┐   ┌──────────────────────────────────┐
│  HUMAN REVIEW GATE               │   │  LEARNING LOOP                   │
│  ┌────────────────────────────┐  │   │  ┌────────────────────────────┐  │
│  │  - Maintainer reviews PR   │  │   │  │  - Log failure reason      │  │
│  │  - Approve or request      │  │   │  │  - Update issue with       │  │
│  │    changes                 │  │   │  │    learnings               │  │
│  │  - Merge when ready        │  │   │  │  - Escalate to human OR    │  │
│  └────────────────────────────┘  │   │  │    retry with adjustments  │  │
│                                  │   │  └────────────────────────────┘  │
│  For config: Auto-merge option   │   │                                  │
│  For code: Human approval req'd  │   │  Close issue with learnings     │
└──────────────────────────────────┘   └──────────────────────────────────┘
```

---

## Phased Experiment Plan

### Phase 1: Documentation Self-Healing (Lowest Risk)

**Goal**: Prove the pattern works with zero risk to code.

| What | How |
|------|-----|
| Trigger | Issue with label `docs-fix-request` |
| Action | Assign to Copilot |
| Scope | `.md` files only |
| Validation | Markdown lint, link checker |
| Merge | Auto-merge on pass |

**Why start here?**
- Worst case: bad docs get merged, easily reverted
- Community can participate immediately
- Builds trust in the system

### Phase 2: Config Self-Healing (Low Risk)

**Goal**: Your tier model — config = auto-fix.

| What | How |
|------|-----|
| Trigger | Issue with label `config-fix-request` or YAML validation failure |
| Action | Assign to Copilot |
| Scope | `*.yaml`, `*.json`, `*.toml` config files |
| Validation | Schema validation, config tests |
| Merge | Auto-merge on pass (with notification) |

**Matches your vision**: Config changes = autonomous, no human approval required.

### Phase 3: Test Self-Healing (Medium Risk)

**Goal**: Flaky test? Agent attempts fix.

| What | How |
|------|-----|
| Trigger | Test failure in CI → auto-issue created |
| Action | Assign to Copilot with test failure context |
| Scope | `tests/` directory |
| Validation | Full test suite must pass |
| Merge | Human review required (code change) |

### Phase 4: Code Self-Healing (Controlled)

**Goal**: The full vision — code changes with human gate.

| What | How |
|------|-----|
| Trigger | Bug report with reproduction steps |
| Action | Assign to Copilot |
| Scope | Full codebase |
| Validation | Tests + security scan + code review |
| Merge | Human approval required (like Linux kernel) |

---

## Open Source Community Integration

### How They Participate

1. **File Issues Normally**
   - Use issue templates that capture reproduction steps
   - Labels indicate self-heal eligibility

2. **Watch the Machine Work**
   - All agent activity visible in issue comments
   - PR shows AI-generated code
   - Actions logs show orchestration

3. **Review & Approve**
   - Community maintainers review Copilot PRs
   - Discussions on approach
   - Learning captured in issue threads

4. **Clone & Run Locally**
   - The autonomous machine (`.dev-machine/`) is in the repo
   - Anyone can fork and run locally
   - **Local mode**: Use local LLM + your own environment

### Making It Forkable

```
my-repo/
├── .github/
│   ├── copilot-instructions.md      # Guide Copilot behavior
│   ├── workflows/
│   │   ├── triage.yml               # Classify and route issues
│   │   ├── self-heal-docs.yml       # Phase 1 automation
│   │   ├── self-heal-config.yml     # Phase 2 automation
│   │   └── validation.yml           # Test/scan pipeline
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md            # Structured bug reports
│       └── self-heal-request.md     # Explicit self-heal trigger
├── .dev-machine/                    # Your autonomous machine
│   ├── build.yaml
│   ├── health-check.yaml
│   └── ...
├── specs/                           # What the code SHOULD do
├── contracts/                       # How modules behave
└── STATE.yaml                       # Machine state
```

**Community can:**
- Fork the whole pattern
- Adapt to their repo
- Run locally without GitHub Copilot (using `.dev-machine/` recipes with local LLM)

---

## Connecting to Your Provider Vision

This GitHub experiment **validates** your provider architecture:

| Your Architecture | GitHub.com Equivalent |
|-------------------|----------------------|
| Anti-corruption layer | `.github/copilot-instructions.md` + workflow isolation |
| Config-over-code | YAML-based action definitions, no code changes for routing |
| Contract tests | PR validation checks enforce spec compliance |
| Spec-driven development | Issue templates embed spec references |
| Tier model (config=auto, code=human) | Branch protection rules + auto-merge config |

**The provider becomes the "local version" of what GitHub.com does in the cloud.**

---

## Immediate Next Steps

### 1. Create Proof-of-Concept Workflow

```yaml
# .github/workflows/self-heal-triage.yml
name: Self-Heal Triage
on:
  issues:
    types: [opened, labeled]

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - name: Check labels
        id: check
        run: |
          # If issue has 'self-heal' label and no assignee
          # Add @copilot as assignee
          
      - name: Assign to Copilot
        if: steps.check.outputs.eligible == 'true'
        run: |
          gh issue edit ${{ github.event.issue.number }} \
            --add-assignee @copilot
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 2. Create Issue Template

```markdown
---
name: Self-Heal Request
about: Request autonomous fix attempt
labels: ["self-heal", "triage-needed"]
---

## What's broken?
<!-- Describe the issue -->

## Expected behavior
<!-- What should happen? -->

## Self-heal scope
- [ ] Documentation only
- [ ] Configuration only
- [ ] Test code
- [ ] Application code

## Acceptance criteria
<!-- How will we know it's fixed? -->
```

### 3. Write Copilot Instructions

```markdown
# .github/copilot-instructions.md

## Self-Healing Guidelines

When assigned to fix an issue:
1. Read the issue description carefully
2. Check the `specs/` folder for expected behavior
3. Check the `contracts/` folder for module boundaries
4. Make minimal changes to fix the specific issue
5. Add or update tests to prevent regression
6. Do NOT change code outside the scope indicated by labels
```

---

## Questions to Resolve

1. **Feedback loop**: How does the system learn from failed fix attempts?
2. **Escalation path**: When should it give up and ping humans?
3. **Metrics**: What defines "success" for self-healing?
4. **Security**: How to prevent malicious issue injection?
5. **Cost**: Copilot usage limits for high-volume repos?

---

## Verdict: You're Thinking in the Right Direction

**What GitHub.com has**:
- ✅ Issue-triggered automation
- ✅ Copilot coding agent (assigns via `@copilot`)
- ✅ PR validation pipeline
- ✅ Human review gates
- ✅ Community participation infrastructure

**What you'd need to add**:
- 🔧 Triage workflow (classify issues)
- 🔧 Learning loop (capture failures)
- 🔧 Copilot instructions (guide behavior)
- 🔧 Tier-based rules (config=auto, code=human)

**The gap is small.** 80% exists, 20% is workflow configuration.

This isn't "thinking over here and there" — this is a coherent vision that **GitHub.com already partially implements** through Dependabot, Copilot Autofix, and the coding agent. You're just proposing to formalize and extend the pattern.

---

## References

- [GitHub Copilot coding agent documentation](https://docs.github.com/en/copilot/using-github-copilot/using-the-copilot-coding-agent)
- [Copilot code review](https://docs.github.com/en/copilot/using-github-copilot/code-review/using-copilot-code-review)
- [GitHub Actions events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows)
- [Branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
