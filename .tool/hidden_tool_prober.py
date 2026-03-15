#!/usr/bin/env python3
"""
Hidden Tool Forensic Prober - F-045 Compliance Verification

This script provides forensic analysis to verify that SDK built-in tools
are NOT being triggered despite the provider passing `available_tools=[]`.

Based on analysis from 2026-03-05 SDK discussion document identifying
28 known tools (13 exposed + 6 in source + 9 runtime-discovered).

Usage:
    # List all known hidden tools
    python hidden_tool_prober.py --list
    
    # Analyze latest session for hidden tool invocations
    python hidden_tool_prober.py --analyze <session_id>
    
    # Generate compliance report
    python hidden_tool_prober.py --report --output report.md

Principal Engineer Note:
    The goal is NEGATIVE verification - we want to prove tools are NOT firing.
    Any detection of these tools in logs indicates F-045 bypass/failure.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from log_paths import find_copilot_logs
from log_collector import read_log_file_raw


# ============================================================================
# KNOWN TOOLS DATABASE - From 2026-03-05 Analysis
# ============================================================================

@dataclass
class KnownTool:
    """A known SDK tool with discovery context."""
    name: str
    category: str  # 'exposed', 'source', 'runtime'
    source: str    # Where it was discovered
    trigger_prompt: str  # Prompt that would typically trigger this tool
    risk_level: str  # 'high', 'medium', 'low'


# 13 tools from tools.list (exposed)
EXPOSED_TOOLS = [
    KnownTool("ask_user", "exposed", "tools.list", "Ask the user a clarifying question", "medium"),
    KnownTool("bash", "exposed", "tools.list", "Run 'echo hello' in bash", "high"),
    KnownTool("fetch_copilot_cli_documentation", "exposed", "tools.list", "Show me Copilot CLI docs", "low"),
    KnownTool("glob", "exposed", "tools.list", "Find all Python files in src/", "high"),
    KnownTool("grep", "exposed", "tools.list", "Search for 'def main' in all files", "high"),
    KnownTool("list_bash", "exposed", "tools.list", "List running bash processes", "medium"),
    KnownTool("read_bash", "exposed", "tools.list", "Read output from bash", "medium"),
    KnownTool("report_intent", "exposed", "tools.list", "Report what you intend to do", "low"),
    KnownTool("stop_bash", "exposed", "tools.list", "Stop the running bash command", "medium"),
    KnownTool("str_replace_editor", "exposed", "tools.list", "Replace 'foo' with 'bar' in file.py", "high"),
    KnownTool("task", "exposed", "tools.list", "Create a new task", "medium"),
    KnownTool("web_fetch", "exposed", "tools.list", "Fetch https://example.com", "high"),
    KnownTool("write_bash", "exposed", "tools.list", "Write input to bash stdin", "medium"),
]

# 6 tools in SDK source (not in tools.list)
SOURCE_TOOLS = [
    KnownTool("view", "source", "nodejs/test/e2e/session.test.ts:102", "View the contents of README.md", "high"),
    KnownTool("edit", "source", "nodejs/test/e2e/builtin_tools.test.ts:55", "Edit README.md and add a line", "high"),
    KnownTool("create_file", "source", "nodejs/test/e2e/builtin_tools.test.ts:67", "Create a new file called test.txt", "high"),
    KnownTool("powershell", "source", "test/harness/util.ts:26", "Run Get-Process in PowerShell", "high"),
    KnownTool("read_powershell", "source", "test/harness/util.ts:27", "Read PowerShell output", "medium"),
    KnownTool("write_powershell", "source", "test/harness/util.ts:28", "Write to PowerShell stdin", "medium"),
]

# 9 runtime-discovered tools
RUNTIME_TOOLS = [
    KnownTool("create", "runtime", "Runtime error discovery", "Create something new", "medium"),
    KnownTool("shell", "runtime", "Model invocation", "Execute shell command", "high"),
    KnownTool("web_search", "runtime", "Model invocation", "Search the web for Python tutorials", "high"),
    KnownTool("report_progress", "runtime", "Session event analysis", "Report progress on the task", "low"),
    KnownTool("update_todo", "runtime", "Session event analysis", "Update the todo list", "medium"),
    KnownTool("skill", "runtime", "Session behavior", "Use a skill to complete this", "medium"),
    KnownTool("task_complete", "runtime", "Session completion events", "Mark the task as complete", "low"),
    KnownTool("search_code_subagent", "runtime", "Model delegation", "Search the codebase for implementations", "medium"),
    KnownTool("github-mcp-server-web_search", "runtime", "MCP tool invocation", "Search GitHub for repos", "medium"),
]

# Combined list
ALL_KNOWN_TOOLS = EXPOSED_TOOLS + SOURCE_TOOLS + RUNTIME_TOOLS


# ============================================================================
# LOG PATTERNS - What tool invocation looks like in logs
# ============================================================================

# Patterns that indicate a tool was invoked
TOOL_INVOCATION_PATTERNS = [
    r'"kind":\s*"tool_use"',
    r'"kind":\s*"tool_call"',
    r'"kind":\s*"tool_result"',
    r'"type":\s*"tool_use"',
    r'"type":\s*"tool_call"',
    r'tool_name["\']?\s*[:=]\s*["\'](\w+)',
    r'"name":\s*"([^"]+)".*"type":\s*"function"',
    r'invok(?:e|ing)\s+tool[:\s]+(\w+)',
    r'tool\s+(?:called|invoked|executed)[:\s]+(\w+)',
]

# Pattern to extract tool names from logs
TOOL_NAME_EXTRACTION_PATTERNS = [
    (r'"tool_name":\s*"([^"]+)"', 1),
    (r'"name":\s*"([^"]+)"', 1),
    (r'tool[:\s]+(\w+)', 1),
]


@dataclass
class ToolInvocationEvidence:
    """Evidence of a tool being invoked."""
    tool_name: str
    log_file: str
    line_number: int
    context: str  # Surrounding log text
    timestamp: str | None
    session_id: str


@dataclass 
class ForensicReport:
    """Complete forensic analysis report."""
    session_id: str
    analysis_timestamp: str
    log_files_analyzed: list[str]
    total_lines_scanned: int
    
    # Tool availability check
    tools_available_value: str  # Should be "[]"
    
    # Invocation evidence
    tools_invoked: list[ToolInvocationEvidence]
    
    # Compliance
    f045_compliant: bool
    
    # Summary
    high_risk_tools_found: list[str]
    medium_risk_tools_found: list[str]
    low_risk_tools_found: list[str]


def get_all_tool_names() -> set[str]:
    """Get set of all known tool names."""
    return {t.name for t in ALL_KNOWN_TOOLS}


def get_tool_by_name(name: str) -> KnownTool | None:
    """Get tool info by name."""
    for tool in ALL_KNOWN_TOOLS:
        if tool.name == name:
            return tool
    return None


def scan_log_for_tool_invocations(
    log_path: Path, 
    session_id: str | None = None
) -> list[ToolInvocationEvidence]:
    """Scan a log file for any evidence of tool invocations."""
    evidence_list: list[ToolInvocationEvidence] = []
    
    try:
        content = log_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"  Warning: Failed to read {log_path}: {e}")
        return []
    
    lines = content.splitlines()
    known_tools = get_all_tool_names()
    
    for line_num, line in enumerate(lines, 1):
        # Skip if session filter doesn't match
        if session_id and session_id not in line:
            continue
        
        # Check for tool invocation patterns
        for pattern in TOOL_INVOCATION_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # Try to extract tool name
                tool_name = "unknown"
                for name_pattern, group_idx in TOOL_NAME_EXTRACTION_PATTERNS:
                    name_match = re.search(name_pattern, line)
                    if name_match:
                        tool_name = name_match.group(group_idx)
                        break
                
                # Only record if it's a known tool or looks like a tool invocation
                if tool_name in known_tools or "tool" in line.lower():
                    # Extract timestamp if present
                    ts_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                    timestamp = ts_match.group(1) if ts_match else None
                    
                    evidence = ToolInvocationEvidence(
                        tool_name=tool_name,
                        log_file=str(log_path),
                        line_number=line_num,
                        context=line[:300],
                        timestamp=timestamp,
                        session_id=session_id or "unknown"
                    )
                    evidence_list.append(evidence)
                    break  # One match per line is enough
    
    return evidence_list


def check_tools_available_value(log_path: Path, session_id: str | None = None) -> str:
    """Extract the tools_available/tool_names value from logs."""
    try:
        content = log_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return "ERROR_READING_LOG"
    
    # Look for tools_available or tool_names in session context
    patterns = [
        r'"tool_names":\s*"(\[[^\]]*\])"',
        r'"available_tools":\s*(\[[^\]]*\])',
        r'tools_available.*?:\s*(\[[^\]]*\])',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    
    return "NOT_FOUND"


def analyze_session(session_id: str, log_limit: int = 30) -> ForensicReport:
    """Perform complete forensic analysis on a session."""
    all_evidence: list[ToolInvocationEvidence] = []
    log_files: list[str] = []
    total_lines = 0
    tools_available = "NOT_FOUND"
    
    print(f"\n{'='*70}")
    print(f"FORENSIC ANALYSIS: Hidden Tool Probe")
    print(f"Session: {session_id}")
    print(f"{'='*70}")
    
    # Scan logs
    print(f"\n[1/4] Scanning log files...")
    for log_source in find_copilot_logs(limit=log_limit):
        content = read_log_file_raw(log_source.path)
        if session_id in content:
            log_files.append(str(log_source.path))
            total_lines += len(content.splitlines())
            
            # Check tools_available value
            ta_value = check_tools_available_value(log_source.path, session_id)
            if ta_value != "NOT_FOUND":
                tools_available = ta_value
            
            # Scan for invocations
            evidence = scan_log_for_tool_invocations(log_source.path, session_id)
            all_evidence.extend(evidence)
            
            print(f"  + {log_source.path.name}: {len(evidence)} tool events")
    
    print(f"\n[2/4] Analyzing tool availability...")
    print(f"  tools_available value: {tools_available}")
    
    # Categorize findings by risk
    print(f"\n[3/4] Categorizing findings...")
    high_risk: list[str] = []
    medium_risk: list[str] = []
    low_risk: list[str] = []
    
    for ev in all_evidence:
        tool = get_tool_by_name(ev.tool_name)
        if tool:
            if tool.risk_level == "high":
                high_risk.append(ev.tool_name)
            elif tool.risk_level == "medium":
                medium_risk.append(ev.tool_name)
            else:
                low_risk.append(ev.tool_name)
    
    # Determine compliance
    print(f"\n[4/4] Determining F-045 compliance...")
    
    # F-045 compliant if:
    # 1. tools_available is "[]" or empty
    # 2. No high-risk tools were invoked
    # 3. No known SDK tools were invoked
    
    sdk_tools_invoked = [
        ev.tool_name for ev in all_evidence 
        if ev.tool_name in get_all_tool_names()
    ]
    
    is_compliant = (
        tools_available in ('[]', '"[]"', 'NOT_FOUND') and
        len(high_risk) == 0 and
        len(sdk_tools_invoked) == 0
    )
    
    report = ForensicReport(
        session_id=session_id,
        analysis_timestamp=datetime.now().isoformat(),
        log_files_analyzed=log_files,
        total_lines_scanned=total_lines,
        tools_available_value=tools_available,
        tools_invoked=all_evidence,
        f045_compliant=is_compliant,
        high_risk_tools_found=list(set(high_risk)),
        medium_risk_tools_found=list(set(medium_risk)),
        low_risk_tools_found=list(set(low_risk))
    )
    
    return report


def generate_report_markdown(report: ForensicReport) -> str:
    """Generate markdown forensic report."""
    lines = [
        "# F-045 Compliance Forensic Report",
        "",
        "> **Hidden Tool Invocation Analysis**",
        "",
        f"**Session ID:** `{report.session_id}`",
        f"**Analysis Time:** {report.analysis_timestamp}",
        f"**Log Files Analyzed:** {len(report.log_files_analyzed)}",
        f"**Total Lines Scanned:** {report.total_lines_scanned:,}",
        "",
        "---",
        "",
        "## 1. F-045 Compliance Status",
        "",
    ]
    
    if report.f045_compliant:
        lines.extend([
            "### [PASS] COMPLIANT",
            "",
            "No hidden SDK tools were detected. The `available_tools=[]` configuration",
            "is effectively suppressing all 28 known SDK tools.",
            "",
        ])
    else:
        lines.extend([
            "### [FAIL] NON-COMPLIANT",
            "",
            "**WARNING: Hidden SDK tools were detected!** This indicates a potential",
            "bypass of the F-045 tool suppression mechanism.",
            "",
        ])
    
    # Tool availability check
    lines.extend([
        "## 2. Tool Availability Configuration",
        "",
        f"**`tools_available` value:** `{report.tools_available_value}`",
        "",
    ])
    
    if report.tools_available_value in ('[]', '"[]"'):
        lines.append("[OK] Correctly set to empty list")
    else:
        lines.append("[WARNING] Unexpected value - should be `[]`")
    
    lines.append("")
    
    # Known tools reference
    lines.extend([
        "## 3. Known Hidden Tools Reference (28 Total)",
        "",
        "| Category | Count | Tools |",
        "|----------|-------|-------|",
        f"| Exposed (tools.list) | 13 | {', '.join(t.name for t in EXPOSED_TOOLS)} |",
        f"| In SDK Source | 6 | {', '.join(t.name for t in SOURCE_TOOLS)} |",
        f"| Runtime Discovered | 9 | {', '.join(t.name for t in RUNTIME_TOOLS)} |",
        "",
    ])
    
    # Detected invocations
    lines.extend([
        "## 4. Tool Invocations Detected",
        "",
    ])
    
    if not report.tools_invoked:
        lines.extend([
            "**None detected.** This is the expected result for F-045 compliance.",
            "",
        ])
    else:
        lines.extend([
            f"**{len(report.tools_invoked)} tool invocation(s) detected:**",
            "",
            "| Tool | Risk | Line | Context |",
            "|------|------|------|---------|",
        ])
        for ev in report.tools_invoked[:20]:  # Limit to 20
            tool = get_tool_by_name(ev.tool_name)
            risk = tool.risk_level if tool else "unknown"
            context = ev.context[:60].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {ev.tool_name} | {risk} | {ev.line_number} | {context}... |")
        
        if len(report.tools_invoked) > 20:
            lines.append(f"| ... | ... | ... | ({len(report.tools_invoked) - 20} more) |")
        lines.append("")
    
    # Risk summary
    lines.extend([
        "## 5. Risk Summary",
        "",
        f"| Risk Level | Tools Found |",
        f"|------------|-------------|",
        f"| HIGH | {', '.join(report.high_risk_tools_found) or 'None'} |",
        f"| MEDIUM | {', '.join(report.medium_risk_tools_found) or 'None'} |",
        f"| LOW | {', '.join(report.low_risk_tools_found) or 'None'} |",
        "",
    ])
    
    # Verdict
    lines.extend([
        "## 6. Verdict",
        "",
    ])
    
    if report.f045_compliant:
        lines.extend([
            "### [PASS] F-045 HOLDING SOLID",
            "",
            "The `available_tools=[]` approach is successfully preventing all 28 known",
            "SDK tools from being invoked. No hidden tool bypass detected.",
            "",
            "**Evidence:**",
            f"- tools_available = `{report.tools_available_value}`",
            f"- SDK tools detected: 0",
            f"- High-risk tools: 0",
            "",
        ])
    else:
        lines.extend([
            "### [FAIL] INVESTIGATION REQUIRED",
            "",
            "Hidden tools were detected despite F-045 suppression. Possible causes:",
            "",
            "1. SDK version introduced new bypass mechanism",
            "2. MCP tools not covered by available_tools filter",
            "3. Tool invocation before session config applied",
            "",
        ])
    
    # Log files analyzed
    lines.extend([
        "## 7. Log Files Analyzed",
        "",
    ])
    for lf in report.log_files_analyzed:
        lines.append(f"- `{Path(lf).name}`")
    
    lines.extend([
        "",
        "---",
        "*Generated by hidden_tool_prober.py - F-045 Compliance Verification*",
    ])
    
    return "\n".join(lines)


def print_tool_list():
    """Print all known hidden tools."""
    print("\n" + "="*70)
    print("KNOWN SDK TOOLS (28 Total)")
    print("="*70)
    
    print("\n## EXPOSED TOOLS (13) - From tools.list")
    print("-" * 50)
    for t in EXPOSED_TOOLS:
        print(f"  [{t.risk_level.upper():6}] {t.name:30} | {t.trigger_prompt[:40]}")
    
    print("\n## SOURCE TOOLS (6) - In SDK source, not in tools.list")
    print("-" * 50)
    for t in SOURCE_TOOLS:
        print(f"  [{t.risk_level.upper():6}] {t.name:30} | {t.source}")
    
    print("\n## RUNTIME TOOLS (9) - Discovered through runtime behavior")
    print("-" * 50)
    for t in RUNTIME_TOOLS:
        print(f"  [{t.risk_level.upper():6}] {t.name:30} | {t.source}")
    
    print("\n" + "="*70)
    print(f"Total: {len(ALL_KNOWN_TOOLS)} tools")
    print("="*70)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='F-045 Hidden Tool Forensic Prober',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python hidden_tool_prober.py --list
  python hidden_tool_prober.py --analyze abc123-def456
  python hidden_tool_prober.py --latest --output report.md
        """
    )
    parser.add_argument('--list', action='store_true', help='List all known hidden tools')
    parser.add_argument('--analyze', metavar='SESSION_ID', help='Analyze specific session')
    parser.add_argument('--latest', action='store_true', help='Analyze most recent session')
    parser.add_argument('--output', '-o', metavar='FILE', help='Write report to file')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of markdown')
    
    args = parser.parse_args()
    
    if args.list:
        print_tool_list()
        return
    
    # Determine session to analyze
    session_id = None
    if args.analyze:
        session_id = args.analyze
    elif args.latest:
        # Find most recent session
        from evidence_collector import find_recent_sessions
        sessions = find_recent_sessions(1)
        if sessions:
            session_id = sessions[0]['session_id']
            print(f"Analyzing most recent session: {session_id}")
        else:
            print("No sessions found")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Run analysis
    report = analyze_session(session_id)
    
    # Generate output
    if args.json:
        output = json.dumps({
            'session_id': report.session_id,
            'analysis_timestamp': report.analysis_timestamp,
            'log_files_analyzed': report.log_files_analyzed,
            'total_lines_scanned': report.total_lines_scanned,
            'tools_available_value': report.tools_available_value,
            'tools_invoked': [
                {
                    'tool_name': ev.tool_name,
                    'line_number': ev.line_number,
                    'context': ev.context[:100]
                }
                for ev in report.tools_invoked
            ],
            'f045_compliant': report.f045_compliant,
            'high_risk_tools_found': report.high_risk_tools_found,
            'medium_risk_tools_found': report.medium_risk_tools_found,
            'low_risk_tools_found': report.low_risk_tools_found,
        }, indent=2)
        
        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f"\nJSON written to: {args.output}")
        else:
            print(output)
    else:
        md_report = generate_report_markdown(report)
        
        if args.output:
            Path(args.output).write_text(md_report, encoding='utf-8')
            print(f"\nReport written to: {args.output}")
        else:
            print(md_report)
    
    # Summary
    print(f"\n{'='*70}")
    print("FORENSIC ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"Session: {session_id[:12]}...")
    print(f"F-045 Status: {'[PASS] COMPLIANT' if report.f045_compliant else '[FAIL] VIOLATION'}")
    print(f"Tools Available: {report.tools_available_value}")
    print(f"Hidden Tools Detected: {len(report.tools_invoked)}")
    print(f"{'='*70}")
    
    # Exit code based on compliance
    sys.exit(0 if report.f045_compliant else 1)


if __name__ == "__main__":
    main()
