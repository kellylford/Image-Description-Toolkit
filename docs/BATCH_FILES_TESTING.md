# AI Provider Batch Files - Testing Guide

This document explains how to test each AI provider batch file to ensure it works correctly.

## Prerequisites

Before testing any batch file, ensure you have:

1. **Python 3.8+** installed
2. **Project dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```
3. **Test images** available (included in `tests/test_files/images/`)

## Provider-Specific Requirements

### Ollama (run_ollama.bat)

**Requirements:**
- Ollama installed from https://ollama.ai
- Model pulled: `ollama pull moondream`

**Test Steps:**
1. Edit `run_ollama.bat`:
   ```batch
   set IMAGE_PATH=C:\path\to\your\test\image.jpg
   ```

2. Run: `run_ollama.bat`

3. **Verify Success:**
   - No error messages
   - New folder created: `wf_ollama_moondream_narrative_YYYYMMDD_HHMMSS/`
   - File exists: `wf_ollama_*/descriptions/descriptions.txt`
   - File contains image description text

**Expected Output:**
```
============================================================================
SUCCESS! Workflow completed successfully
============================================================================

Results saved to: wf_ollama_moondream_narrative_* directory
```

---

### ONNX (run_onnx.bat)

**Requirements:**
- ONNX Runtime: `pip install onnxruntime`
- First run downloads Florence-2 model (~700MB)

**Test Steps:**
1. Edit `run_onnx.bat`:
   ```batch
   set IMAGE_PATH=C:\path\to\your\test\image.jpg
   ```

2. Run: `run_onnx.bat`

3. **First Run:**
   - Wait for model download (~5-15 minutes)
   - Model cached in `~/.cache/torch/hub/checkpoints/`

4. **Verify Success:**
   - No error messages
   - New folder created: `wf_onnx_florence-2-large_narrative_*/`
   - File exists: `wf_onnx_*/descriptions/descriptions.txt`
   - File contains image description text

**Expected Output:**
```
NOTE: If this is your first time using ONNX provider:
  - Florence-2 model will be downloaded (~700MB)
  - This may take a few minutes depending on your internet speed
  - Model is cached for future use

Running workflow...
[Processing messages...]

SUCCESS! Workflow completed successfully
Results saved to: wf_onnx_florence-2-large_narrative_* directory
TIP: Subsequent runs will be faster (model is now cached)
```

---

### OpenAI (run_openai_gpt4o.bat)

**Requirements:**
- OpenAI API key from https://platform.openai.com/api-keys
- API key saved to file (e.g., `openai_key.txt`)
- Account with credits/billing enabled

**Test Steps:**
1. Create API key file:
   ```bash
   echo sk-your-api-key-here > openai_key.txt
   ```

2. Edit `run_openai_gpt4o.bat`:
   ```batch
   set IMAGE_PATH=C:\path\to\your\test\image.jpg
   set API_KEY_FILE=C:\path\to\openai_key.txt
   ```

3. Run: `run_openai_gpt4o.bat`

4. **Verify Success:**
   - No error messages
   - New folder created: `wf_openai_gpt-4o_narrative_*/`
   - File exists: `wf_openai_*/descriptions/descriptions.txt`
   - File contains image description text

**Expected Output:**
```
SUCCESS! Workflow completed successfully
Results saved to: wf_openai_gpt-4o_narrative_* directory

NOTE: Check your OpenAI usage at https://platform.openai.com/usage
      Estimated cost: ~$0.01-0.02 per image with gpt-4o
```

---

### HuggingFace (run_huggingface.bat)

**Requirements:**
- HuggingFace account from https://huggingface.co/join
- API token from https://huggingface.co/settings/tokens
- Token saved to file (e.g., `huggingface_token.txt`)

**Test Steps:**
1. Create token file:
   ```bash
   echo hf_your-token-here > huggingface_token.txt
   ```

2. Edit `run_huggingface.bat`:
   ```batch
   set IMAGE_PATH=C:\path\to\your\test\image.jpg
   set TOKEN_FILE=C:\path\to\huggingface_token.txt
   ```

3. Run: `run_huggingface.bat`

4. **First Request:**
   - May take 30-60 seconds (model loading)
   - Subsequent requests faster

5. **Verify Success:**
   - No error messages
   - New folder created: `wf_huggingface_*_narrative_*/`
   - File exists: `wf_huggingface_*/descriptions/descriptions.txt`
   - File contains image description text

**Expected Output:**
```
NOTE: Using HuggingFace Inference API (cloud processing)
      Images are sent to HuggingFace servers for processing

SUCCESS! Workflow completed successfully
Results saved to: wf_huggingface_*_narrative_* directory

