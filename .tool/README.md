# F-045 Forensic Analysis Toolkit

> **Proving SDK Tools Do NOT Fire When Using Our Provider**

This toolkit provides comprehensive forensic analysis to verify that the 28 known SDK tools
are completely suppressed when using our `available_tools=[]` provider configuration.

## Quick Verification

```powershell
# Run the complete forensic suite (most recent session)
cd .tool
python f045_compliance_suite.py --latest

# Or specify a session ID
python f045_compliance_suite.py --session <session_id>
```

Expected output: `[PASS] F-045 SOLID - NO SDK TOOLS FIRING`

---

## The 28 Known Hidden Tools

### Exposed (13) - From `tools.list`
| Tool | Risk | Trigger Behavior |
|------|------|------------------|
| bash | HIGH | Run shell commands |
| glob | HIGH | Find files |
| grep | HIGH | Search file contents |
| str_replace_editor | HIGH | Edit files |
| web_fetch | HIGH | HTTP requests |
| ask_user | MEDIUM | Prompt user |
| list_bash | MEDIUM | List processes |
| read_bash | MEDIUM | Read process output |
| stop_bash | MEDIUM | Kill processes |
| task | MEDIUM | Create tasks |
| write_bash | MEDIUM | Write to stdin |
| fetch_copilot_cli_documentation | LOW | Get docs |
| report_intent | LOW | Log intent |

### In SDK Source (6) - Not in `tools.list`
| Tool | Risk | Location |
|------|------|----------|
| view | HIGH | test/e2e/session.test.ts |
| edit | HIGH | test/e2e/builtin_tools.test.ts |
| create_file | HIGH | test/e2e/builtin_tools.test.ts |
| powershell | HIGH | test/harness/util.ts |
| read_powershell | MEDIUM | test/harness/util.ts |
| write_powershell | MEDIUM | test/harness/util.ts |

### Runtime Discovered (9)
| Tool | Risk | Discovery Method |
|------|------|------------------|
| shell | HIGH | Model invocation |
| web_search | HIGH | Model invocation |
| create | MEDIUM | Runtime error |
| update_todo | MEDIUM | Session events |
| skill | MEDIUM | Session behavior |
| search_code_subagent | MEDIUM | Model delegation |
| github-mcp-server-web_search | MEDIUM | MCP invocation |
| report_progress | LOW | Session events |
| task_complete | LOW | Completion events |

---

## Available Scripts

### 1. `f045_compliance_suite.py` - Master Orchestrator
Runs all forensic checks in sequence:
```powershell
python f045_compliance_suite.py --latest                    # Analyze recent session
python f045_compliance_suite.py --session <id> --output reports/  # Save reports
python f045_compliance_suite.py --latest --json             # JSON output
```

### 2. `hidden_tool_prober.py` - Known Tool Detection
Scans for the 28 known SDK tools:
```powershell
python hidden_tool_prober.py --list                         # List all known tools
python hidden_tool_prober.py --analyze <session_id>        # Analyze specific session
python hidden_tool_prober.py --latest --output report.md   # Generate report
```

### 3. `deep_log_scanner.py` - Full Evidence Extraction
Extracts ALL tool-related evidence from logs:
```powershell
python deep_log_scanner.py --recent 20                      # Scan last 20 logs
python deep_log_scanner.py --session <id>                   # Filter by session
python deep_log_scanner.py --export evidence.json           # Export raw evidence
```

### 4. `negative_test_suite.py` - Probe Testing
Generates prompts designed to trigger tools (for manual testing):
```powershell
python negative_test_suite.py --generate-prompts            # Create test prompts
python negative_test_suite.py --validate <session_id>       # Validate after testing
```

### 5. `evidence_collector.py` - Session Evidence
Collect evidence from specific sessions:
```powershell
python evidence_collector.py --list                         # List recent sessions
python evidence_collector.py --session <id>                 # Analyze session
```

### 6. `tool_analyzer.py` - Tool Flow Analysis
Analyze tool call flows:
```powershell
python analyze_session.py <session_id>                      # Full 360° analysis
```

---

## Evidence-Based Verification

### What We're Proving (Negative Verification)

We don't test IF tools work - we prove they DON'T work. Evidence must show:

1. **`tool_names: "[]"`** in session logs (SDK received empty tool list)
2. **Zero `tool_use` events** (no tool invocation attempts)
3. **Zero `tool_result` events** (no tool executions)
4. **Zero `tool_call` events** (model didn't try to call tools)

### Forensic Checks Performed

| Check | Purpose | Pass Criteria |
|-------|---------|---------------|
| Tool Availability | Verify tools_available=[] | Value is empty list |
| Tool Announcements | Count tools announced to model | Count = 0 |
| Tool Attempts | Detect model trying to call tools | Count = 0 |
| Tool Executions | Detect tools actually running | Count = 0 |
| Known Tool Match | Check for 28 known tools specifically | None found |

---

## Interpreting Results

### PASS - F-045 COMPLIANT
```
VERDICT: [PASS] F-045 SOLID - NO SDK TOOLS FIRING
```
- `tools_available=[]` is working
- Model cannot invoke any of the 28 known tools
- No tool-related events detected

### FAIL - INVESTIGATION REQUIRED
```
VERDICT: [FAIL] INVESTIGATION REQUIRED
```
Possible causes:
1. Session config not applied correctly
2. SDK version introduced new bypass
3. MCP tools configured (not covered by available_tools)

---

## Historical Context

### March 5, 2026 Analysis
The original analysis identified 28 tools that could potentially fire:
- Complex exclusion list approach was fragile
- Tools could be added silently by SDK updates
- No verification mechanism

### Current F-045 Approach
```python
session_config["available_tools"] = []  # Line 220 in sdk_adapter/client.py
```
- Complete suppression - no exclusion list needed
- Works regardless of new SDK tools
- Verified through forensic evidence

---

## Running Full Forensic Suite

```powershell
# Navigate to toolkit
cd D:\next-get-provider-github-copilot\.tool

# Run complete suite
python f045_compliance_suite.py --latest --output reports/

# Review results
Get-Content reports\f045_compliance_*.md
```

Exit codes:
- `0` - F-045 COMPLIANT
- `1` - F-045 VIOLATION  
- `2` - ERROR

---

*Toolkit created March 14, 2026 - Principal Engineer forensic verification*
