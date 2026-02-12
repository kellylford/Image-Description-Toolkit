# Known Issues and Hints - Version 4.x

## Known Issues

### Batch Processing

#### "Process All Undescribed" Does Nothing After Stopping/Reloading
**Status:** Fixed in 4.0.0Beta1+

**Symptom:** After stopping batch processing and reloading a workspace, the "Process All Undescribed" menu command appears to do nothing.

**Cause:** Worker threads were not being properly cleaned up when loading workspaces, leaving stopped workers in memory that blocked new operations.

**Solution:** Fixed in latest builds. When loading or creating workspaces, all background workers are now stopped and cleared.

**Workaround (older builds):** Use File → New Session (Ctrl+N) to clear worker state, then reload your workspace.

---

#### Application Won't Close (Alt+F4 or File → Quit)
**Status:** Fixed in 4.0.0Beta1+

**Symptom:** Pressing Alt+F4 or selecting File → Quit does nothing. The application remains open.

**Cause:** Worker cleanup during close was failing silently, preventing the window from destroying. Also related to batch progress dialog staying on top.

**Solution:** Fixed in latest builds. Enhanced error handling in close handler with fallback mechanisms.

**Workaround (older builds):** Use File → New Session (Ctrl+N) first, then Alt+F4 will work.

---

### Installation

#### Installer Build Errors with Inno Setup
**Status:** Resolved

**Symptom:** Build fails with "Invalid prototype for 'ShouldShowOllamaInstallTask'" or "Unknown identifier 'BoolToStr'"

**Cause:** Inno Setup Pascal Script has specific requirements:
- Check functions for Tasks/Run sections must be parameterless
- BoolToStr function doesn't exist in Pascal Script
- [Code] section must come before sections that reference functions

**Solution:** 
- Check functions now use: `function ShouldShowOllamaInstallTask: Boolean;` (no parameters)
- Use if/else instead of BoolToStr for boolean-to-string conversion
- [Code] section properly ordered before [Tasks] section

---

## Hints and Best Practices

### Workspace Management

#### Always Name Your Workspaces
Batch processing requires a named workspace (not "Untitled"). You'll be prompted to save with a descriptive name before processing starts.

**Tip:** Use descriptive names based on your image collection (e.g., "Family_Photos_2025" or "Product_Catalog_Electronics").

---

#### Save Before Batch Processing
The application will auto-save before starting batch processing, but it's good practice to manually save (Ctrl+S) after making changes.

---

#### Workspace Recovery
If batch processing is interrupted (power loss, crash, etc.), your workspace will prompt you to resume when you reload it. Progress is saved after each image.

---

### Batch Processing

#### Stop vs Stop All Processing
- **Stop Batch Processing:** Pauses current batch, can be resumed later
- **Stop All Processing (Ctrl+Shift+S):** Emergency stop for ALL background operations (batch, video extraction, downloads, scans)

---

#### Video Frame Extraction
When processing workspaces containing videos, frames will be extracted automatically before describing. Default setting: 1 frame every 5 seconds.

**Tip:** Configure extraction settings in Tools → Configure before adding videos to workspace.

---

### Performance

#### Ollama Model Caching
The first time you open the Processing Options dialog, Ollama models are fetched and cached in the workspace. Subsequent opens are instant.

**Tip:** Use Tools → Refresh Ollama Models to update the cache if you install new models.

---

#### Batch Progress Dialog
- Use Tab to cycle through controls (Pause/Resume, Stop, Close buttons)
- Press Escape to hide the dialog (processing continues in background)
- Use Process → Show Batch Progress to bring it back

---

### Accessibility

#### Screen Reader Support
- Image list uses arrow keys for navigation
- Full description text is announced by screen readers (not truncated)
- Batch progress shows "Last Description" for context
- All dialogs are keyboard accessible

**Tip:** Use single-key shortcuts for common actions:
- `D` - Describe current image
- `P` - Process all undescribed
- `R` - Redescribe all
- `S` - Stop batch processing

---

