# ImageDescriber - AI-Powered Image Description GUI

A Qt6-based standalone application for processing images and generating AI descriptions with a comprehensive document-based workspace approach, advanced batch processing capabilities, and full accessibility support.

## Overview

ImageDescriber provides a professional workspace for managing image description projects. Unlike traditional batch processing tools, it treats your image collections as documents that can be saved, reopened, and incrementally developed over time. The application features enterprise-level batch processing controls, WCAG-compliant accessibility, and advanced filtering and visualization options.

## Key Features

### Document-Based Workspace
- **Save/Load Projects**: Store your work as `.idw` (ImageDescriber Workspace) files
- **Persistent State**: Batch markings, descriptions, and processing history survive app restarts
- **Multiple Descriptions**: Each image can have multiple AI descriptions with different models and prompts
- **Metadata Tracking**: Track which model, prompt style, and creation date for each description
- **Batch Selection Persistence**: Batch-marked items are saved with workspace files for later processing

### Advanced Batch Processing
- **Visual Indicators**: Batch-marked items show with "b" prefix and accessible light blue background
- **Progress Tracking**: Real-time progress in window title ("Batch Processing: 3 of 10")
- **Batch Queue Display**: Shows number of items marked for batch processing
- **Completion Confirmation**: Choice to clear or keep batch selection after processing
- **Stop Processing**: Graceful cancellation of batch operations
- **Filter by Batch Status**: View only batch-marked items
- **Manual Batch Clearing**: Clear all batch markings via menu option

### Processing Capabilities
- **Individual Processing**: Process single images with the P key
- **Batch Processing**: Mark multiple images with B key, then process all at once
- **Process All**: Process all images in workspace with one command
- **HEIC Conversion**: Automatic conversion of HEIC/HEIF images to JPEG
- **Video Frame Extraction**: Extract frames from videos (MP4, MOV, AVI, MKV) for description
- **Live Ollama Integration**: Select from installed Ollama models in real-time
- **Custom Prompts**: Use predefined prompt styles or write custom prompts
- **Skip Model Verification**: Optional faster processing by skipping model checks

### Accessibility & Visual Features
- **WCAG AA/AAA Compliant**: Light blue backgrounds with 18.39:1 contrast ratio
- **Screen Reader Support**: Full accessibility descriptions for all interface elements
- **Multiple Indicators**: Visual prefixes (p/d/b) + color coding + screen reader text
- **Keyboard Navigation**: Complete keyboard control with shortcuts
- **Status Indicators**: "p" for processing, "d" for described, "b" for batch-marked
- **Focus Tracking**: Proper focus management for screen readers and keyboard users

### Advanced Filtering & Views
- **Filter Options**: View All, Described Only, or Batch-Marked Only
- **View Menu Filters**: Organized filter options in View menu
- **Smart Refresh**: Maintains current filter when updating views
- **All Descriptions Dialog**: Browse all descriptions across all images
- **Hierarchical Display**: Videos show extracted frames as children with proper accessibility

### User Interface
- **Menu-Driven**: Organized menus instead of button-heavy interfaces
- **Tree View**: Hierarchical display with videos showing extracted frames as children
- **Split Pane**: Images on left, descriptions on right for efficient workflow
- **Keyboard Shortcuts**: P for process, B for batch marking, standard save/open shortcuts
- **Status Bar**: Real-time processing status and progress information
- **Window Title Updates**: Shows current workspace and batch processing progress

## Getting Started

### Prerequisites
- Python 3.8+ with PyQt6 installed
- Ollama installed and running with at least one vision model (e.g., llava)
- Virtual environment activated (recommended)

### Installation
1. Ensure you're in the Image-Description-Toolkit directory
2. Activate your virtual environment
3. Run the application:
   ```bash
   cd imagedescriber
   python imagedescriber.py
   ```

### First Use
1. **Start a New Project**: File → New Workspace
2. **Load Images**: File → Load Image Directory... (select folder with images/videos)
3. **Process Images**: Select an image, press P or use Processing → Process Selected
4. **Save Your Work**: File → Save Workspace (saves as .idw file)

## Workflow Guide

