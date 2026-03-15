#!/usr/bin/env bash
# WSL Forensic Session Analyzer
# Usage: ./wsl_analyze.sh <session_id>

set -e

SESSION_ID="${1:-}"
if [ -z "$SESSION_ID" ]; then
    echo "Usage: $0 <session_id>"
    exit 1
fi

echo "============================================================"
echo "FORENSIC ANALYSIS: $SESSION_ID"
echo "============================================================"

# Find log files containing session
echo ""
echo "[1/4] Searching logs..."
LOG_FILES=$(grep -l "$SESSION_ID" ~/.copilot/logs/*.log 2>/dev/null || true)
if [ -z "$LOG_FILES" ]; then
    echo "  Checking session-store.db..."
    if grep -q "$SESSION_ID" ~/.copilot/session-store.db 2>/dev/null; then
        echo "  ✓ Found in session-store.db"
    else
        echo "  ✗ Session not found in logs or database"
        exit 1
    fi
else
    echo "  ✓ Found in: $LOG_FILES"
fi

# Extract tool-related events from most recent log
echo ""
echo "[2/4] Analyzing tool configuration..."
LATEST_LOG=$(ls -t ~/.copilot/logs/*.log 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ]; then
    echo "  Log: $(basename $LATEST_LOG)"
    
    # Check tools_available event
    echo ""
    echo "  === TOOLS AVAILABLE (SDK config) ==="
    grep -A3 '"kind": "tools_available"' "$LATEST_LOG" 2>/dev/null | head -10 || echo "  (not found)"
    
    # Check for tool invocations
    echo ""
    echo "  === TOOL INVOCATIONS ==="
    grep -E "tool_use|tool_call|preToolUse|permission" "$LATEST_LOG" 2>/dev/null | head -10 || echo "  (none found)"
fi

# Check for SDK errors
echo ""
echo "[3/4] Checking for errors..."
if [ -n "$LATEST_LOG" ]; then
    ERRORS=$(grep -c '\[ERROR\]' "$LATEST_LOG" 2>/dev/null || echo "0")
    WARNINGS=$(grep -c '\[WARNING\]' "$LATEST_LOG" 2>/dev/null || echo "0")
    echo "  Errors: $ERRORS"
    echo "  Warnings: $WARNINGS"
    
    if [ "$ERRORS" -gt 0 ]; then
        echo ""
        echo "  Recent errors:"
        grep '\[ERROR\]' "$LATEST_LOG" | tail -5
    fi
fi

# Verdict
echo ""
echo "[4/4] Verdict..."
echo ""

# Check if available_tools is empty (F-045 working)
if grep -q '"tool_count": 0' "$LATEST_LOG" 2>/dev/null; then
    echo "✅ F-045 WORKING: SDK tools disabled (tool_count: 0)"
else
    TOOL_COUNT=$(grep -oP '"tool_count":\s*\K\d+' "$LATEST_LOG" 2>/dev/null | head -1 || echo "unknown")
    echo "⚠️  F-045 STATUS: tool_count = $TOOL_COUNT"
fi

# Check for denied tool calls
if grep -q "denied" "$LATEST_LOG" 2>/dev/null; then
    echo "✅ DENY HOOK ACTIVE: Tool calls being denied"
else
    echo "ℹ️  No tool denials detected (may be OK if no tools called)"
fi

echo ""
echo "============================================================"
echo "Analysis complete"
echo "============================================================"
