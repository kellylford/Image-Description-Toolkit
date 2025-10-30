# What's New in v3.5.0-beta

**Release Date:** TBD (In Development)  
**Previous Version:** v3.0.1  
**Status:** Beta - Testing and Validation Phase

---

## 🎯 Major New Features

### 1. **Build Versioning & Validation System** 🏗️ NEW
**Professional build numbering and automated validation**

#### Versioning System
- **Build-numbered versions**: `3.5.0-beta bld001`, `3.5.0-beta bld002`, etc.
- **Multiple sources**: Environment variables, GitHub Actions CI, or local tracker
- **Workflow logs**: Standardized banner with version, commit, mode, and UTC timestamp
- **CLI version command**: Shows full version + commit + frozen/dev mode
- **Unit tested**: Comprehensive tests for all versioning components

#### Build Validation
- **Pre-build check**: `check_spec_completeness.py` verifies all scripts are in PyInstaller spec
- **Post-build validation**: `validate_build.py` smoke tests the frozen executable
  - Tests version command, help, workflow imports, and core commands
  - Catches frozen build issues before deployment
- **Integration tests**: Tests specifically for frozen executable functionality
- **Automated in builditall.bat**: Validation runs automatically during every build

**Files:** `scripts/versioning.py`, `BuildAndRelease/validate_build.py`, `BuildAndRelease/check_spec_completeness.py`, `pytest_tests/integration/test_frozen_executable.py`

### 2. **Metadata Extraction & Geocoding** 🌍
**Complete metadata integration across the entire toolkit**

#### Core Functionality
- Extract GPS coordinates, dates, camera info from images (including HEIC/HEIF)
- **Reverse geocoding via OpenStreetMap Nominatim** (enabled by default)
- Location and date prefixes added to descriptions
- Geocoding cache to minimize API calls
- **Default behavior**: Metadata and geocoding are ON unless explicitly disabled

#### Integration Points
- **CLI**: `--no-metadata`, `--no-geocode` flags (both default to ON)
- **ImageDescriber GUI**: Enhanced metadata display panel
- **Viewer**: Metadata display in image viewer
- **IDTConfigure**: Metadata settings category
- **HTML Output**: Highlighted metadata sections
- **Guided Workflow**: Metadata configuration step

#### Documentation
- `docs/USER_GUIDE.md` - Section 9: Metadata Extraction & Geocoding
- `docs/CLI_REFERENCE.md` - Metadata options
- OpenStreetMap attribution for compliance

### 3. **Video Metadata Embedding** ⭐
**Extracted video frames now preserve GPS, date, and camera metadata from source videos**

- **video_metadata_extractor.py**: Extracts GPS coordinates, recording date/time, and camera info from video files using ffprobe
- **exif_embedder.py**: Converts video metadata to standard EXIF format and embeds in extracted frame JPEGs
- **Seamless Integration**: Works automatically with existing `--metadata` and `--geocode` flags
- **Standards-Based**: Uses standard EXIF tags for maximum compatibility
- **Graceful Degradation**: Works without ffprobe, just doesn't embed metadata
- **Frame Timestamps**: Each frame gets accurate timestamp based on position in video

**Requirements:**
- `piexif>=1.1.3` (included in requirements.txt)
- `ffprobe` (optional, part of ffmpeg)

**Impact:** Video frames are now "first-class citizens" with full metadata support, enabling location/date prefixes in descriptions just like regular photos.

**Documentation:** `docs/VIDEO_METADATA_EMBEDDING.md`

### 4. **IDTConfigure Application** ⚙️
**New GUI application for configuration management**

- Centralized configuration editor
- Visual management of workflow settings
- Metadata settings category
- Integrated into build/release pipeline
- Included in installer

### 5. **Interactive Image Gallery** 🖼️
**Advanced HTML gallery for comparing AI model outputs**

- Side-by-side model comparison
- Provider-based organization
- Collapsible prompt text display
- Description explorer mode
- Model navigation
- Cache-busting for reliable updates
- Automated data collection scripts
- Screen reader accessible

**Location:** `tools/ImageGallery/`

### 6. **Automated Testing Infrastructure** 🧪
**Professional testing setup with pytest**

- pytest configuration
- Automated test runner (Python 3.13+ compatible)
- GitHub Actions CI/CD integration
- **55 unit tests passing** (increased from 39)
- **48 smoke tests** for CLI/GUI entry points
- Integration tests for frozen executable
- Test coverage reporting
- Comprehensive local test suite with clear pass/fail reporting

