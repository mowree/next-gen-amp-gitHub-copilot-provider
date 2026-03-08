# THE AMPLIFIER WAY: Why Config-First Beats Code-First

**Author**: Amplifier Expert (Authoritative Ecosystem Voice)  
**Date**: 2026-03-08  
**Status**: Final Round Critique  
**Target**: The Golden Vision (synthesized from 27 agents across 31 documents)

---

## The Verdict

The Golden Vision is a beautifully engineered document. It is also **fundamentally misaligned with Amplifier's philosophy**. Twenty-seven agents spent three waves and three rounds producing an architecture that treats the provider as a Python engineering problem. But in Amplifier's world, the provider is a **configuration problem** with a thin Python implementation underneath.

The Golden Vision proposes 17 Python modules, ~1,500+ lines of new code, a five-tier testing diamond, and a four-tier autonomy model. It reads like an architecture astronaut's fever dream — impressive, thorough, and almost entirely wrong about *where* complexity should live.

Let me explain why, grounded in the actual philosophy documents that govern this ecosystem.

---

## 1. What "Thin Bundle Pattern" Means for Providers

The BUNDLE_GUIDE.md is unambiguous:

> **Most bundles should be thin** — inheriting from foundation and adding only their unique capabilities.

The canonical example is `amplifier-bundle-recipes`. Its entire `bundle.md` is **14 lines of YAML**. It includes foundation, includes its own behavior, and references a consolidated instructions file. That's it. Everything else — tools, session config, hooks — comes from foundation.

The GitHub Copilot provider should follow the same pattern. It is not a standalone kingdom with its own architecture document, testing philosophy, and autonomy model. It is a **module** that plugs into a bundle. The provider's job — as the Golden Vision itself correctly states — is "translation, not framework."

But the Golden Vision then immediately contradicts this by proposing a framework: 17 modules, an SDK adapter layer with 3 sub-modules, a domain event system, an error hierarchy of 8 exception classes, and a "Contract-Anchored Diamond" testing strategy. This is not a thin translation layer. This is a miniature application framework masquerading as a provider.

**What it should be**: A provider bundle with this structure:

```
amplifier-bundle-provider-github-copilot/
├── bundle.md                          # Thin: metadata + includes
├── behaviors/
│   └── copilot-provider.yaml          # The behavior: tool + context
├── context/
│   ├── sdk-assumptions.md             # SDK contract documentation
│   ├── deny-destroy-pattern.md        # Architecture decision record
│   └── error-mapping.md               # Error translation table
├── modules/
│   └── provider-github-copilot/       # The actual Python module
│       ├── pyproject.toml
│       └── amplifier_module_provider_github_copilot/
│           ├── provider.py            # ~200 lines: Provider protocol
│           ├── converters.py          # ~100 lines: Message translation
│           ├── sdk_driver.py          # Existing: SDK subprocess mgmt
│           ├── client.py              # Existing: Client wrapper
│           └── tool_capture.py        # Existing: Deny + destroy
├── docs/
│   └── SDK_UPGRADE_GUIDE.md
└── README.md
```

Notice: the Python module is **inside** `modules/`. The bundle itself is configuration. The context files carry the knowledge. The behavior makes it composable.

---

## 2. Where Policies Should Live: In YAML Config Files, Not Python Code

The Kernel Philosophy is crystal clear:

> **Mechanism, not policy.** The kernel exposes capabilities and stable contracts. Decisions about behavior belong outside the kernel. If something can plausibly be a policy, it should live in a module, not in core.

> **Litmus test:** If two reasonable teams could want different behavior, it's a **policy** → keep it out of kernel.

Now look at what the Golden Vision puts in Python:

