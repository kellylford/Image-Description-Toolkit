# Pre-Commit Verification Checklist

**MANDATORY: Complete this checklist BEFORE making ANY code changes.**

## Phase 1: Understanding (BEFORE touching code)

### □ Read the actual code first
- [ ] Used `read_file` to read the relevant sections of code
- [ ] Identified actual class names, method names, variable names
- [ ] Verified these exist by searching, not assuming

### □ Search for existing patterns
- [ ] Used `grep_search` to find similar code patterns
- [ ] Used `list_code_usages` to find all callers of methods I'm modifying
- [ ] Checked for duplicate implementations

### □ Verify assumptions
- [ ] Listed what I'm ASSUMING vs. what I've VERIFIED
- [ ] Searched for edge cases (frozen vs dev mode, different code paths)
- [ ] Checked if this code has different behavior in different contexts

**STOP: If you haven't done the above, DO NOT PROCEED TO PHASE 2.**

## Phase 2: Planning Changes

### □ Impact analysis
- [ ] Identified ALL files that will be affected
- [ ] Found ALL callers of functions being changed
- [ ] Checked if other code depends on current behavior

### □ Compatibility check
- [ ] Verified PyInstaller compatibility (no `from scripts.X` imports)
- [ ] Checked for module-level imports with try/except fallback
- [ ] Verified resource paths use config_loader or resource_manager

### □ Documentation review
- [ ] Checked AI_COMPREHENSIVE_REVIEW_PROTOCOL.md for this type of change
- [ ] Reviewed copilot-instructions.md for project-specific requirements
- [ ] Noted any "NEVER" or "ALWAYS" rules that apply

**STOP: If you can't answer "what could break?" with specifics, DO NOT PROCEED.**

## Phase 3: Implementation

### □ Make minimal changes
- [ ] Changed ONLY what's necessary
- [ ] Did NOT refactor while fixing bugs
- [ ] Did NOT "improve" working code without explicit request

### □ Verify syntax
- [ ] Double-checked method names match actual code
- [ ] Verified variable names exist in scope
- [ ] Checked import statements are correct

### □ Test during development
- [ ] Used Python syntax check: `python -m py_compile <file>`
- [ ] Verified imports work in dev mode
- [ ] Checked error messages make sense

**STOP: If syntax validation fails, FIX IT before claiming done.**

## Phase 4: Build & Test (MANDATORY for executables)

### □ Build the executable
- [ ] Actually ran the build script (not just said "it should build")
- [ ] Build completed without errors
- [ ] Checked build output for warnings

### □ Test in frozen mode
- [ ] Ran the built executable with test data
- [ ] Verified it doesn't crash on startup
- [ ] Tested the specific feature that was changed

### □ Verify the fix
- [ ] The original bug is actually fixed (not just "should be fixed")
- [ ] No new errors introduced
- [ ] Checked log files for runtime errors

**STOP: If you haven't RUN the executable, DO NOT CLAIM IT WORKS.**

## Phase 5: Documentation

### □ Commit message accuracy
- [ ] Commit message describes what actually changed (not what should have changed)
- [ ] Listed actual files modified
- [ ] Noted any breaking changes

### □ Test results
- [ ] Documented: "Built: YES, Tested: YES, Result: [specific outcome]"
- [ ] NOT: "This should work" or "The fix looks correct"
- [ ] Provided actual command run and actual output seen

## Red Flags (If ANY of these are true, STOP)

- [ ] ❌ I'm assuming a method name exists without checking
- [ ] ❌ I'm about to change working production code "just in case"
- [ ] ❌ I haven't searched for other uses of this function
- [ ] ❌ I'm claiming something is "fixed" without testing
- [ ] ❌ I'm using `from scripts.X` imports in production code
- [ ] ❌ I'm modifying a function signature without checking callers
- [ ] ❌ I'm renaming variables without grepping for all uses
- [ ] ❌ The code is 500+ lines and I haven't read it all

## Mandatory Statement Before Committing

**I have completed all checklist items. I have:**
- ✅ Read the actual code (not assumed)
- ✅ Searched for impacts (not guessed)
- ✅ Built the executable (not just edited source)
- ✅ Tested with actual commands (not theoretically)
- ✅ Verified the fix works (not claimed it should)

**Test command run:** `[actual command]`  
**Result:** `[exit code, errors, success message]`  
**Logs checked:** `[paths to log files reviewed]`

---

## Example of CORRECT usage:

**User:** "Fix the progress display bug"

**AI Response:**
```
Before making changes, let me verify the code:
1. Reading viewer_wx.py to find progress-related methods...
   [shows grep_search results]
2. Found methods: get_progress_info(), on_live_update(), load_descriptions()
3. Checking if progress file path is correct...
   [reads actual code]
4. Verified file path: self.current_dir / 'logs' / 'image_describer_progress.txt'

Now implementing fix in get_progress_info() at line 908...
[makes change]

Building to test:
[runs build command]
Build completed: 51 seconds

Testing with command:
dist/Viewer.exe "C:\test\workflow"
Result: Opened successfully, shows "23%, 23 of 100 images"

✅ VERIFIED: Progress displays correctly
```

## Example of INCORRECT usage (NEVER DO THIS):

**User:** "Fix the progress display bug"

**AI Response:**
```
I'll fix the progress display by updating the load_workflow method...
[makes change without reading code]
This should work now. The fix looks correct.
```

❌ **WRONG** - Didn't verify method exists  
❌ **WRONG** - Didn't test the fix  
❌ **WRONG** - Used "should work" language

---

**This checklist is MANDATORY. Claiming something is "done" without completing it violates project protocols.**
