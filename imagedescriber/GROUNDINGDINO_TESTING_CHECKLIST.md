# GroundingDINO Testing Checklist

## Pre-Testing Setup
- [ ] GroundingDINO installed: `pip install groundingdino-py`
- [ ] Model downloaded (~700MB, happens automatically on first use)
- [ ] Ollama running (for hybrid mode tests)
- [ ] At least one Ollama vision model installed (llava, bakllava, or moondream)
- [ ] Test images available (various scenes: indoor, outdoor, people, objects)

## Test 1: Standalone GroundingDINO - Preset Modes

### Comprehensive Detection (Auto)
- [ ] Select Provider: GroundingDINO
- [ ] Model shows: "Detection configured below" (disabled dropdown)
- [ ] Detection Mode: Automatic
- [ ] Preset: Comprehensive Detection (Auto)
- [ ] Confidence: 25%
- [ ] Process an image with multiple objects
- [ ] Verify: Detects people, furniture, vehicles, etc.
- [ ] Verify: Shows confidence percentages
- [ ] Verify: Shows locations (top-left, middle-center, etc.)

### Indoor Detection
- [ ] Preset: Indoor Detection
- [ ] Process indoor/office scene
- [ ] Verify: Detects furniture, appliances, electronics
- [ ] Verify: Appropriate for indoor scenes

### Outdoor Detection
- [ ] Preset: Outdoor Detection
- [ ] Process street/landscape scene
- [ ] Verify: Detects vehicles, buildings, nature
- [ ] Verify: Appropriate for outdoor scenes

### Workplace Safety
- [ ] Preset: Workplace Safety
- [ ] Process workplace/construction scene
- [ ] Verify: Detects PPE, equipment, hazards
- [ ] Verify: Safety-relevant objects identified

### Retail Detection
- [ ] Preset: Retail Detection
- [ ] Process store/shopping scene
- [ ] Verify: Detects products, shelves, customers
- [ ] Verify: Retail-relevant objects identified

### Document Detection
- [ ] Preset: Document Detection
- [ ] Process document/page image
- [ ] Verify: Detects text areas, tables, figures
- [ ] Verify: Layout elements identified

## Test 2: Custom Queries

### Simple Custom Query
- [ ] Detection Mode: Custom
- [ ] Query: `person . car . tree`
- [ ] Confidence: 25%
- [ ] Process appropriate image
- [ ] Verify: Only specified objects detected
- [ ] Verify: No other objects reported

### Specific Custom Query
- [ ] Query: `red car . blue car . white car`
- [ ] Verify: Color-specific detection works
- [ ] Verify: Different colored objects distinguished

### Complex Custom Query
- [ ] Query: `person wearing hat . person with glasses . person with backpack`
- [ ] Verify: Attribute-based detection works
- [ ] Verify: Multiple attributes distinguished

## Test 3: Confidence Threshold

### Low Confidence (10%)
- [ ] Set confidence: 10%
- [ ] Process image
- [ ] Verify: More objects detected
- [ ] Verify: Some may be false positives
- [ ] Note: Total object count

### Medium Confidence (25%)
- [ ] Set confidence: 25%
- [ ] Process same image
- [ ] Verify: Balanced results
- [ ] Verify: Fewer objects than 10%
- [ ] Note: Total object count

### High Confidence (50%)
- [ ] Set confidence: 50%
- [ ] Process same image
- [ ] Verify: High-precision results
- [ ] Verify: Fewer objects than 25%
- [ ] Verify: All detections highly confident

## Test 4: Hybrid Mode - GroundingDINO + Ollama

### Basic Hybrid Test
- [ ] Provider: GroundingDINO + Ollama
- [ ] Model dropdown: Shows Ollama models (enabled)
- [ ] Select model: llava:latest (or similar vision model)
- [ ] Detection Mode: Automatic
- [ ] Preset: Comprehensive Detection
- [ ] Confidence: 25%
- [ ] Process image
- [ ] Verify: Two-part output:
  - [ ] Detection Summary with object counts
  - [ ] Detailed Description from Ollama
- [ ] Verify: Description mentions detected objects
- [ ] Verify: No HTTP 404 error

### Hybrid with Different Presets
- [ ] Model: bakllava:latest
- [ ] Preset: Indoor Detection
- [ ] Verify: Indoor-specific detections + description

- [ ] Model: moondream:latest
- [ ] Preset: Outdoor Detection
- [ ] Verify: Outdoor-specific detections + description

### Hybrid with Custom Query
- [ ] Model: llava:latest
- [ ] Detection Mode: Custom
- [ ] Query: `laptop . phone . tablet`
- [ ] Verify: Only specified devices detected
- [ ] Verify: Description focuses on detected devices

## Test 5: Error Handling & Validation

### Invalid Hybrid Configuration
- [ ] Provider: GroundingDINO + Ollama
- [ ] Model: (None selected or "No models available")
- [ ] Click OK
- [ ] Verify: Warning dialog appears
- [ ] Verify: Message explains Ollama model required
- [ ] Verify: Dialog doesn't close

### Provider Not Available
- [ ] Stop Ollama (if running)
- [ ] Provider: GroundingDINO + Ollama
- [ ] Try to process
- [ ] Verify: Appropriate error message
- [ ] Verify: Explains Ollama not running

