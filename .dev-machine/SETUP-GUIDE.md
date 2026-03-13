# Dev-Machine Setup Guide

> **Purpose**: This document captures everything needed to set up and run the autonomous development machine. It includes lessons learned from the initial setup, known pitfalls, and verification steps.

## Quick Start

```bash
cd /path/to/your/project
./.dev-machine/docker-run.sh --build   # First time: builds container
./.dev-machine/docker-run.sh           # Subsequent: reuses container
```

## Prerequisites

### 1. Environment Requirements

| Requirement | Why |
|-------------|-----|
| Docker | Container isolation for autonomous execution |
| GITHUB_TOKEN | Authentication for git push inside container |
| Node.js 18+ | GitHub Copilot SDK CLI dependency |
| Python 3.11+ | Amplifier runtime |

### 2. Pre-Flight Checklist

Before first run, verify:

```bash
# 1. Docker is running
docker info >/dev/null 2>&1 && echo "✓ Docker OK" || echo "✗ Docker not running"

# 2. GITHUB_TOKEN is set
[ -n "$GITHUB_TOKEN" ] && echo "✓ GITHUB_TOKEN set" || echo "✗ GITHUB_TOKEN missing"

# 3. Git identity configured
git config user.email && echo "✓ Git identity OK" || echo "✗ Git identity missing"

# 4. Project dependencies work
uv run ruff check src/ && uv run pyright src/ && echo "✓ Build OK" || echo "✗ Build failed"
```

---

## What is a Recipe?

A **recipe** is a multi-step YAML workflow that orchestrates agents and bash steps to accomplish repeatable tasks. Recipes are Amplifier's way to encode:
- Sequential execution with state persistence
- Agent delegation with context accumulation
- Checkpointing for resumability
- Approval gates for human-in-loop workflows

In this dev-machine:
- `build.yaml` = outer loop orchestrating the entire machine
- `iteration.yaml` = inner loop for one work iteration
- `health-check.yaml` = diagnostic loop for failures

Each recipe is self-contained, resumable, and can reference other recipes as sub-recipes.

---

## Known Pitfalls (MUST READ)

### Pitfall 1: Missing Python Dependencies in Container

**Symptom**:
```
Failed to load module 'tool-mcp': No module named 'mcp'
Failed to load module 'tool-web': No module named 'aiohttp'
```

**Cause**: The Amplifier CLI installs core dependencies, but some modules (tool-web, tool-mcp) have external Python dependencies not bundled.

**Fix**: The Dockerfile now includes:
```dockerfile
RUN TOOL_DIR=$(uv tool dir)/amplifier && \
    $TOOL_DIR/bin/pip install aiohttp mcp
```

**Verification**: After container build, these warnings should NOT appear.

---

### Pitfall 2: Agent vs Recipe Bash Capability Mismatch

**Symptom**: Agent tries to run `git commit` but nothing happens.

**Cause**: There are THREE execution contexts with different capabilities:

| Execution Context | bash | git | file I/O | delegate |
|-------------------|------|-----|----------|----------|
| Recipe `type: bash` step | ✅ | ✅ | ❌ | ❌ |
| Recipe `type: agent` step | Depends on agent | Depends on agent | ✅ (if agent has tools) | ✅ |
| Sub-agent (delegated) | Depends on agent | Depends on agent | ✅ (if agent has tools) | ✅ |

**Key insight**: Agent steps delegate to an agent. Capabilities depend on what that agent can do. Most foundation agents (file-ops, git-ops, explorer) lack bash. Only recipe bash steps have guaranteed shell access.

**Amplifier architecture note**: Modules follow stable protocols (Tool, Provider, Orchestrator). When a module fails to load, the coordinator gracefully removes it from the session. This is by design — modules are swappable.

**Fix**: The `iteration.yaml` post-session step handles git commit/push via bash. Agents only mark features as `implemented`. The bash step promotes to `done` after successful commit.

---

### Pitfall 3: Stale Git Status in Conversation Context

**Symptom**: You see uncommitted files in the conversation context even after recipes have committed them.

**Cause**: The `environment_context` is a **point-in-time snapshot** from the START of the conversation. It never updates during the session.

