# Image Description Model Selection Guide

## Overview

The Image Description Toolkit supports multiple AI providers with dozens of vision models. This guide helps you choose the best model for your specific needs, considering factors like speed, quality, resource usage, and prompt-following ability.

## Quick Recommendations

### 🚀 **Just Getting Started?**
- **Ollama**: `moondream:latest` (fast, lightweight, good quality)
- **Hugging Face**: `microsoft/git-base-coco` (smallest, honest basic captions)

### 🎯 **Best Overall Balance?**
- **Ollama**: `llava-llama3:latest` (excellent quality, reasonable speed)
- **Hugging Face**: ⚠️ **Wait for instructblip download** (blip2-opt disappoints)

### 🏆 **Highest Quality?**
- **OpenAI**: `gpt-4o` (best overall, requires API key)
- **Claude**: `claude-sonnet-4-5-20250929` (Claude 4.5 - exceptional for agents/coding)
- **Claude**: `claude-opus-4-1-20250805` (Claude 4.1 - specialized complex tasks)
- **Ollama**: `llama3.2-vision:latest` (excellent free option)

### ❌ **Models to Avoid**
- **Hugging Face**: `Salesforce/blip2-opt-2.7b` (poor quality despite marketing claims)

---

## Provider Comparison

| Provider | Models | Setup | Cost | Offline | Customization |
|----------|--------|-------|------|---------|---------------|
| **OpenAI** | 3 models | API key required | Pay per use | ❌ No | Limited |
| **Claude** | 7 models | API key required | Pay per use | ❌ No | Limited |
| **Ollama** | 6+ models | Local install | Free | ✅ Yes | High |
| **Hugging Face** | 6 models | Auto-download | Free | ✅ Yes | High |

---

## Ollama Models (Local, Free)

### 🌙 **moondream:latest** - *Best Starter Model*
- **Size**: ~1.7GB
- **Speed**: ⭐⭐⭐⭐⭐ Very Fast
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐ Basic
- **Best for**: Quick captions, batch processing, learning the app
- **Strengths**: Lightweight, fast startup, low resource usage

### 🦙 **llava:latest** - *Classic Vision Model*
- **Size**: ~4.7GB
- **Speed**: ⭐⭐⭐⭐ Fast
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐⭐ Good
- **Best for**: General descriptions, reliable performance
- **Strengths**: Well-established, stable, good balance

### 🦙 **llava-llama3:latest** - *Recommended General Use*
- **Size**: ~4.7GB
- **Speed**: ⭐⭐⭐⭐ Fast
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Best for**: Most users, detailed descriptions, custom prompts
- **Strengths**: Latest Llama 3 base, excellent instruction following

### 🦙 **llama3.2-vision:latest** - *Highest Quality Local*
- **Size**: ~7.9GB
- **Speed**: ⭐⭐⭐ Moderate
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Best for**: High-quality descriptions, complex prompts, professional use
- **Strengths**: Latest model, best local quality, great reasoning

### 💎 **gemma2:latest** - *Efficient Alternative*
- **Size**: ~2.9GB
- **Speed**: ⭐⭐⭐⭐ Fast
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐⭐ Good
- **Best for**: Resource-constrained systems, fast processing
- **Strengths**: Google's efficient architecture, good performance/size ratio

### 🌟 **mistral-small:latest** - *Balanced Option*
- **Size**: ~7.7GB
- **Speed**: ⭐⭐⭐ Moderate
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐⭐ Good
- **Best for**: Users wanting something different from Llama models
- **Strengths**: Mistral architecture, good multilingual support

---

## Hugging Face Models (Local, Free)

### 🏃 **microsoft/git-base-coco** - *Fastest Local*
- **Size**: ~1GB
- **Speed**: ⭐⭐⭐⭐⭐ Very Fast
- **Quality**: ⭐⭐⭐ Basic but honest
- **Prompt Following**: ⭐ None (ignores custom prompts)
- **Best for**: Quick captions, testing, batch processing thousands of images
- **Strengths**: Honest about what it does - simple captions, nothing more
- **Note**: Performs as well as blip2-opt for basic captions despite being 5x smaller

