"""
Log path discovery for forensic analysis.

Finds log files from various sources:
- Copilot CLI/SDK logs
- Amplifier logs
- Provider debug logs
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator


@dataclass
class LogSource:
    """A log source with metadata."""
    name: str
    path: Path
    source_type: str  # 'copilot_cli', 'amplifier', 'provider', 'session_state'


def get_home_dir() -> Path:
    """Get home directory, works on Windows and WSL."""
    return Path(os.path.expanduser("~"))


def get_copilot_log_dir() -> Path:
    """Get Copilot CLI log directory."""
    return get_home_dir() / ".copilot" / "logs"


def get_copilot_session_state_dir() -> Path:
    """Get Copilot session state directory."""
    return get_home_dir() / ".copilot" / "session-state"


def get_amplifier_dir() -> Path:
    """Get Amplifier directory."""
    return get_home_dir() / ".amplifier"


def get_amplifier_log_dir() -> Path:
    """Get Amplifier log directory (if exists)."""
    return get_amplifier_dir() / "logs"


def get_amplifier_cache_dir() -> Path:
    """Get Amplifier cache directory."""
    return get_amplifier_dir() / "cache"


def find_copilot_logs(limit: int = 20) -> Iterator[LogSource]:
    """Find recent Copilot CLI log files."""
    log_dir = get_copilot_log_dir()
    if not log_dir.exists():
        return
    
    # Sort by modification time, newest first
    logs = sorted(
        log_dir.glob("process-*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    for log_path in logs[:limit]:
        yield LogSource(
            name=log_path.name,
            path=log_path,
            source_type="copilot_cli"
        )


def find_session_state_files() -> Iterator[LogSource]:
    """Find Copilot session state files."""
    state_dir = get_copilot_session_state_dir()
    if not state_dir.exists():
        return
    
    for state_file in state_dir.glob("*.json"):
        yield LogSource(
            name=state_file.name,
            path=state_file,
            source_type="session_state"
        )


def find_amplifier_logs() -> Iterator[LogSource]:
    """Find Amplifier log files."""
    log_dir = get_amplifier_log_dir()
    if not log_dir.exists():
        return
    
    for log_path in log_dir.glob("*.log"):
        yield LogSource(
            name=log_path.name,
            path=log_path,
            source_type="amplifier"
        )


def find_all_log_sources(copilot_limit: int = 20) -> list[LogSource]:
    """Find all available log sources."""
    sources = []
    
    # Copilot CLI logs
    sources.extend(find_copilot_logs(limit=copilot_limit))
    
    # Session state files
    sources.extend(find_session_state_files())
    
    # Amplifier logs
    sources.extend(find_amplifier_logs())
    
    return sources


def print_available_sources():
    """Print available log sources for debugging."""
    sources = find_all_log_sources()
    
    print(f"Found {len(sources)} log sources:\n")
    
    by_type: dict[str, list[LogSource]] = {}
    for src in sources:
        by_type.setdefault(src.source_type, []).append(src)
    
    for source_type, items in by_type.items():
        print(f"  {source_type}: {len(items)} files")
        for item in items[:5]:
            print(f"    - {item.name}")
        if len(items) > 5:
            print(f"    ... and {len(items) - 5} more")


if __name__ == "__main__":
    print_available_sources()
