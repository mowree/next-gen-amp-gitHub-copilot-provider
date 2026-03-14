# Local Provider Test Setup Guide

> **Evidence-based documentation from forensic testing session (March 13, 2026)**

This document explains how to test the local development version of `provider-github-copilot` with Amplifier CLI, bypassing the public cached version.

---

## Prerequisites: Install Optional Amplifier Tools

Before testing, install missing optional dependencies in Amplifier's environment to avoid tool loading errors:

```powershell
# Install mcp and aiohttp (required by tool-mcp and tool-web)
uv pip install --python "$env:USERPROFILE\AppData\Roaming\uv\tools\amplifier\Scripts\python.exe" mcp aiohttp

# Install tool-apply-patch from cached bundle
uv pip install --python "$env:USERPROFILE\AppData\Roaming\uv\tools\amplifier\Scripts\python.exe" "$env:USERPROFILE\.amplifier\cache\amplifier-bundle-filesystem-800514b6bec1fdef\modules\tool-apply-patch"
```

**Verify installation:**
```powershell
uv pip list --python "$env:USERPROFILE\AppData\Roaming\uv\tools\amplifier\Scripts\python.exe" | Select-String "mcp|aiohttp|apply-patch"
```

**Expected output:**
```
aiohttp                              3.13.3
amplifier-module-tool-apply-patch    1.0.0
mcp                                  1.26.0
```

> **Note:** These are Amplifier's optional tool dependencies, not our provider's. Without them, you'll see warnings like `Failed to load module 'tool-mcp'` during tests. They don't affect provider functionality but create noise in output.

---

## The Problem

Amplifier caches provider modules from git repositories in `~/.amplifier/cache/`. When you install your local provider via `uv pip install -e .`, Amplifier's loader still prefers the cached git version because:

