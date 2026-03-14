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

cd /workspace

# Check if .venv exists AND has both critical packages
# Must check .venv specifically — system Python has amplifier-core but NOT github-copilot-sdk
if [ -d ".venv" ] && [ -f ".venv/bin/python" ] \
   && .venv/bin/python -c "import amplifier_core; import copilot" 2>/dev/null; then
    echo "✅ .venv has all dependencies, skipping bootstrap"
else
    echo "📦 Bootstrapping dev dependencies (volume mount shadowed build-time .venv)..."
    uv sync --extra dev 2>&1 | tail -5
    echo "✅ Dependencies installed in .venv"
fi

# Final verification — fail fast if something is still wrong
if ! .venv/bin/python -c "import amplifier_core" 2>/dev/null; then
    echo "❌ FATAL: amplifier-core still missing from .venv after bootstrap"
    echo "   Attempting direct install..."
    uv pip install amplifier-core
fi

if ! .venv/bin/python -c "import copilot" 2>/dev/null; then
    echo "❌ FATAL: github-copilot-sdk still missing from .venv after bootstrap"
    echo "   Attempting direct install..."
    uv pip install "github-copilot-sdk>=0.1.32,<0.2.0"
fi

# Execute the main command (amplifier run ...)
exec "$@"
