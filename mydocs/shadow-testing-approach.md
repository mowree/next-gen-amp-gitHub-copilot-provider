# Shadow Testing Approach for GitHub Copilot Provider

This document describes how to perform end-to-end (E2E) validation of the github-copilot provider in a shadow environment before publishing releases.

## Overview

**Shadow testing** is a separate validation step that tests the provider against real Amplifier runtime, distinct from the fast build loop (unit tests). It should be run:
- Before publishing a new release
- After major changes to provider internals
- When comparing local development vs published versions
- For regression testing after SDK updates

## Files Created

| File | Purpose |
|------|---------|
| `.dev-machine/shadow-test.yaml` | Main recipe for shadow testing |
| `.dev-machine/shadow-prompts.yaml` | Test prompts configuration |
| `.dev-machine/shadow-test-bundle.md` | Minimal test bundle for provider isolation |
| `.dev-machine/shadow-results/` | Output directory for test results |

---

## Quick Start

### Option 1: From Current Amplifier Session

If you're already in an Amplifier session (like talking to me), just ask:

```
"Run shadow test on local provider"
"Run shadow test comparing local vs public"
"Run shadow test with SDK version 0.1.33"
```

I will execute the recipe and have session-analyst review the results.

### Option 2: CLI Standalone

```bash
# Test LOCAL provider (your development code)
amplifier recipe execute .dev-machine/shadow-test.yaml

# Test PUBLIC provider (what users have from PyPI)
amplifier recipe execute .dev-machine/shadow-test.yaml \
  context='{"provider_source": "pypi"}'

# Test with specific SDK version
amplifier recipe execute .dev-machine/shadow-test.yaml \
  context='{"provider_source": "local", "sdk_version": "==0.1.33"}'

# Compare mode (runs both local and public, diffs results)
amplifier recipe execute .dev-machine/shadow-test.yaml \
  context='{"compare_mode": true}'
```

### Option 3: Docker (Autonomous Dev Machine)

```bash
# Use the dedicated shadow test script
./.dev-machine/docker-shadow-test.sh

# Or manually with docker run
docker run --rm \
  -v "$PWD:/workspace" \
  -v "$HOME/.amplifier:/home/amplifier/.amplifier" \
  -e "GITHUB_TOKEN=$GITHUB_TOKEN" \
  -e "COPILOT_AGENT_TOKEN=$COPILOT_AGENT_TOKEN" \
  -e "HOME=/home/amplifier" \
  amplifier-dev-machine:provider-github-copilot \
  "Execute recipe .dev-machine/shadow-test.yaml"
```

---

## Configuration Options

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `provider_source` | `"local"` | `"local"`, `"pypi"`, `"git+https://..."` | Where to install provider from |
| `sdk_version` | `"latest"` | `"latest"`, `">=0.1.33"`, `"==0.1.33"` | SDK version constraint |
| `compare_mode` | `false` | `true`, `false` | Run both local and public, diff results |
| `results_dir` | `".dev-machine/shadow-results"` | Any path | Where to write results |

---

## What Gets Tested

### 1. Installation Verification
- Provider installs into Amplifier's tool environment
- Entry point `provider-github-copilot` is discoverable
- `mount()` function is callable

### 2. Connectivity Test
- Basic prompt/response works
- ChatResponse structure is valid
- No authentication failures

### 3. Tool Use Round-Trip
- Tool definitions reach the LLM
- Tool calls are parsed correctly
- Tool results are sent back
- Response incorporates tool results

### 4. Streaming Verification
- Stream events are emitted
- Content accumulates correctly
- Stream start/end pairs match

### 5. Error Handling
- Errors translate to kernel error types
- Retryable errors are retried
- Fatal errors fail gracefully

---

## Reading Results

### Results Files

After a shadow test run, find results in `.dev-machine/shadow-results/`:

```
.dev-machine/shadow-results/
├── shadow-20260313-153045.yaml       # Test results
├── shadow-20260313-153045-forensics.md   # Session analysis
└── session-log-20260313-153045.jsonl     # Raw events (if extracted)
```

### Results YAML Format

```yaml
run_id: shadow-20260313-153045
provider_source: local
timestamp: 2026-03-13T15:30:45Z
tests:
  connectivity: pass
  tool_use: pass
  error_handling: skipped
metrics:
  total_events: 47
  errors: 0
  avg_latency_ms: 1234
  total_tokens: 567
session_id: abc123-def456
notes: "All tests passed. Provider integration healthy."
```

### Forensics Report

The session-analyst generates a forensics report with:

- **Type Contract Compliance**: ChatResponse structure, tool_calls format
- **Error Patterns**: Any llm:error events, unhandled exceptions
- **Streaming Health**: Stream start/end pairs, broken streams
- **Transcript Integrity**: Orphaned tool calls, role ordering

### Status Meanings

| Status | Meaning |
|--------|---------|
| `PASS` | All checks passed, provider healthy |
| `WARN` | Minor issues detected, review recommended |
| `FAIL` | Critical issues found, do not release |

---

## Diagnostic Commands

### Check Session Logs Manually

```bash
# Find session directory
ls -lt ~/.amplifier/sessions/ | head -5

# View events for latest session
SESSION_ID=$(ls -t ~/.amplifier/sessions/ | head -1)
cat ~/.amplifier/sessions/$SESSION_ID/events.jsonl | jq .

# Filter to provider events
jq 'select(.event | startswith("llm:"))' \
  ~/.amplifier/sessions/$SESSION_ID/events.jsonl
```

### Check for Specific Issues

