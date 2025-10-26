---
name: Simplify Gallery Creation Workflow
about: Streamline the complex multi-step process for creating galleries from image descriptions
title: 'Simplify Gallery Creation: From Image Viewing to Published Gallery'
labels: enhancement, user-experience, gallery, workflow-improvement
assignees: ''
---

## Summary
The current process for creating galleries from IDT workflow results involves many complex manual steps that could be significantly simplified. Users should be able to go from viewing images with descriptions to a published gallery with minimal friction.

## Current Complex Workflow (30-45 minutes)

### Step 1: Image Identification (if using gallery identification)
```bash
cd tools/ImageGallery/content-creation/gallery-identification
python gallery_wizard.py
# Select images, create candidates list
# Optionally create IDW workspace for visual review
```

### Step 2: Manual Gallery Setup
```bash
cd tools/ImageGallery
mkdir myproject
mkdir myproject/images
cp /path/to/selected/*.jpg myproject/images/
```

### Step 3: Run 4 Separate Workflows (8-10 minutes)
```bash
cd myproject

# 1. Narrative prompt
c:/idt/idt.exe workflow images \
  --provider claude \
  --model claude-3-haiku-20240307 \
  --prompt-style narrative \
  --name myproject \
  --output-dir descriptions \
  --api-key-file c:/users/kelly/onedrive/idt/claude.txt \
  --batch

# 2. Colorful prompt  
c:/idt/idt.exe workflow images \
  --provider claude \
  --model claude-3-haiku-20240307 \
  --prompt-style colorful \
  --name myproject \
  --output-dir descriptions \
  --api-key-file c:/users/kelly/onedrive/idt/claude.txt \
  --batch

# 3. Technical prompt
c:/idt/idt.exe workflow images \
  --provider claude \
  --model claude-3-haiku-20240307 \
  --prompt-style technical \
  --name myproject \
  --output-dir descriptions \
  --api-key-file c:/users/kelly/onedrive/idt/claude.txt \
  --batch

# 4. Detailed prompt
c:/idt/idt.exe workflow images \
  --provider claude \
  --model claude-3-haiku-20240307 \
  --prompt-style detailed \
  --name myproject \
  --output-dir descriptions \
  --api-key-file c:/users/kelly/onedrive/idt/claude.txt \
  --batch
```

### Step 4: Generate Gallery Data
```bash
python ../generate_descriptions.py \
  --descriptions-dir descriptions \
  --output-dir gallery-data \
  --pattern myproject
```

### Step 5: Generate Alt Text (2-3 minutes)
```bash
export ANTHROPIC_API_KEY=$(cat /c/users/kelly/onedrive/idt/claude.txt)
python ../generate_alt_text.py --jsondata-dir gallery-data/
```

### Step 6: Configure Gallery
```bash
cp ../index.html .
# Edit index.html manually to update CONFIG.workflowPattern
```

### Step 7: Test and Deploy
```bash
python -m http.server 8082
# Copy index.html, images/, gallery-data/ to web server
```

## Problems with Current Workflow

### ❌ Too Many Manual Steps
- 7+ distinct phases requiring terminal commands
- Manual file copying and directory creation
- Manual configuration editing
- Easy to miss steps or make mistakes

### ❌ No Integration with Image Viewing
- When using Viewer tool to browse images, no quick way to "add to gallery"
- When using ImageDescriber to review images, no gallery creation option
- Identification and gallery creation are completely separate workflows

### ❌ Command-Line Heavy
- Requires terminal comfort for multiple complex commands
- Long command lines with many parameters
- Easy to make typos in paths and parameters

### ❌ Time Consuming
- 30-45 minutes for a simple gallery
- Most time spent on repetitive setup, not creative decisions
- Multiple context switches between tools

### ❌ Error Prone
- Many opportunities for path mistakes
- API key management across multiple commands
- Easy to forget steps like alt text generation

## Proposed Simplified Workflows

### Vision 1: Gallery Creation from Image Viewing
**When viewing images in Viewer or ImageDescriber:**

1. **Select Images**: Checkbox or marking system to select favorites
2. **Create Gallery Button**: One-click "Create Gallery from Selected"
3. **Gallery Wizard**: 
   - Choose gallery name
   - Select description styles (auto-run workflows)
   - Choose deployment target
   - One progress bar for everything

**Result**: Gallery ready in 5-10 minutes with minimal user input

### Vision 2: Enhanced Gallery Identification Integration
**Extend the existing gallery identification tool:**

1. **Identify Content**: Use existing wizard or CLI (keeps this part)
2. **Auto-Create Gallery**: New option at end of identification
   - "Create web gallery from these candidates? (Y/n)"
   - Auto-runs all workflows
   - Auto-generates alt text
   - Auto-configures gallery
   - Provides deployment-ready package