**Fix**: Don't trust the environment context for git status after any recipe execution. Use a verification recipe:
```bash
amplifier tool invoke recipes operation=execute recipe_path=.dev-machine/verify-status.yaml
```

Or check directly:
```bash
git log --oneline -5 && git status
```

---

### Pitfall 4: Module Load Warnings Appear as Failures

**Symptom**: Logs show `Failed to load module` but recipe reports `✅ Recipe completed`.

**Cause**: Amplifier gracefully degrades when modules fail to load. The session continues with remaining tools. This is by design but can mask dependency issues.

**Fix**: Check for these warnings after first container build. If present, the Dockerfile is missing dependencies.

---

### Pitfall 5: Git Credentials Not Mounted

**Symptom**: `git push` fails with authentication error.

**Cause**: The container needs access to GitHub credentials. The `docker-run.sh` script should pass `GITHUB_TOKEN` to the container.

**Fix**: Ensure `docker-run.sh` includes:
```bash
-e GITHUB_TOKEN="$GITHUB_TOKEN"
```

And the Dockerfile configures:
```dockerfile
RUN git config --system credential.helper "!gh auth git-credential"
```

---

## Architecture Overview

### File Structure

```
.dev-machine/
├── Dockerfile                    # Container definition
├── docker-run.sh                 # Entry script (builds/runs container)
├── build.yaml                    # OUTER LOOP: orchestrates everything
├── iteration.yaml                # INNER LOOP: one work iteration
├── health-check.yaml             # FIX LOOP: diagnose and repair
├── fix-iteration.yaml            # Single fix attempt
├── working-session-instructions.md  # Agent operating manual
├── feature-spec-template.md      # Template for feature specs
├── SETUP-GUIDE.md               # This document
│
│   # Utility recipes (helpers for manual operations)
├── cleanup.yaml                  # Clean up temporary files
├── commit-all.yaml               # Commit all changes
├── git-output.yaml               # Check git status
├── simple-commit.yaml            # Simple commit helper
└── verify-status.yaml            # Verify build/test status
```

### Loop Hierarchy

```
build.yaml (outer loop)
    └── container-check
    └── read-state
    └── auto-heal (if blockers)
    └── work-loop (while features remain)
        └── iteration.yaml (inner loop)
            └── orient (read state files)
            └── module-health-check
            └── working-session (agent)
            └── build-check (ruff + pyright)
            └── post-session (commit + state update)
        └── health-check.yaml (if build fails)
            └── fix-loop
                └── fix-iteration.yaml
    └── final-summary
```

### State Files

| File | Purpose | Updated When |
|------|---------|--------------|
| `STATE.yaml` | Machine-readable truth: phase, features, blockers | Every iteration |
| `CONTEXT-TRANSFER.md` | Human-readable handoff: session summaries, decisions | Every iteration |
| `SCRATCH.md` | Ephemeral working memory | During session |
| `FEATURE-ARCHIVE.yaml` | Completed features archive | When features done |

---

## Verification After Setup

Run these checks after initial setup:

### 1. Container Builds Clean

```bash
./.dev-machine/docker-run.sh --build 2>&1 | grep -E "(Failed|Error)" || echo "✓ No errors"
```

### 2. Module Load Clean

```bash
# Inside container (or via docker exec)
amplifier tool invoke recipes operation=validate recipe_path=.dev-machine/build.yaml
```

### 3. Git Works Inside Container

```bash
docker run --rm -e GITHUB_TOKEN="$GITHUB_TOKEN" \
  amplifier-dev-machine:your-project \
  bash -c "git config user.email && gh auth status"
```

### 4. State Files Valid

```bash
python3 -c "import yaml; yaml.safe_load(open('STATE.yaml')); print('✓ STATE.yaml valid')"
```

---

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| "No module named 'mcp'" | Dockerfile line 31-32 | Add `pip install mcp aiohttp` |
| "command not found: git" | Docker image | Add git to apt-get install |
| "Permission denied" on .git | Docker volume ownership | Run `sudo chown -R $(whoami) .git` on host |
| Commits not appearing | Check iteration.yaml post-session | Ensure git commit in bash step |
| Push fails | GITHUB_TOKEN | Export token before docker-run.sh |
| Recipe "completed" but no change | Check git status OUTSIDE conversation | Context is stale |

