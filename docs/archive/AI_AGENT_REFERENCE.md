# Image Description Toolkit - AI Agent Technical Reference

**Purpose**: Onboard AI agents to the IDT project quickly with essential technical context.  
**Last Updated**: October 12, 2025  
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
| `prompt-list` | `scripts/list_prompts.py` | List available prompt styles |
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

### Overview: Four Separate Distributions

**IDT Distribution Strategy**:
1. **Main CLI** (`idt.exe`) - Core toolkit with all AI providers
2. **Viewer** (`viewer.exe`) - Standalone workflow browser
3. **Prompt Editor** (`prompt_editor.exe`) - Standalone prompt manager
4. **ImageDescriber** (`ImageDescriber.exe`) - Standalone GUI image processor

**Why Separate?**: Size optimization, dependency isolation, modular installation

**Distribution Packages** (all in `releases/`):
- `ImageDescriptionToolkit_v[VERSION].zip` - Main CLI
- `viewer_v[VERSION]_arm64.zip` - Viewer app
- `prompt_editor_v[VERSION]_arm64.zip` - Prompt editor
- `imagedescriber_v[VERSION]_arm64.zip` - ImageDescriber app

---

### Main CLI Build System

#### PyInstaller Configuration: `final_working.spec`

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

#### Build Scripts

**Main CLI Build**: `build_idt.bat`
```batch
pyinstaller final_working.spec
# Creates: dist/idt.exe (~350MB)
```

**Package Main CLI**: `package_idt.bat`
```batch
# Creates: releases/ImageDescriptionToolkit_v[VERSION].zip
# Contains: idt.exe, USER_GUIDE.md, README.txt, LICENSE
```

---

### GUI Applications Build System

**Critical Design**: Each GUI app has:
- **Separate virtual environment** (`.venv/`) for dependency isolation
- **Own build script** (`build_*.bat`) 
- **Own packaging script** (`package_*.bat`)
- **Own requirements.txt** with standalone dependencies

#### Virtual Environment Strategy

**Location Structure**:
```
idt/
├── viewer/
│   ├── .venv/              # Separate venv for viewer
│   ├── requirements.txt    # PyQt6, Pillow, requests, ollama, pyinstaller
│   ├── build_viewer.bat
│   └── package_viewer.bat
│
├── prompt_editor/
│   ├── .venv/              # Separate venv for prompt editor
│   ├── requirements.txt    # PyQt6, AI providers, pyinstaller
│   ├── build_prompt_editor.bat
│   └── package_prompt_editor.bat
│
└── imagedescriber/
    ├── .venv/              # Separate venv for imagedescriber
    ├── requirements.txt    # PyQt6, image processing, AI providers, pyinstaller
    ├── build_imagedescriber.bat
    └── package_imagedescriber.bat
```

**Setup Process** (from `GUI_VENV_SETUP.md`):
```bash
# Viewer setup
cd viewer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Repeat for prompt_editor and imagedescriber
```

**Why Separate Venvs?**:
- **Dependency Isolation**: Each app has only what it needs
- **Build Reliability**: No dependency conflicts
- **Clean Testing**: Test each app in isolation
- **Size Optimization**: No extra packages bundled

**Trade-off**: ~750MB disk space vs clean separation (acceptable for development)

#### Viewer Build System

**Build Script**: `viewer/build_viewer.bat`
```batch
@echo off
echo Building Viewer application...

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Auto-detect architecture
set ARCH=arm64
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" set ARCH=amd64

REM Build with PyInstaller
pyinstaller --onefile ^
    --windowed ^
    --name viewer_%ARCH% ^
    --add-data "../scripts;scripts" ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    viewer.py

REM Deactivate
call deactivate

echo Build complete: dist/viewer_%ARCH%.exe
```

**Key Features**:
- Uses venv Python (no hardcoded paths)
- Auto-detects ARM64 vs AMD64
- Bundles scripts/ for redescription feature
- `--windowed` hides console window

**Package Script**: `viewer/package_viewer.bat`
```batch
@echo off
REM Reads VERSION file
REM Creates viewer_releases/viewer_v[VERSION]_arm64.zip
REM Contains: viewer.exe, README.txt, screenshots/
```

**Output**: `viewer/viewer_releases/viewer_v[VERSION]_arm64.zip`

#### Prompt Editor Build System

**Build Script**: `prompt_editor/build_prompt_editor.bat`
- Similar structure to viewer
- Output: `dist/prompt_editor_arm64.exe`

