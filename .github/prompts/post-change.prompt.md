---
description: "IDT post-change verification — run after any code edit, before declaring done. Runs py_compile, verifies callers, tests in dev mode, checks build/exe if core files changed, reviews logs."
name: "IDT Post-Change Verification"
argument-hint: "List the files that were modified (e.g. 'imagedescriber_wx.py, ai_providers.py')"
agent: "agent"
tools: [read, search, execute]
---

You are performing the **IDT Post-Change Verification** protocol. Your job is to prove the changes work — not assume they do.

## Input

Files that were modified: `$input`

---

## Steps

### Step 1 — Syntax validation (ALL modified files)

For each modified file, run:
```bash
python -m py_compile <filepath>
```

If any file fails: **STOP. Report the error. Do not continue until syntax is clean.**

### Step 2 — Caller verification

From the pre-change checkpoint (or by searching now), re-check every call site:
- Search for the old function/variable name — does it still exist where it's called?
- Search for the new function/variable name — is it used consistently everywhere?
- Specifically check: return statements, lambda sort keys, default arguments, string formatting

```bash
grep -r "old_name_if_renamed" scripts/ imagedescriber/ analysis/ shared/
grep -r "new_name" scripts/ imagedescriber/ analysis/ shared/
```

### Step 3 — Dev mode test

**For changes to `imagedescriber/imagedescriber_wx.py` or any wx file:**
```bash
cd imagedescriber && .winenv/Scripts/python imagedescriber_wx.py
```
- Reproduce the EXACT scenario that was changed
- Watch stderr for exceptions — wx swallows all exceptions in event handlers; they only appear in stderr when running in dev mode
- Test: open dialog, click button, trigger the changed code path

**For changes to `scripts/workflow.py` or CLI scripts:**
```bash
python scripts/workflow.py [relevant sub-command] testimages/
```

**For changes to `idt/idt_cli.py`:**
```bash
cd idt && python idt_cli.py [sub-command] --help
```

### Step 4 — Build test (REQUIRED for these files)

Run a build if you modified any of:
- `imagedescriber/imagedescriber_wx.py`
- `scripts/workflow.py`
- `scripts/image_describer.py`
- `idt/idt_cli.py`
- Any file listed in `hiddenimports` in a `.spec` file

```batch
# Windows — build imagedescriber:
cd imagedescriber && build_imagedescriber_wx.bat

# Windows — build idt CLI:
cd idt && build_idt.bat

# Windows — build everything:
BuildAndRelease\WinBuilds\builditall_wx.bat
```

After building, run smoke tests:
```batch
dist\idt.exe version
dist\idt.exe --debug-paths
```

### Step 5 — Log review

After any workflow or executable run:
```bash
# Check for errors in workflow logs:
grep -i "error\|exception\|traceback" wf_*/logs/*.log 2>/dev/null | head -50

# Check for import failures specifically:
grep -i "importerror\|modulenotfounderror\|nameerror" wf_*/logs/*.log 2>/dev/null
```

### Step 6 — Write verification summary

Output the following block, filled in with ACTUAL results (not expected):

```
=== IDT POST-CHANGE VERIFICATION ===

Files verified: [list]
Date: [today]

SYNTAX CHECK:
  - [file1]: PASS / FAIL (error: ...)
  - [file2]: PASS / FAIL

CALLER VERIFICATION:
  - All pre-change call sites still valid: YES / NO
  - Any missed references found: NONE / [list]

DEV MODE TEST:
  - Command run: [exact command]
  - Result: PASS / FAIL
  - Stderr output: CLEAN / [paste relevant exceptions]
  - Specific scenario tested: [describe]

BUILD TEST:
  - Required: YES / NO (reason if no: ...)
  - Build completed: YES / NO / NOT RUN
  - Build command: [exact command]
  - Smoke test result: PASS / FAIL / NOT RUN
  - Exe tested: [command run]

LOG REVIEW:
  - Log file checked: [path or N/A]
  - Errors found: NONE / [list errors]

OVERALL: VERIFIED ✓ / NEEDS MORE WORK ✗
  [If NEEDS MORE WORK, list what remains]
=====================================
```

**Rules:**
- If OVERALL is NEEDS MORE WORK, you may NOT declare the task complete
- If build was required but skipped, state explicitly: "Build not run — user must verify exe behavior manually"
- "Should work" and "looks correct" are not acceptable entries in any field — only actual test results

If OVERALL is VERIFIED:
1. Write the verified flag so the hook guard knows post-change was completed:
```bash
# Windows:
mkdir .idt_session 2>nul & echo verified > .idt_session\verified
# macOS/Linux:
mkdir -p .idt_session && echo "verified" > .idt_session/verified
```
2. You may now declare the task complete.
