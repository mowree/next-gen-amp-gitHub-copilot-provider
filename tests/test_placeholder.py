"""
Placeholder test to verify toolchain works.

This test will be replaced by contract compliance tests during Phase 1.
"""


def test_toolchain_works() -> None:
    """Verify the test toolchain is functional."""
    assert True, "Toolchain verification passed"


def test_version_exists() -> None:
    """Verify the package can be imported and has a version."""
    from amplifier_module_provider_github_copilot import __version__

    assert __version__ == "0.1.0"