### Vision 3: Unified Gallery Command
**New IDT command:** `idt create-gallery`

```bash
# Simple case: gallery from directory
idt create-gallery --name "My Trip" --images /path/to/photos

# Advanced case: gallery from identification results  
idt create-gallery --name "Water Scenes" --from-candidates candidates.json

# Fully automated case
idt create-gallery --name "Vacation" --images /path/photos --deploy-to /var/www/galleries
```

**What it does automatically:**
- Creates gallery directory structure
- Runs all 4 workflows in parallel
- Generates JSON data
- Creates alt text
- Configures gallery HTML
- Optionally deploys to web server

## Specific Enhancement Requests

### 1. Add "Include in Gallery" to Image Viewing
**Files to modify:**
- `viewer/viewer.py` - Add gallery selection UI
- `imagedescriber/imagedescriber.py` - Add gallery export option

**New features:**
- Checkbox or star system for image selection
- "Export Selected to Gallery" button
- Gallery creation wizard integration

### 2. Batch Workflow Runner
**New file:** `tools/ImageGallery/create_gallery.py`

**Features:**
- Single command to run all 4 workflows
- Parallel execution where possible
- Progress bar showing overall completion
- Error handling and recovery
- Automatic API key management

### 3. Gallery Template Automation
**Enhancement to:** `tools/ImageGallery/content-creation/build_gallery.py`

**Features:**
- Auto-generate index.html with correct configuration
- Auto-copy images to gallery directory
- Auto-create deployment package
- Validation of gallery completeness

### 4. Integration with Existing Tools
**Enhance:** `tools/ImageGallery/content-creation/gallery-identification/gallery_wizard.py`

**New workflow:**
```
1. Run identification wizard (existing)
2. Review candidates (existing) 
3. NEW: "Create gallery from selected candidates?"
4. NEW: Auto-run workflows on selected images
5. NEW: Auto-generate gallery structure
6. NEW: Provide deployment instructions
```

## Implementation Priority

### Phase 1: Quick Wins (High Impact, Low Effort)
1. **Create gallery automation script** - Single command to create gallery from image directory
2. **Enhance gallery_wizard.py** - Add "create gallery" option after identification
3. **Better error messages** - Clear guidance when steps fail

### Phase 2: UI Integration (Medium Effort, High Impact)  
1. **Add gallery selection to Viewer** - Checkbox system for image selection
2. **Gallery export from ImageDescriber** - Direct export option
3. **Progress indicators** - Visual feedback during gallery creation

### Phase 3: Advanced Features (High Effort, High Impact)
1. **Parallel workflow execution** - Faster gallery creation
2. **Web deployment integration** - Direct upload to servers
3. **Gallery management system** - Edit existing galleries

## Success Criteria

A simplified gallery creation workflow should achieve:

- **⏱️ Time Reduction**: 30-45 minutes → 5-10 minutes for basic gallery
- **🎯 Reduced Steps**: 7+ manual phases → 2-3 user decisions
- **🔧 Less Technical**: No terminal commands for basic users
- **🎨 Better Integration**: Create galleries directly from image viewing
- **⚡ Automation**: Batch workflow execution with progress feedback
- **🛡️ Error Reduction**: Fewer opportunities for user mistakes

## Related Issues
- Gallery identification workflow (recently completed)
- IDW workspace integration (recently completed)
- Viewer tool enhancements
- ImageDescriber workflow improvements

## User Stories

### As a casual user...
> "I want to create a gallery of my vacation photos without learning complex command-line workflows. I should be able to browse my photos, mark favorites, and click 'Create Gallery' to get a web-ready gallery."

### As a power user...
> "I want to go from a large photo collection to multiple themed galleries quickly. I should be able to identify candidates for different themes and automatically generate galleries for each theme."

### As a content creator...
> "I want to integrate gallery creation into my existing workflow. When I'm reviewing images in the Viewer, I should be able to build galleries incrementally by marking images as I review them."

## Technical Considerations

### Backward Compatibility
- Keep existing manual workflow as option for power users
- Don't break existing gallery creation scripts
- Maintain current gallery format and structure

### Performance
- Run workflows in parallel where possible
- Provide progress feedback for long operations
- Allow cancellation of gallery creation process

### Error Handling
- Graceful failure recovery
- Clear error messages with suggested fixes
- Validation before starting long processes

### API Management
- Centralized API key handling
- Cost estimation before starting workflows
- Rate limiting and quota management

---

## Next Steps
1. **Gather user feedback** on proposed workflows
2. **Prototype automation script** for Phase 1 implementation  
3. **Design UI integration** for Viewer/ImageDescriber tools
4. **Create implementation timeline** based on complexity analysis

This enhancement would significantly improve the user experience for one of IDT's most powerful features - creating comparative galleries of AI-generated descriptions.