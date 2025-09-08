# Comprehensive ImageDescriber Test Suite

This test suite provides comprehensive testing of the ImageDescriber functionality across all installed Ollama models and prompt styles.

## What It Tests

### Test Matrix
- **3 randomly selected images** (ensuring at least 1 JPG and 1 HEIC if available)
- **All installed Ollama models** (auto-detected)
- **All prompt styles** (detailed, concise, Narrative, artistic, technical, colorful, social)
- **2 follow-up questions per description** (intelligently generated based on AI responses)

### Total Operations
For example, with 3 images, 3 models, and 7 prompts:
- **63 original descriptions** (3 × 3 × 7)
- **126 follow-up responses** (63 × 2)
- **189 total AI interactions**

## Features

### Smart Follow-up Questions
The script analyzes each AI description and generates targeted follow-up questions based on:
- **Colors mentioned**: "You mentioned red in your description. What makes this red particularly significant?"
- **Objects identified**: "Tell me more about the car you described. What details stand out most?"
- **Emotions described**: "You described the image as peaceful. What visual elements create this peaceful feeling?"
- **Generic backups**: Technical, compositional, and storytelling questions

### Comprehensive Logging
- **Progress tracking**: Real-time updates on current image/model/prompt
- **Timing information**: Track processing duration
- **Error handling**: Log and continue on failures
- **Detailed responses**: Full AI responses logged for analysis

### Output Files
1. **Workspace file**: `comprehensive_test_YYYYMMDD_HHMMSS.idw` - Load in ImageDescriber GUI
2. **Log file**: `test_log_YYYYMMDD_HHMMSS.txt` - Detailed execution log
3. **Summary file**: `test_summary_YYYYMMDD_HHMMSS.json` - Test statistics and results

## Usage

### Prerequisites
1. **Ollama installed** with at least one vision model
2. **Test images directory** at `C:\Users\kelly\GitHub\testingimages`
3. **Virtual environment activated** with ImageDescriber dependencies

### Running the Test
```bash
# Navigate to test directory
cd "C:\Users\kelly\GitHub\Image-Description-Toolkit\imagedescriber\test_comprehensive"

# Run the test (this will take a while!)
python comprehensive_test.py
```

### Expected Runtime
- **~1-2 minutes per model** per image per prompt
- **Total time**: Approximately 30-60 minutes for full test suite
- **Progress**: Check log file for real-time updates

## Analyzing Results

### In ImageDescriber GUI
1. Open ImageDescriber
2. File → Open Workspace
3. Select the generated `.idw` file
4. Browse through images and their descriptions
5. Compare responses across models and prompts

### Description Naming Convention
- **Original**: `{model}_{prompt_style}` (e.g., "moondream_Narrative")
- **Follow-ups**: `{model}_{prompt_style}_followup1` (e.g., "moondream_Narrative_followup1")

### Log Analysis
The log file contains:
- Processing timestamps
- AI response lengths
- Error details
- Follow-up question generation
- Performance metrics

## Configuration

### Customizing Test Images Path
Edit line in `comprehensive_test.py`:
```python
test_images_dir = r"C:\Users\kelly\GitHub\testingimages"  # Change this path
```

### Customizing Prompt Styles
Edit the `prompt_styles` list in the `ComprehensiveTest` class:
```python
self.prompt_styles = ['detailed', 'concise', 'Narrative', 'artistic', 'technical', 'colorful', 'social']
```

### Customizing Image Selection
Modify `select_test_images()` method to change:
- Number of images tested
- File format preferences
- Selection criteria

## Troubleshooting

### Common Issues
1. **No models found**: Install Ollama models with `ollama pull moondream`
2. **No images found**: Check test images directory path
3. **Import errors**: Ensure virtual environment is activated
4. **API timeouts**: Models may be slow - script will continue on errors

### Error Handling
- Script continues processing even if individual operations fail
- All errors logged to both console and log file
- Failed operations marked in summary JSON
- Partial results still saved to workspace

## Output Analysis

### Key Questions to Investigate
1. **Model consistency**: Do models give similar responses for the same prompt?
2. **Follow-up quality**: Are follow-up responses different from originals?
3. **Prompt effectiveness**: Which prompts produce the most useful descriptions?
4. **Model strengths**: Which models perform best for different image types?

### Comparison Workflow
1. Load workspace in ImageDescriber
2. Select an image
3. Review all descriptions for that image
4. Look for patterns across models and prompts
5. Pay special attention to follow-up responses vs. originals

This comprehensive test will help identify the strengths and weaknesses of different models and prompts, and specifically help determine if models like moondream are repeating original descriptions in follow-up responses.
