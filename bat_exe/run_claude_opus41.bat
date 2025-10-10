@echo off
SETLOCAL
REM Run workflow with Claude Opus 4.1 (specialized complex tasks, superior reasoning)
REM Usage: run_claude_opus41.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_claude_opus41.bat --prompt-style colorful test_images
REM   run_claude_opus41.bat test_images --dry-run
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."

idt.exe workflow --provider claude --model claude-opus-4-1-20250805 --output-dir Descriptions %*
ENDLOCAL
