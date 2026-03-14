#!/usr/bin/env python3
"""Apply in-place patch to MockCoordinator.mount() in amplifier-core.

Bug: MockCoordinator.mount() does `await super().mount()` on a synchronous Rust method.
Fix: Replace with direct ModuleCoordinator.mount() call.

This script is called from docker-shadow-test.sh and modifies testing.py IN-PLACE
so the fix persists when `amplifier run` starts as a separate Python process.
"""

import os
import shutil

import amplifier_core.testing

testing_py = amplifier_core.testing.__file__
print(f"  Patching: {testing_py}")

# Clear __pycache__ to force recompile
pycache_dir = os.path.join(os.path.dirname(testing_py), "__pycache__")
if os.path.exists(pycache_dir):
    shutil.rmtree(pycache_dir)
    print("  Cleared __pycache__")

with open(testing_py) as f:
    content = f.read()

# Show BEFORE state
print("  BEFORE patch - relevant lines:")
for i, line in enumerate(content.split("\n")):
    if "super().mount" in line or "super().unmount" in line:
        print(f"    Line {i + 1}: {line.strip()}")

# Replace the mount method's await call
# The issue is super().mount() on a subclass - use explicit class call with await
original = "await super().mount(mount_point, module, name)"
replacement = "await ModuleCoordinator.mount(self, mount_point, module, name=name)"
content = content.replace(original, replacement)

# Replace the unmount method's await call
original2 = "await super().unmount(mount_point, name)"
replacement2 = "await ModuleCoordinator.unmount(self, mount_point, name=name)"
content = content.replace(original2, replacement2)

# Write back
with open(testing_py, "w") as f:
    f.write(content)

# Verify the patch was applied by re-reading
with open(testing_py) as f:
    patched_content = f.read()

print("  AFTER patch - relevant lines:")
for i, line in enumerate(patched_content.split("\n")):
    if "ModuleCoordinator.mount" in line or "ModuleCoordinator.unmount" in line:
        print(f"    Line {i + 1}: {line.strip()}")

if "await ModuleCoordinator.mount" in patched_content:
    print("  ✓ MockCoordinator patched in-place")
else:
    print("  ⚠ Patch NOT applied - original strings not found")
