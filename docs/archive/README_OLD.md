# ImageDescriber - AI-Powered Image Analysis Tool

A comprehensive Python toolkit for processing images using Ollama's vision models to generate detailed descriptions and extract metadata. The project includes both an image description system and a HEIC to JPG converter utility. A script to convert descriptions to an HTML page is also included.

**🚀 NEW: [Workflow System](WORKFLOW_README.md)** - Automated end-to-end processing pipeline that orchestrates all tools together while maintaining full backward compatibility!

## Features

- **🔗 Automated Workflow System**: Complete pipeline from videos/images to HTML reports ([see WORKFLOW_README.md](WORKFLOW_README.md))
- **AI-Powered Descriptions**: Generate detailed descriptions using Ollama vision models (moondream, llama3.2-vision, llava, etc.)
- **Video Frame Extraction**: Extract frames from videos for analysis
- **Batch Processing**: Process entire directories of images efficiently
- **Recursive Processing**: Optionally process subdirectories recursively
- **EXIF Metadata Extraction**: Extract camera settings, GPS location, and photo timestamps
- **Multiple Output Formats**: Save descriptions to text files with comprehensive metadata
- **HTML Web Gallery**: Convert descriptions to beautiful, responsive HTML pages
- **Memory Optimization**: Built-in memory management for large image collections
- **Flexible Configuration**: JSON-based configuration system with multiple prompt styles
- **HEIC Conversion**: Convert HEIC/HEIF images to JPG format with metadata preservation
- **Accessibility Compliant**: HTML output meets WCAG 2.1 standards
- **Supported Formats**: JPG, JPEG, PNG, BMP, TIFF, WebP (plus HEIC conversion)
- **Robust Error Handling**: Continues processing even if individual images fail
- **Detailed Logging**: Comprehensive logging with progress tracking

## Prerequisites

1. **Ollama**: Make sure Ollama is installed and running on your system
   - Download from: https://ollama.com/
   - Install a vision model (recommended): `ollama pull moondream`
   - Alternative models: `ollama pull llama3.2-vision` or `ollama pull llava`

2. **Python 3.8+**: This script requires Python 3.8 or higher

## Installation

1. Clone or download this repository
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

- **🚀 `workflow.py`** - **NEW**: Complete workflow orchestrator ([see WORKFLOW_README.md](WORKFLOW_README.md))
- **🔧 `workflow_utils.py`** - **NEW**: Shared workflow utilities
- **⚙️ `workflow_config.json`** - **NEW**: Workflow configuration
- `image_describer.py` - Main image description script (now workflow-enhanced)
- `video_frame_extractor.py` - Video frame extraction tool
- `descriptions_to_html.py` - HTML converter for description files
- `ConvertImage.py` - HEIC to JPG converter utility
- `image_describer_config.json` - Configuration file with model settings and prompts
- `video_frame_extractor_config.json` - Video extraction configuration
- `requirements.txt` - Complete dependencies for all functionality
- `image_describer_README.md` - Documentation for the AI image description tool
- `video_frame_extractor_README.md` - Documentation for video processing tools
- `ConvertImage_README.md` - Documentation for HEIC conversion tool  
- `descriptions_to_html_README.md` - Documentation for the HTML converter tool
- **📖 `WORKFLOW_README.md`** - **NEW**: Complete workflow system documentation

## Quick Start

### 🚀 New Workflow System (Recommended)
```bash
# Complete automated pipeline
python workflow.py media_folder

# Specific steps only  
python workflow.py photos --steps describe,html
python workflow.py videos --steps video,describe,html

# See WORKFLOW_README.md for complete documentation
```

### Individual Tools (Still Work Unchanged)

### Image Description Tool

#### Command Line Interface

```bash
python image_describer.py <directory> [options]
```

**Arguments:**
- `directory`: Path to the directory containing images to process

**Options:**
- `--model`: Ollama vision model to use (default: from image_describer_config.json)
- `--prompt-style`: Style of prompt to use (detailed, concise, artistic, technical, etc.)
- `--recursive`: Process subdirectories recursively
- `--verbose`: Enable verbose logging
- `--max-size`: Maximum image dimension for processing (default: 1024)
- `--no-compression`: Disable image compression optimization
- `--batch-delay`: Delay between processing images in seconds (default: 1.0)
- `--max-files`: Maximum number of files to process (for testing)
- `--config`: Path to configuration file (default: image_describer_config.json)
- `--no-metadata`: Disable metadata extraction from image files

#### Examples

1. **Process images in a directory:**
   ```bash
   python image_describer.py "photos/"
   ```

2. **Process images recursively with verbose output:**
   ```bash
   python image_describer.py "photos/" --recursive --verbose
   ```

3. **Use a specific model and prompt style:**
   ```bash
   python image_describer.py "photos/" --model moondream --prompt-style artistic
   ```

4. **Memory-optimized processing for large collections:**
   ```bash
   python image_describer.py "photos/" --max-size 512 --batch-delay 2.0
   ```