### Basic Image Processing
1. **Load Directory**: File → Load Image Directory
2. **Select Image**: Click on any image in the left tree
3. **Process**: Press P key or Processing → Process Selected (P)
4. **Choose Options**: Select AI model, prompt style, or write custom prompt
5. **View Result**: Description appears in right panel
6. **Save Project**: Ctrl+S or File → Save Workspace

### Advanced Batch Processing
1. **Mark Images**: Select images and press B key (or Processing → Mark for Batch)
   - Marked images show "b" prefix and light blue background
   - Batch Queue label shows count of marked items
2. **Monitor Progress**: Batch Queue label shows "X items" marked
3. **Process Batch**: Processing → Process Batch
   - Window title shows "Batch Processing: X of Y"
   - Status bar provides real-time updates
4. **Completion Options**: 
   - Dialog asks if you want to clear batch selection
   - Choose "Yes" to clear markings or "No" to keep for reuse
5. **Manual Control**: 
   - Processing → Stop Processing to halt batch operations
   - Processing → Clear Batch Processing to remove all markings

### Filtering and Views
1. **Filter by Status**: View → Filter → [All/Described Only/Batch Processing]
   - All: Shows all images and videos
   - Described Only: Shows only items with descriptions
   - Batch Processing: Shows only batch-marked items
2. **Browse Descriptions**: Descriptions → Show All Descriptions (opens dialog with all descriptions across all images)
3. **Status Indicators**: 
   - "p" prefix: Currently processing
   - "d" prefix: Has descriptions 
   - "b" prefix: Marked for batch processing

### Batch Processing
1. **Mark Images**: Select images and press B key (or Processing → Mark for Batch)
   - Marked images turn yellow in the tree
2. **Process Batch**: Processing → Process Batch
3. **Monitor Progress**: Status bar shows current processing status
4. **Review Results**: Each image will have its description added

### Working with Videos
1. **Extract Frames**: Processing → Extract Video Frames
2. **Process Frames**: Extracted frames appear as children under the video
3. **Describe Frames**: Process frames individually or mark for batch

### Managing Descriptions
- **View All**: Select an image to see all its descriptions in the right panel
- **Edit**: Descriptions → Edit Description
- **Delete**: Descriptions → Delete Description  
- **Copy**: Descriptions → Copy Description (copies to clipboard)
- **Multiple Versions**: Keep multiple descriptions with different models/prompts

## Menu Reference

### File Menu
- **New Workspace** (Ctrl+N): Start fresh project
- **Open Workspace** (Ctrl+O): Load existing .idw project file
- **Save Workspace** (Ctrl+S): Save current project
- **Save Workspace As** (Ctrl+Shift+S): Save with new name
- **Load Image Directory**: Add images from folder to workspace
- **Exit** (Ctrl+Q): Close application

### Processing Menu
- **Process Selected (P)**: Process currently selected image/frame
- **Mark for Batch (B)**: Toggle batch marking for selected item
- **Process Batch**: Process all batch-marked items
- **Clear Batch Processing**: Remove batch markings from all items
- **Stop Processing**: Halt current processing operation
- **Skip Model Verification**: Toggle faster processing by skipping model checks
- **Convert HEIC Files**: Convert all HEIC/HEIF files to JPEG
- **Extract Video Frames**: Extract frames from all videos in workspace
- **Process All**: Process all images in workspace (with confirmation)

### Descriptions Menu
- **Edit Description**: Modify the selected description text
- **Delete Description**: Remove the selected description
- **Copy Description**: Copy description text to clipboard
- **Copy Image Path**: Copy file path to clipboard
- **Show All Descriptions**: Open dialog showing all descriptions across all images

### View Menu
- **Refresh** (F5): Reload workspace view
- **Expand All**: Expand all tree items
- **Collapse All**: Collapse all tree items
- **Filter**: Submenu with filtering options
  - **All**: Show all items (default)
  - **Described Only**: Show only items with descriptions
  - **Batch Processing**: Show only batch-marked items

## Visual Indicators & Accessibility

### Status Prefixes
Items in the tree view show status with accessible prefixes:
- **"p"**: Currently being processed (with accessible descriptions for screen readers)
- **"d[count]"**: Has descriptions (shows count, e.g., "d2" for 2 descriptions)
- **"b"**: Marked for batch processing (with light blue background)

