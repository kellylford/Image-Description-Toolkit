# GitHub Actions - Automated Multi-Platform Builds

## Overview
This project uses GitHub Actions to automatically build executables for multiple platforms. Builds run on GitHub's cloud infrastructure at no cost (public repositories get unlimited free minutes).

## Available Build Workflows

### 1. Windows AMD64 Build
**File:** `.github/workflows/build-windows-amd64.yml`

Builds all four Windows applications:
1. **IDT** (Main CLI toolkit) - `idt.exe`
2. **Viewer** - `viewer.exe`
3. **Prompt Editor** - `prompteditor.exe`
4. **ImageDescriber** - `imagedescriber.exe`

**Platform:** Windows Server 2022 (AMD64)  
**Build Time:** 15-30 minutes

### 2. Linux ARM64 Build
**File:** `.github/workflows/build-linux-arm64.yml`

Builds IDT for ARM64 Linux systems (Raspberry Pi, Apple Silicon via Rosetta, ARM servers):
1. **IDT** (Main CLI toolkit) - `idt` (Linux binary)

**Platform:** Linux ARM64 (via QEMU emulation)  
**Build Time:** 20-40 minutes (emulation adds overhead)  
**Note:** GUI apps not built for Linux (PyQt6 complexity)

## How It Works

### Automatic Triggers
The build automatically runs when you:
- Push commits to the `ImageDescriber` branch
- Push commits to the `main` branch

### Manual Trigger
You can also trigger builds manually:
1. Go to: https://github.com/kellylford/Image-Description-Toolkit/actions
2. Click "Build Windows AMD64 Release" in the left sidebar
3. Click the "Run workflow" button
4. Select the branch you want to build
5. Click "Run workflow"

### Build Process
1. **Checkout code** - Gets the specified branch from GitHub
2. **Set up Python 3.11** - Installs Python on Windows Server 2022
3. **Install dependencies** - Runs `pip install -r requirements.txt` and PyInstaller
4. **Build all apps** - Runs `builditall.bat`
5. **Package all apps** - Runs `packageitall.bat`
6. **Upload artifacts** - Makes ZIP files available for download

### Build Time
- Typical build: 15-30 minutes
- Runs on: Windows Server 2022 (AMD64)
- Cost: **$0.00** (unlimited free builds for public repos)

## Downloading Build Artifacts

After a build completes:

1. **Go to Actions tab**: https://github.com/kellylford/Image-Description-Toolkit/actions
2. **Click on a completed workflow run** (green checkmark)
3. **Scroll to the "Artifacts" section** at the bottom
4. **Download the ZIP files**:

### Windows AMD64 Artifacts:
   - `idt-windows-amd64` - Main toolkit (Windows .exe)
   - `viewer-windows-amd64` - Viewer application
   - `prompteditor-windows-amd64` - Prompt editor
   - `imagedescriber-windows-amd64` - ImageDescriber GUI

### Linux ARM64 Artifacts:
   - `idt-linux-arm64` - Main toolkit (Linux ARM64 binary)

### Artifact Retention
- Artifacts are kept for **90 days** by default
- Download them before they expire
- You can re-run old builds to regenerate artifacts

## Viewing Build Logs

To see what happened during a build:
1. Click on the workflow run
2. Click on "build-windows" job
3. Expand any step to see detailed logs
4. Useful for debugging build failures

## Troubleshooting

### Build Failed
If a build fails:
1. Click on the failed workflow run
2. Look for red X marks on steps
3. Expand failed steps to see error messages
4. Common issues:
   - Missing dependencies in `requirements.txt`
   - Syntax errors in build scripts
   - Missing files or incorrect paths

### Missing Artifacts
If artifacts aren't uploaded:
1. Check the "List release files" step
2. Verify that ZIP files were created
3. Check artifact path patterns match actual file locations

### Build Takes Too Long
- Normal: 15-30 minutes
- Slow: 30-45 minutes (high GitHub load)
- If >45 minutes, check logs for hanging processes

## Manual Alternative

If GitHub Actions isn't working, you can still build locally:
```bash
# On Windows machine:
cd C:\Users\kelly\GitHub\Image-Description-Toolkit
releaseitall.bat
```

## Cost Information

### Public Repository (Current)
- ✅ **Unlimited free minutes**
- ✅ No credit card required
- ✅ Windows, Linux, and macOS runners all free

### If Repository Becomes Private
- 2,000 free minutes/month
- Windows runners: 2x multiplier (30 min build = 60 minutes)
- Additional minutes: $0.008 per minute
- Estimated cost: ~$1-2 per build after free tier

## Workflow Configuration

The workflow can be customized by editing `.github/workflows/build-windows-amd64.yml`:

### Trigger on Different Branches
```yaml
on:
  push:
    branches:
      - main
      - develop
      - release/*
```

### Change Runner (Different Windows Version)
```yaml
runs-on: windows-2019  # Or windows-latest (currently 2022)
```

### Add Email Notifications
```yaml
- name: Send notification
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    # ... configure email
```

### Cache Dependencies (Faster Builds)
```yaml
- name: Cache pip packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

## Best Practices

1. **Test locally first** - Make sure `releaseitall.bat` works on your machine
2. **Check artifact sizes** - Large artifacts consume storage quota
3. **Clean up old artifacts** - Delete unneeded artifacts from old runs
4. **Use manual triggers** - For testing, use manual dispatch instead of pushing
5. **Monitor build times** - If builds get slower, investigate dependencies

## Related Documentation
- GitHub Actions: https://docs.github.com/en/actions
- Windows runners: https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners
- Artifact upload: https://github.com/actions/upload-artifact

## Local Build Scripts
For comparison, local build process:
- `builditall.bat` - Build all executables
- `packageitall.bat` - Package into ZIP files
- `releaseitall.bat` - Complete build + package workflow
- `tools/kelly_release_and_install.bat` - Personal workflow (git-ignored)
