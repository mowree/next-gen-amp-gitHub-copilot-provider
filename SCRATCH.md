# Health Check Findings

## Build Status
Build: FAILED

### Build Errors
```
  /workspace/src/amplifier_module_provider_github_copilot/provider.py:283:15 - error: Return type, "list[Unknown]", is partially unknown (reportUnknownParameterType)
  /workspace/src/amplifier_module_provider_github_copilot/provider.py:290:16 - error: Return type, "list[Unknown]", is partially unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/provider.py:309:15 - error: Return type is unknown (reportUnknownParameterType)
  /workspace/src/amplifier_module_provider_github_copilot/provider.py:356:16 - error: Type of "to_chat_response" is partially unknown
    Type of "to_chat_response" is "() -> Unknown" (reportUnknownMemberType)
  /workspace/src/amplifier_module_provider_github_copilot/provider.py:356:16 - error: Return type is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/provider.py:383:9 - error: Return type, "list[Unknown]", is partially unknown (reportUnknownParameterType)
  /workspace/src/amplifier_module_provider_github_copilot/provider.py:390:16 - error: Return type, "list[Unknown]", is partially unknown (reportUnknownVariableType)
/workspace/src/amplifier_module_provider_github_copilot/sdk_adapter/client.py
  /workspace/src/amplifier_module_provider_github_copilot/sdk_adapter/client.py:23:60 - error: Type of "translate_sdk_error" is partially unknown
    Type of "translate_sdk_error" is "(exc: Exception, config: ErrorConfig, *, provider: str = "github-copilot", model: str | None = None) -> Unknown" (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/sdk_adapter/client.py:198:57 - error: "ProviderUnavailableError" is unknown import symbol (reportAttributeAccessIssue)
  /workspace/src/amplifier_module_provider_github_copilot/sdk_adapter/client.py:198:57 - error: Type of "ProviderUnavailableError" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/sdk_adapter/client.py:200:25 - error: Type of "err" is unknown (reportUnknownVariableType)
/workspace/src/amplifier_module_provider_github_copilot/streaming.py
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:20:10 - error: Import "amplifier_core" could not be resolved (reportMissingImports)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:20:32 - error: Type of "ChatResponse" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:109:9 - error: Return type is unknown (reportUnknownParameterType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:120:14 - error: Import "amplifier_core" could not be resolved (reportMissingImports)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:121:13 - error: Type of "ChatResponse" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:122:13 - error: Type of "TextBlock" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:123:13 - error: Type of "ThinkingBlock" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:124:13 - error: Type of "ToolCall" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:125:13 - error: Type of "Usage" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:128:9 - error: Type of "content" is partially unknown
    Type of "content" is "list[Unknown]" (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:132:13 - error: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:132:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "append" (reportUnknownArgumentType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:136:13 - error: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:136:28 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "append" (reportUnknownArgumentType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:141:13 - error: Type of "tool_calls" is partially unknown
    Type of "tool_calls" is "list[Unknown]" (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/streaming.py:155:13 - error: Type of "usage" is unknown (reportUnknownVariableType)
/workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:22:6 - error: Import "amplifier_core" could not be resolved (reportMissingImports)
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:22:28 - error: Type of "ToolCall" is unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:34:5 - error: Return type, "list[Unknown]", is partially unknown (reportUnknownParameterType)
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:56:16 - error: Return type, "list[Unknown]", is partially unknown (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:58:5 - error: Type of "result" is partially unknown
    Type of "result" is "list[Unknown]" (reportUnknownVariableType)
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:83:9 - error: Type of "append" is partially unknown
    Type of "append" is "(object: Unknown, /) -> None" (reportUnknownMemberType)
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:84:13 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "append" (reportUnknownArgumentType)
  /workspace/src/amplifier_module_provider_github_copilot/tool_parsing.py:91:12 - error: Return type, "list[Unknown]", is partially unknown (reportUnknownVariableType)
83 errors, 0 warnings, 0 informations
```

## Test Status
Tests: FAILING

### Test Output (last 80 lines)
```
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_f037_observability.py:19: in <module>
    from amplifier_module_provider_github_copilot.error_translation import (
src/amplifier_module_provider_github_copilot/__init__.py:36: in <module>
    from .provider import GitHubCopilotProvider, ModelInfo, ProviderInfo
src/amplifier_module_provider_github_copilot/provider.py:30: in <module>
    from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
E   ModuleNotFoundError: No module named 'amplifier_core'
__________________ ERROR collecting tests/test_integration.py __________________
ImportError while importing test module '/workspace/tests/test_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_integration.py:18: in <module>
    from amplifier_module_provider_github_copilot.error_translation import (
src/amplifier_module_provider_github_copilot/__init__.py:36: in <module>
    from .provider import GitHubCopilotProvider, ModelInfo, ProviderInfo
src/amplifier_module_provider_github_copilot/provider.py:30: in <module>
    from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
E   ModuleNotFoundError: No module named 'amplifier_core'
___________________ ERROR collecting tests/test_provider.py ____________________
ImportError while importing test module '/workspace/tests/test_provider.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_provider.py:10: in <module>
    from amplifier_module_provider_github_copilot.provider import (
src/amplifier_module_provider_github_copilot/__init__.py:36: in <module>
    from .provider import GitHubCopilotProvider, ModelInfo, ProviderInfo
src/amplifier_module_provider_github_copilot/provider.py:30: in <module>
    from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
E   ModuleNotFoundError: No module named 'amplifier_core'
_________________ ERROR collecting tests/test_sdk_boundary.py __________________
ImportError while importing test module '/workspace/tests/test_sdk_boundary.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_sdk_boundary.py:15: in <module>
    from amplifier_module_provider_github_copilot.error_translation import (
src/amplifier_module_provider_github_copilot/__init__.py:36: in <module>
    from .provider import GitHubCopilotProvider, ModelInfo, ProviderInfo
src/amplifier_module_provider_github_copilot/provider.py:30: in <module>
    from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
E   ModuleNotFoundError: No module named 'amplifier_core'
________________ ERROR collecting tests/test_security_fixes.py _________________
ImportError while importing test module '/workspace/tests/test_security_fixes.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_security_fixes.py:18: in <module>
    from amplifier_module_provider_github_copilot.error_translation import (
src/amplifier_module_provider_github_copilot/__init__.py:36: in <module>
    from .provider import GitHubCopilotProvider, ModelInfo, ProviderInfo
src/amplifier_module_provider_github_copilot/provider.py:30: in <module>
    from amplifier_core import ChatResponse, ModelInfo, ProviderInfo, ToolCall
E   ModuleNotFoundError: No module named 'amplifier_core'
=========================== short test summary info ============================
ERROR tests/test_completion.py
ERROR tests/test_contract_errors.py
ERROR tests/test_contract_protocol.py
ERROR tests/test_contract_streaming.py
ERROR tests/test_f035_error_types.py
ERROR tests/test_f036_error_context.py
ERROR tests/test_f037_observability.py
ERROR tests/test_integration.py
ERROR tests/test_provider.py
ERROR tests/test_sdk_boundary.py
ERROR tests/test_security_fixes.py
!!!!!!!!!!!!!!!!!!! Interrupted: 11 errors during collection !!!!!!!!!!!!!!!!!!!
======================== 1 skipped, 11 errors in 0.32s =========================
```