### No Objects Detected
- [ ] Use very high confidence (90%)
- [ ] Or use mismatched query
- [ ] Process image
- [ ] Verify: "No objects detected" message
- [ ] Verify: Suggestions provided (lower confidence, adjust query)

## Test 6: Chat Integration

### Chat Detection Query
- [ ] Open chat session
- [ ] Select an image in workspace
- [ ] Ask: "what objects do you detect?"
- [ ] Verify: GroundingDINO detection runs
- [ ] Verify: Objects listed in response

### Chat Custom Detection
- [ ] Select different image
- [ ] Ask: "find all the people in this image"
- [ ] Verify: Custom query parsed correctly
- [ ] Verify: People detected and reported

### Chat Refinement
- [ ] After initial detection, ask: "find only red objects"
- [ ] Verify: New detection with custom query
- [ ] Verify: Context maintained

## Test 7: Performance & Stability

### CPU Performance
- [ ] Run detection on CPU (no CUDA)
- [ ] Note: Processing time (expected: 3-10 seconds)
- [ ] Verify: Completes successfully
- [ ] Verify: Results accurate

### GPU Performance (if available)
- [ ] Run detection on CUDA GPU
- [ ] Note: Processing time (expected: <1 second)
- [ ] Verify: Much faster than CPU
- [ ] Verify: Results accurate

### Multiple Sequential Detections
- [ ] Process 5 different images in sequence
- [ ] Verify: All complete successfully
- [ ] Verify: No memory leaks or slowdowns
- [ ] Verify: Consistent performance

### Large Image
- [ ] Process high-resolution image (>4000px)
- [ ] Verify: Completes successfully
- [ ] Verify: Results accurate
- [ ] Note: Processing time

## Test 8: UI/UX

### Provider Selection Flow
- [ ] Select "GroundingDINO"
- [ ] Verify: Model dropdown disabled, shows "Detection configured below"
- [ ] Verify: Detection controls visible
- [ ] Switch to "GroundingDINO + Ollama"
- [ ] Verify: Model dropdown enabled, shows Ollama models
- [ ] Verify: Detection controls still visible
- [ ] Switch to "Ollama"
- [ ] Verify: Detection controls hidden
- [ ] Verify: Standard prompt controls shown

### Detection Controls Visibility
- [ ] Provider: GroundingDINO
- [ ] Verify: Radio buttons visible (Automatic/Custom)
- [ ] Verify: Preset dropdown visible
- [ ] Verify: Custom query input visible (if Custom selected)
- [ ] Verify: Confidence slider visible
- [ ] Verify: All labels clear and readable

### Mode Switching
- [ ] Select "Automatic" mode
- [ ] Verify: Preset dropdown enabled
- [ ] Verify: Custom query input disabled
- [ ] Select "Custom" mode
- [ ] Verify: Preset dropdown disabled
- [ ] Verify: Custom query input enabled and focused

## Test 9: Edge Cases

### Empty Custom Query
- [ ] Detection Mode: Custom
- [ ] Query: (leave blank)
- [ ] Try to process
- [ ] Verify: Falls back to Comprehensive or shows error

### Invalid Query Format
- [ ] Query: `person car tree` (no dots)
- [ ] Process image
- [ ] Verify: Handles gracefully or shows error

### Very Long Query
- [ ] Query: 20+ objects separated by dots
- [ ] Verify: Processes without crashing
- [ ] Verify: Results reasonable

### Network Image Path
- [ ] Image on network path (\\server\share\image.jpg)
- [ ] Verify: Loads and processes correctly

### Special Characters in Path
- [ ] Image path with spaces or special chars
- [ ] Verify: Loads and processes correctly

## Test 10: Documentation Verification

### Quick Reference
- [ ] Open GROUNDINGDINO_QUICK_REFERENCE.md
- [ ] Verify: All preset modes documented
- [ ] Verify: Custom query format explained
- [ ] Verify: Examples provided

### Hybrid Mode Guide
- [ ] Open HYBRID_MODE_GUIDE.md
- [ ] Verify: Configuration requirements clear
- [ ] Verify: Common mistakes documented
- [ ] Verify: Troubleshooting steps provided
- [ ] Verify: Examples match actual behavior

### User Setup Guide
- [ ] Open USER_SETUP_GUIDE.md
- [ ] Find GroundingDINO section
- [ ] Verify: Installation instructions correct
- [ ] Verify: Model download explained
- [ ] Verify: System requirements listed

## Test Results Summary

### Pass Criteria
- [ ] All standalone detection modes work
- [ ] All hybrid mode tests pass
- [ ] Custom queries function correctly
- [ ] Confidence threshold affects results appropriately
- [ ] Chat integration works
- [ ] Error handling is robust
- [ ] Documentation is accurate
- [ ] No crashes or data loss

### Known Issues (document any found)
1. 
2. 
3. 

### Performance Notes
- CPU processing time: _____ seconds
- GPU processing time: _____ seconds (if applicable)
- Model download time: _____ minutes
- Memory usage: _____ MB

### Recommendations
- [ ] Ready for production use
- [ ] Needs minor fixes (list above)
- [ ] Needs major fixes (list above)
- [ ] Documentation needs updates (specify)

## Testing Completed By
- Tester: _________________
- Date: ___________________
- Version: ________________
- Environment: _____________

## Notes
(Additional observations, suggestions, or comments)
