# Build Number System

## Overview

IDT uses a **base version + build number** format: `3.5.0-beta bld004`

- **Base version**: `3.5.0-beta` (from `VERSION` file in project root)
- **Build number**: `bld004` (auto-incremented per build)

## How It Works

### Build Number Sources (Priority Order)

1. **Environment variable `IDT_BUILD_NUMBER`** - Manual override for single build
   ```bash
   set IDT_BUILD_NUMBER=42
   BuildAndRelease\build_idt.bat
   # Result: 3.5.0-beta bld042
   ```

2. **CI: `GITHUB_RUN_NUMBER`** - GitHub Actions automatically sets this

3. **Local tracker: `build/BUILD_TRACKER.json`** - Auto-incremented per base version
   ```json
   {
     "3.5.0-beta": 4,
     "3.4.0": 12
   }
   ```

### Auto-Increment Behavior

Each build:
1. Reads current build number for the base version from tracker
2. Increments by 1
3. Saves back to tracker
4. Uses format `bld{n:03d}` (e.g., bld001, bld012, bld123)

The build script **preserves** `BUILD_TRACKER.json` when cleaning the `build/` directory.

## Common Scenarios

### Starting a New Version

Edit `VERSION` file:
```
3.6.0
```

Next build will be `3.6.0 bld001` (new key in tracker).

The tracker will now contain:
```json
{
  "3.5.0-beta": 4,
  "3.6.0": 1
}
```

### Manually Setting Build Number

Edit `build/BUILD_TRACKER.json`:
```json
{
  "3.5.0-beta": 100
}
```

Next build will be `3.5.0-beta bld101`.

### One-Time Override (Doesn't Update Tracker)

```bash
set IDT_BUILD_NUMBER=500
BuildAndRelease\build_idt.bat
# Builds as bld500 but tracker unchanged
```

Next build without the env var will continue from tracker value.

## Implementation

- **Code**: `scripts/versioning.py`
- **Tracker file**: `build/BUILD_TRACKER.json` (gitignored, local-only)
- **Version file**: `VERSION` (committed to repo)
- **Build script**: `BuildAndRelease/build_idt.bat` (preserves tracker)

## Why Gitignore the Tracker?

`BUILD_TRACKER.json` is **intentionally gitignored** because:
- It tracks **local development builds** (per-machine state)
- CI builds use `GITHUB_RUN_NUMBER` instead
- Prevents merge conflicts between developers
- Each developer's build numbers are independent

## Display

The full version with build number appears in:
- `idt.exe version` output
- Log file banners
- Executable metadata
- Build completion messages

Example output:
```
Image Description Toolkit 3.5.0-beta bld004
Commit: a1b2c3d
Mode: Frozen
```
