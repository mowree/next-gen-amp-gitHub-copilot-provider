# Public Repo Setup Guide

This document defines the file structure for the GitHub Copilot provider project and specifies which files belong in the PUBLIC repo vs which stay PRIVATE only.

---

## Current Project Structure (Root/Workspace)

```
next-get-provider-github-copilot/
│
├── amplifier_module_provider_github_copilot/   # Provider implementation (PUBLIC)
│   ├── __init__.py                              # Entry point with mount()
│   ├── provider.py                              # Core provider orchestrator
│   ├── error_translation.py                     # Error mapping
│   ├── streaming.py                             # Event translation
│   ├── tool_parsing.py                          # Tool extraction
│   └── sdk_adapter/                             # SDK integration layer
│       ├── __init__.py
│       ├── client.py                            # SDK wrapper
│       └── types.py                             # Type definitions
│
├── config/                                      # YAML policy configs (PUBLIC)
│   ├── __init__.py
│   ├── errors.yaml                              # Error mapping configuration
│   ├── events.yaml                              # Event vocabulary
│   └── retry.yaml                               # Retry policies
│
├── contracts/                                   # Markdown contracts (PUBLIC)
│   ├── behaviors.md
│   ├── deny-destroy.md
│   ├── error-hierarchy.md
│   ├── event-vocabulary.md
│   ├── provider-protocol.md
│   ├── sdk-boundary.md
│   └── streaming-contract.md
│
├── specs/                                       # Feature/module specs (PUBLIC)
│   ├── architecture.md
│   ├── features/                                # 42+ feature specs (F-001 to F-040+)
│   └── modules/                                 # Module specifications
│
├── tests/                                       # Test suite (PUBLIC)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_*.py                                # 40+ test files
│   └── sdk_helpers.py
│
├── docs/                                        # User documentation (PUBLIC)
│   └── plans/                                   # Implementation plans
│
├── .github/                                     # CI/CD workflows (PUBLIC)
│   └── workflows/
│
├── pyproject.toml                               # Build config (PUBLIC)
├── README.md                                    # Project overview (PUBLIC)
├── DEVELOPMENT.md                               # Dev setup guide (PUBLIC)
├── CHANGELOG.md                                 # Version history (PUBLIC)
├── .gitignore                                   # Git ignore rules (PUBLIC)
├── .dockerignore                                # Docker ignore rules (PUBLIC)
│
├── .dev-machine/                                # Autonomous dev machine (PRIVATE)
│   ├── build.yaml                               # Full machine loop
│   ├── iteration.yaml                           # Single iteration
│   ├── health-check.yaml                        # Build/test error detection
│   ├── fix-iteration.yaml                       # Single fix cycle
│   ├── cleanup.yaml
│   ├── commit-all.yaml
│   ├── shadow-test.yaml
│   ├── Dockerfile
│   ├── docker-run.sh
│   ├── docker-shadow-test.sh
│   ├── feature-spec-template.md
│   ├── working-session-instructions.md
│   └── shadow-results/
│
├── mydocs/                                      # Internal documentation (PRIVATE)
│   ├── debates/                                 # Architecture discussions
│   │   ├── GOLDEN_VISION_V2.md                  # The "constitution"
│   │   ├── final-round/
│   │   ├── research/
│   │   ├── round2/
│   │   ├── round3/
│   │   ├── wave1/
│   │   ├── wave2/
│   │   └── wave3/
│   ├── aha/                                     # Insights and discoveries
│   ├── plan/                                    # Planning documents
│   ├── DEV_MACHINE_EXPLAINED.md
│   ├── GIT_CHECKIN_GUIDE.md
│   ├── shadow-testing-approach.md
│   └── public-repo-setup.md                     # This file
│
├── reference-only/                              # Reference materials (PRIVATE)
│   ├── amplifier-bundle-dev-machine/
│   ├── copilot-sdk/
│   └── [other reference materials]
│
├── .dev-machine-assessment.md                   # Machine assessment (PRIVATE)
├── .dev-machine-design.md                       # Machine design (PRIVATE)
├── STATE.yaml                                   # Machine state (PRIVATE)
├── CONTEXT-TRANSFER.md                          # Session handoffs (PRIVATE)
├── SCRATCH.md                                   # Working notes (PRIVATE)
├── FEATURE-ARCHIVE.yaml                         # Completed features (PRIVATE)
├── GIT-STATUS-NOW.txt                           # Git snapshots (PRIVATE)
├── AGENTS.md                                    # Agent documentation (PRIVATE)
├── bundle.md                                    # Bundle config (PRIVATE)
├── run_tests.sh                                 # Test script (PRIVATE)
├── run_shadow_test.sh                           # Shadow test script (PRIVATE)
├── shadow_test_output.log                       # Test logs (PRIVATE)
└── uv.lock                                      # Dependency lock (PRIVATE)
```

---

## Section 1: PUBLIC Repo Contents

These files/folders should be included in the public GitHub repository:

### Core Provider Code
```
amplifier_module_provider_github_copilot/
├── __init__.py
├── provider.py
├── error_translation.py
├── streaming.py
├── tool_parsing.py
└── sdk_adapter/
    ├── __init__.py
    ├── client.py
    └── types.py
```

### Configuration
```
config/
├── __init__.py
├── errors.yaml
├── events.yaml
└── retry.yaml
```

