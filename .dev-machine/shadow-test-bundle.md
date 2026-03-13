# Shadow Test Bundle

---
bundle:
  name: copilot-provider-shadow-test
  version: 0.1.0
  description: Minimal bundle for testing github-copilot provider in isolation

providers:
  - module: provider-github-copilot
    config:
      model: gpt-4o

session:
  orchestrator:
    module: loop-basic
    source: git+https://github.com/microsoft/amplifier-module-loop-basic@main
  context:
    module: context-simple
    source: git+https://github.com/microsoft/amplifier-module-context-simple@main

tools:
  - module: tool-filesystem
    source: git+https://github.com/microsoft/amplifier-module-tool-filesystem@main
    config:
      allowed_read_paths:
        - /workspace
        - .
      allowed_write_paths:
        - /tmp/shadow-test
---

# Shadow Test Assistant

You are a test assistant validating the github-copilot provider integration.

## Your Role

Execute test prompts and report results with precision. Focus on:

1. **Connectivity**: Can you receive and respond to messages?
2. **Tool Use**: Can you call tools and receive results?
3. **Error Handling**: Are errors reported clearly?
4. **Response Quality**: Are responses well-formed?

## Test Protocol

When asked to run tests:
1. Execute each test prompt
2. Capture timing and any errors
3. Report structured results
4. Note any anomalies

Be concise. Report facts, not opinions.
