# Image Description Toolkit v3.0.1

**Release Date:** October 25, 2025

A maintenance release focused on installer improvements and bug fixes to enhance the out-of-box user experience.

## 🎯 Installer Improvements

### IDT_CONFIG_DIR Environment Variable
- Installer now sets `IDT_CONFIG_DIR` environment variable pointing to `{InstallDir}\scripts`
- Allows `idt` command to find configuration files from any directory
- No more "config file not found" errors when running from different locations
- Environment variable automatically removed during uninstall

### Enhanced Desktop Integration
- Added desktop shortcut for IDT CLI tool
- Post-install now launches CLI by default (previously ImageDescriber)
- Both ImageDescriber and CLI shortcuts available on desktop for quick access

## 🐛 Bug Fixes

### Guided Workflow
- **Fixed variable scope error** with `sys` module in guided_workflow
- **Fixed variable shadowing bug** with `default_style` in timeout handling
- Improved error handling and user feedback

### Stats Analysis
- **Fixed stats analysis for resumed workflows** - now correctly counts actual descriptions
- Better handling of workflow directories with partial results
- Improved accuracy in completion percentage calculations

## 📚 Documentation Updates
- Added Windows installer build scripts and comprehensive guide
- Windows install best practices proposal for future improvements
- Clarified that timeout values are user-configurable (not hardcoded)
- Documented guideme workflow flag pass-through feature

## ✨ Feature Enhancement
- Guideme now passes through workflow flags to the workflow command
- Supports all standard workflow options (--model, --output-dir, etc.)

## 📦 What's Included

**Four Complete Applications:**
- **📋 CLI Toolkit (`idt.exe`)** - Advanced batch processing and automation
- **🖼️ GUI ImageDescriber (`imagedescriber.exe`)** - Visual interface for individual images  
- **📝 Prompt Editor (`prompt_editor.exe`)** - Design and test custom prompts
- **📊 Results Viewer (`viewer.exe`)** - Browse results and real-time monitoring

## � Installation

### Windows Installer (Recommended)
1. Download `ImageDescriptionToolkit_Setup_v3.0.1.exe`
2. Run the installer
3. Desktop shortcuts created automatically
4. `IDT_CONFIG_DIR` environment variable configured

### Upgrading from v3.0.0
- Simply run the new installer - it will update your existing installation
- All existing workflows, configurations, and data are preserved

## 🆕 New User? Start Here
1. **Run the installer** - `ImageDescriptionToolkit_Setup_v3.0.1.exe`
2. **Try GUI ImageDescriber** - Perfect for learning
3. **Use CLI wizard** - Batch processing: `idt guideme`  
4. **Design prompts** - Custom descriptions: `prompt_editor.exe`
5. **Browse results** - View outputs: `viewer.exe`

## 📚 Documentation
- **Complete User Guide:** See `docs/USER_GUIDE.md` after installation
- **Quick Start:** Run `idt guideme` for interactive setup
- **Full Changelog:** https://github.com/kellylford/Image-Description-Toolkit/compare/v3.0.0...v3.0.1

## 🔧 Technical Changes
- **12 commits** since v3.0.0 including installer improvements, bug fixes, and documentation updates
- All existing workflows and configurations remain fully compatible
- No breaking changes

---

**System Requirements:** Windows 10+  
**Optional:** Ollama for local AI models, API keys for Claude/OpenAI  
**Support:** [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)