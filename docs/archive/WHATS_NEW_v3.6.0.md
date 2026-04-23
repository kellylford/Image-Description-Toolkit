# What's New in v3.6.0

**Release Date:** December 4, 2025  
**Previous Version:** v3.5.0  
**Status:** Stable Release

---

## 🎯 Major Features

### 1. **HuggingFace Provider** 🤖
**Local AI-powered image descriptions with Florence-2 vision models**

A new provider that enables completely local image descriptions using Microsoft's Florence-2 vision models. Run AI vision models on your own hardware with zero API costs and no internet connection required (after initial model download).

#### Key Features
- **Zero Cost**: No API keys, no cloud costs
- **Privacy**: All processing happens locally on your hardware
- **Self-Contained**: No need to install Ollama or any external AI servers - everything is included in IDT
- **Three Detail Levels**: Simple, detailed, and narrative descriptions
- **Two Model Sizes**: 
  - Florence-2-base (230MB, faster)
  - Florence-2-large (700MB, better quality)

#### CLI Usage
```bash
# Basic usage with HuggingFace provider
idt workflow --provider huggingface --model microsoft/Florence-2-base input_folder/

# With specific prompt style
idt workflow --provider huggingface --model microsoft/Florence-2-large \
  --prompt-style narrative images/

# Single image
idt describe --provider huggingface --model microsoft/Florence-2-base photo.jpg
```

#### GUI Usage
1. Open ImageDescriber application
2. Select **Provider**: `HuggingFace`
3. Select **Model**: `microsoft/Florence-2-base` or `microsoft/Florence-2-large`
4. Select **Prompt Style**: `simple`, `detailed`, or `narrative`
5. Process images normally

#### Model Comparison

| Model | Size | Quality | Best For |
|-------|------|---------|----------|
| **Florence-2-base** | 230MB | Good | Testing, bulk processing |
| **Florence-2-large** | 700MB | Better | Final production, quality-critical |

**Documentation**: See [HUGGINGFACE_PROVIDER_GUIDE.md](HUGGINGFACE_PROVIDER_GUIDE.md) for complete guide

---

### 2. **Redescribe Feature** 🔄
**Re-process existing workflows with different AI models and prompts**

Compare multiple AI models and prompts on identical images by reusing existing workflow outputs. This enables efficient model comparison without re-extracting video frames or re-converting images.

#### Key Features
- **Efficient Reuse**: Reuses extracted video frames and converted images from existing workflows
- **Model Comparison**: Test Ollama, OpenAI, Claude, and HuggingFace on the same images
- **Prompt Testing**: Compare different prompt styles with the same model
- **Workflow Metadata**: Tracks original settings and changes for traceability

#### CLI Usage
```bash
# Redescribe an existing workflow with a different provider
idt workflow --redescribe wf_photos_ollama_llava_narrative_20251204_100000 \
  --provider huggingface --model microsoft/Florence-2-base

# Compare prompt styles with the same model
idt workflow --redescribe wf_photos_openai_gpt4o_detailed_20251204_120000 \
  --provider openai --model gpt-4o --prompt-style narrative

# Test different models side-by-side
idt workflow --redescribe wf_photos_claude_sonnet45_20251204_140000 \
  --provider ollama --model llava:13b
```

#### Benefits
- **Save Time**: Skip video extraction and image conversion steps
- **Save Money**: Avoid re-processing with expensive cloud APIs
- **Fair Comparison**: Identical input images ensure valid model comparisons

---

## 🔧 Improvements & Enhancements

### Provider Configuration
- **Unified provider system**: HuggingFace provider integrated into existing provider framework
- **Prompt style support**: Florence-2 task mapping for simple, technical, detailed, and narrative styles
- **Model registry**: Florence-2 models properly registered with metadata and capabilities

### Documentation Updates
- **HUGGINGFACE_PROVIDER_GUIDE.md**: Comprehensive guide for Florence-2 models
  - Usage examples for CLI, GUI, and Python API
  - Model comparison and performance benchmarks
  - Troubleshooting and technical details
- **Updated guides**: All provider documentation updated to include HuggingFace

---

## 📋 Files Added/Changed

### New Files
- `docs/HUGGINGFACE_PROVIDER_GUIDE.md` - Complete user guide for HuggingFace provider
- `docs/WHATS_NEW_v3.6.0.md` - This file

### Core Provider Files
- `imagedescriber/ai_providers.py` - HuggingFaceProvider class implementation
- `models/provider_configs.py` - HuggingFace provider configuration
- `models/model_options.py` - Model-specific options
- `models/manage_models.py` - Florence-2 model metadata

### Script Files
- `scripts/image_describer.py` - HuggingFace provider support
- `scripts/workflow.py` - Provider choices updated
- `scripts/guided_workflow.py` - Interactive prompts for HuggingFace
- `scripts/list_results.py` - Provider detection
- `models/check_models.py` - Dependency checking

---

## 🚀 Getting Started

### Installation
Image Description Toolkit v3.6.0 includes all necessary dependencies in `requirements.txt`. No additional installation required.

### Try HuggingFace Provider
1. Launch ImageDescriber or use the CLI
2. Select **HuggingFace** as the provider
3. Choose a Florence-2 model (base or large)
4. Process your images locally with zero API costs

### When to Use HuggingFace
- **Privacy-critical projects**: Keep all data on your hardware
- **Cost-sensitive workflows**: No per-image API fees
- **Offline environments**: Works without internet (after initial download)
- **No external dependencies**: Don't want to install Ollama or other AI servers
- **Testing and experimentation**: Free unlimited usage

### When to Use Redescribe
- **Model comparison**: Test which AI gives the best results for your images
- **Prompt optimization**: Find the best prompt style for your use case
- **Cost optimization**: Test expensive models on a subset, then apply to full workflow
- **Quality improvement**: Re-process old workflows with newer, better models

---

## 📖 Documentation

- **HuggingFace Provider Guide**: [docs/HUGGINGFACE_PROVIDER_GUIDE.md](HUGGINGFACE_PROVIDER_GUIDE.md)
- **User Guide**: [docs/USER_GUIDE.md](USER_GUIDE.md)
- **CLI Reference**: [docs/CLI_REFERENCE.md](CLI_REFERENCE.md)

---

---

## Attribution

**Florence-2 Models**: Created by Microsoft Corporation, licensed under MIT License. Available on [HuggingFace Model Hub](https://huggingface.co/microsoft/Florence-2-base).

**Citation**:
```bibtex
@article{xiao2023florence,
  title={Florence-2: Advancing a unified representation for a variety of vision tasks},
  author={Xiao, Bin and Wu, Haiping and Xu, Weijian and Dai, Xiyang and Hu, Houdong and Lu, Yumao and Zeng, Michael and Liu, Ce and Yuan, Lu},
  journal={arXiv preprint arXiv:2311.06242},
  year={2023}
}
```

---

**Previous Release**: [What's New in v3.5.0](WHATS_NEW_v3.5.0.md)