**Package Script**: `prompt_editor/package_prompt_editor.bat`
- Creates: `prompt_editor_releases/prompt_editor_v[VERSION]_arm64.zip`

**Requirements**: PyQt6, anthropic, openai, ollama, pyinstaller

#### ImageDescriber Build System

**Build Script**: `imagedescriber/build_imagedescriber.bat`
- Similar structure to viewer
- Output: `dist/ImageDescriber_arm64.exe`

**Package Script**: `imagedescriber/package_imagedescriber.bat`
- Creates: `imagedescriber_releases/imagedescriber_v[VERSION]_arm64.zip`
- Includes: Extensive documentation from `dist_templates/`

**Requirements**: PyQt6, Pillow, pillow-heif, opencv-python, numpy, AI providers, pyinstaller

---

### Master Build Automation

**Complete Build System** (October 2025):

#### `builditall.bat` - Build All Four Applications

**Purpose**: Build all executables in one command

**Process**:
1. Build main IDT (uses main venv)
2. Build viewer (activates viewer/.venv, builds, deactivates)
3. Build prompt_editor (activates prompt_editor/.venv, builds, deactivates)
4. Build imagedescriber (activates imagedescriber/.venv, builds, deactivates)

**Error Handling**: Tracks failures, continues building others, reports at end

**Time**: ~10-15 minutes total

**Usage**:
```batch
builditall.bat
# No user interaction required
```

#### `packageitall.bat` - Package All Distributions

**Purpose**: Create all distribution ZIPs and consolidate to `releases/`

**Process**:
1. Package main IDT → moves to `releases/ImageDescriptionToolkit_v[VERSION].zip`
2. Package viewer → moves to `releases/viewer_v[VERSION]_arm64.zip`
3. Package prompt_editor → moves to `releases/prompt_editor_v[VERSION]_arm64.zip`
4. Package imagedescriber → moves to `releases/imagedescriber_v[VERSION]_arm64.zip`

**Result**: All packages in single `releases/` directory

**Time**: ~2-3 minutes

**Usage**:
```batch
packageitall.bat
# No user interaction required
```

#### `releaseitall.bat` - Complete Build + Package Automation

**Purpose**: One-command complete release process

**Process**:
```
PHASE 1: BUILD ALL APPLICATIONS
├── Run builditall.bat
│   ├── Build IDT
│   ├── Build viewer
│   ├── Build prompt_editor
│   └── Build imagedescriber
│
PHASE 2: PACKAGE ALL APPLICATIONS
├── Run packageitall.bat
│   ├── Package all four apps
│   └── Move to releases/
│
RELEASE COMPLETE
└── Show summary and next steps
```

**Complete Automation**: Zero user interaction, no pause prompts

**Time**: ~12-18 minutes (unattended)

**Usage**:
```batch
releaseitall.bat
# Walk away, come back to all packages ready in releases/
```

**Exit Codes**: Propagates failures from build/package phases

---

### Architecture Handling

**Current Reality** (October 2025):
- **User Machines**: Surface (ARM64), Lenovo (ARM64)
- **Build Output**: ARM64 executables only
- **Windows Limitation**: PyInstaller cannot cross-compile on Windows

**Auto-Detection**:
```batch
set ARCH=arm64
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" set ARCH=amd64
```

**Naming Convention**: `<app>_arm64.exe` or `<app>_amd64.exe`

**Why `--target-architecture` Removed**:
- Flag only works on macOS
- Causes build failures on Windows
- PyInstaller on Windows builds for current Python's architecture only

**AMD64 Builds**: Would require:
- AMD64 Windows machine, OR
- GitHub Actions runner, OR
- Cross-platform build server

**Current Decision**: ARM64 only (both user machines are ARM64)

---

### Build Troubleshooting

#### Problem: "Hardcoded path not found"

**Historical Issue** (Fixed Oct 2025):
```batch
# OLD BROKEN:
set PYTHON=C:/Users/kelly/GitHub/Image-Description-Toolkit/.venv/Scripts/python.exe

# NEW FIXED:
# Use active venv's python (no hardcoded path)
```

**Solution**: All build scripts now use venv-activated Python

#### Problem: "Invalid flag --target-architecture"

**Root Cause**: macOS-only PyInstaller flag used on Windows

**Solution**: Removed from all build scripts. Architecture detection via `%PROCESSOR_ARCHITECTURE%`

