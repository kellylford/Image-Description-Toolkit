# Testing and Debugging Scripts

This directory contains test files and debugging scripts used during development and troubleshooting.

## Subdirectories

### ModelPerformanceAnalyzer/

Comprehensive analysis tool for comparing AI vision model performance. Combines workflow execution data with generated descriptions to provide insights on speed, cost, and quality trade-offs. See `ModelPerformanceAnalyzer/README.md` for details.

### old_dev_scripts/

Historical batch file debugging scripts from development phase. Archived for reference but no longer actively used.

## Test Scripts

- `test_build.py` - Python build testing script
- `test_build.bat` - Batch file for build testing
- `test_cli_functionality.py` - CLI functionality testing
- `test_deployment.py` - Deployment testing script
- `test_deployment.bat` - Batch file for deployment testing
- `test_executable.py` - Executable testing script

## Configuration Files

- `test_config.json` - Configuration for testing
- `test_deployment_config.json` - Deployment test configuration

## Usage Notes

These scripts were primarily used to resolve issues with:
- Relative path resolution in batch files when using external builds
- Output directory path corrections
- Syntax errors in batch files
- Distribution process fixes

Most of these scripts were run once to fix issues and may not be needed for regular operation, but are preserved for reference and future debugging.