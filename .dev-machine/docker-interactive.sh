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

# Step 4: Configure Amplifier to use our provider
echo "[4/5] Configuring Amplifier..."

# Clear any stale state
rm -f ~/.amplifier/cache/install-state.json 2>/dev/null || true

# Register the provider source
if [ "$PROVIDER_SOURCE" = "local" ]; then
    amplifier source add provider-github-copilot /workspace 2>&1 | head -5 || true
fi

# Set up provider in settings
mkdir -p ~/.amplifier
cat > ~/.amplifier/settings.yaml << 'SETTINGS'
# Auto-generated for testing
provider:
  module: provider-github-copilot
  config:
    model: gpt-4o
SETTINGS
echo "      ✓ Provider configured"

# Step 5: Set the bundle
echo "[5/5] Setting up foundation bundle..."
amplifier bundle use foundation 2>&1 | head -3 || true
echo "      ✓ Foundation bundle activated"

echo ""
echo "=== Environment Ready ==="
echo ""
echo "Quick commands:"
echo "  amplifier                    # Interactive mode"
echo "  amplifier run 'Hello'        # Single prompt"
echo "  amplifier --help             # Full help"
echo "  amplifier bundle list        # Available bundles"
echo "  amplifier routing show       # Routing matrix"
echo ""
echo "Test suggestions:"
echo "  1. Say 'Hello'"
echo "  2. Ask 'What is 2+2?'"
echo "  3. Ask 'List files in /workspace'"
echo "  4. Ask 'Read /workspace/README.md'"
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
