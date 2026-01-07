# Image Description Toolkit for macOS - Quick Start Guide

## What is IDT?

Image Description Toolkit (IDT) is a comprehensive suite for generating AI-powered descriptions of images and videos, with full accessibility support.

## System Requirements

- macOS 10.13 (High Sierra) or later
- For AI features: Ollama (local), OpenAI API key, or Anthropic Claude API key

## Installation Options

### Option 1: Using .pkg Installer (Recommended)

1. Double-click `IDT-{version}.pkg`
2. Follow the installation wizard
3. Applications will be installed to `/Applications/`
4. CLI tool will be installed to `/usr/local/bin/idt`

**After installation:**
- Launch apps from Applications folder or Spotlight
- Run `idt --help` in Terminal for CLI access

### Option 2: Using .dmg Disk Image (Portable)

1. Double-click `IDT-{version}.dmg` to mount
2. Drag .app files to Applications folder (or anywhere you prefer)
3. For CLI access:
   - Open "CLI Tools" folder in the mounted disk image
   - Double-click `INSTALL_CLI.sh` (enter password when prompted)
   - OR manually copy `idt` to `/usr/local/bin/`

**After installation:**
- Apps can run from any location
- Optional CLI installation for terminal access

## What's Included

### 1. ImageDescriber (GUI)
**Batch process images with AI descriptions**

- Select multiple images or folders
- Choose AI provider (Ollama, OpenAI, Claude)
- Customize description prompts
- Export to HTML, CSV, Excel
- Full keyboard navigation

**Launch:** Applications > ImageDescriber

### 2. Viewer (GUI)
**Browse and monitor workflows**

- View workflow results in beautiful layouts
- Live monitoring mode (auto-refresh)
- Date-sorted by EXIF data
- Re-describe images with different models
- Screen reader accessible

**Launch:** Applications > Viewer

### 3. Prompt Editor (GUI)
**Customize AI prompt templates**

- Edit description styles (narrative, technical, etc.)
- Create custom prompts
- Preview changes before saving
- Apply across all tools

**Launch:** Applications > Prompt Editor

### 4. IDT Configure (GUI)
**Manage toolkit settings**

- Configure AI provider settings
- Set default models and prompts
- Workflow preferences
- Export/import configurations

**Launch:** Applications > IDT Configure

### 5. idt (CLI)
**Command-line interface for all features**

```bash
# Get help
idt --help

# Create workflow
idt workflow /path/to/images

# View results
idt listresults

# Export descriptions
idt combinedescriptions

# Check version
idt version
```

## Quick Start Tutorial

### 1. Set Up AI Provider

**For Ollama (local, free):**
```bash
# Install Ollama from https://ollama.com
# Pull a vision model
ollama pull llava

# Test it
idt workflow /path/to/test/images
```

**For OpenAI:**
```bash
# Set API key (get from https://platform.openai.com)
export OPENAI_API_KEY="your-key-here"

# Test it
idt workflow /path/to/images --model gpt-4o
```

**For Claude:**
```bash
# Set API key (get from https://console.anthropic.com)
export ANTHROPIC_API_KEY="your-key-here"

# Test it
idt workflow /path/to/images --model claude-sonnet-4
```

### 2. Process Your First Images

**Using GUI (Easiest):**
1. Open **ImageDescriber** from Applications
2. Click "Select Images" or "Select Folder"
3. Choose AI provider from dropdown
4. Select model (llava, gpt-4o, etc.)
5. Click "Start Processing"
6. View results in the app or export to HTML

**Using CLI:**
```bash
# Create workflow with default settings
idt workflow ~/Pictures/vacation

# With specific model and prompt
idt workflow ~/Pictures/vacation --model llava --prompt technical

# Extract video frames first
idt extractframes ~/Movies/vacation.mp4
idt workflow wf_*/frames/
```

### 3. View Results

**Using Viewer:**
1. Open **Viewer** from Applications
2. Click "Select Workflow" or "Select Folder"
3. Browse descriptions with images
4. Enable "Live Mode" to monitor active workflows