#### Problem: "Module not found in executable"

**Check**:
1. Is module in venv's `requirements.txt`?
2. Is module in `--hidden-import` flags?
3. Did you rebuild after adding dependency?

#### Problem: GUI app won't start

**Check**:
1. Built with `--windowed` flag (hides console)?
2. PyQt6 hidden imports included?
3. Resources bundled with `--add-data`?

---

### Build Documentation

**Complete Guides**:
- `GUI_VENV_SETUP.md` - Virtual environment setup for all GUI apps
- `BUILD_AND_PACKAGE_GUIDE.md` - Master automation documentation
- `viewer/README.md` - Viewer-specific build instructions
- `prompt_editor/README.md` - Prompt editor build instructions
- `imagedescriber/README.md` - ImageDescriber build instructions

**Quick Reference**:
- First-time setup: Follow `GUI_VENV_SETUP.md`
- Complete release: Run `releaseitall.bat`
- Individual app: Navigate to app dir, run `build_*.bat`
- Packages only: Run `packageitall.bat`

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

**Decision**: Four separate distributions instead of one mega-package

**Rationale**:
- **Size**: CLI doesn't need PyQt6 (~200MB savings)
- **Dependencies**: GUIs don't need all AI SDKs, CLI doesn't need GUI frameworks
- **Use case**: Most users only need CLI + Viewer
- **Build time**: Faster incremental builds (5-7 min vs 15+ min)
- **Installation**: Users install only what they need

**Size Comparison**:
- All-in-one: ~600MB+ (everything bundled)
- Separate: IDT ~350MB, Viewer ~100MB, Prompt Editor ~120MB, ImageDescriber ~140MB
- User installs only what they need: Typical = IDT + Viewer = ~450MB vs 600MB+

### 3. Why Separate Virtual Environments for GUI Apps?

**Decision**: Each GUI app has own `.venv/` directory

**Rationale**:
- **Dependency Isolation**: No conflicts between app requirements
- **Build Reliability**: Clean, reproducible builds
- **Testing**: Test each app independently
- **Size Optimization**: Only bundle packages each app actually uses
- **Development**: Work on one app without breaking others

**Trade-off**: ~750MB disk space (3 venvs × ~250MB) vs main venv pollution

**When NOT to use**: If disk space is critical (< 5GB free) - then use main venv

### 4. Why 3.75MB Image Size Limit?

**Decision**: Target 3.75MB file size (not 4.5MB, not 5MB)

**Rationale**:
- Claude API limit: 5MB base64-encoded
- Base64 encoding: 4/3 size increase
- Math: 5MB / 1.33 = 3.75MB
- Safety margin: Accounts for metadata overhead

**Historical Context**: Originally used 4.5MB, but images still failed. Investigation revealed base64 encoding overhead was the culprit. Fixed Oct 11, 2025.

### 5. Why Text File + HTML Instead of Database?

**Decision**: Plain text file during processing, HTML for viewing

**Rationale**:
- Portability: No DB server needed
- Human-readable: Easy debugging
- Live monitoring: File watchers work simply
- Archival: HTML is self-contained
- Performance: Fast for typical workflows (100-1000 images)

### 6. Why Provider Abstraction?

**Decision**: Single `ImageDescriber` class, multiple provider implementations

**Rationale**:
- User flexibility: Switch providers without workflow changes
- Cost optimization: Use cheap/free Ollama for testing, Claude for production
- API stability: Abstract away provider differences
- Future-proof: Easy to add new providers

### 7. Why Complete Build Automation (releaseitall.bat)?

**Decision**: Zero user interaction during build process

**Rationale**:
- **Reliability**: No missed prompts, consistent process
- **Speed**: Can run unattended (overnight, during meetings)
- **CI/CD Ready**: Could integrate with GitHub Actions
- **Error Handling**: Proper exit codes, comprehensive error reporting
- **Documentation**: Repeatable process, easy to hand off

**Before** (Manual):
```
1. cd viewer
2. call build_viewer.bat
3. [Press any key]
4. call package_viewer.bat  
5. [Press any key]
6. cd ../prompt_editor
7. [Repeat for 3 more apps...]
8. Manually move ZIPs to releases/
~30 minutes, 20+ key presses
```

