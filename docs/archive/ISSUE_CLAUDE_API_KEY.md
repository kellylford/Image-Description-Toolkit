# Issue: Claude API Key Configuration Fails in Guideme

## Status
🔴 **OPEN** - Investigation in progress, debug logging added

## Priority
**HIGH** - Affects user experience with guideme wizard for Claude provider

## Description
When using the `guideme` interactive wizard to configure Claude API key, the configuration fails with error:
```
"Claude API key not configured or SDK not installed"
```

However, manually running the `bat/setup_claude_key.bat` file works correctly.

## Environment
- **Version**: Built executable (`idt.exe`)
- **Platform**: Windows
- **Provider**: Claude (Anthropic)
- **Affected Component**: Guideme wizard → Workflow → Image Describer

## Reproduction Steps
1. Run `idt guideme`
2. Select provider: Claude
3. Choose to provide API key file path
4. Enter path to claude API key file (e.g., `C:\Keys\claude.txt`)
5. Continue with workflow setup
6. Error occurs when image description starts

## Working Workaround
Run `bat\setup_claude_key.bat <path_to_key_file>` before running workflow. This sets the `ANTHROPIC_API_KEY` environment variable which works correctly.

## Root Cause Analysis

### How BAT File Works (WORKING ✅)
File: `bat/setup_claude_key.bat`
```batch
for /f "delims=" %%i in ('type "%1"') do set ANTHROPIC_API_KEY=%%i
```
- Sets `ANTHROPIC_API_KEY` environment variable
- Environment variable is inherited by subprocess (idt.exe)

### How Guideme Works (FAILING ❌)

**Flow:**
1. `guided_workflow.py::setup_api_key()` (lines 95-157)
   - Prompts user for API key file path
   - Converts to absolute path: `str(key_path_obj.resolve())` ✅
   - Returns absolute path string

2. `guided_workflow.py` (line 442)
   - Passes to workflow: `["--api-key-file", api_key_file]`

3. `workflow.py::main()` (line 1519)
   - Creates orchestrator with: `api_key_file=args.api_key_file`

4. `workflow.py::describe_images()` (line 654)
   - Passes to subprocess: `cmd.extend(["--api-key-file", self.api_key_file])`

5. `image_describer.py::main()` (lines 1315-1327)
   - Reads file: `api_key = f.read().strip()`
   - Passes to ImageDescriber: `api_key=api_key`

6. `image_describer.py::ImageDescriber._initialize_provider()` (lines 186-193)
   - Creates provider: `provider = ClaudeProvider()`
   - Sets key: `provider.api_key = self.api_key`

7. `imagedescriber/ai_providers.py::ClaudeProvider.__init__()` (line 342)
   - Checks: `self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()`
   - Initializes client if key and SDK available (lines 347-354)

8. `imagedescriber/ai_providers.py::ClaudeProvider.is_available()` (line 374)
   - Returns: `bool(self.api_key and self.client)`
   - If False → Error: "Claude API key not configured or SDK not installed"

### Hypothesis: Possible Causes

**Theory 1: API Key Not Being Passed Correctly**
- File path resolves correctly in guideme ✅
- Path passed to workflow.py ✅
- Path passed to image_describer.py ✅
- File reading might fail in subprocess? ❓

**Theory 2: Anthropic SDK Not Available in Built Executable**
- Import check: `imagedescriber/ai_providers.py` lines 30-34
- If `HAS_ANTHROPIC = False`, client won't initialize
- BUT: BAT file method works, so SDK must be bundled ✅
- SDK is initialized when env var is set ✅

**Theory 3: Client Initialization Fails**
- Lines 347-354 in `ai_providers.py`
- If exception occurs during `anthropic.Anthropic()` initialization
- Client becomes None → is_available() returns False
- BUT: Why would it work with env var but not with passed key? ❓

**Theory 4: API Key Overwritten During Initialization**
- Line 342: `self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()`
- Line 191 in image_describer.py: `provider.api_key = self.api_key`
- **ISSUE**: Setting `provider.api_key` AFTER initialization might not update the client
- The client was already created in `__init__` with possibly None key
- Setting api_key afterward doesn't recreate the client! 🔴

## Most Likely Root Cause

**In `image_describer.py` lines 186-193:**
```python
elif self.provider_name == "claude":
    logger.info("Initializing Claude provider...")
    if not self.api_key:
        raise ValueError("Claude provider requires an API key. Use --api-key-file option.")
    provider = ClaudeProvider()  # ❌ Client initialized without key
    provider.api_key = self.api_key  # ⚠️ Key set AFTER init, client not updated
    return provider
```

