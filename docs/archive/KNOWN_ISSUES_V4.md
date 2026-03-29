# Known Issues and Hints - Version 4.x

**For the latest issues and updates, see the [v4beta issues on GitHub](https://github.com/kellylford/Image-Description-Toolkit/issues?q=is:open+label:v4beta).**

## Known Issues



#### Processing UI Changes Do Not Announce Automatically
**Status:** Open - [Issue #83](https://github.com/kellylford/Image-Description-Toolkit/issues/83)

**Symptom:** When the processing UI (such as batch processing dialog) appears, changes such as the number of images processed do not announce automatically with a screen reader.

**Impact:** Screen reader users must manually navigate the dialog using arrow keys to know the current processing status, reducing the real-time feedback experience.

**Proposed Solution:** Add a setting to announce these changes automatically and a checkbox in the processing UI to enable/disable auto-announcements per session.

**Current Workaround:** Use the arrow keys to review the dialog text and status updates.

---

#### No Setting to Set Image Preview On/Off Permanently
**Status:** Open - [Issue #84](https://github.com/kellylford/Image-Description-Toolkit/issues/84)

**Symptom:** The View menu has a setting to show preview images or not. The app is more speedy with image previews disabled, but there is no way to make this setting permanent. When you close the app and reopen it, you have to turn image previews off again.

**Impact:** Users who prefer performance over previews must manually disable them every session.

**Proposed Solution:** Save the image preview state in the `.idw` workspace file (per-workspace preference) and/or in application settings (global preference).

**Current Workaround:** Manually disable image previews via View menu each time the application is opened.

---

#### Opening Results Viewer Launches Separate Window Instance
**Status:** Open - [Issue #85](https://github.com/kellylford/Image-Description-Toolkit/issues/85)

**Symptom:** When you use the File menu option for opening the Results Viewer to view results from an IDT workflow, a new application window and instance of Viewer opens. This isn't immediately obvious to users.

**Impact:** Users may not realize a new window has opened and think the application is unresponsive or the action failed.

**Current Workaround:** Use Alt+Tab to switch back to the original ImageDescriber window. You can also use Alt+F4 to exit the Results Viewer instance without any consequence to the running IDT workflow or any work you are doing in ImageDescriber.

---

#### CMD Line Prompt to View Results Does Not Work
**Status:** Open - [Issue #86](https://github.com/kellylford/Image-Description-Toolkit/issues/86)

**Symptom:** The CMD IDT tool has a prompt to view the results of a run when it is finished. This bat file does not work currently.

**Impact:** Users cannot view results directly from the command line completion prompt.

**Current Workaround:** Open ImageDescriber and use the Results Viewer option on the File menu, or navigate to the workflow directory directly and view the HTML reports directory or the descriptions directory. Workflow directories are found inside a folder named Descriptions inside the `c:\idt` folder.

---

#### Ollama Install Leaves Ollama UI Open
**Status:** Open - [Issue #87](https://github.com/kellylford/Image-Description-Toolkit/issues/87)

**Symptom:** As a part of installing Ollama, the main Ollama window will be opened.

**Impact:** Users see an unexpected window after Ollama installation during setup.

**Current Workaround:** You can safely close it with Alt+F4.

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

**Tip:** Use Process→ Refresh Ollama Models to update the cache if you install new models.

---

#### Batch Progress Dialog
- Use Tab to cycle through controls (Pause/Resume, Stop, Close buttons)
- Press Escape to hide the dialog (processing continues in background)
- Use Process → Show Batch Progress to bring it back

---

#### Screen Reader Support
- Image list uses arrow keys for navigation
- Full description text is announced by screen readers (not truncated)
- Batch progress shows "Last Description" for context


**Tip:** Use single-key shortcuts for common actions:

- `p` - Process image
- `R` - Redescribe all
- `S` - Stop batch processing

---

### Ollama Installation

#### Automatic Installation (Windows)
The Windows installer can automatically install Ollama via winget if:
- You're on Windows 10/11
- winget (Windows Package Manager) is available
- You check the "Install Ollama via winget" option

**Note:** If winget is not available, you'll have an option to visit the Ollama website instead.

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

### 4.0.0Beta1 (February 2026)
- **Fixed:** Batch processing blocked after workspace reload (worker cleanup issue)
- **Fixed:** Alt+F4 not closing application (worker cleanup during close)
- **Fixed:** Process All hang when loading workspace from file (Path object conversion)
- **Fixed:** Exit command freeze in broken state
- **Fixed:** Worker cleanup during workspace transitions
- **Added:** Automatic Ollama installation via winget (Windows)
- **Added:** "Last Description" display in batch progress dialog
- **Added:** Stop All Processing command (Ctrl+Shift+S)
- **Enhanced:** Error handling in close/cleanup operations
- **Enhanced:** Log file naming standardized (ImageDescriber.log)

---

## Tips for Power Users

### Keyboard Shortcuts Master List
- `Ctrl+N` - New Session
- `Ctrl+O` - Open Workspace
- `Ctrl+S` - Save Workspace
- `Ctrl+Shift+S` - Stop All Processing
- `Ctrl+W` - Close Workspace
- `p` - Process image
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
2. Process individual images one at a time with `p` key
3. Or use "Process All Undescribed" to batch the remainder

---

*Last Updated: February 13, 2026*
*Document Version: 1.0*
