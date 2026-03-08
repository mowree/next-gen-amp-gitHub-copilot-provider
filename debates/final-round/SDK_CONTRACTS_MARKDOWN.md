# SDK CONTRACTS AS MARKDOWN: Declarative Specifications

## The Insight

The council proposed "SDK assumption tests" — Python code that tests SDK behavior. The idea was sound: make SDK expectations explicit, catch breaking changes early, provide documentation through tests. But there's a deeper pattern hiding here.

Amplifier already uses markdown files as specifications. `IMPLEMENTATION_PHILOSOPHY.md` defines how code should be written. `MODULAR_DESIGN_PHILOSOPHY.md` defines how modules should be structured. These aren't code — they're contracts. Human-readable, AI-parseable, declarative specifications that guide behavior.

Why should SDK contracts be any different?

Python tests encode SDK expectations in *implementation*. You have to read code to understand the contract. You have to run code to validate it. You have to maintain code when the SDK changes. But the actual information — "Message has a text field that is a string" — is a *specification*, not an implementation. It belongs in a declarative format.

Markdown is the right medium. Here's why, and here's how.

---

## 1. Contract File Structure

```
contracts/
├── README.md                    # How to read and write contracts
├── sdk-version.md               # Current SDK version pinning
├── types/
│   ├── message.md               # Message type contract
│   ├── session.md               # Session/conversation contract
│   ├── event.md                 # Event type contract
│   ├── tool-call.md             # Tool call structure
│   ├── tool-result.md           # Tool result structure
│   └── completion.md            # Completion/response contract
├── behaviors/
│   ├── streaming.md             # Streaming behavior contract
│   ├── tool-execution.md        # Tool execution lifecycle
│   ├── error-handling.md        # Error types and recovery
│   ├── authentication.md        # Auth flow contract
│   └── rate-limiting.md         # Rate limit behavior
├── assumptions/
│   ├── version-0.2.md           # Assumptions for SDK 0.2.x
│   ├── version-0.3.md           # Assumptions for SDK 0.3.x
│   └── breaking-changes.md      # Known breaking change log
└── generated/
    ├── test_types.py             # Auto-generated type tests
    ├── test_behaviors.py         # Auto-generated behavior tests
    └── test_assumptions.py       # Auto-generated assumption tests
```

### Design Rationale

**Three directories, three concerns:**

- **`types/`** — Structural contracts. "What shape does this data have?" These are the nouns of the SDK: Message, Session, Event. Each file defines fields, types, constraints, and nullability rules.

- **`behaviors/`** — Behavioral contracts. "How does this process work?" These are the verbs: streaming, tool execution, error handling. Each file defines sequences, guarantees, and invariants.

- **`assumptions/`** — Version-specific contracts. "What do we assume about this SDK version?" These are the temporal markers: what's true today, what changed yesterday, what might break tomorrow.

**`generated/`** is output, never input. It contains Python test files auto-generated from the markdown contracts. You never edit these files. You edit the contracts, and the tests regenerate.

This separation means you can review contracts without seeing test code. You can understand SDK expectations without reading Python. You can hand a contract file to a new developer (or a new AI agent) and they immediately understand what the SDK promises.

---

## 2. Contract Syntax

The contract format must satisfy three constraints simultaneously:

1. **Human readable** — A developer skimming the file understands the contract
2. **Machine parseable** — A script can extract structured data from it
3. **Testable** — Every contract statement maps to a verifiable assertion

The key insight: we don't need a new DSL. We need *structured markdown with conventions*. The conventions are simple enough that any markdown parser plus a few regex patterns can extract the contract data.

### 2.1 Type Contracts

