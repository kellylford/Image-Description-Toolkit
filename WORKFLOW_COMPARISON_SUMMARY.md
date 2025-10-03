# Workflow Comparison Summary

## Overview
This document summarizes the comparison between two workflow runs that processed images using different AI configurations.

## Workflows Compared

### Workflow 1: Ollama Only
- **Directory**: `wf_ollama_llava_latest_narrative_20251003_003644/`
- **Configuration**: 
  - Provider: Ollama
  - Model: llava:latest
  - Prompt Style: narrative
  - Total Images Processed: 123

### Workflow 2: ONNX + Ollama
- **Directory**: `wf_onnx_llava_latest_narrative_20251003_001754/`
- **Configuration**: 
  - Provider: ONNX (object detection first) + Ollama
  - Model: llava:latest
  - Prompt Style: narrative
  - Total Images Processed: 144

## Comparison Results

### Common Images
- **Count**: 123 images
- **Source**: Both workflows processed these images
- **Format**: Side-by-side comparison in `workflow_comparison.txt`

### Unique to ONNX Workflow
- **Count**: 21 images
- **Source**: Only processed in the ONNX + Ollama workflow
- **Files**: Listed at the end of `workflow_comparison.txt`
- **Note**: These are all from the `converted_images/` directory with names like `od_photo-*_singular_display_fullPicture.jpg`

### Unique to Ollama Workflow
- **Count**: 0 images
- **Note**: All images in the Ollama workflow were also processed in the ONNX workflow

## Key Differences in Descriptions

### Workflow 1 (Ollama Only)
- More detailed narrative descriptions
- Longer, more flowing prose
- Focuses on overall scene interpretation
- Describes mood, atmosphere, and context
- More speculative about intent and meaning

### Workflow 2 (ONNX + Ollama)
- More structured descriptions
- Often starts with object detection context
- More precise spatial descriptions
- More factual, less speculative
- Better at identifying specific objects and their locations
- Includes technical details (flight numbers, specific model types, etc.)

## File Locations

### Comparison File
- **Location**: `c:\Users\kelly\GitHub\idt\workflow_comparison.txt`
- **Size**: 2,918 lines
- **Format**: 
  - Header with metadata
  - 123 side-by-side comparisons
  - List of 21 ONNX-only images

### Source Files
1. `wf_ollama_llava_latest_narrative_20251003_003644\descriptions\image_descriptions.txt`
2. `wf_onnx_llava_latest_narrative_20251003_001754\descriptions\image_descriptions.txt`

## Usage

### To Review Comparisons
1. Open `workflow_comparison.txt` in a text editor
2. Each image has two descriptions:
   - **WORKFLOW 1**: Ollama-only description
   - **WORKFLOW 2**: ONNX + Ollama description
3. Compare the differences in detail, accuracy, and style

### Example Comparison

**Image**: `09\849adfa4fe72c4fd8f6482ecfde0a4a1.jpeg` (woman with rainbow mohawk in salon)

**Workflow 1 (Ollama)**: 
- 4 paragraphs, ~200 words
- Detailed description of woman's appearance, expression, environment
- Speculates about her emotions and the scene
- More narrative and atmospheric

**Workflow 2 (ONNX + Ollama)**:
- 2 paragraphs, ~80 words
- More concise and factual
- Identifies specific objects (laptop, TV, chairs)
- Focuses on what's visible rather than interpretation
- Less speculative, more observational

## Observations

### When Ollama-Only Works Better
- Creative or artistic images requiring interpretation
- Scenes where context and mood matter more than specific objects
- Images where detailed narrative is valuable

### When ONNX + Ollama Works Better
- Images with many distinct objects
- Scenes requiring spatial precision
- Technical images (screenshots, diagrams, interfaces)
- When object identification is critical
- Images with text or specific identifiable elements

### Trade-offs
- **ONNX + Ollama**: More accurate object detection, but sometimes less narrative flow
- **Ollama Only**: More coherent storytelling, but may miss or misidentify specific objects
- **Processing Time**: ONNX workflow takes longer (object detection + description)
- **Accuracy**: ONNX workflow tends to be more factually accurate about specific objects

## Recommendations

### Use Ollama Only When:
- Processing artistic or creative imagery
- Narrative quality is more important than precision
- Speed is a priority
- You want more interpretive descriptions

### Use ONNX + Ollama When:
- Object identification is critical
- Spatial accuracy matters
- Processing technical or information-dense images
- You need structured, factual descriptions
- You want both detection data and natural language

### Hybrid Approach
Consider using both workflows on the same images when:
- You need comprehensive analysis
- Both narrative and factual descriptions are valuable
- You're evaluating which approach works better for your use case

## Next Steps

1. **Review Sample Images**: Look at 5-10 comparison examples to understand differences
2. **Identify Patterns**: Note which workflow performs better for different image types
3. **Optimize Workflow**: Choose the best workflow for your specific use case
4. **Fine-tune Settings**: Adjust prompts or detection thresholds based on results
5. **Consider Hybrid**: Use both workflows for critical images that need comprehensive analysis

## Questions to Consider

- Which descriptions are more useful for your purposes?
- Are the ONNX detections adding value or just noise?
- Is the additional processing time of ONNX worth the improved object detection?
- Would different prompt styles produce better results?
- Should you run both workflows on future image sets?

## Statistics

- **Total Images Compared**: 123
- **Average Description Length (Ollama)**: ~150-200 words
- **Average Description Length (ONNX)**: ~100-150 words
- **Processing Time Difference**: ONNX workflow likely 2-3x longer
- **Workflow Completion**: Ollama completed all 123, ONNX processed 144 total

---

Generated: 2025-10-03
Comparison File: workflow_comparison.txt
