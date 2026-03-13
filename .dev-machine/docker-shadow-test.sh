#!/bin/bash
# Shadow Test Docker Runner
# Run E2E shadow tests in isolated container environment
# Separate from build.yaml - on-demand validation before releases

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_NAME="amplifier-dev-machine:provider-github-copilot"

echo "🔬 Shadow Test Runner"
echo "Project: $PROJECT_DIR"
echo ""

# Parse arguments
PROVIDER_SOURCE="${1:-local}"
SDK_VERSION="${2:-latest}"

echo "Provider source: $PROVIDER_SOURCE"
echo "SDK version: $SDK_VERSION"
echo ""

# Build the image if needed
if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "📦 Building container image..."
    docker build -t "$IMAGE_NAME" -f "$PROJECT_DIR/.dev-machine/Dockerfile" "$PROJECT_DIR"
    echo ""
fi

# Prepare results directory
mkdir -p "$PROJECT_DIR/.dev-machine/shadow-results"

echo "🚀 Starting shadow tests..."
echo "─────────────────────────────────────────────────────"

# Build docker run arguments
DOCKER_ARGS=(
    --rm
    --user "$(id -u):$(id -g)"
    -v "$PROJECT_DIR:/workspace"
    -v "$HOME/.amplifier:/home/amplifier/.amplifier"
    -e "GITHUB_TOKEN=${GITHUB_TOKEN:-}"
    -e "GH_TOKEN=${GH_TOKEN:-}"
    -e "COPILOT_AGENT_TOKEN=${COPILOT_AGENT_TOKEN:-}"
    -e "HOME=/home/amplifier"
    -e "PROVIDER_SOURCE=$PROVIDER_SOURCE"
    -e "SDK_VERSION=$SDK_VERSION"
)

# Add credential mounts if available
if [ -f "$HOME/.git-credentials" ]; then
    DOCKER_ARGS+=(-v "$HOME/.git-credentials:/home/amplifier/.git-credentials:ro")
fi

if [ -f "$HOME/.gitconfig" ]; then
    DOCKER_ARGS+=(-v "$HOME/.gitconfig:/home/amplifier/.gitconfig:ro")
fi

# Run with custom entrypoint to install provider first
docker run "${DOCKER_ARGS[@]}" \
    --entrypoint bash "$IMAGE_NAME" -c '
    set -e
    echo "=== Installing provider into Amplifier runtime ==="
    
    # Find Amplifier tool venv
    TOOL_VENV="/home/amplifier/.local/share/uv/tools/amplifier"
    if [ ! -d "$TOOL_VENV" ]; then
        echo "ERROR: Amplifier tool venv not found"
        exit 1
    fi
    
    # Install provider based on source
    # Use uv pip with --python flag (uv tool venvs do not have pip module)
    case "$PROVIDER_SOURCE" in
        local)
            echo "Installing LOCAL provider..."
            uv pip install --python "$TOOL_VENV/bin/python" -e /workspace --no-deps -q
            uv pip install --python "$TOOL_VENV/bin/python" github-copilot-sdk pyyaml -q
            ;;
        pypi)
            echo "Installing PUBLIC provider from PyPI..."
            uv pip install --python "$TOOL_VENV/bin/python" amplifier-module-provider-github-copilot -q
            ;;
        *)
            echo "Installing from: $PROVIDER_SOURCE..."
            uv pip install --python "$TOOL_VENV/bin/python" "$PROVIDER_SOURCE" -q
            ;;
    esac
    
    # Handle SDK version
    if [ "$SDK_VERSION" != "latest" ]; then
        uv pip install --python "$TOOL_VENV/bin/python" "github-copilot-sdk$SDK_VERSION" -q
    fi
    
    # Verify installation
    echo ""
    echo "=== Verifying provider installation ==="
    "$TOOL_VENV/bin/python" -c "
from importlib.metadata import entry_points
eps = entry_points(group=\"amplifier.modules\")
found = [ep for ep in eps if ep.name == \"provider-github-copilot\"]
if found:
    print(f\"Entry point found: {found[0]}\")
    mod = found[0].load()
    print(f\"Module loaded: {mod}\")
else:
    print(\"ERROR: Entry point not found\")
    exit(1)
"
    
    echo ""
    echo "=== Running shadow test recipe ==="
    amplifier run "Execute recipe .dev-machine/shadow-test.yaml with provider_source=$PROVIDER_SOURCE sdk_version=$SDK_VERSION"
'

EXIT_CODE=$?

echo "─────────────────────────────────────────────────────"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Shadow tests complete"
    echo ""
    echo "Results in: .dev-machine/shadow-results/"
    ls -la "$PROJECT_DIR/.dev-machine/shadow-results/"
else
    echo "❌ Shadow tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