```markdown
# contracts/types/message.md

# Message Type Contract

> SDK: `anthropic` >= 0.2.0
> Import: `from anthropic.types import Message`

## Required Fields

| Field | Type | Constraint | Default |
|-------|------|-----------|---------|
| `id` | `string` | Non-empty, starts with "msg_" | — |
| `type` | `literal` | Always "message" | "message" |
| `role` | `string` | "user" \| "assistant" | — |
| `content` | `list[ContentBlock]` | Non-null, may be empty | `[]` |
| `model` | `string` | Valid model identifier | — |
| `stop_reason` | `string \| null` | "end_turn" \| "max_tokens" \| "stop_sequence" \| null | — |
| `stop_sequence` | `string \| null` | Present only if stop_reason is "stop_sequence" | `null` |
| `usage` | `Usage` | Non-null | — |

## Optional Fields

| Field | Type | Constraint | Default |
|-------|------|-----------|---------|
| `tool_calls` | `list[ToolCall]` | Never null, empty array if none | `[]` |

## Behavioral Invariants

- MUST: `content` is never `None`, always a list (possibly empty)
- MUST: `id` is always a non-empty string starting with "msg_"
- MUST: `type` always equals the literal string "message"
- MUST: `usage` is always present and non-null
- MUST: `stop_reason` is null while streaming, non-null when complete
- MUST NOT: `content` contain mixed text and tool_use blocks without text first
- SHOULD: `model` match the requested model string exactly

## Nullability Rules

| Field | Can be None? | Can be missing? | Empty value |
|-------|-------------|-----------------|-------------|
| `content` | No | No | `[]` |
| `stop_reason` | Yes (during streaming) | No | — |
| `stop_sequence` | Yes | No | — |
| `tool_calls` | No | Yes (older versions) | `[]` |

## Construction Examples

### Minimal valid message
```python
# This is a REFERENCE example, not a test
message = Message(
    id="msg_abc123",
    type="message",
    role="assistant",
    content=[],
    model="claude-sonnet-4-20250514",
    stop_reason="end_turn",
    stop_sequence=None,
    usage=Usage(input_tokens=10, output_tokens=5),
)
```

### Message with tool use
```python
message = Message(
    id="msg_abc123",
    type="message",
    role="assistant",
    content=[
        TextBlock(type="text", text="I'll help with that."),
        ToolUseBlock(
            type="tool_use",
            id="toolu_abc123",
            name="read_file",
            input={"path": "src/main.py"},
        ),
    ],
    model="claude-sonnet-4-20250514",
    stop_reason="tool_use",
    stop_sequence=None,
    usage=Usage(input_tokens=50, output_tokens=30),
)
```
```

### 2.2 Behavior Contracts

```markdown
# contracts/behaviors/streaming.md

# Streaming Behavior Contract

> SDK: `anthropic` >= 0.2.0
> Applies to: `client.messages.stream()`

## Lifecycle

```
SEQUENCE: stream_lifecycle
  1. message_start    → Message object (incomplete)
  2. content_block_start → ContentBlock (type known)
  3. content_block_delta → Incremental content (repeated)
  4. content_block_stop  → Block complete
  5. message_delta    → Final message metadata
  6. message_stop     → Stream complete
```

## Event Ordering Invariants

- MUST: `message_start` is always the first event
- MUST: `message_stop` is always the last event
- MUST: Every `content_block_start` has a matching `content_block_stop`
- MUST: `content_block_delta` only appears between start/stop of same block
- MUST: Block indices are sequential starting from 0
- MUST NOT: Events for block N+1 appear before block N completes
- MUST NOT: `message_delta` appear before all content blocks are stopped

## Error Behavior

- ON connection drop: SDK raises `APIConnectionError`
- ON timeout: SDK raises `APITimeoutError`
- ON server error during stream: SDK raises `APIStatusError` with partial data
- MUST: Partial message is accessible even after stream error via `.get_final_message()`
- MUST NOT: Stream silently swallow errors

## Accumulation Contract

- MUST: `stream.get_final_message()` returns complete Message after stream ends
- MUST: `stream.get_final_text()` returns concatenated text content
- MUST: Accumulated message matches what non-streaming API would return
- MUST NOT: `get_final_message()` be called before stream completes (raises error)

## Context Manager

- MUST: Stream works as async context manager (`async with`)
- MUST: Exiting context manager closes the stream
- MUST: Stream is iterable (`async for event in stream`)
```

### 2.3 Contract Keywords

The format uses RFC 2119-style keywords with precise semantics:

