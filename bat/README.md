# Batch Files for Image Description Toolkit

Simple batch file wrappers for running the workflow with different AI models and providers.

## Directory Structure

These batch files are in the `bat/` directory, which is one level below the main `workflow.py` script.

## Ollama Models (Local - No API Key Required)

### Fast & Small
- `run_ollama_moondream.bat` - Fastest, smallest (1.7GB)
  ```
  run_ollama_moondream.bat C:\Photos
  ```

### Balanced Quality & Speed
- `run_ollama_llava7b.bat` - LLaVA 7B (4.7GB) - **RECOMMENDED**
  ```
  run_ollama_llava7b.bat C:\Photos
  ```
- `run_ollama_llava.bat` - LLaVA latest (4.7GB)
  ```
  run_ollama_llava.bat C:\Photos
  ```
- `run_ollama_llava_llama3.bat` - LLaVA with Llama 3 base (5.5GB)
  ```
  run_ollama_llava_llama3.bat C:\Photos
  ```
- `run_ollama_bakllava.bat` - BakLLaVA variant (4.7GB)
  ```
  run_ollama_bakllava.bat C:\Photos
  ```

### Best Quality
- `run_ollama_llama32vision11b.bat` - Llama 3.2 Vision 11B (7.5GB) - Most accurate
  ```
  run_ollama_llama32vision11b.bat C:\Photos
  ```
- `run_ollama_llama32vision.bat` - Llama 3.2 Vision latest (7.5GB)
  ```
  run_ollama_llama32vision.bat C:\Photos
  ```

### Other Models
- `run_ollama_mistral.bat` - Mistral Small 3.1 (4GB)
  ```
  run_ollama_mistral.bat C:\Photos
  ```
- `run_ollama_gemma.bat` - Gemma 3 (Google's model, 5GB)
  ```
  run_ollama_gemma.bat C:\Photos
  ```

## OpenAI Models (Cloud - API Key Required)

### Setup API Key (One Time)
```
setup_openai_key.bat C:\Keys\openai.txt
```
OR place `openai.txt` with your API key in the current directory.

### Run Models
- `run_openai_gpt4o_mini.bat` - Fast & affordable
  ```
  run_openai_gpt4o_mini.bat C:\Photos
  ```
- `run_openai_gpt4o.bat` - Best quality
  ```
  run_openai_gpt4o.bat C:\Photos
  ```

### Remove API Key (When Done)
```
remove_openai_key.bat
```

## Claude Models (Cloud - API Key Required)

### Setup API Key (One Time)
```
setup_claude_key.bat C:\Keys\claude.txt
```
OR place `claude.txt` with your API key in the current directory.

### Run Models

#### Claude 4 Series (Latest - 2025)
- `run_claude_sonnet45.bat` - **RECOMMENDED** - Best for agents/coding
  ```
  run_claude_sonnet45.bat C:\Photos
  ```
- `run_claude_opus41.bat` - Specialized complex tasks, superior reasoning
  ```
  run_claude_opus41.bat C:\Photos
  ```
- `run_claude_sonnet4.bat` - High performance
  ```
  run_claude_sonnet4.bat C:\Photos
  ```
- `run_claude_opus4.bat` - Very high intelligence
  ```
  run_claude_opus4.bat C:\Photos
  ```

#### Claude 3.7 Series
- `run_claude_sonnet37.bat` - High performance with extended thinking
  ```
  run_claude_sonnet37.bat C:\Photos
  ```

#### Claude 3.5 Series
- `run_claude_haiku35.bat` - Fastest, most affordable
  ```
  run_claude_haiku35.bat C:\Photos
  ```

#### Claude 3 Series
- `run_claude_haiku3.bat` - Fast and compact
  ```
  run_claude_haiku3.bat C:\Photos
  ```

### Remove API Key (When Done)
```
remove_claude_key.bat
```

## API Key Management

### Three Ways to Provide API Keys:

1. **Environment Variable** (session-based)
   ```
   setup_openai_key.bat C:\Keys\openai.txt
   setup_claude_key.bat C:\Keys\claude.txt
   ```

2. **File in Current Directory** (preferred)
   - Place `openai.txt` in the directory where you run the batch file
   - Place `claude.txt` in the directory where you run the batch file

3. **System Environment Variable** (permanent)
   - Set `OPENAI_API_KEY` in Windows System Environment Variables
   - Set `ANTHROPIC_API_KEY` in Windows System Environment Variables

### Security Notes:
- API key files are read from CURRENT directory only (no automatic searching)
- Environment variables set by batch files are SESSION-ONLY (not permanent)
- Use `remove_*_key.bat` scripts to clear session variables when done

## All Models Use Narrative Prompt Style

All batch files are configured to use the `--prompt-style narrative` setting for consistent, detailed descriptions.

## Examples

### Local Processing (No API Key)
```
cd C:\Users\Kelly\GitHub\idt\bat
run_ollama_llava7b.bat C:\Photos\Vacation2024
```

### Cloud Processing with OpenAI
```
cd C:\Users\Kelly\GitHub\idt\bat
setup_openai_key.bat C:\Keys\openai.txt
run_openai_gpt4o.bat C:\Photos\Vacation2024
remove_openai_key.bat
```

### Cloud Processing with Claude
```
cd C:\Users\Kelly\GitHub\idt\bat
setup_claude_key.bat C:\Keys\claude.txt
run_claude_sonnet45.bat C:\Photos\Vacation2024
remove_claude_key.bat
```

### Compare Multiple Providers
```
cd C:\Users\Kelly\GitHub\idt\bat
run_ollama_llava7b.bat C:\Photos\Test
run_openai_gpt4o.bat C:\Photos\Test
run_claude_sonnet45.bat C:\Photos\Test
```
Then open in the viewer to compare descriptions side-by-side!

## Output Location

All workflows create output in the `Descriptions/` directory (one level up from bat folder).
Each run creates a timestamped `wf_` subdirectory inside `Descriptions/` for organization.

**Directory structure:**
```
C:\Users\Kelly\GitHub\idt\
├── bat\                                           # Batch files
├── Descriptions\                                  # All workflow outputs go here
│   ├── wf_ollama_llava-7b_narrative_20251006_143022\
│   ├── wf_openai_gpt-4o_narrative_20251006_150341\
│   └── wf_claude_sonnet-4-5_narrative_20251006_152105\
└── workflow.py                                    # Main workflow script
```

**Each `wf_` directory contains:**
- `converted/` - HEIC→JPG conversions (if convert step was run)
- `extracted_frames/` - Video frames (if video step was run)
- `descriptions.json` - AI-generated descriptions (if describe step was run)
- `html_output/` - HTML report (if html step was run)
- `logs/` - Workflow execution logs

This keeps all description outputs organized in one place and prevents polluting the project root.

## Requirements

- Python virtual environment at `..\.venv\` (one level up from bat directory)
- Ollama installed locally (for Ollama models)
- OpenAI API key (for OpenAI models)
- Claude API key (for Claude models)
