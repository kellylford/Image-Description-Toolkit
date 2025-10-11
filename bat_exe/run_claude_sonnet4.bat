@echo off
SETLOCAL

REM Capture the original working directory before changing directories
SET ORIGINAL_CWD=%CD%
REM Run workflow with Claude Sonnet 4 (high performance)
REM Usage: run_claude_sonnet4.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_claude_sonnet4.bat --prompt-style colorful test_images
REM   run_claude_sonnet4.bat test_images --dry-run
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
dist\idt.exe workflow --provider claude --model claude-sonnet-4-20250514 --output-dir ../Descriptions --original-cwd "%ORIGINAL_CWD%" %*
ENDLOCAL
