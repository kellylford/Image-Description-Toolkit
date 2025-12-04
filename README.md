# Image Description Toolkit

AI-powered batch image description tool supporting multiple vision models (Ollama, OpenAI GPT-4o, Claude, HuggingFace Florence-2).

## Quick Start

### Installation

Download the latest installer from the [releases](https://github.com/kellylford/Image-Description-Toolkit/releases) page:

**`ImageDescriptionToolkit_Setup_v3.6.0.exe`**

Run the installer - it includes all five applications (IDT CLI, Viewer, ImageDescriber, PromptEditor, IDTConfigure) and documentation.

### Basic Usage

```bash
# Process images with AI descriptions
idt workflow --provider huggingface --model microsoft/Florence-2-base images/

# View results in GUI
viewer.exe

# Batch processing with GUI
imagedescriber.exe
```

## Features

- **Multiple AI Providers**: Ollama (local), OpenAI, Claude, HuggingFace Florence-2
- **Video Frame Extraction**: Extract and describe frames from videos
- **Workflow Management**: Organized results with metadata tracking
- **Re-describe Feature**: Test different models/prompts on same images
- **Analysis Tools**: Compare models, review content, export to CSV/Excel
- **GUI Applications**: Viewer, ImageDescriber, PromptEditor, Configuration Manager

## Documentation

- **[What's New in v3.6.0](docs/WHATS_NEW_v3.6.0.md)** - Latest features (HuggingFace provider, redescribe)
- **[User Guide](docs/USER_GUIDE.md)** - Complete usage instructions
- **[CLI Reference](docs/CLI_REFERENCE.md)** - All commands and options
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)** - Setup and customization
- **[HuggingFace Provider Guide](docs/HUGGINGFACE_PROVIDER_GUIDE.md)** - Florence-2 local models
- **[Changelog](CHANGELOG.md)** - Version history

## Requirements

- **Windows 10/11** (AMD64 or ARM64)
- **Python 3.10+** (for development only, not required for built executables)
- **AI Provider** (choose one or more):
  - Ollama (local, free)
  - OpenAI API key
  - Anthropic Claude API key
  - HuggingFace transformers (local, free)

## Support

- **Issues**: [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
- **Documentation**: See `docs/` directory
- **Repository**: https://github.com/kellylford/Image-Description-Toolkit

## License

MIT License - see [LICENSE](LICENSE) file for details.

### Third-Party Models

- **Florence-2 Models**: Created by Microsoft Corporation, MIT License
- **Citation**: Xiao, Bin, et al. "Florence-2: Advancing a unified representation for a variety of vision tasks." arXiv:2311.06242 (2023)
