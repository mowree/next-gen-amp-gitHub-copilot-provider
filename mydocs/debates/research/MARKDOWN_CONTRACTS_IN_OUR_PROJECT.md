# Markdown Contracts in provider-github-copilot

**Purpose:** How markdown contracts drive both tests AND code behaviors in our architecture  
**Status:** Implementation specification  
**References:** Patterns borrowed from Gauge, W3C WPT, RFC 2119, Kubernetes KEPs

---

## The Dual Role of Markdown Contracts

Markdown contracts in this project serve **two active purposes**:

| Role | Mechanism | Output |
|------|-----------|--------|
| **Test Generation** | Parse MUST/SHOULD/MAY clauses | `tests/contract_*.py` |
| **AI Implementation Guide** | Context injection via @mention | `modules/provider-core/*.py` |

Both roles are **active** — the markdown is not documentation, it is specification.

---

## 1. Contract File Structure

### Directory Layout

```
contracts/
├── provider-protocol.md      # The 5-method Provider Protocol
├── sdk-boundary.md           # What crosses the membrane
├── error-hierarchy.md        # Domain exception taxonomy
├── event-vocabulary.md       # The 6 stable domain events
├── deny-destroy.md           # Sovereignty pattern (non-negotiable)
├── streaming-contract.md     # Delta accumulation rules
└── behaviors.md              # Cross-cutting requirements
```

### Contract File Format

Based on [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt) keywords + structured markdown:

```markdown
# Contract: {name}

## Version
- **Current:** 1.0
- **Config Reference:** config/{related}.yaml
- **Module Reference:** modules/provider-core/{module}.py

## Invariants

### {Invariant Name}
- **MUST:** {required behavior}
- **MUST NOT:** {prohibited behavior}
- **SHOULD:** {recommended behavior}
- **MAY:** {optional behavior}

## Behavioral Requirements

### {Requirement Name}
- **Precondition:** {what must be true before}
- **Postcondition:** {what must be true after}
- **Invariant:** {what must always be true}

## Test Anchors

Each MUST clause has a unique anchor: `{contract}:{section}:{clause_number}`

Example: `error-hierarchy:CopilotAuthError:MUST:1`
```

---

## 2. Example Contract: error-hierarchy.md

This is a complete contract file following the specification:

