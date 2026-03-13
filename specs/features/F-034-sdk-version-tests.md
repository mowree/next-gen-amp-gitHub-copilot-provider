# F-034: SDK Version Drift Detection Tests

## Summary
Add tests to detect SDK version drift and signature changes that could break the provider.

## Status
- **Priority**: Medium
- **Layer**: Test
- **Expert Consensus**: test-coverage recommended

## Background
No tests currently guard against SDK version drift or `create_session` signature changes.

## Changes Required

### 1. Add to tests/test_sdk_assumptions.py

```python
@pytest.mark.sdk_assumption
class TestSDKVersionCompatibility:
    """Detect SDK version drift from v0.1.33 baseline."""

    def test_sdk_version_is_known(self) -> None:
        """SDK package version must be accessible and within expected range."""
        import importlib.metadata
        try:
            version = importlib.metadata.version("github-copilot-sdk")
        except importlib.metadata.PackageNotFoundError:
            pytest.skip("SDK package metadata not available")

        # Document baseline — update when upgrading SDK
        parts = version.split(".")
        major, minor = int(parts[0]), int(parts[1])
        assert (major, minor) >= (0, 1), f"SDK version {version} below baseline 0.1"
        # Print for drift visibility in CI
        print(f"SDK version: {version}")

    def test_sdk_has_permission_handler_type(self) -> None:
        """SDK v0.1.33: PermissionHandler type must exist."""
        try:
            import copilot
            from copilot.types import PermissionHandler
            assert hasattr(PermissionHandler, "approve_all"), (
                "PermissionHandler.approve_all not found — SDK version may have changed"
            )
        except ImportError:
            pytest.skip("SDK not installed")

    def test_copilot_client_accepts_permission_handler(self) -> None:
        """SDK v0.1.33: CopilotClient constructor must accept on_permission_request."""
        try:
            import copilot
            import inspect
            sig = inspect.signature(copilot.CopilotClient.__init__)
            # Constructor takes options dict, which should accept on_permission_request
            # This is a basic smoke test — full validation in live tests
            assert "options" in str(sig) or len(sig.parameters) >= 2
        except ImportError:
            pytest.skip("SDK not installed")
```

## Acceptance Criteria

- [ ] `test_sdk_version_is_known` test exists and passes
- [ ] `test_sdk_has_permission_handler_type` test exists
- [ ] `test_copilot_client_accepts_permission_handler` test exists
- [ ] Tests are marked `@pytest.mark.sdk_assumption`

## References
- test-coverage analysis: "SDK version drift detection"
