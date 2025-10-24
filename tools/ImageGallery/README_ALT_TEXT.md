# Image Gallery Alt Text Implementation

## Overview

The Image Gallery now supports accessibility through alt text generation and display. Alt text provides concise, meaningful descriptions of images for screen readers and users with visual impairments.

## How It Works

### Alt Text Storage
- Alt text is stored in the JSON configuration files alongside image descriptions
- Each image entry can have an optional `alt_text` field
- Alt text is generated using Claude Haiku 3.5 for consistency and quality

### Alt Text Display
- The website automatically loads alt text from the currently selected configuration (Provider + Model + Prompt)
- If no alt text is available in the current configuration, it falls back to preferred configurations:
  1. `claude_claude-3-5-haiku-20241022_narrative`
  2. `claude_claude-3-haiku-20240307_narrative` 
  3. `openai_gpt-4o-mini_narrative`
- If no alt text is found, it uses the filename as fallback

### JSON Structure
```json
{
  "provider": "claude",
  "model": "claude-3-5-haiku-20241022", 
  "prompt_style": "narrative",
  "images": {
    "example.jpg": {
      "description": "Detailed description...",
      "alt_text": "Concise alt text for accessibility",
      "provider": "claude",
      "model": "claude-3-5-haiku-20241022",
      "prompt_style": "narrative",
      "timestamp": "2025-10-23 10:08:24"
    }
  }
}
```

## Adding Alt Text to Your Images

### Method 1: Automated Generation (Recommended)

1. **Set up Claude API key:**
   ```batch
   set ANTHROPIC_API_KEY=your_key_here
   ```

2. **Run the alt text generation script:**
   ```batch
   generate_alt_text.bat
   ```
   Or directly:
   ```bash
   python generate_alt_text.py
   ```

This will:
- Process all JSON files in the `descriptions/` directory
- Generate alt text for each image using Claude Haiku 3.5
- Add `alt_text` field to each image entry
- Create backups of original files

### Method 2: Manual Addition

Edit JSON files directly to add alt text:

```json
"alt_text": "Brief, descriptive alt text (35-45 words recommended)"
```

## Alt Text Guidelines

### Quality Standards
- **Concise:** 35-45 words typically (based on Claude Haiku evaluation)
- **Descriptive:** Focus on key visual elements and context
- **Accessible:** Written for screen reader users
- **Consistent:** Use similar style across images

### Examples
- ✅ Good: "Suburban residential street with two-story houses, parked cars, and concrete sidewalk under a clear blue sky with white clouds"
- ❌ Too long: "Here's a detailed description of the image: The scene depicts a suburban residential street on a clear, bright day with a vivid blue sky dotted with white puffy clouds..."
- ❌ Too short: "Houses and cars"

## Important Technical Note: Direct Image Alt Text Generation

**Issue Identified (October 2024)**: When using vision AI models to generate alt text directly from images (using prompts like "Write 30 words of alt text"), all tested models consistently ignore word limits and produce detailed descriptions instead.

### Tested Models & Results:
- **Claude 3.5 Haiku**: Ignores "30 words maximum" instruction, produces 200+ word detailed descriptions
- **Claude Opus 4**: Ignores word limits, produces even longer detailed descriptions  
- **Gemma3**: Completely ignores alt text instruction, responds with "detailed description suitable for metadata"

### Root Cause:
Vision AI models appear to be fundamentally trained to provide comprehensive descriptions when viewing images, overriding specific brevity instructions.

### Working Solution:
The **two-step process** used by this Image Gallery system:
1. Generate detailed descriptions from images (what models do naturally)
2. Convert existing descriptions to alt text using text-to-text processing (works reliably)

This explains why the Image Gallery alt text generation script works perfectly while direct image-to-alt-text generation fails consistently across all providers.

## Testing Alt Text

1. **Open the Image Gallery** in your browser
2. **Select configuration:** Choose Provider, Model, and Prompt 
3. **Navigate images:** Use Previous/Next buttons
4. **Check alt text:**
   - Right-click image → Inspect Element
   - Look for `alt` attribute on the `<img>` tag
   - Or use screen reader software

## Browser Console Logging

The website logs alt text loading in the browser console:
```
Updated alt text for photo-20825_singular_display_fullPicture.jpg: Suburban residential street with two-story houses...
```

## File Structure

```
tools/ImageGallery/
├── descriptions/           # JSON files with descriptions and alt text
├── images/                # JPG images 
├── index.html            # Main gallery (with alt text support)
├── generate_alt_text.py  # Alt text generation script
├── generate_alt_text.bat # Windows batch wrapper
└── README_ALT_TEXT.md    # This file
```

## Accessibility Benefits

- **WCAG 2.2 AA Compliance**: Meets accessibility standards
- **Screen Reader Support**: Provides meaningful image descriptions
- **Low Vision Users**: Alt text appears in some assistive technologies
- **SEO Benefits**: Search engines can understand image content
- **Robust Fallbacks**: Always provides some form of alt text

## Cost Analysis

Based on evaluation of 185 alt text generations:
- **Cost:** ~$0.03 for 5 images across 37 configurations
- **Rate:** ~$0.006 per configuration per image
- **Full dataset estimate:** ~$6-7 for 25 images × 38 configurations

## Troubleshooting

### Alt Text Not Loading
1. Check browser console for errors
2. Verify JSON files contain `alt_text` fields
3. Ensure selected configuration exists
4. Check network tab for failed JSON requests

### Alt Text Generation Fails
1. Verify `ANTHROPIC_API_KEY` is set correctly
2. Check internet connection
3. Review rate limiting (script includes 1-second delays)
4. Ensure Claude API account has sufficient credits

### Performance Issues
- Alt text loads asynchronously after image loads
- No performance impact on initial page load
- Cached after first load per configuration

## Future Enhancements

- Batch alt text updates via UI
- Alt text quality validation
- Multi-language alt text support
- Integration with automated workflows