### Contracts & Specifications
```
contracts/
└── [all .md files]

specs/
├── architecture.md
├── features/
└── modules/
```

### Tests
```
tests/
└── [all test files]
```

### Documentation
```
docs/
└── plans/

README.md
DEVELOPMENT.md
CHANGELOG.md
```

### Build & CI
```
.github/
└── workflows/

pyproject.toml
.gitignore
.dockerignore
```

---

## Section 2: PRIVATE Repo Contents

These files/folders should remain in the private repo only:

### Autonomous Development Machine
```
.dev-machine/                    # Full dev machine infrastructure
├── build.yaml
├── iteration.yaml
├── health-check.yaml
├── fix-iteration.yaml
├── cleanup.yaml
├── commit-all.yaml
├── shadow-test.yaml
├── Dockerfile
├── docker-run.sh
├── docker-shadow-test.sh
├── feature-spec-template.md
├── working-session-instructions.md
└── shadow-results/
```

### Internal Documentation
```
mydocs/                          # All internal notes and research
├── debates/                     # Architecture discussions
│   └── GOLDEN_VISION_V2.md     # The "constitution" - 43 documents synthesized
├── aha/
├── plan/
├── DEV_MACHINE_EXPLAINED.md
├── GIT_CHECKIN_GUIDE.md
├── shadow-testing-approach.md
└── public-repo-setup.md
```

### Reference Materials
```
reference-only/                  # SDK and provider references
├── amplifier-bundle-dev-machine/
├── copilot-sdk/
└── [other references]
```

### Machine State Files
```
STATE.yaml                       # Machine-readable project state
CONTEXT-TRANSFER.md              # Session summaries and decisions
SCRATCH.md                       # Ephemeral working notes
FEATURE-ARCHIVE.yaml             # Completed features archive
GIT-STATUS-NOW.txt               # Git status snapshots
.dev-machine-assessment.md       # Admissions assessment
.dev-machine-design.md           # Machine design document
```

### Bundle & Agent Config
```
AGENTS.md                        # Agent documentation
bundle.md                        # Bundle configuration
```

### Scripts & Logs
```
run_tests.sh                     # Test runner script
run_shadow_test.sh               # Shadow test runner
shadow_test_output.log           # Test output logs
uv.lock                          # Dependency lock file
```

---

## Creating the Public Repo

When ready to publish:

### Option 1: Manual Copy
```bash
# Create a new directory for public repo
mkdir ../provider-github-copilot-public
cd ../provider-github-copilot-public
git init

# Copy PUBLIC files
cp -r ../next-get-provider-github-copilot/amplifier_module_provider_github_copilot .
cp -r ../next-get-provider-github-copilot/config .
cp -r ../next-get-provider-github-copilot/contracts .
cp -r ../next-get-provider-github-copilot/specs .
cp -r ../next-get-provider-github-copilot/tests .
cp -r ../next-get-provider-github-copilot/docs .
cp -r ../next-get-provider-github-copilot/.github .
cp ../next-get-provider-github-copilot/pyproject.toml .
cp ../next-get-provider-github-copilot/README.md .
cp ../next-get-provider-github-copilot/DEVELOPMENT.md .
cp ../next-get-provider-github-copilot/CHANGELOG.md .
cp ../next-get-provider-github-copilot/.gitignore .
cp ../next-get-provider-github-copilot/.dockerignore .

# Initial commit
git add -A
git commit -m "Initial public release"
```

### Option 2: Git Filter (Advanced)
```bash
# Use git-filter-repo to create a clean history
# This preserves commit history but removes private files
pip install git-filter-repo
git filter-repo --path amplifier_module_provider_github_copilot \
                --path config \
                --path contracts \
                --path specs \
                --path tests \
                --path docs \
                --path .github \
                --path pyproject.toml \
                --path README.md \
                --path DEVELOPMENT.md \
                --path CHANGELOG.md \
                --path .gitignore \
                --path .dockerignore
```

---

## Sync Strategy

**Private Repo (this one):** Source of truth, contains everything
**Public Repo:** Subset, synced periodically

When making changes:
1. Make all changes in the PRIVATE repo
2. Run tests and verify
3. Copy PUBLIC files to the public repo
4. Commit and push to both repos

---

## .gitignore for Public Repo

Create this `.gitignore` in the public repo:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg
*.egg-info/
dist/
build/
.eggs/
*.whl

# Virtual environments
.venv/
venv/
env/

# Testing & coverage
.pytest_cache/
.coverage
htmlcov/
.tox/

# Type checking & linting
.mypy_cache/
.ruff_cache/
.pyright/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# uv lock (regenerated on install)
uv.lock
```

---

## Verification Checklist

Before pushing to public repo:

- [ ] No private paths referenced (mydocs/, debates/, reference-only/)
- [ ] No STATE.yaml, CONTEXT-TRANSFER.md, SCRATCH.md
- [ ] No .dev-machine/ directory
- [ ] No bundle.md or AGENTS.md
- [ ] No shadow test artifacts
- [ ] All tests pass
- [ ] README.md has proper setup instructions
- [ ] CHANGELOG.md is up to date
- [ ] pyproject.toml has correct package paths

---

*Last updated: 2026-03-13*
*Maintained in: mydocs/public-repo-setup.md*
