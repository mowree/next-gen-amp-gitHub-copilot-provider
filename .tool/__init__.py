"""
Forensic log analysis tools for Amplifier/Copilot SDK debugging.

Modules:
- log_paths: Log file discovery
- log_collector: Log reading and parsing  
- tool_analyzer: Tool call analysis
- analyze_session: Main entry point for 360-degree analysis
- evidence_collector: Evidence-based reporting
- tool_tester: Automated tool testing
- hidden_tool_prober: F-045 hidden tool detection
- deep_log_scanner: Deep forensic evidence extraction
- negative_test_suite: Negative verification tests
- f045_compliance_suite: Master forensic orchestrator
"""

# Re-export for package-level imports
from .log_paths import (
    LogSource,
    find_copilot_logs,
    find_session_state_files,
    find_amplifier_logs,
    find_all_log_sources,
)
from .log_collector import (
    LogEntry,
    SessionData,
    collect_logs_for_session,
    read_log_file_raw,
)
from .tool_analyzer import (
    ToolCall,
    find_tool_calls_for_session,
    analyze_tool_flow,
    print_tool_analysis,
)

__all__ = [
    # Core types
    "LogSource",
    "LogEntry",
    "SessionData",
    "ToolCall",
    # Log discovery
    "find_copilot_logs",
    "find_session_state_files", 
    "find_amplifier_logs",
    "find_all_log_sources",
    # Log collection
    "collect_logs_for_session",
    "read_log_file_raw",
    # Tool analysis
    "find_tool_calls_for_session",
    "analyze_tool_flow",
    "print_tool_analysis",
]
