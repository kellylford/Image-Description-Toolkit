# Image Description Toolkit

AI-powered batch image description tool supporting multiple vision models (Ollama, OpenAI GPT-4o, Claude, HuggingFace Florence-2).

## Quick Start

### Installation

Download the latest installer from the [releases](https://github.com/kellylford/Image-Description-Toolkit/releases) page:

**`ImageDescriptionToolkit_Setup_v4.1.0.exe`** (Windows) or **`IDT-4.1.0.pkg`** / **`IDT-4.1.0.dmg`** (macOS)

Run the installer - it includes all five applications (IDT CLI, Viewer, ImageDescriber, PromptEditor, IDTConfigure) and documentation.

**Latest Release (v4.1.0):** wxPython migration complete with improved accessibility, 31+ bug fixes, and comprehensive testing.

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

### User Guides
- **[What's New in v4.1.0](docs/WHATS_NEW_v4.1.0.md)** - wxPython migration, accessibility, code consolidation
- **[User Guide](docs/USER_GUIDE.md)** - Complete usage instructions (Windows)
- **[macOS User Guide](docs/MACOS_USER_GUIDE.md)** - macOS installation and usage
- **[CLI Reference](docs/CLI_REFERENCE.md)** - All commands and options

### Configuration & Setup
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)** - Setup and customization
- **[HuggingFace Provider Guide](docs/HUGGINGFACE_PROVIDER_GUIDE.md)** - Florence-2 local models

### Developer Documentation
- **[Build Guide (Windows)](BuildAndRelease/README.md)** - Windows build instructions
- **[Build Guide (macOS)](docs/BUILD_MACOS.md)** - macOS build instructions
- **[Changelog](CHANGELOG.md)** - Version history

## Requirements

### Windows
- **Windows 10/11** (AMD64 or ARM64)
- **Built Executable**: No Python required - download installer from releases
- **AI Provider** (choose one or more):
  - [Ollama](https://ollama.com) (free, runs locally)
  - [OpenAI API](https://platform.openai.com/api-keys) (GPT-4o, paid)
  - [Claude API](https://console.anthropic.com) (paid)
  - HuggingFace Florence-2 (free, local, no API needed)

### macOS
- **macOS 10.13+** (High Sierra or later)
- **Python 3.8+** (system Python or Homebrew)
- **Installation**: Download .pkg installer or .dmg disk image from releases
- **Build from Source**: See [macOS Build Guide](docs/BUILD_MACOS.md)
- **AI Providers**: Same as Windows (Ollama, OpenAI, Claude, HuggingFace)

**macOS Quick Start:**
```bash
# Install via Homebrew (if building from source)
brew install python@3

# Or download pre-built installer from releases
# Double-click IDT-{version}.pkg or IDT-{version}.dmg
```

### Development (All Platforms)
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
