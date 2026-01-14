# Documentation Index - v4.1.0

**Last Updated:** January 14, 2026 | **Version:** 4.1.0

---

## 📖 User Documentation

### Getting Started
- **[README.md](README.md)** - Project overview, installation, quick start
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user guide for all applications
- **[MACOS_USER_GUIDE.md](MACOS_USER_GUIDE.md)** - macOS-specific user guide
- **[WEB_DOWNLOAD_GUIDE.md](WEB_DOWNLOAD_GUIDE.md)** - Downloading models and resources

### Configuration & Setup
- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Configuration file reference and setup
- **[WINDOWS_SETUP.md](../WINDOWS_SETUP.md)** - Windows installation and setup
- **[MACOS_SETUP.md](../MACOS_SETUP.md)** - macOS installation and setup

### Feature Guides
- **[PROMPT_WRITING_GUIDE.md](PROMPT_WRITING_GUIDE.md)** - Writing effective prompts for AI descriptions
- **[HUGGINGFACE_PROVIDER_GUIDE.md](HUGGINGFACE_PROVIDER_GUIDE.md)** - Using HuggingFace models
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - Complete command-line interface reference

### Release Information
- **[WHATS_NEW_v4.1.0.md](WHATS_NEW_v4.1.0.md)** - What's new in v4.1.0
- **[WHATS_NEW_v3.6.0.md](WHATS_NEW_v3.6.0.md)** - What's new in v3.6.0
- **[WHATS_NEW_v3.5.0.md](WHATS_NEW_v3.5.0.md)** - What's new in v3.5.0

---

## 👨‍💻 Developer Documentation

### Architecture & Design
- **[ARCHITECTURE_SEARCH_RESULTS.md](ARCHITECTURE_SEARCH_RESULTS.md)** - Codebase architecture overview
- **[AI_ONBOARDING.md](AI_ONBOARDING.md)** - AI agent onboarding and project context

### Build & Deployment
- **[BUILD_MACOS.md](BUILD_MACOS.md)** - macOS build process
- **[BuildAndRelease/BUILD_SYSTEM_REFERENCE.md](../BuildAndRelease/BUILD_SYSTEM_REFERENCE.md)** - Complete build system reference
- **[BuildAndRelease/README.md](../BuildAndRelease/README.md)** - Build and release overview

### Code Quality & Testing
- **[ACCESSIBLE_LISTBOX_INTEGRATION_GUIDE.md](ACCESSIBLE_LISTBOX_INTEGRATION_GUIDE.md)** - Accessible UI component implementation
- **[code_audit/](code_audit/)** - Code audit reports and analysis

### Work Tracking
- **[WorkTracking/](WorkTracking/)** - Session summaries and work progress tracking

---

## 📦 Project Files

### Configuration
- **[pyproject.toml](../pyproject.toml)** - Project metadata and dependencies
- **[requirements.txt](../requirements.txt)** - Python package requirements
- **[VERSION](../VERSION)** - Current version number

### Version Control
- **[CHANGELOG.md](../CHANGELOG.md)** - Complete change history
- **[BRANCH_INFO.md](../BRANCH_INFO.md)** - Git branch information
- **[LICENSE](../LICENSE)** - Project license

### Release Notes
- **[RELEASE_NOTES_v4.1.0.md](../RELEASE_NOTES_v4.1.0.md)** - v4.1.0 release notes
- **[RELEASES_README.md](../RELEASES_README.md)** - Release process documentation

---

## 🗂️ Directory Structure

### Source Code
```
scripts/              - Core workflow and image processing scripts
imagedescriber/       - GUI batch processor (wxPython)
viewer/              - Workflow results browser (wxPython)
prompt_editor/       - Prompt template editor (wxPython)
idtconfigure/        - Configuration manager (wxPython)
idt/                 - CLI dispatcher
shared/              - Shared utilities across all applications
analysis/            - Analysis and reporting tools
models/              - AI model provider implementations
MetaData/            - EXIF and metadata handling
```

### Documentation
```
docs/                - User and developer documentation
docs/archive/        - Legacy documentation
docs/code_audit/     - Code analysis reports
docs/packaging/      - Packaging and distribution info
docs/WorkTracking/   - Session summaries and progress
```

### Testing & Build
```
pytest_tests/        - Unit and integration tests
BuildAndRelease/     - Build scripts and processes
testimages/          - Test images for development
```

---

## 🎯 Quick Reference

### Common Tasks

**Running Workflows:**
```bash
idt workflow --provider ollama --model llava testimages/
```

**Batch Processing:**
```bash
ImageDescriber.exe   # or ./dist/ImageDescriber on macOS
```

