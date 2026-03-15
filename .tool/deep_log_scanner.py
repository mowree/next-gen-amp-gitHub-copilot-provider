#!/usr/bin/env python3
"""
Deep Log Scanner - Forensic Evidence Extraction for F-045

This scanner goes beyond simple pattern matching to extract ALL evidence
of tool-related activity from Copilot SDK logs, including:

1. Tool announcements (what tools the SDK says are available)
2. Tool invocation attempts (what the model tried to call)
3. Tool execution events (what actually ran)
4. Tool results (what came back)
5. Denied/blocked tools (what was prevented)

Usage:
    # Scan specific session
    python deep_log_scanner.py --session <id>
    
    # Scan all recent logs
    python deep_log_scanner.py --recent 20
    
    # Export evidence
    python deep_log_scanner.py --session <id> --export evidence.json

Principal Engineer Philosophy:
    In forensics, we trust nothing and verify everything.
    We extract raw evidence first, interpret second.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from log_paths import find_copilot_logs


# ============================================================================
# EVIDENCE TYPES
# ============================================================================

@dataclass
class RawEvidence:
    """Raw evidence extracted from logs."""
    source_file: str
    line_number: int
    evidence_type: str  # 'tool_announcement', 'tool_attempt', 'tool_exec', 'tool_result', 'tool_denied'
    raw_text: str
    extracted_data: dict[str, Any]
    timestamp: str | None
    session_id: str | None


@dataclass
class ToolAnnouncement:
    """SDK announcing available tools."""
    tools: list[str]
    tool_count: int
    source: str
    timestamp: str | None


@dataclass
class ToolAttempt:
    """Model attempting to call a tool."""
    tool_name: str
    arguments: dict[str, Any]
    source: str
    timestamp: str | None
    was_blocked: bool


@dataclass
class ToolExecution:
    """Tool actually executing."""
    tool_name: str
    status: str  # 'started', 'completed', 'failed'
    duration_ms: int | None
    source: str
    timestamp: str | None


@dataclass
class ToolDenial:
    """Tool being denied/blocked."""
    tool_name: str
    reason: str
    source: str
    timestamp: str | None


# ============================================================================
# EXTRACTION PATTERNS
# ============================================================================

# Patterns to find tool announcements
TOOL_ANNOUNCEMENT_PATTERNS = [
    r'"tool_names":\s*"(\[[^\]]*\])"',
    r'"available_tools":\s*(\[[^\]]*\])',
    r'"tools":\s*(\[[^\]]*\])',
    r'tools\s*available[:\s]+(\[.*?\])',
    r'providing\s+tools[:\s]+(\[.*?\])',
]

# Patterns to find tool invocation attempts
TOOL_ATTEMPT_PATTERNS = [
    r'"type":\s*"tool_use".*?"name":\s*"([^"]+)"',
    r'"kind":\s*"tool_call".*?"name":\s*"([^"]+)"',
    r'"function":\s*\{[^}]*"name":\s*"([^"]+)"',
    r'invoking\s+tool[:\s]+([a-z_]+)',
    r'tool\s+(?:call|invocation)[:\s]+([a-z_]+)',
]

# Patterns to find tool execution
TOOL_EXEC_PATTERNS = [
    r'tool\s+(?:started|executing)[:\s]+([a-z_]+)',
    r'"tool_result".*?"name":\s*"([^"]+)"',
    r'completed\s+tool[:\s]+([a-z_]+)',
    r'tool\s+returned[:\s]+([a-z_]+)',
]

# Patterns to find tool denials
TOOL_DENIAL_PATTERNS = [
    r'tool\s+(?:denied|blocked|rejected)[:\s]+([a-z_]+)',
    r'permission\s+denied.*?tool[:\s]+([a-z_]+)',
    r'"denied":\s*true.*?"tool":\s*"([^"]+)"',
    r'blocking\s+tool[:\s]+([a-z_]+)',
]


def extract_timestamp(line: str) -> str | None:
    """Extract ISO timestamp from log line."""
    patterns = [
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)',
        r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None


def extract_session_id(line: str) -> str | None:
    """Extract session ID from log line."""
    patterns = [
        r'"session_id":\s*"([^"]+)"',
        r'"sessionId":\s*"([^"]+)"',
        r'session[:\s]+([a-f0-9-]{8,})',
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return None


def safe_parse_json(text: str) -> dict[str, Any] | list[Any] | str:
    """Safely parse JSON, returning string on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def scan_line_for_evidence(line: str, line_num: int, source_file: str) -> list[RawEvidence]:
    """Scan a single line for any tool-related evidence."""
    evidence_list: list[RawEvidence] = []
    
    timestamp = extract_timestamp(line)
    session_id = extract_session_id(line)
    
    # Check for tool announcements
    for pattern in TOOL_ANNOUNCEMENT_PATTERNS:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            tools_str = match.group(1)
            tools = safe_parse_json(tools_str)
            evidence_list.append(RawEvidence(
                source_file=source_file,
                line_number=line_num,
                evidence_type='tool_announcement',
                raw_text=line[:500],
                extracted_data={
                    'tools': tools if isinstance(tools, list) else [],
                    'raw': tools_str
                },
                timestamp=timestamp,
                session_id=session_id,
            ))
    
    # Check for tool attempts
    for pattern in TOOL_ATTEMPT_PATTERNS:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            tool_name = match.group(1)
            evidence_list.append(RawEvidence(
                source_file=source_file,
                line_number=line_num,
                evidence_type='tool_attempt',
                raw_text=line[:500],
                extracted_data={'tool_name': tool_name},
                timestamp=timestamp,
                session_id=session_id,
            ))
    
    # Check for tool executions
    for pattern in TOOL_EXEC_PATTERNS:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            tool_name = match.group(1)
            evidence_list.append(RawEvidence(
                source_file=source_file,
                line_number=line_num,
                evidence_type='tool_exec',
                raw_text=line[:500],
                extracted_data={'tool_name': tool_name},
                timestamp=timestamp,
                session_id=session_id,
            ))
    
    # Check for tool denials
    for pattern in TOOL_DENIAL_PATTERNS:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            tool_name = match.group(1)
            evidence_list.append(RawEvidence(
                source_file=source_file,
                line_number=line_num,
                evidence_type='tool_denied',
                raw_text=line[:500],
                extracted_data={'tool_name': tool_name},
                timestamp=timestamp,
                session_id=session_id,
            ))
    
    return evidence_list


