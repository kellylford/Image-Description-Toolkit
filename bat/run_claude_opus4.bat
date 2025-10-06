@echo off
REM Run workflow with Claude Opus 4 (very high intelligence)
REM Usage: run_claude_opus4.bat <image_directory>
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

..\.venv\Scripts\python.exe ..\workflow.py --provider claude --model claude-opus-4-20250514 --prompt-style narrative --output-dir ..\Descriptions %1