| Keyword | Meaning | Test Generation |
|---------|---------|-----------------|
| `MUST` | Absolute requirement. Violation is a bug. | Generates assertion test |
| `MUST NOT` | Absolute prohibition. Occurrence is a bug. | Generates negative assertion |
| `SHOULD` | Expected but not guaranteed. Violation is a warning. | Generates warning test |
| `SHOULD NOT` | Discouraged but not prohibited. | Generates warning test |
| `ON` | Trigger condition for behavior. | Generates scenario test |
| `SEQUENCE` | Ordered list of events. | Generates ordering test |

These keywords are always uppercase, always at the start of a bullet point or after a colon. This makes them trivially parseable: `re.findall(r'^- (MUST|MUST NOT|SHOULD|ON|SEQUENCE):', line)`.

### 2.4 Table Format Conventions

Tables use standard GitHub-flavored markdown. Columns have fixed semantics based on the table header:

- **Field tables**: `Field | Type | Constraint | Default`
- **Nullability tables**: `Field | Can be None? | Can be missing? | Empty value`
- **Event tables**: `Event | Payload | Guarantees`

The parser recognizes these by header pattern matching. No special syntax needed.

---

## 3. Test Generation

Contracts generate tests. This is not optional — it's the whole point. A contract that isn't tested is just documentation, and documentation lies.

### 3.1 The Generator

```python
# tools/contract_test_generator.py

"""
Generates Python test files from markdown contract files.

Usage:
    python -m tools.contract_test_generator contracts/ generated/

Parses markdown contracts and emits pytest-compatible test files.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class FieldContract:
    name: str
    type_hint: str
    constraint: str
    default: str | None
    nullable: bool = False
    optional: bool = False


@dataclass
class BehaviorContract:
    keyword: str  # MUST, MUST NOT, SHOULD, etc.
    description: str
    severity: str = "error"  # error for MUST, warning for SHOULD


@dataclass
class TypeContract:
    name: str
    import_path: str
    sdk_version: str
    required_fields: list[FieldContract] = field(default_factory=list)
    optional_fields: list[FieldContract] = field(default_factory=list)
    invariants: list[BehaviorContract] = field(default_factory=list)


def parse_type_contract(markdown_path: Path) -> TypeContract:
    """Parse a type contract markdown file into structured data."""
    text = markdown_path.read_text()
    
    # Extract metadata from blockquote
    sdk_match = re.search(r'> SDK: `(.+?)`\s*(.*)', text)
    import_match = re.search(r'> Import: `(.+?)`', text)
    name_match = re.search(r'^# (.+?) Type Contract', text, re.MULTILINE)
    
    contract = TypeContract(
        name=name_match.group(1) if name_match else markdown_path.stem,
        import_path=import_match.group(1) if import_match else "",
        sdk_version=sdk_match.group(1) if sdk_match else "",
    )
    
    # Parse field tables
    contract.required_fields = _parse_field_table(text, "Required Fields")
    contract.optional_fields = _parse_field_table(text, "Optional Fields")
    
    # Parse behavioral invariants
    contract.invariants = _parse_invariants(text)
    
    return contract


def _parse_field_table(text: str, section: str) -> list[FieldContract]:
    """Extract fields from a markdown table under a given section."""
    fields = []
    pattern = rf'## {section}\n\n\|.*\n\|[-| ]+\n((?:\|.*\n)*)'
    match = re.search(pattern, text)
    if not match:
        return fields
    
    for row in match.group(1).strip().split('\n'):
        cols = [c.strip() for c in row.split('|')[1:-1]]
        if len(cols) >= 3:
            fields.append(FieldContract(
                name=cols[0].strip('`'),
                type_hint=cols[1].strip('`'),
                constraint=cols[2],
                default=cols[3] if len(cols) > 3 and cols[3] != '—' else None,
            ))
    return fields


def _parse_invariants(text: str) -> list[BehaviorContract]:
    """Extract MUST/SHOULD invariants from the contract."""
    invariants = []
    for match in re.finditer(
        r'^- (MUST NOT|MUST|SHOULD NOT|SHOULD): (.+)$', text, re.MULTILINE
    ):
        keyword = match.group(1)
        severity = "error" if keyword.startswith("MUST") else "warning"
        invariants.append(BehaviorContract(
            keyword=keyword,
            description=match.group(2),
            severity=severity,
        ))
    return invariants


