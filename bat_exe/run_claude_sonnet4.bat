@echo off
SETLOCAL
REM Run workflow with Claude Sonnet 4 (high performance)
REM Usage: run_claude_sonnet4.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_claude_sonnet4.bat --prompt-style colorful test_images
REM   run_claude_sonnet4.bat test_images --dry-run
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

..\idt.exe workflow --provider claude --model claude-sonnet-4-20250514 --output-dir ..\Descriptions %*
ENDLOCAL
