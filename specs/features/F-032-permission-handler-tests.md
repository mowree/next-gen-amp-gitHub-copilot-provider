# F-032: Permission Handler Production Path Tests

## Summary
Add unit tests to verify `on_permission_request` handler is present in production `CopilotClientWrapper` initialization path.

## Status
- **Priority**: Critical
- **Layer**: Test
- **Expert Consensus**: bug-hunter + test-coverage identified the gap

## Background
The test fixtures in `conftest.py` include `on_permission_request` handler, but production code in `client.py` does not. Tests pass because they use fixtures, but production will fail.

This spec covers ONLY the tests. The actual fix to `client.py` is in F-033 (pending discussion).

## Changes Required

### 1. New Test File: tests/test_permission_handler.py

```python
"""Tests for on_permission_request handler in production path."""
import pytest
from unittest.mock import patch, MagicMock
from typing import Any


class TestOnPermissionRequestHandler:
    """SDK v0.1.33: CopilotClientWrapper must pass on_permission_request."""

    @pytest.mark.asyncio
    async def test_wrapper_passes_on_permission_request_when_auto_init(self) -> None:
        """Auto-init path must include on_permission_request in client options."""
        captured_options: dict = {}

        class FakeCopilotClient:
            def __init__(self, options: dict) -> None:
                captured_options.update(options)
            async def start(self) -> None:
                pass
            async def create_session(self, cfg: dict) -> MagicMock:
                return MagicMock()

        with patch(
            "amplifier_module_provider_github_copilot.sdk_adapter.client.CopilotClient",
            FakeCopilotClient
        ):
            from amplifier_module_provider_github_copilot.sdk_adapter.client import (
                CopilotClientWrapper
            )
            wrapper = CopilotClientWrapper()
            # Trigger lazy init by accessing _client property
            try:
                async with wrapper.session():
                    pass
            except Exception:
                pass

        assert "on_permission_request" in captured_options, (
            "SDK v0.1.33 requires on_permission_request — missing from auto-init options"
        )
        assert callable(captured_options["on_permission_request"])

    def test_default_permission_handler_exists(self) -> None:
        """A default permission handler function must exist."""
        # Will be implemented based on F-033 discussion outcome
        pass
```

### 2. Add Test for system.notification Classification

Add to `tests/test_streaming.py` or create new `tests/test_event_classification.py`:

```python
def test_system_notification_classified(self) -> None:
    """system.notification must be explicitly classified (not silently unknown)."""
    from amplifier_module_provider_github_copilot.streaming import (
        classify_event, load_event_config, EventClassification
    )
    config = load_event_config()
    result = classify_event("system.notification", config)
    assert result in (EventClassification.DROP, EventClassification.CONSUME), (
        "system.notification should be explicitly DROP or CONSUME, not unknown"
    )
```

## Acceptance Criteria

- [ ] `test_wrapper_passes_on_permission_request_when_auto_init` test exists
- [ ] `test_system_notification_classified` test exists
- [ ] Tests initially FAIL (RED) - proving the gap exists
- [ ] After F-033 implementation, tests pass (GREEN)

## References
- bug-hunter analysis: "The `_default_permission_handler` was added to fixture but never backported to production"
- test-coverage analysis: "No unit test for the auto-init call signature"
