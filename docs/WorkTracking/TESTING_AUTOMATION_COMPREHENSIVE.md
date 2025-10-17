# Comprehensive Testing Automation System

## Overview

Create a comprehensive automated testing system that can build, install, and test the complete Image Description Toolkit pipeline from scratch. This system needs to work both as GitHub Actions (for CI/CD) and as a local testing script for clean machine validation.

## Objectives

### Primary Goals
1. **Full Build Coverage** - Build all four applications (IDT, Viewer, Prompt Editor, ImageDescriber)
2. **End-to-End Installation** - Install outside Python ecosystem as standalone executables
3. **Complete Workflow Testing** - Test all major workflow components with real data
4. **Validation Coverage** - Verify all expected outputs are created correctly

### Fallback Goal
If GitHub Actions prove too complex, create a local automation script that can be run on a clean machine with minimal setup.

## Requirements

### Build Phase
- [ ] Build all four applications using `builditall.bat` / `releaseitall.bat`
- [ ] Verify executables are created and functional
- [ ] Package applications into distribution ZIPs
- [ ] Create master `idt2.zip` package

### Environment Setup
- [ ] Install Ollama automatically
- [ ] Pull required vision models:
  - [ ] `moondream` (fast, lightweight)
  - [ ] `gemma3` (medium quality)
- [ ] Verify models are available and functional

### Test Data Setup
Create comprehensive test dataset with **exactly 5 test files**:

#### Required Test Files
1. **Video File** (1 file)
   - [ ] Duration: exactly 12 seconds
   - [ ] Format: MP4 or MOV
   - [ ] Should generate multiple frames for description

2. **HEIC File** (1 file)
   - [ ] iPhone/modern camera format
   - [ ] Tests conversion pipeline (HEIC → JPG)

3. **JPG File** (1 file)
   - [ ] Standard JPEG format
   - [ ] Tests direct description pipeline

4. **Nested Directory Images** (2 files)
   - [ ] Two images inside a subdirectory
   - [ ] Tests directory traversal and structure preservation
   - [ ] Could be JPG, PNG, or other supported formats

#### Test Data Structure
```
test_data/
├── video_12sec.mp4              # 12-second video
├── photo.heic                   # HEIC conversion test
├── image.jpg                    # Standard JPG test
└── nested/
    ├── nested_image1.jpg        # Subdirectory test 1
    └── nested_image2.png        # Subdirectory test 2
```

### Automated Testing Phase
- [ ] Run `allmodeltest.bat` with test data directory
- [ ] Test with both installed models (moondream, gemma3)
- [ ] Use `--batch` mode for non-interactive execution
- [ ] Monitor for successful completion

### Validation Phase

#### Core Output Validation
- [ ] **Descriptions Generated**: Verify description files exist for all 5 test files
- [ ] **Conversion Success**: HEIC file converted to JPG
- [ ] **Video Frame Extraction**: Video processed into individual frames
- [ ] **Directory Structure**: Nested images processed correctly
- [ ] **HTML Reports**: Complete HTML outputs generated

#### Advanced Validation
- [ ] **CombineDescriptions**: Run and verify combined output
- [ ] **Stats Analysis**: Generate and validate statistics
- [ ] **File Integrity**: All expected workflow files present
- [ ] **Log Analysis**: No critical errors in logs

#### Expected File Structure Validation
For each model run, verify this structure exists:
```
Descriptions/wf_[name]_[model]_[style]_[timestamp]/
├── images/                      # Processed images
├── extracted_frames/            # Video frames (if video present)
├── converted/                   # HEIC conversions (if HEIC present)
├── image_descriptions.txt       # Raw descriptions
├── index.html                   # HTML report
├── logs/                        # Execution logs
│   ├── status.log
│   └── image_describer_progress.txt
└── view_results.bat            # Viewer launcher
```

## Implementation Options

### Option A: GitHub Actions (Preferred)
- **Runner**: `windows-latest` (for Windows executable testing)
- **Environment**: Set up Python, Ollama, test data
- **Execution**: Run complete pipeline
- **Artifacts**: Upload test results and logs
- **Reporting**: Generate test report with pass/fail status

### Option B: Local Automation Script (Fallback)
- **Script**: `test_automation.bat` for Windows
- **Requirements**: Only Git and basic Windows tools
- **Setup**: Automated Python, Ollama installation
- **Execution**: Complete pipeline including validation
- **Output**: Local test report with detailed results

## Success Criteria

### Build Success
- [ ] All four executables built without errors
- [ ] Distribution packages created
- [ ] Master `idt2.zip` contains all packages

### Installation Success
- [ ] Ollama installed and running
- [ ] Required models downloaded and available
- [ ] Executables run without missing dependencies

### Workflow Success
- [ ] All 5 test files processed successfully
- [ ] Both models (moondream, gemma3) complete without errors
- [ ] No critical errors in logs
- [ ] Expected processing times reasonable (< 30 minutes total)

### Validation Success
- [ ] All expected files and directories created
- [ ] Descriptions contain reasonable content (not empty/error messages)
- [ ] HTML reports open and display correctly
- [ ] CombineDescriptions produces valid output
- [ ] Stats analysis completes successfully

## Deliverables

### Phase 1: Infrastructure
- [ ] Test data creation (5 files as specified)
- [ ] GitHub Actions workflow OR local automation script
- [ ] Validation scripts for output verification

### Phase 2: Implementation
- [ ] Complete build → install → test pipeline
- [ ] Automated Ollama and model setup
- [ ] Error handling and reporting

### Phase 3: Validation
- [ ] Comprehensive output checking
- [ ] Test report generation
- [ ] Documentation for running tests

## Timeline

- **Week 1**: Infrastructure setup, test data creation
- **Week 2**: Build and installation automation
- **Week 3**: Workflow testing and validation
- **Week 4**: Refinement and documentation

## Priority

**HIGH PRIORITY** - This is essential for:
- Ensuring releases work on clean machines
- Catching regressions before they reach users
- Validating the complete pipeline end-to-end
- Building confidence in the automation systems

## Technical Notes

### Challenges to Address
1. **Ollama Installation**: Automated installation and service startup
2. **Model Downloads**: Large files (GB), need good progress indication
3. **Path Handling**: Windows path issues with spaces and special characters
4. **Timeout Handling**: Long-running operations need proper timeouts
5. **Error Recovery**: Graceful handling of partial failures

### Resources Required
- **GitHub Actions**: Windows runner time (potentially 30-60 minutes per run)
- **Storage**: Test data files (~100MB), model downloads (~5GB)
- **Network**: Model downloads from Ollama registry

## Success Metrics

1. **Reliability**: 95% success rate on clean runs
2. **Speed**: Complete pipeline in < 60 minutes
3. **Coverage**: All major workflow components tested
4. **Maintainability**: Easy to update test data and validation criteria

---

**Created**: October 17, 2025  
**Assignee**: TBD (Copilot or manual implementation)  
**Labels**: `enhancement`, `testing`, `automation`, `high-priority`