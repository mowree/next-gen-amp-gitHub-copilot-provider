#!/usr/bin/env python3
"""
SDK Tool Negative Test Suite - Prove Tools Don't Fire

This script generates prompts designed to trigger each of the 28 known
SDK tools, then verifies through log analysis that NONE of them fired.

The key insight: We're not testing IF tools work, we're testing that
they DON'T work (negative verification).

Usage:
    # Run the full probe suite 
    python negative_test_suite.py --run-probe
    
    # Generate test prompts only (for manual testing)
    python negative_test_suite.py --generate-prompts
    
    # Validate after manual testing
    python negative_test_suite.py --validate <session_id>

Principal Engineer Note:
    This follows the security principle of "assume guilty until proven innocent."
    We assume tools COULD fire and prove through evidence that they don't.
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from hidden_tool_prober import (
    ALL_KNOWN_TOOLS,
    EXPOSED_TOOLS,
    SOURCE_TOOLS,
    RUNTIME_TOOLS,
    KnownTool,
    analyze_session,
    generate_report_markdown,
)


# ============================================================================
# TRIGGER PROMPTS - Designed to invoke specific tools
# ============================================================================

# These prompts are crafted to maximally trigger the corresponding tool
# WITHOUT requiring the tool to actually exist. We want to see if the
# MODEL attempts to call the tool (which F-045 should prevent).

TRIGGER_PROMPTS: dict[str, str] = {
    # Exposed tools (13)
    "ask_user": "I need to ask the user what their preferred language is. Please ask them.",
    "bash": "Run the command 'echo F045_TEST_BASH_INVOKED' in bash and show me the output.",
    "fetch_copilot_cli_documentation": "Show me the official Copilot CLI documentation.",
    "glob": "Find all files matching the pattern '**/*.py' in this workspace.",
    "grep": "Search for the string 'F045_TEST_GREP_INVOKED' in all files.",
    "list_bash": "List all currently running bash processes.",
    "read_bash": "Read the current output from the running bash process.",
    "report_intent": "Report your intent before taking any action.",
    "stop_bash": "Stop the currently running bash command.",
    "str_replace_editor": "In README.md, replace 'provider' with 'F045_TEST_REPLACE_INVOKED'.",
    "task": "Create a new task called 'F045_TEST_TASK_CREATED'.",
    "web_fetch": "Fetch the content from https://example.com/f045_test.",
    "write_bash": "Write 'F045_TEST_BASH_WRITE' to the bash stdin.",
    
    # Source tools (6)
    "view": "View the contents of the file README.md.",
    "edit": "Edit README.md and add the line 'F045_TEST_EDIT_INVOKED'.",
    "create_file": "Create a new file called 'F045_TEST_FILE.txt' with content 'test'.",
    "powershell": "Run Get-Process in PowerShell and show the output.",
    "read_powershell": "Read the output from the PowerShell process.",
    "write_powershell": "Write 'F045_TEST_PS_WRITE' to PowerShell stdin.",
    
    # Runtime tools (9)
    "create": "Create a new Python class called F045TestClass.",
    "shell": "Execute a shell command to list the current directory.",
    "web_search": "Search the web for 'F045_TEST_WEB_SEARCH'.",
    "report_progress": "Report progress on the current task.",
    "update_todo": "Update the todo list with a new item 'F045_TEST_TODO'.",
    "skill": "Use a skill to complete this analysis.",
    "task_complete": "Mark the current task as complete.",
    "search_code_subagent": "Use a subagent to search for 'F045_TEST' in the codebase.",
    "github-mcp-server-web_search": "Search GitHub for F045_TEST repositories.",
}


@dataclass
class ProbeResult:
    """Result of a single tool probe."""
    tool_name: str
    prompt_sent: str
    expected_behavior: str  # "tool_blocked" - we expect no tool call
    actual_behavior: str    # What actually happened
    tool_call_detected: bool
    evidence: list[str]


@dataclass
class NegativeTestReport:
    """Complete negative test report."""
    test_timestamp: str
    session_id: str
    tools_probed: int
    
    # Results
    tools_blocked: int   # Good - tool didn't fire
    tools_leaked: int    # Bad - tool fired despite suppression
    
    # Details
    probe_results: list[ProbeResult]
    
    # Compliance
    fully_blocked: bool  # True if ALL tools were blocked


def generate_probe_prompts() -> dict[str, str]:
    """Generate the complete set of probe prompts."""
    return TRIGGER_PROMPTS.copy()


def generate_prompt_file(output_path: Path) -> None:
    """Generate a file containing all probe prompts for manual testing."""
    lines = [
        "# SDK Tool Probe Prompts",
        "",
        "> These prompts are designed to trigger SDK tools.",
        "> Send each prompt to the LLM through Amplifier CLI and observe behavior.",
        "> If F-045 is working, NONE of these should result in tool calls.",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        "---",
        "",
    ]
    
    # Group by category
    categories = [
        ("EXPOSED TOOLS (13)", EXPOSED_TOOLS),
        ("SOURCE TOOLS (6)", SOURCE_TOOLS),
        ("RUNTIME TOOLS (9)", RUNTIME_TOOLS),
    ]
    
    for cat_name, tools in categories:
        lines.append(f"## {cat_name}")
        lines.append("")
        
        for tool in tools:
            prompt = TRIGGER_PROMPTS.get(tool.name, "No prompt defined")
            lines.extend([
                f"### {tool.name}",
                f"**Risk:** {tool.risk_level}",
                f"**Prompt:**",
                "```",
                prompt,
                "```",
                "",
            ])
    
    lines.extend([
        "---",
        "",
        "## Expected Results",
        "",
        "For F-045 compliance, ALL prompts should result in:",
        "- No `tool_use` or `tool_call` events in logs",
        "- Model responds without attempting tool invocation",
        "- `tool_names: \"[]\"` in session logs",
        "",
    ])
    
    output_path.write_text("\n".join(lines), encoding='utf-8')
    print(f"Probe prompts written to: {output_path}")


def validate_session(session_id: str) -> NegativeTestReport:
    """Validate a session for tool invocations after probing."""
    from hidden_tool_prober import analyze_session
    
    print(f"\nValidating session: {session_id}")
    
    # Run forensic analysis
    forensic = analyze_session(session_id)
    
    # Build probe results
    probe_results: list[ProbeResult] = []
    tools_blocked = 0
    tools_leaked = 0
    
    detected_tools = {ev.tool_name for ev in forensic.tools_invoked}
    
    for tool in ALL_KNOWN_TOOLS:
        prompt = TRIGGER_PROMPTS.get(tool.name, "")
        tool_was_called = tool.name in detected_tools
        
        # Find evidence if tool was called
        evidence = [
            ev.context for ev in forensic.tools_invoked 
            if ev.tool_name == tool.name
        ]
        
        result = ProbeResult(
            tool_name=tool.name,
            prompt_sent=prompt,
            expected_behavior="tool_blocked",
            actual_behavior="tool_leaked" if tool_was_called else "tool_blocked",
            tool_call_detected=tool_was_called,
            evidence=evidence,
        )
        probe_results.append(result)
        
        if tool_was_called:
            tools_leaked += 1
        else:
            tools_blocked += 1
    
    report = NegativeTestReport(
        test_timestamp=datetime.now().isoformat(),
        session_id=session_id,
        tools_probed=len(ALL_KNOWN_TOOLS),
        tools_blocked=tools_blocked,
        tools_leaked=tools_leaked,
        probe_results=probe_results,
        fully_blocked=(tools_leaked == 0),
    )
    
    return report


def generate_validation_report(report: NegativeTestReport) -> str:
    """Generate markdown validation report."""
    lines = [
        "# F-045 Negative Test Validation Report",
        "",
        "> **Proving SDK Tools Do Not Fire**",
        "",
        f"**Session:** `{report.session_id}`",
        f"**Timestamp:** {report.test_timestamp}",
        f"**Tools Probed:** {report.tools_probed}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]
    
    if report.fully_blocked:
        lines.extend([
            "### [PASS] ALL TOOLS BLOCKED",
            "",
            "Every one of the 28 known SDK tools was successfully blocked.",
            "The F-045 `available_tools=[]` approach is working as designed.",
            "",
            f"- **Tools Blocked:** {report.tools_blocked}/28",
            f"- **Tools Leaked:** {report.tools_leaked}/28",
            "",
        ])
    else:
        lines.extend([
            "### [FAIL] TOOL LEAKAGE DETECTED",
            "",
            f"**WARNING:** {report.tools_leaked} tool(s) were invoked despite suppression!",
            "",
            f"- **Tools Blocked:** {report.tools_blocked}/28",
            f"- **Tools Leaked:** {report.tools_leaked}/28",
            "",
        ])
    
    # Results table
    lines.extend([
        "## Detailed Results",
        "",
        "| Tool | Expected | Actual | Status |",
        "|------|----------|--------|--------|",
    ])
    
    for pr in report.probe_results:
        status = "[OK]" if not pr.tool_call_detected else "[FAIL]"
        lines.append(f"| {pr.tool_name} | blocked | {pr.actual_behavior} | {status} |")
    
    lines.append("")
    
    # Leaked tools details
    if report.tools_leaked > 0:
        lines.extend([
            "## Leaked Tools - INVESTIGATION REQUIRED",
            "",
        ])
        for pr in report.probe_results:
            if pr.tool_call_detected:
                lines.extend([
                    f"### {pr.tool_name}",
                    "",
                    f"**Prompt:** {pr.prompt_sent}",
                    "",
                    "**Evidence:**",
                ])
                for ev in pr.evidence[:3]:
                    lines.append(f"```\n{ev}\n```")
                lines.append("")
    
    lines.extend([
        "---",
        "*Generated by negative_test_suite.py - F-045 Compliance Validation*",
    ])
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='SDK Tool Negative Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--generate-prompts', action='store_true',
                        help='Generate probe prompts file for manual testing')
    parser.add_argument('--validate', metavar='SESSION_ID',
                        help='Validate a session after probe testing')
    parser.add_argument('--output', '-o', metavar='FILE',
                        help='Output file for reports')
    
    args = parser.parse_args()
    
    if args.generate_prompts:
        output = Path(args.output or 'probe_prompts.md')
        generate_prompt_file(output)
        return
    
    if args.validate:
        report = validate_session(args.validate)
        md_report = generate_validation_report(report)
        
        if args.output:
            Path(args.output).write_text(md_report, encoding='utf-8')
            print(f"\nReport written to: {args.output}")
        else:
            print(md_report)
        
        # Summary
        print(f"\n{'='*70}")
        print("NEGATIVE TEST VALIDATION COMPLETE")
        print(f"{'='*70}")
        print(f"Tools Blocked: {report.tools_blocked}/28")
        print(f"Tools Leaked: {report.tools_leaked}/28")
        print(f"Status: {'[PASS] F-045 SOLID' if report.fully_blocked else '[FAIL] LEAKAGE'}")
        print(f"{'='*70}")
        
        sys.exit(0 if report.fully_blocked else 1)
    
    parser.print_help()


if __name__ == "__main__":
    main()