### 🔥 **Salesforce/blip2-opt-2.7b** - *DISAPPOINTING for Detailed Work*
- **Size**: ~5GB
- **Speed**: ⭐⭐⭐⭐ Fast
- **Quality**: ⭐⭐ Poor for narratives
- **Prompt Following**: ⭐⭐ Very limited
- **Best for**: Only basic captioning (similar to git-base)
- **Avoid for**: Detailed descriptions, narrative prompts, professional use
- **Real Result**: "A train is seen at a station" for complex images with detailed prompts
- **Note**: ⚠️ **Not recommended** - performs barely better than git-base despite 5x the size

### 🎯 **Salesforce/blip2-flan-t5-xl** - *Better Instructions*
- **Size**: ~11GB
- **Speed**: ⭐⭐⭐ Moderate
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Best for**: Complex instructions, detailed prompts, reasoning tasks
- **Strengths**: T5 language model, excellent instruction following

### 💬 **openbmb/MiniCPM-V-2** - *Conversational*
- **Size**: ~8GB
- **Speed**: ⭐⭐⭐ Moderate
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐⭐ Good
- **Best for**: Conversational descriptions, interactive use
- **Strengths**: Chat-optimized, efficient architecture

### 🎓 **Salesforce/instructblip-vicuna-7b** - *Instruction Expert*
- **Size**: ~13GB
- **Speed**: ⭐⭐ Slow
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Best for**: Complex instructions, professional descriptions, detailed analysis
- **Strengths**: Instruction-tuned, excellent for complex prompts

### 🦙 **llava-hf/llava-1.5-7b-hf** - *Full Precision LLaVA*
- **Size**: ~13GB
- **Speed**: ⭐⭐ Slow
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Best for**: When you want maximum quality LLaVA (vs compressed Ollama versions)
- **Note**: Similar to Ollama LLaVA but full precision - Ollama versions often better choice

---

## OpenAI Models (Cloud, Paid)

### 🌟 **gpt-4o** - *Best Overall*
- **Speed**: ⭐⭐⭐⭐⭐ Very Fast (cloud)
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Cost**: ~$0.01-0.05 per image
- **Best for**: Professional use, highest quality, complex reasoning

### 🎯 **gpt-4o-mini** - *Balanced Cloud Option*
- **Speed**: ⭐⭐⭐⭐⭐ Very Fast (cloud)
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Cost**: ~$0.001-0.01 per image
- **Best for**: Cost-conscious users, good quality with lower cost

### ⚡ **gpt-4-turbo** - *Legacy Option*
- **Speed**: ⭐⭐⭐⭐ Fast (cloud)
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Cost**: ~$0.01-0.05 per image
- **Best for**: Users with existing workflows, similar to gpt-4o

---

## Claude Models (Anthropic, Cloud, Paid)

**All Claude 3.x and 4.x models support vision.** Claude 2.x models excluded (no vision support).

### 🌟 **claude-sonnet-4-5-20250929** - *Claude 4.5 - Best Overall*
- **Speed**: ⭐⭐⭐⭐ Fast (cloud)
- **Quality**: ⭐⭐⭐⭐⭐ Outstanding
- **Prompt Following**: ⭐⭐⭐⭐⭐ Outstanding
- **Cost**: ~$0.003-0.015 per image
- **Best for**: Agents, coding, highest intelligence across most tasks
- **Strengths**: Top-tier reasoning, complex agents, multilingual, long-context
- **Note**: **RECOMMENDED** - Latest and most capable Claude model

### 🏆 **claude-opus-4-1-20250805** - *Claude 4.1 - Specialized Excellence*
- **Speed**: ⭐⭐⭐ Moderate (cloud)
- **Quality**: ⭐⭐⭐⭐⭐ Exceptional
- **Prompt Following**: ⭐⭐⭐⭐⭐ Outstanding
- **Cost**: ~$0.015-0.075 per image
- **Best for**: Specialized complex tasks requiring superior reasoning
- **Strengths**: Exceptional reasoning, advanced problem-solving
- **Note**: Most powerful for specialized applications

