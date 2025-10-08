# Batch Files Inventory

**Total: 35 batch files**

## Workflow Execution (26 files)

### Ollama Models - Local (16 files)

#### Small/Fast Models (3 files)
1. `run_ollama_moondream.bat` - Moondream (fastest, 1.7GB)
2. `run_ollama_llava_phi3.bat` - LLaVA Phi3 (small but mighty, 2.9GB)
3. `run_ollama_gemma.bat` - Gemma 3 (Google's model, 3.3GB)

#### Medium LLaVA Models (5 files)
4. `run_ollama_llava.bat` - LLaVA latest (4.7GB)
5. `run_ollama_llava7b.bat` - LLaVA 7B (balanced, 4.7GB) - **RECOMMENDED LOCAL**
6. `run_ollama_llava_llama3.bat` - LLaVA with Llama 3 base (5.5GB)
7. `run_ollama_bakllava.bat` - BakLLaVA variant (4.7GB)
8. `run_ollama_llava13b.bat` - LLaVA 13B (higher quality, 8GB)

#### Large LLaVA Models (1 file)
9. `run_ollama_llava34b.bat` - LLaVA 34B (highest quality LLaVA, 20GB)

#### Llama Vision Models (2 files)
10. `run_ollama_llama32vision.bat` - Llama 3.2 Vision (7.8GB)
11. `run_ollama_llama32vision11b.bat` - Llama 3.2 Vision 11B (most accurate, 7.8GB)

#### Other Vision Models (6 files)
12. `run_ollama_mistral31.bat` - Mistral Nemo 3.1 (12GB)
13. `run_ollama_mistral32.bat` - Pixtral 12B (Mistral 3.2, 7.3GB)
14. `run_ollama_minicpmv.bat` - MiniCPM-V (efficient Chinese model, 4GB)
15. `run_ollama_minicpmv8b.bat` - MiniCPM-V 8B (larger Chinese model, 5GB)
16. `run_ollama_qwen2.5vl.bat` - Qwen 2.5 VL (Alibaba's vision model, 5GB)

### OpenAI Models - Cloud (3 files)
20. `run_openai_gpt4o_mini.bat` - GPT-4o mini (fast & affordable)
21. `run_openai_gpt4o.bat` - GPT-4o (best quality)
22. `run_openai_gpt5.bat` - GPT-5 (latest OpenAI model)

### Claude Models - Cloud (7 files)

#### Claude 4 Series (4 files)
23. `run_claude_sonnet45.bat` - **RECOMMENDED** - Sonnet 4.5 (best for agents/coding)
24. `run_claude_opus41.bat` - Opus 4.1 (specialized complex tasks, superior reasoning)
25. `run_claude_sonnet4.bat` - Sonnet 4 (high performance)
26. `run_claude_opus4.bat` - Opus 4 (very high intelligence)

#### Claude 3.x Series (3 files)
27. `run_claude_sonnet37.bat` - Sonnet 3.7 (extended thinking)
28. `run_claude_haiku35.bat` - Haiku 3.5 (fastest, most affordable)
29. `run_claude_haiku3.bat` - Haiku 3 (fast and compact)

## API Key Management (4 files)

### Setup Keys (2 files)
30. `setup_openai_key.bat` - Set OPENAI_API_KEY from file
31. `setup_claude_key.bat` - Set ANTHROPIC_API_KEY from file

### Remove Keys (2 files)
32. `remove_openai_key.bat` - Clear OPENAI_API_KEY
33. `remove_claude_key.bat` - Clear ANTHROPIC_API_KEY

## Test & Utility Scripts (5 files)

34. `allmodeltest.bat` - Run all 16 Ollama models sequentially on test images
35. `allcloudtest.bat` - Run all 10 cloud models (OpenAI + Claude) sequentially
36. `install_vision_models.bat` - Install all vision models (~130GB download)

---

## Quick Reference

### All Models Now Accept Two Parameters:
1. `%1` - Image directory (required)
2. `%2` - Prompt style (optional, defaults to 'narrative')

**Examples:**
```batch
run_ollama_moondream.bat C:\MyImages
run_ollama_moondream.bat C:\MyImages detailed
run_claude_sonnet45.bat "C:\My Photos" creative
allmodeltest.bat C:\TestImages narrative
allcloudtest.bat C:\TestImages technical
```

### Model Recommendations by Use Case:

**Fast Testing (Free/Local):**
- `run_ollama_moondream.bat` - 1.7GB, very fast

**Balanced Local:**
- `run_ollama_llava7b.bat` - 4.7GB, good quality/speed balance

**Best Local Quality:**
- `run_ollama_llama32vision11b.bat` - 7.8GB, highest accuracy

**Fast Cloud (Paid):**
- `run_openai_gpt4o_mini.bat` - OpenAI's affordable option
- `run_claude_haiku35.bat` - Claude's fastest option

**Best Cloud Quality (Paid):**
- `run_claude_sonnet45.bat` - **RECOMMENDED** for most users
- `run_openai_gpt4o.bat` - OpenAI's best
- `run_claude_opus41.bat` - Claude's most capable

**Complex Reasoning (Paid):**
- `run_claude_opus41.bat` - Superior reasoning
- `run_claude_opus4.bat` - Very high intelligence

### Bulk Testing:
- `allmodeltest.bat <directory> [prompt_style]` - Test all 18 Ollama models
- `allcloudtest.bat <directory> [prompt_style]` - Test all 10 cloud models (requires API keys)

**Note:** The 90B Llama Vision model has been removed due to extreme resource requirements (64GB+ RAM, 15+ minutes per image).
