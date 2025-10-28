# Web Image Download Feature

## Overview

IDT now supports downloading images directly from web pages, making it easy to describe images from online galleries, portfolios, or any web page containing images.

## Usage

### Basic Usage

Download images from a URL and describe them:

```bash
idt workflow --url https://example.com/gallery --steps download,describe,html
```

### With Options

Filter images by size and limit the number of downloads:

```bash
idt workflow --url https://example.com/photos \
  --min-size 300x300 \
  --max-images 50 \
  --steps download,describe,html
```

### Full Example with AI Provider

```bash
idt workflow --url https://example.com/gallery \
  --min-size 200x200 \
  --max-images 100 \
  --provider openai \
  --model gpt-4o-mini \
  --api-key-file openai.txt \
  --steps download,describe,html \
  --output-dir my_web_gallery
```

## Command-Line Arguments

### New Arguments for Web Download

- `--url URL`: URL of the web page to download images from (alternative to input_dir)
- `--min-size WIDTHxHEIGHT`: Minimum image size for downloads (e.g., `200x200`)
  - Only images larger than this size will be downloaded
  - Helps filter out icons, buttons, and other small graphics
- `--max-images N`: Maximum number of images to download
  - Limits the total number of images to prevent downloading too many

### How It Works

1. **Fetch Page**: The tool fetches the HTML content from the specified URL
2. **Extract URLs**: It parses the HTML to find all image URLs:
   - Images in `<img>` tags (including `src` and `data-src` attributes)
   - Images in `<picture>` elements
   - Direct links to image files in `<a>` tags
3. **Download Images**: Each image is:
   - Downloaded and validated as a real image file
   - Checked against size requirements (if specified)
   - Checked for duplicates (same image content)
   - Saved with a clean, safe filename
4. **Continue Workflow**: Downloaded images are then processed by subsequent steps (describe, html)

## Workflow Integration

The `download` step integrates seamlessly with existing workflow steps:

```bash
# Download and describe only
idt workflow --url https://example.com/gallery --steps download,describe

# Download, describe, and generate HTML report
idt workflow --url https://example.com/gallery --steps download,describe,html

# Can be combined with other steps (though not typically useful)
idt workflow --url https://example.com/gallery --steps download,convert,describe,html
```

## Features

### Duplicate Detection

The downloader automatically detects and skips duplicate images based on their content (using MD5 hashing), not just their URLs. This means:
- The same image from different URLs is only downloaded once
- Bandwidth and storage are conserved

### Size Filtering

Use `--min-size` to filter out small images like icons, logos, and thumbnails:

```bash
# Only download images at least 400x400 pixels
idt workflow --url https://example.com/gallery --min-size 400x400
```

### Safe Filenames

Downloaded images are given safe, filesystem-friendly filenames:
- Special characters are removed
- Numeric sequence ensures uniqueness
- Original extensions are preserved when possible

### Progress Tracking

The workflow logs track download progress:
```
[DONE] Image download complete (25 images)
```

## Technical Details

### Supported Image Formats

The downloader recognizes these image file extensions:
- `.jpg`, `.jpeg`
- `.png`
- `.gif`
- `.bmp`
- `.webp`
- `.tiff`, `.tif`

### Image Validation

Every downloaded file is validated to ensure it's a real image:
- Opens with PIL/Pillow to verify format
- Checks dimensions for size requirements
- Rejects corrupted or invalid files

### User Agent

The downloader uses a standard browser user agent to ensure compatibility with most websites:
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

### Rate Limiting

To be respectful to web servers, the downloader:
- Adds a 0.5 second delay between downloads
- Uses a reasonable timeout (30 seconds default)

## Limitations

1. **JavaScript-Rendered Content**: Images loaded dynamically by JavaScript may not be detected (static HTML parsing only)
2. **Authentication**: Password-protected or login-required pages are not supported
3. **Rate Limits**: Some websites may block or throttle excessive requests
4. **Robots.txt**: The tool does not currently check robots.txt files
5. **Legal Considerations**: Users are responsible for complying with website terms of service and copyright laws

## Examples

### Art Portfolio Website

```bash
idt workflow --url https://artist-portfolio.example.com \
  --min-size 500x500 \
  --max-images 30 \
  --steps download,describe,html \
  --name "ArtistPortfolio" \
  --output-dir art_descriptions
```

### Product Gallery

```bash
idt workflow --url https://store.example.com/products \
  --min-size 300x300 \
  --steps download,describe \
  --provider openai \
  --model gpt-4o-mini \
  --api-key-file openai.txt
```

### News Article with Images

```bash
idt workflow --url https://news.example.com/article/12345 \
  --steps download,describe,html \
  --output-dir news_article_images
```

## Troubleshooting

### No Images Downloaded

**Problem**: The command runs but no images are downloaded.

**Solutions**:
1. Check if the URL is correct and accessible
2. View the page in a browser to confirm it has images
3. Try without `--min-size` to see if size filtering is too restrictive
4. Add `--verbose` to see detailed logging
5. Some images may be loaded by JavaScript (not supported)

### Connection Errors

**Problem**: "Failed to fetch web page" or timeout errors.

**Solutions**:
1. Check your internet connection
2. Verify the URL is accessible in a browser
3. Some websites may block automated requests
4. Try increasing the timeout (currently not exposed, but default is 30s)

### Size Filtering Not Working

**Problem**: Small images are still being downloaded despite `--min-size`.

**Solutions**:
1. The size check happens after download (validation step)
2. Check the log output to see which images were skipped
3. Images are downloaded briefly to check their size, then discarded if too small

## Dependencies

The web download feature requires:
- `requests>=2.25.0` - HTTP requests
- `beautifulsoup4>=4.9.0` - HTML parsing
- `Pillow>=10.0.0` - Image validation

These are included in the standard `requirements.txt`.

## See Also

- [Workflow Documentation](../WORKFLOW_README.md)
- [Image Describer Guide](../IMAGE_DESCRIBER_GUIDE.md)
- [API Configuration](../OPENAI_SETUP_GUIDE.md)