5. **Testing with limited files:**
   ```bash
   python image_describer.py "photos/" --max-files 5 --verbose
   ```

### HEIC Converter Tool

#### Command Line Interface

```bash
python ConvertImage.py <input> [options]
```

**Arguments:**
- `input`: Path to HEIC file or directory containing HEIC files

**Options:**
- `--output`: Output directory (default: same as input)
- `--quality`: JPEG quality 1-100 (default: 90)
- `--recursive`: Process subdirectories recursively
- `--preserve-metadata`: Keep original EXIF data
- `--overwrite`: Overwrite existing files
- `--verbose`: Enable verbose logging

#### Examples

1. **Convert a single HEIC file:**
   ```bash
   python ConvertImage.py photo.heic
   ```

2. **Convert all HEIC files in a directory:**
   ```bash
   python ConvertImage.py "heic_photos/" --recursive --quality 85
   ```

3. **Convert with metadata preservation:**
   ```bash
   python ConvertImage.py "heic_photos/" --preserve-metadata --output "converted/"
   ```

### HTML Converter Tool

The HTML converter transforms the text files generated by ImageDescriber into beautiful, web-ready HTML pages with proper formatting and styling.

#### Command Line Interface

```bash
python descriptions_to_html.py [input_file] [output_file] [options]
```

**Arguments:**
- `input_file`: Text file with image descriptions (default: image_descriptions.txt)
- `output_file`: Output HTML file (default: input_file with .html extension)

**Options:**
- `--title`: Title for the HTML page (default: "Image Descriptions")
- `--full`: Include full details section with metadata for each image
- `--verbose`: Enable verbose output

#### Examples

1. **Convert descriptions to HTML (minimal view):**
   ```bash
   python descriptions_to_html.py
   ```

2. **Convert with full metadata details:**
   ```bash
   python descriptions_to_html.py --full
   ```

3. **Convert with custom title:**
   ```bash
   python descriptions_to_html.py --title "My Photo Gallery" --full
   ```

4. **Convert specific files:**
   ```bash
   python descriptions_to_html.py vacation_descriptions.txt vacation_gallery.html --full
   ```

#### HTML Features

- **Responsive Design**: Mobile-friendly layout with clean typography
- **Two Display Modes**: 
  - **Minimal**: Photo names and descriptions only (default)
  - **Full**: Complete metadata including camera settings, GPS, timestamps
- **Table of Contents**: Automatically generated for collections with 5+ images
- **Professional Styling**: Color-coded sections with modern CSS
- **Print-Friendly**: Optimized for both screen and print viewing

#### Typical Workflow

1. **Generate descriptions:**
   ```bash
   python image_describer.py "photos/"
   ```

2. **Convert to HTML:**
   ```bash
   python descriptions_to_html.py --full --title "My Photo Collection"
   ```

3. **Open in browser:**
   ```bash
   start image_descriptions.html  # Windows
   open image_descriptions.html   # macOS
   ```

For detailed HTML converter documentation, see `descriptions_to_html_README.md`.

## Configuration

The ImageDescriber uses a comprehensive JSON configuration system stored in `image_describer_config.json`. This allows you to customize model settings, prompts, and output formats without modifying the code.

### Configuration Structure

```json
{
  "model_settings": {
    "model": "moondream",          // Default model to use
    "temperature": 0.1,            // Response creativity (0.0-1.0)
    "num_predict": 600,            // Maximum description length
    "top_k": 40,                   // Token selection diversity
    "top_p": 0.9,                  // Response focus level
    "repeat_penalty": 1.3          // Repetition avoidance
  },
  "prompt_variations": {
    "detailed": "Describe this image in detail...",
    "concise": "Describe this image concisely...",
    "artistic": "Analyze this image from an artistic perspective...",
    "technical": "Provide a technical analysis...",
    "narrative": "Provide a narrative description..."
  },
  "processing_options": {
    "extract_metadata": true,      // Extract EXIF metadata
    "supported_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]
  },
  "output_format": {
    "include_timestamp": true,     // Include processing timestamp
    "include_model_info": true,    // Include model information
    "include_file_path": true,     // Include file path
    "include_metadata": true,      // Include extracted metadata
    "separator": "-"               // Entry separator character
  }
}
```

### Available Models

The system supports various Ollama vision models:

- **moondream**: Compact and efficient (1.7B parameters) - **Recommended**
- **llama3.2-vision**: High-quality descriptions (11B parameters)
- **llava**: Various sizes available (7B, 13B, 34B)
- **llava:7b**: Good balance of speed and quality
- **llava:13b**: Higher quality, slower processing

### Prompt Styles

The system includes several built-in prompt styles:

- **detailed**: Comprehensive descriptions with all elements
- **concise**: Brief but informative descriptions  
- **artistic**: Focus on artistic and compositional elements
- **technical**: Technical analysis of photography aspects
- **narrative**: Story-like descriptions focusing on objects and colors

You can add custom prompt styles by editing the `image_describer_config.json` file.