def generate_type_test(contract: TypeContract) -> str:
    """Generate a pytest test file from a type contract."""
    lines = [
        f'"""Auto-generated tests from {contract.name} type contract.',
        f'',
        f'DO NOT EDIT. Regenerate with: python -m tools.contract_test_generator',
        f'"""',
        f'',
        f'import pytest',
        f'{contract.import_path}',
        f'',
        f'',
        f'class Test{contract.name}TypeContract:',
        f'    """Tests for {contract.name} type structure."""',
        f'',
    ]
    
    # Generate field existence tests
    for f in contract.required_fields:
        lines.extend([
            f'    def test_has_{f.name}_field(self, sample_{contract.name.lower()}):',
            f'        """{contract.name} MUST have {f.name} field."""',
            f'        assert hasattr(sample_{contract.name.lower()}, "{f.name}")',
            f'',
        ])
    
    # Generate invariant tests
    for inv in contract.invariants:
        test_name = _invariant_to_test_name(inv)
        if inv.severity == "error":
            lines.extend([
                f'    def test_{test_name}(self, sample_{contract.name.lower()}):',
                f'        """{inv.keyword}: {inv.description}"""',
                f'        # TODO: Implement assertion for: {inv.description}',
                f'        raise NotImplementedError("Contract needs manual assertion")',
                f'',
            ])
        else:
            lines.extend([
                f'    @pytest.mark.warning',
                f'    def test_{test_name}(self, sample_{contract.name.lower()}):',
                f'        """{inv.keyword}: {inv.description}"""',
                f'        # TODO: Implement check for: {inv.description}',
                f'        raise NotImplementedError("Contract needs manual assertion")',
                f'',
            ])
    
    return '\n'.join(lines)


def _invariant_to_test_name(inv: BehaviorContract) -> str:
    """Convert an invariant description to a valid test name."""
    name = inv.description.lower()
    name = re.sub(r'[^a-z0-9]+', '_', name)
    name = name.strip('_')[:60]
    prefix = "invariant" if inv.keyword.startswith("MUST") else "advisory"
    return f"{prefix}_{name}"
```

### 3.2 Generated Output

From the Message type contract above, the generator produces:

```python
# generated/test_types.py (auto-generated, do not edit)

"""Auto-generated tests from Message type contract.

DO NOT EDIT. Regenerate with: python -m tools.contract_test_generator
"""

import pytest
from anthropic.types import Message


class TestMessageTypeContract:
    """Tests for Message type structure."""

    def test_has_id_field(self, sample_message):
        """Message MUST have id field."""
        assert hasattr(sample_message, "id")

    def test_has_type_field(self, sample_message):
        """Message MUST have type field."""
        assert hasattr(sample_message, "type")

    def test_has_role_field(self, sample_message):
        """Message MUST have role field."""
        assert hasattr(sample_message, "role")

    def test_has_content_field(self, sample_message):
        """Message MUST have content field."""
        assert hasattr(sample_message, "content")

    def test_invariant_content_is_never_none_always_a_list(self, sample_message):
        """MUST: content is never None, always a list (possibly empty)"""
        assert sample_message.content is not None
        assert isinstance(sample_message.content, list)

    def test_invariant_id_is_always_a_non_empty_string_starting_with_msg(self, sample_message):
        """MUST: id is always a non-empty string starting with 'msg_'"""
        assert isinstance(sample_message.id, str)
        assert len(sample_message.id) > 0
        assert sample_message.id.startswith("msg_")

    def test_invariant_type_always_equals_the_literal_string_message(self, sample_message):
        """MUST: type always equals the literal string 'message'"""
        assert sample_message.type == "message"

    def test_invariant_usage_is_always_present_and_non_null(self, sample_message):
        """MUST: usage is always present and non-null"""
        assert hasattr(sample_message, "usage")
        assert sample_message.usage is not None

    @pytest.mark.warning
    def test_advisory_model_match_the_requested_model_string_exactly(self, sample_message):
        """SHOULD: model match the requested model string exactly"""
        # Advisory: not a hard failure
        pass
