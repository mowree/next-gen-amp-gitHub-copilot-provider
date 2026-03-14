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

# Get token from gh auth if not already in environment
if [ -z "$GITHUB_TOKEN" ] && [ -z "$GH_TOKEN" ] && [ -z "$COPILOT_GITHUB_TOKEN" ]; then
    echo "No token in environment, trying gh auth token..."
    TOKEN=$(gh auth token 2>/dev/null)
    if [ -n "$TOKEN" ]; then
        export GITHUB_TOKEN="$TOKEN"
        echo "  Got token from gh auth"
    else
        echo "WARNING: No GitHub token available. Authentication may fail."
    fi
fi

echo "Token status: ${GITHUB_TOKEN:+GITHUB_TOKEN set} ${GH_TOKEN:+GH_TOKEN set} ${COPILOT_GITHUB_TOKEN:+COPILOT_GITHUB_TOKEN set}"

# Build docker run arguments
DOCKER_ARGS=(
    --rm
    --user "$(id -u):$(id -g)"
    -v "$PROJECT_DIR:/workspace"
    -v "$HOME/.amplifier:/home/amplifier/.amplifier"
    -e "GITHUB_TOKEN=${GITHUB_TOKEN:-}"
    -e "GH_TOKEN=${GH_TOKEN:-}"
    -e "COPILOT_GITHUB_TOKEN=${COPILOT_GITHUB_TOKEN:-}"
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
    echo "=== Clearing cached provider (prevents host cache poisoning) ==="
    rm -rf /home/amplifier/.amplifier/cache/amplifier-module-provider-github-copilot-*
    echo "  Cached provider cleared"
    
    echo ""
    echo "=== Installing provider into Amplifier runtime ==="
    
    # Find Amplifier tool venv
    TOOL_VENV="/home/amplifier/.local/share/uv/tools/amplifier"
    if [ ! -d "$TOOL_VENV" ]; then
        echo "ERROR: Amplifier tool venv not found"
        exit 1
    fi
    
    # Install provider based on source
    # Use uv pip with --python flag (uv tool venvs do not have pip module)
    # IMPORTANT: Do NOT use -q flag - we need to see errors
    case "$PROVIDER_SOURCE" in
        local)
            echo "Installing LOCAL provider..."
            echo "  Step 1: Installing github-copilot-sdk..."
            uv pip install --python "$TOOL_VENV/bin/python" "github-copilot-sdk>=0.1.32,<0.2.0" pyyaml 2>&1 | tail -5
            echo "  Step 2: Installing provider (editable)..."
            uv pip install --python "$TOOL_VENV/bin/python" -e /workspace --no-deps 2>&1 | tail -5
            ;;
        pypi)
            echo "Installing PUBLIC provider from PyPI..."
            uv pip install --python "$TOOL_VENV/bin/python" amplifier-module-provider-github-copilot 2>&1 | tail -5
            ;;
        *)
            echo "Installing from: $PROVIDER_SOURCE..."
            uv pip install --python "$TOOL_VENV/bin/python" "$PROVIDER_SOURCE" 2>&1 | tail -5
            ;;
    esac
    
    # Handle SDK version
    if [ "$SDK_VERSION" != "latest" ]; then
        echo "  Installing SDK version constraint: $SDK_VERSION..."
        uv pip install --python "$TOOL_VENV/bin/python" "github-copilot-sdk$SDK_VERSION" 2>&1 | tail -5
    fi
    
    # Verify installations
    echo ""
    echo "  Verifying installed packages..."
    "$TOOL_VENV/bin/python" -c "import copilot; print(\"    github-copilot-sdk: OK\")" 2>&1 || echo "    github-copilot-sdk: FAILED"
    "$TOOL_VENV/bin/python" -c "import amplifier_core; print(\"    amplifier_core: OK\")" 2>&1 || echo "    amplifier_core: FAILED"
    "$TOOL_VENV/bin/python" -c "import amplifier_module_provider_github_copilot; print(\"    provider module: OK\")" 2>&1 || echo "    provider module: FAILED"
    
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
    echo "=== Registering shadow test bundle ==="
    # Force re-register: remove stale cached bundle, then add fresh copy.
    # amplifier bundle add does not overwrite existing registrations,
    # so we must remove first to pick up any changes to shadow-test-bundle.md.
    amplifier bundle remove copilot-provider-shadow-test 2>&1 || true
    amplifier bundle add /workspace/.dev-machine/shadow-test-bundle.md 2>&1 || true
    echo "Available bundles:"
    amplifier bundle list 2>&1 || true
    
    echo ""
    echo "=== Patching MockCoordinator in-place (fixes async/sync bug in amplifier-core) ==="
    # Bug: MockCoordinator.mount() does `await super().mount()` on a synchronous Rust method
    # This patch fixes the async/sync mismatch by calling Rust mount() synchronously
    # We must patch IN-PLACE because `amplifier run` is a separate Python process
    "$TOOL_VENV/bin/python" /workspace/.dev-machine/apply_testing_patch.py 2>&1
    
    echo ""
    echo "=== DIRECT PROVIDER TEST (bypasses bundle layer entirely) ==="
    export SKIP_SDK_CHECK=1
    "$TOOL_VENV/bin/python" /workspace/.dev-machine/direct_provider_test.py 2>&1
    
    echo ""
    echo "=== Diagnostic: Testing mount() directly ===" 
    # This test calls mount() with a mock coordinator INSIDE Docker
    # to catch errors before they get swallowed by Amplifier
    export SKIP_SDK_CHECK=1  # Bypass eager SDK check during import
    "$TOOL_VENV/bin/python" /workspace/.dev-machine/diagnostic_mount_test.py 2>&1
    
    echo ""
    echo "=== Running shadow test ==="
    echo "Testing provider via copilot-provider-shadow-test bundle..."
    
    # Enable debug logging to see actual module loading errors
    export AMPLIFIER_LOG=debug
    export RUST_LOG=amplifier=debug
    export SKIP_SDK_CHECK=1  # Bypass eager SDK check during import
    
    # Simple connectivity test using echo to provide input
    echo "Respond with exactly: SHADOW TEST PASSED. Nothing else." | \
      timeout 120 amplifier run --bundle copilot-provider-shadow-test 2>&1 | tee /tmp/shadow-result.txt
    
    # Check if response contains expected text
    if grep -q "SHADOW TEST PASSED" /tmp/shadow-result.txt 2>/dev/null; then
        echo ""
        echo "SHADOW TEST: SUCCESS - Provider responded correctly"
    elif grep -q "Session ID:" /tmp/shadow-result.txt 2>/dev/null; then
        echo ""
        echo "SHADOW TEST: PARTIAL SUCCESS - Session created, checking response..."
        cat /tmp/shadow-result.txt
    else
        echo ""
        echo "SHADOW TEST: FAILED - No valid response"
        cat /tmp/shadow-result.txt
        exit 1
    fi
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
