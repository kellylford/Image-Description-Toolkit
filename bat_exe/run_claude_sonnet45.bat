@echo off
SETLOCAL
REM Run workflow with Claude Sonnet 4.5 (RECOMMENDED - best for agents/coding)
REM Usage: run_claude_sonnet45.bat [options] <image_directory>
REM Supports all workflow options in any order, e.g.:
REM   run_claude_sonnet45.bat --prompt-style colorful test_images
REM   run_claude_sonnet45.bat test_images --dry-run
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

..\idt.exe workflow --provider claude --model claude-sonnet-4-5-20250929 --output-dir ..\Descriptions %*
ENDLOCAL
