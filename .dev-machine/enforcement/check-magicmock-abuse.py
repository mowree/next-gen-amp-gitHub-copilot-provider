#!/usr/bin/env python3
"""
MagicMock Abuse Detector
========================
Detects bare MagicMock()/AsyncMock() usage at the SDK boundary in test files.

This is the root cause of F-044 and F-045 surviving 42 feature implementations:
MagicMock silently accepts any call without validation, so tests verified
"did we call a function?" not "did we send the correct configuration?".

The fix: use ConfigCapturingMock from tests/fixtures/config_capture.py.

Usage:
  python3 .dev-machine/enforcement/check-magicmock-abuse.py [--json] [tests_dir]

Exit codes:
  0 -- no abuse detected
  1 -- MagicMock abuse at SDK boundary detected (blocking)
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# SDK boundary test files -- only scan these, not all tests
# (unit tests for pure domain logic can use MagicMock freely)
SDK_BOUNDARY_PATTERNS = [
    "test_sdk*.py",
    "test_client*.py",
    "test_session*.py",
    "test_boundary*.py",
    "test_provider*.py",
]

# Patterns indicating MagicMock abuse AT THE SDK BOUNDARY
# (create_session, disconnect, register_pre_tool_use_hook are the critical ones)
ABUSE_PATTERNS: list[tuple[str, str, bool]] = [
    # bare MagicMock() used as create_session return -- won't capture config
    (
        r"create_session\s*=\s*AsyncMock\(\s*return_value\s*=\s*MagicMock\(",
        "create_session must use ConfigCapturingMock to capture SDK config",
        True,
    ),
    (
        r"create_session\s*=\s*AsyncMock\(\s*\)",
        "bare AsyncMock for create_session won't capture SDK config (use ConfigCapturingMock)",
        True,
    ),
    (
        r"mock_client\s*=\s*MagicMock\(\s*\)",
        "bare MagicMock for SDK client won't validate any calls (use ConfigCapturingMock)",
        True,
    ),
    (
        r"mock_client\s*=\s*AsyncMock\(\s*\)",
        "bare AsyncMock for SDK client won't capture config (use ConfigCapturingMock)",
        True,
    ),
    # Tests that assert mode == "append" -- the exact F-044 bug frozen as spec
    (
        r"\"mode\".*\"append\"",
        'CRITICAL: test asserts mode=="append" -- this codifies the F-044 bug',
        True,
    ),
    (
        r"mode.*append",
        'WARNING: test references "append" mode -- verify this is not codifying F-044',
        False,
    ),
    # Tests that never assert on available_tools -- F-045 gap
    # (This is a structural check, done separately below)
]


@dataclass
class Violation:
    file: str
    line: int
    match: str
    message: str
    is_hard_fail: bool


def scan_file(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line_idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, message, is_hard in ABUSE_PATTERNS:
                if re.search(pattern, line):
                    violations.append(
                        Violation(
                            file=str(path),
                            line=line_idx,
                            match=line.strip()[:120],
                            message=message,
                            is_hard_fail=is_hard,
                        )
                    )
    except Exception:
        pass
    return violations


def check_available_tools_coverage(tests_dir: Path) -> list[dict]:
    """
    Structural check: do boundary tests ever assert on available_tools?
    F-045 class bugs survive when no test checks this key.
    """
    issues = []
    for pattern in SDK_BOUNDARY_PATTERNS:
        for tf in tests_dir.glob(pattern):
            try:
                content = tf.read_text(encoding="utf-8")
                if "create_session" in content and "available_tools" not in content:
                    issues.append(
                        {
                            "file": str(tf),
                            "issue": (
                                "test calls create_session but never asserts "
                                "on available_tools (F-045 blind spot)"
                            ),
                            "severity": "warn",
                        }
                    )
            except Exception:
                pass
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="MagicMock abuse detector")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "tests_dir",
        nargs="?",
        default="tests",
        help="Tests directory to scan",
    )
    args = parser.parse_args()

    tests_dir = Path(args.tests_dir)
    if not tests_dir.exists():
        if args.json:
            print(json.dumps({"status": "skip", "reason": "tests directory not found"}))
        else:
            print(f"WARNING: {tests_dir} does not exist -- skipping")
        return 0

    all_violations: list[Violation] = []
    for pattern in SDK_BOUNDARY_PATTERNS:
        for tf in tests_dir.glob(pattern):
            all_violations.extend(scan_file(tf))

    coverage_issues = check_available_tools_coverage(tests_dir)

    hard_violations = [v for v in all_violations if v.is_hard_fail]
    soft_violations = [v for v in all_violations if not v.is_hard_fail]

    def violation_dict(v: Violation) -> dict:
        return {
            "file": v.file,
            "line": v.line,
            "match": v.match,
            "message": v.message,
            "severity": "FAIL" if v.is_hard_fail else "warn",
        }

    if args.json:
        print(
            json.dumps(
                {
                    "hard_violations": [violation_dict(v) for v in hard_violations],
                    "soft_violations": [violation_dict(v) for v in soft_violations],
                    "coverage_issues": coverage_issues,
                    "summary": {
                        "hard_violations": len(hard_violations),
                        "soft_violations": len(soft_violations),
                        "coverage_issues": len(coverage_issues),
                    },
                    "status": "FAIL"
                    if hard_violations
                    else ("warn" if (soft_violations or coverage_issues) else "ok"),
                    "root_cause_note": (
                        "F-044 root cause: test asserted observed behavior (append) "
                        "not required behavior (replace). "
                        "F-045 root cause: no test ever checked available_tools key."
                    ),
                },
                indent=2,
            )
        )
    else:
        print("MagicMock Abuse Detector (F-044/F-045 Prevention)")
        print("=" * 60)

        if not all_violations and not coverage_issues:
            print("\u2705  No MagicMock abuse detected at SDK boundary.")
            return 0

        if hard_violations:
            print("\nHARD VIOLATIONS (blocking -- SDK boundary integrity broken):")
            for v in hard_violations:
                print(f"  \u274c FAIL  {v.file}:{v.line}")
                print(f"          {v.message}")
                print(f"          \u2192 {v.match}")

        if soft_violations:
            print("\nWARNINGS (review required):")
            for v in soft_violations:
                print(f"  \u26a0\ufe0f  WARN  {v.file}:{v.line}")
                print(f"          {v.message}")
                print(f"          \u2192 {v.match}")

        if coverage_issues:
            print("\nCOVERAGE GAPS (F-045 class bugs):")
            for issue in coverage_issues:
                print(f"  \u26a0\ufe0f  {issue['file']}: {issue['issue']}")

        if hard_violations:
            print()
            print("ROOT CAUSE PREVENTION:")
            print("  Use ConfigCapturingMock instead of MagicMock/AsyncMock at SDK boundary.")
            print("  See: tests/fixtures/config_capture.py")
            print("  See: specs/F-047-testing-course-correction.md \u00a7Part 3")

    return 1 if hard_violations else 0


if __name__ == "__main__":
    sys.exit(main())
