#!/usr/bin/env python3
"""Monkey-patch for MockCoordinator.mount() bug in amplifier-core.

BUG: MockCoordinator.mount() does `await super().mount()` on a synchronous
Rust method, causing the mount to not register properly.

EVIDENCE:
- Direct Rust mount: coord.mount_points = {'providers': {'test': <Provider>}}
- Through MockCoordinator: coord.mount_points = {}

This patch fixes the async/sync mismatch until amplifier-core is updated.

See: https://github.com/microsoft/amplifier-core/issues/XXX (TODO: file bug)
"""

import amplifier_core.testing as testing


def apply_patch():
    """Apply the monkey-patch to fix MockCoordinator.mount()."""

    async def fixed_mount(self, mount_point: str, module, name: str | None = None):
        """Fixed mount that calls Rust synchronously, not async."""
        # Track in Python-side history (same as original)
        self.mount_history.append(
            {
                "mount_point": mount_point,
                "module": module,
                "name": name,
            }
        )
        # Call Rust method SYNCHRONOUSLY - don't await!
        # The Rust mount() returns py.None(), not a coroutine
        from amplifier_core import ModuleCoordinator

        ModuleCoordinator.mount(self, mount_point, module, name=name)

    testing.MockCoordinator.mount = fixed_mount
    print("  ✓ MockCoordinator.mount() patched (async/sync fix)")


if __name__ == "__main__":
    apply_patch()
