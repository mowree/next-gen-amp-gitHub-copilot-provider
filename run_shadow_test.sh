#!/bin/bash
set -e

cd /home/mowrim/projects/next-get-provider-github-copilot

docker run --rm \
  -v "$PWD:/workspace" \
  -v "$HOME/.amplifier:/home/amplifier/.amplifier" \
  -e "GITHUB_TOKEN=${GITHUB_TOKEN:-}" \
  -e "GH_TOKEN=${GH_TOKEN:-}" \
  -e "COPILOT_GITHUB_TOKEN=${COPILOT_GITHUB_TOKEN:-}" \
  -e "HOME=/home/amplifier" \
  amplifier-dev-machine:provider-github-copilot \
  bash << 'DOCKER_EOF'
set -e
echo "=== Installing provider ==="
TOOL_VENV="/home/amplifier/.local/share/uv/tools/amplifier"
uv pip install --python "$TOOL_VENV/bin/python" -e /workspace --no-deps -q
uv pip install --python "$TOOL_VENV/bin/python" github-copilot-sdk pyyaml -q

echo "=== Verifying entry point ==="
"$TOOL_VENV/bin/python" -c '
from importlib.metadata import entry_points
eps = entry_points(group="amplifier.modules")
found = [ep for ep in eps if ep.name == "provider-github-copilot"]
if found:
    print(f"Entry point: {found[0]}")
    mod = found[0].load()
    print(f"Module: {mod}")
else:
    print("ERROR: Entry point not found")
    exit(1)
'

echo "=== Listing available bundles ==="
amplifier bundle list

echo "=== Attempting bundle registration ==="
amplifier bundle add /workspace/.dev-machine/shadow-test-bundle.md 2>&1 || echo "Bundle add result: $?"

echo "=== Listing bundles after add ==="
amplifier bundle list
DOCKER_EOF
