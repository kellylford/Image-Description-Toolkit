# Image Description Toolkit

AI-powered batch image description tool supporting multiple vision models (Ollama, OpenAI GPT-4o, Claude).

## Quick Start

### Installation

Download from the [releases](https://github.com/kellylford/Image-Description-Toolkit/releases) page:

| File | Platform |
|---|---|
| **`ImageDescriptionToolkitSetup-4.5.0-windows.exe`** | Windows 10/11, 64-bit |
| **`IDT-4.5.0-macos-arm64.dmg`** | macOS, Apple Silicon |

Either one gives you all the applications:
- **idt** - Command-line interface for batch processing and automation
- **ImageDescriber** - GUI with integrated viewer, prompt editor, and configuration manager
- **IDT Chat** *(Windows)* - An accessible chat client for Ollama, Claude and OpenAI. Not an image tool: it is a general-purpose chat application built for keyboard and screen reader use.

One install covers them all; you never update them separately.

Standalone builds are also published if you want a single tool without an installer:
`idt-4.5.0-windows-x64.exe`, `ImageDescriber-4.5.0-windows-x64.exe`,
`IDTChat-4.5.0-windows-x64.exe`, and `idt-4.5.0-macos-arm64.tar.gz`.
`SHA256SUMS.txt` lets you verify any download.

No Python required. The Windows installer is signed; the macOS build is signed and
notarized.

**Latest Release (v4.5.0):** Unified workspace model, shared engine for CLI and GUI, web image download, video frame extraction, and comprehensive model updates.

### Quick Start

#### GUI (Easiest for Most Users)

1. **Install** Image Description Toolkit from the installer
2. **Launch** `imagedescriber.exe` from the install folder (default: `C:\IDT\`)
3. **Choose** a directory of images (File → Load Directory)
4. **Select** your AI provider, model, and prompt style in the interface
5. **Process** all images (Processing → Process All Undescribed)

Your images will be described automatically! Use Tools → Edit Prompts to customize description styles, or File → Switch to Viewer to browse results.

#### Command Line (For Batch Processing)

1. **Open** a command prompt
2. **Change** to the install directory: `cd C:\IDT`
3. **Run** the interactive guide: `idt guideme`
4. **Answer** the prompts to configure and run your workflow

Results are saved in the `Descriptions/` folder with an HTML viewer.

### Advanced Usage

```bash
# Describe a folder of images
idt describe path/to/images

# Check whether a newer version is available
idt update
```

## Features

- **Two Powerful Applications**: GUI for visual workflow, CLI for automation
- **Multiple AI Providers**: Ollama (local), OpenAI, Claude
- **Batch Processing**: Process directories of images automatically
- **Video Frame Extraction**: Extract and describe frames from videos
- **Integrated Viewer**: Browse and monitor workflows in real-time (built into GUI)
- **Integrated Tools**: Prompt editor and configuration manager built into GUI
- **Workflow Management**: Organized results with metadata tracking
- **Re-describe Feature**: Test different models/prompts on same images
- **Analysis Tools**: Compare models, review content, export to CSV/Excel

## Documentation

### User Guides
- **[Release Notes (v4.5.0)](docs/release-notes-v4.5.0.md)** - What IDT is and what's in the current release
- **[User Guide](docs/USER_GUIDE.md)** - Complete usage instructions, including the full CLI reference
- **[macOS Setup](MACOS_SETUP.md)** - macOS installation and usage

### Configuration & Setup
- **[Configuration Guide](docs/CONFIGURATION_GUIDE.md)** - Setup and customization

### Developer Documentation
- **[Build Guide (Windows)](BuildAndRelease/README.md)** - Windows build instructions
- **[Build Guide (macOS)](BuildAndRelease/MacBuilds/README_MACOS.md)** - macOS build instructions
- **[Changelog](CHANGELOG.md)** - Version history

## Requirements
- **Pre-built Executable**: No Python required - download installer from releases
- **AI Provider** (choose one or more):
  - [Ollama](https://ollama.com) (free, runs locally) - **Recommended for most users**
  - [OpenAI API](https://platform.openai.com/api-keys) (GPT-4o, paid)
  - [Claude API](https://console.anthropic.com) (paid)

### macOS
- **Apple Silicon** — the published build is arm64 only. Intel Macs need to build from source.
- **No Python required** for the pre-built app
- **Installation**: Download `IDT-{version}-macos-arm64.dmg` from releases, open it, and drag ImageDescriber to Applications
- **Build from Source**: See [macOS Build Guide](BuildAndRelease/MacBuilds/README_MACOS.md)
- **AI Providers**: Same as Windows (Ollama, OpenAI, Claude), plus MLX on Apple Silicon

### Development (All Platforms)
- **Python 3.10+** (for development only, not required for built executables)
- **AI Provider** (choose one or more):
  - Ollama (local, free)
  - OpenAI API key
  - Anthropic Claude API key

## Support

- **Issues**: [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)
- **Documentation**: See `docs/` directory
- **Repository**: https://github.com/kellylford/Image-Description-Toolkit

## License

MIT License - see [LICENSE](LICENSE) file for details.
