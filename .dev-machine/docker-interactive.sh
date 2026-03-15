#!/bin/bash
# Interactive Docker Testing Environment
#
# Usage:
#   ./docker-interactive.sh [local|published]
#
# This creates a Docker container pre-configured with:
# - Amplifier CLI installed
# - Your provider (local or published version)
# - Foundation bundle ready
# - Interactive shell for testing
#
# Examples:
#   ./docker-interactive.sh local       # Test your local code changes
#   ./docker-interactive.sh published   # Test the published version
#   ./docker-interactive.sh             # Defaults to local

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROVIDER_SOURCE="${1:-local}"

echo "🐳 Interactive Amplifier Testing Environment"
echo "Project: $PROJECT_DIR"
echo ""
echo "Provider source: $PROVIDER_SOURCE"
echo ""

# Build the container if needed
if [[ ! "$(docker images -q amplifier-dev-machine:provider-github-copilot 2>/dev/null)" ]]; then
    echo "📦 Building container image (first run)..."
    docker build -t amplifier-dev-machine:provider-github-copilot -f "$PROJECT_DIR/.dev-machine/Dockerfile" "$PROJECT_DIR"
fi

# Set up the entrypoint script for container initialization
INIT_SCRIPT=$(cat << 'INITSCRIPT'
#!/bin/bash
set -e

TOOL_VENV="/home/amplifier/.local/share/uv/tools/amplifier"
PROVIDER_SOURCE="${1:-local}"

echo "=== Initializing Amplifier Environment ==="
echo ""

# Step 1: Install SDK
echo "[1/5] Installing github-copilot-sdk..."
uv pip install --python "$TOOL_VENV/bin/python" "github-copilot-sdk>=0.1.32,<0.2.0" -q
echo "      ✓ SDK installed"

# Step 2: Install provider
echo "[2/5] Installing provider ($PROVIDER_SOURCE)..."
if [ "$PROVIDER_SOURCE" = "local" ]; then
    uv pip install --python "$TOOL_VENV/bin/python" -e /workspace -q
    echo "      ✓ Local provider installed (editable)"
else
    uv pip install --python "$TOOL_VENV/bin/python" \
      "git+https://github.com/microsoft/amplifier-module-provider-github-copilot@main" -q
    echo "      ✓ Published provider installed"
fi

# Step 3: Verify installation
echo "[3/5] Verifying installation..."
"$TOOL_VENV/bin/python" -c "
import amplifier_module_provider_github_copilot
print('      ✓ Provider module importable')
from amplifier_module_provider_github_copilot.provider import GitHubCopilotProvider
p = GitHubCopilotProvider(config={})
print(f'      ✓ Provider info: {p.get_info().id}')
"

# Step 4: Pre-seed settings.yaml to bypass first-run wizard
echo "[4/5] Pre-seeding Amplifier settings..."
rm -f ~/.amplifier/cache/install-state.json 2>/dev/null || true
mkdir -p ~/.amplifier

# The wizard checks if ANY provider is in settings.yaml
# This minimal config bypasses the wizard (expert confirmed)
cat > ~/.amplifier/settings.yaml << 'SETTINGS'
# Pre-seeded to bypass first-run wizard
providers:
  - module: provider-github-copilot
    config:
      model: gpt-4o
      priority: 1
SETTINGS
echo "      ✓ Settings pre-seeded"

# Step 5: Register our shadow test bundle
echo "[5/5] Registering shadow test bundle..."
amplifier bundle add copilot-provider-shadow-test /workspace/.dev-machine/shadow-test-bundle.md 2>&1 | head -5 || true
echo "      ✓ Bundle registered"

echo ""
echo "=== Environment Ready ==="
# Step 6: Run amplifier once non-interactively to trigger auto-init
echo "[6/6] Running auto-init (non-TTY triggers auto_init_from_env)..."
# Pipe empty input to trigger non-interactive mode which auto-detects from env vars
echo "" | amplifier run --bundle copilot-provider-shadow-test "Say INIT_TEST" 2>&1 | head -20 || true
echo "      ✓ Auto-init attempted"

echo ""
echo "=== Environment Ready ==="
echo ""
echo "Quick commands:"
echo "  amplifier run --bundle copilot-provider-shadow-test 'Hello'"
echo "  amplifier run --bundle copilot-provider-shadow-test 'What is 2+2?'"
echo "  amplifier --bundle copilot-provider-shadow-test  # Interactive mode"
echo ""
echo "Other commands:"
echo "  amplifier bundle list        # Available bundles"
echo "  amplifier --help             # Full help"
echo ""
echo "Starting bash shell..."
echo ""

exec /bin/bash
INITSCRIPT
)

# Run the container interactively
echo "🚀 Starting interactive environment..."
echo "─────────────────────────────────────────────────"

# Create a temporary init script file to pass to the container
TEMP_INIT_SCRIPT=$(mktemp)
echo "$INIT_SCRIPT" > "$TEMP_INIT_SCRIPT"
chmod +x "$TEMP_INIT_SCRIPT"

docker run -it --rm \
    -v "$PROJECT_DIR:/workspace:rw" \
    -v "$HOME/.amplifier:/root/.amplifier-host:ro" \
    -v "$TEMP_INIT_SCRIPT:/tmp/init.sh:ro" \
    -e "GITHUB_TOKEN=${GITHUB_TOKEN:-}" \
    -e "GH_TOKEN=${GH_TOKEN:-}" \
    -e "COPILOT_AGENT_TOKEN=${COPILOT_AGENT_TOKEN:-}" \
    -e "PROVIDER_SOURCE=$PROVIDER_SOURCE" \
    -w /workspace \
    --entrypoint /bin/bash \
    amplifier-dev-machine:provider-github-copilot \
    /tmp/init.sh

# Clean up temp file
rm -f "$TEMP_INIT_SCRIPT"
