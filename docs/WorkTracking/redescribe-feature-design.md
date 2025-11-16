# Redescribe Feature Design Document

## Problem Statement

Converting images (HEIC → JPG) and extracting video frames can take significant time for large media collections. When users want to re-describe the same set of images with different AI models, prompt styles, or providers, they currently must:

1. Re-run the entire workflow (wasting time on conversion/extraction)
2. OR manually copy files between directories (error-prone, complex)
3. OR use `--resume` with `--preserve-descriptions` (doesn't create a clean new workflow)

**Goal**: Enable efficient re-description of existing processed images without re-running expensive preprocessing steps, while maintaining clean workflow separation and data integrity.

## Use Cases

### Primary Use Cases
1. **Model Comparison**: Describe same images with different models (GPT-4o vs Claude vs Llama)
2. **Prompt Experimentation**: Try different prompt styles (narrative vs technical vs detailed)
3. **Provider Testing**: Compare local (Ollama) vs cloud (OpenAI/Claude) results
4. **Quality Improvement**: Re-describe with newer/better model while preserving original results
5. **Batch Correction**: Fix descriptions after prompt refinement without re-converting images

### Example Scenarios
```bash
# Original workflow with HEIC conversion + video extraction (30 minutes)
idt workflow vacation_media --provider ollama --model llava:7b

# Want to compare with GPT-4o (should take ~5 minutes, not 30)
idt workflow --redescribe wf_vacation_ollama_llava7b_narrative_20251115_100000 \
  --provider openai --model gpt-4o

# Try different prompt style on same images
idt workflow --redescribe wf_vacation_ollama_llava7b_narrative_20251115_100000 \
  --prompt-style technical

# Test new Florence-2 model on existing processed images
idt workflow --redescribe wf_vacation_ollama_llava7b_narrative_20251115_100000 \
  --provider onnx --model microsoft/Florence-2-base
```

## Design Principles

### 1. **Data Safety First**
- NEVER modify the source workflow directory
- Create entirely new workflow directory for redescribe results
- Preserve all original descriptions and metadata
- Use symlinks/hardlinks when possible to avoid disk duplication

### 2. **Clean Workflow Separation**
- Each redescribe creates a standalone workflow directory
- Full workflow_metadata.json with provenance information
- Independent HTML reports and helper scripts
- Can be analyzed, compared, or deleted independently

### 3. **Efficiency Without Compromise**
- Skip video extraction if source workflow already has frames
- Skip image conversion if source workflow already has converted images
- But still run describe + HTML steps fully
- Validate source workflow integrity before proceeding

### 4. **Clear Provenance Tracking**
- Metadata clearly indicates this is a redescribe operation
- Reference to source workflow directory
- Track what was reused vs freshly generated
- Enable workflow lineage analysis

## Technical Implementation

### Command Syntax

```bash
# Primary command
idt workflow --redescribe <source_workflow_dir> [standard workflow options]

# Equivalent alternatives for clarity
idt redescribe <source_workflow_dir> [options]  # Shortcut command
idt workflow --from <source_workflow_dir> [options]  # Alternate flag
```

### Arguments and Behavior

**New Arguments:**
- `--redescribe <dir>`: Source workflow directory to reuse images from
- `--reuse-steps <steps>`: Explicitly specify which steps to reuse (default: auto-detect)
  - Examples: `--reuse-steps video,convert` or `--reuse-steps all-except-describe`
- `--link-images`: Use symlinks/hardlinks instead of copying images (default: auto-detect based on filesystem)
- `--force-copy`: Always copy images even if linking is available

**Inherited Arguments** (work as normal):
- `--provider`, `--model`, `--prompt-style`: New AI configuration for descriptions
- `--output-dir`: Override default output location
- `--config-image-describer`: Use different prompt configuration
- All other standard workflow options

**Incompatible Arguments** (error if used with --redescribe):
- `input_source` positional argument (source is the workflow dir)
- `--download`, `--resume` (conflicting modes)
- `--steps` including video or convert (those are determined by source workflow)

### Workflow Directory Structure

**Source Workflow** (what we're reading from):
```
wf_2025-11-15_143022_gpt4o_narrative/
├── workflow_metadata.json          # Contains input_directory path
├── extracted_frames/               # Video frames (if video step ran)
│   └── *.jpg
├── converted_images/               # HEIC→JPG conversions (if convert step ran)
│   └── *.jpg
└── descriptions/
    ├── image_descriptions.txt
    └── image_descriptions.html

Note: Direct input images (JPG/PNG that needed no conversion) are NOT stored
in the workflow directory. They remain in the original input_directory specified
in workflow_metadata.json.
```

**Redescribed Workflow** (what we're creating):
```
wf_2025-11-16_092045_claude-sonnet45_narrative/
├── workflow_metadata.json          # New metadata with redescribe_operation field
├── extracted_frames/               # Hardlinked/copied from source
│   └── *.jpg
├── converted_images/               # Hardlinked/copied from source
│   └── *.jpg
├── input_images/                   # NEW: Direct input images from original_input_directory
│   └── *.jpg                       # Hardlinked/copied from source metadata's input_directory
└── descriptions/
    ├── image_descriptions.txt      # Freshly generated with new AI settings
    └── image_descriptions.html     # Freshly generated HTML report
```

**Key Implementation Detail**: The `input_images/` directory is only created during redescribe
operations. It contains images that were in the original input directory but needed no
conversion (already JPG/PNG format). The workflow orchestrator scans all three directories
when executing the describe step.

```
wf_vacation_openai_gpt-4o_narrative_20251115_120000/
├── workflow_metadata.json        # Indicates redescribe operation
├── converted_images/              # → Symlink to source workflow
├── descriptions/                  
│   └── image_descriptions.txt     # NEW - freshly generated
├── html_reports/
│   └── image_descriptions.html    # NEW - freshly generated  
├── resume_workflow.bat            # NEW - for this workflow
├── view_results.bat               # NEW - for this workflow
└── workflow.log                   # NEW - for this workflow
```

### Metadata Schema Extensions

**workflow_metadata.json additions:**
```json
{
  "workflow_name": "vacation",
  "provider": "openai",
  "model": "gpt-4o",
  "prompt_style": "narrative",
  "timestamp": "20251115_120000",
  
  "redescribe_operation": {
    "is_redescribe": true,
    "source_workflow": "/full/path/to/wf_vacation_ollama_llava7b_narrative_20251115_100000",
    "source_workflow_name": "wf_vacation_ollama_llava7b_narrative_20251115_100000",
    "reused_steps": ["video", "convert"],
    "images_linked": true,  // vs copied
    "source_metadata": {
      "original_provider": "ollama",
      "original_model": "llava:7b",
      "original_prompt": "narrative",
      "original_timestamp": "20251115_100000"
    },
    "redescribe_timestamp": "20251115_120000",
    "redescribe_reason": "model_comparison"  // Optional user-provided
  },
  
  "steps_executed": ["describe", "html"],
  "config_workflow": "workflow_config.json",
  "config_image_describer": "image_describer_config.json"
}
```

### Implementation Steps

#### 1. Argument Parsing & Validation
```python
def validate_redescribe_args(args):
    """Validate arguments for redescribe operation"""
    
    # Check for incompatible arguments
    if args.redescribe:
        if args.input_source:
            raise ValueError("Cannot specify input_source with --redescribe")
        if args.resume:
            raise ValueError("Cannot use --resume with --redescribe")
        if args.download:
            raise ValueError("Cannot use --download with --redescribe")
    
    # Validate source workflow exists and is valid
    source_dir = Path(args.redescribe)
    if not source_dir.exists():
        raise ValueError(f"Source workflow not found: {source_dir}")
    
    # Load source metadata
    source_metadata = load_workflow_metadata(source_dir)
    if not source_metadata:
        raise ValueError(f"Invalid workflow directory (no metadata): {source_dir}")
    
    # Check for required directories
    required_dirs = ["converted_images"]  # At minimum
    for dir_name in required_dirs:
        dir_path = source_dir / dir_name
        if not dir_path.exists():
            raise ValueError(f"Source workflow missing {dir_name} directory")
    
    return source_dir, source_metadata
```

#### 2. Determine Reusable Steps
```python
def determine_reusable_steps(source_dir: Path, source_metadata: Dict) -> List[str]:
    """Analyze source workflow to determine which steps can be reused"""
    
    reusable = []
    
    # Check for extracted video frames
    extracted_frames = source_dir / "extracted_frames"
    if extracted_frames.exists() and any(extracted_frames.iterdir()):
        reusable.append("video")
        logging.info(f"Found {len(list(extracted_frames.glob('*.jpg')))} extracted frames")
    
    # Check for converted images  
    converted_images = source_dir / "converted_images"
    if converted_images.exists() and any(converted_images.iterdir()):
        reusable.append("convert")
        image_count = len(list(converted_images.glob('*.jpg'))) + \
                      len(list(converted_images.glob('*.png')))
        logging.info(f"Found {image_count} converted images")
    
    # Check for direct input images (images that needed no conversion)
    # IMPLEMENTATION NOTE (Nov 16, 2024): This was added after initial release
    # to handle JPG/PNG files that were processed directly from input directory
    original_input = source_metadata.get("input_directory")
    if original_input:
        original_input_path = Path(original_input)
        if original_input_path.exists():
            supported_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]
            input_images = []
            for fmt in supported_formats:
                input_images.extend(original_input_path.glob(f"*{fmt}"))
                input_images.extend(original_input_path.glob(f"*{fmt.upper()}"))
            
            # Only count direct children (not subdirectories)
            direct_images = [img for img in input_images if img.parent == original_input_path]
            
            if direct_images:
                reusable.append("input")
                logging.info(f"Found {len(direct_images)} direct input images")
    
    return reusable
```

**IMPORTANT**: Direct input images (images already in JPG/PNG format) are not stored in the workflow directory structure during the original workflow. They remain in the original input directory. The redescribe feature accesses them via the `input_directory` field in the source workflow's metadata.
                     len(list(converted_images.glob('*.png')))
        logging.info(f"Found {image_count} converted images")
    
    return reusable
```

#### 3. Image Reuse Strategy
```python
def reuse_images(source_dir: Path, dest_dir: Path, method: str = "auto") -> str:
    """
    Reuse images from source workflow in destination workflow
    
    Args:
        source_dir: Source workflow directory
        dest_dir: Destination workflow directory  
        method: "auto", "link", "copy"
    
    Returns:
        Method used: "hardlink", "symlink", or "copy"
    """
    
    source_images = source_dir / "converted_images"
    dest_images = dest_dir / "converted_images"
    
    # Determine method
    if method == "auto":
        # Check if linking is supported on this filesystem
        if can_create_hardlinks(source_images.parent, dest_images.parent):
            method = "hardlink"
        elif can_create_symlinks():
            method = "symlink"
        else:
            method = "copy"
    
    logging.info(f"Reusing images via {method}")
    
    if method == "hardlink":
        # Create hardlinks (same filesystem, no space duplication)
        dest_images.mkdir(parents=True, exist_ok=True)
        for img in source_images.glob("*"):
            if img.is_file():
                os.link(str(img), str(dest_images / img.name))
        return "hardlink"
    
    elif method == "symlink":
        # Create symlink to entire directory (fast, but some tools may not follow)
        if dest_images.exists():
            dest_images.rmdir()
        dest_images.symlink_to(source_images.resolve(), target_is_directory=True)
        return "symlink"
    
    else:  # copy
        # Fall back to copying (slower, uses disk space)
        shutil.copytree(source_images, dest_images, dirs_exist_ok=True)
        return "copy"
```

#### 4. Create New Workflow Directory
```python
def create_redescribe_workflow(source_dir: Path, args) -> Path:
    """Create new workflow directory for redescribe operation"""
    
    # Generate new workflow name components
    workflow_name = source_metadata.get("workflow_name", "redescribe")
    provider = args.provider
    model = sanitize_name(args.model or get_default_model(provider))
    prompt_style = args.prompt_style or "narrative"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create directory name
    dir_name = f"wf_{workflow_name}_{provider}_{model}_{prompt_style}_{timestamp}"
    
    # Determine output location
    if args.output_dir:
        output_base = Path(args.output_dir)
    else:
        # Use same parent directory as source workflow
        output_base = source_dir.parent
    
    dest_dir = output_base / dir_name
    dest_dir.mkdir(parents=True, exist_ok=False)
    
    return dest_dir
```

#### 5. Execute Redescribe Workflow
```python
def run_redescribe_workflow(source_dir: Path, source_metadata: Dict, args):
    """Execute redescribe workflow"""
    
    # Validate arguments
    validate_redescribe_args(args)
    
    # Create new workflow directory
    dest_dir = create_redescribe_workflow(source_dir, args)
    
    # Determine what can be reused
    reusable_steps = determine_reusable_steps(source_dir, source_metadata)
    
    # Reuse images (link or copy)
    link_method = reuse_images(source_dir, dest_dir, 
                               method="link" if args.link_images else "auto")
    
    # Build redescribe metadata
    redescribe_metadata = {
        "is_redescribe": True,
        "source_workflow": str(source_dir.resolve()),
        "source_workflow_name": source_dir.name,
        "reused_steps": reusable_steps,
        "images_linked": link_method in ["hardlink", "symlink"],
        "link_method": link_method,
        "original_input_directory": source_metadata.get("input_directory"),  # NEW: For direct input images
        "source_metadata": {
            "original_provider": source_metadata.get("provider"),
            "original_model": source_metadata.get("model"),
            "original_prompt": source_metadata.get("prompt_style"),
            "original_timestamp": source_metadata.get("timestamp")
        },
        "redescribe_timestamp": datetime.now().isoformat()
    }
    
    # Build full workflow metadata
    workflow_metadata = {
        "workflow_name": source_metadata.get("workflow_name", "redescribe"),
        "provider": args.provider,
        "model": args.model or get_default_model(args.provider),
        "prompt_style": args.prompt_style or "narrative",
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "redescribe_operation": redescribe_metadata,
        "steps_executed": ["describe", "html"],
        "config_workflow": args.config_workflow,
        "config_image_describer": args.config_image_describer
    }
    
    save_workflow_metadata(dest_dir, workflow_metadata)
    
    # Execute workflow steps (only describe + HTML)
    steps_to_run = ["describe", "html"]
    
    # Use converted_images as input directory
    input_dir = dest_dir / "converted_images"
    
    # Run orchestrator with limited steps
    orchestrator = WorkflowOrchestrator(
        config_file=args.config_workflow,
        logger=WorkflowLogger(dest_dir / "workflow.log")
    )
    
    results = orchestrator.run_workflow(
        input_dir=input_dir,
        output_dir=dest_dir,
        steps=steps_to_run,
        workflow_metadata=workflow_metadata
    )
    
    # Create helper scripts
    create_workflow_helper_files(dest_dir, workflow_metadata)
    
    return dest_dir, results
```

### Error Handling

**Pre-flight Checks:**
- Source workflow must exist and be valid
- Source workflow must have completed image processing (convert or video)
- Source workflow metadata must be readable
- Required directories must exist in source

**Runtime Validation:**
- Verify image count matches between source and destination
- Validate symlinks/hardlinks created successfully
- Check disk space before copying (if copy method used)
- Verify describe step can access images

**User-Friendly Errors:**
```bash
# Missing source workflow
ERROR: Source workflow not found: wf_vacation_20251115_100000
       Check the path and try again.

# Invalid workflow
ERROR: Not a valid workflow directory (missing workflow_metadata.json)
       Directory: wf_vacation_20251115_100000
       Hint: Use 'idt list' to see available workflows

# Incomplete source workflow  
ERROR: Source workflow has not completed image processing
       Missing directory: converted_images
       Run source workflow to completion before redescribing

# Insufficient disk space (copy mode)
ERROR: Insufficient disk space to copy images
       Required: 2.3 GB
       Available: 1.1 GB
       Hint: Use --link-images to avoid copying
```

## User Interface

### Command Help Text
```
idt workflow --redescribe <source_workflow> [options]

Re-describe images from an existing workflow with different AI settings,
without re-running expensive video extraction or image conversion steps.

Arguments:
  source_workflow       Path to completed workflow directory (e.g., wf_vacation_...)

Required Options (at least one):
  --provider PROVIDER   Change AI provider (ollama, openai, claude, onnx)
  --model MODEL         Change AI model
  --prompt-style STYLE  Change prompt style (narrative, detailed, technical, etc.)

Optional:
  --output-dir DIR      Custom output directory (default: same parent as source)
  --link-images         Use symlinks/hardlinks (faster, no space duplication)
  --force-copy          Always copy images (slower, more compatible)
  --config-image-describer FILE  Use different prompt configuration

Examples:
  # Compare models
  idt workflow --redescribe wf_photos_ollama_llava_narrative_20251115_100000 \\
    --provider openai --model gpt-4o

  # Try different prompt style
  idt workflow --redescribe wf_photos_ollama_llava_narrative_20251115_100000 \\
    --prompt-style technical
```

### Progress Output
```
Redescribe Workflow: wf_vacation_ollama_llava7b_narrative_20251115_100000
================================================================================

Source Workflow Analysis:
  Directory: wf_vacation_ollama_llava7b_narrative_20251115_100000
  Original Provider: ollama / llava:7b
  Original Prompt: narrative
  Images Found: 143 converted images
  
New Workflow Configuration:
  Provider: openai
  Model: gpt-4o
  Prompt Style: narrative
  Output: wf_vacation_openai_gpt-4o_narrative_20251115_120000

Reusing Existing Data:
  ✓ Skipping video extraction (using 143 existing frames)
  ✓ Skipping image conversion (linking to source images)
  → Created hardlinks (0 MB disk space used)

Running Workflow Steps:
  [1/2] Describing images with openai/gpt-4o... 
    Progress: 143/143 images (100%)
    Time: 8m 23s
  [2/2] Generating HTML report...
    Created: html_reports/image_descriptions.html

Workflow Complete!
  Output: wf_vacation_openai_gpt-4o_narrative_20251115_120000
  Time Saved: ~22 minutes (skipped video + convert)
  
View results: idt viewer wf_vacation_openai_gpt-4o_narrative_20251115_120000
```

## Testing Strategy

### Unit Tests
- `test_validate_redescribe_args()`: Argument validation logic
- `test_determine_reusable_steps()`: Step detection from source workflow
- `test_reuse_images()`: Image linking/copying logic
- `test_create_redescribe_metadata()`: Metadata generation

### Integration Tests  
- Full redescribe workflow with ollama → openai
- Redescribe with different prompt styles
- Redescribe with --link-images vs --force-copy
- Invalid source workflows (incomplete, missing metadata, etc.)

### Manual Testing Scenarios
1. Redescribe 100-image workflow with different models (verify time savings)
2. Redescribe with symlinks on Windows/Linux/macOS
3. Redescribe source workflow on different drive (verify copy fallback)
4. Delete source workflow after redescribe (verify dest workflow still works)
5. Chain redescribes (A → B → C) to test metadata lineage

## Future Enhancements

### Phase 2 Features
- `idt compare <workflow1> <workflow2>`: Side-by-side comparison of descriptions
- `--merge-descriptions`: Combine multiple workflows' descriptions into one report
- `--redescribe-batch`: Apply same settings to multiple source workflows
- Interactive mode: Show diff preview before running redescribe

### Phase 3 Features
- Workflow lineage visualization (graph of redescribe operations)
- Cost comparison reporting (tokens/API costs across workflows)
- Quality metrics (description length, diversity, etc.)
- Automatic redescribe suggestions based on new model releases

## Implementation Checklist

- [ ] Add `--redescribe` argument to argument parser
- [ ] Implement `validate_redescribe_args()`
- [ ] Implement `determine_reusable_steps()`
- [ ] Implement `reuse_images()` with link/copy logic
- [ ] Implement `create_redescribe_workflow()`
- [ ] Extend workflow_metadata.json schema
- [ ] Update `run_workflow()` to handle redescribe mode
- [ ] Add redescribe-specific error messages
- [ ] Update help text and documentation
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Test on Windows/Linux/macOS
- [ ] Update CHANGELOG.md
- [ ] Update README.md with examples
- [ ] Create docs/REDESCRIBE_GUIDE.md

## Documentation Updates

### Files to Update
- `README.md`: Add redescribe examples to main usage section
- `docs/REDESCRIBE_GUIDE.md`: New comprehensive guide (NEW)
- `CHANGELOG.md`: Document new feature
- `.github/copilot-instructions.md`: Add redescribe patterns for AI agents

### Example Documentation Structure

**docs/REDESCRIBE_GUIDE.md**:
1. Introduction & Benefits
2. Quick Start Examples
3. How It Works (technical overview)
4. Command Reference
5. Performance Comparison Charts
6. Troubleshooting
7. Best Practices
8. Advanced Usage (lineage, comparison, etc.)

## Open Questions

1. **Directory Naming**: Should redescribed workflows include "redescribe" in name?
   - Pro: Makes it obvious this is derived
   - Con: Makes names longer
   - Decision: NO - treat as normal workflow, metadata indicates origin

2. **Default Output Location**: Same parent as source or different default?
   - Decision: Same parent as source (keeps related workflows together)

3. **Symlink Behavior**: Follow symlinks in source or error?
   - Decision: Follow and warn if source uses symlinks

4. **Concurrent Redescribes**: Allow multiple redescribes from same source?
   - Decision: YES - timestamps prevent conflicts

5. **Cleanup**: Should deleting source workflow warn about descendants?
   - Decision: FUTURE - not in v1, add in Phase 2

## Success Metrics

- **Time Savings**: Redescribe completes in <30% of original workflow time
- **Disk Efficiency**: Hardlink mode uses <1% additional disk space
- **User Adoption**: 25%+ of workflows are redescribes after 3 months
- **Error Rate**: <2% of redescribe operations fail validation
- **Documentation**: Zero "how do I..." issues filed about redescribe

## Conclusion

The `--redescribe` feature will dramatically improve the user experience for model/prompt experimentation while maintaining the project's high standards for data integrity, workflow clarity, and user-friendly design. By reusing expensive preprocessing steps and creating clean, independent workflow results, users can iterate rapidly without complexity or risk.
