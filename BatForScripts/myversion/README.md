# Workflow Batch File Examples

This directory contains example batch files showing how to run the end-to-end workflow with different AI providers.

## Quick Start

1. Pick a `.bat` file based on your preferred AI provider
2. Edit the file - change `INPUT_DIR` to your images folder
3. Double-click to run

## Available Examples

- **`run_ollama.bat`** - Ollama (local, free, most popular)
- **`run_onnx.bat`** - ONNX hardware-accelerated (local, free)
- **`run_openai.bat`** - OpenAI GPT-4o (cloud, paid, best quality)
- **`run_huggingface.bat`** - HuggingFace transformers (local, free)
- **`run_complete_workflow.bat`** - Full video→gallery pipeline

## Complete Documentation

**📚 See [docs/BATCH_FILES_GUIDE.md](../docs/BATCH_FILES_GUIDE.md) for:**
- Detailed provider comparison
- Setup instructions
- Customization options
- Troubleshooting
- Examples

## What These Do

All batch files run the **end-to-end workflow**:
1. Process images/videos
2. Generate AI descriptions
3. Create HTML gallery
4. Open viewer application

**These are EXAMPLES** - for advanced usage, use the command line or GUI app.

## Need Help?

- Provider setup → See `docs/<PROVIDER>_GUIDE.md`
- Workflow usage → See `docs/WORKFLOW_README.md`
- GUI app → See `docs/image_describer_README.md`
- All docs → See `docs/README.md`
