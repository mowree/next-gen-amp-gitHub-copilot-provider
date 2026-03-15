#!/usr/bin/env bash
# pull_mydocs.sh - Force-pull latest main for the mydocs parent repo
# Uses fetch + reset --hard (safe for reference/docs usage)
# Usage: ./pull_mydocs.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null)"
LOG_DIR="$SCRIPT_DIR/.mydocs-pull-logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
SUMMARY_LOG="$LOG_DIR/pull_${TIMESTAMP}.log"

G="\033[0;32m"; R="\033[0;31m"; Y="\033[0;33m"; C="\033[0;36m"; N="\033[0m"

echo -e "${C}=== MyDocs Repo Pull - $(date) ===${N}"
echo "Script dir: $SCRIPT_DIR"
echo "Repo root:  $REPO_DIR"
echo "Log file:   $SUMMARY_LOG"
echo ""

if [[ -z "$REPO_DIR" ]]; then
    echo -e "${R}ERROR: Could not find git repo root from $SCRIPT_DIR${N}"
    exit 1
fi

cd "$REPO_DIR"

REPO_NAME="$(basename "$REPO_DIR")"
BEFORE_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "NO_REMOTE")

echo -e "Repo:   ${G}${REPO_NAME}${N}"
echo -e "Remote: $REMOTE_URL"
echo -e "Before: $BEFORE_SHA"
echo ""

{
    echo "=== $REPO_NAME ==="
    echo "Dir: $REPO_DIR"
    echo "Remote: $REMOTE_URL"
    echo "Started: $(date)"
    echo "Before SHA: $BEFORE_SHA"
} > "$SUMMARY_LOG"

if [[ "$REMOTE_URL" == "NO_REMOTE" ]]; then
    echo -e "${R}FAILED - no origin remote configured${N}"
    echo "STATUS: FAILED - no origin remote" >> "$SUMMARY_LOG"
    exit 1
fi

# Stash any local changes
STASH_OUTPUT=$(git stash 2>&1)
if [[ "$STASH_OUTPUT" != "No local changes to save" ]]; then
    echo -e "${Y}Stashed local changes${N}"
    echo "Stashed: yes" >> "$SUMMARY_LOG"
else
    echo "No local changes to stash"
    echo "Stashed: no" >> "$SUMMARY_LOG"
fi

# Fetch
echo ""
echo -e "${C}Fetching origin...${N}"
if ! git fetch origin 2>&1; then
    echo -e "${R}FAILED - fetch failed${N}"
    echo "STATUS: FAILED - fetch failed" >> "$SUMMARY_LOG"
    exit 1
fi

# Verify origin/main exists
if ! git rev-parse origin/main &>/dev/null; then
    echo -e "${R}FAILED - origin/main not found${N}"
    echo "STATUS: FAILED - origin/main not found" >> "$SUMMARY_LOG"
    exit 1
fi

# Checkout main and reset
echo -e "${C}Checking out main and resetting...${N}"
git checkout main 2>&1 || true
git reset --hard origin/main 2>&1

AFTER_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

echo ""
echo -e "${C}=== RESULT ===${N}"

if [[ "$BEFORE_SHA" == "$AFTER_SHA" ]]; then
    echo -e "  ${G}✓ UP-TO-DATE${N}  $REPO_NAME ($AFTER_SHA)"
    echo "After SHA: $AFTER_SHA" >> "$SUMMARY_LOG"
    echo "STATUS: OK - already up to date" >> "$SUMMARY_LOG"
else
    echo -e "  ${G}✓ UPDATED${N}  $REPO_NAME"
    echo -e "  $BEFORE_SHA -> $AFTER_SHA"
    echo "After SHA: $AFTER_SHA" >> "$SUMMARY_LOG"
    echo "STATUS: UPDATED - $BEFORE_SHA -> $AFTER_SHA" >> "$SUMMARY_LOG"

    # Show what changed in mydocs/
    echo ""
    echo -e "${C}Changes in mydocs/:${N}"
    git diff --stat "$BEFORE_SHA" "$AFTER_SHA" -- mydocs/ 2>/dev/null || echo "  (could not diff)"
fi

echo ""
echo -e "${C}Done.${N}"
