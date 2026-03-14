#!/bin/bash
# Docker entrypoint: bootstrap dev dependencies AFTER volume mount
# This runs at container start, when /workspace has the host project mounted.
# The volume mount shadows the build-time .venv, so we must recreate it.
#
# Why this exists:
#   docker-run.sh mounts host project to /workspace with -v, which REPLACES
#   the entire /workspace directory including the .venv created during build.
#   This script recreates .venv with all dev deps before the main command runs.
set -e
set -o pipefail  # Catch failures in piped commands

cd /workspace

# Check if .venv exists AND has both critical packages
# Must check .venv specifically — system Python has amplifier-core but NOT github-copilot-sdk
if [ -d ".venv" ] && [ -f ".venv/bin/python" ] \
   && .venv/bin/python -c "import amplifier_core; import copilot" 2>/dev/null; then
    echo "✅ .venv has all dependencies, skipping bootstrap"
else
    echo "📦 Bootstrapping dev dependencies (volume mount shadowed build-time .venv)..."
    # Don't pipe to tail - we need to see errors and preserve exit code
    if ! uv sync --extra dev; then
        echo "⚠️ uv sync failed, attempting individual package installs..."
    fi
    echo "✅ Bootstrap complete"
fi

# Final verification — HARD GATE: fail if deps missing after bootstrap
if ! .venv/bin/python -c "import amplifier_core" 2>/dev/null; then
    echo "⚠️ amplifier-core missing from .venv, attempting direct install..."
    # Target .venv explicitly, not system Python
    uv pip install --python .venv/bin/python amplifier-core
fi

if ! .venv/bin/python -c "import copilot" 2>/dev/null; then
    echo "⚠️ github-copilot-sdk missing from .venv, attempting direct install..."
    # Target .venv explicitly, not system Python
    uv pip install --python .venv/bin/python "github-copilot-sdk>=0.1.32,<0.2.0"
fi

# HARD GATE: Fail container start if deps still missing
if ! .venv/bin/python -c "import amplifier_core; import copilot" 2>/dev/null; then
    echo "❌ FATAL: Critical dependencies still missing after bootstrap attempts."
    echo "   amplifier_core: $(! .venv/bin/python -c 'import amplifier_core' 2>&1 && echo 'MISSING' || echo 'OK')"
    echo "   copilot: $(! .venv/bin/python -c 'import copilot' 2>&1 && echo 'MISSING' || echo 'OK')"
    echo ""
    echo "   Cannot proceed. Check network connectivity and pyproject.toml."
    exit 1
fi

echo "✅ All dependencies verified in .venv"

# Execute the main command (amplifier run ...)
exec "$@"