---

## 🔧 Improvements & Enhancements

### Monitoring & Progress Tracking

#### Real-Time Status Monitoring
- **monitor_status.bat**: Real-time workflow status monitoring tool
- **10-second intervals**: Consistent across all monitors
- **ASCII symbols**: [ACTIVE]/[DONE]/[FAILED] for screen reader compatibility
- **Network path support**: Works with UNC paths
- **Console title updates**: Progress visible in taskbar

#### Conversion Progress
- Percentage and status display in console
- `logs/status.log` for monitoring
- `convert_images_progress.txt` writer/reader
- User Guide documentation with CMD monitoring examples

### Interactive Features

#### Guideme Wizard Enhancements
- Interactive setup for show_metadata tool with geocoding
- Workflow flag pass-through (passes user flags to underlying workflow command)
- Metadata configuration step in guided workflow
- Testing documentation for guideme functionality

### Build & Release Infrastructure

#### Reorganization
- All build/release scripts moved to `BuildAndRelease/` directory
- Comprehensive README in BuildAndRelease
- Release branch strategy documentation
- Fixed releaseitall.bat syntax error (was causing "unexpected" errors)

#### Environment Setup
- `tools/environmentsetup.bat`: Creates virtual environments for all 5 apps
- Automated dependency installation
- Validation and status reporting

### Documentation

#### New Documentation
- `docs/VIDEO_METADATA_EMBEDDING.md`: Complete video metadata guide
- `docs/TESTING.md`: Testing infrastructure and procedures
- `BuildAndRelease/README.md`: Build process documentation
- Gallery identification system docs
- Workflow performance analysis (Oct 21, 2025)

#### Updated Documentation
- USER_GUIDE.md: Metadata section, monitoring examples
- CLI_REFERENCE.md: Metadata flags, updated options
- Testing checklists: OCT27_2025, guideme testing
- Session summaries: 2025-10-26, 2025-10-27

#### Archived Documentation
- Moved outdated docs to archive
- Removed obsolete performance issue files
- Cleaned up installer guides

### Tool Improvements

#### show_metadata Tool
- Graduated to `tools/show_metadata/` with full structure
- Geocoding support
- CSV export functionality
- README and dedicated requirements.txt
- Interactive guideme wizard
- Fixed GPS IFD handling for HEIC files

#### Gallery Content Identification
- `tools/identify_gallery_content.py`: Content analysis tool
- IDW workspace creation integration
- Unit tests
- Examples and documentation
- CSV data export for 25-image test set

#### Workflow Utilities
- `tools/geotag_workflow.py`: Retroactive geotagging (created but not primary solution)
- `tools/rename_workflows_with_paths.py`: Workflow organization
- `tools/analyze_workflow_naming.py`: Workflow analysis

---

## 🐛 Bug Fixes

### Critical Fixes

1. **Build Validation System Issues**
   - Fixed Unicode encoding errors in validate_build.py (UTF-8 with error replacement)
   - Fixed CMD batch file IF/ELSE parsing error causing `. was unexpected` errors
   - Split IF/ELSE into separate IF statements for CMD compatibility

2. **Geocoding Now Enabled by Default**
   - Changed `enable_geocoding` default from False to True
   - Changed CLI flag from `--geocode` to `--no-geocode` (inverse logic)
   - Matches user expectations: geocoding ON unless explicitly disabled

3. **EXIF Metadata Loss During Image Optimization**
   - Fixed EXIF data preservation during image conversion/optimization
   - GPS and other metadata now correctly preserved through image processing

4. **Workflow Export Enhancements**
   - Added location and source tracking to workflow exports
   - Better metadata integration in CSV/Excel exports

5. **Format String Vulnerabilities**
   - Fixed format string errors in multiple components
   - Metadata config loading corrected
   - Frozen mode path handling fixed

6. **HTML Rendering in Viewer**
   - CRITICAL: Disabled HTML rendering in description pane (security)
   - Prevents XSS vulnerabilities

7. **Geocoding Race Condition**
   - Fixed race condition in geocoding logic
   - Format string vulnerabilities addressed

8. **EXIF GPS Conversion**
   - Fixed GPS conversion to handle rational tuples (num/den)
   - Proper handling of EXIF coordinate format

