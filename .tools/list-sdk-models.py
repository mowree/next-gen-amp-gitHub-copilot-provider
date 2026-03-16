# =============================================================================
# list-sdk-models.py — Query GitHub Copilot SDK for available models and limits
# =============================================================================
#
# PURPOSE:
#   Connects to the GitHub Copilot CLI and fetches the real model catalog
#   including context windows, max tokens, and capabilities. Uses the SDK's
#   list_models() RPC call.
#
# WHEN TO USE:
#   - Verify what models are really available in Copilot
#   - Get actual context_window values for config/models.yaml
#   - Debug model availability issues
#
# CREATED: 2026-03-15 (F-078 investigation)
# MACHINE: Windows/WSL (requires copilot CLI installed and authenticated)
#
# USAGE:
#   python .tools/list-sdk-models.py
#   # or with uv:
#   uv run python .tools/list-sdk-models.py
#
# REQUIREMENTS:
#   - copilot CLI installed and authenticated (copilot --version)
#   - copilot Python SDK installed (pip install github-copilot-sdk)
#
# =============================================================================

import asyncio
import sys


async def main():
    try:
        from copilot import CopilotClient
    except ImportError:
        print("ERROR: copilot SDK not installed")
        print("Install with: pip install github-copilot-sdk")
        sys.exit(1)

    print("=" * 70)
    print("GitHub Copilot SDK Model Discovery")
    print("=" * 70)

    client = CopilotClient()
    try:
        print("\n[1] Starting Copilot client...")
        await client.start()
        print("    ✓ Connected to Copilot CLI")

        print("\n[2] Fetching available models...")
        models = await client.list_models()
        print(f"    ✓ Found {len(models)} models\n")

        print("=" * 70)
        print(f"{'Model ID':<30} {'Context Window':>15} {'Max Output':>12} {'Vision':>8}")
        print("-" * 70)

        for model in models:
            model_id = model.id
            caps = model.capabilities
            limits = caps.limits if caps else None
            supports = caps.supports if caps else None

            context_window = limits.max_context_window_tokens if limits else "N/A"
            max_prompt = limits.max_prompt_tokens if limits else "N/A"
            vision = "Yes" if (supports and supports.vision) else "No"
            reasoning = "Yes" if (supports and supports.reasoning_effort) else "No"

            # Format context window
            if isinstance(context_window, int):
                ctx_str = f"{context_window:,}"
            else:
                ctx_str = str(context_window)

            if isinstance(max_prompt, int):
                max_str = f"{max_prompt:,}"
            else:
                max_str = str(max_prompt)

            print(f"{model_id:<30} {ctx_str:>15} {max_str:>12} {vision:>8}")

            # Print billing/policy info if present
            if model.billing:
                print(f"    └─ Billing multiplier: {model.billing.multiplier}")
            if model.policy:
                print(f"    └─ Policy: {model.policy.state}")
            if model.supported_reasoning_efforts:
                print(f"    └─ Reasoning: {model.supported_reasoning_efforts}")

        print("=" * 70)

        # Summary for config update
        print("\n[3] Config Recommendations for models.yaml:\n")
        for model in models:
            limits = model.capabilities.limits if model.capabilities else None
            ctx = limits.max_context_window_tokens if limits else 128000
            max_out = limits.max_prompt_tokens if limits else 4096
            print(f"  - id: {model.id}")
            print(f"    display_name: \"{model.name}\"")
            print(f"    context_window: {ctx}")
            print(f"    max_output_tokens: {max_out}")
            print()

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("\n[4] Stopping client...")
        await client.stop()
        print("    ✓ Done")


if __name__ == "__main__":
    asyncio.run(main())
