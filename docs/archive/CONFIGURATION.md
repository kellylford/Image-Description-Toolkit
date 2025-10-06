# ImageDescriber Configuration Guide

## Overview

The ImageDescriber uses a comprehensive configuration system that allows you to customize every aspect of how images are analyzed and described. This guide explains all configuration options and how to use them effectively.

## Configuration Structure

The `image_describer_config.json` file contains five main sections:

### 1. Model Settings
Controls how the AI vision model behaves:

```json
{
  "model_settings": {
    "model": "moondream",        // Default model to use
    "temperature": 0.1,          // Creativity level (0.0-1.0)
    "num_predict": 600,          // Max description length
    "top_k": 40,                 // Token selection diversity
    "top_p": 0.9,                // Response focus level
    "repeat_penalty": 1.3        // Repetition avoidance
  }
}
```

**Model Options:**
- `moondream`: Compact and efficient (1.7B parameters) - **Recommended**
- `llama3.2-vision`: High-quality descriptions (11B parameters)
- `llava:7b`: Good balance of speed and quality
- `llava:13b`: Higher quality, slower processing

**Temperature Guidelines:**
- `0.1`: Very consistent, predictable descriptions
- `0.3`: Good balance of consistency and variation
- `0.5`: Moderate creativity
- `0.7+`: High creativity, less predictable

**Length Guidelines:**
- `200`: Short descriptions (1-2 sentences)
- `400`: Medium descriptions
- `600`: Long descriptions (recommended)
- `800+`: Very detailed descriptions
- `600`: Long descriptions (detailed paragraphs)
- `800+`: Very long descriptions (may cause memory issues)

### 2. Prompt Variations
Different styles for different needs:

```json
{
  "prompt_variations": {
    "detailed": "Comprehensive descriptions...",
    "concise": "Brief but informative...",
    "artistic": "Focus on artistic elements...",
    "technical": "Technical photography analysis...",
    "narrative": "Story-like descriptions...",
    "colorful": "Emphasis on colors and lighting...",
    "your_custom_style": "Your custom prompt here..."
  }
}
```

**Built-in Styles:**
- **detailed**: Best for general use, comprehensive coverage
- **concise**: Good for metadata, saves processing time
- **artistic**: Great for art analysis, creative projects
- **technical**: Perfect for photography analysis
- **narrative**: Focuses on objects, colors, and composition
- **colorful**: Emphasizes visual aesthetics and atmosphere

### 3. Output Format
Controls how results are saved:

```json
{
  "output_format": {
    "include_timestamp": true,    // When each image was processed
    "include_model_info": true,   // Model and prompt style used
    "include_file_path": true,    // Full path to image file
    "include_metadata": true,     // Include extracted EXIF data
    "separator": "-"              // Character between entries
  }
}
```

### 4. Processing Options
Performance and compatibility settings:

```json
{
  "processing_options": {
    "default_max_image_size": 1024,  // Max dimension in pixels
    "default_batch_delay": 1.0,      // Seconds between images
    "default_compression": true,      // Enable image compression
    "extract_metadata": true,         // Extract EXIF metadata
    "supported_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]
  }
}
```

## Setting the Default Prompt Style

You can set which prompt style is used by default (when no `--prompt-style` is specified) by editing the JSON file directly.

### Direct JSON Editing
Edit `image_describer_config.json` and change the `default_prompt_style` value:
```json
{
  "default_prompt_style": "artistic",
  "prompt_variations": {
    "detailed": "...",
    "artistic": "...",
    "concise": "..."
  }
}
```


The default style must match one of the keys in `prompt_variations`. If an invalid style is specified, the system will fall back to "detailed" or the first available style.

## Usage Examples

### Basic Usage
```bash
# Use default settings
python image_describer.py photos

# Use specific prompt style
python image_describer.py photos --prompt-style artistic

# Use custom config file
python image_describer.py photos --config my_image_describer_config.json
```

### Memory Optimization
```bash
# Reduce memory usage
python image_describer.py photos --max-size 512 --batch-delay 2.0

# Use smaller model
python image_describer.py photos --model moondream --max-size 512

# Process limited files for testing
python image_describer.py photos --max-files 5

### Direct Editing
Edit `image_describer_config.json` and add to `prompt_variations`:
```json
{
  "prompt_variations": {
    "my_style": "Your custom prompt here. Focus on what matters to you..."
  }
}
```

### Method 3: Multiple Configs
Create different config files for different projects:
```bash
# config_artistic.json for art projects
# config_technical.json for technical analysis  
# config_minimal.json for quick processing
```

## Best Practices

### For Consistency
- Use low temperature (0.1-0.2)
- Use same prompt style for similar images
- Process images in batches with same settings

### For Quality
- Use higher num_predict (400-600) for detailed descriptions
- Use full image size when possible
- Choose appropriate prompt style for your images

### For Performance
- Use smaller models (llava:7b instead of llama3.2-vision)
- Reduce image size (--max-size 512)
- Add batch delays (--batch-delay 2.0)
- Enable compression (default)

### For Organization
- Use descriptive prompt style names
- Include timestamps and model info in output
- Keep separate configs for different projects
- Document custom prompt styles

## Troubleshooting

### Common Issues

**Memory Problems:**
- Reduce `max_image_size` to 512 or lower
- Increase `batch_delay` to 2.0 or higher
- Use smaller model (llava:7b)
- Lower `num_predict` to 200-300

**Inconsistent Descriptions:**
- Lower `temperature` to 0.1-0.2
- Use same prompt style for all images
- Check that model is properly loaded

**Descriptions Too Short/Long:**
- Adjust `num_predict` (200 = short, 600 = long)
- Modify prompt style to be more/less detailed
- Check temperature isn't too high

## Advanced Configuration

### Environment-Specific Configs
Create different configurations for different environments:

```bash
# development.json - faster processing, lower quality
# production.json - high quality, slower processing
# testing.json - limited files, quick validation
```

### Batch Processing Scripts
Create wrapper scripts for common tasks:

```bash
# process_artwork.bat
python image_describer.py %1 --config artistic_image_describer_config.json --prompt-style artistic

# process_photos.bat  
python image_describer.py %1 --config photo_image_describer_config.json --prompt-style technical
```

### Integration with Other Tools
The output format is designed to be easily parsed by other tools:

```python
# Parse output file
with open('image_descriptions.txt', 'r') as f:
    content = f.read()
    entries = content.split('-' * 80)
    # Process each entry...
```
