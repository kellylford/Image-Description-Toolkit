@echo off
SETLOCAL
REM Run workflow with Claude Haiku 3 (fast and compact)
REM Usage: run_claude_haiku3.bat <image_directory> [prompt_style]
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\..\idt.exe workflow --provider claude --model claude-3-haiku-20240307 --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