### Color Coding
- **Light Blue Background**: Batch-marked items (#E3F2FD - WCAG AAA compliant, 18.39:1 contrast ratio)
- **No Color Dependency**: All information available via text prefixes and screen reader descriptions

### Accessibility Features
- **Screen Reader Support**: Full AccessibleTextRole and AccessibleDescriptionRole support
- **Keyboard Navigation**: Complete keyboard control with standard Qt navigation
- **WCAG Compliance**: All color combinations meet WCAG AA/AAA standards
- **Focus Management**: Proper focus tracking for keyboard and screen reader users
- **Multiple Indicators**: Visual + text + audio cues ensure no information is color-dependent

## Batch Processing Workflow

### Marking Items for Batch
1. **Select Items**: Click on images/videos in the tree
2. **Mark for Batch**: Press B key or Processing → Mark for Batch (B)
3. **Visual Confirmation**: Items show "b" prefix and light blue background
4. **Queue Status**: Batch Queue label shows "X items" marked

### Processing Batches
1. **Start Processing**: Processing → Process Batch
2. **Monitor Progress**: 
   - Window title: "Batch Processing: 3 of 10"
   - Status bar: Real-time processing updates
   - Individual items show "p" prefix while processing
3. **Control Options**: 
   - Processing → Stop Processing to halt operation
   - Progress continues in background until stopped

### Completion Handling
1. **Completion Dialog**: Appears when batch finishes (success or with errors)
2. **User Choice**: 
   - **"Yes"**: Clear all batch markings (removes "b" indicators)
   - **"No"**: Keep batch selection for potential reuse
3. **Manual Clearing**: Processing → Clear Batch Processing (available anytime)

## Filtering & Organization

### View Filters (View → Filter)
- **All**: Default view showing all images and videos
- **Described Only**: Shows only items that have at least one description
- **Batch Processing**: Shows only items marked for batch processing

### Smart Organization
- **Hierarchical Display**: Videos show extracted frames as children
- **Status Persistence**: All markings and descriptions saved with workspace
- **Incremental Work**: Add images, mark for batch, save, and continue later

## Keyboard Shortcuts

| Key | Action | Notes |
|-----|--------|-------|
| P | Process selected image | Works on currently selected item |
| B | Toggle batch marking | Adds/removes from batch queue |
| Ctrl+N | New workspace | Starts fresh project |
| Ctrl+O | Open workspace | Load existing .idw file |
| Ctrl+S | Save workspace | Save current project |
| Ctrl+Shift+S | Save workspace as | Save with new name |
| Ctrl+Q | Exit application | Close app |
| F5 | Refresh view | Reload current view with active filter |
| Delete | Delete description | When description is selected |
| Ctrl+C | Copy description | When description is selected |
| Escape | Cancel/Stop | Stop current processing operation |

## File Types Supported

### Images
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tif, .tiff)
- WebP (.webp)
- HEIC/HEIF (.heic, .heif) - auto-converted

### Videos
- MP4 (.mp4)
- MOV (.mov)
- AVI (.avi)
- MKV (.mkv)
- WMV (.wmv)

## Configuration

### Prompt Styles
The app reads prompt configurations from `../scripts/image_describer_config.json`. You can add custom prompt styles by editing this file:

```json
{
  "prompts": {
    "detailed": {
      "text": "Provide a detailed description of this image."
    },
    "brief": {
      "text": "Briefly describe this image."
    },
    "creative": {
      "text": "Describe this image in a creative, engaging way."
    },
    "custom_style": {
      "text": "Your custom prompt here..."
    }
  }
}
```

### Ollama Models
The app automatically detects installed Ollama models. Ensure you have at least one vision-capable model installed:

```bash
ollama pull llava
ollama pull bakllava
ollama pull llava-phi3
```

## Workspace File Format

Workspace files (`.idw`) are JSON documents containing:
- Project metadata (creation/modification dates)
- Image file paths and types
- All descriptions with metadata (model, prompt, creation date)
- Batch markings and processing state (persisted across sessions)
- Video frame relationships and extraction data
- Filter preferences and view state
- Processing history and status tracking

