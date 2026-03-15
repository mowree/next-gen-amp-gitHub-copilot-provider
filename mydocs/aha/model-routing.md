Amplifier:
Good catch. The session analyst confirmed: routing matrix is configured, but the dev-machine session isn't using it yet. All 7 LLM requests went to claude-opus-4.5.

Why: The dev-machine bundle (and most bundles) don't automatically specify model_role when making LLM calls. They use the session default. Model routing kicks in when agents explicitly pass model_role: "fast" or model_role: "reasoning"
etc.

This is expected behavior for now. The routing becomes more useful when:

 1 Sub-agents are spawned with specific roles
 2 The orchestrator is configured to route different phases to different models
 3 Bundles explicitly request model roles

For your current work: This doesn't block anything. The dev-machine is using Opus for everything, which is fine for the scaffold bootstrapping.

How's the dev-machine doing with the bootstrap? Has it created the project scaffold yet?
