#!/usr/bin/env python3
"""
Evidence Collector - Analyze test sessions and produce forensic evidence.

This script analyzes logs from test sessions to produce evidence-based
findings about Amplifier tool behavior.

Usage:
    # List recent sessions
    python evidence_collector.py --list
    
    # Analyze specific session
    python evidence_collector.py <session_id>
    
    # Analyze most recent session
    python evidence_collector.py --latest
    
    # Output to file
    python evidence_collector.py --latest --output evidence.md
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from log_paths import find_copilot_logs, get_copilot_log_dir
from log_collector import collect_logs_for_session, read_log_file_raw
from tool_analyzer import find_tool_calls_for_session, analyze_tool_flow


@dataclass
class SessionEvidence:
    """Evidence collected from a session."""
    session_id: str
    timestamp: str
    log_file: str = ""
    model: str = ""
    duration_seconds: float = 0.0
    
    # Tool metrics
    tool_calls_total: int = 0
    tool_calls_by_name: dict[str, int] = field(default_factory=dict)
    sdk_tools_fired: int = 0
    amplifier_tools_fired: int = 0
    
    # Compliance
    f045_compliant: bool = True  # No SDK tools fired
    
    # Raw evidence
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tool_timeline: list[dict] = field(default_factory=list)


def find_recent_sessions(limit: int = 10) -> list[dict]:
    """Find recent session IDs from logs."""
    sessions = []
    seen_ids = set()
    
    for log_source in find_copilot_logs(limit=20):
        try:
            content = log_source.path.read_text(encoding='utf-8', errors='replace')
            
            # Find session IDs
            pattern = r'"session_id":\s*"([a-f0-9-]{36})"'
            for match in re.finditer(pattern, content, re.IGNORECASE):
                session_id = match.group(1)
                if session_id not in seen_ids:
                    seen_ids.add(session_id)
                    
                    # Try to extract timestamp
                    context_start = max(0, match.start() - 200)
                    context = content[context_start:match.end() + 100]
                    ts_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', context)
                    
                    sessions.append({
                        'session_id': session_id,
                        'timestamp': ts_match.group(1) if ts_match else 'unknown',
                        'log_file': log_source.path.name
                    })
                    
                    if len(sessions) >= limit:
                        return sessions
                        
        except Exception as e:
            print(f"Warning: Failed to read {log_source.path}: {e}")
    
    return sessions


def collect_evidence(session_id: str) -> SessionEvidence:
    """Collect comprehensive evidence for a session."""
    evidence = SessionEvidence(
        session_id=session_id,
        timestamp=datetime.now().isoformat()
    )
    
    print(f"\n{'='*60}")
    print(f"EVIDENCE COLLECTION: {session_id[:8]}...")
    print(f"{'='*60}")
    
    # Find the log file containing this session
    for log_source in find_copilot_logs(limit=30):
        content = read_log_file_raw(log_source.path)
        if session_id in content:
            evidence.log_file = str(log_source.path)
            print(f"[+] Log file: {log_source.path.name}")
            
            # Extract model
            model_match = re.search(r'"model":\s*"([^"]+)"', content)
            if model_match:
                evidence.model = model_match.group(1)
                print(f"[+] Model: {evidence.model}")
            
            # Extract errors
            for match in re.finditer(r'\[ERROR\]\s*(.+)', content):
                if session_id in content[max(0, match.start()-200):match.end()]:
                    error = match.group(1)[:200]
                    evidence.errors.append(error)
            
            if evidence.errors:
                print(f"[!] Errors found: {len(evidence.errors)}")
            
            # Extract warnings
            for match in re.finditer(r'\[WARNING\]\s*(.+)', content):
                if session_id in content[max(0, match.start()-200):match.end()]:
                    warning = match.group(1)[:200]
                    evidence.warnings.append(warning)
            
            if evidence.warnings:
                print(f"[!] Warnings found: {len(evidence.warnings)}")
            
            break
    else:
        print("[!] Session not found in any log file")
        return evidence
    
    # Tool call analysis
    print(f"\n[Analyzing tool calls...]")
    calls = find_tool_calls_for_session(session_id, log_limit=10)
    analysis = analyze_tool_flow(calls)
    
    evidence.tool_calls_total = analysis.get('total_calls', 0)
    evidence.tool_calls_by_name = analysis.get('by_tool', {})
    evidence.sdk_tools_fired = len(analysis.get('sdk_tools_fired', []))
    evidence.amplifier_tools_fired = len(analysis.get('amplifier_tools_fired', []))
    evidence.tool_timeline = analysis.get('timeline', [])
    
    print(f"[+] Total tool-related events: {evidence.tool_calls_total}")
    print(f"[+] SDK tools fired: {evidence.sdk_tools_fired}")
    print(f"[+] Amplifier tools fired: {evidence.amplifier_tools_fired}")
    
    # F-045 compliance
    evidence.f045_compliant = evidence.sdk_tools_fired == 0
    if evidence.f045_compliant:
        print(f"[OK] F-045 COMPLIANT: No SDK built-in tools fired")
    else:
        print(f"[FAIL] F-045 VIOLATION: {evidence.sdk_tools_fired} SDK tools fired!")
    
    return evidence


def generate_evidence_report(evidence: SessionEvidence) -> str:
    """Generate markdown evidence report."""
    lines = [
        "# Forensic Evidence Report",
        "",
        f"> **Session ID:** `{evidence.session_id}`",
        f"> **Collected:** {evidence.timestamp}",
        f"> **Log File:** `{evidence.log_file or 'N/A'}`",
        f"> **Model:** {evidence.model or 'N/A'}",
        "",
        "## F-045 Compliance (SDK Tool Suppression)",
        "",
    ]
    
    if evidence.f045_compliant:
        lines.extend([
            "**Status:** [PASS] COMPLIANT",
            "",
            "No SDK built-in tools were invoked. All tool execution flowed through",
            "the Amplifier orchestration layer as expected.",
            "",
        ])
    else:
        lines.extend([
            "**Status:** [FAIL] VIOLATION DETECTED",
            "",
            f"**SDK Tools Fired:** {evidence.sdk_tools_fired}",
            "",
            "The following SDK built-in tools were invoked directly, bypassing",
            "Amplifier orchestration:",
            "",
        ])
    
    # Tool metrics
    lines.extend([
        "## Tool Call Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total tool events | {evidence.tool_calls_total} |",
        f"| SDK tools fired | {evidence.sdk_tools_fired} |",
        f"| Amplifier tools fired | {evidence.amplifier_tools_fired} |",
        "",
    ])
    
    if evidence.tool_calls_by_name:
        lines.extend([
            "### Tool Breakdown",
            "",
            "| Tool | Count |",
            "|------|-------|",
        ])
        for tool, count in sorted(evidence.tool_calls_by_name.items()):
            lines.append(f"| {tool} | {count} |")
        lines.append("")
    
    # Timeline
    if evidence.tool_timeline:
        lines.extend([
            "### Tool Timeline (First 10)",
            "",
            "| Time | Tool | Source | Status |",
            "|------|------|--------|--------|",
        ])
        for entry in evidence.tool_timeline[:10]:
            time_str = entry.get('time', '???')
            if len(time_str) > 20:
                time_str = time_str[:20]
            lines.append(f"| {time_str} | {entry.get('tool', '?')} | {entry.get('source', '?')} | {entry.get('status', '?')} |")
        lines.append("")
    
    # Errors
    if evidence.errors:
        lines.extend([
            "## Errors Detected",
            "",
        ])
        for i, error in enumerate(evidence.errors[:5], 1):
            lines.extend([
                f"### Error {i}",
                "```",
                error,
                "```",
                "",
            ])
    
    # Warnings
    if evidence.warnings:
        lines.extend([
            "## Warnings Detected",
            "",
        ])
        for i, warning in enumerate(evidence.warnings[:5], 1):
            lines.extend([
                f"### Warning {i}",
                "```",
                warning,
                "```",
                "",
            ])
    
    # Raw evidence
    lines.extend([
        "## Raw Evidence (JSON)",
        "",
        "```json",
        json.dumps({
            'session_id': evidence.session_id,
            'timestamp': evidence.timestamp,
            'log_file': evidence.log_file,
            'model': evidence.model,
            'tool_calls_total': evidence.tool_calls_total,
            'tool_calls_by_name': evidence.tool_calls_by_name,
            'sdk_tools_fired': evidence.sdk_tools_fired,
            'f045_compliant': evidence.f045_compliant,
            'error_count': len(evidence.errors),
            'warning_count': len(evidence.warnings),
        }, indent=2),
        "```",
        "",
        "---",
        "*Evidence collected by forensic analysis tooling*",
    ])
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Evidence Collector')
    parser.add_argument('session_id', nargs='?', help='Session ID to analyze')
    parser.add_argument('--list', action='store_true', help='List recent sessions')
    parser.add_argument('--latest', action='store_true', help='Analyze most recent session')
    parser.add_argument('--output', '-o', help='Write report to file')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of markdown')
    
    args = parser.parse_args()
    
    if args.list:
        print("\nRecent Sessions:")
        print("-" * 60)
        sessions = find_recent_sessions(10)
        for i, s in enumerate(sessions, 1):
            print(f"{i}. {s['session_id'][:12]}... | {s['timestamp']} | {s['log_file']}")
        print("-" * 60)
        print(f"Total: {len(sessions)} sessions found")
        return
    
    # Determine which session to analyze
    if args.latest:
        sessions = find_recent_sessions(1)
        if not sessions:
            print("No sessions found in logs")
            sys.exit(1)
        session_id = sessions[0]['session_id']
        print(f"Analyzing most recent session: {session_id}")
    elif args.session_id:
        session_id = args.session_id
    else:
        parser.print_help()
        sys.exit(1)
    
    # Collect evidence
    evidence = collect_evidence(session_id)
    
    # Generate report
    if args.json:
        output = json.dumps({
            'session_id': evidence.session_id,
            'timestamp': evidence.timestamp,
            'log_file': evidence.log_file,
            'model': evidence.model,
            'tool_calls_total': evidence.tool_calls_total,
            'tool_calls_by_name': evidence.tool_calls_by_name,
            'sdk_tools_fired': evidence.sdk_tools_fired,
            'f045_compliant': evidence.f045_compliant,
            'errors': evidence.errors,
            'warnings': evidence.warnings,
            'tool_timeline': evidence.tool_timeline,
        }, indent=2)
        
        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f"\nJSON written to: {args.output}")
        else:
            print(output)
    else:
        report = generate_evidence_report(evidence)
        
        if args.output:
            Path(args.output).write_text(report, encoding='utf-8')
            print(f"\nReport written to: {args.output}")
        else:
            print("\n" + report)
    
    # Summary
    print(f"\n{'='*60}")
    print("EVIDENCE COLLECTION COMPLETE")
    print(f"{'='*60}")
    print(f"Session: {session_id[:12]}...")
    print(f"F-045 Status: {'[PASS] COMPLIANT' if evidence.f045_compliant else '[FAIL] VIOLATION'}")
    print(f"Tool Events: {evidence.tool_calls_total}")
    print(f"Errors: {len(evidence.errors)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
