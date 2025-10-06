@echo off
REM Run workflow with Claude Haiku 3.5 (fastest, most affordable)
REM Usage: run_claude_haiku35.bat <image_directory>
REM Requires: claude.txt with API key in current directory OR ANTHROPIC_API_KEY environment variable

..\.venv\Scripts\python.exe ..\workflow.py --provider claude --model claude-3-5-haiku-20241022 --prompt-style narrative --output-dir ..\Descriptions %1