| Item | Golden Vision Location | Should Be |
|------|----------------------|-----------|
| Backoff timing and jitter | Python code in `error_translation.py` | YAML config: `config.retry.backoff: exponential` |
| Log verbosity level | Python constant | YAML config: `config.logging.level: INFO` |
| Pagination depth limit | Python constant | YAML config: `config.pagination.max_pages: 10` |
| Retry count and timing | Python code | YAML config: `config.retry.max_attempts: 3` |
| Timeout values | Python constants (`DEFAULT_TIMEOUT`, `DEFAULT_THINKING_TIMEOUT`) | YAML config: `config.timeouts.default: 300` |
| Model cache staleness | Python code in `model_cache.py` | YAML config: `config.cache.stale_after: 3600` |
| Fake tool call detection patterns | Python regex constants | Context file: `context/sdk-assumptions.md` |
| SDK max turns | Python constant (`SDK_MAX_TURNS_DEFAULT`) | YAML config: `config.sdk.max_turns: 3` |

Every single one of these fails the litmus test. Two reasonable teams absolutely could want different retry counts, different timeouts, different pagination depths. These are policies. They belong in YAML.

The bundle system already supports this perfectly:

```yaml
# behaviors/copilot-provider.yaml
bundle:
  name: copilot-provider-behavior
  version: 1.0.0
  description: GitHub Copilot LLM provider via CLI SDK

tools:
  - module: provider-github-copilot
    source: ./modules/provider-github-copilot
    config:
      timeouts:
        default: 300
        thinking: 600
      retry:
        max_attempts: 3
        backoff: exponential
        jitter: true
      pagination:
        max_pages: 10
      sdk:
        max_turns: 3
      cache:
        stale_after: 3600
        directory: ~/.amplifier/cache/
```

And users can override any of these in their `settings.yaml`:

```yaml
# ~/.amplifier/settings.yaml
modules:
  tools:
    - module: provider-github-copilot
      config:
        timeouts:
          default: 600      # I want longer timeouts
        retry:
          max_attempts: 5   # I want more retries
```

This is **the Amplifier way**. Config is deep-merged by module ID. The bundle provides sensible defaults. The user overrides what they need. No Python code changes required.

---

## 3. How Amplifier Core Stays Thin — And Why 1,700 Lines Is a Red Flag

Amplifier's kernel is ~2,600 lines. It provides session lifecycle, module loading, event dispatch, and coordinator plumbing. That's it. The kernel has been ruthlessly pruned to contain only mechanisms that multiple modules need.

The current GitHub Copilot provider is **1,799 lines in provider.py alone**. Add converters.py (426), sdk_driver.py (620), tool_capture.py (218), exceptions.py (322), model_cache.py (415), model_naming.py, models.py, client.py, _constants.py, _permissions.py, _platform.py — and you're looking at well over **4,000 lines** of Python for a single provider.

The Golden Vision proposes to reorganize this into 17 modules but doesn't actually *reduce* the code. It redistributes 1,799 lines into ~1,550 lines across more files, then adds new modules (sdk_adapter/ with 3 files, _types.py, config.py, health.py). The total line count likely *increases*.

This violates the Implementation Philosophy's core tenet:

> **Ruthless Simplicity** — KISS principle taken to heart. Keep everything as simple as possible, but no simpler. Minimize abstractions: every layer of abstraction must justify its existence.

And:

> **Code you don't write has no bugs.**

The question isn't "how do we organize 4,000 lines better?" The question is "why do we have 4,000 lines?"

**Where are those lines going?**

- **~800 lines**: Error detection, translation, and rate limit parsing → Should be a **lookup table in YAML** + 50 lines of generic error mapping code
- **~415 lines**: Model cache with cross-platform file I/O → Should use Amplifier's existing cache infrastructure or a 30-line JSON read/write
- **~300 lines**: Fake tool call detection with code block awareness → This is **orchestrator policy**, not provider concern. The provider returns what the LLM said. If the orchestrator wants to detect fake tool calls, that's the orchestrator's job.
- **~200 lines**: Constant definitions, platform detection, permissions → Should be **context files** and **YAML config**
- **~400 lines**: Streaming event handling, metrics, TTFT measurement → Half is mechanism (keep), half is observability policy (extract to hook)

