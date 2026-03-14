#!/usr/bin/env python3
import sys
sys.path.insert(0, "/workspace")

# Test imports
print("Testing amplifier_core imports...")
try:
    from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
    print(f"  ProviderInfo: {ProviderInfo}")
    print(f"  ModelInfo: {ModelInfo}")
    print(f"  ChatResponse: {ChatResponse}")
    print(f"  ToolCall: {ToolCall}")
except ImportError as e:
    print(f"  FAILED: {e}")

print()
print("Testing provider module imports...")
try:
    from amplifier_module_provider_github_copilot import mount, GitHubCopilotProvider
    print(f"  mount: {mount}")
    print(f"  GitHubCopilotProvider: {GitHubCopilotProvider}")
except Exception as e:
    print(f"  FAILED: {e}")
    import traceback
    traceback.print_exc()

print()
print("Testing provider instantiation...")
try:
    from amplifier_module_provider_github_copilot.provider import GitHubCopilotProvider
    provider = GitHubCopilotProvider(config=None, coordinator=None)
    print(f"  Provider created: {provider}")
    
    info = provider.get_info()
    print(f"  get_info() returned: {type(info)}")
    print(f"  info.id: {info.id}")
    print(f"  info.display_name: {info.display_name}")
except Exception as e:
    print(f"  FAILED: {e}")
    import traceback
    traceback.print_exc()
