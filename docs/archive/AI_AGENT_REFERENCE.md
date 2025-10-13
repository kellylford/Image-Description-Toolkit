# Image Description Toolkit - AI Agent Technical Reference

**Purpose**: Onboard AI agents to the IDT project quickly with essential technical context.  
**Last Updated**: October 11, 2025  
**Target Audience**: AI coding assistants needing project understanding

---

## Project Overview

**Image Description Toolkit (IDT)** is a comprehensive system for batch-processing images through AI vision models to generate descriptions. It supports multiple AI providers (Claude, OpenAI, Ollama) and provides both CLI and GUI interfaces.

**Core Value Proposition**: Automate bulk image description with provider flexibility, workflow management, and quality monitoring.

---

## Architecture at a Glance

```
IDT System Architecture
├── CLI Entry Point (idt.exe / idt_cli.py)
│   └── Command Router → Dispatches to components
│
├── Core Components (scripts/)
│   ├── workflow.py - Main orchestrator
│   ├── image_describer.py - AI provider integration
│   ├── ConvertImage.py - Image optimization/conversion
│   ├── descriptions_to_html.py - HTML report generator
│   └── video_frame_extractor.py - Video processing
│
└── GUI Applications (separate executables)
    ├── imagedescriber/ - Visual AI processing tool
    ├── viewer/ - Browse/review descriptions
    └── prompt_editor/ - Manage AI prompts
```

**Key Principle**: One CLI executable (`idt.exe`) + Three separate GUI executables, all built with PyInstaller.

---

## CLI System (idt.exe / idt_cli.py)

### Entry Point: `idt_cli.py`

**Purpose**: Single unified command dispatcher - does NOT contain business logic, only routes commands.

**Architecture Pattern**: Router only - delegates to existing scripts
```python
# idt_cli.py structure:
def main():
    command = sys.argv[1] if len(sys.argv) > 1 else None
    
    if command == 'workflow':
        # Route to scripts/workflow.py
    elif command == 'image_describer':
        # Route to scripts/image_describer.py
    elif command == 'viewer':
        # Launch viewer.exe (separate process)
    # ... etc
```

**Why This Design**: 
- Scripts can be used standalone OR through CLI
- Easier testing (test scripts directly)
- Clear separation of concerns
- Maintains backward compatibility

### Available Commands

| Command | Script | Purpose |
|---------|--------|---------|
| `workflow` | `scripts/workflow.py` | Full workflow orchestration |
| `image_describer` | `scripts/image_describer.py` | Batch describe images |
| `descriptions-to-html` | `scripts/descriptions_to_html.py` | Generate HTML reports |
| `convert-images` | `scripts/ConvertImage.py` | HEIC → JPG conversion |
| `extract-frames` | `scripts/video_frame_extractor.py` | Extract video frames |
| `check-models` | `models/check_models.py` | Verify Ollama models |
| `stats` | `analysis/analyze_workflow_stats.py` | Performance analysis |
| `contentreview` | `analysis/analyze_description_content.py` | Content quality |
| `combinedescriptions` | `analysis/combine_workflow_descriptions.py` | Aggregate results |
| `viewer` | Launches `viewer.exe` | GUI workflow browser |
| `version` | Built-in | Show version info |

**Usage Pattern**:
```bash
idt <command> [args...]
# Example: idt workflow images/ --provider claude --model claude-3-haiku-20240307
```

---

## Core Workflow System

### Main Orchestrator: `scripts/workflow.py`

**Purpose**: End-to-end automation of image description workflows.

**Workflow Steps**:
1. **Video Processing** - Extract frames from videos (if any)
2. **Image Conversion** - Convert HEIC to JPG (if any)
3. **Image Description** - Send to AI provider for descriptions
4. **HTML Generation** - Create browsable HTML report

**Key Features**:
- Multi-step orchestration with dependency management
- Resume capability (progress tracking)
- Provider-agnostic (works with any AI backend)
- Comprehensive logging and error handling

**Output Structure**:
```
workflow_output/
├── descriptions/
│   └── image_descriptions.txt     # Live description file (plain text)
├── html_reports/
│   └── image_descriptions.html    # Final browsable report
├── logs/
│   ├── workflow_TIMESTAMP.log
│   └── image_describer_TIMESTAMP.log
└── temp_combined_images/          # Staging area (cleaned up after)
```