def scan_log_file(log_path: Path, session_filter: str | None = None) -> Iterator[RawEvidence]:
    """Scan a log file for all tool-related evidence."""
    try:
        content = log_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print(f"  Warning: Failed to read {log_path}: {e}")
        return
    
    for line_num, line in enumerate(content.splitlines(), 1):
        # Apply session filter if specified
        if session_filter and session_filter not in line:
            continue
        
        for evidence in scan_line_for_evidence(line, line_num, str(log_path)):
            yield evidence


def scan_all_logs(
    session_filter: str | None = None,
    log_limit: int = 30
) -> list[RawEvidence]:
    """Scan all Copilot logs for evidence."""
    all_evidence: list[RawEvidence] = []
    
    for log_source in find_copilot_logs(limit=log_limit):
        for evidence in scan_log_file(log_source.path, session_filter):
            all_evidence.append(evidence)
    
    # Sort by timestamp
    all_evidence.sort(key=lambda e: e.timestamp or '')
    
    return all_evidence


@dataclass
class ForensicScanReport:
    """Complete scan report."""
    scan_timestamp: str
    session_filter: str | None
    log_files_scanned: int
    
    # Evidence counts
    total_evidence: int
    tool_announcements: int
    tool_attempts: int
    tool_executions: int
    tool_denials: int
    
    # Extracted data
    announced_tools: set[str]
    attempted_tools: set[str]
    executed_tools: set[str]
    denied_tools: set[str]
    
    # Raw evidence
    evidence: list[RawEvidence]
    
    # F-045 compliance indicators
    tools_available_was_empty: bool
    no_sdk_tools_executed: bool