### � **claude-sonnet-4-20250514** - *Claude 4 - High Performance*
- **Speed**: ⭐⭐⭐⭐ Fast (cloud)
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Cost**: ~$0.003-0.015 per image
- **Best for**: High-performance tasks, balanced quality/speed
- **Strengths**: Excellent general purpose model

### 💎 **claude-3-7-sonnet-20250219** - *Claude 3.7 - Extended Thinking*
- **Speed**: ⭐⭐⭐⭐ Fast (cloud)
- **Quality**: ⭐⭐⭐⭐⭐ Excellent
- **Prompt Following**: ⭐⭐⭐⭐⭐ Excellent
- **Cost**: ~$0.003-0.015 per image
- **Best for**: Tasks requiring extended thinking capability
- **Strengths**: Toggleable extended thinking, high intelligence

### � **claude-3-5-haiku-20241022** - *Claude 3.5 Haiku - Fast & Affordable*
- **Speed**: ⭐⭐⭐⭐⭐ Very Fast (cloud)
- **Quality**: ⭐⭐⭐⭐ Good
- **Prompt Following**: ⭐⭐⭐⭐ Good
- **Cost**: ~$0.0008-0.004 per image
- **Best for**: Batch processing, cost-conscious users, testing
- **Strengths**: Fastest affordable option, excellent value

### ⚡ **claude-3-haiku-20240307** - *Claude 3 Haiku - Ultra Fast*
- **Speed**: ⭐⭐⭐⭐⭐ Very Fast (cloud)
- **Quality**: ⭐⭐⭐ Basic
- **Prompt Following**: ⭐⭐⭐⭐ Good
- **Cost**: ~$0.00025-0.00125 per image
- **Best for**: Very high volume, lowest cost
- **Strengths**: Cheapest option, very fast

**Deprecated Models:** Claude 3.5 Sonnet (Oct/Jun 2024), Claude 3 Opus/Sonnet (Feb 2024) - superseded by Claude 4 series.

---

## Use Case Recommendations

### 📚 **Learning/Testing the App**
1. **Ollama**: `moondream:latest` (fast, lightweight)
2. **HF**: `microsoft/git-base-coco` (tiny download)

