# ImageDescriber - AI-Powered Image Description GUI

A Qt6-based standalone application for processing images and generating AI descriptions with a document-based workspace approach.

## Overview

ImageDescriber provides a professional workspace for managing image description projects. Unlike traditional batch processing tools, it treats your image collections as documents that can be saved, reopened, and incrementally developed over time.

## Key Features

### Document-Based Workspace
- **Save/Load Projects**: Store your work as `.idw` (ImageDescriber Workspace) files
- **Persistent State**: Batch markings, descriptions, and processing history survive app restarts
- **Multiple Descriptions**: Each image can have multiple AI descriptions with different models and prompts
- **Metadata Tracking**: Track which model, prompt style, and creation date for each description

### Processing Capabilities
- **Individual Processing**: Process single images with the P key
- **Batch Processing**: Mark multiple images with B key, then process all at once
- **HEIC Conversion**: Automatic conversion of HEIC/HEIF images to JPEG
- **Video Frame Extraction**: Extract frames from videos (MP4, MOV, AVI, MKV) for description
- **Live Ollama Integration**: Select from installed Ollama models in real-time
- **Custom Prompts**: Use predefined prompt styles or write custom prompts

### User Interface
- **Menu-Driven**: Organized menus instead of button-heavy interfaces
- **Tree View**: Hierarchical display with videos showing extracted frames as children
- **Split Pane**: Images on left, descriptions on right for efficient workflow
- **Keyboard Shortcuts**: P for process, B for batch marking, standard save/open shortcuts

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
- **Convert HEIC Files**: Convert all HEIC/HEIF files to JPEG
- **Extract Video Frames**: Extract frames from all videos in workspace

### Descriptions Menu
- **Edit Description**: Modify the selected description text
- **Delete Description**: Remove the selected description
- **Copy Description**: Copy description text to clipboard
- **Copy Image Path**: Copy file path to clipboard

### View Menu
- **Refresh** (F5): Reload workspace view
- **Expand All**: Expand all tree items
- **Collapse All**: Collapse all tree items

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| P | Process selected image |
| B | Toggle batch marking |
| Ctrl+N | New workspace |
| Ctrl+O | Open workspace |
| Ctrl+S | Save workspace |
| Ctrl+Shift+S | Save workspace as |
| Ctrl+Q | Exit application |
| F5 | Refresh view |

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
- All descriptions with metadata
- Batch markings and processing state
- Video frame relationships

## Tips and Best Practices

### Organizing Work
- **Use Descriptive Names**: Save workspaces with meaningful names
- **Incremental Saves**: Save frequently as you process images
- **Backup Projects**: Keep backup copies of important workspace files

### Processing Strategy
- **Test Single First**: Process one image to verify model/prompt before batch processing
- **Use Batch Marking**: Mark related images for consistent processing
- **Multiple Descriptions**: Try different models/prompts for comparison
- **Custom Prompts**: Use specific prompts for specialized content

### Performance
- **Close When Done**: Exit the app when finished to free resources
- **Monitor Ollama**: Ensure Ollama service is running and responsive
- **Large Batches**: For very large batches, consider processing in smaller groups

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

### v1.0.0
- Initial release with document-based workspace
- Individual and batch processing
- Video frame extraction
- HEIC conversion support
- Multiple descriptions per image
- Menu-driven interface
- Keyboard shortcuts
