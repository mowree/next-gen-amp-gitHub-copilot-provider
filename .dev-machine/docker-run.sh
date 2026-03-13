#!/bin/bash
# Dev-Machine Docker Runner
# Run the autonomous development machine in an isolated container

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_NAME="amplifier-dev-machine:provider-github-copilot"

echo "🐳 Dev-Machine Docker Runner"
echo "Project: $PROJECT_DIR"
echo ""

# Build the image if it doesn't exist or if --build flag is passed
if [[ "$1" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "📦 Building container image..."
    docker build -t "$IMAGE_NAME" -f "$PROJECT_DIR/.dev-machine/Dockerfile" "$PROJECT_DIR"
    echo ""
fi

# Run the dev-machine
echo "🚀 Starting autonomous dev-machine..."
echo "   Recipe: .dev-machine/build.yaml"
echo "   Output will appear below:"
echo "─────────────────────────────────────────────────"

# Build docker run command with proper argument handling
# KEY FIX: Run as host user to prevent root-owned files in mounted volume
# This ensures .git/objects/, STATE.yaml, etc. are owned by the host user
# Expert consensus: 4/4 recommend --user flag (zen-architect, integration-specialist, explorer, web-research)
DOCKER_ARGS=(
    --rm
    --user "$(id -u):$(id -g)"
    -v "$PROJECT_DIR:/workspace"
    -v "$HOME/.gitconfig:/home/amplifier/.gitconfig:ro"
    -v "$HOME/.amplifier:/home/amplifier/.amplifier"
    -e "GITHUB_TOKEN=${GITHUB_TOKEN:-}"
    -e "GH_TOKEN=${GH_TOKEN:-}"
    -e "COPILOT_AGENT_TOKEN=${COPILOT_AGENT_TOKEN:-}"
    -e "HOME=/home/amplifier"
)

# Add credential mount if file exists
if [ -f "$HOME/.git-credentials" ]; then
    DOCKER_ARGS+=(-v "$HOME/.git-credentials:/home/amplifier/.git-credentials:ro")
fi

docker run "${DOCKER_ARGS[@]}" "$IMAGE_NAME" .dev-machine/build.yaml

echo "─────────────────────────────────────────────────"
echo "✅ Dev-machine execution complete"