The irreducible mechanism is: create SDK session → send prompt → stream events → translate response → destroy session. That's ~200 lines of provider.py and ~100 lines of converters.py. The Elon Musk challenge of 300 lines is not just achievable — it's the natural consequence of applying Amplifier's philosophy correctly.

---

## 4. Behaviors That Could Replace Python Code

The Behavior Pattern is Amplifier's answer to the question "how do I package reusable capability?" Let's identify what should be behaviors vs. what should be Python:

### Behavior: `copilot-error-mapping`

Instead of 322 lines of Python exception classes plus detection functions:

```yaml
# context/error-mapping.md
# SDK Error → Domain Error Mapping

| SDK Error Pattern | Domain Error | Retryable | Action |
|-------------------|-------------|-----------|--------|
| "rate limit", "429", "too many requests" | RateLimitError | Yes | Extract retry_after |
| "auth", "unauthorized", "forbidden" | AuthenticationError | No | Re-authenticate |
| "not found", "model not available" | NotFoundError | No | Check model name |
| "timeout", "deadline exceeded" | TimeoutError | Yes | Increase timeout |
| "content filtered", "blocked by policy" | ContentFilterError | No | Modify request |
| "connection", "network", "ECONNREFUSED" | NetworkError | Yes | Retry with backoff |
```

The Python code becomes a generic pattern matcher that reads this table. 30 lines, not 322.

### Behavior: `copilot-sdk-assumptions`

Instead of Python tests that encode SDK assumptions:

```markdown
# context/sdk-assumptions.md

## SDK Version Contract: github-copilot-sdk >=0.1.32, <0.2.0

### Event Ordering (CRITICAL)
- ASSISTANT_MESSAGE events fire BEFORE preToolUse hook
- This enables tool capture before deny
- If this changes: tool_capture.py breaks

### Deny Behavior
- preToolUse deny prevents handler invocation
- SDK denial_behavior = RETRY (will retry with built-in tools)
- Session destroy required after deny to prevent retry loop

### Session Lifecycle
- session.disconnect() replaces session.destroy() (v0.1.32+)
- Sessions are stateful — one prompt per session
- No session reuse across complete() calls

### Known SDK Events (Audit Date: 2026-03-08)
- assistant.message_delta → Content streaming
- assistant.reasoning_delta → Thinking streaming  
- assistant.message → Complete message with tool_requests
- session.idle → Completion signal
- error → SDK error event
- [~50 others] → Dropped with debug logging
```

This is **living documentation** that an AI agent can read, reference, and use to diagnose problems. It's infinitely more useful than a Python test that says `assert hasattr(session, 'disconnect')`.

### Behavior: `copilot-deny-destroy`

The Deny + Destroy pattern is the provider's defining architectural commitment. It deserves its own context file, not just comments in Python:

```markdown
# context/deny-destroy-pattern.md

## The Deny + Destroy Pattern

### Problem
The Copilot SDK is agentic. It has its own tool execution loop. If we let it
run, it becomes a "second orchestrator" that conflicts with Amplifier's
orchestrator. Evidence: Session a1a0af17 — 305 turns, 607 tool calls from a
single request.

### Solution
1. Register tools with SDK (LLM sees structured definitions)
2. Deny ALL execution via preToolUse hook
3. Capture tool_requests from streaming events
4. Destroy session immediately after capture

### Why This Works
- LLM generates proper tool calls (it sees the definitions)
- SDK never executes them (deny hook)
- Amplifier gets the tool calls back (capture)
- SDK can't retry (session destroyed)

### Fragility
This depends on undocumented SDK behavior:
- Event ordering (events before hooks)
- Deny semantics (prevents execution, allows capture)
- Destroy semantics (terminates agent loop)

### Upgrade Checklist
When upgrading SDK version:
1. Verify event ordering hasn't changed
2. Verify deny still prevents execution
3. Verify destroy/disconnect terminates loop
4. Run integration test with real SDK
```