def analyze_evidence(evidence_list: list[RawEvidence]) -> ForensicScanReport:
    """Analyze collected evidence."""
    announcements = [e for e in evidence_list if e.evidence_type == 'tool_announcement']
    attempts = [e for e in evidence_list if e.evidence_type == 'tool_attempt']
    executions = [e for e in evidence_list if e.evidence_type == 'tool_exec']
    denials = [e for e in evidence_list if e.evidence_type == 'tool_denied']
    
    # Extract unique tools from each category
    announced: set[str] = set()
    for e in announcements:
        tools = e.extracted_data.get('tools', [])
        if isinstance(tools, list):
            announced.update(tools)
    
    attempted: set[str] = {e.extracted_data.get('tool_name', '') for e in attempts}
    executed: set[str] = {e.extracted_data.get('tool_name', '') for e in executions}
    denied: set[str] = {e.extracted_data.get('tool_name', '') for e in denials}
    
    # Check F-045 compliance
    tools_empty = len(announced) == 0
    
    # Import known tools for comparison
    from hidden_tool_prober import get_all_tool_names
    known_sdk_tools = get_all_tool_names()
    sdk_tools_executed = executed & known_sdk_tools
    
    return ForensicScanReport(
        scan_timestamp=datetime.now().isoformat(),
        session_filter=None,  # Set by caller
        log_files_scanned=len(set(e.source_file for e in evidence_list)),
        total_evidence=len(evidence_list),
        tool_announcements=len(announcements),
        tool_attempts=len(attempts),
        tool_executions=len(executions),
        tool_denials=len(denials),
        announced_tools=announced,
        attempted_tools=attempted,
        executed_tools=executed,
        denied_tools=denied,
        evidence=evidence_list,
        tools_available_was_empty=tools_empty,
        no_sdk_tools_executed=len(sdk_tools_executed) == 0,
    )