**Viewing Results:**
```bash
Viewer.exe          # or ./dist/Viewer on macOS
```

**Configuration:**
```bash
IDTConfigure.exe    # or ./dist/IDTConfigure on macOS
```

**Building from Source:**
```bash
# Windows
BuildAndRelease\WinBuilds\builditall_wx.bat

# macOS
./BuildAndRelease/MacBuilds/builditall_macos.command
```

---

## 📚 By Topic

### AI Providers
- Configuration: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- HuggingFace Setup: [HUGGINGFACE_PROVIDER_GUIDE.md](HUGGINGFACE_PROVIDER_GUIDE.md)
- API Keys: [USER_GUIDE.md](USER_GUIDE.md#api-keys-and-authentication)
- Model Selection: [WHATS_NEW_v4.1.0.md](WHATS_NEW_v4.1.0.md#supported-providers)

### GUI Applications
- ImageDescriber: [USER_GUIDE.md](USER_GUIDE.md#imagedescriber-app)
- Viewer: [USER_GUIDE.md](USER_GUIDE.md#viewer-app)
- PromptEditor: [USER_GUIDE.md](USER_GUIDE.md#prompt-editor)
- IDTConfigure: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

### Command-Line Interface
- Full Reference: [CLI_REFERENCE.md](CLI_REFERENCE.md)
- Workflows: [CLI_REFERENCE.md](CLI_REFERENCE.md#workflow-command)
- Analysis: [CLI_REFERENCE.md](CLI_REFERENCE.md#analysis-commands)

### Development
- Architecture: [ARCHITECTURE_SEARCH_RESULTS.md](ARCHITECTURE_SEARCH_RESULTS.md)
- Building: [BUILD_MACOS.md](BUILD_MACOS.md) or [WINDOWS_SETUP.md](../WINDOWS_SETUP.md)
- Testing: [pytest_tests/](../pytest_tests/)
- Contributing: See [README.md](README.md#contributing)

---

## 🔍 Searching Documentation

### By Feature
- **Image Processing**: [WHATS_NEW_v4.1.0.md](WHATS_NEW_v4.1.0.md)
- **Video to Images**: [CLI_REFERENCE.md](CLI_REFERENCE.md)
- **Batch Processing**: [USER_GUIDE.md](USER_GUIDE.md#batch-processing)
- **Prompt Customization**: [PROMPT_WRITING_GUIDE.md](PROMPT_WRITING_GUIDE.md)

### By Problem
- **Setup Issues**: Start with [WINDOWS_SETUP.md](../WINDOWS_SETUP.md) or [MACOS_SETUP.md](../MACOS_SETUP.md)
- **Configuration**: [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
- **AI Provider Issues**: [HUGGINGFACE_PROVIDER_GUIDE.md](HUGGINGFACE_PROVIDER_GUIDE.md)
- **Build Failures**: [BuildAndRelease/BUILD_SYSTEM_REFERENCE.md](../BuildAndRelease/BUILD_SYSTEM_REFERENCE.md)

---

## 📝 Documentation Changes in v4.1.0

### Updated
- **README.md** - Version updated to v4.1.0, installer references updated
- **CHANGELOG.md** - v4.1.0 entry added with comprehensive change list
- **USER_GUIDE.md** - wxPython GUI updates (in progress)
- **CONFIGURATION_GUIDE.md** - Frozen mode notes added (in progress)

### New
- **WHATS_NEW_v4.1.0.md** - Comprehensive v4.1.0 release documentation
- **RELEASE_NOTES_v4.1.0.md** - Detailed release notes with installation guide

### Archived
- Legacy PyQt6 documentation moved to `docs/archive/`
- See [Legacy Documentation](#-legacy-documentation) below

---

## 🏛️ Legacy Documentation

Legacy documentation from pre-wxPython versions is archived in `docs/archive/`:
- Original PyQt6 architecture documentation
- Previous version release notes and change logs
- Historical implementation notes
- Deprecated feature documentation

**Note:** These documents are for historical reference only. Use current documentation for development and deployment.

---

## 📞 Getting Help

1. **Check the USER_GUIDE.md** - Most questions answered there
2. **Review relevant How-To guides** - Listed by topic above
3. **Check troubleshooting in CLI_REFERENCE.md** - Common issues and solutions
4. **Browse WHATS_NEW files** - Recent changes and improvements
5. **Report issues on GitHub** - If you find a problem

---

## ✨ Version Information

**Current Release:** v4.1.0 (January 14, 2026)
**Latest Documentation:** Updated for v4.1.0

For version history, see [CHANGELOG.md](../CHANGELOG.md)