---

## Phase 0 Retrospective (Lessons from First Run)

### What the Dev-Machine Self-Fixed

During Phase 0 (9 features, 8 epochs), the dev-machine discovered and fixed issues autonomously:

| Issue | Root Cause | Self-Fix Applied |
|-------|-----------|------------------|
| 7 pyright errors (unused imports, null safety) | Build gate not strict | Health-check loop fixed the code |
| False-positive blocker from ruff exit codes | Exit code handling bug | Fixed `iteration.yaml` exit logic |
| Build gate not failing on pyright errors | Commands piped incorrectly | Separated: `ruff || exit 1; pyright || exit 1` |

### Pitfall 6: Build Gate Not Enforcing pyright Errors

**Symptom**: pyright shows errors, but recipe continues as if successful.

**Cause**: Original `iteration.yaml` piped commands together:
```bash
# BAD: Only checks last command's exit code
if uv run ruff check src/ && uv run pyright src/ 2>&1; then
```

**Fix** (now implemented):
```bash
# GOOD: Fail on ANY error
uv run ruff check src/ || exit 1
uv run pyright src/ || exit 1
```

### Pitfall 7: Aspirational Contracts Not Enforced

**Symptom**: Constitution says "pyright MUST pass" but code with pyright errors gets committed.

**Cause**: The dev-machine wrote the GOLDEN_VISION_V2.md (constitution) but the iteration.yaml (policy) didn't actually enforce it. The mechanism was correct, but the policy was lax.

**Lesson**: Every MUST in the constitution needs a corresponding `exit 1` in the recipe. Aspirational rules that aren't machine-enforced will be violated.

**Fix**: Added `pyright strict` mode to `pyproject.toml`:
```toml
[tool.pyright]
typeCheckingMode = "strict"
```

---

### Pitfall 8: No Completion Gate (False Victory)

**Symptom**: Machine declares "Phase Complete" while build errors still exist.

**Cause**: The work-loop exits when `status == 'complete'` (all features implemented), but there was no verification gate before declaring victory. The machine counted features, not build cleanliness.

**Root Cause Chain**:
1. Session marks features as "implemented"
2. post-session sees 0 remaining features → sets `status: "complete"`
3. build.yaml's while loop exits (break_when condition satisfied)
4. final-summary runs and reports VICTORY
5. **But no code verified the build is clean**

**Fix**: Added `completion-gate` step to `build.yaml` (between work-loop and final-summary):
- Runs ALL three checks: ruff, pyright, pytest
- No short-circuit — all checks run even if one fails
- Aggregates results and adds blocker on any failure
- Uses `on_error: "fail"` to prevent false victory

**Additional Fix**: Removed `--exit-zero` from iteration.yaml's build-check so lint errors are caught during iterations, not just at the gate.

**Expert Consensus** (from 4 parallel reviewers):
- amplifier-expert: "Gate is aligned with verification-before-completion principle"
- zen-architect: "~20 lines YAML, no new recipes, writes blocker on failure"
- core-expert: "This is policy (correct layer), needs all-check aggregation"
- explorer: "Insert between work-loop and final-summary"

### The Honest Self-Assessment

From the dev-machine's own investigation:

> "I wrote the constitution but didn't enforce it in the recipe. The GOLDEN_VISION_V2.md says 'Build MUST pass after every feature' but when I generated iteration.yaml, I wrote a bash check that only checked the LAST exit code."

> "The constitution was aspirational, not enforced."

This is the key lesson: **Contracts in prose must become gates in code.**

---

## For Future Teams

When hydrating a new session with this context:

1. **Share this document** in the initial prompt
2. **Share STATE.yaml** for current progress
3. **Share CONTEXT-TRANSFER.md** for recent decisions
4. **Run pre-flight checklist** before first autonomous execution
5. **Check that every MUST in the constitution has a corresponding `exit 1` in the recipes**

The dev-machine is designed to be stateless and resumable. State lives in files, not in any session's memory.

---

## Phase 1 Lessons: Interactive Execution Mode

### Pitfall 9: File Permissions After Docker Autonomous Work

