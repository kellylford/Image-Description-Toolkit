# Image Description Toolkit v3.0.1 - Performance Optimizations Release

## 🚀 Major Performance Improvements for Ollama Cloud Models

This release delivers **significant performance improvements** for Ollama cloud model processing, reducing typical workflow times from **40 minutes to 15-20 minutes** (60% improvement).

### Key Improvements:
- ⚡ **75% faster error recovery** - Retry delays reduced from 14s to 3.5s total
- ⏱️ **90-second timeout protection** - No more 2+ minute request hangs  
- 🛡️ **Smart request throttling** - Reduces server overload
- 🔧 **Enhanced retry logic** - Better handling of server 500 errors

## 📦 What's Included

**Four Complete Applications:**
- **📋 CLI Toolkit (`idt.exe`)** - Advanced batch processing and automation
- **🖼️ GUI ImageDescriber (`imagedescriber.exe`)** - Visual interface for individual images  
- **📝 Prompt Editor (`prompt_editor.exe`)** - Design and test custom prompts
- **📊 Results Viewer (`viewer.exe`)** - Browse results and real-time monitoring

## 🔧 Fixes
- **Fixed idt2.zip packaging** - Master package now includes all applications correctly
- **Enhanced documentation** - Major User Guide updates featuring GUI applications
- **Improved troubleshooting** - Better guidance for all four applications

## 📥 Installation Options

### Quick Install (Recommended)
1. Download `idt2.zip` (contains everything)  
2. Extract and run `install_idt.bat`
3. Follow setup wizard: `idt guideme`

### Individual Packages
Download all matching v3.0.1 packages:
- `ImageDescriptionToolkit_v3.0.1.zip`
- `imagedescriber_v3.0.1.zip` 
- `prompt_editor_v3.0.1.zip`
- `viewer_v3.0.1.zip`
- `install_idt.bat`

## 🆕 New User? Start Here
1. **Try GUI ImageDescriber** - Perfect for learning: `imagedescriber.exe`
2. **Use CLI wizard** - Batch processing: `idt guideme`  
3. **Design prompts** - Custom descriptions: `prompt_editor.exe`
4. **Browse results** - View outputs: `viewer.exe`

## 📚 Documentation
- **Complete User Guide:** See `docs/USER_GUIDE.md` after installation
- **Quick Start:** Run `idt guideme` for interactive setup
- **Release Notes:** [RELEASE_NOTES_v3.0.1.md](RELEASE_NOTES_v3.0.1.md)

## ⚡ Performance Comparison

| Scenario | v3.0.0 | v3.0.1 | Improvement |
|----------|--------|--------|-------------|
| 25 images, many retries | 40 minutes | 15-20 minutes | **60% faster** |
| Heavy retry scenarios | Multiple 8+ min hangs | 90s max per request | **75% faster recovery** |
| Retry overhead | 14s per failure | 3.5s per failure | **75% reduction** |

## 🔄 Upgrade Notes
- **From v3.0.0:** Direct upgrade, all workflows compatible
- **From v2.x:** Full reinstall recommended  
- **Configuration:** No changes needed, improvements are automatic

---

**System Requirements:** Windows 10+, No Python required  
**Optional:** Ollama for local AI models  
**Support:** [GitHub Issues](https://github.com/kellylford/Image-Description-Toolkit/issues)