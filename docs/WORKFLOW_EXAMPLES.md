# Multi-Step Workflow Examples

## Overview

This guide demonstrates how to use **ONNX** and **GroundingDINO** as part of multi-step workflows, where their output is enhanced or combined with other AI models for comprehensive image analysis.

## Contents

- [Why Multi-Step Workflows?](#why-multi-step-workflows)
- [ONNX Workflow Patterns](#onnx-workflow-patterns)
- [GroundingDINO Workflow Patterns](#groundingdino-workflow-patterns)
- [Workflow Combinations](#workflow-combinations)
- [Best Practices](#best-practices)

---

## Why Multi-Step Workflows?

### The Power of Combining Models

Different AI models have different strengths:

| Model | Strength | Best For |
|-------|----------|----------|
| **ONNX (Florence-2)** | Fast, efficient, good baseline | Initial processing, batch operations |
| **GroundingDINO** | Precise object detection | Finding specific objects, localization |
| **Ollama (moondream)** | Fast local descriptions | Enriching data, no API costs |
| **Ollama (llava)** | Detailed local analysis | In-depth descriptions, privacy |
| **OpenAI GPT-4o** | Premium quality | Professional reports, complex analysis |

### Multi-Step Benefits

✅ **Cost Optimization**: Use free local models first, premium models only when needed  
✅ **Speed**: Fast models for bulk processing, detailed models for refinement  
✅ **Comprehensive Analysis**: Detection + description + context  
✅ **Flexibility**: Choose different models for different stages  
✅ **Scalability**: Process thousands of images efficiently  

---

## ONNX Workflow Patterns

### Pattern 1: ONNX → Ollama (Fast Local Pipeline)

**Use Case**: High-volume image processing with rich descriptions, no API costs

**Workflow**:
1. **ONNX** generates baseline descriptions (fast, ~1-2 sec/image)
2. **Ollama** adds richer, more detailed descriptions
3. **HTML Report** combines both for comprehensive view

**Batch File**: `run_onnx_workflow.bat`

**Configuration**:
```batch
set INPUT_PATH=C:\Users\YourName\Pictures\vacation_photos
set WORKFLOW_STEPS=describe,html
set PROVIDER=onnx
set MODEL=florence-2-large
```

**Then enhance**:
```batch
# Edit run_ollama.bat
set IMAGE_PATH=C:\Users\YourName\Pictures\vacation_photos
set MODEL=llava
set PROMPT_STYLE=narrative

run_ollama.bat
```

**Results**:
- ONNX: Fast baseline descriptions
- Ollama: Detailed narrative descriptions
- Combined: Rich HTML report with both perspectives
- Cost: $0 (completely free)
- Speed: Fast (both run locally)

---

### Pattern 2: ONNX → OpenAI (Cost-Effective Premium)

**Use Case**: Large dataset baseline + selective premium enhancement

**Workflow**:
1. **ONNX** processes all images (free, fast)
2. Review results, identify interesting images
3. **OpenAI GPT-4o** processes selected images for premium quality
4. **HTML Report** with mixed quality levels

**Step 1 - Bulk processing**:
```batch
set INPUT_PATH=C:\Projects\PhotoCollection
set WORKFLOW_STEPS=describe,html
set PROVIDER=onnx
set MODEL=florence-2-large

run_onnx_workflow.bat
```

**Step 2 - Premium enhancement** (selective images):
```batch
# Edit run_openai_gpt4o.bat for specific subfolder or images
set IMAGE_PATH=C:\Projects\PhotoCollection\BestShots
set PROMPT_STYLE=professional

run_openai_gpt4o.bat
```

**Cost Analysis**:
- 1000 images with ONNX: $0
- 50 selected images with GPT-4o: ~$1-2
- Total: ~$2 vs ~$20-50 for all with GPT-4o

---

### Pattern 3: Video → ONNX → HTML (Complete Video Processing)

**Use Case**: Extract frames from video, describe all, create report

**Workflow**:
1. **Video Frame Extractor** extracts frames from video
2. **Image Converter** standardizes formats (optional)
3. **ONNX** describes all frames
4. **HTML Generator** creates navigable report

**Configuration**:
```batch
set INPUT_PATH=C:\Videos\presentation.mp4
set WORKFLOW_STEPS=video,convert,describe,html
set PROVIDER=onnx
set MODEL=florence-2-large
```

**Results**:
- All video frames extracted
- Each frame described by ONNX
- HTML timeline report
- Fast processing (local, no API)

---

### Pattern 4: ONNX → Filter → Premium Model

**Use Case**: Use ONNX to filter/categorize, then enhance specific categories

**Workflow**:
1. **ONNX** describes all images with categorization prompts
2. **Script** filters based on keywords in descriptions
3. **Premium Model** processes filtered subset

**Step 1 - ONNX categorization**:
```batch
set INPUT_PATH=C:\Projects\ImageDatabase
set PROMPT_STYLE=detailed  # Includes categories/tags
set PROVIDER=onnx

run_onnx_workflow.bat
```

**Step 2 - Manual or scripted filtering**:
```python
# Example: Find all images with "landscape" in ONNX description
import os
landscapes = []
for file in os.listdir("C:/Projects/ImageDatabase"):
    if file.endswith("_description.txt"):
        with open(file) as f:
            if "landscape" in f.read().lower():
                landscapes.append(file)
```

**Step 3 - Process filtered images**:
```batch
# Process landscapes folder with premium model
set IMAGE_PATH=C:\Projects\ImageDatabase\Landscapes
set MODEL=gpt-4o

run_openai_gpt4o.bat
```

---

## GroundingDINO Workflow Patterns

### Pattern 1: Hybrid Mode (Detection + Description Combined)

**Use Case**: Need both object detection AND rich descriptions in one pass

**Provider**: `groundingdino+ollama`

**Workflow**:
- GroundingDINO detects and locates objects
- Ollama generates descriptions referencing detected objects
- Integrated output with both datasets

**Batch File**: `run_groundingdino_workflow.bat` (HYBRID mode)

**Configuration**:
```batch
set WORKFLOW_MODE=HYBRID
set INPUT_PATH=C:\Inspection\WorkplaceSafety
set DETECTION_QUERY=people . safety equipment . hazards . fire extinguisher
set DESCRIPTION_MODEL=llava
set WORKFLOW_STEPS=describe,html
```

**Results**:
- Object bounding boxes with labels
- Natural language descriptions
- HTML report with visual overlays
- Single workflow execution

**Best For**:
- Safety inspections
- Inventory management
- Comprehensive scene analysis

---

### Pattern 2: Sequential Mode (Detection First, Description Second)

**Use Case**: Separate detection and description for flexibility

**Workflow**:
1. **GroundingDINO** detects specific objects
2. **Any Vision Model** adds general descriptions
3. Combine results manually or via HTML report

**Batch File**: `run_groundingdino_workflow.bat` (SEQUENTIAL mode)

**Configuration**:
```batch
set WORKFLOW_MODE=SEQUENTIAL
set INPUT_PATH=C:\Quality\ProductPhotos
set DETECTION_QUERY=damaged items . missing labels . defects
set DESCRIPTION_MODEL=gpt-4o
set WORKFLOW_STEPS=describe,html
```

**Results**:
- Two separate processing passes
- Detection data from GroundingDINO
- Descriptions from chosen model
- Both included in HTML report

**Best For**:
- Quality control
- Damage assessment
- Flexible model selection

---

### Pattern 3: GroundingDINO → Filter → Action

**Use Case**: Detect specific conditions, trigger actions based on results

**Workflow**:
1. **GroundingDINO** scans images for specific items
2. **Script** analyzes detection results
3. **Action** triggered if conditions met (alert, move file, etc.)

**Example - Safety Violation Detection**:

```batch
# Step 1: Detect safety equipment
set DETECTION_QUERY=people wearing helmets . people wearing safety vests . people without helmets
set CONFIDENCE=30

run_groundingdino_workflow.bat
```

```python
# Step 2: Check for violations (people without helmets)
import os, json

violations = []
for file in os.listdir("inspection_folder"):
    if file.endswith("_detections.json"):
        with open(file) as f:
            data = json.load(f)
            for detection in data.get('detections', []):
                if 'without helmet' in detection['label'].lower():
                    violations.append({
                        'image': file,
                        'detection': detection
                    })

# Step 3: Generate violation report
if violations:
    print(f"ALERT: {len(violations)} safety violations detected!")
    # Send email, create report, etc.
```

---

### Pattern 4: Multi-Query Analysis

**Use Case**: Run multiple detection queries on same images for comprehensive analysis

**Workflow**:
1. **Query 1**: Safety equipment
2. **Query 2**: People and vehicles
3. **Query 3**: Signage and text
4. Combine all detection results

**Example**:

```batch
REM Query 1 - Safety
set DETECTION_QUERY=fire extinguisher . exit signs . first aid . safety equipment
run_groundingdino.bat

REM Query 2 - Occupancy
set DETECTION_QUERY=people . groups of people . crowds
run_groundingdino.bat

REM Query 3 - Infrastructure
set DETECTION_QUERY=signs . text . warnings . directions . labels
run_groundingdino.bat
```

**Results**:
- Multiple detection passes
- Comprehensive object inventory
- Cross-reference different aspects

---

## Workflow Combinations

### Ultimate Workflow: ONNX + GroundingDINO + Premium Model

**Use Case**: Maximum insight from images

**Workflow**:
1. **ONNX** - Fast baseline descriptions (free, local)
2. **GroundingDINO** - Object detection and localization (free, local)
3. **GPT-4o** - Premium quality descriptions (cloud, paid)
4. **HTML Report** - Comprehensive multi-perspective analysis

**Step-by-Step**:

```batch
REM Step 1: ONNX baseline
set INPUT_PATH=C:\Analysis\Dataset
set PROVIDER=onnx
set WORKFLOW_STEPS=describe
run_onnx_workflow.bat

REM Step 2: GroundingDINO detection
set DETECTION_QUERY=people . vehicles . equipment . signs
set WORKFLOW_STEPS=describe
run_groundingdino.bat

REM Step 3: GPT-4o premium (selective or all)
set PROVIDER=openai
set MODEL=gpt-4o
set WORKFLOW_STEPS=describe,html
run_openai_gpt4o.bat
```

**Results**:
- Baseline descriptions (ONNX)
- Object detection data (GroundingDINO)
- Premium descriptions (GPT-4o)
- Comprehensive HTML report with all data

**Best For**:
- Critical projects
- Professional reports
- Research and analysis
- Maximum quality output

---

## Cost & Speed Comparison

### Workflow Cost Analysis (1000 images)

| Workflow | Cost | Speed | Quality | Best For |
|----------|------|-------|---------|----------|
| **ONNX only** | $0 | Fast | Good | Budget, volume |
| **ONNX → Ollama** | $0 | Medium | Very Good | Best free option |
| **ONNX → GPT-4o (selective 10%)** | ~$2-5 | Fast | Excellent | Cost-effective premium |
| **GroundingDINO + Ollama (Hybrid)** | $0 | Medium | Excellent* | Detection + description |
| **All models combined** | ~$20-50 | Slow | Maximum | Critical projects |

*Excellent for detection, very good for descriptions

### Speed Comparison (per image)

| Model/Workflow | CPU | GPU | Notes |
|----------------|-----|-----|-------|
| **ONNX** | 2-5s | 0.5-1s | Fast baseline |
| **GroundingDINO** | 5-10s | 1-2s | Detection focused |
| **Ollama (moondream)** | 3-8s | 1-2s | Fast local |
| **Ollama (llava)** | 10-20s | 2-5s | Detailed local |
| **GPT-4o** | 2-5s | N/A | API latency |
| **Hybrid (GD+Ollama)** | 15-30s | 3-7s | Combined processing |

---

## Best Practices

### 1. Start Fast, Refine Later

```
Initial Pass: ONNX (fast, free baseline)
    ↓
Review: Identify images needing more detail
    ↓
Refinement: Premium model on selected images
```

### 2. Use Appropriate Models for Task

| Task | Recommended Model |
|------|-------------------|
| **Bulk categorization** | ONNX |
| **Object detection** | GroundingDINO |
| **Rich descriptions** | Ollama (llava) |
| **Professional reports** | GPT-4o |
| **Safety/compliance** | GroundingDINO + GPT-4o |

### 3. Optimize for Cost

**Free workflow** (unlimited images):
```
ONNX → GroundingDINO → Ollama → HTML
Cost: $0
Quality: Very Good
```

**Budget workflow** (1000 images):
```
ONNX (all) → GPT-4o (best 50)
Cost: ~$2-5
Quality: Excellent where it matters
```

### 4. Directory Structure

Organize outputs by model:

```
ProjectFolder/
  ├── images/
  │   ├── photo1.jpg
  │   └── photo2.jpg
  ├── onnx_output/
  │   ├── photo1_description.txt
  │   └── photo2_description.txt
  ├── groundingdino_output/
  │   ├── photo1_detections.json
  │   └── photo2_detections.json
  ├── premium_output/
  │   ├── photo1_description.txt
  │   └── photo2_description.txt
  └── reports/
      └── index.html
```

### 5. Prompt Style Consistency

Use consistent prompt styles across models for comparable results:

```batch
REM For all models in workflow
set PROMPT_STYLE=narrative
```

### 6. Batch Processing Tips

**Process in stages**:
1. Extract/convert (if needed): `--steps video,convert`
2. Describe: `--steps describe` (one model)
3. Enhance: `--steps describe` (another model)
4. Report: `--steps html`

**Use output directories**:
```batch
set OUTPUT_DIR=C:\Projects\Analysis\Run_2024_10_03
```

---

## Example Scenarios

### Scenario 1: Real Estate Photography

**Goal**: Professional property descriptions

**Workflow**:
```
ONNX (all rooms) → Review → GPT-4o (best rooms) → HTML
```

**Why**:
- ONNX handles bulk room photos quickly
- Review to select hero shots
- GPT-4o for marketing-quality descriptions of best shots
- Cost-effective, high quality where needed

---

### Scenario 2: Safety Audit

**Goal**: Detect violations and document conditions

**Workflow**:
```
GroundingDINO (safety equipment detection) → GPT-4o (violation descriptions) → HTML Report
```

**Why**:
- GroundingDINO finds specific equipment/violations
- GPT-4o provides professional documentation
- HTML report for official records

---

### Scenario 3: Product Catalog

**Goal**: Catalog 10,000 product images

**Workflow**:
```
ONNX (all products) → Filter by category → Ollama (detailed descriptions) → HTML
```

**Why**:
- ONNX quickly processes massive volume
- Filter to group by category
- Ollama adds rich descriptions (free)
- No API costs, unlimited scale

---

### Scenario 4: Video Analysis

**Goal**: Analyze presentation video for content

**Workflow**:
```
Video Extractor → ONNX (frame descriptions) → GroundingDINO (detect charts/text) → HTML Timeline
```

**Why**:
- Extract all frames from video
- ONNX describes each frame
- GroundingDINO finds specific visual elements
- Timeline HTML shows content flow

---

## Troubleshooting

### Workflow Fails After First Step

**Problem**: First step completes, but subsequent step fails

**Solution**:
- Check output directory paths
- Verify all required models installed
- Run steps separately to isolate issue
- Check logs for specific errors

### Mixed Output Quality

**Problem**: Some descriptions better than others

**Solution**:
- Use consistent prompt styles
- Verify model is loading correctly
- Check if model switches between images
- Review configuration for each step

### High Memory Usage

**Problem**: System slows down during multi-step processing

**Solution**:
- Process in smaller batches
- Clear cache between steps
- Use `--steps` to run one step at a time
- Restart between major processing runs

---

## Summary

Multi-step workflows with ONNX and GroundingDINO enable:

✅ **Cost optimization** - Free local models for bulk, premium for refinement  
✅ **Speed** - Fast processing with targeted enhancement  
✅ **Quality** - Best model for each specific task  
✅ **Flexibility** - Mix and match based on needs  
✅ **Scalability** - Handle thousands of images efficiently  

**Quick Start**:
1. Use `run_onnx_workflow.bat` for fast baseline processing
2. Use `run_groundingdino_workflow.bat` for detection + description
3. Enhance selectively with premium models
4. Generate comprehensive HTML reports

**Remember**: You don't need to use all models for all images. Choose the right tool for each job!