**Symptom**: `Permission denied` when superpowers:implementer tries to edit files.

```
OS error modifying file: [Errno 13] Permission denied: 'src/.../provider.py'
```

**Cause**: Docker runs as root. Files modified during autonomous Phase 0 are owned by root. When switching to interactive mode (superpowers execute-plan), the host user cannot edit those files.

**Fix**:
```bash
sudo chown -R $(whoami):$(whoami) src/
```

**Prevention**: Add to docker-run.sh or Dockerfile:
```bash
# Match container user to host user
--user $(id -u):$(id -g)
```

---

### Pitfall 10: Superpowers Implementer Lacks Bash Access

**Symptom**: Implementer delegates to foundation:file-ops or foundation:git-ops for shell commands, but those agents also lack bash. Tokens wasted on futile delegation chains.

```
delegate(agent="foundation:file-ops", instruction="run chmod...")
→ Agent tries to read files, can't execute shell, spins futilely
→ Delegates again to another agent
→ More tokens wasted
```

**Cause**: Superpowers is designed for generic interactive work. It has filesystem and delegation tools but NOT bash. The dev-machine recipes (iteration.yaml) have bash because they're designed for autonomous work.

**Key Insight**: Different execution modes have different capabilities:

| Mode | Has Bash | Use Case |
|------|----------|----------|
| Recipe bash step | ✅ YES | Autonomous batch work |
| Recipe agent step | ❌ NO | Agent delegates file ops |
| Superpowers implementer | ❌ NO | Interactive human-reviewed |

**Fix Options**:

1. **Ask human to run shell commands** (current approach)
2. **Create a skill** to encode the knowledge (done — see below)
3. **Modify bundle config** to add bash to implementer (architectural fix)

---

### Skill: delegation-discipline

Created locally at `.amplifier/skills/delegation-discipline/` (workspace skill).

**Why local?** This knowledge is project-specific. Workspace skills are discovered before bundle skills, so this will override any ecosystem version. This works because Amplifier's skill discovery gives workspace skills priority over user and bundle skills.

**Why a skill?** Skills persist across sessions. Any future session can `load_skill(skill_name="delegation-discipline")` to learn:
- Which agents have bash access (none of the foundation agents)
- Anti-patterns: delegating bash work to non-bash agents
- Correct patterns: ask human for shell commands, use edit_file directly

**Usage in future sessions**:
```
load_skill(skill_name="delegation-discipline")
```

This is part of the cross-session learning system — mistakes made once are encoded so they're not repeated.

---

### Why Recipes vs Superpowers for Phase 1

Phase 0 used dev-machine recipes (autonomous, Docker, bash access).
Phase 1 uses superpowers execute-plan (interactive, human gates, no bash).

**This is intentional:**

| Phase | Risk Level | Execution Mode | Why |
|-------|------------|----------------|-----|
| Phase 0 | Low (proven patterns) | Recipe autonomous | Batch features, known territory |
| Phase 1 | High (first SDK integration) | Superpowers interactive | Unknown failure modes, need human catch |
| Phase 2+ | Low (pattern established) | Recipe autonomous | Can return to batch mode |

The trade-off: Interactive mode is safer but slower. Autonomous mode is faster but riskier for new territory.

---

## Phase 0 Final Status

| Metric | Value |
|--------|-------|
| Features completed | 9 (F-001 through F-009) |
| Epochs | 8 |
| Lines of code | ~1,781 (after F-017 cleanup; was ~1,868 before) |
| Build status | ✅ ruff clean, pyright clean (2 expected stub warnings) |
| Test status | ✅ All passing |

The machine successfully built a working GitHub Copilot provider from the GOLDEN_VISION_V2.md constitution.

---

## Pitfall 11: Docker Volume Permissions (PERMANENT FIX)

**Symptom**: After autonomous dev-machine runs, git operations fail:
```
error: insufficient permission for adding an object to repository database .git/objects
```

**Root Cause**: 
- Docker containers run as `root` (UID 0) by default
- Files created in mounted volumes inherit `root:root` ownership
- Host user (UID 1000) cannot write to root-owned files
- Every autonomous run creates new root-owned files → cycle repeats

