# Image Description Toolkit v3.6.0

**Release Date:** December 4, 2025

## 🎯 Major Features

### HuggingFace Provider with Florence-2 Models 🤖

Local AI-powered image descriptions using Microsoft's Florence-2 vision models. Run entirely on your hardware with **zero API costs** and **no internet required** (after initial model download).

**Key Features:**
- ✅ **Zero Cost** - No API keys, no cloud costs
- ✅ **Privacy** - All processing happens locally
- ✅ **Self-Contained** - No Ollama or external AI servers needed
- ✅ **Three Detail Levels** - Simple, detailed, narrative descriptions
- ✅ **Two Model Sizes** - Base (230MB, faster) and Large (700MB, better quality)

**Quick Start:**
```bash
# Process images locally with Florence-2
idt workflow --provider huggingface --model microsoft/Florence-2-base images/

# GUI: Open ImageDescriber → Select Provider: HuggingFace → Choose model → Process
```

📖 **Full Guide:** [docs/HUGGINGFACE_PROVIDER_GUIDE.md](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/HUGGINGFACE_PROVIDER_GUIDE.md)

---

### Redescribe Feature 🔄

Re-process existing workflows with different AI models and prompts. Compare models side-by-side on identical images without re-extracting frames or re-converting files.

**Benefits:**
- ⚡ **Save Time** - Reuses extracted frames and converted images
- 💰 **Save Money** - Avoid re-processing with expensive cloud APIs
- 🎯 **Fair Comparison** - Identical inputs ensure valid model comparisons

**Example:**
```bash
# Test different models on the same images
idt workflow --redescribe wf_photos_ollama_llava --provider huggingface --model microsoft/Florence-2-base
idt workflow --redescribe wf_photos_ollama_llava --provider openai --model gpt-4o
idt workflow --redescribe wf_photos_ollama_llava --provider claude --model claude-sonnet-4
```

---

## 📦 Installation

### Windows Installer (Recommended)

Download and run the installer:

**[ImageDescriptionToolkit_Setup_v3.6.0.exe](https://github.com/kellylford/Image-Description-Toolkit/releases/download/v3.6.0/ImageDescriptionToolkit_Setup_v3.6.0.exe)**

Includes all five applications:
- **idt.exe** - CLI toolkit
- **viewer.exe** - Results browser
- **imagedescriber.exe** - Batch processing GUI
- **prompteditor.exe** - Prompt template editor
- **idtconfigure.exe** - Configuration manager

---

## 🔧 Requirements

- **Windows 10/11** (AMD64 or ARM64)
- **AI Provider** (choose one or more):
  - **HuggingFace** (local, free) - NEW in v3.6.0
  - **Ollama** (local, free)
  - **OpenAI API** (requires API key)
  - **Anthropic Claude** (requires API key)

---

## 📖 Documentation

- **What's New:** [docs/WHATS_NEW_v3.6.0.md](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/WHATS_NEW_v3.6.0.md)
- **HuggingFace Provider Guide:** [docs/HUGGINGFACE_PROVIDER_GUIDE.md](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/HUGGINGFACE_PROVIDER_GUIDE.md)
- **User Guide:** [docs/USER_GUIDE.md](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/USER_GUIDE.md)
- **CLI Reference:** [docs/CLI_REFERENCE.md](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/CLI_REFERENCE.md)
- **Changelog:** [CHANGELOG.md](https://github.com/kellylford/Image-Description-Toolkit/blob/main/CHANGELOG.md)

---

## 🙏 Attribution

**Florence-2 Models**: Created by Microsoft Corporation, licensed under MIT License.

**Citation:**
```bibtex
@article{xiao2023florence,
  title={Florence-2: Advancing a unified representation for a variety of vision tasks},
  author={Xiao, Bin and Wu, Haiping and Xu, Weijian and Dai, Xiyang and Hu, Houdong and Lu, Yumao and Zeng, Michael and Liu, Ce and Yuan, Lu},
  journal={arXiv preprint arXiv:2311.06242},
  year={2023}
}
```

**Research Paper:** [Florence-2: Advancing a Unified Representation for a Variety of Vision Tasks](https://arxiv.org/abs/2311.06242)

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Full Changelog:** [v3.5.0...v3.6.0](https://github.com/kellylford/Image-Description-Toolkit/compare/v3.5.0...v3.6.0)
