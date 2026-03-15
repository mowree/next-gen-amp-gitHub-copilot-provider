#!/usr/bin/env python3
"""
Tool Forensic Tester - Evidence-Based Tool Testing

Runs structured tests against Amplifier tools and produces
forensic evidence for each test case.

Usage:
    python tool_tester.py                    # Run all tests
    python tool_tester.py --tool bash        # Test specific tool
    python tool_tester.py --quick            # Quick smoke test
    python tool_tester.py --output report.md # Write report
"""

import argparse
import json
import os
import subprocess
import sys
import time
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from log_paths import find_copilot_logs, get_copilot_log_dir
from tool_analyzer import find_tool_calls_for_session, analyze_tool_flow


@dataclass
class TestCase:
    """A single tool test case."""
    tool_name: str
    description: str
    prompt: str
    expected_behavior: str
    timeout_seconds: int = 60


@dataclass
class TestResult:
    """Result of a tool test."""
    test_case: TestCase
    status: str  # 'pass', 'fail', 'error', 'timeout'
    session_id: str = ""
    output: str = ""
    error: str = ""
    duration_seconds: float = 0.0
    tool_calls_detected: int = 0
    sdk_tools_fired: int = 0
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


# Define test cases for each Amplifier tool
TOOL_TEST_CASES = [
    TestCase(
        tool_name="bash",
        description="Execute shell command",
        prompt="Run: echo 'FORENSIC_TEST_MARKER_BASH'",
        expected_behavior="Should execute bash and return the marker string",
        timeout_seconds=30
    ),
    TestCase(
        tool_name="read_file",
        description="Read file contents",
        prompt="Read the first 5 lines of pyproject.toml",
        expected_behavior="Should read and display file contents",
        timeout_seconds=30
    ),
    TestCase(
        tool_name="glob",
        description="Find files by pattern",
        prompt="List all .py files in the tests/ directory",
        expected_behavior="Should return list of Python test files",
        timeout_seconds=30
    ),
    TestCase(
        tool_name="grep",
        description="Search text in files",
        prompt="Search for 'def test_' in tests/test_provider.py",
        expected_behavior="Should find test function definitions",
        timeout_seconds=30
    ),
    TestCase(
        tool_name="web_fetch",
        description="Fetch web content",
        prompt="Fetch https://httpbin.org/get and show the response headers",
        expected_behavior="Should retrieve and display HTTP headers",
        timeout_seconds=45
    ),
]

# Quick smoke test - just bash
QUICK_TEST_CASES = [
    TestCase(
        tool_name="bash",
        description="Quick smoke test",
        prompt="Run: echo 'SMOKE_TEST_OK' && exit 0",
        expected_behavior="Should execute and return OK",
        timeout_seconds=45  # Give amplifier time to start
    ),
]


def find_latest_log_after(timestamp: datetime) -> Path | None:
    """Find the newest log file created after timestamp."""
    for log_source in find_copilot_logs(limit=5):
        mtime = datetime.fromtimestamp(log_source.path.stat().st_mtime)
        if mtime >= timestamp:
            return log_source.path
    return None


def extract_session_id_from_log(log_path: Path, start_time: datetime) -> str | None:
    """Extract session ID from log file."""
    try:
        content = log_path.read_text(encoding='utf-8', errors='replace')
        
        # Look for session creation after start_time
        # Pattern: "session_id": "uuid..."
        pattern = r'"session_id":\s*"([a-f0-9-]{36})"'
        
        for match in re.finditer(pattern, content, re.IGNORECASE):
            session_id = match.group(1)
            # Check if this session was created after start_time
            # Look for timestamp near the match
            context_start = max(0, match.start() - 200)
            context = content[context_start:match.end() + 100]
            
            ts_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'
            ts_match = re.search(ts_pattern, context)
            if ts_match:
                try:
                    log_ts = datetime.fromisoformat(ts_match.group(1))
                    if log_ts >= start_time:
                        return session_id
                except ValueError:
                    pass
        
        # Fallback: return first session ID found
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1)
            
    except Exception as e:
        print(f"  Warning: Failed to extract session ID: {e}")
    
    return None


