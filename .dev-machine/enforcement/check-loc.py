#!/usr/bin/env python3
"""
LOC Enforcement Check
=====================
Verifies Python module line counts against Golden Vision V2 thresholds:
  - Soft cap:  400 LOC (warn -- do not add features)
  - Hard cap:  600 LOC (fail -- refactor required before any new work)
  - Core target: ~300 LOC for the main mechanism module

Usage:
  python3 .dev-machine/enforcement/check-loc.py [--hard-fail]
  python3 .dev-machine/enforcement/check-loc.py --json

Exit codes:
  0 -- all within limits
  1 -- hard cap violated (blocking)
  2 -- soft cap exceeded (warning only unless --hard-fail)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Golden Vision V2 §Principle 5 (AI-Maintainability as First-Class Goal)
SOFT_CAP = 400
HARD_CAP = 600
CORE_MECHANISM_TARGET = 300  # For the main translation mechanism


def count_lines(path: Path) -> int:
    """Count non-blank, non-comment lines (effective LOC)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        # Count all lines (total LOC, not just effective LOC)
        return len(lines)
    except Exception:
        return 0


def scan_directory(src_dir: Path) -> list[dict]:
    """Scan directory for Python files and return LOC data."""
    results = []
    for py_file in sorted(src_dir.rglob("*.py")):
        # Skip __pycache__
        if "__pycache__" in str(py_file):
            continue
        loc = count_lines(py_file)
        status = "ok"
        if loc > HARD_CAP:
            status = "hard-cap-violation"
        elif loc > SOFT_CAP:
            status = "soft-cap-warning"
        elif loc > CORE_MECHANISM_TARGET:
            status = "above-target"
        results.append({
            "file": str(py_file),
            "lines": loc,
            "status": status,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="LOC enforcement check")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--hard-fail", action="store_true", help="Fail on soft cap too")
    parser.add_argument(
        "src_dir",
        nargs="?",
        default="amplifier_module_provider_github_copilot",
        help="Source directory to scan"
    )
    args = parser.parse_args()

    src_dir = Path(args.src_dir)
    if not src_dir.exists():
        print(f"ERROR: {src_dir} does not exist", file=sys.stderr)
        return 1

    results = scan_directory(src_dir)
    hard_violations = [r for r in results if r["status"] == "hard-cap-violation"]
    soft_warnings = [r for r in results if r["status"] == "soft-cap-warning"]

    if args.json:
        print(json.dumps({
            "soft_cap": SOFT_CAP,
            "hard_cap": HARD_CAP,
            "core_target": CORE_MECHANISM_TARGET,
            "hard_violations": hard_violations,
            "soft_warnings": soft_warnings,
            "all_files": results,
            "summary": {
                "hard_violations": len(hard_violations),
                "soft_warnings": len(soft_warnings),
                "total_files": len(results),
            },
            "status": "FAIL" if hard_violations else ("warn" if soft_warnings else "ok"),
        }, indent=2))
    else:
        print(f"LOC Check (soft={SOFT_CAP}, hard={HARD_CAP})")
        print("=" * 60)
        for r in results:
            marker = {
                "hard-cap-violation": "❌ HARD",
                "soft-cap-warning":   "⚠️  WARN",
                "above-target":       "📊 HIGH",
                "ok":                 "✅  OK  ",
            }.get(r["status"], "     ")
            print(f"  {marker}  {r['lines']:>4} LOC  {r['file']}")

        if hard_violations:
            print()
            print("HARD CAP VIOLATIONS (blocking):")
            for v in hard_violations:
                print(f"  {v['file']}: {v['lines']} lines > {HARD_CAP} hard cap")
            print()
            print("ACTION REQUIRED: Refactor before adding new features.")
            print("See Golden Vision V2 §Principle 5 and the Three-Medium Architecture.")
        elif soft_warnings:
            print()
            print("SOFT CAP WARNINGS:")
            for w in soft_warnings:
                print(f"  {w['file']}: {w['lines']} lines > {SOFT_CAP} soft cap")
            print()
            print("Consider extracting policy to YAML config before adding more code.")

        if not hard_violations and not soft_warnings:
            print()
            print("✅  All files within LOC limits.")

    if hard_violations:
        return 1
    if args.hard_fail and soft_warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