### Memory Optimization Options

The ImageDescriber includes several memory optimization features:

- `--max-size`: Maximum image dimension (default: 1024) - reduces memory usage
- `--no-compression`: Disable image compression optimization  
- `--batch-delay`: Delay between images in seconds (default: 1.0) - allows memory cleanup
- `--max-files`: Limit number of files to process (useful for testing)

### Python API

You can also use the `ImageDescriber` class directly in your Python code:

```python
from pathlib import Path
from image_describer import ImageDescriber

# Create an instance
describer = ImageDescriber(
    model_name="moondream",
    prompt_style="artistic",
    config_file="image_describer_config.json"
)

# Process a single image
image_path = Path("path/to/image.jpg")
description = describer.get_image_description(image_path)
print(description)

# Process a directory
directory_path = Path("path/to/images")
describer.process_directory(directory_path, recursive=True)
```

## How It Works

### Image Description Process

1. **Image Detection**: Scans the specified directory for supported image formats
2. **Metadata Extraction**: Extracts EXIF data including camera settings, GPS location, and timestamps
3. **Image Optimization**: Resizes and compresses images for optimal processing
4. **Description Generation**: Uses Ollama's vision model to analyze each image and generate descriptions
5. **Output Generation**: Saves descriptions to text files with comprehensive metadata

### Output Format

The system generates `image_descriptions.txt` files containing:

```
File: IMG_001.jpg
Path: /path/to/IMG_001.jpg
Photo Date: 2024-01-15 14:30:22
Location: GPS: 37.7749, -122.4194, Altitude: 10.0m
Camera: Canon EOS R5, Lens: RF 24-70mm F2.8 L IS USM
Settings: ISO: 200, Aperture: f/2.8, Shutter Speed: 1/500s, Focal Length: 35mm
Model: moondream
Prompt Style: artistic
Description: A vibrant sunset over the ocean with dramatic orange and pink clouds...
Timestamp: 2024-01-15 15:45:30
--------------------------------------------------------------------------------
```

### Extracted Metadata

The system extracts the following metadata from images:

- **Date/Time**: When the photo was taken
- **GPS Location**: Latitude, longitude, and altitude (if available)
- **Camera Info**: Make, model, and lens information
- **Technical Settings**: ISO, aperture, shutter speed, focal length

## Supported Image Formats

### Image Description Tool
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- WebP (.webp)

### HEIC Converter Tool
- HEIC (.heic)
- HEIF (.heif)

## Error Handling

Both tools include robust error handling:
- Continues processing even if individual images fail
- Logs detailed error messages for troubleshooting
- Validates Ollama availability before processing (ImageDescriber)
- Checks for model availability (ImageDescriber)
- Handles corrupted or unsupported files gracefully

## Logging

The system provides detailed logging information:
- Progress tracking for batch processing
- Success/failure status for each image
- Error messages with specific details
- Summary statistics at completion
- Memory usage optimization logging

## Troubleshooting

### Common Issues

1. **Ollama not available:**
   - Make sure Ollama is installed and running
   - Check if the service is running: `ollama list`

2. **Model not found:**
   - Install the required model: `ollama pull moondream`
   - Check available models: `ollama list`

3. **Permission errors:**
   - Ensure you have read/write permissions for the image directory
   - Some image formats may be read-only

4. **Memory issues:**
   - **Try lighter models**: `moondream` or `llava:7b` instead of `llama3.2-vision`
   - **Reduce image size**: Use `--max-size 512` or smaller
   - **Process fewer images**: Use `--max-files 10` for testing
   - **Increase delays**: Use `--batch-delay 2.0` for more time between images
   - **Close other applications** to free up memory

5. **HEIC conversion issues:**
   - Install required dependencies: `pip install pillow pillow-heif`
   - On some systems, additional system libraries may be needed

### Performance Tips

- Use `moondream` model for fastest processing
- Reduce `--max-size` to 512 or 256 for large image collections
- Use `--batch-delay 1.0` or higher for memory-constrained systems
- Process images in smaller batches using `--max-files`
- Convert HEIC files to JPG first if processing many HEIC images

## Performance Considerations

- Processing time depends on image size, model complexity, and hardware
- Vision models require significant computational resources
- Consider processing images in batches for large directories
- Network latency may affect processing if Ollama is running remotely
- HEIC conversion is generally fast but depends on image size and quality settings

## License

This project is provided as-is for educational and personal use. Please ensure you have the necessary rights to process and modify your images.

## Contributing

Feel free to submit issues and enhancement requests! The project welcomes contributions for:
- New prompt styles
- Additional vision model support
- Performance improvements
- Bug fixes
- Documentation improvements

## Additional Resources

- [Ollama Documentation](https://ollama.com/)
- [Supported Vision Models](https://ollama.com/library?search=vision)
- [PIL/Pillow Documentation](https://pillow.readthedocs.io/)
- [EXIF Data Standards](https://exiv2.org/tags.html)
