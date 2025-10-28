# Testing Checklist — Oct 28, 2025

This is a living checklist for validation of the recent fixes (format-string errors, Windows date formatting, Ollama fallbacks) and the build pipeline health.

## Core Regressions to Guard Against
- [ ] No "Invalid format string" when writing descriptions
- [ ] Windows date formatting shows no leading zeros in day; correct AM/PM suffix
- [ ] GPS/Altitude/camera/lens lines render without formatting collisions
- [ ] Ollama provider works even if Python client not installed (HTTP fallbacks)
- [ ] GUI and CLI builds complete successfully (PyInstaller present in venvs)

## Quick Sanity (Local)
1) Model availability
   - [ ] `GET http://127.0.0.1:11434/api/tags` returns JSON with expected models (e.g., `moondream:latest`)

2) Script-based describe proof
   - [ ] Run `scripts/image_describer.py` against a small set (converted_images) with:
         provider=ollama, model=moondream:latest, prompt-style=narrative, max-files=5
   - [ ] Verify `image_descriptions.txt` exists and includes:
       - [ ] `Photo Date: M/D/YYYY H:MMA/P`
       - [ ] `GPS: <lat>, <lon>` and `Altitude: Xm`
       - [ ] `Camera: <make> <model>` and optional `Lens: <name>`
       - [ ] No "Invalid format string" in logs

3) HTTP chat fallback (optional)
   - [ ] Temporarily simulate missing Python client (or run in environment without it)
   - [ ] Verify describe still succeeds via HTTP `/api/chat`

## Build Pipeline
1) ImageDescriber (GUI)
   - [ ] Ensure venv exists with python.exe
   - [ ] `pyinstaller` installed in venv
   - [ ] Build completes and outputs `imagedescriber.exe` in `dist/`

2) IDT CLI (idt.exe)
   - [ ] Build idt.exe with latest code
   - [ ] Copy to `C:\idt\idt.exe`
   - [ ] `--version` or `--help` runs without errors

## End-to-End Workflow (UNC Source)
- [ ] If HEIC not discoverable, run ConvertImage step first to JPEGs
- [ ] Run `workflow` with steps `describe,html` on `\\ford\home\photos\mobilebackup\iphone\2023\01`
- [ ] Output in `C:\idt\Descriptions\wf_TheTest_fixed_*` contains:
  - [ ] `image_descriptions.txt` with metadata lines (no format errors)
  - [ ] `logs/image_describer_*.log` without format exceptions
  - [ ] HTML generated with expected entries

## Post-Run Hygiene
- [ ] Ensure `c:\idt\scripts` mirrors repo fixes (no drift)
- [ ] Remove or align duplicate code paths
- [ ] Update this checklist with actual results (dates, run IDs)

## Notes
- The root cause was f-strings within `format_metadata()` in `scripts/image_describer.py`. We replaced all with safe concatenation and explicit numeric formatting.
- Date formatting is standardized (Windows-safe) across helpers to avoid platform issues.