1. The loader's `_find_package_dir()` doesn't search `src/` layouts
2. Git-cached modules take precedence over entry-point installed packages
3. The cached version has different code (e.g., `_constants.py` that our version doesn't have)

**Evidence:**
```
Failed to load module 'provider-github-copilot': Module 'provider-github-copilot' 
failed validation: FAILED: 0/1 checks passed (1 errors, 0 warnings). 
Errors: module_importable: Failed to import module: 
No module named 'amplifier_module_provider_github_copilot._constants'
```

The cached version imports `_constants.py`, but Python resolves to our installed package which doesn't have that file → import fails.

---

## Solution: Replace the Cache

The workaround is to replace the cached module's Python package directory with our local source.

### Step 1: Locate the Cache Directory

```powershell
# Find the cached provider
Get-ChildItem "C:\Users\$env:USERNAME\.amplifier\cache" -Directory | Where-Object { $_.Name -like "*copilot*" }
```

**Expected output:**
```
amplifier-module-provider-github-copilot-ed66ecbd21ea6054
```

The hash suffix (`ed66ecbd21ea6054`) may vary.

### Step 2: Verify Cache Structure

```powershell
Get-ChildItem "C:\Users\$env:USERNAME\.amplifier\cache\amplifier-module-provider-github-copilot-ed66ecbd21ea6054"
```

**Expected structure:**
```
amplifier_module_provider_github_copilot/   ← Python package directory
pyproject.toml
README.md
...
```

### Step 3: Replace Cache with Local Source

```powershell
$src = "D:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot"
$dst = "C:\Users\$env:USERNAME\.amplifier\cache\amplifier-module-provider-github-copilot-ed66ecbd21ea6054\amplifier_module_provider_github_copilot"

# Remove cached package directory
cmd /c "rd /s /q ""$dst"""

# Copy local source
Copy-Item -Path $src -Destination $dst -Recurse -Force

Write-Host "Cache updated with local provider"
```

### Step 4: Verify Replacement

```powershell
# Check a file that's unique to your version
Get-Content "$dst\provider.py" | Select-String "send_and_wait"
```

If you see `send_and_wait` (F-040 fix), you're using the local version. The public version uses `send_message`.

---

## Verification: Confirm Local Provider is in Use

### Method 1: Check for F-040 Fix

The local version uses `send_and_wait()`, not `send_message()`:

```powershell
Select-String -Path "$dst\provider.py" -Pattern "send_and_wait|send_message"
```

**Expected (local version):**
```
sdk_response = await sdk_session.send_and_wait({"prompt": internal_request.prompt})
```

**Would indicate public version:**
```
async for sdk_event in sdk_session.send_message(...)
```

### Method 2: Check Module Import Path

```powershell
& "C:\Users\$env:USERNAME\AppData\Roaming\uv\tools\amplifier\Scripts\python.exe" -c "
import amplifier_module_provider_github_copilot
print(amplifier_module_provider_github_copilot.__file__)
"
```

**Note:** This shows where Python resolves the module. However, Amplifier's loader uses its own resolution path via the cache, so this may differ from what Amplifier actually loads.

### Method 3: Run a Test and Check for Errors

```powershell
amplifier run -v "Say hello" 2>&1 | Select-String "send_message|AttributeError"
```

- **No errors** = Local version (uses `send_and_wait`)
- **AttributeError: 'CopilotSession' object has no attribute 'send_message'** = Public version

### Method 4: Check Response Content

Run a simple test:

```powershell
amplifier run "What is 2+2? Just the number." 2>&1 | Select-String "content="
```

**Expected output:**
```
content='\n\n4'
```

If you get an actual response (not an error), the provider is working.

---

## Post-Test Verification

After running tests, verify the local provider is still in place:

### Check 1: Cache Directory Still Has Local Code

```powershell
$dst = "C:\Users\$env:USERNAME\.amplifier\cache\amplifier-module-provider-github-copilot-ed66ecbd21ea6054\amplifier_module_provider_github_copilot"

# Look for F-040 fix (send_and_wait)
Select-String -Path "$dst\provider.py" -Pattern "send_and_wait"
```

### Check 2: No `_constants.py` (Local Version Indicator)

```powershell
Test-Path "$dst\_constants.py"
```

- **False** = Local version (we don't have `_constants.py`)
- **True** = Public version was restored

### Check 3: Compare File Timestamps

```powershell
Get-Item "$dst\provider.py" | Select-Object LastWriteTime
```

Should match when you did the cache replacement.

---

## Troubleshooting

### Cache Gets Restored Automatically

Amplifier may restore the git-cached version. If this happens:

```powershell
# Re-run the replacement
$src = "D:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot"
$dst = "C:\Users\$env:USERNAME\.amplifier\cache\amplifier-module-provider-github-copilot-ed66ecbd21ea6054\amplifier_module_provider_github_copilot"
cmd /c "rd /s /q ""$dst"""
Copy-Item -Path $src -Destination $dst -Recurse -Force
```

### Import Errors About `_constants`

This means the public cached version is being loaded:

```
No module named 'amplifier_module_provider_github_copilot._constants'
```

**Fix:** Re-run the cache replacement.

### `send_message` AttributeError

```
AttributeError: 'CopilotSession' object has no attribute 'send_message'
```

This means the public version's code is running. The SDK has `send_and_wait()`, not `send_message()`.

**Fix:** Re-run the cache replacement to inject the F-040 fix.

---

## Evidence from Successful Test Session

### Test 1: Hello
```yaml
Session ID: 1c500199-2866-4d4d-bee9-267f58df4af5
output_tokens: 48.0
content: '\n\nHello! This repo uses an autonomous development machine...'
```

### Test 2: Math
```yaml
Session ID: 718b3204-9c74-491f-a27d-f91d9ddac94e
content: '\n\n4'
```

### Test 3: Python Functions
```yaml
Session ID: 08126624-276e-4c8e-8133-e243a7afe1f7
output_tokens: 15.0
content: '\n\nlen\nprint\nrange'
```

All tests returned actual LLM content, confirming:
- F-039: `CopilotClientWrapper` properly wired
- F-040: `send_and_wait()` API works correctly

---

## Quick Start Script

Save this as `setup-local-provider.ps1`:

```powershell
#!/usr/bin/env pwsh
# Setup local provider for Amplifier testing

$ErrorActionPreference = "Stop"

$amplifierPython = "$env:USERPROFILE\AppData\Roaming\uv\tools\amplifier\Scripts\python.exe"
$localSrc = "D:\next-get-provider-github-copilot\src\amplifier_module_provider_github_copilot"
$cacheBase = "$env:USERPROFILE\.amplifier\cache"

# Step 1: Install optional Amplifier dependencies (run once)
Write-Host "Installing optional Amplifier tools..." -ForegroundColor Cyan
$checkMcp = uv pip list --python $amplifierPython 2>$null | Select-String "mcp"
if (-not $checkMcp) {
    uv pip install --python $amplifierPython mcp aiohttp 2>$null
    Write-Host "  ✓ mcp and aiohttp installed" -ForegroundColor Green
}

$checkPatch = uv pip list --python $amplifierPython 2>$null | Select-String "apply-patch"
if (-not $checkPatch) {
    $patchPath = Get-ChildItem $cacheBase -Directory | Where-Object { $_.Name -like "*filesystem*" } | Select-Object -First 1
    if ($patchPath) {
        $patchModule = Join-Path $patchPath.FullName "modules\tool-apply-patch"
        if (Test-Path $patchModule) {
            uv pip install --python $amplifierPython $patchModule 2>$null
            Write-Host "  ✓ tool-apply-patch installed" -ForegroundColor Green
        }
    }
}

# Step 2: Find the cached provider directory
$cacheDir = Get-ChildItem $cacheBase -Directory | Where-Object { $_.Name -like "*provider-github-copilot*" } | Select-Object -First 1

if (-not $cacheDir) {
    Write-Error "No cached provider found. Run 'amplifier run' once to populate cache."
    exit 1
}

$dst = Join-Path $cacheDir.FullName "amplifier_module_provider_github_copilot"

Write-Host "Replacing: $dst" -ForegroundColor Yellow
Write-Host "With: $localSrc" -ForegroundColor Yellow

# Step 3: Remove and replace
cmd /c "rd /s /q ""$dst"""
Copy-Item -Path $localSrc -Destination $dst -Recurse -Force

# Step 4: Verify
$check = Select-String -Path "$dst\provider.py" -Pattern "send_and_wait" -Quiet
if ($check) {
    Write-Host "✓ Local provider installed (F-040 fix detected)" -ForegroundColor Green
} else {
    Write-Host "✗ Warning: F-040 fix not found" -ForegroundColor Yellow
}

Write-Host "`nReady to test! Run: amplifier run 'Say hello'" -ForegroundColor Cyan
```

---

## Summary

| Step | Command | Purpose |
|------|---------|---------|
| 0. Install tools | `uv pip install mcp aiohttp` | Eliminate tool loading warnings |
| 1. Find cache | `Get-ChildItem ~/.amplifier/cache *copilot*` | Locate cached provider |
| 2. Replace | `Copy-Item -Recurse` | Inject local code |
| 3. Verify | `Select-String "send_and_wait"` | Confirm F-040 fix present |
| 4. Test | `amplifier run "test prompt"` | Validate end-to-end |
| 5. Post-check | `Test-Path _constants.py` | Confirm local still active |

---

## Expected Clean Output

After installing optional tools and local provider, test output should be clean:

```powershell
amplifier run "Say OK" 2>&1 | Select-String "Failed to load|content="
```

**Expected (clean):**
```
content='\n\nOK'
```

**Not expected (has warnings):**
```
Failed to load module 'tool-mcp': ...
Failed to load module 'tool-web': ...
content='\n\nOK'
```

If you still see `Failed to load` warnings, re-run the prerequisite installation steps.

---

## WSL (Linux) Setup

WSL has a completely separate Amplifier environment from Windows. The Windows setup does NOT apply.

### Key Difference

WSL doesn't have the github-copilot provider cached by default. You must:
1. Create a local cache manually
2. Fix `~/.amplifier/settings.yaml` if it references Windows paths

### WSL Setup Steps

```bash
# 1. Create provider cache directory
mkdir -p ~/.amplifier/cache/amplifier-module-provider-github-copilot-local

# 2. Copy local source (from Windows mount)
cp -r /mnt/d/next-get-provider-github-copilot/amplifier_module_provider_github_copilot ~/.amplifier/cache/amplifier-module-provider-github-copilot-local/
cp /mnt/d/next-get-provider-github-copilot/pyproject.toml ~/.amplifier/cache/amplifier-module-provider-github-copilot-local/
cp /mnt/d/next-get-provider-github-copilot/README.md ~/.amplifier/cache/amplifier-module-provider-github-copilot-local/

# 3. Install SDK (if not already installed)
~/.local/bin/uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python "github-copilot-sdk>=0.1.32,<0.2.0"

# 4. Install provider module
~/.local/bin/uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python ~/.amplifier/cache/amplifier-module-provider-github-copilot-local --force-reinstall

# 5. Fix settings.yaml (CRITICAL)
# Check for bad Windows path reference:
grep '/mnt/d/next-get-provider-github-copilot/src' ~/.amplifier/settings.yaml

# If found, fix it:
sed -i 's|source: file:///mnt/d/next-get-provider-github-copilot/src|source: file:///home/$USER/.amplifier/cache/amplifier-module-provider-github-copilot-local|' ~/.amplifier/settings.yaml

# 6. Clear install state and test
rm -f ~/.amplifier/cache/install-state.json
amplifier run --bundle foundation "What is 2+2?"
```

### WSL Troubleshooting

**Error: `Path does not contain a valid Python module: /mnt/d/.../src`**

This means `~/.amplifier/settings.yaml` has a bad path. Fix:
```bash
# Check the bad path
grep -r '/mnt/d/next-get-provider-github-copilot/src' ~/.amplifier/

# Fix settings.yaml
sed -i 's|source: file:///mnt/d/next-get-provider-github-copilot/src|source: file:///home/'"$USER"'/.amplifier/cache/amplifier-module-provider-github-copilot-local|' ~/.amplifier/settings.yaml
```

**Error: `uv: command not found`**

Use full path:
```bash
~/.local/bin/uv pip install ...
```

Or add to PATH:
```bash
export PATH=~/.local/bin:$PATH
```

### WSL Quick One-Liner

Paste this entire block to set up WSL:
```bash
mkdir -p ~/.amplifier/cache/amplifier-module-provider-github-copilot-local && \
cp -r /mnt/d/next-get-provider-github-copilot/amplifier_module_provider_github_copilot ~/.amplifier/cache/amplifier-module-provider-github-copilot-local/ && \
cp /mnt/d/next-get-provider-github-copilot/pyproject.toml ~/.amplifier/cache/amplifier-module-provider-github-copilot-local/ && \
cp /mnt/d/next-get-provider-github-copilot/README.md ~/.amplifier/cache/amplifier-module-provider-github-copilot-local/ && \
~/.local/bin/uv pip install --python ~/.local/share/uv/tools/amplifier/bin/python ~/.amplifier/cache/amplifier-module-provider-github-copilot-local --force-reinstall && \
sed -i 's|source: file:///mnt/d/next-get-provider-github-copilot/src|source: file:///home/'"$USER"'/.amplifier/cache/amplifier-module-provider-github-copilot-local|' ~/.amplifier/settings.yaml 2>/dev/null; \
rm -f ~/.amplifier/cache/install-state.json && \
amplifier run --bundle foundation "What is 2+2?"
```

### WSL Evidence

Successful WSL test after fix:
```
Bundle 'foundation' prepared successfully
Session ID: 050c8947-ec14-4203-bc6a-c3c5b3d9be49
Bundle: foundation | Provider: GitHub Copilot SDK | claude-opus-4.5
4
```

---

## Human to test
amplifier run "What is the capital of France?"
amplifier run "What is the capital of France?" 2>&1 | grep "content="
amplifier run "What is the capital of France?" 2>&1 | grep -oP "content='[^']*'"
amplifier routing list and then after they perform what I said
amplifier run --mode chat

"export PATH=~/.local/bin:\$PATH && cd /mnt/d/next-get-provider-github-copilot && amplifier run --mode chat" 
