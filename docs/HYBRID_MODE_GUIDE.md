# GroundingDINO + Ollama Hybrid Mode Guide

## Overview
Hybrid mode combines the precision of GroundingDINO object detection with the natural language capabilities of Ollama, giving you the best of both worlds.

## How It Works

### Two-Stage Process:
1. **GroundingDINO Detection** - Finds objects matching your detection query
2. **Ollama Description** - Generates a natural language description incorporating the detected objects

## Configuration Requirements

### You Need TWO Things:
1. **Ollama Model** (for descriptions)
   - Select from the "AI Model" dropdown
   - Examples: llava:latest, bakllava:latest, moondream:latest
   - Must be a vision-capable model

2. **Detection Settings** (below the model selection)
   - Choose preset mode OR custom query
   - Adjust confidence threshold
   - Detection mode: Automatic or Custom

### Common Mistakes ❌
- ❌ Not selecting an Ollama model (leaving "No models available")
- ❌ Using GroundingDINO standalone when you want descriptions
- ❌ Selecting non-vision Ollama models (mistral-small, gemma3)
- ❌ Setting confidence threshold too high (missing objects)

### Correct Setup ✅
```
Provider: GroundingDINO + Ollama
AI Model: llava:latest  ← Must select an Ollama vision model!
Detection Mode: Automatic ← Choose based on your needs
Preset: Comprehensive Detection (Auto)
Confidence: 25%
```

## When to Use Each Mode

### Standalone GroundingDINO
**Use when:**
- You only need object detection (no description)
- You want structured detection data
- You're doing object counting or location analysis
- Speed is critical (faster than hybrid)

**Output example:**
```
🔍 Object Detection Results
Found 12 objects in image

📦 Furniture (5):
• chair at middle-center (confidence: 92%)
• table at middle-center (confidence: 88%)
...
```

### Hybrid Mode (GroundingDINO + Ollama)
**Use when:**
- You want both detection AND natural description
- You need context about detected objects
- You want human-readable summaries
- You're analyzing complex scenes

**Output example:**
```
🔍 GroundingDINO + Ollama Analysis
📊 Detection Summary (12 objects found):
furniture: 5, people: 3, devices: 4

📝 Detailed Description:
The image shows an office workspace with 5 pieces of furniture
including 2 chairs positioned at a table in the center. There are
3 people working at computers, with 4 electronic devices visible...
```

## Preset Modes

### Comprehensive Detection (Auto)
Detects everything: people, furniture, vehicles, animals, electronics, etc.
**Best for:** General-purpose detection

### Indoor Detection
Optimized for: furniture, appliances, decor, electronics
**Best for:** Home, office, interior scenes

### Outdoor Detection
Optimized for: vehicles, buildings, nature, animals
**Best for:** Street scenes, landscapes, parking lots

### Workplace Safety
Optimized for: PPE, hazards, equipment, people
**Best for:** Safety inspections, compliance monitoring

### Retail Detection
Optimized for: products, shelves, customers, checkout areas
**Best for:** Store monitoring, inventory analysis

### Document Detection
Optimized for: text areas, tables, figures, diagrams
**Best for:** Document analysis, layout detection

### Custom Query
Define your own: `object1 . object2 . object3`
**Best for:** Specific object searches

## Tips & Best Practices

### Confidence Threshold
- **10-20%**: Find everything (more false positives)
- **25-35%**: Balanced (recommended default)
- **40-60%**: High precision (fewer objects, more accurate)
- **70%+**: Very strict (may miss valid objects)

### Custom Queries
Format: `object1 . object2 . object3` (separate with space-dot-space)

Examples:
- `person . car . bicycle`
- `laptop . phone . tablet . monitor`
- `red car . blue car . white car`
- `person wearing hat . person with glasses`

### Performance
- **CPU**: Works but slower (3-10 seconds)
- **GPU**: Much faster (<1 second)
- **First run**: Downloads ~700MB model
- **Subsequent runs**: Uses cached model

### Troubleshooting

#### "No Ollama models available"
- **Solution**: Install Ollama and pull a vision model
  ```bash
  ollama pull llava
  ollama pull bakllava
  ollama pull moondream
  ```

#### "HTTP 404" error
- **Cause**: Invalid Ollama model selected
- **Solution**: Select a valid model from the dropdown

#### "Detection configured below" error in hybrid mode
- **Cause**: Bug in older version (now fixed)
- **Solution**: Update to latest version

#### No objects detected
- **Lower confidence threshold** (try 15-20%)
- **Use broader query** (try "object . thing . item")
- **Check image quality** (good lighting, clear view)
- **Try different preset** (Comprehensive usually works best)

## Integration with Chat

You can use hybrid mode in chat:
```
User: "describe this image" [image selected in workspace]
Assistant: [runs hybrid detection + description]

User: "find all the red objects"
Assistant: [runs custom query: "red object . red item"]
```

## Examples

### Example 1: Office Analysis
```
Provider: GroundingDINO + Ollama
Model: llava:latest
Detection: Indoor Detection
Confidence: 25%
```
Result: Finds chairs, desks, monitors, etc. + description of workspace layout

### Example 2: Safety Inspection
```
Provider: GroundingDINO + Ollama
Model: bakllava:latest
Detection: Workplace Safety
Confidence: 35%
```
Result: Finds PPE, hazards, safety equipment + description of safety status

### Example 3: Custom Search
```
Provider: GroundingDINO + Ollama
Model: moondream:latest
Detection: Custom Query
Query: person wearing mask . person without mask
Confidence: 30%
```
Result: Finds people with/without masks + description of compliance

## Quick Reference

| Scenario | Provider | Model | Detection Mode |
|----------|----------|-------|----------------|
| Just find objects | GroundingDINO | N/A | Any preset |
| Find + describe | Hybrid | llava | Any preset |
| Office scene | Hybrid | bakllava | Indoor |
| Street scene | Hybrid | llava | Outdoor |
| Safety check | Hybrid | moondream | Workplace Safety |
| Specific items | Hybrid | Any | Custom Query |

## Version History
- v2.0: Added hybrid mode validation
- v1.5: Fixed model selection bug
- v1.0: Initial hybrid mode implementation
