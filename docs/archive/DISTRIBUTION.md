# Distribution & Runtime Guide

This guide distills what an external user (or ops team) needs to run the toolkit
with minimal friction.

## Two Ways to Run

| Mode | Best For | Pros | Trade‑offs |
|------|----------|------|-----------|
| Executable (`ImageDescriptionToolkit.exe`) | Distribution, non-dev users | No Python install needed; single artifact | Harder to modify code; must rely on config overrides |
| Source (`python workflow.py`) | Development, rapid iteration | Full code control, immediate edits | Requires Python + dependencies |

## Quick Start (Executable User)

1. Install & start Ollama (or have cloud API keys ready).
2. Put media (images/videos) in a folder.
3. (Optional) Place a custom `image_describer_config.json` next to the EXE.
4. Run:
   ```powershell
   ImageDescriptionToolkit.exe workflow C:\media\collection --steps describe,html
   ```
5. Open generated `workflow_output_*/reports/image_descriptions.html`.

## Overriding Prompts / Defaults

Drop an edited `image_describer_config.json` beside the EXE OR set env vars:

```powershell
set IDT_IMAGE_DESCRIBER_CONFIG=C:\deploy\custom.json
```

Per-run style override:

```powershell
ImageDescriptionToolkit.exe workflow C:\media --prompt-style artistic
```

## Common Flags (Workflow)

| Flag | Purpose | Example |
|------|---------|---------|
| `--steps` | Limit pipeline stages | `--steps describe,html` |
| `--model` | Force specific AI model | `--model llava:7b` |
| `--prompt-style` | Override prompt style for run | `--prompt-style narrative` |
| `--output-dir` | Custom output root | `--output-dir C:\results` |
| `--resume` | Resume a prior output folder | `--resume workflow_output_20251008_101530` |
| `--verbose` | More logging detail | `--verbose` |

## Cloud Provider Keys

| Provider | Env Var | Alt Method |
|----------|---------|------------|
| OpenAI | `OPENAI_API_KEY` | `--api-key-file openai.txt` |
| Claude | `ANTHROPIC_API_KEY` | `--api-key-file claude.txt` |

## Typical Output Tree

```
workflow_output_YYYYMMDD_HHMMSS/
  logs/                  # All step logs
  extracted_frames/      # If video step used
  converted_images/      # HEIC → JPG
  descriptions/          # image_descriptions.txt
  reports/               # image_descriptions.html
```

## Verifying Config Override Worked

1. Run without `--prompt-style`.
2. Open `descriptions/image_descriptions.txt`.
3. Confirm header `Prompt style:` matches your custom default.
4. Re-run with a different `--prompt-style` to confirm override precedence.

## Troubleshooting Quick Table

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Prompt style unchanged | External config not found | Check filename & path; echo `%IDT_IMAGE_DESCRIBER_CONFIG%` |
| Model not found (Ollama) | Model not pulled | `ollama pull <model>` |
| Executable slow first run | PyInstaller extraction | Normal; subsequent runs faster |
| API key error | Missing env/file | Set env var or provide `--api-key-file` |
| No descriptions generated | Wrong step set | Include `describe` in `--steps` |

## Recommended Distribution Bundle

```
Deployment/
  ImageDescriptionToolkit.exe
  image_describer_config.json   # Editable prompts/defaults
  README_RUNTIME.txt            # Minimal run instructions
  examples/ (optional sample media)
```

## Minimal End-User Runtime Instructions (Drop-In Text)

```
1. Install and start Ollama (https://ollama.ai) OR have cloud API keys.
2. Put your images/videos in a folder (e.g. C:\media).
3. (Optional) Edit image_describer_config.json to adjust prompts/default style.
4. Run: ImageDescriptionToolkit.exe workflow C:\media --steps describe,html
5. Open the newest workflow_output_*/reports/image_descriptions.html
```

## When To Rebuild vs Not

| Need | Rebuild? | Reason |
|------|----------|--------|
| Change prompt text/style default | No | Use external config |
| Add new prompt variation | No | Add key in external JSON |
| Switch default model | No | Edit external JSON |
| Add new AI provider code | Yes | Python logic change |
| Modify workflow orchestration | Yes | Python logic change |

---
For deeper customization open an issue with tag `distribution`.
