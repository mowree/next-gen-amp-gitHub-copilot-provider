# Health Check Findings

## Build Status
Build: FAILED

### Build Errors
```
All checks passed!
/workspace/amplifier_module_provider_github_copilot/provider.py
  /workspace/amplifier_module_provider_github_copilot/provider.py:86:20 - error: Type of "get" is partially unknown
    Type of "get" is "Overload[(key: Unknown, default: None = None, /) -> (Unknown | None), (key: Unknown, default: Unknown, /) -> Unknown, (key: Unknown, default: _T@get, /) -> (Unknown | _T@get)]" (reportUnknownMemberType)
  /workspace/amplifier_module_provider_github_copilot/provider.py:86:20 - error: Argument type is unknown
    Argument corresponds to parameter "object" in function "__new__" (reportUnknownArgumentType)
2 errors, 0 warnings, 0 informations
```

## Test Status
Tests: FAILING

### Test Output (last 80 lines)
```
    from amplifier_module_provider_github_copilot.provider import (
amplifier_module_provider_github_copilot/__init__.py:28: in <module>
    raise ImportError(
E   ImportError: Required dependency 'github-copilot-sdk' is not installed. Install with:  pip install 'github-copilot-sdk>=0.1.32,<0.2.0'
_________________ ERROR collecting tests/test_sdk_boundary.py __________________
ImportError while importing test module '/workspace/tests/test_sdk_boundary.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/metadata/__init__.py:563: in from_name
    return next(cls.discover(name=name))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   StopIteration

During handling of the above exception, another exception occurred:
amplifier_module_provider_github_copilot/__init__.py:26: in <module>
    _pkg_version("github-copilot-sdk")
/usr/local/lib/python3.11/importlib/metadata/__init__.py:1009: in version
    return distribution(distribution_name).version
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/local/lib/python3.11/importlib/metadata/__init__.py:982: in distribution
    return Distribution.from_name(distribution_name)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/local/lib/python3.11/importlib/metadata/__init__.py:565: in from_name
    raise PackageNotFoundError(name)
E   importlib.metadata.PackageNotFoundError: No package metadata was found for github-copilot-sdk

The above exception was the direct cause of the following exception:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_sdk_boundary.py:15: in <module>
    from amplifier_module_provider_github_copilot.error_translation import (
amplifier_module_provider_github_copilot/__init__.py:28: in <module>
    raise ImportError(
E   ImportError: Required dependency 'github-copilot-sdk' is not installed. Install with:  pip install 'github-copilot-sdk>=0.1.32,<0.2.0'
________________ ERROR collecting tests/test_security_fixes.py _________________
ImportError while importing test module '/workspace/tests/test_security_fixes.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.11/importlib/metadata/__init__.py:563: in from_name
    return next(cls.discover(name=name))
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   StopIteration

During handling of the above exception, another exception occurred:
amplifier_module_provider_github_copilot/__init__.py:26: in <module>
    _pkg_version("github-copilot-sdk")
/usr/local/lib/python3.11/importlib/metadata/__init__.py:1009: in version
    return distribution(distribution_name).version
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/local/lib/python3.11/importlib/metadata/__init__.py:982: in distribution
    return Distribution.from_name(distribution_name)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/local/lib/python3.11/importlib/metadata/__init__.py:565: in from_name
    raise PackageNotFoundError(name)
E   importlib.metadata.PackageNotFoundError: No package metadata was found for github-copilot-sdk

The above exception was the direct cause of the following exception:
/usr/local/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_security_fixes.py:18: in <module>
    from amplifier_module_provider_github_copilot.error_translation import (
amplifier_module_provider_github_copilot/__init__.py:28: in <module>
    raise ImportError(
E   ImportError: Required dependency 'github-copilot-sdk' is not installed. Install with:  pip install 'github-copilot-sdk>=0.1.32,<0.2.0'
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
============================== 11 errors in 0.46s ==============================
```
