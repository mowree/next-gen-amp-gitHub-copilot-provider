# Dev Machine Explained

## Topic 1: Why Docker?

The dev-machine bundle has a **safety check** that blocks autonomous execution on your bare laptop/WSL.

### Why the Safety Check Exists

The autonomous loop runs `amplifier recipe execute .dev-machine/build.yaml` which:
- Spawns AI sessions that write code
- Runs bash commands (ruff, pyright, pytest)
- Makes git commits

### The Risk

If something goes wrong, an autonomous loop could:
- Fill your disk with files
- Make hundreds of bad commits
- Run indefinitely burning API credits

### Docker Provides Isolation

- Constrained disk space
- Easy to kill and reset
- Your host system is protected

### The Bypass (`DEV_MACHINE_ALLOW_HOST=1`)

- Tells the machine "I understand the risk, run anyway"
- Use this for single iterations or supervised runs
- **Not recommended** for "go to lunch" scenarios

---

## Topic 2: Why amplifier-core Was Compiled Locally

### What Happened

Your `pyproject.toml` has this dev dependency:
```toml
"amplifier-core @ git+https://github.com/microsoft/amplifier-core",
```

### Why It's There

- You need `amplifier_core` types for development (imports like `ChatRequest`, `AuthenticationError`, `ProviderInfo`)
- For testing, pyright, and IDE autocomplete
- The `@` syntax means "install from this git URL"

### Why It Compiled (~6 minutes)

- `amplifier-core` is a **Rust+Python hybrid** (uses PyO3/maturin)
- Installing from git means building from source
- Rust compilation is slow but one-time — now cached in `~/.cache/uv/`

### How It Relates to Your New Provider

| At Development Time | At Runtime |
|---------------------|------------|
| You import from `amplifier_core` for type hints, error classes | Amplifier provides `amplifier_core` — it's already installed |
| You test against the kernel contracts | Your provider just works as a plugin |
| Your provider depends on the types | Your provider doesn't SHIP `amplifier_core` |

### Bottom Line

You compiled it once for development. Users of your provider won't compile it — they'll have Amplifier installed, which includes `amplifier-core`.

---

## Topic 3: Setting Up Git for Dev-Machine Commits

*(To be documented after setup)*

---

*Document created: 2026-03-08*
*For project: amplifier-module-provider-github-copilot*
