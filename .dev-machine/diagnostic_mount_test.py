#!/usr/bin/env python3
"""Diagnostic mount test for shadow testing.

Runs mount() with a mock coordinator INSIDE Docker to catch errors
before they get swallowed by Amplifier's session initialization.
"""

import asyncio
import logging
import sys
import traceback

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


class MockCoordinator:
    """Mock coordinator that records mount() calls."""

    def __init__(self):
        self.mounted = {}

    async def mount(self, mount_point, obj, name=None):
        self.mounted[mount_point] = (obj, name)
        print(f'  coordinator.mount("{mount_point}", {type(obj).__name__}, name="{name}") OK')


async def test():
    """Test mount() function with mock coordinator."""
    try:
        from amplifier_module_provider_github_copilot import mount

        print("  mount function imported OK")

        coord = MockCoordinator()
        result = await mount(coord, {"model": "gpt-4o"})
        print(f"  mount() returned: {type(result).__name__ if result else None}")

        if "providers" in coord.mounted:
            provider, name = coord.mounted["providers"]
            print(f"  Provider mounted: {name}")
            print(f"  Provider.name: {provider.name}")
            info = provider.get_info()
            print(f"  get_info(): id={info.id}, display_name={info.display_name}")
            print("  DIAGNOSTIC: mount() works correctly")
            return 0
        else:
            print("  ERROR: Provider not mounted to coordinator")
            return 1
    except Exception as e:
        print(f"  DIAGNOSTIC FAILURE: {type(e).__name__}: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(test()))