def generate_scan_report_markdown(report: ForensicScanReport) -> str:
    """Generate markdown report from scan."""
    lines = [
        "# Deep Log Scanner - Forensic Evidence Report",
        "",
        f"**Scan Time:** {report.scan_timestamp}",
        f"**Session Filter:** `{report.session_filter or 'None (all logs)'}`",
        f"**Log Files Scanned:** {report.log_files_scanned}",
        "",
        "---",
        "",
        "## Evidence Summary",
        "",
        "| Category | Count |",
        "|----------|-------|",
        f"| Tool Announcements | {report.tool_announcements} |",
        f"| Tool Attempts | {report.tool_attempts} |",
        f"| Tool Executions | {report.tool_executions} |",
        f"| Tool Denials | {report.tool_denials} |",
        f"| **Total Evidence** | **{report.total_evidence}** |",
        "",
        "---",
        "",
        "## F-045 Compliance Check",
        "",
    ]
    
    # Compliance status
    if report.tools_available_was_empty and report.no_sdk_tools_executed:
        lines.extend([
            "### [PASS] F-045 COMPLIANT",
            "",
            "- [x] `tools_available` was empty",
            "- [x] No SDK tools were executed",
            "",
        ])
    else:
        lines.extend([
            "### [FAIL] F-045 VIOLATION DETECTED",
            "",
        ])
        if not report.tools_available_was_empty:
            lines.append(f"- [ ] `tools_available` was NOT empty: {report.announced_tools}")
        if not report.no_sdk_tools_executed:
            lines.append(f"- [ ] SDK tools WERE executed: {report.executed_tools}")
        lines.append("")
    
    # Tools breakdown
    lines.extend([
        "---",
        "",
        "## Tools Detected",
        "",
        "### Announced Tools",
        f"Count: {len(report.announced_tools)}",
        "",
    ])
    if report.announced_tools:
        for tool in sorted(report.announced_tools):
            lines.append(f"- `{tool}`")
    else:
        lines.append("*None - tools_available was empty (good)*")
    
    lines.extend([
        "",
        "### Attempted Tools",
        f"Count: {len(report.attempted_tools)}",
        "",
    ])
    if report.attempted_tools:
        for tool in sorted(report.attempted_tools):
            lines.append(f"- `{tool}`")
    else:
        lines.append("*None - no tool invocation attempts*")
    
    lines.extend([
        "",
        "### Executed Tools",
        f"Count: {len(report.executed_tools)}",
        "",
    ])
    if report.executed_tools:
        for tool in sorted(report.executed_tools):
            lines.append(f"- `{tool}` [CONCERN]")
    else:
        lines.append("*None - no tools executed (good for F-045)*")
    
    lines.extend([
        "",
        "### Denied/Blocked Tools",
        f"Count: {len(report.denied_tools)}",
        "",
    ])
    if report.denied_tools:
        for tool in sorted(report.denied_tools):
            lines.append(f"- `{tool}` [Expected - deny hook working]")
    else:
        lines.append("*None - no denials recorded (normal if no attempts)*")
    
    # Raw evidence samples
    lines.extend([
        "",
        "---",
        "",
        "## Evidence Samples (First 10)",
        "",
    ])
    
    for i, ev in enumerate(report.evidence[:10], 1):
        lines.extend([
            f"### Evidence #{i}",
            f"- **Type:** {ev.evidence_type}",
            f"- **File:** `{Path(ev.source_file).name}:{ev.line_number}`",
            f"- **Data:** `{json.dumps(ev.extracted_data)}`",
            f"- **Raw:** `{ev.raw_text[:100]}...`",
            "",
        ])
    
    if len(report.evidence) > 10:
        lines.append(f"*... and {len(report.evidence) - 10} more evidence items*")
    
    lines.extend([
        "",
        "---",
        "*Generated by deep_log_scanner.py*",
    ])
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deep Log Scanner - Forensic Evidence Extraction',
    )
    parser.add_argument('--session', metavar='ID', help='Filter by session ID')
    parser.add_argument('--recent', type=int, default=30, help='Scan N most recent logs')
    parser.add_argument('--export', metavar='FILE', help='Export raw evidence to JSON')
    parser.add_argument('--output', '-o', metavar='FILE', help='Write report to file')
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print("DEEP LOG SCANNER - Forensic Evidence Extraction")
    print(f"{'='*70}")
    
    # Scan logs
    print(f"\nScanning logs (limit: {args.recent})...")
    evidence = scan_all_logs(
        session_filter=args.session,
        log_limit=args.recent,
    )
    
    print(f"Found {len(evidence)} evidence items")
    
    # Analyze
    print("\nAnalyzing evidence...")
    report = analyze_evidence(evidence)
    report.session_filter = args.session
    
    # Export raw evidence if requested
    if args.export:
        export_data = [
            {
                'source_file': e.source_file,
                'line_number': e.line_number,
                'evidence_type': e.evidence_type,
                'extracted_data': e.extracted_data,
                'timestamp': e.timestamp,
                'session_id': e.session_id,
            }
            for e in evidence
        ]
        Path(args.export).write_text(json.dumps(export_data, indent=2), encoding='utf-8')
        print(f"Raw evidence exported to: {args.export}")
    
    # Generate report
    md_report = generate_scan_report_markdown(report)
    
    if args.output:
        Path(args.output).write_text(md_report, encoding='utf-8')
        print(f"Report written to: {args.output}")
    else:
        print(md_report)
    
    # Summary
    print(f"\n{'='*70}")
    print("SCAN COMPLETE")
    print(f"{'='*70}")
    print(f"Evidence Found: {report.total_evidence}")
    print(f"Tools Announced: {len(report.announced_tools)}")
    print(f"Tools Executed: {len(report.executed_tools)}")
    print(f"F-045 Status: {'[PASS] COMPLIANT' if report.no_sdk_tools_executed and report.tools_available_was_empty else '[FAIL] INVESTIGATE'}")
    print(f"{'='*70}")
    
    sys.exit(0 if report.no_sdk_tools_executed else 1)


if __name__ == "__main__":
    main()
