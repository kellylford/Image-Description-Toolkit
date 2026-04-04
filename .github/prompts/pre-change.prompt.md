---
description: "IDT pre-change verification — run before any code edit. Reads actual code, finds all callers, checks PyInstaller and wx compatibility, and produces a written checkpoint before touching files."
name: "IDT Pre-Change Verification"
argument-hint: "Describe the change you're about to make (e.g. 'rename get_date() in workflow.py')"
agent: "agent"
tools: [read, search, execute]
---

You are performing the **IDT Pre-Change Verification** protocol. Your job is to gather complete information before any code changes are made. You do NOT make any edits.

## Input

The user has described a change they intend to make: `$input`

---

## Steps

### Step 1 — Read every file that will be touched

For each file identified in the change description:
- Read it fully with `read_file` — do not skim
- Identify the exact current code: class names, method names, variable names, signatures
- Note the file's total line count; flag files >500 lines as HIGH RISK

### Step 2 — Find every caller

For each function, method, or variable being changed:
```
grep_search: "function_name"  (broad, all files)
grep_search: "variable_name"  (broad, all files)
```
Also check:
- Return statements that reference the variable
- Lambda functions with the variable in sort keys
- String formatting that includes the name
- Default argument values

List every call site found.

### Step 3 — Check PyInstaller compatibility

Scan the files being changed for any of these patterns:
```
grep_search: "from scripts\."
grep_search: "from imagedescriber\."
grep_search: "from analysis\."
grep_search: "from viewer\."
```

If found: **BLOCKED** — these imports fail in the frozen executable. Flag for fix.

### Step 4 — Check wx safety (if wx GUI files are involved)

If modifying `imagedescriber_wx.py` or any wx file:
```
grep_search: "logger = logging.getLogger" in imagedescriber_wx.py
```
- Verify `logger` is defined at MODULE SCOPE (not inside a function or class)
- If it's inside `main()` or any function: **BLOCKED** — all event handlers will silently fail

### Step 5 — Check frozen vs dev code paths

Scan for:
```
grep_search: "getattr(sys, 'frozen'"
grep_search: "_MEIPASS"
```
If found near code being changed: document both paths and verify both will still work after the change.

### Step 6 — Duplicate implementation check

```
grep_search: [core concept from the change]
```
Look for similar logic elsewhere that would need the same change. Common locations:
- `scripts/` — CLI implementations
- `imagedescriber/` — GUI implementations  
- `analysis/` — analysis tools
- `shared/` — shared utilities

### Step 7 — Write checkpoint summary

Output the following block, filled in completely:

```
=== IDT PRE-CHANGE CHECKPOINT ===

Change description: [what the user described]
Date: [today]

FILES TO BE MODIFIED:
  - [file1] (line count: X) [RISK: normal/HIGH]
  - [file2] ...

EXACT ITEMS CHANGING:
  - [class/function/variable] in [file]: [current value] → [new value]

ALL CALLERS FOUND:
  - [file:line] — [brief description of the call site]
  - (or: NONE — this is a new function/class)

PYINSTALLER COMPATIBILITY: SAFE / BLOCKED (reason: ...)
WX SAFETY CHECK: SAFE / BLOCKED (reason: ...)
FROZEN/DEV PATH IMPACT: NONE / YES (path: ...)
DUPLICATE IMPLEMENTATIONS: NONE / FOUND (locations: ...)

RISKS:
  1. [risk description]
  2. ...

VERDICT: READY TO PROCEED / BLOCKED
  [If BLOCKED, list what must be resolved first]
=================================
```

If VERDICT is BLOCKED, stop here and do not make any edits until the blocks are resolved.

If VERDICT is READY TO PROCEED:
1. Write the session state flag so the hook guard knows pre-change was completed:
```bash
python tools/idt_hook_guard.py --mark-precheck
```
Or create the flag directly:
```bash
# Windows:
mkdir .idt_session 2>nul & echo precheck_done > .idt_session\precheck_done
# macOS/Linux:
mkdir -p .idt_session && echo "precheck_done" > .idt_session/precheck_done
```
2. The user or coding agent may now proceed with the change.
