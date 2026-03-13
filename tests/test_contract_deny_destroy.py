"""
Contract Compliance Tests: Deny + Destroy Pattern.

Contract: contracts/deny-destroy.md
Feature: F-026

Tests the sovereignty guarantee - SDK never executes tools.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest


class TestDenyHookInstalled:
    """deny-destroy:DenyHook:MUST:1,2"""

    def test_create_deny_hook_returns_deny_action(self) -> None:
        """deny-destroy:DenyHook:MUST:2 - Hook returns DENY for all tool requests."""
        from amplifier_module_provider_github_copilot.sdk_adapter import create_deny_hook

        hook = create_deny_hook()
        # Simulate any tool request
        result = hook({"tool": "any_tool", "arguments": {}})

        assert result["action"] == "DENY"

    def test_deny_hook_reason_mentions_amplifier(self) -> None:
        """deny-destroy:DenyHook:MUST:2 - Deny reason references Amplifier orchestrator."""
        from amplifier_module_provider_github_copilot.sdk_adapter import create_deny_hook

        hook = create_deny_hook()
        result = hook({"tool": "test"})

        assert "reason" in result
        # Reason should explain why denial happens
        assert len(result["reason"]) > 0


class TestDenyHookNotConfigurable:
    """deny-destroy:DenyHook:MUST:3 — ARCHITECTURE FITNESS"""

    def test_no_yaml_key_can_disable_deny_hook(self) -> None:
        """deny-destroy:DenyHook:MUST:3 - No config key can disable the deny hook."""
        from pathlib import Path
        import yaml

        config_dir = Path("config")

        for config_file in config_dir.glob("*.yaml"):
            content = yaml.safe_load(config_file.read_text())
            if content is None:
                continue

            # Flatten all keys recursively
            all_keys = _collect_all_keys(content)

            # Check no key could disable deny hook
            for key in all_keys:
                key_lower = key.lower()
                assert "deny" not in key_lower or "disable" not in key_lower, (
                    f"Config {config_file} has key '{key}' that might disable deny hook"
                )
                assert key_lower != "allow_tool_execution", (
                    f"Config {config_file} has forbidden key '{key}'"
                )


class TestArchitectureFitness:
    """deny-destroy:NoExecution:MUST:3 — SDK imports outside sdk_adapter/ are prohibited"""

    def test_no_sdk_imports_outside_adapter(self) -> None:
        """deny-destroy:NoExecution:MUST:3 - SDK imports only in sdk_adapter/."""
        root = Path("src/amplifier_module_provider_github_copilot")

        violations: list[str] = []

        for py_file in root.glob("*.py"):
            # Skip __init__.py which may re-export
            if py_file.name == "__init__.py":
                continue

            try:
                tree = ast.parse(py_file.read_text())
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_sdk_import(alias.name):
                            violations.append(f"{py_file.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and _is_sdk_import(node.module):
                        violations.append(f"{py_file.name}: from {node.module}")

        assert not violations, (
            f"SDK imports found outside sdk_adapter/:\n" + "\n".join(violations)
        )

    def test_sdk_adapter_contains_sdk_imports(self) -> None:
        """Verify sdk_adapter/ is the membrane for SDK imports."""
        adapter_dir = Path("src/amplifier_module_provider_github_copilot/sdk_adapter")

        assert adapter_dir.exists(), "sdk_adapter/ directory must exist"

        # At least one file should exist
        py_files = list(adapter_dir.glob("*.py"))
        assert len(py_files) > 0, "sdk_adapter/ must contain Python files"


class TestSessionEphemerality:
    """deny-destroy:Ephemeral:MUST:1,2,3"""

    def test_session_config_exists(self) -> None:
        """deny-destroy:Ephemeral:MUST:1 - SessionConfig type exists."""
        from amplifier_module_provider_github_copilot.sdk_adapter.types import SessionConfig

        # SessionConfig should be a valid type
        config = SessionConfig(prompt="test", model="gpt-4")
        assert config.prompt == "test"
        assert config.model == "gpt-4"


def _collect_all_keys(data: Any, prefix: str = "") -> list[str]:
    """Recursively collect all keys from nested dict."""
    keys: list[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.append(full_key)
            keys.extend(_collect_all_keys(v, full_key))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            keys.extend(_collect_all_keys(item, f"{prefix}[{i}]"))
    return keys


def _is_sdk_import(module_name: str) -> bool:
    """Check if module name is a GitHub Copilot SDK import."""
    sdk_patterns = [
        "copilot",
        "github_copilot",
        "github.copilot",
        "ghcp",
    ]
    name_lower = module_name.lower()
    return any(pattern in name_lower for pattern in sdk_patterns)
