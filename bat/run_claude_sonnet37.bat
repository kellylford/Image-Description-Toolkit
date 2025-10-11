@echo off
SETLOCAL
REM Run workflow with Ollama claude-3-7-sonnet-20250219
REM Usage: run_claude_sonnet37.bat [options] <image_directory>
REM Supports all workflow options in any order

REM Change to project root directory to ensure config files are found
cd /d "%~dp0\.."
python workflow.py --provider ollama --model claude-3-7-sonnet-20250219 --output-dir Descriptions %*
ENDLOCAL
