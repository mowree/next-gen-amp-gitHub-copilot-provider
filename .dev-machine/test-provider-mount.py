#!/usr/bin/env python3
"""Test provider mount directly - run inside Docker container."""

import asyncio
import os
import sys
import traceback

print(f"GITHUB_TOKEN set: {bool(os.environ.get('GITHUB_TOKEN'))}")
print(f"Token length: {len(os.environ.get('GITHUB_TOKEN', ''))}")
print()

try:
    from amplifier_module_provider_github_copilot import mount

    print("✓ Import OK")

    # Create a mock coordinator
    class MockCoordinator:
        def __init__(self):
            self.mounted = []

        async def mount(self, category, provider, name):
            print(f"  mount() called: category={category}, name={name}")
            self.mounted.append((category, name, provider))

    async def test_mount():
        coordinator = MockCoordinator()
        print("Calling mount()...")
        cleanup = await mount(coordinator, config=None)
        print(f"✓ mount() returned: {cleanup}")
        print(f"✓ Mounted: {len(coordinator.mounted)} providers")

        # Try to get provider info
        if coordinator.mounted:
            _, _, provider = coordinator.mounted[0]
            info = provider.get_info()
            print(f"✓ Provider info: id={info.id}, display_name={info.display_name}")
            print(f"✓ Capabilities: {info.capabilities}")
            print()
            print("SUCCESS: Provider mounted and configured correctly")
        else:
            print("FAILED: No providers were mounted")
            sys.exit(1)

    asyncio.run(test_mount())

except Exception as e:
    print(f"FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)
