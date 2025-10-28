# What's New in v3.5.0-beta

**Release Date:** TBD (In Development)  
**Previous Version:** v3.0.1  
**Status:** Beta - Testing and Validation Phase

---

## 🎯 Major New Features

### 1. **Video Metadata Embedding** ⭐ NEW
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

### 2. **Metadata Extraction & Geocoding** 🌍
**Complete metadata integration across the entire toolkit**

#### Core Functionality
- Extract GPS coordinates, dates, camera info from images (including HEIC/HEIF)
- Optional reverse geocoding via OpenStreetMap Nominatim
- Location and date prefixes added to descriptions
- Geocoding cache to minimize API calls

#### Integration Points
- **CLI**: `--metadata`, `--no-metadata`, `--geocode`, `--geocode-cache` flags
- **ImageDescriber GUI**: Enhanced metadata display panel
- **Viewer**: Metadata display in image viewer
- **IDTConfigure**: Metadata settings category
- **HTML Output**: Highlighted metadata sections
- **Guided Workflow**: Metadata configuration step

#### Documentation
- `docs/USER_GUIDE.md` - Section 9: Metadata Extraction & Geocoding
- `docs/CLI_REFERENCE.md` - Metadata options
- OpenStreetMap attribution for compliance

### 3. **IDTConfigure Application** ⚙️
**New GUI application for configuration management**

- Centralized configuration editor
- Visual management of workflow settings
- Metadata settings category
- Integrated into build/release pipeline
- Included in installer

### 4. **Interactive Image Gallery** 🖼️
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

### 5. **Automated Testing Infrastructure** 🧪
**Professional testing setup with pytest**

- pytest configuration
- Automated test runner
- GitHub Actions CI/CD integration
- 39/39 unit tests passing
- Test coverage reporting

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

1. **Format String Vulnerabilities**
   - Fixed format string errors in multiple components
   - Metadata config loading corrected
   - Frozen mode path handling fixed

2. **HTML Rendering in Viewer**
   - CRITICAL: Disabled HTML rendering in description pane (security)
   - Prevents XSS vulnerabilities

3. **Geocoding Race Condition**
   - Fixed race condition in geocoding logic
   - Format string vulnerabilities addressed

4. **EXIF GPS Conversion**
   - Fixed GPS conversion to handle rational tuples (num/den)
   - Proper handling of EXIF coordinate format

5. **Stats Analysis for Resumed Workflows**
   - Fixed to count actual descriptions, not total images
   - Accurate statistics for interrupted/resumed workflows

6. **Status.log Monitoring**
   - Fixed to prioritize --log-dir over --output-dir
   - Correct log file location resolution

7. **Image Gallery Issues**
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
- PyInstaller spec file updated for new modules (video metadata, exif embedder)
- All 5 apps now have dedicated build/package scripts
- Virtual environment setup automated
- `builditall.bat`: Builds all applications
- `packageitall.bat`: Packages all applications
- `releaseitall.bat`: Complete release pipeline (fixed syntax error)
- `build_installer.bat`: Windows installer creation

### Requirements
- Added `piexif>=1.1.3` for EXIF writing
- Updated to support Python 3.13+
- Separate requirements files for different Python versions
- Enhanced ONNX provider with YOLO detection (ultralytics>=8.0.0)

### Testing
- pytest framework integrated
- Custom test runner for 39 unit tests
- GitHub Actions CI/CD
- Automated testing documentation

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
- [x] Unit tests: 39/39 passing
- [x] Build system: All 5 apps building successfully
- [x] Metadata extraction: Working with JPEG, PNG, HEIC
- [x] Geocoding: OpenStreetMap integration working
- [x] Image Gallery: All features functional

### 🔄 Pending Validation
- [ ] Video metadata embedding: Test with real videos containing GPS
- [ ] Frozen executable (idt.exe): Test all new features in exe mode
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
# Process images with metadata and geocoding
idt workflow --input-dir photos --metadata --geocode

# Use custom geocode cache
idt workflow --input-dir photos --metadata --geocode-cache my_cache.json
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

### Feedback Welcome
This is a **beta release** - we're actively seeking feedback on:
- Video metadata embedding workflow
- Geocoding accuracy and performance
- UI/UX improvements
- Documentation clarity
- Bug reports

---

## 📚 Documentation

### New Documentation
- `docs/VIDEO_METADATA_EMBEDDING.md` - Video metadata complete guide
- `docs/TESTING.md` - Testing infrastructure
- `BuildAndRelease/README.md` - Build documentation
- `tools/show_metadata/README.md` - Metadata tool guide
- `tools/ImageGallery/README.md` - Gallery documentation

### Updated Documentation
- `docs/USER_GUIDE.md` - Added metadata section
- `docs/CLI_REFERENCE.md` - Updated with new flags
- `README.md` - Updated feature list

### Testing Documentation
- `docs/archive/TESTING_CHECKLIST_OCT27_2025.md`
- `docs/archive/guideme_testing.md`

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
All existing workflows continue to work. New features are opt-in via flags or automatic (video metadata).

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
1. Complete pending validation tests
2. Update CHANGELOG.md with final release notes
3. Create GitHub release v3.5.0-beta
4. Upload distribution packages
5. Announce new features

---

*This document will be updated as testing progresses toward the stable v3.5.0 release.*