### 🏠 **Personal Use (Photos, Art)**
1. **Ollama**: `llava-llama3:latest` (excellent quality)
2. **Ollama**: `llama3.2-vision:latest` (highest quality free option)
3. **Claude**: `claude-3-5-haiku-20241022` (affordable cloud option)
4. **HF**: Wait for `instructblip` download (avoid blip2-opt)
5. **OpenAI**: `gpt-4o-mini` (if you don't mind paying)

### 💼 **Professional/Commercial Use**
1. **Claude**: `claude-sonnet-4-5-20250929` (Claude 4.5 - best for agents/complex tasks)
2. **OpenAI**: `gpt-4o` (highest quality, well-established)
3. **Claude**: `claude-opus-4-1-20250805` (Claude 4.1 - specialized excellence)
4. **Ollama**: `llama3.2-vision:latest` (best free option)
5. **HF**: `Salesforce/instructblip-vicuna-7b` (instruction expert - downloading...)

### ⚡ **Batch Processing (Many Images)**
1. **Ollama**: `moondream:latest` (fastest)
2. **Claude**: `claude-3-5-haiku-20241022` (fast + quality, ~$0.80-4/1000 images)
3. **Claude**: `claude-3-haiku-20240307` (ultra-cheap, ~$0.25-1.25/1000 images)
4. **HF**: `microsoft/git-base-coco` (basic captions only)
5. **Ollama**: `llava:latest` (fast + quality)

### 🎨 **Creative/Artistic Descriptions**
1. **Claude**: `claude-sonnet-4-5-20250929` (Claude 4.5 - highest intelligence)
2. **OpenAI**: `gpt-4o` (excellent creativity)
3. **Claude**: `claude-3-7-sonnet-20250219` (extended thinking for complex analysis)
4. **Ollama**: `llava-llama3:latest` (great free option)
5. **HF**: `Salesforce/blip2-flan-t5-xl` (good instruction following)

### 💾 **Limited Resources (RAM/Storage)**
1. **Ollama**: `moondream:latest` (1.7GB)
2. **HF**: `microsoft/git-base-coco` (1GB)
3. **Ollama**: `gemma2:latest` (2.9GB)

### 🌍 **Offline/Air-gapped Systems**
- **Any Ollama or Hugging Face model** (all work offline once downloaded)
- **Not OpenAI** (requires internet connection)

---

## Performance Tips

### 🚀 **Speed Optimization**
- Use **Ollama models** for fastest processing
- **moondream** is fastest overall
- **git-base** is fastest for basic captions
- Close other applications to free up RAM/VRAM

### 💾 **Resource Management**
- **8GB RAM**: Stick to smaller models (moondream, git-base, blip2-opt)
- **16GB+ RAM**: Any model will work
- **GPU**: Dramatically speeds up Hugging Face models
- **CPU only**: Ollama models often better optimized

### 💿 **Storage Considerations**
- **All models combined**: ~100GB+ storage needed
- **Start small**: Download 2-3 models initially
- **Pre-download**: Use download scripts for Hugging Face models
- **Cache location**: 
  - Ollama: `~/.ollama/models/`
  - HF: `~/.cache/huggingface/hub/`

### 🔄 **Model Switching**
- **No restart needed**: Switch between any downloaded models instantly
- **Memory**: Previous model unloads automatically
- **Ollama**: Models stay loaded in Ollama service (faster switching)
- **HF**: Models reload each time (slower but more memory-efficient)

---

## Troubleshooting

### ❌ **Model Not Appearing**
- **Ollama**: Run `ollama list` to verify model is downloaded
- **HF**: Restart app after downloading new models
- **OpenAI**: Check API key is set correctly

### 🐌 **Slow Performance**
- Try smaller models (moondream, git-base)
- Close other applications
- Use Ollama models (often more optimized)
- Check if GPU acceleration is working

### 💥 **Out of Memory Errors**
- Use smaller models
- Close other applications
- For HF models: try CPU-only mode
- Restart the application

### 🌐 **Network Issues**
- **Pre-download HF models**: Use `python download_hf_models.py`
- **Ollama models**: Use `ollama pull model_name`
- **OpenAI**: Check internet connection and API key

### 🚨 **Performance Reality Check**
**Don't believe all marketing claims!** Our real-world testing found:
- `blip2-opt-2.7b` (5GB): Disappointing quality despite size - gave "A train is seen at a station" for detailed narrative prompt
- `git-base-coco` (1GB): Often performs as well as much larger models for basic descriptions
- Size ≠ Quality: Bigger models don't always give better descriptions
- Download time matters: 5GB models may not justify the 30+ minute wait vs 1GB alternatives
- **Recommendation**: Start with `git-base-coco` or `moondream` before downloading huge models

---

## Future Model Support

The toolkit is designed to easily support new models as they become available:

- **Ollama**: New models appear automatically when available in Ollama
- **Hugging Face**: New vision models can be added to the provider
- **OpenAI**: New models can be added as OpenAI releases them

Stay tuned for updates that add support for new vision models and providers!

---

## Quick Reference Chart

| Model | Provider | Size | Speed | Quality | Prompts | Best For |
|-------|----------|------|-------|---------|---------|----------|
| moondream | Ollama | 1.7GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Beginners |
| git-base | HF | 1GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | Quick captions |
| llava-llama3 | Ollama | 4.7GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | General use |
| blip2-opt | HF | 5GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Balanced |
| llama3.2-vision | Ollama | 7.9GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Best free |
| gpt-4o | OpenAI | Cloud | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Best overall |

---

*Last updated: September 2025 - Model landscape changes rapidly, check for updates!*