```

### 3.3 Two Modes of Test Generation

**Mode 1: Static generation (CI pipeline)**

```
contracts/*.md → generator script → generated/test_*.py → pytest
```

The generator runs as a pre-test step. Generated files are committed to `generated/` so developers can review them. CI checks that generated files are up-to-date with contracts (`python -m tools.contract_test_generator --check`).

**Mode 2: Runtime validation (dynamic)**

```python
# Alternative: contracts as runtime validators

class ContractValidator:
    """Validates SDK objects against markdown contracts at runtime."""
    
    def __init__(self, contracts_dir: Path):
        self.contracts = {}
        for md_file in contracts_dir.glob("types/*.md"):
            contract = parse_type_contract(md_file)
            self.contracts[contract.name] = contract
    
    def validate(self, obj, type_name: str) -> list[ContractViolation]:
        """Check an SDK object against its contract."""
        contract = self.contracts.get(type_name)
        if not contract:
            return [ContractViolation(f"No contract for type: {type_name}")]
        
        violations = []
        
        # Check required fields
        for field in contract.required_fields:
            if not hasattr(obj, field.name):
                violations.append(ContractViolation(
                    f"Missing required field: {field.name}",
                    severity="error",
                ))
            elif field.constraint == "Non-null" and getattr(obj, field.name) is None:
                violations.append(ContractViolation(
                    f"Required field is null: {field.name}",
                    severity="error",
                ))
        
        return violations


# Usage in provider code:
validator = ContractValidator(Path("contracts/"))

message = await client.messages.create(...)
violations = validator.validate(message, "Message")
if violations:
    logger.warning(f"SDK contract violations: {violations}")
```

Runtime validation is useful during development and in staging environments. It catches contract violations without requiring a separate test run. In production, you'd disable it for performance.

### 3.4 Smart Test Generation for Behavioral Contracts

Behavioral contracts (streaming, tool execution) generate scenario-based tests:

```python
# generated/test_behaviors.py (from streaming.md)

class TestStreamingBehaviorContract:
    """Tests for streaming lifecycle."""

    async def test_sequence_stream_lifecycle_ordering(self, streaming_client):
        """SEQUENCE: stream_lifecycle events arrive in order."""
        events = []
        async with streaming_client.messages.stream(...) as stream:
            async for event in stream:
                events.append(event.type)
        
        # Verify ordering invariants from contract
        assert events[0] == "message_start", "MUST: message_start is first"
        assert events[-1] == "message_stop", "MUST: message_stop is last"
        
        # Verify block pairing
        starts = [i for i, e in enumerate(events) if e == "content_block_start"]
        stops = [i for i, e in enumerate(events) if e == "content_block_stop"]
        assert len(starts) == len(stops), "MUST: every start has a stop"
        for start, stop in zip(starts, stops):
            assert start < stop, "MUST: start before stop"

    async def test_error_connection_drop_raises(self, unreliable_client):
        """ON connection drop: SDK raises APIConnectionError"""
        with pytest.raises(APIConnectionError):
            async with unreliable_client.messages.stream(...) as stream:
                async for event in stream:
                    pass  # Connection drops mid-stream
```

---

## 4. Version-Specific Contracts

SDK versions break things. The contract system handles this with version annotations and evolution tracking.

### 4.1 Version Pinning

Every contract file declares its applicable SDK version:

```markdown
> SDK: `anthropic` >= 0.2.0, < 0.4.0
```

The generator reads this and wraps tests in version guards:

```python
import anthropic

SDK_VERSION = tuple(int(x) for x in anthropic.__version__.split('.')[:3])

@pytest.mark.skipif(SDK_VERSION < (0, 2, 0), reason="Requires SDK >= 0.2.0")
@pytest.mark.skipif(SDK_VERSION >= (0, 4, 0), reason="Contract expired at SDK 0.4.0")
class TestMessageTypeContract:
    ...
```

### 4.2 Assumption Files

```markdown
# contracts/assumptions/version-0.2.md

# SDK Version 0.2.x Assumptions

> SDK: `anthropic` >= 0.2.0, < 0.3.0
> Status: ACTIVE
> Verified: 2026-02-15

## Assumptions

- ASSUME: Message.content is always a list of ContentBlock objects
- ASSUME: Streaming events use Server-Sent Events format
- ASSUME: Tool results must be sent as user messages
- ASSUME: Rate limit headers are present on all API responses
- ASSUME: client.messages.create() returns Message, not dict

## Known Quirks

- QUIRK: Empty content array serializes to `[]`, not omitted from JSON
- QUIRK: stop_reason "tool_use" appears even if tool call fails validation
- QUIRK: Usage.cache_creation_input_tokens may be 0 rather than absent

## Deprecated Patterns

- DEPRECATED: Direct dict access on Message (use attribute access)
- DEPRECATED: completion.stop param (use stop_sequences)
```

### 4.3 Breaking Change Tracking

```markdown
# contracts/assumptions/breaking-changes.md

# SDK Breaking Change Log

## 0.2.0 → 0.3.0

### BREAKING: Message.content type changed
- Before: `list[dict]`
- After: `list[ContentBlock]`
- Impact: All code accessing content[i]["text"] must change to content[i].text
- Contracts affected: `types/message.md`

### BREAKING: Streaming API changed
- Before: `client.completions.create(stream=True)`
- After: `client.messages.stream()`
- Impact: Complete streaming code rewrite required
- Contracts affected: `behaviors/streaming.md`

### NON-BREAKING: New tool_choice parameter
- Added: `tool_choice` parameter to messages.create()
- Impact: None (additive change)
- Contracts affected: None
```

### 4.4 Contract Evolution Workflow

When an SDK upgrade is planned:

1. **Create new version assumption file** (`assumptions/version-0.3.md`)
2. **Mark expiring contracts** (set upper version bound on old contracts)
3. **Create new versions of changed contracts** (update type/behavior files)
4. **Run generator** — produces tests for both old and new versions
5. **Upgrade SDK** — old tests skip, new tests activate
6. **Archive old assumptions** (move to `assumptions/archive/`)

This is a *declarative upgrade plan*. You can review the entire scope of an SDK upgrade by diffing contract files. No digging through test code to understand what changed.

---

## 5. Advantages Over Code

### 5.1 AI Can Read and Write Markdown More Reliably Than Python

This is the practical argument. When an AI agent needs to understand SDK expectations, it can read a markdown contract faster and more accurately than parsing test code. The contract is the *intent*. The test is the *mechanism*. AI is better at understanding intent.

When an AI agent detects a new SDK version, it can update a markdown contract with the changes. Writing structured markdown (tables, bullet points, keywords) is far less error-prone for AI than writing Python test code with correct imports, fixtures, assertions, and edge case handling.

Consider the workflow:

```
Human or AI detects SDK change
  → Updates contracts/types/message.md (add field, change type)
  → Runs generator
  → Tests regenerate automatically
  → CI validates
```

Versus:

```
Human or AI detects SDK change
  → Must understand existing test structure
  → Must find the right test file and class
  → Must write correct Python with correct imports
  → Must handle fixtures and parameterization
  → Must not break other tests
  → Must run tests to verify
```

The markdown path has fewer failure modes.

### 5.2 Contracts Are Specifications, Not Implementations

A Python test says "here's how to verify X." A markdown contract says "X is true." The difference matters.

Specifications are:
- **Declarative**: They state what, not how
- **Implementation-independent**: The same contract can generate tests in Python, TypeScript, or any language
- **Reviewable**: A product manager can review a contract. They cannot review a test file.
- **Composable**: Contracts can reference other contracts. `message.md` references `ContentBlock` from `content-block.md`.

Tests are:
- **Imperative**: They encode a sequence of actions
- **Language-specific**: Python tests only test Python SDK
- **Technical**: Only developers can review them
- **Isolated**: Tests don't naturally compose or cross-reference

The contract is the source of truth. Tests are derived artifacts. If you lose the tests, regenerate them. If you lose the contracts, you've lost the specification.

### 5.3 Easier to Diff, Review, and Understand

When an SDK upgrade changes the Message type, the diff in `message.md` looks like:

```diff
 ## Required Fields
 
 | Field | Type | Constraint | Default |
 |-------|------|-----------|---------|
   | `id` | `string` | Non-empty, starts with "msg_" | — |
-  | `type` | `literal` | Always "message" | "message" |
+  | `type` | `literal` | "message" \| "error" | "message" |
   | `role` | `string` | "user" \| "assistant" | — |
+  | `metadata` | `dict` | Optional metadata bag | `{}` |
```

Compare with the equivalent test diff:

```diff
     def test_invariant_type_always_equals_the_literal_string_message(self, sample_message):
-        """MUST: type always equals the literal string 'message'"""
-        assert sample_message.type == "message"
+        """MUST: type is 'message' or 'error'"""
+        assert sample_message.type in ("message", "error")
 
+    def test_has_metadata_field(self, sample_message):
+        """Message MUST have metadata field."""
+        assert hasattr(sample_message, "metadata")
+        assert isinstance(sample_message.metadata, dict)
```

The contract diff is instantly understandable. The test diff requires reading code. For PR reviews, the contract format wins decisively.

### 5.4 Single Source of Truth for Multiple Consumers

Markdown contracts serve multiple purposes simultaneously:

| Consumer | What they get |
|----------|--------------|
| **Developers** | Readable SDK reference |
| **AI agents** | Parseable SDK expectations |
| **Test runner** | Generated test suite |
| **CI pipeline** | Automated validation |
| **Documentation** | Always-current SDK docs |
| **Code review** | Clear change impact |
| **New team members** | Onboarding reference |

A Python test file serves exactly one consumer: the test runner.

### 5.5 Natural Integration with Amplifier's Philosophy

Amplifier already treats markdown as specification. Implementation philosophy, modular design philosophy, kernel philosophy — all markdown files that guide behavior. SDK contracts as markdown fits this pattern perfectly.

The contracts become part of the specification layer:

```
Amplifier specification layer:
  IMPLEMENTATION_PHILOSOPHY.md     → How to write code
  MODULAR_DESIGN_PHILOSOPHY.md     → How to structure modules
  contracts/types/message.md        → What the SDK promises
  contracts/behaviors/streaming.md  → How the SDK behaves
```

Everything at the same level of abstraction. Everything in the same format. Everything readable by the same tools (humans, AI agents, parsers).

---

## 6. Implementation Path

### Phase 1: Core Type Contracts
Write contracts for the 3-5 most critical SDK types (Message, ContentBlock, Usage, ToolUseBlock). These are the types that, when they break, break everything.

### Phase 2: Behavior Contracts
Write contracts for streaming and tool execution — the two behavioral areas most likely to change between SDK versions and most painful to debug when they do.

### Phase 3: Generator Tool
Build the contract-to-test generator. Start simple: field existence tests from tables, invariant tests from MUST statements. Grow the generator as contract syntax matures.

### Phase 4: CI Integration
Add contract validation to CI: generate tests, run them, fail on MUST violations, warn on SHOULD violations. Add staleness check: contracts must be regenerated when modified.

### Phase 5: Version Migration
When the next SDK upgrade comes, use contracts to plan the migration. Write the new version's contracts first (specification-driven development), then update code to satisfy them.

---

## The Philosophical Argument

Code tests encode *how we check*. Markdown contracts encode *what we know*. The former is an implementation detail. The latter is knowledge.

When you write `assert message.content is not None`, you're saying "here's a Python expression that should evaluate to True." When you write `MUST: content is never None, always a list`, you're saying "this is a property of the universe we operate in."

The test might be wrong (bad fixture, wrong import, flaky environment). The contract is either true or false. If it's true, the generated test will verify it. If it's false, we update the contract — the source of truth — and the test follows.

This is the Amplifier way: specifications first, implementations derived. Markdown contracts are specifications. Python tests are implementations. Keep the hierarchy clear, and the system stays simple.

SDK contracts as markdown. Not because markdown is better than Python. Because specifications are better than implementations. And markdown is how Amplifier writes specifications.