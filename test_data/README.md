# Test Data for IDT Comprehensive Testing

This directory contains the standardized test dataset for comprehensive testing of the Image Description Toolkit.

## Test Files (5 total)

### 1. video_12sec.mp4
- **Purpose**: Test video frame extraction
- **Duration**: Exactly 12 seconds
- **Expected**: Multiple frames extracted and described

### 2. photo.heic  
- **Purpose**: Test HEIC to JPG conversion pipeline
- **Format**: iPhone/modern camera HEIC format
- **Expected**: Converted to JPG and described

### 3. image.jpg
- **Purpose**: Test standard JPG description pipeline  
- **Format**: Standard JPEG
- **Expected**: Direct description without conversion

### 4. nested/nested_image1.jpg
- **Purpose**: Test directory traversal (1 of 2)
- **Location**: Subdirectory
- **Expected**: Processed with directory structure preserved

### 5. nested/nested_image2.png
- **Purpose**: Test directory traversal (2 of 2)  
- **Location**: Subdirectory
- **Expected**: Processed with directory structure preserved

## Usage

Use this directory as the input for `allmodeltest.bat`:

```bash
allmodeltest.bat test_data --batch --name comprehensive_test
```

## Validation

After processing, verify these outputs exist:
- Descriptions for all 5 files
- Converted JPG from HEIC file
- Video frames extracted
- Nested directory structure preserved
- Complete HTML reports generated

## File Requirements

**NOTE**: The actual test files need to be provided. This README documents the expected structure.

For optimal testing:
- Video should have some visual variety (different scenes)
- HEIC should be a real iPhone/camera photo
- JPG should be a clear, describable image
- Nested images should be different enough to validate distinct descriptions

## Created

October 17, 2025 - Part of comprehensive testing automation initiative