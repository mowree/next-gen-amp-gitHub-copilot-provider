#!/usr/bin/env python3
"""Provider info and dependency exposure utility.

Shows:
1. Active provider name and version
2. Which provider source (local vs published)
3. Amplifier version
4. All upstream dependency versions
5. Python environment info

Usage:
  python provider-info.py                    # Show all info
  python provider-info.py --json             # JSON output for parsing
  python provider-info.py --deps-only        # Upstream deps only

"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pkg_resources


def get_installed_version(package_name: str) -> str | None:
    """Get installed version of a package."""
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None


def is_local_provider() -> bool:
    """Check if provider is installed as editable (local)."""
    try:
        dist = pkg_resources.get_distribution(
            "amplifier-module-provider-github-copilot"
        )
        # Editable installs have .egg-link or are in development mode
        return hasattr(dist, "_path") or "egg-link" in str(dist._egg_info)
    except Exception:
        return False


def get_provider_location() -> str:
    """Get provider installation location."""
    try:
        dist = pkg_resources.get_distribution(
            "amplifier-module-provider-github-copilot"
        )
        location = dist.location
        # Check if it's in /workspace (local development)
        if "/workspace" in location:
            return "local (editable)"
        return f"published ({location})"
    except Exception:
        return "unknown"


def get_provider_info() -> Dict[str, Any]:
    """Get provider information."""
    return {
        "name": "github-copilot",
        "module": "amplifier-module-provider-github-copilot",
        "version": get_installed_version("amplifier-module-provider-github-copilot"),
        "location": get_provider_location(),
        "is_local": is_local_provider(),
    }


def get_amplifier_info() -> Dict[str, Any]:
    """Get Amplifier core information."""
    return {
        "amplifier-core": get_installed_version("amplifier-core"),
        "amplifier-cli": get_installed_version("amplifier"),
    }


def get_sdk_info() -> Dict[str, Any]:
    """Get GitHub Copilot SDK information."""
    return {
        "github-copilot-sdk": get_installed_version("github-copilot-sdk"),
    }


def get_all_upstream_deps() -> Dict[str, Any]:
    """Get versions of all upstream dependencies."""
    deps = {
        "Provider": get_provider_info(),
        "Amplifier": get_amplifier_info(),
        "SDK": get_sdk_info(),
        "Utilities": {
            "pyyaml": get_installed_version("pyyaml"),
        },
        "Python": {
            "version": (
                f"{sys.version_info.major}.{sys.version_info.minor}"
                f".{sys.version_info.micro}"
            ),
            "executable": sys.executable,
        },
    }
    return deps


def format_text_output(deps: Dict[str, Any]) -> str:
    """Format dependency info as human-readable text."""
    lines = []
    lines.append("=" * 70)
    lines.append("PROVIDER & DEPENDENCY INFORMATION")
    lines.append("=" * 70)

    # Provider section
    provider = deps["Provider"]
    lines.append("\n📦 PROVIDER")
    lines.append(f"  Name:     {provider['name']}")
    lines.append(f"  Module:   {provider['module']}")
    lines.append(f"  Version:  {provider['version']}")
    lines.append(f"  Location: {provider['location']}")
    provider_type = "LOCAL (editable)" if provider["is_local"] else "PUBLISHED"
    lines.append(f"  Type:     {provider_type}")

    # Amplifier section
    lines.append("\n⚙️  AMPLIFIER ECOSYSTEM")
    amp = deps["Amplifier"]
    for key, value in amp.items():
        lines.append(f"  {key:.<35} {value}")

    # SDK section
    lines.append("\n🔧 GITHUB COPILOT SDK")
    sdk = deps["SDK"]
    for key, value in sdk.items():
        lines.append(f"  {key:.<35} {value}")

    # Utilities
    lines.append("\n📚 UTILITIES")
    utils = deps["Utilities"]
    for key, value in utils.items():
        lines.append(f"  {key:.<35} {value}")

    # Python
    lines.append("\n🐍 PYTHON ENVIRONMENT")
    python_info = deps["Python"]
    for key, value in python_info.items():
        lines.append(f"  {key:.<35} {value}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Show provider and dependency information"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--deps-only", action="store_true", help="Show only upstream dependencies"
    )
    parser.add_argument(
        "--provider-only", action="store_true", help="Show only provider info"
    )

    args = parser.parse_args()

    deps = get_all_upstream_deps()

    if args.json:
        print(json.dumps(deps, indent=2))
    elif args.provider_only:
        provider = deps["Provider"]
        print(f"Provider: {provider['name']} v{provider['version']}")
        print(f"Location: {provider['location']}")
        provider_type = "LOCAL" if provider["is_local"] else "PUBLISHED"
        print(f"Type:     {provider_type}")
    elif args.deps_only:
        # Show only upstream, not provider
        filtered = {k: v for k, v in deps.items() if k != "Provider"}
        print(json.dumps(filtered, indent=2))
    else:
        print(format_text_output(deps))

    return 0


if __name__ == "__main__":
    sys.exit(main())
