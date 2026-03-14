#!/usr/bin/env python3
"""
Hardcoded Policy Detector
=========================
Detects policy values (thresholds, mappings, constants) hardcoded in Python
that should live in YAML config per the Three-Medium Architecture.

From Golden Vision V2 §Principle 2:
  "Policy thresholds as Python constants" → Anti-pattern
  "Mapping tables as isinstance chains" → Anti-pattern
  "Config for control flow" → Anti-pattern

Usage:
  python3 .dev-machine/enforcement/check-hardcoded-policy.py [--json] [src_dir]

Exit codes:
  0 -- clean or only warnings
  1 -- hard violations found (blocking)
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# fmt: off
def _r(pattern: str, message: str, category: str, hard: bool) -> tuple[str, str, str, bool]:
    return (pattern, message, category, hard)


POLICY_RULES: list[tuple[str, str, str, bool]] = [
    # Retry/timeout/rate-limit constants -- should be in config/errors.yaml
    _r(r"\bMAX_RETRIES\s*=\s*\d+", "retry count constant should be in YAML config",
       "retry-policy", False),
    _r(r"\bRETRY_COUNT\s*=\s*\d+", "retry count constant should be in YAML config",
       "retry-policy", False),
    _r(r"\bTIMEOUT\s*=\s*\d+", "timeout constant should be in YAML config",
       "timeout-policy", False),
    _r(r"\bMAX_TIMEOUT\s*=\s*\d+", "timeout constant should be in YAML config",
       "timeout-policy", False),
    _r(r"\bBACKOFF_FACTOR\s*=\s*[\d.]+", "backoff factor should be in YAML config",
       "retry-policy", False),
    _r(r"\bBACKOFF_BASE\s*=\s*[\d.]+", "backoff base should be in YAML config",
       "retry-policy", False),
    _r(r"\bMAX_TOKENS\s*=\s*\d+", "token limit should be in YAML config",
       "capacity-policy", False),
    _r(r"\bTOKEN_LIMIT\s*=\s*\d+", "token limit should be in YAML config",
       "capacity-policy", False),
    _r(r"\bCIRCUIT_BREAKER_LIMIT\s*=\s*\d+", "circuit breaker limit should be in YAML config",
       "circuit-breaker", False),
    # Model names hardcoded -- should be in config/models.yaml
    _r(r'"gpt-4[o\-][^"]*"', "model name hardcoded; use YAML config", "model-policy", False),
    _r(r'"claude-[23][^"]*"', "model name hardcoded; use YAML config", "model-policy", False),
    _r(r'"o1-[^"]*"', "model name hardcoded; use YAML config", "model-policy", False),
    _r(r'"o3-[^"]*"', "model name hardcoded; use YAML config", "model-policy", False),
    # Error routing as isinstance chains -- should be in config/errors.yaml
    _r(r'elif\s+.*"rate.limit"', "error routing by string should be in YAML",
       "error-policy", False),
    _r(r"elif\s+.*status_code\s*==\s*429", "HTTP 429 routing should be in YAML error table",
       "error-policy", False),
    _r(r"elif\s+.*status_code\s*==\s*401", "HTTP 401 routing should be in YAML error table",
       "error-policy", False),
    _r(r"elif\s+.*status_code\s*==\s*503", "HTTP 503 routing should be in YAML error table",
       "error-policy", False),
    # Config-driven control flow -- mechanism/policy separation violation
    _r(r"if\s+config\.use_streaming", "control flow from config flag makes code untestable",
       "control-flow", True),
    _r(r"if\s+config\.enable_", "enable/disable config flags: control flow anti-pattern",
       "control-flow", True),
]
# fmt: on

# Files to exclude from scanning (test files, config loaders, etc.)
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "test_",  # test files can have some hardcoded values for fixtures
    "_test.py",
    "conftest.py",
    "types.py",  # type definitions OK
    "constants.py",  # constants file is expected, but should be minimal
]


@dataclass
class Violation:
    file: str
    line: int
    match: str
    message: str
    category: str
    is_hard_fail: bool


def should_exclude(path: Path) -> bool:
    name = path.name
    return any(
        excl in str(path) or name.startswith(excl) or name.endswith(excl)
        for excl in EXCLUDE_PATTERNS
    )


def scan_file(path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        for line_idx, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, message, category, is_hard in POLICY_RULES:
                if re.search(pattern, line):
                    violations.append(
                        Violation(
                            file=str(path),
                            line=line_idx,
                            match=line.strip()[:100],
                            message=message,
                            category=category,
                            is_hard_fail=is_hard,
                        )
                    )
    except Exception:
        pass
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Hardcoded policy detector")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--hard-fail-only", action="store_true", help="Exit 1 only for hard violations"
    )
    parser.add_argument(
        "src_dir",
        nargs="?",
        default="amplifier_module_provider_github_copilot",
        help="Source directory to scan",
    )
    args = parser.parse_args()

    src_dir = Path(args.src_dir)
    if not src_dir.exists():
        print(f"ERROR: {src_dir} does not exist", file=sys.stderr)
        return 1

    all_violations: list[Violation] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        if should_exclude(py_file):
            continue
        all_violations.extend(scan_file(py_file))

    hard_violations = [v for v in all_violations if v.is_hard_fail]
    soft_violations = [v for v in all_violations if not v.is_hard_fail]

    def violation_dict(v: Violation) -> dict:
        return {
            "file": v.file,
            "line": v.line,
            "match": v.match,
            "message": v.message,
            "category": v.category,
            "severity": "FAIL" if v.is_hard_fail else "warn",
        }

    if args.json:
        print(
            json.dumps(
                {
                    "hard_violations": [violation_dict(v) for v in hard_violations],
                    "soft_violations": [violation_dict(v) for v in soft_violations],
                    "summary": {
                        "hard_violations": len(hard_violations),
                        "soft_violations": len(soft_violations),
                        "total": len(all_violations),
                    },
                    "status": "FAIL" if hard_violations else ("warn" if soft_violations else "ok"),
                },
                indent=2,
            )
        )
    else:
        print("Hardcoded Policy Check (Three-Medium Architecture)")
        print("=" * 60)
        if not all_violations:
            print("✅  No policy violations found.")
        else:
            by_file: dict[str, list[Violation]] = {}
            for v in all_violations:
                by_file.setdefault(v.file, []).append(v)

            for fpath, file_violations in by_file.items():
                print(f"\n  {fpath}")
                for v in file_violations:
                    marker = "❌ FAIL" if v.is_hard_fail else "⚠️  WARN"
                    print(f"    {marker}  line {v.line}: {v.message}")
                    print(f"            → {v.match}")

        if hard_violations:
            print()
            print("HARD VIOLATIONS (control flow from config -- makes code untestable):")
            for v in hard_violations:
                print(f"  {v.file}:{v.line}: {v.message}")
            print()
            print("These patterns violate Golden Vision V2 §Principle 2.")
            print("See: mydocs/debates/GOLDEN_VISION_V2.md")

        if soft_violations:
            print()
            print(f"SOFT VIOLATIONS ({len(soft_violations)}) -- consider extracting to YAML config")
            print("See Golden Vision V2: 'Policy thresholds as Python constants' anti-pattern.")

    if hard_violations:
        return 1
    if not args.hard_fail_only and soft_violations:
        return 0  # soft violations don't fail by default
    return 0


if __name__ == "__main__":
    sys.exit(main())
