"""
Tool call analyzer for forensic analysis.

Analyzes tool calls from:
- SDK/CLI built-in tools (bash, view, edit, etc.)
- Amplifier tools (delegated via provider)
- Permission requests and denials
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from log_paths import find_copilot_logs


@dataclass
class ToolCall:
    """A tool call event."""
    timestamp: datetime | None
    tool_name: str
    tool_source: str  # 'sdk_builtin', 'amplifier', 'unknown'
    status: str  # 'invoked', 'completed', 'failed', 'denied'
    arguments: dict[str, Any] = field(default_factory=lambda: {})
    result: str = ""
    duration_ms: int | None = None
    session_id: str = ""
    source_file: str = ""
    line_number: int = 0


# SDK built-in tools (these crash in WSL without available_tools=[])
SDK_BUILTIN_TOOLS = {
    'bash', 'view', 'edit', 'glob', 'grep', 'write_file', 
    'create_file', 'edit_file', 'read_file', 'shell',
    'web_search', 'web_fetch', 'think', 'plan'
}

# Amplifier tools
AMPLIFIER_TOOLS = {
    'LSP', 'delegate', 'edit_file', 'glob', 'grep', 'load_skill',
    'mode', 'python_check', 'read_file', 'recipes', 'todo',
    'web_fetch', 'web_search', 'write_file', 'bash'
}


def classify_tool_source(tool_name: str) -> str:
    """Classify tool source based on name."""
    # This is heuristic - both SDK and Amplifier have similar tool names
    # The key is WHERE the tool was invoked
    if tool_name in SDK_BUILTIN_TOOLS:
        return "sdk_builtin_or_amplifier"
    return "unknown"


def extract_tool_calls_from_log(log_path: Path, session_id: str | None = None) -> list[ToolCall]:
    """Extract tool calls from a Copilot CLI log file."""
    tool_calls: list[ToolCall] = []
    
    try:
        content = log_path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return []
    
    lines = content.splitlines()
    
    for line_num, line in enumerate(lines, 1):
        # Skip if session_id specified and not in line
        if session_id and session_id not in line:
            continue
        
        # Look for tool-related patterns
        tool_call = None
        
        # Pattern 1: Tool invocation event
        # "kind": "tool_use" or similar
        if '"kind"' in line and ('tool' in line.lower() or 'permission' in line.lower()):
            try:
                # Try to parse as JSON
                json_match = re.search(r'\{[^{}]*"kind"[^{}]*\}', line)
                if json_match:
                    data = json.loads(json_match.group())
                    kind = data.get('kind', '')
                    
                    if 'tool' in kind.lower():
                        tool_call = ToolCall(
                            timestamp=_extract_timestamp(line),
                            tool_name=data.get('tool_name', data.get('name', 'unknown')),
                            tool_source='from_event',
                            status='invoked',
                            arguments=data.get('arguments', data.get('input', {})),
                            session_id=session_id or "",
                            source_file=str(log_path),
                            line_number=line_num
                        )
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Pattern 2: Tool result
        if 'result_type' in line or 'tool_result' in line.lower():
            result_match = re.search(r'"result_type":\s*"(\w+)"', line)
            if result_match:
                status = result_match.group(1).lower()
                tool_call = ToolCall(
                    timestamp=_extract_timestamp(line),
                    tool_name="unknown",
                    tool_source='from_result',
                    status='completed' if status == 'success' else 'failed',
                    source_file=str(log_path),
                    line_number=line_num
                )
        
        # Pattern 3: Permission denied
        if 'denied' in line.lower() or 'permission' in line.lower():
            if 'deny' in line.lower():
                tool_call = ToolCall(
                    timestamp=_extract_timestamp(line),
                    tool_name="permission_check",
                    tool_source='sdk_builtin',
                    status='denied',
                    result=line[:200],
                    source_file=str(log_path),
                    line_number=line_num
                )
        
        # Pattern 4: Explicit tool names in log
        for tool_name in SDK_BUILTIN_TOOLS:
            pattern = rf'\b{tool_name}\b.*(?:invoke|call|execute|run)'
            if re.search(pattern, line, re.IGNORECASE):
                tool_call = ToolCall(
                    timestamp=_extract_timestamp(line),
                    tool_name=tool_name,
                    tool_source='sdk_builtin',
                    status='invoked',
                    result=line[:200],
                    source_file=str(log_path),
                    line_number=line_num
                )
                break
        
        if tool_call:
            tool_calls.append(tool_call)
    
    return tool_calls


def _extract_timestamp(line: str) -> datetime | None:
    """Extract timestamp from log line."""
    pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)'
    match = re.search(pattern, line)
    if match:
        try:
            return datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
        except ValueError:
            pass
    return None


def find_tool_calls_for_session(session_id: str, log_limit: int = 10) -> list[ToolCall]:
    """Find all tool calls for a session across all logs."""
    all_calls: list[ToolCall] = []
    
    for log_source in find_copilot_logs(limit=log_limit):
        calls = extract_tool_calls_from_log(log_source.path, session_id)
        all_calls.extend(calls)
    
    # Sort by timestamp
    all_calls.sort(key=lambda x: x.timestamp or datetime.min)
    
    return all_calls


def analyze_tool_flow(tool_calls: list[ToolCall]) -> dict[str, Any]:
    """Analyze the flow of tool calls."""
    # Use typed variables to help Pyright
    by_source: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_tool: dict[str, int] = {}
    sdk_tools_fired: list[ToolCall] = []
    amplifier_tools_fired: list[ToolCall] = []
    denied_calls: list[ToolCall] = []
    timeline: list[dict[str, str]] = []
    
    for call in tool_calls:
        # Count by source
        by_source[call.tool_source] = by_source.get(call.tool_source, 0) + 1
        
        # Count by status
        by_status[call.status] = by_status.get(call.status, 0) + 1
        
        # Count by tool name
        by_tool[call.tool_name] = by_tool.get(call.tool_name, 0) + 1
        
        # Categorize
        if call.tool_source == 'sdk_builtin':
            sdk_tools_fired.append(call)
        elif call.tool_source == 'amplifier':
            amplifier_tools_fired.append(call)
        
        if call.status == 'denied':
            denied_calls.append(call)
        
        # Timeline entry
        timeline.append({
            'time': call.timestamp.isoformat() if call.timestamp else '???',
            'tool': call.tool_name,
            'source': call.tool_source,
            'status': call.status
        })
    
    return {
        'total_calls': len(tool_calls),
        'by_source': by_source,
        'by_status': by_status,
        'by_tool': by_tool,
        'sdk_tools_fired': sdk_tools_fired,
        'amplifier_tools_fired': amplifier_tools_fired,
        'denied_calls': denied_calls,
        'timeline': timeline
    }


def print_tool_analysis(analysis: dict[str, Any]):
    """Print formatted tool analysis."""
    print("\n" + "=" * 60)
    print("TOOL CALL ANALYSIS")
    print("=" * 60)
    
    print(f"\nTotal tool calls detected: {analysis['total_calls']}")
    
    if analysis['by_source']:
        print("\nBy Source:")
        for source, count in analysis['by_source'].items():
            print(f"  {source}: {count}")
    
    if analysis['by_status']:
        print("\nBy Status:")
        for status, count in analysis['by_status'].items():
            print(f"  {status}: {count}")
    
    if analysis['by_tool']:
        print("\nBy Tool:")
        for tool, count in analysis['by_tool'].items():
            print(f"  {tool}: {count}")
    
    if analysis['sdk_tools_fired']:
        print("\n⚠️  SDK BUILT-IN TOOLS FIRED:")
        for call in analysis['sdk_tools_fired']:
            print(f"  - {call.tool_name} ({call.status})")
    else:
        print("\n✅ No SDK built-in tools fired (F-045 working)")
    
    if analysis['denied_calls']:
        print("\n🚫 DENIED CALLS:")
        for call in analysis['denied_calls']:
            print(f"  - {call.tool_name}")
    
    if analysis['timeline']:
        print("\nTimeline (first 10):")
        for entry in analysis['timeline'][:10]:
            print(f"  {entry['time']} | {entry['tool']} | {entry['source']} | {entry['status']}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python tool_analyzer.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    print(f"Analyzing tool calls for session: {session_id}")
    
    calls = find_tool_calls_for_session(session_id)
    analysis = analyze_tool_flow(calls)
    print_tool_analysis(analysis)