def run_amplifier_test(test_case: TestCase) -> TestResult:
    """Run a single test case through Amplifier."""
    start_time = datetime.now()
    result = TestResult(
        test_case=test_case,
        status="error",
        timestamp=start_time.isoformat()
    )
    
    print(f"\n{'='*60}")
    print(f"TEST: {test_case.tool_name} - {test_case.description}")
    print(f"{'='*60}")
    print(f"Prompt: {test_case.prompt[:80]}...")
    
    try:
        # Run amplifier with the test prompt
        cmd = ['amplifier', 'run', test_case.prompt]
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=test_case.timeout_seconds,
            cwd=Path(__file__).parent.parent,  # Run from repo root
            env={**os.environ, 'NO_COLOR': '1'}  # Disable colors for clean output
        )
        
        result.output = process.stdout
        result.error = process.stderr
        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        
        # Check for success markers
        if process.returncode == 0:
            result.status = "pass"
        else:
            result.status = "fail"
            
        print(f"  Duration: {result.duration_seconds:.2f}s")
        print(f"  Exit code: {process.returncode}")
        print(f"  Output preview: {result.output[:200]}..." if len(result.output) > 200 else f"  Output: {result.output}")
        
    except subprocess.TimeoutExpired:
        result.status = "timeout"
        result.duration_seconds = test_case.timeout_seconds
        print(f"  TIMEOUT after {test_case.timeout_seconds}s")
        
    except Exception as e:
        result.status = "error"
        result.error = str(e)
        print(f"  ERROR: {e}")
    
    # Forensic analysis: find session and analyze
    print("\n  [Forensic Analysis]")
    
    # Wait a moment for logs to flush
    time.sleep(0.5)
    
    # Find latest log
    log_path = find_latest_log_after(start_time)
    if log_path:
        print(f"  Log file: {log_path.name}")
        
        # Extract session ID
        session_id = extract_session_id_from_log(log_path, start_time)
        if session_id:
            result.session_id = session_id
            print(f"  Session ID: {session_id[:8]}...")
            
            # Analyze tool calls
            calls = find_tool_calls_for_session(session_id, log_limit=3)
            analysis = analyze_tool_flow(calls)
            
            result.tool_calls_detected = analysis.get('total_calls', 0)
            result.sdk_tools_fired = len(analysis.get('sdk_tools_fired', []))
            result.evidence = {
                'session_id': session_id,
                'log_file': str(log_path),
                'tool_analysis': {
                    'total_calls': analysis.get('total_calls', 0),
                    'by_tool': analysis.get('by_tool', {}),
                    'sdk_tools_fired': result.sdk_tools_fired
                }
            }
            
            print(f"  Tool calls detected: {result.tool_calls_detected}")
            print(f"  SDK tools fired: {result.sdk_tools_fired}")
            
            # F-045 check
            if result.sdk_tools_fired > 0:
                print("  ⚠️  WARNING: SDK built-in tools fired!")
            else:
                print("  ✅ F-045 OK: No SDK built-in tools fired")
        else:
            print("  ⚠️  Could not extract session ID")
    else:
        print("  ⚠️  No log file found")
    
    return result


