# Documentation Index

This directory contains all documentation for the Image Description Toolkit.

## 📚 Table of Contents

### Getting Started
- [Quick Start Guide](../QUICK_START.md) - Start here!
- [README](../README.md) - Project overview
- [CHANGELOG](../CHANGELOG.md) - Version history

---

### 🔧 User Guides

#### Core Applications
- [ImageDescriber GUI](image_describer_README.md) - Main GUI application
- [Workflow System](WORKFLOW_README.md) - Batch processing workflow
- [Viewer Application](VIEWER_README.md) - Browse results
- [Prompt Editor](PROMPT_EDITOR_README.md) - Edit prompt styles

#### Utility Scripts
- [Video Frame Extractor](video_frame_extractor_README.md) - Extract frames from videos
- [Convert Image](ConvertImage_README.md) - HEIC to JPG conversion
- [Descriptions to HTML](descriptions_to_html_README.md) - Generate galleries

---

### 🤖 AI Provider Guides

#### Provider Setup & Usage
- [Ollama Provider](OLLAMA_GUIDE.md) - Local AI (FREE, most popular)
- [ONNX Provider](ONNX_GUIDE.md) - Hardware-accelerated local AI (FREE)
- [OpenAI Provider](OPENAI_SETUP_GUIDE.md) - GPT-4o cloud AI (PAID)
- [HuggingFace Provider](HUGGINGFACE_GUIDE.md) - Transformers local AI (FREE)
- [Copilot+ PC Provider](COPILOT_PC_PROVIDER_GUIDE.md) - NPU-accelerated (FREE, requires hardware)
- [GroundingDINO Provider](GROUNDINGDINO_GUIDE.md) - Zero-shot object detection (FREE)

#### Provider Comparisons
- [ONNX vs Copilot+ Providers](ONNX_VS_COPILOT_PROVIDERS.md) - Hardware acceleration comparison
- [Model Selection Guide](MODEL_SELECTION_GUIDE.md) - Choosing the right model

---

### 🎯 Batch File Examples
- **[Batch Files Guide](BATCH_FILES_GUIDE.md)** - Complete workflow examples
  - `run_ollama.bat` - Ollama local AI workflow
  - `run_onnx.bat` - ONNX hardware-accelerated workflow
  - `run_openai.bat` - OpenAI cloud workflow
  - `run_huggingface.bat` - HuggingFace transformers workflow
  - `run_complete_workflow.bat` - Full video→gallery pipeline
- [Batch Files Rewrite Summary](BATCH_FILES_REWRITE_SUMMARY.md) - What was fixed and why

---

### 🛠️ Configuration & Advanced

#### Configuration
- [Configuration Guide](CONFIGURATION.md) - All configuration options
- [Workflow Examples](WORKFLOW_EXAMPLES.md) - Advanced workflow patterns
- [Model Management](MODEL_MANAGEMENT_QUICKSTART.md) - Managing AI models

#### Technical Implementation
- [Refactoring Summary](REFACTORING_COMPLETE_SUMMARY.md) - Architecture improvements
- [Logging Improvements](LOGGING_IMPROVEMENTS.md) - Provider logging updates
- [Phase 3 Complete](PHASE_3_COMPLETE.md) - CLI provider integration
- [Phase 4 Complete](PHASE_4_COMPLETE.md) - Model manager updates  
- [Phase 5 Complete](PHASE_5_COMPLETE.md) - Dynamic UI implementation

#### Recent Enhancements
- **[Chronological Ordering](CHRONOLOGICAL_IMPLEMENTATION_SUMMARY.md)** - Quick reference for Oct 4 implementation
  - Video frames show source video name
  - Descriptions appear in chronological order
  - Frames inherit video timestamps
- [Full Proposal](CHRONOLOGICAL_ORDERING_PROPOSAL.md) - Complete analysis and implementation details (40KB)
- [Quick Reference](CHRONOLOGICAL_PHASE1_QUICKREF.md) - Copy-paste code snippets

---

### 🐛 Troubleshooting & Testing
- [Testing Guide](TESTING_README.md) - How to test components
- [Recent Fixes](FIXES_2025_10_02.md) - Bug fixes and improvements
- [Enhancement Log](ENHANCEMENTS_2025_10_01.md) - Feature additions

---

## 📖 Documentation Organization

### By Use Case

**"I want to describe images quickly"**
→ Read: [Quick Start](../QUICK_START.md) + [Batch Files Guide](BATCH_FILES_GUIDE.md)

**"I want to set up the GUI app"**
→ Read: [ImageDescriber GUI](image_describer_README.md) + [Ollama Guide](OLLAMA_GUIDE.md)

**"I want the best quality descriptions"**
→ Read: [OpenAI Setup](OPENAI_SETUP_GUIDE.md) or [Model Selection Guide](MODEL_SELECTION_GUIDE.md)

**"I want free/local processing"**
→ Read: [Ollama Guide](OLLAMA_GUIDE.md) or [ONNX Guide](ONNX_GUIDE.md)

**"I have videos to process"**
→ Read: [Video Frame Extractor](video_frame_extractor_README.md) + [Workflow Guide](WORKFLOW_README.md)

**"I want to create HTML galleries"**
→ Read: [Workflow Guide](WORKFLOW_README.md) + [Batch Files Guide](BATCH_FILES_GUIDE.md)

---

## 🗂️ Documentation Types

### User-Facing Guides
Files ending in `_GUIDE.md` or `_README.md` are complete, user-friendly guides:
- Installation instructions
- Usage examples
- Troubleshooting tips
- Screenshots/examples

### Technical Documentation
Files with `IMPLEMENTATION`, `SUMMARY`, or `COMPLETE` are technical:
- Architecture decisions
- Code changes
- Development history
- Testing results

### Quick References
Files with `QUICKSTART` or `SETUP` are condensed guides:
- Fast setup instructions
- Essential commands only
- Minimal explanation

---

## 📝 Contributing to Documentation

When adding new documentation:
1. **User guides** → Use `_GUIDE.md` or `_README.md` suffix
2. **Technical docs** → Use descriptive names with context
3. **Update this index** → Add link in appropriate section
4. **Keep it current** → Update existing docs when features change

---

## 🗑️ Deprecated / Archived

The following docs are outdated or superseded:
- Old batch file guides (replaced by BATCH_FILES_GUIDE.md)
- Phase 1-2 planning docs (work completed)
- Pre-refactoring implementation logs

See `archive/` subdirectory for historical documentation.

---

## Last Updated
October 4, 2025