**Using Web Browser:**
```bash
# Workflows create HTML files automatically
open wf_*/workflow_results.html
```

**Export to Excel/CSV:**
```bash
idt combinedescriptions
# Creates combined_descriptions.xlsx
```

## Accessibility Features

All IDT applications are fully accessible:

### VoiceOver Support
- Enable: System Preferences > Accessibility > VoiceOver (Cmd+F5)
- All controls have descriptive labels
- Navigation hints provided
- Status updates announced

### Keyboard Navigation
- **Tab/Shift+Tab:** Move between controls
- **Arrow keys:** Navigate lists and tables
- **Enter/Space:** Activate buttons
- **Cmd+Q:** Quit application
- **Cmd+W:** Close window

### Other Features
- High contrast mode support
- Dynamic type (respects system font size)
- Focus indicators
- WCAG 2.2 AA compliant

## Troubleshooting

### "Cannot open app" or "App is damaged"

This is a macOS security feature (Gatekeeper). Fix:

1. **Right-click the app** in Applications
2. Select **"Open"**
3. Click **"Open"** again in the warning dialog

OR remove quarantine attribute:
```bash
xattr -cr /Applications/viewer.app
```

### CLI tool not found

Add `/usr/local/bin` to your PATH:
```bash
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Then try again:
```bash
idt version
```

### App won't connect to AI provider

**Ollama:**
```bash
# Check if Ollama is running
ollama list

# Start Ollama if needed
ollama serve
```

**OpenAI/Claude:**
```bash
# Verify API key is set
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Set permanently in ~/.zshrc:
echo 'export OPENAI_API_KEY="your-key"' >> ~/.zshrc
```

### Python dependency errors (if building from source)

```bash
pip3 install -r requirements.txt
```

## Uninstalling

### If installed via .pkg:
```bash
# Remove CLI tool
sudo rm /usr/local/bin/idt

# Remove apps
rm -rf /Applications/viewer.app
rm -rf /Applications/imagedescriber.app
rm -rf /Applications/prompteditor.app
rm -rf /Applications/idtconfigure.app

# Remove user data (optional)
rm -rf ~/Library/Application\ Support/IDT
```

### If installed via .dmg:
Simply delete the .app files from wherever you placed them.

## Getting More Help

### Documentation
- Full documentation: See project repository
- Build from source: See `docs/BUILD_MACOS.md`
- Accessibility guide: See `docs/ACCESSIBILITY.md`

### CLI Help
```bash
idt --help                    # General help
idt workflow --help           # Workflow command help
idt combinedescriptions --help # Export command help
```

### Common Tasks

**Extract video frames:**
```bash
idt extractframes video.mp4
```

**Batch process with custom prompt:**
```bash
idt workflow images/ --model gpt-4o --prompt "detailed technical description"
```

**Monitor workflow in real-time:**
```bash
# In one terminal:
idt workflow images/

# In another terminal or use Viewer app:
idt viewer  # or open Viewer.app
```

**Export all workflows to spreadsheet:**
```bash
idt combinedescriptions
open combined_descriptions.xlsx
```

**Check AI provider status:**
```bash
idt checkmodels
```

## Tips for Best Results

1. **Use high-quality images** - AI works best with clear, well-lit photos
2. **Choose the right model** - GPT-4o for detail, Llava for speed
3. **Customize prompts** - Use Prompt Editor for specialized needs
4. **Monitor progress** - Use Viewer in Live mode for long batches
5. **Organize workflows** - Each workflow creates a timestamped folder

## Privacy & Data

- **Local processing:** Ollama models run entirely on your Mac
- **Cloud APIs:** OpenAI/Claude send images to their servers
- **No telemetry:** IDT doesn't collect or transmit usage data
- **Your data:** All workflows and configurations stay on your Mac

## License

See LICENSE file in the installation directory or project repository.

## Support

For issues, questions, or contributions, see the project repository.

---

**Thank you for using Image Description Toolkit!**

We're committed to making AI-powered image description accessible to everyone.
