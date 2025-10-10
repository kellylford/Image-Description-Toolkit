@echo off
SETLOCAL
REM Run workflow with Claude claude-sonnet-4-5-20250929
REM Usage: run_claude_sonnet45.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."

idt.exe workflow --provider claude --model claude-sonnet-4-5-20250929 --output-dir Descriptions %*
ENDLOCAL