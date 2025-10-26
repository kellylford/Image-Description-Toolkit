# Gallery Content Identification Guide

## Overview

The Gallery Content Identification tool (`identify_gallery_content.py`) automatically scans your described image content and identifies the best candidates for themed galleries based on configurable keyword matching and filtering rules.

**Key Benefits:**
- ✅ No script editing required - all configuration is external
- ✅ Reusable configurations for similar galleries
- ✅ Flexible keyword-based matching with scoring
- ✅ Works with any size content library
- ✅ Integrates with existing build_gallery.py workflow

## Quick Start

### Basic Usage

```bash
# Using a configuration file
cd tools/ImageGallery/content-creation
python identify_gallery_content.py --config example_configs/sunset_water.json

# Using command-line parameters
python identify_gallery_content.py \
  --name "My Gallery" \
  --scan ./descriptions \
  --required water,sun \
  --keywords sunset,reflection \
  --output results.json
```

### Typical Workflow

1. **Run IDT workflows** on your image collection
2. **Create or customize** a configuration file for your gallery theme
3. **Run identification** to find matching images
4. **Review results** and adjust criteria if needed
5. **Copy selected images** to gallery directory
6. **Build gallery** using build_gallery.py

## Configuration File Format

Configuration files use JSON format with four main sections:

```json
{
  "gallery_name": "Gallery Title",
  "sources": { /* where to scan */ },
  "content_rules": { /* keyword matching */ },
  "filters": { /* advanced filtering */ },
  "output": { /* result formatting */ }
}
```

### Full Example

```json
{
  "gallery_name": "Sunshine On The Water Makes Me Happy",
  "sources": {
    "directories": [
      "./descriptions",
      "//qnap/home/idt/descriptions"
    ],
    "workflow_patterns": ["*vacation*", "*travel*"],
    "date_range": {
      "start": "2025-01-01",
      "end": "2025-12-31"
    }
  },
  "content_rules": {
    "required_keywords": ["water", "sun"],
    "preferred_keywords": ["sunset", "sunrise", "reflection", "clouds"],
    "excluded_keywords": ["indoor", "night", "dark"],
    "min_keyword_matches": 2,
    "case_sensitive": false
  },
  "filters": {
    "min_description_length": 100,
    "preferred_prompts": ["narrative", "colorful"],
    "preferred_models": ["claude-opus-4"]
  },
  "output": {
    "max_images": 50,
    "sort_by": "keyword_relevance",
    "include_metadata": true
  }
}
```

## Configuration Reference

### sources

Defines where to scan for described content.

**directories** (array of strings, default: `["./descriptions"]`)
- List of directories containing workflow results
- Supports network paths (e.g., `//qnap/home/idt/descriptions`)
- Can scan multiple locations simultaneously

**workflow_patterns** (array of strings, default: `["*"]`)
- Workflow name patterns to include
- Supports simple wildcard matching
- Example: `["*europe*", "*vacation*"]` matches workflows with "europe" or "vacation" in the name

**date_range** (object, optional)
- Filter workflows by timestamp
- `start`: Start date in YYYY-MM-DD format
- `end`: End date in YYYY-MM-DD format
- Example: `{"start": "2025-10-01", "end": "2025-10-31"}`

### content_rules

Defines keyword matching rules for content identification.

**required_keywords** (array of strings, default: `[]`)
- Keywords that MUST be present in descriptions (AND logic)
- All required keywords must match or image is excluded
- Example: `["water", "sun"]` means descriptions must contain both

**preferred_keywords** (array of strings, default: `[]`)
- Keywords that are nice to have but not required
- Each match adds to the relevance score
- Example: `["sunset", "sunrise", "reflection"]`

**excluded_keywords** (array of strings, default: `[]`)
- Keywords that disqualify an image
- Any match immediately excludes the image
- Example: `["indoor", "night", "dark"]`

**min_keyword_matches** (integer, default: `1`)
- Minimum total keyword matches required (required + preferred)
- Higher values = more selective
- Example: `2` means at least 2 keywords must match

**case_sensitive** (boolean, default: `false`)
- Whether keyword matching is case-sensitive
- `false`: "Water" matches "water" (recommended)
- `true`: Only exact case matches count

### filters

Advanced filtering for fine-tuning results.

**min_description_length** (integer, default: `0`)
- Minimum character count for descriptions
- Use to ensure detailed descriptions
- Example: `100` requires at least 100 characters

**preferred_prompts** (array of strings, default: `[]`)
- Prompt styles that receive bonus points
- Values: `"narrative"`, `"colorful"`, `"technical"`, `"detailed"`
- Example: `["narrative", "colorful"]`

**preferred_models** (array of strings, default: `[]`)
- AI models that receive bonus points
- Example: `["claude-opus-4", "claude-sonnet-4", "gpt-4o"]`

### output

Controls output format and sorting.

**max_images** (integer, default: `50`)
- Maximum number of images to return
- `0` = unlimited
- Top-scoring images are selected first

