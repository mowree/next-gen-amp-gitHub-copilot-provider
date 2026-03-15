#!/usr/bin/env python3
"""
Forensic session analyzer - main entry point.

Provides 360° analysis of a session across all available logs:
- Copilot CLI/SDK logs
- Session state files
- Tool call analysis
- Error detection

Usage:
    python analyze_session.py <session_id> [--full] [--tools-only] [--errors-only]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from log_paths import (
    find_all_log_sources,
    find_copilot_logs,
    get_copilot_log_dir,
    get_copilot_session_state_dir,
)
from log_collector import collect_logs_for_session, read_log_file_raw
from tool_analyzer import find_tool_calls_for_session, analyze_tool_flow, print_tool_analysis


def find_log_containing_session(session_id: str) -> Path | None:
    """Find the log file containing a session."""
    for log_source in find_copilot_logs(limit=30):
        content = read_log_file_raw(log_source.path)
        if session_id in content:
            return log_source.path
    return None


def extract_session_block(log_path: Path, session_id: str) -> str:
    """Extract all lines related to a session from a log file."""
    content = read_log_file_raw(log_path)
    lines = content.splitlines()
    
    # Find relevant lines
    relevant = []
    in_json_block = False
    json_buffer = []
    
    for line in lines:
        if session_id in line:
            relevant.append(line)
        elif in_json_block:
            json_buffer.append(line)
            # Check if JSON block ends
            if line.strip() == '}':
                relevant.extend(json_buffer)
                json_buffer = []
                in_json_block = False
        # Start of JSON block that might contain session
        elif line.strip() == '{':
            in_json_block = True
            json_buffer = [line]
    
    return '\n'.join(relevant)


def extract_session_metadata(log_path: Path, session_id: str) -> dict:
    """Extract session metadata from log."""
    content = read_log_file_raw(log_path)
    metadata = {
        'session_id': session_id,
        'log_file': str(log_path),
        'created_at': None,
        'destroyed_at': None,
        'model': None,
        'features': {},
        'client_info': {},
        'turn_count': None,
        'errors': [],
    }
    
    # Find session creation
    create_match = re.search(rf'"session_id":\s*"{session_id}".*?"created_at":\s*"([^"]+)"', content, re.DOTALL)
    if create_match:
        metadata['created_at'] = create_match.group(1)
    
    # Find session destruction
    destroy_pattern = rf'Destroyed session:\s*{session_id}'
    destroy_match = re.search(destroy_pattern, content)
    if destroy_match:
        # Look for timestamp on same line or nearby
        line_start = content.rfind('\n', 0, destroy_match.start()) + 1
        line = content[line_start:destroy_match.end() + 50]
        ts_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)', line)
        if ts_match:
            metadata['destroyed_at'] = ts_match.group(1)
    
    # Find model
    model_match = re.search(r'"model":\s*"([^"]+)"', content)
    if model_match:
        metadata['model'] = model_match.group(1)
    
    # Find turn count
    turn_match = re.search(rf'{session_id}.*?"turn_count":\s*(\d+)', content, re.DOTALL)
    if turn_match:
        metadata['turn_count'] = int(turn_match.group(1))
    
    # Find errors
    for match in re.finditer(r'\[ERROR\]\s*(.+)', content):
        if session_id in content[max(0, match.start()-200):match.end()]:
            metadata['errors'].append(match.group(1)[:200])
    
    # Find warnings
    for match in re.finditer(r'\[WARNING\]\s*(.+)', content):
        if session_id in content[max(0, match.start()-200):match.end()]:
            metadata['errors'].append(f"WARNING: {match.group(1)[:200]}")
    
    return metadata


def analyze_session_360(session_id: str, verbose: bool = False) -> dict:
    """Perform 360° analysis of a session."""
    analysis = {
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'log_source': None,
        'metadata': {},
        'tool_analysis': {},
        'raw_entries': [],
        'summary': {}
    }
    
    print(f"\n{'='*60}")
    print(f"FORENSIC ANALYSIS: {session_id}")
    print(f"{'='*60}")
    
    # Step 1: Find the log file
    print("\n[1/5] Finding log file...")
    log_path = find_log_containing_session(session_id)
    if log_path:
        analysis['log_source'] = str(log_path)
        print(f"  ✓ Found in: {log_path.name}")
    else:
        print("  ✗ Session not found in any log file")
        return analysis
    
    # Step 2: Extract metadata
    print("\n[2/5] Extracting session metadata...")
    metadata = extract_session_metadata(log_path, session_id)
    analysis['metadata'] = metadata
    print(f"  Model: {metadata['model']}")
    print(f"  Created: {metadata['created_at']}")
    print(f"  Destroyed: {metadata['destroyed_at']}")
    print(f"  Turns: {metadata['turn_count']}")
    if metadata['errors']:
        print(f"  ⚠️  Errors/Warnings: {len(metadata['errors'])}")
    
    # Step 3: Tool call analysis
    print("\n[3/5] Analyzing tool calls...")
    tool_calls = find_tool_calls_for_session(session_id)
    tool_analysis = analyze_tool_flow(tool_calls)
    analysis['tool_analysis'] = tool_analysis
    print(f"  Total tool-related events: {tool_analysis['total_calls']}")
    
    # Step 4: Collect raw entries
    print("\n[4/5] Collecting log entries...")
    logs = collect_logs_for_session(session_id)
    total_entries = sum(len(v) for v in logs.values())
    print(f"  Found {total_entries} related entries")
    analysis['raw_entries'] = [
        {'source': k, 'count': len(v)}
        for k, v in logs.items()
    ]
    
    # Step 5: Generate summary
    print("\n[5/5] Generating summary...")
    summary = {
        'session_found': True,
        'has_errors': len(metadata['errors']) > 0,
        'sdk_tools_fired': len(tool_analysis.get('sdk_tools_fired', [])),
        'tool_calls_detected': tool_analysis['total_calls'],
        'model_used': metadata['model'],
    }
    analysis['summary'] = summary
    
    # Print detailed tool analysis
    if tool_analysis['total_calls'] > 0:
        print_tool_analysis(tool_analysis)
    
    # Print errors if any
    if metadata['errors']:
        print("\n" + "="*60)
        print("ERRORS/WARNINGS DETECTED")
        print("="*60)
        for i, error in enumerate(metadata['errors'][:10], 1):
            print(f"\n{i}. {error}")
        if len(metadata['errors']) > 10:
            print(f"\n... and {len(metadata['errors']) - 10} more")
    
    # Final verdict
    print("\n" + "="*60)
    print("VERDICT")
    print("="*60)
    
    if summary['sdk_tools_fired'] > 0:
        print("⚠️  SDK BUILT-IN TOOLS FIRED - F-045 may not be working!")
    else:
        print("✅ No SDK built-in tools fired - F-045 is working")
    
    if summary['has_errors']:
        print("⚠️  Errors detected - review above")
    else:
        print("✅ No errors detected")
    
    return analysis


def main():
    parser = argparse.ArgumentParser(description='Forensic session analyzer')
    parser.add_argument('session_id', help='Session ID to analyze (UUID format)')
    parser.add_argument('--full', action='store_true', help='Show full log output')
    parser.add_argument('--tools-only', action='store_true', help='Only analyze tools')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--output', '-o', help='Write output to file')
    
    args = parser.parse_args()
    
    # Validate session ID format
    if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', args.session_id, re.I):
        print(f"Warning: '{args.session_id}' doesn't look like a UUID, but continuing anyway...")
    
    # Run analysis
    analysis = analyze_session_360(args.session_id, verbose=args.full)
    
    # Output
    if args.json:
        # Convert non-serializable objects
        output = json.dumps(analysis, indent=2, default=str)
        print(output)
    
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\nAnalysis saved to: {output_path}")
    
    print("\n" + "="*60)
    print("Analysis complete")
    print("="*60)


if __name__ == "__main__":
    main()