```bash
# Type mismatches (F-038 pattern)
grep -n "type\|TypeError\|expected" events.jsonl | head -20

# Error events
jq 'select(.event | test("error"))' events.jsonl

# Token usage
jq 'select(.event == "llm:response") | .data.usage' events.jsonl

# Latency outliers
jq 'select(.event == "llm:response") | .data.duration_ms' events.jsonl | sort -rn | head -5
```

### Run Diagnostic Script

```bash
#!/bin/bash
# provider-diagnostics.sh <session_dir>
SESSION_DIR="$1"
EVENTS="$SESSION_DIR/events.jsonl"

echo "=== Provider Health Report ==="
echo ""

echo "--- Event Summary ---"
jq -r '.event' "$EVENTS" | sort | uniq -c | sort -rn

echo ""
echo "--- Error Summary ---"
jq -c 'select(.event | test("error")) | {event, error: .data.error_type}' "$EVENTS"

echo ""
echo "--- LLM Latency (ms) ---"
jq -c 'select(.event == "llm:response") | .data.duration_ms' "$EVENTS" | \
  awk '{sum+=$1; count++; if($1>max)max=$1} END {printf "avg=%.0f max=%d count=%d\n", sum/count, max, count}'

echo ""
echo "--- Token Usage ---"
jq -c 'select(.event == "llm:response") | .data.usage' "$EVENTS"
```

---

## Expert Agents for Review

After shadow tests complete, these agents can help analyze results:

| Agent | Role | When to Use |
|-------|------|-------------|
| **session-analyst** | Parse events.jsonl, detect issues | Always (built into recipe) |
| **amplifier-expert** | Understand integration patterns | When provider loading fails |
| **bug-hunter** | Trace failure root causes | When tests fail |
| **integration-specialist** | Docker/environment issues | When container problems occur |

### Ask for Expert Review

```
"Have session-analyst review the latest shadow test results"
"Ask bug-hunter to investigate the tool_use failure in shadow test"
"Get amplifier-expert to explain why the provider didn't load"
```

---

## Troubleshooting

### Provider Not Found

**Symptom:** `Entry point not found` error

**Fix:** Provider wasn't installed into Amplifier's tool venv

```bash
# Find Amplifier's tool venv
TOOL_VENV="$HOME/.local/share/uv/tools/amplifier"

# Install provider into it
"$TOOL_VENV/bin/python" -m pip install -e . --no-deps
"$TOOL_VENV/bin/python" -m pip install github-copilot-sdk pyyaml
```

### Credentials Missing

**Symptom:** `No credentials available` skip message

**Fix:** Set environment variables

```bash
export GITHUB_TOKEN="your_github_token"
export COPILOT_AGENT_TOKEN="your_copilot_token"
```

### Tool Venv Not Found

**Symptom:** `Cannot find Amplifier tool venv` error

**Fix:** Amplifier CLI isn't installed via uv tool

```bash
uv tool install git+https://github.com/microsoft/amplifier
```

### Docker Permission Issues

**Symptom:** Files created as root, permission denied

**Fix:** Docker run script uses `--user $(id -u):$(id -g)`

```bash
# Ensure docker-run.sh has the --user flag
grep "\-\-user" .dev-machine/docker-run.sh
```

---

## Comparing Versions

### Local vs Public Comparison

```bash
# Run both
amplifier recipe execute .dev-machine/shadow-test.yaml \
  context='{"provider_source": "local"}' \
  && mv .dev-machine/shadow-results/shadow-*.yaml .dev-machine/shadow-results/local-result.yaml

amplifier recipe execute .dev-machine/shadow-test.yaml \
  context='{"provider_source": "pypi"}' \
  && mv .dev-machine/shadow-results/shadow-*.yaml .dev-machine/shadow-results/public-result.yaml

# Diff results
diff .dev-machine/shadow-results/local-result.yaml .dev-machine/shadow-results/public-result.yaml
```

### Key Metrics to Compare

| Metric | What to Look For |
|--------|------------------|
| Latency | New should be ≤ old |
| Token usage | Unexpected changes = prompt format issue |
| Error rate | Should be ≤ old |
| Tool call success | Must be 100% both versions |

---

## Integration with Release Process

### Pre-Release Checklist

1. ✅ All unit tests pass (`uv run pytest tests/ -v`)
2. ✅ Build passes (`uv run ruff check src/ && uv run pyright src/`)
3. ✅ Shadow test LOCAL passes
4. ✅ Shadow test comparison shows no regressions
5. ✅ Forensics report shows `PASS` status
6. ✅ Expert review (session-analyst) complete

### Automated Pre-Release

Add to release workflow:

```bash
# Before tagging release
./.dev-machine/docker-shadow-test.sh
if [ $? -ne 0 ]; then
  echo "Shadow tests failed - do not release"
  exit 1
fi
```

---

## Architecture Notes

### Why Shadow Testing is Separate from Build Loop

| Build Loop | Shadow Testing |
|------------|----------------|
| Fast (minutes) | Slower (requires credentials) |
| Unit tests only | E2E with real Amplifier |
| Every iteration | On-demand |
| No credentials needed | Requires GITHUB_TOKEN |
| Tests internal contracts | Tests external integration |

### Provider Loading Path

```
shadow-test.yaml
  ↓
Install provider into Amplifier tool venv
  ↓
Verify entry point discoverable
  ↓
Amplifier runtime loads provider via mount()
  ↓
Test prompts exercise provider.complete()
  ↓
Session logs captured to events.jsonl
  ↓
session-analyst performs forensics
  ↓
Results written to shadow-results/
```

---

## Support

For issues with shadow testing:

1. Check this documentation
2. Review `.dev-machine/shadow-results/` for error details
3. Ask session-analyst to analyze session logs
4. Escalate to bug-hunter for complex failures
5. Consult amplifier-expert for integration questions
