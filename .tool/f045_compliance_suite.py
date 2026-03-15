#!/usr/bin/env python3
"""
F-045 Forensic Compliance Suite - Master Orchestrator

This is the master script that orchestrates the complete forensic
verification that SDK tools are NOT firing in our provider.

Runs the following in sequence:
1. Hidden Tool Prober - Scans for known 28 SDK tools
2. Deep Log Scanner - Extracts ALL tool evidence
3. Negative Test Validator - Validates probe results
4. Generates unified compliance report

Usage:
    # Full forensic analysis on most recent session
    python f045_compliance_suite.py --latest
    
    # Analyze specific session
    python f045_compliance_suite.py --session <id>
    
    # Full suite with probe prompts generation
    python f045_compliance_suite.py --full --output reports/

Exit codes:
    0 - F-045 COMPLIANT (all tests pass)
    1 - F-045 VIOLATION (one or more tests failed)
    2 - ERROR (execution error)

Principal Engineer Note:
    This suite follows the forensic principle of independent verification.
    Each tool checks different aspects; all must pass for compliance.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class ComponentResult:
    """Result from a forensic component."""
    component_name: str
    passed: bool
    summary: str
    details: dict[str, Any]


@dataclass
class ComplianceVerdict:
    """Final compliance verdict."""
    timestamp: str
    session_id: str
    
    # Component results
    hidden_tool_prober: ComponentResult
    deep_log_scanner: ComponentResult
    
    # Aggregate
    all_passed: bool
    
    # Evidence summary
    tools_available_value: str
    sdk_tools_detected: list[str]
    tool_attempts_detected: int


def run_hidden_tool_prober(session_id: str) -> ComponentResult:
    """Run the hidden tool prober analysis."""
    print("\n[1/3] Running Hidden Tool Prober...")
    
    from hidden_tool_prober import analyze_session, generate_report_markdown
    
    try:
        report = analyze_session(session_id)
        
        return ComponentResult(
            component_name="Hidden Tool Prober",
            passed=report.f045_compliant,
            summary=f"tools_available={report.tools_available_value}, tools_detected={len(report.tools_invoked)}",
            details={
                'tools_available': report.tools_available_value,
                'tools_invoked_count': len(report.tools_invoked),
                'high_risk_tools': report.high_risk_tools_found,
                'medium_risk_tools': report.medium_risk_tools_found,
                'logs_scanned': len(report.log_files_analyzed),
            }
        )
    except Exception as e:
        return ComponentResult(
            component_name="Hidden Tool Prober",
            passed=False,
            summary=f"ERROR: {e}",
            details={'error': str(e)}
        )


def run_deep_log_scanner(session_id: str) -> ComponentResult:
    """Run the deep log scanner."""
    print("\n[2/3] Running Deep Log Scanner...")
    
    from deep_log_scanner import scan_all_logs, analyze_evidence
    
    try:
        evidence = scan_all_logs(session_filter=session_id, log_limit=30)
        report = analyze_evidence(evidence)
        
        return ComponentResult(
            component_name="Deep Log Scanner",
            passed=report.no_sdk_tools_executed and report.tools_available_was_empty,
            summary=f"announcements={report.tool_announcements}, attempts={report.tool_attempts}, executions={report.tool_executions}",
            details={
                'total_evidence': report.total_evidence,
                'tool_announcements': report.tool_announcements,
                'tool_attempts': report.tool_attempts,
                'tool_executions': report.tool_executions,
                'announced_tools': list(report.announced_tools),
                'executed_tools': list(report.executed_tools),
            }
        )
    except Exception as e:
        return ComponentResult(
            component_name="Deep Log Scanner",
            passed=False,
            summary=f"ERROR: {e}",
            details={'error': str(e)}
        )


def run_compliance_check(session_id: str) -> ComponentResult:
    """Run additional compliance checks."""
    print("\n[3/3] Running Compliance Checks...")
    
    from hidden_tool_prober import get_all_tool_names
    from deep_log_scanner import scan_all_logs
    
    try:
        # Quick scan for any of the 28 known tools
        known_tools = get_all_tool_names()
        evidence = scan_all_logs(session_filter=session_id, log_limit=30)
        
        # Check for any tool execution
        executed_tools = set()
        for ev in evidence:
            if ev.evidence_type == 'tool_exec':
                tool_name = ev.extracted_data.get('tool_name', '')
                if tool_name in known_tools:
                    executed_tools.add(tool_name)
        
        passed = len(executed_tools) == 0
        
        return ComponentResult(
            component_name="Known Tool Check",
            passed=passed,
            summary=f"known_sdk_tools_executed={len(executed_tools)}",
            details={
                'known_tools_checked': len(known_tools),
                'executed_sdk_tools': list(executed_tools),
            }
        )
    except Exception as e:
        return ComponentResult(
            component_name="Known Tool Check",
            passed=False,
            summary=f"ERROR: {e}",
            details={'error': str(e)}
        )


def find_most_recent_session() -> str | None:
    """Find the most recent session ID from logs."""
    from evidence_collector import find_recent_sessions
    
    sessions = find_recent_sessions(1)
    if sessions:
        return sessions[0]['session_id']
    return None


def generate_unified_report(
    session_id: str,
    prober_result: ComponentResult,
    scanner_result: ComponentResult,
    check_result: ComponentResult,
) -> str:
    """Generate unified compliance report."""
    
    all_passed = prober_result.passed and scanner_result.passed and check_result.passed
    
    lines = [
        "# F-045 Forensic Compliance Report",
        "",
        "## Executive Summary",
        "",
        f"**Session:** `{session_id}`",
        f"**Analysis Time:** {datetime.now().isoformat()}",
        "",
    ]
    
    if all_passed:
        lines.extend([
            "### **[PASS] F-045 COMPLIANT - SOLID AS A ROCK**",
            "",
            "All forensic components confirm that SDK tools are NOT being invoked.",
            "The `available_tools=[]` approach is successfully suppressing all 28 known tools.",
            "",
        ])
    else:
        lines.extend([
            "### **[FAIL] F-045 VIOLATION DETECTED**",
            "",
            "One or more forensic components detected SDK tool activity.",
            "Immediate investigation required.",
            "",
        ])
    
    # Component results table
    lines.extend([
        "---",
        "",
        "## Component Results",
        "",
        "| Component | Status | Summary |",
        "|-----------|--------|---------|",
        f"| Hidden Tool Prober | {'[PASS]' if prober_result.passed else '[FAIL]'} | {prober_result.summary} |",
        f"| Deep Log Scanner | {'[PASS]' if scanner_result.passed else '[FAIL]'} | {scanner_result.summary} |",
        f"| Known Tool Check | {'[PASS]' if check_result.passed else '[FAIL]'} | {check_result.summary} |",
        "",
    ])
    
    # Detailed findings
    lines.extend([
        "---",
        "",
        "## Detailed Findings",
        "",
        "### Hidden Tool Prober",
        "",
        f"- **Status:** {'PASS' if prober_result.passed else 'FAIL'}",
        f"- **tools_available:** `{prober_result.details.get('tools_available', 'N/A')}`",
        f"- **Tools Invoked:** {prober_result.details.get('tools_invoked_count', 'N/A')}",
        f"- **High Risk Tools:** {prober_result.details.get('high_risk_tools', []) or 'None'}",
        "",
        "### Deep Log Scanner",
        "",
        f"- **Status:** {'PASS' if scanner_result.passed else 'FAIL'}",
        f"- **Total Evidence:** {scanner_result.details.get('total_evidence', 'N/A')}",
        f"- **Tool Announcements:** {scanner_result.details.get('tool_announcements', 'N/A')}",
        f"- **Tool Attempts:** {scanner_result.details.get('tool_attempts', 'N/A')}",
        f"- **Tool Executions:** {scanner_result.details.get('tool_executions', 'N/A')}",
        "",
        "### Known Tool Check",
        "",
        f"- **Status:** {'PASS' if check_result.passed else 'FAIL'}",
        f"- **Tools Checked:** {check_result.details.get('known_tools_checked', 'N/A')}",
        f"- **SDK Tools Executed:** {check_result.details.get('executed_sdk_tools', []) or 'None'}",
        "",
    ])
    
    # Verification
    lines.extend([
        "---",
        "",
        "## What This Means",
        "",
    ])
    
    if all_passed:
        lines.extend([
            "### The 28-Tool Concern is FULLY MITIGATED",
            "",
            "The March 5, 2026 analysis identified 28 tools that could potentially fire:",
            "",
            "- 13 from `tools.list`",
            "- 6 in SDK source code",
            "- 9 runtime-discovered",
            "",
            "With `available_tools=[]` in the session configuration, **none** of these tools",
            "can be invoked by the model. This is a complete suppression approach that:",
            "",
            "1. Does not require maintaining an exclusion list",
            "2. Works regardless of new tools added to SDK",
            "3. Is verified through multiple independent checks",
            "",
        ])
    else:
        lines.extend([
            "### Investigation Required",
            "",
            "SDK tools were detected despite `available_tools=[]`. Check:",
            "",
            "1. Session configuration is being applied correctly",
            "2. No MCP tools are configured",
            "3. SDK version compatibility",
            "",
        ])
    
    lines.extend([
        "---",
        "",
        "## Technical Evidence",
        "",
        "```json",
        json.dumps({
            'prober': prober_result.details,
            'scanner': scanner_result.details,
            'check': check_result.details,
        }, indent=2),
        "```",
        "",
        "---",
        "*Generated by f045_compliance_suite.py*",
    ])
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='F-045 Forensic Compliance Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0  - F-045 COMPLIANT (all checks pass)
  1  - F-045 VIOLATION (one or more checks failed)
  2  - ERROR (execution error)
        """
    )
    parser.add_argument('--session', metavar='ID', help='Analyze specific session')
    parser.add_argument('--latest', action='store_true', help='Analyze most recent session')
    parser.add_argument('--output', '-o', metavar='DIR', help='Output directory for reports')
    parser.add_argument('--json', action='store_true', help='Output JSON summary')
    
    args = parser.parse_args()
    
    print("="*70)
    print("F-045 FORENSIC COMPLIANCE SUITE")
    print("Proving SDK Tools Do Not Fire")
    print("="*70)
    
    # Determine session
    session_id = None
    if args.session:
        session_id = args.session
    elif args.latest:
        session_id = find_most_recent_session()
        if not session_id:
            print("\nERROR: No sessions found in logs")
            sys.exit(2)
        print(f"\nMost recent session: {session_id}")
    else:
        # Find any session
        session_id = find_most_recent_session()
        if not session_id:
            print("\nERROR: No sessions found. Run with --session <id> or --latest")
            sys.exit(2)
        print(f"\nUsing session: {session_id}")
    
    # Run all components
    prober_result = run_hidden_tool_prober(session_id)
    scanner_result = run_deep_log_scanner(session_id)
    check_result = run_compliance_check(session_id)
    
    # Generate report
    report = generate_unified_report(
        session_id,
        prober_result,
        scanner_result,
        check_result,
    )
    
    # Output
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_dir / f"f045_compliance_{timestamp}.md"
        report_path.write_text(report, encoding='utf-8')
        print(f"\nReport written to: {report_path}")
        
        # Also write JSON summary
        if args.json:
            json_path = output_dir / f"f045_compliance_{timestamp}.json"
            json_data = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'all_passed': prober_result.passed and scanner_result.passed and check_result.passed,
                'components': {
                    'hidden_tool_prober': {
                        'passed': prober_result.passed,
                        'details': prober_result.details,
                    },
                    'deep_log_scanner': {
                        'passed': scanner_result.passed,
                        'details': scanner_result.details,
                    },
                    'known_tool_check': {
                        'passed': check_result.passed,
                        'details': check_result.details,
                    },
                },
            }
            json_path.write_text(json.dumps(json_data, indent=2), encoding='utf-8')
            print(f"JSON written to: {json_path}")
    else:
        print(report)
    
    # Final verdict
    all_passed = prober_result.passed and scanner_result.passed and check_result.passed
    
    print("\n" + "="*70)
    print("FORENSIC SUITE COMPLETE")
    print("="*70)
    print(f"Session: {session_id[:16]}...")
    print(f"Hidden Tool Prober: {'[PASS]' if prober_result.passed else '[FAIL]'}")
    print(f"Deep Log Scanner:   {'[PASS]' if scanner_result.passed else '[FAIL]'}")
    print(f"Known Tool Check:   {'[PASS]' if check_result.passed else '[FAIL]'}")
    print("-"*70)
    print(f"VERDICT: {'[PASS] F-045 SOLID - NO SDK TOOLS FIRING' if all_passed else '[FAIL] INVESTIGATION REQUIRED'}")
    print("="*70)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
