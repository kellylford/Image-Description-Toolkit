# Branch Information

## This is the Main Branch (formerly ImageDescriber)

**Branch Rename Date:** October 20, 2025

This branch contains the active v2.0 development of the Image Description Toolkit with full GUI and enhanced CLI features.

### Branch History

On October 20, 2025, the repository structure was reorganized:

- **Former `main` branch** → Renamed to `1.0release` (preserves v1.0.0 and v1.1.0-cli)
- **Former `ImageDescriber` branch** → Renamed to `main` (this branch - active development)

### Why the Reorganization?

The original `main` branch contained only the CLI tools from v1.0.0/v1.1.0-cli. Meanwhile, the `ImageDescriber` branch had evolved significantly with 245+ commits containing all the modern features. To align the repository structure with development reality, the branches were reorganized so the default branch reflects the current state of the project.

### What's in This Branch (v2.0)

This branch represents the comprehensive v2.0 release candidate with:

#### Core Applications
- **Unified CLI Dispatcher** (`idt_cli.py`) - Single entry point for all toolkit commands
- **ImageDescriber GUI** - Interactive application for batch image processing with accessibility features
- **PromptEditor GUI** - Visual prompt template editor with live Ollama model discovery
- **Enhanced Viewer** - CLI-enabled viewer with improved functionality

#### CLI Commands
- `idt workflow` - Automated image description workflow
- `idt viewer` - Launch the results viewer
- `idt prompteditor` - Launch the prompt editor
- `idt imagedescriber` - Launch the ImageDescriber GUI
- `idt guideme` - Interactive workflow setup wizard
- `idt analyze` - Model performance analysis tools

#### Major Features Added Since v1.1.0-cli
- Interactive guideme wizard for accessible workflow setup
- Workflow naming and resume functionality
- Model performance analyzer
- GitHub Actions build workflows (Windows AMD64, Linux ARM64)
- Comprehensive batch file modernization
- PyInstaller compatibility for distribution
- Analysis tools for workflow statistics and performance
- Enhanced accessibility (WCAG 2.2 AA compliance)
- Multi-provider support (Ollama, OpenAI, Claude)
- Real-time status logging
- Automatic viewer launch options
- And 245+ more commits of improvements...

### For Stable v1.0 Releases

If you need the original stable CLI-only releases (v1.0.0 or v1.1.0-cli), please use the **1.0release** branch.

### Related Tags

- `v1.0.0` - Points to the original release on the `1.0release` branch
- `v1.1.0-cli` - Points to the head of the `1.0release` branch
- `v2.0.0-likely` - Points to commit `7c39bdc` on this branch (current main)

### Development Status

This branch is **actively maintained** and represents the current state of development. All new features and improvements are committed here.

---

*This branch rename was performed on October 20, 2025, to make the repository's default branch reflect the actual current state of development.*