**Critical Implementation Detail**: Workflow copies images to temp directory to maintain relative paths, then processes from there. This ensures HTML links work correctly.

### AI Provider Integration: `scripts/image_describer.py`

**Purpose**: Provider-agnostic interface to AI vision models.

**Supported Providers**:
- **Claude** (Anthropic) - API key via env var `ANTHROPIC_API_KEY`
- **OpenAI** (GPT-4 Vision) - API key via env var `OPENAI_API_KEY`
- **Ollama** (Local models) - No auth, expects Ollama running on localhost:11434

**Key Class**: `ImageDescriber`
```python
class ImageDescriber:
    def __init__(self, provider, model, prompt_style, config):
        # Initializes provider-specific client
        
    def describe_image(self, image_path):
        # Returns description string
        # Handles provider differences internally
```

**Image Size Optimization** (CRITICAL):
- **Problem**: AI providers have image size limits (Claude: 5MB, OpenAI: 20MB)
- **Solution**: Pre-optimization in `ConvertImage.py`
- **Target**: 3.75MB file size (accounts for base64 encoding ~33% overhead)
- **Base64 Math**: 3.75MB file × 1.33 = ~5MB encoded (Claude's limit)
- **Location**: 
  - `scripts/ConvertImage.py` line 48: `TARGET_MAX_SIZE = 3.75 * 1024 * 1024`
  - `imagedescriber/imagedescriber.py` line 724: Same limit

**Why 3.75MB?**: Images are base64-encoded for API transmission. 4/3 encoding ratio means 3.75MB → ~5MB encoded.

**Prompt System**:
- Prompts defined in `models/<provider>_prompts.json`
- Styles: `default`, `technical`, `artistic`, `narrative`
- Each provider has customized prompts optimized for their model behavior

### Image Optimization: `scripts/ConvertImage.py`

**Purpose**: Ensure images meet provider size requirements.

**Functions**:
1. `convert_heic_to_jpg()` - Convert Apple HEIC format to JPG
2. `optimize_image_size()` - Reduce file size while preserving quality

**Optimization Strategy**:
```python
def optimize_image_size(image_path, max_file_size=TARGET_MAX_SIZE, quality=90):
    # Iteratively reduce quality until under target
    # Max 10 attempts, reducing quality by 5 each iteration
    # Returns: (success, original_size, final_size)
```

**Provider Limits**:
- Claude: 5MB (base64-encoded)
- OpenAI: 20MB (base64-encoded)
- Ollama: No limit (local processing)

**Defense in Depth**:
- Primary optimization: Called before sending to provider
- Fallback safety check: Re-checks size before API call (lines 453-463 in image_describer.py)

---

## GUI Applications

### 1. ImageDescriber GUI (`imagedescriber/imagedescriber.py`)

**Purpose**: Visual interface for AI image processing with live preview.

**Technology**: PyQt6

**Key Features**:
- Drag-and-drop image loading
- Real-time provider/model selection
- Live description preview
- Batch processing with progress bars
- Copy descriptions to clipboard

**Build**: Separate executable (`imagedescriber.exe`)

**Integration**: Standalone - does NOT use scripts/ (has own implementation)

**Why Separate**: Different UX requirements, real-time feedback, visual workflow

### 2. Viewer (`viewer/viewer.py`)

**Purpose**: Browse and review workflow results.

**Technology**: PyQt6

**Modes**:
1. **HTML Mode** - View completed workflows from HTML reports
2. **Live Mode** - Monitor in-progress workflows with real-time updates

**Command-Line Interface** (NEW - Oct 11, 2025):
```bash
viewer.exe                          # Empty viewer (manual browse)
viewer.exe <directory>              # Load specific workflow output
viewer.exe --open                   # Launch to directory picker
viewer.exe --help                   # Show usage
```

**Live Mode Features**:
- QFileSystemWatcher monitors `descriptions/image_descriptions.txt`
- Auto-refresh on file changes
- Progress tracking (current/total images)
- Seamlessly transitions to HTML mode when workflow completes

**Redescription Feature**:
- Requires Ollama running locally
- Fetches available models dynamically
- Updates description in-place
- Marks updated entries visually

**Build**: Separate executable (`viewer_<arch>.exe`)

**Architecture Detection**: Automatically detects AMD64 vs ARM64 and builds accordingly

### 3. Prompt Editor (`prompt_editor/prompt_editor.py`)

**Purpose**: Manage AI prompts across providers and styles.

**Technology**: PyQt6

**Features**:
- Edit prompts for all provider/style combinations
- Preview before saving
- Validate JSON structure
- Backup management

**File Structure**:
```
models/
├── claude_prompts.json
├── openai_prompts.json
└── ollama_prompts.json
```

**Prompt Format**:
```json
{
  "default": "Describe this image...",
  "technical": "Provide technical analysis...",
  "artistic": "Describe artistic elements...",
  "narrative": "Tell the story of this image..."
}
```

**Build**: Separate executable (`prompt_editor.exe`)

---

## Build System

### PyInstaller Configuration: `final_working.spec`

**Purpose**: Single-file executable with all dependencies bundled.

**Key Sections**:

1. **`datas`** - Non-Python files to bundle:
```python
datas=[
    ('scripts/*.py', 'scripts'),
    ('scripts/*.json', 'scripts'),
    ('models', 'models'),
    ('analysis', 'analysis'),
    ('VERSION', '.'),
]
```

2. **`hiddenimports`** - Modules not auto-detected:
```python
hiddenimports=[
    'scripts.workflow',
    'scripts.image_describer',
    'PIL', 'anthropic', 'openai', 'ollama',
    # ... etc
]
```

3. **`excludes`** - Modules to skip (reduce size):
```python
excludes=[
    'tkinter', 'matplotlib', 'pandas',
    # GUI frameworks not needed in CLI
]
```

### Build Scripts

**Main CLI Build**: `build_executable.sh` (Linux/Mac) or manual PyInstaller
```bash
pyinstaller final_working.spec
# Creates: dist/idt.exe (~350MB)
```

**Viewer Build**: `viewer/build_viewer.bat`
```batch
pyinstaller --onefile --windowed --name viewer_%ARCH% viewer.py
# Creates: viewer/dist/viewer/viewer_amd64.exe (~100MB)
```

**Why Separate Executables**:
- CLI doesn't need PyQt6 (saves ~200MB)
- GUIs don't need AI provider SDKs
- Faster builds, smaller individual files
- Users can install only what they need

### Resource Path Handling (CRITICAL)

**Problem**: PyInstaller extracts files to temporary directory (`sys._MEIPASS`)

**Solution Pattern** (used everywhere):
```python
def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        # Running as executable
        base_path = Path(sys._MEIPASS)
    else:
        # Running from source
        base_path = Path(__file__).parent
    return base_path / relative_path
```

**Why This Matters**: Scripts must find bundled config files, prompts, etc. at runtime.

---

## Data Flow & Integration

### Typical Workflow Execution

```
User runs: idt workflow images/ --provider claude

1. idt_cli.py receives command
   ↓
2. Routes to workflow.py (via workflow wrapper)
   ↓
3. workflow.py orchestrates:
   a. Check for videos → extract frames (video_frame_extractor.py)
   b. Check for HEIC → convert to JPG (ConvertImage.py)
   c. Copy images to temp directory
   d. Call image_describer.py with temp directory
      ↓
      image_describer.py:
      - Loads config from image_describer_config.json
      - Initializes Claude provider
      - For each image:
        * Optimize size (ConvertImage.optimize_image_size)
        * Base64 encode
        * Send to Claude API
        * Parse response
        * Write to descriptions/image_descriptions.txt
      ↓
   e. Generate HTML (descriptions_to_html.py)
   f. Clean up temp directory
   ↓
4. Output ready in workflow_output/
```

### Viewer Integration with Workflow

**Scenario**: User wants to monitor running workflow

```
Terminal 1:
$ idt workflow images/ --provider claude
[Workflow starts, writes to descriptions/image_descriptions.txt]

Terminal 2:
$ idt viewer
[User browses to workflow output directory]
[Enables "Live Mode" checkbox]
[Viewer watches file, auto-refreshes as descriptions appear]
```

**Technical Implementation**:
- `QFileSystemWatcher` monitors file changes
- `DescriptionFileParser` parses text file incrementally
- UI preserves scroll position during updates
- When workflow completes and HTML is generated, viewer can switch modes

---

## Configuration Files

### `scripts/workflow_config.json`
```json
{
  "default_provider": "ollama",
  "default_model": "moondream",
  "default_prompt_style": "default",
  "video_fps": 1.0,
  "video_quality": 2
}
```

### `scripts/image_describer_config.json`
```json
{
  "model": "moondream",
  "temperature": 0.1,
  "num_predict": 600,
  "top_k": 40,
  "top_p": 0.9,
  "repeat_penalty": 1.3
}
```

**Note**: These are Ollama-specific defaults. Provider-specific configs override at runtime.

### `models/<provider>_prompts.json`

See Prompt Editor section above.

---

## Key Technical Decisions

### 1. Why Router Pattern in idt_cli.py?

**Decision**: CLI only routes, never implements logic

**Rationale**:
- Scripts remain independently testable
- No duplication of business logic
- Easier to maintain (one source of truth)
- Backward compatible (scripts work standalone)

### 2. Why Separate GUI Executables?

**Decision**: Three separate .exe files instead of one mega-executable

**Rationale**:
- Size: CLI doesn't need PyQt6 (~200MB savings)
- Dependencies: GUIs don't need AI SDKs
- Use case: Most users only need CLI + Viewer
- Build time: Faster incremental builds

### 3. Why 3.75MB Image Size Limit?

**Decision**: Target 3.75MB file size (not 4.5MB, not 5MB)

**Rationale**:
- Claude API limit: 5MB base64-encoded
- Base64 encoding: 4/3 size increase
- Math: 5MB / 1.33 = 3.75MB
- Safety margin: Accounts for metadata overhead

**Historical Context**: Originally used 4.5MB, but images still failed. Investigation revealed base64 encoding overhead was the culprit. Fixed Oct 11, 2025.

### 4. Why Text File + HTML Instead of Database?

**Decision**: Plain text file during processing, HTML for viewing

**Rationale**:
- Portability: No DB server needed
- Human-readable: Easy debugging
- Live monitoring: File watchers work simply
- Archival: HTML is self-contained
- Performance: Fast for typical workflows (100-1000 images)

### 5. Why Provider Abstraction?

**Decision**: Single `ImageDescriber` class, multiple provider implementations

**Rationale**:
- User flexibility: Switch providers without workflow changes
- Cost optimization: Use cheap/free Ollama for testing, Claude for production
- API stability: Abstract away provider differences
- Future-proof: Easy to add new providers

---

## Common Patterns & Conventions

### Error Handling
```python
# Standard pattern across all scripts:
try:
    result = do_something()
    logger.info(f"Success: {result}")
except SpecificException as e:
    logger.error(f"Failed: {e}")
    # Graceful degradation or exit
```

### Logging
```python
# Setup (done in each script):
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log to both console and file:
file_handler = logging.FileHandler(log_file)
logger.addHandler(file_handler)
```

### Path Handling
```python
# Always use pathlib.Path for cross-platform compatibility
from pathlib import Path

input_dir = Path(args.input_dir).resolve()
output_file = input_dir / "descriptions" / "image_descriptions.txt"
```

### Configuration Loading
```python
# Standard config pattern:
def load_config(config_path):
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return default_config()
```

---

## Testing

### Test Executable: `test_executable.py`

**Purpose**: Verify idt.exe works correctly

**Tests**:
- Command routing
- Resource bundling
- Help text
- Version display
- Path resolution

**Usage**:
```bash
python test_executable.py dist/idt.exe
```

### Manual Testing Checklist

**After building idt.exe**:
1. `idt.exe --version` (should show version)
2. `idt.exe help` (should show all commands)
3. `idt.exe workflow <test_images> --provider ollama` (end-to-end test)
4. Check output structure
5. Test viewer: `idt.exe viewer`

---

## Debugging Tips for AI Agents

### Problem: "Module not found" in executable

**Check**:
1. Is module in `hiddenimports` in `final_working.spec`?
2. Is file in `datas` section?
3. Did you rebuild after changes?

### Problem: "Config file not found"

**Check**:
1. Using `get_resource_path()` helper?
2. Config file in `datas` section of spec?
3. Path relative to `sys._MEIPASS` (not `__file__`)?

### Problem: Images rejected by AI provider

**Check**:
1. File size before/after optimization
2. Base64 encoded size (× 1.33 overhead)
3. Provider limits (Claude: 5MB, OpenAI: 20MB)
4. Optimization logs show actual sizes

### Problem: Workflow fails mid-process

**Check**:
1. Log files in `workflow_output/logs/`
2. Progress file for last successful image
3. API credentials set in environment
4. Ollama running (if using local models)

---

## File Structure Reference

```
idt/
├── idt_cli.py              # Main CLI entry point (router only)
├── workflow.py             # Workflow wrapper
├── idt_runner.py           # Alternative entry point
├── final_working.spec      # PyInstaller build config
├── VERSION                 # Version number (e.g., "1.0.0")
│
├── scripts/                # Core business logic
│   ├── workflow.py         # Orchestrator
│   ├── image_describer.py  # AI integration
│   ├── ConvertImage.py     # Image optimization
│   ├── descriptions_to_html.py
│   ├── video_frame_extractor.py
│   └── *.json              # Config files
│
├── models/                 # AI prompts and model checks
│   ├── check_models.py
│   ├── claude_prompts.json
│   ├── openai_prompts.json
│   └── ollama_prompts.json
│
├── analysis/               # Post-workflow analysis
│   ├── analyze_workflow_stats.py
│   ├── analyze_description_content.py
│   └── combine_workflow_descriptions.py
│
├── imagedescriber/         # GUI app (standalone)
│   ├── imagedescriber.py
│   └── (build scripts)
│
├── viewer/                 # Viewer GUI (standalone)
│   ├── viewer.py
│   ├── build_viewer.bat
│   └── README.md
│
├── prompt_editor/          # Prompt management GUI
│   └── prompt_editor.py
│
├── bat/                    # Helper batch scripts
│   ├── run_*.bat           # Quick-launch scripts for common tasks
│   └── setup_*_key.bat     # API key configuration
│
└── docs/                   # Documentation
    ├── AI_AGENT_REFERENCE.md (this file)
    ├── QUICK_START.md
    └── WorkTracking/       # Development notes
```

---

## Quick Reference: Common Tasks

### Add New AI Provider

1. Create `models/<provider>_prompts.json`
2. Update `scripts/image_describer.py`:
   - Add provider case in `__init__`
   - Implement client initialization
   - Add to `describe_image()` method
3. Update `final_working.spec` hiddenimports
4. Rebuild

### Add New CLI Command

1. Create script in `scripts/`
2. Add command case to `idt_cli.py`
3. Add to help text in `print_usage()`
4. Update `final_working.spec` datas/hiddenimports
5. Rebuild

### Modify Image Size Limits

**Files to update**:
- `scripts/ConvertImage.py` line 48 (`TARGET_MAX_SIZE`)
- `imagedescriber/imagedescriber.py` line 724 (`max_size`)
- `scripts/image_describer.py` line 392 (comment)

**Remember**: Account for base64 encoding (4/3 overhead)

### Update Prompts

1. Edit `models/<provider>_prompts.json` directly, OR
2. Use Prompt Editor GUI
3. No rebuild needed (prompts loaded at runtime)

---

## Version History Context

**Current Version**: 1.0.0 (preparing first release)

**Recent Major Changes** (October 2025):
- Fixed image size optimization (3.75MB limit for base64 overhead)
- Added viewer CLI (--open, directory arg, --help)
- Integrated viewer launcher in main CLI
- Comprehensive documentation overhaul

---

## For AI Agents: How to Use This Document

**When helping with**:
- Architecture questions → See "Architecture at a Glance"
- Adding features → See "Quick Reference: Common Tasks"
- Debugging → See "Debugging Tips"
- Understanding data flow → See "Data Flow & Integration"
- Build issues → See "Build System" and "Resource Path Handling"

**Key mental model**: Router (idt_cli.py) → Scripts (business logic) → Providers (external APIs)

**Always check**:
1. Are you modifying the router or the script?
2. Does change require rebuild?
3. Does change affect both source and executable modes?
4. Are paths handled correctly for PyInstaller?

---

**End of Reference Document**

This document is maintained as project evolves. Last major update: October 11, 2025.