**In `ai_providers.py` lines 337-354:**
```python
def __init__(self, api_key: Optional[str] = None):
    self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()
    # ...
    if self.api_key and HAS_ANTHROPIC:
        try:
            self.client = anthropic.Anthropic(
                api_key=self.api_key,  # Uses self.api_key from __init__
                timeout=self.timeout,
                max_retries=3
            )
```

**The Problem:**
1. `ClaudeProvider()` called with no arguments → `api_key=None` in `__init__`
2. Line 342: `self.api_key = None or os.getenv('ANTHROPIC_API_KEY') or self._load_api_key_from_file()`
3. If env var not set and claude.txt not in current dir → `self.api_key = None`
4. Line 347: `if self.api_key and HAS_ANTHROPIC` → **False**, client not created
5. Later: `provider.api_key = self.api_key` sets the key but doesn't create client
6. `is_available()` → `bool(self.api_key and self.client)` → **False** because client is None

**Why BAT file works:**
- Sets `ANTHROPIC_API_KEY` environment variable
- Line 342: `self.api_key = None or os.getenv('ANTHROPIC_API_KEY')` → Gets env var ✅
- Client gets created in `__init__` ✅

## Debug Logging Added

Added comprehensive logging in `image_describer.py`:

**Lines 1315-1327 (API key loading):**
```python
logger.info(f"Attempting to load API key from: {api_key_path}")
logger.info(f"File exists: {api_key_path.exists()}")
logger.info(f"Absolute path: {api_key_path.resolve()}")
# ... read file ...
logger.info(f"Successfully loaded API key from {api_key_path} (length: {len(api_key)})")
print(f"INFO: Loaded API key from {api_key_path} (length: {len(api_key)})")
```

**Lines 186-194 (Provider initialization):**
```python
provider = ClaudeProvider()
provider.api_key = self.api_key
logger.info(f"Claude provider initialized. API key set: {bool(provider.api_key)}, Client available: {bool(provider.client)}, Is available: {provider.is_available()}")
print(f"INFO: Claude provider - API key set: {bool(provider.api_key)}, Client: {bool(provider.client)}, Available: {provider.is_available()}")
```

## Next Steps

### 1. Verify Root Cause (IMMEDIATE)
Rebuild executable and run guideme with Claude. Look for debug output:
- Should see: `API key set: True, Client: False, Available: False`
- This confirms client isn't initialized

### 2. Fix Provider Initialization (SOLUTION)
**Option A: Pass key to constructor (RECOMMENDED)**
```python
# In image_describer.py line 190
provider = ClaudeProvider(api_key=self.api_key)  # Pass key to __init__
# Remove line 191: provider.api_key = self.api_key
```

**Option B: Add method to update client**
```python
# In ai_providers.py, add method:
def set_api_key(self, api_key: str):
    self.api_key = api_key
    if self.api_key and HAS_ANTHROPIC:
        self.client = anthropic.Anthropic(api_key=self.api_key, ...)
```

**Option C: Move client init to lazy loading**
```python
# Make client a property that initializes on first access
@property
def client(self):
    if self._client is None and self.api_key and HAS_ANTHROPIC:
        self._client = anthropic.Anthropic(api_key=self.api_key, ...)
    return self._client
```

### 3. Apply Same Fix to OpenAI Provider
Check if `OpenAIProvider` has the same issue (lines 178-185 in image_describer.py)

### 4. Test
- Test guideme with Claude
- Test guideme with OpenAI
- Test with --api-key-file direct command
- Test with environment variable (regression test)

## Related Files
- `scripts/guided_workflow.py` - Lines 95-157 (setup_api_key), 442 (passing to workflow)
- `scripts/workflow.py` - Line 1519 (orchestrator creation), 654 (passing to image_describer)
- `scripts/image_describer.py` - Lines 186-194 (provider init), 1315-1327 (key loading)
- `imagedescriber/ai_providers.py` - Lines 334-374 (ClaudeProvider class)
- `bat/setup_claude_key.bat` - Working workaround

## Additional Context
This issue was discovered while testing the guideme wizard after implementing the workflow naming feature. The workflow naming changes did NOT cause this issue - it appears to have been a pre-existing bug that was masked by users primarily using the BAT file method.

## Resolution
- [ ] Verify root cause with debug output
- [ ] Implement fix (Option A recommended)
- [ ] Apply same fix to OpenAI provider
- [ ] Test all provider initialization methods
- [ ] Update documentation if needed
- [ ] Remove debug logging or reduce verbosity
- [ ] Commit fix
- [ ] Update this issue with resolution details

---
**Created:** October 11, 2025
**Last Updated:** October 11, 2025
**Assigned To:** Investigation
