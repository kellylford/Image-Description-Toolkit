@echo off
SETLOCAL
REM Run workflow with Claude Sonnet 3.7 (extended thinking)
REM Usage: run_claude_sonnet37.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_claude_sonnet37.bat --prompt-style colorful test_images
REM   run_claude_sonnet37.bat test_images --dry-run
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."

idt.exe workflow --provider claude --model claude-3-7-sonnet-20250219 --output-dir Descriptions %*
ENDLOCAL
