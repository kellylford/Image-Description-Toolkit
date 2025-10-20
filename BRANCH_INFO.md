# Branch Information

## This is the 1.0release Branch

**Created:** October 20, 2025

This branch preserves the stable v1.0.0 and v1.1.0-cli releases of the Image Description Toolkit.

### Why This Branch Exists

On October 20, 2025, the repository structure was reorganized to better reflect the current state of development:

- The former `main` branch was renamed to `1.0release` to preserve the stable CLI-only releases
- The `ImageDescriber` branch became the new `main` branch, as it represents the active v2.0 development

### What's in This Branch

This branch contains:
- **v1.0.0 release** (September 2, 2025) - Original stable release with CLI tools and viewer
- **v1.1.0-cli release** (October 15, 2025) - Same as v1.0.0 after ImageDescriber GUI was removed from main

### Key Features

- Complete workflow orchestrator (`workflow.py`)
- Image description generation via Ollama
- Video frame extraction
- Image format conversion (HEIC, etc.)
- HTML report generation
- Qt6 Viewer GUI with redescribe functionality
- Comprehensive documentation and test suite

### For Current Development

**⚠️ This branch is archived for historical reference.**

For active development and the latest features, please use the **main** branch, which contains:
- Unified CLI dispatcher (`idt_cli.py`)
- ImageDescriber GUI for interactive processing
- PromptEditor GUI
- Interactive guideme wizard
- Enhanced viewer with CLI support
- Model performance analyzer
- Workflow naming and resume features
- 245+ commits of improvements over v1.1.0-cli

### Related Tags

- `v1.0.0` - Points to commit `6dd2b5d` on this branch
- `v1.1.0-cli` - Points to commit `460b459` on this branch (HEAD of this branch)
- `v2.0.0-likely` - Points to commit `7c39bdc` on the **main** branch

---

*This branch rename was performed to align the repository structure with the actual development state and make the default branch reflect current work.*
