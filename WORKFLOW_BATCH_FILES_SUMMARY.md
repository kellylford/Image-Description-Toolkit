# Multi-Step Workflow Batch Files - Summary

## What Was Created

### New Batch Files (Project Root)

1. **`run_onnx_workflow.bat`**
   - Demonstrates using ONNX as first step in multi-step workflow
   - Fast baseline processing with ONNX Florence-2
   - Then enhance with other models (Ollama, OpenAI, etc.)
   - Includes full workflow steps: video,convert,describe,html
   - Shows cost-effective pattern: free baseline → selective enhancement

2. **`run_groundingdino_workflow.bat`**
   - Demonstrates GroundingDINO in multi-step workflows
   - Two modes: HYBRID and SEQUENTIAL
   - **HYBRID**: Detection + description in one run (groundingdino+ollama)
   - **SEQUENTIAL**: Detection first, then descriptions separately
   - Configurable detection queries and confidence thresholds

### New Documentation (docs/)

3. **`docs/WORKFLOW_EXAMPLES.md`** (~1000 lines)
   - Comprehensive guide to multi-step workflow patterns
   - ONNX workflow patterns (4 patterns documented)
   - GroundingDINO workflow patterns (4 patterns documented)
   - Cost & speed comparisons
   - Best practices and real-world scenarios
   - Troubleshooting multi-step workflows

### Updated Files

4. **`BATCH_FILES_README.md`**
   - Added multi-step workflow section
   - Reference to new workflow examples documentation
   - Updated provider table to include GroundingDINO

---

## Key Workflow Patterns

### ONNX Patterns

#### Pattern 1: ONNX → Ollama (Fast Local Pipeline)
```
ONNX (fast baseline) → Ollama (rich descriptions) → HTML Report
Cost: $0 | Speed: Fast | Quality: Very Good
```

#### Pattern 2: ONNX → OpenAI (Cost-Effective Premium)
```
ONNX (all images) → Review → GPT-4o (selected) → HTML Report
Cost: ~$2-5 for 1000 images | Quality: Excellent where needed
```

#### Pattern 3: Video → ONNX → HTML
```
Extract Frames → ONNX (describe all) → HTML Timeline
Cost: $0 | Use Case: Video content analysis
```

#### Pattern 4: ONNX → Filter → Premium
```
ONNX (categorize) → Filter by keywords → Premium (enhance)
Cost: Minimal | Use Case: Smart selective enhancement
```

### GroundingDINO Patterns

#### Pattern 1: Hybrid Mode (Recommended)
```
GroundingDINO + Ollama (combined detection + description)
Cost: $0 | Use Case: Comprehensive analysis
```

#### Pattern 2: Sequential Mode
```
GroundingDINO (detect) → Any Model (describe) → Combine
Cost: Varies | Use Case: Flexible model selection
```

#### Pattern 3: Detection → Filter → Action
```
GroundingDINO (scan) → Analyze results → Trigger actions
Use Case: Safety audits, compliance, quality control
```

#### Pattern 4: Multi-Query Analysis
```
Query 1 (safety) → Query 2 (occupancy) → Query 3 (signage)
Use Case: Multi-perspective analysis
```

---

## Usage Examples

### Example 1: Bulk Photo Processing with Cost Optimization

**Goal**: Process 1000 vacation photos, enhance best 50

```batch
REM Step 1: ONNX baseline (all 1000)
run_onnx_workflow.bat
# Set INPUT_PATH=C:\Photos\Vacation2024
# Set WORKFLOW_STEPS=describe,html

REM Step 2: Review HTML report, identify best shots

REM Step 3: GPT-4o premium (best 50)
run_openai_gpt4o.bat
# Set IMAGE_PATH=C:\Photos\Vacation2024\BestShots
```

**Result**: $0 for 1000 images + ~$1-2 for 50 premium = ~$2 total vs ~$20-50 all premium

---

### Example 2: Safety Inspection with Detection

**Goal**: Find safety violations and document

```batch
REM Use hybrid mode for detection + description
run_groundingdino_workflow.bat

# Configuration:
# Set WORKFLOW_MODE=HYBRID
# Set DETECTION_QUERY=people wearing helmets . safety vests . fire extinguisher . exit signs
# Set DESCRIPTION_MODEL=gpt-4o (for professional report)
```

**Result**: Detects equipment, people, violations with professional documentation

---

### Example 3: Video Analysis

**Goal**: Analyze training video for content

```batch
REM Use ONNX workflow with video processing
run_onnx_workflow.bat

# Configuration:
# Set INPUT_PATH=C:\Videos\training_session.mp4
# Set WORKFLOW_STEPS=video,convert,describe,html
```

**Result**: All frames extracted and described, HTML timeline created

---

### Example 4: Product Catalog with Detection

**Goal**: Catalog products with damage detection

```batch
REM Sequential mode: detect damage, then describe products
run_groundingdino_workflow.bat

# Configuration:
# Set WORKFLOW_MODE=SEQUENTIAL
# Set DETECTION_QUERY=damaged items . defects . missing labels . scratches
# Set DESCRIPTION_MODEL=llava (detailed local descriptions)
```