def generate_report(results: list[TestResult], output_path: Path | None = None) -> str:
    """Generate markdown report from test results."""
    lines = [
        "# Amplifier Tool Forensic Test Report",
        "",
        f"> **Generated:** {datetime.now().isoformat()}",
        f"> **Tests Run:** {len(results)}",
        "",
        "## Summary",
        "",
        f"| Status | Count |",
        f"|--------|-------|",
    ]
    
    # Count by status
    status_counts = {}
    for r in results:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
    
    # Use ASCII alternatives for Windows compatibility
    status_emoji = {'pass': '[PASS]', 'fail': '[FAIL]', 'error': '[ERR]', 'timeout': '[TIME]'}
    for status, count in status_counts.items():
        emoji = status_emoji.get(status, '?')
        lines.append(f"| {emoji} {status} | {count} |")
    
    # F-045 compliance
    total_sdk_fired = sum(r.sdk_tools_fired for r in results)
    lines.extend([
        "",
        "## F-045 Compliance",
        "",
        f"**SDK Built-in Tools Fired:** {total_sdk_fired}",
        "",
        "[OK] COMPLIANT" if total_sdk_fired == 0 else "[FAIL] NON-COMPLIANT",
        "",
    ])
    
    # Individual results
    lines.extend([
        "## Test Results",
        "",
        "| Tool | Status | Duration | Tool Calls | Session |",
        "|------|--------|----------|------------|---------|",
    ])
    
    # Use ASCII for Windows compatibility
    status_emoji = {'pass': '[PASS]', 'fail': '[FAIL]', 'error': '[ERR]', 'timeout': '[TIME]'}
    
    for r in results:
        emoji = status_emoji.get(r.status, '?')
        session_short = r.session_id[:8] + "..." if r.session_id else "N/A"
        lines.append(f"| {r.test_case.tool_name} | {emoji} {r.status} | {r.duration_seconds:.1f}s | {r.tool_calls_detected} | {session_short} |")
    
    # Detailed results
    lines.extend([
        "",
        "## Detailed Results",
        "",
    ])
    
    for r in results:
        emoji = status_emoji.get(r.status, '?')
        lines.extend([
            f"### {emoji} {r.test_case.tool_name}",
            "",
            f"**Description:** {r.test_case.description}",
            f"**Status:** {r.status}",
            f"**Duration:** {r.duration_seconds:.2f}s",
            f"**Session:** `{r.session_id or 'N/A'}`",
            "",
            "**Prompt:**",
            "```",
            r.test_case.prompt,
            "```",
            "",
        ])
        
        if r.output:
            lines.extend([
                "**Output:**",
                "```",
                r.output[:500] + ("..." if len(r.output) > 500 else ""),
                "```",
                "",
            ])
        
        if r.error:
            lines.extend([
                "**Errors:**",
                "```",
                r.error[:500] + ("..." if len(r.error) > 500 else ""),
                "```",
                "",
            ])
        
        if r.evidence:
            lines.extend([
                "**Evidence:**",
                "```json",
                json.dumps(r.evidence, indent=2, default=str),
                "```",
                "",
            ])
    
    report = "\n".join(lines)
    
    if output_path:
        output_path.write_text(report, encoding='utf-8')
        print(f"\nReport written to: {output_path}")
    
    return report


def main():
    parser = argparse.ArgumentParser(description='Tool Forensic Tester')
    parser.add_argument('--tool', help='Test specific tool only')
    parser.add_argument('--quick', action='store_true', help='Quick smoke test only')
    parser.add_argument('--output', '-o', help='Write report to file')
    parser.add_argument('--json', action='store_true', help='Output JSON instead of markdown')
    
    args = parser.parse_args()
    
    # Select test cases
    if args.quick:
        test_cases = QUICK_TEST_CASES
    elif args.tool:
        test_cases = [tc for tc in TOOL_TEST_CASES if tc.tool_name == args.tool]
        if not test_cases:
            print(f"Unknown tool: {args.tool}")
            print(f"Available: {', '.join(tc.tool_name for tc in TOOL_TEST_CASES)}")
            sys.exit(1)
    else:
        test_cases = TOOL_TEST_CASES
    
    print(f"\n{'#'*60}")
    print(f"# AMPLIFIER TOOL FORENSIC TESTER")
    print(f"# Tests: {len(test_cases)}")
    print(f"{'#'*60}")
    
    # Run tests
    results = []
    for tc in test_cases:
        result = run_amplifier_test(tc)
        results.append(result)
    
    # Generate report
    print(f"\n{'='*60}")
    print("GENERATING REPORT")
    print(f"{'='*60}")
    
    output_path = Path(args.output) if args.output else None
    
    if args.json:
        output = json.dumps([{
            'tool': r.test_case.tool_name,
            'status': r.status,
            'duration': r.duration_seconds,
            'session_id': r.session_id,
            'tool_calls': r.tool_calls_detected,
            'sdk_tools_fired': r.sdk_tools_fired,
            'evidence': r.evidence
        } for r in results], indent=2)
        
        if output_path:
            output_path.write_text(output, encoding='utf-8')
        print(output)
    else:
        report = generate_report(results, output_path)
        if not output_path:
            print(report)
    
    # Summary
    passed = sum(1 for r in results if r.status == 'pass')
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{total} tests passed")
    print(f"{'='*60}")
    
    # Exit with appropriate code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
