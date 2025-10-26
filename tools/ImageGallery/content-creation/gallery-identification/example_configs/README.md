# Gallery Configuration Examples

This directory contains example configuration files for the `identify_gallery_content.py` tool. Each file demonstrates how to configure the tool for different gallery themes.

## Available Examples

### sunset_water.json
**Theme:** "Sunshine On The Water Makes Me Happy"
- Required: Images with both water and sun
- Preferred: Sunset, sunrise, reflections, clouds, moon, golden hour
- Excludes: Indoor, night, dark, stormy scenes
- Best for: Serene water scenes with beautiful lighting

### mountains.json
**Theme:** "Mountain Adventures"
- Required: Mountain imagery
- Preferred: Hiking, peaks, summits, trails, alpine, valleys
- Excludes: Indoor, urban, city scenes
- Best for: Outdoor adventure and mountain landscape galleries

### architecture.json
**Theme:** "Urban Architecture"
- Required: Buildings
- Preferred: Architecture, skyscrapers, modern design, glass, steel
- Excludes: Nature, forest, ocean, mountain
- Best for: Urban and architectural photography

### wildlife.json
**Theme:** "Wildlife and Nature"
- Preferred: Animals, birds, wildlife, various species
- Excludes: Indoor, pets, domestic animals, urban
- Best for: Wildlife and nature photography collections

### food.json
**Theme:** "Food Photography"
- Required: Food
- Preferred: Dishes, plates, meals, cuisine, restaurant
- Excludes: Landscapes, nature, buildings
- Best for: Culinary and food photography galleries

## Using These Examples

### Method 1: Use directly
```bash
python identify_gallery_content.py --config example_configs/sunset_water.json
```

### Method 2: Copy and customize
```bash
cp example_configs/sunset_water.json my_gallery.json
# Edit my_gallery.json to match your needs
python identify_gallery_content.py --config my_gallery.json
```

### Method 3: Use as reference
Open the example files to understand the configuration format, then create your own or use command-line parameters:

```bash
python identify_gallery_content.py \
  --name "My Custom Gallery" \
  --scan ./descriptions \
  --required keyword1,keyword2 \
  --keywords optional1,optional2 \
  --exclude unwanted1,unwanted2 \
  --output my_results.json
```

## Configuration Tips

1. **Start broad, then narrow**: Begin with fewer required keywords and add more as needed
2. **Test iteratively**: Run with different configurations to see what works
3. **Review scores**: Check the output to understand how images are being ranked
4. **Adjust weights**: More keywords = higher scores, so balance required vs preferred
5. **Use exclusions carefully**: They immediately disqualify images, so be selective

## Common Patterns

### Seasonal Galleries
```json
{
  "content_rules": {
    "preferred_keywords": ["spring", "summer", "fall", "winter", "season"],
    "min_keyword_matches": 1
  }
}
```

### Time of Day
```json
{
  "content_rules": {
    "preferred_keywords": ["morning", "afternoon", "evening", "sunset", "sunrise", "golden hour", "blue hour"],
    "excluded_keywords": ["night", "dark"]
  }
}
```

### Color-Based
```json
{
  "content_rules": {
    "preferred_keywords": ["blue", "green", "red", "vibrant", "colorful", "bright"],
    "min_keyword_matches": 2
  }
}
```

### Activity-Based
```json
{
  "content_rules": {
    "preferred_keywords": ["hiking", "camping", "fishing", "swimming", "climbing"],
    "min_keyword_matches": 1
  }
}
```

## See Also

- [Gallery Content Identification Guide](../documentation/GALLERY_CONTENT_IDENTIFICATION.md)
- [JSON Schema](../gallery_config_schema.json)
- Main tool: `identify_gallery_content.py`
