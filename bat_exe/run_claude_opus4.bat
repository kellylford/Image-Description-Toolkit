@echo off
SETLOCAL
REM Run workflow with Claude Opus 4 (very high intelligence)
REM Usage: run_claude_opus4.bat <image_directory> [prompt_style]
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\dist\idt.exe workflow --provider claude --model claude-opus-4-20250514 --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
