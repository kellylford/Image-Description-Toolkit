# Critical Bug Fix: config_workflow vs config_image_describer

## Issue
The frozen executable `idt.exe` was passing `args.config_image_describer` (which is None by default) to functions that expect `args.config_workflow`, causing:

```
WARNING - Could not load workflow config: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'NoneType'
```

## Root Cause
Lines 2665-2666 in `scripts/workflow.py` were calling:
```python
model_name = get_effective_model(args, args.config_image_describer)
prompt_style = get_effective_prompt_style(args, args.config_image_describer)
```

But those functions expect the WORKFLOW config file, not the image describer config file.

## Status
**ALREADY FIXED IN SOURCE CODE** (lines 2665-2666 now correctly use `args.config_workflow`)

The problem is you're running an OLD frozen executable that was built before this fix.

## Solution
**Rebuild the executable:**

```bash
cd BuildAndRelease
builditall.bat
```

Or just rebuild IDT:
```bash
cd BuildAndRelease
build_idt.bat
```

Then reinstall or copy the new `dist\idt.exe` to `C:\idt\`

## Verification
After rebuild, run:
```bash
C:\idt\idt.exe workflow \\qnap\home\idt\images\test
```

The warnings should be gone.
