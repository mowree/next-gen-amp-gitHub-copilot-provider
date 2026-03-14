#!/bin/bash
# Apply in-place patch to MockCoordinator.mount() in amplifier-core
# Bug: MockCoordinator.mount() does `await super().mount()` on a synchronous Rust method
# Fix: Replace with direct ModuleCoordinator.mount() call

set -e

TOOL_VENV="${1:-/home/amplifier/.local/share/uv/tools/amplifier}"

# Find the testing.py file
TESTING_PY=$("$TOOL_VENV/bin/python" -c "import amplifier_core.testing; print(amplifier_core.testing.__file__)")
echo "  Patching: $TESTING_PY"

# Create backup
cp "$TESTING_PY" "${TESTING_PY}.bak"

# Apply patch using Python (avoids bash escaping issues)
"$TOOL_VENV/bin/python" << 'PATCHSCRIPT'
import sys
import re

# Read the file
with open(sys.argv[1] if len(sys.argv) > 1 else "/dev/stdin") as f:
    content = f.read()

# Find testing.py path from env or use the backed-up path
import os
testing_py = os.environ.get("TESTING_PY_PATH")
if not testing_py:
    import amplifier_core.testing
    testing_py = amplifier_core.testing.__file__

with open(testing_py) as f:
    content = f.read()

# Replace the mount method's await call
original = "await super().mount(mount_point, module, name)"
replacement = "ModuleCoordinator.mount(self, mount_point, module, name=name)"
content = content.replace(original, replacement)

# Replace the unmount method's await call
original2 = "await super().unmount(mount_point, name)"
replacement2 = "ModuleCoordinator.unmount(self, mount_point, name=name)"
content = content.replace(original2, replacement2)

# Write back
with open(testing_py, 'w') as f:
    f.write(content)

print("  ✓ MockCoordinator patched in-place")
PATCHSCRIPT

echo "  ✓ MockCoordinator patched in-place"
