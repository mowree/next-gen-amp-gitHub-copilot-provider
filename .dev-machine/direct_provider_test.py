#!/usr/bin/env python3
"""Direct provider test - bypasses bundle layer entirely.

This test proves the provider code works by:
1. Importing the provider module directly
2. Creating a provider instance with config
3. Calling complete() with a test message
4. Verifying we get a response

If this passes but `amplifier run --bundle` fails, the bug is in the bundle/loader layer.
"""

import asyncio
import logging
import os
import sys

# Enable logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(name)s: %(message)s",
)

# Ensure SDK check is bypassed
os.environ["SKIP_SDK_CHECK"] = "1"


async def test_provider_directly():
    """Test the provider without any Amplifier framework."""
    print("=" * 60)
    print("DIRECT PROVIDER TEST (bypasses bundle layer)")
    print("=" * 60)

    # Step 1: Import the provider
    print("\n[1] Importing provider module...")
    try:
        from amplifier_module_provider_github_copilot.provider import (
            GitHubCopilotProvider,
        )

        print(f"    ✓ Provider class imported: {GitHubCopilotProvider}")
    except Exception as e:
        print(f"    ✗ Import failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 2: Create provider instance
    print("\n[2] Creating provider instance...")
    try:
        config = {"model": "gpt-4o"}
        # Provider takes config and coordinator (optional)
        provider = GitHubCopilotProvider(config=config, coordinator=None)
        print(f"    ✓ Provider created: {provider.name}")
        print(f"    ✓ Provider info: {provider.get_info()}")
    except Exception as e:
        print(f"    ✗ Creation failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Step 3: List models
    print("\n[3] Listing available models...")
    try:
        models = await provider.list_models()
        print(f"    ✓ Models available: {len(models)}")
        for model in models[:5]:  # Show first 5
            print(f"      - {model.id}: {model.display_name}")
        if len(models) > 5:
            print(f"      ... and {len(models) - 5} more")
    except Exception as e:
        print(f"    ✗ list_models() failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        # Don't fail the test - list_models might need auth

    # Step 4: Test complete() with a simple message
    print("\n[4] Testing complete() with a simple message...")
    try:
        from amplifier_core.interfaces import Message

        messages = [
            Message(role="user", content="Say exactly: DIRECT TEST PASSED"),
        ]

        print("    Calling provider.complete()...")
        response = await provider.complete(
            messages=messages,
            model="gpt-4o",
            system="You are a test assistant. Follow instructions exactly.",
        )

        print("    ✓ Response received!")
        print(f"    ✓ Response type: {type(response).__name__}")

        # Check the response content
        if hasattr(response, "content"):
            content = response.content
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, "text"):
                        print(f"    ✓ Response text: {block.text[:100]}...")
            else:
                print(f"    ✓ Response content: {content[:100]}...")

        if hasattr(response, "model"):
            print(f"    ✓ Model used: {response.model}")

        if hasattr(response, "usage"):
            print(f"    ✓ Token usage: {response.usage}")

        return True

    except Exception as e:
        print(f"    ✗ complete() failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run the direct provider test."""
    try:
        success = await test_provider_directly()
        print("\n" + "=" * 60)
        if success:
            print("DIRECT PROVIDER TEST: ✓ PASSED")
            print("Provider works independently of bundle layer!")
        else:
            print("DIRECT PROVIDER TEST: ✗ FAILED")
            print("Provider has issues at the code level.")
        print("=" * 60)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
