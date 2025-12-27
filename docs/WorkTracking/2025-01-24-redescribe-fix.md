# 2025-01-24 Redescribe Working Directory Fix

## Problem
When using viewer.exe's Redescribe feature, new workflows were being created inside the source workflow's `descriptions/` subfolder instead of at the same level as the source workflow.

Example:
- Source: `c:\idt\Descriptions\wf_december_claude_...`
- Expected: `c:\idt\Descriptions\wf_december_ollama_gemma3_...`
- Actual: `c:\idt\Descriptions\wf_december_claude_.../descriptions/wf_december_ollama_gemma3_...`

## Root Cause
1. `idt_cli.py` line 124-126 automatically adds `--output-dir Descriptions` for all workflow commands that don't specify `--output-dir`, unless in `--resume` mode
2. The `--redescribe` mode was NOT excluded from this default
3. `Descriptions` is a relative path resolved relative to the current working directory
4. viewer.exe sets `cwd` to the source workflow's parent, but that doesn't override an explicit `--output-dir` argument
5. Since viewer runs from `c:\idt\Descriptions\wf_december_claude_...` and `idt_cli.py` adds `--output-dir Descriptions`, the path resolves to `c:\idt\Descriptions\wf_december_claude_.../Descriptions`

## Solution
Modified `idt_cli.py` line 124 to exclude `--redescribe` from the default `--output-dir` injection:

```python
# Before
if '--output-dir' not in args and '-o' not in args and '--resume' not in args:

# After  
if '--output-dir' not in args and '-o' not in args and '--resume' not in args and '--redescribe' not in args:
```

This allows `workflow.py`'s redescribe logic (lines 3177-3182) to work correctly:
```python
if args.output_dir:
    output_base = Path(args.output_dir)
else:
    # Use same parent directory as source workflow
    output_base = source_dir.parent
```

## Files Changed
- [`idt_cli.py`](idt_cli.py#L124) - Added `and '--redescribe' not in args` to conditional

## Build & Deploy
- Rebuilt `idt.exe` with `BuildAndRelease/build_idt.bat`
- Deployed to `c:\idt\idt.exe`
- Size: 76 MB

## Testing
Ready for user testing with viewer.exe Redescribe button.

## Related Issues
- Resume workflow provider detection fix (previous session)
- Viewer GUI implementation for Resume/Redescribe operations