**sort_by** (string, default: `"keyword_relevance"`)
- How to sort results
- `"keyword_relevance"`: Sort by score (highest first)
- `"filename"`: Sort alphabetically

**include_metadata** (boolean, default: `true`)
- Include provider/model/prompt in output
- Useful for understanding why images matched

## Command-Line Interface

For quick testing without creating configuration files.

### Required Arguments

At least one of these must be specified:
- `--config FILE`: Load configuration from JSON file
- `--required KEYWORDS`: Required keywords (comma-separated)
- `--keywords KEYWORDS`: Preferred keywords (comma-separated)

### Optional Arguments

**Gallery Settings:**
- `--name NAME`: Gallery name (default: "Untitled Gallery")

**Sources:**
- `--scan DIR [DIR ...]`: Directories to scan (default: ./descriptions)
- `--workflow-patterns PATTERNS`: Workflow patterns (comma-separated)
- `--date-start DATE`: Start date (YYYY-MM-DD)
- `--date-end DATE`: End date (YYYY-MM-DD)

**Keywords:**
- `--required KEYWORDS`: Required keywords (comma-separated)
- `--keywords KEYWORDS`: Preferred keywords (comma-separated)
- `--exclude KEYWORDS`: Excluded keywords (comma-separated)
- `--min-matches N`: Minimum keyword matches (default: 1)
- `--case-sensitive`: Use case-sensitive matching

**Filters:**
- `--min-length N`: Minimum description length (default: 0)
- `--prompts STYLES`: Preferred prompts (comma-separated)
- `--models MODELS`: Preferred models (comma-separated)

**Output:**
- `--max-images N`: Maximum images (default: 50, 0 = unlimited)
- `--sort-by METHOD`: Sort method (keyword_relevance or filename)
- `--no-metadata`: Exclude metadata from output
- `--output FILE`: Output file path (default: gallery_candidates.json)

### Examples

**Simple keyword search:**
```bash
python identify_gallery_content.py \
  --required water \
  --keywords ocean,lake,river \
  --output water_images.json
```

**Multiple directories:**
```bash
python identify_gallery_content.py \
  --scan ./descriptions //qnap/idt/descriptions \
  --required mountain \
  --keywords hiking,peak,summit
```

**With filters:**
```bash
python identify_gallery_content.py \
  --required sunset \
  --min-length 150 \
  --prompts narrative,colorful \
  --models claude-opus-4 \
  --max-images 30
```

**Date range filtering:**
```bash
python identify_gallery_content.py \
  --scan ./descriptions \
  --date-start 2025-10-01 \
  --date-end 2025-10-31 \
  --required autumn,fall
```

## Output Format

The tool generates a JSON file with identified candidates:

```json
{
  "gallery_name": "My Gallery",
  "generated_at": "2025-10-26T12:34:56",
  "configuration": {
    "required_keywords": ["water", "sun"],
    "preferred_keywords": ["sunset", "reflection"],
    "excluded_keywords": ["indoor"],
    "min_keyword_matches": 2,
    "max_images": 50
  },
  "total_candidates": 25,
  "candidates": [
    {
      "filename": "IMG_1234.jpg",
      "score": 25.0,
      "workflow_path": "./descriptions/wf_vacation_claude_opus_narrative_20251001_120000",
      "workflow_name": "vacation",
      "description": "A stunning sunset reflects on the calm water...",
      "match_details": {
        "required_matches": ["water", "sun"],
        "preferred_matches": ["sunset", "reflection"],
        "excluded_matches": [],
        "filter_bonuses": {
          "preferred_model": true,
          "preferred_prompt": true
        },
        "passes_filters": true
      },
      "provider": "claude",
      "model": "opus",
      "prompt_style": "narrative",
      "timestamp": "20251001_120000"
    }
  ]
}
```

## Scoring System

Images receive scores based on keyword matches and bonuses:

| Factor | Points | Description |
|--------|--------|-------------|
| Required keyword match | +10.0 | Each required keyword found |
| Preferred keyword match | +5.0 | Each preferred keyword found |
| Preferred model | +3.0 | Model in preferred_models list |
| Preferred prompt | +2.0 | Prompt in preferred_prompts list |
| Excluded keyword | -1000.0 | Immediate disqualification |

**Example Score Calculation:**
- 2 required keywords matched: 2 × 10 = 20 points
- 3 preferred keywords matched: 3 × 5 = 15 points
- Preferred model bonus: +3 points
- **Total: 38 points**

## Best Practices

### Keyword Selection

1. **Start broad, refine later**
   - Begin with 1-2 required keywords
   - Add preferred keywords liberally
   - Run and review results
   - Adjust based on what you see

2. **Use specific terms**
   - ❌ Too broad: "photo", "image", "picture"
   - ✅ Specific: "sunset", "reflection", "golden hour"

3. **Consider synonyms**
   - Include variations: "ocean", "sea", "water"
   - Cover different descriptions: "sunset", "dusk", "evening light"

4. **Use exclusions sparingly**
   - Only exclude clear mismatches
   - Too many exclusions = too restrictive

### Configuration Strategy

**Iteration Approach:**

