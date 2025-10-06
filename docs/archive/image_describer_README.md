# Image Describer - AI-Powered Image Description Tool

The `image_describer.py` script uses Ollama vision models to generate detailed, natural descriptions of images. It processes entire directories of images and creates comprehensive text-based descriptions with optional metadata extraction.

## 🚀 Quick Start

```bash
# Basic usage - process all images in a directory
python image_describer.py photos/

# With custom model and style
python image_describer.py photos/ --model llava:7b --prompt-style artistic

# Recursive processing with verbose output
python image_describer.py photos/ --recursive --verbose
```

## 📋 Features

- **Multiple AI Models**: Support for moondream, llava, llama3.2-vision, and other Ollama vision models
- **Customizable Prompts**: Six built-in prompt styles (detailed, concise, narrative, artistic, technical, colorful)
- **Metadata Extraction**: Optional EXIF data extraction and inclusion
- **Batch Processing**: Efficient processing of large image collections
- **Flexible Output**: Organized text descriptions with configurable formats
- **Resume Capability**: Skip already processed images
- **Size Optimization**: Automatic image resizing for optimal processing

## 🎯 Command Line Options

```bash
python image_describer.py [OPTIONS] DIRECTORY
```

### Required Arguments
- `directory`: Directory containing images to process

### Optional Arguments
- `--model MODEL`: Ollama vision model to use (default: from image_describer_config.json)
- `--recursive`: Process subdirectories recursively
- `--verbose`: Enable verbose logging
- `--max-size MAX_SIZE`: Maximum image dimension for processing (default: 1024)
- `--no-compression`: Disable image compression
- `--batch-delay BATCH_DELAY`: Delay between processing images in seconds (default: 2.0)
- `--max-files MAX_FILES`: Maximum number of files to process (for testing)
- `--config CONFIG`: Path to JSON configuration file (default: image_describer_config.json)
- `--output-dir OUTPUT_DIR`: Output directory for description file (default: workflow_output/descriptions/)
- `--prompt-style STYLE`: Style of prompt to use (default: Narrative)
- `--no-metadata`: Disable metadata extraction from image files

### Available Prompt Styles
- **detailed**: Comprehensive descriptions with technical details
- **concise**: Brief, focused descriptions
- **narrative**: Story-like descriptions (default)
- **artistic**: Creative, artistic interpretations
- **technical**: Technical analysis of image composition
- **colorful**: Emphasis on colors and visual elements

## ⚙️ Configuration

The script uses `image_describer_config.json` for configuration. See `CONFIGURATION.md` for detailed configuration options.

### Key Configuration Sections
- **models**: Available Ollama vision models
- **default_settings**: Default processing parameters
- **prompt_variations**: Customizable prompt styles
- **output_options**: Output formatting preferences
- **processing_options**: Image processing settings

## 📁 Output Structure

When using the workflow system (default), outputs are organized as:

```
workflow_output/
└── descriptions/
    └── image_descriptions.txt
```

The output file contains:
- Image filename and path
- AI-generated description
- Optional metadata (if enabled)
- Processing timestamp

## 💡 Usage Examples

### Basic Image Description
```bash
python image_describer.py family_photos/
```

### Custom Model and Style
```bash
python image_describer.py artwork/ --model llava:13b --prompt-style artistic
```

### Recursive Processing with Metadata
```bash
python image_describer.py photo_archive/ --recursive --prompt-style detailed
```

### Testing with Limited Files
```bash
python image_describer.py test_images/ --max-files 5 --verbose
```

### Custom Configuration
```bash
python image_describer.py photos/ --config custom_image_describer_config.json
```

### Custom Output Directory
```bash
python image_describer.py photos/ --output-dir custom_descriptions/
```

## 🔧 Integration with Workflow System

The image describer integrates seamlessly with the workflow system:

```bash
# Part of complete workflow
python workflow.py media_folder --steps describe,html

# Individual script with workflow output structure
python image_describer.py photos/
# → outputs to workflow_output/descriptions/
```

## 🛠️ Troubleshooting

### Common Issues

**"Ollama connection failed":**
- Ensure Ollama is running: `ollama serve`
- Test connectivity: `python debug_ollama.py`
- Check model availability: `ollama list`

**"No images found":**
- Verify directory path and image formats
- Check file permissions
- Use `--verbose` for detailed scanning output

**"Model not found":**
- Install required models: `ollama pull moondream`
- Check available models: `ollama list`
- Verify model name in configuration

**Memory issues with large images:**
- Reduce `--max-size` parameter
- Enable compression (remove `--no-compression`)
- Process smaller batches

### Performance Optimization

- **Batch Processing**: Use `--batch-delay` to control processing speed
- **Image Size**: Adjust `--max-size` for optimal balance of quality/speed
- **Model Selection**: Smaller models (moondream) are faster, larger models (llava:13b) more detailed
- **Parallel Processing**: Process multiple directories separately

## 📊 Output Format

### Text Description File
```
=== Image Descriptions ===
Generated: 2025-07-20 10:30:45

--- photo1.jpg ---
Path: /path/to/photos/photo1.jpg
Description: A beautiful sunset over the ocean with vibrant orange and pink colors reflecting on the calm water. The silhouette of palm trees frames the scene on the left side.

[Metadata if enabled]
Camera: Canon EOS R5
Focal Length: 24mm
ISO: 100
Aperture: f/8.0
Date Taken: 2025-07-15 18:45:23

--- photo2.jpg ---
[... continues for all processed images ...]
```

## 🔗 Related Tools

- **workflow.py**: Complete pipeline orchestration
- **descriptions_to_html.py**: Convert descriptions to HTML reports
- **video_frame_extractor.py**: Extract frames from videos for description
- **ConvertImage.py**: Convert HEIC files to JPG format

For complete system documentation, see `WORKFLOW_README.md`.
