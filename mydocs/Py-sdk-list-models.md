# GitHub Copilot SDK Model Catalog

Baseline captures from `uv run python .tools/list-sdk-models.py`

---

## 2026-03-15 — Initial Baseline

**Total Models:** 18

| Model ID | Context Window | Max Output | Vision | Billing | Reasoning |
|----------|----------------|------------|--------|---------|-----------|
| claude-sonnet-4.6 | 200,000 | 168,000 | Yes | 1.0x | low/medium/high |
| claude-sonnet-4.5 | 200,000 | 168,000 | Yes | 1.0x | — |
| claude-haiku-4.5 | 200,000 | 136,000 | Yes | 0.33x | — |
| claude-opus-4.6 | 200,000 | 168,000 | Yes | 3.0x | low/medium/high |
| claude-opus-4.6-1m | 1,000,000 | 936,000 | Yes | 6.0x | low/medium/high |
| claude-opus-4.5 | 200,000 | 168,000 | Yes | 3.0x | — |
| claude-sonnet-4 | 216,000 | 128,000 | Yes | 1.0x | — |
| gemini-3-pro-preview | 200,000 | 136,000 | Yes | 1.0x | — |
| gpt-5.4 | 400,000 | 272,000 | Yes | 1.0x | low/medium/high/xhigh |
| gpt-5.3-codex | 400,000 | 272,000 | Yes | 1.0x | low/medium/high/xhigh |
| gpt-5.2-codex | 400,000 | 272,000 | Yes | 1.0x | low/medium/high/xhigh |
| gpt-5.2 | 400,000 | 272,000 | Yes | 1.0x | low/medium/high |
| gpt-5.1-codex-max | 400,000 | 128,000 | Yes | 1.0x | low/medium/high/xhigh |
| gpt-5.1-codex | 400,000 | 128,000 | Yes | 1.0x | low/medium/high |
| gpt-5.1 | 264,000 | 128,000 | Yes | 1.0x | low/medium/high |
| gpt-5.1-codex-mini | 400,000 | 128,000 | Yes | 0.33x | low/medium/high |
| gpt-5-mini | 264,000 | 128,000 | Yes | 0.0x | low/medium/high |
| gpt-4.1 | 128,000 | 64,000 | Yes | 0.0x | — |

### Notes
- All models have `Policy: enabled`
- `gpt-4o` from legacy specs does NOT exist — use `gpt-4.1`
- `claude-opus-4.5` is available (your requested default)