```markdown
# Contract: Error Hierarchy

## Version
- **Current:** 1.0
- **Config Reference:** config/errors.yaml
- **Module Reference:** modules/provider-core/error_translation.py

---

## Domain Exception Taxonomy

```
CopilotProviderError (base)
├── CopilotAuthError
├── CopilotRateLimitError
├── CopilotTimeoutError
├── CopilotContentFilterError
├── CopilotSessionError
├── CopilotModelNotFoundError
├── CopilotSubprocessError
└── CopilotCircuitBreakerError
```

---

## Invariants

### Base Exception Contract
- **MUST:** All domain exceptions inherit from `CopilotProviderError`
- **MUST:** All domain exceptions have a `retryable: bool` attribute
- **MUST:** All domain exceptions have an `original: Exception | None` attribute
- **MUST NOT:** Domain exceptions expose SDK-specific information in their message

### CopilotAuthError
- **MUST:** Have `retryable=False` always
- **MUST:** Be raised for SDK exceptions matching: `AuthenticationError`, `InvalidTokenError`, `PermissionDeniedError`
- **MUST:** Be raised for HTTP status codes: 401, 403
- **MUST NOT:** Be retried under any circumstances

### CopilotRateLimitError
- **MUST:** Have `retryable=True`
- **MUST:** Extract `retry_after` from SDK exception when available
- **MUST:** Be raised for SDK exceptions matching: `RateLimitError`, `QuotaExceededError`
- **MUST:** Be raised for HTTP status codes: 429
- **SHOULD:** Include the `retry_after` value in the exception attributes

### CopilotTimeoutError
- **MUST:** Have `retryable=True`
- **MUST:** Be raised for SDK exceptions matching: `TimeoutError`, `RequestTimeoutError`
- **MUST:** Be raised for `asyncio.TimeoutError`
- **SHOULD:** Include the configured timeout value in the message

### CopilotContentFilterError
- **MUST:** Have `retryable=False`
- **MUST:** Be raised for SDK exceptions matching: `ContentFilterError`, `SafetyError`
- **MUST NOT:** Include filtered content in the exception message

### CopilotSessionError
- **MUST:** Have `retryable=True`
- **MUST:** Be raised for SDK exceptions matching: `SessionCreateError`, `SessionDestroyError`

### CopilotModelNotFoundError
- **MUST:** Have `retryable=False`
- **MUST:** Be raised for SDK exceptions matching: `ModelNotFoundError`, `ModelUnavailableError`
- **SHOULD:** Include the requested model name in the message

### CopilotSubprocessError
- **MUST:** Have `retryable=True`
- **MUST:** Be raised for SDK exceptions matching: `ConnectionError`, `ProcessExitedError`
- **MUST:** Be raised for stdlib `ConnectionRefusedError`

### CopilotCircuitBreakerError
- **MUST:** Have `retryable=False`
- **MUST:** Be raised when turn limit exceeded
- **MUST NOT:** Be raised for normal completion

---

## Behavioral Requirements

### Translation Function Contract
- **Precondition:** Input is a caught exception from SDK or stdlib
- **Postcondition:** Returns exactly one domain exception
- **Invariant:** The function MUST NOT raise; it always returns a domain exception
- **Invariant:** The original exception MUST be preserved in the `.original` attribute

### Config-Driven Matching
- **MUST:** Match SDK exceptions using config/errors.yaml patterns
- **MUST:** Fall through to `CopilotProviderError(retryable=False)` for unknown exceptions
- **MUST NOT:** Hardcode exception types in Python (use config)

---

## Test Anchors

| Anchor | Clause |
|--------|--------|
| `error-hierarchy:Base:MUST:1` | All inherit from CopilotProviderError |
| `error-hierarchy:Base:MUST:2` | All have retryable attribute |
| `error-hierarchy:Base:MUST:3` | All have original attribute |
| `error-hierarchy:CopilotAuthError:MUST:1` | retryable=False always |
| `error-hierarchy:CopilotAuthError:MUST:2` | Raised for AuthenticationError |
| `error-hierarchy:CopilotRateLimitError:MUST:1` | retryable=True |
| `error-hierarchy:CopilotRateLimitError:MUST:2` | Extract retry_after |
| `error-hierarchy:Translation:MUST:1` | Function never raises |
| `error-hierarchy:Translation:MUST:2` | Original preserved |
| `error-hierarchy:Config:MUST:1` | Use config patterns |
| `error-hierarchy:Config:MUST:2` | Fallback to CopilotProviderError |
```

---

## 3. Test Generation from Contracts

### Pattern: W3C Web Platform Tests Style

