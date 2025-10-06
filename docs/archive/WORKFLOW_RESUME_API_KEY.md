# Workflow Resume API Key Requirement

## Issue

When resuming a workflow that uses cloud-based AI providers (OpenAI, Claude, HuggingFace), you must provide the `--api-key-file` parameter again, even though it was provided in the original workflow run.

## Why This Happens

The workflow resume feature reads the following parameters from the workflow logs:
- ✅ Model name (`--model`)
- ✅ Prompt style (`--prompt-style`)
- ✅ Provider (`--provider`)
- ✅ Config file (`--config`)
- ❌ **API key file path is NOT saved/restored**

This is by design for security reasons - API key file paths are not saved in the workflow logs to prevent exposing sensitive credential locations.

## Affected Providers

This requirement applies to cloud-based providers that require API keys:
- **OpenAI** - Requires `OPENAI_API_KEY` or `--api-key-file`
- **Claude** - Requires `ANTHROPIC_API_KEY` or `--api-key-file`
- **HuggingFace** - Requires `HUGGINGFACE_API_KEY` or `--api-key-file`

**Not affected:**
- Ollama (local, no API key)
- ONNX (local, no API key)
- Copilot+ PC (local NPU, no API key)
- GroundingDINO (local, no API key)

## Solutions

### Option 1: Provide API Key File When Resuming (Recommended)

```bash
# Resume with API key file
python workflow.py --resume <workflow_directory> --api-key-file <path_to_key>

# Examples:
python workflow.py --resume wf_openai_gpt-4o-mini_narrative_20251005_122700 --api-key-file ~/openai.txt
python workflow.py --resume wf_claude_claude-sonnet-4-5-20250929_narrative_20251005_150328 --api-key-file ~/claude.txt
```

### Option 2: Set Environment Variable

Set the appropriate environment variable before resuming:

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-your-key-here
python workflow.py --resume wf_openai_gpt-4o-mini_narrative_20251005_122700

set ANTHROPIC_API_KEY=sk-ant-your-key-here
python workflow.py --resume wf_claude_claude-sonnet-4-5-20250929_narrative_20251005_150328
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-your-key-here"
python workflow.py --resume wf_openai_gpt-4o-mini_narrative_20251005_122700

$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
python workflow.py --resume wf_claude_claude-sonnet-4-5-20250929_narrative_20251005_150328
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY=sk-your-key-here
python workflow.py --resume wf_openai_gpt-4o-mini_narrative_20251005_122700

export ANTHROPIC_API_KEY=sk-ant-your-key-here
python workflow.py --resume wf_claude_claude-sonnet-4-5-20250929_narrative_20251005_150328
```

### Option 3: Use Batch Files

Pre-configured batch files that include the API key path:

**For OpenAI:**
```batch
.venv\Scripts\python.exe workflow.py --resume "wf_openai_gpt-4o-mini_narrative_20251005_122700" --api-key-file "BatForScripts\myversion\openai.txt"
```

**For Claude:**
```batch
.venv\Scripts\python.exe workflow.py --resume "wf_claude_claude-sonnet-4-5-20250929_narrative_20251005_150328" --api-key-file "BatForScripts\myversion\claude.txt"
```

## Error Messages

If you forget to provide the API key when resuming, you'll see:

```
ERROR - Provider 'openai' requires an API key.
ERROR - Provide it via --api-key-file or set OPENAI_API_KEY environment variable
```

or

```
ERROR - Provider 'claude' requires an API key.
ERROR - Provide it via --api-key-file or set ANTHROPIC_API_KEY environment variable
```

## Workflow State Preservation

What **IS** preserved when resuming:
- ✅ Input directory path
- ✅ Output directory structure
- ✅ Completed steps (won't re-run)
- ✅ Converted images
- ✅ Extracted video frames
- ✅ Existing descriptions (will skip already described images)
- ✅ Model name
- ✅ Prompt style
- ✅ Provider selection
- ✅ Configuration file

What **IS NOT** preserved (must provide again):
- ❌ API key file path (security reasons)
- ❌ Custom detection queries (for GroundingDINO)
- ❌ Custom confidence thresholds

## Best Practices

1. **Create batch files for your workflows** - Include the `--api-key-file` parameter so you don't forget
2. **Use environment variables** - Set them in your shell profile for convenience
3. **Store API keys securely** - Don't commit them to git, use `.gitignore`
4. **Document your workflow commands** - Keep a note of what parameters you used

## Related Files

- `resume_openai_workflow.bat` - Example batch file for resuming OpenAI workflows
- `resume_claude_workflow.bat` - Example batch file for resuming Claude workflows (if created)
- `run_claude_workflow.bat` - Fresh Claude workflow with API key
- `run_openai_gpt4o.bat` - Fresh OpenAI workflow with API key

## Technical Details

The workflow resume logic is in `scripts/workflow.py` around line 1203-1270. The state parsing extracts workflow metadata from logs but intentionally excludes sensitive information like API key paths for security.

If you need to modify this behavior, look for the `parse_workflow_state()` function and the resume mode handling in the `main()` function.
