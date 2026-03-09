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

| Context | bash | git | file I/O | delegate |
|---------|------|-----|----------|----------|
| Recipe `type: bash` step | ✅ | ✅ | ❌ | ❌ |
| Recipe `type: agent` step | ❌ | ❌ | ✅ | ✅ |
| Sub-agent (delegated) | ❌ | ❌ | ✅ | ✅ |

**Key insight**: Agents CAN'T run bash. Only recipe bash steps can. Git operations MUST be in recipe bash steps, NOT in agent instructions.

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
└── SETUP-GUIDE.md               # This document
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

## For Future Teams

When hydrating a new session with this context:

1. **Share this document** in the initial prompt
2. **Share STATE.yaml** for current progress
3. **Share CONTEXT-TRANSFER.md** for recent decisions
4. **Run pre-flight checklist** before first autonomous execution

The dev-machine is designed to be stateless and resumable. State lives in files, not in any session's memory.
