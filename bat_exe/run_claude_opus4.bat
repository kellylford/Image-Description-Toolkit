@echo off
SETLOCAL
REM Run workflow with Claude Opus 4 (very high intelligence)
REM Usage: run_claude_opus4.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_claude_opus4.bat --prompt-style colorful test_images
REM   run_claude_opus4.bat test_images --dry-run
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."

idt.exe workflow --provider claude --model claude-opus-4-20250514 --output-dir Descriptions %*
ENDLOCAL
