# Dev-Machine Container for amplifier-module-provider-github-copilot
# Provides isolated autonomous execution environment

FROM python:3.11-slim

# Install system dependencies + GitHub CLI for authenticated git operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for github-copilot-sdk CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager) and PyYAML for recipe orchestration scripts
RUN pip install --no-cache-dir uv pyyaml types-pyyaml yamllint

# Create writable home directory for non-root user execution
# When docker-run.sh uses --user $(id -u):$(id -g), the container runs as host user
# This directory provides a writable HOME for uv, amplifier, git, etc.
RUN mkdir -p /home/amplifier/.local/bin /home/amplifier/.amplifier /home/amplifier/.cache \
    && chmod -R 777 /home/amplifier

# Install Amplifier CLI from git (not on PyPI)
# --with flags inject optional module dependencies into the tool's isolated env:
#   tool-web needs aiohttp, tool-mcp needs mcp
RUN UV_TOOL_DIR=/home/amplifier/.local/share/uv/tools \
    UV_TOOL_BIN_DIR=/home/amplifier/.local/bin \
    uv tool install git+https://github.com/microsoft/amplifier \
    --with aiohttp \
    --with mcp \
    --with beautifulsoup4 \
    && chmod -R 777 /home/amplifier/.local
ENV PATH="/home/amplifier/.local/bin:$PATH"

# Install dev tools GLOBALLY so they survive volume mount shadowing
# When docker-run.sh mounts the host project to /workspace, it shadows any .venv
# created during build. Installing to system Python ensures tools are always available.
RUN pip install --no-cache-dir ruff pyright pytest pytest-asyncio

# Verify dev tools are available system-wide (not via uv run, which uses .venv)
RUN ruff --version && pyright --version && pytest --version

# Set working directory
WORKDIR /workspace

# Copy project files (.dockerignore excludes .venv, reference-only, .git, etc.)
COPY . .

# Create project .venv for project dependencies (not dev tools)
# This gets shadowed at runtime but that's OK - we only need project deps at build time
# for validation. At runtime, uv sync will recreate it.
RUN uv sync

# Verify project imports work at build time (validates pyproject.toml is correct)
RUN uv run python -c "import amplifier_module_provider_github_copilot; print('Module import OK')"

# Git identity at SYSTEM level (works regardless of which user runs the container)
# User-level config won't work because --user flag runs as arbitrary UID without /etc/passwd entry
RUN git config --system user.email "amplifier-ai@microsoft.com" \
    && git config --system user.name "Amplifier Dev Machine" \
    && git config --system --add safe.directory /workspace \
    && git config --system credential.helper "!gh auth git-credential"

# Entry point for autonomous execution
# Recipes run FROM WITHIN an Amplifier session via the recipes tool
ENTRYPOINT ["amplifier", "run"]
CMD ["Execute recipe .dev-machine/build.yaml"]