9. **Stats Analysis for Resumed Workflows**
   - Fixed to count actual descriptions, not total images
   - Accurate statistics for interrupted/resumed workflows

10. **Status.log Monitoring**
    - Fixed to prioritize --log-dir over --output-dir
    - Correct log file location resolution

11. **Image Gallery Issues**
   - Fixed prompt text display in Same Prompt mode
   - Fixed description explorer display
   - Fixed JSON loading (index.json vs individual files)
   - Model name extraction uses actual names from descriptions
   - Cache-busting for reliable updates
   - Screen reader accessibility improvements

### Other Fixes

- Fixed batch files to use correct executable path (`c:\idt\idt.exe`)
- Fixed variable scope error with sys module in guided_workflow
- Removed variable shadowing bug in timeout handling
- Fixed workflow pattern option (--pattern → --name)
- Fixed generate_descriptions.py parsing issues
- Normalized Ollama model names (treat 'model' and 'model:latest' as same)
- Fixed sanitize_name behavior (preserve case, remove spaces/punctuation, keep _ and -)
- Fixed path references to final_working.spec in build script

---

## 🏗️ Infrastructure Changes

### Build System
- **Versioning**: Build-numbered versions with tracking (scripts/versioning.py)
- **Validation**: Pre-build spec checks and post-build smoke tests
- PyInstaller spec file updated for new modules (video metadata, exif embedder, versioning)
- All 5 apps now have dedicated build/package scripts
- Virtual environment setup automated
- `builditall.bat`: Builds all applications with validation
- `packageitall.bat`: Packages all applications
- `releaseitall.bat`: Complete release pipeline (fixed IF/ELSE syntax)
- `build_installer.bat`: Windows installer creation

### Requirements
- Added `piexif>=1.1.3` for EXIF writing
- Updated to support Python 3.13+
- Separate requirements files for different Python versions
- Enhanced ONNX provider with YOLO detection (ultralytics>=8.0.0)

### Testing
- pytest framework integrated
- Custom test runner for 55 unit tests + 48 smoke tests
- GitHub Actions CI/CD
- Automated testing documentation
- Integration tests for frozen executables

---

## 📦 Distribution Changes

### Installer Updates
- IDTConfigure now included in installer
- `install_idt.bat` updated
- All 5 apps properly integrated

### Release Structure
- Master package (`idt_v{VERSION}.zip`) contains all individual packages
- Individual packages available separately
- Improved README files in releases

---

## 🎨 User Experience Improvements

### Accessibility
- ASCII symbols replace Unicode for screen reader compatibility
- Enhanced ARIA labels in Image Gallery
- Screen reader-friendly status updates
- Improved keyboard navigation

### UI/UX Enhancements
- Console title updates show progress
- Real-time status monitoring
- Improved error messages
- Better progress feedback
- Clean, organized output

### Workflow Improvements
- Interactive guideme wizard
- Automated gallery data collection
- Batch processing without interactive prompts (--batch flag)
- Better handling of resumed workflows

---

## 📊 Validation & Testing Status

### ✅ Completed Testing
- [x] Unit tests: 55/55 passing
- [x] Smoke tests: 48/48 CLI/GUI entry points passing
- [x] Integration tests: Frozen executable tests passing
- [x] Build system: All 5 apps building successfully with validation
- [x] Metadata extraction: Working with JPEG, PNG, HEIC
- [x] Geocoding: OpenStreetMap integration working, enabled by default
- [x] Versioning: Build numbers and banners appearing in logs and CLI
- [x] Image Gallery: All features functional
- [x] EXIF preservation: Metadata preserved through image optimization

### 🔄 Pending Validation
- [ ] Video metadata embedding: Test with real videos containing GPS
- [ ] Geocoding cache: Validate cache persistence and performance
- [ ] Installer: Test Windows installer with all 5 apps
- [ ] Documentation: Verify all examples and screenshots current
- [ ] Performance: Large workflow testing (1000+ images)
- [ ] Cross-platform: Test on different Windows versions

### ⚠️ Known Issues
- None currently documented (beta release)

---

## 💡 Usage Examples

### Video Metadata Embedding
```bash
# Extract frames from phone video (with GPS)
python scripts/video_frame_extractor.py

# Process frames with metadata
idt workflow --input-dir extracted_frames --metadata --geocode
```