Example structure:
```json
{
  "version": "1.0",
  "created": "2025-09-06T10:30:00",
  "modified": "2025-09-06T15:45:00",
  "items": {
    "image1.jpg": {
      "file_path": "image1.jpg",
      "item_type": "image",
      "batch_marked": true,
      "descriptions": [
        {
          "text": "A detailed description...",
          "model": "llava",
          "prompt_style": "detailed",
          "created": "2025-09-06T15:30:00"
        }
      ]
    }
  }
}
```

## Tips and Best Practices

### Organizing Work
- **Use Descriptive Names**: Save workspaces with meaningful names
- **Incremental Saves**: Save frequently as you process images
- **Backup Projects**: Keep backup copies of important workspace files
- **Batch Strategy**: Mark related images for consistent processing

### Processing Strategy
- **Test Single First**: Process one image to verify model/prompt before batch processing
- **Use Batch Marking**: Mark related images for consistent processing with "b" indicators
- **Multiple Descriptions**: Try different models/prompts for comparison
- **Custom Prompts**: Use specific prompts for specialized content
- **Monitor Progress**: Watch window title and status bar during batch processing
- **Use Filters**: Filter by status to focus on specific items (described, batch-marked, etc.)

### Accessibility & Efficiency
- **Keyboard Navigation**: Use P/B keys and standard shortcuts for faster workflow
- **Screen Reader**: Full accessibility support for visually impaired users
- **Visual Indicators**: Status prefixes (p/d/b) provide quick visual feedback
- **Batch Completion**: Choose whether to clear batch markings after processing
- **Stop Processing**: Use stop option for graceful cancellation of long operations

### Performance
- **Close When Done**: Exit the app when finished to free resources
- **Monitor Ollama**: Ensure Ollama service is running and responsive
- **Large Batches**: For very large batches, consider processing in smaller groups
- **Skip Verification**: Enable for faster processing when using trusted models
- **Filter Views**: Use filtered views to focus on specific subsets of images

## Troubleshooting

### Common Issues

**App Won't Start**
- Ensure virtual environment is activated
- Check PyQt6 installation: `pip install PyQt6`
- Verify Python version (3.8+)

**No Models Available**
- Install Ollama vision models: `ollama pull llava`
- Check Ollama service is running: `ollama list`
- Restart the app after installing models

**Processing Fails**
- Check Ollama service status
- Verify image file isn't corrupted
- Try a different model
- Check available disk space

**Can't Save Workspace**
- Check write permissions in target directory
- Ensure filename doesn't contain invalid characters
- Try saving to a different location

### Getting Help
- Check status bar for progress messages
- Look for error dialogs with specific error details
- Verify Ollama logs if processing fails consistently

## Building Executable

To create a standalone executable:

```bash
cd imagedescriber
./build_imagedescriber.bat
```

The executable will be created in `../dist/imagedescriber_[ARCH]/ImageDescriber/`

## Architecture

ImageDescriber is built using:
- **PyQt6**: Modern Qt6 bindings for Python
- **Ollama Integration**: Direct API communication with Ollama
- **Document Model**: JSON-based workspace persistence
- **Worker Threads**: Non-blocking background processing
- **Modular Design**: Separate classes for UI, processing, and data management

## Version History

### v2.0.0 - Advanced Batch Processing & Accessibility (September 2025)
- **Advanced Batch Processing**: Progress tracking in window title, completion confirmation dialogs
- **WCAG Accessibility**: AA/AAA compliant color scheme (18.39:1 contrast ratio), screen reader support
- **Visual Indicators**: Status prefixes (p/d/b) with accessible color coding
- **Filtering System**: View filters for All/Described Only/Batch Processing
- **Batch Management**: Clear batch processing menu option, persistent batch selections
- **Process All**: Process entire workspace with confirmation
- **Stop Processing**: Graceful cancellation of batch operations
- **Show All Descriptions**: Dialog to browse all descriptions across workspace
- **Enhanced UI**: Real-time progress tracking, status indicators, improved accessibility
- **Workspace Persistence**: Batch selections saved and restored with workspace files

### v1.0.0 - Foundation (Initial Release)
- Initial release with document-based workspace
- Individual and batch processing
- Video frame extraction
- HEIC conversion support
- Multiple descriptions per image
- Menu-driven interface
- Keyboard shortcuts
- Ollama integration
- Custom prompt support