### Ollama Installation

#### Automatic Installation (Windows)
The Windows installer can automatically install Ollama via winget if:
- You're on Windows 10/11
- winget (Windows Package Manager) is available
- You check the "Install Ollama via winget" option

**Note:** If winget is not available, you'll see an option to visit the Ollama website instead.

---

#### Manual Installation
1. Visit https://ollama.com
2. Download and install Ollama
3. Open a terminal and run: `ollama pull moondream`
4. Verify with: `ollama list`

**Recommended Models:**
- `moondream` - Fast, efficient vision model (default)
- `llava` - More detailed descriptions
- `llava:13b` - Highest quality (requires more RAM)

---

## Troubleshooting

### Batch Processing Won't Start

**Check:**
1. Is the workspace named (not "Untitled")?
2. Are there any images in the workspace?
3. Is Ollama running? (Check system tray or run `ollama list`)
4. Try Process → Stop All Processing first to clear any stuck workers

---

### Alt+F4 Won't Close Application

**Try:**
1. File → New Session (Ctrl+N) - this clears worker state
2. Then Alt+F4 or File → Quit should work
3. If still stuck, check Task Manager for hung processes

**Note:** Fixed in 4.0.0Beta1+ - if you're still experiencing this, please update.

---

### "Last Description" Not Showing in Batch Progress

**Check:**
- Make sure you're using the latest build (feature added in 4.0.0Beta1)
- The description appears after the first image completes processing
- Use arrow keys in the stats list to navigate if using screen reader

---

### Video Extraction Fails

**Check:**
1. Is OpenCV installed? Run: `pip install opencv-python`
2. Is the video file corrupted? Try opening in VLC
3. Check extraction config in Tools → Configure
4. Some exotic codecs may not be supported

---

## Reporting Issues

### Before Reporting
1. Check if your issue is listed above
2. Try the workarounds
3. Update to the latest version
4. Check the log files in your workspace directory

### What to Include
- ImageDescriber version (Help → About)
- Operating system and version
- Steps to reproduce
- Error messages or screenshots
- Log files (if available)

### Where to Report
- GitHub Issues: https://github.com/kellylford/Image-Description-Toolkit/issues
- Include "[ImageDescriber]" in the title

---

## Version History

### 4.0.0Beta1
- **Fixed:** Batch processing blocked after workspace reload
- **Fixed:** Alt+F4 not closing application
- **Fixed:** Worker cleanup during workspace transitions
- **Added:** Automatic Ollama installation via winget (Windows)
- **Added:** "Last Description" display in batch progress
- **Added:** Stop All Processing command (Ctrl+Shift+S)
- **Enhanced:** Error handling in close/cleanup operations

---

## Tips for Power Users

### Keyboard Shortcuts Master List
- `Ctrl+N` - New Session
- `Ctrl+O` - Open Workspace
- `Ctrl+S` - Save Workspace
- `Ctrl+Shift+S` - Stop All Processing
- `Ctrl+W` - Close Workspace
- `D` - Describe Image
- `P` - Process All Undescribed
- `R` - Redescribe All
- `S` - Stop Batch Processing
- `Delete` - Remove Image from Workspace
- `F2` - Rename Workspace
- `F5` - Refresh Ollama Models
- `Alt+F4` - Quit Application

### Batch Processing Strategies

#### For Large Collections (100+ images)
1. Create a named workspace
2. Add images via "Add Directory" with subdirectory scan
3. Use "Process All Undescribed" to describe in one batch
4. Progress is saved automatically - safe to pause/resume

#### For Mixed Content (Images + Videos)
1. Videos are extracted automatically before processing
2. Extraction happens first, then all frames are described
3. One progress dialog shows both extraction and description
4. Extracted frames appear nested under their source video

#### For Selective Processing
1. Use filters to view "Undescribed" items only
2. Process individual images one at a time with `D` key
3. Or use "Process All Undescribed" to batch the remainder

---

*Last Updated: February 12, 2026*
*Document Version: 1.0*
