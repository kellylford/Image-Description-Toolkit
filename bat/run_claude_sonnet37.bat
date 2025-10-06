@echo off
REM Run workflow with Claude Sonnet 3.7 (high performance with extended thinking)
REM Usage: run_claude_sonnet37.bat <image_directory>
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

..\.venv\Scripts\python.exe ..\workflow.py --provider claude --model claude-3-7-sonnet-20250219 --prompt-style narrative --output-dir ..\Descriptions %1
