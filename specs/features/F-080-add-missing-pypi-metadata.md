# F-080: Add Missing PyPI Metadata

**Status:** ready
**Priority:** P2
**Source:** packaging review

## Problem Statement
The pyproject.toml is missing required metadata for PyPI publication:
- `authors` — Not specified
- `keywords` — Not specified
- `classifiers` — Not specified
- `[project.urls]` — Not specified (homepage, repository, documentation)

Evidence: Review of pyproject.toml shows these fields are absent.

## Success Criteria
- [ ] `authors` field populated in pyproject.toml
- [ ] `keywords` field populated with relevant terms
- [ ] `classifiers` field includes development status, license, and Python versions
- [ ] `[project.urls]` section includes Homepage, Repository, and Documentation
- [ ] `uv lock` succeeds after changes
- [ ] Existing tests pass unchanged
- [ ] No new dependencies introduced

## Implementation Approach
Add the following to pyproject.toml `[project]` section:
```toml
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["amplifier", "github-copilot", "llm", "provider"]
classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[project.urls]
Homepage = "https://github.com/your-org/provider-github-copilot"
Repository = "https://github.com/your-org/provider-github-copilot"
Documentation = "https://github.com/your-org/provider-github-copilot#readme"
```

Note: Placeholder values (name, email, org) must be replaced with actual values at implementation time.

## Files to Modify
- `pyproject.toml` (add metadata fields)

## TDD Anchor
- Red: Parse pyproject.toml, check for `authors`, `keywords`, `classifiers`, `urls` → missing
- Green: Add all fields → present and well-formed
- Refactor: N/A

## Contract Traceability
- PyPI packaging best practices — metadata required for discoverability and trust

## Not In Scope
- Publishing to PyPI (see F-064)
- Changing build system or dependencies
- Adding license file (assumed already present or handled separately)