NOTE: Free tier has rate limits. If you hit limits, wait or upgrade.
```

---

### GitHub Copilot (run_copilot.bat)

**Requirements:**
- GitHub Copilot subscription ($10-19/month)
- GitHub CLI installed from https://cli.github.com
- Authenticated: `gh auth login`

**Test Steps:**
1. Verify Copilot access:
   ```bash
   gh auth status
   gh copilot --help
   ```

2. Edit `run_copilot.bat`:
   ```batch
   set IMAGE_PATH=C:\path\to\your\test\image.jpg
   ```

3. Run: `run_copilot.bat`

4. **Verify Success:**
   - No error messages
   - New folder created: `wf_copilot_gpt-4o_narrative_*/`
   - File exists: `wf_copilot_*/descriptions/descriptions.txt`
   - File contains image description text

**Expected Output:**
```
Checking GitHub authentication...
Running workflow...
NOTE: Using GitHub Copilot (requires active subscription)
      Images are processed via GitHub Copilot API

SUCCESS! Workflow completed successfully
Results saved to: wf_copilot_gpt-4o_narrative_* directory
```

---

## Quick Verification Checklist

For each provider, verify:

- [ ] Batch file runs without errors
- [ ] Workflow directory created (`wf_<provider>_*`)
- [ ] Descriptions directory created (`wf_*/descriptions/`)
- [ ] Description file created (`descriptions.txt`)
- [ ] File contains actual image description (not empty)
- [ ] Description is relevant to the test image

## Common Issues

### All Providers

**"Python is not installed or not in PATH"**
- Install Python 3.8+ from python.org
- Add to PATH during installation

**"workflow.py not found in current directory"**
- Run batch file from project root directory
- Or move batch file to project root

### Provider-Specific

**Ollama: "Ollama is not running or not installed"**
- Install from https://ollama.ai
- Pull model: `ollama pull moondream`
- Ensure Ollama service is running

**ONNX: "ONNX Runtime not found"**
- Install: `pip install onnxruntime`
- Batch file will try to auto-install

**OpenAI: "Invalid or expired API key"**
- Get new key from https://platform.openai.com/api-keys
- Ensure billing is set up
- Check key has credits

**HuggingFace: "Rate limit exceeded"**
- Wait until next month (free tier resets monthly)
- Upgrade to Pro tier ($9/month)
- Use local provider instead

**Copilot: "No active GitHub Copilot subscription"**
- Subscribe at https://github.com/features/copilot
- Wait for activation (a few minutes)
- Re-authenticate: `gh auth refresh`

## Test Image Recommendations

Use these test images from the project:

```
tests/test_files/images/blue_landscape.jpg    - Landscape photo
tests/test_files/images/green_circle.png      - Simple shape
tests/test_files/images/purple_portrait.png   - Portrait
tests/test_files/images/red_square.jpg        - Geometric
tests/test_files/images/yellow_banner.jpg     - Banner/graphic
```

Or use your own images to test real-world scenarios.

## Automated Testing

For developers wanting to run automated tests:

```bash
# Test ONNX (most reliable, no external API)
python scripts/workflow.py "tests/test_files/images/blue_landscape.jpg" \
  --steps describe \
  --provider onnx \
  --model florence-2-large \
  --prompt-style narrative

# Test with your provider
python scripts/workflow.py "<your-image>" \
  --steps describe \
  --provider <provider> \
  --model <model> \
  --prompt-style narrative \
  [--api-key-file <keyfile>]
```

## Success Criteria

A batch file test is considered successful when:

1. ✅ Runs without Python errors
2. ✅ Creates workflow directory
3. ✅ Generates `descriptions.txt` file
4. ✅ Description text is relevant and accurate
5. ✅ Matches expected format from prompt style
6. ✅ Completes in reasonable time

## Reporting Issues

If a batch file fails:

1. Check the error message
2. Verify all requirements are met
3. Check provider-specific guides in `docs/`
4. Review common issues above
5. Test with direct Python command first
6. Check provider status/availability

## Next Steps

After successful testing:

- Customize batch files for your workflow
- Create additional batch files for different models
- Integrate into your automation scripts
- Share custom configurations with team

## Documentation

For detailed setup guides, see:

- `docs/OLLAMA_GUIDE.md` - Ollama setup and usage
- `docs/ONNX_GUIDE.md` - ONNX setup and usage
- `docs/OPENAI_SETUP_GUIDE.md` - OpenAI setup and usage
- `docs/HUGGINGFACE_GUIDE.md` - HuggingFace setup and usage
- `docs/COPILOT_GUIDE.md` - GitHub Copilot setup and usage