**After** (Automated):
```
1. releaseitall.bat
2. Walk away
~12-18 minutes, zero interaction
```

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
├── final_working.spec      # PyInstaller build config for main CLI
├── VERSION                 # Version number (e.g., "1.0.0")
│
├── build_idt.bat           # Build main CLI (idt.exe)
├── package_idt.bat         # Package main CLI → releases/
├── builditall.bat          # Build all 4 apps (CLI + 3 GUIs)
├── packageitall.bat        # Package all 4 apps → releases/
├── releaseitall.bat        # Build + package everything (complete automation)
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
├── imagedescriber/         # GUI app #1 (standalone)
│   ├── .venv/              # Separate virtual environment
│   ├── requirements.txt    # PyQt6, image libs, AI providers, pyinstaller
│   ├── imagedescriber.py   # Main application
│   ├── build_imagedescriber.bat      # Build executable
│   ├── package_imagedescriber.bat    # Create distribution ZIP
│   ├── dist/               # Build output (ImageDescriber_arm64.exe)
│   └── imagedescriber_releases/      # Packaged ZIPs
│
├── viewer/                 # GUI app #2 (standalone)
│   ├── .venv/              # Separate virtual environment
│   ├── requirements.txt    # PyQt6, Pillow, requests, ollama, pyinstaller
│   ├── viewer.py           # Main application
│   ├── build_viewer.bat    # Build executable
│   ├── package_viewer.bat  # Create distribution ZIP
│   ├── dist/               # Build output (viewer_arm64.exe)
│   ├── viewer_releases/    # Packaged ZIPs
│   └── README.md           # Build documentation
│
├── prompt_editor/          # GUI app #3 (standalone)
│   ├── .venv/              # Separate virtual environment
│   ├── requirements.txt    # PyQt6, AI providers, pyinstaller
│   ├── prompt_editor.py    # Main application
│   ├── build_prompt_editor.bat       # Build executable
│   ├── package_prompt_editor.bat     # Create distribution ZIP
│   ├── dist/               # Build output (prompt_editor_arm64.exe)
│   └── prompt_editor_releases/       # Packaged ZIPs
│
├── releases/               # Final distribution packages (consolidated)
│   ├── ImageDescriptionToolkit_v[VERSION].zip
│   ├── viewer_v[VERSION]_arm64.zip
│   ├── prompt_editor_v[VERSION]_arm64.zip
│   └── imagedescriber_v[VERSION]_arm64.zip
│
├── bat/                    # Helper batch scripts
│   ├── run_*.bat           # Quick-launch scripts for common tasks
│   └── setup_*_key.bat     # API key configuration
│
└── docs/                   # Documentation
    ├── archive/
    │   └── AI_AGENT_REFERENCE.md (this file)
    ├── BUILD_AND_PACKAGE_GUIDE.md    # Master automation docs
    ├── GUI_VENV_SETUP.md             # Virtual environment setup
    ├── QUICK_START.md
    └── WorkTracking/       # Development notes
```

**Key Directories**:
- `scripts/` - All business logic (used by CLI and bundled with executables)
- `models/` - AI prompts (loaded at runtime, bundled with all apps)
- `dist/` - PyInstaller output (gitignored)
- `build/` - PyInstaller cache (gitignored)
- `releases/` - Final distribution packages (uploaded to GitHub)
- `.venv/` - Virtual environments (gitignored, one per app)

---

## Quick Reference: Common Tasks

### Building and Releasing

#### Complete Release Process
```batch
# First time setup (once):
cd viewer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
deactivate

# Repeat for prompt_editor and imagedescriber

# Every release:
releaseitall.bat
# Wait 12-18 minutes, all packages appear in releases/
```

#### Build Individual App
```batch
# Viewer example:
cd viewer
call build_viewer.bat

# Builds to: viewer/dist/viewer_arm64.exe
```

#### Package Individual App
```batch
cd viewer
call package_viewer.bat

# Creates: viewer/viewer_releases/viewer_v[VERSION]_arm64.zip
```

#### Build All Apps (no packaging)
```batch
builditall.bat
# Builds all 4 executables in ~10-15 minutes
```

#### Package All Apps (assumes already built)
```batch
packageitall.bat
# Packages all 4 apps, consolidates to releases/
```

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

### Add Dependency to GUI App

**Example: Adding library to viewer**:
```batch
cd viewer
.venv\Scripts\activate
pip install new-library
pip freeze > requirements.txt
deactivate

