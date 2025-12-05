# ImageDescriber - User Setup Guide

## 📦 What You Have

Congratulations! You have **ImageDescriber.exe** (or **ImageDescriber_amd64.exe** / **ImageDescriber_arm64.exe**), a standalone executable that includes:

✅ **Python runtime** - No Python installation needed  
✅ **Core application** - Full GUI and workspace management  
✅ **Image loading libraries** - HEIC, PNG, JPG, BMP support  
✅ **Basic image processing** - All image manipulation features  

## 🎯 Quick Start (Minimal Setup)

**Want to start immediately?** You can run ImageDescriber right now with NO additional setup:

1. Double-click **ImageDescriber.exe**
2. Load images into a workspace
3. View and organize your images
4. Add manual descriptions
5. Export to HTML

**That's it!** The core application works out-of-the-box.

---

## 🚀 Enable AI Features (Recommended)

To unlock **AI-powered image descriptions**, you need to set up at least ONE AI provider. Choose based on your needs:

### 🌟 Recommended: Ollama (Local, Free, Private)

**Best for**: Most users, completely free, works offline, privacy-focused

**What it does**: Uses local AI models (like ChatGPT but running on your computer)

**Setup time**: 5-10 minutes

**Steps**:

1. **Download Ollama** from [ollama.ai](https://ollama.ai/download/windows)
   - Size: ~250MB installer
   - Requires: Windows 10/11

2. **Install and Start Ollama**
   - Run the installer
   - Ollama starts automatically in the background
   - Look for Ollama icon in system tray

3. **Download a Vision Model**
   - Open Command Prompt or PowerShell
   - Run: `ollama pull llava:7b`
   - Wait 5-10 minutes (downloads ~4GB model)
   - Alternative models: `llava:13b` (better quality, slower) or `moondream` (faster, smaller)

4. **Verify Setup**
   - In ImageDescriber, create/open a workspace
   - Click "Process Images" button
   - Select provider: **Ollama**
   - Choose model: **llava:7b**
   - Select an image and click "Process Selected"

**✅ You're done!** Ollama will generate AI descriptions locally.

---

### ⚡ Optional: Object Detection (YOLO)

**Best for**: Counting objects, detecting specific items, precise analysis

**What it does**: Detects and counts objects (people, cars, animals, etc.) with bounding boxes

**Setup time**: 2-3 minutes

**Steps**:

1. **Run the setup batch file** (included with ImageDescriber)
   - Double-click: **setup_imagedescriber.bat**
   - OR manually: `pip install ultralytics`

2. **Verify Setup**
   - Restart ImageDescriber
   - Look for **"Object Detection"** in the provider dropdown
   - If it appears, you're all set!

**Usage**:
- Provider: **Object Detection**
- Adjust settings: Confidence threshold, max objects, YOLO model size
- Best for: Counting people, vehicles, animals; detecting specific objects

**Note**: YOLO detects 80 common objects (COCO dataset). It won't recognize artistic objects like sculptures, paintings, or specialized items.

---

### 🎯 Optional: GroundingDINO (Text-Prompted Object Detection)

**Best for**: Detecting ANY object you describe, unlimited flexibility, works in chat

**What it does**: Detects objects based on text descriptions - no preset limits!

**Requirements**: Python packages (torch, torchvision, groundingdino-py)

**Setup time**: 5 minutes + ~700MB model download on first use

**Steps**:

1. **Install GroundingDINO**
   ```bash
   pip install groundingdino-py torch torchvision
   ```

2. **First Use Model Download**
   - First time you use GroundingDINO, it downloads ~700MB model
   - This happens automatically
   - Subsequent uses are instant (model is cached)

3. **Verify Installation**
   - In ImageDescriber provider dropdown, look for:
     - **GroundingDINO** (standalone detection)
     - **GroundingDINO + Ollama** (detection + descriptions)

**Usage**:

**Option 1: Preset Detection Modes**
- Provider: **GroundingDINO** or **GroundingDINO + Ollama**
- Detection Mode: **Automatic**
- Choose preset: Comprehensive, Indoor, Outdoor, Workplace, Safety, Retail, Document
- Adjust confidence threshold (default 25%)

**Option 2: Custom Queries** (The Power Feature!)
- Provider: **GroundingDINO** or **GroundingDINO + Ollama**
- Detection Mode: **Custom Query**
- Type what to find: "red cars . blue trucks . motorcycles"
- Separate items with " . " (period with spaces)

**Example Queries**:
- `red cars . blue trucks . motorcycles`
- `people wearing helmets . safety equipment`
- `fire exits . emergency signs . first aid kits`
- `logos . text . diagrams`
- `damaged items . missing parts`

**Chat Integration** (Chat-based Detection):
- Select an image in the workspace
- Open or continue a chat session
- Type natural queries:
  - "find red cars"
  - "detect people wearing hats"
  - "show me safety equipment"
  - "locate fire exits"
- GroundingDINO automatically detects and responds!

**Advantages over YOLO**:
- ✅ Unlimited object types (YOLO limited to 80)
- ✅ Describe attributes: colors, states, conditions
- ✅ Natural language: "person wearing hat" not just "person"
- ✅ Works in chat with conversational queries
- ✅ Hybrid mode: Combines detection with Ollama descriptions

**Note**: First use downloads ~700MB model automatically. Requires internet connection for initial download only.

---

### 🔥 Optional: HuggingFace Provider (Local Florence-2 Models)

**Best for**: Free, privacy-focused local AI vision without internet connection

**What it does**: Runs Microsoft Florence-2 vision models entirely on your computer

**Requirements**: Python environment with transformers library

**Setup time**: 5-10 minutes (first download)

**Steps**:

1. **Install Florence-2 Dependencies**
   ```bash
   pip install transformers torch torchvision einops timm
   ```

2. **First Use Setup**
   - In ImageDescriber, select provider: **HuggingFace**
   - Choose model:
     - **microsoft/Florence-2-base** (230MB, faster)
     - **microsoft/Florence-2-large** (700MB, better quality)
   - First use will download the model automatically

3. **Verify Setup**
   - Process a test image
   - Model should load and generate descriptions
   - Subsequent uses will be faster (model cached locally)

**Usage**:
- Provider: Choose HuggingFace for local processing
- YOLO settings are available in the dialog
- Result: Descriptions include object detection data + AI understanding

---

### 💰 Optional: OpenAI (Cloud, Paid, GPT-4 Vision)

**Best for**: Highest quality descriptions, cloud-based, requires API key

**What it does**: Uses OpenAI's GPT-4 Vision API (same as ChatGPT Plus)

**Cost**: ~$0.01-0.03 per image (pay-as-you-go)

**Setup time**: 2 minutes

**Steps**:

1. **Get API Key**
   - Sign up at [platform.openai.com](https://platform.openai.com/signup)
   - Add payment method (required, but only pay for what you use)
   - Go to [API Keys](https://platform.openai.com/api-keys)
   - Click "Create new secret key"
   - Copy the key (starts with `sk-...`)

2. **Add API Key to ImageDescriber**
   - In ImageDescriber, go to: **Settings → Provider Settings**
   - Find: **OpenAI API Key**
   - Paste your key
   - Click **Save**

3. **Verify Setup**
   - Provider: **OpenAI**
   - Model: **gpt-4o** (recommended) or **gpt-4o-mini** (cheaper, faster)

**Notes**:
- Requires internet connection
- Costs add up with heavy use
- Excellent quality, but not private (images sent to OpenAI)

---

### 🤗 Optional: HuggingFace (Local/Cloud, Mixed)

**Best for**: Experimenting with different AI models, research

**What it does**: Access to thousands of AI models from HuggingFace

**Setup time**: 5 minutes

**Steps**:

1. **Get HuggingFace Token**
   - Sign up at [huggingface.co](https://huggingface.co/join)
   - Go to [Settings → Access Tokens](https://huggingface.co/settings/tokens)
   - Click "New token" → Select "Read"
   - Copy the token

2. **Add Token to ImageDescriber**
   - Settings → Provider Settings → **HuggingFace Token**
   - Paste token and save

3. **Download Models** (optional, for offline use)
   - Most models download on first use
   - Some require manual download
   - See HuggingFace documentation for specific models

---

### 🖥️ Optional: Copilot+ PC (NPU Acceleration)

**Best for**: Copilot+ PC owners with NPU hardware

**What it does**: Uses Windows AI Platform with NPU acceleration (40+ TOPS)

**Requirements**: 
- Copilot+ PC (AMD Ryzen AI 300, Intel Core Ultra 200V, or Snapdragon X)
- Windows 11 (22H2+)

**Setup time**: Automatic (no setup needed!)

**Usage**:
- Provider: **Copilot+ PC**
- Model: Select available Windows AI models
- Performance: ~3-8 seconds per image (hardware accelerated)

**Note**: If you don't have a Copilot+ PC, this provider won't appear.

---

## 🎨 Features Available Without AI

Even without setting up AI providers, you can use ImageDescriber for:

✅ **Workspace Management**
- Organize images into projects
- Add custom display names
- Create folder structures

✅ **Manual Descriptions**
- Type descriptions yourself
- Edit and refine text
- Multi-line support with formatting

✅ **Chat Sessions**
- Conversation-style organization
- Question and answer format
- Great for collaborative work

✅ **Image Preview**
- View images at full resolution
- Fullscreen mode (Enter key)
- HEIC format support

✅ **HTML Export**
- Generate beautiful web galleries
- Side-by-side comparisons
- Share with others

✅ **Batch Operations**
- Rename multiple items
- Delete in bulk
- Copy/paste descriptions

---

## 📋 Setup Checklist

Use this checklist to track what you've set up:

### Core (Already Have)
- [x] ImageDescriber.exe downloaded
- [x] Application launches successfully

### Recommended Setup (5-10 minutes)
- [ ] Ollama installed
- [ ] Ollama running (check system tray)
- [ ] Vision model downloaded (`ollama pull llava:7b`)
- [ ] Test description generated in ImageDescriber

### Optional Enhancements
- [ ] YOLO installed (`pip install ultralytics`)
- [ ] "Object Detection" provider appears in ImageDescriber
- [ ] Florence-2 dependencies installed (for HuggingFace provider)
- [ ] OpenAI API key configured (if using OpenAI)
- [ ] HuggingFace token configured (if using HuggingFace)

---

## 🔧 Troubleshooting

### "Ollama provider not available"

**Solutions**:
1. Check if Ollama is running (look for icon in system tray)
2. Restart Ollama: Exit from system tray, then start again
3. Test connection: Open browser to [http://localhost:11434](http://localhost:11434)
4. Reinstall Ollama if needed

### "Object Detection provider not showing"

**Solutions**:
1. Run: **setup_imagedescriber.bat** (included with ImageDescriber)
2. OR manually: `pip install ultralytics`
3. Restart ImageDescriber
4. Check: Provider dropdown should now show "Object Detection"

### "Unable to load image" errors

**Solutions**:
1. ImageDescriber supports: JPG, PNG, HEIC, BMP, GIF
2. For HEIC files, ensure they're valid (try opening in Windows Photos)
3. Check file isn't corrupted
4. Try converting to JPG first

### "Processing failed" with Ollama

**Possible causes**:
1. Model not downloaded: Run `ollama pull llava:7b`
2. Ollama not running: Check system tray
3. Image too large: Resize to under 4K resolution
4. Insufficient memory: Close other applications
5. Model busy: Wait for previous processing to complete

### Models are slow

**Solutions**:
1. Use smaller models: `moondream` or `llava:7b` instead of `llava:13b`
2. Use GPU: Ollama auto-detects GPU if available
3. Close other applications: Free up RAM
4. For Copilot+ PC: Use Copilot+ provider for NPU acceleration
5. For cloud: Consider OpenAI provider (faster but costs money)

### "API key invalid" (OpenAI/HuggingFace)

**Solutions**:
1. Double-check key/token copied correctly
2. Ensure no extra spaces before/after
3. Check key is still valid on provider website
4. Regenerate new key if needed
5. Verify payment method (OpenAI) or account status

---

## 🎯 Recommended Setup for Different Users

### **Casual User** (Just trying it out)
- ✅ Use built-in features (manual descriptions, workspace management)
- ⏩ Skip AI setup initially
- Time: 0 minutes

### **Home User** (Personal photos, privacy-focused)
- ✅ Install Ollama + llava:7b
- ⏩ Skip cloud providers
- Time: 10 minutes

### **Power User** (Best quality, all features)
- ✅ Install Ollama
- ✅ Install YOLO
- ✅ Install Florence-2 dependencies
- ✅ Use HuggingFace provider
- Time: 20 minutes

### **Professional** (High volume, quality matters)
- ✅ OpenAI API key
- ✅ Install Ollama as backup
- ✅ Install YOLO for object counting
- Cost: ~$0.02/image
- Time: 15 minutes setup

### **Copilot+ PC Owner** (Hardware acceleration)
- ✅ Use Copilot+ provider (built-in)
- ✅ Install Ollama as alternative
- ✅ Install YOLO for object detection
- Time: 15 minutes

---

## 📞 Getting Help

### Documentation
- **User Guide**: This file
- **What's Included**: See `WHATS_INCLUDED.txt`
- **Advanced Features**: See ImageDescriber's Help menu

### Online Resources
- **GitHub**: [kellylford/Image-Description-Toolkit](https://github.com/kellylford/Image-Description-Toolkit)
- **Issues**: Report bugs or request features
- **Discussions**: Ask questions, share tips

### Quick Reference
- **Ollama**: [ollama.ai/download](https://ollama.ai/download)
- **YOLO Setup**: Run `setup_imagedescriber.bat`
- **OpenAI**: [platform.openai.com](https://platform.openai.com)
- **HuggingFace**: [huggingface.co](https://huggingface.co)

---

## 🎉 You're All Set!

**Minimum to start**: Just run ImageDescriber.exe (0 minutes)  
**Recommended setup**: + Ollama (10 minutes)  
**Maximum features**: + HuggingFace Florence-2 (25 minutes total)

**Remember**: Start simple, add features as needed. The core app works great without any AI setup!

---

**Version**: October 2025  
**App Version**: ImageDescriber v2.0+  
**Questions?** See GitHub Issues or Discussions