**Why This Kept Happening**:
```
1. User fixes permissions: sudo chown -R $(whoami) .
2. Docker dev-machine runs → creates root-owned .git/objects/, STATE.yaml
3. User/agent tries to commit → Permission denied
4. Repeat step 1 (happened 4+ times in one day)
```

### The Fix (Applied 2026-03-13)

**Expert Consensus**: 4/4 agents recommended `--user` flag (zen-architect, integration-specialist, bug-hunter, explorer)

#### Changes to docker-run.sh

```bash
# OLD (ran as root):
DOCKER_ARGS=(
    --rm
    -v "$PROJECT_DIR:/workspace"
    -v "$HOME/.gitconfig:/root/.gitconfig:ro"
    -v "$HOME/.amplifier:/root/.amplifier"
    ...
)

# NEW (runs as host user):
DOCKER_ARGS=(
    --rm
    --user "$(id -u):$(id -g)"                          # ← KEY FIX
    -v "$PROJECT_DIR:/workspace"
    -v "$HOME/.gitconfig:/home/amplifier/.gitconfig:ro" # ← Updated path
    -v "$HOME/.amplifier:/home/amplifier/.amplifier"    # ← Updated path
    -e "HOME=/home/amplifier"                           # ← Set HOME env
    ...
)
```

#### Changes to Dockerfile

```dockerfile
# NEW: Create writable home for non-root user
RUN mkdir -p /home/amplifier/.local/bin /home/amplifier/.amplifier /home/amplifier/.cache \
    && chmod -R 777 /home/amplifier

# NEW: Install amplifier to accessible location (not /root/)
ENV UV_TOOL_DIR=/home/amplifier/.local/share/uv/tools
ENV UV_TOOL_BIN_DIR=/home/amplifier/.local/bin
RUN uv tool install git+https://github.com/microsoft/amplifier ...
ENV PATH="/home/amplifier/.local/bin:$PATH"

# CHANGED: Git config at SYSTEM level (works for any user)
RUN git config --system user.email "amplifier-ai@microsoft.com" \
    && git config --system user.name "Amplifier Dev Machine" \
    && git config --system --add safe.directory /workspace \
    && git config --system credential.helper "!gh auth git-credential"
```

### Why This Works

| Before | After |
|--------|-------|
| Container runs as UID 0 (root) | Container runs as UID 1000 (host user) |
| Files created as `root:root` | Files created as `mowrim:mowrim` |
| Host user can't commit | Host user can commit immediately |
| Need `sudo chown` after every run | No permission fixes needed |

### Migration Steps (One-Time)

After the autonomous machine finishes its current run:

```bash
# Step 1: Fix existing root-owned files (one time only)
cd /home/mowrim/projects/next-get-provider-github-copilot
sudo chown -R $(whoami):$(whoami) .

# Step 2: Rebuild the container with the new Dockerfile
./.dev-machine/docker-run.sh --build

# Step 3: Future runs will have correct permissions automatically
./.dev-machine/docker-run.sh
```

### Verification

After rebuild, verify the fix works:

```bash
# Run a quick test
./.dev-machine/docker-run.sh --build

# Check file ownership after run
ls -la STATE.yaml .git/objects/ | head -5
# Should show YOUR user, not root

# Verify git works
git status && git log --oneline -1
# Should work without sudo
```

---

## Steps for Next Run

After the current autonomous machine finishes:

### 1. Fix Existing Permissions (One Time)

```bash
cd /home/mowrim/projects/next-get-provider-github-copilot
sudo chown -R $(whoami):$(whoami) .
```

### 2. Rebuild Container with Permission Fix

```bash
./.dev-machine/docker-run.sh --build
```

This rebuilds the image with:
- `--user $(id -u):$(id -g)` in docker run
- `/home/amplifier` directory for non-root user
- Amplifier CLI installed to `/home/amplifier/.local/bin`

### 3. Run Autonomous Machine

```bash
./.dev-machine/docker-run.sh
```

No more permission issues. Files created by Docker will be owned by your user.

### 4. (Optional) Verify Fix Worked

```bash
# After run completes, check ownership
ls -la STATE.yaml SCRATCH.md
# Should show: mowrim mowrim (not root root)

# Verify git works without sudo
git status
git log --oneline -3
```

---