Borrowed from [W3C WPT](https://github.com/web-platform-tests/wpt) where each test references a spec section:

```python
# tests/contract/test_error_hierarchy.py

"""
Contract compliance tests for: contracts/error-hierarchy.md
Generated from MUST clauses.
"""

import pytest
from provider_core.exceptions import (
    CopilotProviderError,
    CopilotAuthError,
    CopilotRateLimitError,
    CopilotTimeoutError,
)
from provider_core.error_translation import translate_sdk_error
from provider_core.config import load_error_config


class TestBaseExceptionContract:
    """Contract: error-hierarchy.md → Base Exception Contract"""

    @pytest.mark.contract("error-hierarchy:Base:MUST:1")
    def test_all_exceptions_inherit_from_base(self):
        """All domain exceptions inherit from CopilotProviderError."""
        for exc_class in [
            CopilotAuthError,
            CopilotRateLimitError,
            CopilotTimeoutError,
            # ... all other domain exceptions
        ]:
            assert issubclass(exc_class, CopilotProviderError)

    @pytest.mark.contract("error-hierarchy:Base:MUST:2")
    def test_all_exceptions_have_retryable_attribute(self):
        """All domain exceptions have a retryable: bool attribute."""
        for exc_class in [CopilotAuthError, CopilotRateLimitError]:
            exc = exc_class("test")
            assert hasattr(exc, "retryable")
            assert isinstance(exc.retryable, bool)

    @pytest.mark.contract("error-hierarchy:Base:MUST:3")
    def test_all_exceptions_have_original_attribute(self):
        """All domain exceptions have an original: Exception | None attribute."""
        original = ValueError("original error")
        exc = CopilotAuthError("test", original=original)
        assert exc.original is original


class TestCopilotAuthErrorContract:
    """Contract: error-hierarchy.md → CopilotAuthError"""

    @pytest.mark.contract("error-hierarchy:CopilotAuthError:MUST:1")
    def test_auth_error_not_retryable(self):
        """CopilotAuthError MUST have retryable=False always."""
        exc = CopilotAuthError("authentication failed")
        assert exc.retryable is False

    @pytest.mark.contract("error-hierarchy:CopilotAuthError:MUST:2")
    @pytest.mark.parametrize("sdk_error_type", [
        "AuthenticationError",
        "InvalidTokenError", 
        "PermissionDeniedError",
    ])
    def test_auth_error_raised_for_sdk_patterns(self, sdk_error_type):
        """CopilotAuthError MUST be raised for SDK auth errors."""
        config = load_error_config()
        sdk_error = create_mock_sdk_error(sdk_error_type)
        result = translate_sdk_error(sdk_error, config)
        assert isinstance(result, CopilotAuthError)


class TestCopilotRateLimitErrorContract:
    """Contract: error-hierarchy.md → CopilotRateLimitError"""

    @pytest.mark.contract("error-hierarchy:CopilotRateLimitError:MUST:1")
    def test_rate_limit_error_is_retryable(self):
        """CopilotRateLimitError MUST have retryable=True."""
        exc = CopilotRateLimitError("rate limited")
        assert exc.retryable is True

    @pytest.mark.contract("error-hierarchy:CopilotRateLimitError:MUST:2")
    def test_rate_limit_extracts_retry_after(self):
        """CopilotRateLimitError MUST extract retry_after from SDK."""
        config = load_error_config()
        sdk_error = create_mock_sdk_error(
            "RateLimitError", 
            message="Rate limited. Retry after 30 seconds."
        )
        result = translate_sdk_error(sdk_error, config)
        assert isinstance(result, CopilotRateLimitError)
        assert result.retry_after == 30


class TestTranslationFunctionContract:
    """Contract: error-hierarchy.md → Translation Function Contract"""

    @pytest.mark.contract("error-hierarchy:Translation:MUST:1")
    def test_translation_never_raises(self):
        """translate_sdk_error() MUST NOT raise; it always returns."""
        config = load_error_config()
        # Even for completely unknown exceptions
        weird_error = type("WeirdError", (Exception,), {})("weird")
        result = translate_sdk_error(weird_error, config)
        assert isinstance(result, CopilotProviderError)

    @pytest.mark.contract("error-hierarchy:Translation:MUST:2")
    def test_translation_preserves_original(self):
        """translate_sdk_error() MUST preserve original in .original."""
        config = load_error_config()
        original = ValueError("the original")
        result = translate_sdk_error(original, config)
        assert result.original is original


class TestConfigDrivenMatchingContract:
    """Contract: error-hierarchy.md → Config-Driven Matching"""

    @pytest.mark.contract("error-hierarchy:Config:MUST:1")
    def test_matching_uses_config_patterns(self):
        """Matching MUST use config/errors.yaml patterns."""
        config = load_error_config()
        # Config says AuthenticationError → CopilotAuthError
        assert any(
            "AuthenticationError" in m.get("sdk_patterns", [])
            for m in config["error_mappings"]
        )

    @pytest.mark.contract("error-hierarchy:Config:MUST:2")
    def test_unknown_exception_falls_through(self):
        """Unknown exceptions MUST fall through to CopilotProviderError(retryable=False)."""
        config = load_error_config()
        unknown = type("UnknownSDKError", (Exception,), {})("unknown")
        result = translate_sdk_error(unknown, config)
        assert type(result) is CopilotProviderError  # Exact type, not subclass
        assert result.retryable is False
```

### The pytest Marker for Contract Traceability

```python
# tests/conftest.py

import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers", 
        "contract(anchor): marks test as verifying a specific contract clause"
    )

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Add contract reference to test report."""
    if call.when == "call":
        marker = item.get_closest_marker("contract")
        if marker:
            item.user_properties.append(("contract", marker.args[0]))
```

### Contract Coverage Report

Borrowed from [Gauge's specification reporting](https://docs.gauge.org/):

```python
# scripts/contract_coverage.py

"""
Generate a report showing which contract clauses have tests.
"""

import re
from pathlib import Path

def extract_must_clauses(contract_file: Path) -> list[str]:
    """Parse MUST clauses from a contract markdown file."""
    content = contract_file.read_text()
    clauses = []
    
    current_section = None
    clause_number = 0
    
    for line in content.split("\n"):
        if line.startswith("### "):
            current_section = line[4:].strip()
            clause_number = 0
        elif "**MUST:**" in line or "- **MUST:**" in line:
            clause_number += 1
            anchor = f"{contract_file.stem}:{current_section}:MUST:{clause_number}"
            clauses.append(anchor)
    
    return clauses

def find_tested_clauses(test_dir: Path) -> set[str]:
    """Find all contract anchors referenced in tests."""
    tested = set()
    for test_file in test_dir.glob("**/test_*.py"):
        content = test_file.read_text()
        matches = re.findall(r'@pytest\.mark\.contract\("([^"]+)"\)', content)
        tested.update(matches)
    return tested

def main():
    contracts_dir = Path("contracts")
    tests_dir = Path("tests/contract")
    
    all_clauses = []
    for contract in contracts_dir.glob("*.md"):
        all_clauses.extend(extract_must_clauses(contract))
    
    tested = find_tested_clauses(tests_dir)
    
    print("# Contract Coverage Report\n")
    print(f"Total MUST clauses: {len(all_clauses)}")
    print(f"Tested clauses: {len(tested)}")
    print(f"Coverage: {len(tested) / len(all_clauses) * 100:.1f}%\n")
    
    untested = set(all_clauses) - tested
    if untested:
        print("## Untested Clauses\n")
        for clause in sorted(untested):
            print(f"- [ ] {clause}")
```

---

## 4. AI Implementation Guidance

### Pattern: Context Injection via @mention

When an AI agent (Amplifier, Copilot, etc.) implements or regenerates a module, it reads the contract first:

```markdown
# Task: Implement error_translation.py

## Context
@provider-github-copilot:contracts/error-hierarchy.md

## Implementation Requirements
Create `error_translation.py` that satisfies all MUST clauses in the error-hierarchy contract.

## Config Reference
Read mappings from: @provider-github-copilot:config/errors.yaml
```

### Pattern: Contract-Referenced Code Comments

Borrowed from [Rust's rustdoc](https://doc.rust-lang.org/rustdoc/) linking:

```python
# modules/provider-core/error_translation.py

"""
Error translation from SDK exceptions to domain exceptions.

Contract: contracts/error-hierarchy.md
Config: config/errors.yaml
"""

from typing import Any
import re
from .exceptions import (
    CopilotProviderError,
    CopilotAuthError,
    CopilotRateLimitError,
    # ...
)
from .config import ErrorConfig, ErrorMapping


DOMAIN_ERROR_MAP = {
    "CopilotAuthError": CopilotAuthError,
    "CopilotRateLimitError": CopilotRateLimitError,
    # ...
}


def translate_sdk_error(exc: Exception, config: ErrorConfig) -> CopilotProviderError:
    """
    Translate an SDK exception to a domain exception.
    
    Contract: error-hierarchy.md → Translation Function Contract
    
    - MUST NOT raise (error-hierarchy:Translation:MUST:1)
    - MUST preserve original (error-hierarchy:Translation:MUST:2)
    - MUST use config patterns (error-hierarchy:Config:MUST:1)
    - MUST fall through to CopilotProviderError (error-hierarchy:Config:MUST:2)
    """
    exc_type_name = type(exc).__name__
    exc_message = str(exc)
    
    for mapping in config.error_mappings:
        if _matches(exc_type_name, exc_message, mapping):
            return _create_domain_error(mapping, exc)
    
    # Contract: error-hierarchy:Config:MUST:2 - fallback
    return CopilotProviderError(
        message=exc_message,
        retryable=False,
        original=exc,
    )


def _matches(exc_type: str, message: str, mapping: ErrorMapping) -> bool:
    """Check if exception matches a mapping's patterns."""
    # Check SDK type patterns
    if exc_type in mapping.sdk_patterns:
        return True
    
    # Check string patterns in message
    for pattern in mapping.string_patterns:
        if pattern in message:
            return True
    
    return False


def _create_domain_error(mapping: ErrorMapping, original: Exception) -> CopilotProviderError:
    """Create domain error from mapping, preserving original."""
    error_class = DOMAIN_ERROR_MAP[mapping.domain_error]
    
    kwargs = {
        "message": str(original),
        "original": original,  # Contract: error-hierarchy:Translation:MUST:2
    }
    
    # Contract: error-hierarchy:CopilotRateLimitError:MUST:2
    if mapping.extract_retry_after and mapping.domain_error == "CopilotRateLimitError":
        retry_after = _extract_retry_after(str(original))
        if retry_after is not None:
            kwargs["retry_after"] = retry_after
    
    return error_class(**kwargs)


def _extract_retry_after(message: str) -> int | None:
    """Extract retry-after seconds from error message."""
    # Pattern from config/errors.yaml: retry_after_pattern
    match = re.search(r"retry.after\D*(\d+(?:\.\d+)?)", message, re.IGNORECASE)
    if match:
        return int(float(match.group(1)))
    return None
```

### Pattern: Regeneration from Contract

When the AI regenerates a module:

1. Read the contract (source of truth)
2. Read the config (current policy)
3. Generate code that satisfies contract using config
4. Run contract compliance tests
5. If tests pass, commit

```markdown
# Regeneration Protocol

## Input
- contracts/error-hierarchy.md (WHAT must be true)
- config/errors.yaml (WHAT the current mappings are)

## Output
- modules/provider-core/error_translation.py (HOW it's implemented)

## Verification
- tests/contract/test_error_hierarchy.py (PROOF it works)

## Regeneration Trigger
- Contract change → regenerate code + tests
- Config change → regenerate only if new mappings need new code
- SDK change → update config, regenerate if needed
```

---

## 5. The Contract-Config-Code Triangle

```
                    CONTRACT (Markdown)
                         /\
                        /  \
                       /    \
                      /      \
                     / DRIVES \
                    /   BOTH   \
                   /            \
                  /              \
                 /                \
                /                  \
               /                    \
              ▼                      ▼
    CONFIG (YAML)  ◄────────────►  CODE (Python)
                    CONSUMES
```

### Flow for Each Change Type

**Contract Change (rare, high-impact):**
```
1. Update contracts/*.md
2. Contract compliance tests auto-fail (new MUST clauses untested)
3. Update config/*.yaml if needed
4. Regenerate code if needed
5. Write/update tests for new clauses
6. All tests pass → merge
```

**Config Change (common, low-risk):**
```
1. Update config/*.yaml (e.g., add new SDK error pattern)
2. Config compliance tests verify config is valid
3. Contract compliance tests verify behavior unchanged
4. No code change needed (config-driven mapper handles it)
5. All tests pass → auto-merge (Tier 1)
```

**Code Change (medium-risk):**
```
1. Contract compliance tests define expected behavior
2. Write/modify code to satisfy contracts
3. Contract compliance tests pass
4. Human reviews PR (Tier 2-3)
5. Merge
```

---

## 6. Real-World Pattern References

### Borrowed from Gauge (ThoughtWorks)

Gauge uses markdown specs as the executable format. We borrow:
- Structured markdown with clear sections
- Steps that map to test implementations
- Living documentation that shows pass/fail

**Gauge example:**
```markdown
# User Login
## Successful login
* Navigate to login page
* Enter credentials "user@example.com" and "password123"
* Click login button
* Verify dashboard is displayed
```

**Our equivalent:**
```markdown
# Error Translation
## SDK AuthenticationError maps to CopilotAuthError
- MUST: translate_sdk_error(AuthenticationError) returns CopilotAuthError
- MUST: Result has retryable=False
- MUST: Result preserves original exception
```

### Borrowed from W3C WPT

W3C Web Platform Tests reference spec sections. We borrow:
- Test anchors that reference specific spec clauses
- Coverage reports showing tested vs untested requirements
- Spec-driven test organization

**WPT example:**
```python
# Test for: https://html.spec.whatwg.org/#parsing-main-inbody
def test_adoption_agency_algorithm():
    ...
```

**Our equivalent:**
```python
@pytest.mark.contract("error-hierarchy:CopilotAuthError:MUST:1")
def test_auth_error_not_retryable():
    ...
```

### Borrowed from RFC 2119

IETF RFC 2119 defines MUST/SHOULD/MAY keywords. We borrow:
- Precise language for requirements
- Clear distinction between mandatory and optional
- Machine-parseable keywords

**RFC 2119:**
> MUST: This word means that the definition is an absolute requirement.

**Our usage:**
```markdown
- **MUST:** Have `retryable=False` always
- **SHOULD:** Include retry_after value in attributes
- **MAY:** Log the original exception for debugging
```

### Borrowed from Kubernetes KEPs

Kubernetes Enhancement Proposals use structured markdown. We borrow:
- Version tracking in contracts
- Clear sections (motivation, proposal, test plan)
- Machine-readable metadata

**KEP format:**
```markdown
# KEP-1234: Feature Name
## Motivation
## Proposal
## Test Plan
```

**Our format:**
```markdown
# Contract: Error Hierarchy
## Version
## Invariants
## Behavioral Requirements
## Test Anchors
```

---

## 7. Implementation Checklist

### Phase 0: Foundation

- [ ] Create `contracts/` directory structure
- [ ] Write `contracts/error-hierarchy.md` (first contract)
- [ ] Implement contract parser (`scripts/contract_coverage.py`)
- [ ] Add `@pytest.mark.contract` marker
- [ ] Write initial contract compliance tests

### Phase 1: Full Coverage

- [ ] Write all 7 contract files
- [ ] Achieve 100% MUST clause test coverage
- [ ] Add contract coverage to CI (`scripts/contract_coverage.py`)
- [ ] Implement contract-referenced code comments

### Phase 2: AI Integration

- [ ] Document @mention pattern for AI context injection
- [ ] Create regeneration protocol documentation
- [ ] Test regeneration workflow (AI reads contract, generates code)
- [ ] Validate contract-first development flow

---

## 8. Success Criteria

| Metric | Target |
|--------|--------|
| MUST clause test coverage | 100% |
| Contract files | 7 (one per domain) |
| Tests with `@pytest.mark.contract` | All contract tests |
| Contract coverage report | Runs in CI |
| AI regeneration success rate | >80% (module satisfies contract on first try) |

---

## References

- [Gauge](https://gauge.org/) — Markdown-as-spec pattern
- [W3C Web Platform Tests](https://web-platform-tests.org/) — Spec-driven test organization
- [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt) — MUST/SHOULD/MAY keywords
- [Kubernetes KEPs](https://github.com/kubernetes/enhancements) — Structured specification markdown
- [Rust RFCs](https://github.com/rust-lang/rfcs) — Contract-first language design
- [h2spec](https://github.com/summerwind/h2spec) — RFC-derived conformance tests
