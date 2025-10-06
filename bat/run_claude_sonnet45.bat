@echo off
REM Run workflow with Claude Sonnet 4.5 (RECOMMENDED - best for agents/coding)
REM Usage: run_claude_sonnet45.bat <image_directory>
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

..\.venv\Scripts\python.exe ..\workflow.py --provider claude --model claude-sonnet-4-5-20250929 --prompt-style narrative --output-dir ..\Descriptions %1
