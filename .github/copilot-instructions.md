# Copilot Instructions for next-gen-amp-github-copilot-provider

## Git Push Machine Tracking

When pushing to private branches or main, include the **origin machine** in commit messages:

| Machine | Tag | Notes |
|---------|-----|-------|
| Laptop | `(from: laptop)` | Windows laptop dev environment |
| Desktop | `(from: desktop)` | Main development workstation |
| WSL | `(from: wsl)` | WSL2 environment |

### Example Commit Format
```
docs: add forensic analysis tools (from: laptop)
feat: implement F-045 tool suppression (from: desktop)
```

### Push Authorization

When the user authorizes a push to private branch:
1. Note the origin machine in commit message if not already present
2. Use appropriate git credentials for the target remote

## Repository Context

- **Remote**: https://github.com/mowree/next-gen-amp-gitHub-copilot-provider
- **Push account**: `mowree` (not `mowrim_microsoft`)
- **Current machine**: laptop
