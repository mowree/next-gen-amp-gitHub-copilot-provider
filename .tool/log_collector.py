"""
Log collector and parser for forensic analysis.

Reads and parses log files from various sources:
- Copilot CLI JSON logs
- Session state JSON files
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from log_paths import find_copilot_logs, find_session_state_files


@dataclass
class LogEntry:
    """A parsed log entry."""
    timestamp: datetime | None
    level: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""
    line_number: int = 0
    raw_line: str = ""


@dataclass
class SessionData:
    """Session state data from JSON."""
    session_id: str
    data: dict[str, Any]
    source_file: str


def parse_copilot_log_line(line: str, source_file: str = "", line_num: int = 0) -> LogEntry | None:
    """Parse a single line from Copilot CLI log."""
    line = line.strip()
    if not line:
        return None
    
    # Pattern: 2026-03-14T20:15:42.007Z [INFO] message
    timestamp_pattern = r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+\[(\w+)\]\s+(.*)$'
    match = re.match(timestamp_pattern, line)
    
    if match:
        ts_str, level, message = match.groups()
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            ts = None
        
        return LogEntry(
            timestamp=ts,
            level=level,
            message=message,
            source_file=source_file,
            line_number=line_num,
            raw_line=line
        )
    
    # Try to parse as JSON object (some log entries span multiple lines)
    if line.startswith('{'):
        try:
            data = json.loads(line)
            return LogEntry(
                timestamp=None,
                level="DATA",
                message="JSON object",
                data=data,
                source_file=source_file,
                line_number=line_num,
                raw_line=line
            )
        except json.JSONDecodeError:
            pass
    
    # Unstructured line
    return LogEntry(
        timestamp=None,
        level="RAW",
        message=line,
        source_file=source_file,
        line_number=line_num,
        raw_line=line
    )


def read_copilot_log(log_path: Path) -> Iterator[LogEntry]:
    """Read and parse a Copilot CLI log file."""
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                entry = parse_copilot_log_line(line, str(log_path), line_num)
                if entry:
                    yield entry
    except Exception as e:
        yield LogEntry(
            timestamp=None,
            level="ERROR",
            message=f"Failed to read log: {e}",
            source_file=str(log_path),
            line_number=0,
            raw_line=""
        )


def read_session_state_file(state_path: Path) -> SessionData | None:
    """Read a session state JSON file."""
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract session ID from filename or data
        session_id = state_path.stem  # e.g., "abc123.json" -> "abc123"
        if isinstance(data, dict) and 'session_id' in data:
            session_id = data['session_id']
        
        return SessionData(
            session_id=session_id,
            data=data,
            source_file=str(state_path)
        )
    except Exception:
        return None


def collect_logs_for_session(session_id: str, log_limit: int = 20) -> dict[str, list[LogEntry]]:
    """Collect all log entries mentioning a session ID."""
    results: dict[str, list[LogEntry]] = {
        'copilot_cli': [],
        'session_state': [],
    }
    
    # Search Copilot CLI logs
    for log_source in find_copilot_logs(limit=log_limit):
        for entry in read_copilot_log(log_source.path):
            # Check if session ID appears in message or raw line
            if session_id in entry.message or session_id in entry.raw_line:
                results['copilot_cli'].append(entry)
            # Also check in data dict
            elif entry.data and session_id in json.dumps(entry.data):
                results['copilot_cli'].append(entry)
    
    # Check session state files
    for state_source in find_session_state_files():
        state = read_session_state_file(state_source.path)
        if state and session_id in state.session_id:
            results['session_state'].append(LogEntry(
                timestamp=None,
                level="STATE",
                message=f"Session state file: {state.source_file}",
                data=state.data,
                source_file=state.source_file,
                line_number=0,
                raw_line=json.dumps(state.data, indent=2)
            ))
    
    return results


def read_log_file_raw(log_path: Path) -> str:
    """Read entire log file as raw text."""
    try:
        return log_path.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        return f"Error reading {log_path}: {e}"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python log_collector.py <session_id>")
        print("Example: python log_collector.py b0c6837a-3fb1-4754-9eac-ea049c6c9863")
        sys.exit(1)
    
    session_id = sys.argv[1]
    print(f"Collecting logs for session: {session_id}\n")
    
    logs = collect_logs_for_session(session_id)
    
    for source_type, entries in logs.items():
        print(f"\n=== {source_type.upper()} ({len(entries)} entries) ===")
        for entry in entries[:10]:
            ts = entry.timestamp.isoformat() if entry.timestamp else "???"
            print(f"  [{ts}] [{entry.level}] {entry.message[:100]}")
        if len(entries) > 10:
            print(f"  ... and {len(entries) - 10} more entries")