### Metadata & Geocoding
```bash
# Process images with metadata and geocoding (both enabled by default)
idt workflow --input-dir photos

# Disable metadata
idt workflow --input-dir photos --no-metadata

# Disable just geocoding (keep metadata)
idt workflow --input-dir photos --no-geocode

# Use custom geocode cache
idt workflow --input-dir photos --geocode-cache my_cache.json
```

### Build Version Information
```bash
# Check build version
idt version
# Output: Image Description Toolkit 3.5.0-beta bld001
#         Commit: abc1234
#         Mode: Frozen

# Workflow logs now start with version banner automatically
idt workflow --input-dir photos
# Log shows: Build version, commit, mode, and timestamp
```

### Monitoring Workflow
```cmd
REM Terminal 1: Run workflow
idt workflow --input-dir large_folder

REM Terminal 2: Monitor in real-time
tools\monitor_status.bat C:\path\to\workflow\logs\status.log
```

### Interactive Setup
```bash
# Run guided workflow with metadata
python scripts/guideme.py workflow

# Setup show_metadata with wizard
python tools/show_metadata/show_metadata.py --guideme
```

---

## 🔜 Future Considerations

### Potential Enhancements
- Additional video metadata formats support
- More geocoding providers (Google Maps, MapBox)
- Enhanced HEIC metadata extraction
- Performance optimizations for large datasets
- Additional AI providers integration
- Web image download from URLs (partially implemented)

### Feedback Welcome
This is a **beta release** - we're actively seeking feedback on:
- Build versioning and validation system
- Video metadata embedding workflow
- Geocoding accuracy and performance (now enabled by default)
- UI/UX improvements
- Documentation clarity
- Bug reports

---

## 📚 Documentation

### New Documentation
- `docs/VIDEO_METADATA_EMBEDDING.md` - Video metadata complete guide
- `docs/TESTING.md` - Testing infrastructure
- `BuildAndRelease/README.md` - Build documentation including versioning system
- `tools/show_metadata/README.md` - Metadata tool guide
- `tools/ImageGallery/README.md` - Gallery documentation
- Session summaries: 2025-10-26, 2025-10-27, 2025-10-29

### Updated Documentation
- `docs/USER_GUIDE.md` - Added metadata section
- `docs/CLI_REFERENCE.md` - Updated with new flags (--no-geocode, --no-metadata)
- `README.md` - Updated feature list
- Testing checklists: OCT27_2025, guideme testing

### Testing Documentation
- `docs/archive/TESTING_CHECKLIST_OCT27_2025.md`
- `docs/archive/guideme_testing.md`
- `pytest_tests/integration/test_frozen_executable.py` - Frozen build validation
- `pytest_tests/unit/test_versioning.py` - Versioning system tests

---

## 🙏 Credits

Special thanks to:
- OpenStreetMap contributors for geocoding data
- ffmpeg project for video metadata extraction
- pillow-heif developers for HEIC support
- pytest community for testing framework

---

## 📋 Migration Notes

### From v3.0.1 to v3.5.0-beta

#### New Dependencies
```bash
pip install piexif>=1.1.3
```

#### Optional: Install ffprobe for video metadata
```bash
# Windows
# Download from https://ffmpeg.org/download.html

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

#### No Breaking Changes
All existing workflows continue to work. New features are opt-in via flags or automatic.

**Key behavior changes:**
- Metadata extraction is now ON by default (use `--no-metadata` to disable)
- Geocoding is now ON by default (use `--no-geocode` to disable)
- Version command now shows build number and commit info

#### Configuration Changes
- New metadata settings in IDTConfigure
- Geocoding cache location configurable
- No migration of existing configs required

---

## 📞 Support

- **Issues**: Report bugs on GitHub Issues
- **Documentation**: Check `docs/` directory
- **Examples**: See `tools/` and `tests/` directories

---

**Next Steps for Release:**
1. ✅ Complete build validation system
2. ✅ Add versioning with build numbers
3. ✅ Enable geocoding by default
4. ✅ Fix EXIF metadata preservation
5. Complete pending validation tests (video metadata, large workflows)
6. Update CHANGELOG.md with final release notes
7. Create GitHub release v3.5.0-beta
8. Upload distribution packages
9. External user beta testing
10. Announce new features

---

*Last Updated: October 29, 2025*  
*Document Status: Ready for external beta testing*