This context file replaces hundreds of lines of comments scattered across provider.py, tool_capture.py, and sdk_driver.py. It's the single source of truth, referenced by `@copilot-provider:context/deny-destroy-pattern.md`.

---

## 5. Context Files That Should Drive Behavior

Following Amplifier's `context/` pattern, the provider should have:

| File | Purpose | Replaces |
|------|---------|----------|
| `context/sdk-assumptions.md` | SDK contract documentation | Python assumption tests, code comments |
| `context/deny-destroy-pattern.md` | Architecture decision record | Scattered comments across 3 files |
| `context/error-mapping.md` | Error translation table | 322 lines of exception classes |
| `context/model-limits.md` | Known model capabilities | `BUNDLED_MODEL_LIMITS` dict in Python |
| `context/streaming-events.md` | Event handling documentation | Comments in provider.py |
| `context/upgrade-checklist.md` | SDK upgrade procedures | The "recipe" from Golden Vision |

These files serve triple duty:
1. **Human documentation** — readable, diffable, reviewable
2. **AI context** — an agent maintaining this provider reads these files to understand the domain
3. **Behavioral specification** — the Python code implements what these files describe

This is the Amplifier pattern. The recipes bundle does this. The foundation does this. Every well-structured bundle does this.

---

## 6. SDK Assumptions: Declared in YAML/Markdown, Not Python Tests

The Golden Vision proposes "SDK Assumption Tests" as Python code:

```python
def test_session_has_disconnect():
    """SDK assumption: session object has disconnect() method."""
    assert hasattr(session, 'disconnect')
```

This is **the wrong abstraction**. In Amplifier's world, SDK assumptions are **documented facts** in context files that can be verified by any mechanism — including, but not limited to, Python tests.

The right approach:

```markdown
# context/sdk-assumptions.md

## Verified Assumptions (last checked: 2026-03-08, SDK v0.1.32)

### API Surface
- [ ] `Session` has `disconnect()` method (replaced `destroy()` in v0.1.32)
- [ ] `Session` accepts `preToolUse` hook in creation config
- [ ] `preToolUse` hook receives tool name and can return deny
- [ ] `Session.send_message()` returns async iterator of events

### Event Types
- [ ] `assistant.message_delta` contains `text` field
- [ ] `assistant.reasoning_delta` contains `text` field  
- [ ] `assistant.message` contains `tool_requests` array
- [ ] `error` event contains `message` field

### Behavioral
- [ ] Denied tools trigger SDK retry with built-in tools
- [ ] Session disconnect terminates the retry loop
- [ ] Events arrive before hook execution
```

A simple script can verify these checkboxes against the actual SDK. An AI agent can read this file and understand exactly what the provider depends on. A human can review it in a PR. **Text-first, inspectable surfaces** — that's Kernel Philosophy tenet #7.

---

## The 300-Line Challenge: Not Just Achievable, But *Required*

The Council of Elders quote: "If limited to 300 lines: Keep provider.py→200 lines, converters.py→100 lines. Everything else is policy that shouldn't be in the provider."

Let me be precise about what those 300 lines contain:

**provider.py (~200 lines)**:
- `mount()` function — 10 lines
- `CopilotProvider.__init__()` — 15 lines (read config from YAML)
- `get_info()` — 5 lines
- `list_models()` — 30 lines (call SDK, cache result)
- `complete()` — 80 lines (create session, send prompt, stream events, translate, destroy)
- `parse_tool_calls()` — 20 lines
- Error translation dispatch — 30 lines (read mapping table, match pattern, raise)
- Imports and class definition — 10 lines

**converters.py (~100 lines)**:
- `convert_messages_to_prompt()` — 40 lines
- `convert_copilot_response_to_chat_response()` — 40 lines
- `extract_system_message()` — 15 lines
- Imports — 5 lines

