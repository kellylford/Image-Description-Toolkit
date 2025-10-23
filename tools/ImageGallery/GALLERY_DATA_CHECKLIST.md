# Image Gallery Data Collection Checklist

This checklist tracks the workflow runs needed to populate the Image Gallery with comprehensive data.

## Configuration

- **Workflow Name**: 25imagetest
- **Image Directory**: (specify your image directory)
- **Prompts**: narrative, colorful, technical
- **Output Directory**: Descriptions

## Prerequisites

- [ ] Set up Claude API key (run: `setup_claude_key.bat` or set manually)
- [ ] Set up OpenAI API key (run: `setup_openai_key.bat` or set manually)
- [ ] Ensure Ollama is running
- [ ] Install required Ollama models (see Ollama Models section below)

## Claude Models (9 workflows)

### Claude Haiku 3.5
- [ ] claude-3-5-haiku-20241022 + narrative
- [ ] claude-3-5-haiku-20241022 + colorful
- [ ] claude-3-5-haiku-20241022 + technical

### Claude Opus 4
- [ ] claude-opus-4-20250514 + narrative
- [ ] claude-opus-4-20250514 + colorful
- [ ] claude-opus-4-20250514 + technical

### Claude Sonnet 4.5
- [ ] claude-sonnet-4-5-20250929 + narrative
- [ ] claude-sonnet-4-5-20250929 + colorful
- [ ] claude-sonnet-4-5-20250929 + technical

## OpenAI Models (6 workflows)

### GPT-4o-mini
- [ ] gpt-4o-mini + narrative
- [ ] gpt-4o-mini + colorful
- [ ] gpt-4o-mini + technical

### GPT-4o
- [ ] gpt-4o + narrative
- [ ] gpt-4o + colorful
- [ ] gpt-4o + technical

## Ollama Models (12 workflows)

### Qwen3-VL (Cloud)
- [ ] qwen3-vl:235b-cloud + narrative
- [ ] qwen3-vl:235b-cloud + colorful
- [ ] qwen3-vl:235b-cloud + technical

### Llava
- [ ] llava:latest + narrative
- [ ] llava:latest + colorful
- [ ] llava:latest + technical

### Gemma3
- [ ] gemma3:latest + narrative
- [ ] gemma3:latest + colorful
- [ ] gemma3:latest + technical

### Moondream
- [ ] moondream:latest + narrative
- [ ] moondream:latest + colorful
- [ ] moondream:latest + technical

## Ollama Models Installation

Run these commands to install the required Ollama models:

```bash
ollama pull qwen3-vl:235b-cloud
ollama pull llava:latest
ollama pull gemma3:latest
ollama pull moondream:latest
```

## Total Workflows

- **Claude**: 9 workflows
- **OpenAI**: 6 workflows
- **Ollama**: 12 workflows
- **TOTAL**: 27 workflows

## Notes

- Each workflow processes 25 images
- Total descriptions to generate: 675 (27 workflows × 25 images)
- Estimated time will vary by provider and model
- Cloud models (Claude, OpenAI) will incur API costs
- Run `generate_all_gallery_data.bat` to execute all workflows automatically

## After Data Collection

- [ ] Run: `python generate_descriptions.py --name 25imagetest`
- [ ] Copy `descriptions/` folder to web server
- [ ] Copy `index.html` to web server
- [ ] Copy image files to web server
- [ ] Test the gallery in a browser