# Rebuild:
call build_viewer.bat
```

**Important**: Add to `--hidden-import` if PyInstaller doesn't auto-detect

### Troubleshoot Build Failure

1. **Check logs**: Build output shows specific errors
2. **Verify venv**: Ensure venv activated before building
3. **Test in source**: Run `python <app>.py` to verify code works
4. **Check imports**: Missing `--hidden-import` flags?
5. **Check resources**: Missing `--add-data` entries?
6. **Clean build**: Delete `dist/` and `build/` directories, rebuild

---

## Version History Context

**Current Version**: 1.0.0 (preparing first release)

**Recent Major Changes** (October 2025):

**October 12, 2025 - Build System Overhaul**:
- Created separate virtual environments for all GUI apps (viewer, prompt_editor, imagedescriber)
- Fixed broken build scripts (removed hardcoded paths, invalid `--target-architecture` flags)
- Created packaging scripts for all apps
- Implemented master automation: `builditall.bat`, `packageitall.bat`, `releaseitall.bat`
- Removed all pause prompts (24+ across 8 scripts) for complete automation
- Consolidated all packages to `releases/` directory
- Created comprehensive build documentation (`GUI_VENV_SETUP.md`, `BUILD_AND_PACKAGE_GUIDE.md`)

**October 11, 2025 - Viewer and Image Processing**:
- Fixed image size optimization (3.75MB limit for base64 overhead)
- Added viewer CLI (--open, directory arg, --help)
- Integrated viewer launcher in main CLI
- Comprehensive documentation overhaul

**Key Milestones**:
- **Dependency Isolation**: Each GUI app has clean, separate venv
- **Build Reliability**: Removed hardcoded paths, all builds use venv Python
- **Complete Automation**: One command (`releaseitall.bat`) builds and packages everything
- **Distribution Ready**: Four separate packages, all consolidated to `releases/`

---

## For AI Agents: How to Use This Document

**When helping with**:
- Architecture questions → See "Architecture at a Glance"
- Build/release process → See "Build System" and "Master Build Automation"
- Adding features → See "Quick Reference: Common Tasks"
- Debugging builds → See "Build Troubleshooting"
- Understanding data flow → See "Data Flow & Integration"
- Build issues → See "Build System" and "Resource Path Handling"

**Key mental model**: Router (idt_cli.py) → Scripts (business logic) → Providers (external APIs)

**Always check**:
1. Are you modifying the router or the script?
2. Does change require rebuild?
3. Which app(s) are affected (CLI, viewer, prompt_editor, imagedescriber)?
4. Does change affect both source and executable modes?
5. Are paths handled correctly for PyInstaller?
6. If adding dependency to GUI app, which venv needs it?

**Build System Context**:
- **Four separate distributions**: IDT (CLI), viewer, prompt_editor, imagedescriber
- **Separate venvs**: Each GUI app has own `.venv/` directory
- **Master automation**: Use `releaseitall.bat` for complete build + package
- **No user interaction**: All pause statements removed, fully automated
- **Consolidated output**: All packages appear in `releases/` directory

**Common Pitfalls**:
1. **Hardcoded paths**: Never hardcode venv paths (use activated venv's python)
2. **Windows limitations**: No cross-compilation (can't build AMD64 on ARM64)
3. **Invalid flags**: `--target-architecture` only works on macOS, not Windows
4. **Missing imports**: GUI apps need `--hidden-import PyQt6.QtCore`, etc.
5. **Resource paths**: Always use `get_resource_path()` pattern for bundled files
6. **Main project isolation**: When fixing GUI apps, don't touch main `requirements.txt` or `build_idt.bat`

**Before making build changes**:
1. Identify which app(s) affected
2. Check if change requires venv update (`pip install`, update `requirements.txt`)
3. Test in source mode first (`python <app>.py`)
4. Rebuild affected app(s)
5. Test executable
6. Update documentation if adding new features

**Testing checklist after build changes**:
- [ ] App builds without errors
- [ ] Executable starts and shows UI (for GUI apps)
- [ ] Core functionality works
- [ ] Resources load correctly (images, configs, prompts)
- [ ] Size is reasonable (not bloated with extra dependencies)

---

**End of Reference Document**

This document is maintained as project evolves. Last major update: October 12, 2025 (Build System Overhaul).

**Major Update Summary (Oct 12, 2025)**:
- Added comprehensive build system documentation
- Documented virtual environment strategy for GUI apps
- Explained master automation scripts (builditall, packageitall, releaseitall)
- Added architecture handling and Windows limitations
- Expanded troubleshooting and common tasks sections
- Updated file structure to show build/release infrastructure
