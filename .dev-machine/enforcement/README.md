# Enforcement Scripts

Four standalone Python scripts that run inside `tightened-iteration.yaml` gates.
They can also be run manually during development.

## Scripts

### `check-loc.py` — LOC Enforcement
Scans Python source against Golden Vision V2 §Principle 5 thresholds.

| Threshold | LOC | Action |
|-----------|-----|--------|
| Core target | 300 | Informational |
| Soft cap | 400 | Warn — don't add features |
| Hard cap | 600 | **BLOCK** — refactor required |

```bash
python3 .dev-machine/enforcement/check-loc.py
python3 .dev-machine/enforcement/check-loc.py --json
```

### `check-hardcoded-policy.py` — Policy Detector
Detects policy values embedded in Python that should live in YAML config
(Three-Medium Architecture violation).

Categories: `retry-policy`, `timeout-policy`, `model-policy`, `error-policy`,
`control-flow` (hard fail — makes code untestable).

```bash
python3 .dev-machine/enforcement/check-hardcoded-policy.py
python3 .dev-machine/enforcement/check-hardcoded-policy.py --json
```

### `check-magicmock-abuse.py` — MagicMock Abuse Detector
Detects bare `MagicMock()`/`AsyncMock()` at the SDK boundary in test files.

**This is the root cause of F-044 and F-045.** MagicMock silently accepts any
call without validation. Tests verified "did we call a function?" not "did we
send the correct configuration?".

Hard-fail patterns:
- `create_session = AsyncMock()` — won't capture SDK config
- `mock_client = MagicMock()` — won't validate any calls
- `"mode"..."append"` — codifies the F-044 bug as a test assertion

Fix: use `ConfigCapturingMock` from `tests/fixtures/config_capture.py`.

```bash
python3 .dev-machine/enforcement/check-magicmock-abuse.py
python3 .dev-machine/enforcement/check-magicmock-abuse.py --json
```

### `check-contract-coverage.py` — Contract Coverage
Verifies that SDK boundary test functions reference contract anchors in their
docstrings. Prevents the F-044 failure mode (writing tests to observed behavior
instead of required behavior).

A contract anchor looks like: `sdk-boundary:Config:MUST:2`

```python
async def test_system_message_mode(self) -> None:
    """sdk-boundary:Config:MUST:2

    System message MUST use replace mode.
    """
```

```bash
python3 .dev-machine/enforcement/check-contract-coverage.py
python3 .dev-machine/enforcement/check-contract-coverage.py --require-anchors
```

## Integration

All four scripts are integrated into `tightened-iteration.yaml` as Gate 3
(enforcement scan). They run after the working session but before the
5-expert quorum.

Gate progression:
```
Gate 0: Spec contract anchor check     ← BEFORE working session
Gate 1: RED test gate                  ← BEFORE working session
[Working Session]
Gate 2: Boundary contract test suite   ← F-044/F-045 regression check
Gate 3: Enforcement scan (these 4)     ← LOC + policy + MagicMock
Gate 4: Full test suite
Gate 5: 5-expert quorum
```
