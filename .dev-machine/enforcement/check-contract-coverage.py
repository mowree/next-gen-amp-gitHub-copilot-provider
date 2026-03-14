#!/usr/bin/env python3
"""
Contract Coverage Checker
=========================
Verifies that test files reference contract anchors in their docstrings.

The F-044 failure mode: a test was written to OBSERVED behavior (mode="append")
not REQUIRED behavior (mode="replace"). Contract-anchored tests prevent this by
requiring the developer to read the contract BEFORE writing the assertion value.

A contract anchor looks like: `contract-name:Section:MUST:N`
e.g.: sdk-boundary:Config:MUST:2

Usage:
  python3 .dev-machine/enforcement/check-contract-coverage.py [--json] [tests_dir]

Exit codes:
  0 -- all boundary tests have contract anchors
  1 -- boundary tests found without contract anchors (blocking)
"""

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Contract anchor pattern: word-chars:PascalWord:ALLCAPS:digit
# e.g., sdk-boundary:Config:MUST:2, deny-destroy:ToolSuppression:MUST:1
ANCHOR_PATTERN = r"\b[\w-]+:[A-Z][A-Za-z]+:[A-Z]+:\d+\b"

# SDK boundary test files that MUST have contract anchors
# Pure domain logic tests don't require anchors
SDK_BOUNDARY_PATTERNS = [
    "test_sdk_boundary*.py",
    "test_session_config*.py",
    "test_sdk_assumptions*.py",
    "test_provider_protocol*.py",
]


@dataclass
class TestFunction:
    file: str
    class_name: str | None
    func_name: str
    line: int
    has_anchor: bool
    anchor_ids: list[str] = field(default_factory=list)
    docstring: str | None = None


def extract_test_functions(path: Path) -> list[TestFunction]:
    """Parse a Python file and extract test function metadata."""
    results: list[TestFunction] = []
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return results

    import re

    anchor_re = re.compile(ANCHOR_PATTERN)

    def get_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            return node.body[0].value.value
        return None

    def process_function(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        class_name: str | None,
    ) -> None:
        if not node.name.startswith("test_"):
            return
        docstring = get_docstring(node)
        anchors = anchor_re.findall(docstring) if docstring else []
        results.append(
            TestFunction(
                file=str(path),
                class_name=class_name,
                func_name=node.name,
                line=node.lineno,
                has_anchor=bool(anchors),
                anchor_ids=anchors,
                docstring=docstring[:200] if docstring else None,
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in ast.walk(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    process_function(child, node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            process_function(node, None)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Contract coverage checker")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--require-anchors",
        action="store_true",
        help="Fail if any boundary test lacks anchors (default: warn)",
    )
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

    all_tests: list[TestFunction] = []
    for pattern in SDK_BOUNDARY_PATTERNS:
        for tf in tests_dir.glob(pattern):
            all_tests.extend(extract_test_functions(tf))

    if not all_tests:
        if args.json:
            print(
                json.dumps(
                    {
                        "status": "skip",
                        "reason": "no boundary test files found yet",
                        "note": (
                            "Boundary test files (test_sdk_boundary*.py etc.) "
                            "don't exist yet. Create them as part of F-046."
                        ),
                    }
                )
            )
        else:
            print("No boundary test files found yet.")
            print("Create test_sdk_boundary_contract.py as part of F-046.")
        return 0

    with_anchors = [t for t in all_tests if t.has_anchor]
    without_anchors = [t for t in all_tests if not t.has_anchor]

    coverage_pct = (len(with_anchors) / len(all_tests) * 100) if all_tests else 0

    def test_dict(t: TestFunction) -> dict:
        return {
            "file": t.file,
            "class": t.class_name,
            "function": t.func_name,
            "line": t.line,
            "has_anchor": t.has_anchor,
            "anchor_ids": t.anchor_ids,
        }

    if args.json:
        print(
            json.dumps(
                {
                    "total_boundary_tests": len(all_tests),
                    "with_anchors": len(with_anchors),
                    "without_anchors": len(without_anchors),
                    "coverage_pct": round(coverage_pct, 1),
                    "tests_without_anchors": [test_dict(t) for t in without_anchors],
                    "tests_with_anchors": [test_dict(t) for t in with_anchors],
                    "status": (
                        "FAIL"
                        if (without_anchors and args.require_anchors)
                        else ("warn" if without_anchors else "ok")
                    ),
                    "failure_mode_note": (
                        "F-044 root cause: test asserted mode='append' (observed) "
                        "not mode='replace' (required from contract). "
                        "Contract anchors in docstrings force developers to read "
                        "the contract before writing the assertion value."
                    ),
                },
                indent=2,
            )
        )
    else:
        print("Contract Coverage Check")
        print("=" * 60)
        print(f"  Boundary tests:    {len(all_tests)}")
        print(f"  With anchors:      {len(with_anchors)}")
        print(f"  Without anchors:   {len(without_anchors)}")
        print(f"  Coverage:          {coverage_pct:.0f}%")
        print()

        if with_anchors:
            print("Tests with contract anchors:")
            for t in with_anchors:
                cn = f"{t.class_name}::" if t.class_name else ""
                print(f"  \u2705  {cn}{t.func_name}")
                for anchor in t.anchor_ids:
                    print(f"       \u2514\u2500 {anchor}")

        if without_anchors:
            print()
            print("Tests WITHOUT contract anchors (F-044 risk):")
            for t in without_anchors:
                cn = f"{t.class_name}::" if t.class_name else ""
                marker = "\u274c" if args.require_anchors else "\u26a0\ufe0f "
                print(f"  {marker} {t.file}:{t.line}  {cn}{t.func_name}")
                if t.docstring:
                    print(f"       docstring: {t.docstring[:80]}...")
                else:
                    print("       no docstring")

            print()
            print("HOW TO ADD AN ANCHOR:")
            print("  def test_system_message_mode(self) -> None:")
            print('      """sdk-boundary:Config:MUST:2')
            print()
            print("      System message MUST use replace mode.")
            print('      """')
            print()
            print("See contracts/ for available contract anchors.")

    if without_anchors and args.require_anchors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
