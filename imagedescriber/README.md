# Image Describer GUI

A user-frien### User Interface

### Main Window Layout
- **Left Panel**: Image list with processing status indicators
- **Right Panel**: Tabbed interface with Description view and Processing logs
- **Status Bar**: Current operation and directory information

### Visual Indicators
- **White background**: Unprocessed image
- **Yellow background**: Queued for batch processing
- **Gray background**: Successfully processed

### Keyboard Shortcuts
- **P**: Process selected image individually
- **B**: Toggle batch queue for selected image
- **Tab**: Switch between Description and Processing Log tabs

### Description Features
After processing an image, the Description tab shows:
- **Full AI-generated description**: Same quality as command-line scripts
- **Copy button**: Copy description to clipboard
- **Redescribe button**: Generate a new description for the image
- **Real-time updates**: Description appears immediately after processingUI application for processing images and generating AI-powered descriptions. This application provides an intuitive interface that leverages the proven workflow scripts without requiring command-line knowledge.

## Features

### Core Functionality
- **Directory-based browsing**: Select any directory containing images
- **Individual processing**: Press `P` to process the selected image immediately
- **Batch processing**: Press `B` to queue images, then use "Batch Process" button
- **Real-time progress**: Visual feedback during processing with detailed logging
- **HTML generation**: "Finalize" button creates the same HTML output as the scripts

### Supported Formats
- **Images**: JPG, JPEG, PNG, GIF, BMP, TIFF, HEIC, HEIF, WebP
- **Videos**: MP4, MOV, AVI, MKV (automatically extracts frames)

### Smart Processing
- **HEIC conversion**: Automatically converts HEIC/HEIF files to compatible formats
- **Video frame extraction**: Processes video files by extracting representative frames
- **Workflow integration**: Uses the same proven scripts as the command-line tools

## Quick Start

1. **Launch the application**:
   ```bash
   python imagedescriber/imagedescriber.py
   ```

2. **Select a directory**: Click "Select Image Directory" and choose a folder containing images

3. **Process images**:
   - **Individual**: Select an image and press `P` key
   - **Batch**: Select images and press `B` to queue, then click "Batch Process"

4. **Generate output**: Click "Finalize & Generate HTML" when processing is complete

## User Interface

### Main Window Layout
- **Left Panel**: Image list with processing status indicators
- **Right Panel**: Progress tracking and processing logs
- **Status Bar**: Current operation and directory information

### Visual Indicators
- **White background**: Unprocessed image
- **Yellow background**: Queued for batch processing
- **Gray background**: Successfully processed

### Keyboard Shortcuts
- **P**: Process selected image individually
- **B**: Toggle batch queue for selected image

## Processing Workflow

### Individual Processing (P key)
1. Select image from list
2. Press `P` key
3. Watch real-time progress in right panel
4. Image is processed immediately using workflow scripts

### Batch Processing (B key + Batch Process button)
1. Select images and press `B` to add to queue (yellow highlight)
2. Press `B` again on queued items to remove them
3. Click "Batch Process" when ready
4. All queued images are processed sequentially
5. Progress shows current image and completion status

### Finalization
1. After processing any images, "Finalize" button becomes available
2. Click to generate HTML output using `descriptions_to_html.py`
3. Output appears in the working directory, identical to script output

## Technical Details

### Script Integration
The GUI application uses the existing workflow scripts without modification:
- `ConvertImage.py` for HEIC conversion
- `video_frame_extractor.py` for video processing
- `image_describer.py` for AI description generation
- `descriptions_to_html.py` for final HTML output

### Threading
- Image processing runs in background threads
- UI remains responsive during processing
- Real-time progress updates and logging

### Configuration
- Uses default workflow configuration
- Same AI models and settings as command-line scripts
- Compatible with existing configuration files

## Building Standalone Executable

Create a build script similar to the viewer and prompt editor:

```bash
# Create build script
cp viewer/build_viewer.bat imagedescriber/build_imagedescriber.bat
# Edit paths and names in the build script
```

The executable will include all dependencies and the scripts directory.

## Directory Structure

```
imagedescriber/
├── imagedescriber.py          # Main GUI application
├── README.md                  # This documentation
└── build_imagedescriber.bat   # Build script (to be created)
```

## Integration with Existing Tools

This GUI application is designed to:
- **Not break existing workflows**: All script functionality remains unchanged
- **Produce identical output**: Working directory appears the same as script processing
- **Use proven technology**: Leverages tested and reliable workflow scripts
- **Lower barriers**: Makes image description technology accessible to non-technical users

## Troubleshooting

### Common Issues
1. **No images appear**: Ensure the selected directory contains supported file formats
2. **Processing fails**: Check that required dependencies (Ollama, etc.) are installed
3. **HTML generation fails**: Verify that some images have been processed successfully

### Logging
The processing log (right panel) provides detailed information about:
- File operations and conversions
- AI processing status
- Error messages and debugging information

## Requirements

- Python 3.8+
- PyQt6
- Same dependencies as the main workflow scripts
- Access to the `scripts/` directory with workflow tools
