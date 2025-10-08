@echo off
SETLOCAL
REM Run workflow with Claude Sonnet 3.7 (extended thinking)
REM Usage: run_claude_sonnet37.bat <image_directory> [prompt_style]
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

SET PROMPT_STYLE=%2
IF "%PROMPT_STYLE%"=="" SET PROMPT_STYLE=narrative

..\.venv\Scripts\python.exe ..\workflow.py --provider claude --model claude-3-7-sonnet-20250219 --prompt-style %PROMPT_STYLE% --output-dir ..\Descriptions %1
ENDLOCAL
