---
name: delegation-discipline
description: Use when delegating tasks to foundation agents to verify they have required capabilities (bash, filesystem, git access) before delegation. Prevents token waste from futile delegations.
---

# Delegation Discipline

## When to Use

- Before delegating to any foundation agent for bash/shell work
- When you see "permission denied" or agent "spinning futilely"
- When a delegation chain keeps failing
- Before any subagent delegation to verify capability match

## Overview

**Purpose:** Avoid token waste from futile delegations. Know what agents can and cannot do before delegating.

## Agent Capability Quick Reference

| Agent | Has Bash? | Has Filesystem? | Has Git? | Use For |
|-------|-----------|-----------------|----------|---------|
| foundation:file-ops | ❌ NO | ✅ YES | ❌ NO | Read/write files only |
| foundation:git-ops | ❌ NO | ❌ NO | ✅ YES | Git commands only |
| foundation:explorer | ❌ NO | ✅ YES | ❌ NO | Code exploration |
| foundation:bug-hunter | ❌ NO | ✅ YES | ❌ NO | Debugging |
| foundation:modular-builder | ❌ NO | ✅ YES | ❌ NO | Implementation |

## Anti-Patterns

### ❌ Delegating bash work to non-bash agents

```
BAD: delegate(agent="foundation:file-ops", instruction="run chmod -R u+w src/")
Result: Agent tries to read files, can't execute shell, spins futilely
Tokens wasted: ~500+ per failed attempt
```

### ❌ Chain delegation hoping someone has bash

```
BAD: delegate → delegate → delegate looking for bash access
Result: Each hop wastes ~200 tokens, none succeed
```

## Correct Patterns

### ✅ Check capability before delegating

```
GOOD: "Does this agent have bash access?"
If NO → Don't delegate bash work to them
If YES → Delegate confidently
```

### ✅ Ask human for shell commands

```
GOOD: "I need to run chmod -R u+w src/. Please run this command and confirm."
Result: Human runs it, you continue with edit_file
```

### ✅ Use your own tools directly

```
GOOD: Use edit_file directly instead of delegating file edits
Result: Faster, no delegation overhead
```

## Decision Tree

```
Need shell command (chmod, ls -la, etc.)?
├── Do I have bash tool? → Use it directly
├── Does target agent have bash? → Delegate to them
└── No one has bash → Ask human to run command
```

## Superpowers vs Recipes

| Situation | Use | Why |
|-----------|-----|-----|
| First-time work, needs human oversight | Superpowers execute-plan | Interactive gates |
| Proven, repeatable batch work | Dev-machine recipes | Has bash, autonomous |
| Need bash access | Recipes (or ask human) | Superpowers implementer lacks bash |

## Key Insight

**Dev-machine recipes have bash access. Superpowers implementer does not.**

If you're in superpowers mode and need shell:
1. Ask human to run the command
2. Continue with file operations you CAN do
3. Don't waste tokens on impossible delegations
