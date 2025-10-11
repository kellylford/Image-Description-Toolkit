# Testing and Debugging Scripts

This directory contains test files and debugging scripts used during development and troubleshooting.

## Batch File Debugging Scripts

These scripts were created to fix batch file issues during the external build testing phase:

- `check_bat_syntax.py` - Comprehensive syntax checker for all batch files
- `fix_all_bat_files.py` - Script to add --original-cwd support to workflow batch files
- `fix_bat_files.py` - Earlier version of batch file fixer
- `fix_bat_output_dirs.py` - Script to correct output directory paths
- `fix_external_bat_cwd.py` - External build specific batch file fixes
- `fix_external_bat_files.py` - Additional external build fixes

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