**Result**: Damage flagged + detailed product descriptions

---

## Cost Comparison (1000 images)

| Workflow | Total Cost | Speed | Quality |
|----------|-----------|-------|---------|
| **ONNX only** | $0 | Fast | Good |
| **ONNX → Ollama** | $0 | Medium | Very Good |
| **ONNX → GPT-4o (10%)** | ~$2-5 | Fast | Excellent* |
| **GroundingDINO + Ollama** | $0 | Medium | Excellent** |
| **All models combined*** | ~$20-50 | Slow | Maximum |

*Excellent for selected images  
**Excellent for detection, very good for descriptions  
***ONNX + GroundingDINO + GPT-4o for all

---

## When to Use Each Workflow

### Use ONNX Workflow When:
- ✅ Processing large volumes (hundreds/thousands of images)
- ✅ Budget is limited or zero
- ✅ Need fast baseline for all images
- ✅ Want to enhance selectively later
- ✅ Processing videos (many frames)

### Use GroundingDINO Workflow When:
- ✅ Need to detect specific objects
- ✅ Object location matters (bounding boxes)
- ✅ Safety/compliance inspections
- ✅ Inventory or quality control
- ✅ Want text-prompted detection ("red cars", "damaged items")

### Use Hybrid Mode When:
- ✅ Need both detection AND descriptions
- ✅ Want integrated output
- ✅ Single workflow execution preferred
- ✅ Using local models (free)

### Use Sequential Mode When:
- ✅ Need flexibility in model selection
- ✅ Detection and description are separate concerns
- ✅ Want to use premium model for descriptions only
- ✅ Processing detection results programmatically

---

## File Locations

```
idt/
├── run_onnx_workflow.bat           # ONNX multi-step workflow
├── run_groundingdino_workflow.bat  # GroundingDINO workflows (hybrid/sequential)
├── run_onnx.bat                    # ONNX single-step (existing)
├── run_groundingdino.bat           # GroundingDINO single-step (new)
├── run_ollama.bat                  # Ollama (existing)
├── run_openai_gpt4o.bat            # OpenAI (existing)
├── run_huggingface.bat             # HuggingFace (existing)
├── run_copilot.bat                 # Copilot (existing)
├── BATCH_FILES_README.md           # Updated with workflow section
└── docs/
    ├── WORKFLOW_EXAMPLES.md        # NEW: Comprehensive workflow guide
    ├── GROUNDINGDINO_GUIDE.md      # NEW: GroundingDINO setup guide
    ├── ONNX_GUIDE.md               # Existing
    ├── OLLAMA_GUIDE.md             # Existing
    ├── OPENAI_GUIDE.md             # Existing (if exists)
    ├── HUGGINGFACE_GUIDE.md        # Existing
    └── COPILOT_GUIDE.md            # Existing
```

---

## Quick Reference

### ONNX Workflow Command
```batch
# Fast baseline processing
run_onnx_workflow.bat
```

**Configure in file:**
- `INPUT_PATH` - Your images/videos
- `WORKFLOW_STEPS` - What to do (describe,html,etc.)
- `OUTPUT_DIR` - Where to save (optional)

### GroundingDINO Workflow Command
```batch
# Detection + description
run_groundingdino_workflow.bat
```

**Configure in file:**
- `WORKFLOW_MODE` - HYBRID or SEQUENTIAL
- `INPUT_PATH` - Your images
- `DETECTION_QUERY` - What to detect
- `DESCRIPTION_MODEL` - Model for descriptions (hybrid/sequential)

---

## Next Steps

1. **Try ONNX workflow** for bulk processing:
   - Edit `run_onnx_workflow.bat`
   - Set your image path
   - Run it
   - Review HTML output

2. **Try GroundingDINO workflow** for detection:
   - Edit `run_groundingdino_workflow.bat`
   - Choose HYBRID or SEQUENTIAL mode
   - Set detection query
   - Run it

3. **Read full documentation**:
   - `docs/WORKFLOW_EXAMPLES.md` - All patterns and examples
   - `docs/GROUNDINGDINO_GUIDE.md` - GroundingDINO setup and usage
   - `docs/ONNX_GUIDE.md` - ONNX optimization tips

4. **Experiment with combinations**:
   - Try different model sequences
   - Compare costs and quality
   - Find best workflow for your use case

---

## Support

- **Workflow questions**: See `docs/WORKFLOW_EXAMPLES.md`
- **GroundingDINO setup**: See `docs/GROUNDINGDINO_GUIDE.md`
- **ONNX setup**: See `docs/ONNX_GUIDE.md`
- **Other providers**: See respective guide in `docs/`

---

## Summary

You now have:

✅ **2 new batch files** for multi-step workflows  
✅ **1 comprehensive guide** (~1000 lines) with patterns and examples  
✅ **8 workflow patterns** documented with costs and use cases  
✅ **Updated main README** with workflow references  

**Key Advantage**: Save money and time by using free local models for bulk processing, then selectively enhance with premium models where quality matters most!