1. **First run**: Very permissive
   ```json
   {
     "required_keywords": [],
     "preferred_keywords": ["water"],
     "min_keyword_matches": 1
   }
   ```

2. **Review results**: See what matched

3. **Second run**: Add requirements
   ```json
   {
     "required_keywords": ["water"],
     "preferred_keywords": ["sun", "sunset", "reflection"],
     "min_keyword_matches": 2
   }
   ```

4. **Fine-tune**: Adjust based on scores

### Common Patterns

**Themed Galleries:**
```json
{
  "required_keywords": ["theme_word"],
  "preferred_keywords": ["related", "terms", "variations"],
  "min_keyword_matches": 2
}
```

**Quality Filtering:**
```json
{
  "filters": {
    "min_description_length": 150,
    "preferred_prompts": ["detailed"],
    "preferred_models": ["claude-opus-4"]
  }
}
```

**Time-Based:**
```json
{
  "sources": {
    "date_range": {
      "start": "2025-10-01",
      "end": "2025-10-31"
    }
  }
}
```

## Integration with Workflow

### Complete Gallery Creation Process

1. **Describe Images**
   ```bash
   # Run IDT workflows
   idt workflow images/ --provider claude --model opus --prompt-style narrative
   idt workflow images/ --provider claude --model opus --prompt-style colorful
   ```

2. **Identify Content**
   ```bash
   # Find matching images
   cd tools/ImageGallery/content-creation
   python identify_gallery_content.py --config my_gallery.json --output candidates.json
   ```

3. **Review Results**
   ```bash
   # Check the output file
   cat candidates.json
   # Look at scores, matches, and descriptions
   ```

4. **Copy Images**
   ```bash
   # Manual selection based on results
   # Copy selected images to gallery
   cd ../galleries
   mkdir my-gallery
   mkdir my-gallery/images
   # Copy files listed in candidates.json
   ```

5. **Build Gallery**
   ```bash
   cd ../content-creation
   python build_gallery.py ../galleries/my-gallery/
   ```

6. **Deploy**
   ```bash
   # Upload gallery to web server
   rsync -av ../galleries/my-gallery/ user@server:/var/www/galleries/
   ```

## Troubleshooting

### No Candidates Found

**Problem:** Tool returns 0 matches

**Solutions:**
1. Check that directories exist and contain workflows
2. Verify workflow directories have `descriptions/image_descriptions.txt`
3. Try more permissive keywords
4. Remove or reduce `min_keyword_matches`
5. Check `date_range` isn't too restrictive

### Too Many Candidates

**Problem:** Tool returns hundreds of matches

**Solutions:**
1. Add more required keywords
2. Increase `min_keyword_matches`
3. Add excluded keywords for common themes
4. Use `min_description_length` filter
5. Reduce `max_images` limit

### Low Scores

**Problem:** All candidates have low scores

**Solutions:**
1. Review keyword selection - may be too strict
2. Add more preferred keywords
3. Check if preferred_models/prompts are too specific
4. Consider case sensitivity setting

### Wrong Theme

**Problem:** Results don't match intended gallery theme

**Solutions:**
1. Review match_details in output to see what matched
2. Add excluded keywords for unwanted themes
3. Make required keywords more specific
4. Increase min_keyword_matches

## Advanced Usage

### Multiple Configurations

Create variations for comparison:

```bash
# Conservative selection
python identify_gallery_content.py \
  --config strict_sunset.json \
  --output sunset_strict.json

# Liberal selection
python identify_gallery_content.py \
  --config loose_sunset.json \
  --output sunset_loose.json

# Compare results
```

### Batch Processing

Process multiple gallery themes:

```bash
for config in example_configs/*.json; do
  name=$(basename "$config" .json)
  python identify_gallery_content.py \
    --config "$config" \
    --output "candidates_${name}.json"
done
```

### Custom Scoring

Modify the script to adjust scoring weights:

```python
# In identify_gallery_content.py
# Current weights:
# - Required keyword: 10.0
# - Preferred keyword: 5.0
# - Model bonus: 3.0
# - Prompt bonus: 2.0
```

## Future Enhancements

Planned features for future versions:

- **Semantic search**: Use embeddings for "ocean" matching "water"
- **Visual similarity**: Group similar images
- **Machine learning**: Learn from user selections
- **Interactive UI**: Preview and approve candidates
- **Batch gallery generation**: Create multiple galleries from one config
- **Synonym expansion**: Automatic related term detection
- **EXIF filtering**: Time of day, camera settings, location

## See Also

- [JSON Schema](../gallery_config_schema.json) - Complete configuration specification
- [Example Configs](example_configs/) - Ready-to-use gallery configurations
- [Build Gallery Guide](BUILD_GALLERY_README.md) - Next steps after identification
- [ImageGallery README](../README.md) - Overall gallery system documentation

## Support

For issues or questions:
1. Check this guide and examples
2. Review output JSON for clues
3. Test with example configurations
4. Open GitHub issue with configuration and output

---

**Version:** 1.0.0  
**Last Updated:** October 26, 2025
