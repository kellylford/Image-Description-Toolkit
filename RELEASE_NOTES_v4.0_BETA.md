# Image Description Toolkit v4.0 Beta1

**Major Re-Architecture with Stability, Performance & Enhanced AI Features**

## What's New

### ImageDescriber GUI - Completely Rewritten
- **Rebuilt from scratch** for stability and performance
- Faster startup, smoother performance, responsive UI
- More reliable batch processing with resume capability
- Enhanced error handling and recovery

### Simplified Installation
- **Windows installer now offers automatic Ollama & Moondream installation** as an optional checkbox
- Get started with local AI in one click
- No manual model downloading required for new users

### Batch Processing Improvements
- Process entire directories efficiently without losing state
- Resume interrupted batches without reprocessing
- Real-time progress tracking with accurate completion estimates
- Better handling of large image collections

### AI Chat Integration
- **Interactive chat mode** to ask follow-up questions about images
- Ask for clarification, additional details, or different perspectives
- Switch between AI providers mid-conversation
- Seamless integration with existing description workflows

### Enhanced Metadata & Cost Tracking
- **Token usage reporting** for OpenAI and Claude (see what you're paying)
- More detailed image metadata in descriptions:
  - Photo date and time (from EXIF)
  - GPS coordinates with geocoding support
  - Camera information and settings


### Viewer Mode
- Browse all workflow results in one place
- Real-time monitoring of active processing
- Live updates as batches complete

## Performance & Stability

- Multi-threaded batch processing with worker threads
- Better memory management for large workflows
- Improved error recovery and logging
- Enhanced configuration system with fallback handling

## Under the Hood

- **Migrated from PyQt6 to wxPython** for improved cross-platform compatibility
- Modernized workflow orchestration
- Simplified file structure and cleaner codebase
- Better separation of concerns across modules

---

**Note:** Beta version - we're actively testing and refining. Report issues on [GitHub](https://github.com/kellylford/Image-Description-Toolkit/issues).

## Resources

- [User Guide](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/USER_GUIDE_V4.md) - Complete guide for using IDT and ImageDescriber
- [Known Issues](https://github.com/kellylford/Image-Description-Toolkit/blob/main/docs/KNOWN_ISSUES_V4.md) - Current limitations and workarounds