Everything else:
- **Timeouts, retries, pagination limits** → YAML config (0 lines of Python)
- **Error patterns and detection** → context/error-mapping.md (0 lines of Python)
- **SDK assumptions** → context/sdk-assumptions.md (0 lines of Python)
- **Architecture documentation** → context/deny-destroy-pattern.md (0 lines of Python)
- **Model capabilities** → context/model-limits.md (0 lines of Python)
- **Fake tool call detection** → Not the provider's job (0 lines of Python)
- **Streaming metrics/TTFT** → Hook module, not provider (0 lines of Python)
- **Model cache persistence** → Use Amplifier's infrastructure (0 lines of custom cache code)

The existing `sdk_driver.py` (620 lines), `client.py`, and `tool_capture.py` (218 lines) remain as mechanism code — they handle the actual SDK interaction. But the *provider* — the thing that implements the Provider Protocol — is 300 lines.

---

## What the Golden Vision Got Right

To be fair, the Golden Vision correctly identified:

1. **The Deny + Destroy pattern is non-negotiable** — Absolutely correct. This is the provider's core mechanism.
2. **Translation, not framework** — The right principle. But the implementation contradicts it.
3. **SDK changes are certainties to design for** — Correct. But the response should be documented assumptions in markdown, not a five-tier testing diamond.
4. **The Two Orchestrators problem is the biggest risk** — Correct. This is well-understood.
5. **"Build the provider. Make it observable. Make it resilient. In that order."** — Perfect prioritization. But "make it observable" means hooks, not custom Python metrics code.

## What the Golden Vision Got Wrong

1. **Treating the provider as a standalone application** — It's a module in a bundle. It inherits from the ecosystem, it doesn't reinvent it.
2. **Putting policy in Python** — Timeouts, retries, error patterns, model limits — all should be YAML/markdown.
3. **Building a testing framework** — "Contract-Anchored Diamond" with speed tiers, evidence capture, and structured output is a framework. Use pytest. Document contracts in markdown.
4. **The autonomy model** — Four tiers of autonomy with decision trees and confidence scoring is organizational policy, not provider architecture. This belongs in a team playbook, not in code.
5. **17 modules for a translation layer** — If you need 17 modules, you're not building a translation layer. You're building an application.
6. **Ignoring the bundle system** — The entire critique: not once does the Golden Vision mention `bundle.md`, `behaviors/`, `context/`, or the Thin Bundle Pattern. It proposes a pure Python architecture in an ecosystem built on YAML + markdown composition.

---

## The Amplifier Way: A Summary

| Principle | Golden Vision | Amplifier Way |
|-----------|--------------|---------------|
| Structure | Python package with 17 modules | Bundle with behavior + thin module |
| Policy | Python code with constants | YAML config with defaults |
| Documentation | Code comments + docstrings | Context files (markdown) |
| SDK assumptions | Python tests | Documented facts in markdown |
| Error handling | 322 lines of exception classes | Lookup table in markdown + 30 lines generic code |
| Observability | Custom Python metrics | Hook modules |
| Testing | Five-tier diamond with frameworks | pytest + documented contracts |
| Configuration | Python constants | YAML deep-merged by module ID |
| Provider code | ~1,500+ lines across 17 files | ~300 lines across 2 files |

The Amplifier kernel is 2,600 lines because complexity was ruthlessly pushed to the edges. The provider should be 300 lines because complexity should be pushed to configuration, context files, and the existing ecosystem infrastructure.

**Config-first beats code-first** because config is declarative, diffable, overridable, and composable. Code is imperative, opaque, rigid, and monolithic. Amplifier was designed from the ground up for config-first composition. The Golden Vision ignores this in favor of a code-first Python architecture that happens to run inside Amplifier.

That's not the Amplifier way. The Amplifier way is: **keep the center tiny and timeless. Push everything else to the edges.**

---

*"If it's important, it should be in a context file. If it's configurable, it should be in YAML. If it's mechanism, it should be 300 lines of Python. Everything else is policy that doesn't belong in the provider."*

— The Amplifier Philosophy, applied.
