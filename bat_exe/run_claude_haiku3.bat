@echo off
SETLOCAL
REM Run workflow with Claude Haiku 3 (fast and compact)
REM Usage: run_claude_haiku3.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_claude_haiku3.bat --prompt-style colorful test_images
REM   run_claude_haiku3.bat test_images --steps describe --dry-run
REM   run_claude_haiku3.bat --dry-run --prompt-style narrative test_images
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."

idt.exe workflow --provider claude --model claude-3-haiku-20240307 --output-dir Descriptions %*
ENDLOCAL
